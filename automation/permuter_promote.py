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


def promote_from(work: Path, donor: Path, dry_run: bool = False) -> str:
    """Promote the best output of ANOTHER work dir into `work`'s base.c.

    WHY A CROSS-DIR FORM EXISTS
        A work dir imported from a corrected seed starts its search over. On
        2026-08-10 sixteen BOSS/BO0 dirs were re-imported after their seeds
        gained the INCLUDE_ASM stub declarations they were missing, and five
        came back WORSE than the figure the old dir had reached: 801BA724 went
        275 -> 765, 801B8B64 2215 -> 2660.

        That is not a real regression. The old figures had accumulated across
        sessions with promoted bases; the new ones are a single fresh search
        from the seed. The better code still exists, because the re-import
        RENAMED the old dir (`<fn>.stale-<ts>`) instead of deleting it, and
        `workdir_for` deliberately does not match that suffix, so the
        supervisor cannot see it. Nothing could get the work back.

    WHY IT IS NOT A PLAIN COPY
        The donor's source predates the declaration fix, so promoting it
        verbatim would hand the permuter back the undeclared calls its typemap
        raises KeyError on -- reinstating the exact defect the re-import was
        for, while looking like an improvement. The declarations are therefore
        re-applied to the donated source, using worker_direct's own function
        rather than a copy of the rule.

    The donor is only accepted if it is actually better than what `work` has.
    """
    base = work / "base.c"
    if not base.is_file():
        return f"skip {work.name}: no base.c"
    if not donor.is_dir():
        return f"skip {work.name}: donor {donor.name} is not a directory"

    theirs = best_output(donor)
    if theirs is None:
        return f"skip {work.name}: donor {donor.name} has no output-* source.c"
    their_score, their_dir = theirs

    mine = best_output(work)
    my_score = mine[0] if mine else current_score(work)
    if my_score is not None and their_score >= my_score:
        return (f"skip {work.name}: donor best {their_score} is not better "
                f"than what this dir already has ({my_score})")

    if dry_run:
        return (f"would promote {work.name}: base.c <- "
                f"{donor.name}/{their_dir.name} (score {their_score}, "
                f"beats {my_score})")

    text = (their_dir / "source.c").read_text(errors="ignore")
    added = []
    try:
        sys.path.insert(0, str(REPO / "automation" / "win"))
        import os as _os
        _os.environ.setdefault("MODEL_BACKEND", "zen")
        import worker_direct as _wd
        fixed = _wd._declare_stub_siblings(text, text)
        if fixed != text:
            added = [l.strip() for l in fixed.splitlines()
                     if l.strip().startswith("extern")
                     and l not in text.splitlines()]
            text = fixed
    except Exception as e:                                   # noqa: BLE001
        return (f"REFUSING {work.name}: donor source needs the declaration "
                f"pass and it could not be run ({type(e).__name__}: {e}). "
                f"Promoting without it would reinstate the KeyErrors.")

    orig = work / "base.c.orig"
    if not orig.is_file():
        shutil.copy2(base, orig)
    base.write_text(text)
    (work / ".promoted-score").write_text(str(their_score) + "\n")
    return (f"promoted {work.name}: base.c <- {donor.name}/{their_dir.name} "
            f"(score {their_score}, was {my_score})"
            + (f"  [+{len(added)} declaration(s) re-applied]" if added else ""))


def stale_donor(work: Path) -> Path | None:
    """The most recent `<fn>.stale-<ts>` sibling of `work`, if any."""
    sibs = sorted(p for p in work.parent.glob(work.name + ".stale-*")
                  if p.is_dir())
    return sibs[-1] if sibs else None


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

        print("\ncross-dir promotion from a .stale- donor")
        # The case: a dir re-imported from a corrected seed searched worse
        # than the dir it replaced. The better code is in the renamed sibling
        # and nothing else can reach it.
        fresh = w.parent / "fn_fresh"
        fresh.mkdir()
        (fresh / "base.c").write_text("FRESH_SEED\n")
        (fresh / "output-900-1").mkdir()
        (fresh / "output-900-1" / "source.c").write_text("FRESH900\n")
        old = w.parent / "fn_fresh.stale-20260810-000000"
        old.mkdir()
        (old / "base.c").write_text("OLD_SEED\n")
        (old / "output-200-1").mkdir()
        (old / "output-200-1" / "source.c").write_text("OLD200\n")

        ck(stale_donor(fresh) == old, "the donor is found by suffix")
        ck(stale_donor(w) is None, "and a dir with no stale sibling has none")

        msg = promote_from(fresh, old, dry_run=True)
        ck("would promote" in msg and "200" in msg, f"dry run reports ({msg})")
        ck((fresh / "base.c").read_text() == "FRESH_SEED\n",
           "and writes nothing")

        msg = promote_from(fresh, old)
        ck((fresh / "base.c").read_text().startswith("OLD200"),
           f"the donor's better source becomes the new base ({msg})")
        ck((fresh / "base.c.orig").read_text() == "FRESH_SEED\n",
           "and the fresh seed is preserved, so --revert still works")
        ck((fresh / ".promoted-score").read_text().strip() == "200",
           "the stamp records the donated score")

        print("\na donor that is not better is refused")
        worse = w.parent / "fn_fresh2"
        worse.mkdir()
        (worse / "base.c").write_text("X\n")
        (worse / "output-50-1").mkdir()
        (worse / "output-50-1" / "source.c").write_text("GOOD50\n")
        d2 = w.parent / "fn_fresh2.stale-20260810-000000"
        d2.mkdir()
        (d2 / "output-800-1").mkdir()
        (d2 / "output-800-1" / "source.c").write_text("BAD800\n")
        m2 = promote_from(worse, d2)
        ck("skip" in m2 and "not better" in m2,
           f"a worse donor is refused rather than promoted ({m2})")
        ck((worse / "base.c").read_text() == "X\n", "and nothing is written")

        print("\n.stale- dirs are donors, never targets")
        msrc = Path(__file__).read_text(errors="ignore")
        mainb = msrc[msrc.index("def main("):]
        ck('".stale-" not in p.name' in mainb,
           "--all skips them, so nothing promotes into a dir no searcher "
           "can see")

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
    ap.add_argument("--from-stale", action="store_true",
                    help="promote from this dir's `<fn>.stale-<ts>` sibling "
                         "instead of from its own outputs, re-applying the "
                         "stub declarations. For dirs re-imported from a "
                         "corrected seed whose old search had got further")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    if a.dir:
        works = [REPO / a.dir]
    elif a.all:
        root = REPO / "nonmatchings"
        # `.stale-<ts>` dirs are donors, never targets. They are also
        # invisible to permuter_supervisor.workdir_for by design, and
        # promoting INTO one would write code nothing will ever search.
        works = sorted(p for p in root.iterdir()
                       if p.is_dir() and (p / "base.c").is_file()
                       and ".stale-" not in p.name)
    else:
        ap.error("pass --dir <workdir> or --all")

    for w in works:
        if a.revert:
            print(revert(w))
        elif a.from_stale:
            donor = stale_donor(w)
            if donor is None:
                print(f"skip {w.name}: no .stale-* sibling")
            else:
                print(promote_from(w, donor, a.dry_run))
        else:
            print(promote(w, a.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
