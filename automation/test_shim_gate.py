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


def idx_for(wd):
    return json.loads((REPO / "automation" / "index.us.json").read_text())


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

    # --- THE DEFERRAL BRANCH ITSELF -----------------------------------------
    #
    # Every other assertion in this file is `not d`. Audit 2026-08-02 found the
    # consequence: shim_gate's entire `return True` path had never been executed
    # by any test, so the behaviour the gate EXISTS for was unverified, and the
    # file could have passed against a function that always returns False.
    #
    # No live stub currently qualifies (that is the honest state of the tree),
    # so the branch is reached by making shim_viable answer yes for one call.
    # The two extra blockers are real code and still run.
    ci = wd._codebase_index_module()
    real_viable = ci.shim_viable
    try:
        ci.shim_viable = lambda stage, stem, idx: (True, "no known blocker")
        d, why = wd.shim_gate({"src_rel": "src/st/rno0/e_particles.c"})
        check("DEFERRAL BRANCH: a genuinely shimmable record IS deferred", d,
              why[:110])
        check("the reason names the shim include",
              '#include "../e_particles.h"' in why, why[:140])
        check("the reason explains why generating would be wrong",
              "duplicate" in why.lower() or "rejected" in why.lower(), why[:140])

        # And the two extra blockers must still veto even when shim_viable
        # says yes, otherwise they are decorative.
        d2, why2 = wd.shim_gate({"src_rel": "src/st/rchi/e_breakable.c"})
        check("size divergence still vetoes a 'viable' record", not d2,
              why2[:110])
        saved_idx = wd._IDX_JSON
        wd._IDX_JSON = {
            "shared_impls": {
                "e_breakable": {
                    "working_shim_files": ["src/st/no0/e_breakable.c"]
                }
            },
            "splat_segments": {},
        }
        try:
            d3, why3 = wd.shim_gate(
                {"src_rel": "src/st/rno9/e_breakable.c"})
        finally:
            wd._IDX_JSON = saved_idx
        check("stage-data obligation still vetoes a 'viable' record", not d3,
              why3[:110])
    finally:
        ci.shim_viable = real_viable

    # --- the stage-data obligation -----------------------------------------
    #
    # Keep this deterministic instead of binding it to one live splat config.
    # RNO0 gained a named e_breakable data segment, which correctly removed the
    # old blocker. A synthetic stage with no named segment must still be blocked
    # using a current shim file as peer evidence.
    synthetic_idx = {
        "shared_impls": {
            "e_breakable": {
                "working_shim_files": ["src/st/no0/e_breakable.c"]
            }
        },
        "splat_segments": {},
    }
    why = wd.shim_needs_stage_data("rno9", "e_breakable", synthetic_idx)
    check("stage-data obligation blocks a stage without a named segment",
          bool(why), why[:110])
    check("stage-data reason names the missing .data segment",
          "'.data, e_breakable'" in why, why[:140])
    check("stage-data reason cites a current peer",
          "src/st/no0/e_breakable.c" in why, why[:140])

    # --- FALSE POSITIVES the size check must catch -------------------------
    #
    # shim_viable() reported "no known blocker" for all of these, because it
    # checks placement only. They are different implementations.
    #
    # rchi/e_breakable is the one that proves it: the file's own comment says
    # "roughly twice the size of the shared candle implementation (0x270 versus
    # 0x134 bytes)", a rejection upstream had ALREADY investigated. Deferring
    # it would have parked a record behind structural work that can never
    # happen.
    #
    # rno0/e_lock_camera is the direction a naive check misses: it is 0.36x its
    # peers, not larger. Too small is just as divergent as too large.
    # NOTE rno0/e_lock_camera was previously asserted here as "smaller, 0.36x,
    # different implementation". That was WRONG and this suite was encoding the
    # error: it was shimmed and matched on 2026-08-02 (81/81). The divergence
    # check had compared it against the 5 stages shimming e_lock_camera.h while
    # the 20 real shimmers include entity_lock_camera.h and have c segments of
    # 0x1BC, exactly rno0's. The check still keys on FILENAME stem, so it is
    # unreliable whenever the header is named differently; that limitation is
    # recorded rather than asserted as truth.
    for stage, stem, why_frag in (
            ("rchi", "e_breakable", "larger"),):
        d, why = wd.shim_gate({"src_rel": f"src/st/{stage}/{stem}.c"})
        check(f"{stage}/{stem}: size divergence blocks the shim", not d, why[:110])
        check(f"{stage}/{stem}: reason says {why_frag}", why_frag in why, why[:110])
        check(f"{stage}/{stem}: reason gives both sizes",
              "0x" in why and "x," in why, why[:110])

    # the divergence check itself, directly
    check("divergence is silent for an unknown stem",
          wd.shim_size_divergence("rno0", "no_such_stem", idx_for(wd)) == "")

    # --- blocked must NOT be deferred, only annotated ----------------------
    # RCHI's e_breakable is a measured different implementation, so the live
    # size blocker must keep it on the generation path.
    d, why = wd.shim_gate({"src_rel": "src/st/rchi/e_breakable.c"})
    check("rchi/e_breakable: blocked but NOT deferred", not d, why[:90])
    check("rchi/e_breakable: blocker is still reported",
          "blocked" in why.lower(), why[:90])

    # --- files with no shared implementation are silent ---------------------
    d, why = wd.shim_gate({"src_rel": "src/st/rno0/no_such_stem.c"})
    check("no shared impl: not deferred", not d, why[:90])

    # --- paths outside src/st/<stage>/<stem>.c are out of scope -------------
    # _psp and _saturn are different BUILD TARGETS. shim_viable reasons from
    # config/splat.us.* and the us oracle cannot verify a change to them, so a
    # verdict either way would be unfounded.
    for p in ("src/boss/bo6/richter.c", "src/dra/menu.c", "src/st/e_red_door.h",
              "src/st/rchi_psp/e_breakable.c", "src/st/rno0_psp/e_lock_camera.c",
              "", "weird"):
        d, why = wd.shim_gate({"src_rel": p})
        check(f"out of scope, silent: {p!r}", (not d) and why == "", why[:60])

    # --- must never raise ---------------------------------------------------
    wd.WIN_REPO = "/nonexistent-path"
    wd._IDX_JSON = None      # the index is cached per process; clear it too
    try:
        d, why = wd.shim_gate({"src_rel": "src/st/rno0/e_breakable.c"})
        check("missing index degrades to no-defer, does not raise", not d)
    finally:
        wd.WIN_REPO = str(REPO)
        wd._CI_MOD = None
        wd._IDX_JSON = None

    # --- and it must actually be reachable BEFORE generation ----------------
    src = (REPO / "automation" / "win" / "worker_direct.py").read_text(
        encoding="utf-8", errors="replace")
    check("shim_gate is called in the record path",
          "_defer, _why = shim_gate(ctx)" in src)
    # Anchor on the REAL model call, not the dry-run preview.
    #
    # This used to compare against `build_prompt(rec, ctx)`, which occurs only
    # inside the dry-run branch. The live call is `build_prompt(rec, ctx,
    # feedback)`, so the assertion proved the gate preceded a preview nobody
    # runs in production. Found by audit 2026-08-02.
    check("the real model call exists and is distinct from the preview",
          "build_prompt(rec, ctx, feedback)" in src)
    check("it runs BEFORE the real model call",
          src.index("_defer, _why = shim_gate(ctx)")
          < src.index("build_prompt(rec, ctx, feedback)"))
    check("deferrals carry a greppable marker",
          "DEFER_SHIMMABLE" in src and "SHIM_INSTEAD_OF_GENERATE" in src)

    # --- the population split must still hold -------------------------------
    # If a future change makes this gate suddenly eager, this catches it before
    # the fleet stalls.
    idx = json.loads((REPO / "automation" / "index.us.json").read_text())
    inc = re.compile(r'INCLUDE_ASM\("([^"]+)",\s*(\w+)\)')
    deferred = generated = 0
    deferred_paths = []
    for c in (REPO / "src" / "st").glob("*/*.c"):
        n = len(inc.findall(c.read_text(errors="replace")))
        if not n:
            continue
        rel = f"src/st/{c.parent.name}/{c.name}"
        d, _ = wd.shim_gate({"src_rel": rel})
        if d:
            deferred += n
            deferred_paths.append(f"{rel} ({n})")
        else:
            generated += n
    print(f"\n  population: {deferred} stubs deferred, {generated} still generated")
    if deferred_paths:
        print("  deferred paths: " + ", ".join(deferred_paths))
    # The gate first reported 8 shimmable stubs. Most were false positives:
    # different implementations, non-US targets, or missing stage-data slots.
    # The audited live exceptions are RNO1's two red-door stubs plus RNO0's
    # e_breakable and e_collect stubs. RNO0 now has named data segments for both,
    # so the regenerated index correctly removes their former placement blocker.
    #
    # Any new path must be audited before it can be accepted here. A subset is
    # allowed because landing the approved shim removes it from the population.
    approved = {
        "src/st/rno0/e_breakable.c (1)",
        "src/st/rno0/e_collect.c (1)",
        "src/st/rno1/e_red_door.c (2)",
    }
    unaudited = set(deferred_paths) - approved
    check("no unaudited stub is claimed shimmable", not unaudited,
          ", ".join(sorted(unaudited)))
    check("deferrals could never stall the fleet", deferred < generated * 0.10,
          f"{deferred} vs {generated}")

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
