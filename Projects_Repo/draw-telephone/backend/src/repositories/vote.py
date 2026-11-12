"""投票数据访问层。

批量插入投票（唯一约束冲突=已投过），按维度分组统计票数，查节点作者。
Vote 表 uq_vote_chain_user_dim(chain_id,user_id,dimension) 唯一约束 = 每人每维度一票。
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Node, User, Vote


class VoteRepository:
    """投票数据访问。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_votes(
        self, chain_id: str, user_id: str, votes: list[dict]
    ) -> None:
        """批量插入投票。

        Raises:
            ValueError: 唯一约束冲突（该用户该维度已投过）。
        """
        for v in votes:
            vote = Vote(
                chain_id=chain_id,
                user_id=user_id,
                dimension=v["dimension"],
                target_node_id=v["target_node_id"],
            )
            self.db.add(vote)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("已投过票") from None

    async def has_voted(self, chain_id: str, user_id: str) -> bool:
        """该用户是否已对此链投过票（任一维度）。"""
        result = await self.db.execute(
            select(func.count())
            .select_from(Vote)
            .where(Vote.chain_id == chain_id, Vote.user_id == user_id)
            .limit(1)
        )
        return int(result.scalar_one()) > 0

    async def count_by_chain(self, chain_id: str) -> list[dict]:
        """按 dimension + target_node_id 分组统计票数。

        返回 [{dimension, target_node_id, vote_count}, ...]，按 dimension 排序。
        """
        result = await self.db.execute(
            select(
                Vote.dimension,
                Vote.target_node_id,
                func.count(Vote.id).label("vote_count"),
            )
            .where(Vote.chain_id == chain_id)
            .group_by(Vote.dimension, Vote.target_node_id)
            .order_by(Vote.dimension)
        )
        return [
            {
                "dimension": row.dimension,
                "target_node_id": row.target_node_id,
                "vote_count": row.vote_count,
            }
            for row in result.all()
        ]

    async def get_node(self, node_id: str) -> Node | None:
        """查节点（校验 target_node 属于链 + 取 author）。"""
        result = await self.db.execute(select(Node).where(Node.id == node_id))
        return result.scalar_one_or_none()

    async def get_nodes_by_ids(self, node_ids: list[str]) -> dict[str, Node]:
        """批量查节点（取 author_id + author_label），返回 id->Node 映射。"""
        if not node_ids:
            return {}
        result = await self.db.execute(select(Node).where(Node.id.in_(node_ids)))
        return {n.id: n for n in result.scalars().all()}

    async def get_node_authors(self, user_ids: list[str]) -> dict[str, User]:
        """批量查节点作者用户信息（返回 id->User 映射）。"""
        if not user_ids:
            return {}
        result = await self.db.execute(select(User).where(User.id.in_(user_ids)))
        return {u.id: u for u in result.scalars().all()}
