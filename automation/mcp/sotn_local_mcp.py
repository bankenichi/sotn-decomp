#!/usr/bin/env python3
"""
sotn_local_mcp: a stdio FastMCP server that bridges an MCP client to a locally
running OpenAI-compatible LLM (llama-server / llama.cpp / Ollama /v1).

CLIENT-AGNOSTIC. Plain stdio MCP, no client detection and no Claude-only path.
Claude Desktop, Codex CLI and any other MCP client launch it identically. See
docs/CONNECTORS.md for per-client registration.

Purpose:
  The client launches this server on your machine. It reaches your local
  llama-server at LLAMA_BASE_URL. Large assembly and diff text are processed
  here and only compact structured results are returned to the client, keeping
  big payloads out of the orchestrating model's context and spending zero
  frontier tokens on drafting.

CONCURRENCY
  Every tool is `async def` and offloads its blocking HTTP call with
  anyio.to_thread.run_sync. This matters: FastMCP awaits a plain `def` tool
  directly on the event loop, so one slow generation would block the whole
  server, including `health`. The low-level session already dispatches requests
  concurrently (task group + start_soon), so with the blocking call moved to a
  worker thread, several generations genuinely overlap.

  To actually get parallelism end to end, start llama-server with slots:
      llama-server -c <ctx> --parallel N --cont-batching ...
  Note --parallel divides the total context across slots; it does not multiply
  VRAM. Without slots the server serialises regardless of what we do here.

Environment:
  LLAMA_BASE_URL  default http://localhost:8081/v1
  LLAMA_MODEL     default the Qwen GGUF id reported by /v1/models
  LLAMA_API_KEY   optional; sent as a bearer token if set
  LLAMA_TIMEOUT   seconds, default 600
"""
from __future__ import annotations
import sys
from pathlib import Path

# See the identical block in sotn_cmd_mcp.py for why. Short version: sys.path[0]
# is only guaranteed to be this directory under the plain script launch form, and
# a client that starts the server any other way would fail the sibling import at
# startup with the traceback buried in its own log.
_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import anyio  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402
import llama_client as lc  # noqa: E402

mcp = FastMCP("sotn-local")


@mcp.tool()
async def health() -> dict:
    """Check that the local llama-server endpoint is reachable and list models."""
    return await anyio.to_thread.run_sync(lc.health)


@mcp.tool()
async def local_chat(system: str, user: str, temperature: float = 0.2,
                     max_tokens: int = 0) -> str:
    """Generic chat call to the local model. Returns only the assistant text.
    Use for ad-hoc generation; prefer the task tools below for decomp work."""
    return await anyio.to_thread.run_sync(
        lambda: lc.chat(system, user, temperature=temperature,
                        max_tokens=(max_tokens or None)))


@mcp.tool()
async def local_draft(asm_text: str, context: str = "") -> dict:
    """First-pass C draft from MIPS assembly. Returns {"c_code": ...}.
    The large asm_text stays server-side; only the C draft is returned."""
    return await anyio.to_thread.run_sync(
        lambda: lc.local_draft(asm_text, context=context))


@mcp.tool()
async def local_summarize_diff(diff_text: str) -> dict:
    """Reduce verbose asm-differ output to the first divergence and a score hint.
    Returns {"first_divergence": ..., "score_hint": ...}."""
    return await anyio.to_thread.run_sync(
        lambda: lc.local_summarize_diff(diff_text))


@mcp.tool()
async def local_transform(instruction: str, code: str) -> dict:
    """Apply one mechanical transform to a C function. Returns {"code": ...}."""
    return await anyio.to_thread.run_sync(
        lambda: lc.local_transform(instruction, code))


if __name__ == "__main__":
    mcp.run()  # stdio transport: what every MCP client expects
