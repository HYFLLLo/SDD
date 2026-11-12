"""AI 起手题生成 + AI 辅助创作的 Pydantic 模型，与 api-contracts.md 对齐。"""

from pydantic import BaseModel, Field


class AiPromptRequest(BaseModel):
    """POST /api/ai/prompt 请求体。"""

    count: int = Field(default=1, ge=1, le=5, description="生成题词数量 1-5")


class AiPromptResponse(BaseModel):
    """POST /api/ai/prompt 响应 data。"""

    prompts: list[str]


class AiAssistRequest(BaseModel):
    """POST /api/ai/assist 请求体。用户在接力页主动请求 AI 辅助创作。"""

    chain_id: str = Field(description="链 ID（接力页上下文）")


class AiAssistResponse(BaseModel):
    """POST /api/ai/assist 响应 data。

    draw 节点返回 content_type=image + content_url（AI 生成图片 URL）；
    describe 节点返回 content_type=text + content_text（AI 生成描述文字）。
    """

    content_type: str
    content_url: str | None = None
    content_text: str | None = None
