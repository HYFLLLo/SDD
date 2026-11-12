import json
import logging
import os

import pytest


@pytest.fixture()
def logdir(workspace, monkeypatch):
    from app import applog

    monkeypatch.setattr(applog, "_logger", None)
    yield workspace
    logger = logging.getLogger("mmtest")
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    applog._logger = None


def _lines(path):
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def test_info_writes_json_lines(logdir):
    from app import applog

    applog.info("run.create", run_id="r1", count=3)
    rows = _lines(os.path.join(str(logdir), "logs", "app.log"))
    assert rows[-1]["event"] == "run.create"
    assert rows[-1]["level"] == "INFO"
    assert rows[-1]["run_id"] == "r1"
    assert rows[-1]["count"] == 3
    assert rows[-1]["ts"]


def test_secrets_are_masked(logdir):
    from app import applog

    applog.error("call.failed", exc=ValueError("boom sk-abcdef123456 leaked"))
    raw = open(os.path.join(str(logdir), "logs", "app.log"), encoding="utf-8").read()
    assert "sk-abcdef123456" not in raw
    assert "sk-***" in raw


def test_timed_records_success_and_failure(logdir):
    from app import applog

    with applog.timed("task.ok", task="a"):
        pass
    with pytest.raises(RuntimeError):
        with applog.timed("task.fail", task="b"):
            raise RuntimeError("nope")
    rows = _lines(os.path.join(str(logdir), "logs", "app.log"))
    ok = [r for r in rows if r["event"] == "task.ok"][-1]
    bad = [r for r in rows if r["event"] == "task.fail"][-1]
    assert ok["ms"] >= 0
    assert bad["error_type"] == "RuntimeError"


def test_request_middleware_logs_status_and_path(workspace, monkeypatch):
    import asyncio

    import httpx
    from fastapi import FastAPI

    from app import applog

    monkeypatch.setattr(applog, "_logger", None)
    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    applog.install(app)
    asyncio.run(httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1").get("/ping"))

    rows = _lines(os.path.join(str(workspace), "logs", "app.log"))
    req = [r for r in rows if r["event"] == "request"][-1]
    assert req["path"] == "/ping"
    assert req["status"] == 200
    assert req["method"] == "GET"


def test_install_is_idempotent(workspace):
    from fastapi import FastAPI

    from app import applog

    app = FastAPI()
    applog.install(app)
    applog.install(app)
    assert app.state._mmtest_logging_installed is True
