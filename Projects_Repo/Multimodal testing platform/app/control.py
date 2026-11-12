"""进程内控制接口：从页面优雅退出。

打包成无窗口程序后没有控制台可以关，用户需要一个明确的退出入口，
否则只能去任务管理器结束进程（还可能留下锁文件）。

只注册一条接口，且依赖 security.py 的 Host 白名单：只有本机页面能调到。
"""
import threading

from fastapi import APIRouter, HTTPException

router = APIRouter()

_state = {"shutdown": None}


def set_shutdown(callback):
    """由 run.py 注入：置位 uvicorn 的 should_exit。"""
    _state["shutdown"] = callback


def supported():
    return callable(_state["shutdown"])


@router.post("/api/app/shutdown")
def api_shutdown():
    callback = _state["shutdown"]
    if not callable(callback):
        raise HTTPException(status_code=409, detail="当前运行方式不支持从页面退出")

    # 先让响应发出去，再停机；否则浏览器拿到的是连接被重置。
    def _later():
        threading.Event().wait(0.3)
        callback()

    threading.Thread(target=_later, name="mmtest-shutdown", daemon=True).start()
    return {"ok": True}


@router.get("/api/app/can-shutdown")
def api_can_shutdown():
    """前端据此决定是否显示「退出程序」：开发态没有注入回调。"""
    return {"supported": supported()}


def install(app, shutdown=None):
    """幂等挂载；重复调用只更新回调，不重复加路由。"""
    if shutdown is not None:
        set_shutdown(shutdown)
    if getattr(app.state, "_mmtest_control_installed", False):
        return app
    app.include_router(router)
    app.state._mmtest_control_installed = True
    return app
