"""节点路由（接力）。

GET  /api/nodes/{id}/previous —— 获取上一节点内容（防剧透，需当前责任人）
POST /api/nodes/{id}/submit   —— 提交节点（需当前责任人，推进链）

路径参数 {id} 是链 ID（前端 RelayPage 从路由 /chain/:id/relay 取链 ID 调用）。
后端按链 ID 查 current_seq 对应的当前节点，校验当前责任人后返回上一节点 / 接受提交。

错误响应格式遵循 api-contracts.md：{"code":N,"message":"...","data":null}。
"""

from fastapi import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pycore.api import APIRouter, success_response
from src.api.deps import get_current_user
from src.api.ws import ws_manager
from src.db.models import User
from src.db.session import get_db
from src.models.node import (
    NodePreviousResponse,
    SubmitNodeImageRequest,
    SubmitNodeResponse,
    SubmitNodeTextRequest,
)
from src.repositories.chain import ChainRepository
from src.repositories.node import NodeRepository
from src.repositories.notification import NotificationRepository
from src.services.node import NodeService

router = APIRouter(prefix="/api/nodes", tags=["nodes"])


def _error(code: int, message: str) -> JSONResponse:
    """构造 api-contracts 错误响应体。"""
    return JSONResponse(
        status_code=code,
        content={"code": code, "message": message, "data": None},
    )


@router.get("/{chain_id}/previous")
async def get_previous(
    chain_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """GET /api/nodes/{id}/previous —— 获取上一节点内容（防剧透，需当前责任人）。

    {id} 是链 ID。非当前责任人 → 403「当前未轮到你」。
    """
    service = NodeService(NodeRepository(db), ChainRepository(db))
    try:
        data = await service.get_previous(chain_id, current_user)
    except LookupError:
        return _error(404, "链不存在")
    except PermissionError as e:
        return _error(403, str(e))

    resp_data = NodePreviousResponse.model_validate(data)
    resp = success_response(resp_data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))


@router.post("/{chain_id}/submit")
async def submit_node(
    chain_id: str,
    body: SubmitNodeImageRequest | SubmitNodeTextRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """POST /api/nodes/{id}/submit —— 提交节点（需当前责任人，推进链）。

    {id} 是链 ID。画节点提交 image（content_url），描述节点提交 text（content_text）。
    """
    service = NodeService(NodeRepository(db), ChainRepository(db))
    content_url: str | None = None
    content_text: str | None = None
    if isinstance(body, SubmitNodeImageRequest):
        content_url = body.content_url
    else:
        content_text = body.content_text
    try:
        data = await service.submit_node(
            chain_id, current_user, body.content_type, content_url, content_text
        )
    except LookupError:
        return _error(404, "链不存在")
    except PermissionError as e:
        return _error(403, str(e))
    except ValueError as e:
        return _error(400, str(e))

    # 路由层触发 notify 广播（service 层不感知 WS，分层约束）
    # 链完成 → chain_done；否则 → node_submitted + your_turn（下一位接力）
    chain_status = data["chain_status"]
    next_seq = data["next_seq"]
    if chain_status == "completed":
        await ws_manager.broadcast_notify(chain_id, "chain_done", next_seq)
    else:
        await ws_manager.broadcast_notify(chain_id, "node_submitted", next_seq)
        await ws_manager.broadcast_notify(chain_id, "your_turn", next_seq)

    # 路由层生成 DB 通知（持久化，离线用户登录后能看到；与 WS notify 同位置同语义）
    # service 层不感知通知模块，路由层用 ChainRepository 查成员 + NotificationRepository 写通知
    chain_repo = ChainRepository(db)
    notif_repo = NotificationRepository(db)
    members = await chain_repo.get_members(chain_id)
    member_user_ids = [m.user_id for m in members]
    chain_obj = await chain_repo.get_by_id(chain_id)
    chain_title = chain_obj.title or "" if chain_obj else ""
    if chain_status == "completed":
        # 链完成 → 给所有成员发 chain_done 通知
        if member_user_ids:
            await notif_repo.create_many(
                [
                    {
                        "user_id": uid,
                        "type": "chain_done",
                        "chain_id": chain_id,
                        "chain_title": chain_title,
                    }
                    for uid in member_user_ids
                ]
            )
    else:
        # 未完成 → 给下一位责任人发 your_turn + 给所有成员发 node_submitted
        next_author_id = data.get("next_author_id")
        if next_author_id:
            await notif_repo.create(
                next_author_id, "your_turn", chain_id, chain_title
            )
        if member_user_ids:
            await notif_repo.create_many(
                [
                    {
                        "user_id": uid,
                        "type": "node_submitted",
                        "chain_id": chain_id,
                        "chain_title": chain_title,
                    }
                    for uid in member_user_ids
                ]
            )

    resp_data = SubmitNodeResponse.model_validate(data)
    resp = success_response(resp_data.model_dump(mode="json"))
    return JSONResponse(status_code=200, content=resp.model_dump(mode="json"))
