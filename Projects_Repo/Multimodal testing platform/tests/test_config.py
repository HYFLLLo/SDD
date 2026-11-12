import json
import os

import pytest

from app.config import DEFAULT_CONFIG, normalize_config, safe_path


def _minimal_site(**overrides):
    site = {
        "name": "A",
        "base_url": "https://api.example.com/v1/",
        "api_keys": [" k1 ", ""],
        "models": ["m1"],
    }
    site.update(overrides)
    return site


def test_normalize_fills_defaults_and_strips_values():
    cfg = normalize_config({"api": {"sites": [_minimal_site()]}})
    assert cfg["api"]["sites"][0]["name"] == "A"
    assert cfg["api"]["sites"][0]["base_url"] == "https://api.example.com/v1"
    assert cfg["api"]["sites"][0]["api_keys"] == ["k1"]
    assert cfg["api"]["sites"][0]["models"] == ["m1"]
    assert cfg["defaults"]["site"] == "A"
    assert cfg["defaults"]["model"] == "m1"
    assert cfg["defaults"]["temperature"] is None
    assert cfg["defaults"]["judge_temperature"] is None
    for key in ("concurrency", "timeout", "max_tokens", "optimizer_max_tokens",
                "judge_max_tokens", "prompt_max_tokens", "max_retries"):
        assert key in cfg["defaults"]


def test_normalize_rejects_non_object():
    with pytest.raises(ValueError):
        normalize_config([])


def test_normalize_rejects_illegal_site_name():
    for bad in ("a/b", "a\\b", "a:b", "a::b"):
        with pytest.raises(ValueError):
            normalize_config({"api": {"sites": [_minimal_site(name=bad)]}})


def test_normalize_rejects_duplicate_site_name():
    with pytest.raises(ValueError):
        normalize_config({"api": {"sites": [_minimal_site(), _minimal_site()]}})


def test_normalize_rejects_bad_base_url():
    for bad in ("ftp://example.com", "example.com", "", "//example.com"):
        with pytest.raises(ValueError):
            normalize_config({"api": {"sites": [_minimal_site(base_url=bad)]}})


def test_normalize_rejects_empty_models():
    with pytest.raises(ValueError):
        normalize_config({"api": {"sites": [_minimal_site(models=["", "  "])]}})


def test_normalize_rejects_non_list_keys_or_models():
    with pytest.raises(ValueError):
        normalize_config({"api": {"sites": [_minimal_site(api_keys="k")]}})
    with pytest.raises(ValueError):
        normalize_config({"api": {"sites": [_minimal_site(models="m")]}})


@pytest.mark.parametrize("key,value", [
    ("concurrency", 0), ("concurrency", 21),
    ("key_concurrency", 0), ("key_concurrency", 9),
    ("timeout", 4), ("timeout", 601),
    ("max_tokens", 127), ("max_tokens", 131073),
    ("max_retries", 0), ("max_retries", 11),
])
def test_normalize_respects_integer_ranges(key, value):
    with pytest.raises(ValueError):
        normalize_config({"api": {"sites": [_minimal_site()]}, "defaults": {key: value}})


def test_normalize_rejects_non_integer():
    with pytest.raises(ValueError):
        normalize_config({"api": {"sites": [_minimal_site()]}, "defaults": {"concurrency": "abc"}})


def test_normalize_temperature_range_and_none():
    cfg = normalize_config({"api": {"sites": [_minimal_site()]}, "defaults": {"temperature": None}})
    assert cfg["defaults"]["temperature"] is None
    cfg = normalize_config({"api": {"sites": [_minimal_site()]}, "defaults": {"temperature": "1.5"}})
    assert cfg["defaults"]["temperature"] == 1.5
    for bad in (-0.1, 2.1):
        with pytest.raises(ValueError):
            normalize_config({"api": {"sites": [_minimal_site()]}, "defaults": {"temperature": bad}})


def test_normalize_migrates_legacy_single_site_payload():
    cfg = normalize_config({
        "api": {"base_url": "https://legacy.example.com/v1", "api_keys": ["k"], "models": ["m"]},
    })
    site = cfg["api"]["sites"][0]
    assert site["name"] == "默认站点"
    assert site["base_url"] == "https://legacy.example.com/v1"
    assert site["models"] == ["m"]


def test_normalize_empty_sites_falls_back_to_default():
    cfg = normalize_config({"api": {"sites": []}})
    assert cfg["api"]["sites"][0]["name"] == DEFAULT_CONFIG["api"]["sites"][0]["name"]


def test_normalize_model_and_site_selection():
    cfg = normalize_config({
        "api": {"sites": [
            {"name": "A", "base_url": "https://a.example.com", "models": ["m1"]},
            {"name": "B", "base_url": "https://b.example.com", "models": ["m2"]},
        ]},
        "defaults": {"model": "m2", "site": ""},
    })
    assert cfg["defaults"]["model"] == "m2"
    assert cfg["defaults"]["site"] == "B"

    cfg = normalize_config({
        "api": {"sites": [{"name": "A", "base_url": "https://a.example.com", "models": ["m1"]}]},
        "defaults": {"model": "not-there"},
    })
    assert cfg["defaults"]["model"] == "m1"


def test_normalize_does_not_mutate_input():
    source = {"api": {"sites": [_minimal_site()]}, "defaults": {"concurrency": 5}}
    before = json.dumps(source, sort_keys=True)
    normalize_config(source)
    assert json.dumps(source, sort_keys=True) == before


def test_safe_path_allows_inside_and_rejects_traversal(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    inside = base / "a" / "b.txt"
    inside.parent.mkdir()
    inside.write_text("x", encoding="utf-8")

    assert safe_path(str(base), "a", "b.txt") == os.path.realpath(str(inside))
    assert safe_path(str(base)) == os.path.realpath(str(base))

    with pytest.raises(ValueError):
        safe_path(str(base), "..", "outside.txt")
    with pytest.raises(ValueError):
        safe_path(str(base), "a", "..", "..", "outside.txt")


def test_safe_path_rejects_absolute_escape(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    with pytest.raises(ValueError):
        safe_path(str(base), str(tmp_path / "outside.txt"))