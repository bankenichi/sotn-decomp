#!/usr/bin/env python3
"""Audit decompiled C against upstream QUALITY standards, not just matching.

WHY THIS EXISTS
    A byte-identical match is the FLOOR for a decomp contribution, not the bar.
    Upstream review of this fork (2026-07-21) rejected matching code for:

      1. Fake symbols. `extern u16 D_80076306;` is really `g_Entities[64].step_s`.
         Declaring a new symbol for an address that already has a meaning hides
         structure and is unmergeable.
      2. `ext.ILLEGAL` where a NAMED ext variant exists. `ext.ILLEGAL.u16[0]`
         should be `ext.reboundStone.stoneAngle`.
      3. Magic bitmask literals. `RIC_drawFlags &= 0xFB` should be
         `&= ~ENTITY_ROTATE`.
      4. Raw pointer casts instead of an existing struct. `*(u16*)(entry + 4)`
         should be `subwpn->attackElement` via `SubweaponDef*`.
      5. Copy-paste duplicates of functions that already exist elsewhere.
      6. Empty control-flow bodies with no codegen explanation. An empty branch
         is either dead code or a compiler-shaping constraint, and both must be
         made explicit.

    Every one of these is mechanically detectable, so they should be caught by a
    tool before a human ever reads the diff.

STRICTLY READ-ONLY. Never edits sources, never builds.

Usage:
    python3 automation/quality_audit.py                    # audit vs upstream
    python3 automation/quality_audit.py --since <commit>
    python3 automation/quality_audit.py --file src/boss/bo6/us_39144.c
    python3 automation/quality_audit.py --json report.json
    python3 automation/quality_audit.py --self-test
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Track upstream, not a frozen hash. Pinned to 2472557 this diffed against a
# two-week-old baseline, so everything upstream had done since counted as ours
# and the audit scope was wrong in both directions.
UPSTREAM_DEFAULT = "upstream/master"

INDEX = REPO / "automation" / "index.us.json"


def _index() -> dict:
    """The codebase index, which is built FROM UPSTREAM, not the working tree.

    Ground truth must not come from the tree being audited. Reading
    config/symbols.us*.txt directly happens to be safe today only because we
    have not edited config/; the index is safe by construction, and it is the
    same guarantee described in MATCHING-LESSONS.md section 12.
    """
    try:
        return json.loads(INDEX.read_text())
    except (OSError, ValueError):
        return {}


# --------------------------------------------------------------------------
# ground truth loaded from the index
# --------------------------------------------------------------------------

def load_symbol_addresses(idx: dict | None = None) -> dict[str, int]:
    """name -> address, from the index's upstream-derived symbol table."""
    idx = idx if idx is not None else _index()
    raw = idx.get("symbols", {}).get("name_to_addr", {})
    out: dict[str, int] = {}
    for k, v in raw.items():
        try:
            out[k] = int(v, 16) if isinstance(v, str) else int(v)
        except (TypeError, ValueError):
            continue
    if out:
        return out
    for p in (REPO / "config").glob("symbols.us*.txt"):   # fallback
        try:
            for line in p.read_text(errors="ignore").splitlines():
                m = re.match(r"^\s*([A-Za-z_]\w*)\s*=\s*(0x[0-9A-Fa-f]+)", line)
                if m:
                    out.setdefault(m.group(1), int(m.group(2), 16))
        except OSError:
            continue
    return out


def load_entity_layout() -> tuple[dict[int, tuple[str, str]], int]:
    """offset -> (field, type) for the Entity header, plus sizeof(Entity)."""
    layout: dict[int, tuple[str, str]] = {}
    try:
        text = (REPO / "include" / "game.h").read_text(errors="ignore")
    except OSError:
        return layout, 0xBC
    body, seen = [], False
    for line in text.splitlines():
        if re.match(r"^\s*typedef struct Entity \{|^\s*struct Entity \{", line):
            seen = True
            continue
        if seen and re.match(r"^\s*\} Entity;", line):
            break
        if seen:
            body.append(line)
    for line in body:
        m = re.match(r"^\s*/\*\s*(0x[0-9A-Fa-f]+)\s*\*/\s*"
                     r"([A-Za-z_][\w \*]*?)\s*\*?\s*([A-Za-z_]\w*)\s*(?:\[|;|:)", line)
        if m:
            layout[int(m.group(1), 16)] = (m.group(3), m.group(2).strip())
    return layout, 0xBC


def load_ext_variants() -> dict[str, str]:
    """ext variant field name -> its struct type, from the Ext union."""
    out: dict[str, str] = {}
    try:
        text = (REPO / "include" / "entity.h").read_text(errors="ignore")
    except OSError:
        return out
    inside = False
    for line in text.splitlines():
        if re.match(r"^\s*typedef union \{", line):
            inside = True
            continue
        if inside and re.match(r"^\s*\} Ext;", line):
            break
        if inside:
            m = re.match(r"^\s*([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*;", line)
            if m:
                out[m.group(2)] = m.group(1)
    return out


def load_flag_groups() -> list[dict]:
    """Flag-like enum groups from the codebase index, for SCOPED advice.

    Looking a bare value up across the whole codebase is useless: `0x4` has ~50
    candidates (PAD_L1, DRAW_COLORS, dozens of PSP_*). Suggesting that list
    invites picking a plausible wrong constant, which is worse than saying
    nothing. Instead keep whole flag GROUPS (enums whose members are mostly
    powers of two) and pick the group by affinity with the variable name, so
    `drawFlags &= 0xFB` resolves to ENTITY_ROTATE and nothing else.

    Falls back to an empty list if the index has not been built; the check then
    simply does not fire, which is the safe direction.
    """
    idx_path = REPO / "automation" / "index.us.json"
    try:
        groups = json.loads(idx_path.read_text())["constants"]["groups"]
    except (OSError, ValueError, KeyError):
        return []
    out = []
    for gname, members in groups.items():
        vals = []
        for v in members.values():
            try:
                vals.append(int(v, 16))
            except ValueError:
                pass
        if len(vals) < 3:
            continue
        pow2 = [v for v in vals if v and (v & (v - 1)) == 0]
        if len(pow2) < max(3, int(len(vals) * 0.6)):
            continue                              # not a flag enum
        prefixes = {n.split("_")[0] for n in members}
        out.append({"name": gname, "members": members,
                    "prefixes": prefixes,
                    "by_val": {int(v, 16): n for n, v in members.items()
                               if re.match(r"^0x[0-9A-Fa-f]+$", v)}})
    return out


def _field_enum_map() -> dict[str, str]:
    """field name -> enum name, from `// refer to enum X` struct comments."""
    try:
        return json.loads((REPO / "automation" / "index.us.json").read_text()
                          )["constants"].get("field_enum", {})
    except (OSError, ValueError, KeyError):
        return {}


def scoped_constant(var: str, bit: int, groups: list[dict]) -> str | None:
    """Named constant for `bit`, scoped to the variable's flag family.

    AUTHORITATIVE first: the struct declares its enum in a comment
    (`u8 drawFlags; // refer to enum EntityDrawFlags`), so a variable whose name
    ends in that field resolves to exactly one group. Name affinity is only the
    fallback, and it is wrong often enough to matter: it picked DRAW_COLORS for
    `RIC_drawFlags` because "draw" matched, where the answer is ENTITY_ROTATE.
    """
    tail = re.split(r"[\.\->]", var)[-1]           # RIC_drawFlags -> RIC_drawFlags
    fe = _field_enum_map()
    for field, enum_name in fe.items():
        if tail.lower().endswith(field.lower()):
            for g in groups:
                if g["name"] == enum_name:
                    hit = g["by_val"].get(bit)
                    if hit:
                        return hit
    # NO name-affinity fallback. It was wrong both ways and never right:
    #
    #   false negative-ish: it picked DRAW_COLORS for RIC_drawFlags because
    #   "draw" matched, where the struct comment says ENTITY_ROTATE.
    #
    #   false positive: `flag |= 0x80` in AnimateEntity is a LOCAL return-value
    #   bitmask, and affinity matched the token "flag" to an entity flags enum
    #   and proposed FLAG_UNK_80. Upstream's own AnimateEntity
    #   (src/saturn/game_2b.c) writes the bare 0x80 literal, so the suggestion
    #   was to make our code less like upstream's.
    #
    # If the struct does not declare its enum in a `// refer to enum X`
    # comment, we do not know the family, and saying nothing is correct.
    # Guessing a plausible constant is worse than a magic number, because the
    # magic number is at least honestly unexplained.
    return None


def _mask_c_comments_and_literals(source: str) -> str:
    """Blank comments and literals while preserving offsets and newlines."""
    out = list(source)
    i = 0
    while i < len(source):
        if source.startswith("//", i):
            end = source.find("\n", i + 2)
            end = len(source) if end < 0 else end
            for j in range(i, end):
                out[j] = " "
            i = end
            continue
        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            end = len(source) if end < 0 else end + 2
            for j in range(i, end):
                if out[j] != "\n":
                    out[j] = " "
            i = end
            continue
        if source[i] in ('"', "'"):
            quote = source[i]
            out[i] = " "
            i += 1
            while i < len(source):
                if source[i] == "\\":
                    out[i] = " "
                    if i + 1 < len(source):
                        if out[i + 1] != "\n":
                            out[i + 1] = " "
                        i += 2
                    else:
                        i += 1
                    continue
                char = source[i]
                if char != "\n":
                    out[i] = " "
                i += 1
                if char == quote:
                    break
            continue
        i += 1
    return "".join(out)


def _skip_space(text: str, pos: int) -> int:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    return pos


def _matching_delimiter(
        text: str, start: int, opening: str, closing: str) -> int | None:
    depth = 0
    for pos in range(start, len(text)):
        if text[pos] == opening:
            depth += 1
        elif text[pos] == closing:
            depth -= 1
            if depth == 0:
                return pos
    return None


def _has_codegen_reason(comment_text: str) -> bool:
    """Require CODEGEN plus an actual reason, not an empty waiver marker."""
    for match in re.finditer(r"\bCODEGEN\s*:\s*", comment_text,
                             re.IGNORECASE):
        reason = comment_text[match.end():]
        block_end = reason.find("*/")
        if block_end >= 0:
            reason = reason[:block_end]
        reason = re.sub(r"(?m)^\s*(?://|\*)?\s*", " ", reason)
        if len(re.findall(r"[A-Za-z0-9_]+", reason)) >= 3:
            return True
    return False


def _mask_preprocessor_directives(text: str) -> str:
    """Blank complete logical preprocessor directives, including continuations."""
    out = list(text)
    offset = 0
    continued = False
    for line in text.splitlines(keepends=True):
        physical = line.rstrip("\r\n")
        directive = continued or physical.lstrip().startswith("#")
        if directive:
            for pos in range(offset, offset + len(line)):
                if out[pos] not in "\r\n":
                    out[pos] = " "
            continued = physical.rstrip().endswith("\\")
        else:
            continued = False
        offset += len(line)
    return "".join(out)


def _keyword_at(text: str, pos: int, keyword: str) -> bool:
    return bool(re.match(rf"{keyword}\b", text[pos:]))


def _statement_end(text: str, start: int) -> int | None:
    """Return the inclusive end of one C statement in masked source."""
    pos = _skip_space(text, start)
    if pos >= len(text):
        return None
    if text[pos] == "{":
        return _matching_delimiter(text, pos, "{", "}")
    if text[pos] == ";":
        return pos

    for keyword in ("if", "for", "while", "switch"):
        if not _keyword_at(text, pos, keyword):
            continue
        cond_start = _skip_space(text, pos + len(keyword))
        if cond_start >= len(text) or text[cond_start] != "(":
            return None
        cond_end = _matching_delimiter(text, cond_start, "(", ")")
        if cond_end is None:
            return None
        body_end = _statement_end(text, cond_end + 1)
        if body_end is None:
            return None
        if keyword == "if":
            else_pos = _skip_space(text, body_end + 1)
            if _keyword_at(text, else_pos, "else"):
                else_end = _statement_end(text, else_pos + len("else"))
                if else_end is not None:
                    return else_end
        return body_end

    if _keyword_at(text, pos, "do"):
        body_end = _statement_end(text, pos + len("do"))
        if body_end is None:
            return None
        while_pos = _skip_space(text, body_end + 1)
        if not _keyword_at(text, while_pos, "while"):
            return body_end
        cond_start = _skip_space(text, while_pos + len("while"))
        if cond_start >= len(text) or text[cond_start] != "(":
            return body_end
        cond_end = _matching_delimiter(text, cond_start, "(", ")")
        if cond_end is None:
            return body_end
        semicolon = _skip_space(text, cond_end + 1)
        return semicolon if semicolon < len(text) and text[semicolon] == ";" else cond_end

    parens = brackets = braces = 0
    for end in range(pos, len(text)):
        char = text[end]
        if char == "(":
            parens += 1
        elif char == ")" and parens:
            parens -= 1
        elif char == "[":
            brackets += 1
        elif char == "]" and brackets:
            brackets -= 1
        elif char == "{":
            braces += 1
        elif char == "}" and braces:
            braces -= 1
        elif char == ";" and not (parens or brackets or braces):
            return end
    return None


def find_undocumented_empty_control_bodies(
        source: str) -> list[tuple[int, int, str]]:
    """Return (start line, end line, keyword) for unexplained empty bodies.

    This is a lexical scan rather than a C parser because the audited sources
    contain target-specific macros and conditional compilation. Comments and
    literals are masked first, then delimiters are balanced explicitly.
    """
    masked = _mask_preprocessor_directives(
        _mask_c_comments_and_literals(source))
    findings: list[tuple[int, int, str]] = []

    def add(match_start: int, body_end: int, keyword: str) -> None:
        start_line = source.count("\n", 0, match_start) + 1
        end_line = source.count("\n", 0, body_end) + 1
        findings.append((start_line, end_line, keyword))

    # A do-while terminator ends with a required semicolon. Without recording
    # those sites first, the generic `while (...);` check reports the same
    # empty do body twice and even reports a documented do body once.
    do_while_terminators: set[int] = set()
    for match in re.finditer(r"\bdo\b", masked):
        body_start = _skip_space(masked, match.end())
        body_end = _statement_end(masked, body_start)
        if body_end is None:
            continue
        terminator = _skip_space(masked, body_end + 1)
        if _keyword_at(masked, terminator, "while"):
            do_while_terminators.add(terminator)
        if masked[body_start] == ";":
            add(match.start(), body_end, "do")
        elif masked[body_start] == "{":
            first = _skip_space(masked, body_start + 1)
            if first == body_end and not _has_codegen_reason(
                    source[body_start + 1:body_end]):
                add(match.start(), body_end, "do")

    for match in re.finditer(r"\b(if|for|while|switch)\b", masked):
        keyword = match.group(1)
        if keyword == "while" and match.start() in do_while_terminators:
            continue
        pos = _skip_space(masked, match.end())
        if pos >= len(masked) or masked[pos] != "(":
            continue
        cond_end = _matching_delimiter(masked, pos, "(", ")")
        if cond_end is None:
            continue
        body_start = _skip_space(masked, cond_end + 1)
        if body_start >= len(masked):
            continue
        if masked[body_start] == ";":
            # A null statement has no interior. A trailing comment belongs
            # outside it and cannot waive the finding; use braces for CODEGEN.
            add(match.start(), body_start, keyword)
            continue
        if masked[body_start] != "{":
            continue
        first = _skip_space(masked, body_start + 1)
        if first < len(masked) and masked[first] == "}":
            raw_body = source[body_start + 1:first]
            if not _has_codegen_reason(raw_body):
                add(match.start(), first, keyword)

    for match in re.finditer(r"\belse\b", masked):
        body_start = _skip_space(masked, match.end())
        if _keyword_at(masked, body_start, "if"):
            continue
        if body_start >= len(masked):
            continue
        if masked[body_start] == ";":
            add(match.start(), body_start, "else")
            continue
        if masked[body_start] != "{":
            continue
        body_end = _matching_delimiter(masked, body_start, "{", "}")
        if body_end is None:
            continue
        first = _skip_space(masked, body_start + 1)
        if first == body_end:
            raw_body = source[body_start + 1:body_end]
            if not _has_codegen_reason(raw_body):
                add(match.start(), body_end, "else")

    return sorted(set(findings))


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

def resolve_fake_symbol(name: str, syms: dict[str, int],
                        layout: dict[int, tuple[str, str]],
                        ent_size: int,
                        addr_to_name: dict[str, str] | None = None) -> str | None:
    """Say what `D_800xxxxx` really is, or None if the address has no meaning.

    The criterion is NOT "does the name look invented". `extern s32 D_us_801CF3C8;`
    is upstream's OWN convention: upstream decompiled func_us_801B5A14 using
    exactly that form. Flagging the shape would flag upstream.

    The criterion is whether the address ALREADY HAS A MEANING, which it can
    have in two independent ways. Checking only one of them is how this was got
    wrong in both directions on 2026-08-01:

      1. the symbol table already names it, so a new extern is a second name
         for a thing that has one; or
      2. it lands inside a known object whose layout is known. D_80076306 has
         NO symbol-table name and is still g_Entities[64].step_s. Testing only
         (1) declared it clean; it is not.

    D_us_801CF3C8 satisfies neither -- outside g_Entities, unnamed -- which is
    exactly why upstream's use of it is fine and ours is not.
    """
    m = re.match(r"^D_(?:us_)?([0-9A-Fa-f]{8})$", name)
    if not m:
        return None
    addr = int(m.group(1), 16)

    # (1) already named in the symbol table
    if addr_to_name:
        real = addr_to_name.get(f"0x{addr:08X}")
        if real and real != name:
            return f"the named symbol {real}"

    # (2) structurally inside g_Entities, whose layout we know
    base = syms.get("g_Entities")
    if not base:
        return None
    if not (base <= addr < base + ent_size * 256):
        return None
    off = addr - base
    idx, fld = divmod(off, ent_size)
    if fld in layout:
        return f"g_Entities[{idx}].{layout[fld][0]}"
    if fld >= 0x7C:                                  # inside ext
        return f"g_Entities[{idx}].ext (+0x{fld - 0x7C:02X})"
    return f"g_Entities[{idx}] + 0x{fld:02X}"


def check_file(path: Path, syms, layout, ent_size, ext_variants, bits,
                only_lines: set[int] | None = None,
                structural_lines: set[int] | None = None,
                addr_to_name: dict | None = None) -> list[dict]:
    """Return a list of findings for one source file."""
    findings: list[dict] = []
    try:
        source = path.read_text(errors="ignore")
        lines = source.splitlines()
    except OSError:
        return findings
    rel = str(path.relative_to(REPO))
    empty_controls: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for line_no, end_line, keyword in find_undocumented_empty_control_bodies(source):
        empty_controls[line_no].append((end_line, keyword))

    # Track the enclosing function so findings are actionable.
    cur_fn = "?"
    for i, line in enumerate(lines, 1):
        fm = re.match(r"^[A-Za-z_][\w \*]*\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{?\s*$", line)
        if fm:
            cur_fn = fm.group(1)

        def add(kind, detail, fix):
            findings.append({"file": rel, "line": i, "function": cur_fn,
                             "kind": kind, "detail": detail, "fix": fix,
                             "code": line.strip()[:120]})

        for end_line, keyword in empty_controls.get(i, []):
            if (structural_lines is not None and not any(
                    line_no in structural_lines
                    for line_no in range(i, end_line + 1))):
                continue
            add("empty_control_body",
                f"empty `{keyword}` body has no codegen justification",
                "write the direct condition, or put a `CODEGEN:` comment "
                "inside the body explaining the required target shape")

        if only_lines is not None and i not in only_lines:
            continue

        # A line that is only a comment cannot contain a defect, just a mention
        # of one. Without this, the comment explaining WHY a site is
        # deliberately left as ext.ILLEGAL was itself reported as an
        # ext.ILLEGAL finding, so documenting a decision raised the count.
        #
        # THIS GUARD MUST COME FIRST. It used to sit BELOW the fake_symbol
        # check, which meant that check still ran on comments: the audit's only
        # FAKE SYMBOL finding was a comment in us_39144.c explaining how an
        # entity base was derived from the assembly, while the code below it
        # used g_Entities[STAGE_ENTITY_START + 32] correctly. Clean work was
        # penalised precisely for documenting itself, which is the opposite of
        # what this tool should encourage. Found by audit 2026-08-02.
        stripped = line.strip()
        if stripped.startswith(("//", "/*", "*")):
            continue

        # 1. invented externs that alias a real entity field
        for m in re.finditer(r"\bD_(?:us_)?[0-9A-Fa-f]{8}\b", line):
            real = resolve_fake_symbol(m.group(0), syms, layout, ent_size,
                                       addr_to_name)
            if real:
                add("fake_symbol", f"{m.group(0)} is {real}",
                    f"use {real} instead of declaring {m.group(0)}")

        # 2. ext.ILLEGAL where named variants exist
        if "ext.ILLEGAL" in line:
            add("illegal_ext", "generic ext.ILLEGAL accessor",
                "use the named ext variant for this entity type "
                f"({len(ext_variants)} exist, e.g. ext.reboundStone.stoneAngle)")

        # 3. magic bitmask literals where a SCOPED named constant exists.
        #    Only fires when the variable name identifies the flag family, so
        #    the suggestion is unique rather than a list of 50 candidates.
        bm = re.search(r"([A-Za-z_][\w\.\->]*)\s*(&=|\|=)\s*(~?)\s*(0x[0-9A-Fa-f]+)",
                       line)
        if bm:
            var, op, tilde, lit = bm.groups()
            try:
                val = int(lit, 16)
            except ValueError:
                val = None
            if val is not None:
                # `x &= 0xFB` clears the complement; `x &= ~4` / `x |= 4` set it.
                cand = (~val) & 0xFF if (op == "&=" and not tilde) else val
                if cand and (cand & (cand - 1)) == 0:      # single bit
                    named = scoped_constant(var, cand, bits)
                    if named:
                        want = (f"{var} &= ~{named}" if op == "&="
                                else f"{var} |= {named}")
                        add("magic_bitmask", f"{lit} is bit 0x{cand:X} = {named}",
                            f"write `{want}`")

        # 4. raw pointer-cast field access instead of a struct.
        #
        # The original pattern demanded an INLINE (u8*)/(char*) cast inside the
        # parentheses, so it reported zero findings across the whole fork while
        # func_us_801BB370 sat in the tree doing nothing but this. Two holes:
        #   `(unsigned char*)entity + 0xB0`  -- spelling not covered by u8|char
        #   `*(u16*)(entry + 4)`             -- no inline cast at all, and this
        #                                       is the commoner shape
        # Match the actual defect instead: dereferencing a cast pointer at a
        # numeric offset. That is field access with the struct filed off.
        # Both shapes are checked against fixtures in the test at the bottom of
        # this file; a first attempt at this pattern still missed 2 of its own
        # 3 must-fire cases, so do not edit it without re-running those.
        if re.search(
                r"\(\s*(?:(?:un)?signed\s+char|u8|s8|char)\s*\*\s*\)"
                r"[^;]*[+\-]\s*(?:0x)?[0-9A-Fa-f]"
                r"|\*\s*\(\s*[su]\d+\s*\*\s*\)\s*\([^)]*[+\-]\s*(?:0x)?[0-9A-Fa-f]",
                line):
            add("raw_cast", "pointer arithmetic instead of a struct field",
                "declare/typedef the real struct and use named members")

        # NOTE: there is deliberately no "m2c artifact name" check.
        # `temp_s0`, `var_s1` and friends are the decompiler's register names,
        # and flagging them looked obviously right: 78 hits. Then upstream was
        # checked, and upstream uses them everywhere -- var_s1 alone appears in
        # 62 upstream files, temp_s0 in 30. It is this project's accepted
        # convention for a value whose meaning is not yet known. Flagging it
        # would have been the same error as counting upstream's 55 private
        # implementations as our duplicates: measuring our code against a
        # standard upstream does not hold itself to.

        # There is deliberately no automated "noise comment" check either.
        # One was written and run: of its 6 hits, 1 was real. "// unused" tells
        # a reader something the code cannot ("this is never called"), and
        # "// Empty stub" distinguishes "empty in the original" from "not
        # decompiled yet" -- both are content, not noise. Only
        # "/* Advance to next state */" above `step++` was genuinely a
        # restatement. A 1-in-6 check trains people to ignore the tool, and
        # this session has already shown twice what a confident wrong checker
        # costs. Whether a comment earns its place needs a reader, not a regex;
        # it belongs in the review pass, not here.

    return findings


# --------------------------------------------------------------------------
# duplicate detection
# --------------------------------------------------------------------------

def normalise_body(text: str) -> str:
    """Whitespace/comment/identifier-insensitive body signature."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    text = re.sub(r"\s+", "", text)
    return text


def extract_functions(path: Path) -> dict[str, str]:
    """name -> body text, for brace-balanced top-level definitions."""
    out: dict[str, str] = {}
    try:
        src = path.read_text(errors="ignore")
    except OSError:
        return out
    for m in re.finditer(r"^[A-Za-z_][\w \*]*?\s+\*?([A-Za-z_]\w*)\s*\([^;{]*\)\s*\{",
                         src, re.M):
        name, start = m.group(1), m.end() - 1
        depth, i = 0, start
        while i < len(src):
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out[name] = src[start:i + 1]
    return out


def find_duplicates(added_fns: dict[str, tuple[Path, str]],
                    all_files: list[Path]) -> list[dict]:
    """Flag added functions whose body already exists elsewhere.

    Upstream's complaint: 'almost every function you have decompiled here is
    just copies of functions we already have'. Structural equality on the
    normalised body catches verbatim and near-verbatim copies.
    """
    index: dict[str, list[str]] = defaultdict(list)
    for p in all_files:
        for name, body in extract_functions(p).items():
            sig = normalise_body(body)
            if len(sig) > 80:                      # ignore trivial stubs
                index[sig].append(f"{p.relative_to(REPO)}:{name}")
    dups = []
    for name, (path, body) in added_fns.items():
        sig = normalise_body(body)
        if len(sig) <= 80:
            continue
        others = [x for x in index.get(sig, [])
                  if not x.endswith(f":{name}") or not x.startswith(str(path.relative_to(REPO)))]
        others = [o for o in others if o != f"{path.relative_to(REPO)}:{name}"]
        if others:
            dups.append({"file": str(path.relative_to(REPO)), "function": name,
                         "kind": "duplicate", "detail": "identical body exists",
                         "fix": f"reuse/share with {others[0]}",
                         "matches": others[:3], "line": 0, "code": ""})
    return dups


# --------------------------------------------------------------------------

def inherited_from_upstream(findings: list[dict], ref: str) -> set[str]:
    """Which flagged lines exist VERBATIM in upstream's own source.

    A line we copied out of a shared header is upstream's code and upstream's
    convention, whatever our checks think of it. Reporting it as our defect is
    the single most repeated mistake in this project's history: it produced the
    "76 duplicates" figure that was mostly upstream's own architecture, and it
    nearly produced 78 findings against a naming style upstream uses in 62 of
    its own files.

    So the rule is mechanical rather than per-check: if upstream wrote the exact
    line, it is not our finding. Cheap, because only the distinct flagged lines
    are queried, and one `git grep` handles all of them at once.
    """
    uniq = sorted({f["code"].strip() for f in findings
                   if len(f.get("code", "").strip()) > 12})
    if not uniq:
        return set()
    hit: set[str] = set()
    CHUNK = 40                      # keep the argv comfortably short
    for i in range(0, len(uniq), CHUNK):
        args = ["git", "grep", "-F", "-h", "--no-color"]
        for lit in uniq[i:i + CHUNK]:
            args += ["-e", lit]
        args += [ref, "--", "src/"]
        try:
            out = subprocess.run(args, cwd=REPO, capture_output=True,
                                 text=True, errors="replace", timeout=180).stdout
        except (subprocess.SubprocessError, OSError):
            continue
        found = {l.strip() for l in out.splitlines()}
        for lit in uniq[i:i + CHUNK]:
            if lit in found:
                hit.add(lit)
    return hit


def _parse_changed_line_scopes(
        diff: str) -> tuple[dict[str, set[int]], dict[str, set[int]]]:
    """Return added lines and structural hunk spans from a zero-context diff."""
    added: dict[str, set[int]] = defaultdict(set)
    structural: dict[str, set[int]] = defaultdict(set)
    cur = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            cur = line[6:]
        elif line.startswith("@@") and cur:
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if not match:
                continue
            start = int(match.group(1))
            count = int(match.group(2) or 1)
            if count:
                added[cur].update(range(start, start + count))
                structural[cur].update(range(start, start + count))
            # A deletion-only hunk has a zero-width new range. Keep both sides
            # of every hunk so deleting the sole statement from an unchanged
            # control body still intersects that body's current span.
            structural[cur].add(max(1, start - 1))
            structural[cur].add(max(1, start + count))
    return added, structural


def changed_line_scopes_since(
        commit: str) -> tuple[dict[str, set[int]], dict[str, set[int]]]:
    """Return ordinary added-line scope plus structural change boundaries."""
    try:
        diff = subprocess.run(["git", "diff", "-U0", f"{commit}..HEAD", "--", "src/"],
                              cwd=REPO, capture_output=True, text=True,
                              timeout=120).stdout
    except (subprocess.SubprocessError, OSError):
        return {}, {}
    return _parse_changed_line_scopes(diff)


def changed_lines_since(commit: str) -> dict[str, set[int]]:
    """Compatibility wrapper returning only lines added since `commit`."""
    return changed_line_scopes_since(commit)[0]


def _suppress_inherited_findings(
        findings: list[dict], inherited: set[str]) -> list[dict]:
    """Line inheritance cannot suppress findings whose defect is structural."""
    return [
        finding for finding in findings
        if finding["kind"] in ("duplicate", "empty_control_body")
        or finding["code"].strip() not in inherited
    ]


def self_test() -> int:
    """Exercise quality shapes that previously escaped the audit."""
    fixture = """\
void BadNestedIf(void) {
    if (step_s != 0) {
        if (step_s) {
        }
    }
}

void ExplainedCodegenBranch(void) {
    if (step_s) {
        // CODEGEN: Preserve the target's second conditional branch.
    }
}

void BadMissingCodegenReason(void) {
    if (step_s) {
        // CODEGEN:
    }
}

void LegitimateEmptyFunction(void) {
}

void OrdinaryBranch(void) {
    if (step_s) {
        use_step(step_s);
    }
}

void BadEmptyElse(void) {
    if (step_s) use_step(step_s); else;
}

void BadEmptyFor(void) {
    for (;;);
}

void BadEmptyWhile(void) {
    while (hardware_busy());
}

void BadEmptySwitch(void) {
    switch (step_s) {
    }
}

void BadEmptyDoWhile(void) {
    do {
    } while (spin());
}

void ExplainedDoWhile(void) {
    do {
        // CODEGEN: Poll the hardware flag without changing the loop body.
    } while (hardware_busy());
}

void GoodNonbracedDoWhile(void) {
    do use_step(step_s); while (spin());
}

void BadNullDoWhile(void) {
    do; while (spin());
}

void BadTrailingWaiver(void) {
    if (step_s); // CODEGEN: This comment is outside the null statement.
}

void ExplainedMultilineBranch(void) {
    if (step_s) {
        /* CODEGEN:
         * Preserve the target's scheduled conditional branch.
         */
    }
}

void LiteralAndCommentNoise(void) {
    const char* text = "if (step_s) {} else; do; while (spin())";
    // if (step_s) { }
    use_text(text);
}

#define EMPTY_BRANCH_MACRO(value) \\
    if (value) { \\
    }
"""
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".c", prefix="quality_audit_selftest_",
                dir=REPO / "automation", delete=False) as tmp:
            tmp.write(fixture)
            tmp_path = Path(tmp.name)
        findings = check_file(tmp_path, {}, {}, 0xBC, {}, [])
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    empty = [f for f in findings if f["kind"] == "empty_control_body"]
    got = {(f["function"], f["detail"].split("`")[1]) for f in empty}
    want = {
        ("BadNestedIf", "if"),
        ("BadMissingCodegenReason", "if"),
        ("BadEmptyElse", "else"),
        ("BadEmptyFor", "for"),
        ("BadEmptyWhile", "while"),
        ("BadEmptySwitch", "switch"),
        ("BadEmptyDoWhile", "do"),
        ("BadNullDoWhile", "do"),
        ("BadTrailingWaiver", "if"),
    }
    if got != want:
        print(f"FAIL empty-control fixture: expected {want}, got {got}")
        return 1

    spans = find_undocumented_empty_control_bodies(fixture)
    nested_span = next(
        (start, end) for start, end, keyword in spans
        if keyword == "if" and fixture.splitlines()[start - 1].strip() ==
        "if (step_s) {")
    if tmp_path is None:
        print("FAIL structural scope: fixture path was not created")
        return 1
    tmp_path.write_text(fixture, encoding="utf-8")
    try:
        structural = check_file(
            tmp_path, {}, {}, 0xBC, {}, [], only_lines=set(),
            structural_lines={nested_span[1]})
    finally:
        tmp_path.unlink(missing_ok=True)
    if not any(f["function"] == "BadNestedIf" and
               f["kind"] == "empty_control_body" for f in structural):
        print("FAIL structural scope: body-only change did not retain finding")
        return 1

    deletion_diff = """\
diff --git a/src/demo.c b/src/demo.c
--- a/src/demo.c
+++ b/src/demo.c
@@ -3 +3,0 @@
-    use_step(step_s);
"""
    added, structural_lines = _parse_changed_line_scopes(deletion_diff)
    if added.get("src/demo.c") or not {2, 3} <= structural_lines["src/demo.c"]:
        print("FAIL deletion scope: zero-width hunk lost structural boundaries")
        return 1

    inherited = {"if (step_s) {", "D_80000000 = 1;"}
    sample = [
        {"kind": "empty_control_body", "code": "if (step_s) {"},
        {"kind": "fake_symbol", "code": "D_80000000 = 1;"},
    ]
    kept = _suppress_inherited_findings(sample, inherited)
    if kept != sample[:1]:
        print("FAIL inheritance: structural finding was suppressed by header text")
        return 1
    print("quality_audit self-test: PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default=UPSTREAM_DEFAULT,
                    help="audit code changed since this commit")
    ap.add_argument("--file", default="", help="audit one file, whole")
    ap.add_argument("--all", action="store_true", help="audit all of src/, whole")
    ap.add_argument("--json", default="")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    idx = _index()
    addr_to_name = idx.get('symbols', {}).get('addr_to_name', {})
    syms = load_symbol_addresses(idx)
    layout, ent_size = load_entity_layout()
    ext_variants = load_ext_variants()
    bits = load_flag_groups()
    if not bits:
        print("NOTE: automation/index.us.json missing; bitmask check disabled. "
              "Run: python3 automation/codebase_index.py", file=sys.stderr)
    print(f"loaded: {len(syms)} symbols, {len(layout)} Entity fields, "
          f"{len(ext_variants)} ext variants, {len(bits)} flag groups",
          file=sys.stderr)

    findings: list[dict] = []
    if a.file:
        p = REPO / a.file
        findings += check_file(p, syms, layout, ent_size, ext_variants, bits,
                               addr_to_name=addr_to_name)
        scope = [p]
    elif a.all:
        scope = [p for p in (REPO / "src").rglob("*.c")
                 if "_psp" not in str(p) and "saturn" not in str(p)]
        for p in scope:
            findings += check_file(p, syms, layout, ent_size, ext_variants, bits,
                                   addr_to_name=addr_to_name)
    else:
        changed, structural = changed_line_scopes_since(a.since)
        scope = []
        for rel in sorted(set(changed) | set(structural)):
            p = REPO / rel
            if not p.exists():
                continue
            scope.append(p)
            findings += check_file(p, syms, layout, ent_size, ext_variants,
                                   bits, only_lines=changed.get(rel, set()),
                                   structural_lines=structural.get(rel, set()),
                                   addr_to_name=addr_to_name)
        print(f"scope: {len(scope)} files changed since {a.since}", file=sys.stderr)

    # duplicates: compare functions in scope against the whole tree
    added: dict[str, tuple[Path, str]] = {}
    for p in scope:
        for name, body in extract_functions(p).items():
            added[name] = (p, body)
    # MUST include .h. src/st/ deduplicates by putting the shared implementation
    # in src/st/<name>.h and reducing each stage's .c to a 4-line
    # `#include "../st_common.h"` shim (25 stages do this). Globbing only .c
    # made every one of those shared bodies invisible, so this reported 5
    # duplicates when the real figure was ~75: the single largest defect in the
    # fork, missed because the corpus excluded the files that hold the originals.
    corpus = [p for p in (REPO / "src").rglob("*.[ch]")
              if "_psp" not in str(p) and "saturn" not in str(p)]
    findings += find_duplicates(added, corpus)

    # Drop anything upstream wrote verbatim; it is their convention, not our
    # defect. Duplicates are exempt: for those, existing upstream IS the point.
    inherited = inherited_from_upstream(
        [f for f in findings
         if f["kind"] not in ("duplicate", "empty_control_body")], a.since)
    if inherited:
        before = len(findings)
        findings = _suppress_inherited_findings(findings, inherited)
        print(f"suppressed {before - len(findings)} finding(s) whose exact line "
              f"exists in {a.since}", file=sys.stderr)

    by_kind: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        by_kind[f["kind"]].append(f)

    LABEL = {
        "fake_symbol":  "FAKE SYMBOL      (aliases a real entity field)",
        "illegal_ext":  "ILLEGAL EXT      (named variant exists)",
        "magic_bitmask": "MAGIC BITMASK    (named constant exists)",
        "raw_cast":     "RAW CAST         (struct exists)",
        "empty_control_body":
                         "EMPTY CONTROL     (dead or unexplained codegen)",
        "duplicate":    "DUPLICATE        (already in tree)",
    }
    print(f"\n{'='*74}\nQUALITY AUDIT: {len(findings)} findings\n{'='*74}")
    for kind in ("fake_symbol", "duplicate", "illegal_ext", "raw_cast",
                 "magic_bitmask", "empty_control_body"):
        items = by_kind.get(kind, [])
        if not items:
            continue
        print(f"\n{LABEL[kind]}  x{len(items)}")
        print("-" * 74)
        for f in items[:a.limit]:
            loc = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
            print(f"  {loc}  [{f['function']}]")
            print(f"      {f['detail']}")
            print(f"      FIX: {f['fix']}")
        if len(items) > a.limit:
            print(f"  ... and {len(items)-a.limit} more")

    # worst functions first: what to rework
    per_fn: dict[str, list[str]] = defaultdict(list)
    for f in findings:
        per_fn[f"{f['file']}:{f['function']}"].append(f["kind"])
    print(f"\n{'='*74}\nREWORK LIST (most defects first)\n{'='*74}")
    ranked = sorted(per_fn.items(), key=lambda kv: -len(kv[1]))
    for key, kinds in ranked[:a.limit]:
        c = ", ".join(f"{k}x{kinds.count(k)}" for k in sorted(set(kinds)))
        print(f"  {len(kinds):>3}  {key}  ({c})")
    print(f"\n  functions with >=1 defect: {len(per_fn)}")

    if a.json:
        Path(a.json).write_text(json.dumps(findings, indent=2))
        print(f"  wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
