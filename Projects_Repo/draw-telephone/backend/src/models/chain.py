"""
链相关 Pydantic 模型（API/领域模型，与 api-contracts.md 对齐）。

- CreateChainRequest：POST /api/chains 请求体
- ChainRead：创建成功响应 data（与前端 Chain 接口对齐）
"""

from pydantic import BaseModel, ConfigDict, Field


class CreateChainRequest(BaseModel):
    """POST /api/chains 请求体。"""

    title: str | None = Field(None, max_length=100)
    chain_length: int = Field(..., ge=4, le=10, description="链长 4-10")
    visibility: str = Field(..., pattern="^(invite|public)$")
    prompt_source: str = Field(..., pattern="^(manual|ai)$")
    prompt_text: str | None = Field(None, max_length=20, description="起手题词 ≤20 字")


class ChainRead(BaseModel):
    """创建链成功响应 data（与前端 Chain 接口对齐）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None
    chain_length: int
    visibility: str
    room_code: str
    prompt_source: str
    prompt_text: str
    status: str
    creator_id: str
    created_at: str
    expires_at: str
