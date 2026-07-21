#!/usr/bin/env python3
"""
scheduler.py: the single writer to work/queue.jsonl.

Design (see automation/Orchestration-Setup.md and SOTN-Orchestration-Stack.md):
  Workers never edit the queue. They ask the scheduler for the next todo, do the
  work in an isolated git worktree, and report a result back. The scheduler is
  the only process that mutates the queue file, under an exclusive file lock, so
  concurrent workers cannot corrupt state.

This is a working skeleton: init / next / report / list / reclaim / stats are
implemented against a JSONL file with fcntl locking and git worktree helpers.
Wire it into your OpenCode fleet and the Claude harness per the action plan.

Usage:
  scheduler.py init     --from FILE          seed queue from a list of ids
  scheduler.py next     --worker NAME        claim and print the next todo (JSON)
  scheduler.py report   --id ID --status S [--score N --notes STR --tier T]
  scheduler.py list     [--status S]
  scheduler.py stats
  scheduler.py reclaim  --older-than-min M   return stale 'claimed' records to todo

Env:
  SOTN_QUEUE   path to queue.jsonl (default: <repo>/work/queue.jsonl)
  SOTN_REPO    repo root (default: two levels up from this file)
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import fcntl  # POSIX only; this runs in WSL2/Linux, which is correct here.
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - Windows fallback, no real locking
    _HAVE_FCNTL = False

REPO = Path(os.environ.get("SOTN_REPO", Path(__file__).resolve().parents[1]))

# The queue does NOT live in the repo.
#
# The repo may sit under a directory watched by a cloud sync client
# (Proton Drive, OneDrive, Dropbox). Every scheduler transaction rewrites the queue through
# os.replace, producing a fresh inode; under a running fleet that is hundreds of
# replacements per session. On 2026-07-20 the sync daemon lost that race, renamed
# the live file to "queue (# Name clash ... #).jsonl" and left a zero-byte
# queue.jsonl behind. All 438 records vanished from the harness's view.
#
# Keeping the queue on a WSL-native path outside the synced tree removes the
# daemon from the picture entirely. Source stays in the single Windows tree, which
# is the property we actually wanted; only this one hot-rewritten file moves.
# Override with SOTN_QUEUE if you need to.
_DEFAULT_QUEUE = Path(os.path.expanduser("~/sotn-work/queue.jsonl"))
QUEUE = Path(os.environ.get("SOTN_QUEUE", _DEFAULT_QUEUE))
_LEGACY_QUEUE = REPO / "work" / "queue.jsonl"


def _migrate_legacy_queue() -> None:
    """Relocate the queue out of the synced tree, once, automatically.

    The worker fleet, the MCP connector and any local shell may each run in a
    different environment that shares only the /mnt/c repo mount. A WSL-native
    home path is therefore NOT shared between them, and there is no allowlisted
    way to seed it remotely. So each environment migrates its own copy the first
    time it touches the queue: if the new path is absent but the legacy in-repo
    file has records, copy it across.

    Deliberately never deletes the legacy file. It stays as a recovery point, and
    a half-finished migration must not be able to destroy the only copy.
    """
    if QUEUE.exists() and QUEUE.stat().st_size > 0:
        return
    if not (_LEGACY_QUEUE.exists() and _LEGACY_QUEUE.stat().st_size > 0):
        return
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    tmp = QUEUE.with_suffix(f".jsonl.migrating.{os.getpid()}")
    try:
        tmp.write_bytes(_LEGACY_QUEUE.read_bytes())
        os.replace(tmp, QUEUE)
        print(f"[scheduler] migrated queue out of the synced tree: "
              f"{_LEGACY_QUEUE} -> {QUEUE} (legacy copy kept)", file=sys.stderr)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


_migrate_legacy_queue()
WORKTREE_ROOT = REPO / "automation" / "wt"

VALID_STATUS = {"todo", "claimed", "near", "matched", "escalated", "deferred"}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(rec: dict) -> str:
    ov = rec["overlay"].replace("/", "-")
    return f"{rec['build']}-{ov}-{rec['function']}".lower()


class Queue:
    """JSONL queue with an exclusive lock held for the whole read-modify-write."""

    def __init__(self, path: Path = QUEUE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        # Dedicated lock file. Locking the queue itself was unsound: _write
        # replaces the queue via os.replace, so the path points at a new inode
        # while the previous holder still holds a lock on the old one. The next
        # process then locks the NEW inode and enters the critical section
        # concurrently. This file is never replaced, so the inode is stable.
        self.lock_path = self.path.with_suffix(".jsonl.lock")
        self.lock_path.touch(exist_ok=True)

    def _read(self) -> list[dict]:
        out = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def _write(self, records: list[dict]) -> None:
        # Unique temp per process. A shared name let two writers truncate and
        # rename the same file, so one could publish a partial queue.
        tmp = self.path.with_suffix(f".jsonl.tmp.{os.getpid()}")
        try:
            with tmp.open("w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            os.replace(tmp, self.path)
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass

    def transaction(self, fn):
        """Run fn(records) under an exclusive lock; fn returns (records, result)."""
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            if _HAVE_FCNTL:
                fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                records = self._read()
                records, result = fn(records)
                self._write(records)
                return result
            finally:
                if _HAVE_FCNTL:
                    fcntl.flock(lock, fcntl.LOCK_UN)


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args],
                          check=True, capture_output=True, text=True).stdout.strip()


def make_worktree(rec: dict) -> dict:
    """Create an isolated worktree and branch for a record. Idempotent-ish."""
    slug = _slug(rec)
    wt = WORKTREE_ROOT / slug
    branch = f"match/{slug}"
    WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)
    if not wt.exists():
        _git("worktree", "add", str(wt), "-b", branch)
    rec["worktree"] = str(wt.relative_to(REPO))
    rec["branch"] = branch
    return rec


# ---- commands ----

def cmd_init(args):
    q = Queue()

    def fn(records):
        existing = {r["id"] for r in records}
        added = 0
        for line in Path(args.from_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Accept either a bare id or a full JSON record.
            rec = json.loads(line) if line.startswith("{") else _bare(line)
            if rec["id"] in existing:
                continue
            rec.setdefault("status", "todo")
            rec.setdefault("claimed_by", "none")
            rec["updated_at"] = _now()
            records.append(rec)
            existing.add(rec["id"])
            added += 1
        return records, added

    print(f"added {q.transaction(fn)} records to {q.path}")


def _bare(id_str: str) -> dict:
    build, overlay, function = id_str.split(":", 2)
    return {"id": id_str, "build": build, "overlay": overlay, "function": function}


PRIORITY_FILE = REPO / "automation" / "priority.us.json"


def _load_priority() -> dict:
    """Claim-order hints produced by automation/decl_coverage.py.

    Shape: {"<function>": {"rank": int, "blocked": bool}, ...}

    Kept OUT of the queue on purpose. Priority is derived from the repo (which
    symbols are declared, which data addresses are still unnamed) and changes
    every time a symbol gets named, while the queue records durable state. Bake
    the ranking into the records and it is wrong by the next commit; compute it
    at claim time and it is always current.

    Missing or unreadable file means "no opinion", and claiming falls back to
    file order exactly as before.
    """
    try:
        return json.loads(PRIORITY_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def cmd_next(args):
    q = Queue()
    prio = _load_priority()

    # Records the previous tier handed off because the function was too large
    # for it. Only THESE deferrals are claimable here: a record deferred for a
    # structural reason (an unlabelled union member, say) is not made solvable
    # by a bigger context window, and re-claiming it would just burn the
    # stronger tier's budget on the same wall.
    HANDOFF = "TIER_HANDOFF_TOO_LARGE"

    def fn(records):
        todo = [r for r in records if r["status"] == "todo"]
        if args.include_deferred:
            todo += [r for r in records
                     if r["status"] == "deferred"
                     and HANDOFF in (r.get("notes") or "")]
        if not todo:
            return records, None

        def key(r):
            p = prio.get(r.get("function", ""), {})
            # Blocked last. These reference data at raw addresses that nothing
            # in the tree names, which is a structural failure (see
            # MATCHING-LESSONS.md 1a): no model and no permuter run fixes it.
            # As of 2026-07-21 that is 187 of 311 remaining us functions, so
            # without this the fleet spends most of its time on work that
            # cannot succeed.
            return (1 if p.get("blocked") else 0,
                    p.get("rank", 1_000_000))

        if not args.include_blocked:
            workable = [r for r in todo
                        if not prio.get(r.get("function", ""), {}).get("blocked")]
            # Only fall back to blocked records once the workable set is empty,
            # so the fleet never idles, but never starts there either.
            todo = workable or todo

        best = min(todo, key=key)
        for r in records:
            if r is best:
                r["status"] = "claimed"
                r["claimed_by"] = args.worker
                r["updated_at"] = _now()
                if args.worktree:
                    make_worktree(r)
                return records, r
        return records, None

    r = q.transaction(fn)
    print(json.dumps(r) if r else json.dumps({"status": "empty"}))


def _verify_artifacts(version: str) -> tuple[bool, str]:
    """Recompute every artifact hash against config/check.<version>.sha.

    This is the oracle, run by the single queue writer rather than reported to it.
    A caller cannot talk its way past this: the hashes are computed here, from the
    bytes actually on disk, at the moment the claim is recorded.

    Returns (all_ok, human-readable detail).
    """
    import hashlib
    check = REPO / "config" / f"check.{version}.sha"
    if not check.exists():
        return False, f"no oracle file at {check}"
    expected, missing, bad = 0, [], []
    for line in check.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            want, rel = line.split(None, 1)
        except ValueError:
            continue
        expected += 1
        art = REPO / rel.strip()
        if not art.exists():
            missing.append(rel.strip())
            continue
        h = hashlib.sha1()
        with art.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        # config/check.<v>.sha contains mixed-case hex (e.g. CHI.BIN is written
        # 4ea14c8B54B8...B336a2). hexdigest() is always lowercase, so a
        # case-sensitive compare rejects perfectly good artifacts.
        if h.hexdigest().lower() != want.strip().lower():
            bad.append(rel.strip())
    if missing or bad:
        parts = []
        if bad:
            parts.append(f"{len(bad)} MISMATCHED ({', '.join(bad[:3])}"
                         f"{'...' if len(bad) > 3 else ''})")
        if missing:
            parts.append(f"{len(missing)} missing ({', '.join(missing[:3])}"
                         f"{'...' if len(missing) > 3 else ''})")
        return False, f"{expected - len(bad) - len(missing)}/{expected} OK, " + "; ".join(parts)
    return True, f"{expected}/{expected} artifacts byte-exact"


def cmd_report(args):
    if args.status not in VALID_STATUS:
        sys.exit(f"invalid status: {args.status}")

    # STRUCTURAL TRUST INVARIANT
    # A record can only become 'matched' if the reporter supplies machine proof
    # (the built artifact's SHA-1, verified against config/check.<v>.sha). This
    # is what lets the orchestrator read the queue and trust it without
    # re-verifying every function itself. A model's claim is never sufficient.
    if args.status == "matched":
        if not args.proof:
            sys.exit("refused: status 'matched' requires --proof "
                     "(e.g. --proof 'build/us/BO0.BIN sha1=<hash> verified'). "
                     "Report 'near' or 'escalated' instead.")
        # A proof STRING is not proof. The expected hashes live in
        # config/check.<v>.sha, which any agent can read without ever building,
        # so a caller can compose a perfectly plausible proof line having done no
        # work at all. Establish it here instead of accepting testimony.
        ok, detail = _verify_artifacts(args.id.split(":", 1)[0])
        if not ok:
            sys.exit(f"refused: status 'matched' rejected, the tree does not "
                     f"currently build byte-exact. {detail}\n"
                     f"Fix or revert your change, then report again. Report "
                     f"'near' if it compiles but does not match.")
        args.proof = f"{args.proof} [scheduler-verified: {detail}]"

    q = Queue()

    def fn(records):
        for r in records:
            if r["id"] == args.id:
                r["status"] = args.status
                if args.score is not None:
                    r["best_score"] = args.score
                if args.tier is not None:
                    r["tier_reached"] = args.tier
                if args.notes is not None:
                    r["notes"] = args.notes
                if args.proof:
                    r["proof"] = args.proof
                    r["verified_at"] = _now()
                r["iterations"] = r.get("iterations", 0) + args.add_iters
                r["updated_at"] = _now()
                return records, True
        return records, False

    print("updated" if q.transaction(fn) else f"id not found: {args.id}")


def cmd_list(args):
    for r in Queue()._read():
        if args.status and r["status"] != args.status:
            continue
        # Notes carry the FAILURE KIND ("built, but ... does not match" vs
        # "BUILD FAILED" vs a timeout). Without them a status listing cannot be
        # re-triaged, and the queue file lives outside the repo so it cannot be
        # read directly. Printing them is what makes the taxonomy in
        # MATCHING-LESSONS.md sections 6 and 10d auditable after the fact.
        notes = " ".join((r.get("notes") or "").split())
        line = f"{r['status']:>9}  {r.get('best_score', 0):>3}  {r['id']}"
        print(f"{line}  |  {notes}" if notes else line)


def cmd_stats(_args):
    from collections import Counter
    recs = Queue()._read()
    c = Counter(r["status"] for r in recs)
    print(f"total {len(recs)}")
    for s in ["todo", "claimed", "near", "matched", "escalated", "deferred"]:
        print(f"  {s:>9}: {c.get(s, 0)}")


def cmd_reclaim(args):
    q = Queue()
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=args.older_than_min)

    def fn(records):
        n = 0
        for r in records:
            if r["status"] == "claimed":
                ts = dt.datetime.strptime(r.get("updated_at", "1970-01-01T00:00:00Z"),
                                          "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
                if ts < cutoff:
                    r["status"] = "todo"
                    r["claimed_by"] = "none"
                    r["updated_at"] = _now()
                    n += 1
        return records, n

    print(f"reclaimed {q.transaction(fn)} stale records")


def main():
    p = argparse.ArgumentParser(description="SOTN decomp queue scheduler (single writer).")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init"); pi.add_argument("--from", dest="from_file", required=True)
    pi.set_defaults(func=cmd_init)

    pn = sub.add_parser("next"); pn.add_argument("--worker", required=True)
    pn.add_argument("--worktree", action="store_true", help="also create a git worktree")
    pn.add_argument("--include-blocked", action="store_true",
                    help="also claim functions blocked on unnamed data symbols")
    pn.add_argument("--include-deferred", action="store_true",
                    help="also claim records a weaker tier deferred for size "
                         "(notes containing TIER_HANDOFF_TOO_LARGE)")
    pn.set_defaults(func=cmd_next)

    pr = sub.add_parser("report")
    pr.add_argument("--id", required=True)
    pr.add_argument("--status", required=True)
    pr.add_argument("--score", type=float, default=None)
    pr.add_argument("--tier", type=int, default=None)
    pr.add_argument("--notes", default=None)
    pr.add_argument("--proof", default=None,
                    help="machine proof of a match; REQUIRED for status=matched")
    pr.add_argument("--add-iters", type=int, default=0)
    pr.set_defaults(func=cmd_report)

    pl = sub.add_parser("list"); pl.add_argument("--status", default=None)
    pl.set_defaults(func=cmd_list)

    ps = sub.add_parser("stats"); ps.set_defaults(func=cmd_stats)

    prc = sub.add_parser("reclaim"); prc.add_argument("--older-than-min", type=int, default=60)
    prc.set_defaults(func=cmd_reclaim)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
