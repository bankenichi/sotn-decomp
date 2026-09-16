#!/usr/bin/env python3
"""Token-gated HTTP/SSE bridge for sotn-cmd.

Keeps the tool registry in sotn_cmd_mcp.py. This module only:
  - requires SOTN_CMD_HTTP_TOKEN when not on stdio (fail closed if unset)
  - wraps the FastMCP Starlette app with Bearer auth middleware
  - relaxes Host/Origin DNS-rebinding checks for token-gated tunnel use
  - serves via uvicorn using FASTMCP_HOST / FASTMCP_PORT / path settings

Stdio clients never import or call this module.
"""
from __future__ import annotations

import os
import secrets
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

HTTP_TRANSPORTS = frozenset({"sse", "streamable-http"})


def resolve_transport(raw: str | None = None) -> str:
    """Map SOTN_CMD_TRANSPORT to a FastMCP transport name.

    Unset / empty / whitespace => stdio (byte-identical default path).
    """
    value = (os.environ.get("SOTN_CMD_TRANSPORT") if raw is None else raw) or ""
    value = value.strip().lower()
    if not value:
        return "stdio"
    aliases = {
        "stdio": "stdio",
        "sse": "sse",
        "http": "streamable-http",
        "streamable-http": "streamable-http",
        "streamable_http": "streamable-http",
    }
    if value not in aliases:
        raise SystemExit(
            f"SOTN_CMD_TRANSPORT={value!r} is not supported; "
            f"use one of: stdio, sse, streamable-http"
        )
    return aliases[value]


def require_http_token() -> str:
    """Fail closed: HTTP transports need a non-empty shared bearer token."""
    token = os.environ.get("SOTN_CMD_HTTP_TOKEN", "")
    if not token.strip():
        raise SystemExit(
            "SOTN_CMD_HTTP_TOKEN is unset or empty. Refusing to start an HTTP "
            "transport without a shared bearer token. Set SOTN_CMD_HTTP_TOKEN "
            "to a long random secret, or use stdio (leave SOTN_CMD_TRANSPORT unset)."
        )
    return token


def _bearer_ok(header: str | None, expected: str) -> bool:
    if not header:
        return False
    parts = header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False
    # secrets.compare_digest requires equal-length str; length mismatch => False
    got = parts[1].strip()
    if len(got) != len(expected):
        return False
    return secrets.compare_digest(got, expected)


class BearerTokenMiddleware:
    """Reject missing/wrong Authorization: Bearer ... with 401."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }
        if _bearer_ok(headers.get("authorization"), self.token):
            await self.app(scope, receive, send)
            return
        response = JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer realm="sotn-cmd"'},
        )
        await response(scope, receive, send)



def apply_fastmcp_bind_env(mcp) -> None:
    """Constructor defaults override FASTMCP_* env; re-apply bind settings.

    FastMCP() passes host/port/path kwargs into Settings(), so pydantic-settings
    never sees FASTMCP_HOST / FASTMCP_PORT / FASTMCP_STREAMABLE_HTTP_PATH from
    the environment. Re-read them here for HTTP mode only.
    """
    host = os.environ.get("FASTMCP_HOST")
    if host is not None and host.strip() != "":
        mcp.settings.host = host.strip()
    port = os.environ.get("FASTMCP_PORT")
    if port is not None and str(port).strip() != "":
        mcp.settings.port = int(str(port).strip())
    path = os.environ.get("FASTMCP_STREAMABLE_HTTP_PATH")
    if path is not None and path.strip() != "":
        mcp.settings.streamable_http_path = path.strip()
    sse_path = os.environ.get("FASTMCP_SSE_PATH")
    if sse_path is not None and sse_path.strip() != "":
        mcp.settings.sse_path = sse_path.strip()


def configure_tunnel_transport_security(mcp) -> None:
    """Token is the gate; tunnel Host headers are random (*.trycloudflare.com).

    Keep the process bound to FASTMCP_HOST (default 127.0.0.1) so the listener
    is not world-reachable. Disable Host/Origin rebinding checks so a tunnel
    that dials localhost is not rejected with 421 for a foreign Host header.
    Optional SOTN_CMD_HTTP_ALLOWED_HOSTS (comma-separated) re-enables the check
    with an explicit allowlist when the public hostname is fixed.
    """
    from mcp.server.transport_security import TransportSecuritySettings

    raw = os.environ.get("SOTN_CMD_HTTP_ALLOWED_HOSTS", "").strip()
    if raw:
        hosts = [h.strip() for h in raw.split(",") if h.strip()]
        origins = [
            o if "://" in o else f"https://{o.split(':', 1)[0]}"
            for o in hosts
        ]
        # Also keep localhost so direct curls still work.
        for local in ("127.0.0.1:*", "localhost:*", "[::1]:*"):
            if local not in hosts:
                hosts.append(local)
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=hosts,
            allowed_origins=[
                "http://127.0.0.1:*",
                "http://localhost:*",
                "http://[::1]:*",
                *origins,
            ],
        )
    else:
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        )


def build_http_app(mcp, transport: str, token: str):
    """Return the Starlette app for sse or streamable-http, with bearer wrap."""
    apply_fastmcp_bind_env(mcp)
    configure_tunnel_transport_security(mcp)
    if transport == "streamable-http":
        app = mcp.streamable_http_app()
    elif transport == "sse":
        app = mcp.sse_app()
    else:
        raise ValueError(f"not an HTTP transport: {transport}")
    return BearerTokenMiddleware(app, token)


def serve_http(mcp, transport: str) -> None:
    """Block serving HTTP/SSE until interrupted."""
    import asyncio

    import uvicorn

    apply_fastmcp_bind_env(mcp)
    token = require_http_token()
    app = build_http_app(mcp, transport, token)

    host = mcp.settings.host
    port = mcp.settings.port
    path = (
        mcp.settings.streamable_http_path
        if transport == "streamable-http"
        else mcp.settings.sse_path
    )
    print(
        f"sotn-cmd {transport} on http://{host}:{port}{path} "
        f"(bearer token required; bind is for tunnel dial-to-localhost)",
        flush=True,
    )

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=str(mcp.settings.log_level).lower(),
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


def run_from_env(mcp) -> None:
    """Entry used by sotn_cmd_mcp.__main__: stdio unchanged when unset."""
    transport = resolve_transport()
    if transport == "stdio":
        mcp.run()
        return
    serve_http(mcp, transport)
