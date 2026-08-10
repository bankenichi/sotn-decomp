#!/usr/bin/env python3
"""Derive a twin transplant's substitutions from the two .s files.

WHY THIS EXISTS
    The first transplant match needed three things supplied by hand: which
    symbols the destination overlay renames, which constants differ, and
    whether the twin was worth trying at all. A mechanism that needs an
    operator for all three is not a mechanism.

    All three are already written down. func_us_801CC750 and
    func_us_801CC750_from_no0 have 115 instructions in identical order with
    identical registers, and differ in exactly:

        %hi(D_us_80180A88)      vs  %hi(RNO0_EInitSpawner)
        %hi(func_us_801CC8F8)   vs  %hi(func_us_801CC8F8_from_no0)
        ori $t1, $zero, 0xC0    vs  0xE0        \\  the inverted castle
        ori $t0, $zero, 0xE0    vs  0xC0         |  is mirrored, so the
        ori $a1, $zero, 0x91    vs  0x5F         |  sprite's U coords swap
        ori $v1, $zero, 0xC1    vs  0x3F         |  and its Y coords flip
        ori $s3, $zero, 0x8E    vs  0x6A        /

    That is the entire hand-supplied map, minus one entry, recoverable by
    reading two files. No model, no guess.

THE ONE THING THE ASM CANNOT SAY
    E_ID_16 -> E_UNK_16 does not appear in the diff at all, because both enum
    members have the same VALUE. The rename is needed only so the C compiles
    in an overlay whose header does not declare E_ID_16. That is a C-level
    name-availability problem, handled by transplant.auto_decls and by
    matching enum members on value, not something this file can see.

WHAT A DIFFERENCE MEANS
    same length, same mnemonics, differing operands   a clean twin; the
                                                      substitutions below are
                                                      complete
    same length, differing mnemonics                  NOT a twin; the code
                                                      genuinely differs
    different length                                  NOT a twin

    Reporting that honestly is the point. A candidate that is not a twin
    should be said to be not a twin, not forced through a build.

STRICTLY READ-ONLY.

Usage:
    python3 automation/asm_delta.py --pair <twin.s> <target.s>
    python3 automation/asm_delta.py --function func_us_801CC750_from_no0
    python3 automation/asm_delta.py --self-test
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# One instruction line: /* fileoff vaddr word */  mnemonic operands
RX_INSN = re.compile(
    r"^\s*/\*\s*[0-9A-Fa-f]+\s+[0-9A-Fa-f]+\s+[0-9A-Fa-f]+\s*\*/\s*"
    r"(?P<mn>[a-z][a-z0-9.]*)\s*(?P<ops>.*?)\s*$")
# Local labels differ by address between two copies of the same function and
# carry no meaning; they must never become substitutions.
RX_LOCAL_LABEL = re.compile(r"^\.L[A-Za-z0-9_]+$")
RX_SYMREF = re.compile(r"%(?:hi|lo)\(([A-Za-z_]\w*)")
RX_JAL = re.compile(r"^\s*([A-Za-z_]\w*)\s*$")
RX_IMM = re.compile(r"(?<![\w.$])(-?0x[0-9A-Fa-f]+|-?\d+)(?![\w.])")


def instructions(text: str) -> list[tuple[str, str]]:
    """[(mnemonic, operands)] with directives, labels and blanks dropped."""
    out = []
    for line in (text or "").splitlines():
        m = RX_INSN.match(line)
        if m:
            out.append((m.group("mn"), m.group("ops")))
    return out


def delta(twin_asm: str, target_asm: str) -> dict:
    """Substitutions that turn the twin's C into the target's C.

    Returns {"ok", "reason", "symbols", "consts", "insns", "diffs"}.
    """
    a, b = instructions(twin_asm), instructions(target_asm)
    if not a or not b:
        return {"ok": False, "reason": "could not parse instructions",
                "symbols": {}, "consts": {}, "insns": 0, "diffs": 0}
    if len(a) != len(b):
        return {"ok": False,
                "reason": f"different length: {len(a)} vs {len(b)} "
                          f"instructions; not a twin",
                "symbols": {}, "consts": {}, "insns": len(a), "diffs": 0}

    symbols: dict[str, str] = {}
    consts: dict[str, str] = {}
    diffs = 0
    for i, ((mn_a, op_a), (mn_b, op_b)) in enumerate(zip(a, b)):
        if mn_a != mn_b:
            return {"ok": False,
                    "reason": f"instruction {i} differs: {mn_a} vs {mn_b}; "
                              f"the code is not the same, not a twin",
                    "symbols": {}, "consts": {}, "insns": len(a),
                    "diffs": diffs}
        if op_a == op_b:
            continue
        diffs += 1

        sa, sb = RX_SYMREF.findall(op_a), RX_SYMREF.findall(op_b)
        if sa and sb and len(sa) == len(sb):
            for x, y in zip(sa, sb):
                if x != y:
                    symbols[x] = y
            continue
        if mn_a == "jal":
            ja, jb = RX_JAL.match(op_a), RX_JAL.match(op_b)
            if ja and jb and ja.group(1) != jb.group(1):
                symbols[ja.group(1)] = jb.group(1)
                continue

        ia, ib = RX_IMM.findall(op_a), RX_IMM.findall(op_b)
        if ia and ib and len(ia) == len(ib):
            # Branch displacements are encoded as labels in these listings, so
            # an immediate here is a real value. Registers are not matched by
            # RX_IMM because $t1 is excluded by the $ lookbehind.
            for x, y in zip(ia, ib):
                if x != y:
                    consts[x] = y
            continue
        # A difference we cannot classify. Local labels are the benign case.
        if RX_LOCAL_LABEL.match(op_a.split(",")[-1].strip() or "x"):
            continue
    return {"ok": True, "reason": "clean twin", "symbols": symbols,
            "consts": consts, "insns": len(a), "diffs": diffs}


_ASM_INDEX: dict[str, Path] | None = None


def _asm_overlay(p: Path) -> str:
    """`asm/us/st/rno0/nonmatchings/e_x/f.s` -> `st/rno0`.

    The overlay is everything between `asm/us/` and `nonmatchings/`. Split on
    the literal separator rather than counting components, because depth
    varies: `st/rno0`, `boss/bo6`, `ric`.
    """
    s = p.as_posix()
    if "/asm/us/" not in s or "/nonmatchings/" not in s:
        return ""
    return s.split("/asm/us/", 1)[1].split("/nonmatchings/", 1)[0]


def src_overlay(p: str | Path) -> str:
    """`src/st/rno0/e_x.c` -> `st/rno0`. The same key _asm_overlay returns."""
    s = Path(p).as_posix()
    if "src/" not in s:
        return ""
    return "/".join(s.split("src/", 1)[1].split("/")[:-1])


def _find_asm(fn: str, overlay: str = "") -> Path | None:
    """The .s for a function, via an index built ONCE.

    The index is rebuilt at most once per process: the first version rglob'd
    asm/us per call, twice, at 27 seconds a function, and transplant --scan
    calls this for every record.

    KEYED BY NAME, WHICH IS NOT UNIQUE. This stored `setdefault(f.stem, f)`,
    so when one function name has assembly in two overlays the index silently
    kept whichever the walk happened to reach first, and every caller got that
    one with no indication a choice had been made. A delta computed against
    the wrong overlay's function is not an error anyone would notice: it
    returns plausible symbol renames and constant changes for two functions
    that were never related.

    Now every match is kept and the caller must disambiguate:
      - `overlay` given ("st/rno0")  -> that overlay's copy, or None.
      - omitted, one match           -> it.
      - omitted, several             -> None. Refusing is the whole point;
                                        picking one is what this fixes.
    """
    global _ASM_INDEX
    if _ASM_INDEX is None:
        _ASM_INDEX = {}
        root = REPO / "asm" / "us"
        if root.is_dir():
            for f in root.rglob("*.s"):
                # FUNCTIONS ONLY. The walk took every .s under asm/us, which
                # includes the data segments: st_common.data.s exists in 36
                # overlays, sprites.data.s in 27, rooms.data.s in 31. None of
                # them is a function listing and delta() would compare two of
                # them happily. They also drowned the collision report.
                if "/nonmatchings/" not in f.as_posix():
                    continue
                _ASM_INDEX.setdefault(f.stem, []).append(f)
    hits = _ASM_INDEX.get(fn) or []
    if overlay:
        hits = [h for h in hits if _asm_overlay(h) == overlay]
    return hits[0] if len(hits) == 1 else None


def asm_name_collisions() -> dict[str, list[str]]:
    """Function names whose .s exists in more than one overlay. Read-only."""
    _find_asm("")                      # force the index
    return {k: [str(p) for p in v]
            for k, v in sorted((_ASM_INDEX or {}).items()) if len(v) > 1}


def for_function(fn: str, twin_name: str = "", overlay: str = "",
                 twin_overlay: str = "") -> dict:
    """Delta between a queue function and a twin.

    `twin_name` lets a caller nominate a twin found by SIMILARITY rather than
    by the `X_from_Y` naming convention -- asm_twin_finder matches on shape and
    tokens, and most of the tree's twins do not share a name.

    `overlay` / `twin_overlay` ("st/rno0", "boss/bo6") disambiguate when a name
    has assembly in more than one overlay. Pass them whenever you know them;
    src_overlay() derives one from a source path. Without them a colliding
    name resolves to nothing rather than to a guess.

    A NOTE ON WHY THIS OFTEN RETURNS "no twin asm". This derives substitutions
    by DIFFING TWO LISTINGS, so it needs the donor to still have assembly --
    and a donor is a donor precisely because it has already been decompiled,
    which is when its .s disappears. Measured 2026-08-10 on the five twins in
    task #103: only func_us_801D1388_from_are worked, because ARE's copy is
    also still unmatched. For EntityGaibon there is exactly ONE EntityGaibon.s
    in the tree (rchi's own), so target and twin resolve to the same file.
    That is not a defect here; it is the honest answer, and the caller should
    fall back to --map or to the fleet.
    """
    base = twin_name or re.sub(r"_from_\w+$", "", fn)
    tgt = _find_asm(fn, overlay)
    twin = _find_asm(base, twin_overlay)
    if not tgt:
        amb = len((_ASM_INDEX or {}).get(fn) or [])
        why = (f"asm for {fn} exists in {amb} overlays and none was named; "
               f"pass overlay=" if amb > 1 else f"no asm for {fn}")
        return {"ok": False, "reason": why, "symbols": {},
                "consts": {}, "insns": 0, "diffs": 0}
    if not twin or twin == tgt:
        amb = len((_ASM_INDEX or {}).get(base) or [])
        why = (f"twin asm for {base} exists in {amb} overlays and none was "
               f"named; pass twin_overlay=" if amb > 1 and not twin
               else f"no distinct twin asm for {base}")
        return {"ok": False, "reason": why,
                "symbols": {}, "consts": {}, "insns": 0, "diffs": 0}
    d = delta(twin.read_text(errors="ignore"), tgt.read_text(errors="ignore"))
    d["twin_asm"], d["target_asm"] = str(twin), str(tgt)
    return d


def as_maps(d: dict) -> list[str]:
    """The substitutions as OLD=NEW pairs for transplant --map."""
    return ([f"{k}={v}" for k, v in sorted(d.get("symbols", {}).items())]
            + [f"{k}={v}" for k, v in sorted(d.get("consts", {}).items())])


def report(fn: str, overlay: str = "", twin_overlay: str = "") -> int:
    d = for_function(fn, overlay=overlay, twin_overlay=twin_overlay)
    print(f"{fn}")
    print(f"  {d['reason']}  ({d['insns']} instructions, "
          f"{d['diffs']} differing)")
    if not d["ok"]:
        return 1
    print(f"  twin:   {d.get('twin_asm','')}")
    print(f"  target: {d.get('target_asm','')}")
    if d["symbols"]:
        print("\n  symbol renames:")
        for k, v in sorted(d["symbols"].items()):
            print(f"    {k} -> {v}")
    if d["consts"]:
        print("\n  constant changes:")
        for k, v in sorted(d["consts"].items()):
            print(f"    {k} -> {v}")
    pairs = as_maps(d)
    if pairs:
        print("\n  --maps " + "/".join(pairs))
    else:
        print("\n  identical: a straight copy should match")
    return 0


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    twin = (
        "glabel func_a\n"
        "/* 100 80100000 27BDFFD0 */  addiu $sp, $sp, -0x30\n"
        "/* 104 80100004 1880043C */  lui   $a0, %hi(D_us_80180A88)\n"
        "/* 108 80100008 880A8424 */  addiu $a0, $a0, %lo(D_us_80180A88)\n"
        "/* 10C 8010000C 4421070C */  jal   func_us_801C8510\n"
        "/* 110 80100010 C0000934 */  ori   $t1, $zero, 0xC0\n"
        "/* 114 80100014 91000534 */  ori   $a1, $zero, 0x91\n"
        "/* 118 80100018 54004014 */  bnez  $v0, .Lus_801CC8D0\n")
    target = twin.replace("D_us_80180A88", "RNO0_EInitSpawner") \
                 .replace("func_us_801C8510", "InitializeEntity") \
                 .replace("0xC0", "0xE0").replace("0x91", "0x5F") \
                 .replace(".Lus_801CC8D0", ".Lus_801C0A78")

    print("\nthe real substitutions are recovered from the two listings")
    d = delta(twin, target)
    ck(d["ok"], f"a same-shape pair is a clean twin ({d['reason']})")
    ck(d["symbols"].get("D_us_80180A88") == "RNO0_EInitSpawner",
       f"the %hi/%lo symbol rename ({d['symbols']})")
    ck(d["symbols"].get("func_us_801C8510") == "InitializeEntity",
       "the jal target rename")
    ck(d["consts"] == {"0xC0": "0xE0", "0x91": "0x5F"},
       f"the constants, and only the constants ({d['consts']})")

    print("\nlocal labels are NOT mistaken for substitutions")
    # They differ between any two copies of the same function and mean
    # nothing. Emitting `.Lus_801CC8D0=.Lus_801C0A78` would rewrite the C.
    ck(not any(k.startswith(".L") for k in
               {**d["symbols"], **d["consts"]}),
       f"no label appears in the map ({d['symbols']} {d['consts']})")

    print("\nregisters are not read as constants")
    ck("$t1" not in str(d["consts"]) and "1" not in d["consts"],
       f"the $-prefixed register survived ({d['consts']})")

    print("\na pair that is NOT a twin says so instead of guessing")
    shorter = "\n".join(twin.splitlines()[:4])
    ck(not delta(twin, shorter)["ok"], "different instruction counts")
    ck("not a twin" in delta(twin, shorter)["reason"], "and says why")
    swapped = twin.replace("addiu $sp, $sp, -0x30", "subu  $sp, $sp, $v0")
    d2 = delta(twin, swapped)
    ck(not d2["ok"] and "differs" in d2["reason"],
       f"a differing mnemonic is a structural mismatch ({d2['reason']})")

    print("\nan identical pair yields an empty map, not a failure")
    d3 = delta(twin, twin)
    ck(d3["ok"] and not as_maps(d3),
       f"nothing to substitute ({as_maps(d3)})")

    print("\nthe pairs are emitted in transplant's own --maps form")
    ck("D_us_80180A88=RNO0_EInitSpawner" in as_maps(d),
       f"OLD=NEW ({as_maps(d)[:2]})")

    # --- a name is not a unique key for a .s file ----------------------------
    #
    # _ASM_INDEX stored setdefault(f.stem, f): one path per NAME, first one the
    # directory walk reached. Seven function names in this tree have assembly
    # in more than one place, and six of them are live queue records:
    #
    #   EntityShaft      boss/bo6 and st/rcen -- BOTH in `todo`
    #   EntityUnkId1B    st/rcen  and st/rno0 -- BOTH in `todo`
    #   EntityBreakable  st/rchi  and st/rno0 -- rno0's is `deferred`
    #   func_801CE04C  } st/rno0 twice, giantbro_helpers vs unk_4A320,
    #   func_801CE120  } left over from the giantbro split. func_801CE3FC is
    #   func_801CE2CC  } `deferred` with a permuter score and func_801CE2CC
    #   func_801CE3FC  } has a live work dir under nonmatchings/.
    #
    # A delta computed against the wrong overlay's function does not fail. It
    # returns confident symbol renames and constant changes for two functions
    # that were never related, and transplant feeds them straight into --map.
    global _ASM_INDEX
    _saved = _ASM_INDEX
    try:
        a = REPO / "asm/us/st/rno0/nonmatchings/e_x/EntityDup.s"
        b = REPO / "asm/us/st/rchi/nonmatchings/e_x/EntityDup.s"
        c = REPO / "asm/us/st/rcen/nonmatchings/e_y/EntitySolo.s"
        _ASM_INDEX = {"EntityDup": [a, b], "EntitySolo": [c]}

        print("\nan ambiguous name resolves to NOTHING, not to walk order")
        ck(_find_asm("EntityDup") is None,
           "two overlays and no overlay named -> None")
        ck(_find_asm("EntityDup", "st/rno0") == a,
           "naming the overlay picks that one")
        ck(_find_asm("EntityDup", "st/rchi") == b,
           "and the other one, rather than whichever was indexed first")
        ck(_find_asm("EntityDup", "boss/bo6") is None,
           "an overlay that has no copy gets None, not a fallback")
        ck(_find_asm("EntitySolo") == c,
           "an unambiguous name still needs no overlay")

        print("\nand the refusal says what to pass")
        r = for_function("EntityDup", twin_name="EntitySolo")
        ck(not r["ok"] and "2 overlays" in r["reason"],
           f"the target ambiguity is named ({r['reason']})")
        ck("overlay=" in r["reason"], "with the parameter that resolves it")

        print("\noverlay keys derive from both kinds of path")
        ck(_asm_overlay(a) == "st/rno0", f"asm path ({_asm_overlay(a)})")
        ck(src_overlay("src/st/rno0/e_x.c") == "st/rno0",
           f"src path ({src_overlay('src/st/rno0/e_x.c')})")
        ck(src_overlay("src/boss/bo6/us_3E79C.c") == "boss/bo6",
           "a two-level overlay")
        ck(src_overlay("src/ric/319C4.c") == "ric",
           "and a one-level one, since depth varies")
    finally:
        _ASM_INDEX = _saved

    print("\nthe index holds FUNCTIONS, not data segments")
    # It walked every .s under asm/us, so st_common.data.s (36 overlays),
    # sprites.data.s (27) and rooms.data.s (31) were all in it. delta() would
    # have compared two data listings without complaint.
    src_self = Path(__file__).read_text(encoding="utf-8")
    ck('"/nonmatchings/" not in f.as_posix()' in src_self,
       "data segments are skipped when the index is built")
    real = asm_name_collisions()
    ck(not any(".data" in k or ".bss" in k or ".rodata" in k for k in real),
       f"so no data segment appears in the collision report ({list(real)[:3]})")

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
    ap.add_argument("--function")
    ap.add_argument("--overlay", default="",
                    help="disambiguate the TARGET when its name has asm in "
                         "more than one overlay, e.g. st/rno0")
    ap.add_argument("--twin-overlay", default="",
                    help="same, for the twin")
    ap.add_argument("--collisions", action="store_true",
                    help="list every function name whose .s exists in more "
                         "than one overlay. These are the names the index "
                         "used to resolve by walk order")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.collisions:
        c = asm_name_collisions()
        if not c:
            print("no asm filename collisions: every function name is unique "
                  "across overlays in this tree, today.")
            print("The index still keeps all matches and still refuses an "
                  "ambiguous lookup -- the guard is for the tree that exists "
                  "after the next upstream merge, not this one.")
            return 0
        print(f"{len(c)} function name(s) with .s in more than one overlay:\n")
        for k, v in c.items():
            print(f"  {k}")
            for p in v:
                print(f"      {p}")
        return 0
    if a.function:
        return report(a.function, a.overlay, a.twin_overlay)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
