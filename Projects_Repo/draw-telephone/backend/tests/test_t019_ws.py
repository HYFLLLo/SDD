"""T-019 WebSocket 实时围观功能闭环 测试。

测试 WS /ws/room/{chain_id}（JWT 鉴权 + 连接管理 + stroke 广播 + notify 广播）。
- 鉴权/订阅/断开：用 starlette TestClient 的 websocket_connect（同步 WS）
  token 用 create_access_token 直接生成（WS 端点 decode_token 只验签不查 DB，不需注册）
- 广播逻辑：直接测 ConnectionManager（用 MagicMock(spec=WebSocket)）
"""

import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.api.ws import ConnectionManager, ws_manager
from src.core.security import create_access_token
from src.main import app
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """TestClient（同步），app lifespan 的 init_db 会建表。"""
    with TestClient(app) as c:
        yield c


def _make_token() -> str:
    """生成有效 JWT（WS 端点 decode_token 只验签，不查 DB）。"""
    return create_access_token(str(uuid.uuid4()), "wstester")


# ---- 鉴权 / 订阅 / 断开（TestClient 同步 WS）----


def test_ws_connect_subscribed(client: TestClient) -> None:
    """有效 token 连接 → 收 subscribed。"""
    token = _make_token()
    with client.websocket_connect("/ws/room/test-chain-1?token=" + token) as ws:
        msg = ws.receive_json()
    assert msg == {"type": "subscribed", "chain_id": "test-chain-1"}


def test_ws_no_token_error(client: TestClient) -> None:
    """无 token → error「未认证」+ close 4401。"""
    with client.websocket_connect("/ws/room/test-chain-2") as ws:
        msg = ws.receive_json()
        assert msg == {"type": "error", "message": "未认证"}
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
    assert exc_info.value.code == 4401


def test_ws_invalid_token_error(client: TestClient) -> None:
    """无效 token → error「未认证」+ close 4401。"""
    with client.websocket_connect(
        "/ws/room/test-chain-3?token=invalid.jwt.token"
    ) as ws:
        msg = ws.receive_json()
        assert msg == {"type": "error", "message": "未认证"}
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
    assert exc_info.value.code == 4401


def test_ws_disconnect_cleanup(client: TestClient) -> None:
    """断开后连接从房间移除。"""
    token = _make_token()
    with client.websocket_connect("/ws/room/cleanup-chain?token=" + token) as ws:
        ws.receive_json()  # subscribed
        assert "cleanup-chain" in ws_manager._rooms
    # 断开后房间应清空
    assert "cleanup-chain" not in ws_manager._rooms


# ---- ConnectionManager 广播逻辑（单元测试，MagicMock(spec=WebSocket)）----


def _mock_ws() -> MagicMock:
    """构造 mock WebSocket（spec=WebSocket，类型兼容 set[WebSocket]）。"""
    ws = MagicMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_broadcast_delivers_to_all_in_room() -> None:
    """broadcast → 同房间所有连接收到消息。"""
    mgr = ConnectionManager()
    ws1, ws2 = _mock_ws(), _mock_ws()
    mgr._rooms.setdefault("room-a", set()).add(ws1)
    mgr._rooms.setdefault("room-a", set()).add(ws2)
    await mgr.broadcast("room-a", {"type": "notify", "event": "your_turn"})
    ws1.send_json.assert_awaited_once()
    ws2.send_json.assert_awaited_once()
    ws1.send_json.assert_awaited_with({"type": "notify", "event": "your_turn"})


@pytest.mark.asyncio
async def test_broadcast_notify_format() -> None:
    """broadcast_notify → 消息格式 {type:notify, event, chain_id, node_seq}。"""
    mgr = ConnectionManager()
    ws = _mock_ws()
    mgr._rooms.setdefault("room-b", set()).add(ws)
    await mgr.broadcast_notify("room-b", "chain_done", 4)
    ws.send_json.assert_awaited_with(
        {
            "type": "notify",
            "event": "chain_done",
            "chain_id": "room-b",
            "node_seq": 4,
        }
    )


@pytest.mark.asyncio
async def test_broadcast_removes_dead_connections() -> None:
    """广播时发送失败的连接自动移除。"""
    mgr = ConnectionManager()
    live_ws = _mock_ws()
    dead_ws = _mock_ws()
    dead_ws.send_json = AsyncMock(side_effect=RuntimeError("connection closed"))
    mgr._rooms.setdefault("room-c", set()).add(live_ws)
    mgr._rooms.setdefault("room-c", set()).add(dead_ws)
    await mgr.broadcast("room-c", {"type": "stroke"})
    # dead_ws 发送失败被移除，live_ws 保留
    assert dead_ws not in mgr._rooms["room-c"]
    assert live_ws in mgr._rooms["room-c"]


@pytest.mark.asyncio
async def test_broadcast_empty_room_no_error() -> None:
    """广播到不存在的房间不报错（无连接）。"""
    mgr = ConnectionManager()
    await mgr.broadcast("nonexistent", {"type": "notify"})  # 不应抛异常


@pytest.mark.asyncio
async def test_disconnect_removes_from_room() -> None:
    """disconnect 移出房间，房间空则删除。"""
    mgr = ConnectionManager()
    ws = _mock_ws()
    mgr._rooms.setdefault("room-d", set()).add(ws)
    mgr.disconnect("room-d", ws)
    assert "room-d" not in mgr._rooms


def test_ws_manager_singleton() -> None:
    """ws_manager 是全局单例（路由层 + WS 端点共享同一连接池）。"""
    from src.api.routes.nodes import ws_manager as nodes_mgr
    from src.main import ws_manager as main_mgr

    assert nodes_mgr is main_mgr is ws_manager
