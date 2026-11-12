"""Regression: the per-function decompiler drops argument defaults.

Python 3.8 keeps default values in the PARENT code object, so every function
rebuilt from its own code object came back without them and any call that
relied on a default raised TypeError.  `tools/recover/apply_defaults.py`
re-attaches them; these tests fail if that ever regresses.
"""
import ast
import inspect
import os

import pytest

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")


def _signature(path, name):
    """Resolve either `func` or `Class.method` inside one module."""
    wanted = name.split(".")
    tree = ast.parse(open(path, encoding="utf-8").read())

    def walk(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef) and wanted[0] == child.name:
                return walk(child)
            if (isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and child.name == wanted[-1]):
                return child
        return None

    found = walk(tree)
    if found is None:
        raise AssertionError(f"{name} not found in {path}")
    return found


def _defaults(path, name):
    node = _signature(path, name)
    positional = node.args.args
    return {a.arg: ast.unparse(d)
            for a, d in zip(positional[len(positional) - len(node.args.defaults):],
                            node.args.defaults)}


@pytest.mark.parametrize("module, name, expected", [
    ("maas", "MaaSClient._resolve", {"model": "None", "site": "None"}),
    ("maas", "MaaSClient.has_keys", {"site": "None"}),
    ("maas", "MaaSClient._release_key", {"error": "None"}),
    ("maas", "MaaSClient.recommended_concurrency", {"requested": "None", "site": "None"}),
    ("maas", "MaaSClient.chat_image",
     {"site": "None", "temperature": "None", "seed": "None", "max_tokens": "None"}),
    ("annotate", "_clip", {"limit": "48"}),
    ("annotate", "_font", {"size": "20"}),
    ("reviews", "derive_verdict", {"iou_threshold": "0.5"}),
    ("runner", "_meta", {"error": "None"}),
    ("prompt_ai", "_add_attachment", {"dataset": "''", "rel": "''"}),
    ("prompt_ai", "optimize",
     {"model": "None", "max_items": "50", "profile_name": "''", "site": "None",
      "trajectory": "None", "record_id": "None"}),
    ("judge", "start_judge",
     {"model": "None", "concurrency": "2", "force": "False", "profile_name": "''",
      "site": "None", "coverage_threshold": "1.0"}),
])
def test_lost_defaults_are_restored(module, name, expected):
    path = os.path.join(APP_DIR, module + ".py")
    assert _defaults(path, name) == expected


def test_maas_client_single_site_path_accepts_keyword_only_site():
    """`test_connection(site=...)` and `has_keys()` used to raise TypeError."""
    from app import maas

    cfg = {
        "api": {"sites": [{"name": "S", "base_url": "http://127.0.0.1:1",
                           "api_keys": ["k"], "models": ["m"]}]},
        "defaults": {"model": "m", "site": "S", "concurrency": 2,
                     "auto_concurrency": True, "key_concurrency": 1,
                     "key_cooldown": 1, "timeout": 1, "max_retries": 1},
    }
    client = maas.MaaSClient(cfg)
    assert client._resolve(site="S")["name"] == "S"
    assert client._resolve(model="m")["name"] == "S"
    assert client.has_keys() is True
    assert client.has_keys("S") is True
    assert client.recommended_concurrency() == 1
    result = client.test_connection(site="S")
    assert result["ok"] is False
    assert result["results"][0]["site"] == "S"
    assert "TypeError" not in result["results"][0]["error"]


def test_no_same_module_call_omits_required_arguments():
    """Catch the class of bug, not just this instance of it."""
    issues = []
    for filename in sorted(os.listdir(APP_DIR)):
        if not filename.endswith(".py"):
            continue
        path = os.path.join(APP_DIR, filename)
        tree = ast.parse(open(path, encoding="utf-8").read())
        table = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args
                positional = [a.arg for a in args.args]
                required = len(positional) - len(args.defaults)
                required_kw = [a.arg for a in args.kwonlyargs if a.default is None]
                table.setdefault(node.name, []).append(
                    (tuple(positional[:required]), tuple(required_kw)))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            bound = False
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif (isinstance(node.func, ast.Attribute)
                  and isinstance(node.func.value, ast.Name)
                  and node.func.value.id == "self"):
                name = node.func.attr
                bound = True
            else:
                continue
            if name not in table:
                continue
            if any(isinstance(a, ast.Starred) for a in node.args):
                continue
            if any(k.arg is None for k in node.keywords):
                continue
            given = len([a for a in node.args if not isinstance(a, ast.Starred)]) + (1 if bound else 0)
            kwargs = {k.arg for k in node.keywords if k.arg}
            for positional, required_kw in table[name]:
                missing = [p for p in positional[given:] if p not in kwargs]
                missing.extend(p for p in required_kw if p not in kwargs)
                if missing:
                    issues.append(f"{filename}:{node.lineno} {name} missing {missing}")
                    break
    assert issues == []