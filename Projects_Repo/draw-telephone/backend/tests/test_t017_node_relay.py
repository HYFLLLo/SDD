"""T-017 节点接力功能闭环 测试。

测试 GET /api/nodes/{id}/previous（防剧透）+ POST /api/nodes/{id}/submit（推进链），
使用独立测试库。{id} 是链 ID。
"""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.core.security import create_access_token, hash_password
from src.db.models import Base, Chain, Node, User
from src.db.session import get_db
from src.main import app
from src.repositories.chain import ChainRepository

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


async def _create_user(
    db: AsyncSession, username: str, nickname: str
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


async def _create_chain(db: AsyncSession, creator: User) -> Chain:
    """创建链（chain_length=4）+ 创建者成员 + seq=0 draw 节点（创建者承接）。"""
    repo = ChainRepository(db)
    chain = await repo.create_chain_with_first_node(
        creator_id=creator.id,
        title="接力测试链",
        chain_length=4,
        visibility="invite",
        prompt_source="manual",
        prompt_text="戴帽子的猫",
        creator_nickname=creator.nickname,
    )
    return chain


async def _add_member(db: AsyncSession, chain: Chain, user: User) -> None:
    """添加链成员，显式设 joined_at 晚于创建者（保证轮转顺序稳定）。

    创建者 ChainMember 由 create_chain_with_first_node 用 server_default=func.now() 创建，
    本函数显式设 joined_at 为 now+1秒，确保 sort(joined_at) 时创建者在前、后续成员在后。
    测试环境同事务快速执行，server_default 时间戳可能相同导致排序不稳定。
    用 naive datetime 与 SQLite server_default 一致，避免 naive vs aware 比较问题。
    """
    import datetime

    from src.db.models import ChainMember

    member = ChainMember(
        chain_id=chain.id,
        user_id=user.id,
        joined_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=1),
    )
    db.add(member)
    await db.flush()


async def _create_node(
    db: AsyncSession,
    chain: Chain,
    seq: int,
    author: User,
    node_type: str = "describe",
    status: str = "pending",
    content_url: str | None = None,
    content_text: str | None = None,
) -> Node:
    """直接创建一个节点（用于构造非 seq=0 的接力场景）。

    注意：seq=0 节点由 _create_chain 创建，本函数只用于 seq>=1。
    可传入 content_url/content_text 构造已提交节点。
    """
    content_type = None
    if content_url:
        content_type = "image"
    elif content_text:
        content_type = "text"
    node = Node(
        chain_id=chain.id,
        seq=seq,
        type=node_type,
        author_id=author.id,
        content_type=content_type,
        content_url=content_url,
        content_text=content_text,
        is_ai=False,
        author_label=author.nickname,
        status=status,
    )
    db.add(node)
    # 同步推进链 current_seq
    chain.current_seq = seq
    await db.flush()
    await db.refresh(node)
    return node


async def _mark_seq0_submitted(
    db: AsyncSession, chain: Chain, content_url: str = "http://test/drawing.png"
) -> Node:
    """将 _create_chain 创建的 seq=0 节点标记为已提交（画节点）。

    _create_chain 已创建 seq=0 draw pending 节点，本函数更新其内容+状态，
    避免重复创建导致 MultipleResultsFound。
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Node).where(Node.chain_id == chain.id, Node.seq == 0)
    )
    node0 = result.scalar_one()
    node0.content_type = "image"
    node0.content_url = content_url
    node0.status = "submitted"
    await db.flush()
    await db.refresh(node0)
    return node0


# ---------- GET /api/nodes/{id}/previous ----------


@pytest.mark.asyncio
async def test_previous_seq0_returns_prompt(override_db: None, test_db: AsyncSession) -> None:
    """seq=0 当前责任人看 previous → 返回起手题（content_type=text）。"""
    creator = await _create_user(test_db, "creator_p0", "画师甲")
    chain = await _create_chain(test_db, creator)
    token = create_access_token(creator.id, creator.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/nodes/{chain.id}/previous",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["seq"] == -1  # 起手题虚拟节点
    assert data["content_type"] == "text"
    assert data["content_text"] == "戴帽子的猫"
    assert data["type"] == "describe"


@pytest.mark.asyncio
async def test_previous_non_responsible_403(override_db: None, test_db: AsyncSession) -> None:
    """非当前责任人看 previous → 403「当前未轮到你」。"""
    creator = await _create_user(test_db, "creator_p1", "画师甲")
    other = await _create_user(test_db, "other_p1", "画师乙")
    chain = await _create_chain(test_db, creator)
    await _add_member(test_db, chain, other)
    token = create_access_token(other.id, other.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/nodes/{chain.id}/previous",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403
    assert "未轮到你" in resp.json()["message"]


@pytest.mark.asyncio
async def test_previous_non_member_403(override_db: None, test_db: AsyncSession) -> None:
    """非链成员看 previous → 403。"""
    creator = await _create_user(test_db, "creator_p2", "画师甲")
    chain = await _create_chain(test_db, creator)
    outsider = await _create_user(test_db, "outsider_p2", "外人")
    token = create_access_token(outsider.id, outsider.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/nodes/{chain.id}/previous",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403
    assert resp.json()["code"] == 403


@pytest.mark.asyncio
async def test_previous_chain_not_found(override_db: None, test_db: AsyncSession) -> None:
    """链不存在 → 404。"""
    user = await _create_user(test_db, "user_p3", "用户")
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/nodes/nonexistent-id/previous",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_previous_no_token_401(override_db: None) -> None:
    """无 token → 401。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/nodes/some-id/previous")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_previous_returns_submitted_node(override_db: None, test_db: AsyncSession) -> None:
    """seq=1 当前责任人看 previous → 返回 seq=0 已提交的画节点（content_type=image）。"""
    creator = await _create_user(test_db, "creator_p4", "画师甲")
    joiner = await _create_user(test_db, "joiner_p4", "画师乙")
    chain = await _create_chain(test_db, creator)
    await _add_member(test_db, chain, joiner)
    # seq=0 由 _create_chain 创建，标记为已提交；再创建 seq=1 describe 给 joiner
    await _mark_seq0_submitted(test_db, chain)
    await _create_node(test_db, chain, seq=1, author=joiner, node_type="describe")
    token = create_access_token(joiner.id, joiner.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/nodes/{chain.id}/previous",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["seq"] == 0
    assert data["type"] == "draw"
    assert data["content_type"] == "image"
    assert data["content_url"] == "http://test/drawing.png"


# ---------- POST /api/nodes/{id}/submit ----------


@pytest.mark.asyncio
async def test_submit_draw_node_success(override_db: None, test_db: AsyncSession) -> None:
    """画节点提交 image → 200 + 推进链 current_seq=1 + 创建 seq=1 describe 节点。"""
    creator = await _create_user(test_db, "creator_s0", "画师甲")
    chain = await _create_chain(test_db, creator)
    token = create_access_token(creator.id, creator.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/nodes/{chain.id}/submit",
            json={"content_type": "image", "content_url": "http://test/drawing.png"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["seq"] == 0
    assert data["status"] == "submitted"
    assert data["next_seq"] == 1
    assert data["chain_status"] == "in_progress"

    # 验证 DB：链 current_seq=1，seq=1 describe 节点已创建
    await test_db.refresh(chain)
    assert chain.current_seq == 1
    from sqlalchemy import select

    next_nodes = (
        await test_db.execute(select(Node).where(Node.chain_id == chain.id, Node.seq == 1))
    ).scalars().all()
    assert len(next_nodes) == 1
    assert next_nodes[0].type == "describe"
    assert next_nodes[0].status == "pending"


@pytest.mark.asyncio
async def test_submit_describe_node_success(override_db: None, test_db: AsyncSession) -> None:
    """述节点提交 text → 200 + 推进链 current_seq=2 + 创建 seq=2 draw 节点。"""
    creator = await _create_user(test_db, "creator_s1", "画师甲")
    joiner = await _create_user(test_db, "joiner_s1", "画师乙")
    chain = await _create_chain(test_db, creator)
    await _add_member(test_db, chain, joiner)
    # seq=0 由 _create_chain 创建，标记已提交；创建 seq=1 describe 给 joiner
    await _mark_seq0_submitted(test_db, chain)
    await _create_node(test_db, chain, seq=1, author=joiner, node_type="describe")
    token = create_access_token(joiner.id, joiner.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/nodes/{chain.id}/submit",
            json={"content_type": "text", "content_text": "一只戴礼帽的猫"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["seq"] == 1
    assert data["status"] == "submitted"
    assert data["next_seq"] == 2
    assert data["chain_status"] == "in_progress"

    # 验证 DB：seq=2 draw 节点已创建
    await test_db.refresh(chain)
    assert chain.current_seq == 2
    from sqlalchemy import select

    next_nodes = (
        await test_db.execute(select(Node).where(Node.chain_id == chain.id, Node.seq == 2))
    ).scalars().all()
    assert len(next_nodes) == 1
    assert next_nodes[0].type == "draw"


@pytest.mark.asyncio
async def test_submit_non_responsible_403(override_db: None, test_db: AsyncSession) -> None:
    """非当前责任人提交 → 403「当前未轮到你」。"""
    creator = await _create_user(test_db, "creator_s2", "画师甲")
    other = await _create_user(test_db, "other_s2", "画师乙")
    chain = await _create_chain(test_db, creator)
    await _add_member(test_db, chain, other)
    token = create_access_token(other.id, other.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/nodes/{chain.id}/submit",
            json={"content_type": "image", "content_url": "http://test/x.png"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403
    assert "未轮到你" in resp.json()["message"]


@pytest.mark.asyncio
async def test_submit_wrong_content_type_400(override_db: None, test_db: AsyncSession) -> None:
    """画节点提交 text（类型不匹配）→ 400。"""
    creator = await _create_user(test_db, "creator_s3", "画师甲")
    chain = await _create_chain(test_db, creator)
    token = create_access_token(creator.id, creator.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/nodes/{chain.id}/submit",
            json={"content_type": "text", "content_text": "错类型"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400
    assert "图片" in resp.json()["message"]


@pytest.mark.asyncio
async def test_submit_empty_text_400(override_db: None, test_db: AsyncSession) -> None:
    """述节点提交空文字 → 400。"""
    creator = await _create_user(test_db, "creator_s4", "画师甲")
    joiner = await _create_user(test_db, "joiner_s4", "画师乙")
    chain = await _create_chain(test_db, creator)
    await _add_member(test_db, chain, joiner)
    await _mark_seq0_submitted(test_db, chain)
    await _create_node(test_db, chain, seq=1, author=joiner, node_type="describe")
    token = create_access_token(joiner.id, joiner.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # content_text 为空字符串
        resp = await client.post(
            f"/api/nodes/{chain.id}/submit",
            json={"content_type": "text", "content_text": "   "},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_submit_chain_not_found(override_db: None, test_db: AsyncSession) -> None:
    """链不存在 → 404。"""
    user = await _create_user(test_db, "user_s5", "用户")
    token = create_access_token(user.id, user.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/nodes/nonexistent-id/submit",
            json={"content_type": "image", "content_url": "http://test/x.png"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_last_node_completes_chain(override_db: None, test_db: AsyncSession) -> None:
    """提交最后一节点 → 链 completed，不创建下一节点。"""
    creator = await _create_user(test_db, "creator_s6", "画师甲")
    chain = await _create_chain(test_db, creator)
    # chain_length=4：seq=0(draw) 由 _create_chain 创建，标记已提交；
    # seq=1(describe)/seq=2(draw) 已提交；seq=3(describe) pending 给 creator
    await _mark_seq0_submitted(test_db, chain)
    await _create_node(
        test_db, chain, seq=1, author=creator, node_type="describe",
        status="submitted", content_text="描述一",
    )
    await _create_node(
        test_db, chain, seq=2, author=creator, node_type="draw",
        status="submitted", content_url="http://test/d2.png",
    )
    await _create_node(test_db, chain, seq=3, author=creator, node_type="describe")
    token = create_access_token(creator.id, creator.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/nodes/{chain.id}/submit",
            json={"content_type": "text", "content_text": "终幕描述"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["chain_status"] == "completed"
    assert data["next_seq"] == 4  # chain_length

    # 验证 DB：链 completed，无 seq=4 节点
    await test_db.refresh(chain)
    assert chain.status == "completed"
    assert chain.completed_at is not None
    from sqlalchemy import select

    extra = (
        await test_db.execute(select(Node).where(Node.chain_id == chain.id, Node.seq == 4))
    ).scalars().all()
    assert len(extra) == 0


# ---------- 防剧透：提交后下一节点解锁 ----------


@pytest.mark.asyncio
async def test_relay_flow_previous_after_submit(override_db: None, test_db: AsyncSession) -> None:
    """完整接力流程：创建者提交画 → joiner 看 previous（返回画）→ joiner 提交述。"""
    creator = await _create_user(test_db, "creator_flow", "画师甲")
    joiner = await _create_user(test_db, "joiner_flow", "画师乙")
    chain = await _create_chain(test_db, creator)
    await _add_member(test_db, chain, joiner)
    token_creator = create_access_token(creator.id, creator.username)
    token_joiner = create_access_token(joiner.id, joiner.username)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. 创建者看 previous（seq=0 → 起手题 text）
        resp = await client.get(
            f"/api/nodes/{chain.id}/previous",
            headers={"Authorization": f"Bearer {token_creator}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["content_text"] == "戴帽子的猫"

        # 2. joiner 此时看 previous → 403（未轮到）
        resp = await client.get(
            f"/api/nodes/{chain.id}/previous",
            headers={"Authorization": f"Bearer {token_joiner}"},
        )
        assert resp.status_code == 403

        # 3. 创建者提交画
        resp = await client.post(
            f"/api/nodes/{chain.id}/submit",
            json={"content_type": "image", "content_url": "http://test/drawing.png"},
            headers={"Authorization": f"Bearer {token_creator}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["next_seq"] == 1

        # 4. joiner 现在看 previous → 200（返回 seq=0 的画）
        resp = await client.get(
            f"/api/nodes/{chain.id}/previous",
            headers={"Authorization": f"Bearer {token_joiner}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["seq"] == 0
        assert data["content_type"] == "image"
        assert data["content_url"] == "http://test/drawing.png"

        # 5. joiner 提交述
        resp = await client.post(
            f"/api/nodes/{chain.id}/submit",
            json={"content_type": "text", "content_text": "戴礼帽的猫"},
            headers={"Authorization": f"Bearer {token_joiner}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["next_seq"] == 2

        # 6. seq=2 又轮到创建者（2 成员轮转：seq%2=0→creator），创建者能看 previous
        #    返回 seq=1 的述节点（content_type=text, content_text="戴礼帽的猫"）
        resp = await client.get(
            f"/api/nodes/{chain.id}/previous",
            headers={"Authorization": f"Bearer {token_creator}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["seq"] == 1
        assert data["content_type"] == "text"
        assert data["content_text"] == "戴礼帽的猫"

        # 7. joiner 此时看 previous → 403（seq=2 轮到创建者，不是 joiner）
        resp = await client.get(
            f"/api/nodes/{chain.id}/previous",
            headers={"Authorization": f"Bearer {token_joiner}"},
        )
        assert resp.status_code == 403
