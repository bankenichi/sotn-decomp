#!/usr/bin/env python3
"""Promote a permuter work dir's best output to be its new starting point.

WHY THIS EXISTS
    permuter.py reads exactly one seed: base.c (src/main.py:322). It never
    reads the output-* directories it produces. So every restart of a work dir
    throws away everything the previous run found and begins again from the
    original score.

    func_us_801BC3E0 made the cost concrete. It descended 735 -> 160 over 24k
    iterations and was still improving when it was stopped. Restarting it as-is
    would have resumed at 735, discarding all of it.

    This is the tool's intended workflow, not a trick. randomizer.py:2059
    describes perm_remove_ast as cleaning up "unnecessary changes from an
    improved base.c" -- there is a whole mutation pass that exists to tidy a
    promoted seed. We had simply never promoted one.

WHAT PROMOTION COSTS
    Hill climbing. The promoted seed carries the permuter's scaffolding
    (volatile int pad, new_var aliasing, do {} while (0)) and the search will
    now explore around that shape rather than the original. If the scaffolding
    was a wrong turn, the run is now committed to it.

    So the original is ALWAYS preserved as base.c.orig, and --revert restores
    it. Promotion is reversible or it is not safe.

Usage:
    python3 automation/permuter_promote.py --dir nonmatchings/<fn>
    python3 automation/permuter_promote.py --dir nonmatchings/<fn> --revert
    python3 automation/permuter_promote.py --all --dry-run
    python3 automation/permuter_promote.py --self-test
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_OUT = re.compile(r"^output-(\d+)-\d+$")


def best_output(work: Path) -> tuple[int, Path] | None:
    """Lowest-scoring output-<score>-<n> directory holding a source.c.

    Score is parsed from the directory NAME rather than score.txt because the
    name is what the permuter guarantees; score.txt is written separately and a
    run killed mid-write can leave it missing or empty.
    """
    best: tuple[int, Path] | None = None
    for d in work.iterdir():
        if not d.is_dir():
            continue
        m = _OUT.match(d.name)
        if not m or not (d / "source.c").is_file():
            continue
        score = int(m.group(1))
        if best is None or score < best[0]:
            best = (score, d)
    return best


def current_score(work: Path) -> int | None:
    """Score of whatever base.c currently is, if we recorded one."""
    stamp = work / ".promoted-score"
    if stamp.is_file():
        try:
            return int(stamp.read_text().strip())
        except ValueError:
            return None
    return None


def promote(work: Path, dry_run: bool = False) -> str:
    base = work / "base.c"
    orig = work / "base.c.orig"
    if not base.is_file():
        return f"skip {work.name}: no base.c"

    found = best_output(work)
    if found is None:
        return f"skip {work.name}: no output-* with a source.c"
    score, outdir = found

    have = current_score(work)
    if have is not None and score >= have:
        return (f"skip {work.name}: best output {score} is not better than the "
                f"promoted base ({have})")

    if dry_run:
        return f"would promote {work.name}: base.c <- {outdir.name} (score {score})"

    # Preserve the pristine seed exactly once. Overwriting it on a second
    # promotion would destroy the only way back to the hand-derived source.
    if not orig.is_file():
        shutil.copy2(base, orig)
    shutil.copy2(outdir / "source.c", base)
    (work / ".promoted-score").write_text(str(score) + "\n")
    return (f"promoted {work.name}: base.c <- {outdir.name} (score {score})"
            + ("" if orig.is_file() else "  [saved base.c.orig]"))


def revert(work: Path) -> str:
    orig = work / "base.c.orig"
    if not orig.is_file():
        return f"skip {work.name}: no base.c.orig, nothing was promoted"
    shutil.copy2(orig, work / "base.c")
    (work / ".promoted-score").unlink(missing_ok=True)
    return f"reverted {work.name}: base.c restored from base.c.orig"


def self_test() -> int:
    import tempfile
    fails = []

    def ck(c, l):
        print(("  ok   " if c else "  FAIL ") + l)
        if not c:
            fails.append(l)

    with tempfile.TemporaryDirectory() as td:
        w = Path(td) / "func_test"
        w.mkdir()
        (w / "base.c").write_text("ORIGINAL\n")
        for s in (735, 160, 300):
            d = w / f"output-{s}-1"
            d.mkdir()
            (d / "source.c").write_text(f"VARIANT{s}\n")

        print("\npicking the best output")
        ck(best_output(w)[0] == 160, "lowest score wins, not newest or first")

        print("\nan output with no source.c is not a candidate")
        empty = w / "output-5-1"
        empty.mkdir()
        ck(best_output(w)[0] == 160,
           "a score-5 dir with no source.c is ignored rather than crashing")

        print("\npromotion")
        msg = promote(w)
        ck("promoted" in msg, f"reports success ({msg})")
        ck((w / "base.c").read_text() == "VARIANT160\n", "base.c is the winner")
        ck((w / "base.c.orig").read_text() == "ORIGINAL\n",
           "the original seed is preserved")

        print("\npromotion is idempotent and never regresses")
        msg2 = promote(w)
        ck("skip" in msg2, f"a second promote is refused ({msg2})")
        ck((w / "base.c").read_text() == "VARIANT160\n", "base.c is unchanged")

        print("\nthe original is preserved even across a better promotion")
        d = w / "output-90-1"
        d.mkdir()
        (d / "source.c").write_text("VARIANT90\n")
        promote(w)
        ck((w / "base.c").read_text() == "VARIANT90\n", "a better output promotes")
        ck((w / "base.c.orig").read_text() == "ORIGINAL\n",
           "base.c.orig is still the HAND-DERIVED seed, not VARIANT160")

        print("\nrevert")
        ck("reverted" in revert(w), "revert reports success")
        ck((w / "base.c").read_text() == "ORIGINAL\n", "base.c is the original")
        ck(not (w / ".promoted-score").exists(),
           "the score stamp is cleared, so promotion can happen again")

        print("\ndry run touches nothing")
        before = (w / "base.c").read_text()
        promote(w, dry_run=True)
        ck((w / "base.c").read_text() == before, "base.c unchanged after --dry-run")

    print()
    if fails:
        print(f"{len(fails)} FAILED")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--revert", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    if a.dir:
        works = [REPO / a.dir]
    elif a.all:
        root = REPO / "nonmatchings"
        works = sorted(p for p in root.iterdir()
                       if p.is_dir() and (p / "base.c").is_file())
    else:
        ap.error("pass --dir <workdir> or --all")

    for w in works:
        print(revert(w) if a.revert else promote(w, a.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
