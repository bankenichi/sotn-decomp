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
# Only for review_gate: review_checks.py takes a pathlib.Path and does
# .relative_to(REPO) on it, so a plain string will not do.
from pathlib import Path
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

# MODEL_BACKEND=zen: talk to OpenCode Zen over HTTP directly, instead of
# shelling out to `opencode run`.
#
# WHY THIS EXISTS, measured 2026-08-03 with automation/probe_provider.py:
#
#   * The endpoint is HEALTHY. HTTP 200, first byte in ~12s, correct answer,
#     unchanged at an 8000-char prompt. Nothing is refusing us.
#   * Zen serves REASONING models. The reply carries `reasoning_content`
#     alongside `content`, and `completion_tokens_details.reasoning_tokens`
#     counts the thinking.
#   * `opencode run` relays only `content` to stdout. So while a model thinks
#     -- which on a hard function is most of the call -- our stdout is EMPTY,
#     which is byte-for-byte what a dead request looks like. That is the
#     signature behind 878 of 946 dead calls.
#   * opencode also spends ~14s per invocation snapshotting this repo through
#     git, and FAILS at it ("could not open directory 'tools/", exitCode 128),
#     paid on every single call.
#
# Going direct fixes all three: the reasoning stream is captured by the same
# code that already handles it for llama (see the reasoning_content branch in
# the streaming reader), time-to-first-byte becomes real rather than an
# artefact of what opencode chooses to forward, and the per-call snapshot
# overhead disappears.
ZEN_URL = os.environ.get("ZEN_BASE_URL", "https://opencode.ai/zen/v1")
# Headers opencode itself sends. ZEN-FREE-MODELS.md records that Zen
# identifies clients this way; without them we would be a different, anonymous
# client and would not be measuring the service the fleet actually uses.
ZEN_HEADERS = {"User-Agent": "opencode/1.18.12", "x-opencode-client": "cli"}

# THE SINGLE HIGHEST-VALUE SETTING IN THIS FILE.
#
# Measured 2026-08-03, same model (big-pickle), same real decompilation prompt
# (func_us_801B21F0), via automation/probe_provider.py --real-asm:
#
#   thinking ON   77s   8000 completion tokens   0 chars of content
#                       21,535 chars of reasoning_content
#                       finish_reason = "length"  (budget gone, still thinking)
#   thinking OFF  13.5s   647 completion tokens   1,658 chars of C
#                       0 chars of reasoning
#                       finish_reason = "stop"
#
# Twelve times fewer tokens, six times faster, and the difference between a
# complete C function and nothing at all. The model was never failing: it was
# spending its entire budget reasoning and never reaching `content`, and
# `opencode run` relays only `content`, so from the worker's side that is
# indistinguishable from a dead request. That is the 94%.
#
# Which switch actually bites depends on the runtime behind the endpoint.
# Servers ignore fields they do not implement, so send all of them.
NO_THINKING = {
    "reasoning_effort": "none",
    "reasoning_budget": 0,
    "chat_template_kwargs": {"enable_thinking": False},
    "thinking": {"type": "disabled"},
}

# BOUNDED reasoning, not banned reasoning.
#
# Switching thinking off entirely works (13.5s, 647 tokens, a complete
# function) but throws away the thing these models are good at. The failure was
# never that they reasoned, it was that reasoning was UNBOUNDED: 8000 tokens
# spent, `finish_reason: length`, zero content. The budget ran out mid-thought.
#
# So: give them room to think, cap it, and guarantee headroom for the answer.
# REASONING_MAX_TOKENS + CONTENT_MAX_TOKENS is sent as max_tokens, so content
# cannot be starved by thinking no matter how long the thinking runs.
#
# REASONING_EFFORT=none restores the measured-safe behaviour in one env var if
# a model ignores the cap.
# DEFAULT none, on evidence. Apples-to-apples sweep 2026-08-03, one model, one
# prompt, identical max_tokens (probe_provider.py --sweep-effort all):
#
#   none     9.9s   1990 chars of content   0 reasoning      finish stop
#   low     81.5s      0 chars of content   25,215 reasoning finish length
#   medium  94.5s   HTTP 503 Service Unavailable
#   high    39.5s   HTTP 500 Internal Server Error
#
# Reasoning is NOT a knob worth exploiting on Zen. `none` is the only value
# that returns content; `low` spends everything thinking and returns nothing;
# medium and high are not supported at all and fail server-side.
#
# The reasoning machinery stays: the local llama models are reasoning-distilled
# and do emit useful analysis, the capture is what diagnosed this whole class,
# and the force-code pass is the safety net for any model that thinks anyway.
# Set REASONING_EFFORT=low to re-enable it and pay for a second pass.
# DEFAULT low, by choice: reasoning is worth paying for if it produces more
# sensible C, and the sweep only measured WHETHER content came back, never
# whether the content was any good. `none` answers in 9.9s; `low` needs the
# force-code pass and lands around 90s, which is affordable. quality_ab.py
# exists to settle which actually produces better code.
#
# The sweep still stands on the other two: medium is HTTP 503 and high is HTTP
# 500 on Zen, so those are not options, whatever one might want from them.
REASONING_EFFORT = os.environ.get("REASONING_EFFORT", "low").strip().lower()
# 6000, raised from 3000 after the first zen run. ALL TEN calls hit the 3000
# cap with 0 content tokens, and reading the captured reasoning shows why: the
# model was still mid-analysis, working offset by offset through the assembly.
# It was not looping or stuck -- it was cut off. A cap that fires 100% of the
# time is not a safety net, it is the behaviour.
#
# The force-code pass rescued all ten, so nothing was lost, but a truncated
# analysis produces worse C than a finished one: the 8 build failures were all
# "structure has no member named unkNN", i.e. fields it had not finished
# resolving when the axe fell.
REASONING_MAX_TOKENS = int(os.environ.get("REASONING_MAX_TOKENS",
                                          os.environ.get("REASON_CAP", "9000")))
CONTENT_MAX_TOKENS = int(os.environ.get("CONTENT_MAX_TOKENS", "4000"))


def thinking_params() -> dict:
    """What to send so the model thinks a bounded amount and then answers.

    TESTED, AND THE SERVER IGNORES THE SERVER-SIDE KNOBS. Sending
    reasoning_effort="low" with reasoning_budget=2000 and max_tokens=6000 on
    the real func_us_801B21F0 prompt produced 6000 reasoning tokens, zero
    content, finish_reason="length" -- identical to sending nothing at all. Zen
    honours `enable_thinking: false` and nothing finer.

    So the bound has to be OURS. The fields are still sent, because a provider
    that starts honouring them costs us nothing, but the cap that actually
    bites is REASON_CAP in the streaming reader: it counts reasoning tokens as
    they arrive, aborts the stream once they pass the limit with no content,
    and hands the reasoning to _force_code. That gives the model room to think,
    stops it thinking forever, and reuses the thinking instead of binning it.
    """
    if REASONING_EFFORT in ("none", "off", "0"):
        return dict(NO_THINKING, max_tokens=CONTENT_MAX_TOKENS)
    return {
        "reasoning_effort": REASONING_EFFORT,
        "reasoning_budget": REASONING_MAX_TOKENS,
        "chat_template_kwargs": {"enable_thinking": True},
        # Headroom so content cannot be starved even if the server lets
        # thinking run to the ceiling.
        "max_tokens": REASONING_MAX_TOKENS + CONTENT_MAX_TOKENS,
    }
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
#   "zen" (default)  -> POST to the OpenCode Zen API. The configuration to use.
#   "llama"          -> POST to an OpenAI-compatible endpoint. Local
#                       llama-server. Was called "http" until 2026-08-09,
#                       which named the wrong backend: zen is the HTTP one.
#   "cli"            -> shell out to `opencode run`. Uses OpenCode's own auth, so
#                       the free Zen models work with NO API key and NO billing.
#                       Verified 2026-07-20: `opencode auth list` showed 0
#                       credentials and a free model still answered.
# TRADE-OFF: the CLI returns output only when the run finishes, so there is no
# token stream. The live degeneration detector and REASON_CAP both watch the
# stream and cannot function here. FUNC_BUDGET is the only remaining backstop
# against a wedged generation, so keep it set.
MODEL_BACKEND = os.environ.get("MODEL_BACKEND", "zen").strip().lower()
# "http" was the old name for the LOCAL LLAMA backend, which was backwards:
# zen is the one that speaks HTTP. The names now match the things --
# "llama" for llama-server, "zen" for the Zen API -- and the stale spelling
# resolves to what the word actually describes. Normalised here, once, so no
# call site has to know about the rename.
if MODEL_BACKEND == "http":
    MODEL_BACKEND = "zen"
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
# Default chosen by measurement, not preference. The 2026-08-09 battery (90
# generations, 6 functions, 5 models, 3 reasoning configs, then 24 more over
# the newly configured models) put mimo-v2.5-free first on every axis
# independently: 6/6 usable, 1.00 callee recall AND precision, lowest
# fabrication among models that answered, and the fastest at 7s.
# See docs/fleet-dead-time.md.
OPENCODE_MODEL = os.environ.get("OPENCODE_MODEL", "opencode/mimo-v2.5-free")
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


# Prepended to the final retry after repeated empty output. Deliberately the
# same instruction as _force_code's system message: a model that has burned
# several minutes and emitted nothing has usually reasoned itself into a corner,
# and asking it politely to be brief does not work. The thinking has to be shut
# off, not discouraged. Observed 2026-07-21 on the http backend, where a salvage
# pass produced 32000 characters of reasoning and no C at all.
_CLI_FORCE_PREFIX = (
    "You are a C code emitter. You do not explain. You do not analyse.\n"
    "Your ENTIRE reply must be one C function definition and nothing else.\n"
    "No prose before it. No commentary after it. No markdown fences.\n"
    "Begin your reply with the return type.\n\n"
)


def _opencode_run(prompt: str, timeout: float | None = None) -> str:
    """Retry wrapper. Empty output is transient, so do not waste the attempt.

    The LAST retry changes the prompt instead of repeating it. Retrying an
    identical prompt against a model that has already returned rc=0 with zero
    bytes several times is the definition of expecting a different result, and
    it is what the cli fleet was doing: five identical calls at 48-382s each,
    then a hard failure, per function.

    _force_code's salvage cannot help here -- it fires from the degeneration
    detector, which only trips on output that IS arriving and is bad, whereas
    this path exists for output that never arrives at all. So the cli backend
    gets its own last-ditch attempt with thinking suppressed, which is the part
    of _force_code that actually does the work.

    (The cli backend DOES stream now, via Popen in _opencode_run_once, and a
    timed-out stream holding a complete function is salvaged there. This
    fallback covers the different case of a genuinely empty response.)
    """
    deadline = None if timeout is None else time.time() + timeout
    last = None
    for n in range(1, RATE_LIMIT_RETRIES + 1):
        left = None if deadline is None else deadline - time.time()
        if left is not None and left <= 15:
            break
        final = (n == RATE_LIMIT_RETRIES)
        try:
            text = _opencode_run_once(
                (_CLI_FORCE_PREFIX + prompt) if final else prompt, timeout=left)
            if final:
                print("  ++ force-code retry produced "
                      f"{len(text)} chars", flush=True)
            return text
        except _EmptyOutput as e:
            last = e
            tag = " (force-code retry)" if final else ""
            print(f"  !! empty response ({n}/{RATE_LIMIT_RETRIES}){tag}: {e}",
                  flush=True)
            time.sleep(5)
    raise RuntimeError(f"opencode returned empty output repeatedly, including "
                       f"a force-code retry: {last}")


def _telemetry_path() -> str:
    return os.path.join(WIN_REPO, "automation", "logs", "calls.jsonl")


def emit_call(rec: dict) -> None:
    """Append one call record to logs/calls.jsonl. Never raises.

    ONE COMPLETE LINE PER WRITE, in append mode. A worker killed mid-write
    would otherwise leave a half-record that makes the whole file unparseable
    from that point on, and workers get killed routinely here. Serialising
    first and issuing a single write of a string that already ends in \\n is
    what keeps concurrent appends from interleaving: POSIX guarantees an
    append-mode write below PIPE_BUF is atomic, and these records are ~300
    bytes.

    Telemetry must never be able to break a run, hence the bare except: a
    disk-full or permission error here is not a reason to lose a candidate.
    """
    try:
        rec.setdefault("ts", time.time())
        rec.setdefault("worker", WORKER_NAME)
        line = json.dumps(rec, default=str) + "\n"
        d = os.path.dirname(_telemetry_path())
        os.makedirs(d, exist_ok=True)
        with open(_telemetry_path(), "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:                                        # noqa: BLE001
        pass


def _drain_stderr(proc, limit: int = 500) -> str:
    """Whatever the child wrote to stderr, without hanging on it.

    THE POINT OF THE WHOLE EXERCISE. The timeout path used to kill the child
    and re-raise without ever reading stderr, so 724 silent timeouts threw away
    whatever `opencode run` said about them -- rate limit, auth, model gone.

    Runs in a thread with a hard join, because a read on a pipe whose writer
    has been killed is *usually* an instant EOF and occasionally is not, and
    blocking here would turn a 90s timeout into a hang.
    """
    if not proc.stderr:
        return ""
    box: list[str] = []

    def rd():
        try:
            box.append(proc.stderr.read() or "")
        except (OSError, ValueError):
            pass

    t = threading.Thread(target=rd, daemon=True)
    t.start()
    t.join(timeout=3)
    return (box[0].strip()[:limit] if box else "")


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
    # Time to first byte, recorded where the first byte actually lands. This is
    # the field that separates "the provider never answered" from "the provider
    # answered and we cut it off", which the logs could not distinguish at all:
    # both were just `timed out after 90s`. None means nothing ever arrived.
    ttfb: list[float | None] = [None]
    # When the most recent byte arrived. Silence is measured from here, not
    # from the start of the call.
    last_byte = [time.time()]
    done = threading.Event()

    def pump():
        try:
            for line in proc.stdout:
                if ttfb[0] is None:
                    ttfb[0] = time.time() - t0
                last_byte[0] = time.time()
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
    def _adaptive_wait(hard_cap: float) -> str:
        """Block until the child exits or a deadline fires; say WHICH.

        Polls rather than using proc.wait(timeout=...) because the deadline is
        not a constant: it depends on whether anything has been received yet
        and, once it has, on how long ago. 0.25s is well below every deadline
        involved and costs nothing measurable.
        """
        while True:
            if proc.poll() is not None:
                return ""
            now = time.time()
            if ttfb[0] is None:
                if now - t0 >= min(NO_FIRST_BYTE_S, hard_cap):
                    return "no_first_byte"
            elif now - last_byte[0] >= STREAM_IDLE_S:
                return "stream_idle"
            if now - t0 >= hard_cap:
                return "hard_cap"
            time.sleep(0.25)

    kill_reason = _adaptive_wait(_to)
    if kill_reason:
        # SALVAGE BEFORE GIVING UP.
        #
        # `buf` already holds every line the model streamed. Discarding it on
        # timeout threw away finished work: observed 2026-08-03 on
        # func_us_801B21F0, where attempt 2 streamed a complete function and
        # was reported as "timed out" and dropped, so the worker paid for three
        # more attempts on a function it had already answered.
        #
        # Rare in practice -- 2 of 1041 recorded calls -- because the dominant
        # failure produces nothing at all. Kept because it costs nothing and
        # the one case it catches is a whole function.
        #
        # Only a COMPLETE function is salvaged. A truncated body would compile
        # to something arbitrary or fail the build with a confusing error, so
        # complete_function() insists on balanced braces and a closing brace at
        # the end; anything less raises and the attempt is spent as before.
        proc.kill()
        done.wait(timeout=5)
        err = _drain_stderr(proc)
        text = "".join(buf)
        salvaged = complete_function(text)
        emit_call({
            "model": OPENCODE_MODEL, "prompt_chars": len(prompt),
            "ttfb_s": ttfb[0], "total_s": round(time.time() - t0, 1),
            "stream_chars": len(text), "rc": proc.returncode,
            "outcome": ("timeout_complete" if salvaged
                        else "timeout_partial" if text.strip()
                        else "timeout_no_bytes"),
            "stderr_head": err, "cap_s": _to,
            # WHICH deadline fired. Without this the tuning is blind: a run
            # full of `no_first_byte` means the provider is dropping requests,
            # a run full of `stream_idle` means models are stalling mid-answer,
            # and `hard_cap` means the ceiling is genuinely too low. They need
            # opposite responses.
            "kill_reason": kill_reason,
            "no_first_byte_s": NO_FIRST_BYTE_S,
            "stream_idle_s": STREAM_IDLE_S})
        # Surface it in the human log too. A reason that only exists in a JSONL
        # nobody opens is barely better than one that was thrown away.
        why = {"no_first_byte": f"nothing arrived in {NO_FIRST_BYTE_S:.0f}s",
               "stream_idle": f"went quiet for {STREAM_IDLE_S:.0f}s",
               "hard_cap": f"hit the {_to:.0f}s ceiling"}.get(
                   kill_reason, kill_reason)
        print(f"  !! killed at {int(time.time() - t0)}s: {why} "
              f"(ttfb={'never' if ttfb[0] is None else f'{ttfb[0]:.1f}s'}, "
              f"{len(text)} chars). stderr: {err or '(empty)'}", flush=True)
        if salvaged:
            print(f"  ++ attempt timed out at {int(time.time() - t0)}s but the "
                  f"stream already held a COMPLETE function "
                  f"({len(salvaged)} chars); salvaged instead of discarded",
                  flush=True)
            return salvaged
        raise subprocess.TimeoutExpired(argv, _to)
    done.wait(timeout=5)
    out = "".join(buf)
    err = _drain_stderr(proc, limit=800)

    _tel = {"model": OPENCODE_MODEL, "prompt_chars": len(prompt),
            "ttfb_s": ttfb[0], "total_s": round(time.time() - t0, 1),
            "stream_chars": len(out), "rc": proc.returncode,
            "stderr_head": err[:500], "cap_s": _to}
    if aborted[0]:
        emit_call({**_tel, "outcome": "degenerated", "detail": aborted[0][:200]})
    elif proc.returncode not in (0, None) and not out.strip():
        emit_call({**_tel, "outcome": "genfail"})
    elif not out.strip():
        emit_call({**_tel, "outcome": "empty"})
    else:
        emit_call({**_tel, "outcome": "produced"})

    if aborted[0]:
        # Degenerate output is not empty-transient; the model IS answering, just
        # badly. Surface it as a normal failure so the attempt is spent and the
        # retry can carry different feedback.
        raise RuntimeError(f"opencode degenerated: {aborted[0]}")
    if proc.returncode not in (0, None) and not out.strip():
        raise RuntimeError(
            f"opencode run failed (rc={proc.returncode}): {err[:800]}")
    print(f"  --- done in {int(time.time() - t0)}s: {len(out)} chars "
          f"(ttfb={'never' if ttfb[0] is None else f'{ttfb[0]:.1f}s'}) ---",
          flush=True)
    if not out.strip():
        # rc=0 with EMPTY stdout: transient gateway drop, correlated with large
        # prompts. Retry rather than escalate the whole function.
        raise _EmptyOutput(
            f"rc=0 but NO output after {int(time.time() - t0)}s "
            f"(prompt {len(prompt)} chars). stderr: {err[:300]}")
    return out


def _base_url() -> str:
    """The endpoint for the active backend. One place, so the three call sites
    cannot drift apart."""
    return (ZEN_URL if MODEL_BACKEND == "zen" else LLAMA_URL).rstrip("/")


def _active_model() -> str:
    """Zen model ids are bare here; the `opencode/` prefix is a CLI concept."""
    if MODEL_BACKEND != "zen":
        return LLAMA_MODEL
    return (OPENCODE_MODEL or "").split("/")[-1] or "mimo-v2.5-free"


def _api_headers() -> dict:
    h = {"Content-Type": "application/json"}
    if MODEL_BACKEND == "zen":
        h.update(ZEN_HEADERS)
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
# The bound that actually bites, because Zen ignores reasoning_budget.
# Counted in the streaming reader: once reasoning passes this with no
# content, the stream is aborted and the reasoning is handed to
# _force_code rather than thrown away. Same value as
# REASONING_MAX_TOKENS so the request we send and the limit we enforce
# cannot drift apart.
REASON_CAP = REASONING_MAX_TOKENS
# Largest function this tier will attempt, in chars of assembly.
#
# BACKEND-DEPENDENT. 6000 is calibrated for local llama, which loses coherence
# well before that (the 2026-07-21 logs show degenerate-loop aborts on far
# smaller inputs). HOSTED models take much more context, so the hosted tiers
# exist precisely to pick up what llama defers.
#
# Deferring is therefore a HANDOFF, not a dead end: see DEFER_TOO_LARGE and
# scheduler `next --include-deferred`.
#
# THE TEST USED TO BE `== "cli"`, AND ZEN FELL INTO THE LOCAL-LLAMA BRANCH.
# zen is hosted, with the same large context as cli; it was added after this
# line was written and the ternary was never revisited. The effect was that
# the zen fleet deferred every function over 6000 chars to a "next tier" that
# was itself the broken cli backend, so ~25 records accumulated in `deferred`
# having never been attempted by anything. The 2026-08-09 battery put 8.9k and
# 13.9k asm through zen and got usable C back from mimo, so 6000 was never the
# right ceiling for it.
_HOSTED = {"cli", "zen"}
_DEFAULT_MAX_FUNC = "20000" if MODEL_BACKEND in _HOSTED else "6000"
MAX_FUNC_CHARS = int(os.environ.get("MAX_FUNC_CHARS", _DEFAULT_MAX_FUNC))
# Stable marker in the notes so the next tier can find exactly these records.
# Matching on prose would break the moment someone reworded the message.
DEFER_TOO_LARGE = "TIER_HANDOFF_TOO_LARGE"
# A distinct marker so these are greppable and requeueable as a batch once the
# shim is done. They are NOT failures: they are records whose correct fix is
# structural, caught before any quota was spent on them.
DEFER_SHIMMABLE = "SHIM_INSTEAD_OF_GENERATE"
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
# 1800s was chosen in July to keep four real attempts of ~382s each. Measured
# again on 2026-08-03 over 108 cli calls, that ceiling is far too generous:
#
#   productive calls   n=24   median  70s   p75 122s   p90 249s   max 374s
#   dead calls         n=84   median 347s   p90 382s   max 382s
#
# Productive work finishes FAST and dead work runs the clock out. Almost every
# dead call sat at the 382s ceiling, so the ceiling was buying nothing but the
# right to wait. Simulating tighter caps over those same calls:
#
#   180s -> loses  4/24 good calls, saves 165m of dead time
#   240s -> loses  4/24 good calls, saves 109m
#   300s -> loses  2/24 good calls, saves  58m
#
# 900s here gives ~191s per attempt, which covers p75 of productive calls and
# cuts roughly 160 of the 375 wasted minutes. The good calls it does cut are
# not lost work: a function with no candidate is requeued to `todo` and retried
# later, so the cost is a retry rather than a function.
#
# Raise FUNC_BUDGET rather than cutting MAX_ATTEMPTS: retries are the only
# consumer of asm-differ feedback, so trading them away makes every attempt a
# blind first attempt.
_DEFAULT_FUNC_BUDGET = os.environ.get(
    "FUNC_BUDGET", "900" if MODEL_BACKEND == "cli" else "900")
FUNC_BUDGET = float(os.environ.get("FUNC_BUDGET", _DEFAULT_FUNC_BUDGET))
# Per-ATTEMPT ceiling, derived from the function budget so the retries actually
# happen. Without it a single attempt consumed the whole 900s (observed
# 2026-07-20: "BUDGET EXHAUSTED after 900.0s (1 attempts)" repeatedly), which
# silently disabled the retry loop. That matters more than it sounds, because
# retries are the ONLY consumer of asm-differ feedback: attempt 1 has no diff to
# learn from by definition. A blind first attempt is all we were ever running.
# Default leaves a little headroom for the build and diff between attempts.
#
# 90s, MEASURED, not derived. Over 399 calls on 2026-08-03 the two populations
# barely overlap:
#
#     produced   n=58    min 15s   median  73s   p75 138s   p90 182s
#     dead       n=299   min 48s   median 191s   p75 191s   p90 382s
#
# so a cap placed just past the productive median costs 21 of 58 good calls and
# saves 519.6 of the 960.2 wasted minutes -- 54% of all dead time. The derived
# value was 191s, which is exactly the dead median: it sat where the useless
# calls pile up and cut almost none of them.
#
# A cut good call is NOT a lost function. With no candidate the record is
# requeued to `todo` and tried again, so the cost is one retry against half the
# fleet's wall clock. FUNC_BUDGET stays 900 deliberately: 4 attempts now cost at
# most 360s of model time, and the remainder is headroom for the builds and
# diffs between them rather than more waiting on a model.
ATTEMPT_BUDGET = float(os.environ.get("ATTEMPT_BUDGET", "90"))

# ADAPTIVE DEADLINES. A flat cap punishes the wrong call.
#
# Measured 2026-08-03: of 946 dead calls, 878 (93%) returned ZERO bytes, and an
# instrumented run of 11 confirmed 11/11 never produced a first byte -- while
# stderr held nothing but opencode's own startup banner. The provider does not
# refuse, it goes silent.
#
# So silence and slowness are completely different states and deserve
# different deadlines:
#
#   NO_FIRST_BYTE_S  nothing has arrived at all. In every case measured so far
#                    nothing ever did, so waiting the full budget buys nothing.
#                    Kill early and spend the time on the next attempt.
#   STREAM_IDLE_S    bytes ARE arriving. The model is working. Only give up
#                    after it has gone quiet for this long, NOT at some total
#                    elapsed time -- a long function legitimately takes a long
#                    time to write, and killing a model mid-emission throws
#                    away work that was about to land.
#   hard ceiling     whatever remains of FUNC_BUDGET, so a model that streams
#                    forever still cannot hold a worker hostage.
#
# The net effect is the opposite of a flat cap on both ends: dead calls die in
# 45s instead of 90s, and a genuinely productive call may run WELL PAST 90s as
# long as it keeps producing.
#
# CORRECTION 2026-08-03, same day: 45 was WRONG and would have made things
# worse. Probing the endpoint directly (automation/probe_provider.py) showed it
# is healthy -- HTTP 200, first byte in ~12s, correct answer -- and revealed
# why our stdout is empty:
#
#   "message": {"content": "ok",
#               "reasoning_content": "We need to respond with exactly ..."}
#   "completion_tokens_details": {"reasoning_tokens": 12}
#
# These are REASONING models. Output lands in `reasoning_content` first and in
# `content` only when thinking finishes, and opencode streams `content` deltas.
# So a model that is working hard looks byte-for-byte identical to a dead
# request from our side: silence.
#
# "No first byte" therefore does NOT mean "dead", it means "still thinking",
# and a 45s guillotine would kill the models doing the most work on the hardest
# functions. Set high on purpose. The number is provisional until the reasoning
# time on a REAL decompilation prompt is measured
# (probe_provider.py --real-asm); treat any value here as a hypothesis.
NO_FIRST_BYTE_S = float(os.environ.get("NO_FIRST_BYTE_S", "240"))
STREAM_IDLE_S = float(os.environ.get("STREAM_IDLE_S", "45"))
# How often to test the CONTENT stream for a degeneration loop. Cheap: the
# check is three regex passes over the text so far, run every N tokens.
CONTENT_CHECK_EVERY = int(os.environ.get("CONTENT_CHECK_EVERY", "120"))

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from degeneracy import degenerate as _content_degenerate
except ImportError:                                          # pragma: no cover
    def _content_degenerate(_c):                             # type: ignore
        return {"degenerate": False}


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
# The status the claim was taken FROM, so a stranded claim goes back there
# rather than to a hard-coded "todo". See release_claim_if_held.
_CURRENT_CLAIM_FROM: str | None = None


def release_claim_if_held() -> None:
    """Return a still-held claim to WHERE IT CAME FROM. Safe to call twice.

    This used to hard-code 'todo'. `scheduler.py next` can claim a `deferred`
    handoff record, so an interrupted worker silently promoted it out of the
    deferred pool. The same hard-coding in cmd_reclaim would make any future
    tier-2 consumer's escalated record fall back to Tier 0 and be reworked by
    the cheapest model, which inverts the whole point of escalation.
    """
    global _CURRENT_CLAIM, _CURRENT_CLAIM_FROM
    cid, _CURRENT_CLAIM = _CURRENT_CLAIM, None
    back, _CURRENT_CLAIM_FROM = _CURRENT_CLAIM_FROM or "todo", None
    if not cid:
        return
    try:
        print(f"[worker] releasing stranded claim {cid} -> {back}",
              file=sys.stderr)
        sched("report", "--id", cid, "--status", back,
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
                    # Scan the WHOLE FILE, not line by line.
                    #
                    # clang-format wraps a long INCLUDE_ASM across two lines:
                    #
                    #     INCLUDE_ASM(
                    #         "boss/bo6/nonmatchings/us_3E79C", SomeLongName);
                    #
                    # RX_INC's \s* spans the newline happily, but only if it is
                    # given the newline. Matching per-line meant neither half
                    # matched, locate() returned None, and the worker escalated
                    # the record as "INCLUDE_ASM stub not found" -- permanently,
                    # since the name length never changes.
                    #
                    # Two BO6 records sat escalated this way. They were requeued
                    # on 2026-08-02 after the regex was tested against the whole
                    # file and appeared to match; that test exercised
                    # apply_code's pattern, NOT this loop, and the fleet
                    # re-escalated both within the hour. The line number is
                    # derived from the match offset so the index is unchanged.
                    with open(full, errors="ignore") as f:
                        text = f.read()
                    for m in RX_INC.finditer(text):
                        line_no = text.count("\n", 0, m.start()) + 1
                        _INDEX.setdefault(m.group(2), []).append(
                            (rel, line_no, m.group(1)))
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


def candidate_path(rec: dict) -> str:
    """Where a compiling-but-mismatching candidate is kept, per queue record.

    NOT under automation/logs/: that whole directory is gitignored and gets
    archived when the logs get noisy, so anything left there is disposable by
    design. A compiling candidate is the opposite of disposable.
    """
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", rec["id"]).strip("_")
    return os.path.join(WIN_REPO, "automation", "candidates", f"{slug}.c")


def save_candidate(rec: dict, code: str, attempt: int, detail: str,
                   ctx: dict | None = None) -> str:
    """Preserve C that COMPILED AND LINKED but produced the wrong bytes.

    This is the single most valuable artifact the worker produces short of a
    match, and it was being thrown away.

    The permuter mutates a compiling function to search codegen space. It needs
    a compiling function to start from. The worker reverts every failed attempt
    so the tree stays clean for other workers, which is correct, and it writes
    each attempt to automation/logs/gen/ -- but that recorded no verdict, so
    nothing downstream could tell a candidate that compiled from one that never
    built, and the directory is gitignored and periodically archived.

    Net effect measured 2026-08-02: all four `near` records had ZERO surviving
    seeds, live or archived, so the permuter had nothing to run on and P2 sat
    blocked. Every one of those had to be regenerated from scratch.

    THE SEED MUST BE SELF-CONTAINED, which is why `ctx` is taken and
    virtual_apply() is used. A seed is only useful if decomp-permuter's
    import.py can compile it, and import.py compiles the file it is handed --
    nothing else. Writing the model's bare function body produced seeds that
    could not be imported at all:

      - the rcen seed failed with "syntax error in base.c ... before `arg0'"
        because there was no #include, so s32/Entity/g_CurrentEntity were
        undefined types to the parser;
      - the bo6 func_us_801BC3E0 seed failed with "`RIC_step' undeclared"
        because that extern lives elsewhere in us_39144.c, outside the body.

    Both had to be reconstructed by hand: stage a file in the overlay directory
    so the quoted #include resolves, import, then delete it. That is the work
    this function exists to make unnecessary.

    virtual_apply() returns the WHOLE target file with the stub replaced by the
    candidate, so the seed carries every include and every file-scope
    declaration the body depends on, and compiles exactly as the real build
    does. It is the same substitution apply_code() performs, so the seed is a
    faithful record of what was actually built and measured.

    Falls back to the bare body when ctx is absent or the substitution fails --
    an incomplete seed still beats none, and the banner says which it is.

    Returns the repo-relative path, or "" on failure. Never raises: losing the
    seed is bad, but failing the attempt over a filesystem hiccup is worse.
    """
    try:
        path = candidate_path(rec)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        model = OPENCODE_MODEL if MODEL_BACKEND == "cli" else _active_model()
        payload, kind = code, "FUNCTION BODY ONLY"
        if ctx:
            try:
                whole = virtual_apply(ctx, rec["function"], code)
                if whole:
                    payload, kind = whole, "WHOLE FILE (directly importable)"
            except Exception as e:                       # never lose the seed
                print(f"  !! seed fell back to the bare body: {e}", flush=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"/* PERMUTER SEED -- compiled and linked, bytes differ.\n"
                    f"   record : {rec['id']}\n"
                    f"   attempt: {attempt}/{MAX_ATTEMPTS}\n"
                    f"   model  : {model}\n"
                    f"   verdict: {detail[:160]}\n"
                    f"   content: {kind}\n"
                    f"   import : python3 tools/decomp-permuter/import.py "
                    f"<this file> {asm_rel_path(rec, ctx.get('asm_rel', '')) if ctx else '<asm>'}\n"
                    f"   Do NOT apply this to the tree as-is; it does not match.\n"
                    f"   It exists so the permuter has a compiling starting"
                    f" point. */\n")
            f.write(payload)
        return os.path.relpath(path, WIN_REPO).replace("\\", "/")
    except OSError as e:
        print(f"  !! could not save permuter seed: {e}", flush=True)
        return ""


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


def build_error_is_ours(out: str, rec: dict) -> bool:
    """Does this build failure actually implicate the record under work?

    A C edit inside one overlay cannot break another overlay's link. So when the
    captured diagnostics mention only some other overlay's artifacts, the tree
    was dirty and the candidate was never really tested.

    Conservative on purpose: ANY of the function name, the record's source file,
    its overlay leaf, or a generic (non-overlay) compiler diagnostic counts as
    ours. Returning True on an ambiguous failure just preserves the old
    behaviour; returning False wrongly would hide a real defect, which is the
    expensive direction.
    """
    if not out:
        return True
    low = out.lower()
    fn = rec.get("function", "")
    if fn and fn.lower() in low:
        return True
    leaf = rec.get("overlay", "").split("/")[-1].lower()
    if leaf and leaf in low:
        return True
    src = (rec.get("src_rel") or "").lower()
    if src and src in low:
        return True

    # From here on the output does not name us. That is NOT yet enough: it must
    # positively name someone ELSE before we disown the failure. Requiring
    # positive evidence is what keeps the asymmetry right -- a bare
    # "make: *** Error 1" or "ninja: build stopped" names nobody, so it stays
    # ours and behaves exactly as before this guard existed.
    foreign = False

    # A diagnostic inside ANOTHER overlay's source directory, i.e.
    # src/{st,boss,servant}/<stage>/... where <stage> is not our leaf. Shared
    # headers like src/st/st_common.h have no <stage> component and are
    # deliberately NOT foreign: we may well have broken one.
    for m in re.finditer(r"([\w./\\-]+\.[ch]):\d+:", out):
        parts = m.group(1).replace("\\", "/").lower().split("/")
        if len(parts) >= 4 and parts[0] == "src" and \
                parts[1] in ("st", "boss", "servant"):
            if parts[2] != leaf:
                foreign = True
            else:
                return True          # our own overlay: definitely ours
        else:
            return True              # shared, include/, src/main: could be ours

    # A failed link or artifact belonging to another overlay.
    for m in re.finditer(r"(?:FAILED:|-o)\s+build/\w+/(\S+)", out):
        art = m.group(1).lower()
        if leaf and leaf in art:
            return True
        foreign = True

    return not foreign


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

# The `/* fileoff vaddr encoding */` triple splat puts on every instruction.
_ASM_PREFIX = re.compile(
    r"^\s*/\* [0-9A-Fa-f]+ [0-9A-Fa-f]+ [0-9A-Fa-f]+ \*/\s*", re.M)


def compact_asm(text: str) -> str:
    """Strip addressing noise from a splat .s file.

    Every instruction line carries `/* 4B2DC 801CB2DC C8FFBD27 */` -- file
    offset, virtual address and the raw encoding -- plus column padding to
    align the operands. None of it helps write C. The model needs the opcodes
    and the operands; where the instruction lives in the ROM is irrelevant to
    the source that produced it.

    Measured over 372 asm files: a MEDIAN 62% smaller, and 67% on
    BO6_RicEntitySubwpnStopwatchCircle (13,660 -> 4,485 chars). That matters
    because prompt size predicts an EMPTY response: re-measured over 1042
    calls, 3% empty under 5k chars, 19% at 5-10k, 37% at 10-20k. (The COMBINED
    dead rate is flat at 88/82/84; the empty and timeout slopes cancel. Quote
    the split, not the total.)

    Safe with respect to everything downstream. resolve_raw_symbols matches
    `D_us_XXXXXXXX` and undeclared_symbols matches `%hi(...)/%lo(...)`; both
    appear in OPERANDS, never in the stripped prefix. Removing the prefix also
    removes a source of false positives, since it is full of bare hex.

    Second-order benefit: with the asm this much smaller, MAX_ASM_CHARS covers
    roughly three times as much real function, so far fewer prompts are
    truncated mid-function -- which used to produce confident C for the half
    the model was shown.
    """
    t = _ASM_PREFIX.sub("  ", text)
    t = re.sub(r"[ \t]{2,}", " ", t)       # collapse operand alignment padding
    t = re.sub(r"[ \t]+$", "", t, flags=re.M)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


# m2c pads to a column and appends /* extern */ to every declaration it had to
# invent. The marker says nothing the declaration does not, and the padding to
# reach it is pure column alignment: on func_us_801AE858 the two together cost
# 390 chars across 8 lines.
_DRAFT_EXTERN = re.compile(r"[ \t]*/\*[ \t]*extern[ \t]*\*/[ \t]*$", re.M)
# Kept, not stripped. These are m2c telling you WHY it could not produce clean
# C, which is the single most useful sentence in the draft for deciding how to
# restructure the function.
_DRAFT_KEEP = ("Duplicate return", "irregular", "unable to", "Unhandled",
               "Read from unset", "unknown", "warning")


_RX_ENTITY_PTR = re.compile(r"\bEntity\s*\*\s*(\w+)")
_RX_UNK_ACCESS = re.compile(r"\b(\w+)->unk([0-9A-Fa-f]{1,3})\b")
_RX_ANY_PTR = re.compile(r"\b(\w+)\s*\*\s*(\w+)\s*[;,)=]")


def clean_draft(draft: str) -> tuple[str, list[str]]:
    """Resolve `->unkNN` in the m2c draft to real Entity fields.

    THE DRAFT IS THE MODEL'S STARTING POINT and it arrives full of the exact
    thing the prompt then forbids. Telling a model "translate ->unk24 to
    ->zPriority" and handing it a draft saying `->unk24` spends its attention
    on a mechanical lookup the harness can do perfectly, and every offset it
    fails to translate is a build failure: `structure has no member named
    unk24`.

    ONLY VARIABLES m2c ACTUALLY TYPED AS `Entity*`. m2c emits `->unkNN` for
    any struct it could not resolve, so a blind rewrite would paste Entity's
    field names onto a Primitive or a Collider -- which is precisely the
    failure member_types.py was written to catch, and it would be this file
    creating it rather than the model.

    Offsets at 0x7C+ are left alone: that is the ext union, whose field names
    depend on the entity variant and cannot be read off the Entity layout.
    """
    if not draft:
        return draft, []
    typed = set(_RX_ENTITY_PTR.findall(draft))
    if not typed:
        return draft, []
    fields = {off: name for off, name, _t in _layout_fields()}
    notes, seen = [], set()

    def sub(m):
        var, hexoff = m.group(1), m.group(2)
        if var not in typed:
            return m.group(0)
        off = int(hexoff, 16)
        if off >= 0x7C or off not in fields:
            return m.group(0)
        if (var, hexoff) not in seen:
            seen.add((var, hexoff))
            notes.append(f"{var}->unk{hexoff} -> ->{fields[off]}")
        return f"{var}->{fields[off]}"

    return _RX_UNK_ACCESS.sub(sub, draft), notes


def compact_draft(text: str, indent: int = 1) -> str:
    """Trim m2c's output without losing anything that helps write C.

    THE DRAFT IS NOT FREE. Measured over 11 real functions on 2026-08-03, the
    draft averages 0.96x the size of the COMPACTED assembly beside it and runs
    to 1.17x on some, so it is fully half the prompt. Prompt size drives the
    EMPTY-response rate (3% under 5k chars, 37% at 10-20k, over 1042 calls),
    so halving the prompt attacks that specific failure. It does NOT move the
    combined dead rate, which is flat across sizes.

    WHERE THE VOLUME ACTUALLY IS
        On func_us_801AE858, a 16,972-char draft: 5,268 chars of it, 31%, is
        LEADING WHITESPACE. m2c indents four spaces per level and decompiled
        control flow nests deep, so a line can start twenty-four columns in.
        Indentation is the cheapest thing in the file to shrink and the least
        informative: one space per level preserves the nesting exactly, because
        what matters is that the reader can see WHICH level a statement is at,
        not how far right it sits.

    WHAT IS DELIBERATELY KEPT
        Every identifier, literal, operator and brace, so the control flow and
        every symbol the model must reference survive untouched. m2c's
        diagnostic comments are kept too (see _DRAFT_KEEP): "Duplicate return
        node #8. Try simplifying control flow for better match" is the most
        actionable line m2c ever emits, and dropping it to save 70 chars would
        be trading the signal for the noise.
    """
    # Derive the indent unit from the text instead of hardcoding 4. Hardcoding
    # made this NON-IDEMPOTENT: after one pass the unit is 1, so `lead // 4`
    # floors every level to 0 and a second pass flattens the nesting entirely.
    # The prompt is rebuilt on every retry, so a non-idempotent compactor
    # silently destroys structure on attempt 2. The asm compactor is asserted
    # idempotent for exactly this reason.
    leads = [len(l) - len(l.lstrip(" ")) for l in text.splitlines()
             if l.strip() and l.startswith(" ")]
    unit = min(leads) if leads else 4
    out = []
    for line in text.splitlines():
        s = line.lstrip(" \t")
        # m2c's own `//` chatter goes; `/* ... */` diagnostics are judged.
        if s.startswith("//"):
            continue
        if s.startswith("/*") and not any(k in s for k in _DRAFT_KEEP):
            continue
        lead = len(line) - len(s)
        # A re-indent, not a guess: the level survives, the width does not.
        # Also collapse the run of spaces m2c uses to right-align a trailing
        # comment; the comment keeps its meaning, the column does not.
        s = re.sub(r"[ \t]{2,}(/\*)", r"  \1", s)
        out.append(" " * ((lead // max(1, unit)) * indent) + s.rstrip())
    t = "\n".join(out)
    t = _DRAFT_EXTERN.sub("", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def prepare(rec: dict, located) -> dict:
    src_rel, lineno, asm_rel = located
    asm_file = asm_rel_path(rec, asm_rel)
    fn = rec["function"]
    _ = _DECL_CACHE  # module-level cache, populated by lookup_declarations

    asm_text = ""
    asm_full = 0
    p = win_path(asm_file)
    if os.path.exists(p):
        _raw = compact_asm(open(p, errors="ignore").read())
        asm_full = len(_raw)
        asm_text = _raw[:MAX_ASM_CHARS]
        if asm_full > MAX_ASM_CHARS:
            # Say it out loud. Silently handing the model 12000 of a 40000-char
            # function looks exactly like a normal run and produces confident,
            # wrong C for the half it was shown.
            print(f"[prep] WARNING: asm truncated {asm_full} -> {MAX_ASM_CHARS} "
                  f"chars (MAX_ASM_CHARS)", flush=True)

    # m2ctx.py writes ONE file, <repo>/ctx.c, with a hardcoded name.
    #
    # Generation is documented as "safe to overlap because it only reads", and
    # that is wrong: every worker runs m2ctx during this phase and they all
    # write and then read the same path. Worker A can read B's ctx.c and hand
    # m2c the type context of an unrelated file, which silently degrades the
    # draft the model is given. Nothing errors.
    #
    # Serialise the write, then immediately claim the result under a per-worker
    # name. The lock is held only across m2ctx itself, which is fast, so this
    # costs almost nothing compared to the model call it precedes.
    ctx_name = f"ctx.{WORKER_NAME}.c"
    ctx_path = os.path.join(WIN_REPO, ctx_name)
    with Status("m2ctx (generating C type context)") as st:
        with BuildLock(os.path.join(WIN_REPO, "automation", ".m2ctx.lock"),
                       stale_after=300.0):
            rc, out = wsl(f"python3 tools/m2ctx.py {src_rel}", timeout=300)
            shared = os.path.join(WIN_REPO, "ctx.c")
            if rc == 0 and os.path.exists(shared):
                try:
                    shutil.copyfile(shared, ctx_path)
                except OSError as e:
                    rc = 1
                    out = f"could not claim ctx.c: {e}"
        st.update("ok" if rc == 0 else "failed")
    ctx_ok = rc == 0 and os.path.exists(ctx_path)
    if not ctx_ok:
        print(f"[prep] m2ctx failed (continuing without types): {out.strip()[:160]}")

    ctx_arg = f"--context {ctx_name}" if ctx_ok else ""
    with Status("m2c (first-draft decompilation)") as st:
        rc, draft = wsl(
            f"python3 tools/m2c/m2c.py --target mipsel-gcc-c {ctx_arg} "
            f"-f {fn} {asm_file}", timeout=300)
        st.update(f"{len(draft)} chars")
    if rc != 0:
        # retry without the context, which is the usual cause of m2c errors
        rc, draft = wsl(f"python3 tools/m2c/m2c.py --target mipsel-gcc-c "
                        f"-f {fn} {asm_file}", timeout=300)
    draft = compact_draft(draft)[:MAX_CTX_CHARS]
    draft, _cleaned = clean_draft(draft)
    if _cleaned:
        print(f"[prep] draft: resolved {len(_cleaned)} unkNN access(es) "
              f"before the model sees them")
    decls = lookup_declarations(extract_asm_symbols(asm_text, exclude=fn))
    print(f"[prep] draft: {len(draft)} chars, asm: {len(asm_text)} chars, "
          f"decls: {len(decls)}")
    return {"asm": asm_text, "draft": draft, "src_rel": src_rel,
            "lineno": lineno, "asm_rel": asm_rel, "asm_file": asm_file,
            # UNtruncated length. The too-large handoff must be judged on the
            # real function, not on what survived MAX_ASM_CHARS; see the
            # deferral check.
            "asm_full": asm_full,
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
    "are the `ext` union: use the named variant from the EXT VARIANTS "
    "section (`ext.reboundStone.stoneAngle`). NEVER write `ext.ILLEGAL`; it "
    "is a placeholder, not a name, and the gate rejects it. If no named "
    "field covers the offset, say so in one line and stop: the union needs a "
    "field added, which is a header change and not yours to guess. Match the "
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
    "union: use the named field from EXT VARIANTS. If none covers the "
    "offset, report that rather than inventing an access.\n"
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
        # Reached only from the streaming degeneration detector. Guarded so it
        # can never fall through to an HTTP endpoint that is not configured
        # when running on the CLI. (This used to say the CLI has no stream to
        # watch; it has had one since Popen streaming landed.)
        return _opencode_run(f"{sys_msg}\n\n{user}")
    body = json.dumps({
        "model": _active_model(),
        "messages": [{"role": "system", "content": sys_msg},
                     {"role": "user", "content": user}],
        "temperature": 0.1, "stream": True,
        # Turn thinking OFF at the API level rather than asking nicely.
        #   chat_template_kwargs.enable_thinking -> Qwen3-family template switch
        #   reasoning_budget: 0                  -> llama.cpp server flag
        # Unknown fields are ignored by servers that do not implement them, so
        # sending both is safe and covers either build.
        **NO_THINKING,
    }).encode()
    req = urllib.request.Request(_base_url() + "/chat/completions",
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
        "model": _active_model(),
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": temperature, "stream": True,
        **thinking_params(),
    }).encode()
    req = urllib.request.Request(_base_url() + "/chat/completions",
                                 data=body,
                                 headers=_api_headers(),
                                 method="POST")

    t0 = time.time()
    # Mirrors the CLI path's ttfb: the first byte of ANY kind, reasoning
    # included, because on these models reasoning is what arrives first.
    first_byte: list[float | None] = [None]
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
                if first_byte[0] is None:
                    first_byte[0] = time.time() - t0
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
                if first_byte[0] is None:
                    first_byte[0] = time.time() - t0
                if in_reasoning:
                    sys.stdout.write("\n[output] ")
                    in_reasoning = False
                sys.stdout.write(piece)
                sys.stdout.flush()
                content.append(piece)
                n_content += 1
                # WATCH THE CONTENT STREAM, NOT JUST THE REASONING.
                #
                # The degeneration check above runs only while `n_content == 0`
                # and only over reasoning tokens. At REASONING_EFFORT=none
                # there is no reasoning, so nothing was watching anything: in
                # the 2026-08-09 battery, 16 of 54 generations ran to their
                # full timeout emitting `s32 temp661;`, a transcript of the
                # MIPS register file, or a verbatim echo of the input assembly.
                # Each burned its entire budget producing nothing.
                if n_content % CONTENT_CHECK_EVERY == 0:
                    d = _content_degenerate("".join(content))
                    if d.get("degenerate"):
                        if d.get("decl_run", 0) >= 20:
                            why = (f"declaration loop "
                                   f"({d['decl_stem']}{d['decl_run']})")
                        elif d.get("reg_decls", 0) >= 15:
                            why = (f"register-file dump "
                                   f"({d['reg_decls']} declarations)")
                        else:
                            why = f"echoing the input asm ({d['asm_echo']} lines)"
                        aborted = f"degenerate output: {why}"
                        break

    el = time.time() - t0
    text = "".join(content)
    # FORCE CONTENT OUT OF THE REASONING.
    #
    # This used to require `aborted`, i.e. the degeneration detector firing.
    # But the dominant failure is not degeneration: measured 2026-08-03, the
    # model reasons cleanly for 21,535 chars, hits `finish_reason: length`, and
    # the stream simply ENDS with content empty. Nothing aborts, so the salvage
    # never ran, and a call that had done all the analysis was thrown away.
    #
    # The trigger is now the condition that actually matters: no content, but
    # reasoning present. The model has already done the work; the second pass
    # hands its own analysis back as established fact and asks only for
    # transcription, with thinking hard-off so it cannot spend the budget
    # thinking twice.
    if not text.strip() and "".join(reason_buf).strip():
        if aborted:
            print(f"\n  !! {aborted}", flush=True)
        print(f"  --> {n_reason} reasoning tokens, 0 content. Forcing code "
              f"from its own analysis.", flush=True)
        analysis = "".join(reason_buf)[-6000:]
        text = _force_code(prompt, analysis, timeout=budget_left)
        if text.strip():
            print(f"  ++ recovered {len(text)} chars from the reasoning",
                  flush=True)
    if aborted:
        print(f"\n  !! ABORTED: {aborted}", flush=True)
    print(f"  --- done in {el:.0f}s: {n_content} content tokens, "
          f"{n_reason} reasoning tokens, {len(text)} chars ---", flush=True)
    # TELEMETRY ON THIS PATH TOO. It was only wired into the CLI branch, so the
    # first zen run produced 0 records in calls.jsonl and every fleet metric
    # had to be recovered by grepping worker logs. An instrumented backend that
    # is not instrumented on the path you actually use is not instrumented.
    emit_call({
        "model": _active_model(), "backend": MODEL_BACKEND,
        "prompt_chars": len(prompt), "total_s": round(el, 1),
        "ttfb_s": first_byte[0], "stream_chars": len(text), "rc": 0,
        "content_tokens": n_content, "reasoning_tokens": n_reason,
        "reason_cap": REASON_CAP,
        # Which lever actually produced the answer. Without this the fact that
        # 10 of 10 answers came from the force-code pass rather than from the
        # model's own content is invisible.
        "forced": bool(n_content == 0 and text.strip()),
        "outcome": ("produced" if text.strip() else
                    "empty_after_force" if n_reason else "empty"),
        "stderr_head": aborted[:200] if aborted else ""})
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
        "model": _active_model(),
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": temperature, "stream": True,
    }).encode()
    req = urllib.request.Request(_base_url() + "/chat/completions",
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
_RX_ARROW_MEMBER = re.compile(r"->\s*([A-Za-z_]\w*)")
# Some fabricated names encode the offset they stand for (`field1C`,
# `value_BC`, `unk_C`); for those the correct field can be named outright.
#
# The pattern must be NARROW. A permissive `[A-Za-z_]+_?([0-9A-Fa-f]{1,3})$`
# treats a-f as offset digits wherever they fall, so `subType` parsed as
# `subTyp` + 0x0E and `updateFunc` as `updateFun` + 0x0C, and the gate
# confidently told the model that `->updateFunc` meant `velocityY`. Wrong
# guidance is worse than none: it sends the next attempt somewhere new and
# equally wrong. So an offset is only read from a known prefix, or after an
# explicit underscore separator.
_RX_NAME_OFFSET = re.compile(
    r"^(?:field|value|val|data|word|half|byte|off|offset|member|slot|attr)"
    r"_?([0-9A-Fa-f]{1,3})$|^[A-Za-z]+_([0-9A-Fa-f]{1,3})$", re.I)
_RX_HONEST_UNK = re.compile(r"^unk[0-9A-Fa-f]{1,3}$")


def _legal_members() -> set[str]:
    """Every struct member name that exists ANYWHERE in the tree.

    Built from the whole `structs` table, not just Entity, because generated C
    legitimately touches Primitive, the ET_* ext variants and many others. A
    check scoped to Entity alone would reject correct code, and a false
    rejection costs a whole attempt.
    """
    idx = _load_index()
    out = set()
    for _name, flds in (idx.get("structs") or {}).items():
        for f in flds or []:
            n = f.get("name")
            if n:
                out.add(n)
    for _off, f in (idx.get("entity", {}).get("fields") or {}).items():
        if isinstance(f, dict) and f.get("name"):
            out.add(f["name"])
    out |= set(idx.get("ext_variants") or {})
    return out


def invented_members(code: str) -> list[str]:
    """`->name` accesses for members that exist in no struct in the tree.

    THE TOP BUILD-FAILURE CLASS. Every one becomes `structure has no member
    named X`, so catching it here turns a wasted 40s build cycle into free and
    MORE specific retry feedback: the compiler says only that the name is
    wrong, whereas this can usually say which field was meant.

    `unkNN` is deliberately NOT flagged. It is the honest form: it says "I
    could not resolve this offset", and the offset is right there in the name,
    which is far easier to fix than a confident invention like `field1C`.

    Measured against the 2026-08-09 battery: catches 20 of the fabricating
    generations with ZERO false positives across the 39 that scored clean.
    """
    legal = _legal_members()
    if not legal:
        return []                    # no index: do not guess, do not reject
    fields = _layout_fields()
    bad = sorted({n for n in _RX_ARROW_MEMBER.findall(code or "")
                  if n not in legal and not _RX_HONEST_UNK.match(n)})
    out = []
    for n in bad:
        m = _RX_NAME_OFFSET.match(n)
        hint = ""
        if m:
            try:
                off = int(m.group(1) or m.group(2), 16)
            except (ValueError, TypeError):
                off = -1
            exact = [f for f in fields if f[0] == off]
            prior = [f for f in fields if f[0] <= off]
            if exact:
                hint = f"; offset 0x{off:02X} is `{exact[0][1]}`"
            elif off >= 0 and prior:
                b = prior[-1]
                hint = (f"; 0x{off:02X} falls inside `{b[1]}` "
                        f"(0x{b[0]:02X}, {b[2]}) -- use `unk{off:02X}` if you "
                        f"cannot name it")
        if not hint:
            hint = ("; use a field from the ENTITY LAYOUT section, or "
                    "`unkNN` naming the raw offset if you cannot resolve it")
        out.append(f"`->{n}` exists in no struct in this tree{hint}")
    return out



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

    # 4b. Members that exist in NO struct in the tree. Listed before the
    #     stylistic checks because it is the only defect here that is a
    #     GUARANTEED build failure rather than a review objection.
    problems.extend(invented_members(code))

    # 4c. TYPE-AWARE member check. 4b compares against a union of every struct
    #     in the tree, so it can only see a name that exists nowhere. The first
    #     live run produced 20 build failures and 4b caught none of them:
    #     every one was a real name used on the WRONG struct. This resolves the
    #     declared type of each pointer and checks the member against that
    #     struct. Restricted to structs measured at zero false positives over
    #     2,006 known-good files; see automation/member_types.py.
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import member_types                                  # noqa: PLC0415
        problems.extend(member_types.check(code))
    except Exception:                                        # noqa: BLE001
        pass                     # never let a checker failure block a build

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

    Without this the "use the named variant" rule is unactionable: the model
    has no way to know `stoneAngle` exists, so it falls back to
    `ext.ILLEGAL.u16[0]` -- which the gate rejects, so the attempt is wasted.

    Selection is by NAME AFFINITY and that is a real weakness: a function whose
    name shares nothing with its variant gets no list at all, and then the
    prompt asks for a name it never supplied.
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
    out = ["\n=== EXT VARIANTS (the real field names for this entity) ==="]
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


def complete_function(text: str) -> str:
    """The code, if `text` contains a WHOLE function; "" otherwise.

    The gate for salvaging a timed-out stream. A partial body is worse than
    nothing: it either fails the build with an error that describes the
    truncation rather than the real problem, or -- worse -- closes by accident
    and compiles into something the model never wrote. So this is deliberately
    strict and answers only "is this definitely complete?".

    Requirements, all of them:
      - a function signature, i.e. `name(...)` followed by a `{`
      - brace balance that never goes negative and ends at exactly 0
      - the last meaningful character is `}`

    Braces inside string and char literals are ignored, because a body
    containing "}" in a message string would otherwise fail the balance check
    and a correct salvage would be thrown away.
    """
    code = clean_code(text or "")
    if not code.strip():
        return ""
    if not re.search(r"[A-Za-z_]\w*\s*\([^;]*\)\s*\{", code, re.S):
        return ""
    depth = 0
    i = 0
    n = len(code)
    while i < n:
        c = code[i]
        if c == "\\":
            i += 2
            continue
        if c in "\"'":
            quote = c
            i += 1
            while i < n and code[i] != quote:
                i += 2 if code[i] == "\\" else 1
            i += 1
            continue
        if c == "/" and i + 1 < n and code[i + 1] == "/":
            j = code.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and code[i + 1] == "*":
            j = code.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth < 0:
                return ""
        i += 1
    if depth != 0:
        return ""
    return code if code.rstrip().endswith("}") else ""


_WIDTH = {"u8": 1, "s8": 1, "u16": 2, "s16": 2, "u32": 4, "s32": 4,
          "f32": 4, "ptr": 4, "union": 4}
_LAYOUT_RX = re.compile(r"0x([0-9A-Fa-f]{1,3})\s+(\w+)\(([^)]*)\)")
_UNK_RX = re.compile(r"\bunk([0-9A-Fa-f]{1,3})\b")


def _layout_fields() -> list[tuple[int, str, str]]:
    """(offset, name, type) parsed out of the ENTITY_LAYOUT constant."""
    out = [(int(o, 16), n, t) for o, n, t in _LAYOUT_RX.findall(ENTITY_LAYOUT)]
    return sorted(out)


def resolve_unk_offsets(draft: str) -> str:
    """Pre-resolve every `->unkNN` in the m2c draft to a real field.

    THE SINGLE LARGEST CONSUMER OF REASONING. Measured with
    reasoning_audit.py over 543,873 chars captured on 2026-08-03: 34% of all
    model thinking was sentences resolving a raw offset against the layout
    table we had supplied. In prose. One offset at a time. For example:

        "half at 0x0A: not in layout as half. Layout has velocityX (0x08) and
         velocityY (0x0C) both s32. 0x0A is within velocityX? Actually
         velocityX s32 spans 0x08-0x0B, so 0x0A is the high half..."

    That is a table lookup the harness can do for free, and getting it wrong
    is what produced every build failure in that run: all 8 were "structure
    has no member named unkNN", i.e. offsets still unresolved when the
    reasoning cap fired.

    Interior offsets are called out EXPLICITLY rather than left blank. A
    silent gap is what sends the model into the paragraph above; being told
    "0x0A is inside velocityX, the asm is reading half of a word, keep unk0A
    and comment it" ends the question in one line.
    """
    if not draft:
        return ""
    fields = _layout_fields()
    # WHICH POINTER an offset was reached through decides what it means.
    # m2c emits `->unkNN` for every struct it could not type, so a table that
    # says "unk24 -> zPriority" is right for an Entity and WRONG for a
    # Primitive. Emitting that would be the harness fabricating exactly the
    # defect member_types.py exists to catch.
    #
    # MEASURED over 45 real m2c drafts (2026-08-09), 554 `->unkNN` accesses:
    #
    #     Entity *              20   3.6%
    #     another named type   473  85.4%   (void* 422, SeqStruct 26,
    #                                        Primitive 20, Collider 1, ...)
    #     undeclared            61  11.0%
    #
    # That 85% is per ACCESS and overstates the damage: the table is per
    # OFFSET, and `void *` is m2c's "could not type it", which for an entity
    # function usually IS the entity. Scored per table line over the same 45
    # drafts, 262 lines: 15 (6%) asserted an Entity field for a provably
    # different struct, 4 more were reached through a mix. On
    # func_us_801A7DC0 that is 3 wrong lines of 29, not 24.
    #
    # `void *` is the case that makes a two-way split wrong. It is not
    # "another struct", it is m2c's fallback when m2ctx did not resolve the
    # parameter, and for an entity function it usually IS the entity. So it
    # gets the translation with the uncertainty stated, rather than either a
    # confident wrong answer or nothing.
    typed_entity = set(_RX_ENTITY_PTR.findall(draft))
    declared = {v: t for t, v in _RX_ANY_PTR.findall(draft)}
    named_other = {v for v, t in declared.items()
                   if t not in ("Entity", "void") and v not in typed_entity}
    unsure = {v for v, t in declared.items() if t == "void"}
    by_off: dict[int, set[str]] = {}
    for var, h in _RX_UNK_ACCESS.findall(draft):
        by_off.setdefault(int(h, 16), set()).add(var)
    # A bare `unkNN` with no `var->` in front has no pointer to judge.
    for h in _UNK_RX.findall(draft):
        by_off.setdefault(int(h, 16), set())
    wanted = sorted(by_off)
    if not wanted:
        return ""
    lines = []
    for off in wanted:
        vs = by_off[off]
        if vs and vs <= named_other:
            ts = sorted({declared[v] for v in vs})
            lines.append(
                f"  unk{off:02X}  ->  reached only through {', '.join(sorted(vs))} "
                f"({'/'.join(ts)} *), NOT an Entity. The Entity layout does not "
                f"apply. Look 0x{off:02X} up in that struct; do NOT paste an "
                f"Entity field name here.")
    skip = {o for o in wanted if by_off[o] and by_off[o] <= named_other}
    wanted = [o for o in wanted if o not in skip]
    hedge = {o for o in wanted if by_off[o] and by_off[o] & unsure}
    # An offset reached through a MIX of pointer types (some `u8 *`, some
    # `void *`) is not a subset of named_other, so the branch above lets it
    # through and it gets a confident Entity translation. On the measurement
    # draft that is how `unk01` became "inside ->posX" while the sibling
    # offsets unk02..unk04, reached through the same `u8 *` script pointers,
    # were correctly refused. Name the offenders rather than pick a side.
    mixed = {o: sorted(by_off[o] & named_other)
             for o in wanted if by_off[o] & named_other}
    for off in wanted:
        exact = [f for f in fields if f[0] == off]
        if exact:
            _o, name, typ = exact[0]
            note = ("   [m2c typed this pointer `void *`, i.e. it does not "
                    "know. Use this only if the asm shows it is the entity]"
                    if off in hedge else "")
            lines.append(f"  unk{off:02X}  ->  ->{name}    ({typ}){note}")
            continue
        if off >= 0x7C:
            lines.append(
                f"  unk{off:02X}  ->  ext union, {off - 0x7C:#04x} bytes in. "
                f"Use the named field from EXT VARIANTS that sits at this "
                f"offset. If none does, say so; do NOT invent an access")
            continue
        prev = [f for f in fields if f[0] < off]
        if prev:
            po, pname, ptyp = prev[-1]
            w = _WIDTH.get(ptyp, 4)
            if po + w > off:
                lines.append(
                    f"  unk{off:02X}  ->  NO named field. It is INSIDE "
                    f"->{pname} (0x{po:02X}, {ptyp}, {w} bytes), so the asm is "
                    f"reading part of that word. Keep unk{off:02X} and say so "
                    f"in a comment. Do NOT invent a field.")
                continue
        lines.append(
            f"  unk{off:02X}  ->  NO named field at this offset and it is not "
            f"inside one. Keep unk{off:02X}. Do NOT invent a field.")
    if mixed:
        note = {}
        for o, vs in mixed.items():
            ts = "/".join(sorted({declared[v] for v in vs}))
            note[f"  unk{o:02X}  "] = (
                f"   [CAUTION: also reached through {', '.join(vs)} ({ts} *), "
                f"which is not an Entity. This translation applies only to the "
                f"entity accesses]")
        lines = [l + next((n for k, n in note.items() if l.startswith(k)), "")
                 for l in lines]
    return ("\n=== OFFSETS ALREADY RESOLVED FOR YOU ===\n"
            "Every `->unkNN` in the draft, resolved against the Entity layout "
            "where the pointer is actually an Entity.\nLines that say a "
            "pointer is NOT an Entity are as important as the translations: "
            "do not paste an Entity field name there.\n" + "\n".join(lines) + "\n")


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
        # Then the pre-resolved lookup. It goes LAST so it is the most recent
        # thing before the task, and it is the section that replaces 34% of
        # the model's reasoning with text it can simply read.
        entity_sec += resolve_unk_offsets(ctx.get("draft") or "")
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
                    # STEAL BY RENAME, NOT BY UNLINK.
                    #
                    # unlink was a TOCTOU: A and B both measure the same stale
                    # lock, B unlinks and creates (B legitimately holds a FRESH
                    # lock), then A unlinks -- removing B's lock -- and creates.
                    # Both then believe they hold it and both build, which is
                    # exactly what this lock exists to prevent.
                    #
                    # os.rename is atomic on one path: of two racing stealers
                    # only one can move that inode, and the loser gets an error
                    # and re-loops to find the winner's fresh lock. This is the
                    # same reasoning scheduler.py:117-123 applies to the queue
                    # lock. Found by audit 2026-08-02.
                    steal = f"{self.path}.steal.{os.getpid()}"
                    try:
                        os.rename(self.path, steal)
                        os.unlink(steal)
                        print(f"[lock] broke stale lock ({age:.0f}s old)")
                    except OSError:
                        pass          # someone else won the steal; re-loop
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
            # pid is what makes replay safe. Without it a replay cannot tell an
            # abandoned journal from one whose owner is mid-edit right now, and
            # replaying a LIVE worker's journal reverts its edit underneath it.
            json.dump({"src_rel": src_rel, "original": original,
                       "worker": WORKER_NAME, "pid": os.getpid(),
                       "at": time.time()}, f)
        os.replace(tmp, _journal_path())
    except OSError as e:
        print(f"[worker] WARNING: could not write restore journal: {e}",
              file=sys.stderr)


def journal_clear() -> None:
    try:
        os.unlink(_journal_path())
    except OSError:
        pass


def _pid_alive(pid: int) -> bool:
    """Is that process still running? Workers share one OS, so signal 0 works."""
    if not pid or pid == os.getpid():
        return pid == os.getpid()
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True          # exists, owned by someone else
    except OSError:
        return True          # unknown: assume alive, i.e. do not touch it


def replay_pending_journals() -> int:
    """Restore source left modified by a worker that died mid-edit.

    Called at worker startup, from the SIGTERM handler, and on Ctrl-C.

    IT MUST NOT TOUCH A LIVE WORKER'S JOURNAL. This used to replay every file
    in the directory unconditionally, so a worker joining a running fleet would
    revert another worker's in-flight edit: that worker then compiled the stub
    instead of its candidate, misfiled the result, and lost its crash
    protection because the journal was deleted too. With four workers and a
    staggered start that is not a rare race, it is the normal case.

    Two guards, both required:
      - skip journals whose owning pid is still alive;
      - hold BuildLock, because writing source files is exactly what that lock
        serialises. Replaying outside it can clobber a build in progress.
    """
    d = os.path.join(WIN_REPO, "automation", "logs", "pending")
    if not os.path.isdir(d):
        return 0
    n = 0
    with BuildLock(os.path.join(WIN_REPO, "automation", ".build.lock")):
        for name in sorted(os.listdir(d)):
            if not name.endswith(".json"):
                continue
            full = os.path.join(d, name)
            try:
                with open(full, encoding="utf-8") as f:
                    j = json.load(f)
                owner = int(j.get("pid") or 0)
                if owner and owner != os.getpid() and _pid_alive(owner):
                    print(f"[worker] leaving {name}: owner pid {owner} is "
                          f"still running", file=sys.stderr)
                    continue
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


_CI_MOD = None
_IDX_JSON = None


def _load_index_json() -> dict:
    """automation/index.us.json, parsed once per process.

    It is ~7.6 MB. shim_gate used to re-read and re-parse it on every call, so
    a sweep over all 1253 stage files spent minutes in json.load and never
    finished. The worker calls shim_gate once per record, so this also saves
    the fleet a full parse per function.
    """
    global _IDX_JSON
    if _IDX_JSON is None:
        with open(os.path.join(WIN_REPO, "automation", "index.us.json"),
                  encoding="utf-8") as f:
            _IDX_JSON = json.load(f)
    return _IDX_JSON


def _codebase_index_module():
    global _CI_MOD
    if _CI_MOD is None:
        import importlib.util
        p = os.path.join(WIN_REPO, "automation", "codebase_index.py")
        spec = importlib.util.spec_from_file_location("codebase_index", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _CI_MOD = m
    return _CI_MOD


_SEG_CACHE: dict = {}


def _c_segment_sizes(stage: str) -> dict:
    """{stem: text size} for one overlay, from its splat config.

    A segment's size is the distance to the next `c` segment, which is exactly
    the compiled text for that file. That makes it directly comparable across
    overlays implementing the same shared header.
    """
    if stage in _SEG_CACHE:
        return _SEG_CACHE[stage]
    out: dict = {}
    path = os.path.join(WIN_REPO, "config", f"splat.us.st{stage}.yaml")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = [ln for ln in f.read().splitlines() if ", c, " in ln]
        for i, ln in enumerate(lines):
            addr = int(ln.split("[")[1].split(",")[0], 16)
            name = ln.split(", c, ")[1].split("]")[0].strip()
            if i + 1 < len(lines):
                nxt = int(lines[i + 1].split("[")[1].split(",")[0], 16)
                out[name] = nxt - addr
    except (OSError, ValueError, IndexError):
        pass
    _SEG_CACHE[stage] = out
    return out


# How far a stage's text may diverge from its peers' and still plausibly BE the
# same implementation. Peers differ a little for real reasons (inverted-castle
# sign flips, a different ANIMSET bank), so the band is not tight; it only has
# to separate "same code" from "different code".
_SHIM_SIZE_LO, _SHIM_SIZE_HI = 0.75, 1.25


def shim_size_divergence(stage: str, stem: str, idx: dict) -> str:
    """Is this stage's text a plausible size for the shared implementation?

    THIS IS THE BLOCKER shim_viable() DOES NOT HAVE. It checks placement only:
    segments, .data, .bss. It never asks whether the stage's function is the
    SAME CODE. So it happily reported "no known blocker" for
    src/st/rchi/e_breakable.c, a file whose own comment reads "RCHI's breakable
    entity is stage-specific and roughly twice the size of the shared candle
    implementation (0x270 versus 0x134 bytes)" -- a rejection upstream had
    already investigated and recorded.

    Measured 2026-08-02 against the peer median for each shared header:

        rchi/e_breakable     0x674 vs 0x134   5.36x   different code
        rno0/e_lock_camera   0x1bc vs 0x4cc   0.36x   different code
        rno0/e_breakable     0x170 vs 0x134   1.19x   plausible

    Both directions matter and the too-SMALL case is the one a naive check
    misses: rno0's lock camera is a third of its peers', which is no more
    shimmable than rchi's being five times larger.

    Returns "" when the size is plausible, otherwise the reason to block.
    """
    mine = _c_segment_sizes(stage).get(stem)
    if not mine:
        return ""      # no segment of its own; nothing measurable, stay silent
    peers = []
    for p in idx.get("shared_impls", {}).get(stem, {}).get("shimmed_by", []):
        s = _c_segment_sizes(p).get(stem)
        if s:
            peers.append(s)
    if len(peers) < 2:
        return ""      # too few peers for a median to mean anything
    peers.sort()
    med = peers[len(peers) // 2]
    if not med:
        return ""
    ratio = mine / med
    if _SHIM_SIZE_LO <= ratio <= _SHIM_SIZE_HI:
        return ""
    how = "larger" if ratio > 1 else "smaller"
    return (f"{stage}'s {stem} text is {mine:#x} bytes against a peer median of "
            f"{med:#x} ({ratio:.2f}x, {how}). That is a different "
            f"implementation, not a placement problem, so shimming it would "
            f"change behaviour. shim_viable() cannot see this: it checks "
            f"segments and storage, never whether the code is the same")


_STATIC_DEF_RX = re.compile(
    r"^[ \t]*static\b[^;()\n]*?\b(\w+)\s*(?:\[[^\]]*\])?\s*=", re.M)


def shim_needs_stage_data(stage: str, stem: str, idx: dict) -> str:
    """Does shimming this header oblige the STAGE to supply data tables?

    THE SECOND BLIND SPOT in shim_viable(). Its blocker 4 asks whether the
    HEADER defines initialised file-scope data. Several shared headers define
    none, yet still consume tables that each stage must define itself:

        src/st/e_breakable.h reads g_eBreakableAnimations, g_eBreakableHitboxes,
        g_eBreakableExplosionTypes, g_eBreakableanimSets and blend_modes, and
        defines not one of them. Every stage that shims it declares its own
        `static` tables above the #include.

    Those tables are .data belonging to <stem>, so the stage needs a
    '.data, <stem>' splat segment exactly as e_red_door did. rno0 has only
    '[0x364E4, c, e_breakable]' and no data segment, so shimming it would emit
    the tables into the unnamed blob and shift everything after them.

    Detected from the PEERS rather than guessed: read the .c of stages that
    already shim this header and see whether they define static file-scope data
    before the include. If they must, so must this stage.

    Returns "" when there is no obligation, otherwise the reason to block.
    """
    segs = (idx.get("splat_segments", {}).get(f"st{stage}")
            or idx.get("bss_segments", {}).get(f"st{stage}") or {})
    if stem in (segs.get("named_data") or {}):
        return ""                      # already has its own .data segment
    peers = idx.get("shared_impls", {}).get(stem, {}).get("shimmed_by", [])
    for p in peers[:6]:                # a handful is plenty; these all agree
        path = os.path.join(WIN_REPO, "src", "st", p, f"{stem}.c")
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        names = _STATIC_DEF_RX.findall(text)
        if names:
            return (f"shimming {stem} obliges {stage} to define the stage data "
                    f"tables the header consumes ({', '.join(sorted(set(names))[:4])}"
                    f"...), as src/st/{p}/{stem}.c does, but {stage} has no "
                    f"'.data, {stem}' splat segment to pin them. shim_viable() "
                    f"misses this: it checks whether the HEADER defines data, "
                    f"not whether the header REQUIRES the stage to")
    return ""


def shim_gate(ctx: dict) -> tuple[bool, str]:
    """Should this record be SHIMMED instead of generated? (P6)

    `shim_viable()` in codebase_index.py already answered this; it just
    informed a human. Asking it here stops the fleet spending model quota
    writing a private copy of code the tree already has, which the quality
    audit then flags as a duplicate and a reviewer then rejects.

    MEASURED over the 417 INCLUDE_ASM stubs in src/st before this was wired:

        288  no shared implementation      -> generating is correct
        121  shared impl exists, BLOCKED   -> generating is the only option today
          8  shimmable NOW, no blocker     -> generating is simply wrong work

    Only the last group is deferred, and that is a deliberate narrowing of
    ROADMAP P6's wording. Deferring the 121 blocked records too would stall 29%
    of the queue behind structural work that has no automated consumer, which
    trades a small waste for a large stall. They are annotated instead, so the
    blocker is visible on the record without blocking the record.

    Returns (defer, reason). Never raises: a broken advisory check must not
    take the fleet down.
    """
    try:
        parts = ctx.get("src_rel", "").split("/")
        # Only src/st/<stage>/<stem>.c has a shared-implementation notion.
        if len(parts) != 4 or parts[0] != "src" or parts[1] != "st":
            return False, ""
        stage, stem = parts[2], parts[3][:-2]
        # Different BUILD TARGET, not a us overlay. shim_viable reasons from
        # config/splat.us.* and config/check.us.sha, neither of which describes
        # these, so any verdict it returns about them is unfounded. The us
        # oracle cannot verify a psp or saturn change either, so deferring one
        # would park a record on evidence we do not have.
        if any(t in stage for t in ("_psp", "_saturn", "psp", "saturn")):
            return False, ""
        ci = _codebase_index_module()
        idx = _load_index_json()
        if not idx.get("shared_impls", {}).get(stem):
            return False, ""          # nothing to defer to; generate
        ok, why = ci.shim_viable(stage, stem, idx)
        if ok:
            # shim_viable said placement is fine. Ask the question it does not:
            # is this even the same code?
            diverged = shim_size_divergence(stage, stem, idx)
            if diverged:
                return False, f"shared impl exists but blocked: {diverged}"
            needs = shim_needs_stage_data(stage, stem, idx)
            if needs:
                return False, f"shared impl exists but blocked: {needs}"
            return True, (
                f"src/st/{stem}.h is a shared implementation and {stage} has no "
                f"blocker against using it ({why}). The correct fix is a shim, "
                f"not a generated copy: replace this file's body with "
                f'`#include "../{stem}.h"`. Generating C here would duplicate '
                f"tree code and be rejected in review.")
        return False, f"shared impl exists but blocked: {why}"
    except Exception as e:
        print(f"  ~~ shim gate unavailable, ignored: {type(e).__name__}",
              flush=True)
        return False, ""


# P4. review_checks.py has always been able to catch these; it just ran after
# the fact, for a human. Wiring the SAME functions in (rather than
# reimplementing them here) means a check can never drift between the two
# callers, and each keeps its own founding-bug fixture in review_checks'
# self_test.
#
# Excluded on purpose, per ROADMAP P4 and MATCHING-LESSONS section 20:
#   angle, argn  - "same as X except Y" comments that understate a real
#                  difference, and descriptive parameter names replaced by
#                  argN. Both need a reader to judge; as automatic gates they
#                  would reject good code.
#   comment, block - they compare against a PREVIOUS C version of the function.
#                  Before apply the file still holds the INCLUDE_ASM stub, so
#                  there is no prior text to have lost. They stay a review-time
#                  check, where that comparison is meaningful.
_REVIEW_GATE_CHECKS = ("linkage", "ext", "static", "signature", "stub")

_REVIEW_MOD = None


def _review_checks_module():
    global _REVIEW_MOD
    if _REVIEW_MOD is None:
        import importlib.util
        p = os.path.join(WIN_REPO, "automation", "review_checks.py")
        spec = importlib.util.spec_from_file_location("review_checks", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _REVIEW_MOD = m
    return _REVIEW_MOD


def virtual_apply(ctx: dict, fn: str, code: str) -> str:
    """The file as it WOULD look after apply_code, without writing anything.

    The checks need whole-file context: linkage has to see which functions the
    file declares static, ext has to see every ext access in the function's
    neighbourhood. Running them on the bare candidate would miss both.

    Kept deliberately in lockstep with apply_code's substitution. If that
    pattern changes and this does not, the gate silently starts inspecting the
    unmodified file and passes everything, so test_review_gate.py asserts the
    candidate actually appears in the result.
    """
    with open(win_path(ctx["src_rel"]), encoding="utf-8", errors="replace") as f:
        original = f.read()
    pattern = re.compile(
        r'^[ \t]*INCLUDE_ASM\(\s*"' + re.escape(ctx["asm_rel"]) +
        r'"\s*,\s*' + re.escape(fn) + r'\s*\);[ \t]*(?=\r?$)', re.M)
    if not pattern.search(original):
        return ""      # stub not found; apply_code will raise with a real message
    return pattern.sub(lambda _m: code.replace("\r\n", "\n"), original, count=1)


def review_gate(ctx: dict, fn: str, code: str) -> list[str]:
    """Reviewer-perspective defects, as a PRE-BUILD gate.

    The linkage check is the reason this runs before the build rather than
    after: it predicts a link error that the build would otherwise take minutes
    to surface, and it catches the specific mistake that a source grep cannot.
    Adding `static` to StepTowards broke the link once precisely because its
    callers were INCLUDE_ASM stubs in a sibling .c, invisible to grep and fully
    visible to the linker.

    Never raises. A crash in an advisory check must not fail a good candidate.
    """
    try:
        src = virtual_apply(ctx, fn, code)
        if not src:
            return []
        rc = _review_checks_module()
        path = Path(win_path(ctx["src_rel"]))
        out = []
        for key in _REVIEW_GATE_CHECKS:
            fnc = rc.CHECKS.get(key)
            if fnc is None:
                continue
            try:
                for f in fnc(path, src):
                    # Only the function under generation. The file may contain
                    # pre-existing findings in code this worker did not write,
                    # and failing an attempt for those would make the record
                    # unmatchable forever.
                    if f.get("function") and f["function"] != fn:
                        continue
                    out.append(f"{f['check']}: {f['detail']}. FIX: {f['fix']}")
            except Exception as e:
                print(f"  ~~ review check {key} errored, ignored: "
                      f"{type(e).__name__}", flush=True)
        return out
    except Exception as e:
        print(f"  ~~ review gate unavailable, ignored: {type(e).__name__}",
              flush=True)
        return []


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


_COMPILE_FAIL_MARKS = (
    "FAILED:",              # ninja's failed-target block
    "undefined reference",  # link error
    ": error",              # some tools do emit this
)
# GCC 2.7 (cc1-psx-26) writes `file.c:LINE: message` with NO "error:" keyword,
# e.g.  src/boss/bo0/2D26C.c:133: structure has no member named `unk32'
#
# The negative lookahead is LOAD-BEARING. Warnings share that exact shape:
#   src/st/rno0/e_misc.c:88: warning: unused variable `i'
# Without it, a build that COMPILED FINE and merely produced a warning was
# classified as a build failure, which is the precise misrouting this function
# exists to prevent: the record goes to `escalated` instead of `near`, and
# save_candidate() never runs, so the permuter seed is silently discarded.
# GCC 2.7 emits plenty of warnings on this codebase, so this was not academic.
_DIAG_RX = re.compile(r"[^\s]+\.(?:c|h):\d+:(?!\s*warning:)")


def build_failed_to_compile(rc: int, out: str) -> bool:
    """Did the BUILD fail, as opposed to the checksum merely mismatching?

    THIS DISTINCTION IS THE WHOLE POINT. `make build` runs the `check` target
    itself, so a perfectly good compile whose bytes differ still exits non-zero.
    Treating rc != 0 as "build failed" therefore collapsed two outcomes that
    have different owners:

      - never compiled   -> escalated, needs a better model or a human
      - compiled, bytes differ -> near, needs the PERMUTER, costs no tokens

    Everything downstream keys off this, and it was wrong. Observed 2026-08-02
    on func_us_8019AA04: every overlay printed OK, the only failure line was
    `check: checksum check failed`, and the worker still recorded BUILD FAILED.
    That is why four `near` records had to be retriaged BY HAND on 2026-08-01
    with notes reading "misrouted... the tree BUILT and only the checksum
    differed". The hand-fix was applied to the records; the cause was here.

    Deliberately conservative: anything that looks like a compiler diagnostic,
    a ninja FAILED block or a link error counts as a real build failure. Only a
    non-zero exit with NO such evidence is reclassified as a checksum miss, so
    a genuinely broken compile can never be mistaken for a permuter candidate.
    """
    if rc == 0:
        return False
    if any(m in out for m in _COMPILE_FAIL_MARKS) or _DIAG_RX.search(out):
        return True
    # Non-zero, no diagnostics. If make explicitly says the checksum failed,
    # the build itself was fine.
    return "checksum check failed" not in out


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
        really_broken = build_failed_to_compile(rc, out)
        st.update("compiled" if rc == 0 else
                  "BUILD FAILED" if really_broken else
                  "compiled, checksum differs")
    if really_broken and not build_error_is_ours(out, rec):
        # The build broke, but nothing in the diagnostics names our file or our
        # overlay. A C edit inside one overlay cannot break another overlay's
        # link, so this is a dirty tree (a concurrent worker mid-apply, or a
        # stale artifact), not a defect in this candidate.
        #
        # Escalating on it is worse than useless: the record is retired with a
        # note full of some other overlay's linker output and never judged on
        # its merits again. Audit 2026-08-02 found NINE records escalated this
        # way, all quoting stnp3, stnz0 or weapon0 failures for functions in
        # bo0, bo6 and rno0. Report it as a retryable condition instead.
        st.update("build dirty, not ours")
        return False, ("BUILD DIRTY: the build failed but no diagnostic names "
                       f"{rec['function']}, its source file, or overlay "
                       f"{rec['overlay']}. Treating as a dirty tree, not a "
                       "defect in this candidate.\n" + out.strip()[-800:])
    if really_broken:
        return False, "BUILD FAILED:\n" + out.strip()[-1500:]
    if rc != 0:
        # Compiled and linked; make only exited non-zero because its own `check`
        # target found the wrong bytes. The string must NOT contain "BUILD
        # FAILED": the near/escalated routing and the permuter-seed save both
        # test for exactly that substring.
        return False, ("BUILT, CHECKSUM MISMATCH (compiled and linked; bytes "
                       "differ) - permuter candidate:\n" + out.strip()[-1200:])
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
    global _CURRENT_CLAIM, _CURRENT_CLAIM_FROM
    _CURRENT_CLAIM = rec["id"]
    # scheduler.py records this when it claims; older records predate it.
    _CURRENT_CLAIM_FROM = rec.get("claimed_from") or "todo"
    fn = rec["function"]
    print(f"[worker] {rec['id']}")

    located = find_source(fn, rec.get("overlay"))
    if not located:
        sched("report", "--id", rec["id"], "--status", "escalated",
              "--notes", "INCLUDE_ASM stub not found")
        return True
    print(f"[worker] target {located[0]}:{located[1]}")

    ctx = prepare(rec, located)
    # Judge the TRUE size, not the truncated one.
    #
    # This used to read `len(ctx["asm"])`, which prepare() has already clipped
    # to MAX_ASM_CHARS (12000). On the cli backend MAX_FUNC_CHARS is 20000, so
    # the condition could never be true: the tier never deferred anything for
    # size, and instead silently decompiled the first 12000 chars of arbitrarily
    # large functions. Found by audit 2026-08-02.
    _asm_size = ctx.get("asm_full") or len(ctx["asm"])
    if _asm_size > MAX_FUNC_CHARS and not dry:
        print(f"[worker] SKIP: {_asm_size} chars of asm exceeds "
              f"MAX_FUNC_CHARS={MAX_FUNC_CHARS}; too large for this tier")
        sched("report", "--id", rec["id"], "--status", "deferred",
              "--notes", f"{DEFER_TOO_LARGE}: asm {_asm_size} chars > "
                         f"{MAX_FUNC_CHARS} on backend={MODEL_BACKEND}; "
                         f"handed off to the next tier")
        return True
    # P6. Ask BEFORE the model, not after: a record whose right answer is a
    # shim must never cost a generation. The blocked-but-not-shimmable case is
    # only annotated, so it stays workable; see shim_gate's docstring.
    _defer, _why = shim_gate(ctx)
    if _defer and not dry:
        print(f"[worker] SHIM INSTEAD: {_why}", flush=True)
        sched("report", "--id", rec["id"], "--status", "deferred",
              "--notes", (DEFER_SHIMMABLE + ": " + _why)[:250])
        return True
    if _why and not dry:
        print(f"  ~~ {_why}", flush=True)
        # RECORD it, do not just print it. shim_gate's docstring said the
        # blocker was noted on the record; it was only ever written to
        # automation/logs/, which is gitignored and periodically archived. So
        # the one piece of structural analysis the gate produces -- exactly
        # which segment a stem is missing -- was thrown away every run, and had
        # to be rediscovered by hand each time. Found by audit 2026-08-02.
        #
        # Status stays `todo`: this is an annotation, not a routing decision.
        # The record is still workable by the fleet.
        try:
            sched("report", "--id", rec["id"], "--status", "todo",
                  "--notes", ("SHIM_BLOCKED: " + _why)[:250])
        except Exception as e:      # noqa: BLE001
            print(f"  ~~ could not record shim blocker: {type(e).__name__}",
                  flush=True)

    if dry:
        print("--- prompt preview ---")
        print(build_prompt(rec, ctx)[:1500])
        sched("report", "--id", rec["id"], "--status", "todo")
        return True

    original, feedback, best = None, "", "no attempt completed"
    # The last BUILD verdict, kept apart from `best`.
    #
    # `best` is last-writer-wins and every generation failure overwrites it, so
    # a function that produced C, failed to build, and then timed out on a later
    # attempt was filed with the note "attempt 4 timed out". That hides the only
    # useful fact (it reached the compiler and what the compiler said) behind
    # the least useful one, and it is why several escalated records read like
    # generation failures when they are really build failures.
    best_build = ""
    # Did ANY attempt produce C that compiled and merely missed on bytes?
    # That is a fundamentally different outcome from "never built", and it
    # decides where the record is routed when the attempts run out. See the
    # status choice at the end of this function.
    compiled_once = False
    seed_path = ""          # permuter seed written by the last compiling attempt
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
            # P4: the same checks a reviewer would apply, now BEFORE the build.
            # Appended rather than merged so a review finding reads distinctly
            # in the retry feedback and in the log.
            defects += review_gate(ctx, fn, code)
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
                    # DISCARD THE CRASH JOURNAL. This is not tidy-up; omitting
                    # it destroys the match.
                    #
                    # journal_write() saved the PRE-EDIT file (the INCLUDE_ASM
                    # stub) before applying. journal_clear() used to be called
                    # from exactly one place, restore(), which the match path
                    # deliberately does NOT take because a match must keep its
                    # edit. So after every success the journal survived holding
                    # the stub, and replay_pending_journals() -- which runs at
                    # worker startup, on SIGTERM and on Ctrl-C -- would write
                    # that stub back over the matched function while the queue
                    # still recorded `matched` with machine proof.
                    #
                    # Clearing here, after the report, is the right moment: the
                    # applied content is now the intended state, so there is
                    # nothing left to recover.
                    journal_clear()
            best = best_build = detail
            if matched:
                return True
            feedback = detail
            if "BUILD FAILED" not in detail:
                compiled_once = True
                # Save BEFORE collecting the diff. asm-differ is a subprocess
                # that can time out or be killed, and losing the seed to a
                # feedback step that is only advisory would be absurd.
                #
                # A later compiling attempt overwrites an earlier one on
                # purpose: retries carry asm-differ feedback the first attempt
                # never had, so the last one to compile is the closest.
                seed_path = save_candidate(rec, code, attempt, detail, ctx) or seed_path
                if seed_path:
                    print(f"  -> permuter seed saved: {seed_path}", flush=True)
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
            # The note must name the seed FILE, not just assert one exists.
            # The old note said "candidate for permuter" and pointed at nothing,
            # so a later reader could not tell whether a seed had ever been
            # written, and in fact none had.
            where = f" seed={seed_path}" if seed_path else " seed=NONE(save failed)"
            sched("report", "--id", rec["id"], "--status", "near",
                  "--score", "50", "--tier", "0",
                  "--add-iters", str(attempt),
                  "--notes", ("compiled, byte mismatch; permuter candidate."
                              + where + " " + best)[:250])
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
                  # Prefer the BUILD verdict. A later generation timeout must
                  # not be what an escalated record is filed under; the
                  # compiler's message is the only actionable part.
                  "--score", "0", "--tier", "0",
                  # Count the attempt. --add-iters had ZERO call sites, so
                  # `iterations` was permanently 0 and nothing could ever brake
                  # a requeue loop or tell a first attempt from a fifth.
                  "--add-iters", str(attempt),
                  "--notes", (best_build or best)[:250])
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

    # Artifact-name sanity, on every start.
    #
    # This used to be a function with ZERO call sites: it was written as a
    # diagnostic and then never wired in, which is the worst of both worlds,
    # because the defect it detects is already silent. An overlay whose artifact
    # name is missing from the oracle is not "failing", it is permanently
    # unmatchable, and every attempt on it looks like an ordinary hash mismatch.
    # A check nobody runs cannot catch that; found by audit 2026-08-02.
    #
    # Read-only, a few milliseconds, and it warns rather than exits: a stale
    # entry here must not be able to stop a fleet that is otherwise fine.
    try:
        _bad = audit_artifact_mapping()
        for _line in _bad:
            print(f"[worker] WARNING unmatchable overlay: {_line}",
                  file=sys.stderr)
    except OSError as e:
        print(f"[worker] artifact audit skipped: {e}", file=sys.stderr)

    if a.cmd == "preflight":
        # Machine-readable so the connector can gate a fleet launch on it.
        try:
            if MODEL_BACKEND == "cli":
                r = opencode_preflight()
            else:
                r = {"ok": True, "backend": MODEL_BACKEND, "url": _base_url(),
                     "note": f"{MODEL_BACKEND} backend is checked "
                             f"per-request, not here"}
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
