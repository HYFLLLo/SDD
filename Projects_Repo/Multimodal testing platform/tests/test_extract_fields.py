import asyncio
import json

import httpx


def test_extract_fields_endpoint_works(tmp_path, monkeypatch):
    import app.main as main
    import app.runner as runner
    from app.security import install

    install(main.app)
    monkeypatch.setattr(runner, "_run_dir", lambda run_id: str(tmp_path / run_id))

    run_dir = tmp_path / "r1"
    results = run_dir / "results"
    results.mkdir(parents=True)
    (results / "a.json").write_text(
        json.dumps({"a": 1, "objects": [{"name": "x"}], "custom": {"z": 2}}),
        encoding="utf-8",
    )

    async def call():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8735") as c:
            return await c.get("/api/extract/fields", params={"run_id": "r1"})

    r = asyncio.run(call())
    assert r.status_code == 200, r.text
    assert r.json()["fields"] == ["a", "custom.z", "objects[].name"]