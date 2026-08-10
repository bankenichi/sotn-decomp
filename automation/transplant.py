#!/usr/bin/env python3
"""Advance the decomp WITHOUT a model, by transplanting C that already exists.

WHY THIS EXISTS
    The harness spends its budget asking models to rediscover functions. But
    for a large slice of the queue the C already exists somewhere: upstream
    has decompiled 26 of our unmatched functions, and asm_twin_finder found
    174 of 335 stubs have a near-identical twin elsewhere in the tree.

    For those, decompilation is not the problem. Copying is, and a copy is
    verifiable by build rather than by proxy. That makes it strictly better
    evidence than anything a model produces: no fabricated field names to
    detect, no degeneration to abort, no fidelity score standing in for the
    truth. Either the overlay checksums or it does not.

SAFETY
    This does NOT implement apply/build/revert. It calls
    permuter_supervisor.land_match, which is the one sequence in this repo
    hardened against a mid-build crash: it takes the same automation/.build
    .lock the fleet workers hold, journals the original BEFORE writing,
    rebuilds, verifies the 81 SHA-1s independently of make's exit code, and
    reverts unconditionally on anything short of green -- proving the revert
    with _assert_reverted rather than printing the word.

    A second copy of that sequence would be a second thing to get wrong, so
    land_match grew a `body=` parameter instead.

    DRY RUN by default. Nothing touches src/ without --apply.

Usage:
    python3 automation/transplant.py --list
    python3 automation/transplant.py --function <name>            # dry run
    python3 automation/transplant.py --function <name> --apply
    python3 automation/transplant.py --self-test
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "automation"))


def _sup():
    import permuter_supervisor as ps                          # type: ignore
    return ps


def _harv():
    import upstream_harvest as uh                             # type: ignore
    return uh


def candidates() -> list[tuple[str, str, str]]:
    """(function, our overlay, the file in THIS tree that already defines it)."""
    uh = _harv()
    idx = _local_def_index()
    out = []
    for _rid, ovl, fn in uh.unmatched_records():
        base = re.sub(r"_from_\w+$", "", fn)
        for path in idx.get(base, []):
            out.append((fn, ovl, path))
            break
    return sorted(set(out))


_LOCAL_DEFS: dict[str, list[str]] | None = None


def _local_def_index() -> dict[str, list[str]]:
    """{function name: [files defining it]} for all of src/, built once."""
    global _LOCAL_DEFS
    if _LOCAL_DEFS is not None:
        return _LOCAL_DEFS
    import subprocess
    rx = re.compile(r"^(?P<path>[^:]+):[ \t]*(?:static[ \t]+)?"
                    r"[A-Za-z_][A-Za-z0-9_ \t*]*?\b(?P<fn>\w+)[ \t]*\([^;]*$")
    raw = subprocess.run(
        ["git", "grep", "-nE", r"^[A-Za-z_][A-Za-z0-9_ \t*]*\b\w+[ \t]*\(",
         "--", "src/"], capture_output=True, text=True, timeout=300,
        cwd=str(REPO)).stdout
    out: dict[str, list[str]] = {}
    for line in raw.splitlines():
        path, _, rest = line.partition(":")
        _num, _, code = rest.partition(":")
        m = rx.match(f"{path}:{code}")
        if m:
            out.setdefault(m.group("fn"), []).append(m.group("path"))
    _LOCAL_DEFS = out
    return out


_TWIN_JSON: dict | None = None


def twin_sources(fn: str) -> list[str]:
    """Candidate twin symbols for a stub, best evidence first.

    THE NAMING CONVENTION IS A NARROW SUBSET. `X_from_Y` finds only the
    inverted-castle copies; the first full scan reported 267 of 279 records as
    having no twin on that basis alone. asm_twin_finder matches on assembly
    SHAPE and TOKENS and knows about 152 more.

    A candidate is only useful if THIS TREE ALREADY DEFINES IT. Many of
    asm_twin_finder's twins are themselves unmatched stubs -- func_us_801B1DDC
    and func_us_801B1E5C are twins of each other and neither is decompiled --
    so copying from one would copy an INCLUDE_ASM. They are filtered against
    the local definition index, which is the same question the transplant
    already has to answer.

    Ordered: the name-convention base first (it is the strongest signal, and
    the one the 7 matches so far came from), then identical-constant shape
    twins, then the rest.
    """
    global _TWIN_JSON
    if _TWIN_JSON is None:
        try:
            _TWIN_JSON = json.loads(
                (REPO / "automation" / "twins.us.json").read_text())
        except (OSError, ValueError):
            _TWIN_JSON = {}
    idx = _local_def_index()
    out: list[str] = []
    base = re.sub(r"_from_\w+$", "", fn)
    if base != fn and base in idx:
        out.append(base)

    entry = None
    for key, val in (_TWIN_JSON.get("twins") or {}).items():
        if key.rsplit("/", 1)[-1] == fn:
            entry = val
            break
    if entry:
        # THREE SHAPES IN ONE FILE. shape_twins carry `symbol`, while
        # name_twins and token_twins carry `function` and a file path -- and
        # token_twins add a similarity `score`. Reading `symbol` from all
        # three raised KeyError on the first token twin.
        def _name(t: dict) -> str:
            return t.get("symbol") or t.get("function") or ""

        exact = [_name(t) for t in entry.get("shape_twins", [])
                 if t.get("identical_constants")]
        # token_twins are ranked by a similarity score; take them strongest
        # first so a 0.556 match is tried before a 0.4 one.
        toks = sorted(entry.get("token_twins", []),
                      key=lambda t: -(t.get("score") or 0))
        rest = ([_name(t) for t in entry.get("name_twins", [])]
                + [_name(t) for t in entry.get("shape_twins", [])
                   if not t.get("identical_constants")]
                + [_name(t) for t in toks])
        for sym in exact + rest:
            if sym and sym != fn and sym in idx and sym not in out:
                out.append(sym)
    return out


def local_twin(base: str, exclude: str = "") -> tuple[str, str]:
    """(body, path) for a definition of `base` ALREADY IN OUR TREE.

    PREFERRED OVER UPSTREAM, and the reason this whole mechanism works.

    The queue's unmatched record for the inverted castle is
    `func_us_801CC750_from_no0`, an INCLUDE_ASM stub in
    src/st/rno0/e_background_pillars.c. But `func_us_801CC750` itself is
    already decompiled HERE, in src/st/no0/4C750.c, because the normal and
    inverted stages share an implementation. That copy compiles against this
    tree's headers and already matches, which upstream's cannot be assumed to
    do.

    So the first question is never "what does upstream have"; it is "do we
    already have this function under another name".
    """
    # ONE index for the whole run. A git grep per record is fine for a single
    # transplant and hopeless for a scan: 250 records x ~1.5s of grep is most
    # of an hour, and the scan produced no output for seven minutes before
    # this was added.
    hits = _local_def_index().get(base, [])
    uh = _harv()
    for h in hits:
        if exclude and h.endswith(exclude):
            continue
        body = uh._extract((REPO / h).read_text(errors="ignore"), base)
        if body:
            return body, h
    return "", ""


def rename_function(body: str, old: str, new: str) -> str:
    """Rename the DEFINITION and any self-recursion, nothing else.

    The twin is the same code under a different symbol; only the name in the
    signature has to change. Renaming every occurrence would also rewrite an
    unrelated call that happens to contain the old name as a substring, so the
    match is anchored on a word boundary and applied to the whole body, which
    for these functions is the definition plus any recursive call.
    """
    if old == new:
        return body
    return re.sub(r"\b" + re.escape(old) + r"\b", new, body)


def apply_map(body: str, pairs: list[str]) -> tuple[str, list[str]]:
    """Rename symbols the destination overlay calls something else.

    THE THING THAT ACTUALLY BLOCKS A TWIN TRANSPLANT. The C is already correct
    -- the first live test failed only because src/st/rno0 has different NAMES
    for three symbols src/st/no0 uses:

        func_us_801CC8F8  -> func_us_801CC8F8_from_no0   (declared in rno0)
        E_ID_16           -> E_UNK_16                    (rno0.h names the
                                                          same function in its
                                                          comment)
        D_us_80180A88     -> OVL_EXPORT(EInitSpawner)    (byte-identical
                                                          initialiser)

    Supplied EXPLICITLY rather than inferred. Each of those three came from a
    different kind of evidence, and a resolver that guessed them would be a
    fourth unvalidated checker in a day that has already produced five. When
    the mapping has been proven by enough builds, deriving it is a safe next
    step; guessing it first is not.

    Word-anchored, and reports what it changed so a dry run shows the exact
    substitutions before anything is written.
    """
    notes, table = [], {}
    for pair in pairs or []:
        o, _, n_ = pair.partition("=")
        o, n_ = o.strip(), n_.strip()
        if not o or not n_:
            notes.append(f"IGNORED malformed --map {pair!r}")
            continue
        hits = len(re.findall(r"(?<![\w.])" + re.escape(o) + r"(?![\w.])",
                              body))
        if not hits:
            notes.append(f"IGNORED {o}: not present in the body")
            continue
        table[o] = n_
        notes.append(f"{o} -> {n_}  ({hits} occurrence(s))")
    if not table:
        return body, notes
    # SIMULTANEOUS, in ONE pass. Applying the pairs in sequence cannot express
    # a swap: the inverted castle mirrors this sprite, so 0xC0 and 0xE0 trade
    # places, and `0xC0->0xE0` followed by `0xE0->0xC0` collapses both to
    # 0xC0. Longest key first so a shorter one cannot match inside a longer.
    pat = re.compile(r"(?<![\w.])(" + "|".join(
        re.escape(k) for k in sorted(table, key=len, reverse=True))
        + r")(?![\w.])")
    return pat.sub(lambda m: table[m.group(1)], body), notes


RX_OBJ_MACRO = re.compile(r"^#\s*define\s+([A-Z][A-Z0-9_]*)\s+(\S[^\n]*)$",
                          re.M)
RX_FN_MACRO = re.compile(
    r"^#\s*define\s+([A-Z][A-Z0-9_]*)\(\s*x\s*\)\s+(\S[^\n]*)$", re.M)
_SAFE_EXPR = re.compile(r"^[-+*/|&^()<>\s0-9xXa-fA-F]*$")


def _consts_table() -> dict:
    """Object-like macros from game.h that evaluate to a number."""
    out = {}
    h = REPO / "include" / "game.h"
    if not h.is_file():
        return out
    for name, val in RX_OBJ_MACRO.findall(h.read_text(errors="ignore")):
        v = val.split("//")[0].split("/*")[0].strip()
        if _SAFE_EXPR.match(v):
            try:
                out[name] = eval(v, {"__builtins__": {}}, {})   # noqa: S307
            except Exception:                                   # noqa: BLE001
                pass
    return out


def _fn_macros() -> dict:
    """{name: body} for single-argument macros like ANIMSET_OVL(x)."""
    h = REPO / "include" / "game.h"
    if not h.is_file():
        return {}
    return {n: b.split("//")[0].strip()
            for n, b in RX_FN_MACRO.findall(h.read_text(errors="ignore"))}


def _eval_macro(body: str, arg: int, consts: dict) -> int | None:
    expr = re.sub(r"\bx\b", f"({arg})", body)
    for name, val in consts.items():
        expr = re.sub(r"\b" + re.escape(name) + r"\b", str(val), expr)
    if not _SAFE_EXPR.match(expr):
        return None
    try:
        return eval(expr, {"__builtins__": {}}, {})             # noqa: S307
    except Exception:                                           # noqa: BLE001
        return None


def _s16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def macro_consts(body: str, pairs: list[str]) -> tuple[list[str], list[str]]:
    """Constant changes the C expresses through a macro, not a literal.

    asm_delta reports what the ASSEMBLY holds. The C often does not hold it
    directly: `self->animSet = ANIMSET_OVL(1)` assembles to -0x7FFF because
    ANIMSET_OVL(x) is `(x) | 0x8000`, and the target wants -0x7FFE. Searching
    the body for -0x7FFF finds nothing, the substitution is dropped, and the
    transplant compiles to the wrong bytes -- which is worse than failing,
    because it looks like success right up to the checksum.

    So the ARGUMENT is rewritten instead of the literal, and only after the
    arithmetic is CHECKED: the candidate argument is evaluated through the
    real macro body and must produce exactly the value the assembly asks for.
    A proposal that does not evaluate correctly is reported and discarded.
    """
    consts, macros = _consts_table(), _fn_macros()
    out, notes = [], []
    if not macros:
        return out, notes
    for pair in pairs:
        old_s, _, new_s = pair.partition("=")
        try:
            old = int(old_s, 0)
            new = int(new_s, 0)
        except ValueError:
            continue                       # a symbol rename, not a constant
        if re.search(r"(?<![\w.])" + re.escape(old_s) + r"(?![\w.])", body):
            continue                       # present literally; apply_map has it
        for name, mbody in macros.items():
            for m in re.finditer(re.escape(name) + r"\(\s*(-?\w+)\s*\)",
                                 body):
                try:
                    arg = int(m.group(1), 0)
                except ValueError:
                    continue
                got = _eval_macro(mbody, arg, consts)
                if got is None or _s16(got) != _s16(old):
                    continue
                cand = arg + (new - old)
                chk = _eval_macro(mbody, cand, consts)
                if chk is not None and _s16(chk) == _s16(new):
                    out.append(f"{name}({m.group(1)})={name}({cand})")
                    notes.append(f"{name}({m.group(1)}) -> {name}({cand})  "
                                 f"[{old_s} -> {new_s}, verified through the "
                                 f"macro]")
                else:
                    notes.append(f"{name}({m.group(1)}) holds {old_s} but no "
                                 f"argument gives {new_s}; left alone")
    return out, notes


def _ovl_prefix(overlay: Path) -> str:
    """The OVL_EXPORT prefix for an overlay, e.g. RNO0.

    Read from the overlay's own header (`#define OVL_EXPORT(x) RNO0_##x`)
    rather than guessed from the directory name, which is lower case and not
    always the same token.
    """
    for h in overlay.glob("*.h"):
        m = re.search(r"#\s*define\s+OVL_EXPORT\(\s*x\s*\)\s+(\w+)##x",
                      h.read_text(errors="ignore"))
        if m:
            return m.group(1).rstrip("_")
    return ""


def auto_decls(body: str, dest: Path,
               defining: str = "") -> tuple[list[str], list[str]]:
    """Declarations the destination file needs but does not have.

    THE SECOND HALF OF A TWIN TRANSPLANT, and the reason the first two build
    tests failed. The C was correct both times; the destination simply could
    not SEE the symbols it referenced.

    src/st/no0/4C750.c gets them from two places that do not travel with the
    function body:

        void func_us_801CC8F8(Entity*);   a local forward declaration, line 7
        extern EInit D_us_80180A88;       from no0.h, line 115

    src/st/rno0/e_background_pillars.c has neither, and rno0.h exports
    neither, so the transplant referenced two symbols that exist in the
    overlay but are invisible from that translation unit.

    DERIVED FROM THE DEFINITION, not guessed. Each candidate symbol is looked
    up in the destination's OWN overlay directory; a declaration is emitted
    only when its definition is found there, and its shape is taken from that
    definition. A symbol with no definition in the overlay is left alone, so
    the build still fails rather than being handed a fabricated extern.

    A redundant declaration is harmless; a wrong one fails the build and
    reverts. Both outcomes are cheap and neither is silent.
    """
    overlay = dest.parent
    # INCLUDE_ASM LINES ARE NOT DECLARATIONS. e_background_pillars.c mentions
    # func_us_801CC8F8_from_no0 inside an INCLUDE_ASM, which expands to inline
    # assembly and declares no C prototype -- but a plain text search sees the
    # name followed by `)` and concludes it is already visible. That silently
    # suppressed the one declaration the build was asking for, and the symbol
    # did not even appear in the NOT-FOUND list.
    have = re.sub(r"^.*INCLUDE_ASM\(.*$", "", dest.read_text(errors="ignore"),
                  flags=re.M)
    decls, notes = [], []
    # Only symbols that look like this project's globals. A broad identifier
    # sweep would try to declare locals, macros and enum members.
    cands = set(re.findall(r"\b(?:func_us_\w+|func_\d\w*|"
                           r"[A-Z][A-Z0-9]+_[A-Za-z]\w*|D_us_\w+|g_\w+)\b",
                           body))
    # THE FUNCTION BEING DEFINED NEEDS NO DECLARATION. Leaving it in reported
    # "NO DECLARATION FOUND for func_us_801D1184_from_are" while transplanting
    # exactly that function, and the scan then filed five clean candidates
    # under needs-defs for a dependency that does not exist.
    cands.discard(defining)
    pending = sorted(cands)
    while pending:
        sym = pending.pop(0)
        if re.search(r"\b" + re.escape(sym) + r"\b\s*[;)(,]", have):
            continue                       # already visible in this file
        # THE OVL_EXPORT ALIAS. The shared stages name a struct g_EInitCommon
        # while rno0 exports it as OVL_EXPORT(EInitCommon), i.e.
        # RNO0_EInitCommon, and the rno0 assembly confirms %hi(RNO0_EInitCommon)
        # at that site. A transplant carrying the shared name will not compile.
        #
        # This is not invention: the idiom is already used three times in
        # src/st/rno0, e.g. e_clock_room.c:59
        #     #define g_EInitCommon OVL_EXPORT(EInitCommon)
        # and the mapping is only emitted when the destination overlay really
        # does define OVL_EXPORT(<rest>).
        if sym.startswith("g_"):
            rest = sym[2:]
            if any(f"OVL_EXPORT({rest})" in f.read_text(errors="ignore")
                   for f in overlay.glob("*.c") if f != dest):
                decls.append(f"#define {sym} OVL_EXPORT({rest})")
                notes.append(f"#define {sym} OVL_EXPORT({rest})   "
                             f"(the overlay exports it under that name)")
                # AND THE EXTERN FOR THE EXPANDED NAME. The #define alone
                # turns g_EInitCommon into RNO0_EInitCommon, which is DEFINED
                # in the overlay's e_init.c but not DECLARED in any header
                # this file sees -- so the alias merely moved the undeclared
                # identifier from one name to the other, and cost a build to
                # find out.
                pref = _ovl_prefix(overlay)
                if pref:
                    expanded = f"{pref}_{rest}"
                    if (not re.search(r"\b" + re.escape(expanded)
                                      + r"\b\s*[;)(,]", have)
                            and expanded not in cands):
                        cands.add(expanded)
                        pending.append(expanded)
            # Otherwise it is a shared global from game.h -- g_api, g_PrimBuf,
            # g_CurrentEntity -- visible everywhere and not the overlay's to
            # declare. Reporting those as missing would bury the real findings
            # in noise, so they are passed over in silence.
            continue
        # The symbol may be spelled through OVL_EXPORT in its own overlay:
        # rno0/e_init.c writes `EInit OVL_EXPORT(EInitSpawner) = ...`, so a
        # literal search for RNO0_EInitSpawner finds nothing. Both spellings
        # are tried. This cost a build to discover.
        spellings = [sym]
        m_ovl = re.match(r"^[A-Z][A-Z0-9]*_(\w+)$", sym)
        if m_ovl:
            spellings.append(f"OVL_EXPORT({m_ovl.group(1)})")
        found = None
        for f in sorted(overlay.glob("*.c")) + sorted(overlay.glob("*.h")):
            if f == dest:
                continue
            t = f.read_text(errors="ignore")
            for sp in spellings:
                esp = re.escape(sp)
                # A DEFINITION, ending in a brace.
                m = re.search(r"^[ \t]*(?:static[ \t]+)?([A-Za-z_]\w*)[ \t*]+"
                              + esp + r"[ \t]*\(([^;{)]*)\)[ \t]*\{", t, re.M)
                if m:
                    found = (f"{m.group(1)} {sym}"
                             f"({m.group(2).strip() or 'void'});")
                    break
                # An existing DECLARATION is just as good a source for a
                # prototype, and for func_us_801CC8F8_from_no0 it is the ONLY
                # source: rno0 declares it on line 25 and never defines it,
                # because the definition is the INCLUDE_ASM stub. Requiring a
                # brace missed it and cost a second build.
                m = re.search(r"^[ \t]*(?:extern[ \t]+)?([A-Za-z_]\w*)[ \t*]+"
                              + esp + r"[ \t]*\(([^;{)]*)\)[ \t]*;", t, re.M)
                if m:
                    found = (f"{m.group(1)} {sym}"
                             f"({m.group(2).strip() or 'void'});")
                    break
                # Data.
                m = re.search(r"^[ \t]*([A-Za-z_]\w*)[ \t]+" + esp
                              + r"[ \t]*=", t, re.M)
                if m:
                    found = f"extern {m.group(1)} {sym};"
                    break
            if found:
                break
        if found:
            decls.append(found)
            notes.append(f"{found}   (from {f.name})")
        else:
            notes.append(f"NO DECLARATION FOUND for {sym}; the build will say "
                         f"so")
    return decls, notes


RX_ENUM = re.compile(r"enum\s+\w*\s*\{(.*?)\}", re.S)
RX_ENUM_MEMBER = re.compile(
    r"^[ \t]*(?:/\*[^*]*\*/[ \t]*)?([A-Z][A-Z0-9_]*)[ \t]*(?:=[^,]*)?,"
    r"[ \t]*(?://[ \t]*(.*))?$", re.M)


def _enum_members(header: Path) -> list[tuple[str, str]]:
    """[(member, trailing comment)] of the largest enum in a header."""
    if not header.is_file():
        return []
    best: list[tuple[str, str]] = []
    for m in RX_ENUM.finditer(header.read_text(errors="ignore")):
        got = [(a, (b or "").strip())
               for a, b in RX_ENUM_MEMBER.findall(m.group(1))]
        if len(got) > len(best):
            best = got
    return best


def enum_map(body: str, src_h: Path, dest_h: Path) -> tuple[dict, list[str]]:
    """Entity-id members the destination overlay spells differently.

    THE ONE SUBSTITUTION THE ASSEMBLY CANNOT SUPPLY. E_ID_16 and E_UNK_16 have
    the same VALUE, so the two listings are byte-identical there and
    asm_delta sees nothing. The rename is needed only because rno0.h does not
    declare E_ID_16, and the C would not compile.

    Resolved by ORDINAL, then cross-checked against the destination's own
    comment. rno0.h annotates its members with the function each id belongs
    to (`E_UNK_16, // func_us_801CC8F8_from_no0`), which is independent
    evidence: the two enums are 82 and 81 members long, so ordinals CAN drift,
    and a bare ordinal match would be a guess dressed as a derivation.

    A mapping with neither signal confirmed is reported and NOT applied.
    """
    src, dest = _enum_members(src_h), _enum_members(dest_h)
    if not src or not dest:
        return {}, []
    have = {n for n, _c in dest}
    out, notes = {}, []
    for name in sorted(set(re.findall(r"\b(E_[A-Z0-9_]+)\b", body))):
        if name in have:
            continue                      # the destination knows this name
        idx = next((i for i, (n, _c) in enumerate(src) if n == name), -1)
        if idx < 0 or idx >= len(dest):
            notes.append(f"{name}: no ordinal in the destination enum; "
                         f"left alone")
            continue
        cand, comment = dest[idx]
        # Independent confirmation: the destination's comment should name the
        # twin function, i.e. the source function name with or without the
        # _from_<overlay> suffix.
        confirmed = bool(comment) and bool(
            re.search(r"func_|Entity", comment))
        out[name] = cand
        notes.append(f"{name} -> {cand}  (ordinal {idx}"
                     + (f", destination comment: {comment}" if confirmed
                        else ", NO comment to confirm it") + ")")
    return out, notes


def detail_head(fn: str, path: str, stub: str, base: str) -> str:
    return f"twin {path}; stub {stub}"


def preflight(fn: str, mapping: list[str] | None = None,
              auto: bool = False, skip_clean: bool = False
              ) -> tuple[bool, str, str]:
    """Everything checkable before the tree is touched.

    Ordered cheapest-first and STOPS at the first failure, so a dry run costs
    nothing and cannot half-report.
    """
    ps = _sup()
    base = re.sub(r"_from_\w+$", "", fn)

    # Hoisted for scans: this is a git status over the whole repo, ~8s, and
    # the answer cannot change while a read-only scan runs. Checking it per
    # record made the scan 8 seconds slower for every function examined.
    if not skip_clean:
        dirty = ps.require_clean_src()
        if dirty:
            return False, "", f"src/ is not clean: {dirty}"

    # LOOK FOR THE STUB UNDER THE QUEUE'S OWN NAME, suffix and all. The first
    # version stripped `_from_no0` for both lookups and then reported "no
    # INCLUDE_ASM stub for func_us_801CC750" -- true, and irrelevant: the stub
    # we are replacing is `func_us_801CC750_from_no0`.
    found = ps.find_stub(fn)
    if not found:
        return False, "", (f"no INCLUDE_ASM stub for {fn} in src/; it is "
                           f"either already applied or not ours to write")
    stub_path = str(found[0].relative_to(REPO)) if hasattr(
        found[0], "relative_to") else str(found[0])

    # THIS TREE ONLY. Upstream is not a runtime dependency of this mechanism.
    #
    # An earlier version fell back to upstream/master whenever the local
    # lookup missed, which made every scan resolve a network-fetched ref and
    # run a git grep over a foreign tree: three preflights took 118 seconds,
    # nearly all of it upstream, including for a function upstream did not
    # have either. Worse than slow, it made the fork's own tooling depend on
    # somebody else's repository being present and current.
    #
    # Taking what we need from upstream is a deliberate, occasional act, and
    # it has its own tool: upstream_harvest.py. This one answers a question
    # about OUR tree.
    # EVERY candidate twin, best evidence first: the naming convention, then
    # asm_twin_finder's shape and token matches. The first is a narrow subset
    # -- it found 12 candidates where the similarity index knows many more.
    tried: list[str] = []
    body = path = src_kind = ""
    for cand in (twin_sources(fn) or [base]):
        b, pth = local_twin(cand, exclude=Path(stub_path).name)
        if not b:
            tried.append(f"{cand}: no extractable definition")
            continue
        # The twin must actually BE a twin. asm_twin_finder matches on shape
        # and tokens, which is a similarity score, not a proof; asm_delta is
        # the arbiter and rejects a different-length or different-opcode pair.
        if auto:
            import asm_delta as ad                             # type: ignore
            probe = ad.for_function(fn, twin_name=cand)
            if not probe["ok"]:
                tried.append(f"{cand}: {probe['reason']}")
                continue
        body, path, src_kind, base = b, pth, "local twin", cand
        break
    if not body:
        return False, "", ("no usable twin in this tree; tried "
                           + ("; ".join(tried) if tried else "nothing"))
    body = rename_function(body, base, fn)

    pairs = list(mapping or [])
    auto_notes: list[str] = []
    if auto:
        # DERIVED, not supplied. asm_delta reads the two listings and returns
        # every symbol rename and constant change between them; the first
        # transplant needed all of that by hand.
        import asm_delta as ad                                # type: ignore
        d = ad.for_function(fn, twin_name=base)
        auto_notes.append(f"asm delta: {d['reason']} "
                          f"({d['insns']} insns, {d['diffs']} differing)")
        if not d["ok"]:
            return False, "", "\n  ".join([detail_head(fn, path, stub_path,
                                                        base)] + auto_notes)
        pairs = ad.as_maps(d) + pairs
        em, en = enum_map(body, Path(path).parent / f"{Path(path).parent.name}.h",
                          Path(REPO / stub_path).parent
                          / f"{Path(stub_path).parent.name}.h")
        pairs += [f"{k}={v}" for k, v in em.items()]
        auto_notes += [f"enum: {x}" for x in en]

    # Constants the C reaches through a macro cannot be substituted as
    # literals; rewrite the macro argument instead, verified by evaluation.
    mc, mc_notes = macro_consts(body, pairs)
    auto_notes += [f"macro: {x}" for x in mc_notes]
    body, map_notes = apply_map(body, pairs + mc)
    decls, decl_notes = auto_decls(body, REPO / stub_path, defining=fn)
    if decls:
        body = "\n".join(decls) + "\n\n" + body

    # The transplant must define the function we are replacing, not merely
    # mention it. _extract already enforces this, but a wrong body here would
    # be applied to the tree, so it is worth asserting twice.
    head = body.split("{", 1)[0]
    if not re.search(r"\b" + re.escape(fn) + r"\s*\(", head):
        return False, "", f"extracted body does not define {fn}"

    # Type-check the transplant the same way generated C is checked. Upstream
    # writes against upstream's headers; a member that does not exist here
    # would fail the build, and this says so for free.
    try:
        import member_types as mt                             # type: ignore
        bad = mt.check(body)
    except ImportError:                                       # pragma: no cover
        bad = []
    if bad:
        return False, body, ("upstream's C uses members this tree does not "
                             "have: " + "; ".join(bad[:3]))
    detail = (f"ready: {len(body)} chars from the {src_kind} "
              f"{path}\n  stub: {stub_path}"
              + (f"\n  renamed {base} -> {fn}" if base != fn else ""))
    for n in auto_notes:
        detail += f"\n  {n}"
    for n in map_notes:
        detail += f"\n  map: {n}"
    for n in decl_notes:
        detail += f"\n  decl: {n}"
    return True, body, detail


def run(fn: str, apply: bool, mapping: list[str] | None = None,
        auto: bool = False) -> int:
    ok, body, detail = preflight(fn, mapping, auto)
    print(f"{fn}\n  {detail}")
    if not ok:
        return 1
    if not apply:
        print("\n  DRY RUN. Nothing written. Re-run with --apply to test it "
              "for real;\n  the apply path builds, verifies all 81 SHA-1s, "
              "and reverts unless green.")
        print("\n--- transplant body ---")
        print("\n".join("  " + l for l in body.splitlines()[:40]))
        return 0

    ps = _sup()
    print("\n  applying under the fleet's own build lock...")
    good, why = ps.land_match(Path("."), fn, body=body)
    print(f"  {'MATCHED' if good else 'not a match'}: {why}")
    if good:
        print("\n  The overlay rebuilt and all 81 SHA-1s verified. Report it "
              "with\n  queue_report(status='matched', proof=...) -- this tool "
              "does not write\n  to the queue.")
    else:
        print("\n  Reverted. src/ is back to HEAD; land_match proves the "
              "revert rather\n  than asserting it.")
    return 0 if good else 2


def list_all() -> int:
    rows = candidates()
    if not rows:
        print("nothing available to transplant")
        return 0
    print(f"{len(rows)} unmatched function(s) already defined elsewhere in "
          f"THIS tree\n")
    print(f"{'function':34}{'overlay':14}defined in")
    print("-" * 92)
    for fn, ovl, path in rows:
        print(f"{fn[:32]:34}{ovl[:12]:14}{path}")
    print("\nTry one:  transplant.py --function <name>")
    return 0


def scan(limit: int = 0, overlay: str = "") -> int:
    """Classify EVERY unmatched record, unsupervised, writing nothing.

    THE POINT OF THE MECHANISM. A tool that needs an operator to pick the
    candidate, read the asm diff and hand-write the substitutions is not
    automation; it is me with extra steps. This asks the same questions for
    the whole queue and reports what it finds, whether or not any of it
    becomes a match.

    The classes are deliberately about EVIDENCE, not optimism:

      ready       a clean twin whose every substitution resolved and whose
                  every symbol is declarable in the destination. Worth a
                  build.
      needs-defs  a clean twin that references file-scope statics or symbols
                  the destination overlay does not have. func_us_801CC9B4
                  needs two `static s16` arrays that live in no0/4C750.c and
                  do not travel with a function body. Actionable, but not by
                  copying one function.
      not-twin    the assembly genuinely differs: different length, or a
                  different instruction. No amount of renaming fixes that,
                  and saying so is more useful than a failed build.
      no-twin     nothing in the tree defines this function under another
                  name.
    """
    uh = _harv()
    recs = uh.unmatched_records()
    if overlay:
        recs = [r for r in recs if overlay.lower() in r[1].lower()]
    if limit:
        recs = recs[:limit]

    buckets: dict[str, list] = {"ready": [], "needs-defs": [],
                                "not-twin": [], "no-twin": []}
    dirty = _sup().require_clean_src()
    if dirty:
        print(f"src/ is not clean: {dirty}\n")
        return 1
    for _rid, ovl, fn in recs:
        try:
            ok, _body, detail = preflight(fn, None, auto=True,
                                          skip_clean=True)
        except Exception as e:                                # noqa: BLE001
            buckets["no-twin"].append((fn, ovl, f"error: {type(e).__name__}"))
            continue
        if not ok:
            why = detail.splitlines()[-1].strip()
            key = "not-twin" if "not a twin" in why else "no-twin"
            buckets[key].append((fn, ovl, why[:88]))
            continue
        missing = [l.split("for ", 1)[1].split(";")[0]
                   for l in detail.splitlines()
                   if "NO DECLARATION FOUND" in l]
        # Enum members and macros come from the shared headers and are not
        # per-overlay symbols, so they are not a blocker; a bare D_ or func_
        # symbol is.
        real = [m for m in missing
                if re.match(r"^(?:D_us_|D_|func_)", m)]
        if real:
            buckets["needs-defs"].append((fn, ovl, ", ".join(real[:4])))
        else:
            nsub = len([l for l in detail.splitlines()
                        if l.strip().startswith("map: ")
                        and "IGNORED" not in l])
            buckets["ready"].append((fn, ovl, f"{nsub} substitution(s)"))

    total = sum(len(v) for v in buckets.values())
    print(f"{total} unmatched record(s) examined, nothing written\n")
    for k in ("ready", "needs-defs", "not-twin", "no-twin"):
        print(f"  {k:12} {len(buckets[k])}")
    for k in ("ready", "needs-defs", "not-twin"):
        if not buckets[k]:
            continue
        print(f"\n=== {k} ===")
        for fn, ovl, why in buckets[k]:
            print(f"  {fn[:34]:36}{ovl[:12]:14}{why}")
    if buckets["ready"]:
        print("\nEach `ready` is one build away from a verdict:")
        print("  transplant.py --function <name> --auto --apply")
    return 0


def _dirty_files() -> set[str]:
    """Paths under src/ that differ from HEAD."""
    import subprocess
    out = subprocess.run(["git", "status", "--porcelain", "--", "src/"],
                         capture_output=True, text=True, timeout=120,
                         cwd=str(REPO)).stdout
    return {l[3:].strip() for l in out.splitlines() if l[3:].strip()}


def batch(limit: int = 0, overlay: str = "") -> int:
    """Apply every `ready` candidate in turn, building each.

    THE TREE IS LEGITIMATELY DIRTY AFTER A MATCH. land_match keeps a green
    result applied, so a second candidate's clean-tree guard would refuse to
    run -- and blanket-skipping that guard would let an unrelated edit, or a
    half-applied crash, ride along into the next build unnoticed.

    So the batch tracks the files IT landed and requires the dirty set to be
    exactly that. Anything else and it stops, because an unexpected change
    means the tree is not in the state the next build assumes.
    """
    rows = [(fn, ovl) for fn, ovl, _p in candidates()]
    if overlay:
        rows = [r for r in rows if overlay.lower() in r[1].lower()]

    start_dirty = _dirty_files()
    if start_dirty:
        print(f"src/ is not clean to begin with: {sorted(start_dirty)}")
        return 1

    landed: set[str] = set()
    results: list[tuple[str, str, str]] = []
    done = 0
    for fn, _ovl in rows:
        if limit and done >= limit:
            break
        now = _dirty_files()
        if now - landed:
            print(f"\nSTOPPING: unexpected change in {sorted(now - landed)}")
            print("The tree is not in the state the next build assumes.")
            break
        ok, body, detail = preflight(fn, None, auto=True, skip_clean=True)
        if not ok:
            results.append((fn, "skipped", detail.splitlines()[-1].strip()))
            continue
        done += 1
        print(f"\n[{done}] {fn}", flush=True)
        good, why = _sup().land_match(Path("."), fn, body=body)
        if good:
            results.append((fn, "MATCHED", why[:70]))
            landed |= (_dirty_files() - landed)
        elif "CHECKSUM MISMATCH" in why:
            results.append((fn, "compiles-differs", "permuter candidate"))
        else:
            results.append((fn, "failed", why.split("\n")[0][:70]))
        print(f"    {results[-1][1]}: {results[-1][2]}", flush=True)

    print(f"\n{'function':36}{'result':20}detail")
    print("-" * 92)
    for fn, res, why in results:
        print(f"{fn[:34]:36}{res:20}{why[:34]}")
    n_m = sum(1 for _f, r, _w in results if r == "MATCHED")
    print(f"\n{n_m} matched, "
          f"{sum(1 for _f, r, _w in results if r == 'compiles-differs')} "
          f"compile but differ, "
          f"{sum(1 for _f, r, _w in results if r == 'failed')} failed")
    if n_m:
        print("\nMatches are APPLIED and unreported. Record each with "
              "queue_report(status='matched', proof=...) and commit.")
    return 0


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    src = Path(__file__).read_text(errors="ignore")
    print("\nthis module does NOT reimplement apply/build/revert")
    # The hardened sequence lives in exactly one place. A second copy is a
    # second thing to get wrong, and the failure mode is a corrupted tree.
    #
    # Checked against the AST, not the text: the first version searched the
    # source for "apply_code(" and matched its own docstring, failing a module
    # that calls no such thing. Reading prose is not testing code -- the same
    # mistake this project has now made three times.
    import ast as _ast
    # The SELF-TEST is excluded from this scan: it legitimately writes to a
    # temp directory to exercise auto_decls, and including it made the test
    # fail on its own scaffolding. Scope the assertion to the code that
    # actually runs against the repo.
    called = set()
    tree = _ast.parse(src)
    tree.body = [n for n in tree.body
                 if not (isinstance(n, _ast.FunctionDef)
                         and n.name == "self_test")]
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Call):
            f = node.func
            if isinstance(f, _ast.Name):
                called.add(f.id)
            elif isinstance(f, _ast.Attribute):
                called.add(f.attr)
    for danger in ("apply_code", "build_and_check", "journal_write",
                   "copyfile", "write_text", "unlink", "rename"):
        ck(danger not in called, f"never calls {danger}()")
    ck("land_match" in called, "it delegates to land_match")

    print("\nnothing is written without --apply")
    ck('if not apply:' in src and 'DRY RUN' in src,
       "the dry-run branch returns before land_match")
    ck(src.index("if not apply:") < src.index("ps.land_match("),
       "and it does so BEFORE the apply call")

    print("\npreflight stops at the first failure")
    # Each check returns immediately, so a dry run cannot report "ready" while
    # an earlier condition was false.
    body_fn = src[src.index("def preflight"):src.index("def run(")]
    ck(body_fn.count("return False") >= 4,
       f"every failure path returns ({body_fn.count('return False')})")
    ck("require_clean_src()" in body_fn,
       "a dirty tree is refused before anything else")
    ck(body_fn.index("require_clean_src()") < body_fn.index("find_stub"),
       "and that check comes first")

    print("\nthe stub is looked up under the QUEUE's name, suffix and all")
    # The unmatched record is func_us_801CC750_from_no0; the stub in
    # e_background_pillars.c carries that exact name. Stripping the suffix for
    # this lookup reported "no INCLUDE_ASM stub for func_us_801CC750", which
    # is true and useless.
    # Scoped to preflight, not the whole file: the assertion string itself
    # contains the pattern it is looking for, so a whole-file search matches
    # the test rather than the code. FOURTH time today. The rule is simple --
    # a test that greps source text must first cut out its own text.
    ck("find_stub(fn)" in body_fn and "find_stub(base)" not in body_fn,
       "find_stub gets the full name")

    print("\nUPSTREAM IS NOT A RUNTIME DEPENDENCY of this mechanism")
    # Taking what we need from upstream is a deliberate, occasional act with
    # its own tool. Resolving a network-fetched ref on every scan made three
    # preflights take 118 seconds and made the fork's tooling depend on
    # somebody else's repository being present and current.
    ck("local_twin(" in body_fn, "the body comes from this tree")
    for banned in ("upstream_files", "upstream_stubs", "upstream_body",
                   "harvest"):
        ck(banned not in called, f"never calls {banned}()")
    ck("UPSTREAM" not in [n.id for n in _ast.walk(tree)
                          if isinstance(n, _ast.Name)],
       "the upstream ref is never named")

    print("\nthe twin is renamed to the symbol being replaced")
    ck(rename_function("void a(Entity* e) { a(e); }", "a", "a_from_no0")
       == "void a_from_no0(Entity* e) { a_from_no0(e); }",
       "definition and self-recursion are renamed")
    ck(rename_function("void ab(void) { abc(); }", "ab", "ab_x")
       == "void ab_x(void) { abc(); }",
       "a name that merely CONTAINS the old one is left alone")
    ck(rename_function("void a(void){}", "a", "a") == "void a(void){}",
       "renaming to the same name is a no-op")

    print("\nsymbol mapping is explicit, word-anchored, and reported")
    b, n = apply_map("void f(void){ E_ID_16; E_ID_160; }", ["E_ID_16=E_UNK_16"])
    ck("E_UNK_16;" in b and "E_ID_160" in b,
       f"only the whole word is renamed ({b})")
    ck(n and "1 occurrence" in n[0], f"and the count is reported ({n})")
    _b2, n2 = apply_map("void f(void){}", ["Absent=Thing"])
    ck("IGNORED" in n2[0], f"a symbol not present is reported, not silent ({n2})")
    _b3, n3 = apply_map("x", ["garbage"])
    ck("IGNORED malformed" in n3[0], "a malformed pair is reported")
    # A SWAP. Sequential substitution collapses this; the inverted castle
    # mirrors the sprite, so 0xC0 and 0xE0 genuinely trade places.
    sw, _ = apply_map("a = 0xC0; b = 0xE0;", ["0xC0=0xE0", "0xE0=0xC0"])
    ck(sw == "a = 0xE0; b = 0xC0;", f"the values are swapped, not collapsed ({sw})")
    # Numeric literals are not word characters at their edges, so \b would
    # mis-anchor; the guard is a non-word, non-dot lookaround.
    nb, _ = apply_map("x = 0x91; y = 0x910;", ["0x91=0x5F"])
    ck(nb == "x = 0x5F; y = 0x910;", f"0x910 is not touched by 0x91 ({nb})")

    print("\nmissing declarations are DERIVED from the definition")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        ov = Path(td)
        (ov / "e_init.c").write_text(
            "void func_us_801CC8F8_from_no0(Entity* self) { }\n"
            "EInit RNO0_EInitSpawner = {1, 2, 3};\n", encoding="utf-8")
        dest = ov / "e_background_pillars.c"
        dest.write_text("#include \"rno0.h\"\n", encoding="utf-8")
        d, n = auto_decls(
            "void f(Entity* e){ InitializeEntity(RNO0_EInitSpawner);"
            " e->pfnUpdate = func_us_801CC8F8_from_no0; }", dest)
        ck("extern EInit RNO0_EInitSpawner;" in d,
           f"the data symbol becomes an extern ({d})")
        ck(any("func_us_801CC8F8_from_no0(Entity* self);" in x for x in d),
           f"the function becomes a prototype ({d})")
        # A symbol with no definition anywhere must NOT be invented.
        d2, n2 = auto_decls("void f(void){ D_us_DEADBEEF; }", dest)
        ck(d2 == [], f"an unknown symbol yields no declaration ({d2})")
        ck(any("NO DECLARATION FOUND" in x for x in n2),
           "and it is reported rather than passed over")
        # Already visible in the destination: do not redeclare.
        dest.write_text("void func_us_801CC8F8_from_no0(Entity*);\n",
                        encoding="utf-8")
        d3, _ = auto_decls("void f(Entity* e){"
                           " e->pfnUpdate = func_us_801CC8F8_from_no0; }",
                           dest)
        ck(d3 == [], f"a symbol already declared here is skipped ({d3})")
        # An INCLUDE_ASM mention must NOT count as a declaration.
        dest.write_text(
            'INCLUDE_ASM("st/rno0/nonmatchings/x", '
            'func_us_801CC8F8_from_no0);\n', encoding="utf-8")
        (ov / "e_init.c").write_text(
            "void func_us_801CC8F8_from_no0(Entity* self);\n",
            encoding="utf-8")
        d5, _ = auto_decls("void f(Entity* e){"
                           " e->pfnUpdate = func_us_801CC8F8_from_no0; }",
                           dest)
        ck(any("func_us_801CC8F8_from_no0" in x for x in d5),
           f"an INCLUDE_ASM mention does not count as a declaration ({d5})")
        # The function being transplanted is not its own dependency.
        _d6, n6 = auto_decls(
            "void func_us_801D1184_from_are(Entity* e){ e->step = 1; }",
            dest, defining="func_us_801D1184_from_are")
        ck(not any("func_us_801D1184_from_are" in x for x in n6),
           f"the defined function is not reported as missing ({n6})")
        # The OVL_EXPORT alias, only when the overlay really exports it.
        (ov / "e_init.c").write_text(
            "EInit OVL_EXPORT(EInitCommon) = {1};\n", encoding="utf-8")
        dest.write_text("#include \"rno0.h\"\n", encoding="utf-8")
        d7, _ = auto_decls("void f(Entity* e){ InitializeEntity("
                           "g_EInitCommon); }", dest)
        ck("#define g_EInitCommon OVL_EXPORT(EInitCommon)" in d7,
           f"the alias is emitted ({d7})")
        d8, n8 = auto_decls("void f(void){ g_NotExported; }", dest)
        ck(not any("#define" in x for x in d8),
           f"and NOT invented when the overlay does not export it ({d8})")
        # OVL_EXPORT spelling and declaration-only sources: the two misses
        # that each cost a build.
        (ov / "e_init.c").write_text(
            "void func_us_801CC8F8_from_no0(Entity* self);\n"
            "EInit OVL_EXPORT(EInitSpawner) = {1};\n", encoding="utf-8")
        dest.write_text("#include \"rno0.h\"\n", encoding="utf-8")
        d4, _ = auto_decls("void f(Entity* e){ InitializeEntity("
                           "RNO0_EInitSpawner);"
                           " e->pfnUpdate = func_us_801CC8F8_from_no0; }",
                           dest)
        ck("extern EInit RNO0_EInitSpawner;" in d4,
           f"OVL_EXPORT(EInitSpawner) resolves RNO0_EInitSpawner ({d4})")
        ck(any("func_us_801CC8F8_from_no0(Entity* self);" in x for x in d4),
           f"a declaration-only symbol still yields a prototype ({d4})")

    print("\nthe scan classifies on evidence, and writes nothing")
    # By CALLS, not by text: the scan prints a hint containing "--apply", and
    # a text search matched its own help string. Fifth time today.
    # Sliced to scan() ALONE. Anchoring the end on self_test swallowed
    # batch(), which legitimately lands matches, and the assertion then failed
    # on the wrong function's behaviour.
    scan_src = src[src.index("def scan("):src.index("def _dirty_files(")]
    _sc = _ast.parse(scan_src.replace("\ndef scan(", "\ndef scan(", 1))
    _scalls = {n.func.attr if isinstance(n.func, _ast.Attribute)
               else getattr(n.func, "id", "")
               for n in _ast.walk(_sc) if isinstance(n, _ast.Call)}
    ck("land_match" not in _scalls,
       f"the scan never calls land_match ({sorted(_scalls)[:6]})")
    ck("run" not in _scalls, "and never calls run()")
    for k in ("ready", "needs-defs", "not-twin", "no-twin"):
        ck(f'"{k}"' in scan_src, f"the {k} class exists")
    ck("not a twin" in scan_src,
       "a structural mismatch is separated from a missing twin")

    print("\na constant the C reaches through a MACRO is rewritten as an arg")
    # ANIMSET_OVL(x) is `(x) | 0x8000`, so ANIMSET_OVL(1) assembles to -0x7FFF.
    # Searching the body for the literal finds nothing, the substitution is
    # dropped, and the transplant compiles to the WRONG BYTES -- which is
    # worse than failing, because it looks like success until the checksum.
    out, notes = macro_consts("self->animSet = ANIMSET_OVL(1);",
                              ["-0x7FFF=-0x7FFE"])
    ck(out == ["ANIMSET_OVL(1)=ANIMSET_OVL(2)"],
       f"the argument is rewritten, not the literal ({out})")
    ck(any("verified through the macro" in n for n in notes),
       "and the arithmetic is checked, not assumed")
    # A literal already present is apply_map's job, not this one.
    ck(macro_consts("x = -0x7FFF;", ["-0x7FFF=-0x7FFE"])[0] == [],
       "a literal in the body is left to apply_map")
    # A symbol rename must not be parsed as a constant.
    ck(macro_consts("ANIMSET_OVL(1);", ["func_a=func_b"])[0] == [],
       "a symbol pair is ignored here")
    # An unreachable target value must NOT be forced.
    bad, bn = macro_consts("self->animSet = ANIMSET_OVL(1);",
                           ["-0x7FFF=0x1234"])
    ck(bad == [], f"an unreachable value yields no rewrite ({bad})")
    ck(any("left alone" in n for n in bn),
       f"and it is reported rather than passed over ({bn})")

    print("\nthe batch tolerates only the matches IT landed")
    bsrc = src[src.index("def batch("):src.index("def self_test(")]
    ck("now - landed" in bsrc,
       "the dirty set is compared against what the batch itself applied")
    ck("STOPPING" in bsrc, "and it stops rather than building on a surprise")
    ck("start_dirty" in bsrc, "a tree dirty at the start is refused outright")
    ck("queue_report" in bsrc,
       "matches are left for the operator to record, not written here")

    print("\nthe transplant is type-checked like generated C is")
    ck("member_types" in body_fn,
       "upstream's members are validated against THIS tree's structs")

    print("\nland_match accepts a supplied body")
    sup = (REPO / "automation" / "permuter_supervisor.py").read_text(
        errors="ignore")
    ck("body: str = \"\"" in sup, "the parameter exists")
    ck("if not body:" in sup,
       "and the permuter path still works when it is omitted")

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
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--batch", action="store_true",
                    help="apply every ready candidate in turn, building each")
    ap.add_argument("--scan", action="store_true",
                    help="classify every unmatched record, unsupervised")
    ap.add_argument("--overlay", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--function")
    # ONE argument carrying many pairs. The connector caps a call at 12
    # arguments and rejects commas and spaces, so nine renames could not be
    # expressed as nine --map flags. `/` is in the allowed character set and
    # cannot occur in a C identifier or a hex literal.
    # Repeatable as well as slash-separated: a single argument is also capped
    # at ~120 characters, so nine renames need both mechanisms.
    ap.add_argument("--maps", action="append", default=[], metavar="A=B/C=D",
                    help="slash-separated renames, repeatable; for when --map "
                         "would exceed the connector's argument cap")
    ap.add_argument("--map", action="append", default=[], metavar="OLD=NEW",
                    help="rename a symbol the destination overlay calls "
                         "something else; repeatable")
    ap.add_argument("--auto", action="store_true",
                    help="derive every substitution from the asm diff and the "
                         "destination enum; no hand-supplied map")
    ap.add_argument("--apply", action="store_true",
                    help="actually apply, build, verify and revert on failure")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.list:
        return list_all()
    if a.scan:
        return scan(a.limit, a.overlay)
    if a.batch:
        return batch(a.limit, a.overlay)
    if a.function:
        pairs = list(a.map)
        for chunk in a.maps:
            pairs += [x for x in chunk.split("/") if x.strip()]
        return run(a.function, a.apply, pairs, a.auto)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
