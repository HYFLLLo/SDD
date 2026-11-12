"""T-022 通知功能闭环 测试。

测试 GET /api/notifications（列表+unread_only+分页）+ POST /api/notifications/read（标记已读）+
submit 路由层通知生成（your_turn/node_submitted/chain_done）。
"""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.core.security import create_access_token, hash_password
from src.db.models import Base, Chain, ChainMember, Node, Notification, User
from src.db.session import get_db
from src.main import app

# 独立测试库（内存 SQLite，与运行时业务库物理隔离）
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """每测试函数建表 + 销毁。"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture()
def override_db(test_db: AsyncSession) -> Generator[None, None, None]:
    """通过 dependency_overrides 注入测试库 session。"""

    async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


async def _create_user(db: AsyncSession, username: str, nickname: str) -> User:
    """创建用户。"""
    user = User(
        username=username,
        password_hash=hash_password("pass1234"),
        nickname=nickname,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _create_in_progress_chain(
    db: AsyncSession,
    creator: User,
    extra_members: list[User] | None = None,
    chain_length: int = 4,
    title: str = "通知测试链",
) -> tuple[Chain, Node]:
    """创建 in_progress 链 + seq=0 pending 节点（author=creator）+ 成员。

    返回 (chain, node0)。用于 submit 测试（submit node0 → 推进 → 生成通知）。
    """
    import datetime

    now = datetime.datetime.now(datetime.UTC)
    chain = Chain(
        title=title,
        chain_length=chain_length,
        prompt_source="manual",
        prompt_text="起手题",
        visibility="public",
        room_code="N" + title[-3:].upper().ljust(5, "X")[:5],
        status="in_progress",
        creator_id=creator.id,
        current_seq=0,
        created_at=now,
        expires_at=now + datetime.timedelta(days=7),
    )
    db.add(chain)
    await db.flush()

    # 创建者成员 + 额外成员
    # extra_members 显式设 joined_at 晚于创建者（now+1秒），保证 sort(joined_at)
    # 时创建者在前、后续成员在后。测试环境同事务快速执行，server_default 时间戳
    # 可能相同导致轮转排序不稳定（test_t017 同款问题）。
    db.add(ChainMember(chain_id=chain.id, user_id=creator.id))
    for i, m in enumerate(extra_members or []):
        db.add(
            ChainMember(
                chain_id=chain.id,
                user_id=m.id,
                joined_at=now + datetime.timedelta(seconds=i + 1),
            )
        )

    # seq=0 pending 节点（draw，author=creator）
    node0 = Node(
        chain_id=chain.id,
        seq=0,
        type="draw",
        author_id=creator.id,
        content_type=None,
        content_url=None,
        content_text=None,
        is_ai=False,
        author_label=creator.nickname,
        status="pending",
    )
    db.add(node0)
    await db.flush()
    return chain, node0


def _token(user: User) -> str:
    """生成 JWT token。"""
    return create_access_token(user.id, user.nickname)


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user)}"}


async def _create_notification(
    db: AsyncSession,
    user_id: str,
    type: str,
    chain_id: str,
    chain_title: str,
    read: bool = False,
) -> Notification:
    """直接构造通知数据（用于列表/已读测试）。"""
    notif = Notification(
        user_id=user_id,
        type=type,
        chain_id=chain_id,
        chain_title=chain_title,
        read=read,
    )
    db.add(notif)
    await db.flush()
    await db.refresh(notif)
    return notif


# ---- GET /api/notifications ----


@pytest.mark.asyncio
async def test_list_notifications_empty(
    override_db: None, test_db: AsyncSession
) -> None:
    """无通知 → 空列表。"""
    user = await _create_user(test_db, "notifuser1", "通知A")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/notifications", headers=_auth_headers(user))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_notifications_returns(
    override_db: None, test_db: AsyncSession
) -> None:
    """有通知 → 列表含 type/chain_title/read。"""
    user = await _create_user(test_db, "notifuser2", "通知B")
    await _create_notification(test_db, user.id, "your_turn", "chain-1", "戴帽子的猫")
    await _create_notification(test_db, user.id, "chain_done", "chain-1", "戴帽子的猫", read=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/notifications", headers=_auth_headers(user))
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 2
    types = {i["type"] for i in items}
    assert types == {"your_turn", "chain_done"}
    for item in items:
        assert item["chain_title"] == "戴帽子的猫"
        assert "read" in item


@pytest.mark.asyncio
async def test_list_notifications_unread_only(
    override_db: None, test_db: AsyncSession
) -> None:
    """unread_only=true 只返回未读。"""
    user = await _create_user(test_db, "notifuser3", "通知C")
    await _create_notification(test_db, user.id, "your_turn", "c1", "链1", read=False)
    await _create_notification(test_db, user.id, "chain_done", "c1", "链1", read=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/notifications?unread_only=true", headers=_auth_headers(user)
        )
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["read"] is False
    assert items[0]["type"] == "your_turn"


@pytest.mark.asyncio
async def test_list_notifications_pagination(
    override_db: None, test_db: AsyncSession
) -> None:
    """分页。"""
    user = await _create_user(test_db, "notifuser4", "通知D")
    for i in range(3):
        await _create_notification(test_db, user.id, "node_submitted", "c1", f"链{i}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/notifications?page=1&page_size=2", headers=_auth_headers(user)
        )
    data = resp.json()["data"]
    assert len(data["items"]) == 2
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_list_notifications_no_token(override_db: None) -> None:
    """无 token → 401。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/notifications")
    assert resp.status_code == 401


# ---- POST /api/notifications/read ----


@pytest.mark.asyncio
async def test_mark_read_success(
    override_db: None, test_db: AsyncSession
) -> None:
    """标记已读 → read_count + 再查已读。"""
    user = await _create_user(test_db, "notifuser5", "通知E")
    n1 = await _create_notification(test_db, user.id, "your_turn", "c1", "链1")
    n2 = await _create_notification(test_db, user.id, "chain_done", "c1", "链1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/notifications/read",
            json={"notification_ids": [n1.id, n2.id]},
            headers=_auth_headers(user),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["read_count"] == 2

        # 再查 → 全部已读
        resp2 = await client.get(
            "/api/notifications?unread_only=true", headers=_auth_headers(user)
        )
    assert resp2.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_mark_read_only_own(
    override_db: None, test_db: AsyncSession
) -> None:
    """只标记自己的通知（防越权）。"""
    user_a = await _create_user(test_db, "notifuser6", "通知F")
    user_b = await _create_user(test_db, "notifuser7", "通知G")
    # B 的通知（A 不应能标记它）
    n_b = await _create_notification(test_db, user_b.id, "your_turn", "c1", "链1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # A 尝试标记 B 的通知（应不生效，read_count=0）
        resp = await client.post(
            "/api/notifications/read",
            json={"notification_ids": [n_b.id]},
            headers=_auth_headers(user_a),
        )
    assert resp.status_code == 200
    assert resp.json()["data"]["read_count"] == 0  # B 的通知不属于 A


@pytest.mark.asyncio
async def test_mark_read_empty_ids(
    override_db: None, test_db: AsyncSession
) -> None:
    """空 ids → read_count=0。"""
    user = await _create_user(test_db, "notifuser8", "通知H")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/notifications/read",
            json={"notification_ids": []},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 200
    assert resp.json()["data"]["read_count"] == 0


# ---- submit 路由层通知生成 ----


@pytest.mark.asyncio
async def test_submit_generates_your_turn_notification(
    override_db: None, test_db: AsyncSession
) -> None:
    """submit 后下一位责任人收到 your_turn 通知 + 成员收到 node_submitted。"""
    creator = await _create_user(test_db, "notifuser9", "通知I")
    member2 = await _create_user(test_db, "notifuser10", "通知J")
    chain, node0 = await _create_in_progress_chain(
        test_db, creator, extra_members=[member2]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # creator 提交 seq=0 draw
        resp = await client.post(
            f"/api/nodes/{chain.id}/submit",
            json={"content_type": "image", "content_url": "/uploads/n0.png"},
            headers=_auth_headers(creator),
        )
    assert resp.status_code == 200
    assert resp.json()["data"]["chain_status"] == "in_progress"

    # 下一位（member2，按成员轮转 idx=1%2=1）应收到 your_turn 通知
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_m2 = await client.get(
            "/api/notifications", headers=_auth_headers(member2)
        )
    m2_notifs = resp_m2.json()["data"]["items"]
    m2_types = {n["type"] for n in m2_notifs}
    assert "your_turn" in m2_types  # 下一位收到 your_turn
    assert "node_submitted" in m2_types  # 成员收到 node_submitted

    # creator 也应收到 node_submitted（但不应收到 your_turn，因为是 creator 提交的）
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_cr = await client.get(
            "/api/notifications", headers=_auth_headers(creator)
        )
    cr_notifs = resp_cr.json()["data"]["items"]
    cr_types = {n["type"] for n in cr_notifs}
    assert "node_submitted" in cr_types
    assert "your_turn" not in cr_types  # creator 不是下一位


@pytest.mark.asyncio
async def test_submit_generates_chain_done_notification(
    override_db: None, test_db: AsyncSession
) -> None:
    """链完成 submit 后成员收到 chain_done 通知。"""
    creator = await _create_user(test_db, "notifuser11", "通知K")
    # 构造 chain_length=1 的链，提交 seq=0 即完成
    chain, node0 = await _create_in_progress_chain(
        test_db, creator, chain_length=1
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/nodes/{chain.id}/submit",
            json={"content_type": "image", "content_url": "/uploads/n0.png"},
            headers=_auth_headers(creator),
        )
    assert resp.status_code == 200
    assert resp.json()["data"]["chain_status"] == "completed"

    # creator 应收到 chain_done 通知
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_cr = await client.get(
            "/api/notifications", headers=_auth_headers(creator)
        )
    cr_notifs = resp_cr.json()["data"]["items"]
    cr_types = {n["type"] for n in cr_notifs}
    assert "chain_done" in cr_types
