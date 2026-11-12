import asyncio

import httpx
import pytest


@pytest.fixture()
def client():
    import app.main as main
    from app.control import install
    from app.security import install as install_security

    # 按真实启动顺序：安全基线必须在本进程发第一个请求之前装好。
    # 否则 ASGITransport 一旦跑起来，后面的 test_security 再 add_middleware 会报
    # "Cannot add middleware after an application has started"。
    install_security(main.app)
    install(main.app, shutdown=None)
    transport = httpx.ASGITransport(app=main.app)
    return httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8735")


def test_can_shutdown_reports_unsupported_without_callback(client):
    """开发态（serve 未注入回调）不能让前端显示一个点了没反应的退出按钮。"""
    r = asyncio.run(client.get("/api/app/can-shutdown"))
    assert r.status_code == 200
    assert r.json() == {"supported": False}


def test_shutdown_without_callback_is_rejected(client):
    r = asyncio.run(client.post("/api/app/shutdown"))
    assert r.status_code == 409


def test_shutdown_fires_callback_after_responding(client):
    """退出必须先把 200 发出去再停机，否则浏览器看到的是连接被重置。"""
    import app.control as control

    called = []
    control.set_shutdown(lambda: called.append(True))
    try:
        assert asyncio.run(client.get("/api/app/can-shutdown")).json()["supported"] is True
        r = asyncio.run(client.post("/api/app/shutdown"))
        assert r.status_code == 200 and r.json() == {"ok": True}
        for _ in range(100):
            if called:
                break
            import time as _t
            _t.sleep(0.02)
        assert called == [True]
    finally:
        control.set_shutdown(None)


def test_install_is_idempotent():
    import app.main as main
    from app.control import install

    before = len(main.app.routes)
    install(main.app)
    install(main.app, shutdown=lambda: None)
    assert len(main.app.routes) - before <= 1
    assert main.app.state._mmtest_control_installed is True
