"""
链数据访问层。

只依赖 ORM + AsyncSession。房间码唯一冲突（IntegrityError）转为 ValueError。
创建链时同时创建 ChainMember（创建者）+ Node(seq=0, type=draw, pending)。
"""

import datetime
import random
import string

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chain, ChainMember, Node


def generate_room_code(length: int = 6) -> str:
    """生成 6 位大写字母+数字房间码。"""
    chars = string.ascii_uppercase + string.digits
    # 排除易混淆字符 0/O、1/I/L，降低人工输入错误率
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "").replace("L", "")
    return "".join(random.choices(chars, k=length))  # noqa: S311


class ChainRepository:
    """链表数据访问。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, chain_id: str) -> Chain | None:
        result = await self.db.execute(select(Chain).where(Chain.id == chain_id))
        return result.scalar_one_or_none()

    async def get_by_room_code(self, room_code: str) -> Chain | None:
        result = await self.db.execute(select(Chain).where(Chain.room_code == room_code))
        return result.scalar_one_or_none()

    async def count_members(self, chain_id: str) -> int:
        """统计链成员数。"""
        result = await self.db.execute(
            select(func.count()).select_from(ChainMember).where(ChainMember.chain_id == chain_id)
        )
        return int(result.scalar_one())

    async def get_members(self, chain_id: str) -> list[ChainMember]:
        """获取链全部成员。"""
        result = await self.db.execute(
            select(ChainMember).where(ChainMember.chain_id == chain_id)
        )
        return list(result.scalars().all())

    async def get_member(self, chain_id: str, user_id: str) -> ChainMember | None:
        """查询某用户是否已是链成员。"""
        result = await self.db.execute(
            select(ChainMember).where(
                ChainMember.chain_id == chain_id, ChainMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_nodes(self, chain_id: str) -> list[Node]:
        """获取链已创建的节点（按 seq 排序）。"""
        result = await self.db.execute(
            select(Node).where(Node.chain_id == chain_id).order_by(Node.seq)
        )
        return list(result.scalars().all())

    async def get_current_node(self, chain_id: str, current_seq: int) -> Node | None:
        """获取当前 seq 的节点（可能未创建）。"""
        result = await self.db.execute(
            select(Node).where(Node.chain_id == chain_id, Node.seq == current_seq)
        )
        return result.scalar_one_or_none()

    async def list_in_progress(self) -> list[Chain]:
        """查所有 in_progress 链（AI 补位定时扫描用）。"""
        result = await self.db.execute(
            select(Chain).where(Chain.status == "in_progress")
        )
        return list(result.scalars().all())

    async def mark_expired(self, chain: Chain) -> None:
        """标记链 expired（status=expired）。7 天未完成时调用。"""
        chain.status = "expired"
        await self.db.flush()

    async def add_member(self, chain_id: str, user_id: str) -> ChainMember:
        """加入链成员（调用方负责前置校验：未满/未过期/未重复）。"""
        member = ChainMember(chain_id=chain_id, user_id=user_id)
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(member)
        return member

    async def create_chain_with_first_node(
        self,
        creator_id: str,
        title: str | None,
        chain_length: int,
        visibility: str,
        prompt_source: str,
        prompt_text: str,
        creator_nickname: str,
    ) -> Chain:
        """
        创建链 + 创建者成员 + 第一节点（seq=0, type=draw, pending）。

        房间码冲突时重试生成（最多 10 次）。
        """
        now = datetime.datetime.now(datetime.UTC)
        expires_at = now + datetime.timedelta(days=7)

        # 房间码唯一，冲突重试
        chain = None
        for _ in range(10):
            room_code = generate_room_code()
            chain = Chain(
                title=title,
                chain_length=chain_length,
                prompt_source=prompt_source,
                prompt_text=prompt_text,
                visibility=visibility,
                room_code=room_code,
                status="in_progress",
                creator_id=creator_id,
                current_seq=0,
                expires_at=expires_at,
            )
            self.db.add(chain)
            try:
                await self.db.flush()
                break  # 成功
            except IntegrityError:
                await self.db.rollback()
                chain = None
                continue

        if chain is None:
            raise ValueError("房间码生成失败，请重试")

        # 创建者加入链成员
        member = ChainMember(chain_id=chain.id, user_id=creator_id)
        self.db.add(member)

        # 第一节点：seq=0, type=draw, pending，创建者承接
        node = Node(
            chain_id=chain.id,
            seq=0,
            type="draw",
            author_id=creator_id,
            content_type=None,
            content_url=None,
            content_text=None,
            is_ai=False,
            author_label=creator_nickname,
            status="pending",
        )
        self.db.add(node)

        await self.db.flush()
        await self.db.refresh(chain)
        return chain
