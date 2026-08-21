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

  permuter-out  A scheduler-owned current-seed exhaustion verdict, or a legacy
                PERMUTER_EXHAUSTED note with a real score and no improvement.
                The permuter mutates expressions only, so this genuinely means
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
    python3 automation/deferred_triage.py --verdict-migration FILE [--apply]
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
# Legacy compatibility marker from permuter_supervisor.CURRENT_SEED. New
# reports carry scheduler-owned structured authority; historical notes still
# need this fallback when no search_verdict exists.
RX_CURRENT_SEED = re.compile(r"SEED_CURRENT")
RX_RESCUED = re.compile(r"RESCUED", re.I)
RX_CLEAN_RERUN = re.compile(
    r"\b[\d,]+\s+iterations?\b.*?\b0 errors\b", re.I | re.S)
RX_NOTE_SEPARATOR = re.compile(r"\s+\|\|\s+")

# What the hosted tiers will actually attempt. Kept in sync with
# worker_direct._DEFAULT_MAX_FUNC; a record is only "stale" if it is under it.
HOSTED_MAX_CHARS = 20000



_ASM_INDEX: dict | None = None


def _compact_asm():
    """worker_direct.compact_asm, imported rather than reimplemented.

    A second copy of that regex here would be free to drift from the one the
    worker actually runs, and the whole point of this function is to predict
    what the worker will do.
    """
    global _COMPACT
    if _COMPACT is None:
        sys.path.insert(0, str(REPO / "automation" / "win"))
        os.environ.setdefault("MODEL_BACKEND", "zen")
        import worker_direct as _wd
        _COMPACT = _wd.compact_asm
    return _COMPACT


_COMPACT = None


def asm_file_for(rec_id: str) -> Path | None:
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
            return f
    return None


def real_asm_chars(rec_id: str) -> int | None:
    """The size the SIZE GATE will see. Not the note's number, not the file's.

    Three different numbers get called "the asm size" and only one of them
    decides anything:

      the note      truncated. The deferral message reports len(ctx["asm"])
                    after MAX_ASM_CHARS clipped it, so eleven records all
                    claimed exactly "asm 12000 chars" -- a cap, not a
                    measurement.
      the .s file   raw. Every instruction line carries `/* 4B2DC 801CB2DC
                    C8FFBD27 */` plus alignment padding.
      THIS          len(compact_asm(file)), which is what prepare() computes
                    as asm_full and what worker_direct compares to
                    MAX_FUNC_CHARS.

    THIS FUNCTION RETURNED THE RAW FILE SIZE UNTIL 2026-08-10, and compact_asm
    strips a MEDIAN 62%. So every record was scored roughly 2.6x too large:
    func_us_801C2418 is 68865 on disk and 23761 to the gate. The docstring here
    concluded "nine of the twenty-five were genuinely over the hosted 20000
    ceiling" on those inflated numbers, and that conclusion is retracted --
    a raw 25000-char file compacts to about 9500 and the worker would attempt
    it without hesitating.

    The error was conservative in the worst direction: it held records back
    from a tier that would have taken them, which is the exact failure this
    module exists to detect.
    """
    f = asm_file_for(rec_id)
    if not f:
        return None
    try:
        return len(_compact_asm()(f.read_text(errors="ignore")))
    except OSError:
        return None


def raw_asm_chars(rec_id: str) -> int | None:
    """The .s file on disk. For the report only; nothing decides on this."""
    f = asm_file_for(rec_id)
    if not f:
        return None
    try:
        return f.stat().st_size
    except OSError:
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


RX_ZERO_BLOCKED = re.compile(r"scored 0 but does not compile", re.I)
RX_UNDECL_ERR = re.compile(r"`(\w+)'\s+undeclared")


def overlay_src_dir(rec_id: str) -> Path:
    """us:ST/RCHI:fn -> src/st/rchi. See matched_audit.overlay_dir."""
    parts = rec_id.split(":")
    return REPO / ("src/" + parts[1].lower() if len(parts) >= 3 else "src")


_DEF_CACHE: dict[tuple[str, str], str] = {}


def defines_in_own_overlay(symbol: str, rec_id: str) -> str:
    """`path:line` where THIS overlay defines `symbol`, or "".

    A DEFINITION, not a declaration, and only in the record's own overlay.
    Both halves matter and both were learned the hard way on EntityGaibonLeg:

      - Searching for `extern[^;]*g_EInitGaibon` finds src/st/nz0/nz0.h, a
        different overlay. EInit objects are overlay-local data, so borrowing
        NZ0's declaration would name a different object and the build would
        be wrong in a way the compiler cannot see.
      - The right answer, src/st/rchi/e_init.c:96, is a definition
        (`EInit g_EInitGaibon = {...}`) and matches no `extern` pattern at
        all, so a declaration-only search misses it entirely.
    """
    d = overlay_src_dir(rec_id)
    if not symbol or not d.is_dir():
        return ""
    key = (symbol, str(d))
    if key in _DEF_CACHE:
        return _DEF_CACHE[key]
    # A definition: the name at file scope followed by `=` or `[`, not
    # preceded by `extern`.
    rx = re.compile(rf"^(?!\s*extern\b)[A-Za-z_][\w \t*]*\b"
                    rf"{re.escape(symbol)}\s*(\[[^\]]*\])?\s*=")
    hit = ""
    for p in sorted(d.rglob("*.c")) + sorted(d.rglob("*.h")):
        try:
            for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
                if rx.match(line):
                    hit = f"{p.relative_to(REPO).as_posix()}:{i}"
                    break
        except OSError:
            continue
        if hit:
            break
    _DEF_CACHE[key] = hit
    return hit


def latest_verdict(note: str) -> str:
    """Newest search/handoff segment from keep_note's newest-first history."""
    parts = [part.strip() for part in RX_NOTE_SEPARATOR.split(note or "")
             if part.strip()]
    for part in parts:
        if RX_TOO_LARGE.search(part) or RX_EXHAUSTED.search(part):
            return part
    return parts[0] if parts else ""


def classify(note: str, asm_chars: int | None = None,
             seed_retrofitted: bool = False,
             rec_id: str = "") -> tuple[str, str]:
    """(class, action). Pure, so the self-test can pin every branch."""
    note = note or ""
    if not note.strip():
        return "no-note", "no note to assess; read the record"
    # queue_report(keep_note=True) prepends evidence and retains earlier
    # segments after ` || `. Searching the accumulated string lets an old
    # UNDECLARED SYMBOL override a newer SEED_CURRENT exhaustion. Classify the
    # first actual verdict because the history is newest-first.
    note = latest_verdict(note)

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
        # CHECKED FIRST, BECAUSE IT IS THE OPPOSITE OF A FAILURE.
        #
        # This note begins with the same token as 28 genuine exhaustions and
        # then says the search SUCCEEDED:
        #
        #   PERMUTER_EXHAUSTED: scored 0 but does not compile in its real
        #   file; needs declarations the permuter cannot add. COMPILE ERROR:
        #   `g_EInitGaibon' undeclared
        #
        # EntityGaibonLeg sat in deferred like that until 2026-08-10, and this
        # function called it `permuter-out: re-derive from the asm`, which is
        # exactly backwards: there was nothing to re-derive, the answer was
        # already in the work dir. One extern and a --land turned it into a
        # match with zero model calls.
        #
        # A record carrying a finished search must never share a bucket with
        # records that need one.
        if RX_ZERO_BLOCKED.search(note):
            sym = RX_UNDECL_ERR.search(note)
            name = sym.group(1) if sym else ""
            where = defines_in_own_overlay(name, rec_id) if name else ""
            if where:
                return ("zero-blocked",
                        f"THE PERMUTER ALREADY WON. Score 0; it only fails to "
                        f"compile because `{name}` is undeclared, and this "
                        f"overlay DEFINES it at {where}. Add `extern` for it, "
                        f"then permuter_supervisor --land. No model call")
            if name:
                return ("zero-blocked",
                        f"THE PERMUTER ALREADY WON. Score 0, blocked only on "
                        f"`{name}` being undeclared, but this overlay does "
                        f"not define it -- resolve it from this overlay's asm "
                        f"before landing, never by borrowing another "
                        f"overlay's copy")
            return ("zero-blocked",
                    "THE PERMUTER ALREADY WON. Score 0, blocked only on a "
                    "missing declaration the note does not name; read the "
                    "COMPILE ERROR, add it, then --land")

        m = RX_UNDECLARED.search(note)
        if m:
            return ("seed-bug",
                    f"the seed did not declare `{m.group(1)}`, so the "
                    f"permuter's typemap raised KeyError on part of the "
                    f"search. The seed is fixed; requeue as near")
        if (seed_retrofitted
                and not RX_CURRENT_SEED.search(note)
                and not RX_CLEAN_RERUN.search(note)):
            # THE NOTE WINS OVER THE SEED'S HISTORY.
            #
            # seed_retrofitted is permanent -- it says the seed was ONCE
            # missing declarations, not that this verdict is stale. Testing it
            # alone put 15 records in a loop on 2026-08-10: requeue as near,
            # permuter searches the fixed seed, genuinely exhausts, gets
            # deferred, and lands right back here. Each circuit cost a full
            # permuter run and learned nothing.
            #
            # permuter_supervisor now stamps SEED_CURRENT on every verdict it
            # writes, because it imports from automation/candidates/ when it
            # runs and so can only ever be judging the current seed. Present
            # means the search already happened post-fix and the exhaustion is
            # real.
            #
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


def classify_record(rec: dict, asm_chars: int | None = None,
                    seed_retrofitted: bool = False) -> tuple[str, str]:
    """Classify one complete queue record, preferring structured authority.

    Notes remain the human derivation history. They are not a reliable database
    column: historical reports predate SEED_CURRENT, and controlled searches can
    contain ordinary failed mutations even when the preserved seed compiled.
    The scheduler-owned search_verdict records the one fact triage needs without
    reconstructing it from those sentences.
    """
    verdict = rec.get("search_verdict")
    if (isinstance(verdict, dict)
            and verdict.get("kind") == "permuter-exhausted"
            and verdict.get("seed_current") is True):
        return ("permuter-out",
                "current preserved seed genuinely exhausted; re-derive from "
                "the asm")
    return classify(rec.get("note", ""), asm_chars, seed_retrofitted,
                    rec.get("id", ""))


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
         "list", "--status", "deferred", "--json"],
        capture_output=True, text=True, timeout=120, cwd=str(REPO))
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "scheduler list failed").strip())
    records = json.loads(r.stdout)
    if not isinstance(records, list):
        raise RuntimeError("scheduler list --json did not return an array")
    for rec in records:
        rec["note"] = rec.get("notes", "")
    return records


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


def bucket_records(recs: list[dict]) -> dict[str, list]:
    buckets: dict[str, list] = collections.defaultdict(list)
    for rec in recs:
        cls, action = classify_record(
            rec, real_asm_chars(rec["id"]),
            seed_was_retrofitted(rec["id"]))
        buckets[cls].append((rec, action))
    return buckets


def load_verdict_migration(path: str) -> tuple[Path, dict]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = REPO / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(REPO.resolve())
    except ValueError as exc:
        raise ValueError("verdict migration must be an in-repo file") from exc
    data = json.loads(candidate.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError("verdict migration schema must be 1")
    if data.get("kind") != "permuter-exhausted":
        raise ValueError("verdict migration kind must be permuter-exhausted")
    if data.get("seed_current") is not True:
        raise ValueError("verdict migration must assert seed_current=true")
    records = data.get("records")
    if not isinstance(records, dict) or not records:
        raise ValueError("verdict migration records must be a nonempty object")
    if any(not isinstance(rid, str) or not isinstance(source, str)
           or not rid.strip() or not source.strip()
           for rid, source in records.items()):
        raise ValueError("every verdict migration record needs an id and source")
    expected = data.get("expected_after")
    if not isinstance(expected, dict) or not expected:
        raise ValueError("verdict migration requires expected_after counts")
    return candidate, data


def migrate_verdicts(path: str, apply: bool = False) -> int:
    migration_path, migration = load_verdict_migration(path)
    live = load()
    by_id = {rec["id"]: rec for rec in live}
    targets = migration["records"]
    missing = sorted(set(targets) - set(by_id))
    if missing:
        print("migration records are not deferred in the live queue: "
              + ", ".join(missing), file=sys.stderr)
        return 1

    structured = {
        "kind": migration["kind"],
        "seed_current": True,
    }
    pending = []
    projected = []
    for rec in live:
        copy = dict(rec)
        if rec["id"] in targets:
            current = rec.get("search_verdict") or {}
            if (current.get("kind") == migration["kind"]
                    and current.get("seed_current") is True):
                pass
            else:
                cls, _ = classify_record(
                    rec, real_asm_chars(rec["id"]),
                    seed_was_retrofitted(rec["id"]))
                if cls != "degraded-search":
                    print(f"refused: {rec['id']} is {cls}, not degraded-search",
                          file=sys.stderr)
                    return 1
                pending.append(rec["id"])
            copy["search_verdict"] = structured
        projected.append(copy)

    projected_counts = collections.Counter(
        cls for cls, rows in bucket_records(projected).items()
        for _row in rows)
    expected = migration["expected_after"]
    mismatches = {
        key: (projected_counts.get(key, 0), value)
        for key, value in expected.items()
        if projected_counts.get(key, 0) != value
    }
    if mismatches:
        print(f"refused: projected live-pool counts differ: {mismatches}",
              file=sys.stderr)
        return 1

    print(f"verdict migration: {migration_path.relative_to(REPO)}")
    print(f"  {len(targets)} total, {len(pending)} pending")
    print("  projected " + "  ".join(
        f"{key}={projected_counts.get(key, 0)}" for key in expected))
    if not apply:
        for rid in pending:
            print(f"  would certify {rid}")
        print("dry run: re-run with --apply to write through scheduler.py")
        return 0

    failures = []
    for rid in pending:
        source = targets[rid]
        result = subprocess.run(
            [PYTHON, str(REPO / "automation" / "scheduler.py"), "report",
             "--id", rid, "--status", "deferred",
             "--verdict-kind", migration["kind"],
             "--verdict-seed-current", "--verdict-source", source],
            capture_output=True, text=True, timeout=120, cwd=str(REPO))
        if result.returncode != 0:
            failures.append((rid, (result.stderr or result.stdout).strip()))
        else:
            print(f"  certified {rid}")
    if failures:
        for rid, detail in failures:
            print(f"  FAILED {rid}: {detail}", file=sys.stderr)
        return 1

    actual = bucket_records(load())
    actual_counts = {key: len(actual.get(key, [])) for key in expected}
    if any(actual_counts[key] != expected[key] for key in expected):
        print(f"post-apply live-pool regression failed: {actual_counts}",
              file=sys.stderr)
        return 1
    print("  verified " + "  ".join(
        f"{key}={actual_counts[key]}" for key in expected))
    return 0


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
    buckets = bucket_records(recs)

    print(f"{len(recs)} deferred record(s)\n")
    # zero-blocked leads the order: it is a finished match, and burying it
    # under the classes that need work is how one stayed invisible.
    order = ["zero-blocked", "stale-tier", "seed-bug", "degraded-search",
             "no-note", "permuter-out", "too-large-still", "other"]
    for cls in order:
        if buckets.get(cls):
            print(f"  {cls:16} {len(buckets[cls])}")

    actionable = sum(len(buckets.get(c, [])) for c in REQUEUE_TO)
    print(f"\n{actionable} of {len(recs)} are deferred for a reason that no "
          f"longer holds, or for a mechanical fix.\n")

    # Loud, and above everything else. These are finished searches.
    # Deliberately NOT in REQUEUE_TO: requeueing one without first adding the
    # declaration sends it straight back through --land, which fails to
    # compile and re-defers it with the same note. The code edit comes first,
    # so this reports and does not act.
    if buckets.get("zero-blocked"):
        n = len(buckets["zero-blocked"])
        print("!" * 78)
        print(f"\n{n} record(s) HAVE ALREADY BEEN SOLVED and are sitting in "
              f"deferred.\nThe permuter scored 0; they only fail to compile. "
              f"Landing one costs a\ndeclaration and a build, and no model "
              f"call. Do these before anything else.\n")
        for r, action in buckets["zero-blocked"]:
            print(f"  {r['id']}\n      {action}")
        print("\n" + "!" * 78)

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

    print("\na finished-but-uncompilable search is NOT an exhaustion")
    # THE VERBATIM NOTE that hid EntityGaibonLeg in `deferred`. Before
    # 2026-08-10 this classified as permuter-out, "re-derive from the asm",
    # for a record whose answer was already sitting in its work dir at
    # score 0. One extern and a --land made it a match.
    real = ("PERMUTER_EXHAUSTED: scored 0 but does not compile in its real "
            "file; needs declarations the permuter cannot add. COMPILE "
            "ERROR: BUILD FAILED: 193:src/st/rchi/e_gaibon.c:12: "
            "`g_EInitGaibon' undeclared (first use this function) 194:src")
    cls_z, act_z = classify(real, None, False, "us:ST/RCHI:EntityGaibonLeg")
    ck(cls_z == "zero-blocked", f"classified zero-blocked ({cls_z})")
    ck(cls_z != "permuter-out",
       "and specifically NOT permuter-out, which said re-derive from the asm")
    ck("ALREADY WON" in act_z, "the action leads with the good news")
    ck("g_EInitGaibon" in act_z, "and names the blocking symbol")
    ck("no model call" in act_z.lower() or "--land" in act_z,
       "and says how to finish it")

    print("\nand it resolves the symbol in the record's OWN overlay")
    # The trap: `extern EInit g_EInitGaibon;` exists in src/st/nz0/nz0.h, a
    # different overlay. EInit data is overlay-local, so that declaration
    # names a different object. The real answer is a DEFINITION in
    # src/st/rchi/e_init.c and matches no extern pattern at all.
    where = defines_in_own_overlay("g_EInitGaibon", "us:ST/RCHI:EntityGaibonLeg")
    if (REPO / "src" / "st" / "rchi").is_dir():
        ck(where.startswith("src/st/rchi/"),
           f"found in RCHI, not borrowed from NZ0 ({where})")
        ck("nz0" not in where, "and nz0 is not consulted at all")
        ck(defines_in_own_overlay("g_EInitGaibon",
                                  "us:ST/RNO0:whatever") == "",
           "a different overlay does not get RCHI's definition")
    ck(defines_in_own_overlay("", "us:ST/RCHI:x") == "",
       "an empty symbol resolves to nothing rather than matching everything")
    ck(defines_in_own_overlay("no_such_symbol_xyz",
                              "us:ST/RCHI:x") == "",
       "and an absent symbol is not invented")

    print("\nzero-blocked is reported but never auto-requeued")
    # Requeueing without the declaration sends it back through --land, which
    # fails to compile and re-defers it with the same note. Code edit first.
    ck("zero-blocked" not in REQUEUE_TO,
       "it is not in the requeue table")
    ck(src_self.index('"zero-blocked", "stale-tier"')
       < src_self.index('"permuter-out", "too-large-still"'),
       "and it is printed before the classes that need work")

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

    print("\nbut ONCE THE PERMUTER HAS RE-RUN, the verdict is trustworthy again")
    # THE LOOP THIS CLOSES. seed_retrofitted is permanent -- it says the seed
    # was ONCE missing declarations, not that this verdict is stale. Testing it
    # alone meant every future exhaustion was untrustworthy forever:
    #
    #   requeue as near -> permuter searches the FIXED seed -> genuinely
    #   exhausts -> deferred -> "seed was retrofitted, requeue" -> ...
    #
    # 15 records went round that on 2026-08-10, one full permuter run each,
    # learning nothing. The supervisor stamps SEED_CURRENT because it imports
    # from automation/candidates/ when it runs and so cannot be judging a
    # stale seed.
    fresh = ("PERMUTER_EXHAUSTED SEED_CURRENT: best 1770 after 2701 "
             "iterations, 3 promotion(s), no improvement for 2662.")
    cls_f, act_f = classify(fresh, None, True)
    ck(cls_f == "permuter-out",
       f"a stamped verdict is permuter-out even with the retrofit marker "
       f"({cls_f})")
    ck("re-derive" in act_f, "and the action says re-derive, not requeue")
    ck(classify(fresh, None, False)[0] == "permuter-out",
       "and the stamp changes nothing when the seed was never retrofitted")

    print("\nnewest search evidence overrides older retained failures")
    retained = (
        fresh
        + " || Recovered and repaired seed evidence; older proof retained."
        + " || PERMUTER_EXHAUSTED: UNDECLARED SYMBOL: the seed calls "
          "BO6_RicCheckFacing without declaring it.")
    cls_new, _ = classify(retained, None, True)
    ck(cls_new == "permuter-out",
       f"a current exhaustion is not clipped by an older seed bug ({cls_new})")

    targeted = (
        "Seed declaration audit repaired the current whole-file seed."
        " || PERMUTER_EXHAUSTED targeted rerun after parser and scorer "
        "repairs. The immutable seed imports cleanly. A search ran 8,980 "
        "iterations with 0 errors and never improved below 60."
        " || Earlier pre-repair derivation evidence retained.")
    cls_targeted, _ = classify(targeted, None, True)
    ck(cls_targeted == "permuter-out",
       f"a clean targeted rerun is authoritative despite seed history "
       f"({cls_targeted})")

    print("\nstructured verdict authority overrides ambiguous historical prose")
    structured = {
        "id": "us:BOSS/BO0:func_us_801B15BC",
        "note": clean,
        "search_verdict": {
            "kind": "permuter-exhausted",
            "seed_current": True,
            "source": "test receipt",
        },
    }
    cls_structured, _ = classify_record(
        structured, None, seed_retrofitted=True)
    ck(cls_structured == "permuter-out",
       f"structured current-seed exhaustion wins ({cls_structured})")
    structured["search_verdict"]["seed_current"] = False
    cls_untrusted, _ = classify_record(
        structured, None, seed_retrofitted=True)
    ck(cls_untrusted == "degraded-search",
       f"an untrusted structured record does not waive the repair ({cls_untrusted})")

    print("\nthe tracked verdict migration pins the live #98 correction")
    migration_file = (
        "automation/queue/migrations/2026-08-21-permuter-verdicts.json")
    _migration_path, migration = load_verdict_migration(migration_file)
    migration_ids = set(migration["records"])
    ck(len(migration_ids) == 19,
       f"all 19 proven post-repair exhaustions are listed ({len(migration_ids)})")
    ck("us:ST/RNO0:func_801CD78C_801CEB40" not in migration_ids,
       "the genuinely degraded RNO0 record is not certified")
    ck("us:BOSS/BO6:func_us_801B8E80" not in migration_ids,
       "the genuinely degraded BO6 record is not certified")
    ck(migration["expected_after"] == {
        "permuter-out": 33, "degraded-search": 2},
       "the migration carries the live-pool acceptance counts")

    print("\nthe two modules agree on the token, which is why this works")
    # Same failure mode as scheduler.py's `set` subcommand that never existed:
    # one module writing a marker the other never looks for. Read the
    # supervisor rather than trusting that both copies say SEED_CURRENT.
    sup_src = (REPO / "automation" / "permuter_supervisor.py").read_text(
        encoding="utf-8", errors="replace")
    ck('CURRENT_SEED = "SEED_CURRENT"' in sup_src,
       "the supervisor defines the token this module greps for")
    ck(sup_src.count(f"{{EXHAUSTED}} {{CURRENT_SEED}}") >= 2,
       "and stamps it on the exhausted verdicts it writes (retire and cap)")

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


def sizes_report() -> int:
    """Every TIER_HANDOFF record, measured three ways. Read-only.

    WHY: on 2026-08-10 I told Kenichi the nine remaining handoff records would
    take the m2c-only path, cost nothing and finish in 25 seconds each. I had
    read their notes -- "asm 12000 chars > 6000 on backend=http" -- and never
    checked. 12000 is MAX_ASM_CHARS, a cap, and the 6000 was the ceiling of a
    tier that no longer exists. The first record I ran spent ten minutes of
    model time before being cancelled.

    Printing the three numbers side by side is the whole fix: the note's claim,
    the file on disk, and what the gate will actually compare.
    """
    # `note`, singular: that is the key load() builds. Spelling it `notes`
    # here matched nothing and printed a confident "no TIER_HANDOFF_TOO_LARGE
    # records" against a queue holding eleven of them -- the same shape of
    # wrong answer this whole report exists to prevent.
    recs = [r for r in load()
            if RX_TOO_LARGE.search(r.get("note") or "")]
    if not recs:
        print("no TIER_HANDOFF_TOO_LARGE records")
        return 0
    rows = []
    for r in recs:
        note_n = RX_ASM_CHARS.search(r.get("note") or "")
        rows.append((r["id"],
                     int(note_n.group(1)) if note_n else None,
                     raw_asm_chars(r["id"]),
                     real_asm_chars(r["id"])))
    rows.sort(key=lambda t: -(t[3] or 0))

    print(f"\nTIER_HANDOFF_TOO_LARGE: {len(rows)} record(s). "
          f"Gate ceiling is MAX_FUNC_CHARS={HOSTED_MAX_CHARS} on zen.\n")
    print(f"  {'note':>7}  {'.s file':>8}  {'TO GATE':>8}  path      record")
    print("  " + "-" * 92)
    over = under = unknown = 0
    for rid, note_n, raw, gate in rows:
        if gate is None:
            path, unknown = "?", unknown + 1
        elif gate > HOSTED_MAX_CHARS:
            path, over = "m2c-only", over + 1
        else:
            path, under = "MODEL", under + 1
        print(f"  {note_n if note_n is not None else '-':>7}  "
              f"{raw if raw is not None else '-':>8}  "
              f"{gate if gate is not None else '-':>8}  "
              f"{path:<9} {rid}")
    print()
    print(f"  {over} over the ceiling: m2c-only, no model call, ~25s each.")
    print(f"  {under} UNDER it: these are ordinary model work now, not a size "
          f"problem. Minutes each, and they spend quota.")
    if unknown:
        print(f"  {unknown} with no .s file found; check the name.")
    print("\n  `note` is truncated by MAX_ASM_CHARS and decides nothing.")
    print("  `.s file` is raw; compact_asm strips a median 62% before the "
          "gate sees it.")
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
    ap.add_argument("--sizes", action="store_true",
                    help="measure every TIER_HANDOFF record against the real "
                         "gate ceiling and say which path it would take. "
                         "Read-only; run it BEFORE planning any batch")
    ap.add_argument("--verdict-migration", metavar="PATH",
                    help="validate and apply a tracked structured-verdict migration; "
                         "dry run unless --apply is also given")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.sizes:
        return sizes_report()
    if a.verdict_migration:
        if a.requeue or a.requeue_plan:
            print("--verdict-migration cannot be combined with requeue modes",
                  file=sys.stderr)
            return 2
        return migrate_verdicts(a.verdict_migration, apply=a.apply)
    if a.apply and not a.requeue:
        print("--apply does nothing on its own; it modifies --requeue or "
              "--verdict-migration",
              file=sys.stderr)
        return 2
    return report(a.requeue_plan, do_requeue=a.requeue, apply=a.apply)


if __name__ == "__main__":
    raise SystemExit(main())
