# Grok Bot: remote URL (streamable-http)

Grok Bot can `AddMcpServer` by HTTPS URL. Keep `SOTN_CMD_DRYRUN=1` until you have
reviewed `list_allowed` and the argv each tool would run.

## 1. Start sotn-cmd in WSL (bound to localhost)

```bash
cd /mnt/c/Users/kenic/Documents/SOTN-Decomp
export SOTN_CMD_DRYRUN=1
export SOTN_CMD_TRANSPORT=streamable-http
export SOTN_CMD_HTTP_TOKEN='replace-with-a-long-random-secret'
export FASTMCP_HOST=127.0.0.1
export FASTMCP_PORT=8765
# optional: FASTMCP_STREAMABLE_HTTP_PATH=/mcp  (default)
./automation/mcp/.venv/bin/python automation/mcp/sotn_cmd_mcp.py
```

`FASTMCP_HOST=127.0.0.1` is correct for a tunnel: cloudflared/ngrok dials
localhost. Do not bind `0.0.0.0` unless you intend to expose the port on the LAN
as well (the bearer token is still required).

If `SOTN_CMD_HTTP_TOKEN` is unset or empty, HTTP/SSE startup refuses (fail closed).

## 2. Tunnel in front

```bash
cloudflared tunnel --url http://127.0.0.1:8765
# or: ngrok http 8765
```

Copy the public `https://...` URL the tunnel prints.

## 3. AddMcpServer shape

- **url**: `https://<tunnel-host>/mcp` (path must match `FASTMCP_STREAMABLE_HTTP_PATH`)
- **headers**: `Authorization: Bearer <same SOTN_CMD_HTTP_TOKEN value>`

Example (conceptual; use the Grok Bot / Cursor AddMcpServer UI or tool):

```json
{
  "name": "sotn-cmd",
  "url": "https://<tunnel-host>/mcp",
  "headers": {
    "Authorization": "Bearer replace-with-a-long-random-secret"
  }
}
```

## Host header / transport_security

Token-gated HTTP mode disables FastMCP DNS-rebinding Host checks by default,
because quick tunnels mint random hostnames. Auth is the bearer token, and the
listener stays on loopback. To re-enable Host checks with a fixed public name:

```bash
export SOTN_CMD_HTTP_ALLOWED_HOSTS='my-fixed-host.example.com,my-fixed-host.example.com:*'
```

## Safety

Keep dry-run until `list_allowed` is reviewed. There is still no general shell
tool; only the allowlisted registry runs.
