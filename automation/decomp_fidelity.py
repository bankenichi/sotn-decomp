#!/usr/bin/env python3
"""Is this C a decompilation of THIS function, or just clean-looking C?

WHY THIS EXISTS
    Every metric in quality_ab.py is NEGATIVE: invented field names, runaway
    declaration loops, ILLEGAL variants, raw offsets. They count ways the
    output is wrong. None of them can tell the difference between

        a faithful decompilation of the target function, and
        a plausible, well-formed C function about something else entirely

    Both score zero defects. Ranking models on defect counts therefore ranks
    them on tidiness, not on decompilation ability, and the model that writes
    the most cautious generic code wins. That is the wrong winner.

    Worse, quality_ab's own docstring claimed a compile check ("does psx cc
    accept it at all", "the compile check uses a throwaway copy in /tmp") that
    was never implemented. So nothing had ever verified the output positively.

WHAT THIS MEASURES
    The assembly states facts the C must reproduce. Three of them survive
    compilation unambiguously and can be checked without a toolchain:

      callees    every `jal SYMBOL` is a function the C must call. This is the
                 strongest signal available: a model writing generic slop will
                 not invent the name BO6_RicCreateEntFactoryFromEntity.
      constants  distinctive immediates (0x3FFF, 0x28000000) are load-bearing
                 values that must appear literally.
      branching  the count of conditional branches bounds how much control
                 flow the C needs. Not exact (the compiler reorders and the
                 same `if` can emit several branches), so it is reported as a
                 ratio and never used as a pass/fail.

    Recall is what matters, and precision is reported beside it: a function
    that calls something the assembly never calls is fabricating just as surely
    as one that invents a field name.

NOT A MATCH ORACLE
    A perfect fidelity score does not mean the function matches. Only the build
    and the SHA-1s in config/check.us.sha decide that. This measures whether a
    generation is worth spending a build cycle on, which is the question when
    choosing a model.

STRICTLY READ-ONLY. Never writes to src/, never builds, never touches the
queue.

Usage:
    python3 automation/decomp_fidelity.py --rescore      # the whole battery
    python3 automation/decomp_fidelity.py --rescore --by-function
    python3 automation/decomp_fidelity.py --self-test
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BATTERY_JSONL = REPO / "automation" / "logs" / "quality-battery.jsonl"

RX_JAL = re.compile(r"\bjal\s+([A-Za-z_]\w*)")
# Calls through a pointer do not appear as `jal NAME`. The address is loaded
# with %hi/%lo and invoked with jalr, so the callee is only visible as a
# relocation. BO6_RicSetSlideKick calls g_api_PlaySfx exactly this way, and the
# first version of this file scored three models as FABRICATING it while they
# were in fact correct.
RX_RELOC = re.compile(r"%(?:hi|lo)\(([A-Za-z_]\w*)\)")
RX_C_CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
# A DEFINITION looks exactly like a call to the regex above. Counting it as one
# makes every generation appear to call a function the assembly never calls,
# i.e. it manufactures a fabrication for every single output. Definitions and
# prototypes are therefore removed from the call set.
RX_C_DEF = re.compile(r"\b([A-Za-z_]\w*)\s*\([^;{)]*\)\s*\{")
# A prototype must have a RETURN TYPE before the name. Without that
# requirement the pattern also matches an ordinary call statement, because
# `rand();` likewise ends in `);` -- which silently emptied the call set and
# made every model look like it called nothing at all.
RX_C_PROTO = re.compile(
    r"^[ \t]*(?:extern[ \t]+|static[ \t]+)?[A-Za-z_]\w*[\s*]+"
    r"([A-Za-z_]\w*)\s*\([^;{]*\)\s*;", re.M)
RX_BRANCH = re.compile(r"\b(?:beq|bne|blez|bgtz|bltz|bgez|beqz|bnez|bc1[tf])\b")
RX_C_CTRL = re.compile(r"\b(?:if|while|for|case|\?)\b|\?")
RX_FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*$", re.M)
RX_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)

# Immediates worth checking. Small values (0, 1, 2, 4, 8...) appear in any C
# for structural reasons -- array indices, increments, field sizes -- so their
# presence proves nothing. Values at or above this threshold are specific to
# the function being decompiled.
MIN_CONST = 0x40

# Keywords and builtins that look like calls to the regex but are not, and
# would otherwise be scored as fabricated callees.
NOT_CALLS = frozenset({
    "if", "while", "for", "switch", "return", "sizeof", "case", "do", "else",
    "defined", "static", "void", "int", "char", "short", "long", "unsigned",
    "signed", "float", "double", "struct", "union", "enum", "typedef",
    "const", "volatile", "extern", "u8", "s8", "u16", "s16", "u32", "s32",
    "f32", "Entity", "Primitive",
})



# Instructions whose numeric operand is a VALUE the C must contain.
# Masks and comparisons: the immediate is a value whatever the source register.
RX_IMM = re.compile(
    r"\b(andi|xori|slti|sltiu|li)\s+"
    r"\$\w+,\s*(?:\$\w+,\s*)?(-?(?:0x[0-9A-Fa-f]+|\d+))\b")
# `addiu`/`ori` are a literal load ONLY from $zero. From any other register
# they are address arithmetic: `addiu $a0, $s0, 0xbc` is `&self->field_BC`,
# an offset the C should resolve to a field name, not reproduce as a number.
RX_IMM_ZERO = re.compile(
    r"\b(addiu|addi|ori)\s+\$\w+,\s*\$zero,\s*"
    r"(-?(?:0x[0-9A-Fa-f]+|\d+))\b")
# The prologue's frame size is chosen by the compiler and never appears in the
# source. `addiu $sp, $sp, -0x48` made -0x48 the joint most-"missed" value.
RX_SP = re.compile(r"\$sp\s*,")
# `lui` carries the TOP HALF of a 32-bit constant. The C writes the whole
# value, so the halves must be recombined or every one of them reads as a miss.
RX_LUI = re.compile(r"\blui\s+\$(\w+),\s*(0x[0-9A-Fa-f]+|\d+)\b")
# A load/store displacement is a STRUCT FIELD OFFSET, not a value. The correct
# C writes `self->unk50`, not `0x50`.
RX_MEMOFF = re.compile(
    r"\b(?:lw|lh|lhu|lb|lbu|sw|sh|sb|lwc1|swc1|ldc1|sdc1)\s+"
    r"\$?\w+,\s*(-?(?:0x[0-9A-Fa-f]+|\d+))\s*\(")


def _num(tok: str) -> int:
    neg = tok.startswith("-")
    tok = tok.lstrip("-")
    v = int(tok, 16) if tok.lower().startswith("0x") else int(tok)
    return -v if neg else v


def _immediates(asm_text: str) -> set[int]:
    """Values the C must contain literally.

    THE FIRST VERSION OF THIS WAS WRONG, and its error pointed the wrong way.
    It scraped every `0x...` in the file, which swept up the displacement in
    `lw $v0, 0x50($s0)`. That displacement is a STRUCT FIELD OFFSET: the
    correct C writes `self->unk50`, so the scorer was marking a model DOWN for
    resolving offsets to fields, which is the single behaviour the whole
    harness is built to encourage. It also missed `lui $v0, 0x2800` +
    implicit low half, so a correct `0x28000000` read as a miss.

    Together those two errors produced "constant recall is 0.10 to 0.60 across
    all models", which was an artefact, not a finding.
    """
    consts = set()
    for rx in (RX_IMM, RX_IMM_ZERO):
        for m in rx.finditer(asm_text):
            if RX_SP.search(m.group(0)):
                continue
            v = _num(m.group(2))
            if abs(v) >= MIN_CONST:
                consts.add(v)
    for m in RX_LUI.finditer(asm_text):
        v = _num(m.group(2)) << 16
        if v >= MIN_CONST:
            consts.add(v)
    return consts


def strip_fences(code: str) -> str:
    """Models wrap output in markdown fences; they are not part of the C."""
    return RX_FENCE.sub("", code or "")


def asm_facts(asm_text: str) -> dict:
    """What the assembly says the C must contain."""
    callees = set(RX_JAL.findall(asm_text or ""))
    # Relocated symbols may be data or function pointers; we cannot tell which
    # from the assembly alone. So they never count as REQUIRED calls, only as
    # permitted ones, which keeps recall honest and stops precision lying.
    reloc = set(RX_RELOC.findall(asm_text or ""))
    consts = _immediates(asm_text or "")
    return {"callees": callees, "reloc": reloc, "consts": consts,
            "branches": len(RX_BRANCH.findall(asm_text or ""))}


def c_facts(code: str) -> dict:
    """Calls and constants in the CODE, excluding commentary and declarations.

    Two corrections, both of which had inverted real results:

    1. Comments are stripped first. `ling-3.0-flash-free` was credited with
       calling `hi`, `lo` and `entity` purely from prose in a header comment.
    2. Prototypes are removed as TEXT rather than by name. Subtracting declared
       names from the call set deleted the genuine calls too, so
       `nemotron-3-ultra-free`, which correctly declares `extern s32 rand(void);`
       and then calls `rand()`, scored 0.00 callee recall on a faithful
       generation. Declaring a function and calling it is ordinary C.
    """
    code = RX_COMMENT.sub(" ", strip_fences(code))
    defined = set(RX_C_DEF.findall(code)) | set(RX_C_PROTO.findall(code))
    # Blank the prototype lines and the definition headers, keeping bodies.
    body = RX_C_PROTO.sub(" ", code)
    body = RX_C_DEF.sub("{", body)
    calls = {n for n in RX_C_CALL.findall(body) if n not in NOT_CALLS}
    consts = set()
    for m in re.finditer(r"0x([0-9A-Fa-f]+)\b", code):
        consts.add(int(m.group(1), 16))
    for m in re.finditer(r"(?<![\w.])(\d{2,})(?![\w.])", code):
        consts.add(int(m.group(1)))
    return {"calls": calls, "defined": defined, "consts": consts,
            "ctrl": len(RX_C_CTRL.findall(code))}


def fidelity(code: str, asm_text: str, func_name: str = "") -> dict:
    """How much of what the assembly requires does this C actually contain?"""
    a = asm_facts(asm_text)
    c = c_facts(code)
    # The function may legitimately call itself, and its own definition looks
    # like a call to the regex, so exclude its own name from both sides.
    own = {func_name} if func_name else set()
    want_calls = a["callees"] - own
    got_calls = c["calls"] - own

    hit = want_calls & got_calls
    extra = got_calls - a["callees"] - a["reloc"] - own
    recall = len(hit) / len(want_calls) if want_calls else None
    justified = got_calls - extra
    prec = len(justified) / len(got_calls) if got_calls else None

    want_c = a["consts"]
    const_hit = want_c & c["consts"]
    const_recall = len(const_hit) / len(want_c) if want_c else None

    ratio = (c["ctrl"] / a["branches"]) if a["branches"] else None
    return {
        "callees_want": len(want_calls),
        "callees_hit": len(hit),
        "callee_recall": None if recall is None else round(recall, 3),
        "callee_precision": None if prec is None else round(prec, 3),
        "callees_missed": sorted(want_calls - got_calls)[:6],
        "callees_fabricated": sorted(extra)[:6],
        "const_recall": None if const_recall is None else round(const_recall, 3),
        "ctrl_ratio": None if ratio is None else round(ratio, 2),
    }


# ---------------------------------------------------------------- rescoring

def _rows(path: Path) -> list[dict]:
    out = []
    if not path.is_file():
        return out
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip("\x00").strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _asm_index() -> dict:
    """function stem -> .s path, taken from the battery's own list."""
    sys.path.insert(0, str(REPO / "automation"))
    import quality_ab as qa                                   # type: ignore
    return {Path(a).stem: REPO / a for a in qa.BATTERY_ASM}


def rescore(config: str = "none", by_function: bool = False) -> int:
    sys.path.insert(0, str(REPO / "automation"))
    import quality_ab as qa                                   # type: ignore
    idx = _asm_index()
    rows = [r for r in _rows(BATTERY_JSONL) if r.get("config") == config]
    if not rows:
        print(f"no rows for config={config}")
        return 1

    scored = []
    for r in rows:
        code = r.get("code") or ""
        asm = idx.get(r.get("function", ""))
        if not code.strip() or r.get("error") or not asm or not asm.is_file():
            continue
        if qa.degenerate(code)["degenerate"]:
            continue                       # a loop has no fidelity to measure
        f = fidelity(code, asm.read_text(errors="ignore"), r["function"])
        if f["callee_recall"] is None:
            continue                       # nothing to be faithful to
        scored.append({**r, **f})

    if by_function:
        print(f"\nCALLEE RECALL BY FUNCTION (config={config})")
        print(f"{'function':28}{'asm':>7}{'callees':>9}{'n':>4}"
              f"{'recall':>9}{'best model':>26}")
        print("-" * 83)
        g = collections.defaultdict(list)
        for s in scored:
            g[s["function"]].append(s)
        for fn, ss in sorted(g.items(), key=lambda kv: kv[1][0]["asm_chars"]):
            avg = sum(s["callee_recall"] for s in ss) / len(ss)
            best = max(ss, key=lambda s: s["callee_recall"])
            print(f"{fn:28}{ss[0]['asm_chars']:>7}{ss[0]['callees_want']:>9}"
                  f"{len(ss):>4}{avg:>9.2f}"
                  f"{best['model'][:24]:>26}")
        return 0

    print(f"\nDECOMPILATION FIDELITY, config={config}")
    print("Scored on usable generations only; loops and errors excluded.\n")
    print(f"{'model':26}{'n':>4}{'recall':>8}{'prec':>7}"
          f"{'const':>7}{'ctrl':>7}")
    print("-" * 59)
    g = collections.defaultdict(list)
    for s in scored:
        g[s["model"]].append(s)
    ranked = []
    for m, ss in g.items():
        rec = sum(s["callee_recall"] for s in ss) / len(ss)
        pr = [s["callee_precision"] for s in ss
              if s["callee_precision"] is not None]
        cr = [s["const_recall"] for s in ss if s["const_recall"] is not None]
        ct = [s["ctrl_ratio"] for s in ss if s["ctrl_ratio"] is not None]
        ranked.append((rec, m, len(ss),
                       sum(pr) / len(pr) if pr else float("nan"),
                       sum(cr) / len(cr) if cr else float("nan"),
                       sum(ct) / len(ct) if ct else float("nan")))
    for rec, m, n, pr, cr, ct in sorted(ranked, reverse=True):
        print(f"{m:26}{n:>4}{rec:>8.2f}{pr:>7.2f}{cr:>7.2f}{ct:>7.2f}")

    print("\nrecall  fraction of `jal` targets the C actually calls")
    print("prec    fraction of the C's calls that the assembly justifies")
    print("const   fraction of distinctive immediates (>=0x40) reproduced")
    print("ctrl    C control-flow constructs per asm branch; ~1 is plausible,")
    print("        far below 1 means flow was dropped, far above means padding")

    worst = sorted(scored, key=lambda s: s["callee_recall"])[:5]
    print("\nlowest-fidelity generations, with what they missed")
    for s in worst:
        print(f"  {s['callee_recall']:.2f}  {s['model'][:22]:24}"
              f"{s['function'][:24]:26} missed={s['callees_missed'][:3]}")
    fab = [s for s in scored if s["callees_fabricated"]]
    if fab:
        print(f"\n{len(fab)}/{len(scored)} generations call functions the "
              f"assembly never calls, e.g.")
        for s in fab[:4]:
            print(f"  {s['model'][:22]:24}{s['function'][:22]:24}"
                  f"{s['callees_fabricated'][:3]}")
    return 0


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    asm = (
        "glabel func_us_801BD384\n"
        "/* 3D384 801BD384 27BDFFE0 */  addiu $sp, $sp, -0x20\n"
        "/* 3D390 801BD390 0C0123AB */  jal   rand\n"
        "/* 3D394 801BD394 30423FFF */  andi  $v0, $v0, 0x3FFF\n"
        "/* 3D398 801BD398 0C0456CD */  jal   DestroyEntity\n"
        "/* 3D39C 801BD39C 14400005 */  bne   $v0, $zero, .L801BD3B0\n"
        "/* 3D3A0 801BD3A0 10000003 */  beq   $zero, $zero, .L801BD3C0\n")

    print("\nthe assembly's demands are extracted, addresses are not constants")
    a = asm_facts(asm)
    ck(a["callees"] == {"rand", "DestroyEntity"}, f"jal targets ({a['callees']})")
    ck(0x3FFF in a["consts"], "a real immediate is kept")
    # 801BD384 is an address in the listing column, not a value the C needs.
    ck(0x801BD384 not in a["consts"], "an 8-digit address is NOT a constant")
    ck(a["branches"] == 2, f"branches counted ({a['branches']})")

    print("\na load/store displacement is a field offset, not a constant")
    mem = ("/* 1 8010 8FA20050 */  lw   $v0, 0x50($s0)\n"
           "/* 2 8014 34423FFF */  andi $v0, $v0, 0x3FFF\n"
           "/* 3 8018 3C022800 */  lui  $v0, 0x2800\n")
    im = asm_facts(mem)["consts"]
    ck(0x50 not in im, f"0x50 is an offset, excluded ({sorted(map(hex,im))})")
    ck(0x3FFF in im, "0x3FFF is a real immediate")
    ck(0x28000000 in im,
       f"lui is recombined to the full word ({sorted(map(hex,im))})")

    print("\nframe size and address arithmetic are not constants")
    noise = ("/* 1 8000 27BDFFB8 */  addiu $sp, $sp, -0x48\n"
             "/* 2 8004 26040BC0 */  addiu $a0, $s0, 0xbc\n"
             "/* 3 8008 24020064 */  addiu $v0, $zero, 0x64\n")
    nz = asm_facts(noise)["consts"]
    ck(-0x48 not in nz, f"the frame size is excluded ({sorted(map(hex,nz))})")
    ck(0xbc not in nz, "address arithmetic off a struct pointer is excluded")
    ck(0x64 in nz, f"but a literal load from $zero is kept ({sorted(nz)})")

    print("\na faithful generation scores high")
    good = ("```c\nvoid func_us_801BD384(Entity* self) {\n"
            "    s32 t = rand();\n"
            "    if ((t & 0x3FFF) != 0) { DestroyEntity(self); }\n}\n```")
    f = fidelity(good, asm, "func_us_801BD384")
    ck(f["callee_recall"] == 1.0, f"all callees present ({f['callee_recall']})")
    ck(f["callee_precision"] == 1.0, f"no fabricated calls ({f['callees_fabricated']})")
    ck(f["const_recall"] == 1.0, f"the immediate is reproduced ({f['const_recall']})")

    print("\nclean C about the WRONG function scores low, though it has "
          "zero defects")
    slop = ("void func_us_801BD384(Entity* self) {\n"
            "    self->posX.val += self->velocityX;\n"
            "    UpdateAnim(self, 0, 0);\n}\n")
    f2 = fidelity(slop, asm, "func_us_801BD384")
    ck(f2["callee_recall"] == 0.0, f"calls none of them ({f2['callee_recall']})")
    ck(f2["callees_fabricated"] == ["UpdateAnim"],
       f"and its invented call is named ({f2['callees_fabricated']})")
    # The whole point: quality_ab rates this output perfectly.
    sys.path.insert(0, str(REPO / "automation"))
    import quality_ab as qa                                   # type: ignore
    sc = qa.score(slop)
    ck(sc["invented_fields"] == 0 and not sc["degenerate"],
       "quality_ab sees NO defect in it, which is why fidelity is needed")

    print("\nan indirect call via %hi/%lo is justified, not fabricated")
    ind = (asm
           + "/* 3D3A4 801BD3A4 3C048018 */  lui $a0, %hi(g_api_PlaySfx)\n"
             "/* 3D3A8 801BD3A8 0080F809 */  jalr $ra, $t9\n")
    fi = fidelity("void f(void) { rand(); DestroyEntity(0); "
                  "g_api_PlaySfx(1); }", ind)
    ck(fi["callees_fabricated"] == [],
       f"g_api_PlaySfx accepted ({fi['callees_fabricated']})")
    ck(fi["callee_precision"] == 1.0,
       f"and precision is not punished ({fi['callee_precision']})")
    ck(fidelity("void f(void){ rand(); DestroyEntity(0); Bogus(); }",
                ind)["callees_fabricated"] == ["Bogus"],
       "while a genuinely invented call is still caught")

    print("\nself-recursion is not counted as a fabricated call")
    rec = ("void func_us_801BD384(Entity* self) { rand(); DestroyEntity(self);"
           " func_us_801BD384(self); }")
    f3 = fidelity(rec, asm, "func_us_801BD384")
    ck(f3["callees_fabricated"] == [],
       f"own name excluded ({f3['callees_fabricated']})")

    print("\na function's own definition is not one of its calls")
    d = c_facts("void my_helper(Entity* e) {\n    rand();\n}\n")
    ck(d["calls"] == {"rand"}, f"only the real call ({sorted(d['calls'])})")
    ck("my_helper" in d["defined"], "the definition is recorded separately")
    # A prototype that is never invoked contributes no call. One that IS
    # invoked contributes exactly one, from the invocation.
    unused = c_facts("void fwd(s32 a);\nvoid g(void) { rand(); }\n")
    ck("fwd" not in unused["calls"],
       f"an unused prototype is not a call ({sorted(unused['calls'])})")
    used = c_facts("void fwd(s32 a);\nvoid g(void) { fwd(1); rand(); }\n")
    ck(used["calls"] == {"fwd", "rand"},
       f"a declared-then-called function counts once ({sorted(used['calls'])})")

    print("\ndeclaring a function and then calling it counts as a call")
    decl = ("extern s32 rand(void);\nextern void DestroyEntity(Entity*);\n"
            "void f(Entity* e) {\n    s32 v = rand();\n"
            "    DestroyEntity(e);\n}\n")
    fd = fidelity(decl, asm, "f")
    ck(fd["callee_recall"] == 1.0,
       f"both callees credited despite the externs ({fd['callee_recall']})")

    print("\nprose in comments is not code")
    cm = ("/* loads %hi(g_Foo) into entity, then lo(x) */\n"
          "void f(Entity* e) { rand(); }\n")
    ck(c_facts(cm)["calls"] == {"rand"},
       f"only the real call survives ({sorted(c_facts(cm)['calls'])})")

    print("\nkeywords are not mistaken for calls")
    kw = ("void f(Entity* e) { if (e->step) { while (1) { rand(); } } "
          "return; }")
    ck("if" not in c_facts(kw)["calls"] and "while" not in c_facts(kw)["calls"],
       f"if/while/return filtered ({sorted(c_facts(kw)['calls'])})")

    print("\nan asm with no calls yields no recall rather than a fake 0.0")
    f4 = fidelity("void f(void) {}", "addiu $sp, $sp, -0x20\n")
    ck(f4["callee_recall"] is None, f"None, not 0.0 ({f4['callee_recall']})")

    print()
    if fails:
        print(f"{len(fails)} FAILED:")
        for x in fails:
            print("  - " + x)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rescore", action="store_true")
    ap.add_argument("--config", default="none")
    ap.add_argument("--by-function", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.rescore:
        return rescore(a.config, a.by_function)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
