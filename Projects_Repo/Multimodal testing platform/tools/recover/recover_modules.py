"""Two-pass recovery: module prologue (imports/constants/decorators) + per-function bodies.

Pass 1 replaces every nested code object with a signature-preserving stub so the module
body itself can be deparsed. Pass 2 deparses each nested function in isolation. Output is
a candidate tree in _recovered_v2/, never written directly to app/.
"""
import contextlib
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"E:\OpenCode Work\decomp")

from xdis import load_module
from xdis.codetype.code38 import Code38
import decompyle3.main as d3
import uncompyle6.main as u6

PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(PROJECT, "_src", "_pyc")
OUT = os.path.join(PROJECT, "_recovered_v2")


def clone(code, **overrides):
    fields = dict(
        co_argcount=code.co_argcount, co_posonlyargcount=code.co_posonlyargcount,
        co_kwonlyargcount=code.co_kwonlyargcount, co_nlocals=code.co_nlocals,
        co_stacksize=code.co_stacksize, co_flags=code.co_flags, co_code=code.co_code,
        co_consts=code.co_consts, co_names=code.co_names, co_varnames=code.co_varnames,
        co_filename=code.co_filename, co_name=code.co_name,
        co_firstlineno=code.co_firstlineno, co_lnotab=code.co_lnotab,
        co_freevars=code.co_freevars, co_cellvars=code.co_cellvars)
    fields.update(overrides)
    return Code38(**fields)


def stub(child):
    args = child.co_argcount + child.co_argcount and child.co_argcount
    n = child.co_argcount
    return clone(child, co_nlocals=n, co_stacksize=1, co_flags=child.co_flags & 0x03,
                 co_code=bytes([100, 0, 83, 0]), co_consts=(None,), co_names=(),
                 co_varnames=child.co_varnames[:n], co_lnotab=b"",
                 co_freevars=(), co_cellvars=())


def deparse(code):
    errors = []
    for mod in (d3, u6):
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                mod.decompile(code, bytecode_version=(3, 8), out=buf)
            text = buf.getvalue()
            text = "\n".join(l for l in text.splitlines() if not l.startswith(("# decompyle3", "# Python bytecode", "# Decompiled", "# uncompyle6", "# Embedded file")))
            return text.strip("\n"), mod.__name__
        except Exception as exc:
            errors.append(f"{mod.__name__}:{type(exc).__name__}:{exc}")
    return None, " | ".join(errors)


def main():
    os.makedirs(OUT, exist_ok=True)
    report = {}
    for filename in sorted(os.listdir(SRC)):
        if not filename.endswith(".pyc"):
            continue
        name = filename[:-4]
        top = load_module(os.path.join(SRC, filename))[3]
        kids = [c for c in top.co_consts if hasattr(c, "co_code")]
        prologue, via = deparse(clone(top, co_consts=tuple(
            stub(c) if hasattr(c, "co_code") else c for c in top.co_consts)))
        entry = {"prologue": via, "children": {}}
        chunks = [prologue or f"# ===== UNRECOVERED MODULE BODY ({via}) =====\n"]
        for child in kids:
            body, how = deparse(child)
            entry["children"][child.co_name] = how if body else "FAIL"
            if body:
                chunks.append(body)
            else:
                chunks.append(f"# ===== UNRECOVERED {child.co_name} (line {child.co_firstlineno}) =====\n{how}\n")
        report[name] = entry
        with open(os.path.join(OUT, name + ".py"), "w", encoding="utf-8") as fh:
            fh.write("\n\n\n".join(chunks) + "\n")
    with open(os.path.join(OUT, "_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    total = sum(1 for v in report.values() for h in v["children"].values() if h != "FAIL")
    failed = sum(1 for v in report.values() for h in v["children"].values() if h == "FAIL")
    print(f"functions recovered={total} failed={failed}")
    for k, v in report.items():
        bad = [n for n, h in v["children"].items() if h == "FAIL"]
        print(f"  {k:20s} prologue={v['prologue']:20s} kids={len(v['children']):3d} failed={bad}")


if __name__ == "__main__":
    main()

