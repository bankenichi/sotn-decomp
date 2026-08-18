#!/usr/bin/env python3
"""Progress follows linked C and live stubs, not stale extracted assembly."""
from __future__ import annotations

import tempfile
from pathlib import Path

from progress_table import function_is_undecompiled
from source_index import include_asm_symbols


def main() -> int:
    failures: list[str] = []

    def check(condition: bool, label: str) -> None:
        print(("  ok   " if condition else "  FAIL ") + label)
        if not condition:
            failures.append(label)

    with tempfile.TemporaryDirectory() as raw:
        src = Path(raw)
        (src / "live.c").write_text(
            'INCLUDE_ASM(\n'
            '    "boss/bo6/nonmatchings/us_3E79C", LiveStub);\n'
            '// INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", Commented);\n'
            'const char* text = "INCLUDE_ASM(\\\"fake\\\", Literal)";\n',
            encoding="utf-8",
        )
        live = include_asm_symbols(src)

    key = ("boss/bo6/nonmatchings/us_3E79C", "LiveStub")
    check(key in live, "multiline INCLUDE_ASM is indexed path-first")
    check(
        ("boss/bo6/nonmatchings/us_3E79C", "Commented") not in live,
        "a commented stub is not live evidence",
    )
    check(
        ("fake", "Literal") not in live,
        "an INCLUDE_ASM-looking string is not live evidence",
    )

    check(
        function_is_undecompiled(
            "LiveStub",
            key[0],
            live,
            has_nonmatching_symbol=False,
            whole_file_asm=False,
        ),
        "a live stub remains undecompiled inside a C object",
    )
    check(
        not function_is_undecompiled(
            "LandedFunction",
            key[0],
            live,
            has_nonmatching_symbol=False,
            whole_file_asm=False,
        ),
        "a linked C definition is done even if an extracted .s remains on disk",
    )
    check(
        not function_is_undecompiled(
            "LiveStub",
            "boss/bo4/nonmatchings/us_3E79C",
            live,
            has_nonmatching_symbol=False,
            whole_file_asm=False,
        ),
        "the same symbol in another overlay does not create a false stub",
    )
    check(
        function_is_undecompiled(
            "RawAsm",
            "boss/bo6/nonmatchings/raw",
            live,
            has_nonmatching_symbol=False,
            whole_file_asm=True,
        ),
        "a configured whole-file assembly segment remains undecompiled",
    )
    check(
        function_is_undecompiled(
            "Marked",
            key[0],
            live,
            has_nonmatching_symbol=True,
            whole_file_asm=False,
        ),
        "a map .NON_MATCHING marker remains authoritative",
    )

    if failures:
        print(f"\n{len(failures)} FAILED: {', '.join(failures)}")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
