#!/usr/bin/env python3
"""Can a worker be pointed at ONE named record?

WHY THIS EXISTS
    Until now the only way to run a worker was fleet_start, which launches N
    detached loops that claim by declaration-coverage rank. That is correct for
    production and useless for verification.

    Concretely: proving the m2c-only path (6a3952b72) required running
    us:ST/RDAI:func_us_801C2418, 68865 chars, the largest function in the
    queue. It sat at the BOTTOM of a 160-record todo list, because rank orders
    by how well-declared a function is and a huge one ranks badly. A fleet
    launched to test it would have worked a different record and reported
    success, which is the worst possible outcome for a verification run.

    The alternatives were to reorder the live queue, or to run the worker from
    a sandbox shell. The first corrupts the thing being measured; the second is
    forbidden for this project and dies at 45s anyway. So: `--only`.

WHAT IS ASSERTED
    The scheduler half is exercised for REAL against a throwaway queue file:
    these run scheduler.py as a subprocess with SOTN_QUEUE pointed at a temp
    path and check which record actually comes back. That is the half where a
    mistake silently claims the wrong function.

    The worker and connector halves are structural, because driving them needs
    a build and the lock.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "win"))
sys.path.insert(0, os.path.join(HERE, "mcp"))

FAILS = []


def check(cond, label):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


def rec(rid, status):
    return {"id": rid, "status": status, "build": "us",
            "function": rid.rsplit(":", 1)[1], "overlay": "rdai",
            "tier": 0, "iterations": 0, "notes": ""}


def run_next(qpath, *extra):
    """`scheduler.py next` against a throwaway queue. Returns the parsed record.

    SOTN_QUEUE is set to a file that ALREADY HAS CONTENT, which matters:
    scheduler.py migrates the legacy in-repo queue into an empty target on
    import and then refuses every mutating command against the result. An
    empty temp file would make this whole suite test the refusal path.
    """
    env = dict(os.environ, SOTN_QUEUE=qpath)
    p = subprocess.run(
        [sys.executable, os.path.join(HERE, "scheduler.py"), "next",
         "--worker", "test-targeted"] + list(extra),
        capture_output=True, text=True, cwd=REPO, env=env, timeout=120)
    lines = [l for l in p.stdout.splitlines() if l.strip().startswith("{")]
    if not lines:
        return {"status": "no-json", "stdout": p.stdout, "stderr": p.stderr}
    return json.loads(lines[-1])


def write_queue(qpath, records):
    with open(qpath, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def scheduler_behaviour(tmp):
    qpath = os.path.join(tmp, "queue.jsonl")

    print("--only claims the NAMED record, not the highest-ranked one")
    # Three todo records. Without --only the scheduler picks by rank; with it
    # the answer must be the one asked for regardless of where it sits.
    write_queue(qpath, [
        rec("us:ST/RDAI:func_a", "todo"),
        rec("us:ST/RDAI:func_b", "todo"),
        rec("us:ST/RDAI:func_target", "todo"),
    ])
    got = run_next(qpath, "--only", "us:ST/RDAI:func_target")
    check(got.get("id") == "us:ST/RDAI:func_target",
          f"claimed the named id (got {got.get('id')!r})")
    check(got.get("status") == "claimed", "and marked it claimed")
    check(got.get("claimed_from") == "todo",
          "recording claimed_from, so a strand goes back where it came from")
    on_disk = [json.loads(l) for l in open(qpath, encoding="utf-8")]
    others = [r for r in on_disk if r["id"] != "us:ST/RDAI:func_target"]
    check(all(r["status"] == "todo" for r in others),
          "and touched nothing else")

    print("\nand it reaches records the ordinary claim path cannot")
    # The real case: the only todo record is not the one we want, and the one
    # we want is `deferred` WITHOUT the TIER_HANDOFF_TOO_LARGE marker, so
    # --include-deferred would not surface it either.
    write_queue(qpath, [
        rec("us:ST/RDAI:func_a", "todo"),
        rec("us:ST/RDAI:func_deferred", "deferred"),
        rec("us:ST/RDAI:func_escalated", "escalated"),
    ])
    got = run_next(qpath, "--only", "us:ST/RDAI:func_deferred")
    check(got.get("id") == "us:ST/RDAI:func_deferred",
          "an unmarked deferred record is claimable when named")
    check(got.get("claimed_from") == "deferred",
          "and remembers it was deferred, not todo")

    write_queue(qpath, [
        rec("us:ST/RDAI:func_a", "todo"),
        rec("us:ST/RDAI:func_escalated", "escalated"),
    ])
    got = run_next(qpath, "--only", "us:ST/RDAI:func_escalated")
    check(got.get("id") == "us:ST/RDAI:func_escalated",
          "so is an escalated one")

    print("\nbut it will not steal a live claim or re-run a match")
    # Stealing a claim would put two workers on the same source file, and both
    # would journal and restore over each other.
    write_queue(qpath, [
        rec("us:ST/RDAI:func_a", "todo"),
        rec("us:ST/RDAI:func_held", "claimed"),
        rec("us:ST/RDAI:func_done", "matched"),
    ])
    got = run_next(qpath, "--only", "us:ST/RDAI:func_held")
    check(got.get("status") == "empty",
          f"a claimed record is refused (got {got.get('status')!r})")
    got = run_next(qpath, "--only", "us:ST/RDAI:func_done")
    check(got.get("status") == "empty",
          "a matched record is refused; re-running one can only lose it")
    on_disk = {r["id"]: r for r in
               (json.loads(l) for l in open(qpath, encoding="utf-8"))}
    check(on_disk["us:ST/RDAI:func_done"]["status"] == "matched",
          "and the matched record is left exactly as it was")

    print("\na missing id is refused rather than falling back to the queue")
    # THE IMPORTANT ONE. If a typo fell through to the ordinary path, a
    # targeted verification run would work an unrelated function and report
    # success, and nothing in the output would say so.
    write_queue(qpath, [rec("us:ST/RDAI:func_a", "todo")])
    got = run_next(qpath, "--only", "us:ST/RDAI:func_typo")
    check(got.get("status") == "empty",
          f"claims nothing (got {got.get('id') or got.get('status')!r})")
    on_disk = [json.loads(l) for l in open(qpath, encoding="utf-8")]
    check(on_disk[0]["status"] == "todo",
          "in particular it did NOT claim the record it would have picked")

    print("\nwithout --only the ordinary path is unchanged")
    write_queue(qpath, [
        rec("us:ST/RDAI:func_a", "todo"),
        rec("us:ST/RDAI:func_b", "todo"),
    ])
    got = run_next(qpath)
    check(got.get("id") in ("us:ST/RDAI:func_a", "us:ST/RDAI:func_b"),
          "still claims from the todo pool")
    check(got.get("claimed_from") == "todo", "still records claimed_from")


def scheduler_structure():
    src = open(os.path.join(HERE, "scheduler.py"), encoding="utf-8").read()

    print("\none claim writer, so the two paths cannot drift")
    # claimed_from is the field that matters here: release_claim_if_held and
    # cmd_reclaim both read it, and a second claim site that forgot to set it
    # would send stranded records to `todo` from wherever they started.
    check(src.count('r["status"] = "claimed"') == 1,
          "'claimed' is assigned in exactly one place")
    check(src.count('r["claimed_from"] = r["status"]') == 1,
          "and claimed_from beside it, once")
    check("def _take(" in src and src.index("def _take(") < src.index("def cmd_next("),
          "both paths go through _take")

    print("\nthe flag is registered on `next` and nowhere else")
    check('pn.add_argument("--only"' in src, "next takes --only")
    check(src.count('add_argument("--only"') == 1,
          "and no other subcommand does")


def worker_structure():
    import worker_direct as wd
    src = open(wd.__file__, encoding="utf-8", errors="replace").read()

    print("\nthe worker passes it through")
    check("def claim_next(only: str | None = None)" in src,
          "claim_next takes an id")
    check('_next_args += ["--only", only]' in src,
          "and forwards it to the scheduler")
    check("def process_one(dry: bool = False, only: str | None = None)" in src,
          "process_one takes one too")
    check("process_one(a.dry_run, a.only)" in src,
          "and `once` supplies it")

    print("\n`loop --only` is not offered, because it would not mean anything")
    # A loop with a fixed id either re-claims the record it just reported or
    # stops after one pass. Both look like a bug from the outside.
    loop = src[src.index('p2 = sub.add_parser("loop")'):]
    loop = loop[:loop.index("sub.add_parser(\"preflight\"")]
    check("--only" not in loop, "loop has no --only")

    print("\nan unclaimable id says so instead of 'queue empty'")
    # "queue empty" after a targeted run is a lie: the queue is full, that one
    # record was unclaimable, and the two need different responses.
    check("cannot claim" in src, "the message names the id and the reason")


def connector_structure():
    import commands_client as cc
    src = open(cc.__file__, encoding="utf-8", errors="replace").read()

    print("\nboth connector surfaces know about worker_once")
    # REGISTRY and the @mcp.tool() list are separate; a capability added to one
    # only is uncallable.
    check("worker_once" in cc.REGISTRY, "it is in REGISTRY")
    check("worker_once" in cc.LONG_ACTIONS,
          "and in LONG_ACTIONS, so it goes through job_start not run()")
    mcp_src = open(os.path.join(HERE, "mcp", "sotn_cmd_mcp.py"),
                   encoding="utf-8", errors="replace").read()
    # Scoped to job_start's own body. Searching the whole file for
    # `kw = {"version": version}` finds an unrelated earlier one at module
    # level and the ordering check passes for the wrong reason -- which is what
    # the first version of this did.
    js = mcp_src[mcp_src.index("def job_start("):]
    js = js[:js.index("\n@mcp.tool()")]
    check('elif action == "worker_once":' in js,
          "job_start has a branch for it")
    check(js.index('elif action == "worker_once":')
          < js.index('kw = {"version": version}'),
          "before the else-branch that would pass an unsupported version=")
    check("worker_once needs only=" in js,
          "and a missing id fails with the fix in the message")

    print("\nand it is exposed as a tool, not only as a job action")
    # REGISTRY and the @mcp.tool() list are separate: an action in one only is
    # uncallable. test_connector_surfaces enforces this across the board and
    # caught worker_once missing here.
    check("def worker_once(" in mcp_src, "there is a worker_once tool")
    check('MODEL_BACKEND="zen"' in src or "MODEL_BACKEND=zen" in src,
          "and the backend is pinned to zen rather than inherited")

    print("\nthe id is shape-checked before it reaches a subprocess")
    argv = cc.build_argv("worker_once", only="us:ST/RDAI:func_us_801C2418")
    check(argv[-2:] == ["--only", "us:ST/RDAI:func_us_801C2418"],
          "a good id builds the expected argv")
    check("worker_direct.py" in " ".join(argv) and "once" in argv,
          "running the ordinary worker, not a special one")
    for bad in ("", "not an id", "us:ST/RDAI:func;rm -rf /", "../../etc/passwd"):
        try:
            cc.build_argv("worker_once", only=bad)
            check(False, f"rejects {bad!r}")
        except cc.Rejected:
            check(True, f"rejects {bad!r}")

    print("\nexistence is NOT checked here, deliberately")
    # This process does not hold the queue lock, so any existence answer it
    # gave could be stale by the time the worker claims. cmd_next decides,
    # inside the transaction, where the answer is still true.
    vf = src[src.index("def _queue_id("):]
    vf = vf[:vf.index("\ndef ", 10)]
    check("QUEUE_ID_RX.match" in vf, "it is a regex check")
    check(".jsonl" not in vf and "Queue(" not in vf and "open(" not in vf,
          "and reads no queue file to answer")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        scheduler_behaviour(tmp)
    scheduler_structure()
    worker_structure()
    connector_structure()

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED:")
        for f in FAILS:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
