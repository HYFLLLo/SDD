"""通知路由。

GET  /api/notifications       —— 通知列表（分页 + unread_only 过滤，需登录）
POST /api/notifications/read   —— 标记已读（批量，需登录）

错误响应格式遵循 api-contracts.md：{"code":N,"message":"...","data":null}。
"""

from fastapi import Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter, success_response
from src.api.deps import get_current_user
from src.db.models import User
from src.db.session import get_db
from src.models.notification import (
    NotificationListResponse,
    NotificationReadRequest,
    NotificationReadResponse,
)
from src.repositories.notification import NotificationRepository
from src.services.notification import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """GET /api/notifications —— 通知列表（需登录）。

    unread_only=true 时只返回未读。按 created_at 倒序。
    """
    service = NotificationService(NotificationRepository(db))
    data = await service.list_notifications(
        current_user.id, page, page_size, unread_only
    )
    resp_data = NotificationListResponse.model_validate(data)
    resp = success_response(resp_data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))


@router.post("/read")
async def read_notifications(
    body: NotificationReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """POST /api/notifications/read —— 标记已读（批量，需登录）。

    只标记属于当前用户的通知（防越权）。返回 read_count。
    """
    service = NotificationService(NotificationRepository(db))
    data = await service.mark_read(current_user.id, body.notification_ids)
    resp_data = NotificationReadResponse.model_validate(data)
    resp = success_response(resp_data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))
