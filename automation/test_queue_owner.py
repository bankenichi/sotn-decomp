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

import ast
import json
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


def test_report_preserves_complete_evidence() -> None:
    """Queue notes and proofs are evidence, not display summaries. Neither a
    direct report nor --keep-note accumulation may silently shorten them."""
    print("\ntest_report_preserves_complete_evidence")
    with tempfile.TemporaryDirectory() as d:
        q = Path(d) / "queue.jsonl"
        q.write_text(REC)
        first = "first derivation: " + ("A" * 800)
        second = "second derivation: " + ("B" * 800)
        proof = "build proof: " + ("C" * 700)

        r = run(q, "report", "--id", "us:ST/RNO0:Demo", "--status", "near",
                "--notes", first, "--proof", proof)
        check(r.returncode == 0, "the first long report succeeds")
        record = json.loads(q.read_text().splitlines()[0])
        check(record.get("notes") == first,
              "a direct report preserves the complete note")
        check(record.get("proof") == proof,
              "a direct report preserves the complete proof")

        r = run(q, "report", "--id", "us:ST/RNO0:Demo", "--status", "near",
                "--notes", second, "--keep-note")
        check(r.returncode == 0, "the prepending long report succeeds")
        record = json.loads(q.read_text().splitlines()[0])
        check(record.get("notes") == second + " || " + first,
              "--keep-note preserves both complete derivations")


def test_report_preserves_structured_search_verdict() -> None:
    """Search authority must survive without being reconstructed from prose."""
    print("\ntest_report_preserves_structured_search_verdict")
    with tempfile.TemporaryDirectory() as d:
        q = Path(d) / "queue.jsonl"
        q.write_text(REC)
        r = run(
            q, "report", "--id", "us:ST/RNO0:Demo", "--status", "deferred",
            "--verdict-kind", "permuter-exhausted", "--verdict-seed-current",
            "--verdict-source", "test receipt")
        check(r.returncode == 0, "a structured verdict report succeeds")
        record = json.loads(q.read_text().splitlines()[0])
        verdict = record.get("search_verdict") or {}
        check(verdict.get("kind") == "permuter-exhausted",
              "the verdict kind is stored structurally")
        check(verdict.get("seed_current") is True,
              "current-seed authority is stored as a boolean")
        check(verdict.get("source") == "test receipt",
              "the structured verdict retains its evidence source")

        listed = run(q, "list", "--status", "deferred", "--json")
        check(listed.returncode == 0, "structured queue listing succeeds")
        try:
            records = json.loads(listed.stdout)
        except json.JSONDecodeError:
            records = []
        check(records and records[0].get("search_verdict") == verdict,
              "the scheduler exposes structured evidence without flattening it")


def test_queue_writers_do_not_slice_evidence() -> None:
    """Catch silent caps in queue records and direct scheduler calls."""
    print("\ntest_queue_writers_do_not_slice_evidence")
    offenders: list[str] = []

    def contains_slice(value: ast.AST) -> bool:
        return any(isinstance(part, ast.Subscript) and
                   isinstance(part.slice, ast.Slice)
                   for part in ast.walk(value))

    def evidence_target(target: ast.AST) -> bool:
        return (isinstance(target, ast.Subscript) and
                isinstance(target.slice, ast.Constant) and
                target.slice.value in {"notes", "proof"})

    for path in (REPO / "automation").rglob("*.py"):
        if ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                targets = node.targets
                value = node.value
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets = [node.target]
                value = node.value
            else:
                targets = []
                value = None
            if (value is not None and any(evidence_target(t) for t in targets)
                    and contains_slice(value)):
                offenders.append(
                    f"{path.relative_to(REPO)}:{getattr(value, 'lineno', 0)}")

            if isinstance(node, (ast.List, ast.Tuple)):
                values = node.elts
            elif isinstance(node, ast.Call):
                values = node.args
            else:
                continue
            for index, item in enumerate(values[:-1]):
                if not (isinstance(item, ast.Constant) and
                        item.value in {"--notes", "--proof"}):
                    continue
                value = values[index + 1]
                if contains_slice(value):
                    offenders.append(
                        f"{path.relative_to(REPO)}:{getattr(value, 'lineno', 0)}")
    check(not offenders,
          "no queue writer silently slices --notes or --proof arguments "
          f"(offenders: {offenders})")


def test_worker_reports_preserve_prior_notes() -> None:
    """Both Windows transports must make append-only notes the default."""
    print("\ntest_worker_reports_preserve_prior_notes")

    def load_transport(path: Path):
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        fn = next(node for node in tree.body
                  if isinstance(node, ast.FunctionDef) and
                  node.name == "_scheduler_report_transport")
        module = ast.Module(body=[fn], type_ignores=[])
        ast.fix_missing_locations(module)
        namespace = {"json": json}
        exec(compile(module, str(path), "exec"), namespace)
        return namespace["_scheduler_report_transport"]

    workers = (
        REPO / "automation" / "win" / "worker_direct.py",
        REPO / "automation" / "win" / "worker_win.py",
    )
    for path in workers:
        transport = load_transport(path)
        forwarded, payload = transport((
            "report", "--id", "us:ST/RNO0:Demo", "--status", "near",
            "--notes", "new evidence"))
        check(forwarded.count("--keep-note") == 1,
              f"{path.name} adds exactly one --keep-note")
        check("--notes" not in forwarded and
              json.loads(payload or "{}").get("notes") == "new evidence",
              f"{path.name} still uses lossless stdin evidence")

        forwarded, _ = transport((
            "report", "--id", "us:ST/RNO0:Demo", "--status", "near",
            "--keep-note"))
        check(forwarded.count("--keep-note") == 1,
              f"{path.name} does not duplicate explicit --keep-note")


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
    #
    # `snapshot` is on this list and `restore` is deliberately NOT. snapshot
    # borrows the writer's exclusive lock so a running fleet cannot be caught
    # mid-write, but it returns the records unchanged; the queue's content is
    # identical afterwards. Guarding it would be actively wrong: the guard fires
    # when SOTN_QUEUE points at a read-only migrated copy, and taking a BACKUP
    # of a copy you are worried about is exactly the moment you want the tool to
    # work. restore replaces every record and is guarded.
    #
    # This check caught snapshot the moment it was added, on 2026-08-17, which
    # is the whole point of asserting a name list against the real subparsers.
    # Exact queue lookup is also read-only. It was added for lossless long
    # notes and proofs; omitting it here made the first full suite after #230
    # report the safe reader as an unguarded surprise.
    expected_readonly = {
        "get", "list", "stats", "verify", "show", "snapshot",
    }
    surprises = readonly - expected_readonly
    check(not surprises,
          f"no unguarded command outside the known readers (surprises: "
          f"{sorted(surprises)})")
    check("report" in guarded and "next" in guarded,
          "report and next are guarded")
    check("restore" in guarded,
          "restore is guarded: it replaces every record")
    check("snapshot" not in guarded,
          "snapshot is not, so a backup still works on a queue you distrust")


def main() -> int:
    for fn in (test_unstamped_queue_allows_writes,
               test_stamped_queue_refuses_writes,
               test_stamped_queue_still_allows_reads,
               test_report_preserves_complete_evidence,
               test_report_preserves_structured_search_verdict,
               test_queue_writers_do_not_slice_evidence,
               test_worker_reports_preserve_prior_notes,
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
