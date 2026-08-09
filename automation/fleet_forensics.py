#!/usr/bin/env python3
"""WHY do fleet calls fail, not just how often.

WHY THIS EXISTS
    empty_response_audit.py counts outcomes. It answers "how much time is
    wasted" (94%) and stops there, which is not enough to fix anything. This
    replays the worker logs and asks what actually happened inside each dead
    call, using evidence that is already on disk. No fleet run required.

WHAT IT FOUND ON FIRST RUN (1041 calls, 2026-08-03)

    produced                          96
    empty  (rc=0, zero bytes)        154
    timeout                          726
      of which zero bytes streamed   724
      of which a partial body        0
      of which a COMPLETE function   2

    That single line reframes the problem. 724 of 726 timeouts produced NOT
    ONE BYTE before the cap. The failure is not a model writing bad C, not a
    model rambling past the deadline, and not truncation: the request never
    yields anything at all. 880 of 976 completed calls returned nothing.

    It also retires a fix. The timeout-salvage added the same day recovers
    exactly 2 calls out of 1041, because there is almost never anything in the
    buffer to salvage. Worth keeping (it is free) but it is not the answer,
    and the comment claiming it was "the COMMON case" was generalising from a
    single observed instance.

WHAT THE SHAPE OF THE FAILURE RULES OUT
    not warm-up      the first call of a log produces 12% of the time against
                     10% overall, so it is not session initialisation.
    not streaky      dead runs average 9.2 calls, and independent failures at
                     the observed 9.8% success rate predict 9.2. The failures
                     are INDEPENDENT per call. That argues against connection
                     or session state and for each request being dropped on
                     its own merits.
    degrades late    5% success after the 20th call in a log against 14% in
                     the first five. Confounded (later calls may be harder
                     functions) but consistent with a per-session or per-hour
                     provider budget.

WHAT WE STILL CANNOT SEE, AND WHY
    The timeout path kills the child and never reads its stderr, so if
    `opencode run` printed a reason -- rate limit, auth, model unavailable --
    it was discarded along with the process. There is also no time-to-first-
    byte, so "the provider never answered" and "the provider answered slowly
    and we cut it off" are indistinguishable in the logs.

    Those two gaps are the whole diagnosis. See docs/fleet-dead-time.md.

STRICTLY READ-ONLY. Parses logs, runs nothing, changes nothing.

Usage:
    python3 automation/fleet_forensics.py
    python3 automation/fleet_forensics.py --by-model
    python3 automation/fleet_forensics.py --streaks
    python3 automation/fleet_forensics.py --json out.json
    python3 automation/fleet_forensics.py --self-test
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "automation" / "logs"

RX_RUN = re.compile(r"--- opencode run \((\S+), prompt (\d+) chars")
RX_TIMEOUT = re.compile(r"!! attempt \d+ timed out after (\d+)s")
RX_DONE = re.compile(r"--- done in (\d+)s: (\d+) chars ---")
RX_GENFAIL = re.compile(r"!! attempt \d+ generation failed: (\S+)")
RX_STREAM = "  | "

# Outcome vocabulary. Deliberately finer than empty_response_audit's
# produced/empty/dead, because "dead" merges failures with different causes
# and therefore different fixes.
OUTCOMES = ("produced", "empty", "timeout_no_bytes", "timeout_partial",
            "timeout_complete", "genfail", "abandoned")


def log_files() -> list[Path]:
    out = list(LOGS.glob("worker-*.log"))
    arch = LOGS / "archive"
    if arch.is_dir():
        out += list(arch.rglob("worker-*.log"))
    return sorted(out)


def _complete_function(text: str) -> bool:
    """Reuse the worker's own gate so this agrees with what salvage would do."""
    try:
        sys.path.insert(0, str(REPO / "automation" / "win"))
        import worker_direct as wd                           # type: ignore
        return bool(wd.complete_function(text))
    except Exception:                                        # noqa: BLE001
        return False


def parse(paths: list[Path]) -> list[dict]:
    """One record per model call, in order, with what the stream contained."""
    calls: list[dict] = []
    for f in paths:
        cur = None
        buf: list[str] = []
        for line in f.read_text(errors="ignore").splitlines():
            m = RX_RUN.search(line)
            if m:
                if cur:                       # a run with no terminator
                    cur["outcome"] = "abandoned"
                    calls.append(cur)
                cur = {"log": f.name, "model": m.group(1),
                       "prompt": int(m.group(2)), "secs": 0,
                       "stream_chars": 0, "outcome": "abandoned"}
                buf = []
                continue
            if cur is None:
                continue
            if line.startswith(RX_STREAM):
                buf.append(line[len(RX_STREAM):])
                continue
            m = RX_TIMEOUT.search(line)
            if m:
                text = "\n".join(buf)
                cur["secs"] = int(m.group(1))
                cur["stream_chars"] = len(text)
                cur["outcome"] = ("timeout_complete" if _complete_function(text)
                                  else "timeout_partial" if text.strip()
                                  else "timeout_no_bytes")
                calls.append(cur); cur = None; buf = []
                continue
            m = RX_DONE.search(line)
            if m:
                cur["secs"] = int(m.group(1))
                cur["stream_chars"] = int(m.group(2))
                cur["outcome"] = "empty" if m.group(2) == "0" else "produced"
                calls.append(cur); cur = None; buf = []
                continue
            m = RX_GENFAIL.search(line)
            if m:
                cur["outcome"] = "genfail"
                cur["error"] = m.group(1)
                calls.append(cur); cur = None; buf = []
        # Flush a call the log ends in the middle of. Dropping it silently
        # under-counts exactly the calls that were in flight when the fleet was
        # stopped, which is the population most likely to be interesting.
        if cur:
            cur["stream_chars"] = len("\n".join(buf))
            cur["outcome"] = "abandoned"
            calls.append(cur)
    return calls


def streak_stats(calls: list[dict]) -> dict:
    """Are failures independent, or do they arrive in bursts?

    A burst pattern would point at connection or session state -- something
    that breaks and stays broken. Independence points at each request being
    dropped on its own. The test is the mean length of consecutive-failure
    runs against what a coin with the same success rate would give, 1/p - 1.
    """
    per_log: dict[str, list[str]] = defaultdict(list)
    for c in calls:
        per_log[c["log"]].append(c["outcome"])
    runs: list[int] = []
    for seq in per_log.values():
        n = 0
        for o in seq:
            if o == "produced":
                if n:
                    runs.append(n)
                n = 0
            else:
                n += 1
        if n:
            runs.append(n)
    n_all = len(calls)
    p = sum(1 for c in calls if c["outcome"] == "produced") / max(1, n_all)
    return {"runs": len(runs),
            "mean": statistics.mean(runs) if runs else 0.0,
            "median": statistics.median(runs) if runs else 0.0,
            "longest": max(runs) if runs else 0,
            "p_produced": p,
            "expected_mean": (1 / p - 1) if p else 0.0}


def report(calls: list[dict], by_model: bool = False,
           streaks: bool = False) -> None:
    if not calls:
        print("no worker logs found under automation/logs")
        return
    n = len(calls)
    c = Counter(x["outcome"] for x in calls)
    print(f"\n{n} model call(s) across {len({x['log'] for x in calls})} log(s)\n")
    print(f"{'outcome':22} {'count':>6} {'share':>7}   meaning")
    print("-" * 78)
    meaning = {
        "produced": "a candidate came back",
        "empty": "rc=0 and zero bytes",
        "timeout_no_bytes": "cut off having streamed NOTHING",
        "timeout_partial": "cut off mid-answer",
        "timeout_complete": "cut off but the answer was already whole",
        "genfail": "the call raised before finishing",
        "abandoned": "log ends mid-call (fleet stopped)",
    }
    for o in OUTCOMES:
        if c[o]:
            print(f"{o:22} {c[o]:6d} {100.0*c[o]/n:6.0f}%   {meaning[o]}")
    print("-" * 78)

    dead = n - c["produced"]
    silent = c["timeout_no_bytes"] + c["empty"]
    print(f"\n{silent} of {dead} dead calls ({100.0*silent/max(1,dead):.0f}%) "
          f"returned NOT ONE BYTE.")
    print("That is a transport or provider failure, not a model-quality one:")
    print("no amount of prompt engineering changes the behaviour of a request")
    print("that never produces output.")

    recov = c["timeout_complete"] + c["timeout_partial"]
    print(f"\nsalvageable from the stream: {c['timeout_complete']} complete, "
          f"{c['timeout_partial']} partial "
          f"({100.0*recov/max(1,n):.1f}% of all calls)")
    if c["timeout_complete"] <= 2:
        print("  Timeout salvage is therefore near-worthless as a lever. It is")
        print("  cheap enough to keep, but it is not a fix for dead time.")

    if by_model:
        print("\nby model")
        per = defaultdict(Counter)
        for x in calls:
            per[x["model"]][x["outcome"]] += 1
        cols = [o for o in OUTCOMES if c[o]]
        print(f"  {'model':34}" + "".join(f"{o[:9]:>11}" for o in cols))
        for mdl, cc in sorted(per.items(), key=lambda kv: -sum(kv[1].values())):
            print(f"  {mdl:34}" + "".join(f"{cc.get(o,0):11d}" for o in cols))

    if streaks:
        s = streak_stats(calls)
        print("\nare failures independent, or bursty?")
        print(f"  {s['runs']} dead-runs, longest {s['longest']}, "
              f"median {s['median']:.0f}, mean {s['mean']:.1f}")
        print(f"  independent failures at p_produced={s['p_produced']:.3f} "
              f"would give a mean of {s['expected_mean']:.1f}")
        # Report the SENSITIVITY, not just the verdict. This statistic moves
        # depending on whether `genfail` and `abandoned` count as failures:
        # counting only timeout/empty/produced gives mean 9.2 against an
        # expected 9.2 (independent); counting everything gives 12.8 against
        # 9.9 (mildly bursty). A conclusion that flips on a definitional
        # choice is not a conclusion, and saying so is more useful than
        # picking whichever reading suits the story.
        strict = streak_stats([c for c in calls if c["outcome"] in
                               ("produced", "empty", "timeout_no_bytes",
                                "timeout_partial", "timeout_complete")])
        print(f"  counting only real model answers: mean {strict['mean']:.1f} "
              f"vs {strict['expected_mean']:.1f} expected")
        ratios = [s["mean"] / max(0.01, s["expected_mean"]),
                  strict["mean"] / max(0.01, strict["expected_mean"])]
        if max(ratios) < 1.25:
            print("  -> INDEPENDENT on both readings. Each request fails on")
            print("     its own; not a session that breaks and stays broken.")
        elif min(ratios) > 1.25:
            print("  -> BURSTY on both readings. Something breaks and stays")
            print("     broken; look at session or connection state.")
        else:
            print("  -> INCONCLUSIVE: the verdict flips depending on whether")
            print("     aborted calls count as failures. Do not act on this")
            print(f"     alone. The longest run is {s['longest']}, which is")
            print("     worth looking at directly.")

    print("\nWHAT THE LOGS CANNOT TELL US")
    print("  - stderr on the timeout path is discarded with the killed child,")
    print("    so a provider message (rate limit, auth, model gone) is lost.")
    print("  - no time-to-first-byte, so 'never answered' and 'answered too")
    print("    slowly' are the same record.")
    print("  Both are instrumentation, not analysis. See docs/fleet-dead-time.md")


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    print("\na timeout is classified by WHAT WAS STREAMED, not just that it timed out")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "worker-a.log").write_text(
            "  --- opencode run (m/x, prompt 100 chars, streaming) ---\n"
            "  !! attempt 1 timed out after 90s; trying the next attempt\n"
            "  --- opencode run (m/x, prompt 100 chars, streaming) ---\n"
            "  | void f(void) {\n  |   int a;\n  | }\n"
            "  !! attempt 2 timed out after 90s; trying the next attempt\n"
            "  --- opencode run (m/x, prompt 100 chars, streaming) ---\n"
            "  | void g(void) {\n  |   int a;\n"
            "  !! attempt 3 timed out after 90s; trying the next attempt\n"
            "  --- opencode run (m/y, prompt 200 chars, streaming) ---\n"
            "  --- done in 12s: 0 chars ---\n"
            "  --- opencode run (m/y, prompt 200 chars, streaming) ---\n"
            "  | void h(void) {}\n"
            "  --- done in 20s: 16 chars ---\n", encoding="utf-8")
        calls = parse([d / "worker-a.log"])
    got = [c["outcome"] for c in calls]
    ck(got == ["timeout_no_bytes", "timeout_complete", "timeout_partial",
               "empty", "produced"], f"all five classes separated ({got})")
    ck(calls[0]["stream_chars"] == 0, "a silent timeout records zero bytes")
    ck(calls[1]["stream_chars"] > 0, "a complete one records what it held")
    ck(calls[3]["model"] == "m/y" and calls[3]["prompt"] == 200,
       "model and prompt size are carried on every record")

    print("\nthe independence test can tell the two shapes apart")
    bursty = [{"log": "a", "outcome": o} for o in
              (["produced"] * 5 + ["empty"] * 20 + ["produced"] * 5)]
    s = streak_stats(bursty)
    ck(s["mean"] > s["expected_mean"] * 1.5,
       f"one long burst reads as bursty ({s['mean']:.1f} vs "
       f"{s['expected_mean']:.1f} expected)")
    even = [{"log": "a", "outcome": o} for o in
            (["empty", "produced"] * 15)]
    s2 = streak_stats(even)
    ck(abs(s2["mean"] - s2["expected_mean"]) < 1.0,
       f"strict alternation reads as independent ({s2['mean']:.1f} vs "
       f"{s2['expected_mean']:.1f})")

    print("\nparsing survives the logs it will actually meet")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "worker-b.log").write_text(
            "  --- opencode run (m/x, prompt 10 chars, streaming) ---\n"
            "  | half an answer and then the fleet was stopped\n",
            encoding="utf-8")
        calls = parse([d / "worker-b.log"])
    ck([c["outcome"] for c in calls] == ["abandoned"],
       "a log that ends mid-call yields `abandoned`, not a crash")
    ck(parse([]) == [], "no logs yields no records rather than raising")

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
    ap.add_argument("--by-model", action="store_true")
    ap.add_argument("--streaks", action="store_true")
    ap.add_argument("--json", help="write per-call records here")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    calls = parse(log_files())
    if a.json:
        Path(a.json).write_text(json.dumps(calls, indent=2), encoding="utf-8")
        print(f"wrote {len(calls)} record(s) to {a.json}")
    report(calls, by_model=a.by_model, streaks=a.streaks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
