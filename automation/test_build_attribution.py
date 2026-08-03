#!/usr/bin/env python3
"""Does the worker blame the right record when a build fails?

WHY THIS EXISTS
    The build is ninja-parallel over every overlay. If a concurrent worker is
    mid-apply, or an artifact is stale, `make build` can fail for reasons that
    have nothing to do with the candidate just written. The worker used to
    record that as BUILD FAILED and, after four attempts, escalate.

    An escalated record is retired. It gets a note full of some other overlay's
    linker output, and nobody looks at it again on its merits. Audit 2026-08-02
    found NINE records in exactly that state: functions in bo0, bo6 and rno0
    escalated while quoting link failures in stnp3, stnz0 and weapon0.

    build_error_is_ours() is the guard. The asymmetry matters and is asserted
    below: saying "ours" when it is not merely preserves the old behaviour,
    while saying "not ours" when it IS ours would hide a real defect. So every
    ambiguous case must resolve to True.

Run: python3 automation/test_build_attribution.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAILS: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    print(("  ok   " if cond else "  FAIL ") + label
          + ("" if cond else "   " + detail))
    if not cond:
        FAILS.append(label)


# Verbatim shapes taken from the nine real escalations.
LINK_STNP3 = ("mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map "
              "build/us/stnp3.map -T build/us/stnp3.ld -o build/us/stnp3.elf\n"
              "FAILED: build/us/stnp3.elf\n")
LINK_STNZ0 = ("mipsel-linux-gnu-ld -Map build/us/stnz0.map -o "
              "build/us/stnz0.elf\nFAILED: build/us/stnz0.elf\n")
LINK_WEAPON = ("[318/322] psx strip build/us/weapon/w0_056.elf\n"
               "FAILED: build/us/weapon/w0_057.elf\n")


def main() -> int:
    spec = importlib.util.spec_from_file_location(
        "worker_direct", REPO / "automation" / "win" / "worker_direct.py")
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)
    wd.WIN_REPO = str(REPO)
    ours = wd.build_error_is_ours

    bo6 = {"function": "BO6_CheckHighJumpInput", "overlay": "BOSS/BO6",
           "src_rel": "src/boss/bo6/richter.c"}
    bo0 = {"function": "func_us_801BA724", "overlay": "BOSS/BO0",
           "src_rel": "src/boss/bo0/2D26C.c"}
    rno0 = {"function": "func_801C7884", "overlay": "ST/RNO0",
            "src_rel": "src/st/rno0/e_subweapon_container.c"}

    print("\nthe nine real false escalations are all rejected")
    check(not ours(LINK_STNP3, bo6), "bo6 vs an stnp3 link failure")
    check(not ours(LINK_STNP3, rno0), "rno0 vs an stnp3 link failure")
    check(not ours(LINK_STNZ0, bo6), "bo6 vs an stnz0 link failure")
    check(not ours(LINK_STNZ0, bo0), "bo0 vs an stnz0 link failure")
    check(not ours(LINK_WEAPON, bo6), "bo6 vs a weapon0 link failure")
    check(not ours(LINK_WEAPON, rno0), "rno0 vs a weapon0 link failure")

    print("\nreal failures in our own code are still ours")
    check(ours("src/boss/bo0/2D26C.c:133: structure has no member named "
               "`unk32'\n", bo0), "a diagnostic in our own source file")
    check(ours("mipsel-linux-gnu-ld: undefined reference to "
               "`func_us_801BA724'\n", bo0), "a link error naming our function")
    check(ours("FAILED: build/us/bobo0.elf\n", bo0),
          "a link failure in our own overlay's artifact")
    check(ours("[12/40] psx cc src/st/rno0/e_subweapon_container.c\n"
               "src/st/rno0/e_subweapon_container.c:88: parse error\n", rno0),
          "a diagnostic naming our source path")

    print("\nshared code is ours, because we may have broken it")
    check(ours("src/st/st_common.h:120: `foo' undeclared\n", rno0),
          "a diagnostic in a shared src/st header")
    check(ours("include/game.h:44: parse error\n", bo6),
          "a diagnostic in include/")
    check(ours("src/main/psxsdk/libgpu/x.c:9: parse error\n", bo6),
          "a diagnostic in src/main")

    print("\nambiguity resolves to ours, never away from it")
    check(ours("", bo6), "empty output is ours (cannot prove otherwise)")
    check(ours("make: *** [Makefile:127: build_us] Error 1\n", bo6),
          "a bare make summary is ours")
    check(ours("ninja: build stopped: subcommand failed.\n", bo6),
          "a bare ninja summary is ours")

    print("\ncase-insensitive on the overlay leaf")
    check(ours("FAILED: build/us/BOBO6.ELF\n", bo6), "uppercase artifact name")
    check(ours("[3/9] psx cc src/boss/BO6/richter.c\n", bo6),
          "uppercase overlay directory")

    print("\nthe guard is actually wired into the failure path")
    src = (REPO / "automation" / "win" / "worker_direct.py").read_text()
    check("build_error_is_ours(out, rec)" in src,
          "build_error_is_ours is called on the failure path")
    check("BUILD DIRTY" in src,
          "a dirty build reports BUILD DIRTY, not BUILD FAILED")
    i_dirty = src.find("BUILD DIRTY")
    i_failed = src.find('return False, "BUILD FAILED:')
    check(0 < i_dirty < i_failed,
          "the dirty check runs BEFORE the plain BUILD FAILED return")
    check('"BUILD FAILED" not in detail' in src,
          "escalation routing still keys on the BUILD FAILED string, so a "
          "BUILD DIRTY result cannot be routed as a compile defect")

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
