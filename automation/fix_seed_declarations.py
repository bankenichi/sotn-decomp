#!/usr/bin/env python3
"""Retrofit stub declarations onto permuter seeds written before the fix.

WHY THIS EXISTS
    worker_direct._declare_stub_siblings() now declares the same-file
    INCLUDE_ASM stubs a seed calls, because INCLUDE_ASM expands to nothing
    under PERMUTER and decomp-permuter's typemap then raises KeyError on every
    mutation that touches the call. Six BOSS/BO0 records lost 3% to 17% of
    their search that way and were deferred as `seed-bug`.

    That fix only helps seeds written from now on. The seeds already sitting
    in automation/candidates/ were written by the old code, so requeueing
    those six records would re-import the same undeclared seed and reproduce
    the same KeyErrors. This applies the identical function to seeds on disk.

    It calls worker_direct._declare_stub_siblings directly rather than
    reimplementing it. A second copy of the rule would drift, and this is
    exactly the class of bug that has already bitten this repo once.

DEFAULT IS A DRY RUN. Nothing is written without --apply.

    python3 automation/fix_seed_declarations.py            # report
    python3 automation/fix_seed_declarations.py --apply     # write
    python3 automation/fix_seed_declarations.py --self-test
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "win"))
os.environ.setdefault("MODEL_BACKEND", "zen")

import worker_direct as wd  # noqa: E402

SEEDS = os.path.join(HERE, "candidates")

# The seed carries a banner comment; the C starts after it. The banner is a
# single /* ... */ block written by save_candidate.
RX_BANNER = re.compile(r"\A\s*/\*.*?\*/\s*", re.S)


def split_banner(text: str) -> tuple[str, str]:
    """(banner, body). A seed with no banner is all body."""
    m = RX_BANNER.match(text)
    return (m.group(0), text[m.end():]) if m else ("", text)


def fix_one(text: str) -> tuple[str, list[str]]:
    """Returns (new_text, declarations_added)."""
    banner, body = split_banner(text)
    # The "code" argument decides which stubs count as called. Using the whole
    # body is right here: any call anywhere in the seed can be mutated.
    new_body = wd._declare_stub_siblings(body, body)
    if new_body == body:
        return text, []
    added = [l.strip() for l in new_body.splitlines()
             if l.strip().startswith("extern") and l not in body.splitlines()]
    return banner + new_body, added


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="write the changes (default is a dry run)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not os.path.isdir(SEEDS):
        print(f"no seed directory at {SEEDS}")
        return 0

    names = sorted(f for f in os.listdir(SEEDS) if f.endswith(".c"))
    if not names:
        print(f"no seeds under {SEEDS}")
        return 0

    changed = 0
    print(f"{len(names)} seed(s) under automation/candidates/\n")
    for n in names:
        p = os.path.join(SEEDS, n)
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as e:
            print(f"  !! {n}: {e}")
            continue
        new, added = fix_one(text)
        if not added:
            continue
        changed += 1
        print(f"  {n}")
        for a in added:
            print(f"      + {a}")
        if args.apply:
            try:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(new)
            except OSError as e:
                print(f"      !! could not write: {e}")

    print()
    if not changed:
        print("no seed needs a declaration added")
    elif args.apply:
        print(f"{changed} seed(s) rewritten. Set the matching records back to "
              f"`near` so the supervisor re-imports them.")
    else:
        print(f"{changed} seed(s) WOULD be rewritten. Nothing was written; "
              f"re-run with --apply.")
    return 0


def self_test() -> int:
    fails = []

    def ck(cond, label):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    seed = ('/* PERMUTER SEED -- compiled and linked, bytes differ.\n'
            '   record : us:BOSS/BO0:func_us_801B1DDC */\n'
            '#include "bo0.h"\n\n'
            'INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B171C);\n\n'
            's32 f(Entity* e) { return func_us_801B171C(e, 1, 2, 3); }\n')

    real = wd.lookup_declarations
    wd.lookup_declarations = lambda syms, limit=40: []
    try:
        print("the banner survives and stays first")
        new, added = fix_one(seed)
        ck(new.startswith("/* PERMUTER SEED"), "banner is still at the top")
        ck("record : us:BOSS/BO0:func_us_801B1DDC" in new, "and is intact")

        print("\nthe declaration is added and reported")
        ck("extern int func_us_801B171C();" in new, "declaration present")
        ck(added == ["extern int func_us_801B171C();"],
           f"and reported back to the caller ({added})")

        print("\nthe declaration is inside the body, not inside the banner")
        ck(new.index("extern int func_us_801B171C();") > new.index("*/"),
           "after the banner closes")
        ck(new.index("extern int func_us_801B171C();")
           > new.index('#include "bo0.h"'), "and after the include")

        print("\nrunning it twice changes nothing the second time")
        twice, added2 = fix_one(new)
        ck(added2 == [], f"no second declaration ({added2})")
        ck(twice == new, "byte-identical, so --apply is idempotent")

        print("\na seed needing nothing is returned untouched")
        plain = "/* banner */\n#include \"x.h\"\ns32 f(void){return 0;}\n"
        out, add3 = fix_one(plain)
        ck(out == plain and add3 == [], "unchanged")

        print("\na seed with no banner at all still works")
        nb = seed[seed.index('#include'):]
        out4, add4 = fix_one(nb)
        ck(add4 == ["extern int func_us_801B171C();"],
           "declaration still added")
        ck(not out4.startswith("extern"), "and not before the include")
    finally:
        wd.lookup_declarations = real

    print()
    if fails:
        print(f"{len(fails)} FAILED:")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
