#!/usr/bin/env python3
"""Self-tests for the scheduler's queue-ownership guard.

WHAT THIS PROTECTS
    scheduler.py migrates the legacy in-repo queue into ~/sotn-work the first
    time any environment touches it. That is fine for reading and catastrophic
    for writing, because the copies never sync again.

    On 2026-08-02 nine verified matches were reported from the Cowork sandbox.
    Every single call printed "updated" and exited 0. None of them reached the
    live queue: the sandbox had quietly migrated its own 438-record copy and was
    mutating that. The loss was noticed only because a stats call from the
    sandbox disagreed with a stats call through the MCP connector.

    A silent success is the worst possible failure here, so the guard must make
    the write LOUD and NON-ZERO, and must not touch reads.

Run: python3 automation/test_queue_owner.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCHED = REPO / "automation" / "scheduler.py"
FAILS: list[str] = []

REC = ('{"id": "us:ST/RNO0:Demo", "build": "us", "overlay": "ST/RNO0", '
       '"function": "Demo", "status": "todo", "score": 0}\n')


def check(cond: bool, label: str) -> None:
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


def run(queue: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["SOTN_QUEUE"] = str(queue)
    return subprocess.run([sys.executable, str(SCHED), *args],
                          capture_output=True, text=True, env=env, timeout=60)


def test_unstamped_queue_allows_writes() -> None:
    """The live queue has no stamp, because it migrated before the guard
    existed. It must keep working, or the guard breaks the whole harness."""
    print("\ntest_unstamped_queue_allows_writes")
    with tempfile.TemporaryDirectory() as d:
        q = Path(d) / "queue.jsonl"
        q.write_text(REC)
        r = run(q, "report", "--id", "us:ST/RNO0:Demo", "--status", "near")
        check(r.returncode == 0,
              f"report on an unstamped queue exits 0 (got {r.returncode})")
        check("refusing" not in (r.stdout + r.stderr).lower(),
              "no refusal message on an unstamped queue")
        check('"status": "near"' in q.read_text() or '"near"' in q.read_text(),
              "the record was actually written")


def test_stamped_queue_refuses_writes() -> None:
    print("\ntest_stamped_queue_refuses_writes")
    with tempfile.TemporaryDirectory() as d:
        q = Path(d) / "queue.jsonl"
        q.write_text(REC)
        q.with_suffix(".jsonl.from-legacy").write_text("migrated by a test\n")
        before = q.read_text()
        r = run(q, "report", "--id", "us:ST/RNO0:Demo", "--status", "matched",
                "--proof", "fake")
        out = r.stdout + r.stderr
        check(r.returncode != 0,
              f"report on a stamped queue exits NON-ZERO (got {r.returncode})")
        check("refusing to run 'report'" in out,
              "the refusal names the command")
        check("from-legacy" in out,
              "the refusal says how to claim ownership deliberately")
        check(q.read_text() == before,
              "the queue file is byte-identical afterwards")


def test_stamped_queue_still_allows_reads() -> None:
    """A stale read is recoverable; blocking reads would make the sandbox
    useless for triage, which is most of what it is for."""
    print("\ntest_stamped_queue_still_allows_reads")
    with tempfile.TemporaryDirectory() as d:
        q = Path(d) / "queue.jsonl"
        q.write_text(REC)
        q.with_suffix(".jsonl.from-legacy").write_text("migrated by a test\n")
        for cmd in ("stats", "list"):
            r = run(q, cmd)
            check(r.returncode == 0, f"'{cmd}' still exits 0 on a stamped queue")


def test_every_mutating_command_is_covered() -> None:
    """The guard is a name list, so it silently stops protecting anything that
    gets renamed or added. Assert the list against the actual subparsers."""
    print("\ntest_every_mutating_command_is_covered")
    sys.path.insert(0, str(REPO / "automation"))
    src = SCHED.read_text()
    declared = set()
    for line in src.splitlines():
        if 'sub.add_parser("' in line:
            declared.add(line.split('sub.add_parser("')[1].split('"')[0])
    import re
    m = re.search(r"_MUTATING = \{([^}]*)\}", src)
    guarded = {t.strip().strip('"') for t in m.group(1).split(",") if t.strip()}
    readonly = declared - guarded
    check(declared, f"found subcommands: {sorted(declared)}")
    # Anything that writes must be guarded. These are the only safe readers.
    expected_readonly = {"list", "stats", "verify", "show"}
    surprises = readonly - expected_readonly
    check(not surprises,
          f"no unguarded command outside the known readers (surprises: "
          f"{sorted(surprises)})")
    check("report" in guarded and "next" in guarded,
          "report and next are guarded")


def main() -> int:
    for fn in (test_unstamped_queue_allows_writes,
               test_stamped_queue_refuses_writes,
               test_stamped_queue_still_allows_reads,
               test_every_mutating_command_is_covered):
        fn()
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
