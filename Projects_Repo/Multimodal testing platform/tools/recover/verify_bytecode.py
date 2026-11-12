"""Compare a source tree against the original 3.8 bytecode, function by function.

Reports exact matches (instruction stream identical after jump-target
normalisation) and semantic drift.  Used to prove that reconstructed functions
behave like the shipped binary, instead of trusting the decompiler output.
"""
from __future__ import annotations

import dis
import json
import marshal
import os
import sys
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(PROJECT, "_src", "_pyc")
APP = os.path.join(PROJECT, "app")

JUMPS = {"JUMP_ABSOLUTE", "JUMP_FORWARD", "POP_JUMP_IF_TRUE", "POP_JUMP_IF_FALSE",
         "JUMP_IF_TRUE_OR_POP", "JUMP_IF_FALSE_OR_POP", "SETUP_FINALLY", "FOR_ITER",
         "SETUP_WITH", "POP_JUMP_IF_NONE", "POP_JUMP_IF_NOT_NONE", "JUMP_IF_NOT_EXC_MATCH",
         "SETUP_ASYNC_WITH", "SETUP_LOOP", "BREAK_LOOP", "CONTINUE_LOOP"}


def load_pyc(path):
    with open(path, "rb") as fh:
        return marshal.loads(fh.read()[16:])


def walk(code, path=""):
    name = f"{path}/{code.co_name}" if path else code.co_name
    yield name, code
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            yield from walk(const, name)


def normalize(code):
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


def ratio(a, b):
    n, m = len(a), len(b)
    if not n and not m:
        return 1.0
    prev = [0] * (m + 1)
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        ai = a[i - 1]
        for j in range(1, m + 1):
            cur[j] = prev[j - 1] + 1 if ai == b[j - 1] else max(cur[j - 1], prev[j])
        prev = cur
    return prev[m] / max(n, m)


def compare_module(name):
    pyc = os.path.join(SRC, name + ".pyc")
    rel = "__init__.py" if name == "app" else name[4:] + ".py"
    src = os.path.join(APP, rel)
    if not os.path.exists(src):
        return {"module": name, "status": "MISSING_SOURCE", "functions": []}
    with open(src, encoding="utf-8") as fh:
        text = fh.read()
    try:
        new = compile(text, pyc, "exec", dont_inherit=True)
    except SyntaxError as exc:
        return {"module": name, "status": f"SYNTAX:{exc.lineno}:{exc.msg}", "functions": []}
    original = dict(walk(load_pyc(pyc)))
    built = dict(walk(new))
    rows = []
    for key, code in original.items():
        if key not in built:
            rows.append({"fn": key, "score": 0.0, "status": "missing"})
            continue
        score = ratio(normalize(code), normalize(built[key]))
        status = "exact" if (score == 1.0 and code.co_code == built[key].co_code
                             and code.co_names == built[key].co_names
                             and code.co_varnames == built[key].co_varnames) else (
            "near" if score >= 0.98 else "diff")
        rows.append({"fn": key, "score": round(score, 4), "status": status})
    return {"module": name, "status": "OK", "functions": rows}


def main(argv):
    targets = argv[1:] or sorted(f[:-4] for f in os.listdir(SRC) if f.endswith(".pyc"))
    report = [compare_module(t) for t in targets]
    totals = {"exact": 0, "near": 0, "diff": 0, "missing": 0}
    for entry in report:
        rows = entry["functions"]
        counts = {k: sum(1 for r in rows if r["status"] == k) for k in totals}
        for k, v in counts.items():
            totals[k] += v
        print(f"{entry['module']:22s} {entry['status']:10s} "
              f"exact={counts['exact']:3d} near={counts['near']:3d} "
              f"diff={counts['diff']:3d} missing={counts['missing']:3d}")
        for row in rows:
            if row["status"] in ("diff", "missing"):
                print(f"    {row['status']:8s} {row['fn']:44s} {row['score']:.3f}")
    total = sum(totals.values())
    print(f"\nTOTAL {total} functions | exact {totals['exact']} | near {totals['near']} "
          f"| diff {totals['diff']} | missing {totals['missing']}")
    dest = os.path.join(os.path.dirname(__file__), "bytecode_match.json")
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"totals": totals, "modules": report}, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv)
