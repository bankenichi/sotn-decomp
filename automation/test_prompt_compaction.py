#!/usr/bin/env python3
"""Does prompt compaction shrink the prompt WITHOUT losing anything?

WHY THIS EXISTS
    Prompt size is the strongest predictor of a dead model call in this
    harness. Measured 2026-08-03 over 123 cli calls:

        0-5k chars     0% dead
        5-10k chars   61% dead
        10-20k chars  83% dead

    So shrinking the prompt is a bigger lever than either the model or the
    timeout. But a smaller prompt that has quietly dropped a symbol is worse
    than a large one: the model invents an extern instead of using the real
    declaration, and that is the single biggest review-rejection class this
    project has (see resolve_raw_symbols' docstring).

    Hence this file asserts BOTH halves. Size alone is not the goal.

WHAT IS COMPACTED
    Splat writes `/* 4B2DC 801CB2DC C8FFBD27 */` on every instruction: file
    offset, virtual address, raw encoding. None of it helps write C, and it is
    roughly two thirds of the file.

Run: python3 automation/test_prompt_compaction.py
"""
from __future__ import annotations

import importlib.util
import re
import statistics
import sys
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


def main() -> int:
    wd = load()

    print("\nit actually shrinks, measured on the real asm tree")
    # islice, not a list slice. rglob is a GENERATOR: materialising it and
    # then slicing walks the entire asm tree, which takes 16s on the Windows
    # mount and blew the sandbox timeout. Stopping early costs nothing.
    from itertools import islice
    files = list(islice(
        (p for p in (REPO / "asm" / "us").rglob("*.s")
         if p.stat().st_size > 2000), 120))
    if not files:
        print("  ~~ no asm found; run make extract first")
        return 0
    savings = []
    for f in files:
        raw = f.read_text(errors="ignore")
        small = wd.compact_asm(raw)
        savings.append(100.0 * (len(raw) - len(small)) / len(raw))
    med = statistics.median(savings)
    check(med > 45, f"median saving is {med:.0f}%", "expected well over 45%")
    check(min(savings) >= 0, "no file gets LARGER")

    print("\nnothing the prompt depends on is lost")
    # Every symbol the two asm-consuming helpers look for must survive. These
    # are the exact patterns resolve_raw_symbols and undeclared_symbols use.
    rx_draw = re.compile(r"\bD_(?:us_)?[0-9A-Fa-f]{8}\b")
    rx_hilo = re.compile(r"%(?:hi|lo)\(\s*[A-Za-z_]\w*")
    rx_label = re.compile(r"^\s*(glabel|jlabel|\.L\w+|\w+:)", re.M)
    rx_jal = re.compile(r"\bjal\s+(\w+)")
    lost_sym = lost_hilo = lost_label = lost_jal = 0
    checked = 0
    for f in files:
        raw = f.read_text(errors="ignore")
        small = wd.compact_asm(raw)
        checked += 1
        if set(rx_draw.findall(raw)) - set(rx_draw.findall(small)):
            lost_sym += 1
        if set(rx_hilo.findall(raw)) - set(rx_hilo.findall(small)):
            lost_hilo += 1
        if len(rx_label.findall(raw)) != len(rx_label.findall(small)):
            lost_label += 1
        if set(rx_jal.findall(raw)) - set(rx_jal.findall(small)):
            lost_jal += 1
    check(lost_sym == 0, f"no D_ symbol lost in {checked} files ({lost_sym})")
    check(lost_hilo == 0, f"no %hi/%lo operand lost ({lost_hilo})")
    check(lost_label == 0, f"no branch label lost ({lost_label})")
    check(lost_jal == 0, f"no call target lost ({lost_jal})")

    print("\nthe instruction stream itself is intact")
    # Pick a file that actually HAS the prefix. files[0] happened not to, so
    # the first version of this check compared an empty opcode list against an
    # empty one and called that a pass -- a test that could only fail by
    # accident is not a test.
    rx_instr = re.compile(
        r"^\s*/\* [0-9A-Fa-f]+ [0-9A-Fa-f]+ [0-9A-Fa-f]+ \*/\s*(\w+)", re.M)
    sample = ""
    for f in files:
        t = f.read_text(errors="ignore")
        if len(rx_instr.findall(t)) > 20:
            sample = t
            break
    check(bool(sample), "found an asm file with prefixed instructions to check")
    if sample:
        ops_raw = rx_instr.findall(sample)
        small = wd.compact_asm(sample)
        body = [l.strip().split()[0] for l in small.splitlines()
                if l.strip()
                and not l.strip().startswith((".", "/*", "glabel", "jlabel"))]
        check(ops_raw == body[:len(ops_raw)],
              f"every opcode survives in order ({len(ops_raw)} instructions)",
              f"raw {ops_raw[:4]} vs compacted {body[:4]}")
        check(len(ops_raw) > 20, f"and it is a real sample ({len(ops_raw)})")

    print("\nthe draft compactor keeps the code and drops the chatter")
    d = ("// m2c commentary line\n\n\n"
         "void f(s32 a) {   \n    return a + 1;   \n}\n\n\n")
    c = wd.compact_draft(d)
    check("void f(s32 a)" in c and "return a + 1;" in c, "code survives")
    check("m2c commentary" not in c, "m2c's own comment lines are dropped")
    check("\n\n\n" not in c, "runs of blank lines are collapsed")
    check(wd.compact_draft("") == "", "an empty draft does not raise")

    print("\ncompaction is idempotent")
    once = wd.compact_asm(sample)
    check(wd.compact_asm(once) == once,
          "running it twice changes nothing, so a re-prepared function does "
          "not degrade")

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
