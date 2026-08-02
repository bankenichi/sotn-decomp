#!/usr/bin/env python3
"""Does the worker refuse to generate C that should have been a shim? (P6)

WHY THIS EXISTS
    `shim_viable()` in codebase_index.py could always answer "this file should
    defer to src/st/<stem>.h"; it just told a human. Meanwhile the fleet spent
    model quota writing private copies of code the tree already had, which the
    quality audit then flagged as duplicates and a reviewer then rejected. The
    cheapest possible fix is to ask the question before the model call.

WHY IT DEFERS ONLY ONE OF THE THREE GROUPS
    Measured over the 417 INCLUDE_ASM stubs in src/st before wiring:

        288  no shared implementation      -> generating is correct
        121  shared impl exists, BLOCKED   -> generating is the only option today
          8  shimmable NOW, no blocker     -> generating is simply wrong work

    ROADMAP P6 says a record whose target is a shared-implementation file
    "should not reach a model at all until the blocker is cleared". Applied
    literally that defers all 129 and stalls 29% of the queue behind structural
    work with no automated consumer. The narrowing is deliberate: defer the 8
    that have a free correct answer, annotate the 121 so the blocker is visible
    without blocking the record.

    Both halves are asserted below, because the failure modes are opposite. Too
    eager and the fleet starves; too lax and it keeps producing duplicates.

Run:  python3 automation/test_shim_gate.py
Exit: 0 all pass, 1 otherwise.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    spec = importlib.util.spec_from_file_location(
        "worker_direct", REPO / "automation" / "win" / "worker_direct.py")
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)
    wd.WIN_REPO = str(REPO)

    failures = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        print(("  ok   " if cond else "  FAIL ") + name
              + ("" if cond else "   " + detail))
        if not cond:
            failures.append(name)

    # --- shimmable NOW must be deferred ------------------------------------
    # rno0/e_lock_camera and rno0/e_breakable were both measured as
    # "no known blocker" while still carrying INCLUDE_ASM stubs.
    for stage, stem in (("rno0", "e_lock_camera"), ("rno0", "e_breakable")):
        d, why = wd.shim_gate({"src_rel": f"src/st/{stage}/{stem}.c"})
        check(f"{stage}/{stem}: deferred rather than generated", d, why[:90])
        check(f"{stage}/{stem}: reason names the shim include",
              f'#include "../{stem}.h"' in why, why[:90])

    # --- blocked must NOT be deferred, only annotated ----------------------
    # rno0/e_blade has no shared impl to defer to; rno0/collision has one but
    # is blocked on a missing .data segment. Neither may stall.
    for stage, stem in (("rno0", "collision"), ("rno0", "e_collect")):
        d, why = wd.shim_gate({"src_rel": f"src/st/{stage}/{stem}.c"})
        check(f"{stage}/{stem}: blocked but NOT deferred", not d, why[:90])
        check(f"{stage}/{stem}: blocker is still reported",
              "blocked" in why.lower(), why[:90])

    # --- files with no shared implementation are silent ---------------------
    d, why = wd.shim_gate({"src_rel": "src/st/rno0/e_blade.c"})
    check("no shared impl: not deferred", not d, why[:90])

    # --- paths outside src/st/<stage>/<stem>.c are out of scope -------------
    for p in ("src/boss/bo6/richter.c", "src/dra/menu.c", "src/st/e_red_door.h",
              "", "weird"):
        d, why = wd.shim_gate({"src_rel": p})
        check(f"out of scope, silent: {p!r}", (not d) and why == "", why[:60])

    # --- must never raise ---------------------------------------------------
    wd.WIN_REPO = "/nonexistent-path"
    try:
        d, why = wd.shim_gate({"src_rel": "src/st/rno0/e_breakable.c"})
        check("missing index degrades to no-defer, does not raise", not d)
    finally:
        wd.WIN_REPO = str(REPO)
        wd._CI_MOD = None

    # --- and it must actually be reachable BEFORE generation ----------------
    src = (REPO / "automation" / "win" / "worker_direct.py").read_text(
        encoding="utf-8", errors="replace")
    check("shim_gate is called in the record path",
          "_defer, _why = shim_gate(ctx)" in src)
    check("it runs BEFORE the first model call",
          src.index("_defer, _why = shim_gate(ctx)") < src.index("build_prompt(rec, ctx)"))
    check("deferrals carry a greppable marker",
          "DEFER_SHIMMABLE" in src and "SHIM_INSTEAD_OF_GENERATE" in src)

    # --- the population split must still hold -------------------------------
    # If a future change makes this gate suddenly eager, this catches it before
    # the fleet stalls.
    idx = json.loads((REPO / "automation" / "index.us.json").read_text())
    inc = re.compile(r'INCLUDE_ASM\("([^"]+)",\s*(\w+)\)')
    deferred = generated = 0
    for c in (REPO / "src" / "st").glob("*/*.c"):
        n = len(inc.findall(c.read_text(errors="replace")))
        if not n:
            continue
        rel = f"src/st/{c.parent.name}/{c.name}"
        d, _ = wd.shim_gate({"src_rel": rel})
        if d:
            deferred += n
        else:
            generated += n
    print(f"\n  population: {deferred} stubs deferred, {generated} still generated")
    check("deferrals stay a small minority", deferred < generated * 0.10,
          f"{deferred} vs {generated}")
    check("something is actually deferred", deferred > 0, str(deferred))

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
