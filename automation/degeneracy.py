#!/usr/bin/env python3
"""Has the model stopped decompiling and started looping?

WHY THIS IS ITS OWN MODULE
    Both the live worker and the offline scorer need these checks, and they
    must agree. worker_direct cannot import quality_ab (quality_ab imports
    worker_direct, so that would be a cycle), which is exactly the situation
    that produces two drifting copies of a detector. This module imports
    nothing local, so both can depend on it.

THE THREE SHAPES, ALL OBSERVED IN THE 2026-08-09 BATTERY
    Together they wasted 16 of 54 generations, every one burning its FULL
    budget, because the only degeneration check in the worker watched the
    reasoning stream and these all occur in the content stream. At
    REASONING_EFFORT=none there is no reasoning at all, so nothing was
    watching.

    All three score PERFECTLY on the defect metrics -- zero invented fields,
    zero unkNN, zero ILLEGAL -- because they contain no field accesses to get
    wrong. Two of them additionally beat the fidelity scorer.
"""
from __future__ import annotations

import re

# The MIPS register file, which is what a model transcribes when it gives up
# on decompiling and starts describing the assembly instead.
RX_REG_DECL = re.compile(
    r"^\s*(?:[A-Za-z_]\w*\s+)+"
    r"(?:temp_|tmp_|var_)?(?:v[01]|a[0-3]|t[0-9]|s[0-8]|at|gp|sp|fp|ra|hi|lo)"
    r"(?:_\d+)?\s*;\s*$", re.M)

# A line of the disassembly listing: /* fileoff vaddr word */  insn ...
# Echoing these back is not decompilation, and it GAMES the fidelity scorer:
# output containing the assembly trivially "reproduces" every constant and
# symbol in it. ling-3.0-flash-free scored 1.00 constant recall this way.
RX_ASM_ECHO = re.compile(r"^\s*/\*\s*[0-9A-Fa-f]{4,6}\s+8[0-9A-Fa-f]{7}\s+"
                         r"[0-9A-Fa-f]{8}\s*\*/", re.M)

RX_DECL_SEQ = re.compile(
    r"^\s*(?:[A-Za-z_]\w*\s+)+([A-Za-z_]\w*?)(\d+)\s*;\s*$", re.M)


def degenerate(code: str) -> dict:
    """Is the model stuck in a loop instead of writing a function?

    OBSERVED LIVE, 2026-08-09 battery. Three separate cells spent their entire
    300s budget emitting nothing but an ascending list of declarations:

        s32 temp_v0_280;
        s32 temp_v0_281;
        s32 temp_v0_282;      ... and on until the timeout fired

    Every other metric rates that output WELL: zero invented fields, zero
    unkNN, zero ILLEGAL, no raw offsets. Only `chars` is unusual, and a large
    function is legitimately large, so size alone cannot separate the two. A
    battery scored without this check would have reported those cells as clean
    and ranked a looping model above an honest one.

    Detected structurally: a run of declarations whose names differ only by an
    ascending integer suffix. Real decompiled C reuses temporaries; it does not
    number them into the hundreds.
    """
    code = code or ""
    runs: dict[str, list[int]] = {}
    for stem, num in RX_DECL_SEQ.findall(code):
        runs.setdefault(stem, []).append(int(num))
    longest, worst = 0, ""
    for stem, nums in runs.items():
        nums.sort()
        cur = best = 1
        for a, b in zip(nums, nums[1:]):
            cur = cur + 1 if b == a + 1 else 1
            best = max(best, cur)
        if best > longest:
            longest, worst = best, stem
    # SECOND SHAPE, found on big-pickle/func_us_801CF64C after the ascending
    # -integer check was already in place: instead of numbering temporaries the
    # model transcribes the register file, `temp_v0; temp_v1; temp_s0; ...
    # temp_v0_2;`. The suffixes are register names, not an ascending run, so
    # the first check did not see it. Its ctrl_ratio was 0.28, i.e. it had
    # dropped nearly all the control flow, while scoring zero on every defect
    # metric.
    regs = len(RX_REG_DECL.findall(code))
    echo = len(RX_ASM_ECHO.findall(code))

    lines = [l.strip() for l in code.splitlines() if l.strip()]
    dup = (1.0 - len(set(lines)) / len(lines)) if lines else 0.0
    return {"decl_run": longest, "decl_stem": worst if longest >= 20 else "",
            "reg_decls": regs, "asm_echo": echo,
            "dup_line_frac": round(dup, 2),
            # 20 is far above anything hand-written and far below the hundreds
            # seen when a model is actually looping. Real decompiled C does
            # name a few temporaries after registers, so the register-dump
            # threshold is set well clear of legitimate use.
            # A couple of quoted asm lines in a comment is legitimate
            # annotation; ten is a transcript.
            "degenerate": bool(longest >= 20 or regs >= 15 or echo >= 10)}




__all__ = ["degenerate", "RX_DECL_SEQ", "RX_REG_DECL", "RX_ASM_ECHO"]
