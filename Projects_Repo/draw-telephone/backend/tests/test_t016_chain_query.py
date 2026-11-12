"""T-016 链查询/加入功能闭环 测试。

测试 房间码查询/加入链/链大厅详情，使用独立测试库。
"""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.core.security import create_access_token, hash_password
from src.db.models import Base, Chain, ChainMember, User
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
    """每测试函数建表 + 销毁，不污染运行时库。"""
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


async def _create_test_user(
    db: AsyncSession, username: str = "chainuser", nickname: str = "链用户"
) -> User:
    """在测试库中创建用户并返回。"""
    user = User(
        username=username,
        password_hash=hash_password("pass1234"),
        nickname=nickname,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _create_test_chain(
    db: AsyncSession, creator: User, room_code: str = "TEST01"
) -> Chain:
    """在测试库中直接创建链 + 创建者成员 + 第一节点。"""

    from src.repositories.chain import ChainRepository

    repo = ChainRepository(db)
    chain = await repo.create_chain_with_first_node(
        creator_id=creator.id,
        title="测试链",
        chain_length=4,
        visibility="invite",
        prompt_source="manual",
        prompt_text="戴帽子的猫",
        creator_nickname=creator.nickname,
    )
    # 覆盖 room_code 为固定值方便测试
    chain.room_code = room_code
    await db.flush()
    return chain


# ---------- GET /api/chains/{room_code} ----------


@pytest.mark.asyncio
async def test_lookup_chain_success(override_db: None, test_db: AsyncSession) -> None:
    """房间码查询成功 → 200 + ChainLookup。"""
    creator = await _create_test_user(test_db, "creator1", "创建者A")
    await _create_test_chain(test_db, creator, "ABC123")
    token = create_access_token(creator.id, creator.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/chains/ABC123",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "测试链"
    assert data["chain_length"] == 4
    assert data["current_seq"] == 0
    assert data["is_full"] is False
    assert data["remaining_slots"] == 3  # 4 - 1 创建者


@pytest.mark.asyncio
async def test_lookup_chain_invalid_code(override_db: None, test_db: AsyncSession) -> None:
    """无效房间码 → 404。"""
    user = await _create_test_user(test_db)
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/chains/NOPE00",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404
    assert resp.json()["code"] == 404


@pytest.mark.asyncio
async def test_lookup_chain_no_token(override_db: None) -> None:
    """无 token → 401。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/chains/ABC123")
    assert resp.status_code == 401


# ---------- POST /api/chains/{id}/join ----------


@pytest.mark.asyncio
async def test_join_chain_success(override_db: None, test_db: AsyncSession) -> None:
    """加入链成功 → 200 + joined=true。"""
    creator = await _create_test_user(test_db, "creator2", "创建者B")
    chain = await _create_test_chain(test_db, creator, "JOIN01")
    joiner = await _create_test_user(test_db, "joiner1", "加入者1")
    token = create_access_token(joiner.id, joiner.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/chains/{chain.id}/join",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["chain_id"] == chain.id
    assert data["joined"] is True

    # 验证 DB 持久化：成员数=2
    members = (
        await test_db.execute(select(ChainMember).where(ChainMember.chain_id == chain.id))
    ).scalars().all()
    assert len(members) == 2


@pytest.mark.asyncio
async def test_join_chain_duplicate(override_db: None, test_db: AsyncSession) -> None:
    """重复加入 → 403。"""
    creator = await _create_test_user(test_db, "creator3", "创建者C")
    chain = await _create_test_chain(test_db, creator, "DUP001")
    token = create_access_token(creator.id, creator.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/chains/{chain.id}/join",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403
    assert "成员" in resp.json()["message"]


@pytest.mark.asyncio
async def test_join_chain_full(override_db: None, test_db: AsyncSession) -> None:
    """链已满 → 403。"""
    creator = await _create_test_user(test_db, "creator4", "创建者D")
    chain = await _create_test_chain(test_db, creator, "FULL01")
    # chain_length=4，创建者占 1，再加 3 个成员凑满
    for i in range(3):
        m = await _create_test_user(test_db, f"filler{i}", f"填充{i}")
        from src.repositories.chain import ChainRepository

        await ChainRepository(test_db).add_member(chain.id, m.id)
    extra = await _create_test_user(test_db, "extra", "额外")
    token = create_access_token(extra.id, extra.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/chains/{chain.id}/join",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403
    assert "已满" in resp.json()["message"]


@pytest.mark.asyncio
async def test_join_chain_not_found(override_db: None, test_db: AsyncSession) -> None:
    """链不存在 → 404。"""
    user = await _create_test_user(test_db)
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chains/nonexistent-id/join",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


# ---------- GET /api/chains/{id}/detail ----------


@pytest.mark.asyncio
async def test_get_chain_detail_success(override_db: None, test_db: AsyncSession) -> None:
    """链大厅详情成功 → 200 + ChainDetail（含推导进度节点链）。"""
    creator = await _create_test_user(test_db, "creator5", "创建者E")
    chain = await _create_test_chain(test_db, creator, "DET001")
    token = create_access_token(creator.id, creator.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/chains/{chain.id}/detail",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == chain.id
    assert data["chain_length"] == 4
    assert data["current_seq"] == 0
    assert data["current_node_type"] == "draw"
    assert data["current_author"]["nickname"] == "创建者E"
    # T-024：in_progress + pending 节点 → ai_countdown_at = created_at + 24h（真实值）
    assert data["ai_countdown_at"] is not None
    # 成员
    assert len(data["members"]) == 1
    assert data["members"][0]["nickname"] == "创建者E"
    # 进度节点链：chain_length=4 个节点，seq=0 已建（draw 创建者），seq 1-3 未建占位
    assert len(data["nodes"]) == 4
    assert data["nodes"][0]["seq"] == 0
    assert data["nodes"][0]["type"] == "draw"
    assert data["nodes"][0]["author"]["nickname"] == "创建者E"
    assert data["nodes"][1]["seq"] == 1
    assert data["nodes"][1]["type"] == "describe"  # seq 奇数=述
    assert data["nodes"][1]["author"]["nickname"] == "待接"  # 未建占位
    assert data["nodes"][2]["type"] == "draw"  # seq 偶数=画
    assert data["nodes"][3]["type"] == "describe"


@pytest.mark.asyncio
async def test_get_chain_detail_non_member(override_db: None, test_db: AsyncSession) -> None:
    """非链成员访问 → 403。"""
    creator = await _create_test_user(test_db, "creator6", "创建者F")
    chain = await _create_test_chain(test_db, creator, "NOM001")
    outsider = await _create_test_user(test_db, "outsider", "外人")
    token = create_access_token(outsider.id, outsider.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/chains/{chain.id}/detail",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403
    assert resp.json()["code"] == 403


@pytest.mark.asyncio
async def test_get_chain_detail_not_found(override_db: None, test_db: AsyncSession) -> None:
    """链不存在 → 404。"""
    user = await _create_test_user(test_db)
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/chains/nonexistent-id/detail",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_chain_detail_after_join(override_db: None, test_db: AsyncSession) -> None:
    """加入者也能访问链大厅详情 → 200。"""
    creator = await _create_test_user(test_db, "creator7", "创建者G")
    chain = await _create_test_chain(test_db, creator, "AFT001")
    joiner = await _create_test_user(test_db, "joiner2", "加入者2")
    token_joiner = create_access_token(joiner.id, joiner.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 加入
        await client.post(
            f"/api/chains/{chain.id}/join",
            headers={"Authorization": f"Bearer {token_joiner}"},
        )
        # 加入后访问详情
        resp = await client.get(
            f"/api/chains/{chain.id}/detail",
            headers={"Authorization": f"Bearer {token_joiner}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["members"]) == 2  # 创建者 + 加入者
