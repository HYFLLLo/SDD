"""投票路由。

POST /api/chains/{id}/votes        —— 提交投票（链完成 + 房间成员，三维度各一票）
GET  /api/chains/{id}/votes/result —— 投票结果统计

路径参数 {id} 是链 ID。需登录鉴权（房间成员才能投票/看结果）。
错误响应格式遵循 api-contracts.md：{"code":N,"message":"...","data":null}。
"""

from fastapi import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter, success_response
from src.api.deps import get_current_user
from src.db.models import User
from src.db.session import get_db
from src.models.vote import (
    VoteRequest,
    VoteResultDetailResponse,
    VoteResultResponse,
)
from src.repositories.chain import ChainRepository
from src.repositories.vote import VoteRepository
from src.services.vote import VoteService

router = APIRouter(prefix="/api/chains", tags=["votes"])


def _error(code: int, message: str) -> JSONResponse:
    """构造 api-contracts 错误响应体。"""
    return JSONResponse(
        status_code=code,
        content={"code": code, "message": message, "data": None},
    )


@router.post("/{chain_id}/votes")
async def submit_votes(
    chain_id: str,
    body: VoteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """POST /api/chains/{id}/votes —— 提交投票（链完成 + 房间成员）。

    三维度各一票（most_drift/best_draw/best_describe）。
    链未完成/非成员/已投过 → 403「链未完成或无权投票」。
    """
    service = VoteService(VoteRepository(db), ChainRepository(db))
    try:
        data = await service.submit_votes(
            chain_id, current_user, [v.model_dump() for v in body.votes]
        )
    except LookupError:
        return _error(404, "链不存在")
    except PermissionError:
        return _error(403, "链未完成或无权投票")
    except ValueError as e:
        return _error(400, str(e))

    resp_data = VoteResultResponse.model_validate(data)
    resp = success_response(resp_data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))


@router.get("/{chain_id}/votes/result")
async def get_vote_result(
    chain_id: str,
    current_user: User = Depends(get_current_user),  # noqa: ARG001 需登录鉴权
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """GET /api/chains/{id}/votes/result —— 投票结果统计（链完成后）。

    返回三维度统计（含 target_author + vote_count）。链不存在 → 404。
    """
    service = VoteService(VoteRepository(db), ChainRepository(db))
    try:
        data = await service.get_result(chain_id)
    except LookupError:
        return _error(404, "链不存在")

    resp_data = VoteResultDetailResponse.model_validate(data)
    resp = success_response(resp_data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))
