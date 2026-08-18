#!/usr/bin/env python3
"""Does a verified worker match survive until root-owned Git landing?"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "win"))
os.environ.setdefault("MODEL_BACKEND", "zen")

import worker_direct as wd  # noqa: E402


FAILS: list[str] = []


def check(condition: bool, label: str, detail: str = "") -> None:
    print(("  ok   " if condition else "  FAIL ") + label
          + ("" if condition else "   " + detail))
    if not condition:
        FAILS.append(label)


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    old_repo = wd.WIN_REPO
    rec = {
        "id": "us:BOSS/BO6:TestVerifiedLanding",
        "function": "TestVerifiedLanding",
    }
    ctx = {
        "src_rel": "src/boss/bo6/test_verified_landing.c",
        "asm_rel": "boss/bo6/nonmatchings/test_verified_landing",
    }
    original = (
        '#include "common.h"\r\n\r\n'
        'INCLUDE_ASM("boss/bo6/nonmatchings/test_verified_landing", '
        'TestVerifiedLanding);\r\n'
    )
    code = (
        "void TestVerifiedLanding(void) {\n"
        "    g_CurrentEntity->step = 1;\n"
        "}\n"
    )
    proof = "81/81 OK; sha1=" + ("abc123" * 400)

    try:
        wd.WIN_REPO = str(tmp)

        print("a verified replacement is preserved outside src")
        got = wd.require_matched_landing(
            rec, code, 3, proof, ctx, original)
        path = tmp / got
        check(got.startswith("automation/landings/"),
              f"the path is owned by automation/landings ({got})")
        check(path.is_file(), "the snapshot exists")
        with open(path, encoding="utf-8", newline="") as f:
            first = f.read()
        check("TestVerifiedLanding" in first,
              "the record and replacement are both present")
        check("exact stub replacement block" in first,
              "the artifact identifies what its payload represents")
        payload = first.split("*/\n", 1)[1]
        check(code.replace("\n", "\r\n") in payload,
              "the replacement block preserves the source newline convention")
        match = re.search(r"^   proof  : (.+)$", first, re.M)
        decoded = json.loads(match.group(1)) if match else ""
        check(decoded == proof,
              "the complete proof survives beyond the old evidence limits",
              f"{len(decoded)}/{len(proof)} chars")

        print("\na later landing never overwrites the earlier one")
        first_bytes = path.read_bytes()
        got2 = wd.require_matched_landing(
            rec, code.replace(" = 1", " = 2"), 4, proof + "-second",
            ctx, original)
        path2 = tmp / got2
        check(got2 != got and got2.endswith(".2.c"),
              f"the second result gets a numeric suffix ({got2})")
        check(path.read_bytes() == first_bytes,
              "the first snapshot remains byte-identical")
        check(path2.is_file(), "the second snapshot is also retained")

        print("\npreservation failure blocks the matched transaction")
        real_save = wd.save_matched
        try:
            wd.save_matched = lambda *args, **kwargs: ""
            raised = ""
            try:
                wd.require_matched_landing(
                    rec, code, 1, proof, ctx, original)
            except RuntimeError as exc:
                raised = str(exc)
            check("refusing matched report" in raised,
                  "an unwritable archive fails closed before queue reporting",
                  raised)
        finally:
            wd.save_matched = real_save

        print("\nthe live match path orders preservation, report, and cleanup")
        source = Path(wd.__file__).read_text(encoding="utf-8", errors="replace")
        branch = source[source.index('print(f"[worker] MATCHED {fn}")'):]
        marker = "# " + chr(96) + "best" + chr(96) + " is the LAST verdict"
        branch = branch[:branch.index(marker)]
        save_i = branch.index("require_matched_landing(")
        report_i = branch.index('sched("report"')
        matched_i = branch.index("matched = True")
        clear_i = branch.rindex("journal_clear()")
        check(save_i < report_i < matched_i < clear_i,
              "save precedes matched report, which precedes journal clearing")
        fail_block = branch[save_i:matched_i]
        check("restore(ctx, original)" in fail_block and "raise" in fail_block,
              "a save or report failure restores inside the locked transaction")
        check("landing=" in branch,
              "the durable queue note names the snapshot")

    finally:
        wd.WIN_REPO = old_repo
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED:")
        for failure in FAILS:
            print("  - " + failure)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
