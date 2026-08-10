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

    print("\nthe declaration lands after the includes, before the code")
    i_inc = out.index('#include "bo0.h"')
    i_dec = out.index("extern int func_us_801B171C();")
    i_use = out.index("s32 func_us_801B1DDC")
    check(i_inc < i_dec < i_use,
          "ordered include < declaration < first use")
    check(out.index('INCLUDE_ASM("boss/bo0') > i_dec,
          "the stub itself is left untouched below it")

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
