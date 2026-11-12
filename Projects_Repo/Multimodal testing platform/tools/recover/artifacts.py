"""Classify empty except-handlers by reading the bytecode.

An empty handler compiles to `POP_EXCEPT` followed by either
  * JUMP_ABSOLUTE <FOR_ITER>  -> the source was `continue`
  * JUMP_FORWARD <next>       -> the source was `pass`

decompyle3 renders the first form as `while True: pass` and also mis-indents
the code that follows the loop, so we repair those before/after deparsing.
"""
import re

from xdis.bytecode import Bytecode
from xdis.op_imports import get_opcode_module

_OPC = get_opcode_module((3, 8))

SKIP_AFTER_POP = {"POP_EXCEPT", "JUMP_FORWARD", "JUMP_ABSOLUTE", "END_FINALLY",
                  "POP_TOP", "BEGIN_FINALLY", "CALL_FINALLY", "POP_FINALLY"}


def classify_empty_handlers(code):
    """Return ['continue'|'pass', ...] for each empty handler, in bytecode order."""
    ins = list(Bytecode(code, _OPC).get_instructions(code))
    off2idx = {i.offset: n for n, i in enumerate(ins)}
    verdicts = []
    for n, i in enumerate(ins):
        if i.opname != "POP_EXCEPT":
            continue
        nxt = ins[n + 1] if n + 1 < len(ins) else None
        if nxt is None or nxt.opname not in ("JUMP_ABSOLUTE", "JUMP_FORWARD"):
            continue
        target = ins[off2idx[nxt.argval]] if nxt.argval in off2idx else None
        verdict = "continue" if (target is not None and target.opname == "FOR_ITER") else "pass"
        verdicts.append(verdict)
    return verdicts


def _pass_only_handlers(tree):
    """Every except-handler whose body is exactly `pass`, in source order."""
    found = []

    class V(ast.NodeVisitor):
        def visit_Try(self, node):
            for handler in node.handlers:
                body = [n for n in handler.body]
                if len(body) == 1 and isinstance(body[0], ast.Pass):
                    found.append((handler.lineno, handler.col_offset))
            self.generic_visit(node)
        visit_TryStar = visit_Try

    V().visit(tree)
    return found


def repair_continue_handlers(source, verdicts):
    """Rewrite `pass` bodies of empty handlers to `continue` where bytecode says so."""
    if not verdicts:
        return source
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    spots = _pass_only_handlers(tree)
    lines = source.splitlines()
    for (lineno, col), verdict in zip(spots, verdicts):
        if verdict != "continue":
            continue
        # handler.lineno points at the `except` line; body is the next line(s)
        idx = lineno  # 0-based index of the line after `except ...:`
        if idx < len(lines) and lines[idx].strip() == "pass":
            lines[idx] = " " * col + "continue"
    return "\n".join(lines)


def repair_slices(source):
    """decompyle3 renders `x[:n]` as `x[None[:n]]` on 3.8."""
    source = re.sub(r"\[None\[:([^\]\s]*)\]\]", lambda m: "[:%s]" % m.group(1), source)
    return source


def classify_tree(code):
    """Map code name -> list of handler verdicts for `code` and nested defs."""
    out = {code.co_name: classify_empty_handlers(code)}
    for const in code.co_consts:
        if hasattr(const, "co_code"):
            out.update(classify_tree(const))
    return out
