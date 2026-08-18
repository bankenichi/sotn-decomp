# Registering the connectors with any MCP client

Both servers in `automation/mcp/` are plain **stdio MCP servers**. They read the
protocol on stdin and write it on stdout. They contain no client detection, no
vendor SDK, and no Claude-only code path, so every MCP client drives them the
same way. What differs between clients is only the *config file format* and
*where it lives*.

This directory holds one ready-to-edit snippet per client. Full explanation,
including the security model and what each tool does, is in `docs/CONNECTORS.md`.

## The one thing to get right

A client needs three facts:

| fact | value |
|---|---|
| interpreter | the repo venv python, e.g. `<repo>/automation/mcp/.venv/bin/python` |
| script | `<repo>/automation/mcp/sotn_cmd_mcp.py` (absolute) |
| `SOTN_CMD_DRYRUN` | `1` until you have reviewed the argv it produces, then `0` |

Nothing else is required. `SOTN_REPO` and `SOTN_PYTHON` both fall back to values
derived from the script's own location, and the script inserts its own directory
on `sys.path`, so **no `cwd` setting is needed**. That matters because several
clients cannot set one.

`SOTN_CMD_DRYRUN` **fails closed**: unset or empty means dry-run. You cannot
accidentally get a live server by forgetting the variable, only by setting it
to `0` on purpose.

## Files here

| file | client | notes |
|---|---|---|
| `codex.config.toml` | OpenAI Codex CLI | append to `~/.codex/config.toml` |
| `mcp_servers.native.json` | any client on Linux/macOS, or a client running *inside* WSL | the simplest form: interpreter + absolute script path |
| `mcp_servers.windows-wsl.json` | any client on the Windows host reaching a WSL toolchain | needs the `wsl.exe` hop |

For Claude Desktop specifically there are also two MCPB bundles under
`automation/mcpb/`. Those are packaging for one client and are **not** required:
the JSON snippet here does the same job. See `docs/CONNECTORS.md` for why the
bundles carry no server code.

## Windows plus WSL is the awkward case, and it is not a client problem

The build toolchain lives in WSL. If the client process runs on the Windows host
it has to cross that boundary, which is what the `wsl.exe -d <distro> -e bash -lc
...` wrapper does. If the client runs *inside* WSL already -- Codex CLI installed
in the distro, for instance -- use `mcp_servers.native.json` instead and skip the
hop entirely. It is faster and there is one less quoting layer to get wrong.

One trap, recorded here because it silently ran a live server once: MCP `env`
entries are applied to the **`wsl.exe` process on the Windows side** and do not
cross into WSL unless they are named in `WSLENV`. That is why the WSL snippet
passes `SOTN_CMD_DRYRUN` inline in the bash command rather than in `env`. In the
native snippet `env` works normally.
