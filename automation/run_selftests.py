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
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

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
    ap.add_argument("--jobs", type=int, default=4,
                    help="concurrent suites (default 4). Suites that take "
                         "BuildLock always run serially regardless")
    ap.add_argument("--failed-only", action="store_true")
    a = ap.parse_args()

    all_suites = suites()
    if not all_suites:
        print(f"no test_*.py under {HERE}", file=sys.stderr)
        return 2
    parallel = [p for p in all_suites if p.name not in SERIAL]
    serial = [p for p in all_suites if p.name in SERIAL]

    mods = selftest_modules()

    rows: list[tuple[str, bool, float, str]] = []
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        rows.extend(ex.map(lambda p: run_one(p, a.timeout), parallel))
        rows.extend(ex.map(
            lambda p: run_one(p, a.timeout, ("--self-test",)), mods))
    for p in serial:
        rows.append(run_one(p, a.timeout))

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
