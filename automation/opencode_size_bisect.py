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

# Preferred order when the live list is available: least-tried first, so a
# newly published model gets tested before one we already have data on.
# big-pickle is deliberately last; it is a known failure and only here as a
# control, to confirm the harness reproduces the bug it is meant to explain.
PREFERRED = [
    "laguna-s",
    "ling-3.0",
    "deepseek-v4",
    "nemotron-3-ultra",
    "mimo-v2.5",
    "north-mini-code",
    "big-pickle",
]

# Fallback only. The real list comes from `opencode models opencode`, because
# hardcoded IDs go stale every time Zen rotates its free promotions, and a
# typo'd ID fails in a way that looks exactly like the bug under investigation.
MODELS_FALLBACK = [
    "opencode/north-mini-code-free",
    "opencode/nemotron-3-ultra-free",
    "opencode/mimo-v2.5-free",
]

# Straddles the real range. Real prompts are 6k-11k; 500 is known-good territory.
SIZES = [500, 2000, 4000, 6000, 9000, 11000]

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


def run_one(model: str, size: int) -> dict:
    prompt = make_prompt(size)
    env = dict(os.environ, OPENCODE_CONFIG=str(CONFIG))
    argv = ["opencode", "run", "--model", model, "--agent", "raw", "--auto",
            prompt]
    t0 = time.time()
    try:
        p = subprocess.run(argv, cwd=str(REPO), env=env, text=True,
                           stdin=subprocess.DEVNULL, capture_output=True,
                           encoding="utf-8", errors="replace", timeout=TIMEOUT)
        out = (p.stdout or "").strip()
        return {"model": model, "size": size, "rc": p.returncode,
                "chars": len(out), "secs": time.time() - t0,
                "head": out[:40].replace("\n", " "),
                "err": (p.stderr or "").strip()[-120:]}
    except subprocess.TimeoutExpired:
        return {"model": model, "size": size, "rc": None, "chars": 0,
                "secs": time.time() - t0, "head": "", "err": "TIMEOUT"}


def sweep(model: str, sizes: list[int]) -> list[dict]:
    rows = []
    for s in sizes:
        r = run_one(model, s)
        rows.append(r)
        state = ("TIMEOUT" if r["err"] == "TIMEOUT"
                 else "EMPTY" if r["chars"] == 0 else "ok")
        print(f"  {model.split('/')[-1]:24} {s:6} chars  "
              f"{state:8} {r['chars']:5}b {r['secs']:6.1f}s  {r['head']}",
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
    a = ap.parse_args()

    if not CONFIG.exists():
        print(f"missing {CONFIG}; the raw agent will not resolve")
        return 2

    if a.sizes:
        sizes = [int(x) for x in a.sizes.replace(",", " ").split()]
    elif a.quick:
        sizes = [500, 6000, 11000]
    else:
        sizes = SIZES

    if a.models:
        models = a.models.replace(",", " ").split()
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
        for rows in ex.map(lambda m: sweep(m, sizes), models):
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
