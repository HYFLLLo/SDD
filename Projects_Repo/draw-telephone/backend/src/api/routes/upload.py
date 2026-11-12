"""上传路由。

POST /api/upload/image —— 上传画作图片（multipart/form-data，PNG，需登录）

错误响应格式遵循 api-contracts.md：{"code":N,"message":"...","data":null}。
"""

from fastapi import Depends, UploadFile
from fastapi.responses import JSONResponse

from pycore.api import APIRouter, success_response
from src.api.deps import get_current_user
from src.db.models import User
from src.models.upload import UploadImageResponse
from src.services.upload import UploadService

router = APIRouter(prefix="/api/upload", tags=["upload"])


def _error(code: int, message: str) -> JSONResponse:
    """构造 api-contracts 错误响应体。"""
    return JSONResponse(
        status_code=code,
        content={"code": code, "message": message, "data": None},
    )


@router.post("/image")
async def upload_image(
    file: UploadFile,
    current_user: User = Depends(get_current_user),  # noqa: ARG001 需登录鉴权
) -> JSONResponse:
    """POST /api/upload/image —— 上传画作图片（PNG，需登录）。

    multipart/form-data 字段 file。非 PNG → 400「文件格式不支持」。
    """
    data = await file.read()
    service = UploadService()
    try:
        result = await service.upload_image(
            filename=file.filename or "upload.png",
            content_type=file.content_type or "",
            data=data,
        )
    except ValueError as e:
        return _error(400, str(e))

    resp_data = UploadImageResponse.model_validate(result)
    resp = success_response(resp_data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))
