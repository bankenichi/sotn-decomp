"""
llama_client: minimal stdlib client for an OpenAI-compatible chat endpoint
(llama-server / llama.cpp --api, Ollama's /v1, vLLM, etc.).

No third-party dependencies so it can be imported and unit-tested anywhere.
The FastMCP server imports these functions; all large asm/diff text is
processed here and only structured results are returned to the caller.
"""
from __future__ import annotations
import json
import os
import urllib.request
import urllib.error

DEFAULT_BASE_URL = os.environ.get("LLAMA_BASE_URL", "http://localhost:8081/v1")
DEFAULT_MODEL = os.environ.get(
    "LLAMA_MODEL",
    "Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-APEX-MTP-I-Compact.gguf")
DEFAULT_API_KEY = os.environ.get("LLAMA_API_KEY", "")  # llama-server ignores it
DEFAULT_TIMEOUT = float(os.environ.get("LLAMA_TIMEOUT", "600"))


def chat(system: str, user: str, temperature: float = 0.2,
         max_tokens: int | None = None, base_url: str | None = None,
         model: str | None = None, timeout: float | None = None) -> str:
    """POST a chat completion and return only the assistant text."""
    base = (base_url or DEFAULT_BASE_URL).rstrip("/")
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "stream": False,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if DEFAULT_API_KEY:
        headers["Authorization"] = f"Bearer {DEFAULT_API_KEY}"
    req = urllib.request.Request(base + "/chat/completions", data=data,
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout or DEFAULT_TIMEOUT) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def health(base_url: str | None = None) -> dict:
    """Return endpoint reachability and the served model list, if any."""
    base = (base_url or DEFAULT_BASE_URL).rstrip("/")
    try:
        req = urllib.request.Request(base + "/models", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        ids = [m.get("id") for m in body.get("data", [])]
        return {"ok": True, "base_url": base, "models": ids}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "base_url": base, "error": str(e)}


# ---- task-specific helpers (system prompts live here, not in Claude context) ----

_DRAFT_SYS = (
    "You are a MIPS-to-C decompiler assistant for a matching decompilation of "
    "Castlevania: Symphony of the Night (PSX, GCC 2.x). Given MIPS assembly, "
    "produce a single C function that is a plausible first-pass source. Output "
    "ONLY C code, no prose, no markdown fences. Preserve function order and use "
    "existing SOTN struct/symbol names when the context provides them."
)

_DIFF_SYS = (
    "You analyze asm-differ output for a matching decompilation. Identify the "
    "FIRST point where the compiled output diverges from the target. Reply with "
    "two short lines only:\n"
    "FIRST_DIVERGENCE: <file/line or instruction and a one-line cause>\n"
    "SCORE_HINT: <rough percent match as an integer 0-100>"
)

_TRANSFORM_SYS = (
    "You apply a single, mechanical transformation to a C function for a matching "
    "decompilation. Output ONLY the transformed C code, no prose, no fences."
)


def local_draft(asm_text: str, context: str = "", **kw) -> dict:
    user = asm_text if not context else f"CONTEXT:\n{context}\n\nASSEMBLY:\n{asm_text}"
    return {"c_code": chat(_DRAFT_SYS, user, **kw)}


def local_summarize_diff(diff_text: str, **kw) -> dict:
    out = chat(_DIFF_SYS, diff_text, **kw)
    first, score = "", ""
    for line in out.splitlines():
        s = line.strip()
        if s.upper().startswith("FIRST_DIVERGENCE:"):
            first = s.split(":", 1)[1].strip()
        elif s.upper().startswith("SCORE_HINT:"):
            score = s.split(":", 1)[1].strip()
    return {"first_divergence": first or out.strip(), "score_hint": score}


def local_transform(instruction: str, code: str, **kw) -> dict:
    user = f"TRANSFORMATION:\n{instruction}\n\nCODE:\n{code}"
    return {"code": chat(_TRANSFORM_SYS, user, **kw)}
