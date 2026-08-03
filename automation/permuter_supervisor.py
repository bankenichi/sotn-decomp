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
PYTHON = os.environ.get("SOTN_PYTHON", sys.executable)

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
            # A record with no work dir is still a candidate: permuter_import
            # can build one from the seed named in its notes. Flagging it here
            # rather than silently dropping it keeps the plan honest about what
            # it cannot start yet.
            "skip": "" if work else "no work dir; run permuter_import first",
        })

    runnable = [c for c in out if not c["skip"]]
    blocked = [c for c in out if c["skip"]]
    # Unscored dirs sort last: a dir with no output yet is an unknown, and an
    # unknown should not outrank a seed measured at 70.
    runnable.sort(key=lambda c: (c["score"] is None, c["score"] or 0))
    return runnable + blocked


# ---------------------------------------------------------------------- jobs

def _jobs():
    import jobs
    return jobs


def start_one(work: Path, threads: int) -> str:
    import commands_client as cc
    r = cc.start_job("permuter", work_dir=str(work.relative_to(REPO)),
                     threads=threads)
    return r.get("job_id", "")


def promote(work: Path) -> str:
    r = subprocess.run([PYTHON, str(REPO / "automation" / "permuter_promote.py"),
                        "--dir", str(work.relative_to(REPO))],
                       capture_output=True, text=True, cwd=str(REPO))
    return (r.stdout or r.stderr).strip()


def read_log(job_id: str) -> dict:
    from permuter_stall import parse
    jobs = _jobs()
    st = jobs.status(job_id, wait_s=0, tail_lines=1)
    log = Path(st.get("log", ""))
    if not log.is_file():
        return {"state": st.get("state", "?"), "best": None,
                "iterations": 0, "since_improvement": 0, "failures": 0}
    d = parse(log.read_text(errors="ignore"))
    d["state"] = st.get("state", "?")
    return d


# ----------------------------------------------------------------- the loop

def supervise(slots: int, threads: int, stall: int, cycles: int,
              statuses: tuple[str, ...], once: bool = False) -> int:
    jobs = _jobs()
    pending = [c for c in candidates(statuses) if not c["skip"]]
    if not pending:
        print("nothing to permute; every candidate is matched, phantom, or "
              "has no work dir")
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
                done.append(slot)
                del active[jid]
                continue

            if d["state"] not in ("running",):
                slot["result"] = f"job ended ({d['state']}), best {d['best']}"
                done.append(slot)
                del active[jid]
                continue

            if d["since_improvement"] >= stall and d["iterations"] > stall:
                jobs.cancel(jid)
                msg = promote(work)
                improved = msg.startswith("promoted")
                if improved and slot["cycles"] + 1 < cycles:
                    slot["cycles"] += 1
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
                done.append(slot)
                del active[jid]

    _write_state({}, done)
    print("\n--- supervisor finished ---")
    matches = [d for d in done if d.get("result") == "MATCH"]
    for d in done:
        print(f"  {d['function']:34s} {d.get('result', d.get('skip', '?'))}")
    print(f"\n{len(matches)} match(es). Nothing was applied to the tree.")
    return 0


def _write_state(active: dict, done: list) -> None:
    """Publish state for the dashboard. Best effort: never kill the run."""
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps({
            "updated": time.time(),
            "active": [{"function": s["function"], "job": s["job"],
                        "cycles": s["cycles"], "workdir": s["workdir"]}
                       for s in active.values()],
            "done": [{"function": d["function"],
                      "result": d.get("result", d.get("skip", ""))}
                     for d in done],
        }, indent=2))
    except OSError:
        pass


def stop_all() -> int:
    jobs = _jobs()
    n = 0
    for jid in jobs.running_jobs("permuter"):
        jobs.cancel(jid)
        print(f"cancelled {jid}")
        n += 1
    _write_state({}, [])
    print(f"{n} permuter job(s) cancelled")
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
        ck("permuter_import" in blocked[0]["skip"],
           "and it says what to do about it")

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
    ap.add_argument("--slots", type=int, default=DEF_SLOTS)
    ap.add_argument("--threads", type=int, default=DEF_THREADS)
    ap.add_argument("--stall", type=int, default=DEF_STALL)
    ap.add_argument("--cycles", type=int, default=DEF_CYCLES)
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
    if a.stop:
        return stop_all()
    if a.status:
        return show_status()

    statuses = tuple(s.strip() for s in a.status_filter.split(",") if s.strip())

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
        return supervise(a.slots, a.threads, a.stall, a.cycles, statuses)

    ap.error("pass one of --plan, --run, --status, --stop, --self-test")


if __name__ == "__main__":
    raise SystemExit(main())
