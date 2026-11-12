"""版本与运行时元信息。

独立成模块：`app/main.py` 由原始字节码恢复，往里面加路由会改变对拍基线，
因此新增接口通过 APIRouter 在 `run.py` / 测试中挂载。
"""
import json
import os
import platform
import sys

from fastapi import APIRouter

from .config import BASE_DIR

APP_NAME = "multimodal-testing-platform"
VERSION = "0.2.0"


def _build_info():
    """构建时写入的 build_info.json，开发态没有则返回空字典。"""
    candidates = []
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        candidates.append(os.path.join(meipass, "build_info.json"))
    candidates.append(os.path.join(BASE_DIR, "build", "build_info.json"))
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            continue
    return {}


def info():
    build = _build_info()
    return {
        "app": APP_NAME,
        "version": VERSION,
        "build_time": build.get("build_time", ""),
        "git_commit": build.get("git_commit", ""),
        "git_dirty": build.get("git_dirty", None),
        "python": platform.python_version(),
        "frozen": bool(getattr(sys, "frozen", False)),
        "platform": platform.platform(),
        "recovered_from": "多模态测试平台.exe (Python 3.8)",
    }


router = APIRouter()


@router.get("/api/version")
def api_version():
    return info()


def install(app):
    """幂等挂载：重复调用不会重复注册路由。"""
    if getattr(app.state, "_mmtest_meta_installed", False):
        return app
    app.include_router(router)
    app.state._mmtest_meta_installed = True
    return app
