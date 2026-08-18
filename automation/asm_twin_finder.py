#!/usr/bin/env python3
"""Which function in this tree is the unmatched stub a copy of?

WHY THIS EXISTS
    Four functions were matched by hand on 2026-08-01, and all four were
    already written somewhere else in the tree:

      st/rno0 func_us_801B9A8C  -> src/st/e_red_door.h:EntityIsNearPlayer
      boss/bo0 func_us_801BB014 -> the same function, wider box
      boss/bo6 BO6_RicCheckFacing
                                -> src/ric/pl_utils.c:RicCheckFacing
      boss/bo6 BO6_RicCreateEntFactoryFromEntity
                                -> src/ric/pl_blueprints.c:...

    Each was found by reading the assembly, forming a guess about what the
    function DID, and grepping for that guess. That works, and it is exactly
    the kind of work that should not depend on someone having the right hunch.
    The evidence was mechanical every time: a symbol name that survives an
    overlay prefix, or a set of globals and callees that only one function in
    the tree touches.

    Note what this does NOT claim. A twin is a place to start, not an answer.
    Two of the four differed from their twin in a load-bearing way (a
    threshold constant, a missing flag propagation), and copying either
    blindly would have produced a wrong function that happened not to match.
    The output is ranked evidence for a human or a model to check, and the
    report says so on every row.

    It also matters WHERE the twin lives. A twin inside src/st/<name>.h is a
    shared implementation, which means the right answer is usually a shim
    rather than a copy -- see shim_viable() in codebase_index.py. A twin in
    another overlay's .c is a genuine sibling and must be copied and then
    diffed, because sibling overlays routinely differ by a constant.

STRICTLY READ-ONLY. Never edits sources, never builds.

Usage:
    python3 automation/asm_twin_finder.py
    python3 automation/asm_twin_finder.py --json out.json
    python3 automation/asm_twin_finder.py --symbol BO6_RicCheckFacing
    python3 automation/asm_twin_finder.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASM_ROOT = REPO / "asm" / "us"
SRC_ROOT = REPO / "src"

# Report a callee/global-set twin only above this weighted-Jaccard score, and
# only show this many. Both are presentation choices; the scores are printed
# so a reader can disagree.
MIN_TOKEN_SCORE = 0.30
MAX_TOKEN_HITS = 3

# A token carried by more than this fraction of C functions says nothing about
# which function you are looking at. `self`, `entity`, `step` and friends fall
# out here without needing a hand-written stoplist, which is the point: a
# hand-written list goes stale as the tree grows.
MAX_DOC_FREQ = 0.08

# Splat symbol names glue several source-level identifiers together with
# underscores (PLAYER_posX_i_hi). C spells the same thing with dots
# (PLAYER.posX.i.hi). Splitting both on their own separator lands them in the
# same alphabet, which is what makes the two sides comparable at all.
_ASM_SYM_SPLIT = re.compile(r"[_.]+")
_C_IDENT = re.compile(r"[A-Za-z_]\w*")

# Overlay prefixes are a naming convention, not part of the function's
# identity: BO6_RicCheckFacing and RicCheckFacing are the same function
# compiled into two overlays. Strip a leading SHOUTY_ segment, but only when
# what remains still looks like a name rather than an address.
_OVL_PREFIX = re.compile(r"^(?:[A-Z][A-Z0-9]{1,5})_(?=[A-Za-z])")

# An address-derived name carries no information, so name matching must skip
# it. These are the two forms splat emits.
_ADDRESS_NAME = re.compile(r"^(?:func|D)_(?:us_|psp_|beta_|pspeu_|hd_)?[0-9A-Fa-f]{6,8}$")

_INSTR = re.compile(r"^\s*/\*[^*]*\*/\s+(\S+)\s*(.*?)\s*$")
_ASM_REF = re.compile(r"%(?:hi|lo)\(([A-Za-z_]\w*)|^\s*j(?:al)?\s+([A-Za-z_]\w*)")
_IMM = re.compile(r"(?<![\w$])(-?0x[0-9A-Fa-f]+|-?\d+)")


# ---------------------------------------------------------------------------
# assembly side


class Stub:
    __slots__ = ("name", "path", "overlay", "opcodes", "imms", "tokens", "still_asm")

    def __init__(self, name, path, overlay, opcodes, imms, tokens):
        self.name = name
        self.path = path
        self.overlay = overlay
        self.opcodes = opcodes
        self.imms = imms
        self.tokens = tokens
        self.still_asm = True


def parse_stub(path: Path) -> Stub | None:
    """Read one nonmatchings/*.s into opcodes, immediates and symbol tokens."""
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return None

    name = path.stem
    opcodes: list[str] = []
    imms: list[str] = []
    tokens: set[str] = set()

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith((".set", ".size", "glabel", ".L")):
            continue
        m = _INSTR.match(line)
        if not m:
            continue
        opcodes.append(m.group(1))
        operands = m.group(2)
        imms.extend(_IMM.findall(operands))
        for hi_lo, jump in _ASM_REF.findall(operands if "%" in operands else line):
            sym = hi_lo or jump
            if sym and not sym.startswith(".L"):
                tokens |= symbol_tokens(sym)

    # A data or string label extracted into nonmatchings has no instructions.
    # Content, not the filename, is what distinguishes it: seeding by name has
    # already let 34 rodata labels into the work queue once.
    if len(opcodes) < 3:
        return None

    try:
        overlay = str(path.relative_to(ASM_ROOT)).split("nonmatchings")[0].strip("/\\")
    except ValueError:
        overlay = ""
    return Stub(name, path, overlay, opcodes, imms, tokens)


def symbol_tokens(sym: str) -> set[str]:
    # Deliberately NOT prefix-stripped. The prefix regex cannot tell an
    # overlay tag from a real identifier -- PLAYER_posX_i_hi looks exactly
    # like BO6_something -- and stripping it here threw away the single most
    # informative token in the symbol. Overlay tags cost nothing if they
    # survive: they never appear in a C body, so they get no idf entry and
    # drop out of the scoring on their own.
    out = set()
    for part in _ASM_SYM_SPLIT.split(sym):
        if len(part) < 2:
            continue
        if re.fullmatch(r"(?:us|psp|beta|pspeu|hd|hi|lo)", part):
            continue
        if re.fullmatch(r"[0-9A-Fa-f]{4,}", part):
            continue
        out.add(part.lower())
    return out


def strip_overlay_prefix(name: str) -> str:
    return _OVL_PREFIX.sub("", name, count=1)


# ---------------------------------------------------------------------------
# C side


def c_functions() -> list[tuple[str, str, str]]:
    """(relative path, function name, body) for every function src/ defines.

    Headers included, deliberately. src/st deduplicates by putting the shared
    implementation in src/st/<name>.h, so a .c-only corpus is blind to the
    single largest source of copied bodies in this tree.
    """
    out = []
    pat = re.compile(
        r"^(?:static\s+)?[A-Za-z_][\w \*]*?\**\s*"
        r"(?:OVL_EXPORT\(\s*(\w+)\s*\)|([A-Za-z_]\w*))\s*\([^;{]*\)\s*\{",
        re.M,
    )
    for path in sorted(SRC_ROOT.rglob("*")):
        if path.suffix not in (".c", ".h") or "saturn" in path.parts:
            continue
        try:
            src = path.read_text(errors="ignore")
        except OSError:
            continue
        rel = str(path.relative_to(REPO)).replace("\\", "/")
        for m in pat.finditer(src):
            fname = m.group(1) or m.group(2)
            if fname in ("if", "for", "while", "switch", "return", "sizeof"):
                continue
            start = m.end() - 1
            depth, i = 0, start
            while i < len(src):
                if src[i] == "{":
                    depth += 1
                elif src[i] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            out.append((rel, fname, src[start : i + 1]))
    return out


def c_tokens(body: str) -> set[str]:
    body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
    body = re.sub(r"//[^\n]*", " ", body)
    return {t.lower() for t in _C_IDENT.findall(body) if len(t) > 1}


# ---------------------------------------------------------------------------


def build_idf(docs: list[set[str]]) -> dict[str, float]:
    df = Counter()
    for d in docs:
        df.update(d)
    n = max(1, len(docs))
    idf = {}
    for tok, count in df.items():
        if count / n > MAX_DOC_FREQ:
            continue
        idf[tok] = math.log(n / count)
    return idf


class TokenIndex:
    """Inverted index over the C corpus, keyed by informative tokens only.

    Scoring every stub against every C function directly is 1200 x 4000 set
    intersections and does not finish in a useful time. Only functions that
    share at least one informative token can score above zero, and the
    inverted index is exactly the set of those, so the comparison count drops
    by three orders of magnitude without changing a single score.
    """

    def __init__(self, docs: list[set[str]], idf: dict[str, float]):
        self.idf = idf
        self.postings: dict[str, list[int]] = defaultdict(list)
        self.weight: list[float] = []
        for i, doc in enumerate(docs):
            total = 0.0
            for tok in doc:
                w = idf.get(tok)
                if w is None:
                    continue
                total += w
                self.postings[tok].append(i)
            self.weight.append(total)

    def score(self, tokens: set[str]) -> list[tuple[float, int]]:
        inter: dict[int, float] = defaultdict(float)
        query_weight = 0.0
        for tok in tokens:
            w = self.idf.get(tok)
            if w is None:
                continue
            query_weight += w
            for i in self.postings.get(tok, ()):
                inter[i] += w
        if query_weight <= 0:
            return []
        out = []
        for i, hit in inter.items():
            union = query_weight + self.weight[i] - hit
            if union > 0:
                out.append((hit / union, i))
        return out


def include_asm_symbols() -> set[tuple[str, str]]:
    """(asm_dir, symbol) pairs still stubbed by an INCLUDE_ASM somewhere in src/.

    An .s file on disk does not mean the function is unmatched: the build leaves
    the extracted assembly in place after a function is written in C. The
    INCLUDE_ASM is the authority on what still needs work.

    PATH-AWARE, and it has to be. This returned bare symbol NAMES until
    2026-08-02, which made any .s file "live" as soon as some file anywhere
    stubbed a function of the same name. When a `c` segment is split, splat
    writes the moved functions into the new directory and leaves the old copies
    behind, so four functions existed under BOTH
    asm/us/st/rno0/nonmatchings/giantbro_helpers/ and .../unk_4A320/. Both
    copies looked live, both produced a record keyed on overlay/symbol, and
    --record died on its own uniqueness assertion. The twin corpus could not be
    regenerated at all, and it had been stale since commit c614af465.

    Pairing the directory with the symbol makes an orphaned copy exactly what it
    is: assembly no INCLUDE_ASM points at.

    THE WHOLE PATH, NOT THE LAST COMPONENT. Using only the final directory name
    was still ambiguous, because the PSP port reuses the same names:

        us   INCLUDE_ASM("boss/bo0/nonmatchings/3053C",            func_us_801B163C)
        psp  INCLUDE_ASM("boss/bo0_psp/nonmatchings/bo0_psp/2D26C", func_us_801B163C)

    Both ended in a component the us tree also has, so the PSP stub kept an
    ORPHANED us copy alive at asm/us/boss/bo0/nonmatchings/2D26C/. That copy
    was left behind on 2026-08-16 when the bo0 2D26C segment was split at
    0x3053C; splat writes the moved functions into the new directory and does
    not remove the old ones. Two live rows then shared the key
    boss/bo0/func_us_801B163C and --record died on its uniqueness assertion,
    exactly as it had on the previous segment split.

    This is the third time the _psp port has been read as us work (see
    matched_audit's 126 false LOST and readme_status' 775 -> 2734 stub count).
    Comparing the full relative directory removes the whole class here: a PSP
    path can never equal a us stub's directory.
    """
    out: set[tuple[str, str]] = set()
    pat = re.compile(r"INCLUDE_ASM\(\s*\"([^\"]*)\"\s*,\s*(\w+)\s*\)")
    for path in SRC_ROOT.rglob("*.c"):
        try:
            for asm_rel, sym in pat.findall(path.read_text(errors="ignore")):
                out.add((asm_rel.strip("/"), sym))
        except OSError:
            continue
    return out


def analyse(only: str = "") -> list[dict]:
    stubs = []
    for path in sorted(ASM_ROOT.rglob("*.s")):
        if "nonmatchings" not in str(path):
            continue
        stub = parse_stub(path)
        if stub and (not only or stub.name == only):
            stubs.append(stub)

    still = include_asm_symbols()
    for stub in stubs:
        # Match on (FULL asm-relative directory, symbol). Anything shorter is
        # ambiguous: the last component alone is shared between the us tree and
        # the _psp port, and a PSP INCLUDE_ASM then keeps a us orphan alive.
        # See include_asm_symbols() for the case that proved it.
        try:
            asm_dir = str(Path(stub.path).parent.relative_to(ASM_ROOT))
        except ValueError:                                   # pragma: no cover
            asm_dir = Path(stub.path).parent.name
        stub.still_asm = (asm_dir.replace("\\", "/"), stub.name) in still

    cfuncs = c_functions()
    cdocs = [c_tokens(body) for _, _, body in cfuncs]
    idf = build_idf(cdocs)
    index = TokenIndex(cdocs, idf)

    by_name: dict[str, list[int]] = defaultdict(list)
    for i, (_, fname, _) in enumerate(cfuncs):
        by_name[strip_overlay_prefix(fname).lower()].append(i)

    # Cross-overlay stubs that assemble to the same opcode sequence are the
    # same function twice, whether or not either has been written in C.
    shape: dict[tuple, list[Stub]] = defaultdict(list)
    for stub in stubs:
        shape[tuple(stub.opcodes)].append(stub)

    rows = []
    for stub in stubs:
        row = {
            "symbol": stub.name,
            "overlay": stub.overlay,
            "asm": str(stub.path.relative_to(REPO)).replace("\\", "/"),
            "instructions": len(stub.opcodes),
            "still_asm": stub.still_asm,
            "name_twins": [],
            "shape_twins": [],
            "token_twins": [],
        }

        key = strip_overlay_prefix(stub.name).lower()
        if not _ADDRESS_NAME.match(stub.name):
            seen_name: set[tuple[str, str]] = set()
            for i in by_name.get(key, []):
                rel, fname, _ = cfuncs[i]
                identity = (rel, fname)
                if identity in seen_name:
                    continue
                seen_name.add(identity)
                row["name_twins"].append({"file": rel, "function": fname})

        seen_shape: set[tuple[str, str]] = set()
        for other in shape[tuple(stub.opcodes)]:
            identity = (other.overlay, other.name)
            if identity == (stub.overlay, stub.name) or identity in seen_shape:
                continue
            seen_shape.add(identity)
            row["shape_twins"].append(
                {
                    "symbol": other.name,
                    "overlay": other.overlay,
                    "identical_constants": other.imms == stub.imms,
                }
            )

        if stub.tokens:
            scored = [p for p in index.score(stub.tokens) if p[0] >= MIN_TOKEN_SCORE]
            scored.sort(reverse=True)
            seen_token: set[tuple[str, str]] = set()
            for s, i in scored[:MAX_TOKEN_HITS]:
                rel, fname, _ = cfuncs[i]
                identity = (rel, fname)
                if identity in seen_token:
                    continue
                seen_token.add(identity)
                row["token_twins"].append(
                    {"file": rel, "function": fname, "score": round(s, 3)}
                )

        rows.append(row)
    return rows


# ---------------------------------------------------------------------------


# The four functions matched by hand on 2026-08-01, with the twin that was
# actually used. A tool built from four examples must be checked against those
# four examples or it is only a guess with a command line.
MUST_RECOVER = {
    "BO6_RicCheckFacing": "RicCheckFacing",
    "BO6_RicCreateEntFactoryFromEntity": "RicCreateEntFactoryFromEntity",
}

# The other two are a measured limit of the method, kept here rather than
# quietly dropped. Both carry an address-derived name, so there is nothing to
# match on but their referenced symbols, and both reference only
# PLAYER_posX_i_hi and PLAYER_posY_i_hi. Those three tokens sit above the
# document-frequency cut because hundreds of functions in this tree touch the
# player's position, so the query is empty by construction.
#
# Lowering the cut until these two pass would hand every short entity function
# in the tree a confident wrong twin. The correct output for a query with no
# distinguishing content is no output, so what is asserted is that these
# produce SILENCE, not a guess. Both were found by reading the assembly and
# recognising the idiom, which is the model's job, not the index's.
KNOWN_LIMIT = {
    "func_us_801B9A8C": "EntityIsNearPlayer",
    "func_us_801BB014": "EntityIsNearPlayer",
}



def _retired(sym: str) -> bool:
    """Has this symbol been matched, so it is no longer a stub to recover?

    analyse() only walks nonmatchings/. When a function is matched its assembly
    moves to matchings/, so it vanishes from `rows` and any fixture naming it
    reports "stub not parsed" -- which reads like a parser regression and is
    actually the project working as intended.

    That is a rotting fixture, the same failure mode the review-gate test hit on
    2026-08-02. A self-test whose cases expire as the work progresses will
    eventually be silenced rather than read, so it has to tell the two apart.
    """
    return any(ASM_ROOT.rglob(f"matchings/**/{sym}.s"))


def self_test() -> int:
    rows = {r["symbol"]: r for r in analyse()}
    failures = 0

    print(f"{'symbol':40} {'expected twin':32} verdict")
    print("-" * 92)
    for sym, expected in MUST_RECOVER.items():
        row = rows.get(sym)
        if row is None:
            if _retired(sym):
                print(f"{sym:40} {expected:32} n/a: matched, no longer a stub")
                continue
            print(f"{sym:40} {expected:32} FAIL: stub not parsed")
            failures += 1
            continue
        named = [t["function"] for t in row["name_twins"]]
        toked = [t["function"] for t in row["token_twins"]]
        if expected in named:
            print(f"{sym:40} {expected:32} ok via name")
        elif expected in toked:
            print(f"{sym:40} {expected:32} ok via tokens")
        else:
            print(f"{sym:40} {expected:32} FAIL: got {named + toked or '[]'}")
            failures += 1

    print()
    print("known limits (must stay silent rather than guess wrong)")
    print("-" * 92)
    for sym, expected in KNOWN_LIMIT.items():
        row = rows.get(sym)
        if row is None:
            if _retired(sym):
                print(f"{sym:40} {'(matched, no longer a stub)':32} n/a")
                continue
            print(f"{sym:40} {'':32} FAIL: stub not parsed")
            failures += 1
            continue
        found = [t["function"] for t in row["name_twins"] + row["token_twins"]]
        wrong = [f for f in found if f != expected]
        if not found:
            print(f"{sym:40} {'(silent, as expected)':32} ok")
        elif not wrong:
            print(f"{sym:40} {expected:32} ok, now recovered")
        else:
            print(f"{sym:40} {'':32} FAIL: wrong twin {wrong}")
            failures += 1

    print()
    print("candidate lists identify distinct twins exactly once")
    print("-" * 92)
    candidate_checks = 0
    for row in rows.values():
        identity = (row["overlay"], row["symbol"])
        shape_ids = [(t["overlay"], t["symbol"])
                     for t in row["shape_twins"]]
        if identity in shape_ids:
            print(f"{row['symbol']:40} {'':32} FAIL: self shape twin")
            failures += 1
        candidate_checks += 1
        if len(shape_ids) != len(set(shape_ids)):
            print(f"{row['symbol']:40} {'':32} FAIL: duplicate shape twin")
            failures += 1
        candidate_checks += 1
        for kind in ("name_twins", "token_twins"):
            candidate_ids = [(t["file"], t["function"])
                             for t in row[kind]]
            if len(candidate_ids) != len(set(candidate_ids)):
                print(f"{row['symbol']:40} {'':32} FAIL: duplicate {kind}")
                failures += 1
            candidate_checks += 1

    total = len(MUST_RECOVER) + len(KNOWN_LIMIT) + candidate_checks
    print()
    if failures:
        print(f"{failures} of {total} checks failed.")
    else:
        print(f"all {total} checks pass.")
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# auditing what is ALREADY matched
#
# Be precise about what this can and cannot show, because the obvious reading
# of "verify the matches against their twins" promises something the build
# already guarantees.
#
# `verify_build` hashes every one of the 81 overlays against the retail disc.
# A matched function therefore cannot contain a flattened constant, a dropped
# branch, or a wrong field: any of those change the bytes and the overlay
# fails. Looking for correctness defects among matched functions is looking
# for something 81/81 has already excluded.
#
# What the byte check is blind to is architecture and intent, and that is
# where a twin pass earns its keep:
#
#   SHIM_CANDIDATE   we wrote a private copy of a function that already
#                    exists in a shared header. Byte-correct, structurally
#                    wrong, and precisely the thing upstream objected to.
#
#   CONSTANT_DIVERGENT
#                    our copy and its twin have the same shape but different
#                    numbers. Both are correct, and the pair must NEVER be
#                    merged into one shared implementation. Recording the
#                    exact differing constants is what stops a later shim
#                    attempt from silently breaking one of them -- which is
#                    the failure mode the rno0/bo0 pair (0x11 vs 0x19) would
#                    have produced.
#
#   IDENTICAL        same shape, same numbers, twin lives in a sibling
#                    overlay .c. Expected; overlays duplicate by design.

_NUMBER = re.compile(r"\b(?:0[xX][0-9A-Fa-f]+|\d+)\b")


def _strip_comments(body: str) -> str:
    body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
    return re.sub(r"//[^\n]*", " ", body)


def body_numbers(body: str) -> list[int]:
    out = []
    for tok in _NUMBER.findall(_strip_comments(body)):
        try:
            out.append(int(tok, 0))
        except ValueError:
            pass
    return out


def body_shape(body: str) -> list[str]:
    """Token sequence with identifiers and numbers erased.

    Two bodies with the same shape do the same thing to different names and
    numbers, which is exactly the comparison that separates "copied and
    adapted" from "rewritten".
    """
    toks = re.findall(r"[A-Za-z_]\w*|0[xX][0-9A-Fa-f]+|\d+|[^\s\w]",
                      _strip_comments(body))
    out = []
    for t in toks:
        if re.fullmatch(r"[A-Za-z_]\w*", t):
            out.append("ID")
        elif re.fullmatch(r"0[xX][0-9A-Fa-f]+|\d+", t):
            out.append("NUM")
        else:
            out.append(t)
    return out


def _is_shared_impl(rel: str) -> bool:
    """Is this path a shared implementation rather than one overlay's copy?

    src/st/<name>.h is the convention: the implementation sits at the src/st
    level and each stage contributes a three-line shim. A header INSIDE an
    overlay directory (src/st/are/e_breakable.h) is that overlay's own file
    and is not shared.
    """
    if not rel.endswith(".h"):
        return False
    parts = rel.split("/")
    return len(parts) == 3 and parts[0] == "src" and parts[1] in ("st", "ric", "dra")


def _our_files() -> set[str]:
    import subprocess

    try:
        p = subprocess.run(
            ["git", "diff", "--name-only", "upstream/master..HEAD", "--", "src/"],
            cwd=str(REPO), capture_output=True, text=True, timeout=120,
        )
        if p.returncode == 0:
            return {l.strip() for l in p.stdout.splitlines() if l.strip()}
    except Exception:
        pass
    return set()


def audit_matched() -> list[dict]:
    """Cross-check every function written in C against its same-named twins.

    "Matched" here means "written in C and not stubbed by an INCLUDE_ASM",
    which is the only definition available from the files alone. An earlier
    version gated on a surviving nonmatchings/*.s, on the theory that the
    extracted assembly records a function's origin. It does not: extraction
    removes the .s once a function is written, so that gate saw only the two
    functions matched since the last extract and silently called it "all".
    """
    still = include_asm_symbols()
    extracted = {
        p.stem for p in ASM_ROOT.rglob("*.s") if "nonmatchings" in str(p)
    }

    cfuncs = [
        (rel, fname, body)
        for rel, fname, body in c_functions()
        if fname not in still
    ]

    groups: dict[str, list[int]] = defaultdict(list)
    for i, (_, fname, _) in enumerate(cfuncs):
        groups[strip_overlay_prefix(fname).lower()].append(i)

    ours = _our_files()
    cache: dict[int, tuple[list[int], list[str]]] = {}

    def analysed(i):
        if i not in cache:
            body = cfuncs[i][2]
            cache[i] = (body_numbers(body), body_shape(body))
        return cache[i]

    rows = []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        # Each unordered pair once. Reporting both directions doubles every
        # count and makes the totals meaningless.
        for a_i in range(len(members)):
            for b_i in range(a_i + 1, len(members)):
                i, j = members[a_i], members[b_i]
                rel, fname, _ = cfuncs[i]
                trel, tfname, _ = cfuncs[j]
                nums, shape = analysed(i)
                tnums, tshape = analysed(j)

                if shape != tshape:
                    verdict = "STRUCTURAL_DIVERGENT"
                elif nums != tnums:
                    verdict = "CONSTANT_DIVERGENT"
                elif _is_shared_impl(trel) or _is_shared_impl(rel):
                    verdict = "SHIM_CANDIDATE"
                else:
                    verdict = "IDENTICAL"

                rows.append(
                    {
                        "function": fname,
                        "file": rel,
                        "had_asm": fname in extracted,
                        "ours": rel in ours or trel in ours,
                        "twin_file": trel,
                        "twin_function": tfname,
                        "twin_is_shared_impl": _is_shared_impl(trel),
                        "verdict": verdict,
                        "our_constants": nums,
                        "twin_constants": tnums,
                        "differing_constants": (
                            sorted(set(nums) ^ set(tnums)) if nums != tnums else []
                        ),
                    }
                )
    return rows


def report_audit(rows: list[dict]) -> None:
    order = ["SHIM_CANDIDATE", "CONSTANT_DIVERGENT", "STRUCTURAL_DIVERGENT",
             "IDENTICAL"]
    by = defaultdict(list)
    for r in rows:
        by[r["verdict"]].append(r)

    funcs = {(r["file"], r["function"]) for r in rows}
    funcs |= {(r["twin_file"], r["twin_function"]) for r in rows}
    ourpairs = [r for r in rows if r["ours"]]
    print("=" * 78)
    print("AUDIT OF MATCHED FUNCTIONS AGAINST THEIR TWINS")
    print("=" * 78)
    print(f"{len(funcs)} matched functions participate in a twin relationship")
    print(f"{len(rows)} unordered pairs examined, "
          f"{len(ourpairs)} touching a file this fork changed")
    print()
    print("Scope note: all 81 overlays hash-match the retail disc, so none of")
    print("these can be functionally wrong. What follows is architecture and")
    print("intent, which the byte check cannot see.")
    print()
    for v in order:
        print(f"  {v:22} {len(by[v]):5}")

    if by["CONSTANT_DIVERGENT"]:
        print()
        print("CONSTANT_DIVERGENT -- same code, different numbers.")
        print("These pairs are both correct and must NOT be merged into a")
        print("shared implementation. This is the list to check before any")
        print("future shim attempt.")
        print("-" * 78)
        for r in sorted(by["CONSTANT_DIVERGENT"], key=lambda r: r["function"]):
            mark = "*" if r["ours"] else " "
            print(f" {mark}{r['file']}:{r['function']}")
            print(f"    vs {r['twin_file']}:{r['twin_function']}")
            print(f"    differing constants: {r['differing_constants']}")

    if by["SHIM_CANDIDATE"]:
        print()
        print("SHIM_CANDIDATE -- byte-identical to a SHARED implementation.")
        print("A private copy of code that already has a home. Byte-correct,")
        print("structurally wrong; this is upstream's objection, by name.")
        print("-" * 78)
        for r in sorted(by["SHIM_CANDIDATE"], key=lambda r: r["function"]):
            mark = "*" if r["ours"] else " "
            print(f" {mark}{r['file']}:{r['function']}  ->  {r['twin_file']}")
    print()
    print("* marks a file this fork changed relative to upstream/master.")


RECORD_PATH = REPO / "automation" / "twins.us.json"


def write_record() -> int:
    """Persist the twin map where a worker can read it for free.

    The obvious home for this is the work queue, one twin field per record.
    That is not available: the queue lives at $SOTN_QUEUE, which defaults to
    ~/sotn-work/queue.jsonl, so it resolves to a DIFFERENT file depending on
    whose HOME is running. Writing it from here would fork the harness state
    while appearing to succeed -- the same trap that made the sandbox report
    33 matched where the live queue had 134.

    A committed file in the repo is strictly better anyway. It is versioned,
    it regenerates from the tree rather than drifting from it, and a worker
    reads it with a dict lookup instead of spending model tokens rediscovering
    that BO6_RicStepStand is RicStepStand.
    """
    import subprocess

    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(REPO),
            capture_output=True, text=True, timeout=60,
        ).stdout.strip()
    except Exception:
        head = ""

    rows = [r for r in analyse() if r["still_asm"]]

    # Key on overlay AND symbol. A bare symbol is NOT unique: EntityBreakable
    # is stubbed in both st/rchi and st/rno0, and EntityUnkId1B in both
    # st/rcen and st/rno0. Keying on the symbol alone silently dropped one of
    # each pair and would have handed a worker the other overlay's twin --
    # a wrong answer delivered with the same confidence as a right one.
    twins = {
        f"{r['overlay']}/{r['symbol']}": {
            "symbol": r["symbol"],
            "overlay": r["overlay"],
            "instructions": r["instructions"],
            "name_twins": r["name_twins"],
            "shape_twins": r["shape_twins"],
            "token_twins": r["token_twins"],
        }
        for r in rows
        if r["name_twins"] or r["shape_twins"] or r["token_twins"]
    }
    assert len(twins) == sum(
        1 for r in rows
        if r["name_twins"] or r["shape_twins"] or r["token_twins"]
    ), "twin keys collided; the key is not unique"
    doc = {
        "generated_from": head,
        "version": "us",
        "unmatched_stubs": len(rows),
        "with_candidates": len(twins),
        "how_to_read": (
            "A twin is a starting point, not an answer. Diff it against the "
            "stub's assembly before copying: sibling overlays routinely differ "
            "by one constant or one branch, and copying past that difference "
            "produces a function that is wrong in a way the build will catch "
            "but a reviewer will not. A twin under src/st/<name>.h is a SHARED "
            "implementation, so the right answer there is usually a shim, not "
            "a copy -- check shim_viable() in codebase_index.py first."
        ),
        "regenerate": "python3 automation/asm_twin_finder.py --record",
        "twins": twins,
    }
    RECORD_PATH.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"wrote {RECORD_PATH.relative_to(REPO)}")
    print(f"  {len(rows)} unmatched stubs, {len(twins)} with a twin candidate")
    kinds = Counter()
    for v in twins.values():
        if v["name_twins"]:
            kinds["name"] += 1
        if v["shape_twins"]:
            kinds["shape"] += 1
        if v["token_twins"]:
            kinds["tokens"] += 1
    for k, n in sorted(kinds.items()):
        print(f"  {k:8} {n}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--json", default="")
    ap.add_argument("--symbol", default="", help="restrict to one stub")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--audit-matched", action="store_true")
    ap.add_argument(
        "--record",
        action="store_true",
        help="write automation/twins.us.json for workers to read",
    )
    ap.add_argument(
        "--all", action="store_true", help="include stubs already written in C"
    )
    ap.add_argument(
        "--diagnose-keys", action="store_true",
        help="list the overlay/symbol keys that collide, and where each "
             "duplicate came from. Use when --record aborts on its uniqueness "
             "assertion.",
    )
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    if a.audit_matched:
        rows = audit_matched()
        report_audit(rows)
        if a.json:
            Path(a.json).write_text(json.dumps(rows, indent=2))
            print(f"\nwrote {a.json}")
        return 0

    if a.diagnose_keys:
        # Why the record could not be written. write_record() asserts that
        # overlay/symbol is unique and, when it is not, the assertion says only
        # that something collided -- which is the least useful half of the
        # answer. This prints the colliding keys and the files each duplicate
        # came from, which is what you actually need to fix it.
        rows = [r for r in analyse() if r["still_asm"]]
        cand = [r for r in rows
                if r["name_twins"] or r["shape_twins"] or r["token_twins"]]
        seen: dict[str, list] = {}
        for r in cand:
            seen.setdefault(f"{r['overlay']}/{r['symbol']}", []).append(r)
        dupes = {k: v for k, v in seen.items() if len(v) > 1}
        print(f"{len(rows)} unmatched stubs, {len(cand)} with candidates, "
              f"{len(dupes)} colliding key(s)")
        for k, v in sorted(dupes.items()):
            print(f"\n  {k}  x{len(v)}")
            for r in v:
                bits = {kk: r.get(kk) for kk in
                        ("src", "src_rel", "file", "asm", "asm_rel",
                         "instructions") if r.get(kk) is not None}
                print(f"     {bits}")
        return 1 if dupes else 0

    if a.record:
        return write_record()

    rows = analyse(a.symbol)
    if not a.all:
        rows = [r for r in rows if r["still_asm"]]

    with_evidence = [
        r for r in rows if r["name_twins"] or r["shape_twins"] or r["token_twins"]
    ]
    print(f"{len(rows)} unmatched stubs, {len(with_evidence)} with a twin candidate")
    print("A twin is a starting point. Diff it against the assembly before")
    print("copying: siblings routinely differ by one constant or one branch.")
    print("=" * 78)

    by_overlay = defaultdict(list)
    for r in with_evidence:
        by_overlay[r["overlay"]].append(r)

    for overlay in sorted(by_overlay):
        print(f"\n{overlay}  ({len(by_overlay[overlay])})")
        print("-" * 78)
        for r in sorted(by_overlay[overlay], key=lambda r: -r["instructions"]):
            print(f"  {r['symbol']}  ({r['instructions']} instructions)")
            for t in r["name_twins"]:
                print(f"      name    {t['file']}:{t['function']}")
            for t in r["shape_twins"]:
                same = "same constants" if t["identical_constants"] else "DIFFERENT constants"
                print(f"      shape   {t['overlay']}:{t['symbol']}  ({same})")
            for t in r["token_twins"]:
                print(f"      tokens  {t['score']:.3f}  {t['file']}:{t['function']}")

    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=2))
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
