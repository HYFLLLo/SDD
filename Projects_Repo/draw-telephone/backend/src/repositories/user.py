"""
用户数据访问层。

只依赖 ORM（src.db.models）+ AsyncSession，不引入 HTTP/Service 语义。
IntegrityError 在本层捕获并转为 ValueError（数据冲突），供 Service 透传。
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chain, ChainMember, User


class UserRepository:
    """用户表数据访问。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def create(
        self,
        username: str,
        password_hash: str,
        nickname: str,
    ) -> User:
        """创建用户。用户名冲突（IntegrityError）转为 ValueError。"""
        user = User(
            username=username,
            password_hash=password_hash,
            nickname=nickname,
        )
        self.db.add(user)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise ValueError("用户名已存在") from e.orig
        await self.db.refresh(user)
        return user

    async def count_participated(self, user_id: str) -> int:
        """用户参与的链数（ChainMember.user_id 计数）。"""
        result = await self.db.execute(
            select(func.count())
            .select_from(ChainMember)
            .where(ChainMember.user_id == user_id)
        )
        return int(result.scalar_one())

    async def count_created(self, user_id: str) -> int:
        """用户创建的链数（Chain.creator_id 计数）。"""
        result = await self.db.execute(
            select(func.count()).select_from(Chain).where(Chain.creator_id == user_id)
        )
        return int(result.scalar_one())

    async def list_my_works(
        self, user_id: str, page: int, page_size: int
    ) -> tuple[list[Chain], int]:
        """用户参与或创建的链列表（分页，created_at 倒序）。

        范围：ChainMember.user_id==user_id（参与）OR Chain.creator_id==user_id（创建）。
        两者可能重叠（创建者也是成员），用 distinct 去重。
        含 in_progress + completed（区别于广场只查 completed）。

        返回 (chains, total)。
        """
        # 用户参与的链 id 子查询
        member_chain_ids = select(ChainMember.chain_id).where(
            ChainMember.user_id == user_id
        )
        # creator OR member → 用 or_ 合并，distinct 去重
        base = select(Chain).where(
            (Chain.creator_id == user_id) | (Chain.id.in_(member_chain_ids))
        ).distinct()
        # 总数
        count_stmt = select(func.count()).select_from(base.subquery())
        total = int((await self.db.execute(count_stmt)).scalar_one())

        # 分页 + 倒序
        offset = (page - 1) * page_size
        stmt = base.order_by(Chain.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        chains = list(result.scalars().all())
        return chains, total
