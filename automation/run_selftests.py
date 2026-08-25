#!/usr/bin/env python3
"""Run every self-test suite and report one table.

WHY THIS EXISTS
    Each suite is standalone and prints its own reasoning, which is right for
    working on one of them and wrong for answering "is the harness healthy".
    Answering that meant running seventeen commands and reading seventeen
    tails.

    It also closed a reachability gap. The dashboard's diagnostics tab checked
    that every button pointed at an allowlisted script, but never the reverse,
    so eleven allowlisted suites had no button and were quietly never run from
    the UI. Eleven more buttons would have buried the tab; one that runs them
    all is the thing an operator actually wants to click.

SCHEDULING
    Parallel test scripts and module self-tests share one longest-first queue.
    The last measured durations live outside the repository at
    `~/sotn-work/selftest-timings.json`, so scheduling improves without
    dirtying Git. Completion lines are flushed as suites finish.

WHAT IT DOES NOT DO
    It does not build, and it does not touch the queue or `src/`. Every suite
    here is read-only or restores what it touched. `test_connector_surfaces`
    exercises `fleet_stop` against a throwaway file under `logs/`, which is
    gitignored; that is as close to a side effect as this gets.

EXIT CODE
    Non-zero if any suite fails, so it can gate something later if wanted.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import itertools
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
_TIMING_ROOT = Path(os.environ.get(
    "SOTN_SELFTEST_STATE", str(Path.home() / "sotn-work")))
TIMING_CACHE = _TIMING_ROOT / "selftest-timings.json"
JOB_LOGS = _TIMING_ROOT / "jobs"
DEFAULT_JOBS = min(8, max(1, os.cpu_count() or 1))


# Suites that must NOT run concurrently with the others, because they take
# BuildLock or drive a real server. Run them last, serially.
SERIAL = {"test_connector_surfaces.py", "test_journal_replay.py"}

# Modules that carry their own --self-test instead of living in a test_*.py.
# This used to be a printed caveat listing dashboard.py and
# empty_response_audit.py by hand, which is the same reachability gap the
# docstring above describes: the moment a third module grew a --self-test it
# was not run and nobody noticed. Discovered now, so the list cannot go stale.
RX_SELFTEST = re.compile(r"""add_argument\(\s*["']--self-test["']""")


def selftest_modules() -> list[Path]:
    out = []
    for p in sorted(HERE.glob("*.py")):
        if p.name.startswith("test_") or p.name == Path(__file__).name:
            continue
        try:
            if RX_SELFTEST.search(p.read_text(encoding="utf-8", errors="replace")):
                out.append(p)
        except OSError:
            continue
    return out


def suites() -> list[Path]:
    return sorted(HERE.glob("test_*.py"))


def _label(path: Path, args: tuple[str, ...]) -> str:
    return path.name + (" " + " ".join(args) if args else "")


def load_timings() -> dict[str, float]:
    """Load the last durations, recovering once from an existing job log."""
    try:
        raw = json.loads(TIMING_CACHE.read_text(encoding="utf-8"))
        return {str(k): float(v) for k, v in raw.items()}
    except (OSError, ValueError, TypeError):
        pass

    try:
        logs = sorted(
            JOB_LOGS.glob("run_automation-*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return {}
    row = re.compile(r"^(.+?)\s{2,}(?:ok|FAIL)\s+(\d+(?:\.\d+)?)\s{2}")
    for path in logs:
        try:
            found = {}
            for line in path.read_text(
                    encoding="utf-8", errors="replace").splitlines():
                match = row.match(line)
                if match:
                    found[match.group(1).rstrip()] = float(match.group(2))
        except OSError:
            continue
        if found:
            return found
    return {}


def save_timings(rows: list[tuple[str, bool, float, str]]) -> None:
    """Refresh the external scheduling cache without dirtying the repository."""
    try:
        TIMING_CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = TIMING_CACHE.with_name(TIMING_CACHE.name + ".tmp")
        tmp.write_text(
            json.dumps({name: secs for name, _ok, secs, _tail in rows},
                       indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp.replace(TIMING_CACHE)
    except OSError:
        pass


def parallel_work_items(
        test_suites: list[Path],
        modules: list[Path],
        timings: dict[str, float] | None = None,
        ) -> list[tuple[Path, tuple[str, ...]]]:
    """Put both parallel suite classes in one longest-first executor queue.

    The old runner submitted every test_*.py, waited for the slowest one, then
    submitted module self-tests as a second wave. The two independent critical
    paths therefore added together. Unknown suites remain interleaved, while
    measured suites run longest-first so an expensive test cannot start last.
    """
    out: list[tuple[Path, tuple[str, ...]]] = []
    for module, test in itertools.zip_longest(modules, test_suites):
        if module is not None:
            out.append((module, ("--self-test",)))
        if test is not None:
            out.append((test, ()))
    known = timings or {}
    out.sort(key=lambda item: known.get(_label(*item), 0.0), reverse=True)
    return out


def run_one(path: Path, timeout: int,
            args: tuple[str, ...] = ()) -> tuple[str, bool, float, str]:
    t0 = time.time()
    label = path.name + (" " + " ".join(args) if args else "")
    try:
        r = subprocess.run([sys.executable, str(path), *args], cwd=str(REPO),
                           capture_output=True, text=True, timeout=timeout)
        out = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
        tail = out[-1] if out else "(no output)"
        # A suite reports its own verdict; the exit code is the contract.
        return label, r.returncode == 0, time.time() - t0, tail[:90]
    except subprocess.TimeoutExpired:
        return label, False, time.time() - t0, f"TIMED OUT after {timeout}s"
    except OSError as e:
        return label, False, time.time() - t0, f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--timeout", type=int, default=600,
                    help="per suite (default 600)")
    ap.add_argument("--jobs", type=int, default=DEFAULT_JOBS,
                    help=f"concurrent suites (default {DEFAULT_JOBS}). Suites "
                         "that take BuildLock always run serially regardless")
    ap.add_argument("--failed-only", action="store_true")
    ap.add_argument("--self-test", action="store_true",
                    help="exercise runner scheduling without launching suites")
    a = ap.parse_args()

    if a.self_test:
        probes = [HERE / "test_a.py", HERE / "test_b.py"]
        modules = [HERE / "module_a.py", HERE / "module_b.py"]
        work = parallel_work_items(
            probes, modules, {"module_b.py --self-test": 10.0})
        ok = (
            len(work) == 4
            and {p for p, _args in work} == set(probes + modules)
            and {args for p, args in work if p in modules}
                == {("--self-test",)}
            and {args for p, args in work if p in probes} == {()}
            and work[0] == (modules[1], ("--self-test",))
        )
        print("self-test runner scheduling: " + ("PASS" if ok else "FAIL"))
        return 0 if ok else 1

    all_suites = suites()
    if not all_suites:
        print(f"no test_*.py under {HERE}", file=sys.stderr)
        return 2
    parallel = [p for p in all_suites if p.name not in SERIAL]
    serial = [p for p in all_suites if p.name in SERIAL]

    mods = selftest_modules()

    rows: list[tuple[str, bool, float, str]] = []
    t0 = time.time()
    work = parallel_work_items(parallel, mods, load_timings())
    with cf.ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        pending = {
            ex.submit(run_one, path, a.timeout, args): (path, args)
            for path, args in work
        }
        complete = 0
        for future in cf.as_completed(pending):
            row = future.result()
            rows.append(row)
            complete += 1
            print(f"[selftests] {complete}/{len(work)} {row[0]}: "
                  f"{'ok' if row[1] else 'FAIL'} in {row[2]:.1f}s",
                  flush=True)
    for p in serial:
        row = run_one(p, a.timeout)
        rows.append(row)
        print(f"[selftests] serial {row[0]}: "
              f"{'ok' if row[1] else 'FAIL'} in {row[2]:.1f}s",
              flush=True)

    save_timings(rows)
    rows.sort(key=lambda r: (r[1], r[0]))          # failures first
    bad = [r for r in rows if not r[1]]
    print(f"{'suite':<44}{'':<4}{'secs':>6}  verdict")
    print("-" * 96)
    for name, ok, secs, tail in rows:
        if a.failed_only and ok:
            continue
        print(f"{name:<44}{'ok' if ok else 'FAIL':<4}{secs:>6.1f}  {tail}")
    print("-" * 96)
    print(f"{len(rows) - len(bad)}/{len(rows)} suites passed "
          f"in {time.time() - t0:.1f}s wall")
    if bad:
        print("\nFAILED: " + ", ".join(r[0] for r in bad))
    print(f"\n{len(parallel) + len(serial)} test_*.py suite(s) plus "
          f"{len(mods)} module(s) carrying their own --self-test, discovered "
          f"by scanning for the flag rather than from a hand-kept list.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
