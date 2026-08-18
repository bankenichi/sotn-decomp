#!/usr/bin/env python3
"""Is a saved permuter seed actually IMPORTABLE?

WHY THIS EXISTS
    A seed exists for exactly one consumer: decomp-permuter's import.py. That
    tool compiles the file it is handed and nothing else, so a seed that is not
    self-contained is not a seed, it is a note.

    save_candidate() used to write the model's bare function body. Every such
    seed failed to import:

      - the rcen seed: "Syntax error in base.c ... before `arg0'", because with
        no #include the parser had never heard of s32, Entity or
        g_CurrentEntity;
      - bo6 func_us_801BC3E0: "`RIC_step' undeclared", because that extern lives
        elsewhere in us_39144.c, outside the function body.

    Both had to be reconstructed by hand -- stage a file inside the overlay
    directory so the quoted #include resolves, import it, delete it. Three
    times. That is the cost this test exists to prevent recurring.

    The fix is to save what virtual_apply() produces: the whole target file with
    the stub substituted. It compiles exactly as the real build does, because it
    IS what the real build compiled.

WHAT IS ASSERTED
    Not "a file was written" -- the broken version wrote files happily. The
    assertions are about CONTENT: the seed carries the includes and the
    file-scope declarations, and the harness passes ctx so it can.

Run: python3 automation/test_permuter_seed.py
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAILS: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    print(("  ok   " if cond else "  FAIL ") + label
          + ("" if cond else "   " + detail))
    if not cond:
        FAILS.append(label)


def main() -> int:
    spec = importlib.util.spec_from_file_location(
        "worker_direct", REPO / "automation" / "win" / "worker_direct.py")
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)
    wd.WIN_REPO = str(REPO)

    print("\nsave_candidate takes ctx and uses virtual_apply")
    src = (REPO / "automation" / "win" / "worker_direct.py").read_text()
    i = src.find("def save_candidate(")
    body = src[i:src.find("\ndef ", i + 1)]
    check("ctx" in src[i:src.find(")", i) + 1], "save_candidate accepts ctx")
    check("virtual_apply(ctx" in body,
          "it builds the payload with virtual_apply")
    check("f.write(payload)" in body,
          "it writes the substituted payload, not the bare body")
    check("_archive_verdict(detail)" in body,
          "the banner keeps the complete verdict without raw build status")
    check("except Exception" in body,
          "a substitution failure degrades to the bare body rather than losing "
          "the seed")
    check("save_candidate(rec, code, attempt, detail, ctx)" in src,
          "the call site actually passes ctx")

    print("\nthe seed is self-contained for a real repo file")
    # A real file with a real stub, so the substitution is exercised against
    # text that actually ships rather than a fixture that cannot rot.
    ctx = {"src_rel": "src/st/rno0/e_gorgon.c",
           "asm_rel": "st/rno0/nonmatchings/e_gorgon"}
    fn = "func_us_801D2424_from_are"
    stub_owner = (REPO / ctx["src_rel"]).read_text()
    if f", {fn});" not in stub_owner:
        print(f"  ~~ {fn} is no longer a stub in {ctx['src_rel']}; "
              f"pick another to keep this covered")
    else:
        code = f"void {fn}(Entity* self) {{ self->step++; }}\n"
        rec = {"id": f"us:ST/RNO0:{fn}", "function": fn, "build": "us",
               "overlay": "ST/RNO0"}
        out = wd.virtual_apply(ctx, fn, code)
        check(bool(out), "virtual_apply returns the substituted file")
        check("#include" in out,
              "the seed carries an #include (this is what the parser needed)")
        check(code.strip() in out, "the candidate body is present")
        check(f'INCLUDE_ASM("{ctx["asm_rel"]}", {fn});' not in out,
              "the stub it replaced is gone")
        # The property the rcen failure was really about: types are reachable.
        check(len(out) > len(code) * 5,
              "the seed is the whole file, not just the body",
              f"seed {len(out)} vs body {len(code)}")

    print("\nthe banner tells the reader what they have and how to use it")
    check('content: {kind}' in body or '"   content: ' in body,
          "the banner records whether it is a whole file or a bare body")
    check("import.py" in body,
          "the banner shows the import command, so the next reader does not "
          "have to rediscover it")
    check("Do NOT apply this to the tree as-is" in body,
          "the banner still warns that a seed does not match")

    print("\nthe existing seeds on disk")
    seeds = sorted((REPO / "automation" / "candidates").glob("*.c"))
    bare = [p.name for p in seeds
            if "#include" not in p.read_text(errors="ignore")]
    check(True, f"{len(seeds)} seed(s) present, {len(bare)} written before the "
                f"fix and still body-only")
    if bare:
        print(f"       these need re-saving or manual staging to import: "
              f"{', '.join(bare[:6])}")

    print("\nland_match can actually CALL save_candidate")
    # On 2026-08-16 --land reached compiles-differs on func_us_801CFD70 -- the
    # exact outcome this file exists to bank -- and saved nothing, because the
    # rec it builds had no "id" and save_candidate slugs rec["id"] for the
    # filename. The KeyError was caught and returned as the verdict string, so
    # the run printed "reverted (verified): KeyError: 'id'" and moved on.
    # Second time this shape has bitten: the same function's docstring records
    # KeyError: 'overlay' costing a real match on 2026-08-03.
    import inspect
    import permuter_supervisor as ps
    lm = inspect.getsource(ps.land_match)
    rec_line = [l for l in lm.splitlines() if l.strip().startswith("rec = {")]
    check(bool(rec_line), "land_match builds a rec dict")
    if rec_line:
        blob = lm[lm.index(rec_line[0]):][:400]
        for key in ("build", "overlay", "function", "id"):
            check(f'"{key}"' in blob,
                  f"and it carries {key!r}, which save_candidate reads")
    check("rec_id" in inspect.signature(ps.land_match).parameters,
          "the real queue id can be passed in rather than only derived")
    check("INTERNAL ERROR" in lm,
          "an exception is labelled a BUG, not returned as a verdict: "
          "'KeyError: id' printed as 'reverted (verified)' is why this went "
          "unnoticed for a whole run")

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
