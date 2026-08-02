#!/usr/bin/env python3
"""Does the OpenCode CLI stop answering above some prompt size?

WHY THIS EXISTS
    The cli fleet produces nothing on real work. Twelve attempts across three
    functions returned either `rc=0` with zero bytes or a 382s timeout. Four
    explanations were ruled out with evidence (see
    automation/opencode/ZEN-FREE-MODELS.md): not quota, not auth, not agent
    resolution, not stdout routing, and NOT the model, since two different
    models fail identically.

    One variable is left and has never been tested. A 27-character prompt is
    answered instantly. Every prompt a real function generates is 6k-11k
    characters and returns nothing. This measures that directly instead of
    guessing at it a fifth time.

WHAT IT CONTROLS FOR
    Size is the only thing that varies. The model, the agent, the working
    directory and the config are fixed, and the filler is benign repeated text
    so a larger prompt is not also a harder question. Every prompt asks for the
    same two-character answer, so any reply other than OK is itself a finding.

    Models run in PARALLEL, one worker each, which also reproduces the fleet's
    concurrency. If results are clean here but the fleet still fails, the
    difference is concurrency or prompt content, not length.

Run from the repo root, where the opencode CLI is reachable:
    python3 automation/opencode_size_bisect.py
    python3 automation/opencode_size_bisect.py --sizes 500,4000,9000
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "automation" / "opencode" / "opencode.json"

# Order: the models we actually run fleets on come FIRST.
#
# This was reversed once, to test the newest promotions first. That was wrong.
# The 2026-08-02 fleet run settled which models work, so the open question is no
# longer "which of these is any good" but "how large a prompt can the two
# working ones take before they go quiet" -- and a default `--top 3` must spend
# the shared quota answering THAT.
#
# The known-bad four are still listed, after, so `--top 7` sweeps everything and
# reproduces the failure as a control. Anything the CLI reports that is not
# named here sorts last but is still tested, so a new promotion is never
# silently skipped.
PREFERRED = [
    "deepseek-v4",       # works; tolerated 12k in the 07-21 bake-off
    "nemotron-3-ultra",  # works
    "mimo-v2.5",         # works, lower volume
    "ling-3.0",          # rc=0, 0 chars at 9936
    "laguna-s",          # no output at all at 11249
    "north-mini-code",   # empty body, plus tool-call roleplay
    "big-pickle",        # empty body; the original control
]

# Fallback only. The real list comes from `opencode models opencode`, because
# hardcoded IDs go stale every time Zen rotates its free promotions, and a
# typo'd ID fails in a way that looks exactly like the bug under investigation.
MODELS_FALLBACK = [
    "opencode/north-mini-code-free",
    "opencode/nemotron-3-ultra-free",
    "opencode/mimo-v2.5-free",
]

# The first four fleet functions produced 5k-11k prompts, which made 11k look
# like the ceiling worth testing. It is not. Measured over the 308 us functions
# still on INCLUDE_ASM (the worker feeds the .s file verbatim, so asm chars ==
# raw .s size, calibrated exactly against four observed runs):
#
#     p50 asm  8.8k -> ~13k prompt        59% of remaining exceed 11k
#     p75 asm   21k -> ~29k prompt        37% exceed 20k
#     p90 asm   41k -> ~55k prompt        15% exceed 40k
#     max  asm 120k -> ~156k prompt       func_us_801B365C, 1974 instructions
#
# So a clean sweep to 11k says nothing about the majority of the work left.
SIZES = [500, 2000, 4000, 6000, 9000, 11000]
BIG_SIZES = [11000, 20000, 40000, 80000, 120000]

# prompt ~= asm * 1.28 + 2100, from four observed runs: the m2c draft ran
# 0.20-0.34 of asm length, and the fixed sections cost 1900-2700 chars.
DRAFT_RATIO = 1.28
FIXED_OVERHEAD = 2100

ASK = "Reply with the single word OK and nothing else.\n"

# Benign filler that still looks like the tokens a real prompt carries, so this
# is not accidentally testing how the model handles a wall of one repeated
# character. It carries no question, so it cannot make the task harder.
FILLER_LINE = "/* 1A94 80181A94 24020001 */  addiu $v0, $zero, 1\n"

# Generous but far below the worker's 382s. A call that needs longer than this
# is useless to the fleet anyway.
TIMEOUT = 120


def discover_models() -> tuple[list[str], str]:
    """Ask the CLI what exists rather than trusting a list in this file.

    A model ID that Zen has retired fails with an empty response and rc=0,
    which is indistinguishable from the bug being investigated. Discovering
    the list removes that whole class of false positive.
    """
    env = dict(os.environ, OPENCODE_CONFIG=str(CONFIG))
    try:
        p = subprocess.run(["opencode", "models", "opencode"], cwd=str(REPO),
                           env=env, text=True, capture_output=True,
                           stdin=subprocess.DEVNULL, timeout=60,
                           encoding="utf-8", errors="replace")
    except Exception as e:
        return MODELS_FALLBACK, f"discovery failed ({e}); using fallback list"
    ids = [ln.strip() for ln in (p.stdout or "").splitlines()
           if ln.strip().startswith("opencode/")]
    if not ids:
        return MODELS_FALLBACK, "discovery returned no ids; using fallback list"

    def rank(mid: str) -> int:
        bare = mid.split("/", 1)[-1]
        for i, pref in enumerate(PREFERRED):
            if bare.startswith(pref):
                return i
        return len(PREFERRED)  # unknown/new model: test it, after the named ones

    return sorted(ids, key=rank), f"discovered {len(ids)} models from the CLI"


def make_prompt(n: int) -> str:
    body = (FILLER_LINE * ((n // len(FILLER_LINE)) + 1))[:n]
    return f"{ASK}Ignore the following reference material entirely.\n{body}"


def cap_for(size: int) -> int:
    """Bigger prompts legitimately need longer, so a flat cap would read as a
    size failure when it is really the stopwatch. Scales, floored at TIMEOUT."""
    return max(TIMEOUT, size // 300)


def run_one(model: str, size: int, use_stdin: bool = False) -> dict:
    """One call. use_stdin moves the prompt off the command line.

    The command line is where the 32767-char Windows CreateProcess limit
    lives, so this is the candidate fix, not a stylistic preference.
    """
    prompt = make_prompt(size)
    env = dict(os.environ, OPENCODE_CONFIG=str(CONFIG))
    argv = ["opencode", "run", "--model", model, "--agent", "raw", "--auto"]
    if not use_stdin:
        argv.append(prompt)
    t0 = time.time()
    try:
        p = subprocess.run(argv, cwd=str(REPO), env=env, text=True,
                           input=prompt if use_stdin else None,
                           stdin=None if use_stdin else subprocess.DEVNULL,
                           capture_output=True,
                           encoding="utf-8", errors="replace",
                           timeout=cap_for(size))
        out = (p.stdout or "").strip()
        return {"model": model, "size": size, "rc": p.returncode,
                "chars": len(out), "secs": time.time() - t0,
                "head": out[:40].replace("\n", " "),
                "err": (p.stderr or "").strip()[-120:]}
    except subprocess.TimeoutExpired:
        return {"model": model, "size": size, "rc": None, "chars": 0,
                "secs": time.time() - t0, "head": "", "err": "TIMEOUT"}


def sweep(model: str, sizes: list[int], use_stdin: bool = False) -> list[dict]:
    rows = []
    for s in sizes:
        r = run_one(model, s, use_stdin)
        rows.append(r)
        state = ("TIMEOUT" if r["err"] == "TIMEOUT"
                 else "EMPTY" if r["chars"] == 0 else "ok")
        # On failure show stderr and the exit code, not just "EMPTY". A run
        # that dies in 0.0s is the process never starting, which is a totally
        # different fault from a model returning an empty body, and printing
        # only "EMPTY" hides that distinction completely.
        extra = r["head"] if r["chars"] else f"rc={r['rc']} {r['err']}"
        print(f"  {model.split('/')[-1]:24} {s:6} chars  "
              f"{state:8} {r['chars']:5}b {r['secs']:6.1f}s  {extra}",
              flush=True)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    # No commas in any default: the connector's argument filter rejects them,
    # so this stays runnable through run_analysis without a shell.
    ap.add_argument("--sizes", default="")
    ap.add_argument("--models", default="")
    ap.add_argument("--top", type=int, default=4,
                    help="how many models to sweep; also the parallelism")
    ap.add_argument("--quick", action="store_true",
                    help="three sizes instead of six, for a fast re-check")
    ap.add_argument("--stdin", action="store_true",
                    help="pipe the prompt instead of passing it as argv, to "
                         "test the 32767-char Windows command-line limit")
    ap.add_argument("--big", action="store_true",
                    help="sweep 11k-120k, the range 59%% of remaining functions "
                         "actually land in")
    a = ap.parse_args()

    if not CONFIG.exists():
        print(f"missing {CONFIG}; the raw agent will not resolve")
        return 2

    if a.sizes:
        sizes = [int(x) for x in a.sizes.replace(",", " ").replace("+", " ").replace("-", " ").split()]
    elif a.big:
        sizes = BIG_SIZES
    elif a.quick:
        sizes = [500, 6000, 11000]
    else:
        sizes = SIZES

    if a.models:
        # NOT split on "-": every model id contains hyphens.
        models = a.models.replace(",", " ").replace("+", " ").split()
        note = "models given on the command line"
    else:
        models, note = discover_models()
        models = models[:max(1, a.top)]
    print(note)
    print("  " + "\n  ".join(models))
    print()

    print(f"{len(models)} models x {len(sizes)} sizes, models in parallel, "
          f"{TIMEOUT}s cap per call")
    print("Every prompt asks for the same 2-character answer. Only size varies.")
    print()

    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as ex:
        for rows in ex.map(lambda m: sweep(m, sizes, a.stdin), models):
            results.extend(rows)

    print()
    print("threshold per model (largest size that answered):")
    verdicts = []
    for m in models:
        good = [r["size"] for r in results if r["model"] == m and r["chars"] > 0]
        bad = [r["size"] for r in results if r["model"] == m and r["chars"] == 0]
        name = m.split("/")[-1]
        if good and not bad:
            verdicts.append(f"  {name:24} answered at EVERY size up to {max(good)}")
        elif good:
            verdicts.append(f"  {name:24} ok<={max(good)}, failed from {min(bad)}")
        else:
            verdicts.append(f"  {name:24} FAILED AT EVERY SIZE, including {min(bad)}")
    print("\n".join(verdicts))

    print()
    any_ok = any(r["chars"] > 0 for r in results)
    small_ok = any(r["chars"] > 0 and r["size"] <= 2000 for r in results)
    # The decisive signature, and the reason stderr is printed above: the
    # process never starts. Windows CreateProcess caps a command line at 32767
    # chars, and the prompt is passed as an argv element to opencode.exe.
    if any(r["chars"] == 0 and "Invalid argument" in (r["err"] or "")
           for r in results):
        print("READ: opencode.exe returned 'Invalid argument' in ~0.0s. That is "
              "the 32767-char Windows CreateProcess command-line limit, not the "
              "model and not the content. Move the prompt off argv (--stdin), "
              "or run a native Linux opencode inside WSL where the per-argument "
              "limit is 131072.")
        return 0
    if not any_ok:
        print("READ: nothing answered at any size, including small ones. Size is "
              "NOT the variable. Suspect the argv/exec path or the environment "
              "this script inherits versus an interactive shell.")
    elif small_ok and not any(r["chars"] > 0 and r["size"] >= 6000
                              for r in results):
        print("READ: small prompts answer, real-sized ones do not. Size IS the "
              "variable. Fix by shrinking the prompt (the m2c draft is the most "
              "expendable large block) or by passing the prompt on stdin rather "
              "than as an argv element.")
    else:
        print("READ: large prompts answered here but the fleet still fails, so "
              "length is not sufficient to explain it. Next suspects, in order: "
              "concurrency, and prompt CONTENT. Bisect the prompt sections.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
