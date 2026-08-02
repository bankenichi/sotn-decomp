#!/usr/bin/env python3
"""Does the worker tell "never compiled" apart from "compiled, bytes differ"?

WHY THIS EXISTS
    `make build` runs the `check` target itself, so a perfectly good compile
    whose bytes differ still makes make exit non-zero. The worker used to treat
    any non-zero exit as BUILD FAILED, which collapsed two outcomes with
    completely different owners:

        never compiled          -> escalated: needs a better model or a human
        compiled, bytes differ  -> near: needs the PERMUTER, costs no tokens

    The damage was not theoretical. Four `near` records had to be retriaged BY
    HAND on 2026-08-01, every one carrying a note like "misrouted... the tree
    BUILT and only the checksum differed". That fixed the records and left the
    cause in place, so it kept happening: on 2026-08-02 func_us_8019AA04 built
    cleanly (every overlay printed OK, the sole failure line was
    `check: checksum check failed`) and was still recorded BUILD FAILED.

    It also silently disabled the permuter seed, which only saves a candidate
    when the build is judged to have compiled.

    The classifier is deliberately CONSERVATIVE: any compiler diagnostic, ninja
    FAILED block or link error counts as a real build failure, and an
    unexplained non-zero exit does too. Only a non-zero exit that explicitly
    says the checksum failed, with no diagnostic anywhere, is reclassified.
    A broken compile must never be mistaken for a permuter candidate.

Run:  python3 automation/test_build_classifier.py
Exit: 0 all pass, 1 otherwise.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# The actual worker-oc-2 tail from 2026-08-02 that was misclassified. Kept
# verbatim: a synthetic approximation would not have caught this.
REAL_CHECKSUM_ONLY = """  ✅ F_RBO0   ✅ RBO3     ✅ F_RBO3   ✅ RBO5     ✅ F_RBO5
  ✅ TT_000   ✅ TT_001   ✅ TT_002   ✅ TT_003   ✅ TT_004
  ✅ WEAPON0
check: checksum check failed"""

CASES = [
    # (name, rc, output, expected "this was a real build failure")
    ("real checksum-only failure is NOT a build failure",
     2, REAL_CHECKSUM_ONLY, False),
    ("gcc 2.7 diagnostic, which carries no 'error:' keyword",
     2, "src/boss/bo0/2D26C.c:133: structure has no member named `unk32'", True),
    ("ninja FAILED block",
     1, "FAILED: build/us/foo.o\ncc1-psx-26 ...", True),
    ("linker undefined reference",
     1, "undefined reference to `polarPlacePartsList'", True),
    ("diagnostic in a header",
     2, "include/game.h:44: parse error", True),
    ("explicit error keyword",
     1, "ld: error: bad section", True),
    # The dangerous direction: a compile that failed AND reached check must
    # stay a build failure, or broken C gets handed to the permuter.
    ("a diagnostic outranks the checksum line",
     2, "src/x.c:9: parse error\ncheck: checksum check failed", True),
    # A WARNING is not a build failure. GCC 2.7 writes warnings in the exact
    # same `file.c:LINE:` shape as errors, so the diagnostic regex matched them
    # and classified a clean compile as BUILD FAILED. That sent a permuter
    # candidate to `escalated` AND suppressed its saved seed. Found by audit
    # 2026-08-02; this suite had no case containing the word "warning".
    ("a warning alongside a checksum failure is NOT a build failure",
     2, "src/st/rno0/e_misc.c:88: warning: unused variable `i'\n"
        "check: checksum check failed", False),
    ("a warning on its own with a non-zero rc is still not a diagnostic",
     2, "src/st/rno0/e_misc.c:88: warning: unused variable `i'\n"
        "checksum check failed", False),
    # ...but a real error in the same build still wins.
    ("a real error outranks a warning in the same output",
     2, "src/x.c:12: warning: unused variable `i'\n"
        "src/x.c:20: parse error before `foo'\n"
        "check: checksum check failed", True),
    ("unexplained non-zero stays a build failure",
     1, "make: *** [all] Error 1", True),
    ("rc=0 is never a failure", 0, "", False),
    ("rc=0 wins even if the text mentions a checksum",
     0, "checksum check failed", False),
]


def main() -> int:
    spec = importlib.util.spec_from_file_location(
        "worker_direct", REPO / "automation" / "win" / "worker_direct.py")
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)

    failures = []
    for name, rc, out, want in CASES:
        got = wd.build_failed_to_compile(rc, out)
        ok = got == want
        print(("  ok   " if ok else "  FAIL ") + name
              + ("" if ok else f"   got={got} want={want}"))
        if not ok:
            failures.append(name)

    # The routing downstream keys off the literal substring "BUILD FAILED", so
    # assert the contract rather than trusting the two to stay in sync.
    src = (REPO / "automation" / "win" / "worker_direct.py").read_text(
        encoding="utf-8", errors="replace")
    contract = [
        ('checksum path avoids the BUILD FAILED substring',
         'return False, ("BUILT, CHECKSUM MISMATCH' in src),
        ('near routing still tests that substring',
         '"BUILD FAILED" not in detail' in src),
        ('permuter seed is saved on the compiled path',
         'seed_path = save_candidate' in src),
    ]
    for name, cond in contract:
        print(("  ok   " if cond else "  FAIL ") + name)
        if not cond:
            failures.append(name)

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
