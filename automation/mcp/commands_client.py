"""
commands_client: a hard-allowlisted command runner for the SOTN decomp repo.

Security model:
  - There is NO general shell. Only the actions in REGISTRY can run.
  - Every argument is validated (enums, strict regexes, in-repo path checks).
  - subprocess is always invoked with an argv list, never shell=True.
  - stdout/stderr are truncated to keep Claude's context small.
  - Each action has a timeout. Set SOTN_CMD_DRYRUN=1 to return argv without running.

Stdlib only, so it is importable and unit-testable anywhere.
"""
from __future__ import annotations
import datetime as dt
import os
import re
import subprocess
import time
from pathlib import Path

REPO = Path(os.environ.get("SOTN_REPO", Path(__file__).resolve().parents[2]))
PYTHON = os.environ.get("SOTN_PYTHON", "python3")
# Fail CLOSED. If the variable is missing or empty we assume dry-run, because
# an unset safety flag must never mean "execute for real". This bit us once:
# MCP `env` entries are set on the Windows wsl.exe process and do NOT propagate
# into WSL without WSLENV, so the server saw nothing and silently ran live.
# The launcher now passes it inline in the bash command instead.
_dr = os.environ.get("SOTN_CMD_DRYRUN")
DRYRUN = True if _dr is None or _dr.strip() == "" else \
    _dr.strip().lower() not in ("0", "false", "no", "off")
MAX_OUT = int(os.environ.get("SOTN_CMD_MAXOUT", "20000"))

VERSIONS = {"us", "hd", "pspeu", "saturn"}
SYMBOL_RX = re.compile(r"^[A-Za-z0-9_]{1,64}$")
OVERLAY_RX = re.compile(r"^[A-Za-z0-9_]{1,32}$")
FMT = {"plain", "color", "json", "html"}


class Rejected(ValueError):
    """Raised when an argument fails validation. Never executes anything."""


def _v(version: str) -> str:
    if version not in VERSIONS:
        raise Rejected(f"version must be one of {sorted(VERSIONS)}")
    return version


def _sym(symbol: str) -> str:
    if not SYMBOL_RX.match(symbol or ""):
        raise Rejected("symbol must match ^[A-Za-z0-9_]{1,64}$")
    return symbol


def _ov(overlay: str) -> str:
    if not OVERLAY_RX.match(overlay or ""):
        raise Rejected("overlay must match ^[A-Za-z0-9_]{1,32}$")
    return overlay


def _inrepo(p: str, must_be_dir: bool = False, must_exist: bool = True) -> str:
    rp = (REPO / p).resolve()
    if not str(rp).startswith(str(REPO.resolve())):
        raise Rejected("path must resolve inside the repo")
    if must_exist and not rp.exists():
        raise Rejected(f"path does not exist: {p}")
    if must_be_dir and rp.exists() and not rp.is_dir():
        raise Rejected(f"path is not a directory: {p}")
    return str(rp)


def _reject_fmt(fmt):
    raise Rejected(f"fmt must be one of {sorted(FMT)}")


STATUSES = {"todo", "claimed", "near", "matched", "escalated", "deferred"}


def _status(status: str) -> str:
    if status not in STATUSES:
        raise Rejected(f"status must be one of {sorted(STATUSES)}")
    return status


def _msg(message: str) -> str:
    m = (message or "").strip()
    if not (1 <= len(m) <= 200) or "\n" in m:
        raise Rejected("commit message must be 1-200 chars, single line")
    return m


# ---- argv builders (validate then return an argv list) ----

def _make(goal: str, version: str | None = None):
    argv = ["make", goal]
    if version is not None:
        argv.append(f"VERSION={_v(version)}")
    return argv


REGISTRY = {
    # make goals
    "make_build":             lambda version="us": _make("build", version),
    "make_extract":           lambda version="us": _make("extract", version),
    "make_expected":          lambda version="us": _make("expected", version),
    "make_clean":             lambda version="us": _make("clean", version),
    "make_force_symbols":     lambda version="us": _make("force_symbols", version),
    "make_function_finder":   lambda version=None: _make("function-finder",
                                                         version if version else None),
    "make_reports":           lambda: _make("reports"),
    "make_duplicates_report": lambda: _make("duplicates-report"),
    # asm-differ
    "asm_diff": lambda symbol, version="us", overlay="dra", make_first=True, fmt="plain": (
        [PYTHON, "tools/asm-differ/diff.py"]
        + (["-m"] if make_first else [])
        + (["--format", fmt] if (fmt in FMT or _reject_fmt(fmt)) else [])
        + ["--version", _v(version), "--overlay", _ov(overlay), _sym(symbol)]
    ),
    # decomp-permuter
    "permuter": lambda work_dir: [PYTHON, "tools/decomp-permuter/permuter.py",
                                  _inrepo(work_dir, must_be_dir=True)],
    "permuter_import": lambda c_file, asm_file: [
        PYTHON, "tools/decomp-permuter/import.py",
        _inrepo(c_file), _inrepo(asm_file)],
    # queue visibility (read-only): lets the orchestrator poll in one call
    "queue_stats": lambda: [PYTHON, "automation/scheduler.py", "stats"],
    "queue_list":  lambda status="": ([PYTHON, "automation/scheduler.py", "list"]
                                      + (["--status", _status(status)] if status else [])),
    # scoped git (no general shell): status, stage-all, and commit only
    "git_status":  lambda: ["git", "status", "--short"],
    "git_add_all": lambda: ["git", "add", "-A"],
    "git_commit":  lambda message: ["git", "commit", "-m", _msg(message)],
}


def build_argv(action: str, **kwargs) -> list[str]:
    if action not in REGISTRY:
        raise Rejected(f"unknown action '{action}'. allowed: {sorted(REGISTRY)}")
    try:
        return REGISTRY[action](**kwargs)
    except TypeError as e:
        raise Rejected(f"bad arguments for {action}: {e}")


# Actions whose useful content is at the START of the output. Truncating from
# the tail (the default, right for build logs) destroyed asm-differ's header,
# which is exactly where the match percentage lives, and did so silently.
_HEAD_TRUNCATE = {"asm_diff"}


def run(action: str, timeout: float = 3600, **kwargs) -> dict:
    argv = build_argv(action, **kwargs)
    if DRYRUN:
        return {"action": action, "argv": argv, "dry_run": True}
    try:
        p = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True,
                           timeout=timeout)
        head = action in _HEAD_TRUNCATE
        cut = (lambda s: s[:MAX_OUT]) if head else (lambda s: s[-MAX_OUT:])
        return {
            "action": action, "argv": argv, "dry_run": False,
            "returncode": p.returncode,
            "stdout": cut(p.stdout), "stderr": cut(p.stderr),
            "truncated": len(p.stdout) > MAX_OUT or len(p.stderr) > MAX_OUT,
            "truncated_from": ("tail" if not head else "end (head kept)"),
        }
    except subprocess.TimeoutExpired:
        return {"action": action, "argv": argv, "dry_run": False,
                "timed_out": True, "timeout": timeout}


def allowed() -> list[str]:
    return sorted(REGISTRY)


# ---------------------------------------------------------------------------
# Scoped in-repo filesystem access.
#
# These let the harness read, navigate, and edit the WSL2 repo tree THROUGH the
# connector when Cowork is not connected directly to the WSL2 clone. They are
# direct file operations (not a shell), constrained to the repo, with .git and
# size guards. Reads/list/search are read-only and always run; writes respect
# SOTN_CMD_DRYRUN so a dry-run connector never mutates files.
# ---------------------------------------------------------------------------

FS_MAX_READ = int(os.environ.get("SOTN_FS_MAXREAD", "400000"))     # bytes returned
FS_MAX_WRITE = int(os.environ.get("SOTN_FS_MAXWRITE", "2000000"))  # bytes accepted
FS_ACTIONS = ["read_file", "write_file", "list_dir", "search_repo"]


def _resolve(path: str, must_exist: bool, want_dir: bool | None) -> Path:
    rp = (REPO / path).resolve()
    root = REPO.resolve()
    if rp != root and root not in rp.parents:
        raise Rejected("path must resolve inside the repo")
    if rp == (root / ".git") or (root / ".git") in rp.parents:
        raise Rejected("path is inside .git and is not writable/readable here")
    if must_exist and not rp.exists():
        raise Rejected(f"path does not exist: {path}")
    if want_dir is True and rp.exists() and not rp.is_dir():
        raise Rejected(f"not a directory: {path}")
    if want_dir is False and rp.exists() and not rp.is_file():
        raise Rejected(f"not a file: {path}")
    return rp


def fs_read(path: str) -> dict:
    rp = _resolve(path, must_exist=True, want_dir=False)
    data = rp.read_bytes()
    text = data[:FS_MAX_READ].decode("utf-8", errors="replace")
    return {"path": path, "bytes": len(data),
            "truncated": len(data) > FS_MAX_READ, "content": text}


def fs_write(path: str, content: str) -> dict:
    rp = _resolve(path, must_exist=False, want_dir=False)
    enc = content.encode("utf-8")
    if len(enc) > FS_MAX_WRITE:
        raise Rejected(f"content exceeds {FS_MAX_WRITE} bytes")
    if DRYRUN:
        return {"path": path, "dry_run": True, "would_write_bytes": len(enc)}
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_bytes(enc)
    return {"path": path, "dry_run": False, "bytes_written": len(enc)}


def fs_list(path: str = ".") -> dict:
    rp = _resolve(path, must_exist=True, want_dir=True)
    entries = []
    for child in sorted(rp.iterdir()):
        entries.append({
            "name": child.name,
            "type": "dir" if child.is_dir() else "file",
            "size": (child.stat().st_size if child.is_file() else None),
        })
    return {"path": path, "entries": entries[:1000], "count": len(entries)}


def fs_search(query: str, path: str = ".", max_results: int = 200) -> dict:
    if not (1 <= len(query) <= 200):
        raise Rejected("query must be 1-200 chars")
    rp = _resolve(path, must_exist=True, want_dir=None)
    # ripgrep if available, else grep; query passed as argv (no shell).
    tool = "rg" if _has("rg") else "grep"
    if tool == "rg":
        argv = ["rg", "-n", "--no-heading", "-e", query, str(rp)]
    else:
        argv = ["grep", "-rn", "-e", query, str(rp)]
    p = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True,
                       timeout=120)
    lines = [ln for ln in p.stdout.splitlines() if ln][:max_results]
    return {"query": query, "path": path, "matches": lines,
            "count": len(lines), "truncated": len(p.stdout.splitlines()) > max_results}


def _has(prog: str) -> bool:
    from shutil import which
    return which(prog) is not None


def verify_build(version: str = "us") -> dict:
    """THE ORACLE. Rebuild-independent check that every artifact hash matches.

    The charter defines correctness as "all hashes in config/check.<v>.sha
    reproduce", but make_build returns 0 on a tree whose artifacts do not
    match, so success there proves nothing. This is the missing tool: it runs
    the checksum file and reports a structured verdict.
    """
    v = _v(version)
    sha_file = f"config/check.{v}.sha"
    if not (REPO / sha_file).exists():
        raise Rejected(f"missing {sha_file}")
    tool = "shasum" if _has("shasum") else "sha1sum"
    p = subprocess.run([tool, "-c", sha_file], cwd=str(REPO),
                       capture_output=True, text=True, timeout=600)
    lines = [l for l in p.stdout.splitlines() if l.strip()]
    ok = [l for l in lines if l.endswith(": OK")]
    bad = [l for l in lines if not l.endswith(": OK")]
    total = sum(1 for l in (REPO / sha_file).read_text().splitlines() if l.strip())
    return {
        "version": v, "matched": len(ok), "expected": total,
        "failed": bad[:20], "all_ok": len(ok) == total and not bad,
        "verdict": (f"{len(ok)}/{total} OK" if len(ok) == total and not bad
                    else f"{len(ok)}/{total} OK, {len(bad)} FAILED"),
    }


def queue_report(function_id: str, status: str, proof: str = "",
                 score: str = "", notes: str = "") -> dict:
    """Record an outcome through scheduler.py, the single queue writer.

    Without this the orchestrator can verify a match but has no sanctioned way
    to record it, and the charter forbids hand-editing work/queue.jsonl.
    The scheduler still refuses `matched` unless proof is supplied.
    """
    argv = [PYTHON, "automation/scheduler.py", "report",
            "--id", function_id, "--status", _status(status)]
    if proof:
        argv += ["--proof", _msg(proof) if len(proof) <= 200 else proof[:200]]
    if score:
        argv += ["--score", score]
    if notes:
        argv += ["--notes", notes[:250]]
    if DRYRUN:
        return {"action": "queue_report", "argv": argv, "dry_run": True}
    p = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True,
                       timeout=120)
    return {"action": "queue_report", "returncode": p.returncode,
            "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


FLEET_LOGS = "automation/logs"
FLEET_PIDS = "automation/logs/fleet.pids"
# Written by a deliberate fleet_stop. While it exists, fleet_start refuses.
#
# Rationale: an unattended watchdog with authority to start work will restart a
# fleet that a human stopped on purpose (e.g. while reconfiguring llama-server),
# and then quietly mutate the queue underneath them. A crashed fleet never calls
# fleet_stop, so no sentinel exists and automatic recovery still works. Only a
# deliberate stop is sticky.
FLEET_HOLD = "automation/logs/FLEET_HOLD"


def fleet_start(workers: int = 4, max_functions: int = 0,
                force: bool = False) -> dict:
    """Launch N detached worker_direct.py processes inside WSL.

    Lets the orchestrator run the volume tier without a human at a PowerShell
    prompt. Workers run natively here (worker_direct.py is OS-aware), write to
    automation/logs/worker-N.log, and record their PIDs so fleet_stop can reap
    them.

    N is generations in flight. apply/build/verify is serialised by a lock, so
    beyond ~4 workers the extra ones mostly queue. llama-server must be started
    with --parallel >= N or generation serialises too.
    """
    if not 1 <= int(workers) <= 16:
        raise Rejected("workers must be 1-16")
    if DRYRUN:
        return {"action": "fleet_start", "workers": workers, "dry_run": True,
                "note": "would launch detached workers"}
    (REPO / FLEET_LOGS).mkdir(parents=True, exist_ok=True)
    hold = REPO / FLEET_HOLD
    if hold.exists() and not force:
        try:
            why = hold.read_text(encoding="utf-8").strip()
        except OSError:
            why = "(unreadable)"
        return {"action": "fleet_start", "started": 0, "held": True,
                "hold_written": why,
                "note": "fleet is on HOLD after a deliberate fleet_stop and will "
                        "NOT auto-start. An unattended caller must respect this. "
                        "To override intentionally: fleet_start(force=True)."}
    if force and hold.exists():
        try:
            hold.unlink()
        except OSError:
            pass
    running = _fleet_pids_alive()
    if running:
        return {"action": "fleet_start", "started": 0, "already_running": running,
                "note": "fleet already active; call fleet_stop first"}

    extra = f" --max {int(max_functions)}" if int(max_functions) > 0 else ""
    # One bash invocation launches every worker and writes the pid file, so a
    # slow MCP round trip cannot leave a half-started, untracked fleet.
    script = (
        f"cd {REPO} && mkdir -p {FLEET_LOGS} && : > {FLEET_PIDS} && "
        f"for i in $(seq 1 {int(workers)}); do "
        f"  rm -f {FLEET_LOGS}/worker-$i.log; "
        f"  WORKER_NAME=fleet-$i setsid nohup python3 "
        f"automation/win/worker_direct.py loop{extra} "
        f"> {FLEET_LOGS}/worker-$i.log 2>&1 < /dev/null & "
        f"  echo $! >> {FLEET_PIDS}; "
        f"done; cat {FLEET_PIDS}"
    )
    p = subprocess.run(["bash", "-lc", script], cwd=str(REPO),
                       capture_output=True, text=True, timeout=60)
    pids = [int(x) for x in p.stdout.split() if x.isdigit()]
    return {"action": "fleet_start", "started": len(pids), "pids": pids,
            "logs": FLEET_LOGS,
            "note": "detached; poll with fleet_status, stop with fleet_stop"}


def _fleet_pids_alive() -> list[int]:
    """Live worker PIDs, from pid files only.

    Sources, in order: the launcher's pid file, then per-worker pid files that
    each worker writes for itself on startup. Both are cross-checked against
    /proc so dead entries are ignored.

    Deliberately NOT pgrep. Matching on the command line is unsafe: any shell
    running a command that merely mentions worker_direct.py matches too. In
    testing that returned pids 1, 2 and 5 (the sandbox init and two of my own
    shells), which fleet_stop would then have tried to kill. Self-registration
    is the only source that cannot produce a false positive.
    """
    candidates: set[int] = set()
    f = REPO / FLEET_PIDS
    if f.exists():
        candidates |= {int(x) for x in f.read_text().split() if x.isdigit()}
    d = REPO / FLEET_LOGS
    if d.is_dir():
        for pf in d.glob("worker-*.pid"):
            try:
                t = pf.read_text().strip()
            except OSError:
                continue
            if t.isdigit():
                candidates.add(int(t))

    alive: list[int] = []
    for pid in sorted(candidates):
        proc = Path("/proc") / str(pid)
        if not proc.exists():
            continue
        # Confirm it is genuinely a worker, not a recycled pid.
        try:
            text = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace")
        except OSError:
            continue
        if "worker_direct.py" in text and "python" in text:
            alive.append(pid)
    return alive


def fleet_status(tail: int = 2) -> dict:
    """Which workers are alive, plus the last line of each log.

    A silent fleet is indistinguishable from a stuck one, so always look at the
    log tails, not just the PID count.
    """
    alive = _fleet_pids_alive()
    logs = {}
    d = REPO / FLEET_LOGS
    if d.is_dir():
        for lf in sorted(d.glob("worker-*.log")):
            try:
                lines = [l for l in lf.read_text(errors="replace").splitlines() if l.strip()]
                logs[lf.name] = lines[-int(tail):] if lines else ["(empty)"]
            except OSError:
                logs[lf.name] = ["(unreadable)"]
    return {"action": "fleet_status", "alive": alive, "count": len(alive),
            "logs": logs}


def fleet_stop(hold: bool = True) -> dict:
    """Stop all workers and return their claimed records to 'todo'.

    A killed worker cannot release its own claim, so records would otherwise
    sit 'claimed' forever and be skipped by every later run. Always reclaim.
    """
    if DRYRUN:
        return {"action": "fleet_stop", "dry_run": True}
    alive = _fleet_pids_alive()
    for pid in alive:
        subprocess.run(["bash", "-lc", f"kill {pid} 2>/dev/null || true"],
                       cwd=str(REPO), capture_output=True, text=True, timeout=30)
    time.sleep(1)
    still = _fleet_pids_alive()
    for pid in still:
        subprocess.run(["bash", "-lc", f"kill -9 {pid} 2>/dev/null || true"],
                       cwd=str(REPO), capture_output=True, text=True, timeout=30)
    r = subprocess.run([PYTHON, "automation/scheduler.py", "reclaim",
                        "--older-than-min", "0"], cwd=str(REPO),
                       capture_output=True, text=True, timeout=120)
    lock = REPO / "automation" / ".build.lock"
    if lock.exists():
        try:
            lock.unlink()
        except OSError:
            pass
    try:
        (REPO / FLEET_PIDS).unlink()
    except OSError:
        pass
    held = False
    if hold:
        # A deliberate stop is sticky: fleet_start refuses until someone passes
        # force=True. Automated recycling must call fleet_stop(hold=False).
        try:
            (REPO / FLEET_HOLD).write_text(
                f"stopped at {dt.datetime.now().isoformat(timespec='seconds')}; "
                f"fleet_start will refuse until force=True", encoding="utf-8")
            held = True
        except OSError:
            pass
    return {"action": "fleet_stop", "stopped": alive, "hold": held,
            "reclaim": r.stdout.strip(),
            "note": "claims released, lock cleared"
                    + ("; HOLD set, fleet_start will refuse without force"
                       if held else "; no hold (recycle allowed)")}


def capabilities() -> dict:
    return {"commands": sorted(REGISTRY), "filesystem": FS_ACTIONS,
            "dry_run": DRYRUN, "repo": str(REPO)}
