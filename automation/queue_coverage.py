#!/usr/bin/env python3
"""Does the QUEUE know about every function still stubbed in the tree?

WHY THIS EXISTS
    The queue defines what the harness can see. scheduler.py hands out work
    from it, the fleet claims from it, progress_table and the README count
    from it. A function that is still INCLUDE_ASM in src/ but has NO queue
    record is not "hard" or "deferred" -- it is INVISIBLE. No worker will ever
    claim it, no report will ever mention it, and nothing in the harness will
    ever say so.

    matched_audit.py asks the opposite question: does every `matched` record
    still have a body? That catches work the queue OVERCLAIMS. This catches
    work the queue does not claim at all, and nothing else did.

    Kenichi asked for it on 2026-08-16 after noticing that ST/RDAI and
    SLUS_000.67 both show unmatched functions in progress_table while the
    fleet had never been observed touching either. progress_table counts the
    TREE; queue_stats counts the QUEUE; nobody had ever subtracted one from
    the other. The gap was 73 functions.

WHAT IT REPORTS, per overlay
    scope        required US binaries and their splat configs are present
    stubs        INCLUDE_ASM stubs in HEAD under that overlay's src dir
    records      queue records for that overlay, any status
    BLIND        stubs with no queue record at all. The number that matters.
    stale        records whose function is not a stub in HEAD and which are
                 not `matched`. Usually harmless (the body landed via a shim
                 or a sibling overlay and the record was never closed), but
                 worth seeing, because it inflates the todo count.

    `matched` records are expected to have no stub, so they are excluded from
    `stale` rather than reported as an anomaly.

WHAT IT DELIBERATELY DOES NOT DO
    It never writes the live queue. Seeding a queue record is a scope decision,
    so the default remains read-only. --write-seed writes a reviewable,
    deterministic in-repo seed manifest; queue_init is still the separate,
    explicit operation that changes the queue.

_psp IS EXCLUDED. Those directories are a different team's PSP port and are
not compiled into the `us` build at all. Counting them took an earlier tool's
stub total from 775 to 2734 and produced 126 false LOST records. Same rule
here, and the same directory-separator test that fixed it there.

KNOWN LIMIT: SHARED HEADERS ARE ATTRIBUTED BY PATH, WHICH IS WRONG FOR THEM.
A stub inside src/st/<name>.h belongs to whichever overlays include that
header, not to a directory. This tool files those under the pseudo-overlay
"ST", which matches no queue overlay, so they will appear BLIND even when the
including overlay has a record for them. Read a non-zero BLIND count on "ST"
as "go look", not as a finding. Per-directory overlays (src/st/rdai, ...) are
unaffected and are what the interesting numbers come from.

Usage:
    python3 automation/queue_coverage.py
    python3 automation/queue_coverage.py --overlay ST/RDAI   # list the names
    python3 automation/queue_coverage.py --write-seed automation/seed.us.gaps.txt
    python3 automation/queue_coverage.py --self-test
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

# ONE parser for what a stub is, and one for how an id maps to a directory.
# Re-deriving either here is how the two tools would drift into disagreeing
# about the same tree, which is precisely the failure this tool exists to
# detect in the queue.
from matched_audit import stubs_in, overlay_dir, _run, PYTHON  # noqa: E402

FORWARD_STAGES = (
    "ARE", "CAT", "CEN", "CHI", "DAI", "DRE", "LIB", "MAD", "NO0",
    "NO1", "NO2", "NO3", "NO4", "NP3", "NZ0", "NZ1", "ST0", "TOP",
    "WRP",
)
REVERSE_STAGES = (
    "RARE", "RCAT", "RCEN", "RCHI", "RDAI", "RLIB", "RNO0", "RNO1",
    "RNO2", "RNO3", "RNO4", "RNZ0", "RNZ1", "RTOP", "RWRP",
)
REQUIRED_US_ARTIFACTS = (
    "main.exe", "DRA.BIN", "RIC.BIN",
    *(name for stage in FORWARD_STAGES
      for name in (f"{stage}.BIN", f"F_{stage}.BIN")),
    "SEL.BIN",
    *(name for stage in REVERSE_STAGES
      for name in (f"{stage}.BIN", f"F_{stage}.BIN")),
    *(name for n in range(8) for name in (f"BO{n}.BIN", f"F_BO{n}.BIN")),
    "MAR.BIN",
    *(name for n in range(9) for name in (f"RBO{n}.BIN", f"F_RBO{n}.BIN")),
    *(f"TT_{n:03}.BIN" for n in range(5)),
    "WEAPON0.BIN",
)
REQUIRED_US_CONFIGS = (
    "splat.us.main.yaml", "splat.us.dra.yaml", "splat.us.ric.yaml",
    *(f"splat.us.st{stage.lower()}.yaml" for stage in FORWARD_STAGES),
    "splat.us.stsel.yaml",
    *(f"splat.us.st{stage.lower()}.yaml" for stage in REVERSE_STAGES),
    *(f"splat.us.bobo{n}.yaml" for n in range(8)),
    "splat.us.bomar.yaml",
    *(f"splat.us.borbo{n}.yaml" for n in range(9)),
    *(f"splat.us.tt_{n:03}.yaml" for n in range(5)),
    "splat.us.weapon.yaml",
)


def required_scope_gaps(
        manifest_text: str | None = None,
        config_names: set[str] | None = None) -> list[str]:
    """Missing artifacts/configs from the fork's declared US scope.

    Source and queue scans can only see directories already named by a splat
    config. Without this independent policy boundary, omitting an entire
    binary makes queue coverage report a false clean result.
    """
    if manifest_text is None:
        try:
            manifest_text = (REPO / "config" / "check.us.sha").read_text(
                errors="ignore")
        except OSError:
            manifest_text = ""
    if config_names is None:
        config_names = {
            p.name for p in (REPO / "config").glob("splat.us.*.yaml")
        }
    artifacts = {
        line.split()[-1].rsplit("/", 1)[-1]
        for line in manifest_text.splitlines() if line.split()
    }
    required_artifacts = set(REQUIRED_US_ARTIFACTS)
    required_configs = set(REQUIRED_US_CONFIGS)
    gaps = [f"artifact:{name}" for name in REQUIRED_US_ARTIFACTS
            if name not in artifacts]
    gaps.extend(f"config:{name}" for name in REQUIRED_US_CONFIGS
                if name not in config_names)
    gaps.extend(f"unexpected-artifact:{name}"
                for name in sorted(artifacts - required_artifacts))
    gaps.extend(f"unexpected-config:{name}"
                for name in sorted(config_names - required_configs))
    return gaps


def us_src_dirs() -> set[str]:
    """The src/ directories that the `us` build actually compiles.

    Read off config/splat.us.*.yaml's `src_path`, because that IS the
    definition: if no us splat config names a directory, nothing in the us
    build compiles it and its stubs are not us work.

    WITHOUT THIS, SERVANT/FNAME IS A FALSE ALARM. src/servant/fname/fname.c
    holds 3 INCLUDE_ASM stubs and has no queue record, which looks exactly
    like a blind spot. It is not: the only config naming it is
    config/splat.hd.fname.yaml, so fname belongs to the HD build. Seeding
    those 3 would have handed the fleet work that the us oracle cannot even
    check, since none of the 81 us artifacts contain it.

    Falls back to "trust everything" if no configs are readable, so a broken
    glob degrades to the previous behaviour rather than silently reporting
    that the entire tree is out of scope.
    """
    dirs: set[str] = set()
    for cfg in sorted((REPO / "config").glob("splat.us.*.yaml")):
        try:
            for line in cfg.read_text(errors="ignore").splitlines():
                s = line.strip()
                if s.startswith("src_path:"):
                    dirs.add(s.split(":", 1)[1].strip())
        except OSError:                                      # pragma: no cover
            continue
    return dirs


def overlay_of_path(path: str) -> str | None:
    """src/boss/bo6/richter.c -> BOSS/BO6 ; src/dra/foo.c -> DRA

    Returns None for anything not part of the `us` build, which currently
    means the _psp ports. The check is on the DIRECTORY COMPONENT, not a
    substring: `psp` appearing anywhere in a filename must not disqualify it.
    """
    parts = path.split("/")
    if len(parts) < 3 or parts[0] != "src":
        return None
    if any(p.endswith("_psp") or p == "psp" for p in parts[:-1]):
        return None
    # src/st/rno0/x.c -> ST/RNO0 ; src/dra/x.c -> DRA ; src/main/x.c -> MAIN
    if parts[1] in ("st", "boss", "servant") and len(parts) >= 4:
        return f"{parts[1].upper()}/{parts[2].upper()}"
    return parts[1].upper()


def queue_records() -> list[tuple[str, str, str]]:
    """[(status, overlay, function)] for every record, via the scheduler."""
    r = _run([PYTHON, str(REPO / "automation" / "scheduler.py"), "list"],
             timeout=300)
    out = []
    for line in (r.stdout or "").splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        status = parts[0]
        rid = parts[2].partition("|")[0].strip()
        if rid.count(":") < 2:
            continue
        bits = rid.split(":")
        out.append((status, bits[1], bits[-1]))
    return out


def collect() -> dict:
    """{overlay: {"stubs": set, "records": {fn: status}}}"""
    head = stubs_in("HEAD")
    us_dirs = us_src_dirs()
    by: dict[str, dict] = {}
    for path, fn in head:
        ov = overlay_of_path(path)
        if ov is None:
            continue
        # Only count a stub if some us splat config compiles its directory.
        # See us_src_dirs(): SERVANT/FNAME is HD-only and would otherwise read
        # as 3 blind functions forever.
        if us_dirs and not any(path.startswith(d.rstrip("/") + "/")
                               for d in us_dirs):
            continue
        by.setdefault(ov, {"stubs": set(), "records": {}})["stubs"].add(fn)
    for status, ov, fn in queue_records():
        by.setdefault(ov, {"stubs": set(), "records": {}})["records"][fn] = \
            status
    return by


def blind_seed_ids(by: dict) -> list[str]:
    """Return deterministic scheduler ids for every currently blind US stub."""
    return [
        f"us:{ov}:{fn}"
        for ov in sorted(by)
        for fn in sorted(by[ov]["stubs"] - set(by[ov]["records"]))
    ]


def write_seed(path_text: str) -> int:
    """Write blind stubs to an additive scheduler seed file, never the queue."""
    scope_gaps = required_scope_gaps()
    if scope_gaps:
        print("refusing to write a seed: required US binary scope is incomplete")
        for gap in scope_gaps:
            print(f"  MISSING {gap}")
        return 2

    dest = (REPO / path_text).resolve()
    try:
        dest.relative_to(REPO.resolve())
    except ValueError:
        print(f"refusing to write outside the repository: {dest}")
        return 2

    ids = blind_seed_ids(collect())
    if not ids:
        print("No blind stubs remain; seed file was not written.")
        return 0

    head = _run(["git", "rev-parse", "HEAD"], timeout=30).stdout.strip()
    content = (
        "# Additive queue seed generated by automation/queue_coverage.py\n"
        f"# Source tree: {head}\n"
        "# Provenance: INCLUDE_ASM stubs in the exact required US artifact scope\n"
        "# Existing queue records were excluded; scheduler init skips duplicates.\n"
        f"# Records: {len(ids)}\n"
        + "\n".join(ids)
        + "\n"
    )
    if dest.exists():
        if dest.read_text(encoding="utf-8") == content:
            print(f"Seed already current: {dest.relative_to(REPO)} ({len(ids)} ids)")
            return 0
        print(f"refusing to overwrite existing seed with different content: "
              f"{dest.relative_to(REPO)}")
        return 2
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    print(f"Wrote {dest.relative_to(REPO)} with {len(ids)} additive queue ids.")
    return 0


def report(only: str = "") -> int:
    scope_gaps = required_scope_gaps()
    if scope_gaps:
        print("refusing to judge queue coverage: required US binary scope is "
              "incomplete")
        for gap in scope_gaps:
            print(f"  MISSING {gap}")
        print(f"\nSUMMARY  {len(scope_gaps)} REQUIRED-SCOPE gap(s)")
        return 2

    by = collect()
    if not by:
        print("refusing to judge: no stubs and no records were found, which "
              "means a\nsearch failed rather than that the tree is complete.")
        return 2

    rows = []
    tot_blind = tot_stale = tot_stubs = 0
    for ov in sorted(by):
        stubs = by[ov]["stubs"]
        recs = by[ov]["records"]
        blind = sorted(stubs - set(recs))
        stale = sorted(f for f, s in recs.items()
                       if f not in stubs and s != "matched")
        rows.append((ov, len(stubs), len(recs), blind, stale))
        tot_blind += len(blind)
        tot_stale += len(stale)
        tot_stubs += len(stubs)

    if only:
        want = only.upper()
        for ov, nstub, nrec, blind, stale in rows:
            if ov != want:
                continue
            print(f"{ov}: {nstub} stub(s) in HEAD, {nrec} queue record(s)\n")
            print(f"BLIND -- stubbed but not in the queue ({len(blind)}):")
            for f in blind:
                print(f"  {f}")
            print(f"\nstale -- queued but not stubbed, not matched "
                  f"({len(stale)}):")
            for f in stale:
                print(f"  {f}")
            return 0
        print(f"no overlay named {want}. Known: "
              f"{', '.join(ov for ov, *_ in rows)}")
        return 2

    print(f"{'overlay':<18}{'stubs':>7}{'records':>9}{'BLIND':>7}{'stale':>7}")
    print("-" * 48)
    for ov, nstub, nrec, blind, stale in rows:
        flag = "  <-- " if blind else ""
        print(f"{ov:<18}{nstub:>7}{nrec:>9}{len(blind):>7}{len(stale):>7}"
              f"{flag}")
    print("-" * 48)
    print(f"{'TOTAL':<18}{tot_stubs:>7}{'':>9}{tot_blind:>7}{tot_stale:>7}")

    if tot_blind:
        print(f"\n{tot_blind} function(s) are stubbed in HEAD with NO queue "
              f"record.\nThe fleet cannot claim them and no report counts "
              f"them. Run with\n--overlay <NAME> to see the names before "
              f"deciding whether to seed them.")
    else:
        print("\nEvery stub in the tree has a queue record. The queue's scope "
              "and the\ntree's reality agree.")
    # Repeated at the END: connector callers see only the tail.
    print(f"\nSUMMARY  {tot_stubs} stubs  {tot_blind} BLIND  "
          f"{tot_stale} stale  across {len(rows)} overlay(s)")
    return 1 if tot_blind else 0


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    src_self = Path(__file__).read_text(errors="ignore")
    code = src_self.split("def self_test")[0]

    print("a src path maps to the overlay the queue names")
    ck(overlay_of_path("src/boss/bo6/richter.c") == "BOSS/BO6", "BOSS/BO6")
    ck(overlay_of_path("src/st/rno0/e_blade.c") == "ST/RNO0", "ST/RNO0")
    ck(overlay_of_path("src/dra/play.c") == "DRA", "DRA has no sub-overlay")
    ck(overlay_of_path("src/main/main.c") == "MAIN", "MAIN")
    ck(overlay_of_path("src/servant/tt_000/x.c") == "SERVANT/TT_000",
       "SERVANT/TT_000")

    print("\nthe PSP port is not part of the us build and is excluded")
    # The 126-false-LOST bug in matched_audit was this exact confusion. A
    # different team's port must never be counted as missing us work.
    ck(overlay_of_path("src/st/rno0_psp/st_common.c") is None,
       "an _psp overlay dir is skipped")
    ck(overlay_of_path("src/boss/rbo8_psp/unk_DEB8.c") is None,
       "including under boss/")
    ck(overlay_of_path("src/st/rno0/e_psp_thing.c") == "ST/RNO0",
       "but 'psp' inside a FILE name does not disqualify the file")

    print("\nonly directories the us build compiles are counted")
    real_us = us_src_dirs()
    ck(bool(real_us), f"src_path was read from the us splat configs "
                      f"({len(real_us)} dir(s))")
    ck("src/servant/fname" not in real_us,
       "servant/fname is NOT a us src dir -- it is HD-only, and counting it "
       "reported 3 permanently blind functions the us oracle cannot check")
    ck(any(d.rstrip("/") == "src/st/rchi" for d in real_us),
       "while a genuine us overlay dir IS present")

    print("\nwhole-binary omissions cannot masquerade as clean queue coverage")
    complete_manifest = "\n".join(
        f"{'0' * 40}  build/us/{name}" for name in REQUIRED_US_ARTIFACTS)
    complete_configs = set(REQUIRED_US_CONFIGS)
    ck(len(REQUIRED_US_ARTIFACTS) == 113,
       "the exact upstream US oracle contains 113 artifacts")
    ck(required_scope_gaps(complete_manifest, complete_configs) == [],
       "all 113 artifacts and their 62 configs form a complete required scope")
    missing = required_scope_gaps(
        complete_manifest.replace(
            f"{'0' * 40}  build/us/RBO8.BIN\n", ""),
        complete_configs - {"splat.us.borbo7.yaml"})
    ck(missing == [
        "artifact:RBO8.BIN", "config:splat.us.borbo7.yaml"],
       f"an omitted binary and config are both visible ({missing})")
    unexpected = required_scope_gaps(
        complete_manifest + f"\n{'0' * 40}  build/us/FUTURE.BIN",
        complete_configs | {"splat.us.future.yaml"})
    ck(unexpected == [
        "unexpected-artifact:FUTURE.BIN", "unexpected-config:splat.us.future.yaml"],
       f"scope growth cannot bypass an explicit policy update ({unexpected})")

    print("\nmatched records are not mistaken for stale ones")
    # A matched record SHOULD have no stub. Counting that as an anomaly would
    # make the stale column equal the matched count and mean nothing.
    import types
    real_stubs = globals()["stubs_in"]
    real_recs = globals()["queue_records"]
    # BOTH stubs, or the "in neither bucket" case below is untestable: a name
    # absent from the stub set is stale BY DEFINITION, so the fixture has to
    # actually stub the record it claims is healthy. The first run of this
    # test caught exactly that omission.
    globals()["stubs_in"] = lambda rev: {("src/st/rdai/a.c", "OnlyAStub"),
                                         ("src/st/rdai/a.c",
                                          "QueuedAndStubbed")}
    globals()["queue_records"] = lambda: [
        ("matched", "ST/RDAI", "AlreadyDone"),
        ("todo", "ST/RDAI", "QueuedAndStubbed"),
        ("todo", "ST/RDAI", "QueuedNotStubbed"),
    ]
    try:
        by = collect()
        stubs = by["ST/RDAI"]["stubs"]
        recs = by["ST/RDAI"]["records"]
        blind = stubs - set(recs)
        stale = {f for f, s in recs.items()
                 if f not in stubs and s != "matched"}
    finally:
        globals()["stubs_in"] = real_stubs
        globals()["queue_records"] = real_recs
    ck(blind == {"OnlyAStub"},
       f"a stub with no record is BLIND ({sorted(blind)})")
    ck("AlreadyDone" not in stale,
       "a matched record with no stub is NOT stale, it is finished")
    ck("QueuedNotStubbed" in stale,
       f"an unmatched record with no stub IS stale ({sorted(stale)})")
    ck("QueuedAndStubbed" not in blind and "QueuedAndStubbed" not in stale,
       "a record that matches its stub is in neither bucket")

    print("\nthe stub rule is imported, not reinvented")
    ck("from matched_audit import" in src_self, "imported from matched_audit")
    ck("INCLUDE_ASM" not in code.replace(
        "INCLUDE_ASM stubs", "").replace("INCLUDE_ASM in", "").replace(
        "still INCLUDE_ASM", ""),
       "no second stub regex is defined here")

    print("\nan empty result is refused rather than read as success")
    body = src_self[src_self.index("def report("):
                    src_self.index("def self_test")]
    ck("refusing to judge" in body,
       "finding nothing at all means the search broke, not that the tree is "
       "complete")

    print("\nseed generation is explicit, deterministic, and queue-independent")
    fixture = {
        "ST/RDAI": {"stubs": {"B", "A"}, "records": {"B": "todo"}},
        "BOSS/RBO1": {"stubs": {"C"}, "records": {}},
    }
    ck(blind_seed_ids(fixture) == ["us:BOSS/RBO1:C", "us:ST/RDAI:A"],
       "only blind stubs become sorted scheduler ids")
    for bad in ("git checkout", "git restore", "git add", "git commit",
                "scheduler.py\", \"report", "rmtree"):
        ck(bad not in code, f"never {bad}")
    ck('"list"' in code, "the scheduler is only listed from")
    ck('add_argument("--write-seed"' in src_self,
       "the only write path requires an explicit seed destination")

    print("\nthe verdict survives a truncated tail")
    ck("SUMMARY  " in code,
       "counts are repeated at the END; connector callers see only the tail")

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
    ap.add_argument("--overlay", default="",
                    help="list the BLIND and stale function names for one "
                         "overlay, e.g. ST/RDAI")
    ap.add_argument("--write-seed", default="", metavar="PATH",
                    help="write all BLIND stubs as an additive in-repo queue "
                         "seed manifest; never mutates the live queue")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.write_seed:
        return write_seed(a.write_seed)
    return report(a.overlay)


if __name__ == "__main__":
    raise SystemExit(main())
