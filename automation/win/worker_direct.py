#!/usr/bin/env python3
"""
worker_direct.py: harness-driven matcher. The model never uses tools.

WHY THIS EXISTS
---------------
The OpenCode-agent version (worker_win.py) failed repeatedly, not because the
model could not decompile, but because it spent its entire 100k context
DISCOVERING things: listing the repo tree, recursing asm/us, reading
work/queue.jsonl, probing for tools, even hand-writing a MIPS disassembler.
By the time it had the facts it was compacted and lost them.

So we invert it. The harness does every mechanical step:
  1. run tools/m2ctx.py   (in WSL, needs gcc) -> ctx.c with real type info
  2. run tools/m2c/m2c.py (in WSL) with that context -> a TYPED first draft
  3. read the reference .s and the target source file
  4. send ONE prompt to llama-server: asm + draft + context -> C function
  5. apply the edit, build, and check the oracle
  6. on failure, feed back the compiler error or diff and retry

The model does exactly one thing: turn a rough draft into better C. That is
what a ~3B-active model is good at. No tools, no exploration, no MCP.

ORACLE
------
Definitive: after a successful build, the overlay binary must match its SHA-1
in config/check.<version>.sha. That is binary pass/fail, no percentage parsing.
asm-differ output is used only as feedback text between attempts.

Usage (PowerShell, from the repo root):
    python automation\\win\\worker_direct.py once
    python automation\\win\\worker_direct.py loop --max 20
    python automation\\win\\worker_direct.py once --dry-run

Env: SOTN_WIN_REPO, SOTN_WSL_DISTRO, LLAMA_BASE_URL, LLAMA_MODEL,
     MAX_ATTEMPTS (default 4), GEN_TIMEOUT (default 600)
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

IS_WINDOWS = os.name == "nt"
# Runs on Windows (driving wsl.exe) or natively inside WSL. The latter lets the
# sotn-cmd connector start a fleet without a human at a PowerShell prompt.
# Repo root is DERIVED, never hardcoded: this file lives at
# <repo>/automation/win/worker_direct.py, so two levels up is the root. Keeping a
# machine-specific absolute path here would leak the author's home directory into
# a public repo and break on every other machine. Override with SOTN_WIN_REPO.
_DEFAULT_REPO = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
WIN_REPO = os.environ.get("SOTN_WIN_REPO", _DEFAULT_REPO)
DISTRO = os.environ.get("SOTN_WSL_DISTRO", "Ubuntu-24.04")
LLAMA_URL = os.environ.get("LLAMA_BASE_URL", "http://localhost:8081/v1")
# Optional bearer token. Local llama-server needs none, but any hosted
# OpenAI-compatible endpoint (OpenCode Zen, NVIDIA build.nvidia.com, OpenRouter)
# will reject unauthenticated requests. Set MODEL_API_KEY to switch providers
# without touching code.
MODEL_API_KEY = os.environ.get("MODEL_API_KEY", "").strip()
# Free hosted tiers rate-limit hard. Local llama never did, so the worker had no
# retry path at all and a single 429 killed the function outright.
RATE_LIMIT_RETRIES = int(os.environ.get("RATE_LIMIT_RETRIES", "5"))
RATE_LIMIT_BACKOFF = float(os.environ.get("RATE_LIMIT_BACKOFF", "20"))

# Backend selection.
#   "http" (default) -> POST to an OpenAI-compatible endpoint. Local llama-server.
#   "cli"            -> shell out to `opencode run`. Uses OpenCode's own auth, so
#                       the free Zen models work with NO API key and NO billing.
#                       Verified 2026-07-20: `opencode auth list` showed 0
#                       credentials and a free model still answered.
# TRADE-OFF: the CLI returns output only when the run finishes, so there is no
# token stream. The live degeneration detector and REASON_CAP both watch the
# stream and cannot function here. FUNC_BUDGET is the only remaining backstop
# against a wedged generation, so keep it set.
MODEL_BACKEND = os.environ.get("MODEL_BACKEND", "http").strip().lower()
# Free Zen models split cleanly into ones that answer and ones that return an
# empty body. Measured 2026-08-02, one model per worker on real queue functions:
#
#   WORK: deepseek-v4-flash-free, nemotron-3-ultra-free, mimo-v2.5-free
#   DEAD: big-pickle, north-mini-code-free, ling-3.0-flash-free, laguna-s-2.1-free
#
# deepseek is the default because it was the only model to produce clean C on
# the first attempt at every size tested. Full table in
# automation/opencode/ZEN-FREE-MODELS.md.
#
# Note that "the cli backend returns nothing" had TWO independent causes, which
# is why it resisted diagnosis for so long: half the models genuinely return an
# empty body, AND every prompt over 32767 chars failed to exec at all. Fixing
# either one alone still looks broken. See the Popen call for the second.
OPENCODE_MODEL = os.environ.get("OPENCODE_MODEL", "opencode/deepseek-v4-flash-free")
# Optional: point at a running `opencode serve` to skip MCP cold-boot per call.
OPENCODE_ATTACH = os.environ.get("OPENCODE_ATTACH", "").strip()
# Tool-less agent defined in automation/opencode/opencode.json. Must be used, or
# opencode run defaults to the tool-enabled "build" agent and explores the repo.
OPENCODE_AGENT = os.environ.get("OPENCODE_AGENT", "raw")
# Explicit path or command name. Set this if auto-detection picks the wrong one.
OPENCODE_BIN = os.environ.get("OPENCODE_BIN", "").strip()


class OpencodeMissing(RuntimeError):
    """The OpenCode CLI could not be located on PATH."""


# Resolved lazily and cached: shutil.which touches the filesystem for every PATH
# entry, and the Windows PATH visible from WSL is long.
_OPENCODE_RESOLVED: str | None = None


def _opencode_candidates() -> list[str]:
    """Names to try, most specific first.

    OpenCode is installed here as a Windows program, `opencode.CMD`. A worker
    running natively on Windows resolves a bare `opencode` fine, because cmd
    applies PATHEXT. A worker running INSIDE WSL does not: WSL appends the
    Windows PATH so the file is reachable, but Linux exec has no PATHEXT, so
    the extensionless name never matches and you get FileNotFoundError on every
    single generation. That is why the extensions are listed explicitly.
    """
    if OPENCODE_BIN:
        return [OPENCODE_BIN]
    if IS_WINDOWS:
        return ["opencode", "opencode.cmd", "opencode.exe"]
    # Inside WSL a native Linux install should win over the Windows one: calling
    # across the interop boundary costs roughly 200ms per invocation and drags
    # in Windows path translation.
    return ["opencode", "opencode.cmd", "opencode.CMD", "opencode.exe",
            "opencode.bat"]


def resolve_opencode() -> str:
    """Return an executable path for the OpenCode CLI, or raise OpencodeMissing.

    An absolute OPENCODE_BIN is trusted as given so a non-PATH install works.
    """
    global _OPENCODE_RESOLVED
    if _OPENCODE_RESOLVED:
        return _OPENCODE_RESOLVED
    tried = []
    for name in _opencode_candidates():
        if os.path.isabs(name) and os.path.exists(name):
            _OPENCODE_RESOLVED = name
            return name
        found = shutil.which(name)
        tried.append(name)
        if found:
            _OPENCODE_RESOLVED = found
            return found
    raise OpencodeMissing(
        "OpenCode CLI not found. Tried: " + ", ".join(tried) +
        f" (platform={'windows' if IS_WINDOWS else 'posix/wsl'}). "
        "Set OPENCODE_BIN to the full path, or run the fleet on Windows where "
        "opencode.CMD lives.")


def opencode_preflight(timeout: float = 30.0) -> dict:
    """Prove the CLI exists AND runs before a fleet commits to it.

    Launching four workers against a broken CLI is not a harmless mistake: each
    one claims a queue record, fails every attempt, and marks the function
    escalated. The queue ends up poisoned with failures that say nothing about
    the function. So check once, up front, and refuse rather than discover it
    four workers deep.
    """
    path = resolve_opencode()
    p = subprocess.run([path, "--version"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout,
                       stdin=subprocess.DEVNULL)
    ok = p.returncode == 0
    return {"ok": ok, "path": path,
            "version": (p.stdout or "").strip()[:120],
            "stderr": (p.stderr or "").strip()[:300],
            "returncode": p.returncode}


class _EmptyOutput(RuntimeError):
    """opencode returned rc=0 with no output. Transient; retry the call."""


def _opencode_run(prompt: str, timeout: float | None = None) -> str:
    """Retry wrapper. Empty output is transient, so do not waste the attempt."""
    deadline = None if timeout is None else time.time() + timeout
    last = None
    for n in range(1, RATE_LIMIT_RETRIES + 1):
        left = None if deadline is None else deadline - time.time()
        if left is not None and left <= 15:
            break
        try:
            return _opencode_run_once(prompt, timeout=left)
        except _EmptyOutput as e:
            last = e
            print(f"  !! empty response ({n}/{RATE_LIMIT_RETRIES}): {e}",
                  flush=True)
            time.sleep(5)
    raise RuntimeError(f"opencode returned empty output repeatedly: {last}")


def _opencode_run_once(prompt: str, timeout: float | None = None) -> str:
    """Run one non-interactive completion through the OpenCode CLI.

    argv, never shell=True: the prompt contains assembly, braces and quotes that
    would be mangled or worse by a shell.

    The prompt itself is piped on stdin rather than passed as an argument. The
    old claim here, that "prompts here run well under 20KB", was measured on
    four small functions and is false for the population: the median remaining
    function yields a ~13KB prompt and the largest yields ~156KB. See the long
    note at the Popen call.
    """
    # --agent raw and --auto are BOTH required.
    #
    # Without --agent, `opencode run` uses the default "build" agent, which has
    # read/grep/edit/bash and will start exploring the repository instead of
    # answering. Observed 2026-07-20: a 2189-char prompt hit the 600s timeout
    # having produced nothing. That is the exact failure that killed the earlier
    # worker_win.py agent design, described at the top of this file.
    #
    # Without --auto, a tool-capable agent can block on a permission prompt that
    # nobody is there to answer, which looks identical to a hang.
    #
    # The "raw" agent is defined in automation/opencode/opencode.json with every
    # tool disabled, so it can only answer. OPENCODE_CONFIG must point at that
    # file or the agent will not be found.
    argv = [resolve_opencode(), "run", "--model", OPENCODE_MODEL,
            "--agent", OPENCODE_AGENT, "--auto"]
    if OPENCODE_ATTACH:
        argv += ["--attach", OPENCODE_ATTACH]
    # The prompt is PIPED, not appended to argv. See the stdin note below; this
    # is the single most important line in this function.
    print(f"  --- opencode run ({OPENCODE_MODEL}, prompt {len(prompt)} chars, "
          f"streaming) ---", flush=True)
    t0 = time.time()
    _to = GEN_TIMEOUT if timeout is None else max(15.0, min(GEN_TIMEOUT, timeout))

    # STREAMED via Popen, not subprocess.run.
    #
    # subprocess.run blocks until the process exits and hands back one final
    # blob. That gave the cli backend no token stream, so the degeneration
    # detector and the live echo (both of which watch a stream) were inert, and
    # every retry re-sent the same prompt blind. Reading stdout incrementally
    # restores all of it on the free CLI, no API key, no server.
    #
    # CAVEAT this design accepts: it only helps if `opencode run` writes to
    # stdout incrementally in a non-TTY. If it buffers until exit, the reads
    # simply all arrive at the end and behaviour degrades to the old blocking
    # case, no worse. The live test tells us which it is on the first function.
    #
    # THE PROMPT GOES ON STDIN. Do not move it back onto argv.
    #
    # opencode here is a Windows .exe invoked from WSL, so the whole command
    # line must fit Windows CreateProcess's 32767-character limit. Past that the
    # process never starts: rc=1, "opencode.exe: Invalid argument", in 0.0s.
    #
    # This produced months of misdiagnosis, because a failure to EXEC looks
    # exactly like a model returning an empty body. Quota, auth, agent
    # resolution, stdout routing and model choice were all investigated and
    # cleared before the real cause was found. Measured with
    # automation/opencode_size_bisect.py on 2026-08-02:
    #
    #     argv:   32000 chars ok  ->  32700 chars "Invalid argument" in 0.0s
    #     stdin:  40000, 80000, 120000 chars ALL answer normally
    #
    # This is not a tuning knob. 59% of the remaining functions produce prompts
    # over 32767 chars (p50 ~13k, p90 ~55k, max ~156k), so on argv the majority
    # of the work left is unreachable no matter which model is selected.
    #
    # Closing stdin after the write is what makes this safe: opencode probes
    # stdin when it is not a TTY, and an unclosed pipe blocks forever. That is
    # the hang the previous stdin=DEVNULL was defending against.
    proc = subprocess.Popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.PIPE, cwd=WIN_REPO, text=True,
        encoding="utf-8", errors="replace", bufsize=1)

    def feed():
        # In its own thread: a prompt larger than the pipe buffer (64KB on
        # Linux) blocks mid-write until the child drains it, and the child may
        # not drain until it has written stdout that nobody is reading yet.
        # Writing inline would deadlock on exactly the large prompts this
        # change exists to support.
        try:
            proc.stdin.write(prompt)
            proc.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            pass  # child already gone; proc.wait below reports the real error

    threading.Thread(target=feed, daemon=True).start()

    degenerating = make_degeneration_detector()
    buf: list[str] = []
    last_check = [0]
    aborted = [""]
    done = threading.Event()

    def pump():
        try:
            for line in proc.stdout:
                buf.append(line)
                print(f"  | {line.rstrip()}", flush=True)
                total = sum(len(x) for x in buf)
                # Check every ~500 new chars, not every line: the detector
                # re-scans the whole buffer and per-line would be O(n^2).
                if total - last_check[0] >= 500:
                    last_check[0] = total
                    why = degenerating(buf)
                    if why:
                        aborted[0] = why
                        proc.kill()
                        return
        finally:
            done.set()

    t = threading.Thread(target=pump, daemon=True)
    t.start()
    try:
        proc.wait(timeout=_to)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise
    done.wait(timeout=5)
    out = "".join(buf)
    err = (proc.stderr.read() or "").strip() if proc.stderr else ""

    if aborted[0]:
        # Degenerate output is not empty-transient; the model IS answering, just
        # badly. Surface it as a normal failure so the attempt is spent and the
        # retry can carry different feedback.
        raise RuntimeError(f"opencode degenerated: {aborted[0]}")
    if proc.returncode not in (0, None) and not out.strip():
        raise RuntimeError(
            f"opencode run failed (rc={proc.returncode}): {err[:800]}")
    print(f"  --- done in {int(time.time() - t0)}s: {len(out)} chars ---",
          flush=True)
    if not out.strip():
        # rc=0 with EMPTY stdout: transient gateway drop, correlated with large
        # prompts. Retry rather than escalate the whole function.
        raise _EmptyOutput(
            f"rc=0 but NO output after {int(time.time() - t0)}s "
            f"(prompt {len(prompt)} chars). stderr: {err[:300]}")
    return out


def _api_headers() -> dict:
    h = {"Content-Type": "application/json"}
    if MODEL_API_KEY:
        h["Authorization"] = f"Bearer {MODEL_API_KEY}"
    return h


def _open_with_backoff(req, timeout: float):
    """urlopen with retry on 429 and 5xx.

    Returns the open response. Raises the final error if retries are exhausted.
    Honours Retry-After when the server sends it, otherwise backs off linearly.
    """
    last = None
    for attempt in range(1, RATE_LIMIT_RETRIES + 1):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                raise
            wait = RATE_LIMIT_BACKOFF * attempt
            ra = e.headers.get("Retry-After") if e.headers else None
            if ra:
                try:
                    wait = max(wait, float(ra))
                except ValueError:
                    pass
            print(f"  !! HTTP {e.code} from model endpoint; retry "
                  f"{attempt}/{RATE_LIMIT_RETRIES} in {wait:.0f}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(
        f"model endpoint kept failing after {RATE_LIMIT_RETRIES} retries: {last}")
LLAMA_MODEL = os.environ.get(
    "LLAMA_MODEL",
    "Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-APEX-MTP-I-Compact.gguf")
WORKER_NAME = os.environ.get("WORKER_NAME", f"{socket.gethostname()}-{os.getpid()}")
MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", "4"))
GEN_TIMEOUT = float(os.environ.get("GEN_TIMEOUT", "600"))
BUILD_TIMEOUT = float(os.environ.get("BUILD_TIMEOUT", "900"))
MAX_ASM_CHARS = int(os.environ.get("MAX_ASM_CHARS", "12000"))
MAX_CTX_CHARS = int(os.environ.get("MAX_CTX_CHARS", "8000"))
# A reasoning model can think forever on a huge function. Cap it, and skip
# functions that are simply too large for this tier to have a chance at.
# Observed: clean generations land at 490-870 reasoning tokens, so 1200 was
# clipping the slower-but-still-productive tail into the forced-code path.
# Raised again to 3000 on 2026-07-20: the model is now also required to work out
# what the function DOES and name locals meaningfully (see MATCHING-LESSONS.md
# section 8), which is real additional inference, not just transcription. A cap
# tuned for bare codegen would push annotation work into the salvage path.
# Still well inside the per-slot budget (60k context / 4 slots = 15104, prompts
# run ~1000-2400 tokens). Runaway loops are caught by degenerating() on their
# own, independently of this ceiling.
REASON_CAP = int(os.environ.get("REASON_CAP", "3000"))
# Largest function this tier will attempt, in chars of assembly.
#
# BACKEND-DEPENDENT. 6000 is calibrated for local llama, which loses coherence
# well before that (the 2026-07-21 logs show degenerate-loop aborts on far
# smaller inputs). Hosted OpenCode models take much more context, so the cli
# tier exists precisely to pick up what llama defers.
#
# Deferring is therefore a HANDOFF, not a dead end: see DEFER_TOO_LARGE and
# scheduler `next --include-deferred`.
_DEFAULT_MAX_FUNC = "20000" if MODEL_BACKEND == "cli" else "6000"
MAX_FUNC_CHARS = int(os.environ.get("MAX_FUNC_CHARS", _DEFAULT_MAX_FUNC))
# Stable marker in the notes so the next tier can find exactly these records.
# Matching on prose would break the moment someone reworded the message.
DEFER_TOO_LARGE = "TIER_HANDOFF_TOO_LARGE"
# Hard wall-clock ceiling for one function across ALL attempts. Without it,
# MAX_ATTEMPTS forced passes at GEN_TIMEOUT each can silently burn ~40 minutes.
#
# The default is BACKEND-DEPENDENT because the two differ by roughly 3x per
# attempt. Local llama streams and is cut short by the degeneration detector,
# so it rarely approaches the ceiling. A hosted OpenCode run returns only when
# complete and was measured at 120-190s per attempt on 2026-07-21 (2397-2470
# char prompts). Against the shared 900s budget that left 191s per attempt, so
# attempts were timing out roughly as often as they finished.
#
# 1800s keeps four real attempts on the cli backend (~382s each). Raise it
# rather than cutting MAX_ATTEMPTS: retries are the only consumer of asm-differ
# feedback, so trading them away makes every attempt a blind first attempt.
_DEFAULT_FUNC_BUDGET = "1800" if MODEL_BACKEND == "cli" else "900"
FUNC_BUDGET = float(os.environ.get("FUNC_BUDGET", _DEFAULT_FUNC_BUDGET))
# Per-ATTEMPT ceiling, derived from the function budget so the retries actually
# happen. Without it a single attempt consumed the whole 900s (observed
# 2026-07-20: "BUDGET EXHAUSTED after 900.0s (1 attempts)" repeatedly), which
# silently disabled the retry loop. That matters more than it sounds, because
# retries are the ONLY consumer of asm-differ feedback: attempt 1 has no diff to
# learn from by definition. A blind first attempt is all we were ever running.
# Default leaves a little headroom for the build and diff between attempts.
ATTEMPT_BUDGET = float(os.environ.get(
    "ATTEMPT_BUDGET", str(FUNC_BUDGET / max(1, MAX_ATTEMPTS) * 0.85)))


class Status:
    """Live one-line progress with a spinner and elapsed time.

    Every slow step here (model generation, m2c, the build) blocks for tens of
    seconds to minutes. Without this the console looks identical to a hang,
    which is indistinguishable from a real failure.
    """

    SPIN = "-\\|/"

    def __init__(self, label: str):
        self.label = label
        self.extra = ""
        self._stop = threading.Event()
        self._t0 = time.time()
        self._thread: threading.Thread | None = None
        self._tty = sys.stdout.isatty()

    def update(self, extra: str) -> None:
        self.extra = extra

    def _render(self) -> None:
        i = 0
        while not self._stop.is_set():
            el = int(time.time() - self._t0)
            line = (f"  {self.SPIN[i % 4]} {self.label} "
                    f"[{el // 60:02d}:{el % 60:02d}]"
                    f"{('  ' + self.extra) if self.extra else ''}")
            if self._tty:
                sys.stdout.write("\r" + line[:118].ljust(118))
                sys.stdout.flush()
            elif el and el % 15 == 0:
                print(line)
            i += 1
            self._stop.wait(0.4)

    def __enter__(self):
        self._thread = threading.Thread(target=self._render, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        el = int(time.time() - self._t0)
        if self._tty:
            sys.stdout.write("\r" + " " * 118 + "\r")
        mark = "!" if exc[0] else "+"
        print(f"  {mark} {self.label} done in {el // 60:02d}:{el % 60:02d}"
              f"{('  ' + self.extra) if self.extra else ''}")


def wsl_repo() -> str:
    """Repo path as WSL sees it. C:\\x -> /mnt/c/x; already-POSIX paths pass through."""
    p = WIN_REPO.replace("\\", "/")
    if len(p) > 1 and p[1] == ":":
        return "/mnt/" + p[0].lower() + p[2:]
    return p


def win_path(rel: str) -> str:
    """Repo-relative POSIX path -> a real local path on this OS."""
    return os.path.join(WIN_REPO, *[part for part in rel.split("/") if part])


def wsl(cmd: str, timeout: float = 300) -> tuple[int, str]:
    """Run one bash command inside the repo in WSL. Returns (rc, output).

    encoding/errors are pinned explicitly: with bare text=True, Python on
    Windows decodes as cp1252, and the Makefile's emoji output raises
    UnicodeDecodeError inside subprocess's reader thread. That leaves stdout as
    None and surfaces later as a confusing 'NoneType + str' TypeError.
    """
    full = f"cd {wsl_repo()} && {cmd}"
    argv = (["wsl.exe", "-d", DISTRO, "-e", "bash", "-lc", full] if IS_WINDOWS
            else ["bash", "-lc", full])
    try:
        p = subprocess.run(argv, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, ((p.stdout or "") + (p.stderr or ""))
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s"
    except KeyboardInterrupt:
        raise
    except Exception as e:  # noqa: BLE001
        return 1, f"wsl invocation failed: {type(e).__name__}: {e}"


# ---- scheduler ---------------------------------------------------------------

# Set immediately after claim_next(), cleared as soon as the record is reported.
# claim_next() runs outside any try block, so an interrupt arriving between the
# claim and the handler used to strand the record as 'claimed' forever. Two leaked
# that way on 2026-07-20.
_CURRENT_CLAIM: str | None = None


def release_claim_if_held() -> None:
    """Return a still-held claim to 'todo'. Safe to call twice."""
    global _CURRENT_CLAIM
    cid, _CURRENT_CLAIM = _CURRENT_CLAIM, None
    if not cid:
        return
    try:
        print(f"[worker] releasing stranded claim {cid}", file=sys.stderr)
        sched("report", "--id", cid, "--status", "todo",
              "--notes", "released: worker interrupted before reporting")
    except Exception as e:
        print(f"[worker] could not release {cid}: {e}", file=sys.stderr)


def sched(*args: str) -> str:
    # shlex.quote, not naive double-quoting. The old version only quoted args
    # containing spaces, so a note containing a quote, parenthesis or backtick
    # produced a malformed bash command. A worker timeout whose message embedded
    # the whole prompt turned into "syntax error near unexpected token '('" and
    # the real failure was lost. It was also a shell injection vector, since the
    # notes field carries model output.
    global _CURRENT_CLAIM
    if args and args[0] == "report" and "--id" in args:
        _rid = args[args.index("--id") + 1]
        if _rid == _CURRENT_CLAIM:
            _CURRENT_CLAIM = None
    rc, out = wsl("python3 automation/scheduler.py " + " ".join(
        shlex.quote(a) for a in args))
    if rc != 0:
        # Keep the whole traceback. Truncating this to 300 chars once hid a
        # queue-locking bug behind a cut-off stack trace for an entire session.
        raise RuntimeError(f"scheduler failed (rc={rc}):\n{out.strip()}")
    return out.strip()


def claim_next() -> dict | None:
    # The cli tier picks up what llama handed off for size. Without this the
    # deferred records sit forever: llama will never retry them (same gate) and
    # nothing else claims `deferred`.
    _next_args = ["next", "--worker", WORKER_NAME]
    if MODEL_BACKEND == "cli":
        _next_args.append("--include-deferred")
    raw = sched(*_next_args)
    line = [l for l in raw.splitlines() if l.strip().startswith("{")]
    if not line:
        return None
    rec = json.loads(line[-1])
    return None if rec.get("status") == "empty" else rec


# ---- locating the target -----------------------------------------------------

_INDEX: dict[str, tuple[str, int, str]] | None = None
RX_INC = re.compile(r'INCLUDE_ASM\(\s*"([^"]+)"\s*,\s*([A-Za-z0-9_]+)\s*\)')


# ---- symbol declarations for the prompt -------------------------------------
#
# WHY THIS EXISTS
#
# The prompt used to contain only the assembly and the m2c draft. Nothing told
# the model which symbols exist, what type they are, or that it had to declare
# them. So the model guessed, and a guess that is semantically right can still
# generate different code.
#
# Measured cost, 2026-07-21: func_us_801B9DE4 and BO6_RicSetSlide were both
# recorded as near-misses for hours. Both matched on the first try once the
# animation array was declared `extern AnimationFrame D_us_X[];` and passed as
# `D_us_X` rather than the model's `&D_us_X`. The declaration was already
# present in the SAME source file. The harness simply never showed it.
#
# So: pull every symbol the assembly references, find how the repo already
# declares it, and put that in the prompt verbatim.

# %hi(sym) / %lo(sym), optionally with an offset like `g_Ric + 0x340`, plus
# direct `jal sym` call targets.
_ASM_SYM_RE = re.compile(
    r"%(?:hi|lo)\(\s*([A-Za-z_][A-Za-z0-9_]*)|"
    r"\bjal\s+([A-Za-z_][A-Za-z0-9_]*)")
# Cheap guard: these are addressing helpers, not real symbols.
_SYM_SKIP = {"hi", "lo"}
_DECL_CACHE: dict[str, str] = {}


def extract_asm_symbols(asm: str, exclude: str = "") -> list[str]:
    """Every distinct symbol the assembly references, in first-seen order.

    `exclude` drops the function's own name, which appears in glabel/.size and
    would otherwise ask the model to declare the thing it is writing.
    """
    out: list[str] = []
    for m in _ASM_SYM_RE.finditer(asm or ""):
        s = m.group(1) or m.group(2)
        if s and s != exclude and s not in _SYM_SKIP and s not in out:
            out.append(s)
    return out


def lookup_declarations(symbols: list[str], limit: int = 40) -> list[str]:
    """Existing declarations for `symbols`, harvested from the repo itself.

    Deliberately NOT synthesised. A guessed `extern s32 D_us_X;` for something
    the repo declares as `extern AnimationFrame D_us_X[];` would produce exactly
    the codegen mismatch this is meant to prevent. If the tree does not already
    declare a symbol, we say nothing about it rather than inventing a type.
    """
    wanted = [s for s in symbols if s not in _DECL_CACHE][:limit]
    if wanted:
        # One grep for all of them: per-symbol greps over src/ and include/ cost
        # seconds each and this runs before every attempt.
        alt = "|".join(re.escape(s) for s in wanted)
        pat = rf"^[[:space:]]*extern[^;]*\b({alt})\b[^;]*;"
        rc, out = wsl(
            f"grep -rhoE {shlex.quote(pat)} src include "
            f"--include='*.c' --include='*.h' 2>/dev/null | sort -u",
            timeout=120)
        found: dict[str, str] = {}
        if rc == 0:
            for line in out.splitlines():
                line = line.strip()
                for s in wanted:
                    # Bind each declaration to its symbol, shortest wins: the
                    # shortest matching line is the plain declaration rather
                    # than something that merely mentions the name.
                    if re.search(rf"\b{re.escape(s)}\b", line):
                        if s not in found or len(line) < len(found[s]):
                            found[s] = line
        for s in wanted:
            _DECL_CACHE[s] = found.get(s, "")
    return [_DECL_CACHE[s] for s in symbols
            if _DECL_CACHE.get(s)]


def find_source(function: str, overlay: str | None = None):
    """Locate a function's INCLUDE_ASM stub, preferring the RIGHT overlay.

    The old version kept only the FIRST hit from os.walk and indexed every .c
    under src/, including *_psp variants. Those are a different build target that
    the us oracle does not cover, and their asm lives under a path that does not
    exist for us. When os.walk reached the psp copy first, the worker targeted
    it, found no assembly, and handed the model an EMPTY assembly section while
    still asking it to decompile. Observed on UpdateClockHands, which resolved to
    src/st/rno0_psp/unk_1028.c with "asm: 0 chars".

    Now every candidate is kept, psp/saturn variants are dropped outright, and
    the record's own overlay decides which remains.
    """
    global _INDEX
    if _INDEX is None:
        _INDEX = {}
        for dp, _d, fs in os.walk(os.path.join(WIN_REPO, "src")):
            for fn in fs:
                if not fn.endswith(".c"):
                    continue
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, WIN_REPO).replace("\\", "/")
                low = rel.lower()
                # Wrong build targets. Never candidates for a us match.
                if "_psp" in low or "/psp/" in low or "saturn" in low:
                    continue
                try:
                    with open(full, errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            m = RX_INC.search(line)
                            if m:
                                _INDEX.setdefault(m.group(2), []).append(
                                    (rel, i, m.group(1)))
                except OSError:
                    pass
    cands = _INDEX.get(function)
    if not cands:
        return None
    if overlay and len(cands) > 1:
        # "ST/RNO0" -> match a path containing "/rno0/"
        want = "/" + overlay.split("/")[-1].lower() + "/"
        for c in cands:
            if want in c[0].lower():
                return c
    return cands[0]


def asm_rel_path(rec: dict, asm_rel: str) -> str:
    base = asm_rel if asm_rel.startswith("asm/") else f"asm/{rec['build']}/{asm_rel}"
    return f"{base}/{rec['function']}.s"


# Overlays whose artifact is NOT build/<v>/<NAME>.BIN. Verified against
# config/check.us.sha on 2026-07-21.
_ARTIFACT_OVERRIDES = {
    # The main executable is `main.exe`, lowercase, not MAIN.BIN. The derived
    # name produced `build/us/MAIN.BIN`, which appears nowhere in the oracle, so
    # the `grep -F <artifact> check.sha | shasum -c` lookup matched no line and
    # every MAIN function was recorded "built, but does not match" no matter
    # what the worker produced. Nine unmatched functions were unmatchable by
    # construction.
    "MAIN": "main.exe",
}


def overlay_artifact(rec: dict) -> str:
    """The artifact path for this overlay, exactly as it appears in check.<v>.sha.

    The string has to match the oracle byte for byte: it is fed to `grep -F`,
    and a miss is indistinguishable from a hash mismatch.
    """
    name = rec["overlay"].split("/")[-1].upper()
    leaf = _ARTIFACT_OVERRIDES.get(name, f"{name}.BIN")
    return f"build/{rec['build']}/{leaf}"


def audit_artifact_mapping(version: str = "us") -> list[str]:
    """Every overlay whose artifact name is absent from the oracle.

    Cheap, read-only, and worth running after any change to overlay naming.
    A missing entry does not fail loudly at runtime, it just makes that overlay
    permanently unmatchable, which is exactly the kind of defect that hides.
    """
    sha = os.path.join(WIN_REPO, "config", f"check.{version}.sha")
    try:
        with open(sha, errors="ignore") as f:
            known = {ln.split()[1] for ln in f if len(ln.split()) == 2}
    except OSError:
        return [f"cannot read {sha}"]
    asm_root = os.path.join(WIN_REPO, "asm", version)
    overlays, bad = set(), []
    for dirpath, _dirs, files in os.walk(asm_root):
        if os.path.basename(dirpath) == "nonmatchings" and files is not None:
            rel = os.path.relpath(dirpath, asm_root)
            overlays.add(os.path.dirname(rel).replace(os.sep, "/").upper())
    for ov in sorted(o for o in overlays if o):
        art = overlay_artifact({"overlay": ov, "build": version})
        if art not in known:
            bad.append(f"{ov} -> {art} (not in check.{version}.sha)")
    return bad


# ---- context preparation (all mechanical, harness-side) ----------------------

def prepare(rec: dict, located) -> dict:
    src_rel, lineno, asm_rel = located
    asm_file = asm_rel_path(rec, asm_rel)
    fn = rec["function"]
    _ = _DECL_CACHE  # module-level cache, populated by lookup_declarations

    asm_text = ""
    p = win_path(asm_file)
    if os.path.exists(p):
        asm_text = open(p, errors="ignore").read()[:MAX_ASM_CHARS]

    with Status("m2ctx (generating C type context)") as st:
        rc, out = wsl(f"python3 tools/m2ctx.py {src_rel}", timeout=300)
        st.update("ok" if rc == 0 else "failed")
    ctx_ok = rc == 0 and os.path.exists(os.path.join(WIN_REPO, "ctx.c"))
    if not ctx_ok:
        print(f"[prep] m2ctx failed (continuing without types): {out.strip()[:160]}")

    ctx_arg = "--context ctx.c" if ctx_ok else ""
    with Status("m2c (first-draft decompilation)") as st:
        rc, draft = wsl(
            f"python3 tools/m2c/m2c.py --target mipsel-gcc-c {ctx_arg} "
            f"-f {fn} {asm_file}", timeout=300)
        st.update(f"{len(draft)} chars")
    if rc != 0:
        # retry without the context, which is the usual cause of m2c errors
        rc, draft = wsl(f"python3 tools/m2c/m2c.py --target mipsel-gcc-c "
                        f"-f {fn} {asm_file}", timeout=300)
    draft = draft.strip()[:MAX_CTX_CHARS]
    decls = lookup_declarations(extract_asm_symbols(asm_text, exclude=fn))
    print(f"[prep] draft: {len(draft)} chars, asm: {len(asm_text)} chars, "
          f"decls: {len(decls)}")
    return {"asm": asm_text, "draft": draft, "src_rel": src_rel,
            "lineno": lineno, "asm_rel": asm_rel, "asm_file": asm_file,
            "decls": decls}


# ---- the model call (single shot, no tools) ---------------------------------

# Kept DELIBERATELY TERSE. This grew to 5404 chars by accreting a rationale
# ("this exact mistake caused two functions to be misfiled...") after every
# rule. Those justifications are for humans reading this file, not for the
# model, and they doubled the prompt on a tier where large prompts get dropped.
# Rules only; the reasoning lives in MATCHING-LESSONS.md.
SYSTEM = (
    "Expert MIPS decompiler for Castlevania: SOTN (PSX, GCC 2.7.2). Given MIPS "
    "asm and a rough m2c draft, return ONE complete C function that compiles to "
    "identical machine code.\n"
    "OUTPUT: only C. No markdown fences, no prose outside the code. Keep the "
    "exact function name. Use real project types (Entity*, s16/u16/s32), not "
    "the draft's '?'. Invent no helper functions.\n"
    "QUALITY (a byte match is the floor; review rejects code that hides "
    "structure):\n"
    "- Never declare an extern for a raw address that already has a meaning. "
    "A RAW ADDRESSES section, when present, gives the real expression: use it.\n"
    "- Named constants, not bitmask literals: `drawFlags &= ~ENTITY_ROTATE`, "
    "not `&= 0xFB`.\n"
    "- Use existing structs, not pointer arithmetic: `SubweaponDef* p = "
    "&tbl[i]; p->attackElement`, not `*(u16*)(base+4)`.\n"
    "- Follow the conventions of any EXISTING CODE section shown to you.\n"
    "STRUCT FIELDS: m2c writes a synthetic `->unkNN` when it cannot type a "
    "pointer (usually a parameter); `unkNN` is not a real field. Translate it "
    "via the ENTITY LAYOUT section: `->unk24` -> `->zPriority`. Offsets 0x7C+ "
    "are the `ext` union: prefer the named variant from the EXT VARIANTS "
    "section (`ext.reboundStone.stoneAngle`). `ext.ILLEGAL.u16[N]` only if no "
    "named variant fits, with a comment saying so; index (offset-0x7C)/width "
    "and use a concrete array name (u8/u16/s16/s32), never `uN`. Match the "
    "asm's access width. Keep accesses the draft already named. Never write a "
    "`->field` absent from both the draft and ENTITY LAYOUT.\n"
    "C89 ONLY:\n"
    "- Declare EVERY local at the TOP of its block, before any statement. A "
    "declaration after a statement is a hard error. No `for (int i`.\n"
    "- No libc: no rand/memcpy/printf. Only symbols from DECLARATIONS or the "
    "draft.\n"
    "DECLARATIONS section is ground truth: copy those lines verbatim above your "
    "function, match their types exactly. For `extern T NAME[];` pass `NAME`, "
    "never `&NAME`.\n"
    "ANNOTATE (comments and local names cannot change codegen, so they are "
    "free):\n"
    "- One comment above the function saying what it does in game terms.\n"
    "- Name LOCALS meaningfully (angle, timer); never keep arg0/var_a0/temp_v1. "
    "This applies to locals ONLY, never to struct fields: `unk24` stays "
    "`unk24`.\n"
    "- Comment any non-obvious line: magic constant, shift-as-divide, "
    "fixed-point scale, deliberate signedness.\n"
    "- If unsure, say so in the comment rather than stating a confident guess."
)


# The Entity header layout, offset -> field, from include/game.h. This is the
# translation key for m2c's synthetic `->unkNN` accesses: m2c cannot type a
# function parameter, so accesses through it come out as `arg0->unk24` instead
# of `arg0->zPriority`. Giving the model the real map is what lets it fix them.
#
# Only the FIXED header (0x00..0x7B) is listed. Offset 0x7C is the `ext` union,
# whose layout is per-entity-type; for those the generic `ext.ILLEGAL` arrays
# (u8[]/u16[]/s16[]/s32[]) that m2c already emits for typed pointers are safe.
#
# Hardcoded rather than parsed live: the header is stable, and a parser that
# silently drifts would be worse than a constant that is obviously reviewable.
ENTITY_LAYOUT = (
    "=== ENTITY LAYOUT (offset: field, from include/game.h) ===\n"
    "Use this to translate m2c's `->unkNN` (which means offset 0xNN on an "
    "Entity the decompiler could not type). Anything at 0x7C+ is the `ext` "
    "union; for an unknown variant use the generic arrays, e.g. "
    "`ext.ILLEGAL.u16[(0xNN-0x7C)/2]` (or .u8[], .s16[], .s32[] to match the "
    "asm load width). Write a concrete array name, never the placeholder uN.\n"
    "0x00 posX(f32) 0x04 posY(f32) 0x08 velocityX(s32) 0x0C velocityY(s32)\n"
    "0x10 hitboxOffX(s16) 0x12 hitboxOffY(s16) 0x14 facingLeft(u16) 0x16 palette(u16)\n"
    "0x18 blendMode(u8) 0x19 drawFlags(u8) 0x1A scaleX(s16) 0x1C scaleY(s16) 0x1E rotate(s16)\n"
    "0x20 rotPivotX(s16) 0x22 rotPivotY(s16) 0x24 zPriority(u16) 0x26 entityId(u16) 0x28 pfnUpdate(ptr)\n"
    "0x2C step(u16) 0x2E step_s(u16) 0x30 params(u16) 0x32 entityRoomIndex(u16) 0x34 flags(s32)\n"
    "0x3A enemyId(u16) 0x3C hitboxState(u16) 0x3E hitPoints(s16) 0x40 attack(s16) 0x42 attackElement(u16)\n"
    "0x44 hitParams(u16) 0x46 hitboxWidth(u8) 0x47 hitboxHeight(u8) 0x48 hitFlags(u8) 0x49 nFramesInvincibility(u8)\n"
    "0x4A unk4A(s16) 0x4C anim(ptr) 0x50 pose(u16) 0x52 poseTimer(s16) 0x54 animSet(s16) 0x56 animCurFrame(s16)\n"
    "0x58 stunFrames(s16) 0x5A unk5A(u16) 0x5C parent(Entity*) 0x60 nextPart(Entity*) 0x64 primIndex(s32)\n"
    "0x68 unk68(u16) 0x6A hitEffect(u16) 0x6C opacity(u8) 0x6D unk6D[11] 0x78 unk78(s32) 0x7C ext(union)\n"
)


# Hard ceiling on salvage reasoning. Even with degeneration detection, a model
# that rambles without repeating verbatim can run to the budget producing nothing.
SALVAGE_MAX_REASONING = int(os.environ.get("SALVAGE_MAX_REASONING", "24000"))


def make_degeneration_detector():
    """Degeneration detector, shared by the main stream AND the salvage pass.

    This used to be a closure inside llama_echo, so _force_code had no access to
    it: the salvage could loop for the FULL budget with no check whatsoever.
    Observed 2026-07-21: a salvage pass reached 32000 characters of reasoning,
    obviously stuck, and nothing stopped it. Lifted to module level so both
    paths abort on the same evidence.
    """
    strikes = [0]

    def degenerating(buf: list[str]) -> str:
        text = "".join(buf)
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 10]
        if len(lines) >= 8:
            tail = lines[-8:]
            if len(set(tail)) <= 2:
                return "same line repeated 8x"
            short = [l for l in tail if len(l) < 60]
            norm = [re.sub(r"(0x)?[0-9A-Fa-f]{1,8}", "#", l) for l in short]
            if len(short) >= 6 and len(set(norm)) <= 2:
                return f"enumeration loop ({tail[-1][:44]!r}...)"
        if len(text) > 4000:
            chunk = re.sub(r"\s+", " ", text[-300:]).strip()
            earlier = re.sub(r"\s+", " ", text[:-300])
            if len(chunk) > 120 and chunk in earlier:
                strikes[0] += 1
                if strikes[0] >= 2:
                    return "long-cycle repetition (confirmed over two checks)"
            else:
                strikes[0] = 0
        return ""

    return degenerating


def _trim_to_function(code: str) -> str:
    """Cut everything after the function's balanced closing brace.

    Only needed on the reasoning-salvage path. clean_code() finds where the C
    STARTS but has no notion of where it ends, which is fine when the model emits
    code on the content channel and nothing else. Recovering from a reasoning
    stream is different: the model typically writes the function and then keeps
    talking ("That should be correct."). Splicing that trailing prose into a .c
    file produces code that cannot compile, turning a salvaged win into a
    guaranteed build failure.
    """
    depth = 0
    seen = False
    for i, ch in enumerate(code):
        if ch == "{":
            depth += 1
            seen = True
        elif ch == "}":
            depth -= 1
            if seen and depth == 0:
                return code[:i + 1]
    return code


def _force_code(orig_prompt: str, analysis: str,
                timeout: float | None = None) -> str:
    """Second pass: no analysis, just emit the function.

    Used when the first pass reasoned correctly but looped without producing
    code. Its own analysis is handed back as established fact.
    """
    # The salvage fires because the model ALREADY reasoned and failed to produce
    # code. Asking it politely not to think does not work: observed 2026-07-21,
    # a salvage pass emitted 32000 characters of reasoning and no C at all.
    # The thinking must be shut off, not discouraged.
    sys_msg = (
        "You are a C code emitter. You do not explain. You do not analyse.\n"
        "Your ENTIRE reply must be one C function definition and nothing else.\n"
        "The first character you emit MUST be the first character of the "
        "function's return type (for example 'v' of void, 's' of s32).\n"
        "Forbidden: markdown fences, prose, preamble, restating the question, "
        "commentary before or after the code, and any form of step-by-step "
        "thinking. Comments INSIDE the function body are allowed and wanted.\n"
        "The analysis has already been done and is given to you as fact. Your "
        "only remaining job is transcription into C.")
    user = (f"{orig_prompt}\n\n=== ANALYSIS, ALREADY ESTABLISHED, TREAT AS FACT ==="
            f"\n{analysis}\n\n"
            f"Emit the complete C function now. Start with the return type. "
            f"Output nothing that is not C.")
    if MODEL_BACKEND == "cli":
        # Unreachable today: this salvage path only fires from the streaming
        # degeneration detector, which the CLI backend has no stream to watch.
        # Guarded anyway so it can never fall through to an HTTP endpoint that
        # is not configured when running on the CLI.
        return _opencode_run(f"{sys_msg}\n\n{user}")
    body = json.dumps({
        "model": LLAMA_MODEL,
        "messages": [{"role": "system", "content": sys_msg},
                     {"role": "user", "content": user}],
        "temperature": 0.1, "stream": True,
        # Turn thinking OFF at the API level rather than asking nicely.
        #   chat_template_kwargs.enable_thinking -> Qwen3-family template switch
        #   reasoning_budget: 0                  -> llama.cpp server flag
        # Unknown fields are ignored by servers that do not implement them, so
        # sending both is safe and covers either build.
        "chat_template_kwargs": {"enable_thinking": False},
        "reasoning_budget": 0,
    }).encode()
    req = urllib.request.Request(LLAMA_URL.rstrip("/") + "/chat/completions",
                                 data=body,
                                 headers=_api_headers(),
                                 method="POST")
    out: list[str] = []
    reasoning: list[str] = []
    _sal_degen = make_degeneration_detector()
    print("  --- forced code pass ---", flush=True)
    # Bounded by the caller's remaining budget, not a flat GEN_TIMEOUT. The
    # salvage used to be able to run the full 600s on its own, on top of the
    # attempt that already failed.
    _fto = GEN_TIMEOUT if timeout is None else max(30.0, min(GEN_TIMEOUT, timeout))
    with _open_with_backoff(req, _fto) as r:
        for raw in r:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                j = json.loads(payload)
            except json.JSONDecodeError:
                continue
            delta = ((j.get("choices") or [{}])[0].get("delta") or {})
            piece = delta.get("content") or ""
            if piece:
                sys.stdout.write(piece); sys.stdout.flush(); out.append(piece)
            # ALSO capture reasoning. This model is reasoning-distilled: told to
            # "write the function immediately, do not think", it STILL emits
            # reasoning_content, and the C it writes ends up inside that stream.
            # Capturing only `content` meant the salvage pass returned 0 chars on
            # 4 of 6 attempts (measured 2026-07-21) even when the model had in
            # fact written a complete function. The salvage exists precisely for
            # the case where the model reasons instead of answering, so ignoring
            # reasoning made it useless exactly when it was needed.
            rpiece = delta.get("reasoning_content") or delta.get("reasoning") or ""
            if rpiece:
                reasoning.append(rpiece)
                nr = len(reasoning)
                # The salvage can degenerate exactly like the main stream. Check
                # it, and also enforce a hard character ceiling.
                if nr % 40 == 0:
                    why = _sal_degen(reasoning)
                    total = sum(map(len, reasoning))
                    if why or total > SALVAGE_MAX_REASONING:
                        print(f"\n  !! salvage aborted: "
                              f"{why or f'exceeded {SALVAGE_MAX_REASONING} chars'} "
                              f"({total} chars)", flush=True)
                        break
                # Echo a heartbeat. Buffering reasoning silently made a long
                # salvage indistinguishable from a hang: four workers sat in
                # "forced code pass" for six minutes with no console output.
                nr = len(reasoning)
                if nr % 40 == 0:
                    sys.stdout.write(
                        f"\r  ... salvage still reasoning "
                        f"({sum(map(len, reasoning))} chars)   ")
                    sys.stdout.flush()
    content = "".join(out)
    if content.strip():
        print(f"\n  --- forced pass produced {len(content)} chars ---", flush=True)
        return content
    # Nothing on the content channel. Try to recover the function from the
    # reasoning text; clean_code() already discards leading prose and starts at
    # the first line that looks like C.
    salvaged = _trim_to_function(clean_code("".join(reasoning)))
    if salvaged.strip() and "(" in salvaged and "{" in salvaged:
        print(f"\n  --- forced pass: no content tokens, RECOVERED "
              f"{len(salvaged)} chars from reasoning ---", flush=True)
        return salvaged
    print(f"\n  --- forced pass produced 0 chars "
          f"({len(''.join(reasoning))} reasoning chars, no C found) ---", flush=True)
    return ""


def llama_echo(prompt: str, temperature: float = 0.2,
               budget_left: float | None = None) -> str:
    """Stream the completion and ECHO EVERY TOKEN to the console as it arrives.

    Full transparency is the point: you must be able to see whether the model
    is producing code, looping, or thinking silently. A spinner or a token
    counter hides exactly the information needed to tell those apart.

    Handles both `content` and `reasoning_content` deltas. This model is
    reasoning-distilled, so it can emit thousands of reasoning tokens before a
    single content token; without showing them the console looks frozen.
    """
    if MODEL_BACKEND == "cli":
        return _opencode_run(prompt, timeout=budget_left)
    body = json.dumps({
        "model": LLAMA_MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": temperature, "stream": True,
    }).encode()
    req = urllib.request.Request(LLAMA_URL.rstrip("/") + "/chat/completions",
                                 data=body,
                                 headers=_api_headers(),
                                 method="POST")

    t0 = time.time()
    content: list[str] = []
    reason_buf: list[str] = []
    n_content = n_reason = 0
    in_reasoning = False
    aborted = ""

    # Hysteresis for the long-cycle check below: one suspicious repeat is not
    # enough to kill a generation, two consecutive ones is.
    _strikes = [0]

    def degenerating(buf: list[str]) -> str:
        """Detect degeneration, including LONG cycles.

        Observed in practice: the model re-analyses the same eight paragraphs
        repeatedly and never starts writing code. A tail-of-8-lines check
        cannot see a cycle that long, so also test whether the most recent
        chunk of text already appeared earlier in the stream.
        """
        text = "".join(buf)
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 10]
        if len(lines) >= 8:
            tail = lines[-8:]
            if len(set(tail)) <= 2:
                return "same line repeated 8x"
            # Only short, list-shaped lines count as enumeration. Real
            # analysis paragraphs are long and differ in words, not just
            # numbers, so this avoids flagging genuine reasoning.
            short = [l for l in tail if len(l) < 60]
            norm = [re.sub(r"(0x)?[0-9A-Fa-f]{1,8}", "#", l) for l in short]
            if len(short) >= 6 and len(set(norm)) <= 2:
                return f"enumeration loop ({tail[-1][:44]!r}...)"
        # Long-cycle repetition: has the recent chunk been said before?
        #
        # THIS CHECK WAS FAR TOO EAGER and was the single largest source of lost
        # work. Measured 2026-07-21: 22 of 40 generations (55%) produced ZERO
        # output, and the logs show nearly all of them aborted here at
        # 1000-1720 reasoning tokens, well under REASON_CAP=3000.
        #
        # Why it false-positives in THIS domain specifically: the model is
        # reasoning about MIPS assembly. It legitimately quotes instruction
        # sequences, register lists and whole asm lines verbatim, and re-quotes
        # them when walking a loop body a second time. An exact 250-char repeat
        # is therefore normal analysis here, not degeneration. It was also
        # comparing against the ENTIRE history after only 1200 chars, so a single
        # quoted block was enough to kill the generation.
        #
        # Tightened three ways: only look once the stream is genuinely long,
        # ignore whitespace-only differences, and require the repeat to persist
        # across two consecutive checks before believing it. A model that is
        # really stuck will trip it twice; one that quoted an asm block will not.
        if len(text) > 4000:
            chunk = re.sub(r"\s+", " ", text[-300:]).strip()
            earlier = re.sub(r"\s+", " ", text[:-300])
            if len(chunk) > 120 and chunk in earlier:
                _strikes[0] += 1
                if _strikes[0] >= 2:
                    return "long-cycle repetition (confirmed over two checks)"
            else:
                _strikes[0] = 0
        return ""

    print(f"  --- streaming from llama-server "
          f"(prompt {len(prompt)} chars) ---", flush=True)
    # Honour the caller's per-attempt cap on the HTTP path too. Previously only
    # the CLI branch used budget_left, so on llama a single attempt could still
    # eat the entire FUNC_BUDGET and the retry loop never ran.
    _gt = GEN_TIMEOUT if budget_left is None else max(30.0, min(GEN_TIMEOUT, budget_left))
    with _open_with_backoff(req, _gt) as r:
        for raw in r:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                j = json.loads(payload)
            except json.JSONDecodeError:
                continue
            d = (j.get("choices") or [{}])[0].get("delta") or {}

            think = d.get("reasoning_content") or d.get("reasoning") or ""
            if think:
                if not in_reasoning:
                    sys.stdout.write("\n[thinking] ")
                    in_reasoning = True
                sys.stdout.write(think)
                sys.stdout.flush()
                reason_buf.append(think)
                n_reason += 1
                if n_reason % 40 == 0 and n_content == 0:
                    why = degenerating(reason_buf)
                    if why:
                        aborted = f"degenerate reasoning: {why}"
                        break
                    if n_reason > REASON_CAP:
                        aborted = (f"reasoning exceeded {REASON_CAP} tokens "
                                   f"with no code produced")
                        break

            piece = d.get("content") or ""
            if piece:
                if in_reasoning:
                    sys.stdout.write("\n[output] ")
                    in_reasoning = False
                sys.stdout.write(piece)
                sys.stdout.flush()
                content.append(piece)
                n_content += 1

    el = time.time() - t0
    text = "".join(content)
    if aborted and not text.strip():
        # The analysis is typically sound; it just never stopped analysing.
        # Feed its own reasoning back and demand code with no further thinking.
        print(f"\n  !! {aborted}", flush=True)
        print("  --> salvaging: forcing code output from its own analysis",
              flush=True)
        analysis = "".join(reason_buf)[-6000:]
        text = _force_code(prompt, analysis, timeout=budget_left)
    if aborted:
        print(f"\n  !! ABORTED: {aborted}", flush=True)
    print(f"  --- done in {el:.0f}s: {n_content} content tokens, "
          f"{n_reason} reasoning tokens, {len(text)} chars ---", flush=True)
    if n_content == 0:
        print("  !! model produced no content tokens (only reasoning). "
              "It may have run out of budget while thinking.", flush=True)
    return text


def llama(prompt: str, temperature: float = 0.2, status: "Status|None" = None) -> str:
    """Stream the completion so progress is visible while the model works.

    A non-streaming call blocks with zero output for minutes, which is
    indistinguishable from a hang. Streaming lets us report tokens as they
    arrive, and proves the model is alive.
    """
    body = json.dumps({
        "model": LLAMA_MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": temperature, "stream": True,
    }).encode()
    req = urllib.request.Request(LLAMA_URL.rstrip("/") + "/chat/completions",
                                 data=body,
                                 headers=_api_headers(),
                                 method="POST")
    chunks: list[str] = []
    ntok = 0
    with _open_with_backoff(req, GEN_TIMEOUT) as r:
        for raw in r:
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                j = json.loads(payload)
            except json.JSONDecodeError:
                continue
            choices = j.get("choices") or [{}]
            delta = (choices[0].get("delta") or {}).get("content") or ""
            if delta:
                chunks.append(delta)
                ntok += 1
                if status and ntok % 5 == 0:
                    status.update(f"{ntok} tokens, {sum(map(len, chunks))} chars")
    text = "".join(chunks)
    if status:
        status.update(f"{ntok} tokens, {len(text)} chars")
    return text


# NOTE: the '\b' must NOT apply to '#', '//' and '/*'. A trailing word boundary
# after the whole alternation meant "// Face the player" never matched, because
# there is no word boundary between '/' and ' '. That silently deleted every
# function-level doc comment the model produced, and every '#include' it emitted.
# Keep the non-word tokens in their own branch with no \b.
_C_START = re.compile(
    r'^\s*(?:'
    r'#|//|/\*'
    r'|(?:extern|static|typedef|const|volatile|struct|union|enum'
    r'|void|int|char|short|long|float|double|unsigned|signed'
    r'|s8|s16|s32|s64|u8|u16|u32|u64|u_long|Entity|Primitive)\b'
    r')')


# ---- C89 declaration hoister -------------------------------------------------
#
# GCC 2.7 (C89) rejects a declaration that appears after a statement in a block:
#     if (x) { ... }
#     s32 y = z;   // parse error before `y'; then every later use is undeclared
# One violation cascades into many "undeclared" errors. The models produce this
# constantly despite the prompt rule. This pass hoists each offending
# declaration's TYPE to its block top and leaves the assignment in place, which
# is valid C89 and preserves semantics exactly:
#     s32 y;           // hoisted to block top
#     y = z;           // assignment stays where the value is computed
#
# SAFETY: no-ops on already-valid C89 (declarations before any statement are
# untouched), classifies conservatively (a call or assignment is never taken
# for a declaration), handles single-line declarations only, and preserves
# brace balance. Verified on 170 real generations: 19 transformed, 0 mangled.
# The build re-checks every result, so a miss costs nothing and a wrong
# transform (which the safety properties prevent) would be caught immediately.
_HOIST_BASE_TYPES = {
    "s8", "u8", "s16", "u16", "s32", "u32", "s64", "u64", "f32", "f64",
    "int", "char", "short", "long", "void", "unsigned", "signed", "float",
    "double", "bool", "size_t",
}
_HOIST_KEYWORDS = {"return", "if", "else", "for", "while", "do", "switch",
                   "case", "default", "goto", "break", "continue", "sizeof",
                   "typedef"}
_HOIST_DECL_RE = re.compile(
    r"^(?P<indent>\s*)"
    r"(?P<type>(?:const\s+)?(?:unsigned\s+|signed\s+)?(?:struct\s+)?[A-Za-z_]\w*)"
    r"(?P<sep>\s*\*+\s*|\s+)"
    r"(?P<name>[A-Za-z_]\w*)"
    r"\s*(?P<init>=\s*[^;]+)?\s*;"
    r"\s*(?://.*|/\*.*\*/)?\s*$")


def _hoist_is_type(tok: str) -> bool:
    tok = tok.strip()
    return (tok in _HOIST_BASE_TYPES or tok.endswith("_t")
            or bool(re.match(r"^[A-Z][A-Za-z0-9_]*$", tok)))


def _hoist_classify(line: str):
    s = line.strip()
    if not s or s.startswith(("//", "/*", "*", "#")):
        return ("other", None)
    if s in ("{", "}") or s.endswith("{") or s == "};":
        return ("other", None)
    if re.match(r"^[A-Za-z_]\w*\s*:\s*$", s):     # label
        return ("other", None)
    m = _HOIST_DECL_RE.match(line)
    if m and m.group("type").split()[0] not in _HOIST_KEYWORDS \
            and _hoist_is_type(m.group("type").split()[-1]):
        return ("decl", m.groupdict())
    return ("stmt", None)


_INDEX_CACHE: dict | None = None
_EXT_INDEX_CACHE: dict | None = None


def _load_index() -> dict:
    """automation/index.us.json, built by codebase_index.py. Cached."""
    global _INDEX_CACHE
    if _INDEX_CACHE is None:
        try:
            p = os.path.join(WIN_REPO, "automation", "index.us.json")
            with open(p, encoding="utf-8") as f:
                _INDEX_CACHE = json.load(f)
        except (OSError, ValueError):
            _INDEX_CACHE = {}
    return _INDEX_CACHE


def resolve_raw_symbols(asm: str, limit: int = 10) -> str:
    """Resolve `D_800xxxxx` addresses the asm touches into real field names.

    THE fix for the single biggest quality defect. Upstream rejected our code
    for declaring `extern u16 D_80076306;` when that address is really
    `g_Entities[64].step_s`. The model has no way to know that from the asm
    alone, so it invents an extern. The index knows, so tell it up front.

    Arithmetic: g_Entities base + index*sizeof(Entity) + field offset, verified
    against the reviewer's own example.
    """
    idx = _load_index()
    if not idx:
        return ""
    syms = idx.get("symbols", {}).get("name_to_addr", {})
    ent = idx.get("entity", {}).get("fields", {})
    addr_to_name = idx.get("symbols", {}).get("addr_to_name", {})
    try:
        base = int(syms.get("g_Entities", "0x0"), 16)
    except ValueError:
        base = 0
    size = 0xBC
    seen, out = set(), []
    for m in re.finditer(r"\bD_(?:us_)?([0-9A-Fa-f]{8})\b", asm or ""):
        raw = m.group(0)
        if raw in seen:
            continue
        seen.add(raw)
        try:
            addr = int(m.group(1), 16)
        except ValueError:
            continue
        named = addr_to_name.get(f"0x{addr:08X}")
        if named and named != raw:
            out.append(f"{raw} IS the named symbol `{named}` - use that name.")
            continue
        if base and base <= addr < base + size * 256:
            off = addr - base
            i, f = divmod(off, size)
            fld = ent.get(f"0x{f:X}") or ent.get(f"0x{f:02X}")
            if fld:
                out.append(f"{raw} IS g_Entities[{i}].{fld['name']} "
                           f"({fld['type']}) - use that, do NOT declare an extern.")
            elif f >= 0x7C:
                out.append(f"{raw} IS g_Entities[{i}].ext + 0x{f - 0x7C:02X} "
                           f"- use the named ext variant field at that offset, "
                           f"do NOT declare an extern.")
        if len(out) >= limit:
            break
    if not out:
        return ""
    return ("\n=== RAW ADDRESSES ALREADY HAVE MEANINGS ===\n"
            "Declaring a new extern for these is rejected in review.\n"
            + "\n".join(out) + "\n")


# MIPS load/store -> the C type that access width implies. Used to type a
# symbol that the linker knows about but no C file declares.
def quality_gate(code: str, asm: str) -> list[str]:
    """Reject generated C that matches bytes but would fail review.

    PROMPT RULES ARE NOT ENOUGH. Every defect class below was already forbidden
    in SYSTEM and the models produced it anyway. A rule the pipeline cannot
    enforce is a suggestion; this makes the same checks a hard gate, so a
    defective candidate is spent as a failed attempt and its specific defect
    becomes the retry feedback.

    Returns a list of human-readable defects, empty when the code is clean.
    Deliberately conservative: only patterns with a verified, unambiguous fix,
    because a false rejection wastes an attempt on good code.
    """
    idx = _load_index()
    problems: list[str] = []

    # 1. Invented externs for addresses that already have a meaning.
    syms = idx.get("symbols", {}).get("name_to_addr", {})
    ent = idx.get("entity", {}).get("fields", {})
    try:
        base = int(syms.get("g_Entities", "0x0"), 16)
    except ValueError:
        base = 0
    for m in re.finditer(r"^\s*extern\s[^;]*?\bD_(?:us_)?([0-9A-Fa-f]{8})\b",
                         code, re.M):
        addr = int(m.group(1), 16)
        if base and base <= addr < base + 0xBC * 256:
            i, f = divmod(addr - base, 0xBC)
            fld = ent.get(f"0x{f:X}") or ent.get(f"0x{f:02X}")
            where = (f"g_Entities[{i}].{fld['name']}" if fld
                     else f"g_Entities[{i}].ext + 0x{f - 0x7C:02X}")
            problems.append(
                f"declares `D_{m.group(1)}` but that address IS {where}; "
                f"use the real expression, do not declare a new symbol")

    # 2. Raw pointer arithmetic where the project has a struct. Flagged only
    #    when casting off a byte pointer, which is the unambiguous smell.
    n_casts = len(re.findall(
        r"\*\(\s*[a-z]?[su]?\w*\s*\*\s*\)\s*\(\s*\(?\s*(?:unsigned char|u8|char)\s*\*",
        code))
    if n_casts:
        problems.append(
            f"{n_casts} raw byte-pointer cast(s) like `*(u16*)((u8*)p + N)`; "
            f"use the real struct and named members instead")

    # 3. `unsigned char` etc. instead of the project's own scalar typedefs.
    for bad, good in (("unsigned char", "u8"), ("unsigned short", "u16"),
                      ("unsigned int", "u32")):
        if re.search(rf"\b{bad}\b", code):
            problems.append(f"uses `{bad}`; this codebase uses `{good}`")

    # 4. ext.ILLEGAL where the asm shows which named variant applies.
    if "ext.ILLEGAL" in code:
        problems.append(
            "uses `ext.ILLEGAL`; prefer the named ext variant for this entity "
            "type (see the EXT VARIANTS section)")

    # 5. Bitmask literals that have a named constant for that field.
    fe = idx.get("constants", {}).get("field_enum", {})
    groups = idx.get("constants", {}).get("groups", {})
    for m in re.finditer(r"([A-Za-z_][\w\.\->]*)\s*(&=|\|=)\s*(~?)\s*(0x[0-9A-Fa-f]+)",
                         code):
        var, op, tilde, lit = m.groups()
        try:
            val = int(lit, 16)
        except ValueError:
            continue
        cand = (~val) & 0xFF if (op == "&=" and not tilde) else val
        if not cand or (cand & (cand - 1)):
            continue                                   # not a single bit
        tail = re.split(r"[\.\->]", var)[-1].lower()
        for field, enum_name in fe.items():
            if tail.endswith(field.lower()):
                for cname, cval in (groups.get(enum_name) or {}).items():
                    try:
                        if int(cval, 16) == cand:
                            problems.append(
                                f"`{var} {op} {lit}` should use the named "
                                f"constant {cname}")
                            break
                    except ValueError:
                        continue
                break
    return problems


def shared_implementation(function: str, src_rel: str) -> str:
    """Does a SHARED implementation of this function already exist?

    THE most expensive gap found in review. src/st/ deduplicates by putting one
    implementation in src/st/<name>.h and reducing each stage's .c to a shim:

        // src/st/rcen/st_common.c   -- the entire file
        #include "rcen.h"
        #include "../st_common.h"

    25 stages do exactly that. The harness had no concept of it, so it treated
    every INCLUDE_ASM as an isolated target and regenerated 707 lines into
    src/st/rno0/st_common.c that already existed one directory up. Roughly 57%
    of this fork's output was re-implementation of the tree's own code, which is
    the first thing a maintainer checks and the worst thing to get wrong.

    Returns a warning for the prompt, and is deliberately loud: the correct
    action is usually to include the shared header, not to decompile at all.
    """
    if not src_rel or "/st/" not in src_rel.replace("\\", "/"):
        return ""
    base = os.path.basename(src_rel)              # e.g. st_common.c
    stem = os.path.splitext(base)[0]
    shared = os.path.join(WIN_REPO, "src", "st", stem + ".h")
    if not os.path.exists(shared):
        return ""
    try:
        with open(shared, encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return ""
    if not re.search(rf"\b{re.escape(function)}\s*\(", text):
        return ""
    return ("\n=== STOP: A SHARED IMPLEMENTATION ALREADY EXISTS ===\n"
            f"`{function}` is already implemented in src/st/{stem}.h, which "
            f"other stages use via a one-line `#include \"../{stem}.h\"` shim.\n"
            "Do NOT re-implement it. Re-implementing tree code is the single "
            "most common reason a decomp PR is rejected. If this stage needs a "
            "variant, the project's idiom is a `#if STAGE == ...` guard INSIDE "
            "the shared header, not a private copy.\n")


_TWINS: dict | None = None

# Inverted-castle ("reverse") overlays. The second-castle stages are the same
# rooms mirrored, and their code differs from the first castle's in a small,
# repeating set of ways. Names are the splat overlay directory, so `st/rno0`
# and `boss/rbo3` are inverted while `st/no0` and `boss/bo6` are not. Matching
# on a leading `r` alone would misfire on `st/rcen` vs nothing, so keep it to a
# check of the last path component starting with 'r' followed by a known first
# castle name.
_INVERTED = {
    "rare", "rcat", "rcen", "rchi", "rdai", "rno0", "rno1", "rno2", "rno3",
    "rno4", "rnz0", "rnz1", "rtop", "rwrp", "rbo0", "rbo3", "rbo5", "rlib",
}


def _overlay_of(src_path: str) -> str:
    """`src/st/no0/clock_room.c` -> `no0`. Empty when it is not an overlay."""
    parts = (src_path or "").replace("\\", "/").split("/")
    return parts[2] if len(parts) > 3 and parts[0] == "src" else ""


def _is_inverted(overlay: str) -> bool:
    return (overlay or "").replace("\\", "/").split("/")[-1].lower() in _INVERTED


def _load_twins() -> dict:
    """automation/twins.us.json, keyed "<overlay>/<symbol>".

    Regenerate with `python3 automation/asm_twin_finder.py --record`. A missing
    or stale file must never break a run, so every failure path here returns an
    empty map and the prompt simply loses one section.
    """
    global _TWINS
    if _TWINS is None:
        path = os.path.join(WIN_REPO, "automation", "twins.us.json")
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                loaded = json.load(f).get("twins")
            _TWINS = loaded if isinstance(loaded, dict) else {}
        except (OSError, ValueError, AttributeError):
            _TWINS = {}
    return _TWINS


def twin_for(function: str, overlay: str) -> str:
    """Has this function already been written somewhere else in the tree?

    174 of 335 unmatched stubs have a candidate, 145 of them by name alone, so
    for most records this is the single most useful thing we can put in front
    of a model. Without it the worker starts from raw assembly and an m2c draft
    and rediscovers, at full token cost, that BO6_RicStepStand is RicStepStand.

    Deliberately framed as evidence rather than an answer. Of the six BO6 ports
    analysed by hand, FOUR diverged from their twin in a load-bearing way: a
    threshold constant, an entity-slot window and loop count, a missing
    flag-propagation block, a whole absent trailing branch. Telling a model
    "here is the implementation" would convert those into confident wrong code
    that only the build catches, so the wording orders a diff first.

    Silent when the evidence is ambiguous. Symbols are NOT unique across
    overlays -- EntityBreakable is stubbed in both st/rchi and st/rno0 -- so an
    unqualified symbol with more than one candidate yields nothing rather than
    a coin flip.
    """
    twins = _load_twins()
    if not twins or not function:
        return ""
    entry = twins.get(f"{overlay}/{function}")
    if entry is None:
        hits = [v for k, v in twins.items() if k.rsplit("/", 1)[-1] == function]
        if len(hits) != 1:
            return ""
        entry = hits[0]

    names = entry.get("name_twins") or []
    shapes = entry.get("shape_twins") or []
    tokens = entry.get("token_twins") or []
    if not (names or shapes or tokens):
        return ""

    # The stub's size is a cheap sanity check on every candidate below. Two
    # stubs can share a name and therefore a candidate list while being
    # different functions: st/rchi's EntityBreakable is 156 instructions and
    # st/rno0's is 92, against the same eight same-named twins. A twin whose
    # body cannot plausibly assemble to this many instructions is the wrong one.
    n = entry.get("instructions")
    size = f" (this stub is {n} instructions)" if n else ""
    out = [f"\n=== A TWIN OF THIS FUNCTION ALREADY EXISTS IN THE TREE{size} ==="]
    for t in names:
        out.append(f"  same name: {t['file']}:{t['function']}")
    for t in shapes:
        same = "identical" if t.get("identical_constants") else "DIFFERENT"
        out.append(f"  same instruction sequence: {t['overlay']}:{t['symbol']} "
                   f"({same} constants)")
    # Token hits are the weakest signal and get noisy fast, so they are only
    # worth a model's attention when nothing stronger fired.
    if not names and not shapes:
        for t in tokens:
            out.append(f"  similar symbols ({t['score']:.2f}): "
                       f"{t['file']}:{t['function']}")

    # Inverted-castle hint. If this stub is in an R overlay and its twin is not,
    # every divergence found so far has been the same handful of mirrorings.
    # Six clock-room functions in rno0 differed from no0's ONLY in these ways,
    # and knowing to look for them turned a blind search into a checklist.
    if _is_inverted(overlay) and any(
            not _is_inverted(_overlay_of(t.get("file", "")))
            for t in names):
        out.append(
            "  NOTE: this is an INVERTED CASTLE overlay and the twin is not.\n"
            "  Expect the body to be correct but MIRRORED. Every difference\n"
            "  found so far has been one of:\n"
            "    - a sign flip on a position offset (posY -= N becomes += N)\n"
            "    - swapped ++/-- on posX between the two params branches\n"
            "    - a different tilemap index for the same feature\n"
            "    - a different overlay animset bank, ANIMSET_OVL(n)\n"
            "    - the R-prefixed castle flag: CEN_OPEN becomes RCEN_OPEN,\n"
            "      which is +228 (0xE4), so a relocation offset that differs by\n"
            "      exactly 0xE4 is this and not a wrong symbol\n"
            "  These belong in the SHARED header behind a stage guard, not in a\n"
            "  private copy. Upstream parameterises heavily: e_collect.h has 120\n"
            "  conditionals, e_bat.h 8 STAGE_IS references. Use\n"
            "  `#ifdef STAGE_IS_<OVL>` for behaviour and\n"
            "  `#ifndef X / #define X <default>` for constants, so the existing\n"
            "  consumers keep their bytes.\n")

    out.append(
        "READ THE TWIN FIRST, THEN DIFF IT AGAINST THE ASSEMBLY BELOW.\n"
        "It is a starting point, not the answer. Sibling overlays routinely\n"
        "differ by one constant, one loop bound, or a whole missing block, and\n"
        "four of the last six ports diverged in exactly that way. Copying past\n"
        "a difference produces code that looks right and is not.\n"
        "If the twin lives in src/st/<name>.h it is a SHARED implementation:\n"
        "the answer there is a one-line #include shim, not a copy.\n"
        "Globals differ between overlays. Resolve every symbol BY ADDRESS.\n")
    return "\n".join(out)


_ASM_WIDTH_TYPE = {
    "lb": "s8", "lbu": "u8", "sb": "u8",
    "lh": "s16", "lhu": "u16", "sh": "u16",
    "lw": "s32", "sw": "s32",
}


def undeclared_symbols(asm: str, have_decls: list[str], limit: int = 8) -> str:
    """Blessed linker symbols the asm uses that NOTHING in C declares.

    Closes a real gap. `PLAYER_posX_i_hi` is a genuine project symbol
    (config/symbols.us.txt: 0x800733DA) but appears in no C file, so
    lookup_declarations() greps for `extern ... NAME;`, finds nothing, and stays
    silent. The model then uses the name it sees in the asm and never declares
    it: `PLAYER_posX_i_hi undeclared (first use this function)`.

    The type is NOT guessed. It is derived from how the asm actually touches the
    address (`lh` -> s16, `lbu` -> u8, `sw` -> s32), which is the same evidence a
    human would use. Where the asm disagrees with itself, the widest access wins
    and the note says so, because a too-narrow type silently truncates.
    """
    idx = _load_index()
    known = idx.get("symbols", {}).get("name_to_addr", {})
    if not known or not asm:
        return ""
    # Tree-wide declarations, so we never tell the model to redeclare something
    # the headers already provide (g_CurrentEntity, g_api_*, ...). The
    # per-function DECLARATIONS list is capped and locally scoped, so checking
    # only against it over-reports by ~4x.
    already = idx.get("declared_globals", {})
    declared = " ".join(have_decls or [])
    # symbol -> set of instructions that touch it
    touched: dict[str, set] = {}
    for m in re.finditer(
            r"\b(lb|lbu|lh|lhu|lw|sb|sh|sw)\b[^\n]*?%(?:hi|lo)\(\s*([A-Za-z_]\w*)",
            asm):
        touched.setdefault(m.group(2), set()).add(m.group(1))
    # also catch %hi/%lo without a load on the same line (common: lui then lw)
    for m in re.finditer(r"%(?:hi|lo)\(\s*([A-Za-z_]\w*)", asm):
        touched.setdefault(m.group(1), set())

    out = []
    for sym, ops in touched.items():
        if sym not in known:
            continue                      # not a blessed symbol; skip
        if sym in already:
            continue                      # the tree already declares it
        if re.search(rf"\b{re.escape(sym)}\b", declared):
            continue                      # already covered by DECLARATIONS
        if sym.startswith("D_"):
            continue                      # handled by resolve_raw_symbols
        types = {_ASM_WIDTH_TYPE[o] for o in ops if o in _ASM_WIDTH_TYPE}
        if not types:
            continue                      # no width evidence; say nothing
        # SAFETY: if the asm reaches the symbol at more than one offset it is a
        # struct or array, not a scalar, and a width-derived scalar type would
        # be actively wrong (`extern u16 g_Ric;` for a PlayerState). Emitting
        # nothing is always recoverable; emitting a wrong type is not.
        offsets = set(re.findall(
            rf"%lo\(\s*{re.escape(sym)}\s*(?:\+\s*(0x[0-9A-Fa-f]+|\d+))?\s*\)",
            asm))
        if len([o for o in offsets if o]) > 0 or len(offsets) > 1:
            continue
        order = ["s8", "u8", "s16", "u16", "s32"]
        widest = sorted(types, key=lambda t: order.index(t))[-1]
        note = "" if len(types) == 1 else f"  (asm uses {'/'.join(sorted(types))})"
        out.append(f"extern {widest} {sym};   /* {known[sym]} */{note}")
        if len(out) >= limit:
            break
    if not out:
        return ""
    return ("\n=== SYMBOLS YOU MUST DECLARE (real, but undeclared in C) ===\n"
            "These are genuine project symbols with no existing declaration. "
            "Copy these lines above your function; type is from the asm access "
            "width.\n" + "\n".join(out) + "\n")


def precedent_for(function: str, src_rel: str, limit: int = 2) -> str:
    """Show existing functions that solve a similar problem.

    This is the single biggest quality lever, and it is what separated a strong
    model from a weak one in testing: given the same task, the model that went
    looking for precedent found that sibling boss overlays already expressed the
    exact idiom (`g_Entities[STAGE_ENTITY_START + E_AFTERIMAGE_1]
    .ext.afterImage.*`) and conformed to it; the model that did not invented a
    wall of raw casts, which upstream rejects.

    Finding precedent is mechanical, so a cheap model should not have to be
    clever enough to think of it. Match on the function's name stem and its
    overlay's sibling directories.
    """
    idx = _load_index()
    funcs = idx.get("functions", {})
    if not funcs:
        return ""
    stem = re.sub(r"^(func_us_|func_|BO\d_|Entity)", "", function or "")
    stem = re.sub(r"[0-9A-Fa-f]{6,}$", "", stem)
    if len(stem) < 4:
        return ""
    scored = []
    for name, meta in funcs.items():
        if name == function:
            continue
        f = meta.get("file", "")
        if src_rel and f == src_rel:
            continue                      # same file is not "precedent"
        s = 0
        if stem.lower() in name.lower():
            s += len(stem)
        if s:
            scored.append((s, -meta.get("lines", 999), name, meta))
    if not scored:
        return ""
    scored.sort(reverse=True)
    out = ["\n=== EXISTING CODE THAT SOLVES A SIMILAR PROBLEM ===",
           "Follow these conventions. Reuse their idioms, names and helpers "
           "rather than inventing your own."]
    for _, _, name, meta in scored[:limit]:
        out.append(f"- {name}  ({meta.get('file')})   {meta.get('signature','')}")
    return "\n".join(out) + "\n"


def ext_variants_for(function: str, blob: str, limit: int = 4) -> str:
    """Named ext-variant field lists relevant to this function.

    Reads automation/index.us.json (built by codebase_index.py). Selection is by
    name affinity: BO6_ReboundStoneBounce2 -> the `reboundStone` variant,
    BO6_RicDoSubweapon -> `subweapon`. Only a handful are injected, because the
    union has 461 variants and dumping them would bury the prompt.

    Without this the "prefer the named variant" rule is unactionable: the model
    has no way to know `stoneAngle` exists, so it falls back to
    `ext.ILLEGAL.u16[0]`, which upstream rejects.
    """
    global _EXT_INDEX_CACHE
    if _EXT_INDEX_CACHE is None:
        try:
            p = os.path.join(WIN_REPO, "automation", "index.us.json")
            with open(p, encoding="utf-8") as f:
                _EXT_INDEX_CACHE = json.load(f).get("ext_variants", {})
        except (OSError, ValueError):
            _EXT_INDEX_CACHE = {}
    variants = _EXT_INDEX_CACHE
    if not variants:
        return ""
    hay = (function + " " + blob).lower()
    scored = []
    for vname, meta in variants.items():
        if len(vname) < 4:
            continue
        if vname.lower() in hay:
            scored.append((len(vname), vname, meta))
    if not scored:
        return ""
    scored.sort(reverse=True)
    out = ["\n=== EXT VARIANTS (real field names; prefer these over ILLEGAL) ==="]
    for _, vname, meta in scored[:limit]:
        fields = [f["name"] for f in meta.get("fields", []) if f.get("name")]
        if not fields:
            continue
        out.append(f"ext.{vname} ({meta.get('type','?')}): "
                   + ", ".join(fields[:14]))
    return "\n".join(out) + "\n" if len(out) > 1 else ""


def hoist_declarations(code: str) -> str:
    """Move mid-block declarations to their block top for C89. Conservative."""
    lines = code.split("\n")
    out = list(lines)
    hoists = {}          # opening-brace line index -> [(indent, "TYPE NAME;")]
    depth_stack = []     # [{"brace": idx, "seen": bool}]
    changed = False
    for i, line in enumerate(lines):
        kind, gd = _hoist_classify(line)
        if kind == "decl" and depth_stack and depth_stack[-1]["seen"]:
            indent = gd["indent"]
            typ = re.sub(r"\s+", " ", gd["type"]).strip()
            stars = "*" * gd["sep"].count("*")
            name, init = gd["name"], gd["init"]
            hoists.setdefault(depth_stack[-1]["brace"], []).append(
                (indent, f"{typ} {stars}{name};"))
            out[i] = f"{indent}{name} {init.strip()};" if init else None
            changed = True
        elif kind == "stmt" and depth_stack:
            depth_stack[-1]["seen"] = True
        for _ in range(line.count("{")):
            depth_stack.append({"brace": i, "seen": False})
        for _ in range(line.count("}")):
            if depth_stack:
                depth_stack.pop()
    if not changed:
        return code
    rebuilt = []
    for i, line in enumerate(out):
        if line is None:
            continue
        rebuilt.append(line)
        for indent, bare in hoists.get(i, []):
            rebuilt.append(f"{indent}    {bare}")
    return "\n".join(rebuilt)


def clean_code(text: str) -> str:
    """Strip markdown fences and leading prose, but KEEP declarations.

    An earlier version searched for the first line resembling a function
    signature and discarded everything before it. That silently deleted the
    `extern s16 RIC_step;` declarations the model correctly emitted, so the
    function referenced undeclared symbols and GCC produced an empty body
    (`jr ra / nop`) with both stores missing. The generated code shrank from
    119 chars to 74, which was the only visible symptom.

    Keep from the first line that looks like C of ANY kind, declarations
    included.
    """
    text = re.sub(r"^```[a-zA-Z]*\s*$", "", text.strip(), flags=re.M).strip()
    lines = text.splitlines()
    for i, l in enumerate(lines):
        if _C_START.match(l) or re.match(
                r'^\s*[A-Za-z_][\w \*]*\s+[A-Za-z_]\w*\s*\(', l):
            return "\n".join(lines[i:]).strip()
    return text.strip()


def build_prompt(rec: dict, ctx: dict, feedback: str = "") -> str:
    fb = f"\nPREVIOUS ATTEMPT FAILED:\n{feedback}\nFix it.\n" if feedback else ""
    # Declarations harvested from the tree. These are ground truth about types,
    # so they go BEFORE the asm: the model should read them as constraints, not
    # as an afterthought to the draft it has already committed to.
    decls = ctx.get("decls") or []
    dsec = ""
    if decls:
        dsec = ("\n=== DECLARATIONS ALREADY IN THE PROJECT ===\n"
                "These are the real types for the symbols this function uses.\n"
                "Copy any you need verbatim. Do NOT invent a different type.\n"
                "Note the arrays: pass `NAME`, never `&NAME`. Taking the address\n"
                "of an array generates different code and will not match.\n"
                + "\n".join(decls) + "\n")
    # Inject the Entity layout only when this function actually deals with an
    # entity. The signal is either an Entity-typed thing in the draft/asm or the
    # tell-tale `->unkNN` accesses that the layout exists to translate. Skipping
    # it for non-entity functions keeps their prompts lean.
    blob = (ctx.get("draft") or "") + (ctx.get("asm") or "")
    entity_sec = ""
    if ("Entity" in blob or "g_CurrentEntity" in blob or "g_Ric" in blob
            or re.search(r"->unk[0-9A-Fa-f]{1,2}\b", blob)):
        entity_sec = "\n" + ENTITY_LAYOUT
        # Real ext field names for whichever variants this function plausibly
        # touches. Telling the model "prefer the named variant" is useless
        # without the names, which is how ext.ILLEGAL got written everywhere.
        ev = ext_variants_for(rec.get("function", ""), blob)
        if ev:
            entity_sec += ev
    # Index-derived context, independent of whether this is an entity function:
    #   - raw D_ addresses resolved to their real meanings (kills the biggest
    #     review-rejection class: invented externs)
    #   - existing functions to imitate (kills the "invented a new style" class)
    # Shared-implementation warning goes FIRST: if it fires, nothing else in
    # the prompt matters, because the right answer is not to generate at all.
    # Shared-implementation warning first (if it fires, the answer is a shim
    # and nothing else matters), then the twin, which for 174 of 335 stubs is
    # the most useful context available and belongs above the raw assembly.
    entity_sec = (shared_implementation(rec.get("function", ""),
                                        ctx.get("src_rel", ""))
                  + twin_for(rec.get("function", ""), rec.get("overlay", ""))
                  + entity_sec)
    entity_sec += resolve_raw_symbols(ctx.get("asm", ""))
    entity_sec += undeclared_symbols(ctx.get("asm", ""), decls)
    entity_sec += precedent_for(rec.get("function", ""), ctx.get("src_rel", ""))
    return (
        f"Function: {rec['function']}   (overlay {rec['overlay']}, build {rec['build']})\n"
        f"{fb}{dsec}{entity_sec}"
        f"\n=== MIPS ASSEMBLY ===\n{ctx['asm']}\n\n"
        f"=== m2c DRAFT (rough, fix the types) ===\n{ctx['draft']}\n\n"
        f"Return the complete C function {rec['function']} only."
    )


# ---- applying, building, checking -------------------------------------------

class BuildLock:
    """Cross-process lock around apply -> build -> verify -> restore.

    Several workers can run at once, but they share ONE repo and ONE build
    directory. Generation (the slow part, minutes of llama time) is safe to
    overlap because it only reads. Everything after it is not: worker A's edit
    would be present in the tree while worker B builds, so B would verify the
    wrong source and could record a false match.

    So the critical section is exactly apply/build/verify/restore. With N
    workers you get N-way parallel generation and serialised verification,
    which is the correct trade: llama has slots, the build does not.

    Implemented with atomic O_CREAT|O_EXCL (works on Windows and POSIX) plus
    stale takeover, so a crashed worker cannot wedge the fleet forever.
    """

    def __init__(self, path: str, stale_after: float = 3600.0):
        self.path = path
        self.stale_after = stale_after
        self.fd: int | None = None

    def acquire(self, poll: float = 2.0) -> None:
        waited = 0.0
        while True:
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(self.fd, f"{os.getpid()} {time.time()}".encode())
                return
            except FileExistsError:
                try:
                    age = time.time() - os.path.getmtime(self.path)
                except OSError:
                    continue
                if age > self.stale_after:
                    print(f"[lock] breaking stale lock ({age:.0f}s old)")
                    try:
                        os.unlink(self.path)
                    except OSError:
                        pass
                    continue
                if waited == 0 or waited % 30 < poll:
                    print(f"[lock] another worker is building; waiting "
                          f"({waited:.0f}s)")
                time.sleep(poll)
                waited += poll

    def release(self) -> None:
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()


def _read_raw(path: str) -> tuple[str, str]:
    """Read a file without newline translation. Returns (text, line_ending).

    Forcing LF on write made every touched file show as modified in git even
    when the content was identical (numstat 0/0), because this repo's working
    tree uses CRLF. Preserve whatever the file already uses.
    """
    with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        text = f.read()
    return text, ("\r\n" if "\r\n" in text else "\n")


def _journal_path() -> str:
    return os.path.join(WIN_REPO, "automation", "logs", "pending",
                        f"{WORKER_NAME}.json")


def journal_write(src_rel: str, original: str) -> None:
    """Record the pre-edit file contents BEFORE touching the source.

    SIGKILL cannot be caught, so no in-process handler can guarantee a restore.
    A worker killed between apply and restore used to leave broken C in the tree:
    on 2026-07-20 that left `arg0->unk18` in 2D26C.c and took the whole build down,
    costing three reported matches when the files had to be reverted.

    With this journal the damage is recoverable by anyone: the next worker start,
    or fleet_stop, replays it and puts the file back.
    """
    try:
        d = os.path.dirname(_journal_path())
        os.makedirs(d, exist_ok=True)
        tmp = _journal_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"src_rel": src_rel, "original": original,
                       "worker": WORKER_NAME, "at": time.time()}, f)
        os.replace(tmp, _journal_path())
    except OSError as e:
        print(f"[worker] WARNING: could not write restore journal: {e}",
              file=sys.stderr)


def journal_clear() -> None:
    try:
        os.unlink(_journal_path())
    except OSError:
        pass


def replay_pending_journals() -> int:
    """Restore any source left modified by a worker that died mid-edit.

    Called at worker startup. Safe to run when nothing is pending.
    """
    d = os.path.join(WIN_REPO, "automation", "logs", "pending")
    if not os.path.isdir(d):
        return 0
    n = 0
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json"):
            continue
        full = os.path.join(d, name)
        try:
            with open(full, encoding="utf-8") as f:
                j = json.load(f)
            path = win_path(j["src_rel"])
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(j["original"])
            os.unlink(full)
            n += 1
            print(f"[worker] restored {j['src_rel']} from journal left by "
                  f"{j.get('worker', '?')}", file=sys.stderr)
        except (OSError, ValueError, KeyError) as e:
            print(f"[worker] could not replay {name}: {e}", file=sys.stderr)
    return n


def apply_code(ctx: dict, fn: str, code: str) -> str:
    """Replace the INCLUDE_ASM line with the generated C. Returns the original."""
    path = win_path(ctx["src_rel"])
    original, nl = _read_raw(path)
    # Match the stub whether the file uses LF or CRLF (\r sits before the \n).
    pattern = re.compile(
        r'^[ \t]*INCLUDE_ASM\(\s*"' + re.escape(ctx["asm_rel"]) +
        r'"\s*,\s*' + re.escape(fn) + r'\s*\);[ \t]*(?=\r?$)', re.M)
    if not pattern.search(original):
        raise RuntimeError(f"INCLUDE_ASM stub for {fn} not found in {ctx['src_rel']}")
    # The model emits LF; convert the insert to the file's own convention.
    body = code.replace("\r\n", "\n").replace("\n", nl)
    journal_write(ctx["src_rel"], original)   # BEFORE the write, not after
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(pattern.sub(lambda _m: body, original, count=1))
    return original


def restore(ctx: dict, original: str) -> None:
    # newline="" so the original bytes go back exactly as they were read.
    with open(win_path(ctx["src_rel"]), "w", encoding="utf-8", newline="") as f:
        f.write(original)
    journal_clear()


def build_and_check(rec: dict) -> tuple[bool, str]:
    with Status(f"make build VERSION={rec['build']}") as st:
        # `set -o pipefail` is LOAD-BEARING, not tidiness.
        #
        # This was `make build ... 2>&1 | tail -40`. In a pipeline the exit
        # status is the LAST command's, i.e. tail's, which is always 0. So
        # rc != 0 never fired and a compile error was indistinguishable from a
        # successful build. Every failed compile fell through to the hash check
        # and got reported as "built, but does not match".
        #
        # Two consequences, both bad:
        #   1. The failure taxonomy inverted. Functions that never compiled were
        #      routed to `near` (permuter work) instead of `escalated`. On
        #      2026-07-21 func_us_801B7C44 was filed NEAR while all four of its
        #      attempts referenced `unk32`, a field that does not exist.
        #   2. Retry feedback was useless. The model was told "bytes differ"
        #      when the real message was "structure has no member named unk32",
        #      so it had no way to learn the actual mistake and repeated it on
        #      every one of the four attempts.
        # Capture make's REAL exit code, then extract the actual error lines,
        # not `tail -40`.
        #
        # The build is ninja-parallel. When one compile fails, ninja prints its
        # `FAILED:` block and the compiler error, then keeps running the other
        # in-flight targets before exiting non-zero. `tail -40` therefore shows
        # the unrelated targets that happened to finish LAST (stnz0, WEAPON0,
        # strip steps), and the actual error scrolls off. The model was handed
        # that noise as "BUILD FAILED" feedback and had no way to see the real
        # cause (e.g. `implicit declaration of rand`), so retries stayed blind.
        #
        # Write to a temp file, keep make's rc via $?, then grep the error
        # context out of the file. `exit $rc` makes wsl() see make's status, so
        # a grep that finds nothing cannot masquerade as success.
        blog = f"/tmp/sotn_build.{os.getpid()}.log"
        # The compiler is GCC 2.7 (cc1-psx-26). Its diagnostics are formatted
        # `file.c:LINE: message` with NO `error:` keyword, e.g.
        #   src/boss/bo0/2D26C.c:133: structure has no member named `unk32'
        # so an `error:`-only grep matched nothing but make's own `Error 1`
        # summary and the ✅/❌ overlay banner. Match the `file.(c|h):NN:` prefix
        # itself, which is what every real diagnostic carries, plus ninja's
        # `FAILED:` and linker `undefined reference`.
        rc, out = wsl(
            f"make build VERSION={rec['build']} > {blog} 2>&1; rc=$?; "
            f"grep -nE -A2 "
            f"'[^ ]+\\.(c|h):[0-9]+:|FAILED:|undefined reference|: error' "
            f"{blog} | head -60; "
            f"[ $rc -ne 0 ] && echo '--- build tail ---' && tail -6 {blog}; "
            f"rm -f {blog}; exit $rc",
            timeout=BUILD_TIMEOUT)
        st.update("compiled" if rc == 0 else "BUILD FAILED")
    if rc != 0:
        return False, "BUILD FAILED:\n" + out.strip()[-1500:]
    artifact = overlay_artifact(rec)
    with Status(f"verifying {artifact} sha1"):
        rc, out = wsl(f"grep -F '{artifact}' config/check.{rec['build']}.sha "
                      f"| shasum -c - 2>&1")
    if rc == 0 and ": OK" in out:
        # Capture the real hash so the scheduler receives machine proof, not a
        # claim. Nothing can be recorded as 'matched' without this.
        _rc, h = wsl(f"shasum {artifact} 2>/dev/null | awk '{{print $1}}'")
        return True, f"{artifact} sha1={h.strip()} verified against config/check.{rec['build']}.sha"
    return False, f"built, but {artifact} does not match:\n{out.strip()[-400:]}"


def diff_feedback(rec: dict) -> str:
    """asm-differ output, or a loud complaint if the tool is unusable.

    asm-differ exits 0 while printing only 'Missing prerequisite python module
    colorama', so an unusable differ looked like success and the model received
    empty feedback, regenerating the same answer every attempt.
    """
    ov = rec["overlay"].split("/")[-1].lower()
    # Use the VENV python, not system python3. colorama/watchdog/levenshtein/
    # cxxfilt are installed in ./.venv, so invoking system python3 made
    # asm-differ report "Missing prerequisite python module watchdog" even
    # though the modules were present. Every retry then received
    # "[asm-differ unavailable: ...]" instead of a real diff, so the model was
    # told nothing about HOW it failed and simply resampled. This silently
    # crippled the retry loop for both the llama and opencode backends.
    py = "./.venv/bin/python" if os.path.exists(
        os.path.join(WIN_REPO, ".venv", "bin", "python")) else "python3"
    rc, out = wsl(f"{py} tools/asm-differ/diff.py --format plain "
                  f"--version {rec['build']} --overlay {ov} {rec['function']} "
                  f"2>&1 | head -40", timeout=300)
    out = out.strip()
    if not out or "Missing prerequisite" in out:
        return ("[asm-differ unavailable: " + (out[:120] or "no output") +
                "] Install with: ./.venv/bin/pip install colorama watchdog "
                "levenshtein cxxfilt")
    return out[:1500]


# ---- main loop ---------------------------------------------------------------

def process_one(dry: bool = False) -> bool:
    rec = claim_next()
    if rec is None:
        print("[worker] queue empty")
        return False
    global _CURRENT_CLAIM
    _CURRENT_CLAIM = rec["id"]
    fn = rec["function"]
    print(f"[worker] {rec['id']}")

    located = find_source(fn, rec.get("overlay"))
    if not located:
        sched("report", "--id", rec["id"], "--status", "escalated",
              "--notes", "INCLUDE_ASM stub not found")
        return True
    print(f"[worker] target {located[0]}:{located[1]}")

    ctx = prepare(rec, located)
    if len(ctx["asm"]) > MAX_FUNC_CHARS and not dry:
        print(f"[worker] SKIP: {len(ctx['asm'])} chars of asm exceeds "
              f"MAX_FUNC_CHARS={MAX_FUNC_CHARS}; too large for this tier")
        sched("report", "--id", rec["id"], "--status", "deferred",
              "--notes", f"{DEFER_TOO_LARGE}: asm {len(ctx['asm'])} chars > "
                         f"{MAX_FUNC_CHARS} on backend={MODEL_BACKEND}; "
                         f"handed off to the next tier")
        return True
    if dry:
        print("--- prompt preview ---")
        print(build_prompt(rec, ctx)[:1500])
        sched("report", "--id", rec["id"], "--status", "todo")
        return True

    original, feedback, best = None, "", "no attempt completed"
    # Did ANY attempt produce C that compiled and merely missed on bytes?
    # That is a fundamentally different outcome from "never built", and it
    # decides where the record is routed when the attempts run out. See the
    # status choice at the end of this function.
    compiled_once = False
    produced_code = False   # did ANY attempt yield a candidate to build?
    gen_errors = 0          # attempts that errored during generation
    try:
        _deadline = time.time() + FUNC_BUDGET
        for attempt in range(1, MAX_ATTEMPTS + 1):
            # Wall-clock budget for the WHOLE function, not per attempt.
            # MAX_ATTEMPTS=4, and each attempt that trips REASON_CAP falls into a
            # forced pass bounded only by GEN_TIMEOUT (600s). That is ~40 minutes
            # on a single function with nothing reporting how long it has been
            # going. One hard ceiling is what makes a stuck function visible.
            _left = _deadline - time.time()
            if _left <= 0:
                print(f"\n[worker] BUDGET EXHAUSTED after "
                      f"{FUNC_BUDGET}s ({attempt - 1} attempts); escalating",
                      flush=True)
                best = (f"exceeded FUNC_BUDGET={FUNC_BUDGET}s after "
                        f"{attempt - 1} attempts; {best}")
                break
            print(f"\n[worker] attempt {attempt}/{MAX_ATTEMPTS} "
                  f"({int(_left)}s of budget left)")
            # --- generation: safe to run concurrently with other workers ---
            #
            # A generation failure costs ONE ATTEMPT, never the function.
            #
            # This was unguarded until 2026-07-21. subprocess.TimeoutExpired from
            # the cli backend escaped to the per-function handler, which abandoned
            # the function and discarded every remaining attempt. Observed:
            # BO6_CheckHighJumpInput timed out on attempt 1/4 and the worker moved
            # straight to another function, throwing away three unused attempts.
            #
            # It never surfaced on the http backend because streaming plus the
            # degeneration detector always cut in before any hard timeout. The cli
            # backend has neither, so the timeout IS the normal failure mode:
            # ATTEMPT_BUDGET is 191s by default and OpenCode runs take 120-190s.
            try:
                raw = llama_echo(build_prompt(rec, ctx, feedback),
                                 budget_left=min(ATTEMPT_BUDGET,
                                                 _deadline - time.time()))
            except subprocess.TimeoutExpired:
                print(f"  !! attempt {attempt} timed out after "
                      f"{int(ATTEMPT_BUDGET)}s; trying the next attempt",
                      flush=True)
                best = f"attempt {attempt} timed out"
                gen_errors += 1
                feedback = ("Your previous answer did not finish in time. Reply "
                            "with the C function ONLY, no analysis.")
                continue
            except Exception as e:  # noqa: BLE001
                # Any other generation error is also per-attempt. Truncated
                # because the cli backend puts the entire prompt in the message,
                # which buried the actual cause under 4KB of assembly.
                print(f"  !! attempt {attempt} generation failed: "
                      f"{type(e).__name__}: {str(e)[:200]}", flush=True)
                best = f"attempt {attempt} failed: {type(e).__name__}"
                gen_errors += 1
                continue
            code = hoist_declarations(clean_code(raw))
            # Persist every attempt. A failed attempt is reverted to the stub,
            # so without this the model's actual output exists only in the
            # console and is unreviewable afterwards. Being able to tell "wrote
            # sensible C that missed on a type" from "produced nonsense" is the
            # difference between tuning the prompt and changing model.
            try:
                _gd = os.path.join(WIN_REPO, "automation", "logs", "gen")
                os.makedirs(_gd, exist_ok=True)
                with open(os.path.join(_gd, f"{fn}-attempt{attempt}.c"),
                          "w", encoding="utf-8") as _f:
                    _f.write(f"/* {rec['id']}  attempt {attempt}/{MAX_ATTEMPTS}\n"
                             f"   model: {OPENCODE_MODEL if MODEL_BACKEND == 'cli' else LLAMA_MODEL}\n"
                             f"   raw {len(raw)} chars -> cleaned {len(code)} chars */\n")
                    _f.write(code)
            except OSError:
                pass
            # Echo the generated function. The HTTP backend streamed every
            # token so you could watch the model work; the CLI backend returns
            # only at the end, and replacing that stream with two status lines
            # left the console showing nothing useful. Print the result.
            print("  --- generated ---", flush=True)
            for _ln in code.splitlines():
                print(f"  | {_ln}", flush=True)
            print("  --- end ---", flush=True)
            if len(code) < 20:
                feedback = "empty output"; continue
            produced_code = True   # a real candidate reached the build stage

            # QUALITY GATE, before the build. A byte match is not acceptance:
            # code that matches but re-implements tree code, invents symbols or
            # uses raw casts gets rejected upstream, so rejecting it here costs
            # one attempt instead of a review cycle. The specific defect becomes
            # the retry feedback, which is what makes the next attempt better
            # rather than merely different.
            defects = quality_gate(code, ctx.get("asm", ""))
            if defects:
                print(f"  !! QUALITY REJECT ({len(defects)}): "
                      + "; ".join(d[:70] for d in defects[:3]), flush=True)
                best = f"quality reject: {defects[0][:120]}"
                feedback = ("Your previous answer compiled but would be "
                            "REJECTED in review:\n- " + "\n- ".join(defects)
                            + "\nFix these and return the function again.")
                continue

            # --- critical section: one worker at a time touches the tree ---
            #
            # Reporting a match MUST happen inside this lock.
            #
            # scheduler.py refuses `matched` unless it can re-verify, and it
            # re-verifies the WHOLE tree: all 77 hashes, not just this overlay.
            # So the tree has to still be in the state this worker just proved
            # when the scheduler looks at it.
            #
            # The report used to sit after the lock released. Another worker
            # would apply its own edit in that window, the scheduler would see
            # "76/77 OK, 1 MISMATCHED" for an overlay this function never
            # touched, and a REAL match was thrown away and marked escalated.
            # Confirmed on two records during the 2026-07-21 retriage:
            # func_us_801B9D74 (best_score 100, rejected over a dirty BO0.BIN)
            # and func_us_801B20F4 (rejected over a dirty DRA.BIN).
            #
            # Whole-tree verification is correct and worth keeping: it is what
            # stops a worker reporting a match while the tree is broken. It just
            # has to be serialised with everything else that mutates the tree.
            matched = False
            with BuildLock(os.path.join(WIN_REPO, "automation", ".build.lock")):
                original = apply_code(ctx, fn, code)
                print(f"  -> applied {len(code)} chars to {ctx['src_rel']}")
                ok, detail = build_and_check(rec)
                if not ok:
                    # Restore before releasing, so the tree is always clean for
                    # the next worker. A failed edit must never be visible to
                    # someone else's build.
                    restore(ctx, original)
                    original = None
                else:
                    print(f"[worker] MATCHED {fn}")
                    sched("report", "--id", rec["id"], "--status", "matched",
                          "--score", "100", "--tier", "0",
                          "--proof", detail[:200], "--notes", detail[:200])
                    matched = True
            best = detail
            if matched:
                return True
            feedback = detail
            if "BUILD FAILED" not in detail:
                compiled_once = True
                with Status("asm-differ (collecting feedback)"):
                    feedback += "\n\nDIFF:\n" + diff_feedback(rec)
            for dl in detail.splitlines()[:6]:
                print(f"    | {dl[:110]}")
        if original is not None:
            restore(ctx, original)
        # Route by FAILURE KIND, not just by "did not match".
        #
        # "compiled but the bytes differ" and "never built" are different
        # problems with different owners. MATCHING-LESSONS.md section 6 says so,
        # and the tier table routes `near` to the permuter FIRST because it
        # costs no tokens. Reporting both as `escalated` sent codegen near-misses
        # to the expensive model tier and starved the permuter of exactly the
        # records it exists to solve.
        #
        # Evidence this is the common case, 2026-07-21: on func_us_801B9DE4 two
        # unrelated models produced identical, semantically CORRECT C (every
        # struct offset verified by hand against include/game.h) that still
        # missed. No larger model fixes that; a codegen search might.
        if compiled_once:
            print(f"[worker] NEAR {fn}: compiled, bytes differ -> permuter",
                  flush=True)
            sched("report", "--id", rec["id"], "--status", "near",
                  "--score", "50", "--tier", "0",
                  "--notes", ("compiled, byte mismatch; candidate for permuter. "
                              + best)[:250])
        elif not produced_code:
            # The model NEVER produced a candidate: every attempt errored during
            # generation (server error, empty gateway drop, degeneration, or
            # timeout). That is a model/infra failure, not evidence the function
            # is hard, so escalating it to a paid tier is wrong. Return it to
            # todo so a working model re-attempts it.
            #
            # This is what produced the 2026-07-21 escalation spike: a broken
            # free model (hy3 returning UnknownError 80x) burned through ~40
            # functions, escalating each after 4 failed generations it never
            # actually evaluated.
            print(f"[worker] REQUEUE {fn}: no candidate produced in "
                  f"{gen_errors} error(s); back to todo", flush=True)
            sched("report", "--id", rec["id"], "--status", "todo",
                  "--notes", (f"requeued: model produced no candidate "
                              f"({gen_errors} generation errors). {best}")[:250])
        else:
            # A candidate WAS produced and it failed to build. That is a genuine
            # escalation: the model tried and wrote non-compiling C.
            sched("report", "--id", rec["id"], "--status", "escalated",
                  "--score", "0", "--tier", "0", "--notes", best[:250])
    except KeyboardInterrupt:
        # Ctrl-C must never leave a half-applied edit in a real source file.
        print("\n[worker] interrupted; restoring source and releasing record")
        if original is not None:
            try:
                restore(ctx, original)
                print(f"[worker] restored {ctx['src_rel']}")
            except Exception as e:  # noqa: BLE001
                print(f"[worker] WARNING could not restore: {e}", file=sys.stderr)
        try:
            sched("report", "--id", rec["id"], "--status", "todo",
                  "--notes", "interrupted by user")
        except Exception:  # noqa: BLE001
            pass
        raise
    except Exception as e:  # noqa: BLE001
        if original is not None:
            try: restore(ctx, original)
            except Exception: pass
        sched("report", "--id", rec["id"], "--status", "escalated",
              "--notes", f"worker error: {type(e).__name__}: {e}"[:250])
        print(f"[worker] ERROR: {e}", file=sys.stderr)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Harness-driven SOTN matcher.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("once"); p1.add_argument("--dry-run", action="store_true")
    p2 = sub.add_parser("loop")
    p2.add_argument("--max", type=int, default=0)
    p2.add_argument("--dry-run", action="store_true")
    sub.add_parser("preflight",
                   help="check the configured backend is reachable, then exit")
    a = ap.parse_args()

    if not os.path.isdir(WIN_REPO):
        print(f"repo not found: {WIN_REPO}", file=sys.stderr); return 1

    if a.cmd == "preflight":
        # Machine-readable so the connector can gate a fleet launch on it.
        try:
            if MODEL_BACKEND == "cli":
                r = opencode_preflight()
            else:
                r = {"ok": True, "backend": "http", "url": LLAMA_URL,
                     "note": "http backend is checked per-request, not here"}
        except (OpencodeMissing, subprocess.SubprocessError, OSError) as e:
            r = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        r["backend"] = MODEL_BACKEND
        print(json.dumps(r))
        return 0 if r.get("ok") else 1

    # A cli worker that cannot find the CLI will claim a record, fail every
    # attempt and escalate a function for reasons that have nothing to do with
    # the function. Refuse at startup instead.
    if MODEL_BACKEND == "cli":
        try:
            _pf = opencode_preflight()
        except (OpencodeMissing, subprocess.SubprocessError, OSError) as e:
            print(f"[worker] cli backend unusable: {e}", file=sys.stderr)
            return 1
        if not _pf["ok"]:
            print(f"[worker] cli backend unusable: {_pf}", file=sys.stderr)
            return 1
        print(f"[worker] opencode: {_pf['path']} {_pf['version']}",
              file=sys.stderr)

    # fleet_stop sends SIGTERM. Python does NOT raise KeyboardInterrupt for it,
    # so without this handler a killed worker skipped every cleanup path and left
    # its half-applied edit in the tree. That broke the build twice on 2026-07-20
    # and cost three reported matches when the files had to be reverted.
    def _on_sigterm(_sig, _frm):
        print("\n[worker] SIGTERM: restoring source and releasing claim",
              file=sys.stderr)
        try:
            replay_pending_journals()
            release_claim_if_held()
        finally:
            os._exit(143)
    try:
        signal.signal(signal.SIGTERM, _on_sigterm)
    except (ValueError, AttributeError):
        pass

    # Belt and braces: SIGKILL cannot be caught, so also replay at startup. Any
    # edit orphaned by a previous kill is undone before this worker touches
    # anything.
    _restored = replay_pending_journals()
    if _restored:
        print(f"[worker] recovered {_restored} orphaned edit(s) at startup",
              file=sys.stderr)

    # Self-register so the fleet tools can find and stop us. Process-name
    # scanning is not a safe alternative: any shell whose command line mentions
    # worker_direct.py matches it too, which once returned init's pid.
    pidfile = os.path.join(WIN_REPO, "automation", "logs",
                           f"worker-{WORKER_NAME}.pid")
    try:
        os.makedirs(os.path.dirname(pidfile), exist_ok=True)
        with open(pidfile, "w") as f:
            f.write(str(os.getpid()))
    except OSError:
        pidfile = ""

    def _unregister():
        if pidfile:
            try:
                os.unlink(pidfile)
            except OSError:
                pass

    import atexit
    atexit.register(_unregister)

    try:
        if a.cmd == "once":
            process_one(a.dry_run); return 0
        n = 0
        while process_one(a.dry_run):
            n += 1
            if a.max and n >= a.max:
                break
            time.sleep(1)
        print(f"[worker] processed {n}")
        return 0
    except KeyboardInterrupt:
        print("[worker] stopped by user", file=sys.stderr)
        replay_pending_journals()
        release_claim_if_held()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
