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
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    spec = importlib.util.spec_from_file_location(
        "worker_direct", REPO / "automation" / "win" / "worker_direct.py")
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)

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

    old_repo = wd.WIN_REPO
    wd.WIN_REPO = str(tmp)
    try:
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
    finally:
        wd.WIN_REPO = old_repo

    # --- the contracts in the source ---------------------------------------
    src = (REPO / "automation" / "win" / "worker_direct.py").read_text(
        encoding="utf-8", errors="replace")
    check("replay holds BuildLock", "with BuildLock(" in
          inspect.getsource(wd.replay_pending_journals))
    check("journal_write records a pid", '"pid": os.getpid()' in src)
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
