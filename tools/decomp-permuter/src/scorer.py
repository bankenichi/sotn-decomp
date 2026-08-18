import difflib
import hashlib
import re
from typing import Dict, List, Mapping, Optional, Sequence, Tuple
from collections import Counter

from .objdump import ArchSettings, Line, objdump, get_arch


_MAP_ADDRESS_FIRST = re.compile(
    r"^\s*(0x[0-9a-fA-F]+)\s+([A-Za-z_.$][A-Za-z0-9_.$]*)\s*(?:=|$)"
)
_MAP_SYMBOL_FIRST = re.compile(
    r"^\s*([A-Za-z_.$][A-Za-z0-9_.$]*)\s*=\s*(0x[0-9a-fA-F]+)\s*;?\s*$"
)
_SYMBOL_EXPR = re.compile(
    r"(?<![A-Za-z0-9_.$])"
    r"(?P<name>[A-Za-z_.$][A-Za-z0-9_.$]*)"
    r"(?P<offset>[+-](?:0x[0-9a-fA-F]+|[0-9]+))?"
    r"(?![A-Za-z0-9_.$])"
)
_MIPS_REGISTERS = {
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8",
    "k0", "k1", "gp", "sp", "fp", "ra",
}.union({f"f{index}" for index in range(32)})
_HI_IDENTITY = re.compile(r"%hi\(<sym:([0-9a-f]{8})>\)")
_LO_IDENTITY = re.compile(r"%lo\(<sym:([0-9a-f]{8})>\)")


def load_symbol_addresses(filename: str) -> Dict[str, int]:
    """Read symbol values from a GNU ld map or an assignment file."""
    out: Dict[str, int] = {}
    with open(filename, encoding="utf-8", errors="ignore") as stream:
        for row in stream:
            match = _MAP_ADDRESS_FIRST.match(row)
            if match:
                value, name = match.groups()
            else:
                match = _MAP_SYMBOL_FIRST.match(row)
                if not match:
                    continue
                name, value = match.groups()
            out[name] = int(value, 16)
    return out


def normalize_symbolic_row(row: str, addresses: Mapping[str, int]) -> str:
    """Replace relocation aliases with their resolved address identity.

    The assembler can spell one address as `alias` or `base+offset`. Those
    forms link to identical bytes, but comparing their relocation text adds a
    false register-allocation penalty and can hide a real one-instruction near
    miss. Unknown symbols stay unchanged, so different unresolved references
    are still visible.
    """

    def replace(match: re.Match[str]) -> str:
        name = match.group("name")
        if name in _MIPS_REGISTERS or name not in addresses:
            return match.group(0)
        offset_text = match.group("offset")
        offset = int(offset_text, 0) if offset_text else 0
        address = (addresses[name] + offset) & 0xFFFFFFFF
        return f"<sym:{address:08x}>"

    normalized = _SYMBOL_EXPR.sub(replace, row)

    def hi_identity(match: re.Match[str]) -> str:
        address = int(match.group(1), 16)
        return f"<hi:{((address + 0x8000) >> 16) & 0xFFFF:04x}>"

    def lo_identity(match: re.Match[str]) -> str:
        address = int(match.group(1), 16)
        return f"<lo:{address & 0xFFFF:04x}>"

    normalized = _HI_IDENTITY.sub(hi_identity, normalized)
    return _LO_IDENTITY.sub(lo_identity, normalized)


class Scorer:
    PENALTY_INF = 10**9

    PENALTY_STACKDIFF = 1
    PENALTY_REGALLOC = 5
    PENALTY_REORDERING = 60
    PENALTY_INSERTION = 100
    PENALTY_DELETION = 100

    def __init__(
        self,
        target_o: str,
        *,
        stack_differences: bool,
        algorithm: str,
        debug_mode: bool,
        symbol_map: Optional[str] = None,
    ):
        self.target_o = target_o
        self.arch = get_arch(target_o)
        self.stack_differences = stack_differences
        self.algorithm = algorithm
        self.debug_mode = debug_mode
        self.symbol_addresses = (
            load_symbol_addresses(symbol_map) if symbol_map else {}
        )
        _, self.target_seq = self._objdump(target_o)
        self.difflib_differ: difflib.SequenceMatcher[str] = difflib.SequenceMatcher(
            autojunk=False
        )
        self.difflib_differ.set_seq2([line.mnemonic for line in self.target_seq])

    def _objdump(self, o_file: str) -> Tuple[str, List[Line]]:
        lines = objdump(o_file, self.arch, stack_differences=self.stack_differences)
        if self.symbol_addresses:
            lines = [
                Line(
                    row=normalize_symbolic_row(line.row, self.symbol_addresses)
                    if line.has_symbol else line.row,
                    mnemonic=line.mnemonic,
                    has_symbol=line.has_symbol,
                )
                for line in lines
            ]
        return "\n".join([line.row for line in lines]), lines

    def score(self, cand_o: Optional[str]) -> Tuple[int, str]:
        if not cand_o:
            return Scorer.PENALTY_INF, ""

        objdump_output, cand_seq = self._objdump(cand_o)

        num_stack_penalties = 0
        num_regalloc_penalties = 0
        num_reordering_penalties = 0
        num_insertion_penalties = 0
        num_deletion_penalties = 0
        deletions = []
        insertions = []

        def field_matches_any_symbol(field: str, arch: ArchSettings) -> bool:
            if arch.name == "ppc":
                if "..." in field:
                    return True

                parts = field.rsplit("@", 1)
                if len(parts) == 2 and parts[1] in {"l", "h", "ha", "sda21"}:
                    field = parts[0]

                return re.fullmatch(r"^@\d+$", field) is not None

            if arch.name == "mips":
                return "." in field

            # Example: ".text+0x34"
            if arch.name == "arm32":
                return "." in field

            return False

        def diff_sameline(old_line: Line, new_line: Line) -> None:
            nonlocal num_stack_penalties
            nonlocal num_regalloc_penalties

            old = old_line.row
            new = new_line.row

            if old == new:
                return

            ignore_last_field = False
            if self.stack_differences:
                oldsp = re.search(self.arch.re_sprel, old)
                newsp = re.search(self.arch.re_sprel, new)
                if oldsp and newsp:
                    oldrel = int(oldsp.group(1) or "0", 0)
                    newrel = int(newsp.group(1) or "0", 0)
                    num_stack_penalties += abs(oldrel - newrel)
                    ignore_last_field = True

            # Probably regalloc difference, or signed vs unsigned

            # Compare each field in order
            new_parts, old_parts = new.split(None, 1), old.split(None, 1)
            newfields = new_parts[1].split(",") if len(new_parts) > 1 else []
            oldfields = old_parts[1].split(",") if len(old_parts) > 1 else []
            if ignore_last_field:
                newfields = newfields[:-1]
                oldfields = oldfields[:-1]
            else:
                # If the last field has a parenthesis suffix, e.g. "0x38(r7)"
                # we split that part out to make it a separate field
                # however, we don't split if it has a proceeding %hi/%lo  e.g."%lo(.data)" or "%hi(.rodata + 0x10)"
                re_paren = re.compile(r"(?<!%hi)(?<!%lo)\(")
                oldfields = oldfields[:-1] + (
                    re_paren.split(oldfields[-1]) if len(oldfields) > 0 else []
                )
                newfields = newfields[:-1] + (
                    re_paren.split(newfields[-1]) if len(newfields) > 0 else []
                )

            for nf, of in zip(newfields, oldfields):
                if nf != of:
                    # If the new field is a match to any symbol case
                    # and the old field had a relocation, then ignore this mismatch
                    if field_matches_any_symbol(nf, self.arch) and old_line.has_symbol:
                        continue
                    num_regalloc_penalties += 1

            # Penalize any extra fields
            num_regalloc_penalties += abs(len(newfields) - len(oldfields))

        def diff_insert(line: str) -> None:
            # Reordering or totally different codegen.
            # Defer this until later when we can tell.
            insertions.append(line)

        def diff_delete(line: str) -> None:
            deletions.append(line)

        result_diff: Sequence[Tuple[str, int, int, int, int]]
        if self.algorithm == "levenshtein":
            import Levenshtein

            remapping: Dict[str, str] = {}

            def remap(seq: List[str]) -> str:
                seq = seq[:]
                for i in range(len(seq)):
                    val = remapping.get(seq[i])
                    if val is None:
                        val = chr(len(remapping))
                        remapping[seq[i]] = val
                    seq[i] = val
                return "".join(seq)

            result_diff = Levenshtein.opcodes(
                remap([line.mnemonic for line in cand_seq]),
                remap([line.mnemonic for line in self.target_seq]),
            )
        else:
            self.difflib_differ.set_seq1([line.mnemonic for line in cand_seq])
            result_diff = self.difflib_differ.get_opcodes()

        for (tag, i1, i2, j1, j2) in result_diff:
            if tag == "equal":
                for k in range(i2 - i1):
                    old_line = self.target_seq[j1 + k]
                    new_line = cand_seq[i1 + k]
                    diff_sameline(old_line, new_line)
            if tag == "replace" or tag == "delete":
                for k in range(i1, i2):
                    diff_insert(cand_seq[k].row)
            if tag == "replace" or tag == "insert":
                for k in range(j1, j2):
                    diff_delete(self.target_seq[k].row)

        if self.debug_mode:
            # Print simple asm diff
            for (tag, i1, i2, j1, j2) in result_diff:
                if tag == "equal":
                    for k in range(i2 - i1):
                        old = self.target_seq[j1 + k].row
                        new = cand_seq[i1 + k].row
                        color = "\u001b[0m" if old == new else "\u001b[94m"
                        print(color, old[:40].ljust(40), "\t", new)
                if tag == "replace" or tag == "delete":
                    for k in range(i1, i2):
                        print("\u001b[32;1m", "".ljust(40), "\t", cand_seq[k].row)
                if tag == "replace" or tag == "insert":
                    for k in range(j1, j2):
                        print("\u001b[91;1m", self.target_seq[k].row)

            print("\u001b[0m")

        insertions_co = Counter(insertions)
        deletions_co = Counter(deletions)
        for item in insertions_co + deletions_co:
            ins = insertions_co[item]
            dels = deletions_co[item]
            common = min(ins, dels)
            num_insertion_penalties += ins - common
            num_deletion_penalties += dels - common
            num_reordering_penalties += common

        if self.debug_mode:
            print()
            print("--------------- Penalty List ---------------")
            print(
                "Stack Differences: ".ljust(30),
                num_stack_penalties,
                f" ({self.PENALTY_STACKDIFF})",
            )
            print(
                "Register Differences: ".ljust(30),
                num_regalloc_penalties,
                f" ({self.PENALTY_REGALLOC})",
            )
            print(
                "Reorderings: ".ljust(30),
                num_reordering_penalties,
                f" ({self.PENALTY_REORDERING})",
            )
            print(
                "Insertions: ".ljust(30),
                num_insertion_penalties,
                f" ({self.PENALTY_INSERTION})",
            )
            print(
                "Deletions: ".ljust(30),
                num_deletion_penalties,
                f" ({self.PENALTY_DELETION})",
            )

        final_score = (
            num_stack_penalties * self.PENALTY_STACKDIFF
            + num_regalloc_penalties * self.PENALTY_REGALLOC
            + num_reordering_penalties * self.PENALTY_REORDERING
            + num_insertion_penalties * self.PENALTY_INSERTION
            + num_deletion_penalties * self.PENALTY_DELETION
        )

        return (final_score, hashlib.sha256(objdump_output.encode()).hexdigest())
