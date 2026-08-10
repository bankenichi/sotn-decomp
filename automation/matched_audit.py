#!/usr/bin/env python3
"""Does every `matched` queue record still have a body in the committed tree?

WHY THIS EXISTS
    `matched` is the strongest claim the harness makes. scheduler.py refuses
    to write it without machine proof and re-verifies the build itself, so the
    record is trustworthy AT THE MOMENT IT IS WRITTEN. Nothing re-checks it
    afterwards.

    That gap became concrete on 2026-08-10. Three BOSS/BO6 functions were
    `matched` with proof and the BO6.BIN sha1, and their bodies existed only
    in an uncommitted working tree. A single git_restore would have put the
    INCLUDE_ASM stubs back while the queue went on asserting a verified match,
    hash and all. Nothing in the harness would have noticed, and every number
    built on the queue -- progress_table, the README percentages,
    match_provenance -- would have inherited it.

    A BUILD CANNOT FIND THIS. A lost match shows up as a red build somewhere,
    or as nothing at all if the stub still assembles, while the queue keeps
    reporting the same total. The only way to catch it is to ask git what is
    actually committed.

WHAT IT REPORTS
    present      the function is no longer an INCLUDE_ASM stub in HEAD. Fine.
    uncommitted  still a stub in HEAD, but has a body in the working tree.
                 Real work, one commit away from being lost.
    LOST         still a stub in HEAD and in the working tree. The record is
                 FALSE: it claims a verified match for code that does not
                 exist anywhere. Requeue it.

    `LOST` is the whole point. The other two are context.

READ-ONLY. It asks scheduler for the queue and git for the tree, and writes
nothing. There is no --apply, deliberately: requeueing a false record is a
judgement call about work that may be recoverable from a reflog or a stash.

Usage:
    python3 automation/matched_audit.py
    python3 automation/matched_audit.py --verbose     # list every record
    python3 automation/matched_audit.py --self-test
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

from orphan_check import RX_STUB          # noqa: E402  single copy of the rule

PYTHON = str(REPO / ".venv" / "bin" / "python")
if not Path(PYTHON).exists():                                # pragma: no cover
    PYTHON = sys.executable


def _run(argv, timeout=300):
    try:
        return subprocess.run(argv, cwd=str(REPO), capture_output=True,
                              text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:       # pragma: no cover
        class _R:
            returncode = 127
            stdout = ""
            stderr = f"{type(e).__name__}: {e}"
        return _R()


def overlay_dir(rec_id: str) -> str:
    """us:BOSS/BO6:fn -> src/boss/bo6 ; us:MAIN:fn -> src/main

    Scoping the search to the overlay matters. Ids carry a `_from_<overlay>`
    suffix for functions shimmed in from elsewhere, and the stub they refer to
    may be named without it, so an unscoped search for the stripped name can
    match a DIFFERENT overlay's stub and invent a failure.
    """
    parts = rec_id.split(":")
    if len(parts) < 3:
        return "src"
    return "src/" + parts[1].lower()


def stubs_in(rev: str | None) -> set[tuple[str, str]]:
    """{(path, function)} for every INCLUDE_ASM stub under src/.

    -A1 because clang-format wraps a stub whose name is long enough:

        INCLUDE_ASM(
            "boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpn...);

    git grep is line-based, so without the trailing context line those stubs
    are invisible and every one of them would be reported as "present" --
    a false all-clear, which is the worst possible direction for this tool.
    Six real stubs in us_3E79C.c have exactly that shape.
    """
    argv = ["git", "grep", "-n", "-A1", "INCLUDE_ASM("]
    if rev:
        argv.append(rev)
    argv += ["--", "src"]
    r = _run(argv, timeout=300)
    out: set[tuple[str, str]] = set()
    # Lines look like `HEAD:src/a/b.c:12:text` or `src/a/b.c-13-text`.
    rx = re.compile(r"^(?:[^:]*:)?(src/[^:\-]+)[:\-]\d+[:\-](.*)$")
    buf: dict[str, list[str]] = {}
    for line in (r.stdout or "").splitlines():
        m = rx.match(line)
        if not m:
            continue
        path, text = m.group(1), m.group(2)
        buf.setdefault(path, []).append(text)
    for path, lines in buf.items():
        joined = "\n".join(lines)
        for fn in RX_STUB.findall(joined):
            out.add((path, fn))
    return out


def matched_records() -> list[tuple[str, str]]:
    """[(id, function)] for every matched record, through the scheduler."""
    r = _run([PYTHON, str(REPO / "automation" / "scheduler.py"),
              "list", "--status", "matched"], timeout=300)
    recs = []
    for line in (r.stdout or "").splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3 or parts[0] != "matched":
            continue
        rid = parts[2].partition("|")[0].strip()
        if rid.count(":") >= 2:
            recs.append((rid, rid.rsplit(":", 1)[-1]))
    return recs


def classify(rec_id: str, fn: str, head: set, work: set) -> str:
    d = overlay_dir(rec_id)
    in_head = any(p.startswith(d) and f == fn for p, f in head)
    if not in_head:
        return "present"
    in_work = any(p.startswith(d) and f == fn for p, f in work)
    return "LOST" if in_work else "uncommitted"


def report(verbose: bool = False) -> int:
    recs = matched_records()
    if not recs:
        print("no matched records (or the scheduler could not be read)")
        return 2
    head = stubs_in("HEAD")
    work = stubs_in(None)
    if not head:
        print("refusing to judge: found no INCLUDE_ASM stubs in HEAD at all, "
              "which means the\nsearch failed rather than that everything is "
              "matched.")
        return 2

    buckets: dict[str, list] = {"present": [], "uncommitted": [], "LOST": []}
    for rid, fn in recs:
        buckets[classify(rid, fn, head, work)].append((rid, fn))

    print(f"{len(recs)} matched record(s) checked against HEAD\n")
    for k in ("present", "uncommitted", "LOST"):
        print(f"  {k:12} {len(buckets[k])}")
    print()

    if buckets["uncommitted"]:
        print("=" * 74)
        print("\nUNCOMMITTED: still a stub in HEAD, body in the working tree."
              "\nReal work. Commit it; a restore would make the record "
              "false.\n")
        for rid, fn in buckets["uncommitted"]:
            print(f"  {rid}")

    if buckets["LOST"]:
        print("\n" + "=" * 74)
        print("\nLOST: still a stub in HEAD AND in the working tree.\n"
              "These records claim a verified match for code that is not "
              "anywhere.\nThe body was reverted or never committed and the "
              "queue was never told.\nEvery total built on the queue is "
              "overstated by this many.\n")
        for rid, fn in buckets["LOST"]:
            print(f"  {rid}")
        print("\nBefore requeueing, check whether the work is recoverable: "
              "git stash list,\nthe reflog, and automation/candidates/ for a "
              "seed of the same name.")

    if verbose:
        print("\n" + "=" * 74)
        print("\npresent (no longer a stub in HEAD):\n")
        for rid, _fn in buckets["present"]:
            print(f"  {rid}")

    if not buckets["LOST"] and not buckets["uncommitted"]:
        print("Every matched record has a body in the committed tree. The "
              "count is honest.")
    return 1 if buckets["LOST"] else 0


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    src_self = Path(__file__).read_text(errors="ignore")
    code = src_self.split("def self_test")[0]

    print("the three classes are decided correctly")
    H = {("src/boss/bo6/richter.c", "StillAStub"),
         ("src/boss/bo6/richter.c", "AlsoAStub")}
    W = {("src/boss/bo6/richter.c", "AlsoAStub")}
    ck(classify("us:BOSS/BO6:Bodied", "Bodied", H, W) == "present",
       "not a stub in HEAD -> present")
    ck(classify("us:BOSS/BO6:StillAStub", "StillAStub", H, W) == "uncommitted",
       "stub in HEAD, gone from the working tree -> uncommitted")
    ck(classify("us:BOSS/BO6:AlsoAStub", "AlsoAStub", H, W) == "LOST",
       "stub in BOTH -> LOST")

    print("\nthe search is scoped to the record's own overlay")
    # Without scoping, a `_from_<overlay>` id could match a same-named stub in
    # the overlay it was copied FROM and invent a failure.
    ck(overlay_dir("us:BOSS/BO6:fn") == "src/boss/bo6", "BOSS/BO6 maps")
    ck(overlay_dir("us:ST/RNO0:fn") == "src/st/rno0", "ST/RNO0 maps")
    ck(overlay_dir("us:MAIN:fn") == "src/main", "MAIN maps")
    other = {("src/st/no0/4C750.c", "func_us_801C2B24")}
    ck(classify("us:ST/RNO0:func_us_801C2B24_from_no0",
                "func_us_801C2B24_from_no0", other, set()) == "present",
       "a stub in a DIFFERENT overlay does not condemn the record")

    print("\nthe stub rule is imported, not copied")
    ck("from orphan_check import RX_STUB" in src_self, "imported")
    ck("INCLUDE_ASM\\(" not in code.replace(
        "\"INCLUDE_ASM(\"", ""), "no second regex is defined here")

    print("\nwrapped stubs are visible to the search")
    ck('"-A1"' in code,
       "git grep takes a trailing context line, or clang-format-wrapped "
       "stubs read as 'present' and the tool gives a false all-clear")
    wrapped = 'INCLUDE_ASM(\n    "boss/bo6/nonmatchings/us_3E79C", LongName);'
    ck(RX_STUB.search(wrapped) is not None
       and RX_STUB.search(wrapped).group(1) == "LongName",
       "and the regex spans the join")

    print("\nan empty HEAD result is refused, not read as success")
    # If the grep breaks, every record looks 'present' and the tool reports
    # a clean bill of health. That is the failure mode worth guarding.
    body = src_self[src_self.index("def report("):src_self.index("def self_test")]
    ck("if not head:" in body, "an empty stub set stops the run")
    ck("refusing to judge" in body, "and says the search failed")
    ck(body.index("if not head:") < body.index('buckets["LOST"]'),
       "before any verdict is printed")

    print("\nit writes nothing")
    for bad in ("git checkout", "git restore", "git add", '"report"',
                "rmtree", "unlink"):
        ck(bad not in code, f"never {bad}")
    ck('"list"' in code, "the scheduler is only listed from")
    # Assert the PROPERTY, not the absence of a string. The docstring says
    # "there is no --apply, deliberately", so a substring test fails on the
    # sentence explaining the guarantee. Third time this shape of test has
    # bitten today; what matters is that argparse never defines the flag.
    ck('add_argument("--apply"' not in code,
       "no --apply flag is defined, so there is no write path to reach")

    print("\nLOST is the exit code that can gate something")
    ck("return 1 if buckets[\"LOST\"] else 0" in body,
       "non-zero only when a record is actually false")

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
    ap.add_argument("--verbose", action="store_true",
                    help="also list the records that are fine")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    return report(a.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
