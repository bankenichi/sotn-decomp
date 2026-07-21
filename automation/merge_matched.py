#!/usr/bin/env python3
"""
merge_matched.py: review and merge matched branches into an integration branch.

This is the human/Opus review step. It never merges without being told to, and
it uses --no-ff so each matched function is a distinct merge commit. Conflicts
abort that single merge and are reported, never force-resolved.

Usage:
  python3 automation/merge_matched.py list
  python3 automation/merge_matched.py merge --into integration --id us:ST/NO0:func_X
  python3 automation/merge_matched.py merge --into integration --all --yes

Env: SOTN_REPO (default: parent of this file's parent)
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("SOTN_REPO", Path(__file__).resolve().parents[1]))
QUEUE = REPO / "work" / "queue.jsonl"


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args],
                          capture_output=True, text=True, check=check)


def matched() -> list[dict]:
    if not QUEUE.exists():
        return []
    out = []
    for line in QUEUE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r.get("status") == "matched" and r.get("branch"):
            out.append(r)
    return out


def cmd_list(_args):
    rows = matched()
    if not rows:
        print("no matched records")
        return
    for r in rows:
        print(f"{r['best_score']:>3}  {r['branch']:<40}  {r['id']}")
    print(f"\n{len(rows)} matched branch(es)")


def ensure_branch(into: str):
    res = _git("rev-parse", "--verify", into, check=False)
    if res.returncode != 0:
        base = "master"
        print(f"creating integration branch '{into}' from {base}")
        _git("branch", into, base)


def cmd_merge(args):
    rows = matched()
    if args.id:
        rows = [r for r in rows if r["id"] == args.id]
    if not rows:
        print("nothing to merge for that selection")
        return
    ensure_branch(args.into)
    cur = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    _git("checkout", args.into)
    try:
        for r in rows:
            br = r["branch"]
            if not args.yes:
                print(f"[dry] would merge {br}  ({r['id']})")
                continue
            m = _git("merge", "--no-ff", "-m", f"merge {r['id']}", br, check=False)
            if m.returncode != 0:
                print(f"CONFLICT merging {br}; aborting this merge")
                _git("merge", "--abort", check=False)
            else:
                print(f"merged {br}")
    finally:
        _git("checkout", cur, check=False)
    if not args.yes:
        print("\ndry run: re-run with --yes to actually merge")


def main() -> int:
    ap = argparse.ArgumentParser(description="Review and merge matched branches.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(func=cmd_list)
    pm = sub.add_parser("merge")
    pm.add_argument("--into", default="integration")
    g = pm.add_mutually_exclusive_group(required=True)
    g.add_argument("--id")
    g.add_argument("--all", action="store_true")
    pm.add_argument("--yes", action="store_true", help="actually merge (else dry run)")
    pm.set_defaults(func=cmd_merge)
    args = ap.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
