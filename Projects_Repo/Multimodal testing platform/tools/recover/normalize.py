"""Bytecode pre-normalisation for the 3.8 decompilers.

Two transformations let decompyle3/uncompyle6 parse constructs they otherwise
reject:

* `except X: continue` - the deparsers emit a bogus `while True: pass` and then
  mis-indent the rest of the function.  Both JUMP_ABSOLUTE and JUMP_FORWARD are
  2-byte opcodes, so the jump can be rewritten in place without moving any
  offset; the original `continue` is restored in the emitted source.
* a body that starts with `try:` - the 3.8 grammar has no rule for
  SETUP_FINALLY at offset 0.  A no-op pair (LOAD_CONST None / POP_TOP) is
  prepended and every absolute jump is re-targeted.
"""
import dis
import types

from xdis.codetype.code38 import Code38
from xdis.op_imports import get_opcode_module
from xdis.bytecode import Bytecode

_OPC = get_opcode_module((3, 8))
OPMAP = _OPC.opmap

ABS_JUMPS = {
    "JUMP_ABSOLUTE", "POP_JUMP_IF_TRUE", "POP_JUMP_IF_FALSE", "SETUP_FINALLY",
    "SETUP_WITH", "SETUP_ASYNC_WITH", "FOR_ITER", "JUMP_IF_TRUE_OR_POP",
    "JUMP_IF_FALSE_OR_POP", "POP_JUMP_IF_NONE", "POP_JUMP_IF_NOT_NONE",
    "JUMP_IF_NOT_EXC_MATCH", "JUMP_FORWARD",
}


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


def instructions(code):
    return list(Bytecode(code, _OPC).get_instructions(code))


def continue_sites(code):
    """Byte offsets of `JUMP_ABSOLUTE <enclosing FOR_ITER>` right after POP_EXCEPT."""
    ins = instructions(code)
    off2idx = {i.offset: n for n, i in enumerate(ins)}
    sites = []
    for n, item in enumerate(ins):
        if item.opname != "POP_EXCEPT" or n + 1 >= len(ins):
            continue
        nxt = ins[n + 1]
        if nxt.opname != "JUMP_ABSOLUTE":
            continue
        target = ins[off2idx[nxt.argval]] if nxt.argval in off2idx else None
        if target is not None and target.opname == "FOR_ITER":
            sites.append(nxt.offset)
    return sites


def neutralize(code):
    """Return (code_with_continue_turned_into_break, n_sites)."""
    sites = continue_sites(code)
    if not sites:
        return code, 0
    raw = bytearray(code.co_code)
    jump_forward = OPMAP["JUMP_FORWARD"]
    for offset in sites:
        raw[offset] = jump_forward
        raw[offset + 1] = 0
    return clone(code, co_code=bytes(raw)), len(sites)


def neutralize_tree(code):
    """Neutralize `continue` in this code object and every nested one."""
    total = 0
    consts = []
    for const in code.co_consts:
        if isinstance(const, types.CodeType) or hasattr(const, "co_code"):
            new, n = neutralize_tree(const)
            consts.append(new)
            total += n
        else:
            consts.append(const)
    new, n = neutralize(code)
    total += n
    return clone(new, co_consts=tuple(consts)), total


def _encode(opname, arg):
    op = OPMAP[opname]
    if arg is None:
        # 3.8 is wordcode: every instruction occupies two bytes
        return bytes([op, 0])
    value = int(arg)
    out = bytearray()
    chunks = []
    while value > 0xFF:
        chunks.append(value & 0xFF)
        value >>= 8
    for chunk in reversed(chunks):
        out.append(OPMAP["EXTENDED_ARG"])
        out.append(chunk)
    out.append(op)
    out.append(value & 0xFF)
    return bytes(out)


def insert_prefix(code):
    """Prepend two no-ops so a body starting with `try:` does not start at offset 0.

    decompyle3's 3.8 grammar has no rule for SETUP_FINALLY at offset 0.  In 3.8
    every jump argument is *relative* to the following instruction, so inserting
    bytes before the body leaves all jump arguments valid; only absolute line
    offsets are dropped (co_lnotab cleared).
    """
    all_ins = [i for i in instructions(code) if i.opname != "EXTENDED_ARG"]
    if not all_ins or all_ins[0].opname != "SETUP_FINALLY":
        return code, False
    # NOP is a genuine no-op statement token for the deparser; two of them keep
    # the prefix an even number of bytes (3.8 is wordcode)
    prefix = _encode("NOP", None) * 2
    # keep the original line table, shifted so the synthetic statement sits on
    # the function's first line and the real body keeps its original lines
    lnotab = bytes([len(prefix), 0]) + bytes(code.co_lnotab)
    return clone(code, co_code=prefix + code.co_code, co_lnotab=lnotab), True
