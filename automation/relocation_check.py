#!/usr/bin/env python3
"""Are an overlay's byte differences ONLY a shifted relocation? (ROADMAP P6.1)

WHY THIS EXISTS
    When a build misses, the harness burns four attempts asking a model to
    rewrite C. Sometimes no C change could ever help, because the code is
    already right and only the ADDRESSES it references are wrong: a symbol sits
    at the wrong place, so every `lui`/`addiu` pair that refers to it is off by
    the same constant.

    This was worked out by hand twice. The clearest case: rno0's clock room
    differed from no0's by exactly 0xE4 everywhere, which is RCEN_OPEN (228)
    minus CEN_OPEN (0) -- a castle-flag constant, not a coding mistake. The
    second was a 0x10 TEXT overrun that shifted an entire .bss.

    A single dominant constant across every difference is the signature. It
    says: stop generating C, go fix the symbol address or the constant.

HOW IT DECIDES
    Differences are compared as 4-byte MIPS instructions. A difference is
    "relocation-shaped" when the two words are the SAME instruction (same
    opcode and registers) and differ only in the 16-bit immediate -- which is
    exactly what a `%hi`/`%lo` pair looks like when its target moves.

    Any difference that is not that shape (a different opcode, a different
    register, or a change in a data section) means real code differs, and the
    tool says so rather than guessing.

    It reports a relocation shift only when EVERY difference is
    relocation-shaped AND one delta accounts for at least 80% of them. Partial
    agreement is reported as a mixed result, because acting on a wrong constant
    is worse than acting on nothing.

Usage:
    python3 automation/relocation_check.py                 # every failing overlay
    python3 automation/relocation_check.py --overlay RNO0
    python3 automation/relocation_check.py --self-test
"""
from __future__ import annotations

import argparse
import collections
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# MIPS I opcodes whose low 16 bits are an address immediate. These are the only
# instructions a moved symbol rewrites.
_LUI = 0x0F
_IMM_OPS = {
    _LUI,                                  # lui   (%hi)
    0x09,                                  # addiu (%lo)
    0x08,                                  # addi
    0x0D,                                  # ori
    0x23, 0x21, 0x25, 0x20, 0x24,          # lw lh lhu lb lbu
    0x2B, 0x29, 0x28,                      # sw sh sb
    0x31, 0x39,                            # lwc1 swc1
}

# One delta must dominate this share of the differences to be called the cause.
_DOMINANCE = 0.80


def _words(b: bytes, off: int) -> int:
    return int.from_bytes(b[off:off + 4], "little")


def classify(built: bytes, orig: bytes) -> dict:
    """Compare two overlay images. Pure function, so the self-test is real."""
    if len(built) != len(orig):
        return {"verdict": "size", "detail":
                f"images differ in SIZE: {len(built):#x} vs {len(orig):#x}. "
                f"That is a segment/layout problem, not a relocation one.",
                "diffs": 0, "deltas": {}}

    n = min(len(built), len(orig)) & ~3
    reloc_deltas: list[int] = []
    other = 0
    total = 0
    first_other = None

    for off in range(0, n, 4):
        if built[off:off + 4] == orig[off:off + 4]:
            continue
        total += 1
        a, b = _words(built, off), _words(orig, off)
        op_a, op_b = a >> 26, b >> 26
        # Same instruction, same registers, different immediate?
        if op_a == op_b and op_a in _IMM_OPS and (a >> 16) == (b >> 16):
            imm_a, imm_b = a & 0xFFFF, b & 0xFFFF
            # %hi immediates are scaled by 0x10000; normalise so a lui delta and
            # an addiu delta for the same moved symbol report the same number.
            scale = 0x10000 if op_a == _LUI else 1
            d = ((imm_a - imm_b + 0x8000) % 0x10000 - 0x8000) * scale
            reloc_deltas.append(d)
        else:
            other += 1
            if first_other is None:
                first_other = (off, a, b)

    if total == 0:
        return {"verdict": "identical", "detail": "images are identical",
                "diffs": 0, "deltas": {}}

    counts = collections.Counter(reloc_deltas)
    deltas = dict(counts.most_common(6))

    if other:
        off, a, b = first_other
        return {"verdict": "code", "diffs": total, "deltas": deltas,
                "detail": (
                    f"{other} of {total} differing words are NOT relocation-"
                    f"shaped, so real code differs. First at file offset "
                    f"{off:#x}: built {a:#010x} vs original {b:#010x}. "
                    f"Keep working the C.")}

    top, hits = counts.most_common(1)[0]
    if hits / total < _DOMINANCE:
        return {"verdict": "mixed", "diffs": total, "deltas": deltas,
                "detail": (
                    f"all {total} differences are relocation-shaped but no "
                    f"single delta dominates (top {top:#x} covers {hits}/{total}). "
                    f"Probably several symbols moved. Do not act on one "
                    f"constant.")}

    return {"verdict": "relocation", "diffs": total, "deltas": deltas,
            "detail": (
                f"ALL {total} differences are relocation-shaped and {hits} of "
                f"them share one delta of {top:#x} ({top}). No C change will "
                f"fix this: a symbol or constant is off by exactly that much. "
                f"Check the symbol addresses in config/symbols.us.* and any "
                f"castle-flag constant (RCEN_OPEN - CEN_OPEN = 0xE4).")}


def overlay_pair(name: str) -> tuple[Path, Path]:
    built = REPO / "build" / "us" / f"{name}.BIN"
    stem = name[2:] if name.startswith("F_") else name
    for sub in ("ST", "BOSS", "SERVANT"):
        cand = REPO / "disks" / "us" / sub / stem / f"{name}.BIN"
        if cand.exists():
            return built, cand
    return built, REPO / "disks" / "us" / "ST" / stem / f"{name}.BIN"


def staleness_warning() -> str:
    """Is build/us older than the sources it came from?

    This tool reads BUILD ARTIFACTS, and a worker that fails restores the
    source but leaves the artifact behind. Observed 2026-08-02: after the fleet
    stopped, the tree was clean at git level while build/us/RCEN.BIN still held
    a reverted candidate, and the oracle read 80/81. Diffing that artifact
    would have described a candidate nobody was working on any more.
    """
    newest_src = 0.0
    for root in ("src", "config"):
        for dp, _dn, fns in os.walk(REPO / root):
            # src/<overlay>/gen/ IS BUILD OUTPUT, not source. splat writes the
            # asset headers there (g_GfxEquipIcon.h, g_saveIcon*.h, D_800C*.h)
            # during the build, so counting them made every build produce a
            # tree that was newer than its own artifacts the moment it
            # finished.
            #
            # That is why orphan_check --build could never reach a verdict: it
            # built, then reported "sources are NEWER than build/us" and told
            # the caller to re-run with --build, which is what it had just
            # done. The guard could not close, so the whole --build path was
            # dead and every answer had to be got by hand with verify_build.
            #
            # Pruning the walk rather than filtering after it, so the mtimes
            # are never read at all.
            _dn[:] = [d for d in _dn if d != "gen"]
            for fn in fns:
                if fn.endswith((".c", ".h", ".yaml", ".txt")):
                    try:
                        newest_src = max(newest_src,
                                         os.path.getmtime(os.path.join(dp, fn)))
                    except OSError:
                        pass
    # NEWEST artifact, not oldest. `make build` relinks only what changed, so
    # an overlay nobody has touched keeps an mtime from days ago -- and against
    # the OLDEST bin, any source edited since then trips this warning forever,
    # including immediately after a successful full build.
    #
    # That is what made orphan_check --build unable to reach a verdict: it
    # built, the warning fired anyway, and it told the caller to re-run with
    # --build. The guard could never close, so the verdict path was dead code
    # and every answer had to be got by hand with verify_build.
    #
    # Newest is the build's completion time, and a successful `make build`
    # means make considers every artifact consistent with the sources at that
    # moment. An artifact older than that is one make did not need to touch,
    # which is correctness, not staleness.
    #
    # The case this guard EXISTS for still fires: a worker that restores a
    # source after a failed build leaves that source newer than every artifact,
    # so newest_src > newest_bin and the warning stands.
    newest_bin = None
    bdir = REPO / "build" / "us"
    for p in bdir.glob("*.BIN"):
        try:
            t = p.stat().st_mtime
        except OSError:
            continue
        newest_bin = t if newest_bin is None else max(newest_bin, t)
    if newest_bin is not None and newest_src > newest_bin:
        return ("WARNING: sources are NEWER than build/us. These verdicts "
                "describe a stale binary. Rebuild and re-verify first.")
    return ""


def report(name: str) -> int:
    built, orig = overlay_pair(name)
    if not built.exists() or not orig.exists():
        print(f"{name}: missing image ({'built' if not built.exists() else 'original'})")
        return 2
    r = classify(built.read_bytes(), orig.read_bytes())
    print(f"{name}: {r['verdict'].upper()}")
    print(f"  {r['detail']}")
    if r["deltas"]:
        print("  deltas: " + ", ".join(f"{k:#x} x{v}" for k, v in r["deltas"].items()))
    return 0


def self_test() -> int:
    """Synthetic images. A detector that cannot be shown to discriminate is a
    coin flip with extra steps."""
    ok = True

    def ck(name, cond, extra=""):
        nonlocal ok
        print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else "  " + extra))
        ok = ok and cond

    def ins(op, rs, rt, imm):
        return ((op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)).to_bytes(4, "little")

    # identical
    a = ins(_LUI, 0, 2, 0x8018) * 8
    ck("identical images", classify(a, a)["verdict"] == "identical")

    # a symbol moved by 0xE4: every addiu %lo shifts by the same amount
    orig = b"".join(ins(0x09, 2, 2, 0x1000 + i) for i in range(10))
    built = b"".join(ins(0x09, 2, 2, 0x1000 + i + 0xE4) for i in range(10))
    r = classify(built, orig)
    ck("constant relocation shift is detected", r["verdict"] == "relocation",
       str(r))
    ck("and it reports the right delta", 0xE4 in r["deltas"], str(r["deltas"]))

    # a real code change: different opcode entirely
    built2 = bytearray(orig)
    built2[0:4] = ins(0x23, 2, 2, 0x1000)          # lw instead of addiu
    r2 = classify(bytes(built2), orig)
    ck("a real code difference is NOT called relocation",
       r2["verdict"] == "code", str(r2))

    # same opcode but a different REGISTER is also real code, not a relocation
    built3 = bytearray(orig)
    built3[0:4] = ins(0x09, 3, 2, 0x1000)          # rs changed
    ck("a register change is not a relocation",
       classify(bytes(built3), orig)["verdict"] == "code")

    # relocation-shaped but no dominant delta -> must refuse to name one
    built4 = b"".join(ins(0x09, 2, 2, 0x1000 + i + (i * 7)) for i in range(10))
    ck("scattered deltas are reported as mixed, not acted on",
       classify(built4, orig)["verdict"] == "mixed")

    # one real difference hidden among many relocations must still win
    built5 = bytearray(built)
    built5[8:12] = ins(0x23, 2, 2, 0x1000)
    ck("a single real difference outranks 9 relocations",
       classify(bytes(built5), orig)["verdict"] == "code")

    # differing sizes
    ck("size mismatch is its own verdict",
       classify(a, a + b"\0\0\0\0")["verdict"] == "size")

    # THE STALENESS GUARD MUST BE ABLE TO CLOSE.
    #
    # It compared the newest .h under src/ against the oldest build/us/*.BIN,
    # and the build WRITES src/<overlay>/gen/*.h. So finishing a build made the
    # tree newer than its own artifacts, the warning fired forever, and
    # orphan_check --build built and then told the caller to re-run with
    # --build. The whole verdict path was dead.
    import inspect
    sw = inspect.getsource(staleness_warning)
    ck("generated headers are pruned from the source walk",
       '!= "gen"' in sw or "'gen'" in sw, sw[-300:])
    ck("pruned during os.walk, not filtered afterwards",
       "_dn[:]" in sw, "reading their mtimes at all is the waste")
    # And it is still capable of firing: a source genuinely newer than the
    # artifacts must still be caught, or this fix would have disarmed the guard
    # rather than repaired it.
    ck("it compares against the NEWEST artifact, not the oldest",
       "newest_src > newest_bin" in sw,
       "make relinks only what changed, so the oldest .BIN can be days old "
       "and would condemn every build after it")
    ck("oldest_bin is gone entirely", "oldest_bin" not in sw,
       "leaving both would be two rules for one question")
    # It must still be ABLE to warn, or this repaired the message by disarming
    # the guard. The condition is a live comparison, not a constant.
    ck("source mtimes are still gathered and compared",
       "newest_src" in sw and "getmtime" in sw,
       "a guard that stopped looking would be disarmed, not fixed")

    # lui deltas are scaled so a hi/lo pair agrees on one number
    o = ins(_LUI, 0, 2, 0x8018) + ins(0x09, 2, 2, 0x0000)
    b_ = ins(_LUI, 0, 2, 0x8019) + ins(0x09, 2, 2, 0x0000)
    ck("a lui delta is scaled to a real address delta",
       0x10000 in classify(b_, o)["deltas"], str(classify(b_, o)["deltas"]))

    print()
    print("self-test PASSED" if ok else "self-test FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--overlay", default="")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    warn = staleness_warning()
    if warn:
        print(warn + "\n")
    if a.overlay:
        return report(a.overlay)

    # Default: every overlay in the oracle whose build does not match.
    sha = REPO / "config" / "check.us.sha"
    bad = []
    for ln in sha.read_text().splitlines():
        parts = ln.split()
        if len(parts) != 2:
            continue
        want, path = parts
        p = REPO / path
        if not p.exists():
            continue
        import hashlib
        # casefold BOTH sides. config/check.us.sha is not uniformly lowercase
        # (CHI's line reads 4ea14c8B54B8526e...), and a case-sensitive compare
        # reported CHI as failing while `shasum -c` and verify_build both said
        # it was fine. A hash comparison that disagrees with the oracle is
        # worse than no comparison.
        if hashlib.sha1(p.read_bytes()).hexdigest().lower() != want.lower():
            bad.append(Path(path).stem)
    if not bad:
        print("every overlay matches the oracle; nothing to diff")
        return 0
    print(f"{len(bad)} overlay(s) do not match: {', '.join(bad)}\n")
    for name in bad:
        report(name)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
