#!/usr/bin/env python3
"""
gen_seed_us.py: regenerate the static 'us' not-yet-decompiled function seed.

Scans committed C sources for INCLUDE_ASM stubs (functions still built from raw
assembly) belonging to the us (PSX, SLUS-00067) target and emits queue ids of
the form 'us:<overlay>:<function>' to automation/queue/seed.us.txt.

This is the STATIC undecompiled set. It does not include functions that have C
but do not yet byte-match; that authoritative non-matching list only exists
after a real build:
    make VERSION=us extract && make VERSION=us build && make function-finder

Run from the repo root:
    python3 automation/tools/gen_seed_us.py
"""
from __future__ import annotations
import collections
import datetime
import pathlib
import re
import sys

RX = re.compile(r'INCLUDE_ASM\(\s*"([^"]+)"\s*,\s*([A-Za-z0-9_]+)\s*\)')


def build_of(parts, relpath: str) -> str:
    s = "/".join(parts).lower() + " " + relpath.lower()
    if "saturn" in s:
        return "saturn"
    if "psp" in s:
        return "pspeu"
    if "/hd/" in s or "_hd" in s:
        return "hd"
    return "us"


def overlay_of(relpath: str, srcfile: pathlib.Path) -> str:
    p = relpath
    for pre in ("asm/us/", "asm/"):
        if p.startswith(pre):
            p = p[len(pre):]
            break
    parts = p.split("/")
    if "nonmatchings" in parts:
        ov = "/".join(parts[:parts.index("nonmatchings")])
    else:
        ov = "/".join(srcfile.parts[1:-1])
    return ov.upper()


def main() -> int:
    repo = pathlib.Path(__file__).resolve().parents[2]
    src = repo / "src"
    if not src.is_dir():
        print(f"src/ not found at {src}; run from the repo", file=sys.stderr)
        return 1

    rows = []
    for c in src.rglob("*.c"):
        for m in RX.finditer(c.read_text(errors="ignore")):
            relpath, func = m.group(1), m.group(2)
            rel_c = c.relative_to(repo)
            if build_of(rel_c.parts, relpath) != "us":
                continue
            rows.append((overlay_of(relpath, rel_c), func))

    rows = sorted(set(rows))
    by_ov = collections.Counter(ov for ov, _ in rows)
    out = repo / "automation" / "queue" / "seed.us.txt"

    with out.open("w", encoding="utf-8") as f:
        f.write("# SOTN us (PSX, SLUS-00067) not-yet-decompiled function seed\n")
        f.write(f"# Generated {datetime.date.today().isoformat()} from committed "
                "INCLUDE_ASM stubs in src/.\n")
        f.write(f"# Total: {len(rows)} functions across {len(by_ov)} overlays.\n")
        f.write("# These are functions still built from raw assembly (never decompiled).\n")
        f.write("# NOTE: this is the static 'undecompiled' set. The authoritative non-matching\n")
        f.write("#   list (C-present-but-not-byte-matching) comes from a real build via:\n")
        f.write("#     make VERSION=us extract && make VERSION=us build && make function-finder\n")
        f.write("#   Regenerate this static list with automation/tools/gen_seed_us.py\n")
        f.write("# Per-overlay counts:\n")
        for ov, n in sorted(by_ov.items(), key=lambda x: (-x[1], x[0])):
            f.write(f"#   {n:4d}  {ov}\n")
        f.write("# Format below: one queue id per line  ->  us:<overlay>:<function>\n")
        for ov, func in rows:
            f.write(f"us:{ov}:{func}\n")

    print(f"wrote {out} : {len(rows)} ids across {len(by_ov)} overlays")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
