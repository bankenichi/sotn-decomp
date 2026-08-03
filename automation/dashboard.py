#!/usr/bin/env python3
"""Localhost dashboard for the SOTN harness: queue, permuter, fleets.

WHAT IT SHOWS
    - live queue counts by status, straight from the scheduler queue
    - one column per running permuter job: best score, iterations, whether it
      is still improving, and the tail of its log
    - one column per fleet worker: alive/dead and the tail of its log
    - start/stop buttons for the supervised permuter and both fleets

WHY A SERVER AND NOT A SCRIPT
    A silent fleet and a stuck fleet look identical from a PID count, and a
    permuter log is one line per iteration at ten per second, so reading it by
    eye gives the wrong number. Both failure modes are invisible without
    something that polls and summarises continuously.

SAFETY, which is most of the design here
    This process can start and stop jobs, so it is deliberately hard to reach
    and impossible to talk into running something arbitrary:

    1. Binds 127.0.0.1 only. Never 0.0.0.0. Not reachable off the machine.
    2. Actions are a fixed dict of zero-argument callables. There is no command
       string, no argv, no shell anywhere in the request path, so there is
       nothing for a crafted request to inject into.
    3. Mutating requests must be POST and must carry the token printed at
       startup. A GET can never change state, which also means a stray browser
       prefetch or a link in a page cannot stop your fleet.
    4. The token is per-process and random. Restarting invalidates it.
    5. Every stop path is idempotent and reclaims queue records, so pressing
       stop twice is harmless and never leaves records stuck in 'claimed'.
    6. Read endpoints never expose file contents outside the two known log
       directories.

Usage:
    python3 automation/dashboard.py --serve [--port 8777]
    python3 automation/dashboard.py --status
    python3 automation/dashboard.py --stop
    python3 automation/dashboard.py --self-test
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import re
import secrets
import signal
import socketserver
import sys
import threading
import time
import urllib.parse
from collections import Counter
from pathlib import Path

REPO = Path(os.environ.get("SOTN_REPO", Path(__file__).resolve().parents[1]))
QUEUE = Path(os.environ.get(
    "SOTN_QUEUE", os.path.expanduser("~/sotn-work/queue.jsonl")))
JOBS_DIR = Path(os.path.expanduser(
    os.environ.get("SOTN_JOBS_DIR", "~/sotn-work/jobs")))
FLEET_LOGS = REPO / "automation" / "logs"
PIDFILE = Path(os.path.expanduser("~/sotn-work/dashboard.pid"))
SUPERVISOR_STATE = Path(os.path.expanduser("~/sotn-work/supervisor.json"))

sys.path.insert(0, str(REPO / "automation"))
sys.path.insert(0, str(REPO / "automation" / "mcp"))

# commands_client fails CLOSED: unset SOTN_CMD_DRYRUN means dry-run, so
# fleet_start would report what it "would" launch and launch nothing. Pressing
# a button is an explicit request to run, so opt in -- but only if the operator
# has not already chosen, so `SOTN_CMD_DRYRUN=1 sotn-dash start` stays a safe
# preview mode. This MUST happen before commands_client is imported anywhere,
# because it reads the variable once at import time.
os.environ.setdefault("SOTN_CMD_DRYRUN", "0")
# Same reason: anything we spawn (supervisor -> permuter) resolves its
# interpreter from SOTN_PYTHON, defaulting to bare "python3" which lacks
# pycparser. We are already running under the right interpreter, so say so.
os.environ.setdefault("SOTN_PYTHON", sys.executable)

# Model choices for the cli fleet, as an INDEX into this list rather than a
# free-text model id. The action registry takes integers only, so a request can
# pick one of these and nothing else -- no arbitrary string reaches an argv.
#
# Labels carry MEASURED dead-rate from empty_response_audit.py, not folklore.
# Refresh them by re-running it; do not hand-edit from memory.
#
# RETRACTION 2026-08-03: ling-3.0-flash-free was labelled "(empty)" here on the
# strength of ZEN-FREE-MODELS.md calling it a do-not-use model. Over 32 calls it
# produced 10 real generations at a median of 68s, the FASTEST productive time
# of any model measured, and zero timeouts. laguna-s-2.1-free also produced C.
# That is the second time a model verdict in this project has been overturned by
# actually counting, and both times the wrong verdict came from a small sample
# repeated as fact. Prefer the number to the label.
CLI_MODELS = [
    ("ling-3.0-flash-free  62% dead, 68s med", "opencode/ling-3.0-flash-free"),
    ("north-mini-code-free  63% dead", "opencode/north-mini-code-free"),
    ("mimo-v2.5-free  66% dead", "opencode/mimo-v2.5-free"),
    ("nemotron-3-ultra-free  72% dead", "opencode/nemotron-3-ultra-free"),
    ("laguna-s-2.1-free  75% dead, thin data", "opencode/laguna-s-2.1-free"),
    ("deepseek-v4-flash-free  90% dead", "opencode/deepseek-v4-flash-free"),
    ("big-pickle  untested recently", "opencode/big-pickle"),
    ("hy3-free  untested recently", "opencode/hy3-free"),
]

TOKEN = secrets.token_urlsafe(16)
TAIL_LINES = 20
HOST = "127.0.0.1"          # never widen this


# ------------------------------------------------------------------ reading

def tail(path: Path, n: int = TAIL_LINES) -> list[str]:
    """Last n lines, with the permuter's carriage-return padding stripped.

    The permuter rewrites one status line in place using \\b and trailing
    spaces, so a raw tail is mostly backspaces. Cleaning here rather than in
    the browser keeps the payload small.
    """
    try:
        raw = path.read_text(errors="ignore")
    except OSError:
        return []
    lines = [re.sub(r"[\b\r]+", "", l).rstrip() for l in raw.splitlines()]
    return [l for l in lines if l][-n:]


def queue_counts() -> dict:
    if not QUEUE.is_file():
        return {"error": f"no queue at {QUEUE}"}
    c = Counter()
    for line in QUEUE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            c[json.loads(line).get("status", "?")] += 1
        except json.JSONDecodeError:
            c["malformed"] += 1
    return {"total": sum(c.values()), "by_status": dict(sorted(c.items()))}


def permuter_panels() -> list[dict]:
    """Panels for running permuter jobs.

    The "stalled" badge uses the SUPERVISOR's threshold, read from its state
    file, not a number of the dashboard's own. They disagreed before: the UI
    called a job stalled at 2000 iterations while the supervisor only acts at
    2500, so jobs sat there labelled stalled with nothing happening to them and
    the UI looked broken when it was merely using a different definition.
    """
    import jobs
    from permuter_stall import parse
    stall = 2500
    try:
        stall = int(json.loads(SUPERVISOR_STATE.read_text()).get("stall", 2500))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        pass
    out = []
    for jid in jobs.running_jobs("permuter"):
        log = JOBS_DIR / f"{jid}.log"
        d = parse(log.read_text(errors="ignore")) if log.is_file() else {
            "best": None, "iterations": 0, "since_improvement": 0,
            "failures": 0}
        parts = jid.split("-", 3)
        fn = parts[3] if len(parts) == 4 else jid
        # All-time best for the WORK DIR, not just this run. Without it the
        # panel reads as a regression whenever a fresh run has not yet beaten a
        # score an earlier run already banked: BO6_AguneaShuffleParams showed
        # "best 20" while output-10-1 sat on disk. The run number is honest but
        # incomplete, and incomplete looked like lost work.
        alltime = None
        try:
            wd = REPO / "nonmatchings" / fn
            if wd.is_dir():
                for c in wd.iterdir():
                    mm = re.fullmatch(r"output-(\d+)-\d+", c.name)
                    if mm and (c / "source.c").is_file():
                        v = int(mm.group(1))
                        if alltime is None or v < alltime:
                            alltime = v
        except OSError:
            pass
        out.append({"id": jid, "name": fn, "best": d["best"],
                    "alltime": alltime,
                    "iterations": d["iterations"],
                    "since": d["since_improvement"],
                    "failures": d["failures"],
                    "improving": d["since_improvement"] < stall,
                    "stall_at": stall,
                    "log": tail(log)})
    return out


def fleet_panels() -> list[dict]:
    """One panel per worker, each with ITS OWN pid and alive state.

    The first version showed a fleet-wide alive count on every panel, which is
    worse than showing nothing: four panels each reading "3 alive" tells you a
    worker is dead but not which, so you still have to go and diff the pid list
    against the logs by hand.

    The mapping is by name, not by launch order, which drifts the moment one
    worker dies and is not restarted. See the comment below on why the log and
    pid filenames do not actually share a stem.
    """
    out = []
    if not FLEET_LOGS.is_dir():
        return out
    for p in sorted(FLEET_LOGS.glob("worker-*.log")):
        # The log and the pid file do NOT share a stem. fleet_start names the
        # log worker-<tag>-<n>.log but exports WORKER_NAME=fleet-<tag>-<n>, and
        # the worker writes worker-<WORKER_NAME>.pid. So the pid file is
        # worker-fleet-<tag>-<n>.pid, with "fleet-" in the middle.
        #
        # Assuming a shared stem is why every panel read "pid -": the lookup
        # was for a filename that has never existed. Both spellings are tried
        # so this keeps working if the naming is ever unified.
        stem = p.stem                       # worker-<tag>-<n>
        rest = stem[len("worker-"):]
        pid = None
        for cand in (FLEET_LOGS / f"worker-fleet-{rest}.pid",
                     FLEET_LOGS / f"{stem}.pid"):
            try:
                t = cand.read_text().strip()
            except OSError:
                continue
            if t.isdigit():
                pid = int(t)
                break
        out.append({"name": p.stem.replace("worker-", ""),
                    "kind": "llama" if "-llama-" in p.name else "opencode",
                    "pid": pid,
                    "alive": pid_is_worker(pid),
                    "log": tail(p)})
    return out


def pid_is_worker(pid: int | None) -> bool:
    """Alive AND actually a worker, not a recycled pid.

    Checking /proc existence alone would call any process that inherited the
    number a live worker. The cmdline check is the same one commands_client
    uses, kept consistent on purpose: two different definitions of "alive"
    across the dashboard and the launcher is how you get a worker the UI shows
    as running that fleet_stop will not reap.
    """
    if not pid:
        return False
    proc = Path("/proc") / str(pid)
    if not proc.exists():
        return False
    try:
        text = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(
            "utf-8", errors="replace")
    except OSError:
        return False
    return "worker_direct.py" in text and "python" in text


def snapshot() -> dict:
    perm = permuter_panels()
    sup = {}
    if SUPERVISOR_STATE.is_file():
        try:
            sup = json.loads(SUPERVISOR_STATE.read_text())
        except (OSError, json.JSONDecodeError):
            sup = {}
    try:
        import commands_client as cc
        dry = bool(cc.DRYRUN)
    except Exception:
        dry = None
    # fleet_stop writes a HOLD file and fleet_start refuses while it exists.
    # That is a good safeguard and a terrible silent one: every press of the
    # fleet button returns "held" into a status line that is easy to miss,
    # while the panels sit unchanged and look like nothing happened.
    hold = REPO / "automation" / "logs" / "FLEET_HOLD"
    held = ""
    if hold.is_file():
        try:
            held = hold.read_text(errors="ignore").strip() or "on hold"
        except OSError:
            held = "on hold"
    return {"queue": queue_counts(), "permuter": perm, "dryrun": dry,
            "fleet_hold": held,
            "supervisor": sup, "fleet": fleet_panels()}


# ------------------------------------------------------------------ actions
# Zero-argument callables only. Nothing here takes user input, so no request
# can widen what runs. Adding an action means editing this file.

# Parameters each action accepts: name -> (min, max). INTEGERS ONLY, from a
# fixed key set, range-checked server-side. This is what keeps the earlier
# "no argv injection" property intact now that the UI has knobs: a request can
# choose a NUMBER inside a range, never a string, a flag, or a path. Anything
# else is rejected before an action is called.
ACTION_PARAMS: dict[str, dict[str, tuple[int, int]]] = {
    "permuter_start": {"slots": (1, 8), "threads": (1, 16),
                       "stall": (500, 50000), "cycles": (1, 8),
                       "max_iters": (1000, 500000)},
    "fleet_cli_start": {"workers": (1, 8)},
    "fleet_llama_start": {"workers": (1, 8)},
}


# Parameters that are a LIST of integers rather than one. Kept separate so the
# scalar path stays trivially auditable: name -> (item_min, item_max, max_len).
ACTION_LIST_PARAMS: dict[str, dict[str, tuple[int, int, int]]] = {
    "fleet_cli_start": {"models": (0, len(CLI_MODELS) - 1, 8)},
}


def validate_params(action: str, raw: dict) -> tuple[dict, str]:
    """(clean kwargs, error). Unknown keys and out-of-range values are errors,
    not silently dropped: a knob that appears to work and does nothing is the
    failure mode this whole session has been about."""
    spec = ACTION_PARAMS.get(action, {})
    lspec = ACTION_LIST_PARAMS.get(action, {})
    clean = {}
    for k, v in (raw or {}).items():
        if k in lspec:
            lo, hi, maxlen = lspec[k]
            if not isinstance(v, list):
                return {}, f"{k} must be a list, got {type(v).__name__}"
            if not v or len(v) > maxlen:
                return {}, f"{k} must have 1 to {maxlen} entries, got {len(v)}"
            out = []
            for item in v:
                try:
                    n = int(item)
                except (TypeError, ValueError):
                    return {}, f"{k} entries must be integers, got {item!r}"
                if not lo <= n <= hi:
                    return {}, (f"{k} entries must be between {lo} and {hi}, "
                                f"got {n}")
                out.append(n)
            clean[k] = out
            continue
        if k not in spec:
            return {}, f"unknown parameter {k!r} for {action}"
        try:
            n = int(v)
        except (TypeError, ValueError):
            return {}, f"{k} must be an integer, got {v!r}"
        lo, hi = spec[k]
        if not lo <= n <= hi:
            return {}, f"{k} must be between {lo} and {hi}, got {n}"
        clean[k] = n
    return clean, ""


def _sup(*args: str) -> dict:
    import subprocess
    py = os.environ.get("SOTN_PYTHON", sys.executable)
    r = subprocess.run([py, str(REPO / "automation" / "permuter_supervisor.py"),
                        *args], cwd=str(REPO), capture_output=True, text=True,
                       timeout=60)
    return {"ok": r.returncode == 0, "out": (r.stdout or r.stderr)[-4000:]}


SUP_LOG = Path(os.path.expanduser("~/sotn-work/supervisor.log"))


def _sup_start(slots: int = 3, threads: int = 4, stall: int = 2500,
               cycles: int = 4, max_iters: int = 50000) -> dict:
    """Start the supervisor detached, then CHECK it actually survived.

    The first version sent output to DEVNULL and returned {"ok": True}
    unconditionally. A supervisor that exited immediately -- because there were
    no runnable candidates, or because it raised on import -- produced exactly
    the same cheerful message as one that started work, and its reason went to
    /dev/null. That is the "the button does nothing" bug: it was not doing
    nothing, it was failing invisibly and reporting success.

    So: keep the output, wait briefly, and report what actually happened.
    """
    import subprocess
    py = os.environ.get("SOTN_PYTHON", sys.executable)
    SUP_LOG.parent.mkdir(parents=True, exist_ok=True)
    logf = open(SUP_LOG, "w")
    proc = subprocess.Popen(
        [py, str(REPO / "automation" / "permuter_supervisor.py"), "--run",
         "--slots", str(slots), "--threads", str(threads),
         "--stall", str(stall), "--cycles", str(cycles),
         "--max-iters", str(max_iters)],
        cwd=str(REPO), stdout=logf, stderr=subprocess.STDOUT,
        start_new_session=True)
    # Long enough for an immediate failure or an empty candidate list to show,
    # short enough not to hold the request open. A healthy supervisor is still
    # running after this and keeps going.
    time.sleep(2.5)
    rc = proc.poll()
    out = ""
    try:
        out = SUP_LOG.read_text(errors="ignore")[-3000:]
    except OSError:
        pass
    if rc is None:
        return {"ok": True,
                "out": f"supervisor running (pid {proc.pid})\n{out}".rstrip()}
    return {"ok": False,
            "out": (f"supervisor exited immediately with code {rc}. "
                    f"It did NOT start any jobs.\n{out}").rstrip()}


def _fleet(backend: str, default_n: int):
    def go(workers: int = default_n, models: list | None = None) -> dict:
        import commands_client as cc
        kw = {}
        if backend == "cli":
            # fleet_start assigns a comma-separated list round-robin, one model
            # per worker. Passing exactly `workers` entries therefore gives each
            # worker its own model, which is the bake-off shape: same fleet,
            # same functions, one variable.
            idx = models or [0]
            idx = (idx * workers)[:workers]      # pad by repeat if short
            kw["opencode_model"] = ",".join(CLI_MODELS[i][1] for i in idx)
        return {"ok": True, "out": str(cc.fleet_start(workers=workers,
                                                      backend=backend, **kw))}
    return go


def _fleet_stop() -> dict:
    import commands_client as cc
    # hold=True always: a killed worker cannot release its queue claim.
    return {"ok": True, "out": str(cc.fleet_stop(hold=True))}


def _fleet_clear_hold() -> dict:
    """Remove the HOLD that fleet_stop leaves behind.

    fleet_stop writes automation/logs/FLEET_HOLD and fleet_start refuses while
    it exists. That is deliberate: an unattended caller must not silently
    restart a fleet a human stopped. A human pressing this button IS the
    deliberate override the safeguard asks for, so it is exposed as its own
    action rather than folded into start -- clearing the hold and starting stay
    two separate, visible decisions.
    """
    hold = REPO / "automation" / "logs" / "FLEET_HOLD"
    if not hold.is_file():
        return {"ok": True, "out": "no hold in place"}
    why = ""
    try:
        why = hold.read_text(errors="ignore").strip()
        hold.unlink()
    except OSError as e:
        return {"ok": False, "out": f"could not clear hold: {e}"}
    return {"ok": True, "out": f"hold cleared (was: {why}). "
                               f"Press a fleet start button now."}


ACTIONS = {
    "permuter_start": _sup_start,
    "fleet_clear_hold": _fleet_clear_hold,
    "permuter_stop": lambda: _sup("--stop"),
    "permuter_plan": lambda: _sup("--plan"),
    "fleet_cli_start": _fleet("cli", 2),
    "fleet_llama_start": _fleet("http", 2),
    "fleet_stop": _fleet_stop,
}



# ------------------------------------------------------------- diagnostics
# One entry per button. Selected by INDEX, exactly like the model picker, so a
# request can choose one of these and nothing else. The script name and its
# arguments are fixed HERE, never taken from the client, which keeps the
# "no argv from a request" property that the rest of this file relies on.
#
# Every entry is read-only. permuter_promote is deliberately ABSENT even though
# it is allowlisted for run_analysis: it rewrites base.c, and a diagnostics tab
# is a place to look at things, not to change them by accident.
DIAGNOSTICS = [
    # label,                    script,                     args,      note
    ("Permuter plan", "permuter_supervisor.py", "--plan",
     "what would run next, and why the rest would not"),
    ("Permuter stalls", "permuter_stall.py", "--all",
     "true minimum per run, and whether it is still learning"),
    ("Fleet: empty responses", "empty_response_audit.py",
     "--timing --by-prompt-size",
     "dead rate per model, call timing, prompt-size correlation"),
    ("Quality audit", "quality_audit.py", "",
     "ILLEGAL names, invented symbols, magic numbers, duplicates"),
    ("Review checks", "review_checks.py", "",
     "what an upstream reviewer would reject"),
    ("Provenance check", "provenance_check.py", "",
     "does every matched function have evidence behind it"),
    ("Declaration coverage", "decl_coverage.py", "",
     "which todo functions have resolvable declarations"),
    ("Shim sweep", "shim_sweep.py", "",
     "stubs a shared header could retire"),
    ("Twin finder", "asm_twin_finder.py", "",
     "functions with a near-identical twin elsewhere"),
    ("Relocation check", "relocation_check.py", "",
     "symbols that moved and would silently break a match"),
    ("Escalation triage", "escalation_triage.py", "",
     "classify escalated records: harness, C89, symbol, or real"),
    ("Codebase index", "codebase_index.py", "",
     "rebuild the symbol/function index"),
    ("Prompt compaction", "test_prompt_compaction.py", "",
     "asm shrinks and no symbol is lost"),
    ("Permuter settings", "test_permuter_settings.py", "",
     "preserve_macros types are builtins, LOW/LOH absent"),
    ("Connector surfaces", "test_connector_surfaces.py", "",
     "REGISTRY and @mcp.tool() agree"),
    ("Self-test: supervisor", "permuter_supervisor.py", "--self-test",
     "the supervisor's own checks"),
    ("Self-test: audit", "empty_response_audit.py", "--self-test",
     "the audit parser's own checks"),
]


def run_diagnostic(index: int) -> dict:
    """Run one allowlisted diagnostic and return its text output."""
    import subprocess
    if not 0 <= index < len(DIAGNOSTICS):
        return {"ok": False, "out": f"no diagnostic {index}"}
    label, script, args, _ = DIAGNOSTICS[index]
    py = os.environ.get("SOTN_PYTHON", sys.executable)
    argv = [py, str(REPO / "automation" / script)] + args.split()
    t0 = time.time()
    try:
        r = subprocess.run(argv, cwd=str(REPO), capture_output=True,
                           text=True, timeout=600)
        out = (r.stdout or "") + (r.stderr or "")
        # Truncate from the FRONT: these reports put their conclusion last.
        if len(out) > 60000:
            out = "... (earlier output trimmed) ...\n" + out[-60000:]
        return {"ok": r.returncode == 0, "out": out.rstrip(),
                "label": label, "secs": round(time.time() - t0, 1)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "label": label,
                "out": f"{script} exceeded 600s and was killed."}
    except Exception as e:                                  # noqa: BLE001
        return {"ok": False, "label": label,
                "out": f"{type(e).__name__}: {e}"}


# ------------------------------------------------------------------- server

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):        # keep the console readable
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # This page must never be framed or sniffed into something executable.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            opts = "".join(
                f'<option value="{i}">{name}</option>'
                for i, (name, _) in enumerate(CLI_MODELS))
            self._send(200, PAGE.replace("__TOKEN__", TOKEN)
                       .replace("__MODELS__", opts).encode(),
                       "text/html; charset=utf-8")
        elif path == "/api/status":
            self._json(snapshot())
        elif path == "/api/diagnostics":
            self._json({"items": [{"label": l, "note": nt}
                                  for l, _, _, nt in DIAGNOSTICS]})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        # State changes are POST-only and token-gated, so nothing a browser
        # does on its own (prefetch, favicon, a link someone pastes) can reach
        # them.
        if self.headers.get("X-Token") != TOKEN:
            self._json({"error": "bad or missing token"}, 403)
            return
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/diag":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}") if n else {}
                idx = int(body.get("index", -1))
            except (ValueError, json.JSONDecodeError, TypeError):
                self._json({"ok": False, "out": "index must be an integer"})
                return
            self._json(run_diagnostic(idx))
            return
        name = path[len("/api/action/"):] if path.startswith(
            "/api/action/") else ""
        fn = ACTIONS.get(name)
        if fn is None:
            self._json({"error": f"unknown action {name!r}"}, 404)
            return
        raw = {}
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if 0 < n <= 4096:
                raw = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(raw, dict):
                raw = {}
        except (ValueError, json.JSONDecodeError):
            self._json({"ok": False, "out": "body must be a JSON object"}, 200)
            return
        kw, err = validate_params(name, raw)
        if err:
            self._json({"ok": False, "out": err}, 200)
            return
        try:
            self._json(fn(**kw))
        except Exception as e:                       # never 500 silently
            self._json({"ok": False, "out": f"{type(e).__name__}: {e}"}, 200)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve(port: int) -> int:
    PIDFILE.parent.mkdir(parents=True, exist_ok=True)
    PIDFILE.write_text(f"{os.getpid()} {port} {TOKEN}\n")
    # Without this, SIGTERM (which is what `sotn-dash stop` and any kill
    # sends) tears the process down without running the finally below, leaving
    # a pidfile behind that makes `status` report a server that is gone.
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(
        KeyboardInterrupt()))
    with Server((HOST, port), Handler) as srv:
        url = f"http://{HOST}:{port}/"
        # flush=True because stdout is block-buffered whenever this is not a
        # tty. Redirect `sotn-dash start` to a log without it and the URL and
        # token sit in the buffer until the process exits, which is exactly
        # when you no longer need them.
        print(f"dashboard on {url}", flush=True)
        print(f"token {TOKEN}  (embedded in the page; new one each restart)",
              flush=True)
        print("Ctrl-C, or: sotn-dash stop", flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nstopping")
        finally:
            PIDFILE.unlink(missing_ok=True)
    return 0


def read_pidfile() -> tuple[int, int] | None:
    try:
        parts = PIDFILE.read_text().split()
        return int(parts[0]), int(parts[1])
    except (OSError, ValueError, IndexError):
        return None


def stop() -> int:
    got = read_pidfile()
    if not got:
        print("no dashboard pidfile; nothing to stop")
        return 0
    pid, port = got
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"stopped dashboard pid {pid} (port {port})")
    except ProcessLookupError:
        print(f"pid {pid} was already gone")
    PIDFILE.unlink(missing_ok=True)
    return 0


def status() -> int:
    got = read_pidfile()
    if not got:
        print(json.dumps({"running": False}))
        return 0
    pid, port = got
    try:
        os.kill(pid, 0)
        alive = True
    except OSError:
        alive = False
    if not alive:
        # Self-heal: a pidfile for a process that no longer exists is worse
        # than no pidfile, because every later `status` repeats the same wrong
        # answer and `stop` has nothing to kill.
        PIDFILE.unlink(missing_ok=True)
    print(json.dumps({"running": alive, "pid": pid, "port": port,
                      "url": f"http://{HOST}:{port}/",
                      **({} if alive else
                         {"note": "stale pidfile removed"})}, indent=2))
    return 0


PAGE = r"""<!doctype html><meta charset=utf-8>
<title>SOTN harness</title>
<style>
:root{--bg:#12121a;--panel:#1b1b26;--line:#2e2e3d;--fg:#dcdce6;--dim:#8b8ba0;
      --ok:#5ec27a;--warn:#d9a441;--bad:#d4635f;--accent:#7aa2f7}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
     font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
header{display:flex;gap:16px;align-items:center;flex-wrap:wrap;
       padding:10px 16px;border-bottom:1px solid var(--line);position:sticky;
       top:0;background:var(--bg);z-index:2}
h1{font-size:14px;margin:0;letter-spacing:.08em;text-transform:uppercase}
button{background:var(--panel);color:var(--fg);border:1px solid var(--line);
       border-radius:5px;padding:5px 11px;cursor:pointer;font:inherit}
button:hover{border-color:var(--accent)}
button[disabled]{opacity:.45;cursor:not-allowed}
button.danger:hover{border-color:var(--bad);color:var(--bad)}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{background:var(--panel);border:1px solid var(--line);border-radius:999px;
      padding:2px 10px}
.chip b{color:var(--accent)}
.tabs{display:flex;gap:6px}
.tabs button{padding:5px 14px}
.tabs button.on{border-color:var(--accent);color:var(--accent)}
/* Diagnostics is a single scrolling pane, not a split: its output is long and
   wants the full width. */
#pane_diag{flex:1 1 auto;min-height:0;overflow:auto;padding:12px 16px;
           display:flex;flex-direction:column}
.diaggrid{display:grid;gap:8px;flex:0 0 auto;
          grid-template-columns:repeat(auto-fill,minmax(230px,1fr))}
.diagbtn{text-align:left;padding:8px 10px;line-height:1.35}
.diagbtn b{display:block;color:var(--fg)}
.diagbtn span{color:var(--dim);font-size:10px}
#diagout{margin-top:12px;flex:1 1 auto;min-height:0;overflow:auto;
         background:var(--panel);border:1px solid var(--line);
         border-radius:7px;padding:10px 12px;font-size:11px;
         white-space:pre;color:var(--fg)}
.ctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap;flex:0 0 auto;
     padding-bottom:10px;margin-bottom:4px;border-bottom:1px solid var(--line)}
.ctl label{color:var(--dim);display:flex;gap:4px;align-items:center;font-size:11px}
/* Per-worker model pickers sit in the SAME row as the fleet controls. They
   were on their own line below, which cost a full row of vertical space in a
   column whose whole job is showing worker logs. */
#f_rows{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.ctl input,.ctl select{background:var(--bg);color:var(--fg);
     border:1px solid var(--line);border-radius:4px;padding:3px 5px;
     font:inherit;font-size:11px;width:64px}
.ctl select{width:auto}
/* Two top-level columns: permuter on the left, fleet on the right. Each
   column scrolls independently so a chatty fleet cannot push the permuter
   panels off screen, which is the whole reason for splitting them. */
/* Full height minus header and the status bar, so nothing lands below the
   fold and the page never scrolls. The status bar is a fixed-height flex item
   rather than page content for the same reason. */
body{height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{flex:0 0 auto}
.split{display:grid;gap:0;grid-template-columns:1fr 1fr;
       flex:1 1 auto;min-height:0}
.split>section{padding:12px 16px;overflow:hidden;min-width:0;
               display:flex;flex-direction:column}
.split>section+section{border-left:1px solid var(--line)}
@media(max-width:900px){body{height:auto;overflow:auto}
  .split{grid-template-columns:1fr}
  .split>section+section{border-left:0;border-top:1px solid var(--line)}}
h2{font-size:12px;color:var(--dim);margin:0 0 8px;letter-spacing:.1em;
   text-transform:uppercase;flex:0 0 auto}
/* Panels share the column height equally. auto-rows would let one long log
   push the rest below the fold; 1fr per row means N live workers each get 1/N
   of the column and nothing needs page scrolling to be seen. */
.cols{display:grid;gap:12px;grid-template-columns:1fr;
      grid-auto-rows:1fr;height:100%;min-height:0}
.panel{min-height:0}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:7px;
       overflow:hidden;display:flex;flex-direction:column}
.phead{display:flex;justify-content:space-between;gap:8px;padding:7px 10px;
       border-bottom:1px solid var(--line);align-items:center}
.name{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.meta{color:var(--dim);font-size:11px;white-space:nowrap}
.bar{height:3px;background:var(--line)}
.bar>i{display:block;height:100%;background:var(--ok)}
pre{margin:0;padding:8px 10px;flex:1 1 auto;min-height:0;overflow:auto;font-size:11px;
    color:var(--dim);white-space:pre-wrap;word-break:break-word}
.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}
#out{flex:0 0 auto;padding:8px 16px;color:var(--dim);
     border-top:1px solid var(--line);white-space:pre-wrap;
     max-height:22vh;overflow:auto}
.empty{color:var(--dim);padding:6px 0}
</style>
<header>
  <h1>SOTN harness</h1>
  <div class=chips id=q></div>
  <span style="flex:1"></span>
  <div class=tabs>
    <button id=tab_mon class=on onclick="showTab('mon')">monitor</button>
    <button id=tab_diag onclick="showTab('diag')">diagnostics</button>
  </div>
</header>
<div class=split id=pane_mon>
  <section>
    <h2>Permuter</h2>
    <div class=ctl>
      <label>slots <input id=p_slots type=number value=3 min=1 max=8></label>
      <label>threads <input id=p_threads type=number value=4 min=1 max=16></label>
      <label>stall <input id=p_stall type=number value=2500 min=500 max=50000 step=500></label>
      <label>cycles <input id=p_cycles type=number value=4 min=1 max=8></label>
      <label>max it <input id=p_maxit type=number value=50000 min=1000 max=500000 step=5000></label>
      <button onclick="act('permuter_plan')">plan</button>
      <button onclick="act('permuter_start',permParams())">start</button>
      <button class=danger onclick="confirmAct('permuter_stop','Stop all permuter jobs?')">stop</button>
    </div>
    <div class=cols id=perm></div>
  </section>
  <section>
    <h2>Fleet</h2>
    <div class=ctl>
      <label>workers <input id=f_workers type=number value=2 min=1 max=8
                            oninput="renderWorkerRows()"></label>
      <label>backend
        <select id=f_backend onchange="renderWorkerRows()">
          <option value=fleet_cli_start>opencode cli</option>
          <option value=fleet_llama_start>local llama</option>
        </select>
      </label>
      <button onclick="act(el('f_backend').value,fleetParams())">start</button>
      <button class=danger onclick="confirmAct('fleet_stop','Stop all fleet workers and reclaim their queue records?')">stop</button>
      <span id=f_rows></span>
    </div>
    <div id=hold style="margin-bottom:8px"></div>
    <div class=cols id=fleet></div>
  </section>
</div>
<section id=pane_diag style="display:none">
  <h2>Diagnostics</h2>
  <div class=diaggrid id=diagbtns></div>
  <pre id=diagout>Pick a tool. Everything here is read-only.</pre>
</section>
<div id=out></div>
<script>
const TOKEN="__TOKEN__";
const el=(id)=>document.getElementById(id);
const esc=(s)=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

const MODEL_OPTS='__MODELS__';

function renderWorkerRows(){
  // One row per worker, so a 4-worker fleet is four explicit model choices
  // rather than one setting applied four times. That is what makes a bake-off
  // possible: same fleet, same functions, one variable per worker.
  const n=Math.max(1,Math.min(8,+el('f_workers').value||1));
  const cli=el('f_backend').value==='fleet_cli_start';
  const box=el('f_rows');
  if(!cli){ box.innerHTML='<span class=empty>llama workers take no per-worker model</span>'; return; }
  // Preserve existing choices when the count changes, so nudging workers from
  // 2 to 3 does not silently reset the two you already picked.
  const prev=[...box.querySelectorAll('select')].map(s=>s.value);
  let h='';
  for(let i=0;i<n;i++){
    h+=`<label>w${i+1} <select class=wmodel>${MODEL_OPTS}</select></label>`;
  }
  box.innerHTML=h;
  box.querySelectorAll('select').forEach((s,i)=>{ if(prev[i]!==undefined) s.value=prev[i]; });
}

function fleetParams(){
  const p={workers:+el('f_workers').value};
  // models is only meaningful for the cli backend; sending it to llama would be
  // rejected as an unknown parameter, which is correct but unhelpful.
  if(el('f_backend').value==='fleet_cli_start'){
    p.models=[...el('f_rows').querySelectorAll('select')].map(s=>+s.value);
  }
  return p;
}
function showTab(t){
  el('pane_mon').style.display = t==='mon' ? '' : 'none';
  el('pane_diag').style.display = t==='diag' ? '' : 'none';
  el('tab_mon').className = t==='mon' ? 'on' : '';
  el('tab_diag').className = t==='diag' ? 'on' : '';
}

let DIAGS=[];
async function loadDiags(){
  try{ DIAGS=(await (await fetch('/api/diagnostics')).json()).items; }
  catch(e){ return; }
  el('diagbtns').innerHTML = DIAGS.map((d,i)=>
    `<button class=diagbtn onclick="runDiag(${i})">`+
    `<b>${esc(d.label)}</b><span>${esc(d.note)}</span></button>`).join('');
}

async function runDiag(i){
  const btns=[...document.querySelectorAll('.diagbtn')];
  btns.forEach(b=>b.disabled=true);
  el('diagout').textContent = 'running '+DIAGS[i].label+' ...';
  try{
    const r=await fetch('/api/diag',{method:'POST',
      headers:{'X-Token':TOKEN,'Content-Type':'application/json'},
      body:JSON.stringify({index:i})});
    const j=await r.json();
    el('diagout').textContent =
      `${j.label||''}${j.secs!=null?'  ('+j.secs+'s)':''}`+
      `${j.ok===false?'   [non-zero exit]':''}\n\n${j.out||'(no output)'}`;
  }catch(e){ el('diagout').textContent='request failed: '+e; }
  btns.forEach(b=>b.disabled=false);
}

function permParams(){return{slots:+el('p_slots').value,
  threads:+el('p_threads').value,stall:+el('p_stall').value,
  cycles:+el('p_cycles').value,
  max_iters:+el('p_maxit').value};}

async function act(name,params){
  // Buttons disable while in flight so a double click cannot start two fleets.
  document.querySelectorAll('button').forEach(b=>b.disabled=true);
  el('out').textContent='running '+name+' ...';
  try{
    const r=await fetch('/api/action/'+name,{method:'POST',
      headers:{'X-Token':TOKEN,'Content-Type':'application/json'},
      body:JSON.stringify(params||{})});
    const j=await r.json();
    el('out').textContent=(j.out||JSON.stringify(j)).trim();
  }catch(e){ el('out').textContent='request failed: '+e; }
  document.querySelectorAll('button').forEach(b=>b.disabled=false);
  refresh();
}
function confirmAct(name,msg,params){ if(confirm(msg)) act(name,params); }

function panel(title,meta,cls,lines,pct){
  return `<div class=panel><div class=phead>
     <span class=name>${esc(title)}</span>
     <span class="meta ${cls}">${esc(meta)}</span></div>
     ${pct!=null?`<div class=bar><i style="width:${pct}%"></i></div>`:''}
     <pre>${esc(lines.join('\n'))||'(no output yet)'}</pre></div>`;
}

async function refresh(){
  let s; try{ s=await (await fetch('/api/status')).json(); }catch(e){ return; }

  const q=s.queue.by_status||{};
  // A silent dry-run is how the fleet buttons "did nothing" for an afternoon.
  const dry = s.dryrun ? '<span class="chip bad">DRY RUN &mdash; nothing will actually launch</span>' : '';
  // The hold is the single most common reason a fleet start "does nothing".
  el('hold').innerHTML = s.fleet_hold
    ? `<span class="chip bad">FLEET ON HOLD &mdash; ${esc(s.fleet_hold)}</span>`
      + ` <button onclick="act('fleet_clear_hold')">clear hold</button>`
    : '';
  el('q').innerHTML = dry + (s.queue.error ? `<span class="chip bad">${esc(s.queue.error)}</span>`
    : Object.entries(q).map(([k,v])=>`<span class=chip>${esc(k)} <b>${v}</b></span>`)
        .join('') + `<span class=chip>total <b>${s.queue.total}</b></span>`);

  el('perm').innerHTML = s.permuter.length ? s.permuter.map(p=>{
    const cls = p.best===0 ? 'ok' : (p.improving ? '' : 'warn');
    // Show the run's best AND the dir's all-time best when they differ, so a
    // fresh run that has not yet caught up does not read as lost progress.
    const at = (p.alltime!=null && p.alltime!==p.best) ? ` (best ever ${p.alltime})` : '';
    const meta = `run ${p.best==null?'-':p.best}${at} · ${p.iterations} it`
               + (p.improving?'':' · stalled')
               + (p.failures?` · ${p.failures} rej`:'');
    // Progress is "how far into the stall window", the only bounded quantity
    // the permuter has. It is not progress toward a match; there is no such
    // number, because the search is unbounded.
    const pct = Math.min(100, Math.round(p.since/2000*100));
    return panel(p.name, meta, cls, p.log, pct);
  }).join('') : '<div class=empty>no permuter jobs running</div>';

  // Only live workers. Dead ones are logs from a previous run and their
  // presence is pure noise: four DEAD panels crowd out the two that are
  // actually working. The count of hidden ones is still reported, so this
  // hides clutter without hiding information.
  const live = s.fleet.filter(f=>f.alive);
  const dead = s.fleet.length - live.length;   // only used in the empty state
  el('fleet').innerHTML = live.length ? live.map(f=>
      panel(f.name, `${f.kind} · pid ${f.pid} · alive`, 'ok', f.log)
    ).join('')
    : `<div class=empty>no live fleet workers${dead?` (${dead} stopped)`:''}</div>`;

}
renderWorkerRows(); loadDiags();
refresh(); setInterval(refresh,3000);
</script>
"""


def self_test() -> int:
    import tempfile
    fails = []

    def ck(c, l):
        print(("  ok   " if c else "  FAIL ") + l)
        if not c:
            fails.append(l)

    global QUEUE
    print("\nsafety invariants")
    ck(HOST == "127.0.0.1", "binds loopback only, never 0.0.0.0")
    ck(all(callable(v) for v in ACTIONS.values()),
       "every action is a zero-argument callable, so no request supplies argv")
    src = Path(__file__).read_text()
    # Everything BEFORE self_test. The first version of this check searched the
    # whole file and failed on the literal inside its own assertion, which is a
    # neat demonstration of why a grep-style test has to exclude itself.
    code = src[:src.index("def self_test")]
    ck("shell=True" not in code, "no shell=True anywhere in the request path")
    ck("os.system" not in code and "eval(" not in code,
       "no os.system or eval in the request path either")
    ck('self.headers.get("X-Token")' in src, "POST checks the token")
    ck(src.index("def do_POST") > 0 and "X-Token" not in
       src[src.index("def do_GET"):src.index("def do_POST")],
       "GET does NOT require a token, because GET cannot change state")
    ck("hold=True" in src, "fleet stop always reclaims queue records")
    ck(len(TOKEN) >= 20, "token is long and random")

    print("\ntail cleaning")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.log"
        p.write_text("iteration 1, score = 70\b\b\b\b     \n"
                     "\niteration 2, score = 0\r\n")
        t = tail(p)
        ck(t == ["iteration 1, score = 70", "iteration 2, score = 0"],
           f"backspace padding and blank lines are stripped ({t})")
        ck(tail(Path(td) / "missing.log") == [],
           "a missing log gives an empty tail, not an exception")

        print("\nqueue counting")
        QUEUE = Path(td) / "q.jsonl"
        QUEUE.write_text('{"status":"near"}\n{"status":"near"}\n'
                         '{"status":"matched"}\nGARBAGE\n')
        qc = queue_counts()
        ck(qc["by_status"] == {"malformed": 1, "matched": 1, "near": 2},
           f"counts by status and flags malformed lines ({qc['by_status']})")
        ck(qc["total"] == 4, "total includes the malformed line")
        QUEUE = Path(td) / "gone.jsonl"
        ck("error" in queue_counts(), "a missing queue reports an error, not a crash")

    print("\nper-worker pid mapping")
    global FLEET_LOGS
    with tempfile.TemporaryDirectory() as td:
        FLEET_LOGS = Path(td)
        (FLEET_LOGS / "worker-oc-1.log").write_text("hello\n")
        (FLEET_LOGS / "worker-oc-1.pid").write_text(f"{os.getpid()}\n")
        (FLEET_LOGS / "worker-llama-2.log").write_text("hi\n")
        (FLEET_LOGS / "worker-llama-2.pid").write_text("999999\n")
        (FLEET_LOGS / "worker-oc-3.log").write_text("no pidfile\n")
        fp = {f["name"]: f for f in fleet_panels()}
        ck(set(fp) == {"oc-1", "llama-2", "oc-3"},
           f"one panel per worker log ({sorted(fp)})")
        ck(fp["oc-1"]["pid"] == os.getpid(),
           "each panel carries its OWN pid, not a fleet-wide count")
        ck(fp["llama-2"]["pid"] == 999999 and not fp["llama-2"]["alive"],
           "a pid that is gone reports alive=False")
        ck(fp["oc-3"]["pid"] is None and not fp["oc-3"]["alive"],
           "a log with no pidfile degrades to pid None, not an exception")
        ck(fp["llama-2"]["kind"] == "llama" and fp["oc-1"]["kind"] == "opencode",
           "backend is read from the log name")
        # This process is alive but is NOT worker_direct.py, so a bare /proc
        # existence check would wrongly call it a live worker.
        ck(fp["oc-1"]["alive"] is False,
           "a live non-worker pid is not counted as a worker (cmdline checked)")
        ck(pid_is_worker(None) is False and pid_is_worker(0) is False,
           "None and 0 are not workers")

    print("\nstale pidfile self-heals")
    global PIDFILE
    with tempfile.TemporaryDirectory() as td:
        PIDFILE = Path(td) / "dash.pid"
        PIDFILE.write_text("999999 8777 tok\n")
        status()
        ck(not PIDFILE.exists(),
           "status removes a pidfile whose process is gone, so it cannot keep "
           "reporting a server that does not exist")

    print("\ndiagnostics are index-selected and read-only")
    ck(all(len(d) == 4 for d in DIAGNOSTICS),
       "every entry is (label, script, args, note)")
    ck(not any(d[1] == "permuter_promote.py" for d in DIAGNOSTICS),
       "the one WRITING tool is excluded; a diagnostics tab looks, it does not "
       "change base.c by accident")
    ck(run_diagnostic(-1)["ok"] is False
       and run_diagnostic(len(DIAGNOSTICS))["ok"] is False,
       "out-of-range indices are refused rather than clamped")
    ck("index" in PAGE and "/api/diag" in PAGE,
       "the page posts an index, never a script name")
    src_diag = src[src.index("def run_diagnostic"):]
    src_diag = src_diag[:src_diag.index("\n\n\n")]
    ck("DIAGNOSTICS[index]" in src_diag,
       "the script and its args come from the registry, not the request")
    ck("shell=True" not in src_diag, "and it never uses a shell")

    print("\nthe page")
    ck("__TOKEN__" in PAGE, "page carries a token placeholder")
    ck("pid ${f.pid} · alive" in PAGE,
       "live workers show their own pid")
    ck("s.fleet.filter(f=>f.alive)" in PAGE,
       "dead workers are filtered out of the fleet column")
    ck("no live fleet workers" in PAGE,
       "the empty state still says whether stopped workers exist")
    ck("grid-auto-rows:1fr" in PAGE,
       "panels share the column height instead of overflowing it")
    ck("body{height:100vh" in PAGE and "overflow:hidden" in PAGE,
       "the page is exactly one viewport tall, so the status bar cannot push "
       "content below the fold")
    ck("__MODELS__" in PAGE, "the page has a model-options placeholder")
    ck(len(CLI_MODELS) == 8, f"every Zen model is selectable ({len(CLI_MODELS)})")
    ck(all("," not in m for _, m in CLI_MODELS),
       "each entry is ONE model; mixing is now per-worker, not a preset")
    ck(any("% dead" in n for n, _ in CLI_MODELS),
       "labels carry a measured dead-rate rather than a folklore verdict")
    ck("ling-3.0-flash-free" in CLI_MODELS[0][0],
       "the default is the model with the best measured record, not the one "
       "an out-of-date doc recommends")
    ck("renderWorkerRows" in PAGE and "class=wmodel" in PAGE,
       "the page renders one model row per worker")
    ck("best ever" in PAGE,
       "a run that has not yet beaten the dir's all-time best says so, instead "
       "of looking like the score went backwards")
    ck("class=split" in PAGE and "grid-template-columns:1fr 1fr" in PAGE,
       "permuter and fleet are side-by-side columns")
    ck(PAGE.index("id=perm") < PAGE.index("id=fleet"),
       "permuter is the left column")
    ck("s.dryrun ?" in PAGE,
       "a dry run is announced in the header, never silent")

    print("\ndry run must not be silently on")
    import commands_client as cc
    ck(os.environ.get("SOTN_CMD_DRYRUN") == "0",
       "the dashboard opts in to live mode before importing commands_client")
    ck(cc.DRYRUN is False,
       "so commands_client is live, not reporting what it 'would' do")
    ck(snapshot().get("dryrun") is False,
       "and /api/status exposes the state so the UI can show it")
    ck("setInterval" in PAGE, "page refreshes itself")
    ck("confirm(" in PAGE, "destructive buttons confirm first")
    ck("b.disabled=true" in PAGE, "buttons disable in flight, so no double-start")
    ck("esc(" in PAGE and "&lt;" in PAGE,
       "log text is escaped before it reaches the DOM")

    print()
    if fails:
        print(f"{len(fails)} FAILED")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--port", type=int, default=8777)
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.stop:
        return stop()
    if a.status:
        return status()
    if a.serve:
        return serve(a.port)
    ap.error("pass --serve, --stop, --status or --self-test")


if __name__ == "__main__":
    raise SystemExit(main())
