"""通知业务服务层。

依赖 NotificationRepository，不依赖 FastAPI/HTTP。
- list_notifications：用户通知列表（分页 + unread_only）
- mark_read：批量标记已读（防越权，只标记属于该用户的）
"""

from pycore.core import get_logger
from src.repositories.notification import NotificationRepository

logger = get_logger()


class NotificationService:
    """通知业务。"""

    def __init__(self, repo: NotificationRepository) -> None:
        self.repo = repo

    async def list_notifications(
        self,
        user_id: str,
        page: int,
        page_size: int,
        unread_only: bool,
    ) -> dict:
        """通知列表（分页 + unread_only）。

        Returns:
            {"items": [...], "total": N, "page": page, "page_size": page_size}
        """
        notifications, total = await self.repo.list_by_user(
            user_id, page, page_size, unread_only
        )
        items: list[dict] = []
        for n in notifications:
            items.append(
                {
                    "id": n.id,
                    "type": n.type,
                    "chain_id": n.chain_id or "",
                    "chain_title": n.chain_title or "",
                    "read": n.read,
                    "created_at": n.created_at.isoformat()
                    if n.created_at
                    else "",
                }
            )
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def mark_read(self, user_id: str, notification_ids: list[str]) -> dict:
        """标记已读（只标记属于该用户的，防越权）。

        Returns:
            {"read_count": N}
        """
        read_count = await self.repo.mark_read(user_id, notification_ids)
        logger.info(
            "Notifications marked read",
            user_id=user_id,
            requested=len(notification_ids),
            read_count=read_count,
        )
        return {"read_count": read_count}
