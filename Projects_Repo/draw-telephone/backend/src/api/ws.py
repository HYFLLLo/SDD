"""WebSocket 连接管理器（房间广播）。

内存管理 chain_id -> set[WebSocket]，不落 DB。
- connect：接受连接并加入房间
- disconnect：移出房间
- broadcast：广播给同房间所有在线连接
- broadcast_notify：广播 notify 通知事件（submit 路由层触发，service 层不感知 WS）

WS 鉴权在端点层用 query param token + decode_token（浏览器 WS 不能设自定义 header）。
"""

from fastapi import WebSocket

from pycore.core import get_logger

logger = get_logger()


class ConnectionManager:
    """房间 WebSocket 连接管理（内存单例）。"""

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}

    async def connect(self, chain_id: str, ws: WebSocket) -> None:
        """接受连接并加入房间。"""
        await ws.accept()
        self._rooms.setdefault(chain_id, set()).add(ws)
        logger.info("WS connected", chain_id=chain_id)

    def disconnect(self, chain_id: str, ws: WebSocket) -> None:
        """移出房间（连接断开时调用）。"""
        room = self._rooms.get(chain_id)
        if room is not None:
            room.discard(ws)
            if not room:
                self._rooms.pop(chain_id, None)

    async def broadcast(self, chain_id: str, message: dict) -> None:
        """广播给同房间所有在线连接。

        发送失败的连接自动移除（已断开）。
        """
        room = list(self._rooms.get(chain_id, set()))
        for ws in room:
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001 连接已断开等，移除即可
                self.disconnect(chain_id, ws)

    async def broadcast_notify(
        self, chain_id: str, event: str, node_seq: int
    ) -> None:
        """广播 notify 通知事件（submit 路由层触发）。

        event: your_turn / chain_done / node_submitted / ai_filled
        """
        await self.broadcast(
            chain_id,
            {
                "type": "notify",
                "event": event,
                "chain_id": chain_id,
                "node_seq": node_seq,
            },
        )


# 全局单例（路由层 + WS 端点共享同一连接池）
ws_manager = ConnectionManager()
