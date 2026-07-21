#!/usr/bin/env python3
"""
seed_by_size.py: rebuild the us seed ordered smallest function first.

WHY
---
The original seed is alphabetical, so the worker started on BOSS/BO0 and drew
`func_us_801AD338`: an Olrox state machine with a 14-case switch across 24KB of
assembly. That is among the hardest functions in the whole queue, and it is
unmatched precisely because it is hard. Feeding it to a ~3B-active model first
guarantees failure and burns hours.

Sorting ascending by assembly size puts genuinely tractable functions first.
Small leaf functions are where an automated tier can actually win, and each
match also grows the pool of named symbols that makes later functions easier.

Run from the repo root (WSL or Windows):
    python3 automation/tools/seed_by_size.py

Writes automation/queue/seed.us.by-size.txt and prints the size distribution.
"""
from __future__ import annotations
import os
import re
import sys

RX = re.compile(r'INCLUDE_ASM\(\s*"([^"]+)"\s*,\s*([A-Za-z0-9_]+)\s*\)')


def main() -> int:
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    src = os.path.join(repo, "src")
    if not os.path.isdir(src):
        print(f"src/ not found under {repo}", file=sys.stderr)
        return 1

    rows = []
    skipped = 0
    for dp, _d, fs in os.walk(src):
        for fn in fs:
            if not fn.endswith(".c"):
                continue
            full = os.path.join(dp, fn)
            low = full.replace("\\", "/").lower()
            if any(k in low for k in ("psp", "saturn", "/hd/", "_hd")):
                continue
            try:
                text = open(full, errors="ignore").read()
            except OSError:
                continue
            for m in RX.finditer(text):
                asm_rel, func = m.group(1), m.group(2)
                base = asm_rel if asm_rel.startswith("asm/") else f"asm/us/{asm_rel}"
                asm_file = os.path.join(repo, *f"{base}/{func}.s".split("/"))
                if not os.path.exists(asm_file):
                    skipped += 1
                    continue
                overlay = (asm_rel.split("/nonmatchings")[0]
                           .replace("asm/us/", "").upper())
                rows.append((os.path.getsize(asm_file), overlay, func))

    if not rows:
        print("no functions resolved; has `make extract` been run?", file=sys.stderr)
        return 1

    rows.sort()
    out = os.path.join(repo, "automation", "queue", "seed.us.by-size.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("# us functions, SMALLEST FIRST (by reference .s size)\n")
        f.write(f"# {len(rows)} functions; regenerate with "
                f"automation/tools/seed_by_size.py\n")
        for size, overlay, func in rows:
            f.write(f"us:{overlay}:{func}\n")

    sizes = [r[0] for r in rows]
    def pct(p):
        return sizes[min(len(sizes) - 1, int(len(sizes) * p / 100))]
    print(f"wrote {out}")
    print(f"  functions      : {len(rows)}"
          + (f"  ({skipped} had no .s file)" if skipped else ""))
    print(f"  smallest       : {sizes[0]:,} bytes  ({rows[0][1]}:{rows[0][2]})")
    print(f"  median         : {pct(50):,} bytes")
    print(f"  90th percentile: {pct(90):,} bytes")
    print(f"  largest        : {sizes[-1]:,} bytes  ({rows[-1][1]}:{rows[-1][2]})")
    under = sum(1 for s in sizes if s <= 6000)
    print(f"  under 6KB (attemptable at tier 0): {under} of {len(rows)}")
    print("\nSeed the queue with:")
    print("  python3 automation/scheduler.py init --from "
          "automation/queue/seed.us.by-size.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
