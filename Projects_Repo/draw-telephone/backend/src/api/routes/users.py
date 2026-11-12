"""用户路由（个人资料/我的作品）。

GET /api/users/me        —— 个人资料（昵称/参与链数/创建链数），需登录
GET /api/users/me/works  —— 我的作品列表（参与或创建的链，含 role/status/thumb_url），需登录

错误响应格式遵循 api-contracts.md：{"code":N,"message":"...","data":null}。
"""

from fastapi import Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter, success_response
from src.api.deps import get_current_user
from src.db.models import User
from src.db.session import get_db
from src.models.user import (
    MyWorkListResponse,
    UserProfileResponse,
)
from src.repositories.user import UserRepository
from src.repositories.work import WorkRepository
from src.services.user import UserService

router = APIRouter(prefix="/api/users", tags=["users"])


def _error(code: int, message: str) -> JSONResponse:
    """构造 api-contracts 错误响应体。"""
    return JSONResponse(
        status_code=code,
        content={"code": code, "message": message, "data": None},
    )


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """GET /api/users/me —— 个人资料（含参与链数/创建链数统计）。"""
    service = UserService(UserRepository(db), WorkRepository(db))
    try:
        data = await service.get_profile(current_user.id)
    except LookupError:
        return _error(404, "用户不存在")

    resp_data = UserProfileResponse.model_validate(data)
    resp = success_response(resp_data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))


@router.get("/me/works")
async def get_my_works(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """GET /api/users/me/works —— 我的作品列表（参与或创建的链）。"""
    service = UserService(UserRepository(db), WorkRepository(db))
    data = await service.list_my_works(current_user.id, page, page_size)

    resp_data = MyWorkListResponse.model_validate(data)
    resp = success_response(resp_data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))
