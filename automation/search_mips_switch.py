"""Recover local SOTN jump tables from archived assembly, without executing it.

This implementation is derived from SOTN's generated assembly and the IDT
R30xx instruction semantics. It does not read a runtime image, guess indirect
targets, or import another recompiler. The renderer owns ABI and path semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping, Sequence

_SYMBOL = r"[A-Za-z_][A-Za-z0-9_]*"
_LOCAL = r"\.L[A-Za-z0-9_.$]*"
_GPRS = ("zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
         "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
         "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
         "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra")
_SCRATCH = frozenset(_GPRS[1:16] + _GPRS[24:26])
_CONTROL = frozenset({"b", "beq", "bne", "beqz", "bnez", "bltz", "bgez", "bgtz", "blez",
                      "j", "jr", "jal", "jalr", "bal", "bltzal", "bgezal", "bc0f", "bc0t",
                      "bc1f", "bc1t", "bc2f", "bc2t", "bc3f", "bc3t"})


def register_name(text: str) -> str:
    value = text.strip().lower().removeprefix("$")
    number = value.removeprefix("r")
    if number.isdecimal() and 0 <= int(number) < len(_GPRS):
        return _GPRS[int(number)]
    return value


@dataclass(frozen=True)
class SwitchDispatch:
    """A proved branch and its exact ordered local case destinations."""

    branch: int
    selector: str
    default_label: str
    targets: tuple[str, ...]
    jump: int
    address_register: str
    target_register: str


def split_local_tables(text: str, strip_comment) -> tuple[str, dict[str, tuple[str | None, ...]]]:
    """Separate complete read-only tables from one generated function.

    Plain instruction fixtures retain the existing parser behavior. For a
    sectioned function with tables, every data line must be accounted for.
    The table and text stay in the same archived artifact and namespace.
    """
    lines = [strip_comment(line).strip() for line in text.splitlines()]
    if ".section .rodata" not in lines:
        return text, {}
    tables: dict[str, tuple[str | None, ...]] = {}
    code: list[str] = []
    section = None
    active = None
    targets: list[str | None] = []
    function = None
    ended = False
    for line in lines:
        if not line:
            continue
        if re.fullmatch(r"\.set\s+(?:noat|noreorder|nomacro)", line):
            continue
        if line == ".section .rodata" and section is None:
            section = "rodata"
            continue
        if line == ".section .text" and section == "rodata" and active is None:
            section = "text"
            continue
        if section == "rodata":
            if re.fullmatch(r"\.align\s+[23]", line) and active is None:
                continue
            label = re.fullmatch(r"glabel\s+(" + _SYMBOL + ")", line)
            if label and active is None:
                active = label[1]
                if active in tables:
                    raise ValueError("duplicate jump table")
                targets = []
                continue
            word = re.fullmatch(r"\.word\s+(" + _LOCAL + r"|0|0[xX]0+)", line)
            if word and active is not None:
                targets.append(word[1] if word[1].startswith(".L") else None)
                # The renderer admits at most 64 instructions; larger tables
                # are outside this implementation's existing path budget.
                if len(targets) > 64:
                    raise ValueError("table exceeds renderer bound")
                continue
            if active and re.fullmatch(
                    r"\.size\s+" + re.escape(active) + r",\s*\.\s*-\s*" + re.escape(active), line):
                if not targets:
                    raise ValueError("empty jump table")
                tables[active] = tuple(targets)
                active = None
                continue
            raise ValueError("unaccounted read-only data")
        if section == "text" and not ended:
            label = re.fullmatch(r"glabel\s+(" + _SYMBOL + ")", line)
            if label and function is None:
                function = label[1]
                continue
            if function and re.fullmatch(
                    r"\.size\s+" + re.escape(function) + r",\s*\.\s*-\s*" + re.escape(function), line):
                ended = True
                continue
            if function is None or line.startswith("glabel") or line.startswith(".section"):
                raise ValueError("not a single function")
            code.append(line)
            continue
        raise ValueError("unexpected assembly section or trailing definition")
    if section != "text" or active is not None or not function or not ended or not tables:
        raise ValueError("incomplete local table function")
    return "\n".join(code), tables


def recover_dispatches(instructions: Sequence, tables: Mapping[str, tuple[str | None, ...]]) -> dict[int, SwitchDispatch]:
    """Prove the guard/scale/load/jump form emitted in local US assembly.

    The shift executes in the guard's delay slot. LUI and LW use the same
    symbolic table, with ADDU adding the scaled selector between them. A NOP
    makes the loaded target available before JR, whose own slot is inert.
    Anything outside this form remains the renderer's ordinary refusal.
    """
    if not tables:
        return {}
    labels = {}
    for index, item in enumerate(instructions):
        if item.label:
            if item.label in labels:
                raise ValueError("duplicate code label")
            labels[item.label] = index
    slots = {i + 1 for i, item in enumerate(instructions) if item.mnemonic in _CONTROL}
    recovered = {}
    used_tables = set()

    def parts(item):
        return tuple(x.strip() for x in item.operands.split(",")) if item.operands else ()

    for start in range(len(instructions) - 8):
        chunk = instructions[start:start + 9]
        if tuple(x.mnemonic for x in chunk) != (
                "sltiu", chunk[1].mnemonic, "sll", "lui", "addu", "lw", "nop", "jr", "nop"):
            continue
        bound, branch, shift, upper, add, load, gap, jump, slot = map(parts, chunk)
        if len(bound) != 3 or len(shift) != 3 or len(upper) != 2 or len(add) != 3 or len(load) != 2:
            continue
        predicate, selector = map(register_name, bound[:2])
        if predicate not in _SCRATCH or selector not in _SCRATCH or predicate == selector:
            continue
        if chunk[1].mnemonic == "beqz" and len(branch) == 2:
            condition = register_name(branch[0]) == predicate
        elif chunk[1].mnemonic == "beq" and len(branch) == 3:
            condition = {register_name(x) for x in branch[:2]} == {predicate, "zero"}
        else:
            continue
        if not condition or not re.fullmatch(r"(?:0[xX][0-9A-Fa-f]+|[1-9][0-9]*)", bound[2]):
            continue
        count = int(bound[2], 0)
        scaled, shifted = map(register_name, shift[:2])
        if scaled not in _SCRATCH or shifted != selector or shift[2] not in {"2", "0x2"}:
            continue
        address = register_name(upper[0])
        hi = re.fullmatch(r"%hi\((" + _SYMBOL + ")\)", upper[1])
        lo = re.fullmatch(r"%lo\((" + _SYMBOL + ")\)\(([^()]+)\)", load[1])
        if not hi or not lo or hi[1] != lo[1] or hi[1] not in tables:
            continue
        target_register = register_name(load[0])
        if (address not in _SCRATCH or address == scaled
                or target_register not in _SCRATCH or register_name(lo[2]) != address
                or register_name(add[0]) != address
                or {register_name(x) for x in add[1:]} != {address, scaled}
                or tuple(map(register_name, jump)) != (target_register,)
                or gap or slot):
            continue
        entries = tables[hi[1]]
        # SOTN's disassembler can include one zero word after an odd-sized
        # table. The guard must exclude it; zero is never a code target.
        padding = entries[count:]
        targets = entries[:count]
        if (count <= 0 or len(targets) != count or any(target is None for target in targets)
                or padding and not (count % 2 == 1 and padding == (None,))):
            continue
        # No label may admit a path that bypasses the predicate or reaches
        # partially computed table state. This also rejects labelled slots.
        if start in slots or any(item.label for item in chunk[1:]):
            continue
        destinations = (*targets, branch[-1])
        if any(label not in labels or labels[label] <= start + 8 or labels[label] in slots
               for label in destinations):
            continue
        # Only the table relocation operands may have triggered the ordinary
        # parser's unsupported flag.
        if any(item.unsupported for i, item in enumerate(chunk) if i not in {3, 5}):
            continue
        recovered[start + 1] = SwitchDispatch(
            start + 1, selector, branch[-1], targets, start + 7, address, target_register)
        used_tables.add(hi[1])
    if used_tables != set(tables):
        raise ValueError("unproved or unused table")
    return recovered
