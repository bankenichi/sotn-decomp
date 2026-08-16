#!/usr/bin/env python3
"""Which functions we are still fighting has upstream already decompiled?

WHY THIS EXISTS
    On 2026-08-09 the fork was 56 commits and 1,061 files behind upstream
    (+47,188/-14,397). A merge of that size is a long, risky operation that
    would invalidate the queue mid-flight, and most of it is Saturn, PSP and
    asset tooling this fork does not touch.

    But buried in it is the thing that matters most: upstream has decompiled
    functions THIS FORK IS STILL SPENDING MODEL TIME ON. `RNO0 e_breakable`
    (#3468) landed upstream on 2026-08-02; our fleet burned four attempts and
    a build cycle failing that same file on 2026-08-09.

    A function upstream has already matched is not a decompilation problem for
    us. It is a copy, and the build says whether the copy is right.

WHAT THIS DOES
    For every unmatched record in the queue, asks whether upstream/master has
    a REAL definition rather than an INCLUDE_ASM stub, and reports the ones it
    does. Read-only: prints a harvest list, writes nothing, touches neither
    the tree nor the queue.

WHY IT SHELLS OUT TO GIT
    The comparison is against a ref, not the working tree, so `search_repo`
    and the filesystem cannot answer it. This runs on the machine that owns
    the repo (via run_analysis), never in the sandbox.

NOT A MATCH ORACLE
    Upstream's C is written against upstream's headers. It may not compile
    here, and compiling is not matching. Every harvested function still has to
    go through apply -> build -> verify like anything else. This only says
    where it is worth looking.

Usage:
    python3 automation/upstream_harvest.py
    python3 automation/upstream_harvest.py --overlay rno0
    python3 automation/upstream_harvest.py --show <function>
    python3 automation/upstream_harvest.py --self-test
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PYTHON = str(REPO / ".venv" / "bin" / "python")
if not Path(PYTHON).exists():                                # pragma: no cover
    PYTHON = sys.executable

UPSTREAM = "upstream/master"

# A definition, not a declaration and not a stub.
RX_INCLUDE_ASM = re.compile(r'INCLUDE_ASM\([^)]*?,\s*(\w+)\s*\)')


def _git(*args: str, timeout: int = 120) -> str:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True,
                           timeout=timeout, cwd=str(REPO))
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def unmatched_records() -> list[tuple[str, str, str]]:
    """(id, overlay, function) for everything not matched, via the scheduler."""
    out = []
    for status in ("todo", "escalated", "deferred", "near"):
        r = subprocess.run(
            [PYTHON, str(REPO / "automation" / "scheduler.py"),
             "list", "--status", status],
            capture_output=True, text=True, timeout=180, cwd=str(REPO))
        for line in r.stdout.splitlines():
            line = line.strip()
            if not line.startswith(status):
                continue
            parts = line.split(None, 2)
            if len(parts) < 3:
                continue
            rid = parts[2].partition("|")[0].strip()
            bits = rid.split(":")
            if len(bits) >= 3:
                out.append((rid, bits[1], bits[2]))
    return out


_UF_CACHE: dict[str, dict[str, str]] = {}
_US_CACHE: set[str] | None = None


def upstream_files(overlay_hint: str = "") -> dict[str, str]:
    """{function name: upstream path} for every real definition upstream has.

    One `git grep` over the ref rather than a show per file: the per-file
    version is hundreds of subprocesses and minutes of wall clock.
    """
    # CACHED. Each call is a git grep over the whole upstream tree, roughly
    # 30 seconds. transplant --scan asks per record, so without this a scan of
    # 250 records spends over two hours re-reading the same ref.
    if overlay_hint in _UF_CACHE:
        return _UF_CACHE[overlay_hint]
    # `git grep -n` over a ref searches that ref's tree without checking it out.
    pattern = r"^[A-Za-z_][A-Za-z0-9_ \t*]*\b\w+\s*\("
    raw = _git("grep", "-nE", pattern, UPSTREAM, "--", "src/", timeout=300)
    defs: dict[str, str] = {}
    rx = re.compile(
        r"^[^:]+:(?P<path>[^:]+):\d+:"
        r"[A-Za-z_][A-Za-z0-9_ \t*]*?\b(?P<fn>\w+)\s*\([^;]*$")
    for line in raw.splitlines():
        m = rx.match(line)
        if not m:
            continue
        if overlay_hint and overlay_hint not in m.group("path"):
            continue
        defs.setdefault(m.group("fn"), m.group("path"))
    _UF_CACHE[overlay_hint] = defs
    return defs


def upstream_stubs() -> set[str]:
    """Functions upstream still has as INCLUDE_ASM, i.e. NOT decompiled."""
    global _US_CACHE
    if _US_CACHE is None:
        raw = _git("grep", "-hE", "INCLUDE_ASM", UPSTREAM, "--", "src/",
                   timeout=300)
        _US_CACHE = set(RX_INCLUDE_ASM.findall(raw))
    return _US_CACHE


def harvest(overlay: str = "") -> list[tuple[str, str, str]]:
    """(function, our overlay, upstream path) worth copying."""
    recs = unmatched_records()
    if overlay:
        recs = [r for r in recs if overlay.lower() in r[1].lower()]
    defs = upstream_files()
    stubs = upstream_stubs()
    out = []
    for _rid, ovl, fn in recs:
        # Strip the `_from_<overlay>` suffix the queue adds for shimmed stubs;
        # upstream names the function without it.
        base = re.sub(r"_from_\w+$", "", fn)
        if base in stubs:
            continue            # upstream has not decompiled it either
        path = defs.get(base)
        if path:
            out.append((base, ovl, path))
    return sorted(set(out))


def report(overlay: str = "") -> int:
    ref = _git("rev-parse", "--short", UPSTREAM).strip()
    if not ref:
        print(f"cannot resolve {UPSTREAM}; run git_fetch first")
        return 1
    behind = _git("rev-list", "--count", f"HEAD..{UPSTREAM}").strip()
    print(f"upstream/master {ref}, {behind} commits ahead of HEAD\n")

    rows = harvest(overlay)
    if not rows:
        print("nothing to harvest: upstream has no definition for any "
              "function we are still missing")
        return 0
    print(f"{len(rows)} unmatched function(s) upstream HAS decompiled\n")
    print(f"{'function':34}{'our overlay':16}upstream path")
    print("-" * 96)
    for fn, ovl, path in rows:
        print(f"{fn[:32]:34}{ovl[:14]:16}{path}")
    print("\nEach still has to survive apply -> build -> verify here:")
    print("upstream's C is written against upstream's headers, and compiling")
    print("is not matching. This says where to look, not what is true.")
    # REPEATED AT THE END. The header counts are the answer, and every caller
    # reading this through the connector sees only the TAIL -- a long list
    # pushes the count out of view, which is exactly what happened to
    # matched_audit and cost a whole diagnosis to a list with no header.
    by_ovl: dict[str, int] = {}
    for _fn, ovl, _p in rows:
        by_ovl[ovl] = by_ovl.get(ovl, 0) + 1
    spread = "  ".join(f"{o} {n}" for o, n in sorted(by_ovl.items()))
    print(f"\nSUMMARY  {len(rows)} harvestable  from upstream/master {ref} "
          f"({behind} commits ahead)  |  {spread}")
    return 0


def show(fn: str) -> int:
    defs = upstream_files()
    base = re.sub(r"_from_\w+$", "", fn)
    path = defs.get(base)
    if not path:
        print(f"upstream has no definition for {base}")
        return 1
    body = _git("show", f"{UPSTREAM}:{path}")
    if not body:
        print(f"could not read {path} at {UPSTREAM}")
        return 1
    print(f"=== {UPSTREAM}:{path} ===\n")
    print(body)
    return 0




# --------------------------------------------------------------- comparison

RX_UNK_FIELD = re.compile(r"->\s*(unk[0-9A-Fa-f]{1,3})\b")
RX_ILLEGAL = re.compile(r"\bILLEGAL\b")
RX_FAKE_SYM = re.compile(r"\bD_(?:us_)?[0-9A-Fa-f]{8}\b")


def _extract(body_src: str, fn: str) -> str:
    """The single function `fn` out of a whole .c file, or ''. """
    sys.path.insert(0, str(REPO / "automation"))
    try:
        import member_types as mt                            # type: ignore
    except ImportError:                                      # pragma: no cover
        return ""
    # MATCH THE DEFINITION, NOT THE NAME. Searching the head text for the
    # function name also matches a forward declaration or an entry in a
    # pointer table, and then returns whatever region the brace matcher
    # happened to land on. src/boss/bo4/e_init.c only DECLARES
    # EntityDamageDisplay (line 7) and lists it in a table (line 36); the
    # loose version extracted 2,136 unrelated chars from it and reported three
    # raw D_ symbols we do not actually use. That is a fabricated finding, and
    # it is exactly the class of error this whole comparison exists to avoid.
    text = mt.RX_COMMENT.sub(" ", body_src)
    for m in mt.RX_FUNC_HEAD.finditer(text):
        if m.group(1) != fn:
            continue
        i = text.index("{", m.start())
        depth, j = 0, i
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        return text[m.start():j + 1]
    return ""


def compare_matched(limit: int = 0) -> int:
    """Our matched C against upstream's INDEPENDENT decompilation of the same.

    THE FIRST EXTERNAL CHECK THIS PROJECT HAS HAD. Every quality measure so
    far -- invented(), degenerate(), fidelity, member_types -- is something we
    wrote, scoring output against a model of correctness we also wrote. Two of
    them have already been caught agreeing with each other rather than with
    the compiler.

    Upstream decompiled these functions without reference to us. Where both
    sides match the same assembly the SEMANTICS must agree, so every remaining
    difference is naming and shape -- which is exactly the axis our own
    metrics cannot see, and the axis a reviewer judges.

    A field they name and we call `unkNN` is a concrete, checkable upgrade,
    not an opinion.
    """
    ref = _git("rev-parse", "--short", UPSTREAM).strip()
    if not ref:
        print(f"cannot resolve {UPSTREAM}; run git_fetch first")
        return 1

    r = subprocess.run(
        [PYTHON, str(REPO / "automation" / "scheduler.py"),
         "list", "--status", "matched"],
        capture_output=True, text=True, timeout=180, cwd=str(REPO))
    ours = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line.startswith("matched"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        rid = parts[2].partition("|")[0].strip()
        bits = rid.split(":")
        if len(bits) >= 3:
            ours.append((bits[1], re.sub(r"_from_\w+$", "", bits[2])))
    if limit:
        ours = ours[:limit]

    up = upstream_files()
    stubs = upstream_stubs()
    rows, both = [], 0
    for ovl, fn in ours:
        if fn in stubs or fn not in up:
            continue                    # upstream has not done this one
        upath = up[fn]
        utext = _extract(_git("show", f"{UPSTREAM}:{upath}"), fn)
        # Ours: find the file in the working tree that defines it.
        hit = subprocess.run(
            ["git", "grep", "-lE", r"\b" + re.escape(fn) + r"\s*\(", "--",
             "src/"], capture_output=True, text=True, timeout=120,
            cwd=str(REPO)).stdout.split()
        otext = ""
        for h in hit:
            otext = _extract(Path(REPO / h).read_text(errors="ignore"), fn)
            if otext:
                break
        if not utext or not otext:
            continue
        both += 1
        o_unk = set(RX_UNK_FIELD.findall(otext))
        u_unk = set(RX_UNK_FIELD.findall(utext))
        rows.append({
            "fn": fn, "overlay": ovl, "path": upath,
            "our_unk": len(o_unk), "up_unk": len(u_unk),
            # Offsets THEY resolved and we did not: each is a rename we can
            # make with the answer already in hand.
            "upgradable": sorted(o_unk - u_unk)[:6],
            "our_illegal": len(RX_ILLEGAL.findall(otext)),
            "up_illegal": len(RX_ILLEGAL.findall(utext)),
            "our_fake": len(set(RX_FAKE_SYM.findall(otext))),
            "up_fake": len(set(RX_FAKE_SYM.findall(utext))),
            "our_lines": otext.count("\n"), "up_lines": utext.count("\n"),
        })

    print(f"upstream/master {ref}\n")
    if not rows:
        print("no matched function of ours is also decompiled upstream; "
              "nothing to compare")
        return 0
    print(f"{both} of our matched functions are ALSO decompiled upstream, "
          f"independently.\n")
    worse = [r for r in rows if r["our_unk"] > r["up_unk"]]
    better = [r for r in rows if r["our_unk"] < r["up_unk"]]
    ill = [r for r in rows if r["our_illegal"] > r["up_illegal"]]
    fake = [r for r in rows if r["our_fake"] > r["up_fake"]]
    print(f"  unresolved unkNN:  we name fewer fields in {len(worse)}, "
          f"more in {len(better)}, same in {both - len(worse) - len(better)}")
    print(f"  ext.ILLEGAL:       worse in {len(ill)}")
    print(f"  raw D_ symbols:    worse in {len(fake)}")
    tot_up = sum(len(r["upgradable"]) for r in rows)
    # STATE THE ABSOLUTE NUMBERS. "same in 35" is compatible with both sides
    # being zero, which would make the comparison vacuous while reading as a
    # clean bill of health. A parity claim has to show what it is parity AT.
    o_tot = sum(r["our_unk"] for r in rows)
    u_tot = sum(r["up_unk"] for r in rows)
    o_ill = sum(r["our_illegal"] for r in rows)
    u_ill = sum(r["up_illegal"] for r in rows)
    o_fk = sum(r["our_fake"] for r in rows)
    u_fk = sum(r["up_fake"] for r in rows)
    o_ln = sum(r["our_lines"] for r in rows)
    u_ln = sum(r["up_lines"] for r in rows)
    print(f"\n{'':22}{'ours':>8}{'upstream':>10}")
    print(f"  {'unresolved unkNN':20}{o_tot:>8}{u_tot:>10}")
    print(f"  {'ext.ILLEGAL':20}{o_ill:>8}{u_ill:>10}")
    print(f"  {'raw D_ symbols':20}{o_fk:>8}{u_fk:>10}")
    print(f"  {'body lines':20}{o_ln:>8}{u_ln:>10}")
    if o_tot == 0 and u_tot == 0:
        print("\n  NOTE: both sides are zero, so the unkNN comparison is "
              "saturated,\n  not passed. It confirms neither side ships "
              "unresolved offsets; it does\n  NOT show our naming matches "
              "theirs.")

    print(f"\n{tot_up} field name(s) upstream resolved that we left as unkNN.")
    print("Each is a rename with the answer already known -- no model, no "
          "build risk\nbeyond the usual verify.\n")

    if fake:
        print("\nfunctions where WE carry a raw D_ symbol and upstream does "
              "not:")
        for r in fake:
            print(f"  {r['fn'][:32]:34}ours {r['our_fake']} vs "
                  f"theirs {r['up_fake']}   {r['path']}")

    for r in sorted(rows, key=lambda x: -(x["our_unk"] - x["up_unk"]))[:20]:
        d = r["our_unk"] - r["up_unk"]
        if d <= 0 and not r["upgradable"]:
            continue
        print(f"  {r['fn'][:30]:32} ours {r['our_unk']:2} unk vs "
              f"theirs {r['up_unk']:2}   {r['upgradable']}")
    return 0


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    print("\nINCLUDE_ASM stubs are recognised as NOT decompiled")
    ck(RX_INCLUDE_ASM.findall(
        'INCLUDE_ASM("st/rchi/nonmatchings/e_breakable", EntityBreakable);')
        == ["EntityBreakable"], "the stub's function name is extracted")

    print("\nthe queue's _from_<overlay> suffix is stripped")
    # Shimmed records are named func_us_801CC750_from_no0 in the queue but
    # func_us_801CC750 upstream; without stripping, every shimmed record would
    # silently look un-harvestable.
    ck(re.sub(r"_from_\w+$", "", "func_us_801CC750_from_no0")
       == "func_us_801CC750", "suffix stripped")
    ck(re.sub(r"_from_\w+$", "", "EntityBreakable") == "EntityBreakable",
       "a name without the suffix is untouched")

    print("\ngit is reached through the repo, never the sandbox")
    src = Path(__file__).read_text(errors="ignore")
    ck('cwd=str(REPO)' in src, "every git call is cwd-pinned to the repo")
    # Check the CALL SITES, not the file text. The first version searched the
    # whole source for "merge" and matched the word in this module's own
    # docstring, failing a module that does nothing of the kind. A test that
    # reads prose is testing prose.
    subcmds = set(re.findall(r'_git\(\s*"(\w+)"', src))
    writers = subcmds & {"checkout", "merge", "reset", "rebase", "commit",
                         "clean", "apply", "cherry-pick", "push", "fetch"}
    ck(not writers, f"only read-only git subcommands are used ({subcmds})",
       f"writers found: {writers}")

    print("\na single function is extracted from a whole file")
    src2 = ("void other(Entity* e) { e->posX = 1; }\n"
            "void target(Entity* e) { e->unk1C = 2; e->unk80 = 3; }\n")
    got = _extract(src2, "target")
    ck("unk1C" in got and "posX" not in got,
       f"only the requested function comes back ({got[:40]!r})")
    ck(_extract(src2, "absent") == "", "a missing function yields nothing")
    # A declaration and a pointer-table entry are not definitions.
    decl_only = ("void target(Entity*);\n"
                 "EInit D_us_80180434 = {1, 2, 3};\n"
                 "void* tbl[] = { target, other };\n")
    ck(_extract(decl_only, "target") == "",
       f"a declaration alone yields nothing ({_extract(decl_only, 'target')[:40]!r})")

    print("\nthe comparison metric is the one our own metrics cannot see")
    # Both sides match the same asm, so semantics agree and only naming can
    # differ. An offset THEY named and we did not is a checkable upgrade.
    ours = "void f(Entity* e) { e->unk1C = 1; e->unk80 = 2; }"
    theirs = "void f(Entity* e) { e->scaleY = 1; e->unk80 = 2; }"
    o = set(RX_UNK_FIELD.findall(ours)); u = set(RX_UNK_FIELD.findall(theirs))
    ck(sorted(o - u) == ["unk1C"],
       f"the upgradable offset is identified ({sorted(o - u)})")
    ck(sorted(u - o) == [], "and one we already named is not counted against us")

    print("\nthe ref is resolved before any conclusion is drawn")
    ck("cannot resolve" in src and "git_fetch first" in src,
       "a missing upstream ref is reported, not silently treated as empty")

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
    ap.add_argument("--overlay", default="", help="filter, e.g. rno0")
    ap.add_argument("--show", help="print upstream's file for one function")
    ap.add_argument("--compare-matched", action="store_true",
                    help="our matched C vs upstream's independent version")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.show:
        return show(a.show)
    if a.compare_matched:
        return compare_matched(a.limit)
    return report(a.overlay)


if __name__ == "__main__":
    raise SystemExit(main())
