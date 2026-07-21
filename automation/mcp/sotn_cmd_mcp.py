#!/usr/bin/env python3
"""
sotn_cmd_mcp: a stdio FastMCP server exposing a HARD-ALLOWLISTED set of SOTN
build/diff/permuter commands to Claude Desktop. There is no general shell tool.

Each tool validates its arguments (version enums, symbol/overlay regexes, in-repo
path checks) and runs a fixed argv with subprocess (never shell=True). Output is
truncated. See automation/mcp/commands_client.py for the allowlist and validation.

Environment:
  SOTN_REPO        repo root (default: two levels up from this file)
  SOTN_PYTHON      python used for asm-differ/permuter (default: python3;
                   set to the repo .venv python, e.g. .venv/bin/python)
  SOTN_CMD_DRYRUN  set to 1 to return the argv WITHOUT executing (safe preview)
  SOTN_CMD_MAXOUT  max stdout/stderr chars returned (default 20000)

Safety: this server can run make/asm-differ/permuter as you. Keep DRYRUN on
until you have reviewed the argv it produces, and never widen the registry into
a general 'run any command' tool.
"""
from __future__ import annotations
from mcp.server.fastmcp import FastMCP
import commands_client as cc

mcp = FastMCP("sotn-cmd")


@mcp.tool()
def list_allowed() -> dict:
    """Return the exact allowlist of command actions, filesystem actions, and
    the dry-run state."""
    return cc.capabilities()


@mcp.tool()
def make_build(version: str = "us", timeout: int = 3600) -> dict:
    """Run `make build VERSION=<version>` (version in us/hd/pspeu/saturn)."""
    return cc.run("make_build", timeout=timeout, version=version)


@mcp.tool()
def make_extract(version: str = "us", timeout: int = 3600) -> dict:
    """Run `make extract VERSION=<version>` (needs the disc image in disks/)."""
    return cc.run("make_extract", timeout=timeout, version=version)


@mcp.tool()
def make_expected(version: str = "us", timeout: int = 3600) -> dict:
    """Run `make expected VERSION=<version>` (build and record expected output)."""
    return cc.run("make_expected", timeout=timeout, version=version)


@mcp.tool()
def make_clean(version: str = "us", timeout: int = 600) -> dict:
    """Run `make clean VERSION=<version>`."""
    return cc.run("make_clean", timeout=timeout, version=version)


@mcp.tool()
def make_force_symbols(version: str = "us", timeout: int = 1200) -> dict:
    """Run `make force_symbols VERSION=<version>` (symbols from a good build)."""
    return cc.run("make_force_symbols", timeout=timeout, version=version)


@mcp.tool()
def make_function_finder(version: str = "", timeout: int = 1800) -> dict:
    """Run `make function-finder` (decomp status, file lists, call graphs)."""
    kw = {"version": version} if version else {}
    return cc.run("make_function_finder", timeout=timeout, **kw)


@mcp.tool()
def make_reports(timeout: int = 1800) -> dict:
    """Run `make reports` (duplicates report plus function-finder)."""
    return cc.run("make_reports", timeout=timeout)


@mcp.tool()
def make_duplicates_report(timeout: int = 1200) -> dict:
    """Run `make duplicates-report`."""
    return cc.run("make_duplicates_report", timeout=timeout)


@mcp.tool()
def asm_diff(symbol: str, version: str = "us", overlay: str = "dra",
             make_first: bool = True, fmt: str = "plain", timeout: int = 900) -> dict:
    """Run asm-differ for one function. symbol ^[A-Za-z0-9_]+$, overlay like 'no0',
    fmt in plain/color/json/html. Returns returncode and captured diff output."""
    return cc.run("asm_diff", timeout=timeout, symbol=symbol, version=version,
                  overlay=overlay, make_first=make_first, fmt=fmt)


@mcp.tool()
def permuter(work_dir: str, timeout: int = 1800) -> dict:
    """Run decomp-permuter on an in-repo work directory (created by permuter_import)."""
    return cc.run("permuter", timeout=timeout, work_dir=work_dir)


@mcp.tool()
def permuter_import(c_file: str, asm_file: str, timeout: int = 300) -> dict:
    """Prepare a permuter work dir from an in-repo C file and target asm file."""
    return cc.run("permuter_import", timeout=timeout, c_file=c_file, asm_file=asm_file)


@mcp.tool()
def fleet_start(workers: int = 4, max_functions: int = 0,
                force: bool = False) -> dict:
    """Launch N detached volume workers in WSL. Returns immediately.

    workers = generations in flight (1-16). apply/build/verify is lock-
    serialised, so beyond ~4 the extras mostly queue. Requires llama-server
    started with --parallel >= workers. Poll with fleet_status; always end with
    fleet_stop or claims are left stranded.

    HOLD: if the fleet was stopped deliberately (fleet_stop with hold), this
    REFUSES and returns held=True. That is intentional; a human may have stopped
    it to reconfigure llama-server. Automated callers must NOT pass force. Only
    override with force=True on an explicit human instruction to resume."""
    return cc.fleet_start(workers, max_functions, force=force)


@mcp.tool()
def fleet_status(tail: int = 2) -> dict:
    """Which fleet workers are alive, plus the last lines of each worker log.
    Check the log tails, not just the count: a stuck worker still looks alive."""
    return cc.fleet_status(tail)


@mcp.tool()
def fleet_stop(hold: bool = True) -> dict:
    """Stop all fleet workers, release their claimed records, clear the lock.
    Always call this when finished. A killed worker cannot release its own
    claim, so records would sit 'claimed' forever and be skipped.

    hold=True (default) marks the stop as DELIBERATE: fleet_start will then
    refuse until someone passes force=True. Use the default whenever a human
    asked for the fleet to stop.

    hold=False is for automated recycling only, i.e. when a watchdog is about to
    immediately restart a crashed fleet. Never use hold=False to work around a
    hold that a human set."""
    return cc.fleet_stop(hold=hold)


@mcp.tool()
def verify_build(version: str = "us") -> dict:
    """THE ORACLE. Check every artifact hash against config/check.<version>.sha.

    make_build returning 0 does NOT mean the build matches. This is the only
    tool that answers 'is the build byte-correct'. Returns
    {matched, expected, failed, all_ok, verdict}."""
    return cc.verify_build(version)


@mcp.tool()
def queue_report(function_id: str, status: str, proof: str = "",
                 score: str = "", notes: str = "") -> dict:
    """Record an outcome in the work queue via scheduler.py (the single writer).

    status: todo|claimed|near|matched|escalated|deferred.
    'matched' is REFUSED unless proof is supplied: pass the verify_build
    verdict plus the artifact hash. Never hand-edit work/queue.jsonl."""
    return cc.queue_report(function_id, status, proof=proof, score=score,
                           notes=notes)


@mcp.tool()
def queue_stats(timeout: int = 60) -> dict:
    """Queue counts by status (todo/claimed/near/matched/escalated/deferred).
    One cheap call for polling whether the fleet has produced new work."""
    return cc.run("queue_stats", timeout=timeout)


@mcp.tool()
def queue_list(status: str = "", timeout: int = 60) -> dict:
    """List queue records, optionally filtered by status (e.g. 'near',
    'escalated'). Read-only."""
    kw = {"status": status} if status else {}
    return cc.run("queue_list", timeout=timeout, **kw)


@mcp.tool()
def git_status(timeout: int = 60) -> dict:
    """`git status --short` in the WSL2 repo. Read-only."""
    return cc.run("git_status", timeout=timeout)


@mcp.tool()
def git_add_all(timeout: int = 120) -> dict:
    """`git add -A` in the WSL2 repo. Stages all changes in the current worktree."""
    return cc.run("git_add_all", timeout=timeout)


@mcp.tool()
def git_commit(message: str, timeout: int = 120) -> dict:
    """`git commit -m <message>` in the WSL2 repo. Message is 1-200 chars, single line.
    Use after git_add_all to commit a matched function on its branch."""
    return cc.run("git_commit", timeout=timeout, message=message)


# ---- scoped in-repo filesystem (edit the WSL2 tree through the connector) ----

@mcp.tool()
def read_file(path: str) -> dict:
    """Read an in-repo text file (path relative to the repo root). Read-only.
    Returns {path, bytes, truncated, content}."""
    return cc.fs_read(path)


@mcp.tool()
def write_file(path: str, content: str) -> dict:
    """Overwrite (or create) an in-repo text file with full content. Blocked
    outside the repo and inside .git. Respects dry-run: previews without writing."""
    return cc.fs_write(path, content)


@mcp.tool()
def list_dir(path: str = ".") -> dict:
    """List an in-repo directory. Returns entries with name/type/size."""
    return cc.fs_list(path)


@mcp.tool()
def search_repo(query: str, path: str = ".", max_results: int = 200) -> dict:
    """Search the repo for a pattern (ripgrep/grep, argv-safe, no shell).
    Returns matching file:line: text entries."""
    return cc.fs_search(query, path=path, max_results=max_results)


if __name__ == "__main__":
    mcp.run()  # stdio transport, as expected by Claude Desktop
