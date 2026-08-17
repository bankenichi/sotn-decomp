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


def _imm(w: int) -> int:
    """Sign-extended 16-bit immediate, the way addiu reads it."""
    v = w & 0xFFFF
    return v - 0x10000 if v >= 0x8000 else v


def resolve_addr(addr: int, overlay: str) -> str:
    """A name for a data address, from the map, the symbol files, or splat's
    own naming convention.

    The convention fallback is not a guess in the usual sense: splat generates
    `D_us_<ADDR>` for every unnamed data symbol, so for an address that has no
    hand-given name that IS the name the source will use.
    """
    for name, a in load_map(overlay).items():
        if a == addr:
            return name
    for cfg in sorted((REPO / "config").glob("symbols.us.*.txt")):
        try:
            for line in cfg.read_text(errors="ignore").splitlines():
                m = re.match(r"\s*(\w+)\s*=\s*(0x[0-9A-Fa-f]+)\s*;", line)
                if m and int(m.group(2), 16) == addr:
                    return m.group(1)
        except OSError:                                      # pragma: no cover
            continue
    return f"D_us_{addr:08X}"


def diagnose_extern_shape(o: list, events: list, overlay: str) -> list:
    """Name the WRONG-EXTERN-TYPE failure class, with the symbol involved.

    THE CLASS. A harvested or generated body can be character-for-character
    correct and still miss, because a symbol it names is DECLARED with the
    wrong shape. `extern u8 X;` makes a bare `X` read the VALUE at X;
    `extern u8 X[];` makes it decay to the ADDRESS of X. When a function
    passes X to something expecting a pointer, only the second is right, and
    only the second emits the lui/addiu pair that materialises the address.

    THE FINGERPRINT, which is why this is mechanical rather than a hunch:
    the original contains `lui rX, %hi` immediately followed by
    `addiu rX, rX, %lo`, and the build DROPPED the addiu. An address the
    original computes, the build never computed. Everything after it shifts by
    one instruction, so a one-word mistake presents as a dozen diff lines and
    reads like a codegen problem.

    Found 2026-08-16 on func_us_801BBBD0 (BOSS/BO6): upstream's body was
    verbatim, D_us_801812B8 evaluated to 0, and the build passed zero in $a1
    where the original passes 0x801812B8. Declaring it
    `extern AnimationFrame* D_us_801812B8[]` fixed it with no change to the
    body. Diagnosing that by eye took a build, a diff and a symbol hunt; this
    prints it.

    Returns a list of human-readable findings, empty when the shape is fine.
    """
    out = []
    for e in events:
        if not e[0].startswith("ORIGINAL has an instruction we DROPPED"):
            continue
        j, word = e[1], e[2]
        if (word >> 26) != 0x09:            # addiu
            continue
        if j == 0 or (o[j - 1] >> 26) != 0x0F:   # preceded by lui
            continue
        lui, rs = o[j - 1], (word >> 21) & 0x1F
        if ((lui >> 16) & 0x1F) != rs:      # same register
            continue
        addr = ((lui & 0xFFFF) << 16) + _imm(word)
        out.append(
            f"WRONG EXTERN TYPE (likely): the original materialises the "
            f"address {addr:#010x} with a lui/addiu pair and this build did "
            f"not.\n"
            f"    symbol   {resolve_addr(addr, overlay)}\n"
            f"    meaning  the body names it where an ADDRESS is wanted, but "
            f"its declaration\n"
            f"             makes the bare name evaluate to a VALUE (often 0).\n"
            f"    fix      declare it as an ARRAY so it decays to its own "
            f"address, e.g.\n"
            f"             extern <type> {resolve_addr(addr, overlay)}[];\n"
            f"             and check the callee's parameter type for <type>. "
            f"Do NOT edit the body."
        )
    return out


def find_original(overlay: str) -> Path | None:
    for sub in ("ST", "BOSS", "SERVANT"):
        c = REPO / "disks" / "us" / sub / overlay / f"{overlay}.BIN"
        if c.exists():
            return c
    return None


def self_test() -> int:
    """Replay the real 2026-08-16 failure, word for word.

    func_us_801BBBD0 is matched now, so the live tree can no longer produce
    this diff. A fixture built from the actual instruction words is the only
    thing that keeps the detector honest once the bug it was written for is
    gone -- otherwise the next person to touch diagnose_extern_shape has
    nothing telling them they broke it.
    """
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    print("the wrong-extern-type fingerprint is recognised")
    # Verbatim from BO6:func_us_801BBBD0, offsets +59 and +60:
    #   3c058018  lui   $a1, 0x8018
    #   24a512b8  addiu $a1, $a1, 0x12b8      <- the build dropped THIS
    o = [0] * 62
    o[59] = 0x3C058018
    o[60] = 0x24A512B8
    ev = [("ORIGINAL has an instruction we DROPPED", 60, 0x24A512B8)]
    found = diagnose_extern_shape(o, ev, "BO6")
    ck(len(found) == 1, f"exactly one finding ({len(found)})")
    blob = "\n".join(found)
    ck("0x801812b8" in blob.lower(),
       "the reconstructed address is reported", blob[:120])
    ck("D_us_801812B8" in blob,
       "and it resolves to the symbol name", blob[:200])
    ck("extern" in blob and "[]" in blob,
       "the suggested fix is an ARRAY declaration")
    ck("Do NOT edit the body" in blob,
       "and it says not to touch the body, which is the whole point: the "
       "body was already correct")

    print("\nit does not fire on unrelated drops")
    # An addiu with no lui before it is ordinary arithmetic, not an address.
    o2 = [0] * 10
    o2[4] = 0x24A50001                       # addiu $a1, $a1, 1
    ev2 = [("ORIGINAL has an instruction we DROPPED", 4, 0x24A50001)]
    ck(diagnose_extern_shape(o2, ev2, "BO6") == [],
       "a lone addiu is not an address materialisation")
    # A lui for a DIFFERENT register is a different value being built.
    o3 = [0] * 10
    o3[3] = 0x3C048018                       # lui $a0, 0x8018
    o3[4] = 0x24A512B8                       # addiu $a1, $a1, ...
    ev3 = [("ORIGINAL has an instruction we DROPPED", 4, 0x24A512B8)]
    ck(diagnose_extern_shape(o3, ev3, "BO6") == [],
       "a lui into a different register does not pair")
    ck(diagnose_extern_shape(o, [("instructions DIFFER", 60, 1, 2)],
                             "BO6") == [],
       "only a DROPPED event counts; a plain DIFFER is a different class")

    print("\nimmediates are sign-extended, as addiu reads them")
    ck(_imm(0x0000FFFF) == -1, "0xFFFF is -1")
    ck(_imm(0x00008000) == -0x8000, "0x8000 is the negative boundary")
    ck(_imm(0x00007FFF) == 0x7FFF, "0x7FFF stays positive")
    # %lo of an address above a 0x8000 boundary is emitted negative, and the
    # %hi is pre-incremented to compensate. Getting this wrong misnames the
    # symbol by 0x10000, which would send someone to the wrong declaration.
    o4 = [0] * 10
    o4[4] = 0x3C058019                       # lui $a1, 0x8019
    o4[5] = 0x24A5FF00                       # addiu $a1, $a1, -0x100
    ev4 = [("ORIGINAL has an instruction we DROPPED", 5, 0x24A5FF00)]
    got = diagnose_extern_shape(o4, ev4, "BO6")
    ck(got and "0x8018ff00" in got[0].lower(),
       "a negative %lo resolves below the %hi boundary",
       got[0][:120] if got else "no finding")

    print()
    if fails:
        print(f"{len(fails)} FAILED:")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--overlay", required=False)
    ap.add_argument("--function", required=False)
    ap.add_argument("--window", type=int, default=1200)
    ap.add_argument("--max", type=int, default=12)
    ap.add_argument("--vram", default="0x80180000")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if not a.overlay or not a.function:
        ap.error("--overlay and --function are required (or use --self-test)")

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
    found = diagnose_extern_shape(o, events, a.overlay)
    if found:
        print("=" * 74)
        for f in found:
            print("  " + f)
        print("=" * 74)
        print()
    print("Read an EXTRA in BUILT as: the shared header does something this "
          "stage does not. Read a DROPPED as: this stage does something the "
          "header does not, which is the parameter you need.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
