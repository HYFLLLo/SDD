"""
画意接龙后端入口。

基于 pycore.api.APIServer 创建 FastAPI 应用，禁止重写 config/server/logger。
启动：cd backend && PYTHONPATH=.. python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8099
"""

from fastapi import HTTPException, Query, Request, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocketDisconnect

from pycore.api import APIConfig, APIServer
from pycore.core import Logger, LoggerConfig, LogLevel, get_logger
from src.api.routes.ai import router as ai_router
from src.api.routes.auth import router as auth_router
from src.api.routes.chains import router as chains_router
from src.api.routes.nodes import router as nodes_router
from src.api.routes.notifications import router as notifications_router
from src.api.routes.upload import router as upload_router
from src.api.routes.users import router as users_router
from src.api.routes.votes import router as votes_router
from src.api.routes.works import router as works_router
from src.api.ws import ws_manager
from src.core.config import settings
from src.core.security import decode_token
from src.db.session import async_session_maker, close_db, init_db
from src.repositories.chain import ChainRepository
from src.scheduler import init_scheduler, shutdown_scheduler

# 配置日志（使用 pycore，禁止自己重写 logger）
Logger.configure(
    LoggerConfig(
        level=LogLevel.DEBUG if settings.debug else LogLevel.INFO,
        app_name="draw-telephone",
        json_format=False,
    )
)
logger = get_logger()
logger.info(
    "Initializing draw-telephone backend",
    host=settings.host,
    port=settings.port,
)

# 创建 APIServer（使用 pycore，禁止自己重写 FastAPI 实例）
server = APIServer(
    APIConfig(
        title="画意接龙 API",
        version="0.1.0",
        host=settings.host,
        port=settings.port,
        debug=settings.debug,
        cors_origins=settings.cors_origins,
    )
)

# /health 端点由 APIServer 自动注册
# 数据库生命周期：启动时建表，关闭时释放连接
server.on_startup(init_db)
server.on_shutdown(close_db)
# AI 补位定时任务：每小时扫描超时节点 + 7 天过期链
server.on_startup(init_scheduler)
server.on_shutdown(shutdown_scheduler)
# 路由在各功能闭环任务中逐步 include_router
server.include_router(auth_router)
server.include_router(chains_router)
server.include_router(ai_router)
server.include_router(nodes_router)
server.include_router(notifications_router)
server.include_router(upload_router)
server.include_router(users_router)
server.include_router(votes_router)
server.include_router(works_router)

app = server.app

# 静态文件服务：上传的画作图片通过 /uploads/* 访问（T-018）
# Vite proxy /uploads → 后端，前端 img src="/uploads/xxx.png" 可加载
app.mount(settings.upload_url_prefix, StaticFiles(directory=str(settings.upload_path)), name="uploads")


@app.websocket("/ws/room/{chain_id}")
async def room_websocket(
    websocket: WebSocket,
    chain_id: str,
    token: str = Query(default=""),
) -> None:
    """WS /ws/room/{chain_id} —— 链大厅实时围观 + 通知推送（T-019）。

    鉴权用 query param ?token=JWT（浏览器 WS 不能设自定义 header）。
    无效/缺失 token → 发 error 事件 + close(4401)。
    stroke 推送需校验是当前节点责任人（只有作画者能推笔迹）。
    """
    # JWT 鉴权（query param，复用 decode_token）
    payload = decode_token(token) if token else None
    if payload is None or not payload.get("sub"):
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "未认证"})
        await websocket.close(code=4401)
        return
    user_id = str(payload["sub"])

    await ws_manager.connect(chain_id, websocket)
    try:
        await websocket.send_json({"type": "subscribed", "chain_id": chain_id})
        while True:
            msg = await websocket.receive_json()
            msg_type = msg.get("type")
            if msg_type == "subscribe":
                # 客户端订阅确认（连接时已自动加入房间，此处忽略重复订阅）
                continue
            if msg_type == "stroke":
                # stroke 推送：校验是当前节点责任人（独立 session，WS 循环不能持有请求级 session）
                async with async_session_maker() as db:
                    chain = await ChainRepository(db).get_by_id(chain_id)
                    if chain is None or chain.status == "completed":
                        continue
                    node = await ChainRepository(db).get_current_node(
                        chain_id, chain.current_seq
                    )
                    if node is None or node.author_id != user_id:
                        # 非当前责任人，忽略推送
                        continue
                # 广播给同房间所有在线连接（围观者收笔迹）
                await ws_manager.broadcast(chain_id, msg)
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(chain_id, websocket)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """统一 HTTPException 响应格式为 api-contracts：{"code":N,"message":"...","data":null}。

    FastAPI 默认 HTTPException 返回 {"detail":"..."}，与 api-contracts.md 不符。
    此处统一转换（不重写 pycore，仅注册 app 级异常处理器）。
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail), "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic 请求体校验失败 → 400（api-contracts 参数错误码）。

    FastAPI 默认返回 422 + {"detail":[...]}，api-contracts 用 400 表示参数错误。
    """
    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "message": "参数错误",
            "data": None,
        },
    )
