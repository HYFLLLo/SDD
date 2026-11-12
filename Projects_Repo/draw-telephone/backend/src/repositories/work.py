"""作品数据访问层（只读）。

广场列表查 completed 链（分页 + 排序），作品详情查链 + 全已提交节点。
thumb_url 取链中第一个 draw 节点的 content_url。
like_count 查 Vote 表 count（T-021 投票功能，当前无 Vote 返回 0）。
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chain, ChainMember, Node, User, Vote


class WorkRepository:
    """作品只读数据访问。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_completed_chains(
        self, page: int, page_size: int, sort: str
    ) -> tuple[list[Chain], int]:
        """查询已完成链列表（分页 + 排序）。

        sort: latest（创建时间倒序）/ most_liked（点赞数倒序，V1.2）/ most_drift（V1.1）
        MVP 只支持 latest，其余降级为 latest。
        """
        # 基础查询：completed 链
        base = select(Chain).where(Chain.status == "completed")

        # 排序
        if sort == "most_liked":
            # 按点赞数倒序：子查询统计每链 Vote 数
            like_sub = (
                select(Vote.chain_id, func.count(Vote.id).label("cnt"))
                .group_by(Vote.chain_id)
                .subquery()
            )
            stmt = (
                base.outerjoin(like_sub, Chain.id == like_sub.c.chain_id)
                .order_by(func.coalesce(like_sub.c.cnt, 0).desc(), Chain.created_at.desc())
            )
        else:
            # latest 或不支持的模式降级为最新
            stmt = base.order_by(Chain.created_at.desc())

        # 分页
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        chains = list(result.scalars().all())

        # 总数
        count_stmt = select(func.count()).select_from(Chain).where(
            Chain.status == "completed"
        )
        total = int((await self.db.execute(count_stmt)).scalar_one())
        return chains, total

    async def get_chain(self, chain_id: str) -> Chain | None:
        """查询单个链。"""
        result = await self.db.execute(select(Chain).where(Chain.id == chain_id))
        return result.scalar_one_or_none()

    async def get_creator(self, user_id: str) -> User | None:
        """查询链创建者用户信息。"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_nodes(self, chain_id: str) -> list[Node]:
        """获取链全部已提交节点（按 seq 排序）。"""
        result = await self.db.execute(
            select(Node)
            .where(Node.chain_id == chain_id, Node.status == "submitted")
            .order_by(Node.seq)
        )
        return list(result.scalars().all())

    async def get_node_authors(self, user_ids: list[str]) -> dict[str, User]:
        """批量查询节点作者用户信息（返回 id->User 映射）。"""
        if not user_ids:
            return {}
        result = await self.db.execute(select(User).where(User.id.in_(user_ids)))
        return {u.id: u for u in result.scalars().all()}

    async def count_members(self, chain_id: str) -> int:
        """统计链成员数。"""
        result = await self.db.execute(
            select(func.count())
            .select_from(ChainMember)
            .where(ChainMember.chain_id == chain_id)
        )
        return int(result.scalar_one())

    async def count_likes(self, chain_id: str) -> int:
        """统计链点赞数（Vote 表，T-021 投票功能）。"""
        result = await self.db.execute(
            select(func.count()).select_from(Vote).where(Vote.chain_id == chain_id)
        )
        return int(result.scalar_one())

    async def get_thumb_url(self, chain_id: str) -> str:
        """获取链缩略图 URL（第一个 draw 节点的 content_url）。

        无 draw 节点或无 content_url 时返回空字符串。
        """
        result = await self.db.execute(
            select(Node.content_url)
            .where(
                Node.chain_id == chain_id,
                Node.type == "draw",
                Node.content_url.is_not(None),
            )
            .order_by(Node.seq)
            .limit(1)
        )
        url = result.scalar_one_or_none()
        return url or ""
