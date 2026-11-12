import os
import pytest


@pytest.fixture()
def ws(workspace):
    from app import config
    config.WORKSPACE = str(workspace)
    return workspace


def test_reviews_list_returns_all_and_summary_counts_all(ws):
    from app import reviews
    root = os.path.join(str(ws), "reviews", "run-1")
    os.makedirs(root, exist_ok=True)
    import json
    for name, verdict in (("b.json", "错误"), ("a.json", "正确")):
        with open(os.path.join(root, name), "w", encoding="utf-8") as f:
            json.dump({"run_id": "run-1", "image": name[:-5] + ".jpg", "repeat": 1,
                       "verdict": verdict, "expected_objects": []}, f, ensure_ascii=False)
    rows = reviews.list_reviews("run-1")
    assert len(rows) == 2
    out = reviews.summary("run-1")
    assert out["total"] == 2
    assert out["counts"]["正确"] == 1


def test_reviews_metrics_counts_all_rows(ws):
    from app import reviews
    root = os.path.join(str(ws), "reviews", "run-2")
    os.makedirs(root, exist_ok=True)
    import json
    for name, verdict in (("a.json", "正确"), ("b.json", "正确"), ("c.json", "误报")):
        with open(os.path.join(root, name), "w", encoding="utf-8") as f:
            json.dump({"image": name[:-5] + ".jpg", "repeat": 1, "verdict": verdict}, f, ensure_ascii=False)
    out = reviews.metrics("run-2")
    assert out["reviewed"] == 3
    assert out["correct"] == 2
    assert out["accuracy"] == 0.6667


def test_reviews_normalize_objects_keeps_all(ws, tmp_path, monkeypatch):
    from app import reviews, runner
    from PIL import Image
    img = tmp_path / "a.png"
    Image.new("RGB", (100, 100)).save(img)
    monkeypatch.setattr(runner, "get_run", lambda run_id: {"dataset": "d"})
    monkeypatch.setattr(runner, "image_file", lambda run_id, rel: str(img))
    out = reviews._normalize_objects("r", "a.png", [
        {"bbox": [1, 1, 20, 20]},
        {"bbox": [2, 2, 30, 30]},
    ])
    assert len(out) == 2


def test_prompts_add_version_supports_existing_prompt(ws):
    from app import prompts
    prompts.create_prompt("p", "x", "", "", False)
    first = prompts.add_version("p", "y", "n1")
    second = prompts.add_version("p", "z", "n2")
    assert second["version"] == first["version"] + 1
    assert len(prompts.list_prompts()[0]["versions"]) == 3


def test_prompts_update_version_updates_existing_version(ws):
    from app import prompts
    prompts.create_prompt("p", "x", "", "", False)
    prompts.update_version("p", 1, "note", None, None)
    assert prompts.get_version("p", 1)["info"]["note"] == "note"


def test_prompts_update_settings_keeps_map(ws):
    from app import prompts
    prompts.create_prompt("p", "x", "", "", False)
    out = prompts.update_settings("p", {"map": {"status_field": "a", "name_field": "b"}})
    assert out["map"]["status_field"] == "a"
    assert out["map"]["name_field"] == "b"


def test_prompts_mark_version_status_validates_each_version(ws):
    from app import prompts
    import pytest
    prompts.create_prompt("p", "x", "", "", False)
    prompts.add_version("p", "y", "")
    prompts.mark_version_status("p", 2, "rejected")
    with pytest.raises(ValueError):
        prompts.mark_version_status("p", 99, "rejected")


def test_datasets_update_meta_applies_all_keys(ws):
    from app import datasets
    datasets.create_project("p1", "")
    datasets.create_dataset("d1", "p1")
    ref = datasets.dataset_ref("p1", "d1")
    meta = datasets.update_dataset_meta(ref, {"note": "n", "description": "d"})
    assert meta["note"] == "n"
    assert meta["description"] == "d"


def test_datasets_import_from_path_copies_all_files(ws, tmp_path):
    from app import datasets
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    for rel in ("a.jpg", "sub/b.png"):
        (src / rel).write_bytes(b"x")
    datasets.create_project("p1", "")
    ref = datasets.dataset_ref("p1", "d1")
    n = datasets.import_from_path(ref, str(src))
    assert n == 2
    assert len(datasets.scan_images(ref)) == 2