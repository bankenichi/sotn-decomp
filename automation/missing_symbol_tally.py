#!/usr/bin/env python3
"""Tally unresolved externals named in queue record notes.

Queue classification notes name missing symbols per record, either as
``missing=["Name"]`` or as prose ``missing Name, Other``. This aggregates
those names over the requested live statuses so engine-API curation is
sized by evidence instead of anecdote. Read-only: it invokes the
scheduler CLI and never opens the queue file directly.

Example:
    python3 automation/missing_symbol_tally.py \\
        --status todo --status deferred --status escalated
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

AUTO = Path(__file__).resolve().parent
SCHEDULER = AUTO / "scheduler.py"

STATUSES = ("todo", "deferred", "escalated")

_BRACKET_RX = re.compile(r"missing=\[([^\]]*)\]")
_PROSE_RX = re.compile(r"missing ([A-Za-z_]\w*(?:, [A-Za-z_]\w*)*)")
_IDENT_RX = re.compile(r"[A-Za-z_]\w*\Z")


def _is_symbol(token: str) -> bool:
    """Whether a prose token looks like a code symbol, never English."""
    text = token.strip().strip("\"'")
    if not _IDENT_RX.match(text):
        return False
    return any(ch.isupper() or ch == "_" or ch.isdigit() for ch in text)


def missing_from_notes(notes: str) -> list[str]:
    """Sorted missing symbols named in one record's notes, deduplicated."""
    found: set[str] = set()
    for body in _BRACKET_RX.findall(notes or ""):
        for part in body.split(","):
            token = part.strip().strip("\"'")
            if _IDENT_RX.match(token):
                found.add(token)
    for group in _PROSE_RX.findall(notes or ""):
        for token in group.split(","):
            if _is_symbol(token):
                found.add(token.strip().strip("\"'"))
    return sorted(found)


def _load_records(status: str) -> list[dict]:
    """Live queue records in one status through the scheduler CLI."""
    completed = subprocess.run(
        [sys.executable, str(SCHEDULER), "list", "--status", status, "--json"],
        capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise ValueError(f"scheduler list failed for {status}: {completed.stderr.strip()}")
    records = json.loads(completed.stdout or "[]")
    if not isinstance(records, list):
        raise ValueError(f"scheduler list returned non-list for {status}")
    return records


def tally(statuses) -> dict:
    """Aggregate missing symbols over the requested statuses."""
    symbols: dict[str, dict] = {}
    counts = {"records": 0, "with_missing": 0}
    for status in statuses:
        for record in _load_records(status):
            counts["records"] += 1
            names = missing_from_notes(record.get("notes") or "")
            if not names:
                continue
            counts["with_missing"] += 1
            for name in names:
                entry = symbols.setdefault(name, {"todo": 0, "deferred": 0, "escalated": 0, "files": []})
                if status in entry:
                    entry[status] += 1
                if len(entry["files"]) < 10:
                    entry["files"].append(record.get("id", "?"))
    ordered = dict(sorted(symbols.items(), key=lambda item: (-sum(v for k, v in item[1].items() if k != "files"), item[0])))
    return {"statuses": list(statuses), "counts": counts, "symbols": ordered}


def main(argv=None) -> int:
    """Entry point: print the JSON tally plus a one-line digest."""
    parser = argparse.ArgumentParser(description="Tally unresolved externals named in queue notes.")
    parser.add_argument("--status", action="append", default=[],
                        help="Live queue status to include; repeatable.")
    parser.add_argument("--self-test", action="store_true",
                        help="Exercise note parsing without touching the queue.")
    args = parser.parse_args(argv)
    if args.self_test:
        cases = [
            ('missing=["g_A"]', ["g_A"]),
            ("missing=['g_A', 'Helper']", ["Helper", "g_A"]),
            ("missing SetStep, AnimateEntity", ["AnimateEntity", "SetStep"]),
            ("missing g_EInitBombKnight", ["g_EInitBombKnight"]),
            ("missing none", []),
            ("7 referenced symbols; missing none", []),
            ("no missing symbols here", []),
            ('missing=["g_A"] and missing g_A, g_B', ["g_A", "g_B"]),
        ]
        for notes, expected in cases:
            actual = missing_from_notes(notes)
            assert actual == expected, f"{notes!r}: {actual} != {expected}"
        print("missing-symbol parsing checks passed")
        return 0
    statuses = args.status or list(STATUSES)
    for status in statuses:
        if status not in STATUSES:
            parser.error(f"--status must repeat from {', '.join(STATUSES)}")
    result = tally(statuses)
    print(json.dumps(result, indent=2, sort_keys=True))
    top = [(name, sum(v for k, v in entry.items() if k != "files"))
           for name, entry in result["symbols"].items()][:20]
    print("DIGEST " + json.dumps({"records": result["counts"]["records"],
                                  "with_missing": result["counts"]["with_missing"],
                                  "top": [[name, total] for name, total in top]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
