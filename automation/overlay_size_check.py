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
        lines.extend(section_verdict(overlay, bss_start, bad[0][1], bad[0][2]))
    return len(bad), lines


def expected_bss_start(overlay: str) -> int | None:
    """First `.bss`/`bss` subsegment address plus the segment's vram base."""
    p = REPO / "config" / f"splat.us.{overlay}.yaml"
    if not p.exists():
        return None
    vram = None
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(r"^\s*vram:\s*(0x[0-9A-Fa-f]+)", ln)
        if m and vram is None:
            vram = int(m.group(1), 16)
        m = re.match(r"\s*-\s*\[\s*(0x[0-9A-Fa-f]+)\s*,\s*\.?bss\b", ln)
        if m and vram is not None:
            return int(m.group(1), 16) + vram
    return None


def section_verdict(overlay: str, bss_start: int, want: int, got: int) -> list[str]:
    """Which SECTION grew? Requires knowing whether BSS_START itself moved.

    THE BUG THIS FIXES. This used to print, unconditionally, "BSS_START equals
    TEXT_END, so the fault is in TEXT, not in bss". That inference is only
    sound when BSS_START is ITSELF wrong. On 2026-08-02 rno0's BSS_START was
    exactly right and the growth was INSIDE bss -- st_update.h emitted 0x40 of
    unreserved static storage which pushed the trailing bss along. The message
    sent the diagnosis at TEXT for two full build cycles before the linker map
    settled it.

    Now it asks three questions in order:
      1. Is the diverging symbol below BSS_START? Then it is text or data.
      2. Is BSS_START where the splat config says? If NOT, everything before
         bss grew, so the fault is upstream in text or data.
      3. BSS_START correct but a bss symbol moved => something emitted bss that
         no `.bss` segment reserved. That is the actual finding.
    """
    out = [f"  BSS_START = 0x{bss_start:08x} (equals TEXT_END)."]
    if want < bss_start:
        out.append("    The diverging symbol is BELOW BSS_START, so it is in "
                   "TEXT or data. bss is not implicated.")
        return out
    exp = expected_bss_start(overlay)
    if exp is None:
        out.append("    Symbol is in bss, but the expected BSS_START could not "
                   "be read from the splat config, so the section cannot be "
                   "attributed. Compare the .bss objects in the map by hand.")
        return out
    if bss_start != exp:
        out.append(f"    BSS_START is WRONG (expected 0x{exp:08x}, "
                   f"{bss_start - exp:+#x}), so everything before bss grew: the "
                   f"fault is in TEXT or data, not in the .bss segments.")
        return out
    out.append(f"    BSS_START is CORRECT, yet a bss symbol moved {got - want:+#x}. "
               f"So the growth is INSIDE bss: some object is emitting static "
               f"storage that no '.bss, <stem>' segment reserves, and it is "
               f"pushing later bss along.")
    out.append("    Do NOT go diffing functions. Instead list the .bss inputs "
               f"in build/us/{overlay}.map and find the object with no matching "
               f"segment in config/splat.us.{overlay}.yaml.")
    return out


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

    # --- section attribution, the bug that cost two build cycles -----------
    #
    # rno0's real numbers on 2026-08-02: BSS_START 0x801d3eb8 exactly where the
    # splat config puts it, and g_Statues (in bss) shifted +0x40 because
    # st_update.h emitted unreserved static storage. The old code called this
    # TEXT.
    real_bss = 0x801D3EB8
    v = section_verdict("strno0", real_bss, 0x801D4B48, 0x801D4B88)
    joined = " ".join(v)
    ck("bss symbol + correct BSS_START is reported as INSIDE bss",
       "INSIDE bss" in joined, joined[:150])
    ck("and it does NOT blame text", "fault is in TEXT" not in joined,
       joined[:150])
    ck("it says which map section to inspect", ".bss inputs" in joined)

    # A symbol below BSS_START is text/data, whatever bss is doing.
    v2 = " ".join(section_verdict("strno0", real_bss, 0x801B7324, 0x801B7364))
    ck("symbol below BSS_START is attributed to TEXT or data",
       "BELOW BSS_START" in v2, v2[:120])

    # BSS_START itself wrong => the growth is upstream, in text or data.
    v3 = " ".join(section_verdict("strno0", real_bss + 0x40,
                                  0x801D4B48, 0x801D4B88))
    ck("shifted BSS_START is attributed upstream to TEXT/data",
       "BSS_START is WRONG" in v3 and "TEXT or data" in v3, v3[:150])

    ck("expected BSS_START is read from the splat config",
       expected_bss_start("strno0") == real_bss,
       hex(expected_bss_start("strno0") or 0))
    ck("unknown overlay degrades without raising",
       expected_bss_start("stnosuch") is None)

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
