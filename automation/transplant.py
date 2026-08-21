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

import artifact_store

REPO = Path(__file__).resolve().parent.parent
SCORE_ROOT = REPO / "nonmatchings" / ".adapt-scores"
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


def adapt_api_surfaces(
    body: str, target_symbols: set[str]
) -> tuple[str, list[str]]:
    """Select standalone API pointers when the target relocation proves one."""
    notes: list[str] = []
    members = sorted(set(re.findall(r"\bg_api\s*\.\s*([A-Za-z_]\w*)", body)))
    for member in members:
        standalone = f"g_api_{member}"
        if standalone not in target_symbols:
            continue
        pattern = re.compile(
            r"\bg_api\s*\.\s*" + re.escape(member) + r"\b")
        body, count = pattern.subn(standalone, body)
        if count:
            notes.append(
                f"g_api.{member} -> {standalone} "
                f"({count} target-proven occurrence(s))")
    return body, notes


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
    # sweep would try to declare locals, macros and enum members. Overlay
    # globals have a mixed-case suffix (`RNO0_EInitSpawner`); all-uppercase
    # suffixes such as DRAW_COLORS and PL_W_BIBLE are shared enum or macro
    # names and need no file-scope declaration here.
    cands = set(re.findall(r"\b(?:func_us_\w+|func_\d\w*|"
                           r"[A-Z][A-Z0-9]+_[A-Za-z]\w*|D_us_\w+|g_\w+)\b",
                           body))
    cands = {
        sym for sym in cands
        if not re.match(r"^[A-Z][A-Z0-9]+_", sym)
        or any(char.islower() for char in sym.split("_", 1)[1])
    }
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


_C_TYPE = (r"(?:(?:const|volatile)[ \t]+)*"
           r"(?:struct[ \t]+[A-Za-z_]\w*|union[ \t]+[A-Za-z_]\w*|"
           r"enum[ \t]+[A-Za-z_]\w*|[A-Za-z_]\w*)"
           r"(?:[ \t]*\*)*")
_DONOR_OBJECT = re.compile(
    rf"(?m)^(?P<storage>(?:(?:static|extern)[ \t]+)*)"
    rf"(?P<type>{_C_TYPE})[ \t]+"
    r"(?P<name>[A-Za-z_]\w*)(?P<array>(?:[ \t]*\[[^\]\n]*\])*)"
    r"[ \t]*(?:=|;)")
_DONOR_FUNCTION = re.compile(
    rf"(?m)^(?P<storage>(?:(?:static|extern|inline)[ \t]+)*)"
    rf"(?P<type>{_C_TYPE})[ \t]+"
    r"(?P<name>[A-Za-z_]\w*)[ \t]*\((?P<args>[^;{}]*)\)[ \t]*(?:\{|;)")
_DONOR_ENUM = re.compile(
    r"(?s)(?:typedef[ \t]+)?enum(?:[ \t]+[A-Za-z_]\w*)?[ \t]*"
    r"\{(?P<body>.*?)\}[ \t]*(?:[A-Za-z_]\w*)?[ \t]*;")
_DONOR_DEFINE = re.compile(
    r"(?m)^[ \t]*#\s*define[ \t]+(?P<name>[A-Za-z_]\w*)"
    r"(?![ \t]*\()[ \t]+(?P<value>[^\n]+)")


def _donor_scope_sources(donor: Path) -> list[tuple[Path, str]]:
    """Donor plus recursively reachable quoted headers, each read once."""
    pending = [donor]
    seen: set[Path] = set()
    out: list[tuple[Path, str]] = []
    repo = REPO.resolve()
    donor_root = donor.resolve().parent
    while pending and len(seen) < 64:
        path = pending.pop(0).resolve()
        if path in seen or not path.is_file():
            continue
        in_allowed_root = False
        for root in (repo, donor_root):
            try:
                path.relative_to(root)
                in_allowed_root = True
                break
            except ValueError:
                continue
        if not in_allowed_root:
            continue
        seen.add(path)
        text = path.read_text(errors="ignore")
        out.append((path, text))
        for include in re.findall(r'^\s*#\s*include\s+"([^"]+)"',
                                  text, flags=re.M):
            candidates = [path.parent / include,
                          REPO / "src" / include,
                          REPO / "include" / include]
            found = next((item for item in candidates if item.is_file()), None)
            if found is not None and found.resolve() not in seen:
                pending.append(found)
    return out


def _us_visible_source(text: str) -> str:
    """Mask VERSION_PSP-only branches while preserving line structure.

    Isolated scores target the US build. Donor files often carry PSP-only
    declarations whose macro-expanded names conflict with US enum constants.
    This is intentionally a narrow conditional reader, not a C preprocessor:
    unknown conditions keep both branches visible, matching the resolver's
    previous conservative behavior.
    """
    stack: list[tuple[bool, bool | None, bool]] = []
    active = True
    out: list[str] = []
    for line in text.splitlines(keepends=True):
        directive = re.match(r"^\s*#\s*(if|ifdef|ifndef|else|elif|endif)\b(.*)",
                             line)
        if directive:
            op, tail = directive.groups()
            if op in {"if", "ifdef", "ifndef"}:
                expr = tail.strip()
                verdict: bool | None = None
                if op == "ifdef" and expr == "VERSION_PSP":
                    verdict = False
                elif op == "ifndef" and expr == "VERSION_PSP":
                    verdict = True
                elif op == "if":
                    if re.fullmatch(
                            r"defined\s*(?:\(\s*VERSION_PSP\s*\)|"
                            r"VERSION_PSP)", expr):
                        verdict = False
                    elif re.fullmatch(
                            r"!\s*defined\s*(?:\(\s*VERSION_PSP\s*\)|"
                            r"VERSION_PSP)", expr):
                        verdict = True
                stack.append((active, verdict, False))
                active = active and (verdict is not False)
            elif op in {"else", "elif"} and stack:
                parent, verdict, _seen_else = stack[-1]
                if op == "else":
                    stack[-1] = (parent, verdict, True)
                    active = parent and (verdict is not True)
                else:
                    # An elif attached to a known PSP condition is an unknown
                    # alternative. Keep it visible when the PSP arm was false.
                    active = parent and (verdict is not True)
            elif op == "endif" and stack:
                parent, _verdict, _seen_else = stack.pop()
                active = parent
            # These lines are control metadata, not C declarations. Keeping an
            # active #else or #endif produces orphan directives after the PSP
            # arm is masked and can confuse the declaration scanners.
            out.append("\n" if line.endswith("\n") else "")
            continue
        out.append(line if active else ("\n" if line.endswith("\n") else ""))
    return "".join(out)


def _braced_initializer_extent(text: str, start: int) -> int | None:
    """Count top-level elements in a braced initializer at or after start."""
    pos = start
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos >= len(text) or text[pos] != "{":
        return None
    depth = 0
    elements = 0
    has_token = False
    quote = ""
    escaped = False
    i = pos
    while i < len(text):
        char = text[i]
        if quote:
            has_token = True
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            i += 1
            continue
        if char in {'"', "'"}:
            quote = char
            has_token = True
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end < 0 else end + 2
            continue
        elif text.startswith("//", i):
            end = text.find("\n", i + 2)
            i = len(text) if end < 0 else end
            continue
        elif char == "{":
            depth += 1
            if depth > 1:
                has_token = True
        elif char == "}":
            if depth == 1:
                if has_token:
                    elements += 1
                return elements
            depth -= 1
            has_token = True
        elif char == "," and depth == 1:
            if has_token:
                elements += 1
            has_token = False
        elif depth >= 1 and not char.isspace():
            has_token = True
        i += 1
    return None


def _complete_array_shape(source: str, match: re.Match) -> str:
    """Fill one unsized array dimension from its braced initializer."""
    array = match.group("array").replace(" ", "")
    if "[]" not in array or not match.group(0).rstrip().endswith("="):
        return array
    extent = _braced_initializer_extent(source, match.end())
    return array.replace("[]", f"[{extent}]", 1) if extent else array


def _without_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def _destination_visible(dest: Path, name: str) -> bool:
    """Whether the destination translation unit already names a dependency."""
    pieces = [dest.read_text(errors="ignore")]
    pieces.extend(path.read_text(errors="ignore")
                  for path in sorted(dest.parent.glob("*.h")))
    text = _without_comments("\n".join(pieces))
    text = re.sub(r"^.*INCLUDE_(?:ASM|RODATA)\(.*$", "", text, flags=re.M)
    return bool(re.search(
        rf"#\s*define[ \t]+{re.escape(name)}\b|"
        rf"\b{re.escape(name)}\b[ \t]*(?:\[|\(|=|,|;)", text))


def _local_names(body: str) -> set[str]:
    """Names declared inside the transplanted function, including parameters."""
    out: set[str] = set()
    local_decl = re.compile(
        rf"(?m)^[ \t]+(?:(?:auto|register|static)[ \t]+)?"
        rf"(?P<type>{_C_TYPE})[ \t]+(?P<name>[A-Za-z_]\w*)"
        r"[ \t]*(?:\[|=|,|;)")
    non_types = {"return", "if", "else", "for", "while", "switch", "goto"}
    for match in local_decl.finditer(body):
        base_type = re.sub(r"\b(?:const|volatile)\b|\*", "",
                           match.group("type")).strip().split()[0]
        if base_type not in non_types:
            out.add(match.group("name"))

    header = body.split("{", 1)[0]
    args_match = re.search(r"\((.*)\)", header, re.S)
    if args_match:
        for arg in args_match.group(1).split(","):
            names = re.findall(r"[A-Za-z_]\w*", arg)
            if names and names[-1] != "void":
                out.add(names[-1])
    for match in re.finditer(
            rf"\bfor[ \t]*\([ \t]*(?:register[ \t]+)?{_C_TYPE}[ \t]+"
            r"(?P<name>[A-Za-z_]\w*)", body):
        out.add(match.group("name"))
    for enum in _DONOR_ENUM.finditer(_without_comments(body)):
        for raw in enum.group("body").split(","):
            name = raw.partition("=")[0].strip()
            if re.fullmatch(r"[A-Za-z_]\w*", name):
                out.add(name)
    return out


def _enum_values(source: str) -> dict[str, int]:
    """Numeric values of donor enums when their expressions are self-contained."""
    out: dict[str, int] = {}
    for enum in _DONOR_ENUM.finditer(_without_comments(source)):
        current = -1
        valid = True
        for raw in enum.group("body").split(","):
            item = raw.strip()
            if not item:
                continue
            name, mark, expr = item.partition("=")
            name = name.strip()
            if not re.fullmatch(r"[A-Za-z_]\w*", name):
                valid = False
                continue
            if mark:
                cooked = re.sub(r"(?<=\d)[uUlL]+\b", "", expr.strip())
                cooked = re.sub(
                    r"\b[A-Za-z_]\w*\b",
                    lambda match: str(out[match.group(0)])
                    if match.group(0) in out else match.group(0), cooked)
                if (re.search(r"\b[A-Za-z_]\w*\b", cooked)
                        or not re.fullmatch(r"[0-9a-fA-FxX()~+\-*%|&^<> \t]+",
                                            cooked)):
                    valid = False
                    continue
                try:
                    current = int(eval(cooked, {"__builtins__": {}}, {}))  # noqa: S307
                    valid = True
                except (SyntaxError, TypeError, ValueError, ZeroDivisionError):
                    valid = False
                    continue
            elif valid:
                current += 1
            else:
                continue
            out[name] = current
    return out


def donor_scope_decls(body: str, donor: Path, dest: Path,
                      defining: str = "") -> tuple[list[str], list[str]]:
    """Compile-only declarations for donor-local dependencies of a near twin.

    These declarations make the isolated scorer reject or score the actual C
    instead of accepting the legacy compiler's zero-exit invalid object. They
    are not target-symbol proof and are labeled score-only. A full build still
    has to resolve each dependency before a candidate can land.
    """
    sources = [(path, _us_visible_source(text))
               for path, text in _donor_scope_sources(donor)]
    source = "\n".join(text for _path, text in sources)
    used = set(re.findall(r"\b[A-Za-z_]\w*\b", body)) - _local_names(body)
    used.update("E_" + match.group(1) for match in re.finditer(
        r"\bE_ID\s*\(\s*([A-Z][A-Z0-9_]*)\s*\)", body))
    object_decls: list[str] = []
    function_decls: list[str] = []
    define_decls: list[str] = []
    notes: list[str] = []
    claimed: set[str] = set()

    for source_path, source_text in sources:
        for match in _DONOR_OBJECT.finditer(source_text):
            name = match.group("name")
            if (name in claimed or name not in used or name == defining
                    or _destination_visible(dest, name)):
                continue
            array = _complete_array_shape(source_text, match)
            declaration = f"extern {match.group('type').strip()} {name}{array};"
            object_decls.append(declaration)
            claimed.add(name)
            used.update(re.findall(r"\b[A-Za-z_]\w*\b", array))
            notes.append(f"score-only {declaration} from {source_path.name}")

        for match in _DONOR_FUNCTION.finditer(source_text):
            name = match.group("name")
            if (name in claimed or name not in used or name == defining
                    or not re.search(rf"\b{re.escape(name)}\s*\(", body)
                    or _destination_visible(dest, name)):
                continue
            storage = "extern " if "extern" in match.group("storage").split() else ""
            declaration = (f"{storage}{match.group('type').strip()} {name}"
                           f"({match.group('args').strip() or 'void'});")
            function_decls.append(declaration)
            claimed.add(name)
            notes.append(f"score-only {declaration} from {source_path.name}")

    macros: dict[str, tuple[str, Path]] = {}
    for source_path, source_text in sources:
        for match in _DONOR_DEFINE.finditer(source_text):
            macros.setdefault(
                match.group("name"),
                (_without_comments(match.group("value")).strip(), source_path))
    required = set(used)
    pending = set(required)
    added_macros: set[str] = set()
    while pending:
        name = min(pending)
        pending.remove(name)
        item = macros.get(name)
        if (not item or name in added_macros
                or _destination_visible(dest, name)):
            continue
        value, source_path = item
        if not value:
            continue
        declaration = f"#define {name} {value}"
        define_decls.append(declaration)
        added_macros.add(name)
        dependencies = set(re.findall(r"\b[A-Za-z_]\w*\b", value))
        required.update(dependencies)
        pending.update(dependencies)
        notes.append(f"score-only {declaration} from {source_path.name}")

    enum_values = _enum_values(source)
    for name in sorted(required):
        if (name not in enum_values or _destination_visible(dest, name)
                or name in added_macros):
            continue
        declaration = f"#define {name} {enum_values[name]}"
        define_decls.append(declaration)
        notes.append(f"score-only {declaration} from donor enum scope")
    return define_decls + object_decls + function_decls, notes


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


RX_ENTITY_UPDATES = re.compile(
    r"\bPfnEntityUpdate\s+EntityUpdates\s*\[\s*\]\s*=\s*\{(.*?)\};",
    re.S)


def _entity_updates(header: Path) -> list[str]:
    """EntityUpdates entries beside one overlay header, in enum order."""
    init = header.parent / "e_init.c"
    if not init.is_file():
        return []
    # Entity update tables can have PSP and US alternatives. Enum-map proof is
    # for the US queue, so parsing both arms can either shift every ordinal or
    # prove a relationship against the wrong runtime table.
    source = _us_visible_source(init.read_text(errors="ignore"))
    match = RX_ENTITY_UPDATES.search(source)
    if not match:
        return []
    value = re.sub(r"/\*.*?\*/|//[^\n]*", "", match.group(1), flags=re.S)
    value = re.sub(r"^\s*#.*$", "", value, flags=re.M)
    out: list[str] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        exported = re.fullmatch(r"OVL_EXPORT\s*\(\s*(\w+)\s*\)", item)
        plain = re.fullmatch(r"&?\s*(\w+)", item)
        out.append((exported or plain).group(1) if (exported or plain) else "")
    return out


def _same_update(a: str, b: str) -> bool:
    """Treat a transplant provenance suffix as the same update function."""
    normal = lambda value: re.sub(r"_from_\w+$", "", value or "")
    return bool(a and b) and normal(a) == normal(b)


def enum_map(body: str, src_h: Path, dest_h: Path,
             allow_apply: bool = True) -> tuple[dict, list[str]]:
    """Entity-id members the destination overlay spells differently.

    THE ONE SUBSTITUTION THE ASSEMBLY CANNOT SUPPLY. E_ID_16 and E_UNK_16 have
    the same VALUE, so the two listings are byte-identical there and
    asm_delta sees nothing. The rename is needed only because rno0.h does not
    declare E_ID_16, and the C would not compile.

    Resolved by ORDINAL, then cross-checked against both overlays' actual
    EntityUpdates arrays. rno0's E_UNK_16 is safe because ordinal 0x16 points
    at func_us_801CC8F8 in NO0 and func_us_801CC8F8_from_no0 in RNO0. By
    contrast, RNO3's E_NOVA_PULSE and RNO0's E_CORPSEWEED_PROJECTILE share an
    ordinal but dispatch different functions. Comments are diagnostics, not
    proof. The arrays are the runtime relationship the enum controls.

    A mapping with neither signal confirmed is reported and NOT applied.
    """
    src, dest = _enum_members(src_h), _enum_members(dest_h)
    src_updates, dest_updates = _entity_updates(src_h), _entity_updates(dest_h)
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
        # EntityUpdates is indexed as EntityUpdates[entityId - 1]; E_NONE is
        # enum slot zero and has no dispatch-table entry.
        update_idx = idx - 1 if (idx > 0 and src[0][0] == "E_NONE"
                                 and dest[0][0] == "E_NONE") else -1
        src_update = (src_updates[update_idx]
                      if 0 <= update_idx < len(src_updates) else "")
        dest_update = (dest_updates[update_idx]
                       if 0 <= update_idx < len(dest_updates) else "")
        if not _same_update(src_update, dest_update):
            detail = (f"{src_update or 'unknown'} != "
                      f"{dest_update or 'unknown'}")
            notes.append(f"{name} -> {cand}: ordinal {idx} dispatches "
                         f"different updates ({detail}); left alone")
            continue
        evidence = f"{src_update} == {dest_update}"
        if not allow_apply:
            notes.append(f"{name} -> {cand}: proven by EntityUpdates "
                         f"({evidence}) but suppressed for a non-clean twin")
            continue
        out[name] = cand
        notes.append(f"{name} -> {cand}  (ordinal {idx}, EntityUpdates: "
                     f"{evidence}"
                     + (f", destination comment: {comment}" if comment else "")
                     + ")")
    return out, notes


def detail_head(fn: str, path: str, stub: str, base: str) -> str:
    return f"twin {path}; stub {stub}"


def candidate_probe_failure_class(reason: str) -> str:
    """Turn one asm-delta failure into stable scan evidence."""
    if "no distinct twin asm" in reason:
        return "needs-maps"
    if "structural near:" in reason or "schedule-only twin:" in reason:
        return "adaptable"
    if "not a twin" in reason:
        return "not-twin"
    return "error"


def aggregate_candidate_failures(classes: list[str]) -> str:
    """Classify all attempted donors without discarding unresolved evidence."""
    kinds = set(classes)
    if "needs-maps" in kinds:
        return "needs-maps"
    if "adaptable" in kinds:
        return "adaptable"
    if "error" in kinds or not kinds:
        return "error"
    if "not-twin" in kinds:
        return "not-twin"
    if kinds == {"no-definition"}:
        return "no-twin"
    return "error"


def preflight(fn: str, mapping: list[str] | None = None,
              auto: bool = False, skip_clean: bool = False,
              adapt: bool = False, stub_overlay: str = ""
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
    found = ps.find_stub(fn, stub_overlay)
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
    tried: list[tuple[str, str, str]] = []
    body = path = src_kind = ""
    selected_delta: dict | None = None
    for cand in (twin_sources(fn) or [base]):
        b, pth = local_twin(cand, exclude=Path(stub_path).name)
        if not b:
            tried.append((cand, "no-definition", "no extractable definition"))
            continue
        # The twin must actually BE a twin. asm_twin_finder matches on shape
        # and tokens, which is a similarity score, not a proof; asm_delta is
        # the arbiter and rejects a different-length or different-opcode pair.
        if auto:
            import asm_delta as ad                             # type: ignore
            # NAME BOTH OVERLAYS. asm_delta indexes .s files by bare filename,
            # so a name present in two overlays used to resolve to whichever
            # the directory walk reached first -- silently, and possibly to a
            # function with nothing to do with either side of this transplant.
            # Both paths are in hand here: stub_path is the destination and
            # pth is the donor local_twin just found.
            probe = ad.for_function(fn, twin_name=cand,
                                    overlay=ad.src_overlay(stub_path),
                                    twin_overlay=ad.src_overlay(pth),
                                    twin_source=pth)
            adaptable = probe.get("kind") in {
                "structural-near", "schedule-only"
            }
            if not probe["ok"] and not (adapt and adaptable):
                reason = probe["reason"]
                tried.append((cand, candidate_probe_failure_class(reason),
                              reason))
                continue
            selected_delta = probe
        body, path, src_kind, base = b, pth, "local twin", cand
        break
    if not body:
        scan_class = aggregate_candidate_failures([kind for _, kind, _ in tried])
        rendered = "; ".join(f"{cand}: {reason}"
                             for cand, _kind, reason in tried)
        return False, "", (f"scan-class: {scan_class}\n"
                           "no usable twin in this tree; tried "
                           + (rendered if rendered else "nothing"))
    body = rename_function(body, base, fn)

    pairs = list(mapping or [])
    auto_notes: list[str] = []
    target_symbols: set[str] = set()
    adapt_kind = ""
    if auto:
        # DERIVED, not supplied. asm_delta reads the two listings and returns
        # every symbol rename and constant change between them; the first
        # transplant needed all of that by hand.
        import asm_delta as ad                                # type: ignore
        d = selected_delta or ad.for_function(
            fn, twin_name=base,
            overlay=ad.src_overlay(stub_path),
            twin_overlay=ad.src_overlay(path),
            twin_source=path)
        auto_notes.append(f"asm delta: {d['reason']} "
                          f"({d['insns']} insns, {d['diffs']} differing)")
        adaptable = d.get("kind") in {"structural-near", "schedule-only"}
        if not d["ok"] and not (adapt and adaptable):
            return False, "", "\n  ".join([detail_head(fn, path, stub_path,
                                                        base)] + auto_notes)
        if adaptable:
            adapt_kind = d["kind"]
            auto_notes.extend(f"codegen: {hint}" for hint in d.get("hints", []))
            proposed = len(d.get("symbols", {})) + len(d.get("consts", {}))
            if proposed:
                auto_notes.append(
                    f"safety: suppressed {proposed} operand-map proposal(s) "
                    "from non-positional alignment")
                auto_notes.extend(
                    f"safety: diagnostic-only symbol {old} -> {new}"
                    for old, new in sorted(d.get("symbols", {}).items()))
                auto_notes.extend(
                    f"safety: diagnostic-only constant {old} -> {new}"
                    for old, new in sorted(d.get("consts", {}).items()))
        target_symbols = set(d.get("target_symbols", set()))
        pairs = ad.as_maps(d) + pairs
        em, en = enum_map(body,
                          Path(path).parent / f"{Path(path).parent.name}.h",
                          Path(REPO / stub_path).parent
                          / f"{Path(stub_path).parent.name}.h",
                          allow_apply=not bool(adapt_kind))
        pairs += [f"{k}={v}" for k, v in em.items()]
        auto_notes += [f"enum: {x}" for x in en]

    # Constants the C reaches through a macro cannot be substituted as
    # literals; rewrite the macro argument instead, verified by evaluation.
    mc, mc_notes = macro_consts(body, pairs)
    auto_notes += [f"macro: {x}" for x in mc_notes]
    body, map_notes = apply_map(body, pairs + mc)
    body, api_notes = adapt_api_surfaces(body, target_symbols)
    decls, decl_notes = auto_decls(body, REPO / stub_path, defining=fn)
    if adapt_kind:
        donor_decls, donor_notes = donor_scope_decls(
            body, REPO / path, REPO / stub_path, defining=fn)
        decls = list(dict.fromkeys(decls + donor_decls))
        decl_notes += donor_notes
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
    readiness = "adaptable draft" if adapt_kind else "ready"
    detail = (f"{readiness}: {len(body)} chars from the {src_kind} "
              f"{path}\n  stub: {stub_path}"
              + (f"\n  renamed {base} -> {fn}" if base != fn else ""))
    for n in auto_notes:
        detail += f"\n  {n}"
    for n in map_notes:
        detail += f"\n  map: {n}"
    for n in api_notes:
        detail += f"\n  api: {n}"
    for n in decl_notes:
        detail += f"\n  decl: {n}"
    return True, body, detail


def run(fn: str, apply: bool, mapping: list[str] | None = None,
        auto: bool = False, adapt: bool = False, overlay: str = "") -> int:
    ok, body, detail = preflight(
        fn, mapping, auto or adapt, adapt=adapt, stub_overlay=overlay)
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
    record_id = f"us:{overlay.upper()}:{fn}" if overlay else ""
    good, why = ps.land_match(Path("."), fn, body=body, rec_id=record_id)
    print(f"  {'MATCHED' if good else 'not a match'}: {why}")
    if good:
        print("\n  The overlay rebuilt and all 81 SHA-1s verified. Report it "
              "with\n  queue_report(status='matched', proof=...) -- this tool "
              "does not write\n  to the queue.")
    else:
        print("\n  Reverted. src/ is back to HEAD; land_match proves the "
              "revert rather\n  than asserting it.")
    return 0 if good else 2


def score_draft(fn: str, mapping: list[str] | None = None,
                body: str = "", detail: str = "", overlay: str = "") -> dict:
    """Isolated permuter debug score for one target-informed draft."""
    if not body:
        ok, body, detail = preflight(
            fn, mapping, auto=True, adapt=True, stub_overlay=overlay)
        if not ok:
            return {"function": fn, "score": None, "status": "preflight-failed",
                    "archive": "", "detail": detail}
    supervisor = _sup()
    first = supervisor.score_body_draft(
        fn, body, detail, overlay_hint=overlay)
    aliases = {
        old: new for old, new in
        (first.get("relocation_aliases") or {}).items()
        if (re.fullmatch(r"[A-Za-z_]\w*", old)
            and re.fullmatch(r"[A-Za-z_]\w*", new) and old != new)
    }
    if first.get("score") is None or not aliases:
        return first

    mapped_body, map_notes = apply_map(
        body, [f"{old}={new}" for old, new in sorted(aliases.items())])
    if mapped_body == body:
        return first
    lineage = {
        "prior_score": first.get("score"),
        "prior_archive": first.get("archive", ""),
        "relocation_aliases": aliases,
    }
    normalized_detail = detail
    for note in map_notes:
        normalized_detail += f"\n  score relocation: {note}"
    normalized_detail += f"\n  prior score evidence: {first.get('archive', '')}"
    return supervisor.score_body_draft(
        fn, mapped_body, normalized_detail, context=lineage,
        overlay_hint=overlay)


def score_one(fn: str, mapping: list[str] | None = None,
              overlay: str = "") -> int:
    result = score_draft(fn, mapping, overlay=overlay)
    score = result.get("score")
    print(f"{fn}\n  status: {result.get('status')}")
    print(f"  score:  {score if score is not None else 'not available'}")
    print(f"  detail: {result.get('detail', '')}")
    if result.get("archive"):
        print(f"  evidence: {result['archive']}")
    print("\nNo game build or queue write was performed. A score of zero is "
          "only a build candidate, never a match verdict.")
    return 0 if score is not None else 1


def score_scan_preflight_status(ok: bool, detail: str) -> str:
    """Render every exact preflight outcome instead of silently dropping it."""
    if ok and detail.startswith("adaptable draft:"):
        return ""
    if ok and detail.startswith("ready:"):
        return "ready-unscored"
    match = re.search(r"(?m)^scan-class:\s*([^\n]+)", detail)
    if match:
        return match.group(1).strip()
    return "preflight-failed"


def score_scan_failed(rows: list[dict]) -> bool:
    failures = {
        "preflight-error", "preflight-failed", "import-failed",
        "debug-failed", "archive-failed", "source-restore-failed", "error",
    }
    return not rows or any(row.get("status") in failures for row in rows)


def score_scan(limit: int = 0, overlay: str = "") -> int:
    """Generate, isolate-score and rank adaptable queue records."""
    recs = _harv().unmatched_records()
    if overlay:
        recs = [rec for rec in recs if overlay.lower() in rec[1].lower()]
    dirty = _sup().require_clean_src()
    if dirty:
        print(f"src/ is not clean: {dirty}")
        return 1

    rows: list[dict] = []
    attempted = 0
    for _rid, ovl, fn in recs:
        try:
            ok, body, detail = preflight(
                fn, None, auto=True, skip_clean=True, adapt=True,
                stub_overlay=ovl)
        except Exception as exc:                              # noqa: BLE001
            rows.append({"function": fn, "overlay": ovl, "score": None,
                         "status": "preflight-error", "archive": "",
                         "detail": f"{type(exc).__name__}: {exc}"})
            continue
        preflight_status = score_scan_preflight_status(ok, detail)
        if preflight_status:
            rows.append({"function": fn, "overlay": ovl, "score": None,
                         "status": preflight_status, "archive": "",
                         "detail": detail})
            continue
        print(f"[score] {fn} ({ovl})", flush=True)
        result = score_draft(fn, body=body, detail=detail, overlay=ovl)
        result["overlay"] = ovl
        rows.append(result)
        attempted += 1
        if limit and attempted >= limit:
            break

    ranked = sorted(rows, key=lambda row: (
        row.get("score") is None,
        row.get("score") if row.get("score") is not None else 10**18,
        row["function"]))
    print(f"\n{len(ranked)} exact candidate result(s), {attempted} isolated "
          "score(s). Nothing touched the queue or invoked a game build.\n")
    print(f"{'score':>8}  {'function':36} {'overlay':12} status")
    print("-" * 92)
    for row in ranked:
        value = str(row["score"]) if row.get("score") is not None else "-"
        print(f"{value:>8}  {row['function'][:35]:36} "
              f"{row.get('overlay', '')[:11]:12} {row.get('status', '')}")
        if row.get("archive"):
            print(f"          evidence: {row['archive']}")
        if row.get("score") is None:
            print(f"          detail: {row.get('detail', '')[:160]}")
    return 1 if score_scan_failed(ranked) else 0


def _score_receipt_identity(data: dict) -> tuple[str, str, str]:
    """Return (queue id, overlay, function) from one isolated-score receipt."""
    fn = str(data.get("function") or "").strip()
    asm_rel = str(data.get("asm") or "").replace("\\", "/").strip("/")
    source = str(data.get("source") or "").replace("\\", "/").strip("/")
    match = re.match(r"^(.+?)/nonmatchings/", asm_rel)
    if not fn or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", fn):
        raise ValueError("receipt has no valid function")
    if match is None:
        raise ValueError(f"receipt has no exact overlay asm path: {asm_rel}")
    if not source.startswith("src/"):
        raise ValueError(f"receipt has no in-tree source path: {source}")
    overlay = match.group(1).strip("/")
    return f"us:{overlay.upper()}:{fn}", overlay, fn


def _load_score_receipt(path: Path, root: Path = SCORE_ROOT,
                        repo: Path = REPO) -> dict:
    """Validate and load one receipt together with its exact scored body."""
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"receipt escapes score root: {path}") from exc
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("status") != "scored" or not isinstance(data.get("score"), int):
        raise ValueError(f"receipt is not a completed numeric score: {path}")
    record_id, overlay, fn = _score_receipt_identity(data)
    expected_archive = path.parent.resolve().relative_to(
        repo.resolve()).as_posix()
    if data.get("archive") != expected_archive:
        raise ValueError(
            f"receipt archive ownership mismatch: {data.get('archive')} != "
            f"{expected_archive}")
    body_path = path.parent / "transplant-body.c"
    if not body_path.is_file():
        raise ValueError(f"receipt has no transplant-body.c: {path}")
    body = body_path.read_text(encoding="utf-8")
    if not re.search(rf"\b{re.escape(fn)}\s*\(", body):
        raise ValueError(f"scored body does not contain {fn}: {body_path}")
    asm_rel = str(data["asm"]).replace("\\", "/")
    expected_leaf = f"/{fn}.s"
    if not asm_rel.endswith(expected_leaf):
        raise ValueError(f"receipt asm does not end in {fn}.s: {asm_rel}")
    return {
        "record_id": record_id,
        "overlay": overlay,
        "function": fn,
        "score": data["score"],
        "source": str(data["source"]).replace("\\", "/"),
        "asm": asm_rel,
        "stub_asm": asm_rel[:-len(expected_leaf)],
        "receipt": path.resolve().relative_to(repo.resolve()).as_posix(),
        "body_path": body_path,
        "body": body,
    }


def latest_score_receipts(root: Path = SCORE_ROOT,
                          repo: Path = REPO) -> list[dict]:
    """Newest valid scored body per exact queue record."""
    latest: dict[str, tuple[tuple[int, str], Path]] = {}
    if not root.is_dir():
        return []
    for path in root.glob("*/*/adapt-score.json"):
        # Older pre-archive receipts may be incomplete. They still participate
        # in recency selection, but only the newest receipt for a record must
        # satisfy the strict ownership and body checks below. Validating every
        # historical attempt first would let one superseded receipt block the
        # complete current generation.
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("status") != "scored" or not isinstance(
                data.get("score"), int):
            continue
        record_id, _overlay, _fn = _score_receipt_identity(data)
        order = (path.stat().st_mtime_ns, path.as_posix())
        prior = latest.get(record_id)
        if prior is None or order > prior[0]:
            latest[record_id] = (order, path)
    rows = [_load_score_receipt(item[1], root=root, repo=repo)
            for item in latest.values()]
    return sorted(rows, key=lambda row: row["record_id"])


def _selected_score_receipts(min_score: int, max_score: int,
                             overlay: str = "", limit: int = 0) -> list[dict]:
    rows = [row for row in latest_score_receipts()
            if min_score <= row["score"] <= max_score]
    if overlay:
        rows = [row for row in rows
                if overlay.lower() in row["overlay"].lower()]
    rows.sort(key=lambda row: (row["score"], row["record_id"]))
    return rows[:limit] if limit else rows


def _validate_receipt_target(row: dict) -> tuple[bool, str]:
    """Prove the receipt still names the exact live stub it measured."""
    found = _sup().find_stub(row["function"], row["overlay"])
    if found is None:
        return False, "no exact live INCLUDE_ASM stub"
    source_path, asm_rel, _stub = found
    source = source_path.resolve().relative_to(REPO.resolve()).as_posix()
    if source != row["source"] or asm_rel != row["stub_asm"]:
        return False, (f"stale receipt target: source={row['source']} "
                       f"asm={row['stub_asm']}; live source={source} "
                       f"asm={asm_rel}")
    return True, "exact live target"


def _isolated_seed_artifact(row: dict) -> tuple[str, str]:
    """Build a versioned whole-file permuter seed from an isolated receipt."""
    sys.path.insert(0, str(REPO / "automation" / "win"))
    import worker_direct as wd                              # type: ignore

    ctx = {"src_rel": row["source"], "asm_rel": row["stub_asm"]}
    whole = wd.virtual_apply(ctx, row["function"], row["body"])
    if not whole:
        raise ValueError("receipt body no longer replaces its exact live stub")
    whole = wd._declare_stub_siblings(whole, row["body"])
    artifact = (
        "/* PERMUTER SEED -- deterministic isolated-score candidate.\n"
        f"   record : {row['record_id']}\n"
        f"   score  : {row['score']}\n"
        f"   receipt: {row['receipt']}\n"
        "   producer: compiled-donor transplant, no model\n"
        "   content: WHOLE FILE (isolated adaptable draft)\n"
        f"   origin : {row['source']}\n"
        f"   asm    : asm/us/{row['asm']}\n"
        "   verdict: the exact target function compiled under the project\n"
        "            compiler and flags but did not score zero. A full game\n"
        "            build was intentionally not run. Import and search via\n"
        "            permuter_supervisor.py; never treat this as a match. */\n"
        + whole)
    rec = {"id": row["record_id"], "function": row["function"]}
    seed = artifact_store.publish_versioned_artifact(
        wd.candidate_path(rec), artifact, "isolated-score candidate", REPO)
    return seed, artifact


def publish_low_scores(apply: bool, min_score: int = 1, max_score: int = 35,
                       overlay: str = "", limit: int = 0) -> int:
    """Publish the latest low isolated scores as immutable whole-file seeds."""
    rows = _selected_score_receipts(min_score, max_score, overlay, limit)
    if not rows:
        print("no current isolated-score receipts in the requested range")
        return 0
    print(f"{len(rows)} exact receipt(s), scores {min_score}..{max_score}")
    if not apply:
        for row in rows:
            print(f"  {row['score']:5}  {row['record_id']}  {row['receipt']}")
        print("\nDRY RUN. Nothing published. Re-run with --apply.")
        return 0

    failed = 0
    for row in rows:
        valid, why = _validate_receipt_target(row)
        if not valid:
            print(f"REFUSED {row['record_id']}: {why}")
            failed += 1
            continue
        try:
            seed, _artifact = _isolated_seed_artifact(row)
        except (OSError, ValueError) as exc:
            print(f"FAILED {row['record_id']}: {type(exc).__name__}: {exc}")
            failed += 1
            continue
        print(f"PUBLISHED {row['record_id']} score={row['score']} "
              f"seed={seed} receipt={row['receipt']}")
    return 1 if failed else 0


def land_score_zeros(apply: bool, overlay: str = "", limit: int = 0) -> int:
    """Full-build the exact newest score-zero bodies, sequentially."""
    rows = _selected_score_receipts(0, 0, overlay, limit)
    if not rows:
        print("no current score-zero receipts")
        return 0
    print(f"{len(rows)} exact score-zero receipt(s)")
    if not apply:
        for row in rows:
            print(f"  {row['record_id']}  {row['receipt']}")
        print("\nDRY RUN. Nothing built. Re-run with --apply.")
        return 0

    start_dirty = _dirty_files()
    if start_dirty:
        print(f"src/ is not clean to begin with: {sorted(start_dirty)}")
        return 1
    landed: set[str] = set()
    failed = 0
    for index, row in enumerate(rows, 1):
        unexpected = _dirty_files() - landed
        if unexpected:
            print(f"STOPPING: unexpected src/ change in {sorted(unexpected)}")
            return 1
        valid, why = _validate_receipt_target(row)
        if not valid:
            print(f"REFUSED {row['record_id']}: {why}")
            return 1
        print(f"\n[{index}/{len(rows)}] {row['record_id']}\n"
              f"  receipt: {row['receipt']}", flush=True)
        good, verdict = _sup().land_match(
            Path("."), row["function"], body=row["body"],
            rec_id=row["record_id"])
        if good:
            landed |= (_dirty_files() - landed)
            result = "MATCHED"
        else:
            result = "NOT_MATCHED"
            if (verdict.startswith("INTERNAL ERROR")
                    or verdict.startswith("TREE ALREADY BROKEN")
                    or "seed=NONE" in verdict
                    or "rejected=NONE" in verdict):
                failed += 1
        print(f"RESULT {row['record_id']} {result} "
              f"receipt={row['receipt']} verdict={verdict}", flush=True)
        if failed:
            print("STOPPING after an unpreserved or unattributable outcome")
            break
    return 1 if failed else 0


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


def scan_failure_bucket(detail: str) -> str:
    """Classify one unsuccessful automatic twin preflight."""
    marker = re.search(
        r"(?m)^scan-class:\s*(adaptable|needs-maps|not-twin|no-twin|error)\s*$",
        detail)
    return marker.group(1) if marker else "error"


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
      needs-maps  a local donor exists, but its assembly disappeared when it
                   was decompiled. Automatic delta proof is unavailable, so
                   derive explicit maps from the target assembly before a
                   dry-run preflight.
      adaptable   compiled donor evidence is structurally close or differs
                   only in scheduling. The tool can generate a target-informed
                   draft, but it is not clean enough to call build-ready.
      not-twin    the assembly genuinely differs: different length, or a
                   different instruction. No amount of renaming fixes that,
                  and saying so is more useful than a failed build.
      no-twin     nothing in the tree defines this function under another
                   name.
      error       the scan could not classify the evidence honestly. This is
                  an instrument or unsupported-preflight failure, not proof
                  that no donor exists.
    """
    uh = _harv()
    recs = uh.unmatched_records()
    if overlay:
        recs = [r for r in recs if overlay.lower() in r[1].lower()]
    if limit:
        recs = recs[:limit]

    buckets: dict[str, list] = {"ready": [], "needs-defs": [],
                                "adaptable": [], "needs-maps": [],
                                "not-twin": [], "no-twin": [], "error": []}
    dirty = _sup().require_clean_src()
    if dirty:
        print(f"src/ is not clean: {dirty}\n")
        return 1
    for _rid, ovl, fn in recs:
        try:
            ok, _body, detail = preflight(fn, None, auto=True,
                                          skip_clean=True,
                                          stub_overlay=ovl)
        except Exception as e:                                # noqa: BLE001
            buckets["error"].append((fn, ovl, f"error: {type(e).__name__}"))
            continue
        if not ok:
            why = detail.splitlines()[-1].strip()
            key = scan_failure_bucket(detail)
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
    for k in ("ready", "needs-defs", "adaptable", "needs-maps", "not-twin",
              "no-twin", "error"):
        print(f"  {k:12} {len(buckets[k])}")
    for k in ("ready", "needs-defs", "adaptable", "needs-maps", "not-twin",
              "error"):
        if not buckets[k]:
            continue
        print(f"\n=== {k} ===")
        for fn, ovl, why in buckets[k]:
            print(f"  {fn[:34]:36}{ovl[:12]:14}{why}")
    if buckets["ready"]:
        print("\nEach `ready` is one build away from a verdict:")
        print("  transplant.py --function <name> --auto --apply")
    if buckets["adaptable"]:
        print("\nEach `adaptable` can become a target-informed dry-run draft:")
        print("  transplant.py --function <name> --auto --adapt")
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
    for fn, ovl in rows:
        if limit and done >= limit:
            break
        now = _dirty_files()
        if now - landed:
            print(f"\nSTOPPING: unexpected change in {sorted(now - landed)}")
            print("The tree is not in the state the next build assumes.")
            break
        ok, body, detail = preflight(
            fn, None, auto=True, skip_clean=True, stub_overlay=ovl)
        if not ok:
            results.append((fn, "skipped", detail.splitlines()[-1].strip()))
            continue
        done += 1
        print(f"\n[{done}] {fn}", flush=True)
        good, why = _sup().land_match(
            Path("."), fn, body=body, rec_id=f"us:{ovl.upper()}:{fn}")
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
    ck("find_stub(fn" in body_fn and "find_stub(base" not in body_fn,
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

    print("\nordinal enum mapping requires matching entity-update evidence")
    import tempfile as _tempfile
    with _tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src_dir, dst_dir = root / "rno3", root / "rno0"
        src_dir.mkdir()
        dst_dir.mkdir()
        src_h, dst_h = src_dir / "rno3.h", dst_dir / "rno0.h"
        src_h.write_text(
            "enum EntityID {\n"
            "    E_NONE, // EntityNone\n"
            "    E_NOVA_PULSE, // EntityNovaLaserPulse\n"
            "};\n", encoding="utf-8")
        dst_h.write_text(
            "enum EntityID {\n"
            "    E_NONE, // EntityNone\n"
            "    E_CORPSEWEED_PROJECTILE, // EntityCorpseweedProjectile\n"
            "};\n", encoding="utf-8")
        (src_dir / "e_init.c").write_text(
            "PfnEntityUpdate EntityUpdates[] = {\n"
            "    EntityNovaLaserPulse,\n"
            "};\n", encoding="utf-8")
        (dst_dir / "e_init.c").write_text(
            "PfnEntityUpdate EntityUpdates[] = {\n"
            "    EntityCorpseweedProjectile,\n"
            "};\n", encoding="utf-8")
        em, en = enum_map("void f(void) { E_NOVA_PULSE; }", src_h, dst_h)
        ck(em == {},
           f"same ordinal but different entity is rejected ({em})")
        ck(any("left alone" in n or "rejected" in n for n in en),
           f"the rejected guess is reported ({en})")
        ck(any("EntityNovaLaserPulse != EntityCorpseweedProjectile" in n
               for n in en),
           f"the proof reads the entityId-minus-one dispatch slot ({en})")
        src_h.write_text(
            "enum EntityID {\n"
            "    E_NONE,\n"
            "    E_ID_16,\n"
            "};\n", encoding="utf-8")
        dst_h.write_text(
            "enum EntityID {\n"
            "    E_NONE,\n"
            "    E_UNK_16,\n"
            "};\n", encoding="utf-8")
        (src_dir / "e_init.c").write_text(
            "PfnEntityUpdate EntityUpdates[] = {\n"
            "    func_us_801CC8F8,\n"
            "};\n", encoding="utf-8")
        (dst_dir / "e_init.c").write_text(
            "PfnEntityUpdate EntityUpdates[] = {\n"
            "    func_us_801CC8F8_from_no0,\n"
            "};\n", encoding="utf-8")
        proven, _ = enum_map("void f(void) { E_ID_16; }", src_h, dst_h)
        ck(proven == {"E_ID_16": "E_UNK_16"},
           f"matching dispatch functions prove the ordinal rename ({proven})")
        suppressed, sn = enum_map(
            "void f(void) { E_ID_16; }", src_h, dst_h, allow_apply=False)
        ck(suppressed == {} and any("suppressed" in n for n in sn),
           f"even a proven enum rename is diagnostic-only for near twins "
           f"({suppressed}, {sn})")

        print("\nentity-update proof reads only the US conditional branch")
        (src_dir / "e_init.c").write_text(
            "#ifdef VERSION_PSP\n"
            "PfnEntityUpdate EntityUpdates[] = { PspOnlySource };\n"
            "#else\n"
            "PfnEntityUpdate EntityUpdates[] = { func_us_801CC8F8 };\n"
            "#endif\n", encoding="utf-8")
        (dst_dir / "e_init.c").write_text(
            "#if defined(VERSION_PSP)\n"
            "PfnEntityUpdate EntityUpdates[] = { PspOnlyDestination };\n"
            "#else\n"
            "PfnEntityUpdate EntityUpdates[] = { func_us_801CC8F8_from_no0 };\n"
            "#endif\n", encoding="utf-8")
        ck(_entity_updates(src_h) == ["func_us_801CC8F8"],
           f"the PSP table is excluded ({_entity_updates(src_h)})")
        visible = _us_visible_source(
            "#ifdef VERSION_PSP\nint psp;\n#else\nint us;\n#endif\n")
        ck("int us;" in visible and "int psp;" not in visible,
           f"only the US declaration survives ({visible!r})")
        ck(not any(line.lstrip().startswith("#")
                   for line in visible.splitlines()),
           f"no orphan conditional directives survive ({visible!r})")

    print("\nAPI surface adaptation follows target relocation evidence")
    api_body, api_notes = adapt_api_surfaces(
        "g_api.AllocPrimitives(3, 6); g_api.PlaySfx(1);",
        {"g_api_AllocPrimitives"})
    ck("g_api_AllocPrimitives(3, 6)" in api_body,
       f"the target-proven standalone pointer is selected ({api_body})")
    ck("g_api.PlaySfx(1)" in api_body,
       "an API member without target evidence is left alone")
    ck(any("target-proven" in note for note in api_notes),
       f"the evidence-based rewrite is reported ({api_notes})")

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
        d9, n9 = auto_decls(
            "void f(void){ DRAW_COLORS; PL_W_HOLYWATER_FLAMES; }", dest)
        ck(d9 == [] and not any("NO DECLARATION" in x for x in n9),
           f"shared uppercase macros and enum members are not false blockers "
           f"({d9}, {n9})")
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

        print("\nadaptable drafts derive donor-local compile dependencies")
        resolver = globals().get("donor_scope_decls")
        ck(resolver is not None,
           "the donor-scope dependency resolver is available")
        if resolver is not None:
            donor_dir = ov / "donor"
            target_dir = ov / "target"
            donor_dir.mkdir()
            target_dir.mkdir()
            donor = donor_dir / "donor.c"
            (donor_dir / "donor.h").write_text(
                "#define DONOR_COUNT 4\n"
                "extern EInit g_HeaderOnly;\n"
                "extern char* donor_label;\n"
                "extern char donor_label[];\n"
                "enum { E_NONE, E_GREY_PUFF };\n",
                encoding="utf-8")
            donor.write_text(
                '#include "donor.h"\n'
                "extern EInit g_EInitNova;\n"
                "#ifdef VERSION_PSP\n"
                "extern s32 E_ID(GREY_PUFF);\n"
                "extern u16 conditional_values[];\n"
                "#else\n"
                "static u16 conditional_values[] = {1, 2};\n"
                "#endif\n"
                "static s16 sensors2[] = {0, 20, 12, 0};\n"
                "static s16 sized_by_init[] = {1, 2, 3};\n"
                "static s8 unused[] = {1, 2};\n"
                "typedef enum {\n"
                "    NOVA_INIT,\n"
                "    NOVA_IDLE,\n"
                "    NOVA_CHARGE,\n"
                "} NovaSteps;\n"
                "static void donor_fn(void) {\n"
                "    enum LocalStep { LOCAL_ZERO = 0 };\n"
                "    s32 unused = UnkCollisionFunc2(&sensors2);\n"
                "    InitializeEntity(g_EInitNova);\n"
                "    InitializeEntity(g_HeaderOnly);\n"
                "    SetStep(NOVA_CHARGE);\n"
                "    SetStep(DONOR_COUNT);\n"
                "    use(donor_label, conditional_values, sized_by_init, "
                "E_ID(GREY_PUFF), LOCAL_ZERO);\n"
                "}\n", encoding="utf-8")
            score_dest = target_dir / "target.c"
            score_dest.write_text('#include "target.h"\n', encoding="utf-8")
            donor_decls, donor_notes = resolver(
                "static void target(void) {\n"
                "    enum LocalStep { LOCAL_ZERO = 0 };\n"
                "    s32 unused = UnkCollisionFunc2(&sensors2);\n"
                "    InitializeEntity(g_EInitNova);\n"
                "    InitializeEntity(g_HeaderOnly);\n"
                "    SetStep(NOVA_CHARGE);\n"
                "    SetStep(DONOR_COUNT);\n"
                "    use(donor_label, conditional_values, sized_by_init, "
                "E_ID(GREY_PUFF), LOCAL_ZERO);\n"
                "}\n", donor, score_dest)
            ck("extern s16 sensors2[4];" in donor_decls,
               f"a referenced donor-local array gets its exact type ({donor_decls})")
            ck("extern EInit g_EInitNova;" in donor_decls,
               f"an existing donor extern is carried into the draft ({donor_decls})")
            ck("#define NOVA_CHARGE 2" in donor_decls,
               f"an implicit enum value is derived numerically ({donor_decls})")
            ck("#define DONOR_COUNT 4" in donor_decls,
               f"a referenced object-like macro is carried exactly ({donor_decls})")
            ck("extern EInit g_HeaderOnly;" in donor_decls,
               f"direct local includes participate in dependency lookup ({donor_decls})")
            ck(sum("donor_label" in item for item in donor_decls) == 1,
               f"conditional declaration shapes cannot conflict ({donor_decls})")
            ck(not any("E_ID(GREY_PUFF)" in item for item in donor_decls),
               f"an inactive VERSION_PSP declaration is ignored ({donor_decls})")
            ck("#define E_GREY_PUFF 1" in donor_decls,
               f"a US E_ID call carries its donor enum value for scoring "
               f"({donor_decls})")
            ck(not any("LOCAL_ZERO" in item for item in donor_decls),
               f"a function-local enum member is not emitted as a macro "
               f"({donor_decls})")
            ck("extern u16 conditional_values[2];" in donor_decls,
               f"the active US branch supplies an array extent ({donor_decls})")
            ck("extern s16 sized_by_init[3];" in donor_decls,
               f"a braced initializer supplies an exact compile-only extent "
               f"({donor_decls})")
            ck(not any(re.search(r"\bunused\b", item)
                       for item in donor_decls),
               f"a function-local variable is never promoted to extern ({donor_decls})")
            ck(any("score-only" in item for item in donor_notes),
               f"the declaration boundary is explicit ({donor_notes})")

    print("\nqueue identity disambiguates repeated function names")
    bo6_shaft = _sup().find_stub("EntityShaft", "BOSS/BO6")
    rcen_shaft = _sup().find_stub("EntityShaft", "ST/RCEN")
    ck(bo6_shaft is not None and "/boss/bo6/" in
       bo6_shaft[0].as_posix().lower(),
       f"the BO6 queue record selects its own stub ({bo6_shaft})")
    ck(rcen_shaft is not None and "/st/rcen/" in
       rcen_shaft[0].as_posix().lower(),
       f"the RCEN queue record selects its own stub ({rcen_shaft})")

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
    exact_calls = []
    real_harv = globals()["_harv"]
    real_sup = globals()["_sup"]
    real_preflight = globals()["preflight"]
    class _FakeHarvester:
        @staticmethod
        def unmatched_records():
            return [
                ("us:BOSS/BO6:EntityShaft", "BOSS/BO6", "EntityShaft"),
                ("us:ST/RCEN:EntityShaft", "ST/RCEN", "EntityShaft"),
            ]
    class _FakeSupervisor:
        @staticmethod
        def require_clean_src():
            return ""
    def _fake_preflight(fn, _mapping, **kwargs):
        exact_calls.append((fn, kwargs.get("stub_overlay")))
        return False, "", "scan-class: no-twin\nfixture"
    try:
        globals()["_harv"] = lambda: _FakeHarvester()
        globals()["_sup"] = lambda: _FakeSupervisor()
        globals()["preflight"] = _fake_preflight
        exact_scan_rc = scan()
    finally:
        globals()["_harv"] = real_harv
        globals()["_sup"] = real_sup
        globals()["preflight"] = real_preflight
    ck(exact_scan_rc == 0 and exact_calls == [
           ("EntityShaft", "BOSS/BO6"),
           ("EntityShaft", "ST/RCEN"),
       ],
       f"ordinary scan carries each duplicate's queue overlay ({exact_calls})")
    for k in ("ready", "needs-defs", "adaptable", "needs-maps", "not-twin",
              "no-twin", "error"):
        ck(f'"{k}"' in scan_src, f"the {k} class exists")
    ck(scan_failure_bucket(
        "scan-class: adaptable\nno usable twin; structural near")
       == "adaptable",
       "a structurally close donor is kept as an adaptable draft route")
    ck(scan_failure_bucket(
        "scan-class: not-twin\nno usable twin; candidate is not a twin")
       == "not-twin",
       "a structural mismatch is separated from a missing twin")
    ck(scan_failure_bucket(
        "scan-class: needs-maps\n"
        "no usable twin; tried RicStepStand: no distinct twin asm")
       == "needs-maps",
       "a decompiled donor without a retained asm listing needs manual maps")
    ck(scan_failure_bucket(
        "scan-class: needs-maps\n"
        "no usable twin; tried RicStepStand: no distinct twin asm; "
        "RicStepRun: candidate is not a twin") == "needs-maps",
       "an unproven donor outranks a different candidate disproved by asm")
    ck(scan_failure_bucket(
        "scan-class: error\nno usable twin; tried RicStepStand: parse error")
       == "error",
       "an instrument failure is not reported as evidence that no twin exists")
    ck(scan_failure_bucket("unstructured preflight failure") == "error",
       "unknown failure prose falls back to an honest error class")
    ck(aggregate_candidate_failures(["not-twin", "needs-maps"])
       == "needs-maps",
       "mixed candidate evidence keeps the unresolved manual-map route")
    ck(aggregate_candidate_failures(["not-twin", "adaptable"])
       == "adaptable",
       "a viable structural draft outranks a disproved donor")
    ck(aggregate_candidate_failures(["no-definition", "error"])
       == "error",
       "an errored candidate is not collapsed into no-twin")
    ck(aggregate_candidate_failures(["no-definition"]) == "no-twin",
       "no-twin is reserved for candidates with no local definition")

    print("\nscore scans retain every exact record and fail on tool errors")
    ck(score_scan_preflight_status(
           False, "scan-class: not-twin\nstructural mismatch") == "not-twin",
       "a structural not-twin is rendered instead of silently skipped")
    ck(score_scan_preflight_status(True, "ready: clean twin")
       == "ready-unscored",
       "a clean twin remains visible even though it needs no isolated score")
    ck(not score_scan_failed([
           {"status": "scored", "score": 0},
           {"status": "not-twin", "score": None},
       ]),
       "honest scored and structural outcomes make a successful scan")
    ck(score_scan_failed([
           {"status": "scored", "score": 10},
           {"status": "debug-failed", "score": None},
       ]),
       "one tool failure cannot hide behind another record's numeric score")

    print("\nreceipt-driven landing consumes only current owned evidence")
    with tempfile.TemporaryDirectory() as td:
        fake_repo = Path(td)
        fake_root = fake_repo / "nonmatchings" / ".adapt-scores"
        for stamp, score, archive_ok, marker in [
                ("20260818-010000-1-1", 20, False, "old"),
                ("20260818-020000-1-1", 0, True, "new")]:
            receipt_dir = fake_root / stamp / "FixtureFunction"
            receipt_dir.mkdir(parents=True)
            archive = receipt_dir.relative_to(fake_repo).as_posix()
            (receipt_dir / "adapt-score.json").write_text(json.dumps({
                "archive": archive if archive_ok else "",
                "asm": "st/test/nonmatchings/file/FixtureFunction.s",
                "function": "FixtureFunction",
                "score": score,
                "source": "src/st/test/file.c",
                "status": "scored",
            }), encoding="utf-8")
            (receipt_dir / "transplant-body.c").write_text(
                f"void FixtureFunction(void) {{ /* {marker} */ }}\n",
                encoding="utf-8")
        receipt_rows = latest_score_receipts(fake_root, fake_repo)
        ck(len(receipt_rows) == 1 and receipt_rows[0]["score"] == 0,
           "a superseded incomplete receipt cannot block the newest one")
        ck("new" in receipt_rows[0]["body"]
           and "old" not in receipt_rows[0]["body"],
           "the selected body is byte-for-byte from the newest receipt")
        ck(receipt_rows[0]["record_id"]
           == "us:ST/TEST:FixtureFunction",
           "the queue id is derived from the exact receipt overlay")
    landing_src = src[src.index("def land_score_zeros"):
                      src.index("\ndef list_all")]
    ck('body=row["body"]' in landing_src,
       "landing passes the archived body directly to land_match")
    ck("score_draft" not in landing_src and "preflight(" not in landing_src,
       "landing never regenerates the body it is meant to prove")
    publishing_src = src[src.index("def _isolated_seed_artifact"):
                         src.index("\ndef publish_low_scores")]
    ck("artifact_store.publish_versioned_artifact" in publishing_src
       and "content: WHOLE FILE" in publishing_src,
       "low scores publish an immutable whole-file supervisor seed")

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

    print("\nadaptable drafts have an isolated score path")
    definitions = {node.name for node in tree.body
                   if isinstance(node, _ast.FunctionDef)}
    ck("score_draft" in definitions,
       "a draft can be compiled and scored without a game build")
    parser_flags = {
        node.args[0].value
        for node in _ast.walk(tree)
        if (isinstance(node, _ast.Call)
            and isinstance(node.func, _ast.Attribute)
            and node.func.attr == "add_argument"
            and node.args and isinstance(node.args[0], _ast.Constant)
            and isinstance(node.args[0].value, str))
    }
    ck("--score" in parser_flags,
       "the score path is reachable through the existing connector surface")
    ck(_sup().parse_debug_score("base score = 60\n") == 60,
       "the debug receipt yields its numeric score")
    ck(_sup().parse_debug_score("compile failed") is None,
       "a compile failure cannot masquerade as score zero")
    class _FakeScoreSupervisor:
        def __init__(self):
            self.calls = []

        def score_body_draft(self, fn, body, detail, **kwargs):
            self.calls.append((fn, body, detail, kwargs))
            if len(self.calls) == 1:
                return {
                    "function": fn, "score": 10, "status": "scored",
                    "archive": "nonmatchings/.adapt-scores/first/target",
                    "relocation_aliases": {"sensors2": "D_us_80181FAC"},
                }
            return {
                "function": fn, "score": 0, "status": "scored",
                "archive": "nonmatchings/.adapt-scores/second/target",
                "relocation_aliases": {},
            }

    fake_score = _FakeScoreSupervisor()
    real_sup_factory = globals()["_sup"]
    globals()["_sup"] = lambda: fake_score
    try:
        rescored = score_draft(
            "target", body=("extern s16 sensors2[];\n"
                            "void target(void) { use(sensors2); }\n"),
            detail="fixture")
    finally:
        globals()["_sup"] = real_sup_factory
    ck(rescored.get("score") == 0 and len(fake_score.calls) == 2,
       "a relocation-only residue is automatically re-scored once")
    if len(fake_score.calls) == 2:
        second_body = fake_score.calls[1][1]
        ck("D_us_80181FAC" in second_body and "sensors2" not in second_body,
           "the re-score uses the debug-proven target label in C")
        ck(fake_score.calls[1][3].get("context", {}).get("prior_score") == 10,
           "the second receipt links back to its unnormalized score evidence")
    score_node = next((node for node in tree.body
                       if isinstance(node, _ast.FunctionDef)
                       and node.name == "score_draft"), None)
    score_calls = set()
    if score_node is not None:
        for node in _ast.walk(score_node):
            if isinstance(node, _ast.Call):
                score_calls.add(node.func.attr if isinstance(
                    node.func, _ast.Attribute) else getattr(node.func, "id", ""))
    for danger in ("land_match", "build_and_check", "make_build",
                   "queue_report", "report"):
        ck(danger not in score_calls,
           f"isolated scoring never calls {danger} ({sorted(score_calls)})")

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
    ap.add_argument("--adapt", action="store_true",
                    help="emit a target-informed draft from a structural-near "
                         "or schedule-only donor; implies --auto")
    ap.add_argument("--score", action="store_true",
                    help="debug-score an adaptable draft without a game build; "
                         "use with --function or --scan")
    ap.add_argument("--publish-low-scores", action="store_true",
                    help="publish newest isolated scores as immutable seeds")
    ap.add_argument("--land-score-zeros", action="store_true",
                    help="full-build newest exact score-zero receipt bodies")
    ap.add_argument("--score-min", type=int, default=1)
    ap.add_argument("--score-max", type=int, default=35)
    ap.add_argument("--apply", action="store_true",
                    help="actually apply, build, verify and revert on failure")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    pairs = list(a.map)
    for chunk in a.maps:
        pairs += [x for x in chunk.split("/") if x.strip()]
    if a.score:
        if a.function:
            return score_one(a.function, pairs, a.overlay)
        if a.scan:
            return score_scan(a.limit, a.overlay)
        print("--score requires --function NAME or --scan", file=sys.stderr)
        return 2
    if a.publish_low_scores:
        return publish_low_scores(
            a.apply, a.score_min, a.score_max, a.overlay, a.limit)
    if a.land_score_zeros:
        return land_score_zeros(a.apply, a.overlay, a.limit)
    if a.list:
        return list_all()
    if a.scan:
        return scan(a.limit, a.overlay)
    if a.batch:
        return batch(a.limit, a.overlay)
    if a.function:
        return run(a.function, a.apply, pairs, a.auto, a.adapt, a.overlay)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
