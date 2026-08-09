#!/usr/bin/env python3
"""What are the models actually spending their thinking on?

WHY THIS EXISTS
    Until 2026-08-03 the fleet's reasoning was invisible: `opencode run` relays
    only `content`, so a model that thought for four minutes and emitted
    nothing looked identical to a dead request. The zen backend captures
    `reasoning_content`, and that turns the single largest cost in the harness
    into readable evidence.

    This reads it and answers the only question that matters for tuning: where
    does the budget go, and which of that is work the HARNESS should have done
    before the model ever saw the prompt.

WHAT THE FIRST CAPTURE SHOWED (10 calls, 96,569 chars of reasoning)

    36%   sentences resolving a raw offset to a struct field
     1%   verbatim echo of the ENTITY LAYOUT table we supplied
    110   distinct offsets reasoned about across 10 functions

    A representative block opens by restating the task, transcribes the layout
    table into its own reasoning, and then walks the assembly offset by offset:

        "half at 0x0A: not in layout as half. Layout has velocityX (0x08) and
         velocityY (0x0C) both s32. 0x0A is within velocityX? Actually
         velocityX s32 spans 0x08-0x0B, so 0x0A is the high half..."

    That is a table lookup, done in prose, once per offset, by a model that
    charges by the token. The harness already parses the assembly; it knows
    exactly which offsets appear. Resolving them BEFORE the prompt is sent
    replaces the most expensive third of the reasoning with a few lines of
    text, and removes the failure it causes: all 8 build failures in that run
    were "structure has no member named unkNN", i.e. offsets the model had not
    finished resolving when the cap fired.

STRICTLY READ-ONLY.

Usage:
    python3 automation/reasoning_audit.py
    python3 automation/reasoning_audit.py --offsets     # what it struggled on
    python3 automation/reasoning_audit.py --sample 1    # read one block
    python3 automation/reasoning_audit.py --self-test
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "automation" / "logs"

# The worker prints reasoning after a "[thinking]" marker and ends the block at
# the cap notice, the force-code arrow, or the content marker.
RX_BLOCK = re.compile(r"\[thinking\](.*?)(?=\n\s*(?:\[output\]|!!|-->|---)|\Z)",
                      re.S)
RX_OFFSET_SENT = re.compile(r"[^.\n]*0x[0-9A-Fa-f]{1,3}[^.\n]*[.\n]")
RX_OFFSET = re.compile(r"0x[0-9A-Fa-f]{1,3}\b")
RX_UNK = re.compile(r"\bunk[0-9A-Fa-f]{1,3}\b")

# Phrases that mean "the prompt did not tell me something I needed". Each one
# is a candidate prompt fix, which is the entire point of reading this.
GAPS = (
    ("unresolved offset", re.compile(
        r"not in (?:the )?layout|no (?:named )?field|keep unk|"
        r"we (?:can|could|might) keep unk", re.I)),
    ("no raw address given", re.compile(
        r"RAW ADDRESSES|no raw address|not given.*address", re.I)),
    ("no existing code given", re.compile(
        r"EXISTING CODE|no existing (?:code|struct)", re.I)),
    ("guessing the signature", re.compile(
        r"return type (?:is )?(?:unclear|unknown|might)|"
        r"(?:takes|has) no arg|signature (?:is )?unclear", re.I)),
    ("width mismatch", re.compile(
        r"(?:lhu|lh|lbu|lb|lw)\b.*(?:but|however).*(?:s32|u32|word)|"
        r"high half|low half|spans 0x", re.I)),
    ("explicit uncertainty", re.compile(
        r"\bnot sure\b|\bunclear\b|\bhard to say\b|\bwe don't know\b", re.I)),
)


def log_files() -> list[Path]:
    out = list(LOGS.glob("worker-*.log"))
    arch = LOGS / "archive"
    if arch.is_dir():
        out += list(arch.rglob("worker-*.log"))
    return sorted(out)


def blocks(paths: list[Path]) -> list[str]:
    out = []
    for p in paths:
        out += [b for b in RX_BLOCK.findall(p.read_text(errors="ignore"))
                if len(b.strip()) > 200]
    return out


def report(bl: list[str], show_offsets: bool = False) -> None:
    if not bl:
        print("No reasoning captured yet. It only exists on the zen/http "
              "backend:\n  fleet_start(workers=2, backend='zen')\n"
              "The cli backend relays only `content`, so its thinking is gone.")
        return
    total = sum(len(b) for b in bl)
    print(f"\n{len(bl)} reasoning block(s), {total:,} chars\n")

    off_chars = sum(len(m.group(0)) for b in bl
                    for m in RX_OFFSET_SENT.finditer(b))
    print(f"{'where the budget goes':38} {'chars':>9} {'share':>7}")
    print("-" * 58)
    print(f"{'resolving raw offsets to fields':38} {off_chars:9,} "
          f"{100.0*off_chars/total:6.0f}%")
    unk = sum(len(RX_UNK.findall(b)) for b in bl)
    print(f"{'mentions of an unkNN field':38} {unk:9,} {'':>7}")
    print("-" * 58)
    print("Offset resolution is a TABLE LOOKUP. The harness parses the asm and")
    print("already knows every offset in it; doing that lookup before the")
    print("prompt is sent is the largest single saving available.")

    print("\ngaps the reasoning complains about (each is a prompt fix)")
    for label, rx in GAPS:
        n = sum(len(rx.findall(b)) for b in bl)
        if n:
            print(f"  {n:5d}  {label}")

    sizes = sorted(len(b) for b in bl)
    print(f"\nblock size: min {sizes[0]:,}  median {sizes[len(sizes)//2]:,}  "
          f"max {sizes[-1]:,} chars")
    print("If the median sits at the cap, the cap is the behaviour rather than")
    print("a safety net, and the analyses are being truncated mid-thought.")

    if show_offsets:
        c = Counter(o.lower() for b in bl for o in RX_OFFSET.findall(b))
        print(f"\nmost-reasoned-about offsets ({len(c)} distinct)")
        for o, n in c.most_common(25):
            print(f"  {n:4d}x  {o}")
        print("\nPre-resolving these in the prompt is one line of text each.")


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    print("\nreasoning blocks are extracted from real worker-log shapes")
    sample = (
        "  --- streaming from llama-server (prompt 100 chars) ---\n"
        "[thinking] We need to map offset 0x24 to a field. "
        + "The layout says zPriority. " * 20 + "\n"
        "  !! reasoning exceeded 3000 tokens with no code produced\n"
        "  --> 3040 reasoning tokens, 0 content.\n")
    bl = RX_BLOCK.findall(sample)
    ck(len(bl) == 1, f"one block found ({len(bl)})")
    ck("0x24" in bl[0], "the block keeps its content")
    ck("reasoning exceeded" not in bl[0],
       "and stops at the cap notice rather than swallowing the log")

    print("\nshort noise is not mistaken for reasoning")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "worker-zen-x.log"
        p.write_text("[thinking] hm\n", encoding="utf-8")
        ck(blocks([p]) == [], "a two-word block is ignored")

    print("\nthe gap patterns match the phrases models actually used")
    real = ("not in layout as half. Layout has velocityX (0x08). "
            "So we can keep unk8. But there is no RAW ADDRESSES section, "
            "so we are not sure.")
    hits = {label for label, rx in GAPS if rx.search(real)}
    ck("unresolved offset" in hits, f"unresolved offset detected ({hits})")
    ck("no raw address given" in hits, "missing RAW ADDRESSES detected")
    ck("explicit uncertainty" in hits, "explicit uncertainty detected")
    clean = "The function loads posX and stores it back. Straightforward."
    ck(not any(rx.search(clean) for _l, rx in GAPS),
       "clean reasoning raises no gaps")

    print("\nan empty corpus is reported, not crashed on")
    ck(blocks([]) == [], "no files yields no blocks")

    print()
    if fails:
        print(f"{len(fails)} FAILED:")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offsets", action="store_true",
                    help="list the offsets the models spent the most on")
    ap.add_argument("--sample", type=int,
                    help="print one reasoning block in full, 1-based")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    bl = blocks(log_files())
    if a.sample:
        if not 1 <= a.sample <= len(bl):
            print(f"there are {len(bl)} block(s)", file=sys.stderr)
            return 2
        print(bl[a.sample - 1])
        return 0
    report(bl, show_offsets=a.offsets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
