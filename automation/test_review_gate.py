#!/usr/bin/env python3
"""Does the worker's PRE-BUILD review gate actually reject what it claims to?

WHY THIS EXISTS
    review_checks.py could always catch these defects; it just ran afterwards,
    for a human (ROADMAP P4). Wiring it into the worker means a defect costs
    one retry with specific feedback instead of a review cycle. Two things can
    go wrong and neither shows up as a crash:

      - the gate silently inspects the UNMODIFIED file. `virtual_apply` has to
        reproduce `apply_code`'s substitution exactly; if that regex drifts,
        the candidate never lands in the text being checked and every defect
        passes. That is the dangerous failure, because it looks like success.

      - the gate rejects good code, which burns an attempt and can make a
        record unmatchable.

    The linkage case is the one worth the trouble. Adding `static` to
    StepTowards broke the link during an earlier session: a reviewer grepped
    the C sources, found no caller and concluded it was file-local. The callers
    were INCLUDE_ASM stubs in a sibling .c, invisible to grep and entirely
    visible to the linker. Catching it here saves the whole build cycle.

Run:  python3 automation/test_review_gate.py
Exit: 0 all pass, 1 otherwise.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from pathlib import Path as _P0

REPO = Path(__file__).resolve().parent.parent

# A real file with a real INCLUDE_ASM stub, not a fixture. The substitution is
# the thing under test, so it has to run against text that actually ships.
TARGET_SRC = "src/st/rno0/e_gorgon.c"
TARGET_ASM = "st/rno0/nonmatchings/e_gorgon"
TARGET_FN = "func_801CD78C_801CEB40"


def pick_cross_tu_fixture(overlay_dir: Path):
    """Find a live (file, function) pair that the linkage check must reject.

    DERIVED, not hardcoded, and that is the point. This fixture used to name
    func_801CE04C in unk_4A320.c, whose foreign callers lived in e_hammer,
    e_gurkha and e_blade assembly. Shimming those three files on 2026-08-02
    removed their INCLUDE_ASM stubs, which correctly un-owned their .s files, so
    the callers vanished and four assertions here failed.

    Nothing was wrong with the gate or with the shims. The test had pinned
    itself to a fact about the tree that the project's own progress is supposed
    to change: every shim deletes cross-TU assembly callers, so any hardcoded
    example here has a shelf life. Re-pinning it to another function would just
    reset the timer.

    So: reproduce check_linkage_vs_asm's ownership rule (an .s file is owned by
    the .c that INCLUDE_ASMs the function of the same name) and return the first
    pair where the callers are owned by a DIFFERENT, still-live .c. Returns
    (src_rel, asm_rel, function, callers) or None if the overlay has run out of
    such pairs, which is a legitimate end state and is reported, not failed.
    """
    import re
    from collections import defaultdict

    owner: dict[str, str] = {}
    inc = re.compile(r'INCLUDE_ASM\(\s*"[^"]*/([^"/]+)"\s*,\s*(\w+)')
    for c in sorted(overlay_dir.glob("*.c")):
        try:
            for m in inc.finditer(c.read_text(errors="ignore")):
                owner[m.group(2)] = c.name
        except OSError:
            continue

    asm_root = (REPO / "asm" / "us" / "st" / overlay_dir.name / "nonmatchings")
    if not asm_root.is_dir():
        return None
    ref_re = re.compile(r"\b(?:jal|\.word)\s+([A-Za-z_]\w*)")
    callers: dict[str, set] = defaultdict(set)
    for s in asm_root.rglob("*.s"):
        own = owner.get(s.stem)
        if not own:                      # unowned .s: shimmed away, not in the build
            continue
        try:
            t = s.read_text(errors="ignore")
        except OSError:
            continue
        for sym in set(ref_re.findall(t)):
            callers[sym].add(own)

    for fn, owning_c in sorted(owner.items()):
        foreign = callers.get(fn, set()) - {owning_c}
        if foreign:
            stem = Path(owning_c).stem
            return (f"src/st/{overlay_dir.name}/{owning_c}",
                    f"st/{overlay_dir.name}/nonmatchings/{stem}",
                    fn, sorted(foreign))
    return None


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

    ctx = {"src_rel": TARGET_SRC, "asm_rel": TARGET_ASM}

    # --- the substitution must really happen -------------------------------
    marker = "/* UNIQUE_CANARY_9137 */"
    body = f"{marker}\nvoid {TARGET_FN}(void) {{}}\n"
    virt = wd.virtual_apply(ctx, TARGET_FN, body)
    check("virtual_apply returns the file", len(virt) > 200, f"got {len(virt)}")
    check("candidate is actually substituted in", marker in virt)
    check("the stub it replaced is gone",
          f'INCLUDE_ASM("{TARGET_ASM}", {TARGET_FN});' not in virt)
    check("sibling stubs are left alone",
          "func_us_801D2424_from_are" in virt)
    check("unknown stub yields empty, not a wrong-file check",
          wd.virtual_apply(ctx, "NoSuchFunction", body) == "")

    # --- THE defect this is for: static across a TU boundary ---------------
    #
    # Some function is stubbed in one .c and `jal`-ed from assembly owned by a
    # sibling .c. A source grep sees no caller, so `static` looks obviously
    # right and breaks the link. Same shape as the StepTowards incident that
    # motivated the check. Which function that is gets DERIVED below, because
    # the answer changes every time a file is shimmed.
    #
    # The first version of this test used StepTowards directly and failed,
    # correctly: StepTowards is a real function in e_gorgon.c, not an
    # INCLUDE_ASM stub, so virtual_apply refused to substitute and the gate
    # returned nothing. The gate was right and the test was wrong. Keeping the
    # note because "the check did not fire" is exactly the symptom a broken
    # substitution would also produce, and the two must not be confused.
    picked = pick_cross_tu_fixture(REPO / "src" / "st" / "rno0")
    if picked is None:
        print("  ~~ rno0 has no stub with foreign asm callers left; the linkage "
              "assertions below cannot be exercised here. Not a failure: it "
              "means every such stub has been shimmed. Point "
              "pick_cross_tu_fixture at another overlay to keep the coverage.")
        x_src = x_asm = x_fn = None
    else:
        x_src, x_asm, x_fn, x_callers = picked
        print(f"  -- fixture: {x_fn} stubbed in {x_src}, called from "
              f"{', '.join(x_callers)}")
    if x_fn:
        x_ctx = {"src_rel": x_src, "asm_rel": x_asm}
        static_code = (f"static void {x_fn}(Entity* self) "
                       f"{{\n    self->step++;\n}}\n")
        found = wd.review_gate(x_ctx, x_fn, static_code)
        check("static-across-TU is rejected",
              any("linkage" in f for f in found), repr(found[:2]))
        check("the rejection names the foreign callers",
              any(".c" in f and "references it across" in f for f in found),
              repr(found[:2]))
        check("the rejection explains WHY grep missed it",
              any("INCLUDE_ASM" in f for f in found), repr(found[:2]))

        # the SAME function without static must pass, or the check is just noise
        ok_code = f"void {x_fn}(Entity* self) {{\n    self->step++;\n}}\n"
        check("the same function without static passes",
              wd.review_gate(x_ctx, x_fn, ok_code) == [],
              repr(wd.review_gate(x_ctx, x_fn, ok_code)))

    # --- good code must pass ------------------------------------------------
    clean = (f"void {TARGET_FN}(void) {{\n"
             f"    g_CurrentEntity->step++;\n}}\n")
    check("clean candidate is not rejected",
          wd.review_gate(ctx, TARGET_FN, clean) == [],
          repr(wd.review_gate(ctx, TARGET_FN, clean)))

    # --- findings about OTHER functions must not fail this attempt ---------
    #
    # The file can carry pre-existing findings in code this worker did not
    # write. Failing on those would make the record unmatchable forever.
    #
    # This assertion USED TO BE VACUOUS. It ran the gate on a candidate that
    # produced zero findings and asserted `all(... for f in [])`, which is true
    # of anything: the per-function filter it claims to test could be deleted
    # and the suite stayed green. Audit 2026-08-02.
    #
    # The fix is to construct a candidate that provably DOES produce a finding
    # about another function -- a static helper the sibling assembly calls --
    # and then assert both that findings exist and that this one is excluded.
    # The helper must be one a WIRED check actually fires on. `linkage` is the
    # only check that reports a function-scoped finding here, and it fires on a
    # `static` function that sibling assembly calls across a TU boundary.
    # The offending `static` must belong to a DIFFERENT function than the one
    # under generation. Targeting the cross-TU function itself would make the
    # finding self-referential, and the filter would correctly drop it as "the
    # function being generated" -- which is what made an earlier attempt at this
    # fixture still vacuous.
    #
    # Both names are derived, for the reason given on pick_cross_tu_fixture:
    # hardcoding either one pins the test to a fact that shimming is meant to
    # change.
    if x_fn:
        import re as _re
        _src_text = _P0(wd.win_path(x_src)).read_text(errors="ignore")
        _stubs = [m for m in _re.findall(r'INCLUDE_ASM\([^,]+,\s*(\w+)\s*\)',
                                         _src_text) if m != x_fn]
        if not _stubs:
            print(f"  ~~ {x_src} has no second stub to host the noisy static; "
                  f"the filter assertions are skipped, not failed.")
        else:
            noisy_fn = _stubs[0]
            noisy_code = (f"void {noisy_fn}(Entity* self) {{ self->step++; }}\n"
                          f"static void {x_fn}(Entity* s) {{ s->step++; }}\n")
            virt = wd.virtual_apply(x_ctx, noisy_fn, noisy_code)
            check("the noisy fixture really lands in the inspected text",
                  f"static void {x_fn}" in virt)

            # Prove the filter has something to filter: with the filter
            # bypassed, the SAME source yields a finding for another function.
            rc = wd._review_checks_module()
            unfiltered = []
            for key in wd._REVIEW_GATE_CHECKS:
                fnc = rc.CHECKS.get(key)
                if not fnc:
                    continue
                try:
                    unfiltered += [
                        f for f in fnc(_P0(wd.win_path(x_ctx["src_rel"])), virt)
                        if f.get("function") and f["function"] != noisy_fn]
                except Exception:
                    pass
            check("the fixture DOES produce findings about other functions",
                  len(unfiltered) > 0,
                  "no other-function finding was produced, so the filter below "
                  "is untested; pick a fixture that trips a wired check")

            noisy = wd.review_gate(x_ctx, noisy_fn, noisy_code)
            check("and the gate excludes every one of them",
                  all(f["function"] not in " ".join(noisy)
                      for f in unfiltered if f.get("function")),
                  repr(noisy[:2]))

    # --- never raises -------------------------------------------------------
    bad_ctx = {"src_rel": "src/does/not/exist.c", "asm_rel": "nope"}
    check("missing file degrades to no findings, does not raise",
          wd.review_gate(bad_ctx, TARGET_FN, clean) == [])

    # --- the exclusions are deliberate and must stay excluded --------------
    check("angle stays manual (ROADMAP P4)", "angle" not in wd._REVIEW_GATE_CHECKS)
    check("argn stays manual (ROADMAP P4)", "argn" not in wd._REVIEW_GATE_CHECKS)
    check("linkage is wired", "linkage" in wd._REVIEW_GATE_CHECKS)
    check("ext is wired", "ext" in wd._REVIEW_GATE_CHECKS)
    check("every wired key exists in review_checks.CHECKS",
          all(k in wd._review_checks_module().CHECKS
              for k in wd._REVIEW_GATE_CHECKS))

    # --- and it must be reachable from the attempt loop ---------------------
    src = (REPO / "automation" / "win" / "worker_direct.py").read_text(
        encoding="utf-8", errors="replace")
    check("review_gate is called in the attempt loop",
          "defects += review_gate(ctx, fn, code)" in src)
    # rindex, not index. `with BuildLock(` now appears earlier in the file too,
    # inside replay_pending_journals; anchoring on the FIRST occurrence made
    # this assert something unrelated to the attempt loop.
    check("it runs BEFORE the apply/build critical section",
          src.index("defects += review_gate") < src.rindex("with BuildLock("))

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
