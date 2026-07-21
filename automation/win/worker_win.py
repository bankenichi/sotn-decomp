#!/usr/bin/env python3
"""
worker_win.py: volume-engine worker for Topology A (OpenCode native on Windows).

Split of responsibilities:
  - The scheduler, git, and the build stay in WSL. The scheduler remains the
    single writer to work/queue.jsonl with real POSIX locking, and git worktree
    operations run natively on ext4 (fast, correct).
  - This worker runs on WINDOWS. It drives the Windows OpenCode CLI and the
    Windows llama-server, so nothing extra is resident in the WSL VM.
  - Only two things cross the boundary: OpenCode's working directory (the
    worktree, reached over \\wsl$) and the RESULT.json it writes there.

Run this with Windows Python:
    python automation\\win\\worker_win.py once
    python automation\\win\\worker_win.py loop --max 50

Env:
  SOTN_WSL_DISTRO    default Ubuntu-24.04
  SOTN_WSL_REPO      absolute WSL repo path; auto-detected as $HOME/sotn-decomp
  SOTN_UNC_PREFIX    default \\\\wsl$  (use \\\\wsl.localhost if your Windows prefers it)
  WORKER_NAME        worker id (default host-pid)
  OPENCODE_CMD       default opencode
  OPENCODE_AGENT     default sotn-matcher
  OPENCODE_MODEL     Tier 0 model ref (default llama/qwen)
  OPENCODE_MODEL_T1  Tier 1 cloud model ref (optional)
  MAX_ITERS          per-function edit cap passed to the agent (default 20)
  NEAR_THRESHOLD     score counting as 'near' (default 90)
  RUN_TIMEOUT        seconds per OpenCode invocation (default 3600)
  WORKER_DRYRUN=1    do not call OpenCode; report escalated
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time

DISTRO = os.environ.get("SOTN_WSL_DISTRO", "Ubuntu-24.04")
# Single-tree layout: the repo lives in the Windows project directory, and WSL
# reaches that same directory via /mnt/c. Windows tools use the native path
# (fast, no UNC); only the build crosses into WSL.
# Derived from this file's location (<repo>/automation/win/), never hardcoded:
# an absolute home path would leak the author's username and break elsewhere.
WIN_REPO = os.environ.get("SOTN_WIN_REPO", os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
UNC_PREFIX = os.environ.get("SOTN_UNC_PREFIX", r"\\wsl$")  # legacy, unused in single-tree
WORKER_NAME = os.environ.get("WORKER_NAME", f"{socket.gethostname()}-{os.getpid()}")
OPENCODE_CMD = os.environ.get("OPENCODE_CMD", "opencode")
OPENCODE_AGENT = os.environ.get("OPENCODE_AGENT", "sotn-matcher")
MODEL_T0 = os.environ.get(
    "OPENCODE_MODEL",
    "llama/Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-APEX-MTP-I-Compact.gguf")
MODEL_T1 = os.environ.get("OPENCODE_MODEL_T1", "")
MAX_ITERS = int(os.environ.get("MAX_ITERS", "20"))
NEAR_THRESHOLD = float(os.environ.get("NEAR_THRESHOLD", "90"))
# 20 minutes. A build is ~70s, so a productive run fits easily; a model stuck
# in a tool-call loop gets killed and reported as escalated instead of hanging.
RUN_TIMEOUT = float(os.environ.get("RUN_TIMEOUT", "1200"))
DRYRUN = os.environ.get("WORKER_DRYRUN", "") not in ("", "0", "false", "False")


# ---- pure helpers (unit-testable without Windows) --------------------------

def win_to_wsl(win_path: str) -> str:
    r"""Convert a Windows path to how WSL sees it via /mnt.
    C:\Users\<you>\path\to\SOTN-Decomp -> /mnt/c/Users/<you>/path/to/SOTN-Decomp"""
    p = win_path.replace("\\", "/")
    if len(p) > 1 and p[1] == ":":
        return "/mnt/" + p[0].lower() + p[2:]
    raise ValueError(f"expected a drive-letter Windows path, got {win_path!r}")


def win_join(*parts: str) -> str:
    """Join a Windows path from repo-relative pieces (which use / in the queue)."""
    joined = "\\".join(p.replace("/", "\\").strip("\\") for p in parts if p)
    return joined


def unc_path(wsl_path: str, distro: str = DISTRO, prefix: str = UNC_PREFIX) -> str:
    r"""Legacy helper for the two-tree layout (repo inside WSL). Unused in the
    single-tree layout; kept so an older setup still works if SOTN_WIN_REPO is
    pointed at a \\wsl$ location."""
    if not wsl_path.startswith("/"):
        raise ValueError(f"expected an absolute WSL path, got {wsl_path!r}")
    return f"{prefix}\\{distro}" + wsl_path.replace("/", "\\")


_SRC_INDEX: dict[str, tuple[str, int, str]] | None = None


def _build_src_index(root: str) -> dict[str, tuple[str, int, str]]:
    """Map function name -> (source file, line number, INCLUDE_ASM path).

    The agent should never have to search thousands of files for its target,
    so resolve it here and hand over the exact location.
    """
    import re
    rx = re.compile(r'INCLUDE_ASM\(\s*"([^"]+)"\s*,\s*([A-Za-z0-9_]+)\s*\)')
    idx: dict[str, tuple[str, int, str]] = {}
    src = os.path.join(root, "src")
    for dirpath, _dirs, files in os.walk(src):
        for fn in files:
            if not fn.endswith(".c"):
                continue
            full = os.path.join(dirpath, fn)
            try:
                with open(full, "r", errors="ignore") as f:
                    for lineno, line in enumerate(f, 1):
                        m = rx.search(line)
                        if m:
                            rel = os.path.relpath(full, root).replace("\\", "/")
                            idx.setdefault(m.group(2), (rel, lineno, m.group(1)))
            except OSError:
                continue
    return idx


def find_source(function: str, root: str = WIN_REPO):
    global _SRC_INDEX
    if _SRC_INDEX is None:
        _SRC_INDEX = _build_src_index(root)
    return _SRC_INDEX.get(function)


def asm_path_for(rec: dict, asm_rel: str) -> str:
    """Windows-relative path to the reference assembly for this function."""
    rel = asm_rel if asm_rel.startswith("asm/") else f"asm/{rec['build']}/{asm_rel}"
    return f"{rel}/{rec['function']}.s".replace("/", "\\")


def build_task_prompt(rec: dict, max_iters: int = MAX_ITERS,
                      located=None) -> str:
    """A strict recipe. Every path and command is pre-resolved.

    The agent must not need to explore. An earlier version only named the
    function; the model spent its whole budget listing directories, probing
    for tools, and writing its own MIPS disassembler, and never attempted the
    task. Everything it needs is stated literally below.
    """
    fn = rec["function"]
    ov = rec["overlay"].split("/")[-1].lower()
    v = rec["build"]
    wrapper = os.path.join(WIN_REPO, "automation", "win", "sotn.cmd").replace("/", "\\")

    if not located:
        return (f"Decompile {fn} ({v}, {rec['overlay']}). Its INCLUDE_ASM stub "
                f"could not be located automatically. Write RESULT.json with "
                f'{{"status":"escalated","best_score":0,"notes":"stub not found"}}')

    src_file, lineno, asm_rel = located
    src_win = src_file.replace("/", "\\")
    asm_win = asm_path_for(rec, asm_rel)

    return f"""Decompile ONE MIPS function to C that compiles to identical bytes.

FACTS (all verified, do not search or explore):
  function     {fn}
  reference asm{'':<1} {asm_win}
  source file  {src_win}  (line {lineno})
  current stub INCLUDE_ASM("{asm_rel}", {fn});
  you are in   {WIN_REPO}

PROCEDURE - follow in order:

1. Read the reference assembly:
     {asm_win}

2. Get a first-draft decompilation (do NOT write your own disassembler):
     python tools\\m2c\\m2c.py -t mipsel-gcc-c {asm_win}

3. Edit {src_win}: replace the single line
     INCLUDE_ASM("{asm_rel}", {fn});
   with your C function named {fn}. Keep it at the SAME position in the file;
   function order changes the output. Leave every other line untouched.

4. Build:
     & "{wrapper}" build {v}

5. Diff:
     & "{wrapper}" diff {fn} {v} {ov}
   Read the FIRST divergence only. Fix one class at a time in this order:
   types, control flow, local/stack usage, operation order. Re-diff after each
   change. Revert anything that lowers the score.

6. Repeat 4-5 at most {max_iters} times, then stop.

7. ALWAYS write RESULT.json in {WIN_REPO}:
     {{"status":"matched|near|escalated","best_score":<0-100>,"notes":"<first divergence and cause>"}}
   matched = diff says 100%. near = high score, a few instructions off.
   escalated = could not get close. This file is REQUIRED even on failure.

RULES:
  - Do not list directories, glob, or search the tree. The paths above are
    correct and complete. Open files with the read tool, by path.
  - Never use MCP resources. Do not call read_mcp_resource,
    list_mcp_resources, or list_mcp_resource_templates. If a tool call fails,
    do NOT retry it; use the read tool on the plain path instead.
  - Do not run make, gcc, or bare `sotn`. The compiler is in WSL; only the
    quoted wrapper command above reaches it.
  - Windows Python is `python`, not `python3`.
  - Edit only {src_win}."""


def resolve_opencode(cmd: str = OPENCODE_CMD) -> str | None:
    """Resolve the OpenCode executable to a full path.

    On Windows, npm/bun global installs create a .cmd shim. subprocess without
    shell=True calls CreateProcess, which does NOT apply PATHEXT, so a bare
    "opencode" raises WinError 2 even though it works in the shell.
    shutil.which() does honour PATHEXT, so resolve first and pass the full path.
    """
    found = shutil.which(cmd)
    if found:
        return found
    for ext in (".cmd", ".exe", ".bat", ".ps1"):  # explicit fallbacks
        found = shutil.which(cmd + ext)
        if found:
            return found
    return None


def opencode_argv(prompt: str, model: str, exe: str | None = None) -> list[str]:
    return [exe or OPENCODE_CMD, "run", prompt,
            "--agent", OPENCODE_AGENT, "--model", model]


# ---- WSL bridge ------------------------------------------------------------

def _wsl(*args: str, check: bool = True) -> str:
    """Run the WSL-side dispatcher and return stdout."""
    argv = ["wsl.exe", "-d", DISTRO, "-e", "bash",
            f"{wsl_repo()}/automation/win/sotn_dispatch.sh", *args]
    p = subprocess.run(argv, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"wsl dispatch failed ({p.returncode}): {p.stderr.strip()}")
    return p.stdout.strip()


_REPO_CACHE: str | None = None


def wsl_repo() -> str:
    """The repo as WSL sees it. Derived from the Windows path, so there is a
    single tree and nothing to keep in sync."""
    global _REPO_CACHE
    if _REPO_CACHE:
        return _REPO_CACHE
    _REPO_CACHE = os.environ.get("SOTN_WSL_REPO") or win_to_wsl(WIN_REPO)
    return _REPO_CACHE.rstrip("/")


def sched(*args: str) -> str:
    return _wsl("sched", *args)


def claim_next() -> dict | None:
    # No --worktree: we run in the main repo. See worktree_dir() for why.
    rec = json.loads(sched("next", "--worker", WORKER_NAME))
    return None if rec.get("status") == "empty" else rec


# ---- work ------------------------------------------------------------------

def worktree_dir(rec: dict) -> str:
    """Directory OpenCode runs in.

    We deliberately run in the MAIN repo, not a per-function git worktree.
    A worktree is a checkout of committed files only, so it lacks:
      - asm/ (generated by extraction; this is the reference assembly the
        agent must read, so without it the task is impossible)
      - build/ and the extracted assets
      - populated submodules, notably tools/m2c
    and worktrees created by WSL git carry /mnt/c gitdir paths that Windows
    git cannot resolve (they show as 'prunable'). OpenCode also sandboxes the
    agent to its working directory, so anything outside is auto-rejected.

    Running in the main repo gives the agent everything in one place.
    """
    return WIN_REPO


def read_result(workdir: str) -> dict | None:
    p = os.path.join(workdir, "RESULT.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return None


def run_opencode(workdir: str, prompt: str, model: str) -> None:
    exe = resolve_opencode()
    if not exe:
        raise RuntimeError(
            f"'{OPENCODE_CMD}' not found on PATH. On Windows, npm/bun installs "
            f"create a .cmd shim that subprocess cannot see without resolving "
            f"PATHEXT. Check with: where.exe {OPENCODE_CMD}")
    env = dict(os.environ)
    # Single tree: the config lives in the Windows project directory.
    env["OPENCODE_CONFIG"] = os.path.join(
        WIN_REPO, "automation", "opencode", "opencode.json")
    subprocess.run(opencode_argv(prompt, model, exe), cwd=workdir, env=env,
                   timeout=RUN_TIMEOUT)


def attempt(rec: dict) -> dict:
    workdir = worktree_dir(rec)
    located = find_source(rec["function"])
    if located:
        print(f"[worker] target: {located[0]}:{located[1]}")
    else:
        print(f"[worker] warning: could not locate {rec['function']} in src/")
    prompt = build_task_prompt(rec, located=located)

    if DRYRUN:
        return {"status": "escalated", "best_score": 0, "tier": 0,
                "notes": "WORKER_DRYRUN: no OpenCode invocation"}

    stale = os.path.join(workdir, "RESULT.json")
    if os.path.exists(stale):
        os.remove(stale)

    run_opencode(workdir, prompt, MODEL_T0)
    res = read_result(workdir) or {"status": "escalated", "best_score": 0,
                                   "notes": "no RESULT.json from Tier 0"}
    res["tier"] = 0
    if res.get("status") == "matched" or float(res.get("best_score", 0)) >= NEAR_THRESHOLD:
        if res.get("status") != "matched":
            res["status"] = "near"
        return res

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

    if res.get("status") not in ("matched", "near"):
        res["status"] = "escalated"
    return res


def process_one() -> bool:
    rec = claim_next()
    if rec is None:
        print("[worker] queue empty")
        return False
    print(f"[worker] claimed {rec['id']} -> {rec.get('worktree')}")
    try:
        res = attempt(rec)
    except Exception as e:  # noqa: BLE001
        # Never orphan a claimed record: report it back so the scheduler can
        # route it, rather than leaving it stuck in 'claimed' until reclaim.
        msg = f"{type(e).__name__}: {e}"
        print(f"[worker] ERROR on {rec['id']}: {msg}", file=sys.stderr)
        sched("report", "--id", rec["id"], "--status", "escalated",
              "--score", "0", "--tier", "0", "--notes", f"worker error: {msg}"[:300])
        return False
    sched("report", "--id", rec["id"], "--status", res["status"],
          "--score", str(res.get("best_score", 0)),
          "--tier", str(res.get("tier", 0)),
          "--notes", str(res.get("notes", "")))
    print(f"[worker] {rec['id']} -> {res['status']} (score {res.get('best_score', 0)})")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="SOTN worker (Windows/OpenCode).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("once")
    pl = sub.add_parser("loop")
    pl.add_argument("--max", type=int, default=0)
    pl.add_argument("--sleep", type=float, default=2.0)
    args = ap.parse_args()

    # Preflight before claiming anything, so a misconfigured environment does
    # not pull a record out of the queue and then fail.
    if not DRYRUN:
        exe = resolve_opencode()
        if not exe:
            print(f"[worker] FATAL: '{OPENCODE_CMD}' not found on PATH.\n"
                  f"  Check with: where.exe {OPENCODE_CMD}\n"
                  f"  If it is installed as a .cmd shim this should still "
                  f"resolve; if not, set OPENCODE_CMD to its full path.\n"
                  f"  To test the plumbing without a model: "
                  f"set WORKER_DRYRUN=1", file=sys.stderr)
            return 1
        print(f"[worker] opencode: {exe}")
    if not os.path.isdir(WIN_REPO):
        print(f"[worker] FATAL: repo not found at {WIN_REPO}. "
              f"Set SOTN_WIN_REPO.", file=sys.stderr)
        return 1

    if args.cmd == "once":
        process_one()
        return 0

    n = 0
    while process_one():
        n += 1
        if args.max and n >= args.max:
            break
        time.sleep(args.sleep)
    print(f"[worker] done, processed {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
