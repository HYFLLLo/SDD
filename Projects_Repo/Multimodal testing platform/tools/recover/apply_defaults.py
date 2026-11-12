"""Re-attach argument defaults lost by the per-function decompiler.

Python 3.8 stores default values in the PARENT code object (the
``BUILD_TUPLE`` + ``LOAD_CONST '<qualname>'`` before ``MAKE_FUNCTION``), so a
function deparsed from its own code object never sees them.  The module/class
scaffold produced by the deparser does, because it is deparsed from the parent
body.  This tool therefore reads the scaffold and copies the default *text*
back onto the existing sources, touching signature lines only.
"""
from __future__ import annotations

import ast
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.environ.get("DECOMP_DIR", r"E:\OpenCode Work\decomp"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xdis import load_module

import assemble


def qualified(node, prefix=""):
    """Walk a scaffold: functions are leaves (bodies are `pass`), classes recurse."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield prefix + child.name, child
        elif isinstance(child, ast.ClassDef):
            yield from qualified(child, prefix + child.name + ".")


def scaffold_defaults(source):
    """qualname -> [(arg, default_text), ...] for the trailing defaulted args."""
    tree = ast.parse(source)
    out = {}
    for name, node in qualified(tree):
        pairs = assemble.arg_defaults(node, source)
        if pairs:
            out[name] = pairs
    return out


def source_functions(node, prefix=""):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = prefix + child.name
            yield name, child
            yield from source_functions(child, name + ".")
        elif isinstance(child, ast.ClassDef):
            yield from source_functions(child, prefix + child.name + ".")


def patch(path, defaults, report):
    raw = open(path, "rb").read()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    tree = ast.parse(text)
    inserts = []
    for name, node in source_functions(tree):
        want = defaults.get(name)
        if not want:
            continue
        positional = node.args.args
        have = set(len(positional) - len(node.args.defaults), ) if False else None
        first = len(positional) - len(node.args.defaults)
        names = [a.arg for a in positional[first:]]
        if names == [n for n, _ in want]:
            continue
        target = [n for n, _ in want]
        if [a.arg for a in positional[-len(target):]] != target:
            report.append((os.path.basename(path), name, "arg-name-mismatch"))
            continue
        if first > len(positional) - len(target):
            report.append((os.path.basename(path), name, "already-partial"))
        for arg, (_, piece) in zip(positional[-len(target):], want):
            if arg.arg in names:
                continue
            inserts.append((arg.end_lineno, arg.end_col_offset, "=" + piece))
        if inserts:
            report.append((os.path.basename(path), name, "patched"))
    if not inserts:
        return 0
    lines = text.splitlines(keepends=True)
    for lineno, col, piece in sorted(inserts, key=lambda i: (i[0], i[1]), reverse=True):
        line = lines[lineno - 1]
        lines[lineno - 1] = line[:col] + piece + line[col:]
    result = "".join(lines)
    if crlf:
        result = result.replace("\n", "\r\n")
    open(path, "w", encoding="utf-8", newline="").write(result)
    return len(inserts)


def main():
    project = assemble.PROJECT
    src = assemble.SRC
    app_dir = assemble.OUT
    total = 0
    report = []
    for filename in sorted(os.listdir(src)):
        if not filename.endswith(".pyc"):
            continue
        module = filename[:-4]
        rel = "__init__.py" if module == "app" else module[4:] + ".py"
        path = os.path.join(app_dir, rel)
        if not os.path.exists(path):
            continue
        code = load_module(os.path.join(src, filename))[3]
        scaffold = assemble.stub_source(code)
        if scaffold is None:
            report.append((rel, "-", "scaffold-failed"))
            continue
        total += patch(path, scaffold_defaults(scaffold), report)
    for row in report:
        print("  ".join(row))
    print("defaults inserted:", total)


if __name__ == "__main__":
    main()