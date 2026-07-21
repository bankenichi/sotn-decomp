#!/usr/bin/env python3
"""
merge_verified.py: merge matched branches with an automated safety gate.

No human review required. The gate is the oracle, not an opinion:
after each merge, the full build must still reproduce every SHA-1 in
config/check.<build>.sha. If it does not, the merge is rolled back with
`git reset --hard` and the function is flipped to `escalated` with a note.

This is what lets Opus own merging end to end. A merge is accepted only when
the byte-for-byte build still matches; there is nothing for a human to judge.

Usage:
  python3 automation/merge_verified.py run --into integration
  python3 automation/merge_verified.py run --into integration --limit 5
  python3 automation/merge_verified.py run --into integration --batch
  python3 automation/merge_verified.py run --dry-run
  python3 automation/merge_verified.py status

Options:
  --into BRANCH   integration branch (default: integration), created if absent
  --limit N       merge at most N branches this run
  --batch         verify once after all merges instead of after each. Faster,
                  but on failure the whole batch is rolled back together.
  --dry-run       show what would be merged, touch nothing

Env:
  SOTN_REPO    repo root (default: parent of this file's dir)
  VERIFY_CMD   override the verification command (used by tests)
"""
from __future__ import annotations
import argparse
import datetime as dt
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


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load() -> list[dict]:
    if not QUEUE.exists():
        return []
    return [json.loads(l) for l in QUEUE.read_text().splitlines() if l.strip()]


def save(recs: list[dict]) -> None:
    tmp = QUEUE.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    os.replace(tmp, QUEUE)


def mergeable(recs: list[dict]) -> list[dict]:
    return [r for r in recs
            if r.get("status") == "matched" and r.get("branch")
            and not r.get("merged")]


def verify(build: str) -> tuple[bool, str]:
    """The gate: rebuild and confirm every hash. Returns (ok, detail)."""
    override = os.environ.get("VERIFY_CMD")
    if override:
        p = subprocess.run(override, shell=True, cwd=str(REPO),
                           capture_output=True, text=True)
        return p.returncode == 0, (p.stdout + p.stderr).strip()[-400:]

    b = subprocess.run(["make", "build", f"VERSION={build}"], cwd=str(REPO),
                       capture_output=True, text=True)
    if b.returncode != 0:
        return False, "build failed:\n" + (b.stdout + b.stderr)[-400:]

    sha_file = REPO / "config" / f"check.{build}.sha"
    if not sha_file.exists():
        return False, f"missing {sha_file}"
    tool = "shasum" if _has("shasum") else "sha1sum"
    v = subprocess.run([tool, "-c", str(sha_file.relative_to(REPO))],
                       cwd=str(REPO), capture_output=True, text=True)
    bad = [l for l in v.stdout.splitlines() if not l.endswith(": OK")]
    if v.returncode != 0 or bad:
        return False, "hash mismatch:\n" + "\n".join(bad[:10])
    n_ok = sum(1 for l in v.stdout.splitlines() if l.endswith(": OK"))
    return True, f"{n_ok} hashes OK"


def _has(prog: str) -> bool:
    from shutil import which
    return which(prog) is not None


def ensure_branch(into: str) -> None:
    if _git("rev-parse", "--verify", into, check=False).returncode != 0:
        base = "master"
        print(f"[merge] creating integration branch '{into}' from {base}")
        _git("branch", into, base)


def cmd_status(_a) -> int:
    recs = load()
    pending = mergeable(recs)
    merged = [r for r in recs if r.get("merged")]
    print(f"matched and unmerged: {len(pending)}")
    for r in pending:
        print(f"  {r['best_score']:>5}  {r['branch']:<40} {r['id']}")
    print(f"already merged: {len(merged)}")
    return 0


def cmd_run(a) -> int:
    recs = load()
    pending = mergeable(recs)
    if a.limit:
        pending = pending[:a.limit]
    if not pending:
        print("[merge] nothing matched and unmerged")
        return 0

    if a.dry_run:
        for r in pending:
            print(f"[dry-run] would merge {r['branch']}  ({r['id']})")
        print(f"\n[dry-run] {len(pending)} branch(es); nothing changed")
        return 0

    ensure_branch(a.into)
    original = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    _git("checkout", a.into)
    batch_base = _git("rev-parse", "HEAD").stdout.strip()
    accepted, rejected = [], []

    try:
        for r in pending:
            pre = _git("rev-parse", "HEAD").stdout.strip()
            m = _git("merge", "--no-ff", "-m", f"match {r['id']}", r["branch"],
                     check=False)
            if m.returncode != 0:
                _git("merge", "--abort", check=False)
                r.update(status="escalated", merged=False, updated_at=_now(),
                         notes=(r.get("notes", "") +
                                " | merge conflict, needs manual resolution").strip(" |"))
                rejected.append((r, "conflict"))
                print(f"[merge] CONFLICT {r['branch']} -> escalated")
                continue

            if a.batch:
                accepted.append(r)
                print(f"[merge] merged {r['branch']} (batch verify pending)")
                continue

            ok, detail = verify(r["build"])
            if ok:
                r.update(merged=True, updated_at=_now())
                accepted.append(r)
                print(f"[merge] OK {r['branch']} ({detail})")
            else:
                _git("reset", "--hard", pre)
                r.update(status="escalated", merged=False, updated_at=_now(),
                         notes=(r.get("notes", "") +
                                f" | merge rolled back, verification failed: {detail[:160]}").strip(" |"))
                rejected.append((r, detail))
                print(f"[merge] ROLLED BACK {r['branch']}: {detail.splitlines()[0][:80]}")

        if a.batch and accepted:
            ok, detail = verify(accepted[0]["build"])
            if ok:
                for r in accepted:
                    r.update(merged=True, updated_at=_now())
                print(f"[merge] batch verified ({detail})")
            else:
                _git("reset", "--hard", batch_base)
                for r in accepted:
                    r.update(status="escalated", merged=False, updated_at=_now(),
                             notes=(r.get("notes", "") +
                                    " | batch rolled back, verification failed").strip(" |"))
                rejected.extend((r, detail) for r in accepted)
                accepted = []
                print(f"[merge] BATCH ROLLED BACK: {detail.splitlines()[0][:80]}")
    finally:
        save(recs)
        _git("checkout", original, check=False)

    print(f"\n[merge] accepted {len(accepted)}, rejected {len(rejected)}")
    return 0 if not rejected else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge matched branches behind an automated gate.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(func=cmd_status)
    pr = sub.add_parser("run")
    pr.add_argument("--into", default="integration")
    pr.add_argument("--limit", type=int, default=0)
    pr.add_argument("--batch", action="store_true")
    pr.add_argument("--dry-run", action="store_true")
    pr.set_defaults(func=cmd_run)
    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
