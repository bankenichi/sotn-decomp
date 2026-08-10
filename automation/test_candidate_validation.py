#!/usr/bin/env python3
"""Is corrupted model output stopped before it reaches a build?

WHY THIS EXISTS
    Three records in the live escalated queue on 2026-08-10 were not
    decompilation failures. They were corrupted output that nothing checked:

      us:ST/RNO0:func_us_8019FD4C_from_rcen
        BUILD FAILED: earch_text<arg_key>pattern</arg_key><arg_value>
        func_us_8019FD4C</arg_value></tool_call> ... malformatted chara

        Raw tool-call markup written into a .c file in src/.

      us:BOSS/BO6:BO6_RicStepSlide
        BUILD FAILED: richter.c:232: stray '\\' in program (x4)

      us:ST/RNO0:func_us_801CF24C
        BUILD FAILED: undefined reference to `sw'

        A MIPS store instruction emitted as a C call. It got past the
        compiler and was caught by the LINKER.

    Each cost a full build to discover, then sat in `escalated` looking like
    a hard function among genuinely hard functions. The check is cheap and
    the class is preventable.

WHAT IS DELIBERATELY NOT CHECKED
    Anything ambiguous. A false positive here discards a real candidate, so
    the stray-backslash case is left out: a backslash is legal in string
    escapes and in macro line continuations, and no cheap rule separates the
    bad ones without risking good C.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "win"))
os.environ.setdefault("MODEL_BACKEND", "zen")

import worker_direct as wd  # noqa: E402

FAILS = []


def check(cond, label):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


GOOD = """s32 func_us_801B1DDC(Entity* entity) {
    s32 n;
    n = 0;
    if (entity->step == 0) {
        n = 1;  // a { brace } in a comment
    }
    return n;
}
"""


def main():
    print("real C passes")
    check(wd.validate_candidate(GOOD) == "", "a normal candidate is accepted")
    check(wd.validate_candidate(
        's32 f(void) { const char* s = "}{"; return 0; }') == "",
        "braces inside a string literal do not count")
    check(wd.validate_candidate(
        "s32 f(void) { char c = '}'; return 0; }") == "",
        "a brace as a char literal does not count")
    check(wd.validate_candidate(
        's32 f(void) { char c = \'\\\'\'; return 0; }') == "",
        "an escaped quote does not swallow the rest of the file")
    check(wd.validate_candidate("s32 f(void) { /* } */ return 0; }") == "",
        "a brace in a block comment does not count")

    print("\nthe three real corruptions are all rejected")
    # Verbatim from the queue note.
    xml = ('void f(void) { earch_text<arg_key>pattern</arg_key>'
           '<arg_value>func_us_8019FD4C</arg_value></tool_call> }')
    why = wd.validate_candidate(xml)
    check(bool(why), f"tool-call markup is rejected ({why})")
    check("markup" in why or "not C" in why, "and the reason says why")

    mips = "void f(void) { sw(0x80000000, 4); }"
    why2 = wd.validate_candidate(mips)
    check(bool(why2), f"a bare `sw(` call is rejected ({why2})")
    check("sw" in why2 and "MIPS" in why2, "and names the mnemonic")
    check(bool(wd.validate_candidate("void f(void) { lh(p, 2); }")),
          "`lh(` too, which is the other one that reached a build")

    print("\nunbalanced braces are caught before the compiler sees them")
    check(bool(wd.validate_candidate("void f(void) { if (x) { return; }")),
          "an unclosed brace is rejected")
    check(bool(wd.validate_candidate("void f(void) { } }")),
          "a stray closer is rejected")
    check(wd.validate_candidate("") != "", "empty is rejected")
    check(wd.validate_candidate("   \n ") != "", "whitespace-only is rejected")

    print("\nlegitimate C that merely LOOKS like a mnemonic is not rejected")
    # The guard must not fire on a member, a longer name, or a declaration.
    for ok_src in (
        "void f(Entity* e) { e->sw(1); }",          # a member call
        "void f(void) { switch_mode(1); }",         # longer name
        "void f(void) { s32 sw; sw = 1; }",         # a variable
        "void f(void) { obj.lw(2); }",              # member access
    ):
        check(wd.validate_candidate(ok_src) == "",
              f"accepted: {ok_src.strip()[:44]}")

    print("\nthe gate runs BEFORE the checks that assume the text is C")
    src = wd.__file__ and open(wd.__file__, encoding="utf-8",
                               errors="replace").read()
    body = src[src.index("def review_gate("):]
    body = body[:body.index("\ndef ")]
    check("validate_candidate(code)" in body,
          "review_gate calls it")
    check(body.index("validate_candidate") < body.index("virtual_apply"),
          "before virtual_apply, so linkage analysis never runs over markup")
    check("not usable C" in body,
          "and the finding says the text is not C, not that the code is bad")

    print("\na candidate that fails to build is ARCHIVED, not discarded")
    # The escalation path used to report the compiler's message and throw the
    # code away, so an escalated record described something nobody could read.
    # Twelve live records failed on nothing worse than a missing extern and
    # still need a full re-attempt, because the near-miss C is gone.
    rec = {"id": "us:ST/RCEN:func_us_8019F9C0"}
    p = wd.rejected_path(rec)
    check("rejected" in p, f"archived under automation/rejected ({p})")
    check("candidates" not in p,
          "NOT under candidates/, which permuter_supervisor reads as seeds "
          "and which would hand it code that has never compiled")
    check("logs" not in p,
          "and not under logs/, which is gitignored and periodically cleared")

    import shutil
    import tempfile
    tmp = tempfile.mkdtemp()
    real_repo = wd.WIN_REPO
    try:
        wd.WIN_REPO = tmp
        got = wd.save_rejected(rec, "void f(void) { bad_c }", 3,
                               "BUILD FAILED: `g_EInitCommon' undeclared",
                               {"src_rel": "src/st/rcen/unk_1F0D8.c"})
        check(got.startswith("automation/rejected/"),
              f"returns a repo-relative path ({got})")
        body = open(os.path.join(tmp, got.replace("/", os.sep)),
                    encoding="utf-8").read()
        check("void f(void) { bad_c }" in body, "the C itself is kept")
        check("g_EInitCommon" in body, "with the verdict that rejected it")
        check("us:ST/RCEN:func_us_8019F9C0" in body, "and the record id")
        check("src/st/rcen/unk_1F0D8.c" in body, "and where it belongs")
        # "never built", not "never compiled". A draft stopped by the
        # pre-build quality gate never reached gcc at all, so claiming it
        # failed to compile sends the reader after output that does not exist.
        # "built" covers both that and a genuine compile failure, and the
        # header line above it now names which one happened.
        check("never built" in body,
              "and a warning that it is not a permuter seed")
        check("REJECTED BEFORE THE BUILD" in body or "did NOT compile" in body,
              "and the header says which of the two it was")
    finally:
        wd.WIN_REPO = real_repo
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nand the queue note points at the archive")
    # Same lesson as seed=: the note is the only index, so an archive nothing
    # references is a directory nobody opens.
    esc = src[src.index("A candidate WAS produced and it failed to build"):]
    esc = esc[:esc.index("except KeyboardInterrupt")]
    check("save_rejected(" in esc, "the escalation path archives")
    check("rejected=" in esc, "and names the file in the note")
    check("best_build_code" in esc,
          "archiving the candidate that produced the RECORDED error, not "
          "whatever the last generation happened to be")

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
