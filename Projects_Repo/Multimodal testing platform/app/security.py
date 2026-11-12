"""本地服务安全基线：Host 白名单 + 安全响应头。

单独成模块，避免改动由字节码装配生成的 app/main.py。
run.py 导入 app 之后调用 install(app) 完成注册。
"""
import hashlib
import os
import sys
from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from . import meta

DEFAULT_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}

CSP = ("default-src 'self'; "
       "img-src 'self' data: blob:; "
       "style-src 'self' 'unsafe-inline'; "
       "script-src 'self'; "
       "connect-src 'self'; "
       "object-src 'none'; "
       "base-uri 'self'; "
       "form-action 'self'; "
       "frame-ancestors 'none'")

# FastAPI 自带的 /docs、/redoc 依赖 CDN 资源，单独放宽，避免本地文档页白屏。
DOCS_CSP = ("default-src 'self'; "
            "img-src 'self' data: blob: https://fastapi.tiangolo.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' data: https://cdn.jsdelivr.net; "
            "object-src 'none'; "
            "frame-ancestors 'none'")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}

DOCS_PREFIXES = ("/docs", "/redoc")


def allowed_hosts():
    raw = os.environ.get("MMTEST_ALLOWED_HOSTS", "")
    extra = {x.strip().lower() for x in raw.split(",") if x.strip()}
    return DEFAULT_ALLOWED_HOSTS | extra


def host_name(host_header):
    """取 Host 头里的主机名，支持 IPv6 字面量与可选端口。"""
    value = (host_header or "").strip()
    if not value:
        return ""
    if value.startswith("["):
        end = value.find("]")
        return value[1:end].lower() if end != -1 else ""
    if value.count(":") == 1:
        value = value.rsplit(":", 1)[0]
    return value.strip().lower()


# 前端没有构建链、文件名也不带指纹，一旦被浏览器长缓存，用户会长期停在旧界面。
# 统一要求回源校验（ETag 命中时仍是 304，只多一次条件请求）。
NO_CACHE_TYPES = ("text/html", "text/css", "text/javascript", "application/javascript")


def _needs_revalidation(path, response):
    ctype = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
    if ctype in NO_CACHE_TYPES:
        return True
    return path == "/" or path.startswith("/static/")


ASSET_VERSION_MARK = "__ASSET_VERSION__"


def _asset_paths():
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
    if getattr(sys, "frozen", False):
        base = os.path.join(sys._MEIPASS, "web")
    return [os.path.join(base, name) for name in ("app.js", "style.css")]


def _content_hash():
    """静态资源内容指纹：内容一变 URL 就变，彻底躲开旧的浏览器缓存。"""
    digest = hashlib.sha1()
    for path in _asset_paths():
        try:
            with open(path, "rb") as fh:
                digest.update(fh.read())
        except OSError:
            digest.update(path.encode("utf-8"))
    return digest.hexdigest()[:8]


def asset_version():
    """静态资源版本号：版本 + 内容指纹 + 构建提交号。"""
    info = {}
    try:
        info = meta.info()
    except Exception:
        pass
    parts = [str(getattr(meta, "VERSION", "0")), _content_hash(),
             str(info.get("git_commit") or "")[:8]]
    return "-".join(x for x in parts if x)


async def _inject_asset_version(response):
    body = b""
    async for chunk in response.body_iterator:
        body += chunk if isinstance(chunk, bytes) else str(chunk).encode(response.charset)
    text = body.decode(response.charset or "utf-8")
    text = text.replace(ASSET_VERSION_MARK, asset_version())
    headers = {k: v for k, v in response.headers.items()
               if k.lower() not in {"content-length", "content-encoding"}}
    return Response(content=text, status_code=response.status_code,
                    headers=headers, media_type=response.media_type)


def _is_index(path):
    return path in ("/", "/index.html")


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if host_name(request.headers.get("host")) not in allowed_hosts():
            return JSONResponse({"detail": "Host not allowed"}, status_code=400)
        response = await call_next(request)
        path = urlsplit(request.url.path).path
        csp = DOCS_CSP if path.startswith(DOCS_PREFIXES) else CSP
        response.headers.setdefault("Content-Security-Policy", csp)
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        if _needs_revalidation(path, response):
            response.headers.setdefault("Cache-Control", "no-cache, must-revalidate")
        ctype = (response.headers.get("content-type") or "").lower()
        if ctype.startswith("text/html") and _is_index(path):
            return await _inject_asset_version(response)
        return response


def install(app):
    """幂等注册：重复调用（如测试夹具）不会重复加中间件。"""
    if getattr(app.state, "_mmtest_security_installed", False):
        return app
    app.add_middleware(SecurityMiddleware)
    app.state._mmtest_security_installed = True
    return app
