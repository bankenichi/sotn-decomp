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


def include_asm_symbols() -> set[str]:
    """Symbols still stubbed by an INCLUDE_ASM somewhere in src/.

    An .s file on disk does not mean the function is unmatched: the build
    leaves the extracted assembly in place after a function is written in C.
    The INCLUDE_ASM is the authority on what still needs work.
    """
    out = set()
    pat = re.compile(r"INCLUDE_ASM\(\s*\"[^\"]*\"\s*,\s*(\w+)\s*\)")
    for path in SRC_ROOT.rglob("*.c"):
        try:
            out.update(pat.findall(path.read_text(errors="ignore")))
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
        stub.still_asm = stub.name in still

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
            for i in by_name.get(key, []):
                rel, fname, _ = cfuncs[i]
                row["name_twins"].append({"file": rel, "function": fname})

        for other in shape[tuple(stub.opcodes)]:
            if other is stub:
                continue
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
            for s, i in scored[:MAX_TOKEN_HITS]:
                rel, fname, _ = cfuncs[i]
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


def self_test() -> int:
    rows = {r["symbol"]: r for r in analyse()}
    failures = 0

    print(f"{'symbol':40} {'expected twin':32} verdict")
    print("-" * 92)
    for sym, expected in MUST_RECOVER.items():
        row = rows.get(sym)
        if row is None:
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

    total = len(MUST_RECOVER) + len(KNOWN_LIMIT)
    print()
    if failures:
        print(f"{failures} of {total} checks failed.")
    else:
        print(f"all {total} checks pass.")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--json", default="")
    ap.add_argument("--symbol", default="", help="restrict to one stub")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument(
        "--all", action="store_true", help="include stubs already written in C"
    )
    a = ap.parse_args()

    if a.self_test:
        return self_test()

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
