#!/usr/bin/env python3
"""Self-tests for shim_sweep.py, built around the two bugs it was born with.

Both were real: the first draft reported 86 candidates, of which 74 were noise
of exactly these two kinds. A test that only asserted "returns some hits" would
have passed on the broken version, so every case here asserts a SPECIFIC
inclusion or exclusion.

Run: python3 automation/test_shim_sweep.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shim_sweep as ss  # noqa: E402

FAILS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


def build(tmp: Path, layout: dict[str, str]) -> tuple[dict, dict]:
    """layout maps repo-relative path -> contents; returns (peers, state)."""
    for rel, body in layout.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    ss.REPO = tmp
    headers = ss.shared_headers()
    return ss.build_peer_map(headers, ss.stage_files()), headers


SHIM = '#include "sta.h"\n#include "../e_thing.h"\n'
IMPL = ('#include "stb.h"\n#include "../pad2_anim_debug.h"\n'
        "void EntityThing(Entity* self) { self->step = 1; }\n")
STUB = ('#include "stc.h"\n'
        'INCLUDE_ASM("asm/us/st/stc/nonmatchings/e_thing", EntityThing);\n')
HDR_REAL = "void EntityThing(Entity* self) { self->step = 1; }\n"
HDR_HELPER = "void DebugPad(void) { return; }\n"


def test_finds_a_real_candidate() -> None:
    print("\ntest_finds_a_real_candidate")
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (peers, state), headers = build(tmp, {
            "src/st/e_thing.h": HDR_REAL,
            "src/st/sta/e_thing.c": SHIM,
            "src/st/stc/e_thing.c": STUB,
        })
        check("e_thing" in peers.get("e_thing", {}),
              "a pure two-line shim registers as a peer")
        check(peers["e_thing"]["e_thing"] == ["sta"],
              "the peer is the stage that shims, not the stage that stubs")
        stc = tmp / "src/st/stc/e_thing.c"
        check(state[stc]["stubs"] == 1, "the stub file is counted as having 1 stub")
        check(state[stc]["stub_fns"] == ["EntityThing"],
              "the stubbed function name is extracted")


def test_helper_include_is_not_a_shim() -> None:
    """The pad2_anim_debug bug: a fully-implemented file that includes a small
    helper must not make that helper look like the file's shared implementation."""
    print("\ntest_helper_include_is_not_a_shim")
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (peers, state), headers = build(tmp, {
            "src/st/pad2_anim_debug.h": HDR_HELPER,
            "src/st/e_thing.h": HDR_REAL,
            "src/st/stb/e_thing.c": IMPL,      # implements its own body
            "src/st/stc/e_thing.c": STUB,
        })
        check("pad2_anim_debug" not in peers.get("e_thing", {}),
              "a file with its own function bodies does not vouch for a helper")
        stb = tmp / "src/st/stb/e_thing.c"
        check(state[stb]["own_bodies"] == 1,
              "own_bodies counts the implementing file's real definition")


def test_header_must_define_the_stub() -> None:
    """The decisive filter. A header may be shimmed by many peers and still not
    contain the function we stubbed, in which case including it retires nothing."""
    print("\ntest_header_must_define_the_stub")
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        build(tmp, {"src/st/pad2_anim_debug.h": HDR_HELPER,
                    "src/st/e_thing.h": HDR_REAL})
        helper = ss.defined_functions(HDR_HELPER)
        real = ss.defined_functions(HDR_REAL)
        check("EntityThing" not in helper,
              "the helper header does not define EntityThing")
        check("EntityThing" in real,
              "the real shared header does define EntityThing")
        check(ss.defined_functions("if (x) { y(); }\nwhile (a) { b(); }\n") == set(),
              "control-flow keywords are not mistaken for definitions")
        check("Foo" in ss.defined_functions("static s32 Foo(s32 a) {\n"),
              "a static definition still counts")


def test_partial_shim_file_is_not_a_peer() -> None:
    """A file that both includes the header AND still carries INCLUDE_ASM is a
    half-converted file. It is not evidence that the header suffices."""
    print("\ntest_partial_shim_file_is_not_a_peer")
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (peers, _), _ = build(tmp, {
            "src/st/e_thing.h": HDR_REAL,
            "src/st/sta/e_thing.c":
                '#include "sta.h"\n#include "../e_thing.h"\n'
                'INCLUDE_ASM("asm", EntityOther);\n',
        })
        check(peers.get("e_thing", {}).get("e_thing") in (None, []),
              "a file with both an include and a stub is not counted as a peer")


def test_ports_are_excluded_by_default() -> None:
    print("\ntest_ports_are_excluded_by_default")
    check(bool(ss._PORT.search("rno0_psp")), "rno0_psp is recognised as a port")
    check(bool(ss._PORT.search("rcen_saturn")), "rcen_saturn is recognised")
    check(not ss._PORT.search("rno0"), "rno0 is not a port")
    check(not ss._PORT.search("rno0_pspx"), "a suffix must be terminal")


def test_risk_detection() -> None:
    print("\ntest_risk_detection")
    check("data" in ss.header_risks_text('static u8 tbl[] = {1, 2, 3};\n'),
          "an initialised static array is flagged as data")
    check("bss" in ss.header_risks_text("static s32 g_count;\n"),
          "an uninitialised static is flagged as bss")
    r = ss.header_risks_text("#if defined(STAGE_FOO)\n#endif\n")
    check(any(x.startswith("cond:") for x in r),
          "preprocessor conditionals are counted")
    check(ss.header_risks_text("void F(void) { return; }\n") == [],
          "a header with neither storage nor conditionals is clean")


def main() -> int:
    for fn in (test_finds_a_real_candidate,
               test_helper_include_is_not_a_shim,
               test_header_must_define_the_stub,
               test_partial_shim_file_is_not_a_peer,
               test_ports_are_excluded_by_default,
               test_risk_detection):
        fn()
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
