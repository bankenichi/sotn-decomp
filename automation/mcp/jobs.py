"""Detached long-running jobs, so a build can never time out a tool call.

THE PROBLEM THIS SOLVES
    `commands_client.run()` is synchronous: it blocks in subprocess.run until
    the command finishes. A full `make build VERSION=us` takes minutes. The MCP
    transport gives up long before the command does, and the caller gets

        MCP error -32001: Request timed out

    while the build is still running happily in WSL. That is the worst possible
    failure shape, because the tree is now MID-BUILD and the caller does not
    know it. The temptation is to start another build, which is exactly how you
    corrupt a shared build directory.

    Raising the tool's own timeout does not help. The tool timeout was already
    1500s when this happened; the limit that fired belongs to the transport,
    not to us, and it is not ours to configure.

THE FIX
    Never hold a request open across a long command. Spawn it detached, return
    a job id immediately, and let the caller poll. Every call is milliseconds.

    Completion is determined from FILES, never from a process handle, so a job
    survives a connector restart: the wrapper writes the exit code to
    <id>.done when the command finishes. If the connector is restarted
    mid-build, `job_status` still reports correctly afterwards.

DESIGNED AROUND THE CALLER'S LIMITS
    The caller polling this may be an agent whose own sleep is capped (45s in
    the Cowork sandbox), so a blocking wait longer than that is useless to it.
    `status(wait_s=...)` therefore blocks for AT MOST MAX_WAIT seconds and then
    returns whatever it has. Polling is cheap and bounded, and a caller with a
    30s ceiling and a caller with none use the identical code path.

    Output is returned as a short tail plus an extracted summary, not the whole
    log. A full build log is ~300 lines of ninja chatter whose only interesting
    content is the overlay grid and the final verdict. Returning all of it
    burned enormous context for no information.

WHERE THIS WORKS, AND WHERE IT CANNOT
    This is for the CONNECTOR side (WSL), which is an ordinary long-lived Linux
    userspace. It does NOT work in the Cowork sandbox, and that is not a bug to
    fix. Measured, not assumed: a 60s job started there wrote "begin" to its log
    and then died the moment the bash call returned, never writing its exit
    code. `ps` explains why:

        bwrap --new-session --die-with-parent --unshare-pid ...

    Every sandbox bash call gets a FRESH PID namespace that is torn down when
    the call ends. Killing PID 1 of a namespace kills everything in it, so
    nothing can outlive a single call and `start_new_session=True` is
    irrelevant. There is no background in that environment, only a 45s ceiling.

    The consequence for tooling: anything slow must run through the connector
    (uncapped, and asynchronous via this module), not through the sandbox. The
    sandbox is for work that fits comfortably inside one call.

Stdlib only, no shell injection: argv is built by commands_client's allowlist
and quoted with shlex, never interpolated raw.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import signal
import subprocess
import time
from pathlib import Path

JOBS_DIR = Path(os.environ.get(
    "SOTN_JOBS_DIR", Path.home() / "sotn-work" / "jobs"))

# A blocking wait must stay comfortably under any plausible transport timeout,
# and under the 45s sleep ceiling of the sandbox that polls this.
MAX_WAIT = 30.0
POLL = 0.5
DEFAULT_TAIL = 40

# Lines worth surfacing from a build log. The overlay grid and the verdict are
# on stderr; everything else is ninja progress.
_SUMMARY_RX = re.compile(
    r"(✅|❌|check:|checksum|error|Error|ERROR|warning: |Traceback|"
    r"make: \*\*\*|No rule to make target)")


def _now() -> float:
    return time.time()


def _paths(job_id: str) -> tuple[Path, Path, Path]:
    return (JOBS_DIR / f"{job_id}.json",
            JOBS_DIR / f"{job_id}.log",
            JOBS_DIR / f"{job_id}.done")


def _read_meta(job_id: str) -> dict | None:
    meta_p, _, _ = _paths(job_id)
    try:
        return json.loads(meta_p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _alive(pid: int) -> bool:
    """Is the process group still running?

    os.kill(pid, 0) raises ProcessLookupError when it is gone and
    PermissionError when it exists but is not ours; the latter still means
    alive. On WSL this is a real Linux /proc, so it is reliable.
    """
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def running_jobs(action: str | None = None) -> list[str]:
    """Job ids that have not finished, optionally filtered by action."""
    out = []
    if not JOBS_DIR.exists():
        return out
    for meta_p in JOBS_DIR.glob("*.json"):
        job_id = meta_p.stem
        _, _, done_p = _paths(job_id)
        if done_p.exists():
            continue
        meta = _read_meta(job_id)
        if not meta:
            continue
        if action and meta.get("action") != action:
            continue
        if _alive(int(meta.get("pid", -1))):
            out.append(job_id)
    return sorted(out)


def start(action: str, argv: list[str], cwd: str,
          exclusive: bool = True, slug: str = "") -> dict:
    """Spawn `argv` detached and return immediately with a job id.

    `exclusive` refuses to launch when another job of the same action is still
    running. Two concurrent `make build`s share one build directory and would
    interleave writes, producing artifacts that match nothing and a checksum
    failure with no cause. Refusing is always better than racing.

    It is NOT right for every action, though. The permuter takes a work_dir,
    compiles into that directory alone, and never touches build/ or invokes
    make -- so N permuter runs on N different seeds share nothing. Serialising
    them was a real cost: the near pool is the most valuable pool the project
    has, and only one seed could be searched at a time. Callers that own their
    own workspace pass exclusive=False.

    `slug` disambiguates the job id. The id was action+HHMMSS+pid, which is not
    unique once several jobs of one action can start in the same second from the
    same connector process; the second would silently overwrite the first's
    metadata and log.
    """
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    if exclusive:
        busy = running_jobs(action)
        if busy:
            return {"started": False, "reason": "already_running",
                    "action": action, "running": busy,
                    "hint": f"poll job_status('{busy[0]}') instead of starting "
                            f"another {action}"}

    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", slug).strip("_")[:40]
    job_id = f"{action}-{time.strftime('%H%M%S')}-{os.getpid()}"
    if safe:
        job_id += f"-{safe}"
    # Even with a slug, two runs on the same seed in the same second would
    # collide. Cheap insurance: bump until the metadata path is free.
    n = 0
    while _paths(job_id)[0].exists() and not _paths(job_id)[2].exists():
        n += 1
        job_id = f"{job_id.rsplit('~', 1)[0]}~{n}"
    meta_p, log_p, done_p = _paths(job_id)
    for p in (log_p, done_p):
        try:
            p.unlink()
        except OSError:
            pass

    # The wrapper is what makes completion durable. Redirecting inside sh and
    # writing $? to a sentinel means the exit code outlives both this process
    # and the connector.
    quoted = " ".join(shlex.quote(a) for a in argv)
    script = (f"{quoted} > {shlex.quote(str(log_p))} 2>&1; "
              f"printf '%s' \"$?\" > {shlex.quote(str(done_p))}")

    proc = subprocess.Popen(
        ["/bin/sh", "-c", script],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,      # survives the connector going away
    )

    meta = {"job_id": job_id, "action": action, "argv": argv, "cwd": cwd,
            "pid": proc.pid, "started_at": _now()}
    meta_p.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return {"started": True, "job_id": job_id, "action": action,
            "pid": proc.pid,
            "hint": f"poll job_status('{job_id}', wait_s=25)"}


def _tail(path: Path, n: int) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-n:])
    except OSError:
        return ""


def _summary(path: Path, limit: int = 60) -> list[str]:
    """The lines that actually say whether it worked."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            hits = [ln.rstrip("\n") for ln in f if _SUMMARY_RX.search(ln)]
    except OSError:
        return []
    return hits[-limit:]


def status(job_id: str, wait_s: float = 0.0,
           tail_lines: int = DEFAULT_TAIL) -> dict:
    """Poll a job, optionally blocking up to `wait_s` (hard-capped MAX_WAIT)."""
    meta = _read_meta(job_id)
    if not meta:
        return {"job_id": job_id, "state": "unknown",
                "error": "no such job; call job_list()"}

    _, log_p, done_p = _paths(job_id)
    deadline = _now() + min(max(0.0, wait_s), MAX_WAIT)
    while True:
        if done_p.exists():
            break
        if _now() >= deadline:
            break
        time.sleep(POLL)

    elapsed = round(_now() - float(meta.get("started_at", _now())), 1)
    if done_p.exists():
        try:
            rc = int((done_p.read_text(encoding="utf-8") or "1").strip() or 1)
        except (OSError, ValueError):
            rc = 1
        return {"job_id": job_id, "action": meta.get("action"),
                "state": "done", "ok": rc == 0, "returncode": rc,
                "elapsed_s": elapsed,
                "summary": _summary(log_p),
                "tail": _tail(log_p, tail_lines),
                "log": str(log_p)}

    alive = _alive(int(meta.get("pid", -1)))
    if not alive:
        # No sentinel and no process: the wrapper was killed outright.
        return {"job_id": job_id, "action": meta.get("action"),
                "state": "vanished", "ok": False, "elapsed_s": elapsed,
                "summary": _summary(log_p), "tail": _tail(log_p, tail_lines),
                "hint": "process died without writing an exit code; "
                        "treat the tree as mid-build and rebuild"}
    return {"job_id": job_id, "action": meta.get("action"),
            "state": "running", "elapsed_s": elapsed,
            "summary": _summary(log_p, limit=12),
            "tail": _tail(log_p, min(tail_lines, 12)),
            "hint": f"still running; poll again with wait_s=25"}


def list_jobs(limit: int = 20) -> dict:
    if not JOBS_DIR.exists():
        return {"jobs": [], "dir": str(JOBS_DIR)}
    out = []
    for meta_p in sorted(JOBS_DIR.glob("*.json"),
                         key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        job_id = meta_p.stem
        meta = _read_meta(job_id) or {}
        _, _, done_p = _paths(job_id)
        out.append({"job_id": job_id, "action": meta.get("action"),
                    "state": "done" if done_p.exists()
                    else ("running" if _alive(int(meta.get("pid", -1)))
                          else "vanished")})
    return {"jobs": out, "dir": str(JOBS_DIR)}


def cancel(job_id: str) -> dict:
    meta = _read_meta(job_id)
    if not meta:
        return {"job_id": job_id, "cancelled": False, "error": "no such job"}
    pid = int(meta.get("pid", -1))
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError) as e:
        return {"job_id": job_id, "cancelled": False, "error": str(e)}
    return {"job_id": job_id, "cancelled": True}
