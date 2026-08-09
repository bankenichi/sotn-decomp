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


def upstream_files(overlay_hint: str = "") -> dict[str, str]:
    """{function name: upstream path} for every real definition upstream has.

    One `git grep` over the ref rather than a show per file: the per-file
    version is hundreds of subprocesses and minutes of wall clock.
    """
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
    return defs


def upstream_stubs() -> set[str]:
    """Functions upstream still has as INCLUDE_ASM, i.e. NOT decompiled."""
    raw = _git("grep", "-hE", "INCLUDE_ASM", UPSTREAM, "--", "src/",
               timeout=300)
    return set(RX_INCLUDE_ASM.findall(raw))


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
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.show:
        return show(a.show)
    return report(a.overlay)


if __name__ == "__main__":
    raise SystemExit(main())
