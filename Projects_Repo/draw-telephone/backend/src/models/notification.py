"""通知 Pydantic 模型。

GET /api/notifications       —— 通知列表（分页 + unread_only 过滤）
POST /api/notifications/read —— 标记已读（批量）
"""

from pydantic import BaseModel


class NotificationItemResponse(BaseModel):
    """通知列表项。"""

    id: str
    type: str  # your_turn / chain_done / node_submitted
    chain_id: str
    chain_title: str
    read: bool
    created_at: str


class NotificationListResponse(BaseModel):
    """GET /api/notifications 响应 data。"""

    items: list[NotificationItemResponse]
    total: int
    page: int
    page_size: int


class NotificationReadRequest(BaseModel):
    """POST /api/notifications/read 请求体。"""

    notification_ids: list[str]


class NotificationReadResponse(BaseModel):
    """POST /api/notifications/read 响应 data。"""

    read_count: int
