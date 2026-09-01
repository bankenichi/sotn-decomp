"""Canonical architecture-neutral assembly selectors for indexed search.

The donor scanner and target renderer consume different assembly parsers, but
their semantic selectors must be byte-identical.  This module owns the shared
normalization and the instruction, CFG, and dataflow signature protocols.

Assembler directives, relocation expressions, and numeric branch targets are
placement-dependent evidence.  They are represented as unsupported parser
records when a parser needs to retain its line position, then omitted here.
Omitting only those records lets safe instructions from the same function and
the same platform survive.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

try:  # package imports
    from .search_types import hash_canonical
except ImportError:  # direct invocation from the automation directory
    from search_types import hash_canonical  # type: ignore


SEMANTIC_SIGNATURE_PROTOCOL = "sotn-search-semantic-signature-v1"


@dataclass(frozen=True)
class SemanticInstruction:
    """One parser instruction at the shared semantic boundary."""

    mnemonic: str
    operands: str = ""
    unsupported: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.mnemonic, str) or not self.mnemonic.strip():
            raise ValueError("semantic instruction mnemonic must be nonempty text")
        if not isinstance(self.operands, str):
            raise ValueError("semantic instruction operands must be text")
        if not isinstance(self.unsupported, bool):
            raise ValueError("semantic instruction unsupported must be boolean")


@dataclass(frozen=True)
class SemanticClassification:
    """Exact role classification used by CFG and dataflow selectors."""

    branch: bool
    call: bool
    load: bool
    store: bool
    is_return: bool


_REGISTER = re.compile(
    r"(?:\$[0-9]{1,2}|\$(?:zero|at|v[01]|a[0-3]|t[0-9]|s[0-7]|k[01]|gp|sp|fp|ra)|"
    r"(?:r(?:[0-9]{1,2}|zero|at|v[01]|a[0-3]|t[0-9]|s[0-7]|k[01]|gp|sp|fp|ra)|"
    r"[vastr][0-9]{1,2}|a[0-3]|v[01]|t[0-9]|s[0-9]|sp|fp|lr|pc|ip|cpsr|apsr))",
    re.IGNORECASE,
)
_REGISTER_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_$])(?:\$[0-9]{1,2}|\$(?:zero|at|v[01]|a[0-3]|t[0-9]|s[0-7]|k[01]|gp|sp|fp|ra)|"
    r"(?:r(?:[0-9]{1,2}|zero|at|v[01]|a[0-3]|t[0-9]|s[0-7]|k[01]|gp|sp|fp|ra)|"
    r"[vastr][0-9]{1,2}|a[0-3]|v[01]|t[0-9]|s[0-9]|sp|fp|lr|pc|ip|cpsr|apsr))"
    r"(?![A-Za-z0-9_$])",
    re.IGNORECASE,
)
_NUMBER = re.compile(
    r"(?<![A-Za-z_])(?:[+#]?(?:-?0[xX][0-9A-Fa-f]+|-?[0-9]+))(?![A-Za-z_])"
)
_FULL_NUMBER = re.compile(r"^[+#]?(?:-?0[xX][0-9A-Fa-f]+|-?[0-9]+)$", re.IGNORECASE)
_OPERAND_SYMBOL = re.compile(r"[.$A-Za-z_]\w*")
_RELOCATION = re.compile(
    r"(?:\.reloc\b|%hi\b|%lo\b|%higher\b|%highest\b|@(?:ha|l|h)\b|"
    r"R_(?:MIPS|SH|ARM)|\b(?:HI16|LO16|REL(?:32|24)?)\b)",
    re.IGNORECASE,
)
_MEMORY_OFFSET = re.compile(
    r"^[+-]?(?:0[xX][0-9A-Fa-f]+|[0-9]+)?\([^()]*\)$", re.IGNORECASE
)
_RETURN_MNEMONICS = frozenset({"jr", "rts", "ret", "rte"})
_CALL_MNEMONICS = frozenset(
    {
        "jal",
        "jalr",
        "bl",
        "blx",
        "blr",
        "bal",
        "bgezal",
        "bltzal",
        "bsr",
        "bsrf",
        "call",
        "jsr",
        "bctrl",
    }
)
_LOAD_MNEMONICS = frozenset(
    {
        # MIPS and common pseudo/instruction-set variants.
        "lb",
        "lbu",
        "lh",
        "lhu",
        "lw",
        "lwl",
        "lwr",
        "ld",
        "ldl",
        "ldr",
        "lwc1",
        "ldc1",
        "lq",
        # ARM/AArch load forms.
        "ldrb",
        "ldrh",
        "ldrsb",
        "ldrsh",
        "ldrsw",
        "ldp",
        "ldur",
        "ldurb",
        "ldurh",
        "ldursb",
        "ldursh",
        "ldursw",
        "vldr",
        "ldrex",
        "ldrexb",
        "ldrexh",
        "ldrexd",
        # SH load pseudo-forms whose mnemonic is unambiguous.
        "movua",
        "movub",
        "movuw",
        "movli",
    }
)
_STORE_MNEMONICS = frozenset(
    {
        # MIPS and common pseudo/instruction-set variants.
        "sb",
        "sh",
        "sw",
        "sdl",
        "sdr",
        "sc",
        "scd",
        "swc1",
        "sdc1",
        # ARM/AArch store forms.
        "str",
        "strb",
        "strh",
        "stp",
        "stur",
        "sturb",
        "sturh",
        "vstr",
        "strex",
        "strexb",
        "strexh",
        "strexd",
    }
)
_SH_MOVES = frozenset({"mov", "mov.b", "mov.w", "mov.l", "mov.q"})
_BRANCHES = frozenset(
    {
        # MIPS.
        "b",
        "beq",
        "bne",
        "beqz",
        "bnez",
        "blez",
        "bgtz",
        "bltz",
        "bgez",
        "bc1f",
        "bc1t",
        "j",
        "jr",
        "jal",
        "jalr",
        "bl",
        "bal",
        "bgezal",
        "bltzal",
        # ARM/AArch and SH forms that are not covered by the patterns below.
        "bx",
        "blx",
        "cbz",
        "cbnz",
        "tbz",
        "tbnz",
        "tbb",
        "tbh",
        "bra",
        "braf",
        "bsr",
        "bsrf",
        "bt",
        "bf",
        "bts",
        "bfs",
        "jmp",
        "jsr",
        "bctrl",
        "call",
    }
)
_ARM_CONDITION = re.compile(
    r"^b(?:\.(?:eq|ne|cs|hs|cc|lo|mi|pl|vs|vc|hi|ls|ge|lt|gt|le|al|nv)|"
    r"(?:eq|ne|cs|hs|cc|lo|mi|pl|vs|vc|hi|ls|ge|lt|gt|le|al|nv))$",
    re.IGNORECASE,
)
_SH_BRANCH = re.compile(r"^(?:bt|bf)(?:/s)?$", re.IGNORECASE)
_DIRECTIVE_MNEMONICS = frozenset(
    {
        # GNU/MIPS assembler metadata and data directives.  Dotted forms are
        # also filtered by the startswith(".") guard below, but retaining their
        # bare spellings here keeps the policy explicit for parser records that
        # have already stripped the dot.
        "glabel",
        "globl",
        "global",
        "extern",
        "section",
        "subsection",
        "include",
        "incbin",
        "size",
        "type",
        "comm",
        "ent",
        "end",
        "frame",
        "mask",
        "fmask",
        "set",
        "loc",
        "word",
        "half",
        "byte",
        "dword",
        "qword",
        "long",
        "ascii",
        "asciz",
        "string",
        "fill",
        "space",
        "zero",
        "align",
        "balign",
        "p2align",
        # Saturn/SH data and section directives.
        "dc",
        "dc.b",
        "dc.w",
        "dc.l",
        "dc.q",
        "dcb",
        "dcb.b",
        "dcb.w",
        "dcb.l",
        "ds",
        "ds.b",
        "ds.w",
        "ds.l",
        "org",
        "even",
        "text",
        "data",
        "bss",
        "rodata",
    }
)


def _split_operands(operands: str) -> tuple[str, ...]:
    """Split operands without breaking ARM brackets or SH addressing."""

    if not operands.strip():
        return ()
    result: list[str] = []
    current: list[str] = []
    depth = 0
    for char in operands:
        if char in "([":
            depth += 1
        elif char in ")]" and depth:
            depth -= 1
        if char == "," and depth == 0:
            result.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    result.append("".join(current).strip())
    return tuple(item for item in result if item)


def _is_memory_operand(value: str) -> bool:
    lower = value.strip().lower()
    return bool(
        (lower.startswith("[") and lower.endswith("]"))
        or (lower.startswith("(") and lower.endswith(")"))
        or _MEMORY_OFFSET.fullmatch(lower)
        or lower.startswith("@")
        or lower.startswith("*")
    )


def normalize_operands(mnemonic: str, operands: str) -> str:
    """Return the canonical operand categories for one instruction."""

    if not isinstance(mnemonic, str) or not isinstance(operands, str):
        raise ValueError("semantic instruction fields must be text")
    normalized: list[str] = []
    for part in _split_operands(operands):
        lower = part.lower()
        if _REGISTER.fullmatch(lower):
            normalized.append("REG")
        elif _FULL_NUMBER.fullmatch(lower.lstrip("#")):
            normalized.append("IMM")
        elif _is_memory_operand(lower):
            normalized.append("MEM")
        elif lower.startswith("."):
            normalized.append("LABEL")
        elif _OPERAND_SYMBOL.fullmatch(lower):
            normalized.append("SYM")
        else:
            value = _REGISTER_TOKEN.sub("REG", lower)
            value = _NUMBER.sub("IMM", value)
            value = _OPERAND_SYMBOL.sub("SYM", value)
            normalized.append(value.replace(" ", "") or "NONE")
    return ",".join(normalized)


def is_branch_mnemonic(mnemonic: str) -> bool:
    """Return whether a mnemonic terminates a canonical CFG block."""

    value = mnemonic.strip().lower()
    return (
        value in _BRANCHES
        or _ARM_CONDITION.fullmatch(value) is not None
        or _SH_BRANCH.fullmatch(value) is not None
        or bool(re.fullmatch(r"bc[0-9]+[ft]", value))
    )


def is_return_mnemonic(mnemonic: str, operands: str = "") -> bool:
    """Return whether a mnemonic and return-register operand end a function."""

    value = mnemonic.strip().lower()
    if value in {"rts", "rte", "ret"}:
        return True
    if value == "jr":
        parts = _split_operands(operands)
        return bool(parts) and parts[-1].strip().lower() in {
            "$ra",
            "ra",
            "$31",
            "r31",
        }
    if value == "bx":
        parts = _split_operands(operands)
        return bool(parts) and parts[-1].strip().lower() in {"lr", "r14"}
    return False


def is_call_mnemonic(mnemonic: str) -> bool:
    """Return whether a mnemonic is a canonical call operation."""

    return mnemonic.strip().lower() in _CALL_MNEMONICS


def has_numeric_branch_target(mnemonic: str, operands: str) -> bool:
    """Apply the shared policy for unstable numeric branch displacements."""

    if not is_branch_mnemonic(mnemonic):
        return False
    parts = _split_operands(operands)
    if not parts:
        return False
    target = parts[-1].strip()
    if target.startswith("#"):
        target = target[1:].strip()
    return _FULL_NUMBER.fullmatch(target) is not None


def classify_instruction(mnemonic: str, operands: str = "") -> SemanticClassification:
    """Classify one usable instruction with explicit, non-prefix rules."""

    value = mnemonic.strip().lower()
    parts = _split_operands(operands)
    memory_positions = tuple(index for index, part in enumerate(parts) if _is_memory_operand(part))
    load = value in _LOAD_MNEMONICS
    store = value in _STORE_MNEMONICS
    if value in _SH_MOVES and memory_positions:
        # SH uses source,destination order for memory moves.  A memory source
        # is a load; a memory destination is a store.  If both are present,
        # retain both roles because the operation is a true memory transfer.
        load = bool(parts) and _is_memory_operand(parts[0])
        store = bool(parts) and _is_memory_operand(parts[-1])
    return SemanticClassification(
        branch=is_branch_mnemonic(value),
        call=is_call_mnemonic(value),
        load=load,
        store=store,
        is_return=is_return_mnemonic(value, operands),
    )


def _coerce_instruction(value: Any) -> SemanticInstruction:
    if isinstance(value, SemanticInstruction):
        return value
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        return SemanticInstruction(
            value[0],
            value[1],
            bool(value[2]) if len(value) > 2 else False,
        )
    mnemonic = getattr(value, "mnemonic", None)
    operands = getattr(value, "operands", None)
    if mnemonic is None or operands is None:
        raise ValueError("assembly parser returned an untyped instruction")
    return SemanticInstruction(mnemonic, operands, bool(getattr(value, "unsupported", False)))


def _usable_instructions(instructions: Iterable[Any]) -> tuple[SemanticInstruction, ...]:
    result: list[SemanticInstruction] = []
    for raw in instructions:
        instruction = _coerce_instruction(raw)
        mnemonic = instruction.mnemonic.strip().lower()
        if (
            instruction.unsupported
            or not mnemonic
            or mnemonic.startswith(".")
            or mnemonic in _DIRECTIVE_MNEMONICS
            or _RELOCATION.search(instruction.mnemonic)
            or _RELOCATION.search(instruction.operands)
            or has_numeric_branch_target(mnemonic, instruction.operands)
        ):
            continue
        result.append(SemanticInstruction(mnemonic, instruction.operands, False))
    return tuple(result)


def instruction_signature(instructions: Sequence[Any]) -> str:
    """Hash normalized instruction order after applying the refusal policy."""

    normalized = tuple(
        (
            instruction.mnemonic,
            normalize_operands(instruction.mnemonic, instruction.operands),
        )
        for instruction in _usable_instructions(instructions)
    )
    return hash_canonical(
        {
            "protocol": SEMANTIC_SIGNATURE_PROTOCOL,
            "kind": "instruction",
            "instructions": normalized,
            "assembly": True,
        }
    )


def cfg_signature(instructions: Sequence[Any]) -> str:
    """Hash canonical basic-block boundaries and fall-through successors."""

    blocks: list[dict[str, Any]] = []
    current: list[str] = []
    for instruction in _usable_instructions(instructions):
        classification = classify_instruction(instruction.mnemonic, instruction.operands)
        current.append(instruction.mnemonic)
        if classification.branch or classification.is_return:
            blocks.append(
                {
                    "instructions": tuple(current),
                    "branch": classification.branch,
                    "return": classification.is_return,
                }
            )
            current = []
    if current:
        blocks.append(
            {
                "instructions": tuple(current),
                "branch": False,
                "return": False,
            }
        )
    rows = []
    for index, block in enumerate(blocks):
        successors = (
            (index + 1,)
            if index + 1 < len(blocks) and not block["return"]
            else ()
        )
        rows.append({**block, "successors": successors})
    return hash_canonical(
        {
            "protocol": SEMANTIC_SIGNATURE_PROTOCOL,
            "kind": "cfg",
            "blocks": tuple(rows),
        }
    )


def dataflow_profile(instructions: Sequence[Any]) -> dict[str, Any]:
    """Return the typed intermediate used by the dataflow signature."""

    usable = _usable_instructions(instructions)
    mnemonics = tuple(item.mnemonic for item in usable)
    calls = tuple(
        item.mnemonic
        for item in usable
        if classify_instruction(item.mnemonic, item.operands).call
    )
    loads = sum(
        classify_instruction(item.mnemonic, item.operands).load for item in usable
    )
    stores = sum(
        classify_instruction(item.mnemonic, item.operands).store for item in usable
    )
    returns = sum(
        classify_instruction(item.mnemonic, item.operands).is_return for item in usable
    )
    # Keep this local assertion visible to type checkers and future edits: the
    # mnemonic tuple is intentionally derived even though calls is the only
    # ordered dataflow component today.
    if len(mnemonics) < len(calls):
        raise AssertionError("dataflow call count exceeds instruction count")
    return {"calls": calls, "loads": loads, "stores": stores, "returns": returns}


def dataflow_signature(instructions: Sequence[Any]) -> str:
    """Hash exact call/load/store/return roles after refusal filtering."""

    return hash_canonical(
        {
            "protocol": SEMANTIC_SIGNATURE_PROTOCOL,
            "kind": "dataflow",
            **dataflow_profile(instructions),
        }
    )


def assembly_signatures(instructions: Sequence[Any]) -> tuple[str, str, str]:
    """Return instruction, CFG, and dataflow identities in protocol order."""

    return (
        instruction_signature(instructions),
        cfg_signature(instructions),
        dataflow_signature(instructions),
    )


__all__ = [
    "SEMANTIC_SIGNATURE_PROTOCOL",
    "SemanticClassification",
    "SemanticInstruction",
    "assembly_signatures",
    "cfg_signature",
    "classify_instruction",
    "dataflow_profile",
    "dataflow_signature",
    "has_numeric_branch_target",
    "instruction_signature",
    "is_branch_mnemonic",
    "is_call_mnemonic",
    "is_return_mnemonic",
    "normalize_operands",
]
