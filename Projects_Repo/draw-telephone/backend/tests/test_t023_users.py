"""T-023 个人资料/我的作品功能闭环 测试。

测试 GET /api/users/me（个人资料 + 参与链数/创建链数统计）+
GET /api/users/me/works（我的作品列表，含 role/status/thumb_url）。
"""

import datetime
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.core.security import create_access_token, hash_password
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


def _token(user: User) -> str:
    """生成 JWT token。"""
    return create_access_token(user.id, user.username)


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user)}"}


async def _create_chain(
    db: AsyncSession,
    creator: User,
    *,
    title: str = "我的链",
    chain_length: int = 4,
    status: str = "in_progress",
    room_code: str = "T023A",
    with_creator_member: bool = True,
    with_thumb: bool = False,
) -> Chain:
    """创建链（creator 创建）。with_creator_member 时加创建者成员。
    with_thumb 时加 seq=0 draw 节点带 content_url（造 thumb_url）。
    """
    now = datetime.datetime.now(datetime.UTC)
    chain = Chain(
        title=title,
        chain_length=chain_length,
        prompt_source="manual",
        prompt_text="起手题",
        visibility="public",
        room_code=room_code,
        status=status,
        creator_id=creator.id,
        current_seq=0,
        created_at=now,
        expires_at=now + datetime.timedelta(days=7),
    )
    db.add(chain)
    await db.flush()

    if with_creator_member:
        db.add(ChainMember(chain_id=chain.id, user_id=creator.id))

    if with_thumb:
        # seq=0 draw 节点带 content_url（thumb_url 取第一个 draw 节点 content_url）
        db.add(
            Node(
                chain_id=chain.id,
                seq=0,
                type="draw",
                author_id=creator.id,
                content_type="image",
                content_url="/uploads/thumb.png",
                content_text=None,
                is_ai=False,
                author_label=creator.nickname,
                status="submitted",
            )
        )
    await db.flush()
    return chain


async def _join_chain(db: AsyncSession, chain: Chain, user: User) -> None:
    """用户加入链（成员）。显式设 joined_at 晚于创建者（轮转顺序稳定）。"""
    now = datetime.datetime.now(datetime.UTC)
    db.add(
        ChainMember(
            chain_id=chain.id,
            user_id=user.id,
            joined_at=now + datetime.timedelta(seconds=1),
        )
    )
    await db.flush()


# ---- GET /api/users/me ----


@pytest.mark.asyncio
async def test_get_profile_basic(override_db: None, test_db: AsyncSession) -> None:
    """个人资料含 nickname/username/created_at。"""
    user = await _create_user(test_db, "profile1", "资料甲")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/users/me", headers=_auth_headers(user))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == user.id
    assert data["username"] == "profile1"
    assert data["nickname"] == "资料甲"
    assert "created_at" in data
    assert "avatar_url" in data


@pytest.mark.asyncio
async def test_get_profile_stats_zero(override_db: None, test_db: AsyncSession) -> None:
    """新用户参与=0/创建=0。"""
    user = await _create_user(test_db, "profile2", "资料乙")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/users/me", headers=_auth_headers(user))
    data = resp.json()["data"]
    assert data["participated_chains"] == 0
    assert data["created_chains"] == 0


@pytest.mark.asyncio
async def test_get_profile_stats_after_activity(
    override_db: None, test_db: AsyncSession
) -> None:
    """建链+加入后 participated/created 正确。"""
    creator = await _create_user(test_db, "profile3", "资料丙")
    other = await _create_user(test_db, "profile4", "资料丁")
    # creator 建链（创建者成员）→ created=1, participated=1
    await _create_chain(test_db, creator, room_code="STAT1")
    # creator 加入另一条链 → participated=2
    chain2 = await _create_chain(
        test_db, other, room_code="STAT2", with_creator_member=True
    )
    await _join_chain(test_db, chain2, creator)
    await test_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/users/me", headers=_auth_headers(creator))
    data = resp.json()["data"]
    assert data["participated_chains"] == 2  # 自己建的 + 加入的
    assert data["created_chains"] == 1  # 只建了 1 条


@pytest.mark.asyncio
async def test_get_profile_no_token(override_db: None) -> None:
    """无 token → 401。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/users/me")
    assert resp.status_code == 401


# ---- GET /api/users/me/works ----


@pytest.mark.asyncio
async def test_my_works_empty(override_db: None, test_db: AsyncSession) -> None:
    """无作品 → 空列表。"""
    user = await _create_user(test_db, "works1", "作品甲")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/users/me/works", headers=_auth_headers(user))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_my_works_as_creator(override_db: None, test_db: AsyncSession) -> None:
    """创建者作品 role=creator。"""
    creator = await _create_user(test_db, "works2", "作品乙")
    await _create_chain(test_db, creator, room_code="CR1", with_thumb=True)
    await test_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/users/me/works", headers=_auth_headers(creator))
    data = resp.json()["data"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["role"] == "creator"
    assert item["title"] == "我的链"
    assert item["thumb_url"] == "/uploads/thumb.png"


@pytest.mark.asyncio
async def test_my_works_as_participant(override_db: None, test_db: AsyncSession) -> None:
    """参与者作品 role=participant。"""
    creator = await _create_user(test_db, "works3", "作品丙")
    participant = await _create_user(test_db, "works4", "作品丁")
    chain = await _create_chain(
        test_db, creator, room_code="PT1", with_creator_member=True, with_thumb=True
    )
    await _join_chain(test_db, chain, participant)
    await test_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/users/me/works", headers=_auth_headers(participant)
        )
    data = resp.json()["data"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["role"] == "participant"
    assert item["thumb_url"] == "/uploads/thumb.png"


@pytest.mark.asyncio
async def test_my_works_includes_in_progress(
    override_db: None, test_db: AsyncSession
) -> None:
    """含进行中链（status=in_progress）。"""
    creator = await _create_user(test_db, "works5", "作品戊")
    await _create_chain(
        test_db, creator, room_code="IP1", status="in_progress", with_thumb=True
    )
    await test_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/users/me/works", headers=_auth_headers(creator))
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["status"] == "in_progress"


@pytest.mark.asyncio
async def test_my_works_pagination(override_db: None, test_db: AsyncSession) -> None:
    """分页。"""
    creator = await _create_user(test_db, "works6", "作品己")
    for i in range(3):
        await _create_chain(
            test_db, creator, title=f"链{i}", room_code=f"PG{i}", with_thumb=True
        )
    await test_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/users/me/works?page=1&page_size=2", headers=_auth_headers(creator)
        )
    data = resp.json()["data"]
    assert len(data["items"]) == 2
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_my_works_no_token(override_db: None) -> None:
    """无 token → 401。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/users/me/works")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_my_works_not_in_others(
    override_db: None, test_db: AsyncSession
) -> None:
    """用户看不到他人参与/创建的链（防越权）。"""
    user_a = await _create_user(test_db, "works7", "作品庚")
    user_b = await _create_user(test_db, "works8", "作品辛")
    # B 建链 + B 成员，A 未参与
    await _create_chain(test_db, user_b, room_code="NO1", with_creator_member=True)
    await test_db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/users/me/works", headers=_auth_headers(user_a))
    data = resp.json()["data"]
    assert data["total"] == 0  # A 看不到 B 的链
