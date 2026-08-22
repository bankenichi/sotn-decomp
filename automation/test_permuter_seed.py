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
import shutil
import sys
import tempfile
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
    import permuter_supervisor as ps

    print("\nsave_candidate takes ctx and uses virtual_apply")
    src = (REPO / "automation" / "win" / "worker_direct.py").read_text()
    i = src.find("def save_candidate(")
    body = src[i:src.find("\ndef ", i + 1)]
    check("ctx" in src[i:src.find(")", i) + 1], "save_candidate accepts ctx")
    check("virtual_apply(ctx" in body,
          "it builds the payload with virtual_apply")
    check("+ payload" in body,
          "it publishes the substituted payload, not the bare body")
    check("_publish_versioned_artifact" in body,
          "the writer routes through immutable artifact publication")
    check("_archive_verdict(detail)" in body,
          "the banner keeps the complete verdict without raw build status")
    check("except Exception" in body,
          "a substitution failure degrades to the bare body rather than losing "
          "the seed")
    check("save_candidate(rec, code, attempt, detail, ctx)" in src,
          "the call site actually passes ctx")

    print("\nwhole-file seed declarations cover existing C functions")
    whole = (
        '#include "game.h"\n'
        'void Existing(Entity* self) { DestroyEntity(self); }\n'
        'INCLUDE_ASM("test", Candidate);\n')
    candidate = "void Candidate(void) {}\n"
    check("_declare_stub_siblings(whole, whole)" in body,
          "save_candidate scans the complete preserved translation unit")
    repaired = wd._declare_stub_siblings(whole, whole)
    check("void DestroyEntity(Entity*);" in repaired,
          "an implicit call outside the generated body receives its real prototype")

    print("\nimmutable evidence publication has a public shared owner")
    for rel in ("fix_seed_declarations.py", "permuter_supervisor.py", "transplant.py"):
        consumer = (REPO / "automation" / rel).read_text()
        check("artifact_store" in consumer,
              f"{rel} imports the shared artifact store")
        check("wd._publish_versioned_artifact" not in consumer
              and "wd._artifact_history_versions" not in consumer,
              f"{rel} no longer calls worker_direct private storage helpers")

    print("\nevery saved seed has an immutable queue path and stable current view")
    temp_root = Path(tempfile.mkdtemp())
    real_repo = wd.WIN_REPO
    try:
        wd.WIN_REPO = str(temp_root)
        rec = {"id": "us:ST/TEST:VersionedSeed",
               "function": "VersionedSeed", "build": "us",
               "overlay": "ST/TEST"}
        current = Path(wd.candidate_path(rec))
        current.parent.mkdir(parents=True, exist_ok=True)
        legacy = b"/* legacy current seed */\nvoid VersionedSeed(void) {}\n"
        current.write_bytes(legacy)

        translation_unit = (
            '#include "game.h"\n'
            'void Existing(Entity* self) { DestroyEntity(self); }\n'
            'INCLUDE_ASM("test", VersionedSeed);\n')
        original_virtual_apply = wd.virtual_apply
        try:
            wd.virtual_apply = lambda _ctx, _fn, generated: (
                translation_unit.replace(
                    'INCLUDE_ASM("test", VersionedSeed);', generated))
            first = wd.save_candidate(
                rec,
                "void VersionedSeed(void) { g_CurrentEntity->step = 1; }\n",
                1, "BUILT, CHECKSUM MISMATCH",
                {"src_rel": "src/st/test.c", "asm_rel": "st/test"})
        finally:
            wd.virtual_apply = original_virtual_apply
        first_path = temp_root / first
        versions = sorted((current.parent / "history").glob("*.c"))
        check("/history/" in first.replace("\\", "/"),
              f"the queue path is immutable ({first})")
        check(first_path.is_file(), "the first immutable version exists")
        check("void DestroyEntity(Entity*);" in first_path.read_text(),
              "published whole-file generation is declaration-complete")
        check(any(item.read_bytes() == legacy for item in versions),
              "a legacy stable seed is archived byte-for-byte before replacement")
        check(len(versions) == 2,
              f"legacy plus first generation are retained ({len(versions)})")
        first_bytes = first_path.read_bytes()

        second = wd.save_candidate(
            rec, "void VersionedSeed(void) { g_CurrentEntity->step = 2; }\n",
            2, "BUILT, CHECKSUM MISMATCH after feedback", None)
        second_path = temp_root / second
        check(second != first and second_path.is_file(),
              f"a later attempt gets a distinct immutable path ({second})")
        check(first_path.read_bytes() == first_bytes,
              "the first generated version remains byte-identical")
        check("step = 2" in current.read_text(encoding="utf-8"),
              "the stable top-level seed is the newest generation")
        top_level = sorted(current.parent.glob("*.c"))
        check(top_level == [current],
              "the supervisor's non-recursive scan still sees one current seed")

        real_replace = wd.os.replace
        try:
            def reject_refresh(_src, _dst):
                raise OSError("simulated stable refresh failure")
            wd.os.replace = reject_refresh
            third = wd.save_candidate(
                rec,
                "void VersionedSeed(void) { g_CurrentEntity->step = 3; }\n",
                3, "BUILT, CHECKSUM MISMATCH with publish failure", None)
        finally:
            wd.os.replace = real_replace
        check("/history/" in third.replace("\\", "/")
              and (temp_root / third).is_file(),
              "a stable-refresh failure still returns the preserved generation")
        check("step = 2" in current.read_text(encoding="utf-8"),
              "a failed refresh leaves the prior stable view intact")
    finally:
        wd.WIN_REPO = real_repo
        shutil.rmtree(temp_root, ignore_errors=True)

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
    seed_texts = [(p.name, p.read_text(errors="ignore")) for p in seeds]
    bare = [name for name, text in seed_texts
            if not ps.seed_has_include_context(text)]
    check(not bare, f"{len(seeds)} seed(s) present and all are self-contained",
          f"body-only: {', '.join(bare)}")
    check(not ps.seed_has_include_context(
              "/* banner mentions #include */\nvoid f(void) {}\n"),
          "banner prose cannot hide a body-only payload")
    if bare:
        print(f"       these need re-saving or manual staging to import: "
              f"{', '.join(bare[:6])}")

    print("\nevery current seed has complete permuter typemap declarations")
    import fix_seed_declarations as fsd
    pending = {
        name: added
        for name, _new, added in fsd.scan_seed_texts(seed_texts)
        if added
    }
    check(not pending,
          "no current seed still needs fix_seed_declarations",
          "; ".join(f"{name}: {', '.join(added)}"
                    for name, added in pending.items()))

    print("\nland_match can actually CALL save_candidate")
    # On 2026-08-16 --land reached compiles-differs on func_us_801CFD70 -- the
    # exact outcome this file exists to bank -- and saved nothing, because the
    # rec it builds had no "id" and save_candidate slugs rec["id"] for the
    # filename. The KeyError was caught and returned as the verdict string, so
    # the run printed "reverted (verified): KeyError: 'id'" and moved on.
    # Second time this shape has bitten: the same function's docstring records
    # KeyError: 'overlay' costing a real match on 2026-08-03.
    import inspect
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
