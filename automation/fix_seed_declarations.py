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
import tempfile

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
    original_lines = set(body.splitlines())
    added = [line.strip() for line in new_body.splitlines()
             if line not in original_lines and line.strip().endswith(";")]
    return banner + new_body, added


def _called_symbols(text: str) -> list[str]:
    """Names the seed writer may need to declare for the permuter typemap."""
    _banner, body = split_banner(text)
    stubs = set(wd._RX_STUB_IN_FILE.findall(body))
    called = sorted(
        name for name in stubs
        if re.search(rf"\b{re.escape(name)}\s*\(", body))
    called += wd._undeclared_calls(body, body, skip=set(called))
    return list(dict.fromkeys(called))


def scan_seed_texts(items: list[tuple[str, str]]) -> list[tuple[str, str, list[str]]]:
    """Return every repaired payload after one batched declaration lookup.

    Calling fix_one independently once per seed made a corpus check run one
    repository grep per seed. Prewarming worker_direct's declaration cache in
    chunks keeps the check exact while reducing the scan to a few greps.
    """
    symbols = list(dict.fromkeys(
        symbol for _name, text in items for symbol in _called_symbols(text)))
    for start in range(0, len(symbols), 40):
        chunk = symbols[start:start + 40]
        wd.lookup_declarations(chunk, limit=len(chunk))
    return [(name, *fix_one(text)) for name, text in items]


def publish_fixed_seed(path: str, text: str) -> str:
    """Publish a declaration repair without overwriting prior evidence."""
    return wd._publish_versioned_artifact(path, text, "permuter seed")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="write the changes (default is a dry run)")
    ap.add_argument("--seed", action="append", default=[], metavar="NAME",
                    help="operate on one exact candidates/ filename; repeatable")
    ap.add_argument("--from-prior", action="store_true",
                    help="rebuild named seeds from the version immediately "
                         "before their current stable generation")
    ap.add_argument("--from-back", type=int, default=0, metavar="N",
                    help="rebuild named seeds from N preserved generations back")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not os.path.isdir(SEEDS):
        print(f"no seed directory at {SEEDS}")
        return 0

    names = sorted(f for f in os.listdir(SEEDS) if f.endswith(".c"))
    if args.seed:
        requested = set(args.seed)
        missing = sorted(requested - set(names))
        if missing:
            print("unknown seed(s): " + ", ".join(missing))
            return 1
        names = [name for name in names if name in requested]
    if args.from_prior and args.from_back:
        print("choose only one of --from-prior and --from-back")
        return 1
    history_back = 1 if args.from_prior else args.from_back
    if history_back < 0:
        print("--from-back must be positive")
        return 1
    if history_back and (not args.apply or not args.seed):
        print("history rebuild requires --apply and at least one --seed")
        return 1
    if not names:
        print(f"no seeds under {SEEDS}")
        return 0

    changed = 0
    print(f"{len(names)} seed(s) under automation/candidates/\n")
    items = []
    for n in names:
        p = os.path.join(SEEDS, n)
        try:
            source = p
            if history_back:
                versions = wd._artifact_history_versions(p)
                if len(versions) <= history_back:
                    print(f"  !! {n}: only {len(versions)} preserved generation(s), "
                          f"cannot go back {history_back}")
                    continue
                with open(p, "rb") as stable, open(versions[-1], "rb") as latest:
                    if stable.read() != latest.read():
                        print(f"  !! {n}: stable bytes do not match latest history")
                        continue
                source = versions[-1 - history_back]
            with open(source, encoding="utf-8", errors="replace") as f:
                items.append((n, f.read()))
        except OSError as e:
            print(f"  !! {n}: {e}")
    for n, new, added in scan_seed_texts(items):
        if not added and not history_back:
            continue
        changed += 1
        print(f"  {n}")
        if added:
            for a in added:
                print(f"      + {a}")
        else:
            print("      restored from prior generation; no declaration needed")
        if args.apply:
            try:
                p = os.path.join(SEEDS, n)
                published = publish_fixed_seed(p, new)
                print(f"      seed={published}")
            except OSError as e:
                print(f"      !! could not write: {e}")

    print()
    if not changed:
        print("no seed needs a declaration added")
    elif args.apply:
        print(f"{changed} seed(s) versioned. Add each printed immutable seed= "
              f"path to its queue record before re-importing.")
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

        print("\napplying a fix versions evidence instead of overwriting it")
        old_repo = wd.WIN_REPO
        try:
            with tempfile.TemporaryDirectory() as td:
                wd.WIN_REPO = td
                path = os.path.join(td, "automation", "candidates", "us_X.c")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                original = b"/* original seed */\nvoid f(void) {}\n"
                with open(path, "wb") as handle:
                    handle.write(original)
                published = publish_fixed_seed(
                    path, "/* repaired seed */\nvoid f(void) { helper(); }\n")
                versions = wd._artifact_history_versions(path)
                ck("/history/" in published.replace("\\", "/"),
                   "the returned queue path is immutable")
                retained = []
                for item in versions:
                    with open(item, "rb") as handle:
                        retained.append(handle.read())
                ck(original in retained,
                   "the prior stable seed survives byte-identical in history")
                ck(len(versions) == 2,
                   "the original and repaired versions both exist")
        finally:
            wd.WIN_REPO = old_repo
    finally:
        wd.lookup_declarations = real

    print("\nordinary header prototypes win over an implicit-int fallback")
    declarations = wd.lookup_declarations(
        ["InitializeEntity", "rsin", "DestroyEntity"])
    ck(any("void InitializeEntity(" in line for line in declarations),
       f"InitializeEntity prototype found ({declarations})")
    ck(any("int rsin(" in line for line in declarations),
       f"rsin prototype found ({declarations})")
    ck(any("void DestroyEntity(Entity*" in line for line in declarations),
       f"US DestroyEntity prototype wins ({declarations})")
    ck(not any("s32 DestroyEntity();" in line for line in declarations),
       "the Saturn declaration is excluded")
    typed_seed = ('#include "stage.h"\n'
                  'void f(void) { InitializeEntity(0); rsin(0); }\n')
    typed_out, typed_added = fix_one(typed_seed)
    ck("void InitializeEntity(u16 arg0[]);" in typed_out,
       "the real void prototype is inserted")
    ck("int rsin(int a);" in typed_out,
       "the SDK prototype is inserted")
    ck("extern int InitializeEntity();" not in typed_out,
       "no conflicting implicit-int declaration is invented")
    ck(len(typed_added) == 2,
       f"ordinary prototypes are reported as repairs ({typed_added})")

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
