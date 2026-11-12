"""Assemble maintainable sources from Python 3.8 bytecode.

Module/class scaffolds are deparsed with nested code objects replaced by
signature-preserving stubs, then each real function body is spliced back in by
walking the original code-object tree.  Imports, decorators and class
membership therefore follow the bytecode exactly.
"""
from __future__ import annotations

import ast
import contextlib
import re
import io
import json
import os
import sys
import textwrap

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.environ.get("DECOMP_DIR", r"E:\OpenCode Work\decomp"))

from xdis import load_module
from xdis.codetype.code38 import Code38
import decompyle3.main as d3
import uncompyle6.main as u6

PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(PROJECT, "_src", "_pyc")
OUT = os.path.join(PROJECT, "app")
MANUAL = os.path.join(os.path.dirname(__file__), "manual")
HEADER_LINES = ("# decompyle3", "# Python bytecode", "# Decompiled", "# uncompyle6",
                "# Embedded file", "# pydisasm")


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


def is_class_body(code):
    """Class bodies are the only code objects without CO_OPTIMIZED (0x01)."""
    return not (code.co_flags & 0x01) and not code.co_name.startswith("<")


def stub(child):
    """Same signature, empty body; class bodies keep their members stubbed."""
    if child.co_name.startswith("<"):
        return child
    if is_class_body(child):
        return clone(child, co_consts=tuple(
            stub(c) if hasattr(c, "co_code") else c for c in child.co_consts))
    n = child.co_argcount + child.co_kwonlyargcount
    return clone(child, co_nlocals=max(n, len(child.co_varnames) if child.co_varnames else n),
                 co_stacksize=1, co_flags=child.co_flags & 0x03,
                 co_code=bytes([100, 0, 83, 0]), co_consts=(None,), co_names=(),
                 co_varnames=child.co_varnames, co_lnotab=b"",
                 co_freevars=(), co_cellvars=())


def wrap(child, name):
    code = bytes([100, 0, 100, 1, 132, 0, 90, 0, 100, 2, 83, 0])
    return Code38(co_argcount=0, co_posonlyargcount=0, co_kwonlyargcount=0,
                  co_nlocals=0, co_stacksize=3, co_flags=0x40, co_code=code,
                  co_consts=(child, name, None), co_names=(name,),
                  co_varnames=(), co_filename=child.co_filename, co_name="<module>",
                  co_firstlineno=1, co_lnotab=b"", co_freevars=(), co_cellvars=())


def _clean(text):
    return "\n".join(l for l in text.splitlines() if not l.startswith(HEADER_LINES))


def deparse(code, emit_def=False):
    target = wrap(code, code.co_name) if emit_def else code
    for mod in (d3, u6):
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                mod.decompile(target, bytecode_version=(3, 8), out=buf)
            return _clean(buf.getvalue()).strip("\n")
        except Exception:
            continue
    return None


def children(code):
    return [c for c in code.co_consts if hasattr(c, "co_code")]


def stub_source(code):
    return deparse(clone(code, co_consts=tuple(
        stub(c) if hasattr(c, "co_code") else c for c in code.co_consts)))


def indent(text, spaces=4):
    pad = " " * spaces
    return "\n".join((pad + line) if line.strip() else "" for line in text.splitlines())


def manual_fragment(module, qualname):
    """Hand-written implementations live in manual/<module>.<QualName>.py."""
    candidates = [f"{module}.{qualname}.py"]
    short = qualname.split(".")[-1]
    candidates.append(f"{module}.{short}.py")
    for name in candidates:
        path = os.path.join(MANUAL, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return fh.read().rstrip("\n")
    return None



def arg_defaults(node, source):
    """Ordered (name, default-source) pairs for a scaffold function signature.

    Defaults are stored in the PARENT code object in Python 3.8, so the
    scaffold (deparsed module/class body) still sees them while a function
    deparsed on its own does not.  Copy the text across instead of guessing
    values, which keeps non-literal defaults byte-identical.
    """
    args = node.args
    if not args.defaults:
        return []
    names = args.args[len(args.args) - len(args.defaults):]
    out = []
    for arg, default in zip(names, args.defaults):
        piece = ast.get_source_segment(source, default)
        if piece:
            out.append((arg.arg, piece))
    return out if len(out) == len(args.defaults) else []


def apply_arg_defaults(text, defaults=None, skipped=None):
    """Re-attach defaults to a function deparsed from its own code object."""
    if not defaults:
        return text
    tree = ast.parse(text)
    fn = next((n for n in tree.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    if fn is None:
        return text
    positional = [a.arg for a in fn.args.args]
    names = [name for name, _ in defaults]
    if positional[-len(names):] != names:
        if skipped is not None:
            skipped.append(fn.name + ":signature-mismatch")
        return text
    inserts = []
    for arg, (name, piece) in zip(fn.args.args[-len(names):], defaults):
        inserts.append((arg.end_lineno, arg.end_col_offset, "=" + piece))
    lines = text.splitlines(keepends=True)
    for lineno, col, piece in sorted(inserts, key=lambda i: (i[0], i[1]), reverse=True):
        line = lines[lineno - 1]
        lines[lineno - 1] = line[:col] + piece + line[col:]
    return "".join(lines)


ARTIFACT_LOOP = "while True:"


def repair(text):
    """Fix decompiler artifacts that would change behaviour.

    * `except X: continue` is emitted as `while True: pass` followed by a
      mis-indented `else:` block; restoring `continue` keeps the loop going,
      which is what the original bytecode does.
    * 3.8 slices are emitted as `x[None[:n]]`.
    """
    lines = text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == ARTIFACT_LOOP and i + 1 < len(lines) and lines[i + 1].strip() == "pass":
            out.append(line[:len(line) - len(line.lstrip())] + "continue")
            i += 2
            continue
        out.append(line)
        i += 1
    text = "\n".join(out)
    # 3.8 BUILD_SLICE is emitted as a subscript of a slice object:
    #   x[None[:n]]        -> x[:n]
    #   x[None[:None]]     -> x[:]
    #   x[(-6)[:None]]     -> x[-6:]
    text = re.sub(r"\[None\[:(\d*)\]\]", lambda m: "[:%s]" % m.group(1), text)
    text = re.sub(r"\[\((-?\d+)\)\[:None\]\]", lambda m: "[%s:]" % m.group(1), text)
    text = text.replace("[None[:None]]", "[:]")
    return text


class Assembler:
    def __init__(self, module="app"):
        self.module = module
        self.failures = []
        self.manual = []
        self.missing = []
        self.defaults_skipped = []

    def function(self, code, decorators=(), qualname=None, defaults=None):
        qualname = qualname or code.co_name
        # A curated implementation in tools/recover/manual/ always wins: it is the
        # only place that can fix decompiler artefacts that parse but mean
        # something else (mis-nested try/except, inverted colour tests, ...).
        text = manual_fragment(self.module, qualname)
        if text is not None:
            self.manual.append(qualname)
        else:
            text = deparse(code, emit_def=True)
            if text is None:
                self.missing.append(qualname)
                text = (f"def {code.co_name}(*args, **kwargs):\n"
                        f'    """TODO(recovery): original body could not be deparsed."""\n'
                        f"    raise NotImplementedError({code.co_name!r})")
        text = repair(text)
        # Only deparsed bodies lost their defaults; curated fragments in
        # tools/recover/manual/ already spell the signature they need.
        if defaults and manual_fragment(self.module, qualname) is None:
            text = apply_arg_defaults(text, defaults, self.defaults_skipped)
        lines = text.splitlines()
        # the outer decorator list lives in the parent code object, not in the
        # function body; drop any decorator lines the deparser re-emitted
        while lines and lines[0].lstrip().startswith("@"):
            lines.pop(0)
        if decorators:
            lines = list(decorators) + lines
        return "\n".join(lines)

    def splice(self, source, code, prefix=""):
        tree = ast.parse(source)
        kids = {c.co_name: c for c in children(code)}
        lines = source.splitlines()
        out = []
        cursor = 0
        for node in tree.body:
            start, end = node.lineno - 1, node.end_lineno
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in kids:
                out.extend(lines[cursor:start])
                decorators = ["@" + ast.unparse(d) for d in node.decorator_list]
                out.append(self.function(kids[node.name], decorators,
                                         qualname=(prefix + node.name),
                                         defaults=arg_defaults(node, source)))
                cursor = end
            elif isinstance(node, ast.ClassDef) and node.name in kids:
                out.extend(lines[cursor:start])
                head_end = start
                for idx in range(start, end):
                    if lines[idx].rstrip().endswith(":"):
                        head_end = idx
                        break
                header = lines[start:head_end + 1]
                body_src = textwrap.dedent("\n".join(lines[head_end + 1:end]))
                cleaned = [l for l in body_src.splitlines()
                           if not l.strip().startswith(("__module__ =", "__qualname__ =", "__doc__ ="))]
                body_src = textwrap.dedent("\n".join(cleaned)).strip("\n")
                inner = self.splice(body_src + "\n", kids[node.name],
                                    prefix=(prefix + node.name + ".")) if body_src else ""
                doc = None
                consts = kids[node.name].co_consts
                if consts and isinstance(consts[0], str) and consts[0].strip():
                    doc = consts[0]
                pieces = []
                if doc and '"""' not in doc:
                    pieces.append('"""' + doc.rstrip() + '"""')
                if inner.strip():
                    pieces.append(inner.rstrip())
                block = "\n".join(header) + "\n" + indent("\n\n".join(pieces) if pieces else "pass")
                out.append(block)
                cursor = end
        out.extend(lines[cursor:])
        return "\n".join(out)

    def module_body(self, code):
        scaffold = stub_source(code)
        if scaffold is None:
            self.failures.append(code.co_filename)
            return ("# TODO(recovery): module scaffold could not be deparsed.\n"
                    "# Original bytecode preserved in _src/_pyc.\n")
        try:
            text = self.splice(scaffold, code)
        except SyntaxError as exc:
            self.failures.append(f"{code.co_filename}: {exc}")
            return scaffold + "\n"
        return repair(text).strip("\n") + "\n"


def extra_manual_fragments(module, code):
    """字节码里不存在、但手工新增到 manual/ 的顶层函数。

    装配只按原始 code object 逐函数还原，手工新增的辅助函数不会出现在
    任何 code object 里，重跑装配就会被悄悄丢掉，运行时表现为 NameError。
    命名约定：manual/<module>.<新函数名>.py（只有一层点，类方法不参与）。
    """
    if not os.path.isdir(MANUAL):
        return []
    existing = {c.co_name for c in children(code)}
    prefix = module + "."
    extras = []
    for filename in sorted(os.listdir(MANUAL)):
        if not filename.startswith(prefix) or not filename.endswith(".py"):
            continue
        rest = filename[len(prefix):-3]
        if not rest or "." in rest or rest in existing:
            continue
        extras.append((rest, io.open(os.path.join(MANUAL, filename), encoding="utf-8").read()))
    return extras


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(MANUAL, exist_ok=True)
    for filename in sorted(os.listdir(SRC)):
        if not filename.endswith(".pyc"):
            continue
        module = filename[:-4]
        code = load_module(os.path.join(SRC, filename))[3]
        asm = Assembler(filename[:-4])
        text = asm.module_body(code)
        extras = extra_manual_fragments(module, code)
        if extras:
            blocks = [body.rstrip("\n") for _, body in extras]
            text = text.rstrip("\n") + "\n\n\n" + "\n\n\n".join(blocks) + "\n"
            print(f"{module}: appended manual-only functions", [name for name, _ in extras])
        target = os.path.join(OUT, "__init__.py") if module == "app" else os.path.join(OUT, module[4:] + ".py")
        # 显式 LF：Windows 默认换行是 CRLF，会把整个 app/ 变成「全文件重写」，
        # 让真正的逻辑改动淹没在噪声里，也违反仓库 UTF-8 无 BOM + LF 约定。
        with open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"{os.path.relpath(target, PROJECT):24s} {len(text.splitlines()):5d} lines")
    print("manual fragments used:", sorted(set(asm.manual)))
    print("missing functions:", sorted(set(asm.missing)))
    print("defaults not restored:", sorted(set(asm.defaults_skipped)))


if __name__ == "__main__":
    main()
