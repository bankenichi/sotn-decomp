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
OPENCODE_MODEL = os.environ.get("OPENCODE_MODEL", "opencode/big-pickle")
# Optional: point at a running `opencode serve` to skip MCP cold-boot per call.
OPENCODE_ATTACH = os.environ.get("OPENCODE_ATTACH", "").strip()
# Tool-less agent defined in automation/opencode/opencode.json. Must be used, or
# opencode run defaults to the tool-enabled "build" agent and explores the repo.
OPENCODE_AGENT = os.environ.get("OPENCODE_AGENT", "raw")


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
    would be mangled or worse by a shell. Linux argv limits are ~2MB and prompts
    here run well under 20KB, so passing it directly is safe.
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
    argv = ["opencode", "run", "--model", OPENCODE_MODEL,
            "--agent", OPENCODE_AGENT, "--auto"]
    if OPENCODE_ATTACH:
        argv += ["--attach", OPENCODE_ATTACH]
    argv.append(prompt)
    print(f"  --- opencode run ({OPENCODE_MODEL}, prompt {len(prompt)} chars) ---",
          flush=True)
    t0 = time.time()
    # stdin=DEVNULL is REQUIRED, not tidiness. capture_output only redirects
    # stdout/stderr; stdin stays inherited. Run from a terminal that is fine,
    # but opencode probes stdin when it is not a TTY and then blocks forever
    # waiting for input nobody will send. Symptom: identical 600s timeouts on
    # every prompt while the same command typed by hand returns instantly.
    # Cap at the caller's remaining budget, not the flat GEN_TIMEOUT.
    # Without this an attempt starting with 5s of budget left still ran
    # the full 600s, so FUNC_BUDGET overshot by ~7 minutes per attempt.
    _to = GEN_TIMEOUT if timeout is None else max(15.0, min(GEN_TIMEOUT, timeout))
    p = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=_to, cwd=WIN_REPO,
                       stdin=subprocess.DEVNULL)
    out = p.stdout or ""
    err = (p.stderr or "").strip()
    if p.returncode != 0:
        raise RuntimeError(
            f"opencode run failed (rc={p.returncode}): {err[:800]}")
    print(f"  --- done in {int(time.time() - t0)}s: {len(out)} chars ---",
          flush=True)
    # rc=0 with EMPTY stdout is a real failure wearing a success mask. opencode
    # writes its decorative header AND its errors to stderr, so quota exhaustion,
    # rate limiting and model errors all look like a clean exit with no answer.
    # Discarding stderr here meant three attempts burned 22 minutes producing
    # "0 chars" with no clue why. Surface it.
    if not out.strip():
        # Empty output is TRANSIENT, not fatal. Observed repeatedly: rc=0, no
        # stderr error, just nothing, after 400-480s. It correlates with larger
        # prompts (2636/3072/4285 chars failed; 2367-2686 succeeded), so it looks
        # like a gateway-side limit or drop rather than a model refusal.
        #
        # Previously this raised, which escalated the whole FUNCTION on the first
        # occurrence and threw away the remaining attempts. Retry the call
        # instead, and only give up after RATE_LIMIT_RETRIES tries.
        raise _EmptyOutput(
            f"rc=0 but NO output after {int(time.time() - t0)}s "
            f"(prompt {len(prompt)} chars). stderr: {err[:300]}")
    # The CLI prefixes a decorative status line like "> build - big-pickle".
    # clean_code() already discards leading non-C prose, so no special handling
    # is needed here; returning raw output keeps this backend dumb on purpose.
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
MAX_FUNC_CHARS = int(os.environ.get("MAX_FUNC_CHARS", "6000"))
# Hard wall-clock ceiling for one function across ALL attempts. Without it,
# MAX_ATTEMPTS forced passes at GEN_TIMEOUT each can silently burn ~40 minutes.
FUNC_BUDGET = float(os.environ.get("FUNC_BUDGET", "900"))
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
    raw = sched("next", "--worker", WORKER_NAME)
    line = [l for l in raw.splitlines() if l.strip().startswith("{")]
    if not line:
        return None
    rec = json.loads(line[-1])
    return None if rec.get("status") == "empty" else rec


# ---- locating the target -----------------------------------------------------

_INDEX: dict[str, tuple[str, int, str]] | None = None
RX_INC = re.compile(r'INCLUDE_ASM\(\s*"([^"]+)"\s*,\s*([A-Za-z0-9_]+)\s*\)')


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


def overlay_artifact(rec: dict) -> str:
    """build/<v>/<NAME>.BIN for this overlay, as it appears in check.<v>.sha."""
    name = rec["overlay"].split("/")[-1].upper()
    return f"build/{rec['build']}/{name}.BIN"


# ---- context preparation (all mechanical, harness-side) ----------------------

def prepare(rec: dict, located) -> dict:
    src_rel, lineno, asm_rel = located
    asm_file = asm_rel_path(rec, asm_rel)
    fn = rec["function"]

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
    print(f"[prep] draft: {len(draft)} chars, asm: {len(asm_text)} chars")
    return {"asm": asm_text, "draft": draft, "src_rel": src_rel,
            "lineno": lineno, "asm_rel": asm_rel, "asm_file": asm_file}


# ---- the model call (single shot, no tools) ---------------------------------

SYSTEM = (
    "You are an expert MIPS decompiler for Castlevania: Symphony of the Night "
    "(PSX, GCC 2.7.2). You are given MIPS assembly and a rough m2c draft. "
    "Return ONE complete C function that compiles to identical machine code.\n"
    "Rules: emit ONLY C, with no markdown fences and no prose before or after "
    "it. Use the project's real types (Entity*, Primitive*, s16/s32/u8/u16) "
    "instead of the draft's '?' placeholders. Do not invent helper functions. "
    "Keep the exact function name given.\n"
    "ANNOTATE THE CODE. 'No prose' means no text outside the C; it does NOT "
    "mean no comments. A matching decompilation that nobody can read is worth "
    "very little, and comments and local variable names cannot change the "
    "generated machine code, so they are free:\n"
    "- Put a short comment above the function saying what it does, in terms of "
    "  game behaviour where you can infer it (what entity, what state, what "
    "  effect), not a restatement of the C.\n"
    "- Name locals for their meaning: 'angle', 'distance', 'prim', 'timer'. "
    "  Never keep m2c artefacts like arg0, var_a0, temp_v1, phi_a1.\n"
    "- Comment any line whose reason is not obvious: a magic constant, a shift "
    "  used as a divide, a fixed-point scale, a deliberate signed/unsigned "
    "  choice, or a field accessed by raw offset.\n"
    "- If you are unsure what something does, say so in the comment rather "
    "  than inventing a confident explanation. 'unclear, possibly a cooldown' "
    "  is useful; a wrong claim stated firmly is worse than none."
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
    return (
        f"Function: {rec['function']}   (overlay {rec['overlay']}, build {rec['build']})\n"
        f"{fb}\n=== MIPS ASSEMBLY ===\n{ctx['asm']}\n\n"
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
        rc, out = wsl(f"make build VERSION={rec['build']} 2>&1 | tail -40",
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
              "--notes", f"asm {len(ctx['asm'])} chars > {MAX_FUNC_CHARS}; "
                         f"needs a stronger tier")
        return True
    if dry:
        print("--- prompt preview ---")
        print(build_prompt(rec, ctx)[:1500])
        sched("report", "--id", rec["id"], "--status", "todo")
        return True

    original, feedback, best = None, "", "no attempt completed"
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
            raw = llama_echo(build_prompt(rec, ctx, feedback),
                             budget_left=min(ATTEMPT_BUDGET,
                                             _deadline - time.time()))
            code = clean_code(raw)
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

            # --- critical section: one worker at a time touches the tree ---
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
            best = detail
            if ok:
                print(f"[worker] MATCHED {fn}")
                sched("report", "--id", rec["id"], "--status", "matched",
                      "--score", "100", "--tier", "0",
                      "--proof", detail[:200], "--notes", detail[:200])
                return True
            feedback = detail
            if "BUILD FAILED" not in detail:
                with Status("asm-differ (collecting feedback)"):
                    feedback += "\n\nDIFF:\n" + diff_feedback(rec)
            for dl in detail.splitlines()[:6]:
                print(f"    | {dl[:110]}")
        if original is not None:
            restore(ctx, original)
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
    a = ap.parse_args()

    if not os.path.isdir(WIN_REPO):
        print(f"repo not found: {WIN_REPO}", file=sys.stderr); return 1

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
