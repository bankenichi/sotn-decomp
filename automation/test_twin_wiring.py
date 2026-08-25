#!/usr/bin/env python3
"""Does the worker actually get the twin, and stay quiet when it shouldn't?

WHY THIS EXISTS
    `twin_for()` feeds a section straight into the model prompt. Two things can
    go wrong and neither shows up as a crash:

      - it stays silent when a twin exists, and the worker quietly pays full
        token cost rediscovering that BO6_RicStepStand is RicStepStand;
      - it speaks when the evidence is ambiguous, and the worker is handed
        another overlay's function with the same confidence as the right one.

    The second is the dangerous one, and it nearly shipped. Symbols are not
    unique across overlays: EntityBreakable is stubbed in BOTH st/rchi (156
    instructions) and st/rno0 (92). An earlier version of twins.us.json was
    keyed on the bare symbol, silently collapsed the pair, and would have
    handed one overlay the other's record.

    Two failures found by running this, worth recording because both looked
    fine on inspection:
      1. keying the record file on the bare symbol (above), caught by asserting
         both colliding keys resolve independently;
      2. an assertion of mine that was simply WRONG -- I expected the two
         EntityBreakable sections to differ textually. They legitimately do
         not: the name-twin lookup is by name, so both stubs get the same
         eight candidates. The real property to assert is that the two records
         resolve independently and carry their own overlay and size, which is
         what this file checks now.

Run:  python3 automation/test_twin_wiring.py
Exit: 0 all pass, 1 otherwise.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_worker():
    path = REPO / "automation" / "win" / "worker_direct.py"
    spec = importlib.util.spec_from_file_location("worker_direct", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    wd = load_worker()
    wd.WIN_REPO = str(REPO)
    wd._TWINS = None

    failures = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        print(("  ok   " if cond else "  FAIL ") + name
              + ("" if cond else "   " + detail))
        if not cond:
            failures.append(name)

    twins = wd._load_twins()
    check("twins.us.json loads", len(twins) > 0, f"got {len(twins)}")

    # --- the record file must still be free of key collisions ---------------
    doc = json.loads((REPO / "automation" / "twins.us.json").read_text())
    keys = list(doc["twins"])
    check("record keys are unique", len(keys) == len(set(keys)))
    colliding = [k for k in keys if k.rsplit("/", 1)[-1] == "EntityBreakable"]
    expected_collisions = set()
    for asm in (REPO / "asm" / "us").rglob("EntityBreakable.s"):
        parts = asm.relative_to(REPO / "asm" / "us").parts
        if "nonmatchings" not in parts:
            continue
        expected_collisions.add(
            "/".join(parts[:parts.index("nonmatchings")]).lower()
            + "/EntityBreakable")
    check("every colliding symbol keeps its overlay-qualified record",
          set(colliding) == expected_collisions,
          f"expected={sorted(expected_collisions)} got={sorted(colliding)}")
    for key in sorted(expected_collisions):
        overlay, function = key.rsplit("/", 1)
        section = wd.twin_for(function, overlay.upper())
        instructions = doc["twins"][key].get("instructions")
        check(f"queue-style uppercase collision resolves {key}",
              bool(section) and f"{instructions} instructions" in section,
              repr(section[:160]))

    # --- the happy path -----------------------------------------------------
    s = wd.twin_for("BO6_RicStepStand", "boss/bo6")
    check("name twin surfaces", "src/ric/pl_steps.c:RicStepStand" in s,
          repr(s[:160]))
    check("orders a diff before copying", "DIFF IT AGAINST THE ASSEMBLY" in s)
    check("warns that globals differ by overlay", "BY ADDRESS" in s)
    check("weak token hits suppressed when a name twin exists",
          "similar symbols" not in s)
    check("stub size is stated", "instructions)" in s, repr(s[:120]))

    # --- the collision, which is the whole reason this file exists ----------
    rchi = wd.twin_for("EntityBreakable", "st/rchi")
    rno0 = wd.twin_for("EntityBreakable", "st/rno0")
    check("collision: rchi resolves", rchi != "")
    check("collision: rno0 resolves", rno0 != "")
    # They share a candidate list by design; what must differ is the size,
    # because these are genuinely different functions.
    check("collision: rchi reports its own size", "156 instructions" in rchi,
          repr(rchi[:120]))
    check("collision: rno0 reports its own size", "92 instructions" in rno0,
          repr(rno0[:120]))

    # --- silence where silence is correct -----------------------------------
    check("unknown function is silent",
          wd.twin_for("NoSuchFunctionAnywhere", "boss/bo6") == "")
    check("empty function is silent", wd.twin_for("", "boss/bo6") == "")
    check("unique symbol resolves even with a wrong overlay",
          wd.twin_for("BO6_RicStepStand", "nonsense/overlay") != "")
    check("COLLIDING symbol with a wrong overlay stays silent",
          wd.twin_for("EntityBreakable", "nonsense/overlay") == "")

    # --- inverted-castle hint -----------------------------------------------
    # Fires only when the stub is a second-castle overlay AND its twin is not.
    check("overlay parsing: src path -> overlay",
          wd._overlay_of("src/st/no0/clock_room.c") == "no0",
          wd._overlay_of("src/st/no0/clock_room.c"))
    check("overlay parsing: non-overlay path is empty",
          wd._overlay_of("src/dra/menu.c") == "")
    check("rno0 is inverted", wd._is_inverted("st/rno0"))
    check("no0 is not inverted", not wd._is_inverted("st/no0"))
    check("bo6 is not inverted", not wd._is_inverted("boss/bo6"))
    check("rbo3 is inverted", wd._is_inverted("boss/rbo3"))

    rno0_stub = wd.twin_for("EntityBreakable", "st/rno0")
    check("inverted hint fires for rno0 with a non-inverted twin",
          "INVERTED CASTLE" in rno0_stub)
    check("inverted hint names the 0xE4 castle-flag delta",
          "0xE4" in rno0_stub)
    check("inverted hint points at the shared header, not a copy",
          "SHARED header" in rno0_stub)
    check("no inverted hint for a first-castle overlay",
          "INVERTED CASTLE" not in wd.twin_for("BO6_RicStepStand", "boss/bo6"))

    # --- the shim advice is UNCONDITIONAL, and that is the point ------------
    #
    # This used to read: check("shared-impl twin names the shim rule",
    # "#include shim" in bat). That was vacuous. The phrase is part of a
    # trailer appended to EVERY twin section, so the assertion passed for any
    # non-empty output and tested nothing about shared implementations.
    # twin_for contains no shared-impl routing at all. Audit 2026-08-02.
    #
    # Asserting the truth instead: the advice appears for every twin, shared
    # implementation or not, so its presence carries no information about the
    # stem. If per-stem routing is ever added, the second assertion here fails
    # and this comment stops being true.
    # NAMING A SPECIFIC STUB DATES THE TEST. This block used to call
    # twin_for("EntityBat", "st/rchi"); EntityBat was later decompiled, so it
    # dropped out of twins.us.json, twin_for returned "" and the assertion
    # failed for a reason that had nothing to do with twin wiring. Pick the
    # examples out of the current record instead, so the test tracks the tree.
    same_name = other_name = ""
    for key in wd._load_twins():
        # keys are "<overlay>/<symbol>", e.g. "boss/bo0/func_us_801B1DDC"
        ov, _, sym = key.rpartition("/")
        sec = wd.twin_for(sym, ov)
        if not sec:
            continue
        if "same name:" in sec:
            same_name = same_name or sec
        else:
            other_name = other_name or sec
        if same_name and other_name:
            break
    check("the record still has a same-name (shared-impl) twin to test with",
          bool(same_name))
    check("shim advice is present on a shared-impl twin",
          "#include shim" in same_name, repr(same_name[:120]))
    check("shim advice is present on a NON-shared-impl twin too, so it is a "
          "constant trailer and not evidence of routing",
          "#include shim" in other_name, repr(other_name[:120]))

    # --- a missing or corrupt record file must never break a run ------------
    wd._TWINS = None
    wd.WIN_REPO = "/nonexistent-path"
    try:
        check("missing twins.us.json degrades to silence",
              wd.twin_for("BO6_RicStepStand", "boss/bo6") == "")
    finally:
        wd.WIN_REPO = str(REPO)
        wd._TWINS = None

    # --- the section must actually reach the prompt --------------------------
    rec = {"function": "BO6_RicStepStand", "overlay": "boss/bo6",
           "build": "us"}
    ctx = {"asm": "  lui $v0, %hi(g_Ric)\n", "draft": "void f(void) {}",
           "src_rel": "src/boss/bo6/richter.c", "decls": []}
    prompt = wd.build_prompt(rec, ctx)
    check("build_prompt includes the twin section",
          "A TWIN OF THIS FUNCTION ALREADY EXISTS" in prompt)
    check("twin appears BEFORE the assembly",
          prompt.index("A TWIN OF THIS FUNCTION")
          < prompt.index("=== MIPS ASSEMBLY ==="))

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
