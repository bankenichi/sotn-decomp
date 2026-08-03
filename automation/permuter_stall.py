#!/usr/bin/env python3
"""Has a permuter run stopped making progress, and what does that mean?

WHY THIS EXISTS
    The permuter searches forever by default. Left alone it will happily hold a
    core for hours after it has stopped learning anything, and the log gives no
    signal you can act on -- it is one line per iteration at roughly ten per
    second, all of them looking identical.

    Measured over five real runs on 2026-08-03:

        func_us_801C488C    141,409 iters   floor  750    never improved
        func_us_801B8E80     26,106 iters   floor  210    never improved
        func_us_801BC3E0     23,634 iters   floor  735    never improved
        func_us_801B6520     26,534 iters   floor 3275    1542 permuter failures
        func_us_8019AA04     16,630 iters   floor 1720    never improved

    Every one plateaued early and then ran on. The 141k-iteration search spent
    two and a half hours confirming a number it had after the first few hundred.

WHAT THE SCORE SHAPE MEANS
    The permuter mutates EXPRESSIONS. It cannot restructure control flow, split
    a loop, or invent a branch. So a floor it returns to thousands of times and
    never beats is not "a hard search" -- it is evidence the seed's SHAPE is
    wrong, and no amount of further searching will fix it. The answer is to
    re-derive from the assembly, not to wait.

    A high `permuter failures` count is a stronger version of the same message:
    the mutations themselves are being rejected, so the seed is barely
    perturbable. func_us_801B6520 failed 1542 times while pinned at 3275.

Usage:
    python3 automation/permuter_stall.py --log <job log>
    python3 automation/permuter_stall.py --all          # every permuter job log
    python3 automation/permuter_stall.py --self-test
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

JOBS_DIR = Path(os.path.expanduser(
    os.environ.get("SOTN_JOBS_DIR", "~/sotn-work/jobs")))

_ITER = re.compile(r"iteration (\d+)")
_SCORE = re.compile(r"score = (\d+)")
_FAILS = re.compile(r"(\d+) permuter failures")

# How long a run may go without improving before it is called stalled.
#
# 2000 is deliberately well past the point any of the five observed runs last
# improved, so a real but slow search is not cut off. The cost of waiting too
# long is CPU; the cost of stopping too early is a lost match, so the threshold
# leans generous.
STALL_ITERS = 2000


def parse(text: str) -> dict:
    """Best score, when it was last reached, and how far the run went."""
    best = None
    best_at = 0
    last_iter = 0
    fails = 0
    for line in text.splitlines():
        m = _ITER.search(line)
        if m:
            last_iter = int(m.group(1))
        f = _FAILS.search(line)
        if f:
            fails = int(f.group(1))
        s = _SCORE.search(line)
        if not s:
            continue
        score = int(s.group(1))
        if best is None or score < best:
            best, best_at = score, last_iter
    return {"best": best, "best_at": best_at, "iterations": last_iter,
            "failures": fails,
            "since_improvement": last_iter - best_at if best is not None else 0}


def verdict(st: dict) -> tuple[str, str]:
    """(verdict, what to do about it). Never says "keep waiting" on a stall."""
    if st["best"] is None:
        return ("no data", "the log has no score lines yet; poll again")
    if st["best"] == 0:
        return ("MATCH", "score 0 reached; collect the output and apply it")
    if st["failures"] > st["iterations"] // 20:
        return ("UNPERTURBABLE",
                f"{st['failures']} mutations were rejected. The seed is barely "
                f"mutable, which usually means its structure is wrong. "
                f"Re-derive from the assembly.")
    if st["since_improvement"] >= STALL_ITERS:
        return ("STALLED",
                f"no improvement for {st['since_improvement']} iterations "
                f"(best {st['best']} at iteration {st['best_at']}). The "
                f"permuter mutates expressions only, so a stable floor means "
                f"the SHAPE is wrong. Stop and re-derive from the assembly.")
    return ("searching",
            f"best {st['best']}, improved {st['since_improvement']} iterations "
            f"ago; still making progress")


def report(name: str, st: dict) -> None:
    v, why = verdict(st)
    print(f"\n{name}")
    print(f"  iterations {st['iterations']:>8}   best {st['best']}"
          f"   last improved at {st['best_at']}"
          + (f"   failures {st['failures']}" if st["failures"] else ""))
    print(f"  {v}: {why}")


def self_test() -> int:
    fails = []

    def ck(c, l):
        print(("  ok   " if c else "  FAIL ") + l)
        if not c:
            fails.append(l)

    print("\nparsing a real log shape")
    log = "\n".join(
        f"iteration {i}, 0 errors, score = {900 if i < 50 else 750}"
        for i in range(1, 4001))
    st = parse(log)
    ck(st["best"] == 750, f"best score found ({st['best']})")
    ck(st["best_at"] == 50, f"records WHEN the best was reached ({st['best_at']})")
    ck(st["iterations"] == 4000, "records how far the run went")
    ck(st["since_improvement"] == 3950, "computes iterations since improvement")

    print("\nverdicts")
    ck(verdict(st)[0] == "STALLED", "a long flat run is STALLED")
    ck(verdict(parse("iteration 10, 0 errors, score = 500"))[0] == "searching",
       "a young run is still searching")
    ck(verdict(parse("iteration 5, 0 errors, score = 0"))[0] == "MATCH",
       "score 0 is a MATCH")
    ck(verdict(parse(""))[0] == "no data", "an empty log says so")

    print("\nthe unperturbable case (func_us_801B6520's real shape)")
    bad = "\n".join(
        f"iteration {i}, 0 errors, {i//2} permuter failures, score = 3275"
        for i in range(1, 3001))
    ck(verdict(parse(bad))[0] == "UNPERTURBABLE",
       "heavy mutation rejection is called out separately from a plain stall")

    print("\na stall verdict never advises waiting")
    ck("re-derive" in verdict(st)[1].lower(),
       "STALLED tells you to re-derive from the assembly")
    ck("wait" not in verdict(st)[1].lower(), "and does not say to wait")

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
    ap.add_argument("--log", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    logs = []
    if a.log:
        logs = [Path(a.log)]
    elif a.all:
        logs = sorted(JOBS_DIR.glob("permuter-*.log"))
        if not logs:
            print(f"no permuter logs under {JOBS_DIR}")
            return 0
    else:
        ap.error("pass --log <file> or --all")

    stalled = 0
    for p in logs:
        try:
            st = parse(p.read_text(errors="ignore"))
        except OSError as e:
            print(f"\n{p.name}\n  cannot read: {e}")
            continue
        report(p.stem.replace("permuter-", ""), st)
        if verdict(st)[0] in ("STALLED", "UNPERTURBABLE"):
            stalled += 1
    if stalled:
        print(f"\n{stalled} run(s) are not learning anything. Cancel them with "
              f"job_cancel and re-derive those seeds from the assembly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
