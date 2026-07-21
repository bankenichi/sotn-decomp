#!/usr/bin/env python3
"""
worker.py: one autonomous volume-engine worker.

Loop: claim the next todo from scheduler.py, run OpenCode headless on that
function inside its own git worktree, read the RESULT.json the agent writes, and
report the outcome back to the scheduler. Never edits the queue directly; the
scheduler is the single writer.

Tiering: attempts Tier 0 (local model) first; if the result is not matched/near,
re-attempts at Tier 1 (a cheap cloud model) when OPENCODE_MODEL_T1 is set. On
still-no-near it reports 'escalated' for the Claude harness to pick up.

Usage:
  python3 automation/worker.py once                 # one function then exit
  python3 automation/worker.py loop --max 50        # up to 50, then exit
  python3 automation/worker.py loop                 # until the queue is empty

Env:
  WORKER_NAME        worker id (default: host-pid)
  OPENCODE_CMD       opencode binary (default: opencode)
  OPENCODE_AGENT     agent name (default: sotn-matcher)
  OPENCODE_MODEL     Tier 0 model ref (default: llama/qwen)
  OPENCODE_MODEL_T1  Tier 1 model ref (optional, e.g. openrouter/...)
  OPENCODE_CONFIG    path to opencode.json (default: automation/opencode/opencode.json)
  MAX_ITERS          per-function edit cap passed to the agent (default: 20)
  NEAR_THRESHOLD     score at/above which a result counts as 'near' (default: 90)
  RUN_TIMEOUT        seconds per OpenCode invocation (default: 3600)
  WORKER_DRYRUN=1    do not call OpenCode; simulate an escalated result
"""
from __future__ import annotations
import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(os.environ.get("SOTN_REPO", Path(__file__).resolve().parents[1]))
SCHEDULER = REPO / "automation" / "scheduler.py"
WORKER_NAME = os.environ.get("WORKER_NAME", f"{socket.gethostname()}-{os.getpid()}")
OPENCODE_CMD = os.environ.get("OPENCODE_CMD", "opencode")
OPENCODE_AGENT = os.environ.get("OPENCODE_AGENT", "sotn-matcher")
MODEL_T0 = os.environ.get("OPENCODE_MODEL", "llama/qwen")
MODEL_T1 = os.environ.get("OPENCODE_MODEL_T1", "")
OPENCODE_CONFIG = os.environ.get(
    "OPENCODE_CONFIG", str(REPO / "automation" / "opencode" / "opencode.json"))
MAX_ITERS = int(os.environ.get("MAX_ITERS", "20"))
NEAR_THRESHOLD = float(os.environ.get("NEAR_THRESHOLD", "90"))
RUN_TIMEOUT = float(os.environ.get("RUN_TIMEOUT", "3600"))
DRYRUN = os.environ.get("WORKER_DRYRUN", "") not in ("", "0", "false", "False")


def sched(*args: str) -> str:
    out = subprocess.run([sys.executable, str(SCHEDULER), *args],
                         cwd=str(REPO), capture_output=True, text=True, check=True)
    return out.stdout.strip()


def claim_next() -> dict | None:
    rec = json.loads(sched("next", "--worker", WORKER_NAME, "--worktree"))
    return None if rec.get("status") == "empty" else rec


def build_task_prompt(rec: dict) -> str:
    return (
        f"Match one SOTN function to a byte-for-byte identical build.\n"
        f"build={rec['build']} overlay={rec['overlay']} function={rec['function']}\n"
        f"You are in the git worktree for this function; edit only here.\n"
        f"Iteration cap: {MAX_ITERS}. Follow the loop and rules in your agent prompt.\n"
        f"When you stop, write a file named RESULT.json in the worktree root with:\n"
        f'  {{"status": "matched|near|escalated", "best_score": <0-100>, '
        f'"notes": "<first divergence and cause>"}}\n'
        f"status matched requires asm-differ 100 percent and a green build. "
        f"Use status near for a high score with residual instructions. "
        f"Use status escalated if you cannot get near within the cap."
    )


def run_opencode(workdir: Path, prompt: str, model: str) -> None:
    env = dict(os.environ)
    env["OPENCODE_CONFIG"] = OPENCODE_CONFIG
    argv = [OPENCODE_CMD, "run", prompt, "--agent", OPENCODE_AGENT, "--model", model]
    subprocess.run(argv, cwd=str(workdir), env=env, timeout=RUN_TIMEOUT)


def read_result(workdir: Path) -> dict | None:
    p = workdir / "RESULT.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None


def attempt(rec: dict) -> dict:
    """Run the tier ladder for one record and return a normalized result dict."""
    workdir = REPO / rec["worktree"]
    prompt = build_task_prompt(rec)

    if DRYRUN:
        return {"status": "escalated", "best_score": 0, "tier": 0,
                "notes": "WORKER_DRYRUN: no OpenCode invocation"}

    # Tier 0
    for p in (workdir / "RESULT.json",):
        if p.exists():
            p.unlink()
    run_opencode(workdir, prompt, MODEL_T0)
    res = read_result(workdir) or {"status": "escalated", "best_score": 0,
                                    "notes": "no RESULT.json from Tier 0"}
    res["tier"] = 0
    if res.get("status") == "matched" or float(res.get("best_score", 0)) >= NEAR_THRESHOLD:
        if res.get("status") != "matched":
            res["status"] = "near"
        return res

    # Tier 1 (optional)
    if MODEL_T1:
        run_opencode(workdir, prompt, MODEL_T1)
        res1 = read_result(workdir)
        if res1:
            res1["tier"] = 1
            if res1.get("status") == "matched" or \
               float(res1.get("best_score", 0)) >= NEAR_THRESHOLD:
                if res1.get("status") != "matched":
                    res1["status"] = "near"
            else:
                res1["status"] = "escalated"
            return res1
    res["status"] = res.get("status", "escalated")
    if res["status"] not in ("matched", "near"):
        res["status"] = "escalated"
    return res


def process_one() -> bool:
    rec = claim_next()
    if rec is None:
        print("[worker] queue empty")
        return False
    print(f"[worker] claimed {rec['id']} -> {rec.get('worktree')}")
    res = attempt(rec)
    sched("report", "--id", rec["id"], "--status", res["status"],
          "--score", str(res.get("best_score", 0)),
          "--tier", str(res.get("tier", 0)),
          "--notes", str(res.get("notes", "")))
    print(f"[worker] {rec['id']} -> {res['status']} (score {res.get('best_score', 0)})")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="SOTN volume-engine worker.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("once")
    pl = sub.add_parser("loop")
    pl.add_argument("--max", type=int, default=0, help="max functions (0 = until empty)")
    pl.add_argument("--sleep", type=float, default=2.0)
    args = ap.parse_args()

    if args.cmd == "once":
        return 0 if process_one() else 0

    n = 0
    while True:
        did = process_one()
        if not did:
            break
        n += 1
        if args.max and n >= args.max:
            break
        time.sleep(args.sleep)
    print(f"[worker] done, processed {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
