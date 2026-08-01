#!/usr/bin/env python3
"""Where did each of our functions actually come from?

WHY THIS EXISTS
    Upstream's review of this fork said: "almost every function you have
    decompiled here is just copies of functions we already have."

    `quality_audit.py` answers a narrower question than that charge. Its
    duplicate check is EXACT equality on the normalised body, so it finds
    verbatim copies and nothing else. A function that was copied and then had
    a variable renamed, a constant changed, or a call site adapted reads as
    original work to it. That is precisely the shape most copying takes here,
    because a body lifted from a shared header usually needs one or two
    adjustments to compile in the destination overlay.

    This grades every function we define by its best fuzzy match against
    UPSTREAM's tree, so the answer is a distribution rather than a yes/no:

      verbatim  >= 0.95   the body is upstream's, modulo whitespace/comments
      adapted   >= 0.80   upstream's structure with local edits
      derived   >= 0.55   recognisably modelled on an upstream function
      original  <  0.55   no close upstream relative

    None of these are automatically defects. Reusing a shared implementation is
    correct when the alternative is a private copy, and `shim_viable` in
    codebase_index.py decides that separately. What matters is knowing which is
    which, and not describing a copy as a decompilation.

STRICTLY READ-ONLY. Never edits sources, never builds.

Usage:
    python3 automation/provenance_check.py
    python3 automation/provenance_check.py --json out.json
    python3 automation/provenance_check.py --threshold 0.8
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
UPSTREAM = "upstream/master"

VERBATIM, ADAPTED, DERIVED = 0.95, 0.80, 0.55

# A similarity score is only meaningful once a body has enough shape to be
# distinctive. Erasing identifiers and numbers is what lets the metric see
# through a rename, and it is also what makes every "load a pointer, store
# three fields" setter look like every other one.
#
# Measured, not guessed. A manual pass over the flagged functions found THREE
# misattributions of exactly this kind, all scoring 1.000:
#   BO6_RicSetAnimation  -> dop_anim.h:func_8010DA2C   (real twin: ric/pl_utils.c)
#   SetSubStep           -> dop_anim.h:func_8010DA2C   (real twin: st/st_common.h)
#   func_us_801B9C14     -> bo4:EnableAfterImage       (2 statements vs our 4)
# The first two matching the SAME upstream function was the tell. Once control
# flow enters, shape alone can no longer be satisfied by unrelated code, and
# RicEntitySubwpnCross's 0.809 held up under line-by-line review.
# Flatness alone is the WRONG test, and trying it proved that: it suppressed
# UpdateClockHands, a confirmed real copy verified instruction-by-instruction
# against two overlays' ground truth. The problem was never that a body is
# short. It is that a short body can match MANY upstream functions equally
# well, and picking one of them to name is arbitrary.
#
# So gate on ambiguity instead. If several unrelated upstream functions tie at
# the top score, the shape is generic and no attribution is honest. If exactly
# one function stands at the top, the attribution means something however short
# the body is. That keeps UpdateClockHands (a unique twin in st/no0) and drops
# the three-field setters (dozens of equals across the tree).
MAX_TIES = 3            # distinct upstream functions allowed at the top score

# Shingles are a SET, and repeated statements collapse in a set. `a=0; b=0;
# c=0; d=0;` and `a=0; b=0;` erase to the SAME shingles, so Jaccard reports
# 1.000 for bodies of visibly different length. That is how func_us_801B9C14
# (four field-zeroings) scored a perfect match against bo4's EnableAfterImage
# (two). Set similarity cannot see multiplicity, so carry length separately:
# two bodies of materially different size are not the same body whatever their
# shingles say.
LEN_RATIO = 0.75        # shorter/longer normalised token count, minimum


def _token_len(body: str) -> int:
    return len(re.findall(r"[A-Za-z_]\w*|0x[0-9A-Fa-f]+|\d+|[^\s\w]",
                          _normalise(body)))


def _git(*args: str, timeout: int = 300) -> str:
    try:
        p = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True,
                           text=True, errors="replace", timeout=timeout)
        return p.stdout if p.returncode == 0 else ""
    except (subprocess.SubprocessError, OSError):
        return ""


def _normalise(body: str) -> str:
    """Strip what a copier would not bother to change."""
    body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
    body = re.sub(r"//[^\n]*", " ", body)
    return re.sub(r"\s+", " ", body).strip()


def _shingles(body: str, k: int = 5) -> set[str]:
    """Token k-grams with identifiers and numbers erased.

    Erasing them is the point. A copy that renames `arg0` to `heartIdx` or
    swaps one constant for another still produces the same shingles, which is
    exactly the case exact-match duplicate detection misses.
    """
    toks = re.findall(r"[A-Za-z_]\w*|0x[0-9A-Fa-f]+|\d+|[^\s\w]", _normalise(body))
    norm = []
    for t in toks:
        if re.match(r"^[A-Za-z_]\w*$", t):
            norm.append("ID")
        elif re.match(r"^(0x[0-9A-Fa-f]+|\d+)$", t):
            norm.append("NUM")
        else:
            norm.append(t)
    return {"".join(norm[i:i + k]) for i in range(max(0, len(norm) - k + 1))}


def _functions(src: str) -> list[tuple[str, str]]:
    out = []
    for m in re.finditer(
            r"^(?:static\s+)?[A-Za-z_][\w \*]*?\**\s*"
            r"(?:OVL_EXPORT\(\s*(\w+)\s*\)|([A-Za-z_]\w*))\s*\([^;{]*\)\s*\{",
            src, re.M):
        name = m.group(1) or m.group(2)
        if name in ("if", "for", "while", "switch", "return", "sizeof"):
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
        out.append((name, src[start:i + 1]))
    return out


def upstream_corpus() -> dict[str, tuple[str, set[str], int]]:
    """Every function upstream defines: key -> (where, shingles).

    Headers included. src/st deduplicates by putting the shared implementation
    in src/st/<name>.h, so a .c-only corpus is blind to the single largest
    source of copied bodies in this tree.
    """
    files = [f for f in _git("ls-tree", "-r", "--name-only", UPSTREAM).splitlines()
             if f.startswith("src/") and f.endswith((".c", ".h"))
             and "saturn" not in f]
    corpus: dict[str, tuple[str, set[str], int]] = {}
    CH = 400
    for i in range(0, len(files), CH):
        batch = files[i:i + CH]
        p = subprocess.run(["git", "cat-file", "--batch"], cwd=str(REPO),
                           input=("\n".join(f"{UPSTREAM}:{f}" for f in batch)
                                  + "\n").encode(),
                           capture_output=True, timeout=600)
        buf, pos = p.stdout, 0
        for f in batch:
            nl = buf.find(b"\n", pos)
            if nl < 0:
                break
            hdr = buf[pos:nl].decode("utf-8", "replace").split()
            pos = nl + 1
            if len(hdr) < 3:
                continue
            size = int(hdr[2])
            text = buf[pos:pos + size].decode("utf-8", "replace")
            pos += size + 1
            for name, body in _functions(text):
                sh = _shingles(body)
                if len(sh) >= 8:              # ignore trivial one-liners
                    corpus[f"{f}:{name}"] = (f, sh, _token_len(body))
    return corpus


def our_functions() -> list[tuple[str, str, str]]:
    """Functions WE authored, not every function in a file we touched.

    Grading a whole changed file overstates the copying badly: our 22 files
    contain plenty of functions upstream already had, and those scored 1.000
    against themselves. Anything whose normalised body is identical to the
    same-named function at the same path upstream is upstream's work and is
    excluded here.
    """
    out = []
    for rel in _git("diff", "--name-only", f"{UPSTREAM}..HEAD", "--", "src/").split():
        p = REPO / rel
        if not rel.endswith(".c") or not p.exists():
            continue
        try:
            src = p.read_text(errors="ignore")
        except OSError:
            continue
        theirs = {n: _normalise(b)
                  for n, b in _functions(_git("show", f"{UPSTREAM}:{rel}"))}
        for name, body in _functions(src):
            if theirs.get(name) == _normalise(body):
                continue            # unchanged from upstream; not ours to grade
            out.append((rel, name, body))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", default="")
    ap.add_argument("--threshold", type=float, default=DERIVED)
    a = ap.parse_args()

    print(f"building upstream corpus from {UPSTREAM} ...", file=sys.stderr)
    corpus = upstream_corpus()
    ours = our_functions()
    print(f"  {len(corpus)} upstream functions, {len(ours)} of ours",
          file=sys.stderr)

    rows = []
    for rel, name, body in ours:
        sh = _shingles(body)
        if len(sh) < 8:
            rows.append({"file": rel, "function": name, "score": None,
                         "grade": "trivial", "match": ""})
            continue

        best, score, ties = "", 0.0, 0
        selfkey = f"{rel}:{name}"
        ourlen = _token_len(body)
        scored: list[tuple[float, str]] = []
        for key, (_, osh, olen) in corpus.items():
            if key == selfkey:
                continue            # a function cannot be a copy of itself
            inter = len(sh & osh)
            if not inter:
                continue
            j = inter / len(sh | osh)
            # Penalise by length agreement, so a set-similarity tie between
            # bodies of different size cannot masquerade as verbatim.
            if ourlen and olen:
                j *= min(ourlen, olen) / max(ourlen, olen)
            scored.append((j, key))
            if j > score:
                best, score = key, j
        # How many DISTINCT upstream functions sit at that same top score?
        ties = len({k.rsplit(":", 1)[-1] for j, k in scored
                    if score - j < 1e-9})
        if score > 0 and ties > MAX_TIES:
            rows.append({"file": rel, "function": name, "score": round(score, 3),
                         "grade": "unattributable", "match": "",
                         "note": f"{ties} distinct upstream functions tie at "
                                 f"{score:.3f}; the shape is generic, so naming "
                                 f"one source would be arbitrary"})
            continue
        grade = ("verbatim" if score >= VERBATIM else
                 "adapted" if score >= ADAPTED else
                 "derived" if score >= DERIVED else "original")
        rows.append({"file": rel, "function": name, "score": round(score, 3),
                     "grade": grade, "match": best})

    order = ["verbatim", "adapted", "derived", "original",
             "unattributable", "trivial"]
    by = defaultdict(list)
    for r in rows:
        by[r["grade"]].append(r)

    print(f"\n{'='*74}\nPROVENANCE OF {len(rows)} FUNCTIONS WE DEFINE\n{'='*74}")
    for g in order:
        n = len(by[g])
        if n:
            print(f"  {g:9} {n:4}   {100.0*n/len(rows):5.1f}%")

    for g in ("verbatim", "adapted"):
        if not by[g]:
            continue
        print(f"\n{g.upper()} (score >= {VERBATIM if g=='verbatim' else ADAPTED})")
        print("-" * 74)
        for r in sorted(by[g], key=lambda r: -(r["score"] or 0)):
            print(f"  {r['score']:.3f}  {r['file']}:{r['function']}")
            print(f"         <- {r['match']}")

    if by["original"]:
        print(f"\nORIGINAL (no upstream relative above {DERIVED})")
        print("-" * 74)
        for r in sorted(by["original"], key=lambda r: -(r["score"] or 0)):
            print(f"  {r['score']:.3f}  {r['file']}:{r['function']}")

    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=2))
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
