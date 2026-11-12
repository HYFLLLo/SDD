"""T-014 链创建功能闭环 测试。

测试创建链（房间码生成+第一节点+创建者成员），使用独立测试库。
"""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.core.security import create_access_token
from src.db.models import Base, Chain, ChainMember, Node, User
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


async def _create_test_user(db: AsyncSession, username: str = "chainuser", nickname: str = "链用户") -> User:
    """在测试库中创建用户并返回。"""
    from src.core.security import hash_password

    user = User(
        username=username,
        password_hash=hash_password("pass1234"),
        nickname=nickname,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_create_chain_success(override_db: None, test_db: AsyncSession) -> None:
    """创建链成功 → 200，返回房间码 + 链信息。"""
    user = await _create_test_user(test_db)
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chains",
            json={
                "title": "戴帽子的猫",
                "chain_length": 6,
                "visibility": "invite",
                "prompt_source": "manual",
                "prompt_text": "戴帽子的猫",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert len(data["room_code"]) == 6
    assert data["chain_length"] == 6
    assert data["visibility"] == "invite"
    assert data["prompt_source"] == "manual"
    assert data["prompt_text"] == "戴帽子的猫"
    assert data["status"] == "in_progress"
    assert data["creator_id"] == user.id
    assert data["expires_at"]  # 非空


@pytest.mark.asyncio
async def test_create_chain_persists_first_node_and_member(
    override_db: None, test_db: AsyncSession
) -> None:
    """创建链后，DB 中应有 1 链 + 1 成员 + 1 节点（seq=0, draw, pending）。"""
    user = await _create_test_user(test_db, "persistuser", "持久用户")
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chains",
            json={
                "chain_length": 4,
                "visibility": "public",
                "prompt_source": "manual",
                "prompt_text": "会飞的鱼",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    chain_id = resp.json()["data"]["id"]

    # 验证 DB 持久化
    chain = (await test_db.execute(select(Chain).where(Chain.id == chain_id))).scalar_one()
    assert chain.chain_length == 4
    assert chain.visibility == "public"
    assert chain.status == "in_progress"
    assert chain.current_seq == 0

    members = (await test_db.execute(select(ChainMember).where(ChainMember.chain_id == chain_id))).scalars().all()
    assert len(members) == 1
    assert members[0].user_id == user.id

    nodes = (await test_db.execute(select(Node).where(Node.chain_id == chain_id))).scalars().all()
    assert len(nodes) == 1
    assert nodes[0].seq == 0
    assert nodes[0].type == "draw"
    assert nodes[0].author_id == user.id
    assert nodes[0].status == "pending"
    assert nodes[0].is_ai is False
    assert nodes[0].author_label == "持久用户"


@pytest.mark.asyncio
async def test_create_chain_invalid_length(override_db: None, test_db: AsyncSession) -> None:
    """链长 <4 或 >10 → 400（Pydantic 校验经全局 handler 转为契约 400）。"""
    user = await _create_test_user(test_db)
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 链长 3（<4）
        resp = await client.post(
            "/api/chains",
            json={
                "chain_length": 3,
                "visibility": "invite",
                "prompt_source": "manual",
                "prompt_text": "x",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400  # 全局 validation handler 转 422→400
    assert resp.json()["code"] == 400


@pytest.mark.asyncio
async def test_create_chain_manual_without_prompt_text(
    override_db: None, test_db: AsyncSession
) -> None:
    """prompt_source=manual 但无 prompt_text → 400。"""
    user = await _create_test_user(test_db)
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chains",
            json={
                "chain_length": 6,
                "visibility": "invite",
                "prompt_source": "manual",
                "prompt_text": "",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 400
    assert "题词" in body["message"]


@pytest.mark.asyncio
async def test_create_chain_no_token(override_db: None) -> None:
    """无 token → 401。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chains",
            json={
                "chain_length": 6,
                "visibility": "invite",
                "prompt_source": "manual",
                "prompt_text": "x",
            },
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_room_code_format(override_db: None, test_db: AsyncSession) -> None:
    """房间码为 6 位大写字母+数字（无易混淆字符 O/0/I/1/L）。"""
    user = await _create_test_user(test_db)
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chains",
            json={
                "chain_length": 6,
                "visibility": "invite",
                "prompt_source": "manual",
                "prompt_text": "x",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    room_code = resp.json()["data"]["room_code"]
    assert len(room_code) == 6
    # 大写字母+数字，无易混淆字符
    allowed = set("ABCDEFGHJKMNPQRSTUVWXYZ23456789")
    assert all(c in allowed for c in room_code), f"room_code 含易混淆字符: {room_code}"
