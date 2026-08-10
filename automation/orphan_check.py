#!/usr/bin/env python3
"""Is there uncommitted work in src/, and is it a MATCH or is it debris?

WHY THIS EXISTS
    On 2026-08-10 src/boss/bo6/richter.c and src/boss/bo6/us_39144.c were
    sitting modified with candidate bodies over three INCLUDE_ASM stubs, and
    automation/logs/pending was empty. Every signal said "debris from a killed
    worker": no journal, no queue record, no running fleet. The obvious action
    was git_restore.

    They were three genuine matches. make_build then verify_build reported
    81/81 with them applied. They had been one command away from deletion for
    an unknown number of days, and were saved only because the oracle happened
    to be run first.

THE QUEUE USUALLY KNOWS, AND NOBODY ASKED IT
    The first version of this file claimed the working tree was the only
    record. That was wrong, and checking would have taken one command. All
    three BO6 functions were ALREADY `matched` in the queue, with proof and
    the BO6.BIN sha1, recorded the night before:

        matched 100.0 us:BOSS/BO6:BO6_RicStepThrowDaggers
            | build/us/BO6.BIN sha1=fe067af9... verified against check.us.sha

    So the worker did not die before reporting. It reported, and then the
    files were never COMMITTED. The queue was the durable half; git was the
    missing half.

    That is worse than the story it replaces, not better. A `matched` record
    whose body exists only in an uncommitted working tree is a record that
    goes false the moment anyone restores that file: the queue keeps
    asserting a verified match, complete with a hash, for a function that is
    an INCLUDE_ASM stub again. Nothing would notice.

    Hence the queue lookup below. Asking it turns "run a full build to find
    out what this is" into an instant answer, and it is the check that would
    have settled the original incident in seconds.

WHY THE TREE CAN STILL BE THE ONLY RECORD
    The journal is an UNDO log, not a record of work. It stores the ORIGINAL
    so a crash can revert an unverified edit, and worker_direct deliberately
    DROPS it on the success path, because a later replay would otherwise write
    the old INCLUDE_ASM stub back over a landed match. So a worker killed
    between "build verified" and "reported to the queue" really does leave
    something indistinguishable from a failed attempt. That window is real;
    it just was not what happened here.

WHY LOOKING AT THE ARTIFACTS IS NOT ENOUGH
    dashboard.restore_dirty_src already refuses when the tree verifies, but it
    runs `sha1sum -c` against whatever is in build/ WITHOUT REBUILDING. A
    worker that fails restores the source and leaves the artifact behind, so
    build/ routinely describes a source state that no longer exists. If those
    artifacts happen to read red while src/ holds a match, the guard opens and
    the match is destroyed. Staleness is therefore checked FIRST here, using
    relocation_check.staleness_warning() rather than a second copy of the
    rule, and a stale tree is never given a verdict.

WHAT THIS DOES NOT DO
    It never writes. It does not restore, commit, or touch the queue. The
    whole point is that the destructive step needs evidence in front of it,
    and evidence is all this produces.

Usage:
    python3 automation/orphan_check.py              # classify, read-only
    python3 automation/orphan_check.py --build      # build first, then classify
    python3 automation/orphan_check.py --self-test
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PENDING = REPO / "automation" / "logs" / "pending"
LOCK = REPO / "automation" / ".build.lock"

RX_STUB = re.compile(r'INCLUDE_ASM\(\s*"[^"]+"\s*,\s*(\w+)\s*\)')


def _run(argv, timeout=900):
    try:
        return subprocess.run(argv, cwd=str(REPO), capture_output=True,
                              text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:      # pragma: no cover
        class _R:
            returncode = 127
            stdout = ""
            stderr = f"{type(e).__name__}: {e}"
        return _R()


def dirty_src() -> list[str]:
    """Tracked files under src/ that differ from HEAD.

    Scoped to src/ on purpose. automation/ is written constantly by the
    harness and a dirty file there means nothing; a dirty file under src/ is
    either in-flight work or a result nobody recorded.
    """
    r = _run(["git", "status", "--porcelain", "--", "src"], timeout=120)
    if r.returncode != 0:
        return []
    out = []
    for line in (r.stdout or "").splitlines():
        if not line.strip() or line.startswith("??"):
            continue
        out.append(line[3:].strip())
    return out


def journalled() -> set[str]:
    """Files a crash journal already covers: in-flight, not orphaned."""
    got = set()
    for p in glob.glob(str(PENDING / "*.json")):
        try:
            with open(p, encoding="utf-8") as f:
                got.add(json.load(f).get("src_rel", ""))
        except (OSError, ValueError, AttributeError):
            continue
    got.discard("")
    return got


def functions_bodied(path: str) -> list[str]:
    """Which INCLUDE_ASM stubs this diff replaced with real code.

    A removed `INCLUDE_ASM(..., NAME)` line is exactly the event "NAME stopped
    being assembly", which is the thing worth naming in the report. Reading it
    off the diff means no guessing about what the worker was doing.
    """
    r = _run(["git", "diff", "--unified=0", "HEAD", "--", path], timeout=120)
    names = []
    for line in (r.stdout or "").splitlines():
        if line.startswith("-") and not line.startswith("---"):
            m = RX_STUB.search(line)
            if m and m.group(1) not in names:
                names.append(m.group(1))
    return names


def queue_status_by_function() -> dict:
    """function name -> (status, note), read THROUGH the scheduler.

    Never off disk: SOTN_QUEUE resolves per environment, and a direct read of
    the wrong file answers confidently and wrongly.
    """
    out = {}
    r = _run([sys.executable, str(REPO / "automation" / "scheduler.py"),
              "list"], timeout=180)
    for line in (r.stdout or "").splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        status, _score, tail = parts
        rid, _, note = tail.partition("|")
        rid = rid.strip()
        if ":" in rid:
            out[rid.rsplit(":", 1)[-1]] = (status, note.strip())
    return out


def verify() -> tuple[bool, str]:
    """The oracle, on whatever is currently in build/."""
    r = _run(["sha1sum", "-c", "config/check.us.sha"], timeout=900)
    lines = (r.stdout or "").splitlines()
    bad = [l for l in lines if l.strip().endswith(": FAILED")]
    ok = r.returncode == 0 and not bad
    n_ok = sum(1 for l in lines if l.strip().endswith(": OK"))
    return ok, (f"{n_ok}/{len(lines)} OK" if lines else
                (r.stderr or "no output")[:200])


def staleness() -> str:
    """Reused from relocation_check, never reimplemented."""
    sys.path.insert(0, str(REPO / "automation"))
    try:
        from relocation_check import staleness_warning
        return staleness_warning()
    except Exception as e:                                   # noqa: BLE001
        return f"could not determine build staleness ({e}); treat as stale"


def report(do_build: bool = False) -> int:
    files = dirty_src()
    if not files:
        print("src/ matches HEAD. Nothing uncommitted, nothing at risk.")
        return 0

    jrn = journalled()
    live = sorted(f for f in files if f in jrn)
    orphans = sorted(f for f in files if f not in jrn)

    print(f"{len(files)} modified file(s) under src/\n")
    if live:
        print("IN FLIGHT (a crash journal covers these; leave them alone):")
        for f in live:
            print(f"  {f}")
        print()
    if LOCK.exists():
        print("NOTE: automation/.build.lock exists, so a build or a worker "
              "may be running right now.\n      Any verdict below is a "
              "snapshot of a tree somebody else is editing.\n")
    if not orphans:
        print("No orphans: every modified file is journalled and will be "
              "restored or completed by its worker.")
        return 0

    print("ORPHANED (no crash journal, so nothing will ever clean these up):")
    qstat = queue_status_by_function()
    already_matched = []
    for f in orphans:
        fns = functions_bodied(f)
        print(f"  {f}")
        for fn in fns:
            status, note = qstat.get(fn, ("(not in queue)", ""))
            print(f"      {fn}: queue says {status}")
            if status == "matched":
                already_matched.append((f, fn, note))
    print()

    if already_matched:
        # THE ANSWER, WITHOUT A BUILD. The queue already carries a verified
        # match for these, hash and all. Restoring the file would not "undo a
        # failed attempt", it would delete the body that the queue is still
        # asserting exists, and the record would go quietly false.
        print("=" * 74)
        print("\nSTOP. The queue ALREADY records these as matched, with "
              "proof:\n")
        for f, fn, note in already_matched:
            print(f"  {fn}  ({f})")
            if note:
                print(f"      {note[:120]}")
        print("\nSo this is not unverified work and not debris: it is a "
              "verified match\nthat was never committed. Restoring the file "
              "would delete the body the\nqueue still claims exists, leaving "
              "a `matched` record with a hash for a\nfunction that is an "
              "INCLUDE_ASM stub again, and nothing would notice.\n")
        print("Commit them:\n")
        for f in sorted({f for f, _fn, _n in already_matched}):
            print(f"    git_add {f}")
        print()

    if do_build:
        print("building so the oracle describes THIS source ...")
        b = _run(["make", "build", "VERSION=us"], timeout=3600)
        print(f"  build rc={b.returncode}")
        if b.returncode != 0:
            print("\nThe build FAILED, so these cannot be matches as they "
                  "stand.\nThat is still not a licence to delete them: fix "
                  "or extract the work first.")
            return 1

    warn = staleness()
    if warn:
        print(warn)
        print("\nNO VERDICT. build/ describes a source state that no longer "
              "exists, so the\noracle would be answering a question about "
              "different code. This is exactly\nhow a landed match gets "
              "thrown away: stale artifacts read red, the guard\nopens, and "
              "the match in src/ is restored over.\n\nRe-run with --build.")
        return 2

    ok, detail = verify()
    print("=" * 74)
    if ok:
        print(f"\nTHESE ARE MATCHES. The oracle passes ({detail}) with them "
              f"applied.\n")
        print("DO NOT RESTORE THEM. Commit them:\n")
        for f in orphans:
            print(f"    git_add {f}")
        print("\nThen record the functions in the queue so the fleet does "
              "not redo them.")
        return 0

    print(f"\nNot a match ({detail}). These look like a failed attempt.\n")
    print("Restoring is REASONABLE here, but it is still a judgement call:\n"
          "a candidate that compiles and differs is worth keeping as a\n"
          "permuter seed rather than deleting. Check before discarding:\n")
    for f in orphans:
        print(f"    git_diff {f}")
    return 1


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    src_self = Path(__file__).read_text(errors="ignore")

    print("this tool cannot destroy anything")
    for bad in ("git checkout", "git restore", "git clean", "rmtree",
                "unlink"):
        ck(bad not in src_self.split("def self_test")[0],
           f"never calls {bad}")
    ck('"make", "build"' in src_self,
       "the only write it performs is a build, and only under --build")
    # scheduler.py IS invoked now, to read the queue. That is fine only for
    # as long as it stays a read: `report` is the write verb and must never
    # appear here, or a diagnostic could start changing statuses.
    _code0 = src_self.split("def self_test")[0]
    ck('"list"' in _code0, "the scheduler is called with list")
    ck('"report"' not in _code0,
       "and never with report, which is the verb that writes")

    print("\nstaleness is checked BEFORE any verdict is given")
    body = src_self[src_self.index("def report("):src_self.index("def self_test")]
    ck(body.index("staleness()") < body.index("verify()"),
       "staleness() is consulted first")
    ck("NO VERDICT" in body,
       "and a stale tree gets no verdict at all rather than a wrong one")
    ck("return 2" in body, "with its own exit code, distinct from red")

    print("\nthe queue is asked before the oracle is")
    # The lesson from the incident: all three functions were ALREADY matched
    # in the queue with proof, and the first version of this tool did not
    # look, so answering "what is this" needed a 110s build instead of a
    # lookup.
    ck(body.index("queue_status_by_function()") < body.index("staleness()"),
       "the queue lookup happens before the staleness gate")
    ck("already_matched" in body,
       "a matched record is called out specifically")
    ck("STOP" in body and "never committed" in body,
       "and the message says it is an uncommitted match, not debris")
    ck("scheduler.py" not in src_self.split("def queue_status_by_function")[0],
       "the queue is not read anywhere before the scheduler helper")
    _q = src_self.split("def queue_status_by_function")[1].split("\ndef ")[0]
    ck("scheduler.py" in _q and "queue.jsonl" not in _q,
       "and it goes through the scheduler, never at the file")

    print("\nthe staleness rule is reused, not reimplemented")
    ck("from relocation_check import staleness_warning" in src_self,
       "imported from relocation_check")
    # Scoped to the CODE, not the whole file: this assertion names the very
    # identifiers it is forbidding, so searching src_self entire made it fail
    # on itself. Same trap the requeue test hit by splitting on a prefix.
    _code = src_self.split("def self_test")[0]
    ck("oldest_bin" not in _code and "newest_src" not in _code,
       "and there is no second copy of the mtime comparison here")

    print("\njournalled files are separated from orphans")
    ck("f not in jrn" in body and "f in jrn" in body,
       "the split is on journal coverage")
    rc = (REPO / "automation" / "win" / "worker_direct.py").read_text(
        errors="ignore")
    ck('"src_rel"' in rc,
       "and src_rel is really the journal's field name for the path")

    print("\nbodied stubs are read off the diff, not guessed")
    ck(bool(RX_STUB.search('INCLUDE_ASM("boss/bo6/nonmatchings/richter", '
                           'BO6_RicStepThrowDaggers);')),
       "the stub regex matches a real line")
    ck(RX_STUB.search('INCLUDE_ASM("a/b", Foo);').group(1) == "Foo",
       "and captures the function name")
    ck(RX_STUB.search("INCLUDE_ASM(\n    \"a/b\", Foo);") is not None,
       "including the clang-format-wrapped form")

    print("\nonly src/ is examined")
    ck('"--", "src"' in src_self,
       "git status is scoped to src/, so a busy automation/ is ignored")

    print("\nthe real incident would have been caught")
    # The three functions that were nearly lost, as the diff presented them.
    diff_lines = [
        '-INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepThrowDaggers);',
        '-INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801B9D74);',
        '-INCLUDE_ASM("boss/bo6/nonmatchings/us_39144", func_us_801BA050);',
        '+void BO6_RicStepThrowDaggers(void) {',
    ]
    found = [RX_STUB.search(l).group(1) for l in diff_lines
             if l.startswith("-") and RX_STUB.search(l)]
    ck(found == ["BO6_RicStepThrowDaggers", "func_us_801B9D74",
                 "func_us_801BA050"],
       f"all three would have been named ({found})")
    ck(not [l for l in diff_lines
            if l.startswith("+") and RX_STUB.search(l)],
       "and an ADDED stub line is not counted as a body")

    print()
    if fails:
        print(f"{len(fails)} FAILED:")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true",
                    help="build first so the oracle describes the current "
                         "source (slow, takes the tree; still never restores)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    return report(a.build)


if __name__ == "__main__":
    raise SystemExit(main())
