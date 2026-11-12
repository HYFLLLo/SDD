import asyncio
import json
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def client():
    import app.main as main
    from app.security import install

    install(main.app)
    transport = httpx.ASGITransport(app=main.app)
    return httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8735")


def _get(client, path, headers=None):
    return asyncio.run(client.get(path, headers=headers))


def test_index_serves_versioned_assets(client):
    """静态资源 URL 必须带内容指纹：否则改完前端，用户刷新仍拿到旧 app.js。"""
    from app.security import ASSET_VERSION_MARK, asset_version

    version = asset_version()
    assert version and len(version) > 4

    r = _get(client, "/")
    assert ASSET_VERSION_MARK not in r.text
    assert f"/static/app.js?v={version}" in r.text
    assert f"/static/style.css?v={version}" in r.text


def test_static_assets_require_revalidation(client):
    """前端没有文件名指纹，静态资源必须回源校验，否则用户会长期停在旧界面。"""
    for path in ("/", "/static/app.js", "/static/style.css"):
        r = _get(client, path)
        assert r.status_code == 200, path
        assert "no-cache" in r.headers.get("cache-control", ""), path


def test_index_has_security_headers(client):
    r = _get(client, "/")
    assert r.status_code == 200
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert "javascript:" not in r.text
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"


def test_static_assets_have_security_headers(client):
    for path in ("/static/app.js", "/static/style.css"):
        r = _get(client, path)
        assert r.status_code == 200, path
        assert "content-security-policy" in r.headers, path
        assert r.headers["x-content-type-options"] == "nosniff", path


def test_docs_use_relaxed_csp(client):
    r = _get(client, "/docs")
    assert r.status_code == 200
    csp = r.headers["content-security-policy"]
    assert "https://cdn.jsdelivr.net" in csp


def test_host_allowlist_rejects_dns_rebinding(client):
    r = _get(client, "/", headers={"Host": "evil.example.com"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Host not allowed"


@pytest.mark.parametrize("host", ["127.0.0.1:8735", "localhost:8735", "[::1]:8735"])
def test_host_allowlist_accepts_local(client, host):
    assert _get(client, "/", headers={"Host": host}).status_code == 200


def test_missing_host_header_is_rejected(client):
    assert _get(client, "/", headers={"Host": ""}).status_code == 400


def test_frontend_has_no_inline_event_handlers():
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "javascript:" not in js
    assert "javascript:" not in html
    assert " onclick=" not in js
    assert " onerror=" not in js
    assert " onclick=" not in html


def test_frontend_assets_server_rendered_html_is_standalone():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/static/app.js" in html
    assert "/static/style.css" in html