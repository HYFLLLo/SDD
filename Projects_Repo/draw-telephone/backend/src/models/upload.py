"""上传 Pydantic 模型。

对应 api-contracts.md POST /api/upload/image 响应。
"""

from pydantic import BaseModel


class UploadImageResponse(BaseModel):
    """上传图片响应 data。"""

    url: str
    size: int
