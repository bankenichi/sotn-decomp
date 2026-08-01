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

    Every one of these is mechanically detectable, so they should be caught by a
    tool before a human ever reads the diff.

STRICTLY READ-ONLY. Never edits sources, never builds.

Usage:
    python3 automation/quality_audit.py                    # audit vs upstream
    python3 automation/quality_audit.py --since <commit>
    python3 automation/quality_audit.py --file src/boss/bo6/us_39144.c
    python3 automation/quality_audit.py --json report.json
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
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
               addr_to_name: dict | None = None) -> list[dict]:
    """Return a list of findings for one source file."""
    findings: list[dict] = []
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except OSError:
        return findings
    rel = str(path.relative_to(REPO))

    # Track the enclosing function so findings are actionable.
    cur_fn = "?"
    for i, line in enumerate(lines, 1):
        fm = re.match(r"^[A-Za-z_][\w \*]*\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{?\s*$", line)
        if fm:
            cur_fn = fm.group(1)
        if only_lines is not None and i not in only_lines:
            continue

        def add(kind, detail, fix):
            findings.append({"file": rel, "line": i, "function": cur_fn,
                             "kind": kind, "detail": detail, "fix": fix,
                             "code": line.strip()[:120]})

        # 1. invented externs that alias a real entity field
        for m in re.finditer(r"\bD_(?:us_)?[0-9A-Fa-f]{8}\b", line):
            real = resolve_fake_symbol(m.group(0), syms, layout, ent_size,
                                       addr_to_name)
            if real:
                add("fake_symbol", f"{m.group(0)} is {real}",
                    f"use {real} instead of declaring {m.group(0)}")

        # A line that is only a comment cannot contain a defect, just a mention
        # of one. Without this, the comment explaining WHY a site is
        # deliberately left as ext.ILLEGAL was itself reported as an
        # ext.ILLEGAL finding, so documenting a decision raised the count.
        stripped = line.strip()
        if stripped.startswith(("//", "/*", "*")):
            continue

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


def changed_lines_since(commit: str) -> dict[str, set[int]]:
    """file -> set of line numbers added since `commit`."""
    try:
        diff = subprocess.run(["git", "diff", "-U0", f"{commit}..HEAD", "--", "src/"],
                              cwd=REPO, capture_output=True, text=True,
                              timeout=120).stdout
    except (subprocess.SubprocessError, OSError):
        return {}
    out: dict[str, set[int]] = defaultdict(set)
    cur = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            cur = line[6:]
        elif line.startswith("@@") and cur:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if m:
                start = int(m.group(1))
                for n in range(start, start + int(m.group(2) or 1)):
                    out[cur].add(n)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default=UPSTREAM_DEFAULT,
                    help="audit only lines added since this commit")
    ap.add_argument("--file", default="", help="audit one file, whole")
    ap.add_argument("--all", action="store_true", help="audit all of src/, whole")
    ap.add_argument("--json", default="")
    ap.add_argument("--limit", type=int, default=40)
    a = ap.parse_args()

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
        changed = changed_lines_since(a.since)
        scope = []
        for rel, lines in changed.items():
            p = REPO / rel
            if not p.exists():
                continue
            scope.append(p)
            findings += check_file(p, syms, layout, ent_size, ext_variants,
                                   bits, only_lines=lines,
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
        [f for f in findings if f["kind"] != "duplicate"], a.since)
    if inherited:
        before = len(findings)
        findings = [f for f in findings
                    if f["kind"] == "duplicate"
                    or f["code"].strip() not in inherited]
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
        "duplicate":    "DUPLICATE        (already in tree)",
    }
    print(f"\n{'='*74}\nQUALITY AUDIT: {len(findings)} findings\n{'='*74}")
    for kind in ("fake_symbol", "duplicate", "illegal_ext", "raw_cast",
                 "magic_bitmask"):
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
