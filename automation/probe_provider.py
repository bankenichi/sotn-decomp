#!/usr/bin/env python3
"""Is the provider acknowledging our requests at all?

WHY THIS EXISTS
    Instrumented run, 2026-08-03: 11 of 11 calls produced ZERO bytes, and the
    stderr we now capture held nothing but opencode's own startup banner:

        > raw . deepseek-v4-flash-free

    So `opencode run` starts, announces the model, and then goes silent until
    we kill it. No error, no refusal, no rate-limit message. That is all the
    CLI is willing to tell us, and it is not enough: it cannot distinguish

        A. the request never reached the provider
        B. the provider accepted it and never replied
        C. the provider replied with an error the CLI swallowed
        D. the provider replied fine and the CLI failed to relay it

    Those need completely different fixes and the CLI cannot separate them.

WHAT THIS DOES INSTEAD
    Talks to the endpoint directly. The provider is a plain OpenAI-compatible
    server (`https://opencode.ai/zen/v1` per automation/opencode/opencode.json),
    so a single HTTP request answers the question the CLI cannot:

      * does the socket connect, and how fast
      * what HTTP status comes back
      * what headers (rate-limit and retry-after headers, if any)
      * what body, verbatim, including an error envelope
      * how long until the FIRST BYTE of the response

    It also runs `opencode run` with debug logging so the CLI's own view of the
    same exchange can be compared against the raw one.

SAFETY
    - Sends TINY prompts ("reply with the word ok"), not decompilation work.
    - Touches neither the queue, nor src/, nor the build. Writes only to
      automation/logs/probe-*.json.
    - Refuses to run while fleet workers are alive, so it cannot contend with
      a real run or be blamed for one.

Usage:
    python3 automation/probe_provider.py                  # http + cli, 1 model
    python3 automation/probe_provider.py --all-models
    python3 automation/probe_provider.py --repeat 5
    python3 automation/probe_provider.py --http-only
    python3 automation/probe_provider.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "automation" / "opencode" / "opencode.json"
OUT_DIR = REPO / "automation" / "logs"

# Headers opencode itself sends. ZEN-FREE-MODELS.md records that Zen identifies
# clients this way and treats requests without it as anonymous, so a probe that
# omitted them would be measuring a different service than the fleet uses.
CLIENT_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "opencode/1.18.12",
    "x-opencode-client": "cli",
}

# Anything that looks like a credential is replaced before it can reach a log
# file or this tool's stdout.
_SECRET = re.compile(
    r"(?i)(bearer\s+|sk-|api[_-]?key[\"'\s:=]+)[A-Za-z0-9_\-\.]{8,}")


def redact(text: str) -> str:
    return _SECRET.sub(lambda m: m.group(1) + "<redacted>", text or "")


def load_config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def base_url(cfg: dict) -> str:
    try:
        return (cfg["provider"]["opencode"]["options"]["baseURL"]).rstrip("/")
    except (KeyError, TypeError):
        return "https://opencode.ai/zen/v1"


def models(cfg: dict) -> list[str]:
    try:
        return sorted(cfg["provider"]["opencode"]["models"].keys())
    except (KeyError, TypeError):
        return []


def fleet_alive() -> list[int]:
    """PIDs of live workers. This probe must not run alongside them."""
    out = []
    pid_dir = REPO / "automation" / "logs"
    for f in pid_dir.glob("worker-*.pid"):
        try:
            pid = int(f.read_text().strip())
            os.kill(pid, 0)
            out.append(pid)
        except (OSError, ValueError):
            continue
    return out


def probe_http(url: str, model: str, timeout: float = 60.0,
               stream: bool = False, max_tokens: int = 8,
               extra: dict | None = None, prompt_chars: int = 0,
               ask: str | None = None) -> dict:
    """One direct request. Reports what came back, not what we hoped for.

    Measures connect time and time-to-first-byte separately, because they
    answer different questions: a slow connect is the network, a fast connect
    with no first byte is the provider holding the request open.
    """
    # Inert padding, not a harder task. The point is to vary SIZE while
    # holding the work constant, so any change in behaviour is attributable to
    # the request size rather than to the model thinking harder.
    ask = ask or "Reply with the word ok."
    if prompt_chars:
        pad = ("\n/* padding line, ignore this entirely */" *
               max(1, prompt_chars // 40))
        ask = ask + pad[:max(0, prompt_chars - len(ask))]
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": ask}],
        "max_tokens": max_tokens,
        "stream": stream,
    }
    payload.update(extra or {})
    body = json.dumps(payload).encode()
    key = os.environ.get("MODEL_API_KEY") or os.environ.get("OPENCODE_API_KEY")
    headers = dict(CLIENT_HEADERS)
    if key:
        headers["Authorization"] = f"Bearer {key}"

    rec: dict = {"model": model, "stream": stream, "url": url,
                 "authenticated": bool(key)}
    t0 = time.time()
    req = urllib.request.Request(url + "/chat/completions", data=body,
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            rec["connect_s"] = round(time.time() - t0, 2)
            rec["status"] = r.status
            rec["headers"] = {k.lower(): v for k, v in r.headers.items()
                              if k.lower().startswith(("x-", "retry", "ratelimit"))}
            first = r.read(1)
            rec["ttfb_s"] = round(time.time() - t0, 2)
            rest = r.read()
            rec["total_s"] = round(time.time() - t0, 2)
            raw = (first + rest).decode("utf-8", "replace")
            rec["body_chars"] = len(raw)
            rec["body_head"] = redact(raw[:600])
            rec["verdict"] = ("ANSWERED" if raw.strip()
                              else "CONNECTED BUT EMPTY BODY")
            # THE FINDING. These are reasoning models: they fill
            # `reasoning_content` first and only then `content`. opencode
            # streams `content` deltas, so while a model is thinking our
            # stdout stays EMPTY -- which is indistinguishable from a dead
            # request unless you look at the raw envelope, as here.
            try:
                j = json.loads(raw)
                ch = (j.get("choices") or [{}])[0]
                msg = ch.get("message") or ch.get("delta") or {}
                rec["finish_reason"] = ch.get("finish_reason")
                rec["content_chars"] = len(msg.get("content") or "")
                rec["reasoning_chars"] = len(msg.get("reasoning_content") or "")
                rec["usage"] = j.get("usage")
                if rec["reasoning_chars"] and not rec["content_chars"]:
                    rec["verdict"] = ("ALL OUTPUT WENT TO reasoning_content; "
                                      "content is EMPTY")
            except (ValueError, AttributeError, IndexError):
                pass
    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode("utf-8", "replace")
        except Exception:                                    # noqa: BLE001
            pass
        rec.update(status=e.code, total_s=round(time.time() - t0, 2),
                   headers={k.lower(): v for k, v in (e.headers or {}).items()
                            if k.lower().startswith(("x-", "retry", "ratelimit"))},
                   body_head=redact(raw[:600]),
                   verdict=f"HTTP {e.code} — the provider REFUSED and said so")
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, OSError) as e:
        rec.update(status=None, total_s=round(time.time() - t0, 2),
                   error=f"{type(e).__name__}: {e}",
                   verdict="NO HTTP RESPONSE AT ALL — never got a status line")
    return rec


def probe_cli(model: str, timeout: float = 90.0, ask: str | None = None) -> dict:
    """The same question through `opencode run`, with its logs turned on.

    Comparing this against probe_http is the whole point: if the raw endpoint
    answers in 2s and the CLI produces nothing in 90s, the fault is between
    them, and every conclusion drawn from fleet logs so far has been about the
    wrong layer.
    """
    exe = os.environ.get("OPENCODE_BIN", "opencode")
    argv = [exe, "run", "--model", f"opencode/{model}", "--agent", "raw",
            "--auto", "--log-level", "DEBUG", "--print-logs"]
    env = dict(os.environ)
    env.setdefault("OPENCODE_CONFIG", str(CONFIG))
    rec = {"model": model, "argv": " ".join(argv)}
    t0 = time.time()
    try:
        p = subprocess.run(argv, input=ask or "Reply with the word ok.",
                           capture_output=True, text=True, timeout=timeout,
                           cwd=str(REPO), env=env)
        rec.update(rc=p.returncode, total_s=round(time.time() - t0, 1),
                   stdout_chars=len(p.stdout or ""),
                   stdout_head=redact((p.stdout or "")[:400]),
                   stderr_head=redact((p.stderr or "")[-2000:]),
                   verdict=("ANSWERED" if (p.stdout or "").strip()
                            else "rc=%s with NO stdout" % p.returncode))
    except subprocess.TimeoutExpired as e:
        rec.update(rc=None, total_s=round(time.time() - t0, 1),
                   stdout_head=redact((e.stdout or b"").decode("utf-8", "replace")[:400]
                                      if isinstance(e.stdout, bytes) else str(e.stdout or "")[:400]),
                   stderr_head=redact((e.stderr or b"").decode("utf-8", "replace")[-2000:]
                                      if isinstance(e.stderr, bytes) else str(e.stderr or "")[-2000:]),
                   verdict=f"CLI produced nothing in {timeout:.0f}s")
    except OSError as e:
        rec.update(error=f"{type(e).__name__}: {e}",
                   verdict="could not start opencode")
    return rec


# Every known way to say "do not think". Which one bites depends on the
# runtime behind the endpoint; unknown fields are ignored by servers that do
# not implement them, so sending all of them is safe and one probe covers the
# whole space instead of four.
NO_THINK = {
    "reasoning_effort": "none",
    "reasoning_budget": 0,
    "chat_template_kwargs": {"enable_thinking": False},
    "thinking": {"type": "disabled"},
}


def thinking_extra(a) -> dict | None:
    extra = json.loads(a.extra) if getattr(a, "extra", None) else {}
    eff = getattr(a, "effort", None)
    if eff and eff != "none":
        extra = {"reasoning_effort": eff,
                 "reasoning_budget": getattr(a, "reasoning_budget", 2000),
                 "chat_template_kwargs": {"enable_thinking": True}, **extra}
    elif eff == "none" or getattr(a, "no_thinking", False):
        extra = {**NO_THINK, **extra}
    return extra or None


def probe_worker(model: str, ask: str, timeout: float = 600.0) -> dict:
    """Drive the WORKER's own generation path, not a hand-rolled request.

    The raw HTTP probe proves what the provider does. This proves what the
    harness does with it, which is a different question and the one that
    decides whether a fleet run is worth starting: bounded reasoning, the
    client-side REASON_CAP, and the _force_code pass that turns captured
    reasoning into content all live in worker_direct and none of them are
    exercised by a bare urllib call.
    """
    os.environ.setdefault("MODEL_BACKEND", "zen")
    os.environ["OPENCODE_MODEL"] = f"opencode/{model}"
    sys.path.insert(0, str(REPO / "automation" / "win"))
    import importlib
    import worker_direct as wd                                # type: ignore
    importlib.reload(wd)
    rec = {"model": model, "backend": wd.MODEL_BACKEND,
           "url": wd._base_url(), "reason_cap": wd.REASON_CAP,
           "effort": wd.REASONING_EFFORT}
    t0 = time.time()
    try:
        text = wd.llama_echo(ask, budget_left=timeout)
        rec.update(total_s=round(time.time() - t0, 1),
                   content_chars=len(text or ""),
                   content_head=redact((text or "")[:400]),
                   verdict="ANSWERED" if (text or "").strip()
                           else "no content even after the force-code pass")
    except Exception as e:                                     # noqa: BLE001
        rec.update(total_s=round(time.time() - t0, 1),
                   error=f"{type(e).__name__}: {redact(str(e))[:300]}",
                   verdict="raised")
    return rec


def real_ask(a) -> str | None:
    """A genuine decompilation ask, or None for the trivial one.

    Inert padding does not make a model think; only a real task does, and
    thinking is what we suspect the deadline was killing. Both probes must be
    able to send it or the http-vs-cli comparison is between two different
    questions.
    """
    if not getattr(a, "real_asm", None):
        return None
    asm = Path(a.real_asm).read_text(errors="ignore")
    return ("Write ONE C function that compiles to this MIPS assembly under "
            "GCC 2.7.2. Output only C.\n\n" + asm[:12000])


def summarise(results: list[dict]) -> None:
    print("\n" + "=" * 78)
    print("WHICH LAYER IS SILENT")
    print("=" * 78)
    http = [r for r in results if r.get("kind") == "http"]
    cli = [r for r in results if r.get("kind") == "cli"]
    http_ok = sum(1 for r in http if r.get("verdict") == "ANSWERED")
    cli_ok = sum(1 for r in cli if r.get("verdict") == "ANSWERED")
    if http:
        print(f"  raw HTTP : {http_ok}/{len(http)} answered")
    if cli:
        print(f"  opencode : {cli_ok}/{len(cli)} answered")
    if http and cli:
        if http_ok and not cli_ok:
            print("\n  -> The PROVIDER answers and the CLI does not relay it.")
            print("     The fault is in opencode or how we invoke it. Calling")
            print("     the endpoint directly would bypass the whole problem.")
        elif not http_ok and not cli_ok:
            print("\n  -> Neither layer gets an answer. The provider is")
            print("     dropping us. Check the statuses and headers above for")
            print("     whether it refuses (an HTTP error) or simply holds the")
            print("     connection open (no status line at all).")
        elif http_ok and cli_ok:
            print("\n  -> Both work on a TINY prompt. The failure therefore")
            print("     depends on the request, not the plumbing: re-run with")
            print("     --repeat and with real prompt sizes.")
    print("\nStatuses seen:", sorted({str(r.get('status')) for r in http}) or "none")


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    print("\ncredentials can never reach a log file or stdout")
    for probe in ("Authorization: Bearer sk-abcdef1234567890abcdef",
                  'api_key: "abcdef1234567890abcdef"',
                  "sk-proj-ABCDEFGHIJKLMNOP1234"):
        out = redact(probe)
        ck("abcdef1234567890" not in out and "ABCDEFGHIJKLMNOP" not in out,
           f"redacted: {out[:52]}")
    ck(redact("nothing secret here") == "nothing secret here",
       "ordinary text is left alone")
    ck(redact("") == "", "empty input does not raise")

    print("\nconfiguration is read from the same file the fleet uses")
    cfg = load_config()
    ck(base_url(cfg).startswith("http"), f"base url resolves ({base_url(cfg)})")
    ck(base_url({}) == "https://opencode.ai/zen/v1",
       "and falls back to the known Zen endpoint if the config is unreadable")
    ms = models(cfg)
    ck(isinstance(ms, list), f"model list resolves ({len(ms)} models)")

    print("\nthe probe identifies itself the way opencode does")
    ck(CLIENT_HEADERS.get("x-opencode-client") == "cli",
       "x-opencode-client: cli is sent, or we would be probing a different "
       "service than the fleet talks to")

    print("\nit refuses to contend with a live fleet")
    src = Path(__file__).read_text(encoding="utf-8")
    m = src[src.index("def main("):]
    ck("fleet_alive()" in m,
       "main() checks for live workers before sending anything")

    print()
    if fails:
        print(f"{len(fails)} FAILED:")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", help="single model to probe")
    ap.add_argument("--all-models", action="store_true")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--http-only", action="store_true")
    ap.add_argument("--cli-only", action="store_true")
    ap.add_argument("--worker", action="store_true",
                    help="drive worker_direct's own generation path (bounded "
                         "reasoning + force-code), not a bare HTTP request")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--max-tokens", type=int, default=8)
    ap.add_argument("--prompt-chars", type=int, default=0,
                    help="pad the prompt with inert text to this size")
    ap.add_argument("--real-asm",
                    help="send a REAL decompilation ask built from this .s "
                         "file. Inert padding does not make a model think; "
                         "only a real task does, and thinking is what we "
                         "suspect the timeout is actually killing.")
    ap.add_argument("--extra", help="JSON merged into the request body, for "
                                    "testing reasoning switches")
    ap.add_argument("--effort", choices=("none", "low", "medium", "high"),
                    help="bounded reasoning: send reasoning_effort plus a "
                         "reasoning_budget, so the model may think but cannot "
                         "spend the whole completion doing it")
    ap.add_argument("--reasoning-budget", type=int, default=2000)
    ap.add_argument("--no-thinking", action="store_true",
                    help="ask the model NOT to reason. A flag rather than raw "
                         "JSON because the connector rejects brace-laden "
                         "arguments, and because the exact switch differs per "
                         "runtime: send all the known ones and let the server "
                         "ignore the fields it does not implement.")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()

    alive = fleet_alive()
    if alive:
        print(f"REFUSING: fleet workers are alive ({alive}). Stop the fleet "
              f"first; a probe that competes with real work measures the "
              f"contention it created.", file=sys.stderr)
        return 2

    cfg = load_config()
    url = base_url(cfg)
    picks = ([a.model] if a.model else
             models(cfg) if a.all_models else
             (models(cfg)[:1] or ["mimo-v2.5-free"]))
    print(f"endpoint {url}\nmodels   {', '.join(picks)}\n"
          f"prompt   'Reply with the word ok.' (tiny, deliberately)")

    results = []
    if a.worker:
        ask = real_ask(a) or "Reply with the word ok."
        for model in picks:
            r = probe_worker(model, ask, timeout=a.timeout)
            r["kind"] = "worker"; results.append(r)
            print(f"\n[worker] {model}  backend={r.get('backend')} "
                  f"effort={r.get('effort')} cap={r.get('reason_cap')}")
            print(f"  total {r.get('total_s')}s  "
                  f"content {r.get('content_chars', 0)} chars")
            if r.get("content_head"):
                print("  " + r["content_head"][:300].replace("\n", "\n  "))
            if r.get("error"):
                print(f"  error {r['error']}")
            print(f"  -> {r.get('verdict')}")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUT_DIR / f"probe-{int(time.time())}.json"
        out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nwrote {out}")
        return 0
    for model in picks:
        for i in range(a.repeat):
            if not a.cli_only:
                r = probe_http(url, model, timeout=a.timeout,
                               max_tokens=a.max_tokens,
                               prompt_chars=a.prompt_chars,
                               ask=real_ask(a), extra=thinking_extra(a))
                r["kind"] = "http"; results.append(r)
                print(f"\n[http {i+1}/{a.repeat}] {model}")
                print(f"  status {r.get('status')}  "
                      f"ttfb {r.get('ttfb_s')}  total {r.get('total_s')}s")
                if r.get("headers"):
                    print(f"  headers {r['headers']}")
                if r.get("error"):
                    print(f"  error {r['error']}")
                if r.get("body_head"):
                    print(f"  body {r['body_head'][:300]}")
                if r.get("reasoning_chars") is not None:
                    print(f"  content {r['content_chars']} chars | "
                          f"reasoning {r['reasoning_chars']} chars | "
                          f"finish {r.get('finish_reason')} | "
                          f"usage {r.get('usage')}")
                print(f"  -> {r.get('verdict')}")
            if not a.http_only:
                r = probe_cli(model, timeout=max(30.0, a.timeout),
                              ask=real_ask(a))
                r["kind"] = "cli"; results.append(r)
                print(f"\n[cli  {i+1}/{a.repeat}] {model}")
                print(f"  rc {r.get('rc')}  total {r.get('total_s')}s  "
                      f"stdout {r.get('stdout_chars', 0)} chars")
                if r.get("stderr_head"):
                    print("  stderr tail:")
                    for line in r["stderr_head"].splitlines()[-12:]:
                        print("    " + line[:160])
                print(f"  -> {r.get('verdict')}")

    summarise(results)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"probe-{int(time.time())}.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
