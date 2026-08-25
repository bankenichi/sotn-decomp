#!/usr/bin/env python3
"""Does journal replay leave LIVE workers alone, and clear a match's journal?

WHY THIS EXISTS
    The restore journal is the harness's crash protection, and two defects in
    it were found by audit on 2026-08-02. Both destroy work silently, and
    neither shows up as an error.

    1. journal_clear() had exactly ONE call site, inside restore(). The match
       path deliberately does not call restore(), because a match must keep its
       edit. So after every SUCCESS the journal survived holding the pre-edit
       INCLUDE_ASM stub, and replay_pending_journals() -- which runs at worker
       startup, from the SIGTERM handler and on Ctrl-C -- would write that stub
       back over the matched function while the queue still said `matched`
       with machine proof.

    2. replay_pending_journals() replayed EVERY journal in the directory,
       regardless of owner or liveness, without holding BuildLock. A worker
       joining a running fleet reverted another worker's in-flight edit; that
       worker then built the stub, misfiled the outcome, and lost its own crash
       protection because the journal was deleted underneath it. With four
       workers and staggered starts this is the normal case, not a rare race.

Run:  python3 automation/test_journal_replay.py
Exit: 0 all pass, 1 otherwise.
"""
from __future__ import annotations

import importlib.util
import inspect
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    spec = importlib.util.spec_from_file_location(
        "worker_direct", REPO / "automation" / "win" / "worker_direct.py")
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)
    sys.modules["worker_direct"] = wd
    ps_spec = importlib.util.spec_from_file_location(
        "permuter_supervisor", REPO / "automation" / "permuter_supervisor.py")
    ps = importlib.util.module_from_spec(ps_spec)
    ps_spec.loader.exec_module(ps)

    failures = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        print(("  ok   " if cond else "  FAIL ") + name
              + ("" if cond else "   " + detail))
        if not cond:
            failures.append(name)

    # --- liveness helper, the guard everything else rests on ----------------
    check("own pid counts as alive", wd._pid_alive(os.getpid()))
    check("pid 0 is not alive", not wd._pid_alive(0))
    # A pid that cannot exist. Linux pids are bounded well below this.
    check("an impossible pid is not alive", not wd._pid_alive(4_000_000))

    # --- replay in a scratch repo ------------------------------------------
    tmp = Path(tempfile.mkdtemp())
    (tmp / "automation" / "logs" / "pending").mkdir(parents=True)
    (tmp / "src").mkdir()
    target = tmp / "src" / "victim.c"
    target.write_text("APPLIED CANDIDATE\n", encoding="utf-8")

    pend = tmp / "automation" / "logs" / "pending"

    def journal(name, pid):
        (pend / name).write_text(json.dumps({
            "src_rel": "src/victim.c", "original": "ORIGINAL STUB\n",
            "worker": name[:-5], "pid": pid, "at": 0}), encoding="utf-8")

    def disarmed(path: Path) -> bool:
        if not path.exists():
            return True
        return json.loads(path.read_text(encoding="utf-8")).get("files") == []

    old_repo = wd.WIN_REPO
    wd.WIN_REPO = str(tmp)
    try:
        old_exists = wd.os.path.exists
        wd.os.path.exists = lambda _path: (_ for _ in ()).throw(
            PermissionError("induced stat denial"))
        try:
            clear_without_precheck = wd.journal_clear()
        finally:
            wd.os.path.exists = old_exists
        check("journal disarm never treats a stat denial as already clear",
              clear_without_precheck)

        # A LIVE owner's journal must be untouched. This is the dangerous one.
        journal("worker-live.json", os.getpid() + 0)   # ourselves == alive
        # make it a foreign live pid: use our own, but not equal to getpid()
        (pend / "worker-live.json").write_text(json.dumps({
            "src_rel": "src/victim.c", "original": "ORIGINAL STUB\n",
            "worker": "worker-live", "pid": os.getppid(), "at": 0}),
            encoding="utf-8")
        n = wd.replay_pending_journals()
        check("a live owner's journal is NOT replayed", n == 0, f"n={n}")
        check("and the applied file is untouched",
              target.read_text() == "APPLIED CANDIDATE\n", target.read_text())
        check("and the journal survives for its owner",
              (pend / "worker-live.json").exists())

        # A DEAD owner's journal must be replayed.
        (pend / "worker-live.json").unlink()
        journal("worker-dead.json", 4_000_000)
        n = wd.replay_pending_journals()
        check("a dead owner's journal IS replayed", n == 1, f"n={n}")
        check("and the source is restored",
              target.read_text() == "ORIGINAL STUB\n", target.read_text())
        check("and the journal is consumed",
              not (pend / "worker-dead.json").exists())

        # A batch journal restores every file as one recovery transaction while
        # old one-file journals above remain readable.
        first = tmp / "src" / "first.c"
        second = tmp / "src" / "second.c"
        first_stub = ('INCLUDE_ASM("st/rno0/nonmatchings/first", One);\n'
                      'INCLUDE_ASM("st/rno0/nonmatchings/first", Two);\n')
        second_stub = 'INCLUDE_ASM("st/rno0/nonmatchings/second", Three);\n'
        first.write_text(first_stub, encoding="utf-8")
        second.write_text(second_stub, encoding="utf-8")
        originals = wd.apply_code_batch([
            ({"src_rel": "src/first.c",
              "asm_rel": "st/rno0/nonmatchings/first"},
             "One", "void One(void) {}\n"),
            ({"src_rel": "src/first.c",
              "asm_rel": "st/rno0/nonmatchings/first"},
             "Two", "void Two(void) {}\n"),
            ({"src_rel": "src/second.c",
              "asm_rel": "st/rno0/nonmatchings/second"},
             "Three", "void Three(void) {}\n"),
        ])
        check("a batch applies several stubs in one file",
              "void One" in first.read_text() and "void Two" in first.read_text())
        check("a batch applies another file in the same transaction",
              "void Three" in second.read_text())
        batch_journal = pend / f"{wd.WORKER_NAME}.json"
        saved = json.loads(batch_journal.read_text(encoding="utf-8"))
        check("the batch journal retains every original",
              len(saved.get("files", [])) == 2, repr(saved))
        wd.restore_many(originals)
        check("batch restore is byte-exact for the first file",
              first.read_text() == first_stub, first.read_text())
        check("batch restore is byte-exact for the second file",
              second.read_text() == second_stub, second.read_text())
        check("batch restore consumes the transaction journal",
              disarmed(batch_journal))

        # The recovery path must understand the new multi-file schema, not just
        # the legacy one-file journal above.
        wd.apply_code_batch([
            ({"src_rel": "src/first.c",
              "asm_rel": "st/rno0/nonmatchings/first"},
             "One", "void One(void) {}\n"),
            ({"src_rel": "src/second.c",
              "asm_rel": "st/rno0/nonmatchings/second"},
             "Three", "void Three(void) {}\n"),
        ])
        crashed = json.loads(batch_journal.read_text(encoding="utf-8"))
        crashed["pid"] = 4_000_000
        batch_journal.write_text(json.dumps(crashed), encoding="utf-8")
        n = wd.replay_pending_journals()
        check("dead-worker replay restores every batch file", n == 2, f"n={n}")
        check("crash replay is byte-exact for the first file",
              first.read_text() == first_stub, first.read_text())
        check("crash replay is byte-exact for the second file",
              second.read_text() == second_stub, second.read_text())
        check("crash replay consumes the batch journal",
              not batch_journal.exists())

        # Fail after the first file is written, then fail one of the immediate
        # restores too. The original bytes must remain in the journal until a
        # later replay can complete recovery.
        real_open = open
        second_path = str(second)

        def fail_second_write(path, mode="r", *args, **kwargs):
            if os.fspath(path) == second_path and "w" in mode:
                raise OSError("induced second-file write/restore failure")
            return real_open(path, mode, *args, **kwargs)

        wd.open = fail_second_write
        partial_failed = False
        try:
            wd.apply_code_batch([
                ({"src_rel": "src/first.c",
                  "asm_rel": "st/rno0/nonmatchings/first"},
                 "One", "void One(void) {}\n"),
                ({"src_rel": "src/second.c",
                  "asm_rel": "st/rno0/nonmatchings/second"},
                 "Three", "void Three(void) {}\n"),
            ])
        except OSError:
            partial_failed = True
        finally:
            del wd.open
        check("a partial batch write raises", partial_failed)
        check("a failed immediate restore retains the journal",
              batch_journal.exists())
        saved = json.loads(batch_journal.read_text(encoding="utf-8"))
        saved["pid"] = 4_000_000
        batch_journal.write_text(json.dumps(saved), encoding="utf-8")
        n = wd.replay_pending_journals()
        check("later replay recovers a partial-write transaction", n == 2,
              f"n={n}")
        check("partial-write replay restores the first file exactly",
              first.read_text() == first_stub, first.read_text())
        check("partial-write replay restores the second file exactly",
              second.read_text() == second_stub, second.read_text())
        check("successful retry consumes the retained journal",
              not batch_journal.exists())

        # Exercise the supervisor's batch failure behavior with real source
        # application and restore, while replacing only the expensive build and
        # checksum boundaries.
        old_ps_repo = ps.REPO
        old_find_stub = ps.find_stub
        old_build_check = wd.build_and_check
        old_journal_clear = wd.journal_clear
        old_verify = ps.verify_checksums
        ps.REPO = tmp
        stub_map = {
            "One": (first, "st/rno0/nonmatchings/first", ""),
            "Three": (second, "st/rno0/nonmatchings/second", ""),
        }
        ps.find_stub = lambda fn, _overlay: stub_map.get(fn)

        class NullLock:
            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

        entries = [
            {"record_id": "us:ST/RNO0:One", "function": "One",
             "body": "void One(void) {}\n"},
            {"record_id": "us:ST/RNO0:Three", "function": "Three",
             "body": "void Three(void) {}\n"},
        ]
        try:
            build_results = iter([(False, "FAILED: induced candidate failure"),
                                  (True, "baseline green")])
            wd.build_and_check = lambda _rec: next(build_results)
            ok, detail = ps.land_match_batch(entries, lock=NullLock)
            check("supervisor batch failure is not accepted", not ok, detail)
            check("supervisor batch failure restores the first file",
                  first.read_text() == first_stub, first.read_text())
            check("supervisor batch failure restores the second file",
                  second.read_text() == second_stub, second.read_text())
            check("supervisor batch failure consumes a completed restore journal",
                  disarmed(batch_journal))

            build_results = iter([(True, "candidate compiled"),
                                  (False, "baseline red")])
            wd.build_and_check = lambda _rec: next(build_results)
            ps.verify_checksums = lambda _build: (False, "checksum mismatch")
            ok, detail = ps.land_match_batch(entries, lock=NullLock)
            check("checksum failure with red reverted baseline is unattributed",
                  not ok and "TREE ALREADY BROKEN" in detail, detail)
            check("red-baseline path still restores both files exactly",
                  first.read_text() == first_stub
                  and second.read_text() == second_stub)

            build_results = iter([(True, "candidate compiled"),
                                  (False, "singleton baseline red")])
            wd.build_and_check = lambda _rec: next(build_results)
            ps.verify_checksums = lambda _build: (False, "checksum mismatch")
            ok, detail = ps.land_match(
                tmp, "One", body="void One(void) {}\n",
                rec_id="us:ST/RNO0:One", lock=NullLock)
            check("singleton checksum failure also audits the reverted baseline",
                  not ok and "TREE ALREADY BROKEN" in detail, detail)
            check("singleton red-baseline path restores its source exactly",
                  first.read_text() == first_stub, first.read_text())

            build_results = iter([(True, "candidate compiled")])
            wd.build_and_check = lambda _rec: next(build_results)
            ps.verify_checksums = lambda _build: (True, "oracle green")
            wd.journal_clear = lambda: False
            ok, detail = ps.land_match_batch(entries, lock=NullLock)
            check("a replayable journal prevents GREEN",
                  not ok and "journal could not be disarmed" in detail, detail)
            check("journal-disarm failure restores both files exactly",
                  first.read_text() == first_stub
                  and second.read_text() == second_stub)
            check("failed disarm retains recovery evidence",
                  batch_journal.exists())
            wd.journal_clear = old_journal_clear
            saved = json.loads(batch_journal.read_text(encoding="utf-8"))
            saved["pid"] = 4_000_000
            batch_journal.write_text(json.dumps(saved), encoding="utf-8")
            wd.replay_pending_journals()
        finally:
            ps.REPO = old_ps_repo
            ps.find_stub = old_find_stub
            wd.build_and_check = old_build_check
            wd.journal_clear = old_journal_clear
            ps.verify_checksums = old_verify
    finally:
        wd.WIN_REPO = old_repo

    # --- the contracts in the source ---------------------------------------
    src = (REPO / "automation" / "win" / "worker_direct.py").read_text(
        encoding="utf-8", errors="replace")
    check("replay holds BuildLock", "with BuildLock(" in
          inspect.getsource(wd.replay_pending_journals))
    check("journal_write records a pid", '"pid": os.getpid()' in src)
    publish_src = inspect.getsource(wd.journal_write_many)
    check("journal publication fsyncs prepared bytes before atomic replace",
          publish_src.index("f.flush()") < publish_src.index("os.fsync(")
          < publish_src.index("os.replace("))
    check("journal publication durably commits the rename",
          publish_src.index("os.replace(") < publish_src.index("_fsync_parent("))
    clear_src = inspect.getsource(wd.journal_clear)
    check("journal clear durably commits its empty replacement",
          clear_src.index("os.replace(") < clear_src.index("_fsync_parent("))
    check("journal clear retains the harmless committed record",
          "os.unlink(path)" not in clear_src)
    check("journal_clear has TWO call sites (restore AND the match path)",
          src.count("journal_clear()") >= 3,   # def + 2 calls
          str(src.count("journal_clear()")))
    i = src.index("matched = True")
    check("the match path clears the journal",
          "journal_clear()" in src[i:i + 1400])

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
