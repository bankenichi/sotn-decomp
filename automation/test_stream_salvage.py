#!/usr/bin/env python3
"""Does a timed-out attempt keep the code the model already finished?

WHY THIS EXISTS
    Observed on worker-oc-1, 2026-08-03, function func_us_801B21F0:

        [worker] attempt 2/4 (809s of budget left)
          --- opencode run (opencode/mimo-v2.5-free, prompt 8307 chars, ...) ---
          | void func_us_801B21F0(void) {
          |     ... 130 lines of complete, plausible C ...
          | }
          !! attempt 2 timed out after 90s; trying the next attempt

    The model finished the function. The worker threw it away, spent two more
    attempts, and reported the function as producing no candidate.

    The cause was five lines in _opencode_run_once: on subprocess.TimeoutExpired it
    killed the child and re-raised, and `buf` -- which held every streamed line
    -- went out of scope. Nothing was wrong with the generation; the salvage
    simply did not exist.

    Tightening ATTEMPT_BUDGET to 90s made this the COMMON case rather than a
    rare one. The measured productive median is 73s, so a model that writes the
    code and then keeps talking now routinely crosses the cap during its own
    epilogue, with the answer already on stdout.

WHY THE GATE IS STRICT
    A partial body is worse than nothing. It either fails the build with an
    error describing the truncation rather than the real problem, or closes by
    accident and compiles into something the model never wrote. So
    complete_function() salvages ONLY on balanced braces ending in `}`, and
    anything less re-raises exactly as before.

Run: python3 automation/test_stream_salvage.py
"""
from __future__ import annotations

import importlib.util
import inspect
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAILS: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    print(("  ok   " if cond else "  FAIL ") + label
          + ("" if cond else "   " + detail))
    if not cond:
        FAILS.append(label)


def load():
    spec = importlib.util.spec_from_file_location(
        "worker_direct", REPO / "automation" / "win" / "worker_direct.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# Trimmed from the real worker-oc-1 log. Ends with the closing brace, which is
# the whole point: this is a finished answer that was discarded.
REAL_STREAM = """/* Updates boss limb positions relative to body using rotation. */
void func_us_801B21F0(void) {
    Entity* boss = g_CurrentEntity;
    Entity* limb1 = (Entity*)boss->ext.ILLEGAL.u32[1];
    s32 angle, sinVal, cosVal;

    if (boss->facingLeft != 0) {
        angle = 0xC00 - limb1->hitboxOffX;
    } else {
        angle = limb1->hitboxOffX + 0xC00;
    }
    cosVal = rcos(angle);
    limb1->posX.val = cosVal;
}
"""


def main() -> int:
    wd = load()
    cf = wd.complete_function

    print("\nthe real discarded answer is recognised as complete")
    got = cf(REAL_STREAM)
    check(bool(got), "the func_us_801B21F0 stream salvages")
    check("func_us_801B21F0" in got, "and the function name survives")
    check(got.rstrip().endswith("}"), "and it ends at the closing brace")

    print("\ncomplete bodies salvage")
    for text, label in [
        ("void f(void) {\n  int a = 1;\n}\n", "a plain function"),
        ("void f(void) {\n  if (x) {\n    y();\n  }\n}", "nested braces"),
        ('void f(void) {\n  msg("}");\n}', "a brace inside a string literal"),
        ("void f(void) {\n  c = '}';\n}", "a brace inside a char literal"),
        ("void f(void) {\n  /* } */\n}", "a brace inside a block comment"),
        ("void f(void) {\n  // }\n}", "a brace inside a line comment"),
        ("extern s16 RIC_step;\nvoid f(void) {\n  RIC_step = 1;\n}",
         "declarations kept ahead of the body"),
    ]:
        check(bool(cf(text)), label)

    print("\nanything less than complete is REFUSED, so no partial body builds")
    for text, label in [
        ("void f(void) {\n  int a = 1;\n", "truncated mid-body"),
        ("void f(void) {\n  if (x) {\n    y();\n", "truncated inside nesting"),
        ("", "an empty stream"),
        ("Here is my analysis of the function.", "prose with no code at all"),
        ("void f(void) {\n}\n\nI hope this helps!", "trailing prose"),
        ("void f(void) {\n  s = \"unterminated;\n}", "an unterminated string"),
        ("/* thinking about it */", "a comment only"),
    ]:
        check(not cf(text), label)

    print("\nthe salvage is wired into the timeout path, not just defined")
    src = inspect.getsource(wd._opencode_run_once)
    # Strip comments first. The prose in the handler MENTIONS
    # complete_function() before the call site, so ordering assertions made
    # against the raw text were measuring the explanation, not the code.
    src = "\n".join(l for l in src.splitlines()
                    if not l.lstrip().startswith("#"))
    # The salvage used to live in an `except subprocess.TimeoutExpired`. It now
    # hangs off the adaptive-wait verdict, because a deadline that varies with
    # what has been received cannot be expressed as proc.wait(timeout=...).
    to = src[src.index("if kill_reason:"):]
    check("complete_function" in to,
          "the kill path consults the gate")
    check(to.index("proc.kill()") < to.index("complete_function"),
          "it stops the child before reading the buffer")
    check("done.wait" in to,
          "and waits for the pump thread, so the last lines are not missed")
    check("raise" in to,
          "an incomplete stream still raises, so the attempt is spent")
    check(to.index("complete_function") < to.rindex("raise"),
          "salvage is attempted BEFORE giving up, not after")

    print("\nthe deadline is adaptive, not a flat cap")
    wait = src[src.index("def _adaptive_wait"):src.index("kill_reason =")]
    check("ttfb[0] is None" in wait,
          "silence and slowness are handled as different states")
    check("NO_FIRST_BYTE_S" in wait and "STREAM_IDLE_S" in wait,
          "each state has its own deadline")
    check("last_byte[0]" in wait,
          "idle time is measured from the LAST BYTE, not from the start, so a "
          "model that keeps producing is never cut off for taking long")
    check("hard_cap" in wait,
          "and an absolute ceiling still exists, so a chatty model cannot hold "
          "a worker forever")
    check(wd.NO_FIRST_BYTE_S >= 120,
          f"the no-first-byte deadline is generous ({wd.NO_FIRST_BYTE_S}s): on "
          f"a reasoning model no first byte means STILL THINKING, not dead")

    print("\nthe cap that made this common is still the measured one")
    check(wd.ATTEMPT_BUDGET <= 120,
          f"ATTEMPT_BUDGET is tight ({wd.ATTEMPT_BUDGET}s), which is exactly "
          f"why salvage matters")

    print("\nthe degeneration detector does not kill REAL analysis")
    # Replayed against reasoning captured from the first zen run. All ten of
    # those blocks ended in a usable analysis that the force-code pass turned
    # into C, so any firing here is a false positive that would throw away
    # working generation.
    #
    # This matters because a SYNTHETIC "healthy" case -- "step 1: offset 0x01,
    # step 2: offset 0x02, ..." -- DOES trip the enumeration rule. Real
    # reasoning is not that regular, but the margin is thin enough that the
    # detector must be regression-tested against real text, never against a
    # pattern someone invented.
    fx = REPO / "automation" / "fixtures" / "real_reasoning.txt"
    if fx.is_file():
        real = fx.read_text(errors="ignore")
        chunks = re.findall(r"\S+\s*", real)
        det = wd.make_degeneration_detector()
        fired = ""
        for j in range(40, len(chunks) + 1, 40):
            fired = det(chunks[:j])
            if fired:
                break
        check(not fired,
              f"real captured reasoning runs clean ({len(real)} chars)", fired)
    else:
        check(False, "the real-reasoning fixture is present")

    # And it must still catch the thing it exists for.
    det2 = wd.make_degeneration_detector()
    stuck = ["the same sentence repeated verbatim\n"] * 80
    caught = ""
    for j in range(40, len(stuck) + 1, 40):
        caught = det2(stuck[:j])
        if caught:
            break
    check(bool(caught), f"a genuinely stuck stream is still caught ({caught})")

    print("\nthe reasoning cap is not the default behaviour")
    check(wd.REASON_CAP >= 6000,
          f"REASON_CAP is {wd.REASON_CAP}: the first zen run hit 3000 on 10 of "
          f"10 calls mid-analysis, which means the cap WAS the behaviour "
          f"rather than a safety net")

    print("\nstale claims about the CLI having no stream are gone")
    whole = (REPO / "automation" / "win" / "worker_direct.py").read_text(
        errors="ignore")
    check("gives no stream to watch" not in whole,
          "the CLI backend does stream now; the old comment said otherwise "
          "and would send the next reader down the wrong path")

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
