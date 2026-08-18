#!/usr/bin/env python3
"""Does the scheduler stop handing out a record the fleet is looping on?

WHY THIS EXISTS
    On 2026-08-16 a 4-worker run spent roughly 480 model calls and resolved
    NOTHING. Two workers claimed the same record about 35 times each --
    EntityGaibon alone took 141 of one worker's 240 attempts -- and every
    attempt ended in a byte-identical quality reject. Neither worker ever
    printed a terminal verdict.

    Nothing stopped it, and nothing even counted it. `iterations` looked like
    the natural guard but only moves on `report --add-iters`, and this loop
    died before reaching any reporting path at all. A counter that only
    increments when a worker finishes cleanly cannot see a worker that never
    finishes.

    So the counter sits on the CLAIM, in _take, which is the single place a
    claim is written. A worker that crashes, is killed, or exits silently
    still had to come through there to get the record. That makes the breaker
    independent of WHY the loop happens -- which matters, because the cause is
    still open (#113) and this has to bound the cost meanwhile.

WHAT IS ASSERTED
    Against a throwaway queue file, for real, through the scheduler CLI: the
    count rises per claim, the breaker trips at the ceiling, the record is
    parked with a note that says what happened, its old note survives, and a
    named --only claim is still allowed through.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

FAILS = []


def check(cond, label, detail=""):
    print(("  ok   " if cond else "  FAIL ") + label
          + ("" if cond else "   " + detail))
    if not cond:
        FAILS.append(label)


def rec(rid, status="todo", claims=None, notes=""):
    r = {"id": rid, "status": status, "build": "us",
         "function": rid.rsplit(":", 1)[1], "overlay": "rdai",
         "tier": 0, "iterations": 0, "notes": notes}
    if claims is not None:
        r["claims"] = claims
    return r


def write_queue(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def read_queue(path):
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                out[r["id"]] = r
    return out


def sched(qpath, *args):
    env = dict(os.environ, SOTN_QUEUE=qpath)
    p = subprocess.run(
        [sys.executable, os.path.join(HERE, "scheduler.py")] + list(args),
        capture_output=True, text=True, cwd=REPO, env=env, timeout=120)
    lines = [l for l in p.stdout.splitlines() if l.strip().startswith("{")]
    return (json.loads(lines[-1]) if lines
            else {"status": "no-json", "stdout": p.stdout, "stderr": p.stderr})


def main():
    d = tempfile.mkdtemp(prefix="claimlimit-")
    q = os.path.join(d, "queue.jsonl")

    print("\nevery claim is counted, even though no report ever happens")
    # The whole point: this test NEVER calls `report`. It only claims and
    # releases, exactly like a worker that dies before its verdict.
    write_queue(q, [rec("us:ST/RDAI:loop_fn")])
    for i in (1, 2, 3):
        sched(q, "next", "--worker", "t")
        got = read_queue(q)["us:ST/RDAI:loop_fn"]
        check(got.get("claims") == i, f"claim {i} counted (claims={got.get('claims')})")
        # Put it back the way a released/stranded claim would.
        write_queue(q, [rec("us:ST/RDAI:loop_fn", "todo", claims=i)])

    print("\nthe breaker trips at the ceiling and parks the record")
    prior_note = "  TIER_HANDOFF_TOO_LARGE: real prior note " + ("Z" * 1600) + "  \n"
    write_queue(q, [rec("us:ST/RDAI:loop_fn", "todo", claims=11,
                        notes=prior_note)])
    r = sched(q, "next", "--worker", "t")
    check(r.get("id") == "us:ST/RDAI:loop_fn",
          "claim 12 is still allowed; the ceiling is a limit, not an off-by-one")

    write_queue(q, [rec("us:ST/RDAI:loop_fn", "todo", claims=12,
                        notes=prior_note)])
    r = sched(q, "next", "--worker", "t")
    check(r.get("id") != "us:ST/RDAI:loop_fn",
          f"claim 13 is REFUSED (got {r.get('id')!r})")
    parked = read_queue(q)["us:ST/RDAI:loop_fn"]
    check(parked["status"] == "escalated",
          f"and the record is escalated, not left in todo to be re-picked "
          f"(status={parked['status']})")
    check("CLAIM_LIMIT" in parked["notes"],
          "the note names the reason, so this is not a silent disappearance")
    check("TIER_HANDOFF_TOO_LARGE" in parked["notes"],
          "and the PRIOR note survives; the note is the only index, and "
          "overwriting it has destroyed a record's classification before")
    check(parked["notes"].endswith(prior_note),
          "and the complete prior note survives beyond the old 1000-character cap")

    print("\na burned record does not block the rest of the queue")
    write_queue(q, [rec("us:ST/RDAI:loop_fn", "todo", claims=50),
                    rec("us:ST/RDAI:good_fn", "todo")])
    r = sched(q, "next", "--worker", "t")
    check(r.get("id") == "us:ST/RDAI:good_fn",
          f"the healthy record is claimed instead (got {r.get('id')!r})")
    after = read_queue(q)
    check(after["us:ST/RDAI:loop_fn"]["status"] == "escalated",
          "and the burned one is parked in the same pass")

    print("\nnaming an id still works, because that is an operator act")
    write_queue(q, [rec("us:ST/RDAI:loop_fn", "todo", claims=99)])
    r = sched(q, "next", "--worker", "t", "--only", "us:ST/RDAI:loop_fn")
    check(r.get("id") == "us:ST/RDAI:loop_fn",
          f"--only bypasses the breaker (got {r.get('id')!r})")

    print("\nrecords predating the counter are not treated as burned")
    # Every record in the live queue is missing `claims` entirely. If a missing
    # key read as anything but 0, this change would escalate the whole queue on
    # the next claim.
    write_queue(q, [rec("us:ST/RDAI:old_fn")])
    old = read_queue(q)["us:ST/RDAI:old_fn"]
    check("claims" not in old, "fixture has no claims key, like the live queue")
    r = sched(q, "next", "--worker", "t")
    check(r.get("id") == "us:ST/RDAI:old_fn",
          f"and it is claimed normally (got {r.get('id')!r})")

    print("\na size handoff goes to a BIGGER tier, never back to the deferrer")
    HANDOFF = "TIER_HANDOFF_TOO_LARGE"
    # Exactly the shape that looped: zen defers at 20000, then asks again at
    # 20000 with --include-deferred and is handed its own record back.
    def handoff(limit):
        return [rec("us:ST/RDAI:big_fn", "deferred",
                    notes=f"{HANDOFF}: asm 23208 chars > {limit}")
                | {"handoff_limit": limit}]

    write_queue(q, handoff(20000))
    r = sched(q, "next", "--worker", "t", "--include-deferred",
              "--max-func-chars", "20000")
    check(r.get("id") != "us:ST/RDAI:big_fn",
          f"an equal tier is REFUSED, which is the #113 loop (got {r.get('id')!r})")

    write_queue(q, handoff(20000))
    r = sched(q, "next", "--worker", "t", "--include-deferred",
              "--max-func-chars", "6000")
    check(r.get("id") != "us:ST/RDAI:big_fn",
          f"and so is a SMALLER tier (got {r.get('id')!r})")

    write_queue(q, handoff(6000))
    r = sched(q, "next", "--worker", "t", "--include-deferred",
              "--max-func-chars", "20000")
    check(r.get("id") == "us:ST/RDAI:big_fn",
          f"a genuinely bigger tier still gets it, so the handoff pool is not "
          f"simply disabled (got {r.get('id')!r})")

    print("\nrecords deferred before handoff_limit existed are not stranded")
    legacy = [rec("us:ST/RDAI:big_fn", "deferred",
                  notes=f"{HANDOFF}: asm 23208 chars > 6000 on backend=http")]
    write_queue(q, legacy)
    r = sched(q, "next", "--worker", "t", "--include-deferred")
    check(r.get("id") != "us:ST/RDAI:big_fn",
          "a caller that declares no limit gets nothing; declaring nothing is "
          "the shape that caused the loop")
    write_queue(q, legacy)
    r = sched(q, "next", "--worker", "t", "--include-deferred",
              "--max-func-chars", "20000")
    check(r.get("id") == "us:ST/RDAI:big_fn",
          f"but a caller that DOES declare one gets a shot at it, and the "
          f"record gains a limit when it defers again (got {r.get('id')!r})")

    print("\n" + ("all checks passed" if not FAILS else f"{len(FAILS)} FAILED"))
    for f in FAILS:
        print("  - " + f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
