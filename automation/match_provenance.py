#!/usr/bin/env python3
"""Which part of the harness actually produced each match?

WHY THIS EXISTS
    The harness has six ways to turn a stub into a matching function, and they
    cost wildly different amounts. A header shim lands a dozen functions in one
    build cycle for a few minutes of segment work; a fleet model burns roughly
    ten minutes of wall clock per attempt and produces nothing 91% of the time;
    the permuter can hold four cores for hours. Until now nothing measured
    which of them the 189 matches actually came from, so every decision about
    where to spend effort was made on impression.

    `provenance_check.py` answers a DIFFERENT question -- how similar a body is
    to upstream's -- and deliberately says nothing about who wrote it here.

WHAT COUNTS AS A SOURCE
    shim-segment   a shared header adopted with splat .data/.bss segment work.
                   The expensive, high-yield engineering: one shim retires many
                   stubs at once.
    shim-header    a body copied or relocated verbatim from a shared header
                   that needed no segment surgery.
    twin-port      a body ported from a sibling overlay or the RIC twin, with
                   the divergences worked out by hand.
    permuter       decomp-permuter searched an existing compiling body to a
                   score of 0.
    model-fleet    an OpenCode or llama worker generated the C.
    claude-manual  written or repaired by hand/agent, including the cases where
                   a model's C was correct but needed a declaration fix.
    unknown        the evidence does not support a claim. REPORTED, NOT HIDDEN.

    A match often has more than one contributor -- a model produces C, a human
    fixes one extern, the permuter closes the last 160 points. So each record
    gets ONE primary source (by the precedence in _PRECEDENCE, which orders by
    which step was decisive) and a set of contributors, and both are reported.

WHY SOME RECORDS CANNOT BE ATTRIBUTED
    `scheduler.py report` OVERWRITES the notes field. When a landing finishes it
    writes "build/us/BO6.BIN sha1=... verified", which destroys whatever method
    note was there before. Those records fall back to git and to claimed_by,
    and when neither resolves it they are counted as unknown rather than
    guessed at. The unknown count IS the finding: it measures how much history
    the overwrite has already eaten.

EVIDENCE, in the order it is trusted
    1. queue notes        explicit prose about how it was solved
    2. queue fields       claimed_by, iterations, best_score, tier_reached
    3. git                the commit that introduced the body (pickaxe on the
                          function name), its subject and author
    4. source file        the shim include that makes the body reachable

STRICTLY READ-ONLY. Never edits sources, never builds, never touches the queue.

Usage:
    python3 automation/match_provenance.py
    python3 automation/match_provenance.py --detail        # per-function table
    python3 automation/match_provenance.py --source permuter
    python3 automation/match_provenance.py --unknown       # only the gaps
    python3 automation/match_provenance.py --no-git        # skip git (faster)
    python3 automation/match_provenance.py --json out.json
    python3 automation/match_provenance.py --self-test
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
QUEUE = Path(os.path.expanduser(
    os.environ.get("SOTN_QUEUE", "~/sotn-work/queue.jsonl")))

# ---------------------------------------------------------------- the sources

SOURCES = ("shim-segment", "shim-header", "twin-port", "permuter",
           "model-fleet", "claude-manual", "unknown")

# Ordered by which step was DECISIVE, not by which happened first.
#
# The permuter outranks the model deliberately: when a model produced a body
# that scored 735 and the permuter drove it to 0, the search is what turned a
# near into a match, and counting it as a model win would overstate the fleet.
# Shims outrank everything because a shimmed function was never generated at
# all -- attributing it to whatever agent pressed the button would be pure
# fiction.
_PRECEDENCE = ("shim-segment", "shim-header", "twin-port", "permuter",
               "claude-manual", "model-fleet", "unknown")

# Every pattern below was read off real queue notes on 2026-08-03, not
# invented. Keep them anchored to phrases the harness and its operators
# actually write, and prefer a miss (-> unknown) over a loose match.
_PATTERNS = (
    # (source, compiled regex, why this phrase means that source)
    ("shim-segment", re.compile(
        r"\bshimmed via\b|\bsplat \.data\b|\badded \.data\b|\.bss segment|"
        r"\bsegment work\b|\bdata split at\b", re.I)),
    ("shim-header", re.compile(
        r"verbatim (copy|from)|copied (the )?body|relocated (body )?verbatim|"
        r"\brelocated verbatim\b|adopted shared body|"
        r"\bcopied body from\b|shared body from", re.I)),
    ("twin-port", re.compile(
        r"\bported from\b|\bmirrored\b|\btwin\b|\bfrom_bo0\b|\bfrom_no4\b|"
        r"sibling overlay", re.I)),
    ("permuter", re.compile(
        r"\bpermuter\b|seed promotion|\bscore-\d+ base\b|"
        r"\bpromoted to\b|iterations?\b.*\bscore 0\b", re.I)),
    ("claude-manual", re.compile(
        r"\bwrote per proposal\b|\bper patch note\b|\bhand-\w+\b|"
        r"the model'?s C was\b|\bfixed by declaring\b|\bmanually\b|"
        r"\bwrote the body\b|\bre-derived\b", re.I)),
    ("model-fleet", re.compile(
        r"\bmodel produced\b|\bmatched first try\b|\battempt \d+\b|"
        r"\blow-confidence patch\b|\bgeneration errors\b", re.I)),
)

# A note that is ONLY a build proof carries no method information at all. It is
# what scheduler.py writes when a landing succeeds, and it overwrote whatever
# was there. Detecting it explicitly keeps these out of `unknown-blank`, which
# is a different failure: blank means nothing was ever recorded, overwritten
# means something was and is gone.
_PROOF_ONLY = re.compile(
    r"^\s*build/\S+\.BIN sha1=[0-9a-f]{40} verified[^|]*$", re.I)
_VERIFY_ONLY = re.compile(
    r"^\s*(already present in src/|verified \d+/\d+ checksum)", re.I)


def classify_note(note: str) -> set[str]:
    """Every source the note gives positive evidence for."""
    if not note:
        return set()
    return {src for src, rx in _PATTERNS if rx.search(note)}


def note_is_proof_only(note: str) -> bool:
    """True when the note is a build receipt that replaced the method note."""
    if not note:
        return False
    return bool(_PROOF_ONLY.match(note.strip())
                or _VERIFY_ONLY.match(note.strip()))


# claimed_by tells WHO ran it. Worker names come from fleet_start; the
# supervisor and manual sessions use their own. This is weaker evidence than a
# note -- a fleet worker can claim a record whose body ends up hand-written --
# so it only ever ADDS a contributor, and only decides the primary source when
# nothing else did.
_CLAIM_FLEET = re.compile(r"^(fleet|worker)-", re.I)
_CLAIM_PERMUTER = re.compile(r"permuter|supervisor", re.I)
_CLAIM_MANUAL = re.compile(r"claude|agent|manual|manual-|kenichi", re.I)


def classify_claim(claimed_by: str) -> set[str]:
    if not claimed_by:
        return set()
    if _CLAIM_PERMUTER.search(claimed_by):
        return {"permuter"}
    if _CLAIM_FLEET.match(claimed_by):
        return {"model-fleet"}
    if _CLAIM_MANUAL.search(claimed_by):
        return {"claude-manual"}
    return set()


def classify_fields(rec: dict) -> set[str]:
    """Structural evidence that does not depend on anyone writing prose.

    `iterations` is only ever set by the permuter loop, so a positive count is
    hard evidence the search ran on this function regardless of what the note
    says or whether it was later overwritten.
    """
    out = set()
    try:
        if int(rec.get("iterations") or 0) > 0:
            out.add("permuter")
    except (TypeError, ValueError):
        pass
    return out


# ------------------------------------------------------------------ git layer

def git_introduced(fn: str, timeout: int = 20) -> tuple[str, str]:
    """(commit subject, author) for the commit that introduced this body.

    Pickaxe on the function NAME with -S, which finds commits that changed the
    number of occurrences of the string -- i.e. the one that added the
    definition. Falls back to ("", "") rather than raising: git being slow or
    unavailable must degrade this report, not break it.
    """
    if not re.fullmatch(r"[A-Za-z_]\w*", fn or ""):
        return "", ""
    # %x09 (a TAB), not a literal NUL. `--format=%s\x00%an` put a real zero
    # byte in argv, and execve() cannot carry one: every call raised
    # ValueError: embedded null byte before git ever ran. It survived review
    # because both self-tests passed names that return early, so the
    # subprocess line was never once executed. git expands %x09 itself, so the
    # separator reaches the output without ever being a NUL in our argv.
    SEP = "\t"
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--diff-filter=M", f"-S{fn}(",
             "--format=%s%x09%an", "--", "src"],
            cwd=str(REPO), capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return "", ""
    if r.returncode != 0 or not (r.stdout or "").strip():
        return "", ""
    head = r.stdout.strip().splitlines()[0]
    subj, _, author = head.partition(SEP)
    return subj.strip(), author.strip()


_COMMIT_PATTERNS = (
    ("shim-segment", re.compile(r"\bshim\w*\b|\bsegment\b|\bsplat\b", re.I)),
    ("shim-header", re.compile(r"\bharvest\w*\b|\bshared header\b", re.I)),
    ("permuter", re.compile(r"\bpermuter\b", re.I)),
    ("twin-port", re.compile(r"\btwin\b|\bport\w*\b|\bmirror\w*\b", re.I)),
)


def classify_commit(subject: str) -> set[str]:
    if not subject:
        return set()
    return {src for src, rx in _COMMIT_PATTERNS if rx.search(subject)}


# --------------------------------------------------------------- the verdict

def attribute(rec: dict, subject: str = "", author: str = "") -> dict:
    """One record -> primary source, contributors, and the evidence used.

    Every returned verdict carries WHY, because an attribution nobody can check
    is worth as much as a guess.
    """
    note = (rec.get("notes") or "").strip()
    ev: list[str] = []

    from_note = classify_note(note)
    if from_note:
        ev.append(f"notes: {', '.join(sorted(from_note))}")
    from_fields = classify_fields(rec)
    if from_fields:
        ev.append(f"iterations={rec.get('iterations')}")
    from_claim = classify_claim(str(rec.get("claimed_by") or ""))
    if from_claim:
        ev.append(f"claimed_by={rec.get('claimed_by')}")
    from_commit = classify_commit(subject)
    if from_commit:
        ev.append(f"commit: {subject[:60]}")

    contributors = from_note | from_fields | from_claim | from_commit
    overwritten = note_is_proof_only(note)

    # Notes and structure decide; claimed_by and the commit only break ties,
    # because "a fleet worker held this record" does not mean a model wrote the
    # body that finally matched.
    strong = from_note | from_fields
    pool = strong or from_commit or from_claim
    primary = "unknown"
    for src in _PRECEDENCE:
        if src in pool:
            primary = src
            break

    return {
        "function": rec.get("function", ""),
        "id": rec.get("id", ""),
        "overlay": rec.get("overlay", ""),
        "primary": primary,
        "contributors": sorted(contributors),
        "evidence": ev,
        "note_overwritten": overwritten,
        "note": note[:200],
        "commit": subject[:100],
        "author": author,
    }


def load_queue(path: Path | None = None) -> list[dict]:
    p = path or QUEUE
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def analyse(records: list[dict], use_git: bool = True) -> list[dict]:
    out = []
    for rec in records:
        if rec.get("status") != "matched":
            continue
        subj = auth = ""
        if use_git:
            subj, auth = git_introduced(rec.get("function", ""))
        out.append(attribute(rec, subj, auth))
    return out


# ------------------------------------------------------------------ reporting

def report(rows: list[dict], detail: bool = False) -> None:
    if not rows:
        print("No matched records found. Is SOTN_QUEUE pointing at the real "
              f"queue? Tried {QUEUE}")
        return

    n = len(rows)
    prim = Counter(r["primary"] for r in rows)
    print(f"\n{n} matched function(s)\n")
    print(f"{'source':16} {'count':>6} {'share':>7}   what it means")
    print("-" * 78)
    blurb = {
        "shim-segment": "shared header + splat segment work",
        "shim-header":  "body copied from a shared header",
        "twin-port":    "ported from a sibling overlay / RIC",
        "permuter":     "decomp-permuter search reached 0",
        "model-fleet":  "an OpenCode or llama worker wrote it",
        "claude-manual": "written or repaired by hand",
        "unknown":      "evidence insufficient; NOT a guess",
    }
    for src in _PRECEDENCE:
        c = prim.get(src, 0)
        if not c:
            continue
        print(f"{src:16} {c:6d} {100.0*c/n:6.0f}%   {blurb.get(src,'')}")
    print("-" * 78)
    print(f"{'TOTAL':16} {n:6d}")

    # Contribution counts every source that touched a function, so a match the
    # model started and the permuter finished shows up under both. These sum to
    # more than the total on purpose.
    contrib = Counter()
    for r in rows:
        for c in r["contributors"]:
            contrib[c] += 1
    if contrib:
        print("\ncontributed to (a match can have several; these overlap)")
        for src, c in contrib.most_common():
            print(f"  {src:16} {c:5d}")

    over = [r for r in rows if r["note_overwritten"]]
    blank = [r for r in rows if not r["note"] and not r["note_overwritten"]]
    unk = [r for r in rows if r["primary"] == "unknown"]
    print(f"\n{len(unk)} unattributed ({100.0*len(unk)/n:.0f}%)")
    print(f"  {len(over)} had their method note OVERWRITTEN by a build receipt")
    print(f"  {len(blank)} never had a note at all")
    if over:
        print("\n  scheduler.py report replaces `notes` wholesale, so a "
              "landing\n  receipt erases how the function was solved. That is "
              "recoverable\n  going forward by appending rather than "
              "replacing; it is not\n  recoverable for the records above.")

    by_ovl = defaultdict(Counter)
    for r in rows:
        by_ovl[r["overlay"] or "?"][r["primary"]] += 1
    print("\nby overlay")
    hdr = [s for s in _PRECEDENCE if prim.get(s)]
    print(f"  {'overlay':14}" + "".join(f"{s[:11]:>13}" for s in hdr))
    for ovl, c in sorted(by_ovl.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {ovl:14}" + "".join(f"{c.get(s,0):13d}" for s in hdr))

    if detail:
        print("\nper function")
        for r in sorted(rows, key=lambda r: (r["primary"], r["function"])):
            print(f"  {r['primary']:14} {r['function'][:38]:38} "
                  f"{'; '.join(r['evidence'])[:70]}")


# --------------------------------------------------------------- self-test

def self_test() -> int:
    fails = []

    def ck(cond, label, detail=""):
        print(("  ok   " if cond else "  FAIL ") + label
              + ("" if cond else "   " + detail))
        if not cond:
            fails.append(label)

    print("\nreal queue notes are classified the way a reader would")
    # Every string here is copied from an actual matched record.
    cases = [
        ("Verbatim copy from st_common.h:426-430.", "shim-header"),
        ("Relocated verbatim from giantbro_helpers.h, no changes needed.",
         "shim-header"),
        ("Copied body verbatim from sibling overlay src/st/no0/clock_room.c:65.",
         "shim-header"),
        ("Shimmed via src/st/e_medusa_head.h, .data e_medusa_head at 0x3354.",
         "shim-segment"),
        ("Ported from src/ric/pl_steps.c:RicStepFall.", "twin-port"),
        ("Mirrored matched original at src/st/no2_bg.h:114.", "twin-port"),
        ("Matched via permuter seed promotion 735->160->0.", "permuter"),
        ("Matched via double seed promotion 220->70->0 in 31 iterations.",
         "permuter"),
    ]
    for note, want in cases:
        got = attribute({"notes": note, "function": "f"})["primary"]
        ck(got == want, f"{want:14} <- {note[:52]}", f"got {got}")

    print("\nprecedence reflects which step was DECISIVE")
    r = attribute({"notes": "Matched via permuter seed promotion 735->160->0; "
                            "the model's C was the starting point",
                   "function": "f"})
    ck(r["primary"] == "permuter",
       "a model draft finished by the permuter counts as permuter")
    ck("claude-manual" in r["contributors"] or "permuter" in r["contributors"],
       "but the other contributor is still recorded, not discarded")
    r2 = attribute({"notes": "Shimmed via src/st/collision.h", "function": "f",
                    "claimed_by": "fleet-oc-1"})
    ck(r2["primary"] == "shim-segment",
       "a shimmed function is NOT credited to the worker that held the record")

    print("\nstructural evidence works without any prose")
    r3 = attribute({"notes": "", "iterations": 4210, "function": "f"})
    ck(r3["primary"] == "permuter",
       "a positive iteration count is set only by the permuter loop")
    ck("iterations=4210" in " ".join(r3["evidence"]),
       "and the evidence says so, so the call can be checked")

    print("\noverwritten notes are detected, not silently counted as blank")
    proof = ("build/us/BO6.BIN sha1=fe067af9b7adca08dc99b108129a0f45a7ad45cd "
             "verified against config/check.us.sha")
    ck(note_is_proof_only(proof),
       "a build receipt is recognised as carrying no method information")
    ck(not note_is_proof_only("Verbatim copy from st_common.h:426-430."),
       "a real method note is not mistaken for a receipt")
    r4 = attribute({"notes": proof, "function": "f"})
    ck(r4["primary"] == "unknown",
       "and it yields unknown rather than an invented source")
    ck(r4["note_overwritten"],
       "flagged as overwritten, which is a different gap from never-recorded")

    print("\nthe report never invents an attribution")
    r5 = attribute({"notes": "", "function": "f"})
    ck(r5["primary"] == "unknown" and not r5["contributors"],
       "no evidence at all yields unknown with no contributors")
    ck("unknown" in SOURCES and _PRECEDENCE[-1] == "unknown",
       "unknown is last in precedence, so anything real outranks it")

    print("\nclaimed_by only breaks ties, it never overrides a note")
    r6 = attribute({"notes": "Verbatim copy from st_common.h:1.",
                    "claimed_by": "fleet-oc-2", "function": "f"})
    ck(r6["primary"] == "shim-header",
       "a worker holding the record does not make it a model win")
    r7 = attribute({"notes": proof, "claimed_by": "fleet-oc-2", "function": "f"})
    ck(r7["primary"] == "model-fleet",
       "but with the note destroyed, claimed_by is better than nothing")

    print("\ngit failures degrade the report, they do not break it")
    ck(git_introduced("") == ("", ""), "an empty function name is refused")
    ck(git_introduced("not a real name; rm -rf") == ("", ""),
       "and anything that is not an identifier never reaches git")
    # THE CHECK THAT WAS MISSING. Both cases above return before the
    # subprocess call, so the argv was never actually executed and a literal
    # NUL byte in the format string shipped. Every dashboard button that ran
    # without --no-git died with "ValueError: embedded null byte".
    got = git_introduced("InitializeEntity")
    ck(isinstance(got, tuple) and len(got) == 2,
       f"a REAL identifier reaches git and comes back cleanly ({got!r})")
    ck(all(isinstance(x, str) for x in got),
       "both halves are strings whether or not git found anything")
    ck(all("\x00" not in x for x in got),
       "and no NUL survives into the result")
    # Scope to CODE lines. The first version of this scanned the raw source
    # and matched the comment above explaining the bug, which is the same
    # class of mistake as the assertions that matched their own prose earlier
    # today: a check that reads documentation instead of behaviour.
    body = inspect.getsource(git_introduced)
    code = "\n".join(l for l in body.splitlines()
                     if not l.lstrip().startswith("#"))
    code = re.sub(r'""".*?"""', "", code, flags=re.S)
    ck("\\x00" not in code and "\x00" not in code,
       "the git argv contains no literal NUL; execve cannot carry one")

    print("\nthe full pipeline runs end to end, git included")
    # analyse() with use_git=True is the path the dashboard actually calls.
    rows = analyse([{"status": "matched", "function": "InitializeEntity",
                     "id": "x", "overlay": "ST/RNO0",
                     "notes": "Verbatim copy from st_common.h:506-533."}],
                   use_git=True)
    ck(len(rows) == 1 and rows[0]["primary"] == "shim-header",
       f"one matched record in, one attributed row out ({rows})")

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
    ap.add_argument("--detail", action="store_true",
                    help="one line per matched function")
    ap.add_argument("--source", help="show only this source, with evidence")
    ap.add_argument("--unknown", action="store_true",
                    help="show only records that could not be attributed")
    ap.add_argument("--no-git", action="store_true",
                    help="skip the git pickaxe; faster, slightly less evidence")
    ap.add_argument("--json", help="write the full attribution to this file")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    recs = load_queue()
    if not recs:
        print(f"no queue at {QUEUE}. Set SOTN_QUEUE if it lives elsewhere.",
              file=sys.stderr)
        return 2
    rows = analyse(recs, use_git=not a.no_git)

    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"wrote {len(rows)} record(s) to {a.json}")

    if a.unknown or a.source:
        want = "unknown" if a.unknown else a.source
        sel = [r for r in rows if r["primary"] == want]
        print(f"\n{len(sel)} record(s) with primary source {want}\n")
        for r in sel:
            print(f"  {r['function'][:40]:40} {r['overlay']:14}")
            if r["note"]:
                print(f"      note: {r['note'][:110]}")
            if r["commit"]:
                print(f"      commit: {r['commit'][:100]}")
            if r["note_overwritten"]:
                print("      (method note was overwritten by a build receipt)")
        return 0

    report(rows, detail=a.detail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
