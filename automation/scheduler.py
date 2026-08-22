#!/usr/bin/env python3
"""
scheduler.py: the single writer to the work queue.

The queue lives at ~/sotn-work/queue.jsonl by default, NOT at work/queue.jsonl.
That legacy in-repo path is still recognised for migration but is not where the
live queue is; a file-sync daemon destroyed it once (see _DEFAULT_QUEUE below).

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
  SOTN_QUEUE   path to queue.jsonl (default: ~/sotn-work/queue.jsonl)
  SOTN_REPO    repo root (default: two levels up from this file)
"""
from __future__ import annotations
import re
import argparse
import datetime as dt
import json
import os
import platform
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
# Written only when THIS environment created its queue by migration.
_FROM_LEGACY = QUEUE.with_suffix(".jsonl.from-legacy")


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

    READ-ONLY. A migrated copy is a SNAPSHOT of a stale in-repo file, not the
    live queue, and the environments do not sync afterwards. Writing to one is
    silent data loss: on 2026-08-02 nine verified matches were reported from the
    Cowork sandbox, every call printed "updated", and not one reached the real
    queue, because the sandbox had migrated its own 438-record copy from the
    legacy file and was happily mutating that. The stamp written here is what
    _require_queue_owner() later refuses to mutate.
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
        _FROM_LEGACY.write_text(
            f"migrated from {_LEGACY_QUEUE} by pid {os.getpid()} on "
            f"{platform.node()}\n")
        print(f"[scheduler] migrated a READ-ONLY snapshot out of the synced "
              f"tree: {_LEGACY_QUEUE} -> {QUEUE}. Mutating commands are "
              f"refused here; run them where the live queue is.",
              file=sys.stderr)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


# Commands that write. Everything else may run against a migrated snapshot,
# because a stale read is recoverable and a stale write is not.
# `restore` belongs here and `snapshot` does not. restore replaces the queue
# wholesale, which is the most destructive thing in this file; snapshot only
# reads (it borrows the writer's lock so a running fleet cannot be caught
# mid-write, but it leaves the content identical). Taking a backup of a
# read-only migrated copy is harmless and occasionally exactly what you want.
_MUTATING = {"init", "seed", "next", "report", "reclaim", "annotate", "prune",
             "restore"}


def _require_queue_owner(cmd: str) -> None:
    if cmd not in _MUTATING or not _FROM_LEGACY.exists():
        return
    sys.exit(
        f"refusing to run '{cmd}': {QUEUE} is a read-only snapshot that this\n"
        f"environment migrated from {_LEGACY_QUEUE}, not the live queue.\n"
        f"  {_FROM_LEGACY.read_text().strip()}\n"
        f"Writing here would report into a copy nobody reads. Run mutating\n"
        f"commands through the MCP connector, or set SOTN_QUEUE to the live\n"
        f"path. To claim ownership deliberately, delete {_FROM_LEGACY}.")


_migrate_legacy_queue()
WORKTREE_ROOT = REPO / "automation" / "wt"

VALID_STATUS = {"todo", "claimed", "near", "matched", "escalated", "deferred"}
VALID_VERDICT_KIND = {"permuter-exhausted"}


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

    Shape: {"<build>:<overlay>:<function>":
            {"rank": int, "blocked": bool}, ...}

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


def priority_for(priority: dict, record: dict) -> dict:
    """Return one record's hints without collapsing equal function names.

    The function-name fallback reads older generated files safely during an
    update, but every new writer uses the full queue id.
    """
    return priority.get(record.get("id", ""),
                        priority.get(record.get("function", ""), {}))


def _take(records, best, args):
    """Mark `best` as claimed. THE ONLY PLACE A CLAIM IS WRITTEN.

    Both the ranked path and the --only path come through here, so they cannot
    drift. The specific thing that must not drift is `claimed_from`: release
    and reclaim both read it to decide where a stranded record goes back to,
    and a claim path that forgot to set it would send the record to "todo"
    regardless of where it started.
    """
    for r in records:
        if r is best:
            # Remember WHERE this was claimed from. Without it, reclaim and
            # release both hard-coded "todo", so a `deferred` handoff record
            # that got claimed and then stranded came back as `todo` and
            # escaped the deferred pool entirely. That also blocks any
            # future tier-2 consumer: a dead consumer's escalated record
            # would silently fall back to Tier 0 and be reworked by the
            # cheapest model, which is the opposite of escalation.
            r["claimed_from"] = r["status"]
            r["status"] = "claimed"
            r["claimed_by"] = args.worker
            r["updated_at"] = _now()
            # THE CIRCUIT BREAKER. Counts CLAIMS, not reports.
            #
            # On 2026-08-16 two workers claimed the same record ~35 times each
            # and burned ~480 model calls between them producing nothing:
            # EntityGaibon took 141 of one worker's 240 attempts, every one
            # ending in a byte-identical quality reject, and neither worker
            # ever printed a terminal verdict. `iterations` did not catch it
            # because iterations only moves on `report --add-iters`, and that
            # loop died before it reached any reporting path at all.
            #
            # So the counter has to sit on the CLAIM. A worker that crashes,
            # is killed, or exits silently still had to come through here to
            # get the record, which makes this the one place that sees the
            # loop no matter what the loop's cause turns out to be. The cause
            # is still open (#113); this bounds the cost while it is.
            r["claims"] = r.get("claims", 0) + 1
            r["claimed_at"] = r["updated_at"]
            if args.worktree:
                make_worktree(r)
            return records, r
    return records, None


def cmd_next(args):
    q = Queue()
    prio = _load_priority()

    # Records the previous tier handed off because the function was too large
    # for it. Only THESE deferrals are claimable here: a record deferred for a
    # structural reason (an unlabelled union member, say) is not made solvable
    # by a bigger context window, and re-claiming it would just burn the
    # stronger tier's budget on the same wall.
    HANDOFF = "TIER_HANDOFF_TOO_LARGE"

    # How many times one record may be claimed before the scheduler stops
    # handing it out. Comfortably above legitimate rework -- a record that is
    # requeued, permuted, requeued again and re-attempted is well inside this --
    # and far below the ~35 re-claims per record seen on 2026-08-16. Env-tunable
    # so a deliberate grind can raise it without editing code.
    MAX_CLAIMS = int(os.environ.get("MAX_CLAIMS", "12"))

    def fn(records):
        # A NAMED record bypasses the pool and the ranking entirely.
        #
        # Everything below this block exists to CHOOSE a record: coverage rank,
        # blocked-last, deferred-last. When the caller names an id there is
        # nothing to choose, and applying the heuristics anyway just means a
        # targeted run silently claims something else. That is not theoretical:
        # verifying the m2c-only path meant running one specific 68865-char
        # function, and it sat at the BOTTOM of a 160-record todo list, so
        # every ordinary claim reached a different record first.
        #
        # Status rules, deliberately narrow:
        #   - `claimed` is refused; another worker holds it and stealing the
        #     claim would let two workers edit the same source file.
        #   - `matched` is refused; re-running a good record can only lose it.
        #   - anything else is fair game, including `escalated` and plain
        #     `deferred` WITHOUT the handoff marker. Naming an id is a
        #     deliberate operator act, unlike the fleet's own scheduling, and
        #     re-testing a record in an arbitrary state is the entire point.
        # claimed_from is set below, so a stranded targeted claim goes back to
        # wherever it came from rather than leaking into `todo`.
        if getattr(args, "only", None):
            hit = [r for r in records if r["id"] == args.only]
            if not hit:
                return records, None
            r = hit[0]
            if r["status"] in ("claimed", "matched"):
                return records, None
            return _take(records, r, args)

        todo = [r for r in records if r["status"] == "todo"]
        deferred_ids = set()
        if args.include_deferred:
            for r in records:
                if not (r["status"] == "deferred"
                        and HANDOFF in (r.get("notes") or "")):
                    continue
                # A HANDOFF IS TO A BIGGER TIER, NOT TO WHOEVER ASKS.
                #
                # This block used to re-serve any handoff record to any caller
                # passing --include-deferred. The zen fleet both DEFERS records
                # for exceeding its MAX_FUNC_CHARS and PASSES that flag, so it
                # handed records to itself: on 2026-08-16 two records bounced
                # about 35 times each, taking the m2c-only path, producing a
                # deterministic quality reject, deferring again, and being
                # served straight back. No model calls, but hours of build
                # cycles. The marker said "someone bigger should take this" and
                # nothing checked that the taker was bigger.
                #
                # handoff_limit is the MAX_FUNC_CHARS of the tier that gave up.
                # A caller is only a valid next tier if it can read MORE than
                # that, which is the whole content of "bigger tier" here.
                lim = r.get("handoff_limit", 0)
                if lim and lim >= args.max_func_chars:
                    continue
                # Legacy records predate handoff_limit, so their deferring tier
                # is unknown. Serve them once to a caller that DECLARES a limit;
                # when it defers them again they gain one and are gated properly
                # from then on. A caller that declares nothing gets nothing,
                # because that is the shape that caused the loop.
                if not lim and not args.max_func_chars:
                    continue
                todo.append(r)
                deferred_ids.add(r["id"])

        # Trip the breaker BEFORE ranking, so a looping record cannot be picked
        # again no matter how well it ranks. Deliberately not applied to the
        # --only path above: naming an id is an operator act, and the operator
        # is allowed to re-run something the fleet has given up on.
        #
        # Escalated rather than deferred: `deferred` means "a bigger tier might
        # do this", which is a claim about the FUNCTION. This is a claim about
        # the HARNESS, and escalated is the status a human actually reads.
        burned = [r for r in todo if r.get("claims", 0) >= MAX_CLAIMS]
        for r in burned:
            r["status"] = "escalated"
            r["updated_at"] = _now()
            was = r.get("notes") or ""
            r["notes"] = (
                f"CLAIM_LIMIT: claimed {r['claims']} times without ever "
                f"reaching a verdict; the fleet is looping on this record, not "
                f"working it (see #113). Requeue only after that is fixed. "
                f"|| {was}")
            todo.remove(r)
        if not todo:
            return records, None

        def key(r):
            p = priority_for(prio, r)
            # Ordering, outermost first:
            #   1. deferred records LAST. A deferred handoff is a fallback: work
            #      it only once the live todo pool is exhausted. Without this the
            #      big handed-off functions (which rank high on declaration
            #      coverage) get claimed before ordinary todo, which also makes
            #      any model bake-off unfair, since some models draw a 12k-char
            #      prompt that drops empty for size, not capability.
            #   2. blocked last within a tier. Raw D_ addresses nothing names are
            #      a structural failure (MATCHING-LESSONS.md 1a) no model fixes.
            #   3. then declaration-coverage rank.
            return (1 if r["id"] in deferred_ids else 0,
                    1 if p.get("blocked") else 0,
                    p.get("rank", 1_000_000))

        if not args.include_blocked:
            workable = [r for r in todo
                        if not priority_for(prio, r).get("blocked")]
            # Only fall back to blocked records once the workable set is empty,
            # so the fleet never idles, but never starts there either.
            todo = workable or todo

        return _take(records, min(todo, key=key), args)

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
    # AN EMPTY ORACLE IS NOT A PASS.
    #
    # With expected == 0 this returned True, "0/0 artifacts byte-exact", and
    # this function is what gates recording a `matched` record. An empty or
    # truncated check.<v>.sha therefore turned every claim into an automatic
    # success. That file is also writable through the connector's write_file,
    # so this was reachable without touching the repo by hand.
    #
    # There is no legitimate reason for the oracle to be empty: the us build
    # has 81 artifacts. Refuse instead. Found by audit 2026-08-02.
    if expected == 0:
        return False, (f"REFUSED: {check} lists no artifacts. An empty oracle "
                       f"cannot prove a match; expected 81 for us.")
    return True, f"{expected}/{expected} artifacts byte-exact"


def cmd_report(args):
    if args.evidence_stdin:
        try:
            evidence = json.load(sys.stdin)
        except (json.JSONDecodeError, OSError) as exc:
            sys.exit(f"invalid --evidence-stdin JSON: {exc}")
        if not isinstance(evidence, dict):
            sys.exit("invalid --evidence-stdin JSON: expected an object")
        unknown = sorted(set(evidence) - {"notes", "proof"})
        if unknown:
            sys.exit("invalid --evidence-stdin keys: " + ", ".join(unknown))
        for field in ("notes", "proof"):
            value = evidence.get(field)
            if value is None:
                continue
            if not isinstance(value, str):
                sys.exit(f"invalid --evidence-stdin {field}: expected a string")
            if getattr(args, field) is not None:
                sys.exit(f"refused: {field} supplied both on argv and stdin")
            setattr(args, field, value)

    if args.status not in VALID_STATUS:
        sys.exit(f"invalid status: {args.status}")

    verdict_requested = bool(
        args.verdict_kind or args.verdict_seed_current or args.verdict_source)
    if verdict_requested:
        if args.verdict_kind not in VALID_VERDICT_KIND:
            sys.exit("invalid --verdict-kind: expected one of "
                     + ", ".join(sorted(VALID_VERDICT_KIND)))
        if not args.verdict_seed_current:
            sys.exit("refused: a structured search verdict must explicitly say "
                     "--verdict-seed-current")
        if not (args.verdict_source or "").strip():
            sys.exit("refused: a structured search verdict requires "
                     "--verdict-source")
        if args.status != "deferred":
            sys.exit("refused: structured search verdicts require "
                     "--status deferred")

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
                prior_status = r["status"]
                r["status"] = args.status
                if verdict_requested:
                    r["search_verdict"] = {
                        "kind": args.verdict_kind,
                        "seed_current": True,
                        "source": args.verdict_source,
                        "recorded_at": _now(),
                    }
                elif args.status != "deferred" or prior_status != "deferred":
                    # A structured exhaustion controls only the deferral it was
                    # recorded for. Once the record leaves deferred, a later
                    # attempt must earn a new verdict rather than inherit this
                    # one. Deferred-to-deferred maintenance notes preserve it.
                    r.pop("search_verdict", None)
                if args.score is not None:
                    r["best_score"] = args.score
                if args.tier is not None:
                    r["tier_reached"] = args.tier
                if args.notes is not None:
                    # Notes remain the human derivation and provenance index.
                    # Size handoffs, permuter seed paths and false-escalation
                    # rescues still use `seed=`, `rejected=` and
                    # TIER_HANDOFF_TOO_LARGE here. Machine authority for a
                    # current-seed search exhaustion belongs to the structured
                    # `search_verdict` field above.
                    #
                    # A plain overwrite is right for a verdict, which
                    # supersedes what came before. It is WRONG for a release,
                    # which reports nothing about the function and should not
                    # be able to erase what the last real attempt learned. On
                    # 2026-08-10 cancelling one worker turned
                    #   "TIER_HANDOFF_TOO_LARGE: asm 12000 chars > 6000 ..."
                    # into
                    #   "released: worker interrupted before reporting"
                    # and the record vanished from deferred_triage's handoff
                    # class while sitting in plain sight in the queue.
                    if args.keep_note and (r.get("notes") or "").strip():
                        # Evidence is never a display summary. The old 1000
                        # character slice silently cut derivations mid-word
                        # after the connector had already shortened each new
                        # note. If a storage bound is ever needed, reject the
                        # write loudly instead of accepting partial evidence.
                        r["notes"] = args.notes + " || " + r["notes"]
                    else:
                        r["notes"] = args.notes
                if args.proof:
                    r["proof"] = args.proof
                    r["verified_at"] = _now()
                r["iterations"] = r.get("iterations", 0) + args.add_iters
                # Stamp WHO gave up, in the only unit that matters for a size
                # handoff: how much asm that tier could read. `next` compares
                # against it so the record goes to something bigger rather than
                # back to the tier that just failed on it.
                if args.handoff_limit:
                    r["handoff_limit"] = args.handoff_limit
                r["updated_at"] = _now()
                return records, True
        return records, False

    # EXIT NON-ZERO WHEN NOTHING WAS UPDATED.
    #
    # This printed "id not found" and exited 0, so a caller that mistyped an id,
    # or reported against a record pruned from the queue, saw success and moved
    # on. The worker calls this to record every outcome, including `matched`, so
    # a silent no-op loses the result of a whole function. sched() in
    # worker_direct.py raises on rc != 0, which is exactly the behaviour wanted.
    # Found by audit 2026-08-02.
    if q.transaction(fn):
        print("updated")
    else:
        sys.exit(f"id not found: {args.id} (nothing was updated)")


def cmd_annotate(args):
    """Attach twin candidates from automation/twins.us.json to queue records.

    174 of 335 unmatched stubs already exist somewhere else in the tree, 145 of
    them findable by name alone. Recording that ON THE RECORD means a worker or
    subagent starts from "this is RicStepStand in src/ric/pl_steps.c, diff it"
    instead of from raw assembly, which is the difference between a cheap port
    and an expensive rediscovery.

    WHY THIS COMMAND EXISTS RATHER THAN A SANDBOX SCRIPT
    SOTN_QUEUE defaults to ~/sotn-work/queue.jsonl, so it resolves to a
    DIFFERENT file per HOME. A helper run from the Cowork sandbox saw 33 matched
    where the live queue had 134. Writing from there would have forked the
    harness state while printing success. So this runs inside the same process
    family as every other writer, and it prints the resolved path every time so
    a fork is visible immediately instead of months later.

    Annotation is NOT progress: status, tier, iterations and updated_at are all
    left alone. Only `twin` is written, so re-running is a no-op once applied
    and this can never disturb the ordering the fleet pulls work in.

    DRY RUN BY DEFAULT, matching `prune`.
    """
    src = Path(args.from_file)
    if not src.is_absolute():
        src = REPO / src
    try:
        doc = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"cannot read {src}: {e}")
    twins = doc.get("twins") or {}
    if not twins:
        sys.exit(f"{src} has no 'twins' map; regenerate with "
                 f"`python3 automation/asm_twin_finder.py --record`")

    print(f"queue:  {QUEUE}")
    print(f"twins:  {src}  ({len(twins)} entries, "
          f"generated from {doc.get('generated_from') or 'unknown'})")

    # Case-insensitive keys. The queue stores overlay UPPERCASE ("BOSS/BO6",
    # from the seed) while twins.us.json derives it from the asm path and gets
    # lowercase ("boss/bo6"). Matching them literally found ZERO records, and
    # the first version of this command then printed "every matching record is
    # already annotated", which is how a total no-op passes for success. Fold
    # case on both sides, and never let "nothing matched" share a message with
    # "nothing left to do".
    lookup = {k.lower(): v for k, v in twins.items()}

    records = Queue()._read()
    planned: dict[str, dict] = {}
    matched_any = 0
    for r in records:
        entry = lookup.get(f"{r.get('overlay')}/{r.get('function')}".lower())
        if not entry:
            continue
        matched_any += 1
        twin = {
            "name": [f"{t['file']}:{t['function']}"
                     for t in entry.get("name_twins") or []],
            "shape": [f"{t['overlay']}:{t['symbol']}"
                      + ("" if t.get("identical_constants") else " (DIFFERENT constants)")
                      for t in entry.get("shape_twins") or []],
            "tokens": [f"{t['file']}:{t['function']} ({t['score']})"
                       for t in entry.get("token_twins") or []],
            "instructions": entry.get("instructions"),
        }
        if r.get("twin") == twin:
            continue                      # already annotated, nothing to do
        planned[r["id"]] = twin

    for rid in sorted(planned):
        names = planned[rid]["name"]
        head = names[0] if names else "(no name twin)"
        extra = f" +{len(names) - 1} more" if len(names) > 1 else ""
        print(f"  annotate  {rid}\n              -> {head}{extra}")

    if not matched_any:
        # Loud, because this is indistinguishable from success if you only read
        # the exit code. It means the two id schemes have drifted apart again.
        sample_q = [f"{r.get('overlay')}/{r.get('function')}"
                    for r in records[:3]]
        sample_t = list(twins)[:3]
        sys.exit(
            f"\nERROR: not one of {len(records)} queue records matched any of "
            f"the {len(twins)} twin entries.\n"
            f"  queue keys look like: {sample_q}\n"
            f"  twin  keys look like: {sample_t}\n"
            f"This is a key-format mismatch, not an empty result. Nothing was "
            f"written.")
    if not planned:
        print(f"\nnothing to do: all {matched_any} matching record(s) are "
              f"already annotated.")
        return
    if not args.apply:
        print(f"\ndry run: {len(planned)} record(s) would be annotated. "
              f"Re-run with --apply to write.")
        return

    def fn(records):
        n = 0
        for r in records:
            if r["id"] in planned:
                r["twin"] = planned[r["id"]]
                n += 1
        return records, n

    n = Queue().transaction(fn)
    print(f"\nannotated {n} record(s) in {QUEUE}")


def cmd_prune(args):
    """Remove records that are not decompilable functions at all.

    Needed because `init` is additive and has no inverse. 34 rodata string
    labels (aCdlnop, aComplete, a0123456789abcd ...) were seeded as decomp
    targets because the seed filtered data by NAME, and these are `.asciz`
    constants whose names look like ordinary identifiers. A cli worker claiming
    one burns its entire 1800s budget on something with nothing to decompile.

    DELETES rather than marks. A status like `deferred` would be wrong twice
    over: it implies a weaker tier handed the record on, and
    `next --include-deferred` would hand it straight back to a cli worker,
    which is the exact failure this prevents.

    DRY RUN BY DEFAULT. `--apply` is required to write, because this is the
    only destructive queue operation and a mistyped pattern would otherwise
    silently drop real work. Refuses to touch anything not in `todo`: a
    matched, near or escalated record represents work already done and is never
    prunable by pattern.
    """
    pat = re.compile(args.pattern)
    doomed, protected = [], []
    for r in Queue()._read():
        if not pat.search(r["id"]):
            continue
        (doomed if r.get("status") == "todo" else protected).append(r)

    for r in doomed:
        print(f"  prune  {r['id']}")
    for r in protected:
        print(f"  KEEP   {r['id']}  (status={r.get('status')}, not todo)")

    if not args.apply:
        print(f"\ndry run: {len(doomed)} would be pruned, "
              f"{len(protected)} protected. Re-run with --apply to write.")
        return

    ids = {r["id"] for r in doomed}

    def fn(records):
        kept = [r for r in records if r["id"] not in ids]
        return kept, len(records) - len(kept)

    print(f"\npruned {Queue().transaction(fn)} records")


def cmd_list(args):
    records = [r for r in Queue()._read()
               if not args.status or r["status"] == args.status]
    if args.json:
        print(json.dumps(records, sort_keys=True))
        return
    for r in records:
        # Notes carry the FAILURE KIND ("built, but ... does not match" vs
        # "BUILD FAILED" vs a timeout). Without them a status listing cannot be
        # re-triaged, and the queue file lives outside the repo so it cannot be
        # read directly. Printing them is what makes the taxonomy in
        # MATCHING-LESSONS.md sections 6 and 10d auditable after the fact.
        notes = " ".join((r.get("notes") or "").split())
        line = f"{r['status']:>9}  {r.get('best_score', 0):>3}  {r['id']}"
        print(f"{line}  |  {notes}" if notes else line)


def cmd_get(args):
    """Return one complete queue record by exact full id."""
    records = [r for r in Queue()._read() if r.get("id") == args.id]
    if not records:
        print(f"queue record not found: {args.id}", file=sys.stderr)
        raise SystemExit(1)
    if len(records) != 1:
        print(f"queue corruption: {args.id} occurs {len(records)} times",
              file=sys.stderr)
        raise SystemExit(2)
    print(json.dumps(records[0], sort_keys=True))


def cmd_stats(_args):
    from collections import Counter
    recs = Queue()._read()
    c = Counter(r["status"] for r in recs)
    print(f"total {len(recs)}")
    for s in ["todo", "claimed", "near", "matched", "escalated", "deferred"]:
        print(f"  {s:>9}: {c.get(s, 0)}")


SNAPSHOT_DIR = REPO / "automation" / "queue" / "snapshots"


def _sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _head_short() -> str:
    try:
        return _git("rev-parse", "--short=7", "HEAD")
    except Exception:                                       # noqa: BLE001
        return "nogit"


def cmd_snapshot(args):
    """Copy the live queue INTO the repo so a git checkpoint can hold it.

    WHY THIS EXISTS, and why the copy is deliberate rather than continuous.

    The live queue is at ~/sotn-work/queue.jsonl, outside the repo, and that is
    not negotiable: see _DEFAULT_QUEUE. Every transaction rewrites it through
    os.replace, hundreds of times per fleet session, and on 2026-07-20 a cloud
    sync daemon lost that race, renamed the live file to
    "queue (# Name clash ... #).jsonl" and left a zero-byte queue.jsonl. All 438
    records vanished from the harness's view. Moving it to WSL-native storage
    removed the daemon from the picture.

    But that decision answered "where should the hot file live" and never
    answered "what backs it up", so until 2026-08-17 the answer was nothing.
    The repo carried 259 matched records' worth of derivations and provenance
    notes that existed in exactly one place, on one disk, with no history. A
    backup branch protected the source and not the record of how it got there.

    A snapshot is the resolution: the hot file stays on WSL-native storage, and
    a POINT-IN-TIME COPY lands in the repo only when someone asks for one. It is
    written once, never rewritten, so no daemon can lose a race against it.

    Taken under the same exclusive lock as every other transaction, so a running
    fleet cannot be caught mid-write. Read-only with respect to the queue.
    """
    q = Queue()
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = Path(args.out) if args.out else \
        SNAPSHOT_DIR / f"queue.{stamp}.{_head_short()}.jsonl"

    def fn(records):
        # Return the records unchanged: this is a reader borrowing the writer's
        # lock, not a mutation. _write still runs and rewrites the queue with
        # identical content, which is harmless and keeps one code path.
        return records, records

    records = q.transaction(fn)
    with out.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    c = Counter(r["status"] for r in records)
    print(f"snapshot: {out}")
    print(f"source:   {q.path}")
    print(f"records:  {len(records)}")
    print(f"sha256:   {_sha256(out)}")
    print("  " + "  ".join(f"{s}={c.get(s, 0)}" for s in sorted(VALID_STATUS)))
    print("\nCommit it explicitly. It is a checkpoint, not a live file, and it\n"
          "will be stale the moment the next report lands.")


def cmd_restore(args):
    """Replace the live queue with a snapshot. Destructive, hence --confirm.

    Takes a snapshot of the CURRENT queue first, unconditionally. A restore that
    destroys the state you were about to compare against is not a recovery tool,
    it is a second incident, and the one thing you always want after an
    unexpected restore is the ability to undo it.
    """
    src = Path(args.from_file)
    if not src.is_file():
        sys.exit(f"no such snapshot: {src}")

    records = []
    for n, line in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            sys.exit(f"{src}:{n}: not valid JSON ({e}). Refusing to restore a "
                     f"file this tool cannot fully parse.")
        for field in ("id", "status"):
            if field not in rec:
                sys.exit(f"{src}:{n}: record has no '{field}'. This does not "
                         f"look like a queue snapshot.")
        if rec["status"] not in VALID_STATUS:
            sys.exit(f"{src}:{n}: unknown status {rec['status']!r}. "
                     f"Valid: {sorted(VALID_STATUS)}")
        records.append(rec)

    q = Queue()
    live = q._read()
    if not args.confirm:
        sys.exit(
            f"refusing to restore without --confirm.\n"
            f"  from: {src} ({len(records)} records)\n"
            f"  onto: {q.path} ({len(live)} records, which would be REPLACED)\n"
            f"The current queue would be snapshotted first, so this is\n"
            f"reversible, but it is still a wholesale replacement.")

    # Snapshot what is about to be replaced, before replacing it.
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    pre = SNAPSHOT_DIR / f"queue.{stamp}.pre-restore.jsonl"
    with pre.open("w", encoding="utf-8") as f:
        for r in live:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    q.transaction(lambda _old: (records, None))
    print(f"restored {len(records)} records from {src}")
    print(f"the {len(live)} records it replaced are at {pre}")


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
                    # Restore to whatever the record was claimed FROM, not to a
                    # hard-coded "todo". Records claimed before claimed_from
                    # existed have no such field, so they keep the old
                    # behaviour rather than being guessed at.
                    r["status"] = r.pop("claimed_from", None) or "todo"
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
                    help="also claim records a WEAKER tier deferred for size "
                         "(notes containing TIER_HANDOFF_TOO_LARGE)")
    pn.add_argument("--max-func-chars", type=int, default=0,
                    help="this caller's MAX_FUNC_CHARS. A handoff record is "
                         "only served if the tier that deferred it could read "
                         "LESS than this; without it a fleet hands records to "
                         "itself forever")
    pn.add_argument("--only", default=None, metavar="ID",
                    help="claim exactly this record id, ignoring rank, the "
                         "blocked filter and the deferred-last rule. Refused "
                         "if it is already claimed or already matched. For "
                         "targeted verification runs; the fleet never uses it")
    pn.set_defaults(func=cmd_next)

    pr = sub.add_parser("report")
    pr.add_argument("--id", required=True)
    pr.add_argument("--status", required=True)
    pr.add_argument("--score", type=float, default=None)
    pr.add_argument("--tier", type=int, default=None)
    pr.add_argument("--notes", default=None)
    pr.add_argument("--keep-note", action="store_true",
                    help="PREPEND --notes to the existing note instead of "
                         "replacing it. For reports that say nothing about "
                         "the function (a release, a reclaim): they must not "
                         "erase seed=, rejected= or TIER_HANDOFF_TOO_LARGE, "
                         "which are only ever recorded in the note")
    pr.add_argument("--proof", default=None,
                    help="machine proof of a match; REQUIRED for status=matched")
    pr.add_argument("--evidence-stdin", action="store_true",
                    help="read a JSON object containing notes and/or proof from "
                         "stdin. Used by Windows workers so durable evidence "
                         "does not cross the command-line length boundary")
    pr.add_argument("--verdict-kind", choices=sorted(VALID_VERDICT_KIND),
                    default=None,
                    help="structured search verdict stored separately from notes")
    pr.add_argument("--verdict-seed-current", action="store_true",
                    help="assert that the verdict used the current preserved seed")
    pr.add_argument("--verdict-source", default=None,
                    help="durable receipt or task reference supporting the verdict")
    pr.add_argument("--add-iters", type=int, default=0)
    pr.add_argument("--handoff-limit", type=int, default=0,
                    help="the MAX_FUNC_CHARS of the tier deferring this "
                         "record, so a later `next` can tell whether the "
                         "caller is actually bigger")
    pr.set_defaults(func=cmd_report)

    pl = sub.add_parser("list")
    pl.add_argument("--status", default=None)
    pl.add_argument("--json", action="store_true",
                    help="emit complete queue records as one JSON array")
    pl.set_defaults(func=cmd_list)

    pg = sub.add_parser("get")
    pg.add_argument("--id", required=True)
    pg.set_defaults(func=cmd_get)

    ps = sub.add_parser("stats"); ps.set_defaults(func=cmd_stats)

    pp = sub.add_parser("prune")
    pp.add_argument("--pattern", required=True,
                    help="regex matched against the record id; only `todo` "
                         "records are eligible")
    pp.add_argument("--apply", action="store_true",
                    help="actually write; without it this is a dry run")
    pp.set_defaults(func=cmd_prune)

    pa = sub.add_parser("annotate")
    pa.add_argument("--from", dest="from_file",
                    default="automation/twins.us.json")
    pa.add_argument("--apply", action="store_true",
                    help="actually write; without it this is a dry run")
    pa.set_defaults(func=cmd_annotate)

    prc = sub.add_parser("reclaim"); prc.add_argument("--older-than-min", type=int, default=60)
    prc.set_defaults(func=cmd_reclaim)

    psn = sub.add_parser("snapshot",
                         help="copy the live queue into the repo so a git "
                              "checkpoint can hold it")
    psn.add_argument("--out", default=None,
                     help="destination path; defaults to "
                          "automation/queue/snapshots/queue.<stamp>.<head>.jsonl")
    psn.set_defaults(func=cmd_snapshot)

    prs = sub.add_parser("restore",
                         help="replace the live queue with a snapshot")
    prs.add_argument("--from", dest="from_file", required=True)
    prs.add_argument("--confirm", action="store_true",
                     help="required. Without it this prints what it would "
                          "replace and exits")
    prs.set_defaults(func=cmd_restore)

    args = p.parse_args()
    # Before anything writes. sys.argv[1] is the subcommand name; argparse has
    # already validated it by this point.
    _require_queue_owner(sys.argv[1] if len(sys.argv) > 1 else "")
    args.func(args)


if __name__ == "__main__":
    main()
