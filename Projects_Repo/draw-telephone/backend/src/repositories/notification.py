"""通知数据访问层。

创建通知（单条/批量）、查询用户通知列表（分页 + unread_only）、批量标记已读（防越权）。
"""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Notification


class NotificationRepository:
    """通知数据访问。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, user_id: str, type: str, chain_id: str, chain_title: str
    ) -> Notification:
        """创建单条通知。"""
        notif = Notification(
            user_id=user_id,
            type=type,
            chain_id=chain_id,
            chain_title=chain_title,
            read=False,
        )
        self.db.add(notif)
        await self.db.flush()
        await self.db.refresh(notif)
        return notif

    async def create_many(self, items: list[dict]) -> None:
        """批量创建通知。

        items=[{user_id, type, chain_id, chain_title}, ...]
        给多个成员发同一事件时用。逐条 add + flush。
        """
        for item in items:
            notif = Notification(
                user_id=item["user_id"],
                type=item["type"],
                chain_id=item["chain_id"],
                chain_title=item["chain_title"],
                read=False,
            )
            self.db.add(notif)
        await self.db.flush()

    async def list_by_user(
        self,
        user_id: str,
        page: int,
        page_size: int,
        unread_only: bool,
    ) -> tuple[list[Notification], int]:
        """查询用户通知列表（分页 + unread_only 过滤，按 created_at 倒序）。

        返回 (notifications, total)。
        """
        base = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            base = base.where(Notification.read.is_(False))

        # 总数
        count_stmt = select(func.count()).select_from(base.subquery())
        total = int((await self.db.execute(count_stmt)).scalar_one())

        # 分页 + 倒序
        offset = (page - 1) * page_size
        stmt = base.order_by(Notification.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        notifications = list(result.scalars().all())
        return notifications, total

    async def mark_read(self, user_id: str, notification_ids: list[str]) -> int:
        """批量标记已读（只标记属于该用户的，防越权）。

        返回受影响行数。
        """
        if not notification_ids:
            return 0
        stmt = (
            update(Notification)
            .where(
                Notification.id.in_(notification_ids),
                Notification.user_id == user_id,
                Notification.read.is_(False),
            )
            .values(read=True)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        # SQLAlchemy 2.0 async update 返回 CursorResult，运行时有 rowcount，
        # 但 mypy stub 标注为 Result（无 rowcount），故加 ignore（非 unused）。
        return int(result.rowcount)  # type: ignore[attr-defined]
