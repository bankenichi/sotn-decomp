#!/usr/bin/env python3
"""A cancelled job must not look like a crashed one.

WHY THIS EXISTS
    job_list showed five permuter jobs for func_us_801C4B2C, across five
    sessions, all in state `vanished` (#117). They were the phantom rows on the
    dashboard: jobs that render, show "run - . 0 it", and never come back.

    They were not crashes. `cancel()` kills the process group and returns, and
    the wrapper writes its exit sentinel on the line AFTER the work finishes --
    a line a killed wrapper never reaches. status() then sees no sentinel and a
    dead pid, which is its definition of `vanished`, and reports

        "process died without writing an exit code;
         treat the tree as mid-build and rebuild"

    That is correct advice for a genuine crash and alarming nonsense for a stop
    the operator asked for. Worse, it is permanent: nothing ever revisits the
    record, so a stopped job haunts job_list forever.

WHAT IS ASSERTED
    Against real processes and a real temp jobs dir: a job that is cancelled
    reports done-and-cancelled rather than vanished, and a job that is genuinely
    killed behind the module's back still reports vanished, because that
    distinction is the entire point.
"""
import os
import sys
import time
import signal
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "mcp"))

FAILS = []


def check(cond, label, detail=""):
    print(("  ok   " if cond else "  FAIL ") + label
          + ("" if cond else "   " + detail))
    if not cond:
        FAILS.append(label)


def main() -> int:
    import jobs

    tmp = Path(tempfile.mkdtemp(prefix="jobcancel-"))
    jobs.JOBS_DIR = tmp

    print("a cancelled job reports as stopped, not as a crash")
    r = jobs.start("run_analysis", ["sleep", "60"], cwd=str(HERE),
                   exclusive=False, slug="cancelme")
    check(r.get("started"), f"job started ({r.get('job_id')})")
    jid = r["job_id"]
    time.sleep(0.4)

    c = jobs.cancel(jid)
    check(c.get("cancelled"), "cancel reports success")
    # Give the kill a moment to be reaped.
    for _ in range(30):
        if jobs.status(jid).get("state") != "running":
            break
        time.sleep(0.1)

    st = jobs.status(jid)
    check(st["state"] != "vanished",
          f"state is NOT vanished (got {st['state']!r}) -- vanished is what "
          f"made five stopped jobs look like crashes forever")
    check(st["state"] == "done", f"it is done (got {st['state']!r})")
    check(st.get("cancelled") is True, "and flagged as cancelled")
    check(st.get("returncode") in (143, 137),
          f"the code is 128+signal, so it names the signal rather than "
          f"inventing a vocabulary (got {st.get('returncode')})")
    check(not st.get("ok"), "it is not reported as a success")
    check("cancelled on request" in (st.get("hint") or ""),
          "the hint says it was asked for, not that the tree needs rebuilding")

    print("\nlist_jobs agrees with status")
    listed = {j["job_id"]: j["state"] for j in jobs.list_jobs()["jobs"]}
    check(listed.get(jid) == "done",
          f"the job list shows done, not vanished (got {listed.get(jid)!r})")

    print("\na genuine crash STILL reports vanished")
    # The distinction is the point: kill the wrapper behind the module's back,
    # so no sentinel is written by anyone. That is a real crash and must keep
    # its warning.
    r2 = jobs.start("run_analysis", ["sleep", "60"], cwd=str(HERE),
                    exclusive=False, slug="crashme")
    jid2 = r2["job_id"]
    time.sleep(0.4)
    try:
        os.killpg(os.getpgid(r2["pid"]), signal.SIGKILL)
    except OSError:
        pass
    for _ in range(30):
        if jobs.status(jid2).get("state") != "running":
            break
        time.sleep(0.1)
    st2 = jobs.status(jid2)
    check(st2["state"] == "vanished",
          f"an unannounced death is still vanished (got {st2['state']!r})")
    check("mid-build" in (st2.get("hint") or ""),
          "and keeps the rebuild warning, which is correct for a real crash")

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED:")
        for f in FAILS:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
