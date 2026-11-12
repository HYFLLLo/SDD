"""节点数据访问层。

只依赖 ORM + AsyncSession。按链 ID 查当前节点、上一节点、更新节点提交状态、推进链。
"""

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chain, Node, User


class NodeRepository:
    """节点表数据访问。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_chain(self, chain_id: str) -> Chain | None:
        """按 ID 查链。"""
        result = await self.db.execute(select(Chain).where(Chain.id == chain_id))
        return result.scalar_one_or_none()

    async def get_user(self, user_id: str) -> User | None:
        """按 ID 查用户（用于下一位责任人 nickname）。"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_current_node(self, chain: Chain) -> Node | None:
        """获取链当前 seq 的节点（可能未创建）。"""
        result = await self.db.execute(
            select(Node).where(
                Node.chain_id == chain.id, Node.seq == chain.current_seq
            )
        )
        return result.scalar_one_or_none()

    async def get_previous_node(self, chain: Chain) -> Node | None:
        """获取链上一节点（current_seq - 1）。seq=0 时无上一节点。"""
        if chain.current_seq <= 0:
            return None
        result = await self.db.execute(
            select(Node).where(
                Node.chain_id == chain.id, Node.seq == chain.current_seq - 1
            )
        )
        return result.scalar_one_or_none()

    async def update_node_submit(
        self,
        node: Node,
        content_type: str,
        content_url: str | None,
        content_text: str | None,
    ) -> Node:
        """更新节点提交内容 + 状态 submitted。"""
        node.content_type = content_type
        node.content_url = content_url
        node.content_text = content_text
        node.status = "submitted"
        await self.db.flush()
        await self.db.refresh(node)
        return node

    async def update_node_ai_fill(
        self,
        node: Node,
        content_type: str,
        content_url: str | None,
        content_text: str | None,
    ) -> Node:
        """AI 补位更新节点：content + is_ai=True + status=ai_filled + submitted_at=now。

        与人工 submit 区别：is_ai=True、status=ai_filled（非 submitted）。
        """
        node.content_type = content_type
        node.content_url = content_url
        node.content_text = content_text
        node.is_ai = True
        node.status = "ai_filled"
        node.submitted_at = datetime.datetime.now(datetime.UTC)
        await self.db.flush()
        await self.db.refresh(node)
        return node

    async def advance_chain(self, chain: Chain) -> tuple[Chain, bool]:
        """推进链 current_seq +1，返回 (chain, is_completed)。

        若推进后 current_seq >= chain_length，链标记 completed。
        """
        chain.current_seq += 1
        if chain.current_seq >= chain.chain_length:
            chain.status = "completed"
            import datetime

            chain.completed_at = datetime.datetime.now(datetime.UTC)
        await self.db.flush()
        await self.db.refresh(chain)
        return chain, chain.status == "completed"

    async def create_next_node(
        self, chain: Chain, author_id: str | None, author_label: str
    ) -> Node | None:
        """为下一 seq 创建 pending 节点（接力提交后，下一位承接）。

        若链已完成（current_seq >= chain_length）则不创建，返回 None。
        节点 type 按 seq 推导：偶数 draw，奇数 describe。
        author_id 可为 None（成员不足时待接，T-024 AI 补位）。
        """
        if chain.current_seq >= chain.chain_length:
            return None
        node_type = "draw" if chain.current_seq % 2 == 0 else "describe"
        node = Node(
            chain_id=chain.id,
            seq=chain.current_seq,
            type=node_type,
            author_id=author_id,
            content_type=None,
            content_url=None,
            content_text=None,
            is_ai=False,
            author_label=author_label,
            status="pending",
        )
        self.db.add(node)
        await self.db.flush()
        await self.db.refresh(node)
        return node
