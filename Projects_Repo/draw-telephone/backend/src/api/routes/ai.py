"""AI 路由。

POST /api/ai/prompt  —— 生成起手题词（需登录，调 DeepSeek，Key 缺失返回 503）
POST /api/ai/assist  —— 接力页 AI 辅助创作（需登录 + 当前责任人，调 Qwen-Image/VLM）

错误响应格式遵循 api-contracts.md：{"code":N,"message":"...","data":null}。
"""

from fastapi import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter, success_response
from src.api.deps import get_current_user
from src.db.models import User
from src.db.session import get_db
from src.models.ai import AiAssistRequest, AiAssistResponse, AiPromptRequest, AiPromptResponse
from src.repositories.chain import ChainRepository
from src.repositories.node import NodeRepository
from src.services.ai import AiService
from src.services.node import NodeService

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _error(code: int, message: str) -> JSONResponse:
    """构造 api-contracts 错误响应体。"""
    return JSONResponse(
        status_code=code,
        content={"code": code, "message": message, "data": None},
    )


@router.post("/prompt")
async def generate_prompt(
    body: AiPromptRequest,
    current_user: User = Depends(get_current_user),  # noqa: ARG001 需登录鉴权
    db: AsyncSession = Depends(get_db),  # noqa: ARG001 预留未来记录 AI 调用日志
) -> JSONResponse:
    """POST /api/ai/prompt —— 生成起手题词（需登录）。

    Key 缺失返回 503（fallback 降级），Key 存在调 DeepSeek。
    """
    service = AiService()
    try:
        prompts = await service.generate_prompts(body.count)
    except RuntimeError as e:
        # Key 缺失 → 503
        return _error(503, str(e))

    data = AiPromptResponse(prompts=prompts)
    resp = success_response(data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))


@router.post("/assist")
async def ai_assist(
    body: AiAssistRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """POST /api/ai/assist —— 接力页 AI 辅助创作（需登录 + 当前责任人）。

    用户在接力页主动请求 AI 生成当前节点内容：
    - draw 节点：调 Qwen-Image 文生图，输入=上一节点 content_text（seq=0 用 chain.prompt_text）
    - describe 节点：调 Qwen3.6 VLM 看图，输入=上一节点 content_url

    返回 AI 生成的内容（content_url 或 content_text），前端填入画布/输入框，
    用户可微调后走正常提交流程。AI 辅助产出的节点提交后仍标注真人署名
    （用户主动请求 ≠ AI 补位，is_ai=false）。

    非当前责任人 → 403；链不存在 → 404；AI 服务不可用 → 503。
    """
    # 复用 NodeService.get_previous：校验责任人 + 取上一节点内容作为 AI 输入
    node_service = NodeService(NodeRepository(db), ChainRepository(db))
    try:
        prev = await node_service.get_previous(body.chain_id, current_user)
    except LookupError:
        return _error(404, "链不存在")
    except PermissionError as e:
        return _error(403, str(e))

    # 当前节点类型：get_previous 返回的 prev.seq 是上一节点 seq，当前 = prev.seq + 1
    # draw 节点 seq 偶数（0/2/...），describe seq 奇数（1/3/...）
    current_seq = prev["seq"] + 1
    is_draw = current_seq % 2 == 0

    ai_service = AiService()
    try:
        if is_draw:
            # 画节点：输入=上一节点文字（描述→画图）；seq=0 用起手题
            prompt = prev["content_text"] or ""
            content_url = await ai_service.generate_image(prompt)
            data = AiAssistResponse(content_type="image", content_url=content_url)
        else:
            # 述节点：输入=上一节点画作 URL（画→描述）
            image_url = prev["content_url"] or ""
            content_text = await ai_service.describe_image(image_url)
            data = AiAssistResponse(content_type="text", content_text=content_text)
    except RuntimeError as e:
        return _error(503, str(e))

    resp = success_response(data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))
