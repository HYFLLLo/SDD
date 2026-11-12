"""
认证路由（注册/登录）。

POST /api/auth/register —— 注册，用户名已存在 → 400
POST /api/auth/login    —— 登录，凭据错误 → 401

错误响应格式遵循 api-contracts.md：{"code":N,"message":"...","data":null}。
FastAPI 默认 HTTPException 返回 {"detail":"..."}，与契约不符，
故错误分支用 JSONResponse 显式构造契约体（成功分支用 pycore success_response）。
"""

from fastapi import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter, success_response
from src.db.session import get_db
from src.models.user import AuthData, LoginRequest, RegisterRequest, UserPublic
from src.repositories.user import UserRepository
from src.services.user import UserService

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _error(code: int, message: str) -> JSONResponse:
    """构造 api-contracts 错误响应体。"""
    return JSONResponse(
        status_code=code,
        content={"code": code, "message": message, "data": None},
    )


@router.post("/register")
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """POST /api/auth/register —— 注册账号。"""
    service = UserService(UserRepository(db))
    try:
        user, token = await service.register(body.username, body.password, body.nickname)
    except ValueError:
        # 用户名已存在 → 400
        return _error(400, "用户名已存在")

    data = AuthData(access_token=token, user=UserPublic.model_validate(user))
    resp = success_response(data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """POST /api/auth/login —— 登录。"""
    service = UserService(UserRepository(db))
    try:
        user, token = await service.login(body.username, body.password)
    except PermissionError:
        # 凭据错误 → 401
        return _error(401, "用户名或密码错误")

    data = AuthData(access_token=token, user=UserPublic.model_validate(user))
    resp = success_response(data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))
