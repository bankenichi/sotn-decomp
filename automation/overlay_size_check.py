#!/usr/bin/env python3
"""Which function is the wrong SIZE? Answer it in one second, not one diff.

WHY THIS EXISTS
    Shimming rno0's clock room produced a checksum failure with six candidate
    functions and no indication which was at fault. Reading asm_diff output for
    each is ~15k tokens a time and mostly shows matching instructions.

    There is a far cheaper signal. Every function's intended address is already
    written down in config/symbols.us.<overlay>.txt, and the linker records
    where each one actually landed in build/us/<overlay>.map. Compare the two:

      - functions BEFORE the bug are all at their expected addresses
      - the first function to diverge is the one AFTER the oversized function
      - the delta is exactly how many bytes wrong that function is

    In the real case every clock-room function sat at its exact expected
    address and only the trailing stub was 0x10 high, which isolated the fault
    to EntityStoneDoor and, at 4 instructions, pointed straight at its one
    remaining #ifdef branch. That took seconds instead of several diffs.

A SECOND SIGNAL, FREE FROM THE SAME DATA
    `<ovl>_BSS_START` in the map equals `<ovl>_TEXT_END`. If BSS_START is off
    but every bss symbol is correct relative to its own segment, the fault is
    in TEXT, not bss. That distinction cost real time: a shifted bss block
    looked like a bss/segmentation bug and was actually a 0x10 text overrun.

STRICTLY READ-ONLY. Reads the map and the symbol config; never builds or edits.

Usage:
    python3 automation/overlay_size_check.py                # every us overlay
    python3 automation/overlay_size_check.py --overlay strno0
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# `NAME = 0xADDR;` with an optional trailing comment.
_SYM = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*(0x[0-9A-Fa-f]+)\s*;")
# A map line that assigns an address to a symbol: leading spaces, addr, name.
_MAP_SYM = re.compile(r"^\s+(0x[0-9a-f]+)\s+([A-Za-z_]\w*)\s*$")
_MAP_MARK = re.compile(r"^\s+(0x[0-9a-f]+)\s+(\w+_(?:BSS_START|TEXT_END))\s*=")


def read_expected(overlay: str) -> dict[str, int]:
    p = REPO / "config" / f"symbols.us.{overlay}.txt"
    if not p.exists():
        return {}
    out = {}
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _SYM.match(line)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out


def read_actual(overlay: str) -> tuple[dict[str, int], dict[str, int]]:
    p = REPO / "build" / "us" / f"{overlay}.map"
    if not p.exists():
        return {}, {}
    syms: dict[str, int] = {}
    marks: dict[str, int] = {}
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _MAP_MARK.match(line)
        if m:
            marks[m.group(2)] = int(m.group(1), 16)
            continue
        m = _MAP_SYM.match(line)
        if m:
            # First definition wins; later lines repeat symbols in other roles.
            syms.setdefault(m.group(2), int(m.group(1), 16))
    return syms, marks


def check(overlay: str) -> tuple[int, list[str]]:
    expected = read_expected(overlay)
    actual, marks = read_actual(overlay)
    if not expected:
        return 0, [f"{overlay}: no symbols.us.{overlay}.txt, skipped"]
    if not actual:
        return 0, [f"{overlay}: no build/us/{overlay}.map, build it first"]

    common = [(n, a) for n, a in expected.items() if n in actual]
    if not common:
        return 0, [f"{overlay}: no overlap between symbols and map, skipped"]

    # Sort by INTENDED address so "first divergence" means first in the binary.
    common.sort(key=lambda t: t[1])
    bad = [(n, want, actual[n]) for n, want in common if actual[n] != want]

    lines = []
    if not bad:
        lines.append(f"{overlay}: {len(common)} symbols, all at their expected "
                     f"addresses")
    else:
        n, want, got = bad[0]
        delta = got - want
        lines.append(f"{overlay}: {len(bad)} of {len(common)} symbols shifted")
        lines.append(f"  FIRST DIVERGENCE  {n}")
        lines.append(f"    expected 0x{want:08x}, got 0x{got:08x} "
                     f"(delta {delta:+#x} = {delta // 4:+d} instructions)")
        # The culprit is whatever function PRECEDES the first divergence: it is
        # the one whose size is wrong.
        idx = [i for i, (nm, _) in enumerate(common) if nm == n]
        if idx and idx[0] > 0:
            prev = common[idx[0] - 1][0]
            lines.append(f"    => {prev} is {delta:+#x} bytes wrong. Diff THAT "
                         f"function, not the whole overlay.")
        else:
            lines.append("    => the divergence starts at the first symbol; the "
                         "fault is before it, in data or the segment layout.")

    # Text-vs-bss discrimination.
    bss_start = next((v for k, v in marks.items() if k.endswith("_BSS_START")), None)
    if bss_start is not None and bad:
        lines.append(f"  BSS_START = 0x{bss_start:08x}. BSS_START equals "
                     f"TEXT_END, so if it is off by the same delta the fault is "
                     f"in TEXT, not in bss or the splat .bss segments.")
    return len(bad), lines


def _locate(common: list[tuple[str, int]], actual: dict[str, int]):
    """(first diverging symbol, delta, culprit) or None. Pure, so it is testable
    without a build."""
    for i, (name, want) in enumerate(sorted(common, key=lambda t: t[1])):
        got = actual.get(name)
        if got is not None and got != want:
            ordered = sorted(common, key=lambda t: t[1])
            culprit = ordered[i - 1][0] if i > 0 else None
            return name, got - want, culprit
    return None


def self_test() -> int:
    """Reproduce the real case: everything correct until one oversized function.

    Passing on a green tree only proves the checker does not false-positive.
    This proves it DETECTS, which is the half that matters.
    """
    fails = []

    def ck(name, cond, detail=""):
        print(("  ok   " if cond else "  FAIL ") + name
              + ("" if cond else "   " + detail))
        if not cond:
            fails.append(name)

    # Modelled on the actual clock-room failure: A..D fine, E is 0x10 long, so
    # F (and everything after) shifts by +0x10.
    common = [("A", 0x1000), ("B", 0x1100), ("C", 0x1200),
              ("D", 0x1300), ("E", 0x1400), ("F", 0x1500)]
    actual = {"A": 0x1000, "B": 0x1100, "C": 0x1200,
              "D": 0x1300, "E": 0x1400, "F": 0x1510}
    r = _locate(common, actual)
    ck("detects a shifted symbol", r is not None)
    if r:
        first, delta, culprit = r
        ck("names the FIRST divergence", first == "F", str(first))
        ck("reports the byte delta", delta == 0x10, hex(delta))
        ck("blames the PRECEDING function", culprit == "E", str(culprit))

    ck("clean input reports nothing",
       _locate(common, {n: a for n, a in common}) is None)

    # A divergence at the very first symbol has no preceding function to blame.
    r2 = _locate(common, {**{n: a for n, a in common}, "A": 0x1008})
    ck("first-symbol divergence yields no culprit",
       r2 is not None and r2[2] is None, str(r2))

    # Symbols absent from the map must not be treated as divergences.
    ck("missing map symbols are ignored",
       _locate([("Z", 0x9000)], {}) is None)

    print()
    print(f"{len(fails)} failure(s)" if fails else "all checks pass.")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--overlay", default="",
                    help="e.g. strno0; default checks every overlay with a map")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    if a.overlay:
        overlays = [a.overlay]
    else:
        overlays = sorted(
            p.stem for p in (REPO / "build" / "us").glob("*.map")
            if (REPO / "config" / f"symbols.us.{p.stem}.txt").exists())

    total = 0
    for ov in overlays:
        n, lines = check(ov)
        total += n
        for l in lines:
            print(l)
    print()
    print(f"{total} shifted symbol(s) across {len(overlays)} overlay(s)")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
