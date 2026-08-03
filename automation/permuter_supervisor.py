#!/usr/bin/env python3
"""Run the permuter across every candidate that deserves it, then stop.

WHAT IT REPLACES
    Hand-driven permuting, which on 2026-08-03 looked like this: start jobs,
    poll them, read a tail by eye, get the score wrong, promote by hand,
    restart by hand, and leave four jobs running for half an hour after
    reporting them cancelled. Two matches came out of that day and both needed
    a human in the loop for every cycle.

    The cycle that produced those matches is mechanical:

        pick candidates -> drop phantoms -> run N at once
          -> when one improves, promote its seed and restart it
          -> when one stalls, retire it
          -> when one hits zero, bank it and stop that slot
        -> exit when nothing is left

    That is what this does. It does NOT apply matches to the tree or build:
    a permuter zero is necessary but not sufficient (see the frame bug in
    src/boss/bo6/us_39144.c), so landing a match stays a human decision.

WHY IT SELF-TERMINATES
    The permuter never exits on its own. Every previous run had to be killed,
    and the two that were not killed burned a core for 170,002 and 141,409
    iterations respectively, long after their last improvement at iteration
    5,701. Exiting when the work is done is the point of the whole thing.

CANDIDATE SELECTION
    From the live queue (scheduler.py), status `near` by default: those are
    records that COMPILED and produced wrong bytes, which is exactly the
    precondition the permuter needs. `todo` records have no compiling C at all
    and are not permuter work.

    Every candidate is then checked against the tree. A work dir whose function
    is already defined in src/ with no INCLUDE_ASM is a phantom and is dropped:
    four of nine work dirs were phantoms when this was written, and one of them
    reported score 10 while being long since matched and shipped.

Usage:
    python3 automation/permuter_supervisor.py --plan          # show, run nothing
    python3 automation/permuter_supervisor.py --run
    python3 automation/permuter_supervisor.py --run --slots 3 --threads 4
    python3 automation/permuter_supervisor.py --status        # one JSON blob
    python3 automation/permuter_supervisor.py --stop          # cancel everything
    python3 automation/permuter_supervisor.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(os.environ.get("SOTN_REPO", Path(__file__).resolve().parents[1]))
QUEUE = Path(os.environ.get(
    "SOTN_QUEUE", os.path.expanduser("~/sotn-work/queue.jsonl")))
WORKROOT = REPO / "nonmatchings"
STATE = Path(os.path.expanduser("~/sotn-work/supervisor.json"))
# Written by dashboard.py when it launches us detached. Exposed via --log
# because a detached supervisor that fails leaves no other trace: the caller
# sees "started" and the permuter column sees no jobs, with the reason in a
# file nothing reads.
LOG = Path(os.path.expanduser("~/sotn-work/supervisor.log"))
# One line per live supervisor. --stop reads it to kill the LOOP, not just the
# jobs the loop happens to have started right now.
PIDS = Path(os.path.expanduser("~/sotn-work/supervisor.pids"))
PYTHON = os.environ.get("SOTN_PYTHON", sys.executable)
# Propagate, so permuter jobs started via commands_client use this interpreter
# rather than falling back to a bare "python3" without pycparser.
os.environ.setdefault("SOTN_PYTHON", PYTHON)

sys.path.insert(0, str(REPO / "automation"))
sys.path.insert(0, str(REPO / "automation" / "mcp"))

# Defaults chosen from measurement, not taste:
#   slots 3   -- four concurrent jobs at 4 threads saturated the machine while a
#                build also wanted cores. Three leaves headroom for make_build,
#                which is exclusive and must not be starved.
#   threads 4 -- the permuter defaults to ONE. Every run before 2026-08-03 was
#                single-threaded.
#   stall 2500 -- past the last improvement seen in any observed run (6,810 was
#                the latest, but that run had improved steadily up to it).
#   cycles 4  -- promote-and-restart this many times before giving up on a seed.
#                801C488C needed two promotions; nothing has needed four.
DEF_SLOTS = 3
DEF_THREADS = 4
DEF_STALL = 2500
DEF_CYCLES = 4
# Hard ceiling per job. There was NO such cap before, which is why a run reached
# 170,002 iterations: the stall check was the only brake and it was broken (see
# read_log). A cap is a second, independent brake that does not depend on
# parsing anything correctly -- the one number the supervisor can always trust
# is how far the run has gone.
DEF_MAX_ITERS = 50000
POLL_S = 20


# ----------------------------------------------------------------- candidates

def load_queue() -> list[dict]:
    if not QUEUE.is_file():
        return []
    out = []
    for line in QUEUE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def workdir_for(fn: str) -> Path | None:
    """The nonmatchings/ dir for `fn`, tolerating the -2 disambiguator.

    permuter_import appends -2, -3 when a name repeats, so the dir name is not
    always the function name. Matching on the prefix rather than assuming
    equality is what lets func_us_8019AA04-2 be found at all.
    """
    exact = WORKROOT / fn
    if exact.is_dir():
        return exact
    if not WORKROOT.is_dir():
        return None
    for p in sorted(WORKROOT.iterdir()):
        if p.is_dir() and re.fullmatch(rf"{re.escape(fn)}(-\d+)?", p.name):
            return p
    return None


def best_score(work: Path) -> int | None:
    """Lowest score this work dir has ever produced."""
    best = None
    for d in work.iterdir():
        m = re.fullmatch(r"output-(\d+)-\d+", d.name) if d.is_dir() else None
        if m and (d / "source.c").is_file():
            s = int(m.group(1))
            if best is None or s < best:
                best = s
    return best


def _why_skip(rec: dict, work) -> str:
    """Reasons not to spend a slot on this record."""
    notes = rec.get("notes", "") or ""
    if MATCH_PENDING in notes:
        # Already solved by an earlier run and waiting on a human build.
        # Re-searching it would burn a slot on finished work.
        return "permuter already scored 0; apply it and build"
    if not work:
        return "no work dir; will import from seed"
    return ""


def candidates(statuses: tuple[str, ...] = ("near",),
               check_tree: bool = True) -> list[dict]:
    """Queue records worth permuting, best-scoring first.

    check_tree is a parameter only so the self-test can exercise ordering
    without paying for a full src/ scan. Real runs always check.
    """
    try:
        from permuter_stall import workdir_state
    except ImportError:                                   # pragma: no cover
        workdir_state = None

    out = []
    for rec in load_queue():
        if rec.get("status") not in statuses:
            continue
        fn = rec.get("function", "")
        if not fn:
            continue
        work = workdir_for(fn)
        state = "stub"
        where = ""
        if check_tree and workdir_state is not None:
            state, where = workdir_state(fn)
        if state == "phantom":
            out.append({"function": fn, "id": rec.get("id", ""),
                        "workdir": str(work) if work else "",
                        "score": None, "skip": f"phantom, defined at {where}"})
            continue
        out.append({
            "function": fn,
            "id": rec.get("id", ""),
            "workdir": str(work) if work else "",
            "score": best_score(work) if work else None,
            "seed": seed_from_notes(rec.get("notes", "")),
            "notes": rec.get("notes", "") or "",
            # A record with no work dir is not dropped: --run imports one from
            # the seed named in its notes. --plan still reports it as blocked,
            # because planning must not write to src/.
            "skip": _why_skip(rec, work),
        })

    runnable = [c for c in out if not c["skip"]]
    blocked = [c for c in out if c["skip"]]
    # Unscored dirs sort last: a dir with no output yet is an unknown, and an
    # unknown should not outrank a seed measured at 70.
    runnable.sort(key=lambda c: (c["score"] is None, c["score"] or 0))
    return runnable + blocked


# ---------------------------------------------------------------------- jobs

# Queue statuses the permuter can actually consume.
#
# The permuter mutates an EXISTING, COMPILING function. `near` records compiled
# and produced wrong bytes, which is exactly that precondition. A `todo` record
# has no C at all, so pointing the supervisor at `todo` would import nothing,
# find nothing, and burn a slot per record discovering it. Refusing is better
# than a flag that silently does nothing useful.
USABLE_STATUSES = {"near", "escalated"}


def check_statuses(statuses: tuple[str, ...]) -> str:
    bad = [s for s in statuses if s not in USABLE_STATUSES]
    if not bad:
        return ""
    return (f"refusing status(es) {', '.join(bad)}: the permuter needs a "
            f"function that already compiles, so only "
            f"{'/'.join(sorted(USABLE_STATUSES))} records are usable. "
            f"A 'todo' record has no C to mutate.")


def seed_from_notes(notes: str) -> str:
    """The `seed=...` path a worker recorded when it filed a near miss."""
    m = re.search(r"seed=(\S+\.c)", notes or "")
    return m.group(1) if m else ""


def import_workdir(fn: str, seed_rel: str) -> tuple[Path | None, str]:
    """Create a permuter work dir for `fn` by staging its seed into src/.

    permuter_import compiles the file it is given, so the function has to be
    real C in its real source file with its real includes. The seed on disk is
    only a body. This stages the body over the INCLUDE_ASM stub, imports, and
    then puts the file back.

    The restore is in a finally and reads from an in-memory copy taken before
    any write, so an exception, a failed import or a crash mid-import all leave
    the tree exactly as found. That matters more than the feature: this is the
    only part of the harness that edits src/ without a human looking at it.

    Also note this is the ONLY path that picks up [preserve_macros] from
    config/permuter_settings.toml, because macro preservation happens at import
    and nowhere else. Existing work dirs cannot gain it without re-importing,
    which would discard their promoted seeds.
    """
    seed = REPO / seed_rel
    if not seed.is_file():
        return None, f"seed not found: {seed_rel}"

    # Whitespace-tolerant on BOTH sides of the opening paren and the comma.
    # clang-format wraps a stub whose name is long enough:
    #
    #     INCLUDE_ASM(
    #         "boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnStopwatchCircle);
    #
    # A regex requiring `INCLUDE_ASM("` adjacent never matched those, so the
    # importer reported "no INCLUDE_ASM stub in src/" for a stub that is plainly
    # there. Six stubs were invisible this way, all in src/boss/bo6/us_3E79C.c
    # and all with names long enough to trigger the wrap -- which is why the
    # affected set looked arbitrary rather than like a formatting artefact.
    stub = re.compile(
        rf'INCLUDE_ASM\(\s*"([^"]+)"\s*,\s*{re.escape(fn)}\s*\)\s*;')
    target = None
    for p in (REPO / "src").rglob("*.c"):
        text = p.read_text(errors="ignore")
        m = stub.search(text)
        if m:
            target = (p, text, m)
            break
    if target is None:
        return None, f"no INCLUDE_ASM stub for {fn} in src/"

    path, original, m = target
    asm_rel = m.group(1)
    body = seed.read_text(errors="ignore")
    # Strip any banner the candidate saver added; it is prose, not C.
    body = "\n".join(l for l in body.splitlines()
                     if not l.startswith("// ==="))

    import commands_client as cc
    try:
        path.write_text(original[:m.start()] + body + original[m.end():])
        r = cc.run("permuter_import", timeout=300,
                   c_file=str(path.relative_to(REPO)),
                   asm_file=f"asm/us/{asm_rel}/{fn}.s")
        ok = r.get("returncode") == 0
        detail = (r.get("stdout") or r.get("stderr") or "")[-300:]
    except Exception as e:                                # noqa: BLE001
        ok, detail = False, f"{type(e).__name__}: {e}"
    finally:
        # Unconditional. The tree must look untouched whatever happened above.
        path.write_text(original)

    work = workdir_for(fn)
    if work is None:
        return None, f"import did not produce a work dir: {detail}"
    return work, ("imported" if ok else f"imported with warnings: {detail}")


# Notes markers. Same pattern as worker_direct's DEFER_TOO_LARGE: the status
# says "not now", the marker says WHY and makes the class findable later with a
# grep. Without one, a deferred record is indistinguishable from every other
# deferred record and nobody can ever undo the decision selectively.
EXHAUSTED = "PERMUTER_EXHAUSTED"
MATCH_PENDING = "PERMUTER_MATCH_PENDING_BUILD"


def report(fn_id: str, status: str, notes: str) -> str:
    """Record an outcome through scheduler.py, the single queue writer.

    The supervisor did not write to the queue at all before, which meant a
    function it had just retired stayed `near` and was picked again by the very
    next plan. The loop could not terminate: three candidates, killed and
    re-selected forever.
    """
    if not fn_id:
        return "no record id"
    r = subprocess.run(
        [PYTHON, str(REPO / "automation" / "scheduler.py"), "report",
         "--id", fn_id, "--status", status, "--notes", notes[:250]],
        cwd=str(REPO), capture_output=True, text=True, timeout=60)
    return (r.stdout or r.stderr).strip()


def _jobs():
    import jobs
    return jobs


def start_one(work: Path, threads: int) -> str:
    """Promote to the best known seed, THEN start.

    permuter.py only ever reads base.c, so a run begins wherever base.c happens
    to be. Promotion used to happen only on stall or on a match, which meant a
    fresh start could begin from a seed WORSE than one already sitting in the
    work dir:

      BO6_AguneaShuffleParams  output-10-1 on disk, base.c never promoted
                               -> every restart threw the 10 away
      func_us_8019AA04-2       output-885 on disk, base.c promoted at 1100
                               -> searching from a seed 215 points worse

    Both look like the score going backwards, and effectively it is: the work
    was not lost from disk, but every restart discarded it. Promoting here makes
    a run monotonic by construction -- it can never start from worse than the
    best output the dir has ever produced.
    """
    msg = promote(work)
    if msg.startswith("promoted"):
        print(f"[seed] {msg}")
    import commands_client as cc
    r = cc.start_job("permuter", work_dir=str(work.relative_to(REPO)),
                     threads=threads)
    return r.get("job_id", "")


def promote(work: Path) -> str:
    r = subprocess.run([PYTHON, str(REPO / "automation" / "permuter_promote.py"),
                        "--dir", str(work.relative_to(REPO))],
                       capture_output=True, text=True, cwd=str(REPO))
    return (r.stdout or r.stderr).strip()


JOBS_DIR = Path(os.path.expanduser(
    os.environ.get("SOTN_JOBS_DIR", "~/sotn-work/jobs")))


def read_log(job_id: str) -> dict:
    """Parse a job's log, whether or not the job has finished.

    The log path is CONSTRUCTED, not read out of jobs.status(). status() only
    includes a "log" key once the job is done (jobs.py, the state == "done"
    branch); a running job's response has no such key. read_log used to do
    st.get("log", ""), so for every RUNNING job it got "", found no file, and
    returned the zero fallback -- since_improvement = 0, forever.

    The effect was that the supervisor could never see a stall on a live job.
    It never cycled, never promoted, never retired, and only ever reacted when
    a job ended by itself. Two jobs sat stalled for 20,907 and 32,059
    iterations with the supervisor polling them every 20 seconds and reading
    zeros each time.

    The dashboard had it right all along -- it builds JOBS_DIR / f"{jid}.log"
    directly, which is why its panels showed live scores the supervisor was
    blind to. That disagreement was the evidence.
    """
    from permuter_stall import parse
    jobs = _jobs()
    st = jobs.status(job_id, wait_s=0, tail_lines=1)
    log = Path(st.get("log") or (JOBS_DIR / f"{job_id}.log"))
    if not log.is_file():
        return {"state": st.get("state", "?"), "best": None,
                "iterations": 0, "since_improvement": 0, "failures": 0}
    d = parse(log.read_text(errors="ignore"))
    d["state"] = st.get("state", "?")
    return d


# ----------------------------------------------------------------- the loop

def already_busy() -> list[str]:
    """Work dirs that a permuter job is ALREADY searching.

    Starting a second supervisor while one is running used to spawn duplicate
    jobs on the same work dirs. Both then write output-* into the same
    directory and promote the same base.c underneath each other, and the
    duplicates die almost immediately -- which from the UI looks exactly like
    "the start button did nothing".

    Observed 2026-08-03: pressing start while supervisor pid 6941 was running
    produced permuter-143902-* jobs that went straight to state 'done'.
    """
    jobs = _jobs()
    busy = []
    for jid in jobs.running_jobs("permuter"):
        # Job ids are <action>-<hhmmss>-<pid>-<workdir slug>, and running_jobs
        # returns the WHOLE id including the action prefix. Splitting on 2
        # instead of 3 yields "6941-func_us_8019AA04-2" -- a string that never
        # equals a work dir name, so the guard silently matched nothing and the
        # supervisor started duplicates anyway. Off-by-one in a field index
        # fails exactly like having no guard at all.
        parts = jid.split("-", 3)
        if len(parts) == 4:
            busy.append(parts[3])
    return busy


def supervise(slots: int, threads: int, stall: int, cycles: int,
              statuses: tuple[str, ...], once: bool = False,
              max_iters: int = DEF_MAX_ITERS) -> int:
    jobs = _jobs()
    _register_pid()
    _CFG.update({"stall": stall, "slots": slots, "threads": threads,
                 "cycles": cycles, "max_iters": max_iters})
    all_c = candidates(statuses)
    busy = already_busy()
    for c in all_c:
        slug = Path(c["workdir"]).name if c["workdir"] else ""
        if slug and slug in busy:
            c["skip"] = (f"already being permuted by a running job; "
                         f"stop it first (run-permuter stop)")
    pending = [c for c in all_c if not c["skip"]]

    # Import anything that only lacks a work dir. Done here and not in
    # candidates() because this writes to src/ (transiently) and --plan must
    # stay read-only.
    for c in all_c:
        if not c["skip"].startswith("no work dir"):
            continue
        if not c["seed"]:
            print(f"[skip] {c['function']}: no seed= in its queue notes")
            continue
        work, msg = import_workdir(c["function"], c["seed"])
        print(f"[import] {c['function']}: {msg}")
        if work is not None:
            pending.append({**c, "workdir": str(work),
                            "score": best_score(work), "skip": ""})

    pending.sort(key=lambda c: (c["score"] is None, c["score"] or 0))
    if not pending:
        blocked = [c for c in all_c if "already being permuted" in c["skip"]]
        if blocked:
            print(f"NOTHING STARTED: all {len(blocked)} candidate(s) are "
                  f"already being permuted by jobs that are still running:")
            for c in blocked:
                print(f"  {c['function']}")
            print("Run `run-permuter stop` first, or let the existing "
                  "supervisor finish. Starting a second one would duplicate "
                  "jobs on the same work dirs and both would fail.")
            return 1
        print("nothing to permute; every candidate is matched, phantom, or "
              "has no work dir")
        for c in all_c:
            print(f"  {c['function']}: {c['skip']}")
        return 0

    print(f"{len(pending)} candidate(s), {slots} slot(s), {threads} threads each")
    for c in pending:
        print(f"  {c['function']:34s} best {c['score']}")

    active: dict[str, dict] = {}          # job_id -> slot record
    done: list[dict] = []

    while pending or active:
        while pending and len(active) < slots:
            c = pending.pop(0)
            work = Path(c["workdir"])
            jid = start_one(work, threads)
            if not jid:
                c["skip"] = "failed to start"
                done.append(c)
                continue
            active[jid] = {**c, "job": jid, "cycles": 0,
                           "started": time.time()}
            print(f"[start] {c['function']} -> {jid}")

        if not active:
            break

        _write_state(active, done)
        if once:
            break
        time.sleep(POLL_S)

        for jid, slot in list(active.items()):
            d = read_log(jid)
            fn = slot["function"]
            work = Path(slot["workdir"])

            if d["best"] == 0:
                jobs.cancel(jid)
                promote(work)
                slot["result"] = "MATCH"
                slot["best"] = 0
                print(f"[MATCH] {fn} scored 0. Output in {work}/output-0-1. "
                      f"Apply it and BUILD before believing it.")
                # Stays `near`, because it is NOT matched until a build says so
                # and only a human does that. The marker stops the next plan
                # from spending a slot re-searching a function that is already
                # solved and merely waiting to be applied.
                print("  queue: " + report(
                    slot.get("id", ""), "near",
                    f"{MATCH_PENDING}: permuter scored 0. Output at "
                    f"{work}/output-0-1/source.c. Apply it and run make_build; "
                    f"a permuter zero is necessary but not sufficient."))
                done.append(slot)
                del active[jid]
                continue

            if d["state"] not in ("running",):
                slot["result"] = f"job ended ({d['state']}), best {d['best']}"
                done.append(slot)
                del active[jid]
                continue

            if d["iterations"] >= max_iters:
                jobs.cancel(jid)
                promote(work)
                slot["result"] = (f"hit the {max_iters}-iteration cap at "
                                  f"best {d['best']}")
                print(f"[cap] {fn}: {slot['result']}. Best output is promoted "
                      f"and kept; re-derive from the asm to go further.")
                print("  queue: " + report(
                    slot.get("id", ""), "deferred",
                    f"{EXHAUSTED}: hit the {max_iters}-iteration cap at best "
                    f"{d['best']}. Seed is promoted; re-derive from the asm, "
                    f"then set this back to near."))
                done.append(slot)
                del active[jid]
                continue

            if d["since_improvement"] >= stall and d["iterations"] > stall:
                jobs.cancel(jid)
                msg = promote(work)
                improved = msg.startswith("promoted")
                if improved and slot["cycles"] + 1 < cycles:
                    slot["cycles"] += 1
                    # start_one promotes again; that is a no-op here because we
                    # just promoted, and promote() refuses a non-improvement.
                    njid = start_one(work, threads)
                    print(f"[cycle {slot['cycles']}] {fn} stalled at "
                          f"{d['best']}; {msg} -> {njid}")
                    del active[jid]
                    if njid:
                        active[njid] = {**slot, "job": njid}
                    continue
                slot["result"] = (
                    f"retired at {d['best']} after {slot['cycles']} promotion(s)"
                    + ("" if improved else "; no better output to promote"))
                print(f"[retire] {fn}: {slot['result']}. The permuter mutates "
                      f"expressions only, so re-derive this one from the asm.")
                print("  queue: " + report(
                    slot.get("id", ""), "deferred",
                    f"{EXHAUSTED}: best {d['best']} after {d['iterations']} "
                    f"iterations, {slot['cycles']} promotion(s), no improvement "
                    f"for {d['since_improvement']}. The permuter mutates "
                    f"expressions only; re-derive from the asm, then set this "
                    f"back to near."))
                done.append(slot)
                del active[jid]

    _write_state({}, done)
    _unregister_pid()
    print("\n--- supervisor finished ---")
    matches = [d for d in done if d.get("result") == "MATCH"]
    for d in done:
        print(f"  {d['function']:34s} {d.get('result', d.get('skip', '?'))}")
    print(f"\n{len(matches)} match(es). Nothing was applied to the tree.")
    return 0


_CFG: dict = {}


def _write_state(active: dict, done: list) -> None:
    """Publish state for the dashboard. Best effort: never kill the run."""
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps({
            "updated": time.time(),
            # Published so the dashboard can label "stalled" using the SAME
            # threshold this loop acts on. Two definitions of stalled is how a
            # job ends up badged stalled with nothing happening to it.
            **_CFG,
            "active": [{"function": s["function"], "job": s["job"],
                        "cycles": s["cycles"], "workdir": s["workdir"]}
                       for s in active.values()],
            "done": [{"function": d["function"],
                      "result": d.get("result", d.get("skip", ""))}
                     for d in done],
        }, indent=2))
    except OSError:
        pass


def _register_pid() -> None:
    """Record this supervisor so --stop can find it."""
    try:
        PIDS.parent.mkdir(parents=True, exist_ok=True)
        with open(PIDS, "a") as f:
            f.write(f"{os.getpid()}\n")
    except OSError:
        pass


def _unregister_pid() -> None:
    try:
        live = [l for l in PIDS.read_text().split()
                if l.strip().isdigit() and int(l) != os.getpid()]
        PIDS.write_text("\n".join(live) + ("\n" if live else ""))
    except OSError:
        pass


def _supervisor_pids() -> list[int]:
    """Live supervisor processes, by pid, cross-checked against /proc.

    The cmdline check keeps a recycled pid from being killed. Same reasoning as
    commands_client's worker check: a pid file alone is a claim, not evidence.
    """
    cands: set[int] = set()
    try:
        cands |= {int(t) for t in PIDS.read_text().split() if t.isdigit()}
    except OSError:
        pass

    # ALSO scan /proc. The pidfile only knows about supervisors started after
    # it was introduced, so relying on it alone reported "0 supervisor(s)
    # stopped" while two were plainly running and restarting their jobs. A
    # registry is a convenience; the process table is the truth.
    try:
        for d in Path("/proc").iterdir():
            if d.name.isdigit():
                cands.add(int(d.name))
    except OSError:
        pass

    out = []
    for pid in sorted(cands):
        if pid == os.getpid():
            continue
        try:
            cmd = (Path("/proc") / str(pid) / "cmdline").read_bytes()
        except OSError:
            continue
        # Must be a supervisor RUN, not a --stop or --plan invocation, or a
        # `run-permuter stop` would kill itself mid-stop.
        if b"permuter_supervisor.py" in cmd and b"--run" in cmd:
            out.append(pid)
    return out


def stop_all() -> int:
    """Stop the supervisor LOOP first, then its jobs.

    Order matters and getting it wrong is why "stop" did not stop. Cancelling
    only the jobs left the loop alive; it polled, saw them ended, and promoted
    and restarted them. From the UI that looks like a permuter that refuses to
    stop and a start button that does nothing, because the work dirs are still
    busy so a NEW supervisor correctly declines to touch them.

    Killing the loop before the jobs also avoids the race where the loop
    launches a replacement between our cancel and our exit.
    """
    import signal as _sig
    killed = 0
    for pid in _supervisor_pids():
        try:
            os.kill(pid, _sig.SIGTERM)
            print(f"stopped supervisor pid {pid}")
            killed += 1
        except OSError as e:
            print(f"could not stop supervisor pid {pid}: {e}")
    if killed:
        time.sleep(1.0)          # let it die before we cancel its children

    jobs = _jobs()
    n = 0
    for jid in jobs.running_jobs("permuter"):
        jobs.cancel(jid)
        print(f"cancelled {jid}")
        n += 1
    try:
        PIDS.write_text("")
    except OSError:
        pass
    _write_state({}, [])
    print(f"{killed} supervisor(s) stopped, {n} permuter job(s) cancelled")
    return 0


def show_status() -> int:
    jobs = _jobs()
    out = {"running": [], "state_file": str(STATE)}
    for jid in jobs.running_jobs("permuter"):
        d = read_log(jid)
        out["running"].append({"job": jid, "best": d["best"],
                               "iterations": d["iterations"],
                               "since_improvement": d["since_improvement"]})
    if STATE.is_file():
        try:
            out["supervisor"] = json.loads(STATE.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    print(json.dumps(out, indent=2))
    return 0


# ------------------------------------------------------------------- tests

def self_test() -> int:
    import tempfile
    fails = []

    def ck(c, l):
        print(("  ok   " if c else "  FAIL ") + l)
        if not c:
            fails.append(l)

    global WORKROOT, QUEUE
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        WORKROOT = t / "nonmatchings"
        WORKROOT.mkdir()
        for name, scores in [("fn_a", [700, 220]), ("fn_b", [90]),
                             ("fn_c-2", [1500]), ("fn_d", [])]:
            w = WORKROOT / name
            w.mkdir()
            (w / "base.c").write_text("x")
            for s in scores:
                o = w / f"output-{s}-1"
                o.mkdir()
                (o / "source.c").write_text("y")

        print("\nwork dir lookup")
        ck(workdir_for("fn_a").name == "fn_a", "finds an exact match")
        ck(workdir_for("fn_c").name == "fn_c-2",
           "finds the -2 disambiguated dir from the bare function name")
        ck(workdir_for("fn_zz") is None, "returns None for an unknown function")
        ck(workdir_for("fn_") is None,
           "does not match a prefix that is not a full name")

        print("\nbest score")
        ck(best_score(WORKROOT / "fn_a") == 220, "lowest output wins")
        ck(best_score(WORKROOT / "fn_d") is None, "no outputs means no score")

        QUEUE = t / "q.jsonl"
        QUEUE.write_text("\n".join(json.dumps(r) for r in [
            {"id": "1", "function": "fn_a", "status": "near"},
            {"id": "2", "function": "fn_b", "status": "near"},
            {"id": "3", "function": "fn_c", "status": "near"},
            {"id": "4", "function": "fn_d", "status": "near"},
            {"id": "5", "function": "fn_e", "status": "near"},
            {"id": "6", "function": "fn_x", "status": "todo"},
            {"id": "7", "function": "fn_y", "status": "matched"},
        ]))

        print("\ncandidate selection")
        cs = candidates(check_tree=False)
        names = [c["function"] for c in cs]
        ck("fn_x" not in names, "a todo record is not permuter work")
        ck("fn_y" not in names, "a matched record is not permuter work")
        runnable = [c for c in cs if not c["skip"]]
        ck([c["function"] for c in runnable] == ["fn_b", "fn_a", "fn_c", "fn_d"],
           f"ranked by best score, unscored last ({[c['function'] for c in runnable]})")
        blocked = [c for c in cs if c["skip"]]
        ck([c["function"] for c in blocked] == ["fn_e"],
           "a record with no work dir is reported, not silently dropped")
        ck("import from seed" in blocked[0]["skip"],
           "and says it will be imported rather than dropped")

        print("\nseed path extraction from queue notes")
        ck(seed_from_notes("compiled, byte mismatch; permuter candidate. "
                           "seed=automation/candidates/us_X.c BUILT")
           == "automation/candidates/us_X.c", "pulls seed= out of a real note")
        ck(seed_from_notes("no seed here") == "", "absent seed yields empty")
        ck(seed_from_notes(None) == "", "a None note does not raise")

        print("\nstatus filter refuses what the permuter cannot use")
        ck(check_statuses(("near",)) == "", "near is accepted")
        ck(check_statuses(("near", "escalated")) == "", "escalated is accepted")
        bad = check_statuses(("todo",))
        ck(bad != "" and "todo" in bad, "todo is refused by name")
        ck("already compiles" in bad, "and the refusal explains why")

        print("\nimport restores src/ even when the import fails")
        # The guarantee that matters: whatever happens between the write and
        # the restore, the file on disk ends up byte-identical to before.
        src_dir = t / "srcfake"
        (src_dir).mkdir()
        f = src_dir / "x.c"
        before = 'INCLUDE_ASM("boss/bo6/nonmatchings/x", fn_q);\n'
        f.write_text(before)
        import types
        global REPO
        old_repo = REPO
        REPO = t
        (t / "src").mkdir(exist_ok=True)
        (t / "src" / "x.c").write_text(before)
        seedf = t / "seed.c"
        seedf.write_text("void fn_q(void) {}\n")
        w, msg = import_workdir("fn_q", "seed.c")
        ck((t / "src" / "x.c").read_text() == before,
           "src file is byte-identical after a failed import")
        ck(w is None, f"a failed import returns no work dir ({msg})")
        w2, msg2 = import_workdir("fn_missing", "seed.c")
        ck(w2 is None and "no INCLUDE_ASM stub" in msg2,
           "a function with no stub is reported clearly")
        w3, msg3 = import_workdir("fn_q", "nope.c")
        ck(w3 is None and "seed not found" in msg3,
           "a missing seed is reported clearly")
        REPO = old_repo

        print("\nempty queue")
        QUEUE.write_text("")
        ck(candidates(check_tree=False) == [], "an empty queue yields nothing")
        QUEUE = t / "nope.jsonl"
        ck(candidates(check_tree=False) == [], "a missing queue does not crash")

        print("\nmalformed queue lines are skipped, not fatal")
        QUEUE = t / "bad.jsonl"
        QUEUE.write_text('{"id":"1","function":"fn_a","status":"near"}\n'
                         'NOT JSON\n\n')
        ck(len(candidates(check_tree=False)) == 1,
           "one good record survives a garbage line")

    print("\nbusy-workdir parsing (guards against duplicate supervisors)")
    import types
    fake = types.SimpleNamespace(running_jobs=lambda a: [
        "permuter-141610-6941-func_us_8019AA04-2",
        "permuter-143902-55599-func_us_801B8E80",
        "make_build-110820-9159"])
    real = globals()["_jobs"]
    globals()["_jobs"] = lambda: fake
    b = already_busy()
    ck("func_us_8019AA04-2" in b,
       f"the -2 work dir slug survives the split ({b})")
    ck("func_us_801B8E80" in b, "a plain slug is parsed too")
    ck(not any(x.isdigit() and len(x) > 4 for x in b),
       f"no pid fragments leak into the slug list ({b})")
    globals()["_jobs"] = real

    print("\na run never starts from a worse seed than the best on disk")
    src_sup = Path(__file__).read_text()
    i = src_sup.index("def start_one")
    body = src_sup[i:src_sup.index("\ndef ", i + 1)]
    ck("promote(work)" in body,
       "start_one promotes before starting, so base.c is always the best known "
       "seed")
    ck(body.index("promote(work)") < body.index("start_job"),
       "and it promotes BEFORE the job starts, not after")

    print("\nwrapped INCLUDE_ASM stubs are found")
    # Against the REAL tree: this is a formatting artefact, so a fixture would
    # not rot the way the source does.
    real = REPO / "src" / "boss" / "bo6" / "us_3E79C.c"
    if real.is_file():
        txt = real.read_text(errors="ignore")
        wrapped_fn = "BO6_RicEntitySubwpnStopwatchCircle"
        rx = re.compile(
            rf'INCLUDE_ASM\(\s*"([^"]+)"\s*,\s*{re.escape(wrapped_fn)}\s*\)\s*;')
        m = rx.search(txt)
        ck(m is not None,
           f"a stub wrapped across two lines by clang-format is matched")
        ck(bool(m) and m.group(1) == "boss/bo6/nonmatchings/us_3E79C",
           "and its asm path is captured correctly")
        tight = re.compile(
            rf'INCLUDE_ASM\("([^"]+)",\s*{re.escape(wrapped_fn)}\);')
        ck(tight.search(txt) is None,
           "while the old adjacent-paren regex does NOT match it, which is the "
           "bug this guards")
    else:
        print("  ~~ src/boss/bo6/us_3E79C.c missing; wrap check skipped")

    print("\nthe loop can terminate: outcomes are written back to the queue")
    src_sup = Path(__file__).read_text()
    i = src_sup.index("def supervise")
    sup = src_sup[i:src_sup.index("\ndef _write_state")]
    ck(sup.count("report(") >= 3,
       "retire, cap and match each record an outcome; without this a retired "
       "function stays `near` and the very next plan picks it again")
    ck('"deferred"' in sup,
       "exhausted candidates go to deferred, which is excluded from `near`")
    ck(EXHAUSTED in src_sup and MATCH_PENDING in src_sup,
       "each carries a findable marker, so the decision can be undone "
       "selectively later")

    print("\na solved-but-unbuilt function is not re-searched")
    ck(_why_skip({"notes": f"x {MATCH_PENDING} y"}, Path(".")) != "",
       "a record already at score 0 is skipped rather than given a slot")
    ck("apply it and build" in _why_skip({"notes": MATCH_PENDING}, Path(".")),
       "and the reason says what the human must do")
    ck(_why_skip({"notes": "ordinary near record"}, Path(".")) == "",
       "an ordinary near record is still runnable")
    ck(_why_skip({"notes": ""}, None) == "no work dir; will import from seed",
       "the missing-work-dir reason still works")

    print("\nread_log works for a RUNNING job, not just a finished one")
    # The bug this guards: jobs.status() only includes a "log" key once the job
    # is done, so relying on it made the supervisor blind to every live job.
    import tempfile as _tf, types as _ty
    with _tf.TemporaryDirectory() as td:
        global JOBS_DIR
        old_jd = JOBS_DIR
        JOBS_DIR = Path(td)
        (JOBS_DIR / "permuter-1-2-fn_x.log").write_text(
            "\n".join(f"iteration {i}, 0 errors, score = "
                       f"{900 if i < 100 else 400}" for i in range(1, 6001)))
        fake = _ty.SimpleNamespace(
            # exactly what jobs.status() returns while RUNNING: no "log" key
            status=lambda j, wait_s=0, tail_lines=1: {"state": "running"},
            running_jobs=lambda a: [])
        real = globals()["_jobs"]
        globals()["_jobs"] = lambda: fake
        d = read_log("permuter-1-2-fn_x")
        ck(d["best"] == 400,
           f"a running job's score is read ({d['best']}), not defaulted to None")
        ck(d["since_improvement"] > 5000,
           f"and its stall is measurable ({d['since_improvement']}), which is "
           f"what lets the supervisor act on a live job")
        globals()["_jobs"] = real
        JOBS_DIR = old_jd

    print("\nan iteration cap exists as a second, independent brake")
    src_sup = Path(__file__).read_text()
    ck("DEF_MAX_ITERS" in src_sup and "max_iters" in src_sup,
       "there is a hard per-job iteration ceiling")
    ck(DEF_MAX_ITERS <= 50000,
       f"and it is not so high as to be theoretical ({DEF_MAX_ITERS})")
    i = src_sup.index("def supervise")
    sup_body = src_sup[i:src_sup.index("\ndef ", i + 1)]
    ck(sup_body.index('d["iterations"] >= max_iters')
       < sup_body.index('d["since_improvement"] >= stall'),
       "the cap is checked BEFORE the stall rule, so a job cannot outrun it "
       "by appearing to still improve")

    print("\nsupervisor discovery does not depend on the pidfile")
    src_sup = Path(__file__).read_text()
    i = src_sup.index("def _supervisor_pids")
    body = src_sup[i:src_sup.index("\ndef ", i + 1)]
    ck("Path(\"/proc\").iterdir()" in body,
       "it scans /proc, so supervisors started before the pidfile existed are "
       "still found")
    ck('b"--run" in cmd' in body,
       "and it only matches --run, so `--stop` does not kill itself")
    me = already_busy  # keep the name referenced
    ck(os.getpid() not in _supervisor_pids(),
       "the calling process is never in its own kill list")

    print("\nlong-running output must not be block-buffered")
    src = Path(__file__).read_text()
    ck("line_buffering=True" in src,
       "stdout is line-buffered, so the job log fills as the run proceeds "
       "rather than all at once when it exits")

    print("\ndefaults are the measured ones")
    ck(DEF_THREADS > 1, "threads default is not 1 (the library default is)")
    ck(DEF_SLOTS < 4, "slots leave headroom for the exclusive build")
    ck(DEF_STALL >= 2000, "stall threshold is past observed late improvements")

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
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--log", action="store_true",
                    help="print the detached supervisor's own log")
    ap.add_argument("--slots", type=int, default=DEF_SLOTS)
    ap.add_argument("--threads", type=int, default=DEF_THREADS)
    ap.add_argument("--stall", type=int, default=DEF_STALL)
    ap.add_argument("--cycles", type=int, default=DEF_CYCLES)
    ap.add_argument("--max-iters", type=int, default=DEF_MAX_ITERS,
                    help="hard per-job iteration ceiling")
    ap.add_argument("--status-filter", default="near",
                    help="comma-separated queue statuses to draw from")
    a = ap.parse_args()

    # Line-buffer stdout. This process runs for hours with its output
    # redirected to a job log, and Python block-buffers whenever stdout is not
    # a tty: without this the log stays EMPTY until the run ends, which is
    # precisely when you no longer need to watch it. The same bug bit
    # dashboard.py's startup banner an hour earlier.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):     # pragma: no cover
        pass

    if a.self_test:
        return self_test()
    if a.log:
        if not LOG.is_file():
            print(f"no supervisor log at {LOG}")
            return 0
        print(LOG.read_text(errors="ignore"))
        return 0
    if a.stop:
        return stop_all()
    if a.status:
        return show_status()

    statuses = tuple(s.strip() for s in a.status_filter.split(",") if s.strip())
    bad = check_statuses(statuses)
    if bad:
        print(bad, file=sys.stderr)
        return 2

    if a.plan:
        cs = candidates(statuses)
        if not cs:
            print("no candidates")
            return 0
        print(f"{'function':36s} {'best':>6}  workdir / why not")
        for c in cs:
            print(f"{c['function']:36s} {str(c['score']):>6}  "
                  f"{c['skip'] or c['workdir']}")
        n = len([c for c in cs if not c["skip"]])
        print(f"\n{n} runnable, {len(cs) - n} blocked. "
              f"Run with --run to start {min(n, a.slots)} now.")
        return 0

    if a.run:
        return supervise(a.slots, a.threads, a.stall, a.cycles, statuses,
                         max_iters=a.max_iters)

    ap.error("pass one of --plan, --run, --status, --stop, --self-test")


if __name__ == "__main__":
    raise SystemExit(main())
