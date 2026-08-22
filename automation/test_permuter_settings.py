#!/usr/bin/env python3
"""Is config/permuter_settings.toml importable by decomp-permuter?

WHY THIS EXISTS
    A bad entry in [preserve_macros] does not fail loudly. import.py emits the
    preserved macros as `<type> <NAME>();` into a block at the TOP of base.c,
    ABOVE the typedef section, then hands the file to pycparser. If the type is
    a project typedef, pycparser meets it before its typedef and the whole
    import dies with a bare:

        Syntax error in base.c.

    which names neither the macro nor the type. Observed 2026-08-03: `s32 FIX();`
    landed at line 6 of BO6_AguneaShuffleParams/base.c while
    `typedef signed int s32;` sat at line 24. Every permuter run on that work dir
    failed instantly, while older work dirs imported before the table existed
    kept working -- so the symptom looked like one broken function rather than a
    broken config.

    Cheap to check here, expensive to diagnose there.

Run: python3 automation/test_permuter_settings.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CFG = REPO / "config" / "permuter_settings.toml"
PERMUTER_SRC = REPO / "tools" / "decomp-permuter" / "src"
FAILS: list[str] = []

# Types pycparser knows without any typedef. Anything outside this set is only
# valid AFTER the typedef block, which is precisely where these declarations
# are not placed.
BUILTIN = {
    "void", "char", "short", "int", "long", "float", "double",
    "signed char", "unsigned char", "signed short", "unsigned short",
    "signed int", "unsigned int", "signed long", "unsigned long",
    "long long", "unsigned long long",
}

# Macros used as assignment targets in this codebase. A preserved macro becomes
# a function call, and `f(x) = 5` is not C, so preserving one of these breaks
# every write. Counts measured over src/**/*.{c,h} on 2026-08-03.
LVALUE_MACROS = {"LOW": 921, "LOH": 253}


def check(cond: bool, label: str, detail: str = "") -> None:
    print(("  ok   " if cond else "  FAIL ") + label
          + ("" if cond else "   " + detail))
    if not cond:
        FAILS.append(label)


def main() -> int:
    try:
        import toml
    except ImportError:
        print("toml not installed; skipping (pip install toml)")
        return 0

    print("\nthe file parses and keeps its non-macro settings")
    try:
        data = toml.load(CFG)
    except Exception as e:                                   # noqa: BLE001
        print(f"  FAIL cannot parse {CFG}: {e}")
        return 1
    check(True, "parses as TOML")
    for key in ("compiler_type", "compiler_command", "assembler_command",
                "asm_prelude_file"):
        check(key in data, f"{key} still present")

    pm = data.get("preserve_macros", {})
    check(bool(pm), "a [preserve_macros] table exists")

    print("\nevery preserved type is a BUILTIN, not a project typedef")
    for name, typ in sorted(pm.items()):
        check(typ in BUILTIN, f"{name} -> {typ!r}",
              f"{typ!r} is a typedef; import.py emits '{typ} {name}();' above "
              f"the typedef block, so pycparser cannot parse it")

    print("\nno macro that is used as an assignment target is preserved")
    for name, writes in sorted(LVALUE_MACROS.items()):
        check(name not in pm, f"{name} is absent",
              f"{name} is written to {writes} times in src/; preserving it "
              f"would emit '{name}(...) = x', which is not valid C")

    print("\nevery key compiles as a regex")
    import re
    for name in pm:
        try:
            re.compile(f"^(?:{name})$")
            check(True, f"{name}")
        except re.error as e:
            check(False, f"{name}", str(e))

    print("\nthe types match what the codebase's typedefs resolve to")
    # Guards against a plausible wrong fix: swapping s32 for "long" would parse
    # but is a different width on some targets and changes how the permuter
    # types the expression.
    expected = {"FIX": "int", "FLT": "int", "ROT": "int", "FLT_TO_I": "int",
                "COLOR16": "unsigned short", "PAL_FLAG": "unsigned short"}
    for name, want in expected.items():
        if name in pm:
            check(pm[name] == want, f"{name} is {want}",
                  f"got {pm[name]!r}; s32 is 'signed int' and u16 is "
                  f"'unsigned short' in include/common.h")

    print("\nbranch targets participate in the permuter score")
    sys.path.insert(0, str(PERMUTER_SRC))
    import objdump
    check(not objdump.ign_branch_targets,
          "branch target normalization is disabled")
    branch_a = objdump.simplify_objdump(
        ["header", "0:\t14400009\tbnez\tv0,28"],
        objdump.MIPS_SETTINGS, stack_differences=True)
    branch_b = objdump.simplify_objdump(
        ["header", "0:\t1440001b\tbnez\tv0,70"],
        objdump.MIPS_SETTINGS, stack_differences=True)
    check(branch_a and branch_b and branch_a[0].row != branch_b[0].row,
          "different local branch destinations remain distinguishable")
    jump_reloc = objdump.process_mips_reloc(
        "R_MIPS_26 .text", "j\t1c8", ".text", "1c8")
    check(jump_reloc == ".text+0x1c8",
          "bare hexadecimal jump relocation addends parse without crashing",
          jump_reloc)

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
