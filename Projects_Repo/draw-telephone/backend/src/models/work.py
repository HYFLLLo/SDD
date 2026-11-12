"""作品（只读全链）Pydantic 模型。

GET /api/works 广场列表 + GET /api/works/{id} 作品详情（游客可访问）。
"""

from pydantic import BaseModel


class WorkAuthorResponse(BaseModel):
    """作品作者（id + nickname）。"""

    id: str
    nickname: str


class WorkListItemResponse(BaseModel):
    """GET /api/works 列表项。"""

    id: str
    title: str | None
    chain_length: int
    member_count: int
    like_count: int
    thumb_url: str
    created_at: str


class WorkNodeResponse(BaseModel):
    """作品节点（全链展示）。"""

    id: str
    seq: int
    type: str
    author: WorkAuthorResponse
    content_type: str
    content_url: str | None = None
    content_text: str | None = None
    is_ai: bool
    submitted_at: str


class WorkDetailResponse(BaseModel):
    """GET /api/works/{id} 作品详情。"""

    id: str
    title: str | None
    chain_length: int
    creator: WorkAuthorResponse
    prompt_source: str
    prompt_text: str
    status: str
    created_at: str
    completed_at: str | None = None
    nodes: list[WorkNodeResponse]


class WorkListResponse(BaseModel):
    """GET /api/works 分页响应。"""

    items: list[WorkListItemResponse]
    total: int
    page: int
    page_size: int
