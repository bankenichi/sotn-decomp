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

REPO = Path(__file__).resolve().parent.parent

# A real file with a real INCLUDE_ASM stub, not a fixture. The substitution is
# the thing under test, so it has to run against text that actually ships.
TARGET_SRC = "src/st/rno0/e_gorgon.c"
TARGET_ASM = "st/rno0/nonmatchings/e_gorgon"
TARGET_FN = "func_801CD78C_801CEB40"


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
    # func_801CE04C is stubbed in unk_4A320.c and `jal`-ed from assembly owned
    # by e_blade.c, e_gurkha.c and e_hammer.c. A source grep sees no caller, so
    # `static` looks obviously right and breaks the link. This is the same
    # shape as the StepTowards incident that motivated the check.
    #
    # The first version of this test used StepTowards directly and failed,
    # correctly: StepTowards is a real function in e_gorgon.c, not an
    # INCLUDE_ASM stub, so virtual_apply refused to substitute and the gate
    # returned nothing. The gate was right and the test was wrong. Keeping the
    # note because "the check did not fire" is exactly the symptom a broken
    # substitution would also produce, and the two must not be confused.
    x_ctx = {"src_rel": "src/st/rno0/unk_4A320.c",
             "asm_rel": "st/rno0/nonmatchings/unk_4A320"}
    x_fn = "func_801CE04C"
    static_code = f"static void {x_fn}(Entity* self) {{\n    self->step++;\n}}\n"
    found = wd.review_gate(x_ctx, x_fn, static_code)
    check("static-across-TU is rejected", any("linkage" in f for f in found),
          repr(found[:2]))
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
    # The file can carry pre-existing findings in code this worker did not
    # write. Failing on those would make the record unmatchable forever.
    noisy = wd.review_gate(x_ctx, x_fn,
                           f"void {x_fn}(Entity* self) {{ self->step++; }}\n"
                           f"static void SomeOtherHelper(void) {{}}\n")
    check("a finding about another function is not attributed here",
          all("SomeOtherHelper" not in f for f in noisy), repr(noisy[:2]))

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
    check("it runs BEFORE the build lock",
          src.index("defects += review_gate") < src.index("with BuildLock("))

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
