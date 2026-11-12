"""作品路由（只读，游客可访问）。

GET /api/works          —— 广场作品列表（分页 + 排序）
GET /api/works/{id}     —— 作品详情（只读全链）

错误响应格式遵循 api-contracts.md：{"code":N,"message":"...","data":null}。
"""

from fastapi import Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter, success_response
from src.db.session import get_db
from src.models.work import WorkDetailResponse, WorkListResponse
from src.repositories.work import WorkRepository
from src.services.work import WorkService

router = APIRouter(prefix="/api/works", tags=["works"])


def _error(code: int, message: str) -> JSONResponse:
    """构造 api-contracts 错误响应体。"""
    return JSONResponse(
        status_code=code,
        content={"code": code, "message": message, "data": None},
    )


@router.get("")
async def list_works(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: str = Query(default="latest"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """GET /api/works —— 广场作品列表（游客可访问）。

    sort: latest（最新，默认）/ most_drift（V1.1）/ most_liked（V1.2）
    不支持的模式降级为 latest。
    """
    service = WorkService(WorkRepository(db))
    data = await service.list_works(page, page_size, sort)
    resp_data = WorkListResponse.model_validate(data)
    resp = success_response(resp_data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))


@router.get("/{work_id}")
async def get_work_detail(
    work_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """GET /api/works/{id} —— 作品详情（只读全链，游客可访问）。

    链不存在或未完成 → 404「作品不存在」。
    """
    service = WorkService(WorkRepository(db))
    try:
        data = await service.get_work_detail(work_id)
    except LookupError:
        return _error(404, "作品不存在")

    resp_data = WorkDetailResponse.model_validate(data)
    resp = success_response(resp_data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))
