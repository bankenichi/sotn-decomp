#!/usr/bin/env python3
"""Tier 2: read the escalated pool, classify it, and resolve what is mechanical.

WHY THIS EXISTS (ROADMAP P6 item 2)
    `escalated` had no automated consumer. Records accumulated until someone
    picked them up by hand, and "someone picks it up" is how a record sits for a
    week carrying a note about a failure that was never its fault.

    The pool is not homogeneous. Measured over the live queue, escalations fall
    into four classes with four completely different correct actions, and only
    ONE of them is "a human should read the assembly":

      symbol    the model invented an identifier. `RIC_step' undeclared,
                `structure has no member named unk24'. MECHANICAL: the real name
                exists, and the fix is a rename, not a rewrite. This tool
                resolves the invented name against the actual declarations and
                emits the mapping.
      nocode    the model produced nothing. "attempt 4 timed out", "failed:
                RuntimeError". Says nothing about the function. Requeue.
      harness   the harness could not do its job. "INCLUDE_ASM stub not found"
                was six bo6 stubs that clang-format had wrapped onto two lines,
                invisible to a line-by-line scan. Fix the harness, requeue.
      real      a genuine decompilation problem. Needs a human or a strong model.

    Only `real` deserves expensive attention. Everything else is either free or
    a harness defect, and spending model quota on it is the waste the tiering
    was built to prevent.

WHAT IT DOES NOT DO
    It does not edit sources, does not build, and does not mutate the queue.
    It reads and reports. Applying a rename is a build-gated action and the
    fleet usually holds that lock; this runs safely alongside it.

Usage:
    python3 automation/escalation_triage.py
    python3 automation/escalation_triage.py --json out.json
    python3 automation/escalation_triage.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(os.environ.get("SOTN_REPO", Path(__file__).resolve().parents[1]))
PYTHON = os.environ.get("SOTN_PYTHON", sys.executable)

# ---------------------------------------------------------------------------
# classification
#
# Ordered, and the order is load-bearing: a note can carry more than one
# signal, and the FIRST match should be the one that decides what to do. A
# record whose build failed because a stub was not found is a harness problem
# even though the note also contains "BUILD FAILED".

_CLASSES = [
    ("harness", re.compile(
        r"INCLUDE_ASM stub not found|BUILD DIRTY|stub not parsed", re.I)),
    ("nocode", re.compile(
        r"timed out|failed: \w*Error|produced no candidate|generation errors",
        re.I)),
    ("symbol", re.compile(
        r"undeclared|has no member named|parse error before", re.I)),
    # "byte mismatch" and "bytes differ" are the same condition written two
    # ways by two different call sites; matching only one of them classified a
    # real near as `unknown`.
    ("real", re.compile(
        r"BUILD FAILED|checksum|bytes? (?:differ|mismatch)|permuter candidate",
        re.I)),
]

# GCC 2.7 diagnostics. No `error:` keyword, which is why an error:-only grep
# found nothing here for a long time.
_UNDECLARED = re.compile(r"`([A-Za-z_]\w*)' undeclared")
_NO_MEMBER = re.compile(
    r"(?:structure|union) has no member named `([A-Za-z_]\w*)'")
_PARSE_ERR = re.compile(r"parse error before `([A-Za-z_]\w*)'")


def is_c89_declaration_error(note: str) -> bool:
    """Is this the C89 declaration-after-statement error, wearing a disguise?

    GCC 2.7 is C89: every declaration must precede every statement in a block.
    When a model emits `s16 distX = ...;` after a statement, GCC does NOT say
    "declarations must come first". It says:

        parse error before `distX'
        `distX' undeclared (first use this function)

    which reads exactly like a wrong field name, and gets triaged as one. The
    tell is that the SAME identifier appears in both messages and is declared
    nowhere in the tree -- a real-but-misnamed symbol would exist somewhere.

    This matters because the two fixes are unrelated. A field-name problem needs
    the assembly read; this needs the declarations moved to the top of the
    block, which is mechanical and needs no analysis at all.
    """
    parsed = set(_PARSE_ERR.findall(note or ""))
    if not parsed:
        return False
    undecl = set(_UNDECLARED.findall(note or ""))
    # The identifier that broke the parse is also reported undeclared, or the
    # declaration it belonged to is: either way the block is mixing the two.
    if not (parsed & undecl) and not undecl:
        return False
    return all(declared_at(n) is None for n in parsed)


def classify(note: str) -> str:
    for name, rx in _CLASSES:
        if rx.search(note or ""):
            return name
    return "unknown"


def bad_identifiers(note: str) -> list[str]:
    """Every identifier the compiler rejected, deduplicated, in order."""
    out, seen = [], set()
    for rx in (_UNDECLARED, _NO_MEMBER, _PARSE_ERR):
        for m in rx.finditer(note or ""):
            s = m.group(1)
            if s not in seen:
                seen.add(s)
                out.append(s)
    return out


# ---------------------------------------------------------------------------
# resolution
#
# The dominant failure is an invented FLAT name for something that is really a
# struct path: RIC_posX_i_hi for RIC.posX.i.hi, RIC_step for RIC.step. That is
# exactly the mistake ROADMAP P2b warns about ("resolve every global BY ADDRESS,
# not by name affinity"), and it is mechanical to undo.

def _split_flat(name: str) -> list[str]:
    return [p for p in name.split("_") if p]


def suggest_struct_path(name: str, known: set[str]) -> str | None:
    """Turn a flat invented name back into a dotted path, if one exists.

    RIC_posX_i_hi -> RIC.posX.i.hi, but ONLY when the leading component is a
    real object. Without that guard this happily "corrects" any identifier
    containing an underscore, which would be worse than saying nothing.
    """
    parts = _split_flat(name)
    if len(parts) < 2:
        return None
    if parts[0] not in known:
        return None
    return parts[0] + "." + ".".join(parts[1:])


def known_objects() -> set[str]:
    """Globals the tree actually declares, from the C sources and headers.

    Deliberately broad and cheap: this only has to answer "is the first
    component of this flat name a real object", so a name-level index is
    enough and no parsing of types is needed.
    """
    out: set[str] = set()
    rx = re.compile(r"\bextern\s+[A-Za-z_][\w \*]*?\b([A-Za-z_]\w*)\s*(?:\[|;)")
    for p in list((REPO / "include").rglob("*.h")) + \
            list((REPO / "src").rglob("*.h")):
        try:
            out.update(rx.findall(p.read_text(errors="ignore")))
        except OSError:
            continue
    # The two the boss overlays actually use, which are #defines rather than
    # externs and so are invisible to the pattern above.
    out.update({"RIC", "PLAYER", "g_Ric", "g_Player", "g_CurrentEntity"})
    return out


_DECL_INDEX: dict[str, str] | None = None


def _build_decl_index() -> dict[str, str]:
    """symbol -> "path:line" for every file-scope declaration in the tree.

    Built ONCE and cached. The first version re-scanned src/ and include/ for
    each identifier, which is O(tree x names) over a slow mount and did not
    finish inside a 45s call. One pass with one regex is the same answer.

    Matches `extern <type> name;` and file-scope `<type> name =`, anchored at
    column 0 so a local variable inside a function body cannot register as a
    declaration.
    """
    idx: dict[str, str] = {}
    rx = re.compile(
        r"^(?:extern\s+)?[A-Za-z_][\w\s\*]*?\b([A-Za-z_]\w*)\s*"
        r"(?:\[[^\]]*\])?\s*(?:=[^=]|;)", re.M)
    for root in ("include", "src"):
        base = REPO / root
        if not base.is_dir():
            continue
        for p in base.rglob("*.[ch]"):
            low = str(p).lower()
            if "_psp" in low or "saturn" in low or "/psp/" in low:
                continue
            try:
                text = p.read_text(errors="ignore")
            except OSError:
                continue
            rel = p.relative_to(REPO).as_posix()
            for m in rx.finditer(text):
                name = m.group(1)
                if name not in idx:
                    idx[name] = f"{rel}:{text.count(chr(10), 0, m.start()) + 1}"
    return idx


def declared_at(name: str) -> str | None:
    """Where the tree already declares this symbol, if anywhere.

    THE question to ask before proposing any rename: is the identifier the
    compiler rejected actually REAL somewhere else? If it is, the record failed
    for want of a declaration in one file, and renaming would silently change
    what the function does.

    This check was missing from the first version and it produced a confidently
    wrong answer on the very first real record. BO6_CheckHighJumpInput failed on
    `RIC_step' undeclared, and both this tool and a subagent proposed rewriting
    it to RIC.step. But `extern u16 RIC_step;' is declared at
    src/boss/bo6/us_39144.c:15. The symbol is real; it is simply not declared in
    richter.c where the new function lives. The fix is one extern line.
    """
    global _DECL_INDEX
    if _DECL_INDEX is None:
        _DECL_INDEX = _build_decl_index()
    return _DECL_INDEX.get(name)


def struct_members(limit_files: int = 400) -> dict[str, set[str]]:
    """member name -> the struct/union tags that declare it.

    Used to answer the other half: when the model says `unk24' does not exist,
    what DOES exist near there. Reported as evidence, never auto-applied.
    """
    out: dict[str, set[str]] = defaultdict(set)
    tag_rx = re.compile(
        r"\b(?:struct|union)\s+(\w+)?\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}",
        re.S)
    mem_rx = re.compile(r"\b([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*;")
    n = 0
    for p in list((REPO / "include").rglob("*.h")):
        if n >= limit_files:
            break
        n += 1
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        for m in tag_rx.finditer(text):
            tag = m.group(1) or "(anonymous)"
            for mem in mem_rx.findall(m.group(2)):
                out[mem].add(tag)
    return out


# ---------------------------------------------------------------------------
# queue access

def queue_is_snapshot() -> str | None:
    """Is the queue this environment sees a read-only migrated snapshot?

    scheduler.py copies the legacy in-repo queue into ~/sotn-work the first time
    any environment touches it, and stamps the copy. Mutations are refused, but
    READS are allowed, so a stale snapshot answers questions silently and
    plausibly. This tool asked the snapshot for the escalated pool and got 3
    records when the live queue had 16 -- a wrong answer with no error.

    Returns the stamp text when the queue is a snapshot, else None.
    """
    q = Path(os.path.expanduser(
        os.environ.get("SOTN_QUEUE", "~/sotn-work/queue.jsonl")))
    stamp = q.with_suffix(".jsonl.from-legacy")
    try:
        return stamp.read_text().strip() if stamp.exists() else None
    except OSError:
        return None


def read_escalated() -> list[dict]:
    """Escalated records, via the scheduler so the live queue path is honoured.

    Never reads a queue file directly: SOTN_QUEUE resolves per environment and
    a direct read is how a stale snapshot gets mistaken for the real thing.
    """
    r = subprocess.run(
        [PYTHON, str(REPO / "automation" / "scheduler.py"),
         "list", "--status", "escalated"],
        capture_output=True, text=True, timeout=120, cwd=str(REPO))
    out = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line.startswith("escalated"):
            continue
        rest = line.split(None, 2)
        if len(rest) < 3:
            continue
        tail = rest[2]
        rid, _, note = tail.partition("|")
        out.append({"id": rid.strip(), "note": note.strip()})
    return out


def triage(records: list[dict]) -> list[dict]:
    known = known_objects()
    members = struct_members()
    rows = []
    for rec in records:
        note = rec["note"]
        cls = classify(note)
        bad = bad_identifiers(note)
        if cls == "symbol" and is_c89_declaration_error(note):
            cls = "c89"
        fixes, unknowns = [], []
        for b in bad:
            # FIRST: does the name already exist somewhere in the tree?
            #
            # This check has to come before any rewrite suggestion, and leaving
            # it out produced a confidently wrong answer on the very first real
            # record. BO6_CheckHighJumpInput failed on `RIC_step' undeclared,
            # and both this tool and a subagent proposed rewriting it to
            # RIC.step. But `extern u16 RIC_step;' is declared at
            # src/boss/bo6/us_39144.c:15 -- the symbol is real, it is simply not
            # declared in richter.c where the new function lives.
            #
            # The correct fix is one extern line. Rewriting to a struct path
            # would have compiled and produced DIFFERENT CODE, which is the
            # failure this whole pipeline exists to avoid: plausible beats
            # verified right up until the bytes disagree.
            where = declared_at(b)
            if where:
                fixes.append({
                    "invented": b,
                    "likely": f"already declared at {where}; add that "
                              f"declaration to this file",
                    "why": "symbol EXISTS elsewhere, so this is a missing "
                           "declaration, not a wrong name"})
                continue
            path = suggest_struct_path(b, known)
            if path:
                fixes.append({"invented": b, "likely": path,
                              "why": "flat name whose head is a real object, "
                                     "and no declaration of it exists anywhere "
                                     "(UNVERIFIED: confirm against the asm)"})
            elif b in members:
                fixes.append({"invented": b,
                              "likely": f"member of {sorted(members[b])[:3]}",
                              "why": "name exists, but not on the struct used"})
            else:
                unknowns.append(b)
        rows.append({
            "id": rec["id"], "class": cls, "bad_identifiers": bad,
            "resolvable": fixes, "unresolved": unknowns,
            "action": {
                "harness": "fix the harness, then requeue as todo",
                "nocode": "requeue as todo; the note says nothing about the code",
                "symbol": ("requeue with the mapping below as feedback"
                           if fixes else "needs a human: names not resolvable"),
                "c89": ("move every declaration to the top of its block; "
                        "GCC 2.7 is C89 and this is NOT a wrong field name"),
                "real": "needs a strong model or a human",
            }.get(cls, "read it"),
        })
    return rows


# ---------------------------------------------------------------------------

def self_test() -> int:
    fails = []

    def ck(c, l):
        print(("  ok   " if c else "  FAIL ") + l)
        if not c:
            fails.append(l)

    print("\nclassification, against real notes from the live queue")
    cases = [
        ("INCLUDE_ASM stub not found", "harness"),
        ("BUILD DIRTY: the build failed but no diagnostic names foo", "harness"),
        ("attempt 4 timed out", "nocode"),
        ("attempt 4 failed: RuntimeError", "nocode"),
        ("requeued: false escalation, model produced no candidate", "nocode"),
        ("BUILD FAILED: src/boss/bo6/richter.c:25: `RIC_step' undeclared",
         "symbol"),
        ("BUILD FAILED: 2D26C.c:68: structure has no member named `state'",
         "symbol"),
        ("BUILD FAILED: us_3E79C.c:1070: parse error before `randomIndex'",
         "symbol"),
        ("compiled, byte mismatch; permuter candidate", "real"),
        ("", "unknown"),
    ]
    for note, want in cases:
        got = classify(note)
        ck(got == want, f"{want:8} <- {note[:52]!r} (got {got})")

    print("\nharness beats BUILD FAILED when a note carries both")
    ck(classify("BUILD FAILED ... INCLUDE_ASM stub not found") == "harness",
       "a stub-not-found inside a BUILD FAILED note is still a harness problem")

    print("\nidentifier extraction")
    note = ("src/boss/bo0/2D26C.c:68: structure has no member named `state' "
            "src/boss/bo0/2D26C.c:78: structure has no member named `unk24' "
            "src/boss/bo6/richter.c:25: `RIC_step' undeclared "
            "us_3E79C.c:1070: parse error before `randomIndex'")
    got = bad_identifiers(note)
    ck("state" in got and "unk24" in got, "no-member names extracted")
    ck("RIC_step" in got, "undeclared names extracted")
    ck("randomIndex" in got, "parse-error names extracted")
    ck(got.count("unk24") == 1, "duplicates collapsed (GCC repeats them)")

    print("\nan existing symbol is a MISSING DECLARATION, never a rename")
    # The check that was missing, and the record that proved it.
    ck(declared_at("RIC_step") is not None,
       "RIC_step is declared somewhere in the tree (it is real)")
    ck(declared_at("totally_made_up_identifier_xyz") is None,
       "an invented name is declared nowhere")

    print("\nC89 declaration-after-statement is not a field-name problem")
    c89 = ("BUILD FAILED: us_3E79C.c:1070: parse error before `swapTarget' "
           "us_3E79C.c:1074: `swapTarget' undeclared (first use this function)")
    ck(is_c89_declaration_error(c89),
       "parse-error + undeclared on an unknown name is the C89 error")
    ck(classify(c89) == "symbol",
       "  classify() alone still calls it symbol (triage promotes it)")
    notc89 = "BUILD FAILED: richter.c:25: `RIC_step' undeclared"
    ck(not is_c89_declaration_error(notc89),
       "a real-but-undeclared symbol is NOT the C89 error")
    ck(not is_c89_declaration_error("attempt 4 timed out"),
       "a note with no parse error is not the C89 error")

    print("\nflat-name resolution, and its guard")
    known = {"RIC", "PLAYER"}
    ck(suggest_struct_path("RIC_posX_i_hi", known) == "RIC.posX.i.hi",
       "RIC_posX_i_hi -> RIC.posX.i.hi")
    ck(suggest_struct_path("RIC_step", known) == "RIC.step",
       "RIC_step -> RIC.step")
    ck(suggest_struct_path("some_random_local", known) is None,
       "an unknown head is NOT rewritten (the guard that stops noise)")
    ck(suggest_struct_path("RIC", known) is None,
       "a bare name with no underscore yields nothing")

    print()
    if fails:
        print(f"{len(fails)} FAILED")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", default="")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--notes-file", default="",
                    help="classify notes captured elsewhere, one 'id | note' "
                         "per line. Use when the live queue is only reachable "
                         "from another environment (see queue_is_snapshot).")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    if a.notes_file:
        recs = []
        for line in Path(a.notes_file).read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            rid, _, note = line.partition("|")
            recs.append({"id": rid.strip(), "note": note.strip()})
        print(f"classifying {len(recs)} record(s) from {a.notes_file}\n")
    else:
        stamp = queue_is_snapshot()
        if stamp:
            print("REFUSING: the queue this environment sees is a READ-ONLY "
                  "SNAPSHOT, not the live queue.", file=sys.stderr)
            print(f"  {stamp}", file=sys.stderr)
            print("Triaging it would report on records nobody is working. Run "
                  "this where the live queue is, or pass --notes-file with "
                  "output captured from there.", file=sys.stderr)
            return 2
        recs = read_escalated()
    rows = triage(recs)
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=2))
        print(f"wrote {a.json}")

    counts = Counter(r["class"] for r in rows)
    print(f"{len(rows)} escalated record(s)\n")
    for cls in ("harness", "nocode", "c89", "symbol", "real", "unknown"):
        if counts.get(cls):
            print(f"  {cls:8} {counts[cls]:3d}")
    print()
    free = (counts.get("harness", 0) + counts.get("nocode", 0)
            + counts.get("c89", 0))
    print(f"{free} of {len(rows)} are NOT decompilation problems and can be "
          f"requeued without spending a single model call.\n")
    print("=" * 78)
    for r in sorted(rows, key=lambda x: x["class"]):
        print(f"\n[{r['class']}] {r['id']}")
        print(f"  action: {r['action']}")
        for f in r["resolvable"]:
            print(f"    {f['invented']}  ->  {f['likely']}     ({f['why']})")
        if r["unresolved"]:
            print(f"    unresolved: {', '.join(r['unresolved'][:6])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
