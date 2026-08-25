#!/usr/bin/env python3
"""Do same-file INCLUDE_ASM stubs reach the permuter declared?

WHY THIS EXISTS
    Six BOSS/BO0 records were deferred as `seed-bug`, all six naming one
    symbol:

        UNDECLARED SYMBOL: the seed calls func_us_801B171C without declaring
        it, so the permuter raised KeyError on 316 mutations (8% of
        iterations)

    That is not an import failure and not a compile failure. The seed
    imported and the permuter ran thousands of iterations; it is just that
    3% to 17% of the search died on KeyError, silently, because
    decomp-permuter's typemap has no entry for the identifier.

    include/include_asm.h expands INCLUDE_ASM to NOTHING under PERMUTER, so
    every sibling stub in the seed loses its only mention.

WHAT IS ASSERTED
    That a called stub gets a declaration; that a declaration found in the
    tree is preferred over the synthesised one; that the synthesised form is
    exactly the C89 implicit declaration and nothing more inventive; and that
    the function stays quiet when there is nothing to declare.

    The last one matters most. lookup_declarations() deliberately refuses to
    invent types, because a wrong prototype changes codegen and would send the
    permuter searching a different function than the one that was measured.
    `extern int f();` is the ONE form that is not an invention: C89 6.3.2.2
    says an implicitly declared function behaves as if exactly that had been
    written, and implicit declaration is what the real build already uses.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "win"))
os.environ.setdefault("MODEL_BACKEND", "zen")

import worker_direct as wd  # noqa: E402

FAILS = []


def check(cond, label):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


# The real shape of src/boss/bo0/2D26C.c, reduced: a stub, then a caller.
BO0 = '''#include "bo0.h"

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B171C);

s32 func_us_801B1DDC(Entity* entity, Entity* child) {
    s32 result1 = func_us_801B171C(entity, -0x40, 0x40, 0x60);
    s32 result2 = func_us_801B171C(child, -0x200, 0x280, 0x50);
    return (result1 + result2) == 2;
}
'''
CALLER = BO0[BO0.index("s32 func_us_801B1DDC"):]


def main():
    # Neutralise the repo grep: these cases are about what the function does
    # with a lookup result, not about whether grep works. The real lookup is
    # exercised separately below.
    real_lookup = wd.lookup_declarations
    wd.lookup_declarations = lambda syms, limit=40: []

    print("a called stub with no declaration anywhere gets the implicit form")
    out = wd._declare_stub_siblings(BO0, CALLER)
    check("extern int func_us_801B171C();" in out,
          "emits `extern int func_us_801B171C();`")
    check(out.count("extern int func_us_801B171C();") == 1,
          "exactly once, not once per call site")
    check("6.3.2.2" in out, "and cites why that form is not a guess")

    print("\nseed-only prefixes cannot cross the source-write boundary")
    prefixed = ('#define PLAYER g_Entities[0]\n#define true 1\n'
                'extern EInit g_EInitEnvironment;\n'
                'extern EInit g_EInitEnvironment;\n'
                'void Target(void) { (void)g_EInitEnvironment; }\n')
    rejected = False
    try:
        wd._candidate_function_only(prefixed, "Target")
    except RuntimeError as exc:
        rejected = "file-scope scaffolding" in str(exc)
    check(rejected, "macros and duplicate receipt declarations are rejected")
    exact = 'void Target(void) { (void)g_EInitEnvironment; }\n'
    old_symbol_declaration = wd._symbol_declaration
    wd._symbol_declaration = lambda name, _src: (
        "extern EInit g_EInitEnvironment;"
        if name == "g_EInitEnvironment" else None)
    try:
        prepared = wd._prepare_candidate_body("", exact, "Target", "src/st/test.c")
    finally:
        wd._symbol_declaration = old_symbol_declaration
    check("#define" not in prepared and prepared.count(
        "extern EInit g_EInitEnvironment;") == 1 and "void Target" in prepared,
          "the exact function receives one centrally derived declaration")

    print("\na later declaration is not visible at the replaced stub")
    later = ('#include "test.h"\n'
             'INCLUDE_ASM("st/test/nonmatchings/file", Target);\n'
             'u8 D_us_80180000[] = {1};\n')
    later_body = 'void Target(void) { (void)D_us_80180000[0]; }\n'
    old_symbol_declaration = wd._symbol_declaration
    wd._symbol_declaration = lambda name, _src: (
        "extern u8 D_us_80180000[];" if name == "D_us_80180000" else None)
    try:
        later_prepared = wd._prepare_candidate_body(
            later, later_body, "Target", "src/st/test.c")
    finally:
        wd._symbol_declaration = old_symbol_declaration
    check("extern u8 D_us_80180000[];" in later_prepared,
          "a definition after Target cannot suppress its required extern")

    print("\ntrusted receipt support is normalized at the write boundary")
    supported = wd._prepare_candidate_body(
        'INCLUDE_ASM("st/test/nonmatchings/file", Target);\n',
        'void Target(void) { LaterCall(); }   \n',
        "Target", "src/st/test.c",
        support_declarations=["void LaterCall(void);"])
    check("void LaterCall(void);" in supported
          and supported.index("void LaterCall(void);")
          < supported.index("void Target"),
          "validated score context remains visible before the exact function")
    check(not any(line.endswith(" ") for line in supported.splitlines()),
          "receipt whitespace is normalized before it reaches src/")

    print("\nthe declaration lands after the includes, before the code")
    i_inc = out.index('#include "bo0.h"')
    i_dec = out.index("extern int func_us_801B171C();")
    i_use = out.index("s32 func_us_801B1DDC")
    check(i_inc < i_dec < i_use,
          "ordered include < declaration < first use")
    check(out.index('INCLUDE_ASM("boss/bo0') > i_dec,
          "the stub itself is left untouched below it")
    local_include = ('#include "top.h"\n\nvoid f(void) {\n'
                     '#include "function_local.h"\n'
                     '    MissingCall();\n}\n')
    local_out = wd._declare_stub_siblings(local_include, local_include)
    check(local_out.index("extern int MissingCall();")
          < local_out.index("void f(void)"),
          "a function-local include cannot pull declarations into the body")

    print("\nnothing is invented beyond the implicit declaration")
    added = [l for l in out.splitlines()
             if l not in BO0.splitlines() and l.strip().startswith("extern")]
    check(all(re.fullmatch(r"extern int \w+\(\);", l.strip()) for l in added),
          f"every emitted declaration is `extern int f();` ({added})")
    check(not re.search(r"extern\s+\w+\s+\w+\s*\(\s*(?:Entity|s32|void)\s*\*?",
                        "\n".join(added)),
          "no argument types were guessed")

    print("\na stub that is NOT called is left alone")
    two = BO0.replace(
        'INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B171C);',
        'INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B171C);\n'
        'INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_UNCALLED);')
    out2 = wd._declare_stub_siblings(two, CALLER)
    check("func_us_UNCALLED();" not in out2,
          "an uncalled stub gets no declaration")
    check("extern int func_us_801B171C();" in out2,
          "while the called one still does")

    print("\na file with no stubs is returned byte-identical")
    plain = "#include \"bo0.h\"\n\ns32 f(void) { return 1; }\n"
    check(wd._declare_stub_siblings(plain, plain) == plain, "unchanged")

    print("\na stub the file already prototypes is not re-declared")
    proto = BO0.replace('#include "bo0.h"\n',
                        '#include "bo0.h"\n\ns32 func_us_801B171C(Entity*, s32, s32, s32);\n')
    out3 = wd._declare_stub_siblings(proto, CALLER)
    check("extern int func_us_801B171C();" not in out3,
          "the existing prototype is left as the only declaration")

    print("\nan undeclared call that is NOT a same-file stub is also declared")
    # func_us_801C5AA0 was deferred with "the seed calls GetSideToPlayer
    # without declaring it", 1% of iterations lost to KeyError. It is not an
    # INCLUDE_ASM sibling, so the original fix walked straight past it.
    nonstub = ('#include "rdai.h"\n\n'
               'INCLUDE_ASM("st/rdai/nonmatchings/x", func_other);\n\n'
               's32 f(Entity* e) { return GetSideToPlayer(e); }\n')
    out5 = wd._declare_stub_siblings(nonstub, nonstub)
    check("extern int GetSideToPlayer();" in out5,
          "a called function the file never declares gets the implicit form")

    print("\nbut anything the file DOES account for in C is left alone")
    # NOT a stub: a stub in this file is exactly the case the whole function
    # exists for, and asserting it stays undeclared was my own error, caught
    # by this suite.
    for src_ok, why in (
        ('#include "x.h"\ns32 Known(Entity*);\n'
         's32 f(Entity* e){return Known(e);}\n', "already prototyped"),
        ('#include "x.h"\ns32 Known(Entity* e){return 1;}\n'
         's32 f(Entity* e){return Known(e);}\n', "defined in this file"),
        ('#include "x.h"\nstatic void Known(Entity* e) { (void)e; }\n'
         's32 f(Entity* e){Known(e); return 1;}\n',
         "defined static in this file"),
    ):
        got = wd._declare_stub_siblings(src_ok, src_ok)
        check("extern int Known();" not in got, f"not re-declared: {why}")

    print("\nprose is not code: comments and strings are never scanned")
    # The idempotence check in fix_seed_declarations caught this. The block
    # this module writes contains "C89 implicit declaration (6.3.2.2)", and
    # `declaration(` reads as a call, so a second pass emitted
    # `extern int declaration();` into the seed. Running it once on any
    # commented candidate would have invented externs out of English.
    prose = ('#include "x.h"\n'
             '// see the implicit declaration (6.3.2.2) note\n'
             '/* another mention (here) of wording (again) */\n'
             's32 f(Entity* e) { const char* s = "call_me(1)"; return 0; }\n')
    got_p = wd._declare_stub_siblings(prose, prose)
    for ghost in ("declaration", "here", "again", "call_me"):
        check(f"extern int {ghost}();" not in got_p,
              f"`{ghost}(` in prose is not treated as a call")
    check(got_p == prose, "and the file is returned unchanged")

    print("\nthe stripper keeps offsets and lines intact")
    st = wd._strip_comments_and_strings('a /* x */ b\n// y\nc "z" d\n')
    check(len(st) == len('a /* x */ b\n// y\nc "z" d\n'),
          "length is preserved, so line numbers still line up")
    check(st.count("\n") == 3, "and newlines survive")
    check("x" not in st and "y" not in st and "z" not in st,
          "while the contents are gone")

    print("\nand control flow is never mistaken for a call")
    ctrl = ('#include "x.h"\n'
            's32 f(Entity* e) {\n'
            '    if (e->step) { while (1) { break; } }\n'
            '    switch (e->step) { case 0: break; }\n'
            '    return sizeof(Entity);\n}\n')
    got_c = wd._declare_stub_siblings(ctrl, ctrl)
    for kw in ("if", "while", "switch", "sizeof", "return"):
        check(f"extern int {kw}();" not in got_c,
              f"`{kw}(` is not treated as a call")
    check(got_c == ctrl, "a file needing nothing is returned unchanged")

    print("\na declaration found in the TREE wins over the implicit form")
    wd.lookup_declarations = lambda syms, limit=40: [
        "extern s32 func_us_801B171C(Entity*, s32, s32, s32);"]
    out4 = wd._declare_stub_siblings(BO0, CALLER)
    check("extern s32 func_us_801B171C(Entity*, s32, s32, s32);" in out4,
          "the real declaration is used")
    check("extern int func_us_801B171C();" not in out4,
          "and the implicit form is NOT also emitted")
    check("Declared by the tree" in out4, "labelled as coming from the tree")

    wd.lookup_declarations = real_lookup

    print("\na non-static definition is authoritative declaration evidence")
    derived = wd._repo_declaration(
        "bool StepTowards(s16* val, s32 target, s32 step) { return true; }\n",
        "StepTowards")
    check(derived == "bool StepTowards(s16* val, s32 target, s32 step);",
          f"the exact definition signature becomes a prototype ({derived})")
    hidden = wd._repo_declaration(
        "static bool StepTowards(s16* val, s32 target, s32 step) { return true; }\n",
        "StepTowards")
    check(hidden == "", "a static definition in another file is not exported")

    print("\nmultiline SDK prototypes win over implicit-int fallbacks")
    sdk = wd.lookup_declarations(["RotTransPers4", "LoadTPage"])
    check(any("long RotTransPers4(" in line for line in sdk),
          f"RotTransPers4 multiline prototype found ({sdk})")
    check(any(re.search(r"(?:extern\s+)?u_short\s+LoadTPage\(", line)
              for line in sdk),
          f"LoadTPage typed declaration or definition found ({sdk})")
    sdk_seed = ('#include "rno0.h"\n'
                'static void DrawLaserRing(void) {\n'
                '    RotTransPers4(0, 0, 0, 0, 0, 0, 0, 0, 0);\n'
                '}\n'
                'void f(void) { DrawLaserRing(); LoadTPage(0, 0, 0, 0, 0, 0, 0); }\n')
    sdk_out = wd._declare_stub_siblings(sdk_seed, sdk_seed)
    check("extern int DrawLaserRing();" not in sdk_out,
          "the seed target's static definition is not contradicted")
    check("extern int RotTransPers4();" not in sdk_out,
          "the SDK's RotTransPers4 type is not contradicted")
    check("extern int LoadTPage();" not in sdk_out,
          "the SDK's LoadTPage type is not contradicted")
    check("long RotTransPers4(" in sdk_out,
          "the real multiline RotTransPers4 prototype is copied")
    check(bool(re.search(r"(?:extern\s+)?u_short\s+LoadTPage\(", sdk_out)),
          "the real LoadTPage type is copied from a declaration or definition")

    print("\nglobals are recognised, locals and temporaries are not")
    rx = wd._RX_GLOBALISH
    for good in ("g_EInitCommon", "g_Entities_224", "D_us_80180600"):
        check(bool(rx.search(f"x = {good};")), f"{good} looks global")
    for bad in ("temp_s0", "self", "arg0", "i", "var_v1", "D_x"):
        check(not rx.search(f"x = {bad};"),
              f"{bad} is not mistaken for a global")

    print("\nan overlay path is distinguished from a shared one")
    # _overlay_dir_of, NOT _overlay_of. worker_direct already had an
    # _overlay_of returning the bare name ("no0") for the inverted-overlay
    # twin logic; defining a second one shadowed it and broke twin wiring.
    check(wd._overlay_of("src/st/no0/clock_room.c") == "no0",
          "the pre-existing _overlay_of still answers its own question")
    check(wd._overlay_dir_of("src/st/rchi/e_gaibon.c") == "src/st/rchi",
          "an overlay file maps to its overlay")
    check(wd._overlay_dir_of("src/boss/bo6/richter.c") == "src/boss/bo6",
          "and so does a boss overlay")
    check(wd._overlay_dir_of("src/st/e_fire_warg.h") == "",
          "a shared src/st header belongs to no overlay, so it is borrowable")
    check(wd._overlay_dir_of("include/game.h") == "",
          "and neither does include/")

    print("\nthe declaration is COPIED from the tree, with its real type")
    # Data has no C89 implicit-declaration rule, so guessing `extern int` for
    # an EInit or for `Entity g_Entities_224[]` is wrong in a way the
    # compiler will not always catch where it is used.
    d1 = wd._symbol_declaration("g_EInitCommon", "src/st/rchi/e_breakable.c")
    check(d1.startswith("extern ") and "EInit" in d1,
          f"g_EInitCommon comes back as an EInit ({d1})")
    d2 = wd._symbol_declaration("g_Entities_224", "src/st/rchi/e_slogra.c")
    check("[]" in d2, f"the array keeps its brackets ({d2})")
    check("int " not in d2, "and is not flattened to int")
    d3 = wd._symbol_declaration("g_EInitGorgon", "src/st/rno0/unk_4F968.c")
    check(d3 == "extern EInit g_EInitGorgon;",
          f"a DEFINITION becomes a declaration ({d3})")

    print("\nand a cross-overlay declaration is refused")
    # The EntityGaibonLeg trap: nz0.h is the only `extern g_EInitGaibon` in
    # the tree, and EInit data is overlay-local.
    d4 = wd._symbol_declaration("g_EInitGaibon", "src/st/rchi/e_gaibon.c")
    check("EInit" in d4,
          f"RCHI gets its own definition, not nz0's extern ({d4})")
    d5 = wd._symbol_declaration("g_EInitGorgon", "src/st/rchi/e_gaibon.c")
    check(d5 == "", f"RNO0's symbol is NOT offered to RCHI ({d5})")

    print("\nnothing is injected for a symbol the file already mentions")
    have = ('#include "rchi.h"\nextern EInit g_EInitCommon;\n'
            'INCLUDE_ASM("a/b", Foo);\n')
    check(wd._declare_used_symbols(have, "void f(void){InitializeEntity("
                                         "g_EInitCommon);}",
                                   "src/st/rchi/x.c") == "",
          "an already-declared symbol is left alone")
    check(wd._declare_used_symbols('#include "rchi.h"\n',
                                   "void f(void){ return; }",
                                   "src/st/rchi/x.c") == "",
          "and a candidate using no globals injects nothing")

    print("\nthe injection sits at the STUB, which is always above the body")
    wsrc = open(wd.__file__, encoding="utf-8", errors="replace").read()
    for fname in ("def apply_code(", "def virtual_apply("):
        seg = wsrc[wsrc.index(fname):]
        seg = seg[:seg.index("\ndef ", 10)]
        check("_prepare_candidate_body(" in seg,
              f"{fname.strip('def (')} injects")
        check(seg.index("_prepare_candidate_body") < seg.index("pattern.sub"),
              "before the substitution, so it lands where the stub was")

    print("\nretained assembly resolves raw data without guessing semantics")
    retained = wd.lookup_declarations(
        ["D_us_801812B9"], overlay="BOSS/BO6",
        asm_text="lbu $v0, %lo(D_us_801812B9)($at)")
    check(any(item.startswith("extern u8 D_us_801812B9[];")
              for item in retained),
          f"the target load and retained byte label agree ({retained})")
    alias = wd.lookup_declarations(
        ["D_8007C6E8"], overlay="ST/RCEN",
        asm_text="lhu $v0, %lo(D_8007C6E8)($at)")
    check(any("&g_Entities[200].params" in item for item in alias),
          f"the global address resolves through the Entity layout ({alias})")
    refused = wd.lookup_declarations(
        ["D_us_DEADBEEF"], overlay="BOSS/BO6", asm_text="")
    check(not refused, f"an absent retained label is still refused ({refused})")

    print("\nthe live tree really does not declare func_us_801B171C")
    # This is the premise of the whole fix. If someone later adds a real
    # prototype, this flips and the branch above takes over -- correctly, but
    # the test should say so rather than quietly keep passing.
    try:
        live = wd.lookup_declarations(["func_us_801B171C"])
        check([d for d in live if d.strip()] == [],
              f"grep over src/ and include/ finds nothing ({live})")
    except Exception as e:                      # noqa: BLE001
        print(f"  skip  could not reach the tree to confirm ({e})")

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
