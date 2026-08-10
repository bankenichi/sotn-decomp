#!/usr/bin/env python3
"""Does the forced code pass stop when its OUTPUT degenerates?

WHY THIS EXISTS
    worker-zen-2, 2026-08-09. The main stream degenerated, the reasoning
    detector caught it, the worker fell back to a forced code pass -- and that
    pass emitted

        s32 temp2;
        s32 temp3;
        ...
        s32 temp5008;

    for 84KB until the function budget cut it off. Nothing stopped it.

    THE DETECTOR WAS NEVER THE PROBLEM. Replayed against that captured log it
    returns "enumeration loop" after 30 lines / 506 characters. The bug was
    pure wiring: `_force_code` checked the `reasoning` channel and left
    `content` completely unwatched, so the one channel the runaway was
    actually on had no check and no ceiling.

    Two consequences, both tested below: it must abort early, and it must not
    then return the partial text as if it were a candidate function.

HOW THIS IS TESTED
    By driving the REAL `_force_code` against a fake HTTP stream, not by
    calling the detector directly. A test that only calls the detector is the
    test that would have passed while this bug was live.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "win"))
os.environ.setdefault("MODEL_BACKEND", "zen")

import worker_direct as wd  # noqa: E402

FAILS = []


def check(cond, label):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


class FakeStream(io.RawIOBase):
    """Minimal stand-in for the SSE response object `_force_code` iterates."""

    def __init__(self, pieces, channel="content"):
        self.lines = []
        for p in pieces:
            d = {"choices": [{"delta": {channel: p}}]}
            self.lines.append(b"data: " + json.dumps(d).encode())
        self.lines.append(b"data: [DONE]")
        self.served = 0

    def __iter__(self):
        for l in self.lines:
            self.served += 1
            yield l

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def run_force_code(pieces, channel="content"):
    """Call the real _force_code with the network and console stubbed out."""
    stream = FakeStream(pieces, channel)
    real_open, real_stdout = wd._open_with_backoff, sys.stdout
    wd._open_with_backoff = lambda req, to: stream
    sys.stdout = io.StringIO()
    try:
        result = wd._force_code("prompt", "prior analysis", timeout=60)
        log = sys.stdout.getvalue()
    finally:
        wd._open_with_backoff, sys.stdout = real_open, real_stdout
    return result, log, stream


def main():
    n = wd.CONTENT_CHECK_EVERY

    print("a runaway declaration list on the CONTENT channel is stopped")
    runaway = [f"    s32 temp{i};\n" for i in range(1, 4000)]
    res, log, stream = run_force_code(runaway)
    check("salvage aborted" in log,
          "the salvage announces the abort")
    check("declaration loop" in log or "enumeration" in log,
          f"and names the shape it saw ({log.strip().splitlines()[-1][:70]!r})")
    check(stream.served < len(runaway) / 2,
          f"it stops EARLY rather than draining the stream "
          f"({stream.served} of {len(runaway)} chunks read)")
    check(stream.served <= n * 3,
          f"within a few check intervals ({stream.served} chunks, interval {n})")

    print("\nand the garbage is not returned as a candidate function")
    check(res == "",
          f"_force_code returns nothing, not the partial text "
          f"({len(res)} chars returned)")
    check("discarded" in log, "the log says the text was discarded")

    print("\na normal short function is untouched")
    good = ["void ", "EntityDummy", "(Entity* self) ", "{\n",
            "    self->step++;\n", "}\n"]
    res2, log2, stream2 = run_force_code(good)
    check("EntityDummy" in res2, "the function comes back intact")
    check("aborted" not in log2, "no abort fires on healthy output")
    check(stream2.served == len(good) + 1, "the whole stream was read")

    print("\nthe real captured log is what the detector is judged against")
    here = os.path.dirname(os.path.abspath(__file__))
    cap = os.path.join(here, "fixtures", "zen2-salvage-runaway.txt")
    if os.path.exists(cap):
        body = open(cap, encoding="utf-8", errors="replace").read()
        why = wd._content_degen_reason(body)
        check(bool(why), f"the captured worker-zen-2 output is flagged ({why!r})")
        head = "\n".join(body.splitlines()[:40])
        check(bool(wd._content_degen_reason(head)),
              "and flagged from its first 40 lines, so the abort is early")
    else:
        check(False, f"the captured runaway fixture is missing ({cap})")

    print("\nan offset TABLE is not an enumeration loop")
    # Measured 2026-08-09 over 179 aborts in the archived logs: the
    # enumeration branch fired ~95 times and the trigger strings were things
    # like `- 0x52: unk52`, `/* 0x16 */ s16 y3;`, `- 0x0A: y0 (s16)`. Those
    # are the model writing out a struct layout -- the work the prompt asks
    # for -- and the old rule killed it, because it normalised every number to
    # `#` before comparing and a layout then collapses to one shape.
    table = ["- 0x20: s16 x0", "- 0x22: s16 y0", "- 0x24: s16 x1",
             "- 0x26: s16 y1", "- 0x28: s16 x2", "- 0x2A: s16 y2",
             "- 0x2C: s16 x3", "- 0x2E: s16 y3"]
    check(wd._enumeration_loop(table) == "",
          "a table of DISTINCT ascending offsets is left alone")
    layout = ["/* 0x16 */ s16 y3;", "/* 0x18 */ s16 x4;",
              "/* 0x1A */ s16 y4;", "/* 0x1C */ s16 x5;",
              "/* 0x1E */ s16 y5;", "/* 0x20 */ s16 x6;"]
    check(wd._enumeration_loop(layout) == "",
          "and so is a C struct layout, which was a 100% false-positive shape")
    loop = ["- 0x20: s16 x0", "- 0x20: s16 x0", "- 0x20: s16 x0",
            "- 0x20: s16 x0", "- 0x20: s16 x0", "- 0x20: s16 x0"]
    check("enumeration loop" in wd._enumeration_loop(loop),
          "but the SAME offset repeated is still caught: repetition is the "
          "signal, not shape")
    short_run = ["- 0x20: a", "- 0x22: b", "- 0x24: c"]
    check(wd._enumeration_loop(short_run) == "",
          "fewer than 6 short lines is never enough evidence")

    print("\nthe abort NAMES the line that repeated, not the last line seen")
    # TASK #85 asked for a false-positive rate measured from the logs. It could
    # not be answered, because the one recorded field was misattributed: the
    # message quoted tail[-1], and the tail usually ends with a sentence of
    # prose AFTER the repeating run. So the archives are full of aborts reading
    #   enumeration loop ('Actually wait - looking at the code more car'...)
    #   enumeration loop ("Hmm, without the Primitive struct definition"...)
    # which look exactly like the detector killing live reasoning and are no
    # evidence either way.
    trailing_prose = loop + ["Actually wait, let me re-check the layout here."]
    v = wd._enumeration_loop(trailing_prose)
    check("0x20" in v,
          f"the repeated line is quoted ({v!r})")
    check("Actually wait" not in v,
          "and the trailing prose, which did NOT repeat, is not")
    check("x6" in v,
          "with the repeat count, so a tight loop reads differently from a "
          "line that merely occurs twice")

    print("\nrestating while still naming new symbols is not a loop")
    # 66 of 179 archived aborts came from the long-cycle rule and 52% of those
    # killed a real derivation, e.g. "Now I'm verifying the offset calculation:
    # the code multiplies arg1 by 188 (0xBC)...". The rule fired because a
    # 300-char tail appeared verbatim earlier. Careful decompilation restates
    # constantly; what distinguishes a loop is that nothing NEW appears.
    filler = "The function reads the entity and updates its state. " * 90
    repeated = "Looking at the comparison logic more carefully, the code loads a value from g_Ric and shifts it left by sixteen bits then right again to sign extend the halfword before comparing. " * 2
    advancing = repeated + filler + repeated + (
        " Now offset 0x34A holds invincibilityTimer, 0x8C is spriteBank, "
        "0x1F4 selects the palette, and D_us_80181524 indexes the table, "
        "while func_us_801B9DE4 does the actual step dispatch.")
    st = [0]
    verdicts = [wd._long_cycle(advancing, st) for _ in range(4)]
    check(all(v == "" for v in verdicts),
          f"a verbatim repeat is forgiven while new symbols keep appearing "
          f"({[v[:24] for v in verdicts if v]})")

    stuck = repeated + filler + repeated
    st2 = [0]
    outs = [wd._long_cycle(stuck, st2) for _ in range(4)]
    check(any("long-cycle" in v for v in outs),
          "but a repeat with NO new symbols is still caught")
    check(outs[0] == "" and outs[1] == "",
          "and it takes three strikes, not one, so a single restatement is "
          "never fatal")

    print("\nand THAT abort records what it decided on")
    # Same defect as the enumeration branch quoting tail[-1]: this said only
    # "repeating and no new symbols over three checks", which records no
    # evidence at all. Nobody can second-guess the call without the raw log,
    # and the raw logs are what #85 had to work from.
    msg = next((v for v in outs if v), "")
    # A WINDOW, so it starts mid-sentence: the rule compares the last `window`
    # characters, not whole sentences. My first version of this asserted the
    # opening words of the repeated sentence and failed for that reason. What
    # matters is that the quote is real stream content, so check a distinctive
    # symbol from inside the window rather than its start.
    check("g_Ric" in msg,
          f"the repeated chunk is quoted verbatim ({msg[:60]!r})")
    check("new tokens" in msg,
          "and the novelty count that failed the escape, which is the other "
          "half of the decision")

    st3 = [0]
    check(wd._long_cycle("short stream", st3) == "",
          "a short stream is never judged at all")

    print("\nboth streaming paths share one formatter")
    src = open(os.path.join(here, "win", "worker_direct.py"),
               encoding="utf-8").read()
    body = src.split("def _content_degen_reason", 1)[1]
    check(body.count("_content_degen_reason(") >= 2,
          "the main loop and the salvage both call it, so they cannot drift")

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
