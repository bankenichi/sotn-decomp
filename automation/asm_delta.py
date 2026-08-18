#!/usr/bin/env python3
"""Derive a twin transplant's substitutions from the two .s files.

WHY THIS EXISTS
    The first transplant match needed three things supplied by hand: which
    symbols the destination overlay renames, which constants differ, and
    whether the twin was worth trying at all. A mechanism that needs an
    operator for all three is not a mechanism.

    All three are already written down. func_us_801CC750 and
    func_us_801CC750_from_no0 have 115 instructions in identical order with
    identical registers, and differ in exactly:

        %hi(D_us_80180A88)      vs  %hi(RNO0_EInitSpawner)
        %hi(func_us_801CC8F8)   vs  %hi(func_us_801CC8F8_from_no0)
        ori $t1, $zero, 0xC0    vs  0xE0        \\  the inverted castle
        ori $t0, $zero, 0xE0    vs  0xC0         |  is mirrored, so the
        ori $a1, $zero, 0x91    vs  0x5F         |  sprite's U coords swap
        ori $v1, $zero, 0xC1    vs  0x3F         |  and its Y coords flip
        ori $s3, $zero, 0x8E    vs  0x6A        /

    That is the entire hand-supplied map, minus one entry, recoverable by
    reading two files. No model, no guess.

THE ONE THING THE ASM CANNOT SAY
    E_ID_16 -> E_UNK_16 does not appear in the diff at all, because both enum
    members have the same VALUE. The rename is needed only so the C compiles
    in an overlay whose header does not declare E_ID_16. That is a C-level
    name-availability problem, handled by transplant.auto_decls and by
    matching enum members on value, not something this file can see.

WHAT A DIFFERENCE MEANS
    same length, same mnemonics, differing operands   a clean twin; the
                                                      substitutions below are
                                                      complete
    same length, differing mnemonics                  NOT a twin; the code
                                                      genuinely differs
    different length                                  NOT a twin

    Reporting that honestly is the point. A candidate that is not a twin
    should be said to be not a twin, not forced through a build.

STRICTLY READ-ONLY.

Usage:
    python3 automation/asm_delta.py --pair <twin.s> <target.s>
    python3 automation/asm_delta.py --function func_us_801CC750_from_no0
    python3 automation/asm_delta.py --self-test
"""
from __future__ import annotations

import argparse
from collections import Counter
from difflib import SequenceMatcher
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# One instruction line: /* fileoff vaddr word */  mnemonic operands
RX_INSN = re.compile(
    r"^\s*/\*\s*[0-9A-Fa-f]+\s+[0-9A-Fa-f]+\s+[0-9A-Fa-f]+\s*\*/\s*"
    r"(?P<mn>[a-z][a-z0-9.]*)\s*(?P<ops>.*?)\s*$")
RX_OBJDUMP_INSN = re.compile(
    r"^\s*[0-9A-Fa-f]+:\s+[0-9A-Fa-f]{8}\s+"
    r"(?P<mn>[a-z][a-z0-9.]*)\s*(?P<ops>.*?)\s*$")
RX_OBJDUMP_RELOC = re.compile(
    r"^\s*[0-9A-Fa-f]+:\s+R_MIPS_(?P<kind>[A-Z0-9_]+)\s+"
    r"(?P<symbol>\S+)")
# Local labels differ by address between two copies of the same function and
# carry no meaning; they must never become substitutions.
RX_LOCAL_LABEL = re.compile(r"^\.L[A-Za-z0-9_]+$")
RX_SYMREF = re.compile(
    r"%(?:hi|lo)\(([A-Za-z_]\w*(?:[+-]0x[0-9A-Fa-f]+)?)")
RX_JAL = re.compile(r"^\s*([A-Za-z_]\w*)\s*$")
RX_IMM = re.compile(r"(?<![\w.$])(-?0x[0-9A-Fa-f]+|-?\d+)(?![\w.])")


def _relocated_operand(mnemonic: str, operands: str,
                       kind: str, symbol: str) -> str:
    """Put objdump's following relocation back into its instruction."""
    if kind == "HI16":
        head, sep, _tail = operands.rpartition(",")
        return f"{head}{sep}%hi({symbol})" if sep else operands
    if kind in ("LO16", "GPREL16"):
        head, sep, tail = operands.partition(",")
        marker = "%lo" if kind == "LO16" else "%gp_rel"
        tail = re.sub(
            r"(?<![\w.$])-?(?:0x[0-9A-Fa-f]+|\d+)(?![\w.])",
            f"{marker}({symbol})",
            tail,
            count=1,
        )
        return f"{head}{sep}{tail}" if sep else operands
    if kind in ("26", "PC16") and mnemonic in ("jal", "j"):
        return symbol
    return operands


def _objdump_instructions(text: str) -> list[tuple[str, str]]:
    out: list[list[str]] = []
    for line in (text or "").splitlines():
        insn = RX_OBJDUMP_INSN.match(line)
        if insn:
            out.append([insn.group("mn"), insn.group("ops")])
            continue
        reloc = RX_OBJDUMP_RELOC.match(line)
        if reloc and out:
            out[-1][1] = _relocated_operand(
                out[-1][0], out[-1][1],
                reloc.group("kind"), reloc.group("symbol"))
    return [(mn, ops) for mn, ops in out]


def instructions(text: str) -> list[tuple[str, str]]:
    """[(mnemonic, operands)] with directives, labels and blanks dropped."""
    out = []
    for line in (text or "").splitlines():
        m = RX_INSN.match(line)
        if m:
            out.append((m.group("mn"), m.group("ops")))
    return out or _objdump_instructions(text)


def _number_value(raw: str) -> int | None:
    try:
        return int(raw, 0)
    except ValueError:
        return None


def _comparable_operands(mnemonic: str, operands: str) -> str:
    """Normalize formatting and equivalent numbers, retaining symbol names."""
    value = operands.replace("$", "")
    value = re.sub(r"\s+", "", value)

    def number(match: re.Match) -> str:
        parsed = _number_value(match.group(1))
        return f"#{parsed}" if parsed is not None else match.group(1)

    value = RX_IMM.sub(number, value)
    if mnemonic.startswith("b") or mnemonic in ("j", "jr"):
        parts = value.split(",")
        if parts and (
            parts[-1].startswith(".L")
            or re.fullmatch(r"(?:0x)?[0-9A-Fa-f]+", parts[-1])
        ):
            parts[-1] = "<target>"
            value = ",".join(parts)
    return value


def _instruction_shape(mnemonic: str, operands: str) -> str:
    """Instruction identity with names and literal values abstracted."""
    value = _comparable_operands(mnemonic, operands)
    value = re.sub(
        r"%(hi|lo|gp_rel)\([^)]*\)", r"%\1(SYM)", value)
    value = re.sub(r"#-?\d+", "IMM", value)
    if mnemonic == "jal":
        value = "<call>"
    return f"{mnemonic} {value}"


def _record_operand_maps(
    mnemonic: str,
    donor: str,
    target: str,
    symbols: dict[str, str],
    consts: dict[str, str],
) -> bool:
    """Record supported changes; return False for an unexplained operand delta."""
    def record(mapping: dict[str, str], old: str, new: str,
               numeric: bool = False) -> bool:
        """Keep a proposal only when every occurrence agrees.

        A single donor name or literal can occur more than once. If aligned
        rows map it to two target values, either the alignment is wrong or the
        relationship cannot be expressed as one C substitution. Retaining the
        last value would make a confident but destructive automatic map.
        """
        equivalent = (
            (lambda key: _number_value(key) == _number_value(old))
            if numeric else (lambda key: key == old)
        )
        prior = [value for key, value in mapping.items() if equivalent(key)]
        if prior:
            same = (
                all(_number_value(value) == _number_value(new)
                    for value in prior)
                if numeric else all(value == new for value in prior)
            )
            if same and numeric and old not in mapping:
                # Preserve each donor spelling so apply_map can replace the C
                # token whether the listing rendered it decimal or hex.
                mapping[old] = new
            return same
        mapping[old] = new
        return True

    if _comparable_operands(mnemonic, donor) == _comparable_operands(
        mnemonic, target
    ):
        return True
    src_symbols, dst_symbols = RX_SYMREF.findall(donor), RX_SYMREF.findall(target)
    if src_symbols and dst_symbols and len(src_symbols) == len(dst_symbols):
        consistent = True
        for old, new in zip(src_symbols, dst_symbols):
            if old != new:
                consistent &= record(symbols, old, new)
        return consistent
    if mnemonic == "jal":
        old_call, new_call = RX_JAL.match(donor), RX_JAL.match(target)
        if old_call and new_call:
            if old_call.group(1) != new_call.group(1):
                return record(
                    symbols, old_call.group(1), new_call.group(1))
            return True
    src_imms, dst_imms = RX_IMM.findall(donor), RX_IMM.findall(target)
    if src_imms and dst_imms and len(src_imms) == len(dst_imms):
        consistent = True
        for old, new in zip(src_imms, dst_imms):
            if _number_value(old) != _number_value(new):
                consistent &= record(consts, old, new, numeric=True)
        return consistent
    donor_tail = donor.split(",")[-1].strip()
    target_tail = target.split(",")[-1].strip()
    if RX_LOCAL_LABEL.match(donor_tail or "x") and RX_LOCAL_LABEL.match(
        target_tail or "x"
    ):
        return True
    return False


def _codegen_hints(
    kind: str,
    donor: list[tuple[str, str]],
    target: list[tuple[str, str]],
) -> list[str]:
    hints: list[str] = []
    if kind == "schedule-only":
        hints.append(
            "same instruction shapes moved locally; test alias visibility, "
            "API member versus standalone pointer surface, and temporary "
            "placement with the permuter"
        )
    if any(mn == "jalr" for mn, _ in donor + target):
        hints.append(
            "indirect calls are present; compare g_api.Member, "
            "g_api_Member, and a cached function pointer"
        )
    if donor and target and donor[0][0] == target[0][0] == "addiu":
        src = RX_IMM.findall(donor[0][1])
        dst = RX_IMM.findall(target[0][1])
        if src and dst and _number_value(src[-1]) != _number_value(dst[-1]):
            hints.append(
                "stack frames differ; check missing locals or an intentional "
                "volatile frame pad only after control flow agrees"
            )
    if abs(len(donor) - len(target)) <= max(4, len(target) // 20):
        hints.append(
            "length is close; inspect direct assignment versus increment and "
            "explicit no-op switch cases before broader derivation"
        )
    return hints


def delta(twin_asm: str, target_asm: str) -> dict:
    """Substitutions that turn the twin's C into the target's C.

    Returns classifications and operand-map proposals. `maps_safe` is true
    only when instruction shapes align position-for-position; near alignment
    can pair unrelated calls and must never rewrite C automatically.
    """
    a, b = instructions(twin_asm), instructions(target_asm)
    if not a or not b:
        return {"ok": False, "reason": "could not parse instructions",
                "symbols": {}, "consts": {}, "insns": 0, "target_insns": 0,
                "diffs": 0, "similarity": 0.0, "kind": "error", "hints": [],
                "maps_safe": False}

    shapes_a = [_instruction_shape(*insn) for insn in a]
    shapes_b = [_instruction_shape(*insn) for insn in b]
    matcher = SequenceMatcher(None, shapes_a, shapes_b, autojunk=False)
    similarity = matcher.ratio()
    matched_pairs: list[tuple[int, int]] = []
    for block in matcher.get_matching_blocks():
        matched_pairs.extend(
            (block.a + offset, block.b + offset)
            for offset in range(block.size)
        )

    symbols: dict[str, str] = {}
    consts: dict[str, str] = {}
    operand_diffs = 0
    unexplained = 0
    for src_i, dst_i in matched_pairs:
        mn_a, op_a = a[src_i]
        mn_b, op_b = b[dst_i]
        if _comparable_operands(mn_a, op_a) == _comparable_operands(mn_b, op_b):
            continue
        operand_diffs += 1
        if not _record_operand_maps(
            mn_a, op_a, op_b, symbols, consts
        ):
            unexplained += 1

    missing = max(len(a), len(b)) - len(matched_pairs)
    diffs = missing + operand_diffs
    if shapes_a == shapes_b:
        if unexplained == 0:
            kind = "clean"
            ok = True
            reason = "clean twin"
        else:
            kind = "structural-near"
            ok = False
            reason = (
                "same instruction shape, but "
                f"{unexplained} operand mapping(s) conflict or are unexplained"
            )
    elif len(a) == len(b) and Counter(shapes_a) == Counter(shapes_b):
        kind = "schedule-only"
        ok = False
        reason = (
            f"schedule-only twin: {missing} instruction position(s) moved; "
            "same instruction-shape multiset"
        )
    elif similarity >= 0.65:
        kind = "structural-near"
        ok = False
        reason = (
            f"structural near: {len(a)} vs {len(b)} instructions, "
            f"{similarity:.1%} aligned; code shape differs"
        )
    else:
        kind = "not-twin"
        ok = False
        reason = (
            f"different length or opcode shape: {len(a)} vs {len(b)} "
            f"instructions, {similarity:.1%} aligned; not a twin"
        )
    return {
        "ok": ok,
        "reason": reason,
        "symbols": symbols,
        "consts": consts,
        "insns": len(a),
        "target_insns": len(b),
        "diffs": diffs,
        "similarity": similarity,
        "kind": kind,
        "hints": _codegen_hints(kind, a, b),
        "maps_safe": kind == "clean",
    }


_ASM_INDEX: dict[str, Path] | None = None


def _asm_overlay(p: Path) -> str:
    """`asm/us/st/rno0/nonmatchings/e_x/f.s` -> `st/rno0`.

    The overlay is everything between `asm/us/` and `nonmatchings/`. Split on
    the literal separator rather than counting components, because depth
    varies: `st/rno0`, `boss/bo6`, `ric`.
    """
    s = p.as_posix()
    if "/asm/us/" not in s or "/nonmatchings/" not in s:
        return ""
    return s.split("/asm/us/", 1)[1].split("/nonmatchings/", 1)[0]


def src_overlay(p: str | Path) -> str:
    """`src/st/rno0/e_x.c` -> `st/rno0`. The same key _asm_overlay returns."""
    s = Path(p).as_posix()
    if "src/" not in s:
        return ""
    return "/".join(s.split("src/", 1)[1].split("/")[:-1])


def _find_asm(fn: str, overlay: str = "") -> Path | None:
    """The .s for a function, via an index built ONCE.

    The index is rebuilt at most once per process: the first version rglob'd
    asm/us per call, twice, at 27 seconds a function, and transplant --scan
    calls this for every record.

    KEYED BY NAME, WHICH IS NOT UNIQUE. This stored `setdefault(f.stem, f)`,
    so when one function name has assembly in two overlays the index silently
    kept whichever the walk happened to reach first, and every caller got that
    one with no indication a choice had been made. A delta computed against
    the wrong overlay's function is not an error anyone would notice: it
    returns plausible symbol renames and constant changes for two functions
    that were never related.

    Now every match is kept and the caller must disambiguate:
      - `overlay` given ("st/rno0")  -> that overlay's copy, or None.
      - omitted, one match           -> it.
      - omitted, several             -> None. Refusing is the whole point;
                                        picking one is what this fixes.
    """
    global _ASM_INDEX
    if _ASM_INDEX is None:
        _ASM_INDEX = {}
        root = REPO / "asm" / "us"
        if root.is_dir():
            for f in root.rglob("*.s"):
                # FUNCTIONS ONLY. The walk took every .s under asm/us, which
                # includes the data segments: st_common.data.s exists in 36
                # overlays, sprites.data.s in 27, rooms.data.s in 31. None of
                # them is a function listing and delta() would compare two of
                # them happily. They also drowned the collision report.
                if "/nonmatchings/" not in f.as_posix():
                    continue
                _ASM_INDEX.setdefault(f.stem, []).append(f)
    hits = _ASM_INDEX.get(fn) or []
    if overlay:
        hits = [h for h in hits if _asm_overlay(h) == overlay]
    return hits[0] if len(hits) == 1 else None


def asm_name_collisions() -> dict[str, list[str]]:
    """Function names whose .s exists in more than one overlay. Read-only."""
    _find_asm("")                      # force the index
    return {k: [str(p) for p in v]
            for k, v in sorted((_ASM_INDEX or {}).items()) if len(v) > 1}


def for_function(fn: str, twin_name: str = "", overlay: str = "",
                 twin_overlay: str = "", twin_source: str = "") -> dict:
    """Delta between a queue function and a twin.

    `twin_name` lets a caller nominate a twin found by SIMILARITY rather than
    by the `X_from_Y` naming convention -- asm_twin_finder matches on shape and
    tokens, and most of the tree's twins do not share a name.

    `overlay` / `twin_overlay` ("st/rno0", "boss/bo6") disambiguate when a name
    has assembly in more than one overlay. Pass them whenever you know them;
    src_overlay() derives one from a source path. Without them a colliding
    name resolves to nothing rather than to a guess.

    A NOTE ON WHY THIS OFTEN RETURNS "no twin asm". This derives substitutions
    by DIFFING TWO LISTINGS, so it needs the donor to still have assembly --
    and a donor is a donor precisely because it has already been decompiled,
    which is when its .s disappears. Measured 2026-08-10 on the five twins in
    task #103: only func_us_801D1388_from_are worked, because ARE's copy is
    also still unmatched. For EntityGaibon there is exactly ONE EntityGaibon.s
    in the tree (rchi's own), so target and twin resolve to the same file.
    That is not a defect here; it is the honest answer, and the caller should
    fall back to --map or to the fleet.
    """
    base = twin_name or re.sub(r"_from_\w+$", "", fn)
    tgt = _find_asm(fn, overlay)
    twin = _find_asm(base, twin_overlay)
    if not tgt:
        amb = len((_ASM_INDEX or {}).get(fn) or [])
        why = (f"asm for {fn} exists in {amb} overlays and none was named; "
               f"pass overlay=" if amb > 1 else f"no asm for {fn}")
        return {"ok": False, "reason": why, "symbols": {},
                "consts": {}, "insns": 0, "diffs": 0}
    target_text = tgt.read_text(errors="ignore")
    compiled_text = ""
    compiled_path = ""
    compiled_error = ""
    if (not twin or twin == tgt) and twin_source:
        compiled_text, compiled_path, compiled_error = compiled_twin_asm(
            base, twin_source, target_text)
    if (not twin or twin == tgt) and not compiled_text:
        amb = len((_ASM_INDEX or {}).get(base) or [])
        why = (f"twin asm for {base} exists in {amb} overlays and none was "
               f"named; pass twin_overlay=" if amb > 1 and not twin
               else f"no distinct twin asm for {base}")
        if compiled_error:
            why += f"; compiled fallback: {compiled_error}"
        return {"ok": False, "reason": why,
                "symbols": {}, "consts": {}, "insns": 0, "diffs": 0}
    twin_text = compiled_text or twin.read_text(errors="ignore")
    d = delta(twin_text, target_text)
    d["twin_asm"] = compiled_path or str(twin)
    d["target_asm"] = str(tgt)
    d["target_symbols"] = referenced_symbols(target_text)
    return d


def referenced_symbols(asm_text: str) -> set[str]:
    """Symbols named by relocations or direct calls in one listing."""
    out = set(RX_SYMREF.findall(asm_text))
    for mnemonic, operands in instructions(asm_text):
        if mnemonic == "jal":
            match = RX_JAL.match(operands)
            if match:
                out.add(match.group(1))
    return out


RX_LOCAL_INCLUDE = re.compile(r'^\s*#\s*include\s*"([^"]+)"', re.M)
_DIRECT_INCLUDE_PARENTS: dict[Path, set[Path]] = {}


def _direct_include_parents(target: Path) -> set[Path]:
    """Tracked C/headers that directly include target, cached per header."""
    target = target.resolve()
    if target in _DIRECT_INCLUDE_PARENTS:
        return _DIRECT_INCLUDE_PARENTS[target]
    out: set[Path] = set()
    try:
        result = subprocess.run(
            ["git", "grep", "-l", "-F", target.name, "--", "src/"],
            cwd=str(REPO), capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        result = None
    for raw_path in (result.stdout.splitlines() if result else []):
        path = REPO / raw_path
        if path.suffix not in {".c", ".h"}:
            continue
        try:
            includes = RX_LOCAL_INCLUDE.findall(path.read_text(errors="ignore"))
        except OSError:
            continue
        if any((path.parent / include).resolve() == target
               for include in includes):
            out.add(path.resolve())
    _DIRECT_INCLUDE_PARENTS[target] = out
    return out


def compiled_object_paths(source_path: str | Path) -> list[Path]:
    """US object candidates that compile a C source or a shared header."""
    source = Path(source_path)
    if not source.is_absolute():
        source = REPO / source
    source = source.resolve()
    try:
        source.relative_to(REPO.resolve())
    except ValueError:
        return []

    consumers: set[Path] = set()
    if source.suffix == ".c":
        consumers.add(source)
    elif source.suffix == ".h":
        pending = [source]
        seen = {source}
        while pending:
            target = pending.pop()
            for parent in _direct_include_parents(target):
                if parent.suffix == ".c":
                    consumers.add(parent)
                elif parent.suffix == ".h" and parent not in seen:
                    seen.add(parent)
                    pending.append(parent)

    out = []
    for consumer in consumers:
        try:
            rel = consumer.relative_to(REPO.resolve())
        except ValueError:
            continue
        out.append(REPO / "build" / "us" / Path(str(rel) + ".o"))
    return sorted(out)


def parse_ninja_dependencies(output: str, root: Path = REPO) -> list[Path]:
    """Dependency paths from `ninja -t deps TARGET` output."""
    dependencies: list[Path] = []
    for line in (output or "").splitlines():
        if not line[:1].isspace():
            continue
        value = line.strip()
        if not value:
            continue
        path = Path(value)
        dependencies.append(path if path.is_absolute() else root / path)
    return dependencies


def compiled_object_dependencies(obj: Path) -> tuple[list[Path], str]:
    """Complete compiler dependency set recorded by Ninja for one object."""
    ninja = shutil.which("ninja")
    if not ninja:
        return [], "ninja is unavailable, so compiler dependencies are unknown"
    try:
        target = obj.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return [], "compiled object is outside the repository"
    try:
        result = subprocess.run(
            [ninja, "-t", "deps", target], cwd=str(REPO),
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], f"ninja dependency query failed: {type(exc).__name__}: {exc}"
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        return [], f"ninja dependency query failed: {detail}"
    dependencies = parse_ninja_dependencies(result.stdout)
    if not dependencies:
        return [], "ninja recorded no compiler dependencies for the object"
    return dependencies, ""


def compiled_twin_asm(
    function: str, source_path: str | Path, target_asm: str = ""
) -> tuple[str, str, str]:
    """Disassemble an already-matched donor from a current US build object.

    A definition in a shared header has no `.h.o`. Follow the local include
    graph to every compiled C consumer and, when target assembly is available,
    select the consumer whose function is structurally closest to it.
    """
    source = Path(source_path)
    if source.is_absolute():
        try:
            source = source.relative_to(REPO)
        except ValueError:
            return "", "", "source is outside the repository"
    objects = compiled_object_paths(source)
    existing = [obj for obj in objects if obj.is_file()]
    if not existing:
        expected = str(objects[0]) if objects else str(
            REPO / "build" / "us" / Path(str(source) + ".o"))
        if source.suffix == ".h":
            return "", expected, (
                "no compiled US C consumer object exists for this header; "
                "check its include and splat wiring")
        return "", expected, "compiled donor object is missing; run a build"
    source_abs = REPO / source
    current: list[Path] = []
    rejected: list[str] = []
    for obj in existing:
        dependencies, dependency_error = compiled_object_dependencies(obj)
        if dependency_error:
            rejected.append(f"{obj.name}: {dependency_error}")
            continue
        inputs = list(dependencies) + [source_abs]
        try:
            consumer = REPO / obj.relative_to(REPO / "build" / "us").with_suffix("")
        except ValueError:
            consumer = source_abs
        if consumer != source_abs:
            inputs.append(consumer)
        if compiled_object_is_current(obj, inputs):
            current.append(obj)
        else:
            rejected.append(
                f"{obj.name}: object is older than a compiler dependency")
    if existing and not current:
        return "", str(existing[0]), (
            "no dependency-complete current donor object; "
            + "; ".join(rejected[:2])
            + ". Run a build before using it as twin evidence")
    existing = current

    objdump = shutil.which("mipsel-linux-gnu-objdump")
    if not objdump:
        return "", str(existing[0]), "mipsel-linux-gnu-objdump is unavailable"

    found: list[tuple[tuple, str, Path]] = []
    errors: list[str] = []
    for obj in existing:
        try:
            result = subprocess.run(
                [objdump, "-dr", f"--disassemble={function}", str(obj)],
                cwd=str(REPO),
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"{obj.name}: {type(exc).__name__}: {exc}")
            continue
        text = result.stdout or ""
        if result.returncode != 0:
            errors.append(f"{obj.name}: {(result.stderr or text).strip()}")
            continue
        if not _objdump_instructions(text):
            continue
        if not target_asm:
            return text, str(obj), ""
        if target_asm:
            comparison = delta(text, target_asm)
            kinds = {"clean": 4, "schedule-only": 3,
                     "structural-near": 2, "not-twin": 1, "error": 0}
            rank = (kinds.get(comparison.get("kind", "error"), 0),
                    comparison.get("similarity", 0.0),
                    -comparison.get("diffs", 0))
        else:
            rank = (0, 0.0, 0)
        found.append((rank, text, obj))
    if not found:
        detail = ("; " + "; ".join(errors[:2])) if errors else ""
        return "", str(existing[0]), (
            f"{function} was not found in {len(existing)} compiled consumer "
            f"object(s){detail}")
    _rank, text, obj = max(found, key=lambda item: item[0])
    return text, str(obj), ""


def compiled_object_is_current(obj: Path, inputs: list[Path]) -> bool:
    """True only when an object is at least as new as every existing input."""
    try:
        object_time = obj.stat().st_mtime_ns
        return bool(inputs) and all(
            path.is_file() and path.stat().st_mtime_ns <= object_time
            for path in inputs)
    except OSError:
        return False


def as_maps(d: dict) -> list[str]:
    """Position-proven substitutions as OLD=NEW pairs for transplant --map.

    Sequence alignment still records operand proposals for diagnostics, but a
    structural-near alignment can pair unrelated calls. Returning those as
    edits caused `rand -> InitializeEntity` in a BO6 draft. Only a clean,
    position-aligned twin is safe to rewrite automatically.
    """
    if not d.get("maps_safe", False):
        return []
    return ([f"{k}={v}" for k, v in sorted(d.get("symbols", {}).items())]
            + [f"{k}={v}" for k, v in sorted(d.get("consts", {}).items())])


def report(fn: str, overlay: str = "", twin_overlay: str = "") -> int:
    d = for_function(fn, overlay=overlay, twin_overlay=twin_overlay)
    print(f"{fn}")
    print(f"  {d['reason']}  ({d['insns']} instructions, "
          f"{d['diffs']} differing)")
    if not d["ok"]:
        return 1
    print(f"  twin:   {d.get('twin_asm','')}")
    print(f"  target: {d.get('target_asm','')}")
    if d["symbols"]:
        print("\n  symbol renames:")
        for k, v in sorted(d["symbols"].items()):
            print(f"    {k} -> {v}")
    if d["consts"]:
        print("\n  constant changes:")
        for k, v in sorted(d["consts"].items()):
            print(f"    {k} -> {v}")
    pairs = as_maps(d)
    if pairs:
        print("\n  --maps " + "/".join(pairs))
    else:
        print("\n  identical: a straight copy should match")
    return 0


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    twin = (
        "glabel func_a\n"
        "/* 100 80100000 27BDFFD0 */  addiu $sp, $sp, -0x30\n"
        "/* 104 80100004 1880043C */  lui   $a0, %hi(D_us_80180A88)\n"
        "/* 108 80100008 880A8424 */  addiu $a0, $a0, %lo(D_us_80180A88)\n"
        "/* 10C 8010000C 4421070C */  jal   func_us_801C8510\n"
        "/* 110 80100010 C0000934 */  ori   $t1, $zero, 0xC0\n"
        "/* 114 80100014 91000534 */  ori   $a1, $zero, 0x91\n"
        "/* 118 80100018 54004014 */  bnez  $v0, .Lus_801CC8D0\n")
    target = twin.replace("D_us_80180A88", "RNO0_EInitSpawner") \
                 .replace("func_us_801C8510", "InitializeEntity") \
                 .replace("0xC0", "0xE0").replace("0x91", "0x5F") \
                 .replace(".Lus_801CC8D0", ".Lus_801C0A78")

    print("\nthe real substitutions are recovered from the two listings")
    d = delta(twin, target)
    ck(d["ok"], f"a same-shape pair is a clean twin ({d['reason']})")
    ck(d["symbols"].get("D_us_80180A88") == "RNO0_EInitSpawner",
       f"the %hi/%lo symbol rename ({d['symbols']})")
    ck(d["symbols"].get("func_us_801C8510") == "InitializeEntity",
       "the jal target rename")
    ck(d["consts"] == {"0xC0": "0xE0", "0x91": "0x5F"},
       f"the constants, and only the constants ({d['consts']})")

    print("\ncompiled donor objects are valid twin evidence")
    objdump = (
        "00000000 <func_a>:\n"
        "   0: 27bdffd0  addiu sp,sp,-48\n"
        "   4: 3c040000  lui   a0,0x0\n"
        "            4: R_MIPS_HI16 D_us_80180A88\n"
        "   8: 24840000  addiu a0,a0,0\n"
        "            8: R_MIPS_LO16 D_us_80180A88\n"
        "   c: 0c000000  jal   0 <func_a>\n"
        "            c: R_MIPS_26 func_us_801C8510\n"
        "  10: 340900c0  ori   t1,zero,0xc0\n")
    obj_target = (
        "glabel func_b\n"
        "/* 100 80100000 27BDFFD0 */ addiu $sp, $sp, -0x30\n"
        "/* 104 80100004 1880043C */ lui $a0, %hi(RNO0_EInitSpawner)\n"
        "/* 108 80100008 880A8424 */ addiu $a0, $a0, %lo(RNO0_EInitSpawner)\n"
        "/* 10C 8010000C 4421070C */ jal InitializeEntity\n"
        "/* 110 80100010 C0000934 */ ori $t1, $zero, 0xE0\n")
    compiled_delta = delta(objdump, obj_target)
    ck(compiled_delta["ok"],
       f"objdump and splat listings compare directly ({compiled_delta['reason']})",
       f"{[_instruction_shape(*x) for x in instructions(objdump)]} != "
       f"{[_instruction_shape(*x) for x in instructions(obj_target)]}")
    ck(compiled_delta["symbols"].get("D_us_80180A88")
       == "RNO0_EInitSpawner",
       f"HI16/LO16 relocations retain the donor symbol "
       f"({compiled_delta['symbols']})")
    ck(compiled_delta["symbols"].get("func_us_801C8510")
       == "InitializeEntity",
       "R_MIPS_26 retains the donor call target")
    ck(compiled_delta["consts"].get("0xc0") == "0xE0",
       f"numeric spelling is normalized across objdump and splat "
       f"({compiled_delta['consts']})")

    print("\nshared-header donors resolve through a compiled C consumer")
    shared_text, shared_path, shared_error = compiled_twin_asm(
        "EntityRelicOrb", "src/st/e_collect.h")
    ck(bool(shared_text) and not shared_error,
       f"the existing US build supplies EntityRelicOrb ({shared_error})")
    ck(shared_path.endswith("e_collect.c.o"),
       f"the evidence names a consumer object, not a .h.o path ({shared_path})")

    print("\nlegal instruction scheduling is a distinct near class")
    scheduled_target = (
        "/* 0 0 0 */ sh $zero, 0x3C($s2)\n"
        "/* 4 4 0 */ lui $v0, %hi(g_api_AllocPrimitives)\n"
        "/* 8 8 0 */ lw $v0, %lo(g_api_AllocPrimitives)($v0)\n")
    scheduled_current = (
        "/* 0 0 0 */ lui $v0, %hi(g_api_AllocPrimitives)\n"
        "/* 4 4 0 */ lw $v0, %lo(g_api_AllocPrimitives)($v0)\n"
        "/* 8 8 0 */ sh $zero, 0x3C($s2)\n")
    scheduled = delta(scheduled_current, scheduled_target)
    ck(not scheduled["ok"] and scheduled["kind"] == "schedule-only",
       f"motion is routed near, not called structural failure "
       f"({scheduled['reason']})")
    ck(any("API member" in hint for hint in scheduled["hints"]),
       f"the diagnostic points at the source surfaces that affect GCC "
       f"scheduling ({scheduled['hints']})")

    print("\nnear alignment cannot perform automatic operand rewrites")
    near_donor = (
        "/* 0 0 0 */ jal rand\n"
        "/* 4 4 0 */ addiu $sp, $sp, -0x20\n"
        "/* 8 8 0 */ jr $ra\n")
    near_target = (
        "/* 0 0 0 */ jal InitializeEntity\n"
        "/* 4 4 0 */ ori $v0, $zero, 1\n"
        "/* 8 8 0 */ jr $ra\n")
    near = delta(near_donor, near_target)
    ck(near["kind"] == "structural-near",
       f"the adversarial fixture reaches the near path ({near['reason']})")
    ck(near["symbols"].get("rand") == "InitializeEntity",
       "the raw diagnostic exposes the ambiguous aligned proposal")
    ck(as_maps(near) == [],
       f"but the proposal can never become an automatic edit ({as_maps(near)})")

    print("\nconflicting aligned proposals cannot become an automatic map")
    conflict_donor = (
        "/* 0 0 0 */ jal SharedDonor\n"
        "/* 4 4 0 */ nop\n"
        "/* 8 8 0 */ jal SharedDonor\n"
        "/* C C 0 */ nop\n")
    conflict_target = (
        "/* 0 0 0 */ jal FirstTarget\n"
        "/* 4 4 0 */ nop\n"
        "/* 8 8 0 */ jal SecondTarget\n"
        "/* C C 0 */ nop\n")
    conflict = delta(conflict_donor, conflict_target)
    ck(conflict["kind"] == "structural-near" and not conflict["maps_safe"],
       f"same shapes with a one-to-many symbol map are not clean "
       f"({conflict['reason']})")
    ck(as_maps(conflict) == [],
       f"the conflicting proposal is diagnostic-only ({as_maps(conflict)})")

    print("\ncompiled donor evidence must be newer than its inputs")
    import tempfile
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        source = root / "donor.c"
        header = root / "donor.h"
        obj = root / "donor.c.o"
        source.write_text('#include "donor.h"\nvoid donor(void) {}\n',
                          encoding="utf-8")
        header.write_text("#define DONOR_VALUE 1\n", encoding="utf-8")
        obj.write_bytes(b"object")
        fixture = (
            f"{obj}: #deps 2, deps mtime 100 (VALID)\n"
            f"    {source}\n"
            f"    {header}\n")
        dependencies = parse_ninja_dependencies(fixture, root)
        ck(dependencies == [source, header],
           f"the complete Ninja dependency receipt is parsed ({dependencies})")
        os.utime(obj, ns=(1_000_000_000, 1_000_000_000))
        os.utime(source, ns=(500_000_000, 500_000_000))
        os.utime(header, ns=(2_000_000_000, 2_000_000_000))
        ck(not compiled_object_is_current(obj, dependencies),
           "a newer included header rejects the otherwise-current object")
        os.utime(obj, ns=(3_000_000_000, 3_000_000_000))
        ck(compiled_object_is_current(obj, dependencies),
           "an object rebuilt after every included header is accepted")

    print("\nlocal labels are NOT mistaken for substitutions")
    # They differ between any two copies of the same function and mean
    # nothing. Emitting `.Lus_801CC8D0=.Lus_801C0A78` would rewrite the C.
    ck(not any(k.startswith(".L") for k in
               {**d["symbols"], **d["consts"]}),
       f"no label appears in the map ({d['symbols']} {d['consts']})")

    print("\nregisters are not read as constants")
    ck("$t1" not in str(d["consts"]) and "1" not in d["consts"],
       f"the $-prefixed register survived ({d['consts']})")

    print("\na pair that is NOT a twin says so instead of guessing")
    shorter = "\n".join(twin.splitlines()[:4])
    ck(not delta(twin, shorter)["ok"], "different instruction counts")
    ck("not a twin" in delta(twin, shorter)["reason"], "and says why")
    swapped = twin.replace("addiu $sp, $sp, -0x30", "subu  $sp, $sp, $v0")
    d2 = delta(twin, swapped)
    ck(not d2["ok"] and "differs" in d2["reason"],
       f"a differing mnemonic is a structural mismatch ({d2['reason']})")

    print("\nan identical pair yields an empty map, not a failure")
    d3 = delta(twin, twin)
    ck(d3["ok"] and not as_maps(d3),
       f"nothing to substitute ({as_maps(d3)})")

    print("\nthe pairs are emitted in transplant's own --maps form")
    ck("D_us_80180A88=RNO0_EInitSpawner" in as_maps(d),
       f"OLD=NEW ({as_maps(d)[:2]})")

    # --- a name is not a unique key for a .s file ----------------------------
    #
    # _ASM_INDEX stored setdefault(f.stem, f): one path per NAME, first one the
    # directory walk reached. Seven function names in this tree have assembly
    # in more than one place, and six of them are live queue records:
    #
    #   EntityShaft      boss/bo6 and st/rcen -- BOTH in `todo`
    #   EntityUnkId1B    st/rcen  and st/rno0 -- BOTH in `todo`
    #   EntityBreakable  st/rchi  and st/rno0 -- rno0's is `deferred`
    #   func_801CE04C  } st/rno0 twice, giantbro_helpers vs unk_4A320,
    #   func_801CE120  } left over from the giantbro split. func_801CE3FC is
    #   func_801CE2CC  } `deferred` with a permuter score and func_801CE2CC
    #   func_801CE3FC  } has a live work dir under nonmatchings/.
    #
    # A delta computed against the wrong overlay's function does not fail. It
    # returns confident symbol renames and constant changes for two functions
    # that were never related, and transplant feeds them straight into --map.
    global _ASM_INDEX
    _saved = _ASM_INDEX
    try:
        a = REPO / "asm/us/st/rno0/nonmatchings/e_x/EntityDup.s"
        b = REPO / "asm/us/st/rchi/nonmatchings/e_x/EntityDup.s"
        c = REPO / "asm/us/st/rcen/nonmatchings/e_y/EntitySolo.s"
        _ASM_INDEX = {"EntityDup": [a, b], "EntitySolo": [c]}

        print("\nan ambiguous name resolves to NOTHING, not to walk order")
        ck(_find_asm("EntityDup") is None,
           "two overlays and no overlay named -> None")
        ck(_find_asm("EntityDup", "st/rno0") == a,
           "naming the overlay picks that one")
        ck(_find_asm("EntityDup", "st/rchi") == b,
           "and the other one, rather than whichever was indexed first")
        ck(_find_asm("EntityDup", "boss/bo6") is None,
           "an overlay that has no copy gets None, not a fallback")
        ck(_find_asm("EntitySolo") == c,
           "an unambiguous name still needs no overlay")

        print("\nand the refusal says what to pass")
        r = for_function("EntityDup", twin_name="EntitySolo")
        ck(not r["ok"] and "2 overlays" in r["reason"],
           f"the target ambiguity is named ({r['reason']})")
        ck("overlay=" in r["reason"], "with the parameter that resolves it")

        print("\noverlay keys derive from both kinds of path")
        ck(_asm_overlay(a) == "st/rno0", f"asm path ({_asm_overlay(a)})")
        ck(src_overlay("src/st/rno0/e_x.c") == "st/rno0",
           f"src path ({src_overlay('src/st/rno0/e_x.c')})")
        ck(src_overlay("src/boss/bo6/us_3E79C.c") == "boss/bo6",
           "a two-level overlay")
        ck(src_overlay("src/ric/319C4.c") == "ric",
           "and a one-level one, since depth varies")
    finally:
        _ASM_INDEX = _saved

    print("\nthe index holds FUNCTIONS, not data segments")
    # It walked every .s under asm/us, so st_common.data.s (36 overlays),
    # sprites.data.s (27) and rooms.data.s (31) were all in it. delta() would
    # have compared two data listings without complaint.
    src_self = Path(__file__).read_text(encoding="utf-8")
    ck('"/nonmatchings/" not in f.as_posix()' in src_self,
       "data segments are skipped when the index is built")
    real = asm_name_collisions()
    ck(not any(".data" in k or ".bss" in k or ".rodata" in k for k in real),
       f"so no data segment appears in the collision report ({list(real)[:3]})")

    print()
    if fails:
        print(f"{len(fails)} FAILED:")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--function")
    ap.add_argument("--overlay", default="",
                    help="disambiguate the TARGET when its name has asm in "
                         "more than one overlay, e.g. st/rno0")
    ap.add_argument("--twin-overlay", default="",
                    help="same, for the twin")
    ap.add_argument("--collisions", action="store_true",
                    help="list every function name whose .s exists in more "
                         "than one overlay. These are the names the index "
                         "used to resolve by walk order")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.collisions:
        c = asm_name_collisions()
        if not c:
            print("no asm filename collisions: every function name is unique "
                  "across overlays in this tree, today.")
            print("The index still keeps all matches and still refuses an "
                  "ambiguous lookup -- the guard is for the tree that exists "
                  "after the next upstream merge, not this one.")
            return 0
        print(f"{len(c)} function name(s) with .s in more than one overlay:\n")
        for k, v in c.items():
            print(f"  {k}")
            for p in v:
                print(f"      {p}")
        return 0
    if a.function:
        return report(a.function, a.overlay, a.twin_overlay)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
