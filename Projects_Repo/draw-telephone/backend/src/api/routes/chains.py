"""
链路由。

POST /api/chains —— 创建链（需登录），生成房间码 + 第一节点
GET  /api/chains/{room_code} —— 按房间码查询（加入前校验，需登录）
POST /api/chains/{id}/join —— 加入链（需登录）
GET  /api/chains/{id} —— 链大厅详情（需链成员权限）

错误响应格式遵循 api-contracts.md：{"code":N,"message":"...","data":null}。
"""

from fastapi import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter, success_response
from src.api.deps import get_current_user
from src.db.models import Chain, User
from src.db.session import get_db
from src.models.chain import CreateChainRequest
from src.repositories.chain import ChainRepository
from src.services.chain import ChainService

router = APIRouter(prefix="/api/chains", tags=["chains"])


def _error(code: int, message: str) -> JSONResponse:
    """构造 api-contracts 错误响应体。"""
    return JSONResponse(
        status_code=code,
        content={"code": code, "message": message, "data": None},
    )


def _chain_to_read(chain: Chain) -> dict:
    """Chain ORM → ChainRead dict（datetime 转 ISO 字符串）。"""
    return {
        "id": chain.id,
        "title": chain.title,
        "chain_length": chain.chain_length,
        "visibility": chain.visibility,
        "room_code": chain.room_code,
        "prompt_source": chain.prompt_source,
        "prompt_text": chain.prompt_text,
        "status": chain.status,
        "creator_id": chain.creator_id,
        "created_at": chain.created_at.isoformat() if chain.created_at else "",
        "expires_at": chain.expires_at.isoformat() if chain.expires_at else "",
    }


@router.post("")
async def create_chain(
    body: CreateChainRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """POST /api/chains —— 创建链（需登录）。"""
    service = ChainService(ChainRepository(db))
    try:
        chain = await service.create_chain(
            creator=current_user,
            title=body.title,
            chain_length=body.chain_length,
            visibility=body.visibility,
            prompt_source=body.prompt_source,
            prompt_text=body.prompt_text,
        )
    except ValueError as e:
        return _error(400, str(e))

    data = _chain_to_read(chain)
    resp = success_response(data)
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))


@router.get("/{room_code}")
async def lookup_chain(
    room_code: str,
    current_user: User = Depends(get_current_user),  # noqa: ARG001 需登录鉴权
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """GET /api/chains/{room_code} —— 按房间码查询链（加入前校验，需登录）。"""
    service = ChainService(ChainRepository(db))
    try:
        data = await service.lookup_chain(room_code)
    except ValueError:
        return _error(404, "房间码无效或链已过期")

    resp = success_response(data)
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))


@router.post("/{chain_id}/join")
async def join_chain(
    chain_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """POST /api/chains/{id}/join —— 加入链（需登录）。"""
    service = ChainService(ChainRepository(db))
    try:
        data = await service.join_chain(chain_id, current_user)
    except LookupError:
        return _error(404, "链不存在")
    except ValueError as e:
        return _error(403, str(e))

    resp = success_response(data)
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))


@router.get("/{chain_id}/detail")
async def get_chain_detail(
    chain_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """GET /api/chains/{id} —— 链大厅详情（需链成员权限）。

    路径用 /{chain_id}/detail 避免与 /{room_code} 冲突（两者都是 /{param}）。
    前端 getChainDetail 调 /chains/{id}/detail。
    """
    service = ChainService(ChainRepository(db))
    try:
        data = await service.get_chain_detail(chain_id, current_user)
    except LookupError:
        return _error(404, "链不存在")
    except PermissionError:
        return _error(403, "无权访问该链")

    resp = success_response(data)
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))
