#!/usr/bin/env python3
"""Is BuildLock correct, and is its cost charged to the right budget?

WHY THIS EXISTS
    The lock itself was never suspected: 122 contended acquisitions across the
    archived logs and ZERO stale-lock steals, so no wedge and no double build.
    What the logs did show is a long tail -- mean wait 22s, worst 300s, 44.5
    minutes in total.

    300s is a third of FUNC_BUDGET (900s), and the lock is taken INSIDE that
    budget. So a worker that queued behind two other builds could be killed
    with "BUDGET EXHAUSTED ... escalating" for being unlucky rather than for
    working on a hard function, and escalation routes the record to a more
    expensive tier. The bug was accounting, not locking.

WHAT IS ASSERTED
    Mutual exclusion under real concurrent processes, stale takeover by
    rename rather than unlink, and that waiting is credited back.
"""
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "win"))
os.environ.setdefault("MODEL_BACKEND", "zen")

import worker_direct as wd  # noqa: E402

FAILS = []


def check(cond, label):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


def main():
    tmp = tempfile.mkdtemp()
    lockpath = os.path.join(tmp, ".build.lock")

    print("only one holder at a time, under real threads")
    inside, overlaps, order = [], [], []

    def worker(n):
        lk = wd.BuildLock(lockpath)
        lk.acquire(poll=0.02)
        inside.append(n)
        if len(inside) > 1:
            overlaps.append(list(inside))
        time.sleep(0.05)
        order.append(n)
        inside.remove(n)
        lk.release()

    ts = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=30)
    check(not overlaps, f"never two holders at once ({overlaps})")
    check(len(order) == 6, f"and every waiter eventually got it ({len(order)}/6)")
    check(not os.path.exists(lockpath), "the lock file is gone after release")

    print("\nwaiting is credited back to the function budget")
    # A held lock, then a second acquirer that must wait. The accumulator has
    # to grow by roughly the wait, or the retry loop cannot compensate.
    held = wd.BuildLock(lockpath)
    held.acquire(poll=0.02)
    before = wd._LOCK_WAIT_TOTAL
    done = threading.Event()

    def waiter():
        lk = wd.BuildLock(lockpath)
        lk.acquire(poll=0.02)
        lk.release()
        done.set()

    th = threading.Thread(target=waiter)
    th.start()
    time.sleep(0.30)
    held.release()
    th.join(timeout=30)
    grew = wd._LOCK_WAIT_TOTAL - before
    check(done.is_set(), "the waiter acquired once the holder released")
    check(grew >= 0.2,
          f"and the wait was recorded, so the budget can be extended by it "
          f"({grew:.2f}s recorded for a ~0.3s wait)")
    check(grew < 5.0, f"without wildly over-counting ({grew:.2f}s)")

    print("\nan uncontended acquire costs the budget nothing")
    before2 = wd._LOCK_WAIT_TOTAL
    lk = wd.BuildLock(lockpath)
    lk.acquire(poll=0.02)
    lk.release()
    check(wd._LOCK_WAIT_TOTAL - before2 < 0.1,
          f"({wd._LOCK_WAIT_TOTAL - before2:.3f}s)")

    print("\na stale lock is stolen by RENAME, not unlink")
    # unlink was a TOCTOU: two workers both see the same stale lock, one
    # unlinks and creates a fresh one, the other unlinks THAT and creates its
    # own. Both then believe they hold it and both build.
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "win", "worker_direct.py"), encoding="utf-8").read()
    body = src[src.index("class BuildLock"):]
    body = body[:body.index("\n\nclass ") if "\n\nclass " in body else len(body)]
    check("os.rename(self.path, steal)" in body,
          "the steal is a rename")
    check("os.unlink(self.path)" not in body.split("def release")[0],
          "and acquire never unlinks the live lock path")

    with open(lockpath, "w") as f:
        f.write("99999 0")
    os.utime(lockpath, (0, 0))                      # ancient
    lk2 = wd.BuildLock(lockpath, stale_after=1.0)
    t0 = time.time()
    lk2.acquire(poll=0.02)
    check(time.time() - t0 < 5, "a stale lock is taken over promptly")
    lk2.release()

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
