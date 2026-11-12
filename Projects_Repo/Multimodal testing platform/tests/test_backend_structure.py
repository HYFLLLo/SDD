"""P1 回归：锁定反编译恢复后修复的结构缺陷。

这些用例不依赖真实模型服务，只验证控制流与数据契约。
"""
import json
import os
import types

import pytest


@pytest.fixture()
def ws(workspace):
    from app import config

    config.WORKSPACE = str(workspace)
    return workspace


def _image(rel, *repeats):
    return {"rel": rel, "repeats": list(repeats)}


def test_targets_keeps_only_existing_error_free_reviewed(ws, monkeypatch):
    from app import judge, reviews, runner

    monkeypatch.setattr(
        runner,
        "list_run_images",
        lambda run_id: [
            _image(
                "a.jpg",
                {"repeat": 1, "exists": True, "error": ""},
                {"repeat": 2, "exists": False, "error": ""},
                {"repeat": 3, "exists": True, "error": "boom"},
                {"repeat": 4, "exists": True, "error": ""},
            )
        ],
    )
    reviewed = {("a.jpg", 1), ("a.jpg", 2), ("a.jpg", 3), ("a.jpg", 4)}
    monkeypatch.setattr(reviews, "list_reviews", lambda run_id: [
        {"image": rel, "repeat": rep} for rel, rep in reviewed
    ])
    monkeypatch.setattr(reviews, "get_review", lambda run_id, rel, rep: {"verdict": "正确"})
    monkeypatch.setattr(judge, "get_judgment", lambda run_id, rel, rep: {})

    targets, skipped = judge._targets("run-1")
    assert targets == [("a.jpg", 1), ("a.jpg", 4)]
    assert skipped == 0


def test_targets_counts_existing_judgment_as_skipped(ws, monkeypatch):
    from app import judge, reviews, runner

    monkeypatch.setattr(runner, "list_run_images", lambda run_id: [
        _image("a.jpg", {"repeat": 1, "exists": True, "error": ""})
    ])
    monkeypatch.setattr(reviews, "list_reviews", lambda run_id: [{"image": "a.jpg", "repeat": 1}])
    monkeypatch.setattr(reviews, "get_review", lambda run_id, rel, rep: {"verdict": "正确"})
    monkeypatch.setattr(judge, "get_judgment", lambda run_id, rel, rep: {"verdict": "正确"})

    assert judge._targets("run-1") == ([], 1)
    assert judge._targets("run-1", force=True) == ([("a.jpg", 1)], 0)


def test_eligible_targets_excludes_missing_and_errored(ws, monkeypatch):
    from app import judge, reviews, runner

    monkeypatch.setattr(runner, "list_run_images", lambda run_id: [
        _image(
            "a.jpg",
            {"repeat": 1, "exists": True, "error": ""},
            {"repeat": 2, "exists": False, "error": ""},
            {"repeat": 3, "exists": True, "error": "boom"},
        )
    ])
    monkeypatch.setattr(reviews, "list_reviews", lambda run_id: [
        {"image": "a.jpg", "repeat": 1},
        {"image": "a.jpg", "repeat": 2},
        {"image": "a.jpg", "repeat": 3},
    ])
    assert judge._eligible_targets("run-1") == 1
    assert judge.coverage("run-1")["eligible"] == 1


def test_parse_failed_samples_are_excluded_from_judge_scope(ws, monkeypatch):
    """解析失败样本模型没有可比较结论，不进裁判目标，也不进覆盖率分母。"""
    from app import judge, reviews, runner

    monkeypatch.setattr(runner, "list_run_images", lambda run_id: [
        _image(
            "ok.jpg",
            {"repeat": 1, "exists": True, "error": "", "parse_ok": True},
        ),
        _image(
            "broken.jpg",
            {"repeat": 1, "exists": True, "error": "", "parse_ok": False},
        ),
    ])
    reviewed = [{"image": "ok.jpg", "repeat": 1}, {"image": "broken.jpg", "repeat": 1}]
    monkeypatch.setattr(reviews, "list_reviews", lambda run_id: reviewed)
    monkeypatch.setattr(reviews, "get_review", lambda run_id, rel, rep: {"verdict": "正确"})
    monkeypatch.setattr(judge, "get_judgment", lambda run_id, rel, rep: {})

    targets, _ = judge._targets("run-1")
    assert targets == [("ok.jpg", 1)]
    assert judge._eligible_targets("run-1") == 1
    assert judge._parse_failed_targets("run-1") == 1


def test_list_runs_reports_parse_failed_separately(ws, monkeypatch):
    """解析失败不能算进「调用失败」，否则界面出现失败 0 却有图没结论。"""
    from app import config, runner

    run_dir = os.path.join(config.WORKSPACE, "runs", "run-1")
    os.makedirs(os.path.join(run_dir, "results"), exist_ok=True)
    with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
        json.dump({"id": "run-1", "status": "done", "done": 2, "failed": 0, "total": 2}, f)
    with open(os.path.join(run_dir, "results", "a.jpg__r1.json"), "w", encoding="utf-8") as f:
        json.dump({"parse_ok": True, "objects": [], "_meta": {}}, f)
    with open(os.path.join(run_dir, "results", "b.jpg__r1.json"), "w", encoding="utf-8") as f:
        json.dump({"parse_ok": False, "objects": [], "_meta": {}}, f)

    runner._runs_cache.invalidate()
    run = [r for r in runner.list_runs() if r["id"] == "run-1"][0]
    assert run["failed"] == 0
    assert run["parse_failed"] == 1
    assert run["done"] == 2


def test_reconcile_counts_keeps_call_failure_and_parse_failure_apart(ws):
    from app import config, runner

    run_dir = os.path.join(config.WORKSPACE, "runs", "run-2")
    results = os.path.join(run_dir, "results")
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "ok.jpg__r1.json"), "w", encoding="utf-8") as f:
        json.dump({"parse_ok": True, "_meta": {}}, f)
    with open(os.path.join(results, "broken.jpg__r1.json"), "w", encoding="utf-8") as f:
        json.dump({"parse_ok": False, "_meta": {}}, f)
    with open(os.path.join(results, "error.jpg__r1.json"), "w", encoding="utf-8") as f:
        json.dump({"parse_ok": False, "_meta": {"error": "timeout"}}, f)

    run = {"id": "run-2"}
    runner._reconcile_counts(run)
    assert run["done"] == 2
    assert run["failed"] == 1
    assert run["parse_failed"] == 1


def test_reparse_results_repairs_only_parse_failures_and_backs_up(ws):
    """重新解析：只动「接口成功但解析失败」的结果，原始文件先备份。"""
    from app import config, runner

    run_dir = os.path.join(config.WORKSPACE, "runs", "run-3")
    results = os.path.join(run_dir, "results")
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as f:
        json.dump({"id": "run-3", "status": "done", "done": 1, "failed": 1, "total": 2,
                   "repeat": 1, "dataset": "p/d", "prompt_name": "t", "prompt_version": 1,
                   "model": "m", "prompt_settings": {}}, f)
    broken_raw = (
        "```json\n{\n  \"objects\": [{\n    \"labelName\": \"水边人员\",\n"
        "    \"bbox\": [1,2,3,4]]\n  }],\n  \"analysis_summary\": \"ok\"\n}\n```"
    )
    with open(os.path.join(results, "a.jpg__r1.json"), "w", encoding="utf-8") as f:
        json.dump({"parse_ok": False, "objects": [], "raw": broken_raw, "_meta": {}}, f)
    with open(os.path.join(results, "b.jpg__r1.json"), "w", encoding="utf-8") as f:
        json.dump({"parse_ok": False, "objects": [], "raw": "", "_meta": {"error": "timeout"}}, f)

    out = runner.reparse_results("run-3")
    assert out["repaired"] == 1
    assert out["still_failed"] == 1
    assert out["backup"] and os.path.isdir(out["backup"])

    with open(os.path.join(results, "a.jpg__r1.json"), encoding="utf-8") as f:
        fixed = json.load(f)
    assert fixed["parse_ok"] is True
    assert fixed["objects"][0]["name"] == "水边人员"
    with open(os.path.join(results, "b.jpg__r1.json"), encoding="utf-8") as f:
        untouched = json.load(f)
    assert untouched["parse_ok"] is False


def test_start_judge_with_empty_jobs_does_not_unboundlocal(ws, monkeypatch):
    from app import judge, maas, runner

    monkeypatch.setattr(runner, "get_run", lambda run_id: {"id": run_id})
    monkeypatch.setattr(judge, "_jobs", {})
    monkeypatch.setattr(judge, "_targets", lambda run_id, force=False: ([], 0))
    monkeypatch.setattr(judge, "_save_job", lambda job: None)
    monkeypatch.setattr(judge, "_eligible_targets", lambda run_id: 0)
    monkeypatch.setattr(judge, "_should_auto_force", lambda *a, **k: (False, ""))
    monkeypatch.setattr(judge, "_existing_judge_model", lambda run_id: None)
    monkeypatch.setattr(judge, "_existing_judge_profile", lambda run_id: "")
    monkeypatch.setattr(maas.MaaSClient, "has_keys", lambda self, site=None: True)
    monkeypatch.setattr(maas.MaaSClient, "recommended_concurrency", lambda self, n, site=None: n)
    monkeypatch.setattr(judge.threading, "Thread", lambda *a, **k: types.SimpleNamespace(start=lambda: None))

    job = judge.start_judge("run-new")
    assert job["run_id"] == "run-new"


def test_prompt_chat_returns_generating_and_starts_thread(ws, monkeypatch):
    from app import prompt_ai

    started = []

    class FakeThread:
        def __init__(self, target=None, args=(), daemon=None):
            self.target = target
            self.args = args

        def start(self):
            started.append((self.target, self.args))

    session = prompt_ai.create_session("", "", "标题", "", "", "")
    monkeypatch.setattr(prompt_ai.threading, "Thread", FakeThread)

    out = prompt_ai.chat(session["id"], "你好")
    assert out["status"] == "generating"
    assert out["session"]["messages"][-1]["content"] == "你好"
    assert len(started) == 1
    assert started[0][0] is prompt_ai._chat_background


def test_chat_background_sends_image_only_for_new_message(ws, monkeypatch):
    from app import prompt_ai

    session = prompt_ai.create_session("", "", "t", "", "", "")
    session["messages"] = [
        {"role": "user", "content": "旧图", "images": ["a.png"]},
        {"role": "assistant", "content": "收到"},
        {"role": "user", "content": "新图", "images": ["b.png"]},
    ]
    prompt_ai._save_session(session)

    captured = {}

    class FakeClient:
        def __init__(self, cfg):
            pass

        def has_keys(self, site):
            return True

        def image_part(self, path):
            return {"type": "image_url", "image_url": {"url": "data:x"}}

        def chat_messages(self, messages, model, **kwargs):
            captured["messages"] = messages
            return {"text": "ok"}

    monkeypatch.setattr(prompt_ai, "MaaSClient", FakeClient)
    monkeypatch.setattr(prompt_ai, "attachment_file", lambda sid, name: name)
    monkeypatch.setattr(prompt_ai.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(prompt_ai, "_save_session", lambda s: None)

    prompt_ai._chat_background(session["id"], "m", None)
    msgs = captured["messages"]
    assert msgs[0]["content"] == "旧图"
    assert isinstance(msgs[0]["content"], str)
    assert isinstance(msgs[2]["content"], list)
    assert msgs[2]["content"][0]["type"] == "image_url"


def test_chat_background_raises_on_model_error(ws, monkeypatch):
    from app import prompt_ai

    session = prompt_ai.create_session("", "", "t", "", "", "")
    session["messages"] = [{"role": "user", "content": "hi", "images": []}]
    prompt_ai._save_session(session)

    class FakeClient:
        def __init__(self, cfg):
            pass

        def has_keys(self, site):
            return True

        def chat_messages(self, messages, model, **kwargs):
            return {"error": "vision unsupported"}

    saved = []
    monkeypatch.setattr(prompt_ai, "MaaSClient", FakeClient)
    monkeypatch.setattr(prompt_ai, "_save_session", lambda s: saved.append(s))

    prompt_ai._chat_background(session["id"], "m", None)
    assert saved, "失败时应把错误消息写回会话"
    assert "生成失败" in saved[-1]["messages"][-1]["content"]


def test_compare_quality_improvement(ws):
    from app import workflow

    state = {"thresholds": {"judge_coverage": 1.0}, "min_improvement": 0.05}
    previous = {"accuracy": 0.5, "parse_rate": 1.0, "protocol_valid_rate": 1.0,
                "judge_coverage": 1.0, "high_severity_errors": 0}
    candidate = {"accuracy": 0.7, "parse_rate": 1.0, "protocol_valid_rate": 1.0,
                 "judge_coverage": 1.0, "high_severity_errors": 0}
    improved, delta, reason = workflow._compare_quality(previous, candidate, state)
    assert improved is True
    assert delta["accuracy"] == 0.2
    assert "提升" in reason


def test_quality_without_deterministic_comparison(ws, monkeypatch):
    from app import judge, reviews, stats, workflow

    monkeypatch.setattr(stats, "run_stability", lambda run_id: {})
    monkeypatch.setattr(reviews, "metrics", lambda run_id: {})
    monkeypatch.setattr(judge, "list_judgments", lambda run_id: [
        {"verdict": "错误", "severity": "高", "deterministic_verdict": "错误"}
    ])
    monkeypatch.setattr(judge, "get_job", lambda run_id: {})

    out = workflow._quality("run-1")
    assert out["box_f1"] is None
    assert out["high_severity_errors"] == 1
    assert out["root_cause_counts"] == {"无法确定": 1}


def test_labels_for_image_returns_candidate_task(ws, monkeypatch):
    from app import truth

    monkeypatch.setattr(truth, "list_tasks", lambda: [{"id": "t1", "dataset": "ds"}])
    monkeypatch.setattr(truth, "get_task_meta", lambda task: {"name": "n", "kind": "binary"})
    monkeypatch.setattr(truth, "_labeled_map", lambda task: {"a.jpg": ["阳性"]})

    out = truth.labels_for_image("ds", "a.jpg")
    assert out["task"] == "t1"
    assert out["labels"] == ["阳性"]


def test_extract_rejects_empty_output_name(ws):
    from app import extractor

    with pytest.raises(ValueError):
        extractor.extract({"run_id": "r", "output_name": "  "})
    with pytest.raises(ValueError):
        extractor.extract({"run_id": "r", "output_name": "../escape"})


def test_maas_client_defaults_callable(ws):
    from app import maas

    cfg = {"api": {"sites": []}, "defaults": {}}
    client = maas.MaaSClient(cfg)
    assert client.default_site == ""


def test_chat_multimodal_sends_text_once(ws, monkeypatch, tmp_path):
    from app import maas

    img = tmp_path / "a.png"
    img.write_bytes(b"x")
    cfg = {"api": {"sites": []}, "defaults": {}}
    client = maas.MaaSClient(cfg)
    monkeypatch.setattr(maas.MaaSClient, "_data_url", staticmethod(lambda p: "data:image/png;base64,eA=="))
    captured = {}
    monkeypatch.setattr(
        maas.MaaSClient,
        "_chat",
        lambda self, messages, model=None, temperature=None, seed=None,
        max_tokens=None, site=None, timeout=None, max_retries=None:
            captured.update(messages=messages) or {"text": ""},
    )

    client.chat_multimodal([str(img), str(img)], "prompt", "m", "", None, None, None, None)
    content = captured["messages"][-1]["content"]
    assert [part["type"] for part in content] == ["image_url", "image_url", "text"]


def test_add_version_note_defaults_to_empty(ws):
    from app import prompts

    prompts.create_prompt("p", "x", "", "", False)
    rec = prompts.add_version("p", "hello")
    assert rec["version"] >= 1
    assert rec["note"] == ""
