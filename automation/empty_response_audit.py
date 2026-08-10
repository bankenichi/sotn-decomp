#!/usr/bin/env python3
"""How often does each model return nothing, and what does that cost?

WHY THIS EXISTS
    An empty response is the most expensive kind of failure in this harness. It
    is not free and it is not fast: the call runs its full timeout, is retried,
    and the function is then requeued, so the same work is paid for again later.
    A model that fails loudly is cheaper than one that returns rc=0 with zero
    bytes after 382 seconds.

    "deepseek is coming up empty" needs to be a number before it justifies
    switching models, because the last three model decisions in this project
    were each reversed by measurement (see ZEN-FREE-MODELS.md, which retracts
    its own "not the model" conclusion).

WHAT IT DOES NOT MEASURE
    Queue damage, because there is none. worker_direct.py:3238 already requeues
    a function to `todo` when no candidate was produced, precisely so a broken
    model cannot escalate work it never evaluated. That was the fix for the
    2026-07-21 escalation spike. The cost here is time and quota, not status.

DATA
    automation/logs/worker-*.log for the current fleet, plus every run kept
    under automation/logs/archive/. fleet_start used to `rm -f` the logs on each
    launch, so history before archiving is simply gone; a small sample here
    usually means the fleet was restarted, not that little happened.

Usage:
    python3 automation/empty_response_audit.py
    python3 automation/empty_response_audit.py --by-prompt-size
    python3 automation/empty_response_audit.py --self-test
"""
from __future__ import annotations

import argparse
import time
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "automation" / "logs"

RX_RUN = re.compile(r"opencode run \((opencode/[\w.\-]+), prompt (\d+) chars")
RX_DONE = re.compile(r"--- done in (\d+)s: (\d+) chars ---")
RX_TIMEOUT = re.compile(r"attempt \d+ timed out after (\d+)s")
RX_REQUEUE = re.compile(r"REQUEUE (\S+): no candidate produced")


RX_ABORT = re.compile(
    r"^\s*!!\s*(?:degenerate reasoning|degenerate output|salvage aborted)\s*:?\s*(.*)$",
    re.M)


def degen_audit(paths: list[Path], context: int = 26) -> None:
    """Are the degeneration aborts CORRECT, or are they cutting off real work?

    WHY THIS IS NOT THE SAME QUESTION AS "does the detector fire"
        Every existing check on these detectors asks whether they catch a
        runaway. None asks what they killed. A detector that aborts a model
        mid-derivation is worse than no detector: the run still costs its
        tokens, and the answer it was about to produce is gone with no trace
        that anything was lost.

        So this scores the OPPOSITE direction. For every abort in the logs it
        pulls the text immediately before it and classifies what the model was
        actually doing.

    HOW A LINE IS JUDGED
        The detectors fire on SHAPE, so the audit judges shape too:

          runaway   the preceding lines really are near-identical, ascending,
                    or a register dump. The abort was right.
          circling  distinct sentences, but the same question restated. The
                    abort is defensible: this is the 800-restart failure mode,
                    and it does not resolve on its own.
          working   the preceding lines are a normal derivation -- reading the
                    asm, naming offsets, writing C. A false positive, and the
                    one that costs matches.

        `working` is the number that matters. Anything above a few percent
        means the thresholds are too tight.
    """
    seen: dict[str, int] = defaultdict(int)
    examples: dict[str, list] = defaultdict(list)
    by_reason: dict[str, dict] = defaultdict(lambda: {"n": 0, "working": 0})
    # The live rule, so this reports on the code as it stands rather than on a
    # copy that can drift from it.
    try:
        sys.path.insert(0, str(REPO / "automation" / "win"))
        os.environ.setdefault("MODEL_BACKEND", "zen")
        from worker_direct import _enumeration_loop as _enum_rule  # type: ignore
    except Exception:                                       # noqa: BLE001
        _enum_rule = None
    RX_DECL = re.compile(r"^\s*(?:s32|s16|u8|u16|u32|s8)\s+\w+\d+;\s*$")
    RX_REG = re.compile(r"^\s*\w+\s+temp_[a-z]\d?(?:_\d+)?;\s*$")
    RX_ASM = re.compile(r"^\s*/\*\s*[0-9A-F]+\s+[0-9A-F]+\s+[0-9A-F]+\s*\*/")
    RX_RESTART = re.compile(r"^\s*(Actually|Wait|Hmm|But wait|Alternatively|"
                            r"Let me|OK|Hold on)\b", re.I)
    # A derivation looks like this: it names concrete things.
    RX_WORK = re.compile(r"0x[0-9A-Fa-f]+|->\w+|\b(lw|sw|lh|sh|lbu|addiu|"
                         r"beq|bne|jal|sll|sra|andi|ori|lui)\b|[;{}]")

    for p in paths:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            m = RX_ABORT.match(line)
            if not m:
                continue
            why = (m.group(1) or "").strip()[:48]
            before = [l for l in lines[max(0, i - context):i] if l.strip()]
            if not before:
                seen["no-context"] += 1
                continue
            tail = before[-14:]
            structural = sum(bool(RX_DECL.match(l) or RX_REG.match(l)
                                  or RX_ASM.match(l)) for l in tail)
            norm = [re.sub(r"\d+", "#", l.strip()) for l in tail]
            near_same = len(set(norm)) <= max(2, len(norm) // 4)
            restarts = sum(bool(RX_RESTART.match(l)) for l in tail)
            worky = sum(bool(RX_WORK.search(l)) for l in tail)

            if structural >= 6 or near_same:
                kind = "runaway"
            elif restarts >= 3:
                kind = "circling"
            elif worky >= 8:
                kind = "working"
            else:
                kind = "unclear"
            # WOULD THE CURRENT RULE STILL FIRE? The logs record what the
            # detector did at the time; replaying the context through today's
            # code is the only way to tell whether a change actually helped,
            # as opposed to whether the old aborts are still in the file.
            if _enum_rule is not None and why.startswith("enumeration loop"):
                if not _enum_rule(tail):
                    seen["now-spared"] += 1
            seen[kind] += 1
            by_reason[why or "(no reason given)"]["n"] += 1
            by_reason[why or "(no reason given)"]["working"] += (kind == "working")
            if len(examples[kind]) < 3:
                examples[kind].append((p.name, why, tail[-3:]))

    total = sum(seen.values())
    if not total:
        print("no degeneration aborts in this window. Nothing to judge.")
        return
    print(f"\n{total} degeneration abort(s) examined\n")
    print(f"{'verdict':<12}{'count':>7}{'share':>8}   what it means")
    print("-" * 78)
    order = [("runaway", "correct: the stream really had run away"),
             ("circling", "defensible: restating, does not self-resolve"),
             ("unclear", "cannot tell from shape alone; read these"),
             ("working", "FALSE POSITIVE: killed a real derivation"),
             ("no-context", "abort with nothing before it; parser gap")]
    for k, meaning in order:
        if seen[k]:
            print(f"{k:<12}{seen[k]:>7}{seen[k]/total:>7.0%}   {meaning}")
    print("-" * 78)
    fp = seen["working"] / total
    print(f"\nfalse-positive rate: {fp:.1%}"
          + ("  -- acceptable" if fp <= 0.03 else
             "  -- TOO HIGH, loosen the thresholds"))

    # WHICH DETECTOR is wrong matters more than the total. They have separate
    # thresholds and separate failure modes; a single rate hides which one to
    # touch and invites loosening all of them.
    if seen["now-spared"]:
        n_enum = sum(c["n"] for r, c in by_reason.items()
                     if r.startswith("enumeration loop"))
        print(f"\nreplayed through the CURRENT enumeration rule: "
              f"{seen['now-spared']} of {n_enum} of those aborts would no "
              f"longer fire ({seen['now-spared']/max(n_enum,1):.0%}). The rule "
              f"now requires the numbers to REPEAT; a table of distinct "
              f"offsets is work, not a loop.")

    print(f"\nby abort reason (the detector that fired):")
    print(f"{'reason':<44}{'total':>7}{'working':>9}{'FP rate':>9}")
    print("-" * 78)
    for reason, c in sorted(by_reason.items(), key=lambda kv: -kv[1]["n"]):
        n, w = c["n"], c["working"]
        print(f"{reason[:43]:<44}{n:>7}{w:>9}{w/n:>8.0%}")
    for k in ("working", "unclear"):
        if examples[k]:
            print(f"\n{k} examples (the last 3 lines before each abort):")
            for name, why, tail in examples[k]:
                print(f"  {name}  [{why}]")
                for l in tail:
                    print(f"      {l.strip()[:96]}")


def parse_since(spec: str) -> float:
    """A cutoff timestamp from a human spec. Raises ValueError if unparseable.

    Accepts `90m`, `6h`, `3d`, `today`, `2026-08-09`, or a fleet archive stamp
    `20260809-200431`. The stamp form matters because that is exactly how
    fleet_start names its archive directories, so "since the run before last"
    is a value you can read straight off the log tab.
    """
    spec = (spec or "").strip().lower()
    now = time.time()
    if spec in ("", "all"):
        return 0.0
    if spec == "today":
        t = time.localtime(now)
        return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1))
    m = re.fullmatch(r"(\d+)\s*([mhd])", spec)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        return now - n * {"m": 60, "h": 3600, "d": 86400}[unit]
    for fmt in ("%Y%m%d-%H%M%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return time.mktime(time.strptime(spec, fmt))
        except ValueError:
            continue
    raise ValueError(
        f"cannot read --since {spec!r}; use 90m, 6h, 3d, today, "
        f"2026-08-09, or an archive stamp like 20260809-200431")


def log_files(since: float = 0.0, current_only: bool = False,
              archived: bool = False) -> list[Path]:
    """Worker logs, optionally windowed.

    ARCHIVED HISTORY IS OPT-IN. This used to pool logs/archive/ into every
    report by default, so a change made today was averaged against thousands
    of calls from runs that predate it. Reported 2026-08-09: "the logs from
    the old calls are holding the statistics back". Pooling is right for
    "which model is best" and wrong for "did that fix work", and the common
    question is the second one, so the common case is now the default. Pass
    archived=True to get the whole history back.

    current_only means the run that fleet.pids describes, anchored on that
    file's mtime because fleet_start rewrites it at launch.

    "the live logs" alone is NOT that run, which is the trap here:
    fleet_start archives only the tags it is about to start, so after a cli
    fleet is replaced by a zen fleet the old worker-oc-*.log files are still
    sitting in logs/ untouched. Taking every live log therefore mixed 68
    laguna calls from a previous cli run into what claimed to be the current
    zen run. Filtering by the pidfile's mtime keeps only workers that have
    written since this fleet started.
    """
    out = list(LOGS.glob("worker-*.log"))
    if current_only:
        pids = LOGS / "fleet.pids"
        anchor = pids.stat().st_mtime if pids.exists() else 0.0
        if not anchor and out:
            # No pidfile (a stopped fleet clears it). Fall back to the newest
            # log and a short trailing window, and the caller is told.
            anchor = max(p.stat().st_mtime for p in out) - 3600
        since = max(since, anchor)
    elif archived:
        arch = LOGS / "archive"
        if arch.is_dir():
            out += list(arch.rglob("worker-*.log"))
    if since:
        out = [p for p in out if p.stat().st_mtime >= since]
    return sorted(out)


def scan(paths: list[Path]) -> tuple[dict, list, int]:
    """Per-model tallies, per-call records, and requeue count."""
    stats: dict = defaultdict(
        lambda: {"calls": 0, "empty": 0, "produced": 0, "timeouts": 0,
                 "secs_empty": 0, "secs_produced": 0, "chars": 0})
    calls: list = []
    requeues = 0
    for f in paths:
        model = None
        for line in f.read_text(errors="ignore").splitlines():
            m = RX_RUN.search(line)
            if m:
                model, prompt = m.group(1), int(m.group(2))
                stats[model]["calls"] += 1
                calls.append({"model": model, "prompt": prompt,
                              "outcome": "unknown", "secs": 0})
                continue
            if RX_REQUEUE.search(line):
                requeues += 1
                continue
            m = RX_DONE.search(line)
            if m and model:
                secs, chars = int(m.group(1)), int(m.group(2))
                if chars == 0:
                    stats[model]["empty"] += 1
                    stats[model]["secs_empty"] += secs
                    if calls:
                        calls[-1].update(outcome="empty", secs=secs)
                else:
                    stats[model]["produced"] += 1
                    stats[model]["secs_produced"] += secs
                    stats[model]["chars"] += chars
                    if calls:
                        calls[-1].update(outcome="produced", secs=secs)
                continue
            m = RX_TIMEOUT.search(line)
            if m and model:
                stats[model]["timeouts"] += 1
                stats[model]["secs_empty"] += int(m.group(1))
                if calls:
                    calls[-1].update(outcome="timeout", secs=int(m.group(1)))
    return stats, calls, requeues


def report(stats: dict, calls: list, requeues: int, n_logs: int) -> None:
    print(f"\n{n_logs} log file(s), {len(calls)} model call(s), "
          f"{requeues} function(s) requeued to todo\n")
    if not stats:
        print("No opencode calls found. Either no cli fleet has run since the "
              "logs were last cleared, or only llama workers ran.")
        return

    print(f"{'model':32s} {'calls':>5} {'empty':>6} {'t/out':>6} {'ok':>4} "
          f"{'dead%':>6} {'wasted':>8} {'useful':>8}")
    print("-" * 82)
    tot_waste = tot_useful = 0
    for model, d in sorted(stats.items(), key=lambda kv: -kv[1]["calls"]):
        dead = d["empty"] + d["timeouts"]
        n = max(1, d["calls"])
        waste_m = d["secs_empty"] / 60.0
        useful_m = d["secs_produced"] / 60.0
        tot_waste += waste_m
        tot_useful += useful_m
        print(f"{model:32s} {d['calls']:5d} {d['empty']:6d} {d['timeouts']:6d} "
              f"{d['produced']:4d} {100.0*dead/n:5.0f}% "
              f"{waste_m:7.1f}m {useful_m:7.1f}m")
    print("-" * 82)
    total = tot_waste + tot_useful
    pct = (100.0 * tot_waste / total) if total else 0.0
    print(f"{'TOTAL':32s} {'':5} {'':6} {'':6} {'':4} {'':6} "
          f"{tot_waste:7.1f}m {tot_useful:7.1f}m")
    print(f"\n{pct:.0f}% of model time produced nothing.")

    # Sample-size honesty. Three calls is an anecdote; this project has already
    # drawn a wrong model conclusion from an unbalanced tally where one model
    # simply had more runs than the others.
    thin = [m for m, d in stats.items() if d["calls"] < 10]
    if thin:
        print(f"\nCAUTION: fewer than 10 calls for {', '.join(sorted(thin))}. "
              f"Not enough to rank models. ZEN-FREE-MODELS.md records a "
              f"previous wrong call made exactly this way.")


def by_prompt_size(calls: list) -> None:
    """Failure rate against prompt size, split by FAILURE MODE.

    This used to print one `dead` column combining empty and timeout, under
    the heading "empty rate". Those are different failures with different
    causes -- an empty response is the provider returning rc=0 and no bytes,
    a timeout is us cutting the call off -- and merging them hid the only
    real signal in the table.

    It also let a stale claim survive. The docstring said prompt size was
    "the one variable known to matter", citing 0% / 61% / 83% dead across the
    size buckets. That was 123 calls on 2026-08-03. At 1042 calls the combined
    figure is 88% / 82% / 84%: FLAT, and slightly WORSE for the smallest
    prompts. Whatever the old number measured, it does not reproduce.
    """
    print("\nfailure mode by prompt size")
    buckets = [(0, 5000), (5000, 10000), (10000, 20000), (20000, 10**9)]
    print(f"{'prompt chars':>16} {'calls':>6} {'empty':>6} {'empty%':>7} "
          f"{'t/out':>6} {'t/out%':>7} {'ok':>5} {'dead%':>7}")
    rows = []
    for lo, hi in buckets:
        sel = [c for c in calls if lo <= c["prompt"] < hi]
        if not sel:
            continue
        n = len(sel)
        empty = sum(1 for c in sel if c["outcome"] == "empty")
        tout = sum(1 for c in sel if c["outcome"] == "timeout")
        ok = sum(1 for c in sel if c["outcome"] == "produced")
        label = f"{lo//1000}k-{hi//1000}k" if hi < 10**9 else f"{lo//1000}k+"
        rows.append((label, n, empty, tout, ok))
        print(f"{label:>16} {n:6d} {empty:6d} {100.0*empty/n:6.0f}% "
              f"{tout:6d} {100.0*tout/n:6.0f}% {ok:5d} "
              f"{100.0*(empty+tout)/n:6.0f}%")

    if len(rows) < 2:
        return
    # State the conclusion rather than leaving a table for someone to
    # misremember later. Spread is the honest summary: a variable that
    # "predicts" a failure should separate the buckets.
    for name, idx in (("empty", 2), ("timeout", 3)):
        rates = [100.0 * r[idx] / r[1] for r in rows]
        spread = max(rates) - min(rates)
        verdict = ("tracks prompt size" if spread >= 25 else
                   "does NOT track prompt size")
        print(f"\n  {name:8} {' / '.join(f'{x:.0f}%' for x in rates)}"
              f"   spread {spread:.0f} points -> {verdict}")

    # THE CONFOUND. ATTEMPT_BUDGET was 191s until 2026-08-03 and is 90s after,
    # so a timeout means different things in different halves of this sample
    # and the timeout column cannot be read as a property of prompt size
    # alone. The cap in force is recoverable per call: a timeout lands AT the
    # cap, so the durations cluster around whichever one was active.
    touts = sorted(c["secs"] for c in calls if c["outcome"] == "timeout")
    if touts:
        era90 = sum(1 for s in touts if s <= 120)
        era191 = sum(1 for s in touts if 120 < s <= 250)
        older = len(touts) - era90 - era191
        print(f"\ntimeout durations: {len(touts)} total, "
              f"{era90} at <=120s (the 90s cap), {era191} at 121-250s "
              f"(the old 191s cap), {older} longer")
        if era90 and era191:
            print("  MIXED SAMPLE: this spans both caps, so the t/out column "
                  "above is partly an artefact of when the call ran, not of "
                  "how big its prompt was. Re-run once the fleet has "
                  "accumulated calls entirely under the 90s cap.")

    print("\nOn argv, anything over 32767 chars never started at all "
          "(ZEN-FREE-MODELS.md). The prompt now goes on stdin, so that "
          "mechanism is gone; any surviving correlation is a different one, "
          "and the numbers above are the only thing that should be quoted "
          "for it.")


def timing(calls: list) -> None:
    """How long a call takes, split by whether it produced anything.

    This is the number a timeout should be set from. The two populations are
    almost disjoint: productive work finishes fast, dead work runs the clock
    out, so a cap placed between them costs little and saves a lot.
    """
    import statistics as stat
    prod = sorted(c["secs"] for c in calls if c["outcome"] == "produced")
    dead = sorted(c["secs"] for c in calls
                  if c["outcome"] in ("empty", "timeout"))
    if not prod or not dead:
        print("\nnot enough completed calls to time")
        return

    def pct(v, p):
        return v[min(len(v) - 1, int(len(v) * p))]

    print(f"\n{'':10} {'n':>4} {'min':>6} {'median':>7} {'p75':>6} "
          f"{'p90':>6} {'max':>6}")
    for name, v in (("produced", prod), ("dead", dead)):
        print(f"{name:10} {len(v):4d} {min(v):5d}s {int(stat.median(v)):6d}s "
              f"{pct(v, .75):5d}s {pct(v, .90):5d}s {max(v):5d}s")

    print("\nwhat a tighter per-attempt cap would cost and save")
    print(f"{'cap':>6} {'good calls lost':>17} {'dead time saved':>17}")
    for cap in (60, 90, 120, 150, 180, 240, 300, 382):
        lost = sum(1 for x in prod if x > cap)
        saved = sum(max(0, x - cap) for x in dead) / 60.0
        print(f"{cap:5d}s {lost:8d}/{len(prod):<8} {saved:15.1f}m")
    print("\nA cut good call is not a lost function: with no candidate the "
          "record is requeued to `todo` and retried, so the cost is a retry.")


def self_test() -> int:
    import tempfile
    fails = []

    def ck(c, l):
        print(("  ok   " if c else "  FAIL ") + l)
        if not c:
            fails.append(l)

    sample = """[worker] us:BOSS/BO6:fn_a
  --- opencode run (opencode/deepseek-v4-flash-free, prompt 5166 chars, streaming) ---
  --- done in 48s: 0 chars ---
  !! empty response (1/5)
  --- opencode run (opencode/deepseek-v4-flash-free, prompt 5166 chars, streaming) ---
  --- done in 60s: 2474 chars ---
  --- opencode run (opencode/nemotron-3-ultra-free, prompt 17918 chars, streaming) ---
  !! attempt 1 timed out after 382s; trying the next attempt
[worker] REQUEUE fn_b: no candidate produced in 4 error(s); back to todo
"""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "worker-oc-1.log"
        p.write_text(sample)
        stats, calls, requeues = scan([p])

        print("\nparsing")
        ck(len(calls) == 3, f"one record per opencode call ({len(calls)})")
        ck(requeues == 1, "requeues are counted")
        ds = stats["opencode/deepseek-v4-flash-free"]
        ck(ds["calls"] == 2 and ds["empty"] == 1 and ds["produced"] == 1,
           f"empty and produced are separated ({ds['empty']}/{ds['produced']})")
        ck(ds["secs_empty"] == 48 and ds["secs_produced"] == 60,
           "time is attributed to the outcome it bought")
        nm = stats["opencode/nemotron-3-ultra-free"]
        ck(nm["timeouts"] == 1 and nm["secs_empty"] == 382,
           "a timeout counts as dead time, not as a produced call")

        print("\na timeout is distinct from an empty body")
        ck(nm["empty"] == 0,
           "a timed-out call is not also counted as empty; they have different "
           "causes and different mitigations")

        print("\nprompt size is captured for correlation")
        ck({c["prompt"] for c in calls} == {5166, 17918},
           "prompt sizes are recorded per call")

        print("\nempty log")
        s2, c2, r2 = scan([])
        ck(s2 == {} and c2 == [] and r2 == 0, "no logs yields empty tallies")

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
    ap.add_argument("--by-prompt-size", action="store_true")
    ap.add_argument("--timing", action="store_true",
                    help="duration split by productive vs dead, and what a "
                         "tighter cap would cost")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--degen-audit", action="store_true",
                    help="judge the degeneration aborts THEMSELVES: how many "
                         "killed a runaway vs a real derivation. Every other "
                         "check asks whether the detector fires; this asks "
                         "what it hit")
    ap.add_argument("--since", default="",
                    help="only logs at or after this point: 90m, 6h, 3d, "
                         "today, 2026-08-09, or an archive stamp such as "
                         "20260809-200431. Default is every run ever "
                         "recorded, which answers 'which model is best' but "
                         "NOT 'did today's change help'")
    ap.add_argument("--archived", action="store_true",
                    help="also read logs/archive/, i.e. every run ever "
                         "recorded. Off by default: pooled history buries a "
                         "recent change. Use it to rank models, not to judge "
                         "a fix")
    ap.add_argument("--current", action="store_true",
                    help="only the CURRENT fleet run (fleet_start archives "
                         "the previous run's logs, so the live logs are "
                         "exactly the run in progress)")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    try:
        cutoff = parse_since(a.since)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    every = log_files(archived=True)
    paths = log_files(cutoff, a.current, a.archived)
    # STATE THE WINDOW, ALWAYS. A filtered report that looks like an
    # unfiltered one is how a partial number gets quoted as a total.
    if a.current:
        _pids = LOGS / "fleet.pids"
        _anch = ("fleet.pids at " + time.strftime(
                     "%Y-%m-%d %H:%M", time.localtime(_pids.stat().st_mtime))
                 if _pids.exists() else
                 "NO fleet.pids (fleet stopped) -- falling back to the last "
                 "hour of the newest log, which may still span two runs")
        print(f"\nWINDOW: the latest fleet run only "
              f"({len(paths)} of {len(every)} logs; anchored on {_anch})")
    elif cutoff:
        print(f"\nWINDOW: since {time.strftime('%Y-%m-%d %H:%M', time.localtime(cutoff))} "
              f"({len(paths)} of {len(every)} logs; "
              f"{len(every) - len(paths)} older ones excluded)")
    elif a.archived:
        print(f"\nWINDOW: every run ever recorded ({len(paths)} logs, "
              f"archive included). Good for ranking models; a change made "
              f"today is averaged against all of it.")
    else:
        print(f"\nWINDOW: current logs only ({len(paths)} of {len(every)}; "
              f"{len(every) - len(paths)} archived runs excluded). "
              f"Add --archived for the full history.")
    if not paths:
        print("no logs in that window.")
        return 0
    stats, calls, requeues = scan(paths)
    report(stats, calls, requeues, len(paths))
    if a.by_prompt_size:
        by_prompt_size(calls)
    if a.timing:
        timing(calls)
    if a.degen_audit:
        degen_audit(paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
