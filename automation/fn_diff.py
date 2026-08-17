#!/usr/bin/env python3
"""Where do two builds of the SAME function diverge, instruction by instruction?

WHY THIS EXISTS
    `overlay_size_check.py` says WHICH function is the wrong size.
    `relocation_check.py` says whether the whole overlay differs only by a
    constant. Neither answers the question that actually unblocks a shim:
    *which instructions* does my build have that the original does not.

    Doing that by eye means reading two 800-instruction listings side by side.
    Done that way once, it found the giant-bro `zPriority += 8` in about an
    hour. As a tool it takes a second, and it is the difference between
    parameterising a shared header on evidence and guessing at it.

HOW IT ALIGNS
    Compares built vs original as MIPS words, keyed on opcode plus register
    fields but IGNORING the 16-bit immediate, because that is where relocations
    live and they legitimately differ between overlays. A run of equal keys is
    a match; a single-sided skip is an inserted or deleted instruction.

    That means it reports STRUCTURAL differences. Two instructions that differ
    only in an immediate are treated as the same instruction, which is
    deliberate: use relocation_check.py for that class.

Usage:
    python3 automation/fn_diff.py --overlay RNO0 --function EntityHammer
    python3 automation/fn_diff.py --overlay RNO0 --function EntityHammer --window 900
"""
from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

_SYM = re.compile(r"^\s+(0x[0-9a-f]+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*$")

# Opcodes whose low 16 bits carry a relocation or a branch offset. Compare
# these on opcode+registers only.
_IMM_OPS = {0x0F, 0x09, 0x08, 0x0D, 0x23, 0x21, 0x25, 0x20, 0x24,
            0x2B, 0x29, 0x28, 0x31, 0x39, 0x04, 0x05, 0x06, 0x07, 0x01}


def key(w: int):
    op = w >> 26
    if op == 3:            # jal: the target is an absolute address
        return ("jal",)
    if op in _IMM_OPS:
        return (op, w >> 16)
    return w


# A stage's map is st<name>.map, but a boss's is bo<name>.map, a reverse
# boss's is borbo<name>.map, and main/dra/ric have no prefix at all. This
# tried "st" then bare, so every boss overlay reported "not in
# build/us/stbo0.map" -- which reads like a build problem and is really the
# tool declining to look in the right place. Found 2026-08-16 diffing BO0,
# and the boss overlays are 20 of the 38 remaining upstream harvests, so this
# would have recurred on nearly every one of them.
def _map_candidates(overlay: str) -> list:
    o = overlay.lower()
    # Ordered most-specific first: "bo0" must not match "borbo0" by accident,
    # and an already-prefixed name ("bobo0") must be tried verbatim.
    return [f"{o}", f"st{o}", f"bo{o}", f"borbo{o}", f"b{o}"]


def load_map(overlay: str) -> dict:
    p = None
    for name in _map_candidates(overlay):
        cand = REPO / "build" / "us" / f"{name}.map"
        if cand.exists():
            p = cand
            break
    out = {}
    if p is None:
        return out
    for ln in p.read_text(errors="replace").splitlines():
        m = _SYM.match(ln.rstrip())
        if m:
            out.setdefault(m.group(2), int(m.group(1), 16))
    return out


def find_original(overlay: str) -> Path | None:
    for sub in ("ST", "BOSS", "SERVANT"):
        c = REPO / "disks" / "us" / sub / overlay / f"{overlay}.BIN"
        if c.exists():
            return c
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--overlay", required=True)
    ap.add_argument("--function", required=True)
    ap.add_argument("--window", type=int, default=1200)
    ap.add_argument("--max", type=int, default=12)
    ap.add_argument("--vram", default="0x80180000")
    a = ap.parse_args()

    syms = load_map(a.overlay)
    if a.function not in syms:
        tried = "  ".join(f"build/us/{n}.map"
                          for n in _map_candidates(a.overlay))
        print(f"{a.function} not in any map for overlay {a.overlay}. "
              f"Build first, and check the name.\n  tried: {tried}")
        return 2
    orig_p = find_original(a.overlay)
    built_p = REPO / "build" / "us" / f"{a.overlay}.BIN"
    if not orig_p or not built_p.exists():
        print("missing original or built binary")
        return 2

    off = syms[a.function] - int(a.vram, 16)
    built = built_p.read_bytes()
    orig = orig_p.read_bytes()
    n = min(a.window, (len(built) - off) // 4, (len(orig) - off) // 4)
    if n <= 0:
        print("function offset is outside one of the images")
        return 2
    b = list(struct.unpack_from(f"<{n}I", built, off))
    o = list(struct.unpack_from(f"<{n}I", orig, off))

    i = j = 0
    events = []
    while i < n and j < n and len(events) < a.max:
        if key(b[i]) == key(o[j]):
            i += 1
            j += 1
            continue
        if i + 1 < n and key(b[i + 1]) == key(o[j]):
            events.append(("BUILT has an EXTRA instruction", i, b[i]))
            i += 1
            continue
        if j + 1 < n and key(b[i]) == key(o[j + 1]):
            events.append(("ORIGINAL has an instruction we DROPPED", j, o[j]))
            j += 1
            continue
        events.append(("instructions DIFFER", i, b[i], o[j]))
        i += 1
        j += 1

    print(f"{a.overlay}:{a.function}  at {syms[a.function]:#010x}, "
          f"comparing {n} instructions")
    if not events:
        print("  no structural difference in this window. If the build still "
              "fails, the difference is in an immediate: use "
              "relocation_check.py.")
        return 0
    for e in events:
        where = syms[a.function] + e[1] * 4
        if len(e) == 3:
            print(f"  {where:#010x} (+{e[1]:4d})  {e[0]}: {e[2]:#010x}")
        else:
            print(f"  {where:#010x} (+{e[1]:4d})  {e[0]}: "
                  f"built {e[2]:#010x} vs original {e[3]:#010x}")
    print()
    print("Read an EXTRA in BUILT as: the shared header does something this "
          "stage does not. Read a DROPPED as: this stage does something the "
          "header does not, which is the parameter you need.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
