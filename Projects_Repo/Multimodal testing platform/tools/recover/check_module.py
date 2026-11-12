"""Diff one recovered module against its original 3.8 bytecode, function by function.

Usage:
    python tools/recover/check_module.py app.config
    python tools/recover/check_module.py app.config --fn normalize_config -v
"""
import difflib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import verify_bytecode as V

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def pair(module, qual, verbose=0):
    pyc = V.load_pyc(os.path.join(V.SRC, module + ".pyc"))
    rel = "__init__.py" if module == "app" else module[4:] + ".py"
    src = os.path.join(V.APP, rel)
    with open(src, encoding="utf-8") as fh:
        text = fh.read()
    new = compile(text, src, "exec", dont_inherit=True)
    a = dict(V.walk(pyc))
    b = dict(V.walk(new))
    if qual not in a or qual not in b:
        print(f"{qual}: missing (orig={qual in a}, new={qual in b})")
        return
    x, y = V.normalize(a[qual]), V.normalize(b[qual])
    score = V.ratio(x, y)
    print(f"{qual}: orig={len(x)} new={len(y)} score={score:.4f}")
    if verbose:
        shown = 0
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                None, x, y, autojunk=False).get_opcodes():
            if tag == "equal":
                continue
            print(f"  {tag} orig[{i1}:{i2}]={x[i1:i2]}")
            print(f"       new [{j1}:{j2}]={y[j1:j2]}")
            shown += 1
            if shown >= verbose:
                break


def main():
    module = sys.argv[1]
    verbose = 3
    only = None
    args = sys.argv[2:]
    for i, arg in enumerate(args):
        if arg == "-v":
            verbose = 20
        elif arg == "--fn" and i + 1 < len(args):
            only = args[i + 1]
    pyc = V.load_pyc(os.path.join(V.SRC, module + ".pyc"))
    for name, _ in V.walk(pyc):
        if only and only not in name:
            continue
        pair(module, name, verbose)


if __name__ == "__main__":
    main()