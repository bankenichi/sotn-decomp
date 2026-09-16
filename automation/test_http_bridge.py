#!/usr/bin/env python3
"""Focused tests for the sotn-cmd HTTP/SSE bridge.

Does not need the full decomp toolchain. Covers:
  - transport selection (default stdio, aliases, reject unknown)
  - token fail-closed when HTTP transport is selected
  - bearer accept / reject against a live streamable-http app

Run (WSL, repo mcp venv):
  automation/mcp/.venv/bin/python automation/test_http_bridge.py
Under any other interpreter the suite reports a skip and exits zero.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

MCP = Path(__file__).resolve().parent / "mcp"
sys.path.insert(0, str(MCP))

try:
    import http_bridge as hb  # noqa: E402
    _HAVE_BRIDGE_DEPS = True
except ImportError:
    hb = None  # type: ignore
    _HAVE_BRIDGE_DEPS = False

FAILS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


def test_transport_selection() -> None:
    print("\ntransport selection")
    saved = os.environ.pop("SOTN_CMD_TRANSPORT", None)
    try:
        check(hb.resolve_transport(None) == "stdio", "unset env => stdio")
        check(hb.resolve_transport("") == "stdio", "empty => stdio")
        check(hb.resolve_transport("  ") == "stdio", "whitespace => stdio")
        check(hb.resolve_transport("stdio") == "stdio", "stdio explicit")
        check(hb.resolve_transport("streamable-http") == "streamable-http",
              "streamable-http")
        check(hb.resolve_transport("http") == "streamable-http", "http alias")
        check(hb.resolve_transport("streamable_http") == "streamable-http",
              "underscore alias")
        check(hb.resolve_transport("sse") == "sse", "sse")
        try:
            hb.resolve_transport("websocket")
            check(False, "unknown transport is rejected")
        except SystemExit as e:
            check("not supported" in str(e), "unknown transport is rejected")
    finally:
        if saved is not None:
            os.environ["SOTN_CMD_TRANSPORT"] = saved


def test_token_fail_closed() -> None:
    print("\ntoken fail-closed")
    saved = os.environ.pop("SOTN_CMD_HTTP_TOKEN", None)
    try:
        try:
            hb.require_http_token()
            check(False, "missing token raises SystemExit")
        except SystemExit as e:
            check("SOTN_CMD_HTTP_TOKEN" in str(e), "missing token raises SystemExit")
        os.environ["SOTN_CMD_HTTP_TOKEN"] = "   "
        try:
            hb.require_http_token()
            check(False, "whitespace-only token raises SystemExit")
        except SystemExit:
            check(True, "whitespace-only token raises SystemExit")
        os.environ["SOTN_CMD_HTTP_TOKEN"] = "s3cret-token"
        check(hb.require_http_token() == "s3cret-token", "non-empty token accepted")
    finally:
        if saved is None:
            os.environ.pop("SOTN_CMD_HTTP_TOKEN", None)
        else:
            os.environ["SOTN_CMD_HTTP_TOKEN"] = saved


def test_bearer_helpers() -> None:
    print("\nbearer header helpers")
    tok = "abc123XYZ"
    check(hb._bearer_ok(f"Bearer {tok}", tok), "exact Bearer accepted")
    check(hb._bearer_ok(f"bearer {tok}", tok), "bearer case-insensitive")
    check(not hb._bearer_ok(None, tok), "missing header rejected")
    check(not hb._bearer_ok("", tok), "empty header rejected")
    check(not hb._bearer_ok(f"Bearer {tok}x", tok), "wrong token rejected")
    check(not hb._bearer_ok(f"Basic {tok}", tok), "non-Bearer scheme rejected")
    check(not hb._bearer_ok("Bearer ", tok), "empty bearer value rejected")



def test_bind_env_overrides() -> None:
    print("\nFASTMCP bind env overrides constructor defaults")
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:
        check(False, f"mcp available ({e})")
        return
    mcp = FastMCP("bind-test")
    check(mcp.settings.port == 8000, "default port is 8000 before override")
    os.environ["FASTMCP_PORT"] = "8765"
    os.environ["FASTMCP_HOST"] = "127.0.0.1"
    os.environ["FASTMCP_STREAMABLE_HTTP_PATH"] = "/mcp"
    try:
        hb.apply_fastmcp_bind_env(mcp)
        check(mcp.settings.port == 8765, "FASTMCP_PORT overrides to 8765")
        check(mcp.settings.host == "127.0.0.1", "FASTMCP_HOST applied")
        check(mcp.settings.streamable_http_path == "/mcp", "path applied")
    finally:
        os.environ.pop("FASTMCP_PORT", None)
        os.environ.pop("FASTMCP_HOST", None)
        os.environ.pop("FASTMCP_STREAMABLE_HTTP_PATH", None)


def test_live_bearer_http() -> None:
    """Spin a tiny FastMCP streamable-http app behind the middleware."""
    print("\nlive bearer accept/reject")
    try:
        from mcp.server.fastmcp import FastMCP
        import httpx
        import uvicorn
    except ImportError as e:
        check(False, f"mcp/httpx/uvicorn available ({e})")
        return

    mcp = FastMCP("sotn-cmd-http-test")

    @mcp.tool()
    def ping() -> str:
        return "pong"

    token = "test-token-not-for-prod"
    # Ephemeral port
    import socket
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    os.environ["SOTN_CMD_HTTP_TOKEN"] = token
    # Prefer no Host rebinding so Host: 127.0.0.1:port is fine either way
    os.environ.pop("SOTN_CMD_HTTP_ALLOWED_HOSTS", None)
    app = hb.build_http_app(mcp, "streamable-http", token)

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait until listening
    deadline = time.time() + 5
    ready = False
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                ready = True
                break
        except OSError:
            time.sleep(0.05)
    check(ready, f"server listening on 127.0.0.1:{port}")
    if not ready:
        server.should_exit = True
        return

    url = f"http://127.0.0.1:{port}/mcp"
    # Streamable HTTP expects MCP-shaped POSTs; we only assert auth gate.
    headers_base = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    }

    with httpx.Client(timeout=5.0) as client:
        r0 = client.post(url, headers=headers_base, json=body)
        check(r0.status_code == 401, f"no Authorization => 401 (got {r0.status_code})")

        r1 = client.post(
            url,
            headers={**headers_base, "Authorization": "Bearer wrong"},
            json=body,
        )
        check(r1.status_code == 401, f"wrong token => 401 (got {r1.status_code})")

        r2 = client.post(
            url,
            headers={**headers_base, "Authorization": f"Bearer {token}"},
            json=body,
        )
        # Auth passed: not 401. Protocol may return 200 / 202 / 406 depending
        # on negotiated Accept; connection must not be refused.
        check(r2.status_code != 401,
              f"correct token not 401 (got {r2.status_code})")
        check(r2.status_code < 500,
              f"correct token not 5xx (got {r2.status_code})")

    server.should_exit = True
    thread.join(timeout=3)


def main() -> int:
    if not _HAVE_BRIDGE_DEPS:
        print("SKIPPED: starlette is unavailable; rerun with automation/mcp/.venv/bin/python")
        return 0
    test_transport_selection()
    test_token_fail_closed()
    test_bearer_helpers()
    test_bind_env_overrides()
    test_live_bearer_http()
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILURE(S)")
        for f in FAILS:
            print(" -", f)
        return 1
    print("all http bridge checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
