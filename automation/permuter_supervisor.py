#!/usr/bin/env python3
"""Run the permuter across every candidate that deserves it, then stop.

WHAT IT REPLACES
    Hand-driven permuting, which on 2026-08-03 looked like this: start jobs,
    poll them, read a tail by eye, get the score wrong, promote by hand,
    restart by hand, and leave four jobs running for half an hour after
    reporting them cancelled. Two matches came out of that day and both needed
    a human in the loop for every cycle.

    The cycle that produced those matches is mechanical:

        pick candidates -> drop phantoms -> run N at once
          -> when one improves, promote its seed and restart it
          -> when one stalls, retire it
          -> when one hits zero, bank it and stop that slot
        -> exit when nothing is left

    On a score of 0 it also APPLIES the seed and BUILDS it (--no-apply opts
    out). A permuter zero is necessary but not sufficient -- func_us_801BC3E0
    scored 0 and then failed the real build at 80/81 over an eight-byte stack
    frame -- so the build is what decides, and anything short of green is
    reverted. See land_match for the verdict taxonomy and for how a
    pre-existing broken tree is kept from being blamed on the seed.

WHY IT SELF-TERMINATES
    The permuter never exits on its own. Every previous run had to be killed,
    and the two that were not killed burned a core for 170,002 and 141,409
    iterations respectively, long after their last improvement at iteration
    5,701. Exiting when the work is done is the point of the whole thing.

CANDIDATE SELECTION
    From the live queue (scheduler.py), status `near` by default: those are
    records that COMPILED and produced wrong bytes, which is exactly the
    precondition the permuter needs. `todo` records have no compiling C at all
    and are not permuter work.

    Every candidate is then checked against the tree. A work dir whose function
    is already defined in src/ with no INCLUDE_ASM is a phantom and is dropped:
    four of nine work dirs were phantoms when this was written, and one of them
    reported score 10 while being long since matched and shipped.

Usage:
    python3 automation/permuter_supervisor.py --plan          # show, run nothing
    python3 automation/permuter_supervisor.py --run
    python3 automation/permuter_supervisor.py --run --slots 3 --threads 4
    python3 automation/permuter_supervisor.py --status        # one JSON blob
    python3 automation/permuter_supervisor.py --run --no-apply # find, do not land
    python3 automation/permuter_supervisor.py --import-seeds   # import only
    python3 automation/permuter_supervisor.py --stop          # cancel everything
    python3 automation/permuter_supervisor.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(os.environ.get("SOTN_REPO", Path(__file__).resolve().parents[1]))
QUEUE = Path(os.environ.get(
    "SOTN_QUEUE", os.path.expanduser("~/sotn-work/queue.jsonl")))
WORKROOT = REPO / "nonmatchings"
STATE = Path(os.path.expanduser("~/sotn-work/supervisor.json"))
# Written by dashboard.py when it launches us detached. Exposed via --log
# because a detached supervisor that fails leaves no other trace: the caller
# sees "started" and the permuter column sees no jobs, with the reason in a
# file nothing reads.
LOG = Path(os.path.expanduser("~/sotn-work/supervisor.log"))
# One line per live supervisor. --stop reads it to kill the LOOP, not just the
# jobs the loop happens to have started right now.
PIDS = Path(os.path.expanduser("~/sotn-work/supervisor.pids"))
PYTHON = os.environ.get("SOTN_PYTHON", sys.executable)
# Propagate, so permuter jobs started via commands_client use this interpreter
# rather than falling back to a bare "python3" without pycparser.
os.environ.setdefault("SOTN_PYTHON", PYTHON)

sys.path.insert(0, str(REPO / "automation"))
sys.path.insert(0, str(REPO / "automation" / "mcp"))

# Defaults chosen from measurement, not taste:
#   slots 3   -- four concurrent jobs at 4 threads saturated the machine while a
#                build also wanted cores. Three leaves headroom for make_build,
#                which is exclusive and must not be starved.
#   threads 4 -- the permuter defaults to ONE. Every run before 2026-08-03 was
#                single-threaded.
#   stall 2500 -- past the last improvement seen in any observed run (6,810 was
#                the latest, but that run had improved steadily up to it).
#   cycles 4  -- promote-and-restart this many times before giving up on a seed.
#                801C488C needed two promotions; nothing has needed four.
DEF_SLOTS = 3
DEF_THREADS = 4
DEF_STALL = 2500
DEF_CYCLES = 4
# Hard ceiling per job. There was NO such cap before, which is why a run reached
# 170,002 iterations: the stall check was the only brake and it was broken (see
# read_log). A cap is a second, independent brake that does not depend on
# parsing anything correctly -- the one number the supervisor can always trust
# is how far the run has gone.
DEF_MAX_ITERS = 50000
# The poll is what bounds how fast a fault can be caught, so it is sized in
# ITERATIONS, not seconds. Measured on permuter-175223-34471-func_us_801B1EDC:
# 1497 iterations in 2939s, i.e. 0.51 iterations/s, so 10s is ~5 iterations.
# A small function on 4 threads can run ~50x faster; 10s still bounds that at
# ~250 iterations, inside the 100-500 window a fault should be caught in.
# The cost is one linewise regex pass over a ~130KB log per job per poll,
# which is milliseconds -- there is no reason to be stingy here.
POLL_S = 10


# ----------------------------------------------------------------- candidates

def load_queue() -> list[dict]:
    if not QUEUE.is_file():
        return []
    out = []
    for line in QUEUE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def workdir_for(fn: str) -> Path | None:
    """The nonmatchings/ dir for `fn`, tolerating the -2 disambiguator.

    permuter_import appends -2, -3 when a name repeats, so the dir name is not
    always the function name. Matching on the prefix rather than assuming
    equality is what lets func_us_8019AA04-2 be found at all.
    """
    exact = WORKROOT / fn
    if exact.is_dir():
        return exact
    if not WORKROOT.is_dir():
        return None
    for p in sorted(WORKROOT.iterdir()):
        if p.is_dir() and re.fullmatch(rf"{re.escape(fn)}(-\d+)?", p.name):
            return p
    return None


def best_score(work: Path) -> int | None:
    """Lowest score this work dir has ever produced."""
    best = None
    for d in work.iterdir():
        m = re.fullmatch(r"output-(\d+)-\d+", d.name) if d.is_dir() else None
        if m and (d / "source.c").is_file():
            s = int(m.group(1))
            if best is None or s < best:
                best = s
    return best


def _why_skip(rec: dict, work) -> str:
    """Reasons not to spend a slot on this record."""
    notes = rec.get("notes", "") or ""
    if MATCH_PENDING in notes:
        # Already solved by an earlier run and waiting on a human build.
        # Re-searching it would burn a slot on finished work.
        return "permuter already scored 0; apply it and build"
    if not work:
        return "no work dir; will import from seed"
    return ""


def candidates(statuses: tuple[str, ...] = ("near",),
               check_tree: bool = True) -> list[dict]:
    """Queue records worth permuting, best-scoring first.

    check_tree is a parameter only so the self-test can exercise ordering
    without paying for a full src/ scan. Real runs always check.
    """
    try:
        from permuter_stall import workdir_state
    except ImportError:                                   # pragma: no cover
        workdir_state = None

    out = []
    for rec in load_queue():
        if rec.get("status") not in statuses:
            continue
        fn = rec.get("function", "")
        if not fn:
            continue
        work = workdir_for(fn)
        state = "stub"
        where = ""
        if check_tree and workdir_state is not None:
            state, where = workdir_state(fn)
        if state == "phantom":
            out.append({"function": fn, "id": rec.get("id", ""),
                        "workdir": str(work) if work else "",
                        "score": None, "skip": f"phantom, defined at {where}"})
            continue
        out.append({
            "function": fn,
            "id": rec.get("id", ""),
            "workdir": str(work) if work else "",
            "score": best_score(work) if work else None,
            "seed": seed_from_notes(rec.get("notes", "")),
            "notes": rec.get("notes", "") or "",
            # A record with no work dir is not dropped: --run imports one from
            # the seed named in its notes. --plan still reports it as blocked,
            # because planning must not write to src/.
            "skip": _why_skip(rec, work),
        })

    runnable = [c for c in out if not c["skip"]]
    blocked = [c for c in out if c["skip"]]
    # Unscored dirs sort last: a dir with no output yet is an unknown, and an
    # unknown should not outrank a seed measured at 70.
    runnable.sort(key=lambda c: (c["score"] is None, c["score"] or 0))
    return runnable + blocked


# ---------------------------------------------------------------------- jobs

# Queue statuses the permuter can actually consume.
#
# The permuter mutates an EXISTING, COMPILING function. `near` records compiled
# and produced wrong bytes, which is exactly that precondition. A `todo` record
# has no C at all, so pointing the supervisor at `todo` would import nothing,
# find nothing, and burn a slot per record discovering it. Refusing is better
# than a flag that silently does nothing useful.
USABLE_STATUSES = {"near", "escalated"}


def check_statuses(statuses: tuple[str, ...]) -> str:
    bad = [s for s in statuses if s not in USABLE_STATUSES]
    if not bad:
        return ""
    return (f"refusing status(es) {', '.join(bad)}: the permuter needs a "
            f"function that already compiles, so only "
            f"{'/'.join(sorted(USABLE_STATUSES))} records are usable. "
            f"A 'todo' record has no C to mutate.")


def seed_from_notes(notes: str) -> str:
    """The `seed=...` path a worker recorded when it filed a near miss."""
    m = re.search(r"seed=(\S+\.c)", notes or "")
    return m.group(1) if m else ""


def _build_lock():
    """A factory for the SAME lock the fleet workers use.

    Resolved from this file's location rather than the REPO global, because
    REPO is overridable by env and by tests, and a lock that can be pointed
    somewhere else is not a lock.
    """
    here = Path(__file__).resolve().parent          # automation/
    sys.path.insert(0, str(here / "win"))
    from worker_direct import BuildLock             # type: ignore
    return lambda: BuildLock(str(here / ".build.lock"))


def import_workdir(fn: str, seed_rel: str, lock=None) -> tuple[Path | None, str]:
    """Create a permuter work dir for `fn` by staging its seed into src/.

    permuter_import compiles the file it is given, so the function has to be
    real C in its real source file with its real includes. The seed on disk is
    only a body. This stages the body over the INCLUDE_ASM stub, imports, and
    then puts the file back.

    The restore is in a finally and reads from an in-memory copy taken before
    any write, so an exception, a failed import or a crash mid-import all leave
    the tree exactly as found. That matters more than the feature: this is the
    only part of the harness that edits src/ without a human looking at it.

    Also note this is the ONLY path that picks up [preserve_macros] from
    config/permuter_settings.toml, because macro preservation happens at import
    and nowhere else. Existing work dirs cannot gain it without re-importing,
    which would discard their promoted seeds.
    """
    seed = REPO / seed_rel
    if not seed.is_file():
        return None, f"seed not found: {seed_rel}"

    # Whitespace-tolerant on BOTH sides of the opening paren and the comma.
    # clang-format wraps a stub whose name is long enough:
    #
    #     INCLUDE_ASM(
    #         "boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnStopwatchCircle);
    #
    # A regex requiring `INCLUDE_ASM("` adjacent never matched those, so the
    # importer reported "no INCLUDE_ASM stub in src/" for a stub that is plainly
    # there. Six stubs were invisible this way, all in src/boss/bo6/us_3E79C.c
    # and all with names long enough to trigger the wrap -- which is why the
    # affected set looked arbitrary rather than like a formatting artefact.
    stub = re.compile(
        rf'INCLUDE_ASM\(\s*"([^"]+)"\s*,\s*{re.escape(fn)}\s*\)\s*;')
    target = None
    for p in (REPO / "src").rglob("*.c"):
        text = p.read_text(errors="ignore")
        m = stub.search(text)
        if m:
            target = (p, text, m)
            break
    if target is None:
        return None, f"no INCLUDE_ASM stub for {fn} in src/"

    path, original, m = target
    asm_rel = m.group(1)
    body = seed.read_text(errors="ignore")
    # Strip any banner the candidate saver added; it is prose, not C.
    body = "\n".join(l for l in body.splitlines()
                     if not l.startswith("// ==="))

    import commands_client as cc

    # TAKE THE BUILD LOCK. This function writes to a real src/ file, and fleet
    # workers do the same under automation/.build.lock (worker_direct.py:3228)
    # around apply -> build -> restore. Without the lock there are two ways to
    # corrupt the tree, and the second one is silent:
    #
    #   1. A worker has its candidate applied and is building. We overwrite the
    #      file with a seed, so the worker's build compiles OUR code and returns
    #      a verdict about a function it never tested.
    #
    #   2. Worse: we snapshot the file WHILE the worker's candidate is applied,
    #      then restore that snapshot in our finally. The worker's unverified
    #      candidate is now permanently in src/, and nothing reports it.
    #
    # Same lock, same path, so we serialise against every worker rather than
    # inventing a second, weaker exclusion.
    with (lock or _build_lock())():
        return _import_locked(path, original, m, body, asm_rel, fn, cc)


def _import_locked(path: Path, original: str, m, body: str, asm_rel: str,
                   fn: str, cc) -> tuple[Path | None, str]:
    """The staged import itself. Split out so the lock scope is obvious."""
    try:
        path.write_text(original[:m.start()] + body + original[m.end():])
        r = cc.run("permuter_import", timeout=300,
                   c_file=str(path.relative_to(REPO)),
                   asm_file=f"asm/us/{asm_rel}/{fn}.s")
        ok = r.get("returncode") == 0
        detail = (r.get("stdout") or r.get("stderr") or "")[-300:]
    except Exception as e:                                # noqa: BLE001
        ok, detail = False, f"{type(e).__name__}: {e}"
    finally:
        # Unconditional. The tree must look untouched whatever happened above.
        path.write_text(original)

    work = workdir_for(fn)
    if work is None:
        return None, f"import did not produce a work dir: {detail}"
    return work, ("imported" if ok else f"imported with warnings: {detail}")


# Notes markers. Same pattern as worker_direct's DEFER_TOO_LARGE: the status
# says "not now", the marker says WHY and makes the class findable later with a
# grep. Without one, a deferred record is indistinguishable from every other
# deferred record and nobody can ever undo the decision selectively.
EXHAUSTED = "PERMUTER_EXHAUSTED"
MATCH_PENDING = "PERMUTER_MATCH_PENDING_BUILD"


def report(fn_id: str, status: str, notes: str) -> str:
    """Record an outcome through scheduler.py, the single queue writer.

    The supervisor did not write to the queue at all before, which meant a
    function it had just retired stayed `near` and was picked again by the very
    next plan. The loop could not terminate: three candidates, killed and
    re-selected forever.
    """
    if not fn_id:
        return "no record id"
    r = subprocess.run(
        [PYTHON, str(REPO / "automation" / "scheduler.py"), "report",
         "--id", fn_id, "--status", status, "--notes", notes[:250]],
        cwd=str(REPO), capture_output=True, text=True, timeout=60)
    return (r.stdout or r.stderr).strip()



# ------------------------------------------------------- landing a match

def find_stub(fn: str) -> tuple[Path, str, object] | None:
    """(src file, asm path, regex match) for fn's INCLUDE_ASM stub."""
    stub = re.compile(
        rf'INCLUDE_ASM\(\s*"([^"]+)"\s*,\s*{re.escape(fn)}\s*\)\s*;')
    for p in (REPO / "src").rglob("*.c"):
        text = p.read_text(errors="ignore")
        m = stub.search(text)
        if m:
            return p, m.group(1), m
    return None


def extract_function(text: str, fn: str) -> str:
    """The complete definition of fn, from its return type to its closing brace.

    The permuter's source.c is the whole preprocessed translation unit, so the
    function has to be cut out of ~4000 lines of expanded headers. Brace
    counting rather than a regex, because a regex cannot find a matching brace.
    """
    m = re.search(
        rf"^[A-Za-z_][\w \*]*\b{re.escape(fn)}\s*\([^;{{]*\)\s*\{{",
        text, re.M)
    if not m:
        return ""
    depth = 0
    seen = False
    for i in range(m.start(), len(text)):
        c = text[i]
        if c == "{":
            depth += 1
            seen = True
        elif c == "}":
            depth -= 1
            if seen and depth == 0:
                return text[m.start():i + 1]
    return ""


def classify_build_failure(detail: str) -> str:
    """Turn build_and_check's text into a verdict the caller can act on.

    The three failures need different responses and conflating them is how a
    function gets the wrong status:

      CHECKSUM MISMATCH -- it compiled, the bytes differ. Exactly the
        func_us_801BC3E0 case: scored 0 in isolation, frame was 0x20 vs 0x18.
        The seed is still good permuter work, so the record stays `near`.

      COMPILE ERROR -- the seed references something the real file does not
        declare. The permuter cannot fix that; it mutates expressions, it does
        not add externs. Needs a human, so the record is deferred with the
        error attached.

      DIRTY -- the build failed without naming a diagnostic. Not a verdict
        about anything.
    """
    if "CHECKSUM MISMATCH" in detail:
        return "CHECKSUM MISMATCH: " + detail[:400]
    if "BUILD DIRTY" in detail:
        return "DIRTY: " + detail[:400]
    if "BUILD FAILED" in detail:
        return "COMPILE ERROR: " + detail[:600]
    return "UNKNOWN: " + detail[:400]


def land_match(work: Path, fn: str, build: str = "us",
               lock=None) -> tuple[bool, str]:
    """Apply a score-0 seed to src/, BUILD it, and revert unless it is green.

    A permuter zero is necessary but NOT sufficient. func_us_801BC3E0 scored 0
    and then failed the real build at 80/81, because a `volatile int pad` made
    its stack frame 0x20 where the target was 0x18. The permuter compiles one
    function in isolation; only a full build knows whether the overlay still
    checksums. So this ALWAYS builds, and reverts on anything short of green.

    Concurrency: it takes the same automation/.build.lock the fleet workers
    hold around apply -> build -> restore, so a running fleet is serialised
    against rather than stopped. Stopping the fleet would be heavier and no
    safer: the lock is what the workers actually respect, and killing them
    mid-generation would waste the calls in flight and strand their claims.

    Reverting is unconditional on failure and uses apply_code's own returned
    original, which it journals BEFORE writing, so a crash mid-build is
    recoverable by the existing journal replay.
    """
    out0 = work / "output-0-1" / "source.c"
    if not out0.is_file():
        return False, f"no output-0-1/source.c in {work.name}"
    body = extract_function(out0.read_text(errors="ignore"), fn)
    if not body:
        return False, f"could not extract {fn} from the score-0 source"

    found = find_stub(fn)
    if not found:
        return False, (f"no INCLUDE_ASM stub for {fn} in src/; it may already "
                       f"be applied")
    path, asm_rel, _ = found
    ctx = {"src_rel": str(path.relative_to(REPO)), "asm_rel": asm_rel}

    sys.path.insert(0, str(Path(__file__).resolve().parent / "win"))
    import worker_direct as wd                              # type: ignore

    original = None
    with (lock or _build_lock())():
        try:
            original = wd.apply_code(ctx, fn, body)
            ok, detail = wd.build_and_check({"build": build})
            if ok:
                # An INDEPENDENT oracle, not a second opinion from the same
                # one. build_and_check trusts make's exit code; this reads the
                # 81 SHA-1s out of config/check.<build>.sha and hashes the
                # artefacts itself. The two have disagreed before -- a stale
                # artefact satisfies make and fails this -- and when they do,
                # the hashes win.
                vok, vdetail = verify_checksums(build)
                if vok:
                    return True, f"GREEN: {detail}; {vdetail}"
                path.write_text(original, newline="")
                # Rebuild so the tree is not left holding artefacts built from
                # a seed that is no longer in src/. Leaving those behind is
                # exactly the stale-artefact condition that produced the
                # disagreement in the first place.
                wd.build_and_check({"build": build})
                return False, f"VERIFY FAILED: {vdetail}"

            # Revert FIRST. A failed build must leave the tree exactly as found
            # before anything else is attempted.
            path.write_text(original, newline="")

            # Then ask whether the failure was even OURS. If the reverted tree
            # is also red, something was broken before we touched it -- a
            # worker mid-apply, a bad commit, a stale artifact -- and blaming
            # this seed would file a wrong verdict against a function that may
            # be perfectly good. worker_direct learned this the hard way and
            # has build_error_is_ours for the same reason.
            ok2, _ = wd.build_and_check({"build": build})
            if not ok2:
                return False, ("TREE ALREADY BROKEN: the build fails with the "
                               "seed REVERTED too, so this failure is not "
                               "attributable to " + fn + ". Nothing recorded.")
            return False, classify_build_failure(detail)
        except Exception as e:                              # noqa: BLE001
            if original is not None:
                try:
                    path.write_text(original, newline="")
                except OSError:
                    pass
            return False, f"{type(e).__name__}: {e}"


def require_clean_src() -> str:
    """"" if src/ matches HEAD, else a message naming what is dirty.

    WHY THIS EXISTS
        On 2026-08-03 --land spent two full builds discovering, via TREE
        ALREADY BROKEN, that src/st/rno0/unk_4A320.c still had a fleet
        candidate for func_801CE2CC applied to it. The seed had been left
        behind by an earlier run that was KILLED between staging and restoring:
        import_workdir restores in a `finally` from an in-memory copy, and a
        `finally` does not run when the process is SIGKILLed. The dashboard
        killed it, because _sup ran --import-seeds under a 60s subprocess
        timeout and that scan walks every .c under src/ on a Windows mount.

        A leftover apply is invisible: the tree builds, and only the checksums
        disagree. Checking git is instant and names the file outright, so a
        stale apply can never again be mistaken for a bad seed.
    """
    r = subprocess.run(["git", "status", "--porcelain", "--", "src"],
                       cwd=str(REPO), capture_output=True, text=True,
                       timeout=120)
    if r.returncode != 0:
        return f"could not check git status: {(r.stderr or '').strip()[:200]}"
    dirty = [l[3:] for l in (r.stdout or "").splitlines() if l.strip()]
    if not dirty:
        return ""
    return ("src/ does not match HEAD, so nothing can be landed or attributed "
            "until it does. Uncommitted: " + ", ".join(dirty[:8])
            + (f" (+{len(dirty) - 8} more)" if len(dirty) > 8 else "")
            + ". This is usually a candidate left applied by a run that was "
              "killed mid-apply. Restore those files from HEAD, rebuild, then "
              "run --land again.")


def verify_checksums(build: str = "us") -> tuple[bool, str]:
    """Hash the built artefacts against config/check.<build>.sha directly.

    This is the project's real oracle: 81 SHA-1s, all of which must match. It
    is deliberately NOT `make`, so it cannot be satisfied by a build system
    that decided nothing needed doing.
    """
    sha = REPO / "config" / f"check.{build}.sha"
    if not sha.is_file():
        return False, f"no {sha.name} to verify against"
    r = subprocess.run(["sha1sum", "-c", f"config/{sha.name}"],
                       cwd=str(REPO), capture_output=True, text=True,
                       timeout=900)
    lines = [l for l in (r.stdout or "").splitlines() if l.strip()]
    ok_n = sum(1 for l in lines if l.endswith(": OK"))
    bad = [l for l in lines if l.endswith(": FAILED")]
    total = ok_n + len(bad)
    if r.returncode == 0 and not bad:
        return True, f"verified {ok_n}/{total or ok_n} checksums"
    names = ", ".join(l.split(":")[0] for l in bad[:6]) or "(none named)"
    return False, (f"{ok_n}/{total} checksums matched; {len(bad)} FAILED: "
                   f"{names}")


def land_pending(statuses: tuple[str, ...] = ("near",)) -> int:
    """Apply and build every candidate that ALREADY sits at score 0.

    WHY THIS IS SEPARATE FROM --run
        supervise() lands a match the moment it finds one, but only for jobs it
        started itself. A record that reached 0 in an earlier run carries
        MATCH_PENDING in its notes, and _why_skip deliberately excludes those
        from the plan so a slot is not burnt re-searching solved work. The
        effect was a dead end: --run would not touch them, and the dashboard's
        build tab only builds the tree as it stands -- it does not apply
        anything, so pressing Build there would have rebuilt an unchanged tree
        and reported a green 81/81 that said nothing about the seed.

        func_us_801B1E5C was sitting in exactly that gap.

    Each landing is a full apply -> build -> revert-unless-green through
    land_match, so a permuter zero that does not survive the real build cannot
    slip in. They are done ONE AT A TIME and the tree is clean between them, so
    a failure is always attributable to a single function.
    """
    # BEFORE anything else, and before any build. Landing onto a tree that
    # already differs from HEAD cannot produce an attributable result: a green
    # would credit this seed for someone else's edit, and a red would blame it
    # for one. Refusing costs a git call; not refusing cost two builds and a
    # corrupted-looking tree.
    unclean = require_clean_src()
    if unclean:
        print("REFUSING: " + unclean)
        return 2

    cs = [c for c in candidates(statuses)
          if c["skip"].startswith("permuter already scored 0")]
    if not cs:
        print("nothing is waiting to be landed")
        return 0

    lock = _build_lock()
    print(f"{len(cs)} match(es) pending a build\n")
    landed = 0
    for c in cs:
        fn, work = c["function"], c["workdir"]
        if not work:
            print(f"[skip] {fn}: notes say score 0 but there is no work dir")
            continue
        print(f"[land] {fn} from {work}")
        good, why = land_match(Path(work), fn, lock=lock)
        if good:
            landed += 1
            print(f"  LANDED: {why}")
            print("  queue: " + report(
                c.get("id", ""), "matched",
                f"permuter match, applied and built green. {why}"))
            continue
        print(f"  reverted: {why[:300]}")
        if why.startswith("VERIFY FAILED"):
            # make said green and the hashes said otherwise. That is not a
            # "keep permuting" result -- the seed is reverted and the
            # disagreement itself needs looking at, so it goes to deferred
            # rather than back into the search pool.
            print("  queue: " + report(
                c.get("id", ""), "deferred",
                f"{EXHAUSTED}: build reported success but the checksum "
                f"verification disagreed; seed reverted. {why[:150]}"))
        elif why.startswith("TREE ALREADY BROKEN"):
            # Not this function's failure, so the record is left alone. A
            # status change here would file a wrong verdict.
            print("  queue: untouched; fix the tree and run --land again")
        elif why.startswith("COMPILE ERROR"):
            print("  queue: " + report(
                c.get("id", ""), "deferred",
                f"{EXHAUSTED}: scored 0 but does not compile in its real "
                f"file; needs declarations the permuter cannot add. {why[:120]}"))
        else:
            print("  queue: " + report(
                c.get("id", ""), "near",
                f"permuter scored 0 in isolation but the overlay checksum "
                f"still differs; seed at {work}. Keep searching. {why[:120]}"))
    print(f"\n{landed} of {len(cs)} landed.")
    return 0


def _jobs():
    import jobs
    return jobs


def start_one(work: Path, threads: int) -> str:
    """Promote to the best known seed, THEN start.

    permuter.py only ever reads base.c, so a run begins wherever base.c happens
    to be. Promotion used to happen only on stall or on a match, which meant a
    fresh start could begin from a seed WORSE than one already sitting in the
    work dir:

      BO6_AguneaShuffleParams  output-10-1 on disk, base.c never promoted
                               -> every restart threw the 10 away
      func_us_8019AA04-2       output-885 on disk, base.c promoted at 1100
                               -> searching from a seed 215 points worse

    Both look like the score going backwards, and effectively it is: the work
    was not lost from disk, but every restart discarded it. Promoting here makes
    a run monotonic by construction -- it can never start from worse than the
    best output the dir has ever produced.
    """
    msg = promote(work)
    if msg.startswith("promoted"):
        print(f"[seed] {msg}")
    import commands_client as cc
    r = cc.start_job("permuter", work_dir=str(work.relative_to(REPO)),
                     threads=threads)
    return r.get("job_id", "")


def promote(work: Path) -> str:
    r = subprocess.run([PYTHON, str(REPO / "automation" / "permuter_promote.py"),
                        "--dir", str(work.relative_to(REPO))],
                       capture_output=True, text=True, cwd=str(REPO))
    return (r.stdout or r.stderr).strip()


JOBS_DIR = Path(os.path.expanduser(
    os.environ.get("SOTN_JOBS_DIR", "~/sotn-work/jobs")))


def read_log(job_id: str) -> dict:
    """Parse a job's log, whether or not the job has finished.

    The log path is CONSTRUCTED, not read out of jobs.status(). status() only
    includes a "log" key once the job is done (jobs.py, the state == "done"
    branch); a running job's response has no such key. read_log used to do
    st.get("log", ""), so for every RUNNING job it got "", found no file, and
    returned the zero fallback -- since_improvement = 0, forever.

    The effect was that the supervisor could never see a stall on a live job.
    It never cycled, never promoted, never retired, and only ever reacted when
    a job ended by itself. Two jobs sat stalled for 20,907 and 32,059
    iterations with the supervisor polling them every 20 seconds and reading
    zeros each time.

    The dashboard had it right all along -- it builds JOBS_DIR / f"{jid}.log"
    directly, which is why its panels showed live scores the supervisor was
    blind to. That disagreement was the evidence.
    """
    from permuter_stall import parse, scan_faults
    jobs = _jobs()
    st = jobs.status(job_id, wait_s=0, tail_lines=1)
    log = Path(st.get("log") or (JOBS_DIR / f"{job_id}.log"))
    if not log.is_file():
        return {"state": st.get("state", "?"), "best": None,
                "iterations": 0, "since_improvement": 0, "failures": 0,
                "faults": {"faults": 0, "undeclared": []}}
    raw = log.read_text(errors="ignore")
    d = parse(raw)
    # Only scanned when the counter says something is wrong, so the common
    # case stays a single cheap pass over the log.
    d["faults"] = (scan_faults(raw) if d.get("failures")
                   else {"faults": 0, "undeclared": []})
    d["state"] = st.get("state", "?")
    return d


# ----------------------------------------------------------------- the loop

def already_busy() -> list[str]:
    """Work dirs that a permuter job is ALREADY searching.

    Starting a second supervisor while one is running used to spawn duplicate
    jobs on the same work dirs. Both then write output-* into the same
    directory and promote the same base.c underneath each other, and the
    duplicates die almost immediately -- which from the UI looks exactly like
    "the start button did nothing".

    Observed 2026-08-03: pressing start while supervisor pid 6941 was running
    produced permuter-143902-* jobs that went straight to state 'done'.
    """
    jobs = _jobs()
    busy = []
    for jid in jobs.running_jobs("permuter"):
        # Job ids are <action>-<hhmmss>-<pid>-<workdir slug>, and running_jobs
        # returns the WHOLE id including the action prefix. Splitting on 2
        # instead of 3 yields "6941-func_us_8019AA04-2" -- a string that never
        # equals a work dir name, so the guard silently matched nothing and the
        # supervisor started duplicates anyway. Off-by-one in a field index
        # fails exactly like having no guard at all.
        parts = jid.split("-", 3)
        if len(parts) == 4:
            busy.append(parts[3])
    return busy


def supervise(slots: int, threads: int, stall: int, cycles: int,
              statuses: tuple[str, ...], once: bool = False,
              max_iters: int = DEF_MAX_ITERS,
              apply_matches: bool = True) -> int:
    jobs = _jobs()
    _register_pid()
    _CFG.update({"stall": stall, "slots": slots, "threads": threads,
                 "cycles": cycles, "max_iters": max_iters})
    all_c = candidates(statuses)
    busy = already_busy()
    for c in all_c:
        slug = Path(c["workdir"]).name if c["workdir"] else ""
        if slug and slug in busy:
            c["skip"] = (f"already being permuted by a running job; "
                         f"stop it first (run-permuter stop)")
    pending = [c for c in all_c if not c["skip"]]

    # Import anything that only lacks a work dir. Done here and not in
    # candidates() because this writes to src/ (transiently) and --plan must
    # stay read-only.
    for c in all_c:
        if not c["skip"].startswith("no work dir"):
            continue
        if not c["seed"]:
            print(f"[skip] {c['function']}: no seed= in its queue notes")
            continue
        work, msg = import_workdir(c["function"], c["seed"])
        print(f"[import] {c['function']}: {msg}")
        if work is not None:
            pending.append({**c, "workdir": str(work),
                            "score": best_score(work), "skip": ""})

    pending.sort(key=lambda c: (c["score"] is None, c["score"] or 0))
    if not pending:
        blocked = [c for c in all_c if "already being permuted" in c["skip"]]
        if blocked:
            print(f"NOTHING STARTED: all {len(blocked)} candidate(s) are "
                  f"already being permuted by jobs that are still running:")
            for c in blocked:
                print(f"  {c['function']}")
            print("Run `run-permuter stop` first, or let the existing "
                  "supervisor finish. Starting a second one would duplicate "
                  "jobs on the same work dirs and both would fail.")
            return 1
        print("nothing to permute; every candidate is matched, phantom, or "
              "has no work dir")
        for c in all_c:
            print(f"  {c['function']}: {c['skip']}")
        return 0

    print(f"{len(pending)} candidate(s), {slots} slot(s), {threads} threads each")
    for c in pending:
        print(f"  {c['function']:34s} best {c['score']}")

    active: dict[str, dict] = {}          # job_id -> slot record
    done: list[dict] = []

    while pending or active:
        while pending and len(active) < slots:
            c = pending.pop(0)
            work = Path(c["workdir"])
            jid = start_one(work, threads)
            if not jid:
                c["skip"] = "failed to start"
                done.append(c)
                continue
            active[jid] = {**c, "job": jid, "cycles": 0,
                           "started": time.time()}
            print(f"[start] {c['function']} -> {jid}")

        if not active:
            break

        _write_state(active, done)
        if once:
            break
        time.sleep(POLL_S)

        for jid, slot in list(active.items()):
            d = read_log(jid)
            fn = slot["function"]
            work = Path(slot["workdir"])

            if d["best"] == 0:
                jobs.cancel(jid)
                promote(work)
                slot["result"] = "MATCH"
                slot["best"] = 0
                if apply_matches:
                    good, why = land_match(work, fn)
                    if good:
                        slot["result"] = "MATCHED AND BUILT"
                        print(f"[LANDED] {fn}: {why}")
                        print("  queue: " + report(
                            slot.get("id", ""), "matched",
                            f"permuter match, applied and built green. {why}"))
                        done.append(slot)
                        del active[jid]
                        continue
                    print(f"[revert] {fn}: tree restored. {why[:300]}")
                    if why.startswith("TREE ALREADY BROKEN"):
                        # Say nothing to the queue. The failure is not this
                        # function's and a status change would be a lie.
                        slot["result"] = "build was already broken; unrecorded"
                    elif why.startswith("COMPILE ERROR"):
                        slot["result"] = "scored 0 but does not compile in situ"
                        print("  queue: " + report(
                            slot.get("id", ""), "deferred",
                            f"{EXHAUSTED}: permuter scored 0 but the seed does "
                            f"not compile in its real file. Needs declarations "
                            f"a human must add; the permuter cannot. {why[:120]}"))
                    else:
                        # Compiled, bytes differ. Still permuter work.
                        slot["result"] = "scored 0 but bytes differ in the build"
                        print("  queue: " + report(
                            slot.get("id", ""), "near",
                            f"permuter scored 0 in isolation but the overlay "
                            f"checksum still differs; seed at {work}. "
                            f"Keep searching. {why[:120]}"))
                print(f"[MATCH] {fn} scored 0. Output in {work}/output-0-1. "
                      f"Apply it and BUILD before believing it.")
                # Stays `near`, because it is NOT matched until a build says so
                # and only a human does that. The marker stops the next plan
                # from spending a slot re-searching a function that is already
                # solved and merely waiting to be applied.
                print("  queue: " + report(
                    slot.get("id", ""), "near",
                    f"{MATCH_PENDING}: permuter scored 0. Output at "
                    f"{work}/output-0-1/source.c. Apply it and run make_build; "
                    f"a permuter zero is necessary but not sufficient."))
                done.append(slot)
                del active[jid]
                continue

            if d["state"] not in ("running",):
                slot["result"] = f"job ended ({d['state']}), best {d['best']}"
                done.append(slot)
                del active[jid]
                continue

            # A self-inflicted fault beats every other rule. It is definite,
            # it is deterministic, and unlike a stall there is a specific fix,
            # so there is no reason to let the job keep burning a core while a
            # counter climbs toward some threshold.
            from permuter_stall import fault_verdict
            fv = fault_verdict(d, d.get("faults") or {})
            if fv:
                jobs.cancel(jid)
                slot["result"] = fv
                print(f"[FAULT] {fn}: {fv}")
                print("  queue: " + report(
                    slot.get("id", ""), "deferred",
                    f"{EXHAUSTED}: {fv[:200]}"))
                done.append(slot)
                del active[jid]
                continue

            if d["iterations"] >= max_iters:
                jobs.cancel(jid)
                promote(work)
                slot["result"] = (f"hit the {max_iters}-iteration cap at "
                                  f"best {d['best']}")
                print(f"[cap] {fn}: {slot['result']}. Best output is promoted "
                      f"and kept; re-derive from the asm to go further.")
                print("  queue: " + report(
                    slot.get("id", ""), "deferred",
                    f"{EXHAUSTED}: hit the {max_iters}-iteration cap at best "
                    f"{d['best']}. Seed is promoted; re-derive from the asm, "
                    f"then set this back to near."))
                done.append(slot)
                del active[jid]
                continue

            if d["since_improvement"] >= stall and d["iterations"] > stall:
                jobs.cancel(jid)
                msg = promote(work)
                improved = msg.startswith("promoted")
                if improved and slot["cycles"] + 1 < cycles:
                    slot["cycles"] += 1
                    # start_one promotes again; that is a no-op here because we
                    # just promoted, and promote() refuses a non-improvement.
                    njid = start_one(work, threads)
                    print(f"[cycle {slot['cycles']}] {fn} stalled at "
                          f"{d['best']}; {msg} -> {njid}")
                    del active[jid]
                    if njid:
                        active[njid] = {**slot, "job": njid}
                    continue
                slot["result"] = (
                    f"retired at {d['best']} after {slot['cycles']} promotion(s)"
                    + ("" if improved else "; no better output to promote"))
                print(f"[retire] {fn}: {slot['result']}. The permuter mutates "
                      f"expressions only, so re-derive this one from the asm.")
                print("  queue: " + report(
                    slot.get("id", ""), "deferred",
                    f"{EXHAUSTED}: best {d['best']} after {d['iterations']} "
                    f"iterations, {slot['cycles']} promotion(s), no improvement "
                    f"for {d['since_improvement']}. The permuter mutates "
                    f"expressions only; re-derive from the asm, then set this "
                    f"back to near."))
                done.append(slot)
                del active[jid]

    _write_state({}, done)
    _unregister_pid()
    print("\n--- supervisor finished ---")
    matches = [d for d in done if d.get("result") == "MATCH"]
    for d in done:
        print(f"  {d['function']:34s} {d.get('result', d.get('skip', '?'))}")
    print(f"\n{len(matches)} match(es). Nothing was applied to the tree.")
    return 0


_CFG: dict = {}


def _write_state(active: dict, done: list) -> None:
    """Publish state for the dashboard. Best effort: never kill the run."""
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps({
            "updated": time.time(),
            # Published so the dashboard can label "stalled" using the SAME
            # threshold this loop acts on. Two definitions of stalled is how a
            # job ends up badged stalled with nothing happening to it.
            **_CFG,
            "active": [{"function": s["function"], "job": s["job"],
                        "cycles": s["cycles"], "workdir": s["workdir"]}
                       for s in active.values()],
            "done": [{"function": d["function"],
                      "result": d.get("result", d.get("skip", ""))}
                     for d in done],
        }, indent=2))
    except OSError:
        pass


def _register_pid() -> None:
    """Record this supervisor so --stop can find it."""
    try:
        PIDS.parent.mkdir(parents=True, exist_ok=True)
        with open(PIDS, "a") as f:
            f.write(f"{os.getpid()}\n")
    except OSError:
        pass


def _unregister_pid() -> None:
    try:
        live = [l for l in PIDS.read_text().split()
                if l.strip().isdigit() and int(l) != os.getpid()]
        PIDS.write_text("\n".join(live) + ("\n" if live else ""))
    except OSError:
        pass


def _supervisor_pids() -> list[int]:
    """Live supervisor processes, by pid, cross-checked against /proc.

    The cmdline check keeps a recycled pid from being killed. Same reasoning as
    commands_client's worker check: a pid file alone is a claim, not evidence.
    """
    cands: set[int] = set()
    try:
        cands |= {int(t) for t in PIDS.read_text().split() if t.isdigit()}
    except OSError:
        pass

    # ALSO scan /proc. The pidfile only knows about supervisors started after
    # it was introduced, so relying on it alone reported "0 supervisor(s)
    # stopped" while two were plainly running and restarting their jobs. A
    # registry is a convenience; the process table is the truth.
    try:
        for d in Path("/proc").iterdir():
            if d.name.isdigit():
                cands.add(int(d.name))
    except OSError:
        pass

    out = []
    for pid in sorted(cands):
        if pid == os.getpid():
            continue
        try:
            cmd = (Path("/proc") / str(pid) / "cmdline").read_bytes()
        except OSError:
            continue
        # Must be a supervisor RUN, not a --stop or --plan invocation, or a
        # `run-permuter stop` would kill itself mid-stop.
        if b"permuter_supervisor.py" in cmd and b"--run" in cmd:
            out.append(pid)
    return out


def stop_all() -> int:
    """Stop the supervisor LOOP first, then its jobs.

    Order matters and getting it wrong is why "stop" did not stop. Cancelling
    only the jobs left the loop alive; it polled, saw them ended, and promoted
    and restarted them. From the UI that looks like a permuter that refuses to
    stop and a start button that does nothing, because the work dirs are still
    busy so a NEW supervisor correctly declines to touch them.

    Killing the loop before the jobs also avoids the race where the loop
    launches a replacement between our cancel and our exit.
    """
    import signal as _sig
    killed = 0
    for pid in _supervisor_pids():
        try:
            os.kill(pid, _sig.SIGTERM)
            print(f"stopped supervisor pid {pid}")
            killed += 1
        except OSError as e:
            print(f"could not stop supervisor pid {pid}: {e}")
    if killed:
        time.sleep(1.0)          # let it die before we cancel its children

    jobs = _jobs()
    n = 0
    for jid in jobs.running_jobs("permuter"):
        jobs.cancel(jid)
        print(f"cancelled {jid}")
        n += 1
    try:
        PIDS.write_text("")
    except OSError:
        pass
    _write_state({}, [])
    print(f"{killed} supervisor(s) stopped, {n} permuter job(s) cancelled")
    return 0


def show_status() -> int:
    jobs = _jobs()
    out = {"running": [], "state_file": str(STATE)}
    for jid in jobs.running_jobs("permuter"):
        d = read_log(jid)
        out["running"].append({"job": jid, "best": d["best"],
                               "iterations": d["iterations"],
                               "since_improvement": d["since_improvement"]})
    if STATE.is_file():
        try:
            out["supervisor"] = json.loads(STATE.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    print(json.dumps(out, indent=2))
    return 0


# ------------------------------------------------------------------- tests

def self_test() -> int:
    import tempfile
    fails = []

    def ck(c, l):
        print(("  ok   " if c else "  FAIL ") + l)
        if not c:
            fails.append(l)

    global WORKROOT, QUEUE
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        WORKROOT = t / "nonmatchings"
        WORKROOT.mkdir()
        for name, scores in [("fn_a", [700, 220]), ("fn_b", [90]),
                             ("fn_c-2", [1500]), ("fn_d", [])]:
            w = WORKROOT / name
            w.mkdir()
            (w / "base.c").write_text("x")
            for s in scores:
                o = w / f"output-{s}-1"
                o.mkdir()
                (o / "source.c").write_text("y")

        print("\nwork dir lookup")
        ck(workdir_for("fn_a").name == "fn_a", "finds an exact match")
        ck(workdir_for("fn_c").name == "fn_c-2",
           "finds the -2 disambiguated dir from the bare function name")
        ck(workdir_for("fn_zz") is None, "returns None for an unknown function")
        ck(workdir_for("fn_") is None,
           "does not match a prefix that is not a full name")

        print("\nbest score")
        ck(best_score(WORKROOT / "fn_a") == 220, "lowest output wins")
        ck(best_score(WORKROOT / "fn_d") is None, "no outputs means no score")

        QUEUE = t / "q.jsonl"
        QUEUE.write_text("\n".join(json.dumps(r) for r in [
            {"id": "1", "function": "fn_a", "status": "near"},
            {"id": "2", "function": "fn_b", "status": "near"},
            {"id": "3", "function": "fn_c", "status": "near"},
            {"id": "4", "function": "fn_d", "status": "near"},
            {"id": "5", "function": "fn_e", "status": "near"},
            {"id": "6", "function": "fn_x", "status": "todo"},
            {"id": "7", "function": "fn_y", "status": "matched"},
        ]))

        print("\ncandidate selection")
        cs = candidates(check_tree=False)
        names = [c["function"] for c in cs]
        ck("fn_x" not in names, "a todo record is not permuter work")
        ck("fn_y" not in names, "a matched record is not permuter work")
        runnable = [c for c in cs if not c["skip"]]
        ck([c["function"] for c in runnable] == ["fn_b", "fn_a", "fn_c", "fn_d"],
           f"ranked by best score, unscored last ({[c['function'] for c in runnable]})")
        blocked = [c for c in cs if c["skip"]]
        ck([c["function"] for c in blocked] == ["fn_e"],
           "a record with no work dir is reported, not silently dropped")
        ck("import from seed" in blocked[0]["skip"],
           "and says it will be imported rather than dropped")

        print("\nseed path extraction from queue notes")
        ck(seed_from_notes("compiled, byte mismatch; permuter candidate. "
                           "seed=automation/candidates/us_X.c BUILT")
           == "automation/candidates/us_X.c", "pulls seed= out of a real note")
        ck(seed_from_notes("no seed here") == "", "absent seed yields empty")
        ck(seed_from_notes(None) == "", "a None note does not raise")

        print("\nstatus filter refuses what the permuter cannot use")
        ck(check_statuses(("near",)) == "", "near is accepted")
        ck(check_statuses(("near", "escalated")) == "", "escalated is accepted")
        bad = check_statuses(("todo",))
        ck(bad != "" and "todo" in bad, "todo is refused by name")
        ck("already compiles" in bad, "and the refusal explains why")

        print("\nimport restores src/ even when the import fails")
        # The guarantee that matters: whatever happens between the write and
        # the restore, the file on disk ends up byte-identical to before.
        src_dir = t / "srcfake"
        (src_dir).mkdir()
        f = src_dir / "x.c"
        before = 'INCLUDE_ASM("boss/bo6/nonmatchings/x", fn_q);\n'
        f.write_text(before)
        import types
        global REPO
        old_repo = REPO
        REPO = t
        (t / "src").mkdir(exist_ok=True)
        (t / "src" / "x.c").write_text(before)
        seedf = t / "seed.c"
        seedf.write_text("void fn_q(void) {}\n")
        import contextlib as _ctx
        nolock = lambda: _ctx.nullcontext()
        w, msg = import_workdir("fn_q", "seed.c", lock=nolock)
        ck((t / "src" / "x.c").read_text() == before,
           "src file is byte-identical after a failed import")
        ck(w is None, f"a failed import returns no work dir ({msg})")
        w2, msg2 = import_workdir("fn_missing", "seed.c", lock=nolock)
        ck(w2 is None and "no INCLUDE_ASM stub" in msg2,
           "a function with no stub is reported clearly")
        w3, msg3 = import_workdir("fn_q", "nope.c", lock=nolock)
        ck(w3 is None and "seed not found" in msg3,
           "a missing seed is reported clearly")
        REPO = old_repo

        print("\nempty queue")
        QUEUE.write_text("")
        ck(candidates(check_tree=False) == [], "an empty queue yields nothing")
        QUEUE = t / "nope.jsonl"
        ck(candidates(check_tree=False) == [], "a missing queue does not crash")

        print("\nmalformed queue lines are skipped, not fatal")
        QUEUE = t / "bad.jsonl"
        QUEUE.write_text('{"id":"1","function":"fn_a","status":"near"}\n'
                         'NOT JSON\n\n')
        ck(len(candidates(check_tree=False)) == 1,
           "one good record survives a garbage line")

    print("\nbusy-workdir parsing (guards against duplicate supervisors)")
    import types
    fake = types.SimpleNamespace(running_jobs=lambda a: [
        "permuter-141610-6941-func_us_8019AA04-2",
        "permuter-143902-55599-func_us_801B8E80",
        "make_build-110820-9159"])
    real = globals()["_jobs"]
    globals()["_jobs"] = lambda: fake
    b = already_busy()
    ck("func_us_8019AA04-2" in b,
       f"the -2 work dir slug survives the split ({b})")
    ck("func_us_801B8E80" in b, "a plain slug is parsed too")
    ck(not any(x.isdigit() and len(x) > 4 for x in b),
       f"no pid fragments leak into the slug list ({b})")
    globals()["_jobs"] = real

    print("\na run never starts from a worse seed than the best on disk")
    src_sup = Path(__file__).read_text()
    i = src_sup.index("def start_one")
    body = src_sup[i:src_sup.index("\ndef ", i + 1)]
    ck("promote(work)" in body,
       "start_one promotes before starting, so base.c is always the best known "
       "seed")
    ck(body.index("promote(work)") < body.index("start_job"),
       "and it promotes BEFORE the job starts, not after")

    import contextlib as _ctx
    src_sup = Path(__file__).read_text()
    print("\nextracting a function from a permuter source.c")
    tu = ("typedef int s32;\n\nstatic int other(void) { return 1; }\n\n"
          "void my_fn(s32 a) {\n  if (a) {\n    a--;\n  }\n}\n\n"
          "void after(void) {}\n")
    got = extract_function(tu, "my_fn")
    ck(got.startswith("void my_fn(s32 a)") and got.endswith("}"),
       "cuts from the return type to the matching brace")
    ck("static int other" not in got and "void after" not in got,
       "and takes NEITHER neighbour, which brace counting gets right and a "
       "regex cannot")
    ck(got.count("{") == got.count("}") == 2, "braces balance")
    ck(extract_function(tu, "nope") == "", "a missing function yields empty")

    print("\nlanding a match ALWAYS builds, and reverts unless green")
    i = src_sup.index("def land_match")
    lm = src_sup[i:src_sup.index("\ndef _jobs")]
    ck("build_and_check" in lm,
       "it runs the real build; a permuter zero is not sufficient on its own")
    ck(lm.count("write_text(original") >= 2,
       "it reverts on a red build AND on an exception")
    ck("except Exception" in lm, "an exception cannot leave the tree modified")
    ck("lock or _build_lock()" in lm,
       "and the whole apply/build/revert happens under the fleet's lock")
    ck(lm.index("build_and_check") < lm.index("return True"),
       "there is no path that returns success without having built")

    print("\ninternal permuter faults are detected and acted on")
    from permuter_stall import scan_faults, fault_verdict, MIN_FAULTS
    # Shaped like a REAL log, which is the whole point of this block. main.py
    # dedupes the banner by stack trace, so a fault that fires 117 times prints
    # "internal permuter failure." exactly ONCE and shows up only as a rising
    # counter. The previous fixture repeated the banner 12 times, which no
    # permuter has ever done, so it passed while the check was dead in practice.
    real = ("iteration 1, 0 errors, score = 100\n"
            "[fn] internal permuter failure.\n"
            "Traceback (most recent call last):\n"
            "KeyError: 'func_us_801B171C'\n"
            + "".join(f"iteration {i}, 0 errors, {i // 13} permuter "
                      f"failures, score = 100\n" for i in range(2, 1498)))
    f = scan_faults(real)
    ck(f["traces"] == 1,
       f"the banner is printed once, as the permuter really does ({f['traces']})")
    ck(f["faults"] == 115,
       f"the COUNTER is what gets counted, not the banner ({f['faults']})")
    ck(f["faults"] >= MIN_FAULTS,
       "so a real single-banner log actually crosses the threshold")
    ck(f["undeclared"] == ["func_us_801B171C"],
       f"names the undeclared symbol ({f['undeclared']})")
    v = fault_verdict({"iterations": 1497}, f)
    ck("func_us_801B171C" in v and "extern" in v,
       "the verdict names the symbol AND the fix")
    ck("will not improve by searching longer" in v,
       "and says explicitly that waiting does not help")
    ck(fault_verdict({"iterations": 100},
                     {"faults": MIN_FAULTS - 1,
                      "undeclared": ["x"]}) == "",
       "a couple of failures are tolerated as noise")
    ck(fault_verdict({"iterations": 100},
                     {"faults": 999, "undeclared": []}) == "",
       "failures with no KeyError are NOT called an undeclared symbol; that "
       "is the stall path's job")
    sup3 = src_sup[src_sup.index("def supervise"):]
    ck(sup3.index("fault_verdict") < sup3.index('d["iterations"] >= max_iters'),
       "the fault check runs BEFORE the cap and the stall rule, so a broken "
       "seed is stopped immediately rather than after 50k iterations")
    # Ordering alone is not timeliness. The check runs once per poll, so the
    # poll is the real bound on how long a broken seed burns a core.
    ck(POLL_S <= 10,
       f"and the poll is short enough to make that ordering matter ({POLL_S}s)")
    ck(MIN_FAULTS <= 5,
       f"the threshold does not add a long wait of its own ({MIN_FAULTS})")

    print("\nbuild verdicts are classified, not lumped together")
    ck(classify_build_failure("BUILT, CHECKSUM MISMATCH (bytes differ)")
       .startswith("CHECKSUM MISMATCH"),
       "compiled-but-different is its own verdict; the record stays `near`")
    ck(classify_build_failure("BUILD FAILED:\n x.c:9: undeclared")
       .startswith("COMPILE ERROR"),
       "a compile error is distinct; the permuter cannot add an extern")
    ck(classify_build_failure("BUILD DIRTY: no diagnostic").startswith("DIRTY"),
       "a dirty build is not a verdict about the function")
    ck(classify_build_failure("something else").startswith("UNKNOWN"),
       "an unrecognised failure is not silently treated as a mismatch")

    print("\na pre-existing broken tree is not blamed on the seed")
    lm2 = src_sup[src_sup.index("def land_match"):]
    lm2 = lm2[:lm2.index("\ndef _jobs")]
    ck("TREE ALREADY BROKEN" in lm2,
       "after a red build it rebuilds the REVERTED tree to see whose fault it "
       "was")
    ck(lm2.index("write_text(original") < lm2.index("ok2"),
       "and it reverts BEFORE that second build, so the check is honest")
    sup2 = src_sup[src_sup.index("def supervise"):]
    ck("TREE ALREADY BROKEN" in sup2 and "unrecorded" in sup2,
       "that case records NOTHING to the queue rather than filing a wrong "
       "status")

    print("\na missing score-0 output is refused, not guessed at")
    import tempfile as _tf2
    with _tf2.TemporaryDirectory() as td2:
        w = Path(td2) / "fn_none"
        w.mkdir()
        okk, why = land_match(w, "fn_none", lock=lambda: _ctx.nullcontext())
        ck(okk is False and "no output-0-1" in why,
           f"refuses when there is no score-0 seed ({why})")

    print("\nthe staged import is serialised against the fleet")
    # It writes to a REAL src/ file while workers do the same under
    # automation/.build.lock. Unlocked, a worker's build can compile our seed,
    # or our restore can leave the worker's unverified candidate in the tree.
    src_sup = Path(__file__).read_text()
    i = src_sup.index("def import_workdir")
    body_iw = src_sup[i:src_sup.index("\ndef _import_locked")]
    ck("lock or _build_lock()" in body_iw,
       "import_workdir takes a lock around the staged write")
    ck("BuildLock" in src_sup and ".build.lock" in src_sup,
       "and it is the SAME lock the workers use, not a second weaker one")
    lf = _build_lock()
    ck(callable(lf) and type(lf()).__name__ == "BuildLock",
       "the DEFAULT really resolves to BuildLock, so production always locks "
       "even though the test injects a null lock for speed")

    print("\nwrapped INCLUDE_ASM stubs are found")
    # Against the REAL tree: this is a formatting artefact, so a fixture would
    # not rot the way the source does.
    real = REPO / "src" / "boss" / "bo6" / "us_3E79C.c"
    if real.is_file():
        txt = real.read_text(errors="ignore")
        wrapped_fn = "BO6_RicEntitySubwpnStopwatchCircle"
        rx = re.compile(
            rf'INCLUDE_ASM\(\s*"([^"]+)"\s*,\s*{re.escape(wrapped_fn)}\s*\)\s*;')
        m = rx.search(txt)
        ck(m is not None,
           f"a stub wrapped across two lines by clang-format is matched")
        ck(bool(m) and m.group(1) == "boss/bo6/nonmatchings/us_3E79C",
           "and its asm path is captured correctly")
        tight = re.compile(
            rf'INCLUDE_ASM\("([^"]+)",\s*{re.escape(wrapped_fn)}\);')
        ck(tight.search(txt) is None,
           "while the old adjacent-paren regex does NOT match it, which is the "
           "bug this guards")
    else:
        print("  ~~ src/boss/bo6/us_3E79C.c missing; wrap check skipped")

    print("\nthe loop can terminate: outcomes are written back to the queue")
    src_sup = Path(__file__).read_text()
    i = src_sup.index("def supervise")
    sup = src_sup[i:src_sup.index("\ndef _write_state")]
    ck(sup.count("report(") >= 3,
       "retire, cap and match each record an outcome; without this a retired "
       "function stays `near` and the very next plan picks it again")
    ck('"deferred"' in sup,
       "exhausted candidates go to deferred, which is excluded from `near`")
    ck(EXHAUSTED in src_sup and MATCH_PENDING in src_sup,
       "each carries a findable marker, so the decision can be undone "
       "selectively later")

    print("\na solved-but-unbuilt function is not re-searched")
    ck(_why_skip({"notes": f"x {MATCH_PENDING} y"}, Path(".")) != "",
       "a record already at score 0 is skipped rather than given a slot")
    ck("apply it and build" in _why_skip({"notes": MATCH_PENDING}, Path(".")),
       "and the reason says what the human must do")
    ck(_why_skip({"notes": "ordinary near record"}, Path(".")) == "",
       "an ordinary near record is still runnable")
    ck(_why_skip({"notes": ""}, None) == "no work dir; will import from seed",
       "the missing-work-dir reason still works")

    print("\nread_log works for a RUNNING job, not just a finished one")
    # The bug this guards: jobs.status() only includes a "log" key once the job
    # is done, so relying on it made the supervisor blind to every live job.
    import tempfile as _tf, types as _ty
    with _tf.TemporaryDirectory() as td:
        global JOBS_DIR
        old_jd = JOBS_DIR
        JOBS_DIR = Path(td)
        (JOBS_DIR / "permuter-1-2-fn_x.log").write_text(
            "\n".join(f"iteration {i}, 0 errors, score = "
                       f"{900 if i < 100 else 400}" for i in range(1, 6001)))
        fake = _ty.SimpleNamespace(
            # exactly what jobs.status() returns while RUNNING: no "log" key
            status=lambda j, wait_s=0, tail_lines=1: {"state": "running"},
            running_jobs=lambda a: [])
        real = globals()["_jobs"]
        globals()["_jobs"] = lambda: fake
        d = read_log("permuter-1-2-fn_x")
        ck(d["best"] == 400,
           f"a running job's score is read ({d['best']}), not defaulted to None")
        ck(d["since_improvement"] > 5000,
           f"and its stall is measurable ({d['since_improvement']}), which is "
           f"what lets the supervisor act on a live job")
        globals()["_jobs"] = real
        JOBS_DIR = old_jd

    print("\nan iteration cap exists as a second, independent brake")
    src_sup = Path(__file__).read_text()
    ck("DEF_MAX_ITERS" in src_sup and "max_iters" in src_sup,
       "there is a hard per-job iteration ceiling")
    ck(DEF_MAX_ITERS <= 50000,
       f"and it is not so high as to be theoretical ({DEF_MAX_ITERS})")
    i = src_sup.index("def supervise")
    sup_body = src_sup[i:src_sup.index("\ndef ", i + 1)]
    ck(sup_body.index('d["iterations"] >= max_iters')
       < sup_body.index('d["since_improvement"] >= stall'),
       "the cap is checked BEFORE the stall rule, so a job cannot outrun it "
       "by appearing to still improve")

    print("\nsupervisor discovery does not depend on the pidfile")
    src_sup = Path(__file__).read_text()
    i = src_sup.index("def _supervisor_pids")
    body = src_sup[i:src_sup.index("\ndef ", i + 1)]
    ck("Path(\"/proc\").iterdir()" in body,
       "it scans /proc, so supervisors started before the pidfile existed are "
       "still found")
    ck('b"--run" in cmd' in body,
       "and it only matches --run, so `--stop` does not kill itself")
    me = already_busy  # keep the name referenced
    ck(os.getpid() not in _supervisor_pids(),
       "the calling process is never in its own kill list")

    print("\nlong-running output must not be block-buffered")
    src = Path(__file__).read_text()
    ck("line_buffering=True" in src,
       "stdout is line-buffered, so the job log fills as the run proceeds "
       "rather than all at once when it exits")

    print("\ndefaults are the measured ones")
    ck(DEF_THREADS > 1, "threads default is not 1 (the library default is)")
    ck(DEF_SLOTS < 4, "slots leave headroom for the exclusive build")
    ck(DEF_STALL >= 2000, "stall threshold is past observed late improvements")

    print()
    if fails:
        print(f"{len(fails)} FAILED")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--import-seeds", action="store_true",
                    help="import work dirs for candidates that lack one, "
                         "then stop; starts no jobs")
    ap.add_argument("--land", action="store_true",
                    help="apply and build every candidate already sitting at "
                         "score 0, then stop; starts no searches")
    ap.add_argument("--log", action="store_true",
                    help="print the detached supervisor's own log")
    ap.add_argument("--slots", type=int, default=DEF_SLOTS)
    ap.add_argument("--threads", type=int, default=DEF_THREADS)
    ap.add_argument("--stall", type=int, default=DEF_STALL)
    ap.add_argument("--cycles", type=int, default=DEF_CYCLES)
    ap.add_argument("--max-iters", type=int, default=DEF_MAX_ITERS,
                    help="hard per-job iteration ceiling")
    ap.add_argument("--no-apply", action="store_true",
                    help="find matches but do not apply or build them")
    ap.add_argument("--status-filter", default="near",
                    help="comma-separated queue statuses to draw from")
    a = ap.parse_args()

    # Line-buffer stdout. This process runs for hours with its output
    # redirected to a job log, and Python block-buffers whenever stdout is not
    # a tty: without this the log stays EMPTY until the run ends, which is
    # precisely when you no longer need to watch it. The same bug bit
    # dashboard.py's startup banner an hour earlier.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):     # pragma: no cover
        pass

    if a.self_test:
        return self_test()
    if a.import_seeds:
        statuses = tuple(x.strip() for x in a.status_filter.split(",")
                         if x.strip())
        bad = check_statuses(statuses)
        if bad:
            print(bad, file=sys.stderr)
            return 2
        n = 0
        for c in candidates(statuses):
            if not c["skip"].startswith("no work dir"):
                continue
            if not c["seed"]:
                print(f"[skip] {c['function']}: no seed= in its queue notes")
                continue
            work, msg = import_workdir(c["function"], c["seed"])
            print(f"[import] {c['function']}: {msg}")
            n += work is not None
        print(f"\n{n} work dir(s) imported. Nothing was started; press "
              f"start to search them.")
        return 0
    if a.land:
        statuses = tuple(x.strip() for x in a.status_filter.split(",")
                         if x.strip())
        bad = check_statuses(statuses)
        if bad:
            print(bad, file=sys.stderr)
            return 2
        return land_pending(statuses)
    if a.log:
        if not LOG.is_file():
            print(f"no supervisor log at {LOG}")
            return 0
        print(LOG.read_text(errors="ignore"))
        return 0
    if a.stop:
        return stop_all()
    if a.status:
        return show_status()

    statuses = tuple(s.strip() for s in a.status_filter.split(",") if s.strip())
    bad = check_statuses(statuses)
    if bad:
        print(bad, file=sys.stderr)
        return 2

    if a.plan:
        cs = candidates(statuses)
        if not cs:
            print("no candidates")
            return 0
        print(f"{'function':36s} {'best':>6}  workdir / why not")
        for c in cs:
            print(f"{c['function']:36s} {str(c['score']):>6}  "
                  f"{c['skip'] or c['workdir']}")
        n = len([c for c in cs if not c["skip"]])
        print(f"\n{n} runnable, {len(cs) - n} blocked. "
              f"Run with --run to start {min(n, a.slots)} now.")
        return 0

    if a.run:
        return supervise(a.slots, a.threads, a.stall, a.cycles, statuses,
                         max_iters=a.max_iters,
                         apply_matches=not a.no_apply)

    ap.error("pass one of --plan, --run, --status, --stop, --self-test")


if __name__ == "__main__":
    raise SystemExit(main())
