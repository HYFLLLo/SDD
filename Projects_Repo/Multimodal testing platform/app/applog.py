"""结构化日志：JSON Lines + 轮转，失败不影响主流程。

只记录事件与耗时，不记录提示词正文、图片内容或 API Key；
错误信息在写入前统一过一遍脱敏（sk- 开头的串被替换）。
"""
import json
import logging
import os
import re
import sys
import threading
import time
from logging.handlers import RotatingFileHandler

from .config import subdir

_MAX_BYTES = 2 * 1024 * 1024
_BACKUPS = 3
_SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{6,})")
_lock = threading.Lock()
_logger = None


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)[-2000:]
        text = json.dumps(payload, ensure_ascii=False)
        return _SECRET_RE.sub("sk-***", text)


def log_path():
    folder = subdir("logs")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "app.log")


def _handler_target(handler):
    return os.path.abspath(getattr(handler, "baseFilename", "") or "")


def get_logger():
    global _logger
    target = os.path.abspath(log_path())
    if _logger is not None and _logger.handlers and _handler_target(_logger.handlers[0]) == target:
        return _logger
    with _lock:
        logger = logging.getLogger("mmtest")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        for old in list(logger.handlers):
            try:
                old.close()
            except Exception:
                pass
            logger.removeHandler(old)
        try:
            handler = RotatingFileHandler(
                target, maxBytes=_MAX_BYTES, backupCount=_BACKUPS, encoding="utf-8"
            )
            handler.setFormatter(JsonFormatter())
            logger.addHandler(handler)
        except Exception:
            pass
        if os.environ.get("MMTEST_LOG_STDERR", "").strip().lower() in {"1", "true", "yes"}:
            stream = logging.StreamHandler(sys.stderr)
            stream.setFormatter(JsonFormatter())
            logger.addHandler(stream)
        _logger = logger
        return logger


def debug(event, **fields):
    # 文件日志级别固定为 INFO：debug 事件默认不落盘，仅用于显式排查。
    get_logger().debug(event, extra={"fields": fields})


def info(event, **fields):
    get_logger().info(event, extra={"fields": fields})


def warning(event, **fields):
    get_logger().warning(event, extra={"fields": fields})


def error(event, exc=None, **fields):
    # 传 exc_info=False 而不是 None，否则 logging 会自行抓取当前异常上下文
    get_logger().error(event, exc_info=exc, extra={"fields": fields})


class timed:
    """with timed("run.create", run_id=...): 记录耗时，异常也记。"""

    def __init__(self, event, **fields):
        self.event = event
        self.fields = fields
        self.started = 0.0

    def __enter__(self):
        self.started = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        cost = round((time.perf_counter() - self.started) * 1000, 1)
        payload = dict(self.fields, ms=cost)
        if exc_type is None:
            info(self.event, **payload)
        else:
            payload["error_type"] = exc_type.__name__
            error(self.event, exc=exc, **payload)
        return False


def install(app):
    """挂载请求日志中间件：只记路径、状态码、耗时，不记请求体。"""
    if getattr(app.state, "_mmtest_logging_installed", False):
        return app
    from starlette.middleware.base import BaseHTTPMiddleware

    class RequestLog(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            started = time.perf_counter()
            try:
                response = await call_next(request)
            except Exception as exc:
                cost = round((time.perf_counter() - started) * 1000, 1)
                error("request.failed", exc=exc, method=request.method,
                      path=request.url.path, ms=cost)
                raise
            cost = round((time.perf_counter() - started) * 1000, 1)
            path = request.url.path
            # 静态资源与高频轮询降级为 debug，避免日志被刷满
            noisy = path.startswith("/static/") or path in ("/api/dashboard", "/api/runs")
            verbose = noisy and cost < 1000 and response.status_code < 400
            level = debug if verbose else info
            level("request", method=request.method, path=path,
                  status=response.status_code, ms=cost, noisy=noisy)
            return response

    app.add_middleware(RequestLog)
    app.state._mmtest_logging_installed = True
    return app
