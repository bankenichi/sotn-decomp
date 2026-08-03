#!/usr/bin/env python3
"""Can the worker find every INCLUDE_ASM stub, including the wrapped ones?

WHY THIS EXISTS
    find_source() indexes the tree by scanning for INCLUDE_ASM. It used to scan
    LINE BY LINE. clang-format wraps a long INCLUDE_ASM across two lines:

        INCLUDE_ASM(
            "boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnStopwatchCircle);

    RX_INC's \\s* spans a newline happily -- but only if it is handed the
    newline. Per-line matching meant neither half matched, find_source returned
    None, and the worker escalated the record as "INCLUDE_ASM stub not found".

    That is a PERMANENT failure, not a flaky one: the function's name length
    never changes, so every future attempt fails identically. Six bo6 stubs were
    unmatchable this way, and the two that had been picked up were sitting in
    the escalated pool.

    Worth recording how the first fix went wrong. Both records were requeued on
    2026-08-02 after the regex was tested against whole-file text and appeared to
    match. That test exercised apply_code's pattern, which reads the whole file,
    NOT this loop, which did not. The fleet re-escalated both within the hour.
    Testing the wrong code path looks exactly like testing the right one.

Run: python3 automation/test_stub_locate.py
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAILS: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    print(("  ok   " if cond else "  FAIL ") + label
          + ("" if cond else "   " + detail))
    if not cond:
        FAILS.append(label)


def main() -> int:
    spec = importlib.util.spec_from_file_location(
        "worker_direct", REPO / "automation" / "win" / "worker_direct.py")
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)
    wd.WIN_REPO = str(REPO)

    print("\nthe known wrapped stubs resolve")
    # Real, currently-wrapped stubs in the tree. If clang-format ever unwraps
    # them this test still passes; it asserts they are FOUND, not that they wrap.
    for fn in ("BO6_RicEntitySubwpnStopwatchCircle",
               "BO6_RicEntityCrashReboundStoneExplosion",
               "BO6_RicEntitySubwpnHolyWaterFlame"):
        got = wd.find_source(fn, "BOSS/BO6")
        check(got is not None, f"find_source resolves {fn}", repr(got))
        if got:
            check(got[0].endswith(".c") and got[1] > 0,
                  f"  and reports a real file and line for {fn}", repr(got))

    print("\nordinary single-line stubs still resolve")
    for fn, ov in (("EntityBreakable", "ST/RNO0"),
                   ("BO6_EntityStopWatch", "BOSS/BO6")):
        got = wd.find_source(fn, ov)
        check(got is not None, f"find_source resolves {fn}", repr(got))

    print("\nthe overlay still decides between same-named stubs")
    # EntityBreakable is stubbed in more than one overlay; the record's overlay
    # must pick, or the worker edits the wrong file entirely.
    a = wd.find_source("EntityBreakable", "ST/RNO0")
    b = wd.find_source("EntityBreakable", "ST/RCHI")
    check(a and b and a[0] != b[0],
          "the same symbol in two overlays resolves to two different files",
          f"{a} vs {b}")
    check(a and "/rno0/" in a[0], "ST/RNO0 picks the rno0 file", repr(a))
    check(b and "/rchi/" in b[0], "ST/RCHI picks the rchi file", repr(b))

    print("\nno stub in the tree is invisible to the index")
    # The property that actually matters, asserted against the whole tree rather
    # than a fixture: whole-file scanning and the worker's index must agree.
    rx = re.compile(r'INCLUDE_ASM\(\s*"([^"]+)"\s*,\s*([A-Za-z0-9_]+)\s*\)')
    missing = []
    for c in sorted((REPO / "src").rglob("*.c")):
        low = str(c).lower()
        if "_psp" in low or "saturn" in low or "/psp/" in low:
            continue
        text = c.read_text(errors="ignore")
        for m in rx.finditer(text):
            if wd.find_source(m.group(2)) is None:
                missing.append((c.name, m.group(2)))
    check(not missing,
          f"every INCLUDE_ASM in src/ is findable ({len(missing)} invisible)",
          repr(missing[:5]))

    print("\nthe line-by-line scan that caused this is gone")
    src = (REPO / "automation" / "win" / "worker_direct.py").read_text()
    i = src.find("def find_source(")
    body = src[i:i + 3000]
    check("for i, line in enumerate(f, 1)" not in body,
          "find_source no longer iterates the file line by line")
    check("RX_INC.finditer(text)" in body,
          "find_source scans whole-file text")

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED:")
        for f in FAILS:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
