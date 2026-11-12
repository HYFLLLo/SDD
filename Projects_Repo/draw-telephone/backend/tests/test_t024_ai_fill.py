"""T-024 AI 补位定时任务功能闭环 测试。

测试 AiFillService：扫描 24h 超时 pending 节点 → AI 补位（draw 调文生图 /
describe 调 VLM 看图）→ 推进链 + 建下一节点 + 通知；7 天过期链标记 expired。

AiService.generate_image/describe_image 用 mock 替换（不调真实 MaaS）。
"""

import datetime
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.core.security import hash_password
from src.db.models import Base, Chain, ChainMember, Node, User
from src.services.ai_fill import AiFillService

# 独立测试库（内存 SQLite）
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


async def _create_user(db: AsyncSession, nickname: str) -> User:
    """创建用户。"""
    user = User(
        username=f"ai_{nickname}",
        password_hash=hash_password("pass1234"),
        nickname=nickname,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _create_chain_with_pending_node(
    db: AsyncSession,
    creator: User,
    *,
    chain_length: int = 4,
    node_created_at: datetime.datetime | None = None,
    extra_members: list[User] | None = None,
    current_seq: int = 0,
    node_type: str = "draw",
    prev_node_text: str | None = None,
    prev_node_url: str | None = None,
) -> tuple[Chain, Node]:
    """创建 in_progress 链 + pending 当前节点（可设 created_at 控制超时）。

    current_seq=0 时无上一节点；current_seq>=1 时可造上一节点带 content。
    """
    now = datetime.datetime.now(datetime.UTC)
    created_at = node_created_at if node_created_at else now
    chain = Chain(
        title="AI补位测试链",
        chain_length=chain_length,
        prompt_source="manual",
        prompt_text="戴帽子的猫",
        visibility="public",
        room_code="AI" + creator.id[:4].upper(),
        status="in_progress",
        creator_id=creator.id,
        current_seq=current_seq,
        created_at=now,
        expires_at=now + datetime.timedelta(days=7),
    )
    db.add(chain)
    await db.flush()

    # 创建者成员 + 额外成员
    db.add(ChainMember(chain_id=chain.id, user_id=creator.id))
    for i, m in enumerate(extra_members or []):
        db.add(
            ChainMember(
                chain_id=chain.id,
                user_id=m.id,
                joined_at=now + datetime.timedelta(seconds=i + 1),
            )
        )

    # 上一节点（current_seq >= 1 时造）
    if current_seq >= 1:
        prev = Node(
            chain_id=chain.id,
            seq=current_seq - 1,
            type="draw" if (current_seq - 1) % 2 == 0 else "describe",
            author_id=creator.id,
            content_type="image" if prev_node_url else "text",
            content_url=prev_node_url,
            content_text=prev_node_text,
            is_ai=False,
            author_label=creator.nickname,
            status="submitted",
            submitted_at=now,
        )
        db.add(prev)

    # 当前 pending 节点
    node = Node(
        chain_id=chain.id,
        seq=current_seq,
        type=node_type,
        author_id=creator.id,
        content_type=None,
        content_url=None,
        content_text=None,
        is_ai=False,
        author_label=creator.nickname,
        status="pending",
        created_at=created_at,
    )
    db.add(node)
    await db.flush()
    await db.refresh(chain)
    return chain, node


# ---- 扫描逻辑 ----


@pytest.mark.asyncio
async def test_scan_finds_timeout_node(test_db: AsyncSession) -> None:
    """24h 未提交 pending 节点被扫描补位。"""
    creator = await _create_user(test_db, "甲")
    # 节点 created_at = 25h 前（超 24h）
    old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=25)
    await _create_chain_with_pending_node(test_db, creator, node_created_at=old)
    await test_db.commit()

    with patch.object(AiFillService, "_fill_node", new=AsyncMock()) as mock_fill:
        service = AiFillService(test_db)
        result = await service.scan_and_fill()
    # _fill_node 被 mock（不抛异常），filled 计数 +1，说明扫描到了超时节点
    assert mock_fill.called
    assert result["filled"] == 1
    await test_db.rollback()


@pytest.mark.asyncio
async def test_scan_skips_recent_node(test_db: AsyncSession) -> None:
    """未超 24h 的 pending 节点不补位。"""
    creator = await _create_user(test_db, "乙")
    # 节点 created_at = 1h 前（未超 24h）
    recent = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
    await _create_chain_with_pending_node(test_db, creator, node_created_at=recent)
    await test_db.commit()

    with patch.object(AiFillService, "_fill_node", new=AsyncMock()) as mock_fill:
        service = AiFillService(test_db)
        await service.scan_and_fill()
    assert not mock_fill.called  # 未超时，不调补位
    await test_db.rollback()


@pytest.mark.asyncio
async def test_scan_skips_submitted_node(test_db: AsyncSession) -> None:
    """submitted 节点不补位（即使超时）。"""
    creator = await _create_user(test_db, "丙")
    old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=25)
    chain, node = await _create_chain_with_pending_node(
        test_db, creator, node_created_at=old
    )
    # 把节点改成 submitted
    node.status = "submitted"
    await test_db.flush()
    await test_db.commit()

    with patch.object(AiFillService, "_fill_node", new=AsyncMock()) as mock_fill:
        service = AiFillService(test_db)
        await service.scan_and_fill()
    assert not mock_fill.called
    await test_db.rollback()


# ---- 补位内容生成 ----


@pytest.mark.asyncio
async def test_fill_draw_node_calls_image_api(test_db: AsyncSession) -> None:
    """draw 节点补位调 generate_image + is_ai=true。"""
    creator = await _create_user(test_db, "丁")
    chain, node = await _create_chain_with_pending_node(
        test_db, creator, current_seq=0, node_type="draw"
    )
    await test_db.commit()

    service = AiFillService(test_db)
    with patch.object(
        service.ai_service, "generate_image", new=AsyncMock(return_value="/uploads/ai.png")
    ) as mock_img:
        await service._fill_node(chain, node)
    assert mock_img.called
    # 验证 prompt 是起手题（seq=0 无上一节点）
    call_args = mock_img.call_args
    assert call_args[0][0] == "戴帽子的猫"
    await test_db.refresh(node)
    assert node.is_ai is True
    assert node.status == "ai_filled"
    assert node.content_url == "/uploads/ai.png"
    await test_db.rollback()


@pytest.mark.asyncio
async def test_fill_describe_node_calls_vlm_api(test_db: AsyncSession) -> None:
    """describe 节点补位调 describe_image（输入上一节点 content_url）。"""
    creator = await _create_user(test_db, "戊")
    chain, node = await _create_chain_with_pending_node(
        test_db,
        creator,
        current_seq=1,
        node_type="describe",
        prev_node_url="/uploads/prev.png",
    )
    await test_db.commit()

    service = AiFillService(test_db)
    with patch.object(
        service.ai_service, "describe_image", new=AsyncMock(return_value="一只猫")
    ) as mock_vlm:
        await service._fill_node(chain, node)
    assert mock_vlm.called
    call_args = mock_vlm.call_args
    assert call_args[0][0] == "/uploads/prev.png"
    await test_db.refresh(node)
    assert node.is_ai is True
    assert node.content_text == "一只猫"
    await test_db.rollback()


@pytest.mark.asyncio
async def test_fill_advances_chain(test_db: AsyncSession) -> None:
    """补位后推进链 current_seq+1。"""
    creator = await _create_user(test_db, "己")
    chain, node = await _create_chain_with_pending_node(
        test_db, creator, current_seq=0, node_type="draw"
    )
    await test_db.commit()

    service = AiFillService(test_db)
    with patch.object(
        service.ai_service, "generate_image", new=AsyncMock(return_value="/uploads/ai.png")
    ):
        await service._fill_node(chain, node)
    await test_db.refresh(chain)
    assert chain.current_seq == 1  # 推进 +1
    await test_db.rollback()


@pytest.mark.asyncio
async def test_fill_creates_next_node(test_db: AsyncSession) -> None:
    """补位后创建下一节点（seq=1, describe）。"""
    creator = await _create_user(test_db, "庚")
    chain, node = await _create_chain_with_pending_node(
        test_db, creator, current_seq=0, node_type="draw"
    )
    await test_db.commit()

    service = AiFillService(test_db)
    with patch.object(
        service.ai_service, "generate_image", new=AsyncMock(return_value="/uploads/ai.png")
    ):
        await service._fill_node(chain, node)
    await test_db.flush()
    # 查 seq=1 节点应存在
    from sqlalchemy import select

    result = await test_db.execute(
        select(Node).where(Node.chain_id == chain.id, Node.seq == 1)
    )
    next_node = result.scalar_one_or_none()
    assert next_node is not None
    assert next_node.type == "describe"  # seq=1 奇数 describe
    await test_db.rollback()


@pytest.mark.asyncio
async def test_fill_notifies_next_author(test_db: AsyncSession) -> None:
    """补位后下一位责任人收 your_turn 通知。"""
    creator = await _create_user(test_db, "辛")
    member2 = await _create_user(test_db, "壬")
    chain, node = await _create_chain_with_pending_node(
        test_db, creator, current_seq=0, node_type="draw", extra_members=[member2]
    )
    await test_db.commit()

    service = AiFillService(test_db)
    with patch.object(
        service.ai_service, "generate_image", new=AsyncMock(return_value="/uploads/ai.png")
    ):
        await service._fill_node(chain, node)
    await test_db.flush()
    # member2 是下一位（轮转 idx=1%2=1），应收 your_turn
    from sqlalchemy import select
    from src.db.models import Notification

    result = await test_db.execute(
        select(Notification).where(
            Notification.user_id == member2.id, Notification.type == "your_turn"
        )
    )
    assert result.scalar_one_or_none() is not None
    await test_db.rollback()


# ---- 7 天过期 ----


@pytest.mark.asyncio
async def test_expire_chain_after_7_days(test_db: AsyncSession) -> None:
    """7 天未完成链标记 expired。"""
    creator = await _create_user(test_db, "癸")
    # 链 created_at = 8 天前
    old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=8)
    chain, node = await _create_chain_with_pending_node(
        test_db, creator, node_created_at=old
    )
    chain.created_at = old
    await test_db.flush()
    await test_db.commit()

    service = AiFillService(test_db)
    with patch.object(AiFillService, "_fill_node", new=AsyncMock()):
        await service.scan_and_fill()
    await test_db.refresh(chain)
    assert chain.status == "expired"
    await test_db.rollback()


@pytest.mark.asyncio
async def test_expire_notifies_members(test_db: AsyncSession) -> None:
    """过期链成员收通知。"""
    creator = await _create_user(test_db, "元")
    member2 = await _create_user(test_db, "亨")
    old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=8)
    chain, node = await _create_chain_with_pending_node(
        test_db, creator, node_created_at=old, extra_members=[member2]
    )
    chain.created_at = old
    await test_db.flush()
    await test_db.commit()

    service = AiFillService(test_db)
    with patch.object(AiFillService, "_fill_node", new=AsyncMock()):
        await service.scan_and_fill()
    await test_db.flush()
    from sqlalchemy import select
    from src.db.models import Notification

    # 两个成员都应收 chain_done 通知
    for uid in [creator.id, member2.id]:
        result = await test_db.execute(
            select(Notification).where(
                Notification.user_id == uid, Notification.type == "chain_done"
            )
        )
        assert result.scalar_one_or_none() is not None
    await test_db.rollback()
