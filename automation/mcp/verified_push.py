#!/usr/bin/env python3
"""Run the fixed pre-push gates, then publish HEAD to origin.

This script deliberately accepts no arguments. The remote, refspec, drift
checker, and cleanliness check are fixed so the connector cannot be steered
toward upstream or asked to force, delete, mirror, or rewrite anything.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
README_STATUS = REPO / "automation" / "readme_status.py"


def _run(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def main() -> int:
    if len(sys.argv) != 1:
        print("verified_push accepts no arguments", file=sys.stderr)
        return 2

    clean = _run(["git", "status", "--porcelain"], timeout=120)
    if clean.returncode != 0:
        print(clean.stderr or clean.stdout, file=sys.stderr, end="")
        return clean.returncode
    if clean.stdout:
        print("REFUSED: worktree or index is dirty:", file=sys.stderr)
        print(clean.stdout, file=sys.stderr, end="")
        return 1

    drift = _run(
        [sys.executable, str(README_STATUS), "--drift"],
        timeout=600,
    )
    print(drift.stdout or drift.stderr, end="")
    if drift.returncode != 0:
        print("REFUSED: managed documentation is stale", file=sys.stderr)
        return drift.returncode

    diff_check = _run(["git", "diff", "--check", "HEAD^", "HEAD"], timeout=120)
    if diff_check.returncode != 0:
        print(diff_check.stderr or diff_check.stdout, file=sys.stderr, end="")
        print("REFUSED: the commit fails git diff --check", file=sys.stderr)
        return diff_check.returncode

    pushed = _run(["git", "push", "origin", "HEAD"], timeout=3600)
    print(pushed.stdout, end="")
    print(pushed.stderr, file=sys.stderr, end="")
    return pushed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
