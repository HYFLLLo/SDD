import pytest


@pytest.fixture()
def ws(workspace):
    from app import config

    config.WORKSPACE = str(workspace)
    return workspace


def test_list_prompts_returns_empty_list_not_none(ws):
    from app import prompts

    assert prompts.list_prompts() == []


def test_list_prompts_returns_all_items(ws):
    from app import prompts

    prompts.create_prompt("b", "x", "", "", False)
    prompts.create_prompt("a", "y", "", "", False)
    items = prompts.list_prompts()
    assert isinstance(items, list)
    assert [i["name"] for i in items] == ["a", "b"]


def test_project_datasets_returns_all_items(ws):
    from app import datasets

    datasets.create_project("p1", "")
    datasets.create_dataset("d1", "p1")
    datasets.create_dataset("d2", "p1")
    names = [d["name"] for d in datasets._project_datasets("p1")]
    assert names == ["d1", "d2"]


def test_update_dataset_meta_applies_all_keys(ws):
    from app import datasets

    datasets.create_project("p1", "")
    datasets.create_dataset("d1", "p1")
    ref = datasets.dataset_ref("p1", "d1")
    meta = datasets.update_dataset_meta(ref, {"note": "n"})
    assert meta["note"] == "n"


def test_truth_list_tasks_returns_all(ws):
    import os

    from app import datasets, truth

    datasets.create_project("p1", "")
    datasets.create_dataset("d1", "p1")
    ref = datasets.dataset_ref("p1", "d1")
    with open(os.path.join(datasets._dataset_dir(ref, create=True), "a.jpg"), "wb") as f:
        f.write(b"x")
    truth.create_task("t1", "single", ["a", "b"], ref)
    truth.create_task("t2", "single", ["a", "b"], ref)
    assert len(truth.list_tasks()) == 2


def test_list_sessions_returns_all(ws):
    from app import prompt_ai

    s1 = prompt_ai.create_session("", "", "one", "", "", "")
    s2 = prompt_ai.create_session("", "", "two", "", "", "")
    ids = {s["id"] for s in prompt_ai.list_sessions()}
    assert {s1["id"], s2["id"]} <= ids


def test_existing_result_path_falls_back_to_canonical(ws):
    import os

    from app import runner

    path = runner._existing_result_path("no-such-run", "a.jpg", 1)
    assert path.endswith(os.path.join("results", runner._result_rel("a.jpg", 1)))