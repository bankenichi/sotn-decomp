#!/usr/bin/env python3
"""Regression tests for the consolidated self-test scheduler."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

AUTO = Path(__file__).resolve().parent
sys.path.insert(0, str(AUTO))

import run_selftests as runner  # noqa: E402


def main() -> int:
    fails: list[str] = []

    def check(condition: bool, label: str) -> None:
        print(("ok   " if condition else "FAIL ") + label)
        if not condition:
            fails.append(label)

    tests = [AUTO / "test_a.py", AUTO / "test_b.py"]
    modules = [AUTO / "module_a.py", AUTO / "module_b.py"]
    try:
        work = runner.parallel_work_items(
            tests, modules, {"module_b.py --self-test": 10.0})
    except AttributeError:
        work = []

    check(len(work) == 4,
          "parallel test scripts and module self-tests share one work queue")
    check({path for path, _args in work} == set(tests + modules),
          "the combined queue retains every discovered suite")
    check({args for path, args in work if path in modules} == {("--self-test",)},
          "module suites retain their --self-test argument")
    check({args for path, args in work if path in tests} == {()},
          "test scripts retain their argument-free invocation")
    check(work and work[0] == (modules[1], ("--self-test",)),
          "the longest measured suite is scheduled first")
    check(1 <= runner.DEFAULT_JOBS <= 8,
          "the default worker count is bounded to the verified ceiling")

    selected_tests, selected_modules, missing = runner.select_named(
        tests, modules, ["test_b.py", "module_a.py"])
    check(selected_tests == [tests[1]] and selected_modules == [modules[0]],
          "--only selects exact test and module filenames")
    check(not missing, "known --only suite names are accepted")
    _tests, _modules, missing = runner.select_named(
        tests, modules, ["test"])
    check(not _tests and not _modules and missing == ["test"],
          "--only refuses substrings instead of silently broadening scope")

    old_cache, old_logs = runner.TIMING_CACHE, runner.JOB_LOGS
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            runner.TIMING_CACHE = root / "selftest-timings.json"
            runner.JOB_LOGS = root / "jobs"
            runner.JOB_LOGS.mkdir()
            (runner.JOB_LOGS / "run_automation-probe.log").write_text(
                f"{'slow.py --self-test':<44}ok    12.3  all checks passed\n",
                encoding="utf-8",
            )
            recovered = runner.load_timings()
            runner.save_timings([
                ("slow.py --self-test", True, 12.3, "all checks passed")
            ])
            cached = json.loads(runner.TIMING_CACHE.read_text(encoding="utf-8"))
            failing = root / "nested_failure.py"
            failing.write_text(
                "print('specific nested failure detail')\n"
                "raise SystemExit(1)\n",
                encoding="utf-8",
            )
            failure_row = runner.run_one(failing, timeout=5)
        check(recovered.get("slow.py --self-test") == 12.3,
              "timings recover from an existing job table")
        check(cached.get("slow.py --self-test") == 12.3,
              "the refreshed timing cache is valid JSON")
        check(not failure_row[1] and
              "specific nested failure detail" in failure_row[3],
              "failed nested suites retain actionable diagnostic output")
    finally:
        runner.TIMING_CACHE, runner.JOB_LOGS = old_cache, old_logs

    if fails:
        print(f"{len(fails)} failed")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
