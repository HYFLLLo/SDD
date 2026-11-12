"""投票 Pydantic 模型。

POST /api/chains/{id}/votes  —— 提交投票（三维度各一票）
GET  /api/chains/{id}/votes/result —— 投票结果统计

target_author 复用 work.WorkAuthorResponse（id+nickname）。
"""

from pydantic import BaseModel

from src.models.work import WorkAuthorResponse


class VoteItemRequest(BaseModel):
    """单条投票（维度 + 目标节点）。"""

    dimension: str  # most_drift / best_draw / best_describe
    target_node_id: str


class VoteRequest(BaseModel):
    """提交投票请求体。"""

    votes: list[VoteItemRequest]


class VoteCountItem(BaseModel):
    """POST 响应项：维度 + 目标节点 + 票数。"""

    dimension: str
    target_node_id: str
    vote_count: int


class VoteResultItem(BaseModel):
    """GET 响应项：维度 + 目标节点 + 作者 + 票数。"""

    dimension: str
    target_node_id: str
    target_author: WorkAuthorResponse
    vote_count: int


class VoteResultResponse(BaseModel):
    """POST /api/chains/{id}/votes 响应 data。"""

    results: list[VoteCountItem]


class VoteResultDetailResponse(BaseModel):
    """GET /api/chains/{id}/votes/result 响应 data。"""

    results: list[VoteResultItem]
