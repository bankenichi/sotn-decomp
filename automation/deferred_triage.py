#!/usr/bin/env python3
"""Which deferred records are still deferred for a reason that still exists?

WHY THIS EXISTS
    `escalation_triage.py` classifies the escalated pile; nothing classified
    the deferred pile, so it was read by hand or not at all. Deferral is a
    HANDOFF, not a verdict, which makes a stale deferral invisible: the record
    looks deliberate, the note explains itself, and nothing ever re-checks
    whether the condition that caused it is still true.

    Measured 2026-08-09 over 46 records: the largest class had been waiting on
    a tier that could not run.

THE CLASSES

  stale-tier    TIER_HANDOFF_TOO_LARGE raised by the llama tier at 6000 chars
                and handed to "the next tier". The zen backend is hosted and
                takes 20000, but `_DEFAULT_MAX_FUNC` tested `== "cli"`, so zen
                inherited the local-llama ceiling and deferred these too. They
                were handed to a tier that was itself the broken cli backend.
                Now attemptable: requeue as todo.

  seed-bug      PERMUTER_EXHAUSTED where the note names an UNDECLARED SYMBOL.
                Not a decompilation failure at all: the permuter seed omits an
                `extern`, so a percentage of mutations die on KeyError. The
                fix is stated in the note and is mechanical. Several records
                usually share ONE missing symbol.

  permuter-out  PERMUTER_EXHAUSTED with a real score and no improvement. The
                permuter mutates expressions only, so this genuinely means
                re-derive from the asm. Legitimately deferred.

  no-note       no note at all. Cannot be assessed from the queue; needs a
                look.

  other         a note that says something specific and human (an unlabelled
                union member, say). Legitimately deferred.

STRICTLY READ-ONLY by default. `--requeue-plan` prints the exact scheduler
commands and still writes nothing.

Usage:
    python3 automation/deferred_triage.py
    python3 automation/deferred_triage.py --requeue-plan
    python3 automation/deferred_triage.py --self-test
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PYTHON = str(REPO / ".venv" / "bin" / "python")
if not Path(PYTHON).exists():                                # pragma: no cover
    PYTHON = sys.executable

RX_TOO_LARGE = re.compile(r"TIER_HANDOFF_TOO_LARGE")
RX_ASM_CHARS = re.compile(r"asm (\d+) chars")
RX_UNDECLARED = re.compile(r"UNDECLARED SYMBOL: the seed calls (\w+)")
RX_EXHAUSTED = re.compile(r"PERMUTER_EXHAUSTED")
RX_RESCUED = re.compile(r"RESCUED", re.I)

# What the hosted tiers will actually attempt. Kept in sync with
# worker_direct._DEFAULT_MAX_FUNC; a record is only "stale" if it is under it.
HOSTED_MAX_CHARS = 20000


def classify(note: str, asm_chars: int | None = None) -> tuple[str, str]:
    """(class, action). Pure, so the self-test can pin every branch."""
    note = note or ""
    if not note.strip():
        return "no-note", "no note to assess; read the record"

    if RX_TOO_LARGE.search(note):
        m = RX_ASM_CHARS.search(note)
        size = asm_chars if asm_chars is not None else (
            int(m.group(1)) if m else None)
        if size is not None and size > HOSTED_MAX_CHARS:
            return ("too-large-still",
                    f"asm {size} still exceeds the hosted ceiling "
                    f"{HOSTED_MAX_CHARS}; leave deferred")
        return ("stale-tier",
                f"deferred at the llama 6000-char ceiling"
                + (f" (asm {size})" if size else "")
                + "; the hosted tier takes 20000. Requeue as todo")

    if RX_EXHAUSTED.search(note):
        m = RX_UNDECLARED.search(note)
        if m:
            return ("seed-bug",
                    f"permuter seed omits `extern {m.group(1)}`; add it to "
                    f"base.c and re-import. NOT a decompilation failure")
        return ("permuter-out",
                "permuter genuinely exhausted; re-derive from the asm")

    return "other", "specific human note; leave deferred"


def load() -> list[dict]:
    """Deferred records, THROUGH THE SCHEDULER.

    Never reads a queue file directly. SOTN_QUEUE resolves per environment
    (~/sotn-work/queue.jsonl by default, outside the repo), and escalation_
    triage.py records an incident where a direct read of a stale snapshot
    returned 3 records while the live queue held 16 -- a wrong answer with no
    error. The scheduler is the single reader that always resolves the live
    path.
    """
    r = subprocess.run(
        [PYTHON, str(REPO / "automation" / "scheduler.py"),
         "list", "--status", "deferred"],
        capture_output=True, text=True, timeout=120, cwd=str(REPO))
    out = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line.startswith("deferred"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        tail = parts[2]
        rid, _, note = tail.partition("|")
        out.append({"id": rid.strip(), "note": note.strip()})
    return out


def queue_identity() -> tuple[str, dict]:
    """The resolved queue path and its status counts, printed before anything.

    A TOOL THAT READS THE WRONG QUEUE ANSWERS CONFIDENTLY AND WRONGLY. Run
    from the sandbox, SOTN_QUEUE resolves to a DIFFERENT ~/sotn-work than the
    operator's machine: on 2026-08-09 the sandbox copy held 438 records with
    33 matched and 1 deferred, while the live queue held 470 with 190 matched
    and 46 deferred. The report was correct about the file it read and useless
    about the one that matters.

    So the identity of the queue is stated up front, every run. A wrong queue
    is then obvious in one line instead of being invisible.
    """
    q = os.path.expanduser(os.environ.get("SOTN_QUEUE",
                                          "~/sotn-work/queue.jsonl"))
    r = subprocess.run([PYTHON, str(REPO / "automation" / "scheduler.py"),
                        "stats"], capture_output=True, text=True,
                       timeout=120, cwd=str(REPO))
    counts = {}
    for line in r.stdout.splitlines():
        k, _, v = line.strip().partition(":")
        if v.strip().isdigit():
            counts[k.strip()] = int(v.strip())
    return q, counts


def report(plan: bool = False) -> int:
    qpath, counts = queue_identity()
    print(f"queue: {qpath}")
    print("       " + "  ".join(f"{k} {v}" for k, v in counts.items()))
    if not counts.get("deferred"):
        print("\nNo deferred records in THIS queue. If that is unexpected, "
              "this is\nprobably not the queue you meant: run it through the "
              "connector, which\nexecutes on the machine that owns the live "
              "queue.")
    print()
    recs = load()
    if not recs:
        print("no deferred records")
        return 0
    buckets: dict[str, list] = collections.defaultdict(list)
    for r in recs:
        cls, action = classify(r.get("note", ""))
        buckets[cls].append((r, action))

    print(f"{len(recs)} deferred record(s)\n")
    order = ["stale-tier", "seed-bug", "no-note", "permuter-out",
             "too-large-still", "other"]
    for cls in order:
        if buckets.get(cls):
            print(f"  {cls:16} {len(buckets[cls])}")

    actionable = len(buckets.get("stale-tier", [])) + \
        len(buckets.get("seed-bug", []))
    print(f"\n{actionable} of {len(recs)} are deferred for a reason that no "
          f"longer holds, or for a mechanical fix.\n")
    print("=" * 78)

    for cls in order:
        for r, action in buckets.get(cls, []):
            print(f"\n[{cls}] {r['id']}\n  action: {action}")

    # One missing symbol usually strands several records at once, so name the
    # shared cause rather than repeating it per record.
    shared = collections.Counter()
    for r, _a in buckets.get("seed-bug", []):
        m = RX_UNDECLARED.search(r.get("note", ""))
        if m:
            shared[m.group(1)] += 1
    if shared:
        print("\n" + "=" * 78)
        print("\nseed-bug records grouped by the ONE symbol that strands them:")
        for sym, n in shared.most_common():
            print(f"  {n:2}x  extern for `{sym}` missing from base.c")

    if plan:
        print("\n" + "=" * 78)
        print("\nrequeue plan (nothing has been written):\n")
        for r, _a in buckets.get("stale-tier", []):
            print(f"  scheduler.py set {r['id']} --status todo")
    return 0


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    print("\na llama-ceiling handoff under the hosted ceiling is STALE")
    cls, act = classify(
        "TIER_HANDOFF_TOO_LARGE: asm 7234 chars > 6000 on backend=http; "
        "handed off to the next tier")
    ck(cls == "stale-tier", f"classified stale-tier ({cls})")
    ck("20000" in act, "and the action says why it is attemptable now")

    print("\nbut one genuinely over the hosted ceiling is NOT")
    cls2, act2 = classify(
        "TIER_HANDOFF_TOO_LARGE: asm 24000 chars > 6000 on backend=http")
    ck(cls2 == "too-large-still", f"stays deferred ({cls2})")
    # The distinction matters: requeueing these would send them straight back
    # to deferred, burning a claim and a scheduler round trip each time.
    ck("leave deferred" in act2, "and says so")

    print("\nan undeclared-symbol permuter note is a seed bug, not a failure")
    cls3, act3 = classify(
        "PERMUTER_EXHAUSTED: UNDECLARED SYMBOL: the seed calls "
        "func_us_801B171C without declaring it, so the permuter raised "
        "KeyError on 316 mutations (8% of iterations).")
    ck(cls3 == "seed-bug", f"classified seed-bug ({cls3})")
    ck("func_us_801B171C" in act3, "and names the missing symbol")

    print("\na real permuter exhaustion stays deferred")
    cls4, _ = classify(
        "PERMUTER_EXHAUSTED: best 400 after 2967 iterations, 1 promotion(s), "
        "no improvement for 2967.")
    ck(cls4 == "permuter-out", f"classified permuter-out ({cls4})")

    print("\nan empty note is not silently bucketed as fine")
    ck(classify("")[0] == "no-note", "empty note flagged")
    ck(classify("   ")[0] == "no-note", "whitespace-only note flagged")

    print("\na specific human note is left alone")
    ck(classify("Needs the correct member name for Ext union offset 0x2E")[0]
       == "other", "unlabelled union member stays deferred")

    print("\nthe queue is read through the scheduler, never off disk")
    src_self = Path(__file__).read_text(errors="ignore")
    ck("scheduler.py" in src_self and "queue.jsonl" not in src_self.split(
        "def self_test")[0].replace("~/sotn-work/queue.jsonl", ""),
       "no direct queue-file read in the loader")

    print("\nthe queue being read is identified before any conclusion")
    src_self = Path(__file__).read_text(errors="ignore")
    ck("def queue_identity" in src_self
       and "print(f\"queue: {qpath}\")" in src_self,
       "the resolved path and counts are printed first")

    print("\nthe hosted ceiling matches the worker's own constant")
    src = (REPO / "automation" / "win" / "worker_direct.py").read_text(
        errors="ignore")
    ck(f'"{HOSTED_MAX_CHARS}" if MODEL_BACKEND in _HOSTED' in src,
       "HOSTED_MAX_CHARS agrees with worker_direct")
    ck('_HOSTED = {"cli", "zen"}' in src,
       "and zen is on the hosted side of that test")

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
    ap.add_argument("--requeue-plan", action="store_true",
                    help="print the scheduler commands; writes nothing")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    return report(a.requeue_plan)


if __name__ == "__main__":
    raise SystemExit(main())
