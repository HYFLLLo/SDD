"""节点 Pydantic 模型（接力提交）。

对应 api-contracts.md POST /api/nodes/{id}/submit 请求体与响应。
"""

from pydantic import BaseModel, Field


class SubmitNodeImageRequest(BaseModel):
    """画节点提交请求体。"""

    content_type: str = Field(..., pattern="^image$")
    content_url: str = Field(..., min_length=1, max_length=512)


class SubmitNodeTextRequest(BaseModel):
    """描述节点提交请求体。"""

    content_type: str = Field(..., pattern="^text$")
    content_text: str = Field(..., min_length=1, max_length=30)


class SubmitNodeResponse(BaseModel):
    """提交节点响应 data。"""

    node_id: str
    seq: int
    status: str
    next_seq: int
    chain_status: str


class NodePreviousResponse(BaseModel):
    """上一节点内容响应 data（防剧透，只返回上一节点）。"""

    node_id: str
    seq: int
    type: str
    content_type: str
    content_url: str | None = None
    content_text: str | None = None
