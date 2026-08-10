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



_ASM_INDEX: dict | None = None


def real_asm_chars(rec_id: str) -> int | None:
    """The size of the actual .s file, not the size the note claims.

    THE NOTE CANNOT BE TRUSTED FOR THIS. The deferral message reports the
    length of the asm AFTER the prompt builder truncated it, so eleven records
    all claimed exactly "asm 12000 chars" -- a cap, not a measurement. Their
    real sizes ranged from 12,186 to 43,582, and nine of the twenty-five were
    genuinely over the hosted 20000 ceiling. Requeueing those on the strength
    of the note would send them straight back to deferred, one wasted claim and
    scheduler round trip each.
    """
    global _ASM_INDEX
    if _ASM_INDEX is None:
        _ASM_INDEX = {}
        root = REPO / "asm" / "us"
        if root.is_dir():
            for f in root.rglob("*.s"):
                _ASM_INDEX.setdefault(f.stem, f)
    fn = rec_id.rsplit(":", 1)[-1]
    # Queue ids carry a `_from_<overlay>` suffix for shimmed-in functions; the
    # .s file is named without it.
    for cand in (fn, re.sub(r"_from_\w+$", "", fn)):
        f = _ASM_INDEX.get(cand)
        if f:
            try:
                return f.stat().st_size
            except OSError:
                return None
    return None


# The marker fix_seed_declarations.py / worker_direct._declare_stub_siblings
# leave in a seed whose INCLUDE_ASM stub siblings had to be declared.
SEED_RETROFIT_MARKER = "Added by the permuter-seed writer"
SEEDS = REPO / "automation" / "candidates"


def seed_path(rec_id: str) -> Path:
    """automation/candidates/ name for a record id.

    us:BOSS/BO0:func_us_801B1DDC -> us_BOSS_BO0_func_us_801B1DDC.c
    """
    return SEEDS / (rec_id.replace(":", "_").replace("/", "_") + ".c")


def seed_was_retrofitted(rec_id: str) -> bool:
    """Did this record's seed need stub declarations added after it ran?

    If so, the permuter searched it while decomp-permuter's typemap was
    raising KeyError on every mutation that touched an undeclared call --
    between 3% and 17% of iterations on the BOSS/BO0 records. A
    PERMUTER_EXHAUSTED verdict reached under that handicap is not evidence
    that the function is hard, so it must not keep sitting in the same bucket
    as a search that really did run to completion.
    """
    p = seed_path(rec_id)
    try:
        return SEED_RETROFIT_MARKER in p.read_text(encoding="utf-8",
                                                   errors="replace")
    except OSError:
        return False


def classify(note: str, asm_chars: int | None = None,
             seed_retrofitted: bool = False) -> tuple[str, str]:
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
                    f"the seed did not declare `{m.group(1)}`, so the "
                    f"permuter's typemap raised KeyError on part of the "
                    f"search. The seed is fixed; requeue as near")
        if seed_retrofitted:
            # The note reads like a clean exhaustion, and it is not. Only the
            # seed on disk knows: it carries the retrofit marker, so the run
            # that produced this verdict was missing a declaration the note
            # never mentioned. On BOSS/BO0 that was func_us_801B163C, named in
            # no note at all.
            return ("degraded-search",
                    "reported as exhausted, but its seed was missing stub "
                    "declarations at the time, so part of every mutation set "
                    "died on KeyError. Verdict not trustworthy; requeue as "
                    "near")
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


# class -> the status a requeue should file it under.
#   near  the seed is good and the permuter should pick it up again
#   todo  no usable seed; a worker has to derive it from the asm
REQUEUE_TO = {"seed-bug": "near", "degraded-search": "near",
              "stale-tier": "todo"}

# Overwrites the stale deferral note. Leaving the old one in place would keep
# telling the next reader that the permuter is exhausted, which is the belief
# this requeue exists to correct.
REQUEUE_NOTE = {
    "seed-bug":
        "requeued by deferred_triage: the seed did not declare an "
        "INCLUDE_ASM stub sibling it calls, so the permuter's typemap raised "
        "KeyError on part of the search. Seed fixed by "
        "fix_seed_declarations.py; this was never a decompilation failure.",
    "degraded-search":
        "requeued by deferred_triage: the earlier PERMUTER_EXHAUSTED verdict "
        "was reached on a seed missing stub declarations, so a share of every "
        "mutation set died on KeyError. Seed fixed; the exhaustion figure in "
        "the previous note does not describe a complete search.",
    "stale-tier":
        "requeued by deferred_triage: deferred at the local llama 6000-char "
        "ceiling, which the hosted tier does not have.",
}


def requeue_note(cls: str, rec_id: str) -> str:
    """The replacement note, WITH the seed reference preserved.

    THE NOTE IS NOT JUST PROSE. permuter_supervisor.candidates() finds a
    record's starting point by parsing `seed=<path>` out of this field; there
    is nowhere else it is recorded. Overwriting the note with a tidy
    explanation and no seed= would file sixteen records as `near` that the
    supervisor then could not import, which is a worse state than leaving them
    deferred, because it looks like progress.

    A deferral note may or may not carry seed=, so it is regenerated from the
    file on disk rather than salvaged from the old text.
    """
    note = REQUEUE_NOTE[cls]
    p = seed_path(rec_id)
    if p.exists():
        note += f" seed={p.relative_to(REPO).as_posix()}"
    return note


def requeue(buckets: dict, apply: bool = False) -> int:
    """Move the actionable classes back into circulation.

    Writes THROUGH scheduler.py, never to the queue file. The scheduler is the
    single writer, it is the thing that refuses `matched` without --proof, and
    going around it is how two processes end up with different ideas of the
    same record.

    Nothing here can produce `matched`; the only reachable statuses are `near`
    and `todo`, both of which mean "someone should look at this again".
    """
    todo = [(cls, r["id"]) for cls in REQUEUE_TO
            for r, _a in buckets.get(cls, [])]
    if not todo:
        print("\nnothing to requeue")
        return 0

    print("\n" + "=" * 78)
    print(f"\nrequeue: {len(todo)} record(s)"
          + ("" if apply else "  [DRY RUN, nothing written]") + "\n")
    ok = bad = 0
    for cls, rid in todo:
        status = REQUEUE_TO[cls]
        if not apply:
            print(f"  {status:5} <- {cls:16} {rid}")
            continue
        # `report`, not `set`. There is no `set` subcommand and there never
        # was; --requeue-plan printed `scheduler.py set <id> --status todo`
        # for months and anyone who pasted it got
        # "invalid choice: 'set'". The plan was never executed, so nothing
        # caught it. That is the argument for the tool doing the write rather
        # than printing instructions for a human to run.
        r = subprocess.run(
            [PYTHON, str(REPO / "automation" / "scheduler.py"), "report",
             "--id", rid, "--status", status,
             "--notes", requeue_note(cls, rid)],
            capture_output=True, text=True, timeout=120, cwd=str(REPO))
        if r.returncode == 0:
            ok += 1
            print(f"  {status:5} <- {cls:16} {rid}")
        else:
            bad += 1
            err = (r.stderr or r.stdout or "").strip().splitlines()
            print(f"  FAILED {rid}: {err[-1] if err else r.returncode}")
    if apply:
        print(f"\n{ok} requeued, {bad} failed")
        if ok:
            print("Run permuter_supervisor.py --plan to see what it will "
                  "pick up.")
    else:
        print("\nRe-run with --apply to write.")
    return 1 if bad else 0


def report(plan: bool = False, do_requeue: bool = False,
           apply: bool = False) -> int:
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
        cls, action = classify(r.get("note", ""),
                               real_asm_chars(r["id"]),
                               seed_was_retrofitted(r["id"]))
        buckets[cls].append((r, action))

    print(f"{len(recs)} deferred record(s)\n")
    order = ["stale-tier", "seed-bug", "degraded-search", "no-note",
             "permuter-out", "too-large-still", "other"]
    for cls in order:
        if buckets.get(cls):
            print(f"  {cls:16} {len(buckets[cls])}")

    actionable = sum(len(buckets.get(c, [])) for c in REQUEUE_TO)
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
        for cls in REQUEUE_TO:
            for r, _a in buckets.get(cls, []):
                print(f"  scheduler.py report --id {r['id']} "
                      f"--status {REQUEUE_TO[cls]}")
    if do_requeue:
        return requeue(buckets, apply=apply)
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

    print("\nthe MEASURED asm size overrides the size the note claims")
    # Eleven notes all said "asm 12000 chars" because the prompt builder had
    # truncated there. Real sizes were 12,186 to 43,582.
    capped = "TIER_HANDOFF_TOO_LARGE: asm 12000 chars > 6000 on backend=http"
    ck(classify(capped, 43582)[0] == "too-large-still",
       "a note saying 12000 does not requeue a 43,582-char function")
    ck(classify(capped, 13447)[0] == "stale-tier",
       "while a genuinely mid-size one still requeues")
    ck(classify(capped)[0] == "stale-tier",
       "and with no measurement it falls back to the note")

    print("\nthe queue being read is identified before any conclusion")
    src_self = Path(__file__).read_text(errors="ignore")
    ck("def queue_identity" in src_self
       and "print(f\"queue: {qpath}\")" in src_self,
       "the resolved path and counts are printed first")

    print("\na retrofitted seed makes an 'exhausted' verdict untrustworthy")
    # The note is indistinguishable from a clean exhaustion. Only the seed on
    # disk records that the search was handicapped, which is why classify
    # takes the seed state as a separate input rather than parsing for it.
    clean = ("PERMUTER_EXHAUSTED: best 1770 after 2701 iterations, "
             "3 promotion(s), no improvement for 2662.")
    ck(classify(clean, None, False)[0] == "permuter-out",
       "without the marker it stays permuter-out")
    cls_d, act_d = classify(clean, None, True)
    ck(cls_d == "degraded-search", f"with it, degraded-search ({cls_d})")
    ck("not trustworthy" in act_d, "and the action says why")
    ck(REQUEUE_TO.get("degraded-search") == "near",
       "which requeues to near, not todo: the seed is now good")

    print("\nrequeue can never produce a matched record")
    ck(set(REQUEUE_TO.values()) <= {"near", "todo"},
       f"only near/todo are reachable ({sorted(set(REQUEUE_TO.values()))})")
    # Anchor on the full signature: `def requeue_note` sorts before
    # `def requeue(` in this file, and a loose "def requeue" split silently
    # measured the wrong function.
    ck("def requeue(buckets" in src_self, "the requeue function is findable")
    src_rq = src_self.split("def requeue(buckets")[1].split("\ndef ")[0]
    ck("scheduler.py" in src_rq, "writes go through scheduler.py")
    ck("queue.jsonl" not in src_rq, "and never straight to the queue file")
    ck("apply" in src_rq and 'if not apply' in src_rq,
       "and it is a dry run unless --apply")

    print("\nthe subcommand it calls actually exists in scheduler.py")
    # --requeue-plan printed `scheduler.py set <id> --status todo` for months.
    # There is no `set` subcommand. Nobody noticed because the plan was only
    # ever printed, never run. Pin the name against the real parser.
    ssrc = (REPO / "automation" / "scheduler.py").read_text(errors="ignore")
    subs = set(re.findall(r'sub\.add_parser\("(\w+)"', ssrc))
    called = set(re.findall(r'"scheduler\.py"\), "(\w+)"', src_self))
    ck(called and called <= subs,
       f"every subcommand this module invokes exists ({sorted(called)} "
       f"against {sorted(subs)})")
    ck("set" not in called, "and it is not the `set` that never existed")
    for flag in ("--id", "--status", "--notes"):
        ck(f'pr.add_argument("{flag}"' in ssrc,
           f"scheduler report accepts {flag}")

    print("\nthe requeue note keeps the seed= the supervisor parses for")
    # permuter_supervisor.candidates() finds the seed ONLY by parsing seed=
    # out of the note. A tidy replacement note without it would file records
    # as near that cannot then be imported.
    real_id = "us:BOSS/BO0:func_us_801B1DDC"
    if seed_path(real_id).exists():
        n = requeue_note("degraded-search", real_id)
        ck("seed=automation/candidates/" in n, f"seed= is present ({n[-60:]})")
        ck(seed_path(real_id).name in n, "and names this record's own seed")
        sup = (REPO / "automation" / "permuter_supervisor.py").read_text(
            errors="ignore")
        m = re.search(r'seed=\S*?\(\[^\\s\]\+\)|seed=', sup)
        ck(bool(m), "the supervisor really does parse seed= from the note")
    else:
        print("  skip  no seed on disk for the sample record")
    ck("seed=" not in REQUEUE_NOTE["degraded-search"],
       "the template itself has no hardcoded seed path")
    ck(requeue_note("stale-tier", "us:NO/SUCH:function").count("seed=") == 0,
       "and a record with no seed file gets no seed= at all")

    print("\nthe seed path derived from a record id is the real one")
    ck(seed_path("us:BOSS/BO0:func_us_801B1DDC").name
       == "us_BOSS_BO0_func_us_801B1DDC.c", "id maps to the seed filename")
    ck(seed_was_retrofitted("us:NO/SUCH:function") is False,
       "a missing seed is not treated as retrofitted")

    print("\nthe marker matches what the seed writer actually emits")
    wsrc = (REPO / "automation" / "win" / "worker_direct.py").read_text(
        errors="ignore")
    ck(SEED_RETROFIT_MARKER in wsrc,
       "worker_direct emits the string this module looks for")
    fsrc = (REPO / "automation" / "fix_seed_declarations.py").read_text(
        errors="ignore")
    ck("_declare_stub_siblings" in fsrc,
       "and the retrofit tool calls the same function rather than copying it")

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
    ap.add_argument("--requeue", action="store_true",
                    help="requeue the actionable classes (seed-bug and "
                         "degraded-search to near, stale-tier to todo). "
                         "DRY RUN unless --apply is also given")
    ap.add_argument("--apply", action="store_true",
                    help="with --requeue, actually write through scheduler.py")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.apply and not a.requeue:
        print("--apply does nothing on its own; it modifies --requeue",
              file=sys.stderr)
        return 2
    return report(a.requeue_plan, do_requeue=a.requeue, apply=a.apply)


if __name__ == "__main__":
    raise SystemExit(main())
