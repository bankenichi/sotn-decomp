#!/usr/bin/env python3
"""Advance the decomp WITHOUT a model, by transplanting C that already exists.

WHY THIS EXISTS
    The harness spends its budget asking models to rediscover functions. But
    for a large slice of the queue the C already exists somewhere: upstream
    has decompiled 26 of our unmatched functions, and asm_twin_finder found
    174 of 335 stubs have a near-identical twin elsewhere in the tree.

    For those, decompilation is not the problem. Copying is, and a copy is
    verifiable by build rather than by proxy. That makes it strictly better
    evidence than anything a model produces: no fabricated field names to
    detect, no degeneration to abort, no fidelity score standing in for the
    truth. Either the overlay checksums or it does not.

SAFETY
    This does NOT implement apply/build/revert. It calls
    permuter_supervisor.land_match, which is the one sequence in this repo
    hardened against a mid-build crash: it takes the same automation/.build
    .lock the fleet workers hold, journals the original BEFORE writing,
    rebuilds, verifies the 81 SHA-1s independently of make's exit code, and
    reverts unconditionally on anything short of green -- proving the revert
    with _assert_reverted rather than printing the word.

    A second copy of that sequence would be a second thing to get wrong, so
    land_match grew a `body=` parameter instead.

    DRY RUN by default. Nothing touches src/ without --apply.

Usage:
    python3 automation/transplant.py --list
    python3 automation/transplant.py --function <name>            # dry run
    python3 automation/transplant.py --function <name> --apply
    python3 automation/transplant.py --self-test
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "automation"))


def _sup():
    import permuter_supervisor as ps                          # type: ignore
    return ps


def _harv():
    import upstream_harvest as uh                             # type: ignore
    return uh


def candidates() -> list[tuple[str, str, str]]:
    """(function, our overlay, upstream path) we could transplant right now."""
    return _harv().harvest()


def upstream_body(fn: str) -> tuple[str, str]:
    """(C source of fn as upstream writes it, upstream path)."""
    uh = _harv()
    base = re.sub(r"_from_\w+$", "", fn)
    path = uh.upstream_files().get(base)
    if not path:
        return "", ""
    whole = uh._git("show", f"{uh.UPSTREAM}:{path}")
    return uh._extract(whole, base), path


def local_twin(base: str, exclude: str = "") -> tuple[str, str]:
    """(body, path) for a definition of `base` ALREADY IN OUR TREE.

    PREFERRED OVER UPSTREAM, and the reason this whole mechanism works.

    The queue's unmatched record for the inverted castle is
    `func_us_801CC750_from_no0`, an INCLUDE_ASM stub in
    src/st/rno0/e_background_pillars.c. But `func_us_801CC750` itself is
    already decompiled HERE, in src/st/no0/4C750.c, because the normal and
    inverted stages share an implementation. That copy compiles against this
    tree's headers and already matches, which upstream's cannot be assumed to
    do.

    So the first question is never "what does upstream have"; it is "do we
    already have this function under another name".
    """
    import subprocess
    hits = subprocess.run(
        ["git", "grep", "-lE", r"^[A-Za-z_][A-Za-z0-9_ \t*]*\b"
         + re.escape(base) + r"\s*\(", "--", "src/"],
        capture_output=True, text=True, timeout=120,
        cwd=str(REPO)).stdout.split()
    uh = _harv()
    for h in hits:
        if exclude and h.endswith(exclude):
            continue
        body = uh._extract((REPO / h).read_text(errors="ignore"), base)
        if body:
            return body, h
    return "", ""


def rename_function(body: str, old: str, new: str) -> str:
    """Rename the DEFINITION and any self-recursion, nothing else.

    The twin is the same code under a different symbol; only the name in the
    signature has to change. Renaming every occurrence would also rewrite an
    unrelated call that happens to contain the old name as a substring, so the
    match is anchored on a word boundary and applied to the whole body, which
    for these functions is the definition plus any recursive call.
    """
    if old == new:
        return body
    return re.sub(r"\b" + re.escape(old) + r"\b", new, body)


def preflight(fn: str) -> tuple[bool, str, str]:
    """Everything checkable before the tree is touched.

    Ordered cheapest-first and STOPS at the first failure, so a dry run costs
    nothing and cannot half-report.
    """
    ps = _sup()
    base = re.sub(r"_from_\w+$", "", fn)

    dirty = ps.require_clean_src()
    if dirty:
        return False, "", f"src/ is not clean: {dirty}"

    # LOOK FOR THE STUB UNDER THE QUEUE'S OWN NAME, suffix and all. The first
    # version stripped `_from_no0` for both lookups and then reported "no
    # INCLUDE_ASM stub for func_us_801CC750" -- true, and irrelevant: the stub
    # we are replacing is `func_us_801CC750_from_no0`.
    found = ps.find_stub(fn)
    if not found:
        return False, "", (f"no INCLUDE_ASM stub for {fn} in src/; it is "
                           f"either already applied or not ours to write")
    stub_path = str(found[0].relative_to(REPO)) if hasattr(
        found[0], "relative_to") else str(found[0])

    # OUR OWN TREE FIRST. A twin already compiling here beats upstream's C,
    # which is written against upstream's headers.
    body, path = local_twin(base, exclude=Path(stub_path).name)
    src_kind = "local twin"
    if not body:
        body, path = upstream_body(base)
        src_kind = "upstream"
    if not body:
        return False, "", (f"neither this tree nor upstream has an "
                           f"extractable definition of {base}")
    body = rename_function(body, base, fn)

    # The transplant must define the function we are replacing, not merely
    # mention it. _extract already enforces this, but a wrong body here would
    # be applied to the tree, so it is worth asserting twice.
    head = body.split("{", 1)[0]
    if not re.search(r"\b" + re.escape(fn) + r"\s*\(", head):
        return False, "", f"extracted body does not define {fn}"

    # Type-check the transplant the same way generated C is checked. Upstream
    # writes against upstream's headers; a member that does not exist here
    # would fail the build, and this says so for free.
    try:
        import member_types as mt                             # type: ignore
        bad = mt.check(body)
    except ImportError:                                       # pragma: no cover
        bad = []
    if bad:
        return False, body, ("upstream's C uses members this tree does not "
                             "have: " + "; ".join(bad[:3]))
    return True, body, (f"ready: {len(body)} chars from the {src_kind} "
                        f"{path}\n  stub: {stub_path}"
                        + (f"\n  renamed {base} -> {fn}" if base != fn else ""))


def run(fn: str, apply: bool) -> int:
    ok, body, detail = preflight(fn)
    print(f"{fn}\n  {detail}")
    if not ok:
        return 1
    if not apply:
        print("\n  DRY RUN. Nothing written. Re-run with --apply to test it "
              "for real;\n  the apply path builds, verifies all 81 SHA-1s, "
              "and reverts unless green.")
        print("\n--- transplant body ---")
        print("\n".join("  " + l for l in body.splitlines()[:40]))
        return 0

    ps = _sup()
    print("\n  applying under the fleet's own build lock...")
    good, why = ps.land_match(Path("."), fn, body=body)
    print(f"  {'MATCHED' if good else 'not a match'}: {why}")
    if good:
        print("\n  The overlay rebuilt and all 81 SHA-1s verified. Report it "
              "with\n  queue_report(status='matched', proof=...) -- this tool "
              "does not write\n  to the queue.")
    else:
        print("\n  Reverted. src/ is back to HEAD; land_match proves the "
              "revert rather\n  than asserting it.")
    return 0 if good else 2


def list_all() -> int:
    rows = candidates()
    if not rows:
        print("nothing available to transplant")
        return 0
    print(f"{len(rows)} function(s) upstream has decompiled and we have not\n")
    print(f"{'function':34}{'overlay':14}upstream path")
    print("-" * 92)
    for fn, ovl, path in rows:
        print(f"{fn[:32]:34}{ovl[:12]:14}{path}")
    print("\nTry one:  transplant.py --function <name>")
    return 0


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    src = Path(__file__).read_text(errors="ignore")
    print("\nthis module does NOT reimplement apply/build/revert")
    # The hardened sequence lives in exactly one place. A second copy is a
    # second thing to get wrong, and the failure mode is a corrupted tree.
    #
    # Checked against the AST, not the text: the first version searched the
    # source for "apply_code(" and matched its own docstring, failing a module
    # that calls no such thing. Reading prose is not testing code -- the same
    # mistake this project has now made three times.
    import ast as _ast
    called = set()
    for node in _ast.walk(_ast.parse(src)):
        if isinstance(node, _ast.Call):
            f = node.func
            if isinstance(f, _ast.Name):
                called.add(f.id)
            elif isinstance(f, _ast.Attribute):
                called.add(f.attr)
    for danger in ("apply_code", "build_and_check", "journal_write",
                   "copyfile", "write_text", "unlink", "rename"):
        ck(danger not in called, f"never calls {danger}()")
    ck("land_match" in called, "it delegates to land_match")

    print("\nnothing is written without --apply")
    ck('if not apply:' in src and 'DRY RUN' in src,
       "the dry-run branch returns before land_match")
    ck(src.index("if not apply:") < src.index("ps.land_match("),
       "and it does so BEFORE the apply call")

    print("\npreflight stops at the first failure")
    # Each check returns immediately, so a dry run cannot report "ready" while
    # an earlier condition was false.
    body_fn = src[src.index("def preflight"):src.index("def run(")]
    ck(body_fn.count("return False") >= 4,
       f"every failure path returns ({body_fn.count('return False')})")
    ck("require_clean_src()" in body_fn,
       "a dirty tree is refused before anything else")
    ck(body_fn.index("require_clean_src()") < body_fn.index("find_stub"),
       "and that check comes first")

    print("\nthe stub is looked up under the QUEUE's name, suffix and all")
    # The unmatched record is func_us_801CC750_from_no0; the stub in
    # e_background_pillars.c carries that exact name. Stripping the suffix for
    # this lookup reported "no INCLUDE_ASM stub for func_us_801CC750", which
    # is true and useless.
    # Scoped to preflight, not the whole file: the assertion string itself
    # contains the pattern it is looking for, so a whole-file search matches
    # the test rather than the code. FOURTH time today. The rule is simple --
    # a test that greps source text must first cut out its own text.
    ck("find_stub(fn)" in body_fn and "find_stub(base)" not in body_fn,
       "find_stub gets the full name")

    print("\nour own tree is preferred over upstream")
    ck(body_fn.index("local_twin(") < body_fn.index("upstream_body("),
       "local_twin is tried first")

    print("\nthe twin is renamed to the symbol being replaced")
    ck(rename_function("void a(Entity* e) { a(e); }", "a", "a_from_no0")
       == "void a_from_no0(Entity* e) { a_from_no0(e); }",
       "definition and self-recursion are renamed")
    ck(rename_function("void ab(void) { abc(); }", "ab", "ab_x")
       == "void ab_x(void) { abc(); }",
       "a name that merely CONTAINS the old one is left alone")
    ck(rename_function("void a(void){}", "a", "a") == "void a(void){}",
       "renaming to the same name is a no-op")

    print("\nthe transplant is type-checked like generated C is")
    ck("member_types" in body_fn,
       "upstream's members are validated against THIS tree's structs")

    print("\nland_match accepts a supplied body")
    sup = (REPO / "automation" / "permuter_supervisor.py").read_text(
        errors="ignore")
    ck("body: str = \"\"" in sup, "the parameter exists")
    ck("if not body:" in sup,
       "and the permuter path still works when it is omitted")

    print()
    if fails:
        print(f"{len(fails)} FAILED:")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--function")
    ap.add_argument("--apply", action="store_true",
                    help="actually apply, build, verify and revert on failure")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.list:
        return list_all()
    if a.function:
        return run(a.function, a.apply)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
