#!/usr/bin/env python3
"""The permuter imports one function despite unrelated GNU C extensions."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PERMUTER = REPO / "tools" / "decomp-permuter"
sys.path.insert(0, str(PERMUTER))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> int:
    strip_mod = load("vendored_strip_other_fns", PERMUTER / "strip_other_fns.py")
    importer = load("vendored_permuter_import", PERMUTER / "import.py")
    from src.compiler import Compiler
    from src.error import CandidateConstructionFailure
    from src.scorer import load_symbol_addresses, normalize_symbolic_row

    failures: list[str] = []

    def check(condition: bool, label: str) -> None:
        print(("  ok   " if condition else "  FAIL ") + label)
        if not condition:
            failures.append(label)

    source = r'''
typedef int s32;

static s32 helper(s32 value) {
    const char* braces = "{ not a block }";
    /* } neither is this { */
    return value + 1;
}

void keep_me(
    s32 value
) {
    if (value) {
        value = helper(value);
    }
}

void unrelated(s32 value) {
    static void* const dispatch[] = {
        &&case_0, &&case_1,
    };
    goto *dispatch[value];
case_0:
    return;
case_1:
    return;
}
'''
    stripped = strip_mod.strip_other_fns(source, "keep_me")
    check("void keep_me(" in stripped and "value = helper(value)" in stripped,
          "the selected multiline function body is preserved")
    check("&&case_0" not in stripped and "goto *dispatch" not in stripped,
          "the unrelated computed-goto body is removed before parsing")
    check("return value + 1;" in stripped,
          "a directly called helper remains available for inline codegen")
    check("void unrelated(s32 value);" in stripped,
          "an unrelated function becomes a declaration")

    # import.py receives preprocessed C, so comments have already been removed
    # before prune_source runs. Keep the comment in the strip_other_fns fixture
    # above to exercise brace scanning, but model the real parser boundary here.
    parser_source = source.replace("    /* } neither is this { */\n", "")
    parsed, compilable = importer.prune_source(
        parser_source, True, "keep_me")
    check("void keep_me" in parsed and "&&case_0" not in parsed,
          "import pruning retries with the isolated translation unit")
    check(compilable is not None,
          "a successful parse produces compiler input instead of warnings")

    target_extension = parser_source.replace(
        "value = helper(value);", "goto *&&case_0;")
    try:
        importer.prune_source(target_extension, True, "keep_me")
    except CandidateConstructionFailure:
        rejected = True
    else:
        rejected = False
    check(rejected,
          "an extension inside the selected function is a hard import failure")

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        symbol_map = root / "build" / "us" / "bobo6.map"
        symbol_map.parent.mkdir(parents=True)
        symbol_map.write_text(
            "  0x8003c774 g_api = 0x8003c774\n"
            "  0x8003c7dc g_api_PlaySfx = 0x8003c7dc\n"
            "  0x801d10d0 D_us_801D10D0\n"
            "  0x801d10d2 D_us_801D10D2 = 0x801d10d2\n",
            encoding="utf-8")
        addresses = load_symbol_addresses(str(symbol_map))
        check(normalize_symbolic_row(
                  "%hi(g_api_PlaySfx)", addresses) ==
              normalize_symbolic_row("%hi(g_api+0x68)", addresses),
              "equivalent API relocation spellings share one score identity")
        check(normalize_symbolic_row(
                  "%lo(D_us_801D10D2)", addresses) ==
              normalize_symbolic_row("%lo(D_us_801D10D0+2)", addresses),
              "an interior data label equals its base-plus-offset spelling")

        asm = root / "asm" / "us" / "boss" / "bo6" / "target.s"
        asm.parent.mkdir(parents=True)
        asm.write_text("glabel target\n", encoding="utf-8")
        config = root / "config" / "splat.us.bobo6.yaml"
        config.parent.mkdir(parents=True)
        config.write_text(
            "options:\n"
            "  basename: bobo6\n"
            "  build_path: build/us\n"
            "  asm_path: asm/us/boss/bo6\n",
            encoding="utf-8")
        found = importer.find_symbol_map(str(root), str(asm))
        check(found == str(symbol_map.resolve()),
              "the importer selects the link map from the asm path")
        settings = root / "settings.toml"
        importer.create_write_settings_toml(
            "target", "gcc", str(settings), "../../build/us/bobo6.map")
        check('symbol_map = "../../build/us/bobo6.map"' in
              settings.read_text(encoding="utf-8"),
              "the imported work directory records its score symbol map")

        lying_compiler = root / "lying-compiler.py"
        lying_compiler.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "pathlib.Path(sys.argv[3]).write_bytes(b'invalid object')\n"
            "print(\"input.c:1: `missing_symbol' undeclared\", file=sys.stderr)\n",
            encoding="utf-8")
        os.chmod(lying_compiler, 0o755)
        compiled = Compiler(
            str(lying_compiler), show_errors=False, debug_mode=False
        ).compile("void target(void) {}")
        check(compiled is None,
              "compiler diagnostics reject an object even when the wrapper exits zero")

        silent_compiler = root / "silent-compiler.py"
        silent_compiler.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "pathlib.Path(sys.argv[3]).write_bytes(b'valid object')\n",
            encoding="utf-8")
        os.chmod(silent_compiler, 0o755)
        compiled = Compiler(
            str(silent_compiler), show_errors=False, debug_mode=False
        ).compile("void target(void) {}")
        check(compiled is not None and Path(compiled).read_bytes() == b"valid object",
              "a silent zero-exit compile still returns its fresh object")
        if compiled is not None:
            Path(compiled).unlink()

    if failures:
        print(f"\n{len(failures)} FAILED: {', '.join(failures)}")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
