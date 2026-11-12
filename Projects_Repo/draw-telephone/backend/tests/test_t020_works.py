"""T-020 作品详情功能闭环 测试。

测试 GET /api/works（广场列表）+ GET /api/works/{id}（只读全链），使用独立测试库。
构造 completed 链（建链 + 提交全部节点）验证作品列表 + 详情。
"""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.core.security import hash_password
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


async def _create_completed_chain(
    db: AsyncSession,
    creator: User,
    chain_length: int = 4,
    title: str = "测试作品",
    prompt_text: str = "起手题",
) -> Chain:
    """创建一条已完成的链（全部节点 submitted，status=completed）。

    chain_length=4：seq=0 draw, seq=1 describe, seq=2 draw, seq=3 describe
    """
    import datetime

    now = datetime.datetime.now(datetime.UTC)
    chain = Chain(
        title=title,
        chain_length=chain_length,
        prompt_source="manual",
        prompt_text=prompt_text,
        visibility="public",
        room_code="T" + title[-3:].upper().ljust(5, "X")[:5],
        status="completed",
        creator_id=creator.id,
        current_seq=chain_length,
        created_at=now,
        completed_at=now,
        expires_at=now + datetime.timedelta(days=7),
    )
    db.add(chain)
    await db.flush()

    # 创建者成员
    db.add(ChainMember(chain_id=chain.id, user_id=creator.id))

    # 全部节点 submitted
    for seq in range(chain_length):
        node_type = "draw" if seq % 2 == 0 else "describe"
        if node_type == "draw":
            content_type = "image"
            content_url = f"/uploads/draw{seq}.png"
            content_text = None
        else:
            content_type = "text"
            content_url = None
            content_text = f"描述{seq}"
        node = Node(
            chain_id=chain.id,
            seq=seq,
            type=node_type,
            author_id=creator.id,
            content_type=content_type,
            content_url=content_url,
            content_text=content_text,
            is_ai=False,
            author_label=creator.nickname,
            status="submitted",
            submitted_at=now,
        )
        db.add(node)
    await db.flush()
    return chain


# ---- GET /api/works 广场列表 ----


@pytest.mark.asyncio
async def test_list_works_empty(override_db: None) -> None:
    """无作品 → 空列表。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/works")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_list_works_returns_completed_chains(
    override_db: None, test_db: AsyncSession
) -> None:
    """广场列表返回 completed 链（含 member_count/like_count/thumb_url）。"""
    creator = await _create_user(test_db, "workuser1", "小A")
    chain = await _create_completed_chain(test_db, creator, title="戴帽子的猫")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/works")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == chain.id
    assert item["title"] == "戴帽子的猫"
    assert item["chain_length"] == 4
    assert item["member_count"] == 1
    assert item["like_count"] == 0  # 无投票
    assert item["thumb_url"] == "/uploads/draw0.png"  # 第一个 draw 节点


@pytest.mark.asyncio
async def test_list_works_excludes_incomplete_chains(
    override_db: None, test_db: AsyncSession
) -> None:
    """广场列表只返回 completed 链，in_progress 不展示。"""
    creator = await _create_user(test_db, "workuser2", "小B")
    # 已完成链
    await _create_completed_chain(test_db, creator, title="已完成作品")
    # 未完成链（in_progress）
    import datetime

    now = datetime.datetime.now(datetime.UTC)
    chain2 = Chain(
        title="未完成作品",
        chain_length=4,
        prompt_source="manual",
        prompt_text="题",
        visibility="public",
        room_code="INCOM1",
        status="in_progress",
        creator_id=creator.id,
        current_seq=1,
        created_at=now,
        expires_at=now + datetime.timedelta(days=7),
    )
    test_db.add(chain2)
    await test_db.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/works")
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["title"] == "已完成作品"


@pytest.mark.asyncio
async def test_list_works_pagination(override_db: None, test_db: AsyncSession) -> None:
    """分页：page + page_size。"""
    creator = await _create_user(test_db, "workuser3", "小C")
    for i in range(3):
        await _create_completed_chain(test_db, creator, title=f"作品{i}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/works?page=1&page_size=2")
    data = resp.json()["data"]
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2


@pytest.mark.asyncio
async def test_list_works_guest_accessible(override_db: None) -> None:
    """广场列表游客可访问（无 token 不报 401）。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/works")
    assert resp.status_code == 200  # 无 token 仍 200


# ---- GET /api/works/{id} 作品详情 ----


@pytest.mark.asyncio
async def test_get_work_detail_success(
    override_db: None, test_db: AsyncSession
) -> None:
    """作品详情 → 全链节点（含 author/content_url/content_text/is_ai）。"""
    creator = await _create_user(test_db, "workuser4", "小D")
    chain = await _create_completed_chain(test_db, creator, chain_length=4)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/works/{chain.id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == chain.id
    assert data["status"] == "completed"
    assert data["creator"]["nickname"] == "小D"
    assert len(data["nodes"]) == 4
    # seq=0 draw 节点
    n0 = data["nodes"][0]
    assert n0["seq"] == 0
    assert n0["type"] == "draw"
    assert n0["content_type"] == "image"
    assert n0["content_url"] == "/uploads/draw0.png"
    assert n0["is_ai"] is False
    # seq=1 describe 节点
    n1 = data["nodes"][1]
    assert n1["type"] == "describe"
    assert n1["content_type"] == "text"
    assert n1["content_text"] == "描述1"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_get_work_detail_not_found(override_db: None) -> None:
    """作品不存在 → 404。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/works/nonexistent-id")
    assert resp.status_code == 404
    assert resp.json()["code"] == 404
    assert "作品不存在" in resp.json()["message"]


@pytest.mark.asyncio
async def test_get_work_detail_incomplete_404(
    override_db: None, test_db: AsyncSession
) -> None:
    """未完成链查作品详情 → 404（只读全链要求已完成）。"""
    creator = await _create_user(test_db, "workuser5", "小E")
    import datetime

    now = datetime.datetime.now(datetime.UTC)
    chain = Chain(
        title="未完成",
        chain_length=4,
        prompt_source="manual",
        prompt_text="题",
        visibility="public",
        room_code="INCOM2",
        status="in_progress",
        creator_id=creator.id,
        current_seq=1,
        created_at=now,
        expires_at=now + datetime.timedelta(days=7),
    )
    test_db.add(chain)
    await test_db.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/works/{chain.id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_work_detail_guest_accessible(
    override_db: None, test_db: AsyncSession
) -> None:
    """作品详情游客可访问（无 token 不报 401）。"""
    creator = await _create_user(test_db, "workuser6", "小F")
    chain = await _create_completed_chain(test_db, creator)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/works/{chain.id}")
    assert resp.status_code == 200  # 无 token 仍 200


@pytest.mark.asyncio
async def test_get_work_detail_ai_node_tag(
    override_db: None, test_db: AsyncSession
) -> None:
    """AI 补位节点 is_ai=true 标签。"""
    creator = await _create_user(test_db, "workuser7", "小G")
    chain = await _create_completed_chain(test_db, creator, chain_length=4)
    # 把 seq=2 节点改为 AI 补位（author_id=None，nickname fallback 到 author_label）
    from sqlalchemy import select

    result = await test_db.execute(
        select(Node).where(Node.chain_id == chain.id, Node.seq == 2)
    )
    node2 = result.scalar_one()
    node2.is_ai = True
    node2.author_id = None  # AI 补位节点无真实作者
    node2.author_label = "AI"
    await test_db.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/works/{chain.id}")
    nodes = resp.json()["data"]["nodes"]
    assert nodes[2]["is_ai"] is True
    assert nodes[2]["author"]["nickname"] == "AI"
    assert nodes[0]["is_ai"] is False
