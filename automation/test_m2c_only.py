#!/usr/bin/env python3
"""Does an oversized function still get attempted, without a model call?

WHY THIS EXISTS
    Eleven records sat in `deferred` reading TIER_HANDOFF_TOO_LARGE, measured
    asm 20165 to 68865 chars against a 20000 ceiling. They looked like work
    the fleet might one day pick up, and it never could.

    The ceiling was on the wrong step. worker_direct runs prepare() BEFORE the
    size check, and prepare() shells out to tools/m2ctx.py and tools/m2c/m2c.py
    to build a typed C draft. MAX_FUNC_CHARS exists because the assembly does
    not fit in a MODEL's context window; m2c is a static translator and has no
    context window at all. So for every one of the eleven, a usable draft was
    computed and then discarded.

    Now size removes only the MODEL. The draft is still cleaned, applied,
    built and judged by the oracle, and "compiles, bytes differ" is by
    definition a permuter seed.

WHAT IS ASSERTED
    That the oversized path runs one attempt, takes its C from the m2c draft
    rather than from llama_echo, gives up immediately if there is no draft,
    keeps the too-large marker when the draft does not compile, and labels
    every outcome so nobody mistakes a mechanical seed for a reasoned one.

    Structural, not behavioural: driving the real worker loop needs a live
    queue, a build and the lock. These pin the decisions that were wrong
    before, which is what a regression here would look like.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "win"))
os.environ.setdefault("MODEL_BACKEND", "zen")

import worker_direct as wd  # noqa: E402

FAILS = []


def check(cond, label):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


def main():
    src = open(wd.__file__, encoding="utf-8", errors="replace").read()
    # The whole per-record function, from the size gate to the final report.
    body = src[src.index("_asm_size = ctx.get("):]
    body = body[:body.index("\ndef ", 10)]

    print("the size gate no longer ends the record")
    gate = body[:body.index("m2c_only = True") + 40]
    check("m2c_only = True" in body,
          "an oversized record sets the m2c-only flag")
    check(gate.count('"--status", "deferred"') == 1,
          "the only immediate deferral left is the no-draft case")
    check("m2c produced no usable draft" in body,
          "and that case says m2c had nothing, not merely that it was big")

    print("\nthe draft is used INSTEAD of the model, never as well as")
    loop = body[body.index("if m2c_only:"):]
    loop = loop[:loop.index("except subprocess.TimeoutExpired")]
    check('raw = ctx["draft"]' in loop, "raw comes from the m2c draft")
    check("gen_ok = True" in loop, "and the generation call is skipped")
    check(loop.index('raw = ctx["draft"]') < loop.index("llama_echo"),
          "the draft branch is taken before llama_echo is reached")
    check("if not gen_ok:" in loop,
          "llama_echo is guarded, so an m2c run cannot also spend a call")

    print("\nit is one shot; the permuter is what iterates")
    check("if attempt > 1:" in loop and "break" in loop,
          "a second attempt breaks out")
    check("no feedback loop without a model" in loop,
          "and the reason is recorded: re-cleaning a static draft cannot "
          "reach a different verdict, it just burns build cycles")

    print("\nevery outcome says it came from m2c with no model call")
    check('_m2c_tag = "M2C-ONLY (no model call): " if m2c_only else ""' in body,
          "the tag is set from the flag")
    check("_m2c_tag + \"compiled, byte mismatch" in body,
          "a permuter seed from m2c is labelled as such")
    check("m2c draft was" in body and "did not compile" in body,
          "and so is a failure")

    print("\na non-compiling draft keeps the too-large marker")
    # Filing it as an ordinary `escalated` would lose the one label that
    # identifies this class, and deferred_triage buckets on that marker.
    tail = body[body.index("A candidate WAS produced"):]
    check("if m2c_only:" in tail, "the escalation path branches on the flag")
    check(tail.index("if m2c_only:") < tail.index('"--status", "escalated"'),
          "before the ordinary escalation is written")
    # By NAME, not by value: the source says {DEFER_TOO_LARGE}, which is the
    # point. Asserting the literal "TIER_HANDOFF_TOO_LARGE" would pass only
    # for a hardcoded copy and fail for the shared constant, rewarding
    # exactly the wrong thing.
    check("DEFER_TOO_LARGE" in tail,
          f"and re-uses the DEFER_TOO_LARGE constant "
          f"({wd.DEFER_TOO_LARGE!r}), which deferred_triage buckets on")
    check(wd.DEFER_TOO_LARGE not in tail,
          "spelled as the constant rather than pasted as a literal")

    print("\nthe rejected draft is archived, not discarded")
    check("save_rejected(" in tail and "rejected=" in tail,
          "so the next attempt starts from the draft rather than from nothing")

    print("\nthe ceiling itself is unchanged for the model path")
    check(wd.MAX_FUNC_CHARS == 20000,
          f"MAX_FUNC_CHARS is still {wd.MAX_FUNC_CHARS}")
    check('_HOSTED = {"cli", "zen"}' in src,
          "and zen is still on the hosted side of the ternary")

    print("\nprepare() really does produce the draft this depends on")
    prep = src[src.index("def prepare("):]
    prep = prep[:prep.index("\ndef ", 10)]
    check("m2c" in prep, "prepare runs m2c")
    check(re.search(r'"draft"\s*:', prep) is not None,
          "and returns it under ctx['draft']")
    check(src.index("def prepare(") < src.index("_asm_size = ctx.get("),
          "prepare is defined before the gate that now consumes its output")

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
