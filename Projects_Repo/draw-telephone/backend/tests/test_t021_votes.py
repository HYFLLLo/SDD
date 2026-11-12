"""T-021 投票功能闭环 测试。

测试 POST /api/chains/{id}/votes（提交投票）+ GET /api/chains/{id}/votes/result（结果统计）。
构造 completed 链 + 全部 submitted 节点 + 成员，验证投票权限/三维度/唯一约束/结果统计。
"""

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


async def _create_completed_chain(
    db: AsyncSession,
    creator: User,
    extra_members: list[User] | None = None,
    chain_length: int = 4,
    title: str = "投票测试链",
) -> tuple[Chain, list[Node]]:
    """创建一条已完成的链（全部节点 submitted，status=completed）+ 成员。

    chain_length=4：seq=0 draw, seq=1 describe, seq=2 draw, seq=3 describe
    返回 (chain, nodes)。
    """
    import datetime

    now = datetime.datetime.now(datetime.UTC)
    chain = Chain(
        title=title,
        chain_length=chain_length,
        prompt_source="manual",
        prompt_text="起手题",
        visibility="public",
        room_code="V" + title[-3:].upper().ljust(5, "X")[:5],
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
    # 额外成员
    for m in extra_members or []:
        db.add(ChainMember(chain_id=chain.id, user_id=m.id))

    # 全部节点 submitted
    nodes: list[Node] = []
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
        nodes.append(node)
    await db.flush()
    return chain, nodes


def _token(user: User) -> str:
    """生成 JWT token（get_current_user 查 DB 验证用户存在，用户须已建）。"""
    return create_access_token(user.id, user.nickname)


def _auth_headers(user: User) -> dict[str, str]:
    """构造 Authorization header。"""
    return {"Authorization": f"Bearer {_token(user)}"}


def _vote_body(nodes: list[Node]) -> dict:
    """构造三维度投票 body（target 取链内节点）。"""
    draw_nodes = [n for n in nodes if n.type == "draw"]
    describe_nodes = [n for n in nodes if n.type == "describe"]
    return {
        "votes": [
            {"dimension": "most_drift", "target_node_id": nodes[0].id},
            {"dimension": "best_draw", "target_node_id": draw_nodes[1].id if len(draw_nodes) > 1 else draw_nodes[0].id},
            {"dimension": "best_describe", "target_node_id": describe_nodes[0].id},
        ]
    }


# ---- POST /api/chains/{id}/votes ----


@pytest.mark.asyncio
async def test_submit_votes_success(
    override_db: None, test_db: AsyncSession
) -> None:
    """成员投三维度 → 200 + results 含三维度 vote_count=1。"""
    creator = await _create_user(test_db, "voteuser1", "投票A")
    chain, nodes = await _create_completed_chain(test_db, creator)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/chains/{chain.id}/votes",
            json=_vote_body(nodes),
            headers=_auth_headers(creator),
        )
    assert resp.status_code == 200
    results = resp.json()["data"]["results"]
    dims = {r["dimension"] for r in results}
    assert dims == {"most_drift", "best_draw", "best_describe"}
    for r in results:
        assert r["vote_count"] == 1


@pytest.mark.asyncio
async def test_submit_votes_chain_not_completed(
    override_db: None, test_db: AsyncSession
) -> None:
    """链未完成 → 403「链未完成或无权投票」。"""
    creator = await _create_user(test_db, "voteuser2", "投票B")
    chain, nodes = await _create_completed_chain(test_db, creator)
    # 改为未完成
    chain.status = "in_progress"
    await test_db.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/chains/{chain.id}/votes",
            json=_vote_body(nodes),
            headers=_auth_headers(creator),
        )
    assert resp.status_code == 403
    assert resp.json()["code"] == 403
    assert "链未完成或无权投票" in resp.json()["message"]


@pytest.mark.asyncio
async def test_submit_votes_non_member(
    override_db: None, test_db: AsyncSession
) -> None:
    """非成员 → 403。"""
    creator = await _create_user(test_db, "voteuser3", "投票C")
    chain, nodes = await _create_completed_chain(test_db, creator)
    # 另一个非成员用户
    outsider = await _create_user(test_db, "voteoutsider1", "外人甲")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/chains/{chain.id}/votes",
            json=_vote_body(nodes),
            headers=_auth_headers(outsider),
        )
    assert resp.status_code == 403
    assert "链未完成或无权投票" in resp.json()["message"]


@pytest.mark.asyncio
async def test_submit_votes_already_voted(
    override_db: None, test_db: AsyncSession
) -> None:
    """重复投票 → 403（已投过）。"""
    creator = await _create_user(test_db, "voteuser4", "投票D")
    chain, nodes = await _create_completed_chain(test_db, creator)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 第一次投票
        resp1 = await client.post(
            f"/api/chains/{chain.id}/votes",
            json=_vote_body(nodes),
            headers=_auth_headers(creator),
        )
        assert resp1.status_code == 200
        # 第二次投票（重复）
        resp2 = await client.post(
            f"/api/chains/{chain.id}/votes",
            json=_vote_body(nodes),
            headers=_auth_headers(creator),
        )
    assert resp2.status_code == 403
    assert "链未完成或无权投票" in resp2.json()["message"]


@pytest.mark.asyncio
async def test_submit_votes_missing_dimension(
    override_db: None, test_db: AsyncSession
) -> None:
    """三维度不齐 → 400。"""
    creator = await _create_user(test_db, "voteuser5", "投票E")
    chain, nodes = await _create_completed_chain(test_db, creator)

    # 只投两维度
    body = {"votes": _vote_body(nodes)["votes"][:2]}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/chains/{chain.id}/votes",
            json=body,
            headers=_auth_headers(creator),
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_submit_votes_invalid_target(
    override_db: None, test_db: AsyncSession
) -> None:
    """target_node 不属于链 → 400。"""
    creator = await _create_user(test_db, "voteuser6", "投票F")
    chain, nodes = await _create_completed_chain(test_db, creator)

    # 构造不属于该链的 target（用一个不存在的 node_id）
    body = _vote_body(nodes)
    body["votes"][0]["target_node_id"] = "nonexistent-node-id"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/chains/{chain.id}/votes",
            json=body,
            headers=_auth_headers(creator),
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_submit_votes_no_token(
    override_db: None, test_db: AsyncSession
) -> None:
    """无 token → 401。"""
    creator = await _create_user(test_db, "voteuser7", "投票G")
    chain, nodes = await _create_completed_chain(test_db, creator)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/chains/{chain.id}/votes",
            json=_vote_body(nodes),
        )
    assert resp.status_code == 401


# ---- GET /api/chains/{id}/votes/result ----


@pytest.mark.asyncio
async def test_get_vote_result_success(
    override_db: None, test_db: AsyncSession
) -> None:
    """投票后查结果 → 200 含 target_author + vote_count。"""
    creator = await _create_user(test_db, "voteuser8", "投票H")
    chain, nodes = await _create_completed_chain(test_db, creator)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 先投票
        await client.post(
            f"/api/chains/{chain.id}/votes",
            json=_vote_body(nodes),
            headers=_auth_headers(creator),
        )
        # 查结果
        resp = await client.get(
            f"/api/chains/{chain.id}/votes/result",
            headers=_auth_headers(creator),
        )
    assert resp.status_code == 200
    results = resp.json()["data"]["results"]
    assert len(results) == 3
    for r in results:
        assert "target_author" in r
        assert r["target_author"]["nickname"]  # 非空
        assert r["vote_count"] == 1


@pytest.mark.asyncio
async def test_get_vote_result_chain_not_found(
    override_db: None, test_db: AsyncSession
) -> None:
    """链不存在 → 404。"""
    creator = await _create_user(test_db, "voteuser9", "投票I")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/chains/nonexistent-id/votes/result",
            headers=_auth_headers(creator),
        )
    assert resp.status_code == 404
    assert "链不存在" in resp.json()["message"]


@pytest.mark.asyncio
async def test_get_vote_result_empty(
    override_db: None, test_db: AsyncSession
) -> None:
    """无投票 → 200 空结果。"""
    creator = await _create_user(test_db, "voteuser10", "投票J")
    chain, _ = await _create_completed_chain(test_db, creator)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/chains/{chain.id}/votes/result",
            headers=_auth_headers(creator),
        )
    assert resp.status_code == 200
    assert resp.json()["data"]["results"] == []
