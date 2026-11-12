import asyncio
import json

import httpx
import pytest


@pytest.fixture()
def client():
    import app.main as main
    from app.meta import install

    install(main.app)
    transport = httpx.ASGITransport(app=main.app)
    return httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8735")


def _get(client, path):
    return asyncio.run(client.get(path))


def test_version_endpoint_returns_metadata(client):
    r = _get(client, "/api/version")
    assert r.status_code == 200
    body = r.json()
    assert body["app"] == "multimodal-testing-platform"
    assert body["version"] == "0.2.0"
    assert body["frozen"] is False
    assert body["python"]
    assert body["platform"]


def test_info_has_stable_shape():
    from app import meta

    body = meta.info()
    for key in ("app", "version", "build_time", "git_commit", "git_dirty",
                "python", "frozen", "platform", "recovered_from"):
        assert key in body


def test_install_is_idempotent():
    import app.main as main
    from app import meta

    before = len(main.app.routes)
    meta.install(main.app)
    meta.install(main.app)
    after = len(main.app.routes)
    assert after - before <= 1
    assert main.app.state._mmtest_meta_installed is True


def test_build_info_is_optional(monkeypatch, tmp_path):
    from app import meta

    monkeypatch.setattr(meta, "BASE_DIR", str(tmp_path))
    assert meta._build_info() == {}

    build = tmp_path / "build"
    build.mkdir()
    (build / "build_info.json").write_text(
        json.dumps({"build_time": "2026-11-06 10:00", "git_commit": "abc1234",
                    "git_dirty": False}), encoding="utf-8")
    info = meta.info()
    assert info["build_time"] == "2026-11-06 10:00"
    assert info["git_commit"] == "abc1234"
    assert info["git_dirty"] is False
