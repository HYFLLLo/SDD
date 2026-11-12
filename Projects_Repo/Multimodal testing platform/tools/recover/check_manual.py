"""Compile a manual fragment with Python 3.8 and diff it against the original function.

Usage: python tools/recover/check_manual.py app.runner._execute app.maas.MaaSClient._chat
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
PY38 = os.environ.get("PY38", os.path.expandvars(r"%TEMP%\py38\python.exe"))

DUMP = r"""
import dis, marshal, sys, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

JUMPS = {"JUMP_ABSOLUTE", "JUMP_FORWARD", "POP_JUMP_IF_TRUE", "POP_JUMP_IF_FALSE",
         "JUMP_IF_TRUE_OR_POP", "JUMP_IF_FALSE_OR_POP", "SETUP_FINALLY", "FOR_ITER",
         "SETUP_WITH", "POP_JUMP_IF_NONE", "POP_JUMP_IF_NOT_NONE",
         "JUMP_IF_NOT_EXC_MATCH"}

def norm(code):
    ins = list(dis.get_instructions(code))
    off2idx = {i.offset: n for n, i in enumerate(ins)}
    out = []
    for i in ins:
        arg = i.argval
        if hasattr(arg, "co_code"):
            arg = "<code>"
        if i.opname in JUMPS and isinstance(arg, int) and arg in off2idx:
            arg = ("@", off2idx[arg])
        out.append((i.opname, arg))
    return out

def at(code, path):
    for part in path:
        # class bodies are not CO_OPTIMIZED; search every nested code object so
        # "MaaSClient._chat" resolves without knowing the nesting strategy
        queue = [c for c in code.co_consts if hasattr(c, "co_code")]
        found = None
        while queue:
            c = queue.pop(0)
            if c.co_name == part:
                found = c
                break
            queue.extend(x for x in c.co_consts if hasattr(x, "co_code"))
        if found is None:
            return None
        code = found
    return code

path, file = sys.argv[1], sys.argv[2]
raw = open(file, "rb").read()
code = at(marshal.loads(raw[16:]), path.split("."))
if code is None:
    raise SystemExit("function not found: " + path)
flat = [c if not hasattr(c, "co_code") else "<code>" for c in code.co_consts]
print(repr((code.co_names, code.co_varnames, flat, norm(code))))
"""


def load(path, qual):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run([PY38, "-c", DUMP, qual, path], env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode:
        raise SystemExit(proc.stdout + proc.stderr)
    return eval(proc.stdout)


def main(spec):
    parts = spec.split(".")
    module, qual = ".".join(parts[:2]), ".".join(parts[2:])
    frag = os.path.join(HERE, "manual", f"{module}.{qual}.py")
    if not os.path.exists(frag):
        raise SystemExit(f"no manual fragment: {frag}")
    orig_pyc = os.path.join(PROJECT, "_src", "_pyc", module + ".pyc")
    with tempfile.TemporaryDirectory() as tmp:
        built_pyc = os.path.join(tmp, "frag.pyc")
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        proc = subprocess.run([PY38, "-c",
                               "import py_compile,sys; py_compile.compile(sys.argv[1], cfile=sys.argv[2], doraise=True)",
                               frag, built_pyc], env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if proc.returncode:
            raise SystemExit(proc.stdout + proc.stderr)
        o_names, o_vars, o_consts, o_ops = load(orig_pyc, qual)
        # the fragment is a standalone def, so it lives at module level
        b_names, b_vars, b_consts, b_ops = load(built_pyc, qual.split(".")[-1])

    same = sum(1 for x, y in zip(o_ops, b_ops) if x == y)
    print(f"{spec}")
    print(f"  instructions: original={len(o_ops)} rebuilt={len(b_ops)} positional-match={same}")
    print(f"  names equal   : {o_names == b_names}")
    print(f"  varnames equal: {o_vars == b_vars}")
    print(f"  consts equal  : {o_consts == b_consts}")
    if o_vars != b_vars:
        print(f"    only original: {[v for v in o_vars if v not in b_vars]}")
        print(f"    only rebuilt : {[v for v in b_vars if v not in o_vars]}")
    if o_names != b_names:
        print(f"    only original: {[v for v in o_names if v not in b_names]}")
        print(f"    only rebuilt : {[v for v in b_names if v not in o_names]}")
    for i, (x, y) in enumerate(zip(o_ops, b_ops)):
        if x != y:
            print(f"  first opcode diff at #{i}: original={x} rebuilt={y}")
            break


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        main(arg)
