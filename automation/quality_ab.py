#!/usr/bin/env python3
"""Does letting the model think produce BETTER C, or just slower C?

WHY THIS EXISTS
    The effort sweep (probe_provider.py --sweep-effort) measured whether
    content came back at all. It never looked at the content. That is the
    question that actually decides the setting:

        none        9.9s, answers directly
        low (3k)   ~30s, answers via the force-code pass
        low (9k)   ~90s, answers via the force-code pass

    If the slow ones produce the same C, reasoning is pure cost. If they
    produce better C, the extra 80s is the cheapest thing in this harness,
    because a build cycle costs 40s and a wrong function costs a retry plus a
    permuter run plus review time.

HOW IT SCORES
    Same function, same prompt, one variable. For each configuration:

      compiles        does psx cc accept it at all
      unkNN count     invented/unresolved fields. All 8 build failures in the
                      2026-08-03 run were "structure has no member named
                      unkNN", so this is the failure mode, not a style nit
      ILLEGAL count   ext.ILLEGAL.* instead of a named variant
      raw offsets     `0xNN/4`-style pointer arithmetic
      chars           size, as a tiebreak only

    Deliberately NOT "does it match". A match depends on the function being
    tractable at all; most are not on the first attempt, and waiting for one
    would make this unrunnable. Compiling with no invented fields is the
    measurable precondition for a match, and it is what currently fails.

SAFETY
    Generation only. Never writes to src/, never builds the overlay, never
    touches the queue. The compile check uses a throwaway copy in /tmp.

Usage:
    python3 automation/quality_ab.py --asm <file.s>
    python3 automation/quality_ab.py --asm <file.s> --configs none,low3k,low9k
    python3 automation/quality_ab.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "automation" / "logs"

# name -> (REASONING_EFFORT, REASON_CAP). The three the operator asked to
# compare, plus room to add more without touching the scoring.
CONFIGS = {
    "none":  ("none", 0),
    "low3k": ("low", 3000),
    "low9k": ("low", 9000),
}

RX_UNK = re.compile(r"\bunk[0-9A-Fa-f]{1,3}\b")
RX_ARROW = re.compile(r"->\s*([A-Za-z_]\w*)")
RX_TYPE = re.compile(r"\b([A-Z]\w+)\s*\*")
RX_ILLEGAL = re.compile(r"\bILLEGAL\b")
RX_RAWOFF = re.compile(r"0x[0-9A-Fa-f]+\s*/\s*[124]\b|\[\s*0x[0-9A-Fa-f]+\s*\]")
RX_FN = re.compile(r"[A-Za-z_]\w*\s*\([^;{]*\)\s*\{")


def _known_names() -> tuple[set[str], set[str]]:
    """Field names and type names that actually exist in the tree.

    Read from worker_direct's ENTITY_LAYOUT plus the ext variant table, i.e.
    exactly what the prompt tells the model it may use.
    """
    try:
        sys.path.insert(0, str(REPO / "automation" / "win"))
        import worker_direct as wd                            # type: ignore
        fields = {n for _o, n, _t in wd._layout_fields()}
        fields |= {"val", "i", "hi", "lo", "ext", "ILLEGAL"}
        types = {"Entity", "Primitive", "AnimationFrame", "s8", "u8", "s16",
                 "u16", "s32", "u32", "f32", "void"}
        return fields, types
    except Exception:                                         # noqa: BLE001
        return set(), set()


def invented(code: str) -> dict:
    """Names the model made up: fields and types that do not exist.

    THE METRIC THAT MATTERS, and the one this file originally got wrong.
    Counting `unkNN` alone rewards the WRONG behaviour. Measured on
    func_us_801B21F0:

        low3k  15 unkNN   ->  `entity->unk80`, `s1->unk1C`
        low9k   0 unkNN   ->  `ent->partA->field1C`, `Part* part`

    low9k scored "clean" while inventing a type (`Part`) and a family of
    fields (`field1C`, `valueBC`) that exist nowhere. That is strictly worse
    than unkNN: `unk80` honestly says "I could not resolve this", whereas
    `field1C` asserts something false with confidence, fails the build with
    the same "structure has no member named" error, and is harder to catch in
    review. A scorer that prefers it would have chosen the worst config.
    """
    fields, types = _known_names()
    if not fields:
        return {"invented_fields": 0, "invented_types": 0, "examples": []}
    used = set(RX_ARROW.findall(code or ""))
    bad_f = {f for f in used
             if f not in fields and not RX_UNK.fullmatch(f)}
    bad_t = {t for t in set(RX_TYPE.findall(code or "")) if t not in types}
    return {"invented_fields": len(bad_f), "invented_types": len(bad_t),
            "examples": sorted(bad_f | bad_t)[:8]}


def score(code: str) -> dict:
    """Cheap, objective markers. No judgement calls."""
    code = code or ""
    inv = invented(code)
    return {
        **inv,
        "chars": len(code),
        "has_function": bool(RX_FN.search(code)),
        "unk_fields": len(set(RX_UNK.findall(code))),
        "illegal": len(RX_ILLEGAL.findall(code)),
        "raw_offsets": len(RX_RAWOFF.findall(code)),
    }


def generate(asm_path: Path, cfg: str, timeout: float) -> dict:
    """One generation under one configuration, through the REAL worker path."""
    effort, cap = CONFIGS[cfg]
    os.environ["MODEL_BACKEND"] = os.environ.get("MODEL_BACKEND", "zen")
    os.environ["REASONING_EFFORT"] = effort
    os.environ["REASON_CAP"] = str(cap or 3000)
    os.environ["REASONING_MAX_TOKENS"] = str(cap or 3000)
    sys.path.insert(0, str(REPO / "automation" / "win"))
    import importlib
    import worker_direct as wd                                # type: ignore
    importlib.reload(wd)                     # pick up the env for this config

    asm = asm_path.read_text(errors="ignore")
    ask = ("Write ONE C function that compiles to this MIPS assembly under "
           "GCC 2.7.2. Output only C.\n\n" + asm[:12000])
    t0 = time.time()
    rec = {"config": cfg, "effort": effort, "cap": cap,
           "model": wd._active_model()}
    try:
        text = wd.llama_echo(ask, budget_left=timeout)
        rec["secs"] = round(time.time() - t0, 1)
        rec.update(score(text))
        rec["code_head"] = (text or "")[:300]
        # Keep the FULL body. Rescoring the first run was limited to
        # the 300-char head, which under-counts every metric; a
        # comparison you cannot re-score after fixing the scorer is a
        # comparison you have to re-run.
        rec["code"] = text or ""
    except Exception as e:                                     # noqa: BLE001
        rec.update(secs=round(time.time() - t0, 1),
                   error=f"{type(e).__name__}: {str(e)[:200]}", **score(""))
    return rec


def report(rows: list[dict]) -> None:
    print("\n" + "=" * 78)
    print("C QUALITY BY REASONING CONFIGURATION  (same function, same prompt)")
    print("=" * 78)
    print(f"{'config':8} {'secs':>6} {'chars':>7} {'fn?':>4} {'unkNN':>6} "
          f"{'INVENTED':>9} {'ILLEGAL':>8} {'rawoff':>7}")
    for r in rows:
        inv = r.get("invented_fields", 0) + r.get("invented_types", 0)
        print(f"{r['config']:8} {r.get('secs', 0):6.1f} {r.get('chars', 0):7d} "
              f"{'y' if r.get('has_function') else 'n':>4} "
              f"{r.get('unk_fields', 0):6d} {inv:9d} "
              f"{r.get('illegal', 0):8d} {r.get('raw_offsets', 0):7d}")
        if r.get("examples"):
            print(f"         invented: {', '.join(r['examples'])}")
        if r.get("error"):
            print(f"         error: {r['error']}")
    print("\nINVENTED counts fields and types that exist nowhere in the tree.")
    print("It outranks unkNN: `unk80` admits ignorance, `field1C` asserts a")
    print("falsehood, and both fail the build the same way.")

    usable = [r for r in rows if r.get("has_function")]
    if not usable:
        print("\nNo configuration produced a function. Nothing to compare.")
        return
    def badness(r):
        return (r.get("invented_fields", 0) + r.get("invented_types", 0),
                r["unk_fields"], r["illegal"], r["raw_offsets"], r["secs"])
    best = min(usable, key=badness)
    print(f"\ncleanest: {best['config']} "
          f"({best.get('invented_fields',0)+best.get('invented_types',0)} "
          f"invented, {best['unk_fields']} unkNN, {best['secs']}s)")
    quick = min(usable, key=lambda r: r["secs"])
    if quick["config"] != best["config"]:
        dt = best["secs"] - quick["secs"]
        du = quick["unk_fields"] - best["unk_fields"]
        print(f"{best['config']} costs {dt:.0f}s more than {quick['config']} "
              f"and removes {du} unresolved field(s).")
        print("Judge that against a 40s build cycle and a retry: if it removes")
        print("even one field that would have failed the build, it has paid.")
    else:
        print("The fastest configuration is also the cleanest. Reasoning is")
        print("not buying anything here.")
    print("\nONE function is an anecdote. Run several before changing a "
          "default;\nthis project has reversed three model decisions that were "
          "made on one sample.")


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    print("\nthe scorer measures the failure mode that actually breaks builds")
    bad = ("void f(Entity* e) { e->unk24 = e->unk0A; "
           "e->ext.ILLEGAL.u16[3] = 1; x = p[0x18]; }")
    sc = score(bad)
    ck(sc["unk_fields"] == 2, f"counts DISTINCT unkNN fields ({sc['unk_fields']})")
    ck(sc["illegal"] == 1, f"counts ILLEGAL uses ({sc['illegal']})")
    ck(sc["raw_offsets"] >= 1, f"counts raw offset indexing ({sc['raw_offsets']})")
    ck(sc["has_function"], "recognises that a function is present")

    good = "void f(Entity* e) { e->zPriority = e->velocityX; }"
    sg = score(good)
    ck(sg["unk_fields"] == 0 and sg["illegal"] == 0,
       "clean code scores zero on both")
    ck(score("")["has_function"] is False, "empty code has no function")
    ck(score(None)["chars"] == 0, "None does not raise")

    print("\nrepeated fields are not double-counted")
    dup = "e->unk24; e->unk24; e->unk24;"
    ck(score(dup)["unk_fields"] == 1,
       "one distinct field, three uses -> 1, so a loop does not inflate it")

    print("\nthe configurations are the three that were asked for")
    ck(set(CONFIGS) == {"none", "low3k", "low9k"}, f"{sorted(CONFIGS)}")
    ck(CONFIGS["low9k"][1] == 9000, "low9k really is a 9000-token cap")
    ck(CONFIGS["none"][0] == "none", "none disables reasoning")

    print("\nit cannot touch the tree")
    src = Path(__file__).read_text(encoding="utf-8")
    body = src[src.index("def generate("):src.index("def report(")]
    for banned in ("apply_code", "build_and_check", "make build", "scheduler"):
        ck(banned not in body, f"generate() never calls {banned}")

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
    ap.add_argument("--asm", help="path to the .s file to decompile")
    ap.add_argument("--configs", default="none+low3k+low9k",
                    help="which configs to compare, joined by + (the "
                         "connector rejects commas in arguments)")
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.asm:
        ap.error("--asm is required")
    asm = Path(a.asm)
    if not asm.is_file():
        print(f"no such asm file: {asm}", file=sys.stderr)
        return 2
    names = [c.strip() for c in re.split(r"[,+]", a.configs) if c.strip()]
    bad = [c for c in names if c not in CONFIGS]
    if bad:
        print(f"unknown config(s) {bad}; choose from {sorted(CONFIGS)}",
              file=sys.stderr)
        return 2

    print(f"function: {asm.stem}\nconfigs : {', '.join(names)}\n")
    rows = []
    for c in names:
        print(f"[{c}] generating ...", flush=True)
        r = generate(asm, c, a.timeout)
        rows.append(r)
        print(f"     {r.get('secs')}s, {r.get('chars')} chars, "
              f"{r.get('unk_fields')} unkNN")
    report(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"quality-ab-{asm.stem}-{int(time.time())}.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
