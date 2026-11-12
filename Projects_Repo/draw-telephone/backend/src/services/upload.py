"""上传业务服务层。

依赖 settings（上传目录/URL 前缀），不依赖 FastAPI/HTTP。
- upload_image：校验 PNG，UUID 文件名存储，返回 {url, size}
"""

import uuid

from pycore.core import get_logger
from src.core.config import settings

logger = get_logger()

# PNG 文件头魔数
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PNG_EXT = ".png"


class UploadService:
    """图片上传业务。"""

    def __init__(self) -> None:
        self.upload_dir = settings.upload_path
        self.url_prefix = settings.upload_url_prefix

    async def upload_image(self, filename: str, content_type: str, data: bytes) -> dict:
        """上传图片，校验 PNG，UUID 文件名存储。

        Raises:
            ValueError: 非 PNG 文件（→400）。
        """
        # PNG 校验：以文件头魔数为准（不信任客户端 content_type，空文件/伪装文件均拒绝）
        if not data.startswith(PNG_MAGIC):
            raise ValueError("文件格式不支持")

        # UUID 文件名，保留 .png 扩展名（原始 filename 可能含中文/特殊字符）
        stored_name = f"{uuid.uuid4().hex}{PNG_EXT}"
        file_path = self.upload_dir / stored_name

        # 写入文件
        file_path.write_bytes(data)

        url = f"{self.url_prefix}/{stored_name}"
        size = len(data)
        logger.info(
            "Image uploaded",
            filename=filename,
            content_type=content_type,
            stored_name=stored_name,
            size=size,
        )
        return {"url": url, "size": size}
