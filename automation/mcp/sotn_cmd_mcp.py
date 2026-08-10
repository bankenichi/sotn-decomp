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
import re
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP
import commands_client as cc

mcp = FastMCP("sotn-cmd")


def _exposed_tool_names() -> list[str]:
    """Names actually decorated with @mcp.tool() in this module.

    Derived from this module's own globals rather than from FastMCP internals
    on purpose. Tool-registry attribute names differ between FastMCP versions,
    and a diagnostic that reaches into them can raise on import or upgrade.
    A diagnostic must never be able to kill its host: that has already happened
    once here, when a startup guard referenced names it had not imported and
    took the whole connector down. Hence the bare except and the empty-list
    fallback -- a missing list is a nuisance, a dead connector is an outage."""
    try:
        names = []
        for name, obj in list(globals().items()):
            if name.startswith("_") or name == "mcp":
                continue
            target = obj if callable(obj) else None
            fn = getattr(obj, "fn", None)          # FastMCP Tool wrapper, if any
            if getattr(target, "__module__", None) == __name__:
                names.append(name)
            elif fn is not None and getattr(fn, "__module__", None) == __name__:
                names.append(name)
        return sorted(set(names))
    except Exception:
        return []


@mcp.tool()
def list_allowed() -> dict:
    """Return the allowlist, the CALLABLE tool surface, and the dry-run state.

    There are TWO surfaces and they are not the same set. `commands_client
    .REGISTRY` is the allowlist of shell actions; the `@mcp.tool()` decorators
    in this file are what a caller can actually invoke. Some tools (verify_build,
    fleet_start) are decorated without a REGISTRY entry, so a REGISTRY-only
    answer under-reports them.

    That gap cost a wasted connector restart: an action was added to REGISTRY
    but not decorated, so it was uncallable while this reported it as available,
    and reading this list looked like confirmation. Report both, always."""
    caps = cc.capabilities()
    caps["mcp_tools"] = _exposed_tool_names()
    caps["note"] = ("'commands' is the shell allowlist; 'mcp_tools' is what is "
                    "actually callable. A name in one but not the other is a "
                    "wiring bug, not a capability.")
    return caps


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
def permuter(work_dir: str, threads: int = 4, stop_on_zero: bool = True,
             better_only: bool = True, algorithm: str = "",
             timeout: int = 1800) -> dict:
    """Run decomp-permuter on an in-repo work directory (from permuter_import).

    Prefer job_start(action="permuter", work_dir=...) -- the search is unbounded
    and will outlive any synchronous call. Permuter jobs are NOT exclusive, so
    several seeds can be searched at once.

    threads (-j): the permuter is multithreaded and DEFAULTS TO ONE. Every run
    before 2026-08-03 was single-threaded, including a 141,000-iteration search
    that held one core for two and a half hours. Capped at 16, and keep it
    modest while a fleet is running.

    stop_on_zero: without it a run that finds a match keeps searching, so the
    job never finishes and nothing downstream sees the win.

    better_only: log only improvements. The default emits a line per iteration
    at roughly ten per second, which is how a stall analysis ends up parsing
    141k lines to recover a single number.

    algorithm: difflib (default) or levenshtein. Worth A/B-ing on a seed that
    has plateaued, since they score differently."""
    return cc.run("permuter", timeout=timeout, work_dir=work_dir,
                  threads=threads, stop_on_zero=stop_on_zero,
                  better_only=better_only, algorithm=algorithm)


@mcp.tool()
def permuter_import(c_file: str, asm_file: str, timeout: int = 300) -> dict:
    """Prepare a permuter work dir from an in-repo C file and target asm file."""
    return cc.run("permuter_import", timeout=timeout, c_file=c_file, asm_file=asm_file)


@mcp.tool()
def fleet_start(workers: int = 4, max_functions: int = 0,
                force: bool = False, backend: str = "zen",
                cli_workers: int = 0, opencode_model: str = "") -> dict:
    """Launch detached volume workers in WSL. Returns immediately.

    backend picks the model tier:
      "zen"  (default) - `workers` workers talking straight to the Zen HTTP
                         API. THIS IS THE CONFIGURATION TO USE. Preferred over
                         "cli" because the OpenCode CLI relays only `content`,
                         while the models worth running fill
                         `reasoning_content` first and so come back empty
                         through the CLI.
      "llama"          - `workers` local llama workers. Free and unlimited,
                         but plateaued on the functions that remain. This was
                         called "http" until 2026-08-09, which was backwards:
                         zen is the backend that speaks HTTP. "http" is still
                         accepted and now resolves to "zen".
      "cli"            - `workers` OpenCode CLI workers. Same free Zen models
                         reached through the CLI. Use only when deliberately
                         testing the CLI path. Quota is ACCOUNT-WIDE and shared
                         across every model, so N parallel workers drain it
                         about N times faster.
      "mixed"          - `workers` llama workers AND `cli_workers` OpenCode
                         workers against the same queue.

    This list omitted "zen" until 2026-08-09, and defaulted to "http", even
    though the code has accepted "zen" throughout and zen is the agreed
    configuration. An agent read the help, saw no zen, and started a cli
    fleet. A supported value missing from its own help is a defect, and so is
    a name that describes a different backend than the one it selects.

    opencode_model overrides the worker default, which is
    opencode/mimo-v2.5-free (this line said big-pickle long after that stopped
    being true). Rotating models does NOT grant fresh quota; see
    automation/opencode/ZEN-FREE-MODELS.md. Pass a comma-separated list to
    round-robin one model per worker, which is how a bake-off is run.

    Total workers 1-16 = generations in flight. apply/build/verify is lock-
    serialised, so beyond ~4 the extras mostly queue. llama workers need
    llama-server started with --parallel >= that count.

    Any cli worker triggers a preflight first: if the OpenCode CLI is not usable
    from the worker's environment, NOTHING is started. Otherwise those workers
    would claim records and escalate them for reasons unrelated to the function.

    Poll with fleet_status; always end with fleet_stop or claims are stranded.

    HOLD: if the fleet was stopped deliberately (fleet_stop with hold), this
    REFUSES and returns held=True. That is intentional; a human may have stopped
    it to reconfigure llama-server. Automated callers must NOT pass force. Only
    override with force=True on an explicit human instruction to resume."""
    return cc.fleet_start(workers, max_functions, force=force, backend=backend,
                          cli_workers=cli_workers,
                          opencode_model=opencode_model)


@mcp.tool()
def opencode_preflight() -> dict:
    """Check the OpenCode CLI is reachable from the worker environment.

    Returns ok, the resolved binary path and its version. Cheap, spends no model
    quota, and answers "will a cli fleet actually run here" without launching
    one."""
    return cc.opencode_preflight()


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


@mcp.tool()
def git_push(timeout: int = 300) -> dict:
    """`git push origin HEAD` in the WSL2 repo. Publishes the current branch.

    Takes no remote, refspec or flag, and that is deliberate rather than a
    limitation: there is no input, so there is nothing to validate and nothing
    to get wrong. This repo has two remotes and `upstream` is the project we
    forked from, so a caller-chosen remote would be one typo away from pushing
    at it. `origin` is hard-coded here and upstream's push URL is separately
    disabled in the repo config.

    Runs in WSL because that is where the git credentials live; the Cowork
    sandbox has none and fails with "could not read Username"."""
    return cc.run("git_push", timeout=timeout)


@mcp.tool()
def queue_prune(pattern: str, apply: bool = False, timeout: int = 120) -> dict:
    """Remove queue records matching a regex. DRY RUN unless apply=True.

    Exists because `init` is additive with no inverse. 34 rodata string labels
    (aCdlnop, aComplete, ...) were seeded as decomp targets by a name-based
    filter; they are `.asciz` constants and a worker claiming one burns its
    whole budget on nothing.

    Deletes rather than marks: `deferred` would be wrong, since
    `next --include-deferred` hands those straight back to a cli worker. Only
    `todo` records are eligible, so matched/near/escalated work is never at
    risk. Always run once without apply and read the list first."""
    return cc.run("queue_prune", timeout=timeout, pattern=pattern, apply=apply)


@mcp.tool()
def queue_init(from_file: str = "automation/seed.us.txt", timeout: int = 120) -> dict:
    """`scheduler.py init --from <file>`: add queue records for new functions.

    Additive; ids already present are skipped, so re-running is safe.

    MUST run here rather than in a sandbox shell. SOTN_QUEUE defaults to
    ~/sotn-work/queue.jsonl, so a different HOME resolves to a DIFFERENT queue
    file: the Cowork sandbox's copy reports 33 matched where this one has 134.
    Seeding the wrong file would fork the harness state while appearing to
    succeed."""
    return cc.run("queue_init", timeout=timeout, from_file=from_file)


@mcp.tool()
def job_start(action: str, version: str = "us", script: str = "",
              args: str = "", work_dir: str = "", threads: int = 4,
              stop_on_zero: bool = True, better_only: bool = True,
              algorithm: str = "") -> dict:
    """Start a long command in the background and return a job id immediately.

    USE THIS INSTEAD OF make_build. A synchronous build outlives the MCP
    transport timeout: 8 calls failed that way in one day while the build kept
    running, leaving the tree mid-build with the caller unaware. This returns in
    milliseconds and cannot time out.

    action: make_build | make_extract | make_expected | make_clean |
            make_force_symbols | make_reports | make_duplicates_report |
            make_function_finder | run_analysis | permuter
    For run_analysis, pass script= (e.g. asm_twin_finder.py) and args=.

    Refuses to start a second job for the same action while one is running: two
    concurrent builds share one build directory and would produce artifacts
    matching nothing.

    Then poll: job_status(job_id, wait_s=25) until state == 'done', and read
    'ok' and 'summary'."""
    kw = {}
    if action == "run_analysis":
        kw = {"script": script, "args": args}
    elif action == "permuter":
        # permuter takes a work_dir, not a version. This branch used to pass
        # NOTHING, so `permuter` was advertised as a job action while being
        # impossible to start as one: cc.start_job() raised on the missing
        # positional every time. Found 2026-08-02, when the permuter was first
        # needed as a background job alongside a running fleet.
        #
        # It matters because the permuter is the one long job that MUST be
        # backgrounded. It searches indefinitely by design, so a synchronous
        # call cannot terminate before the MCP transport does.
        if not work_dir:
            raise ValueError(
                "permuter needs work_dir=, e.g. "
                "nonmatchings/<function> (create it with permuter_import)")
        kw = {"work_dir": work_dir, "threads": threads,
              "stop_on_zero": stop_on_zero, "better_only": better_only,
              "algorithm": algorithm}
    else:
        kw = {"version": version}
    return cc.start_job(action, **kw)


@mcp.tool()
def job_status(job_id: str, wait_s: float = 25.0,
               tail_lines: int = 40) -> dict:
    """Poll a job. Blocks up to wait_s (hard-capped at 30s), then returns.

    The cap is deliberate: a caller polling this may itself be capped (the
    Cowork sandbox kills any bash call at 45s), so a longer block would be
    useless to it. Poll repeatedly; each call is cheap.

    Returns state running|done|vanished, plus 'ok', 'returncode', 'summary'
    (the lines that actually say whether it worked) and a short 'tail'. The full
    log path is returned rather than the log: a build log is ~300 lines of ninja
    chatter and returning it wastes enormous context."""
    return cc.job_status(job_id, wait_s=wait_s, tail_lines=tail_lines)


@mcp.tool()
def job_list(limit: int = 20) -> dict:
    """Recent jobs and their states."""
    return cc.job_list(limit=limit)


@mcp.tool()
def job_cancel(job_id: str) -> dict:
    """Terminate a running job's process group."""
    return cc.job_cancel(job_id)


@mcp.tool()
def git_restore(path: str, timeout: int = 120) -> dict:
    """`git checkout -- <path>`: discard uncommitted changes to ONE path.

    DESTRUCTIVE. It throws away working-tree edits that are not committed, so
    pass an explicit path and never a directory you have not inspected with
    git_status first. There is deliberately no "restore everything" form.

    Use it to revert a failed experiment: write, build, and if verify_build does
    not report the expected N/N, restore the file and rebuild so the tree is
    never left in a half-changed state.

    Run it HERE, not from a sandbox shell. The Cowork sandbox tears down its PID
    namespace when a bash call ends or hits its 45s cap. Doing this there once
    killed git mid-operation and left a stale .git/index.lock that blocked every
    later commit until it was removed by hand."""
    return cc.run("git_restore", timeout=timeout, path=path)


@mcp.tool()
def git_restore_from_head(path: str, timeout: int = 120) -> dict:
    """`git checkout HEAD -- <path>`: restore ONE path to its committed state.

    Different from git_restore, and the difference matters. git_restore restores
    from the INDEX, so if something has staged a bad state it faithfully returns
    the bad state. This restores from HEAD, which is what you want after an
    interrupted rebase, a bad `git add`, or any time the index is not trusted.

    DESTRUCTIVE in the same way: uncommitted edits to that path are discarded.
    Pass an explicit path, and read git_status first.

    Added 2026-08-02 because it did not exist when it was needed. Recovering
    three source files meant reaching for sandbox git, which hit a stale
    .git/index.lock left by an earlier sandbox git that the 45s cap had killed
    mid-rebase. Git writes belong on this side, which means the git writes we
    actually need have to live on this side."""
    return cc.run("git_restore_from_head", timeout=timeout, path=path)


@mcp.tool()
def run_analysis(script: str, args: str = "", timeout: int = 1800) -> dict:
    """Run a read-only analysis script in WSL, synchronously.

    Exists because these were being run from the Cowork sandbox, which caps
    every call at 45s and reaches the repo over a slow Windows mount:
    asm_twin_finder used 1.8s of CPU but 37s of wall clock, and any extra
    command after it blew the limit. That was most of the 40 sandbox timeouts
    in a single day, each costing a full re-run.

    Allowed scripts: whatever is in `commands_client.ANALYSIS_SCRIPTS` (45 of
    them as of 2026-08-09). A rejected name returns the full list in the
    error, so ask by being wrong rather than trusting a docstring.

    This paragraph used to enumerate seven scripts and had been wrong for
    months: empty_response_audit, match_provenance, transplant and thirty
    others were callable and undocumented. That is the same defect as
    fleet_start's help omitting `backend="zen"` -- a list maintained by hand
    beside the real one drifts, and the copy a caller reads is the one that
    misleads them.

    If it might exceed a couple of minutes, use
    job_start('run_analysis', script=..., args=...) instead."""
    return cc.run("run_analysis", timeout=timeout, script=script, args=args)


@mcp.tool()
def queue_annotate(from_file: str = "automation/twins.us.json",
                   apply: bool = False, timeout: int = 300) -> dict:
    """`scheduler.py annotate`: attach twin candidates to queue records.

    174 of 335 unmatched stubs already exist elsewhere in the tree, 145 of them
    findable by name. Recording that on the record lets a worker start from
    "this is RicStepStand in src/ric/pl_steps.c, diff it against the asm"
    rather than from raw assembly.

    Non-destructive: writes only the `twin` field, never status, tier or
    iterations, so it cannot disturb the order the fleet pulls work in, and
    re-running is a no-op. DRY RUN unless apply=True.

    MUST run here, not in a sandbox shell. SOTN_QUEUE resolves via $HOME, so
    another environment would annotate a different queue file and fork the
    harness state while printing success. The command prints the resolved
    queue path so that fork is visible immediately.

    Regenerate the input first with:
        python3 automation/asm_twin_finder.py --record"""
    return cc.run("queue_annotate", timeout=timeout,
                  from_file=from_file, apply=apply)


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


def _assert_registry_is_exposed() -> None:
    """Every allowlisted action must also be a callable tool.

    These are TWO surfaces and it is easy to update one and not the other.
    `list_allowed` reads commands_client.REGISTRY, but Claude can only call what
    is decorated `@mcp.tool()` here. Adding git_push and queue_init to the
    registry alone made `list_allowed` report 18 commands while both remained
    uncallable -- the connector looked correctly updated and was not, which
    cost a restart to discover.

    Warn rather than exit: a missing wrapper makes one action unreachable, and
    refusing to start would take the other seventeen down with it.
    """
    # Everything below is wrapped, because a STARTUP DIAGNOSTIC MUST NOT BE
    # ABLE TO KILL THE SERVER IT DIAGNOSES. The first version of this function
    # referenced `sys` and `Path`, neither of which this module imported, and
    # took the whole connector down on launch -- a check meant to prevent a
    # broken connector became the thing that broke it. Syntax was fine, so
    # ast.parse said nothing; only running it would have shown the NameError.
    try:
        src = Path(__file__).read_text(encoding="utf-8")
        exposed = {m.group(1)
                   for m in re.finditer(r"@mcp\.tool\(\)\s*\ndef (\w+)", src)}
        missing = sorted(set(cc.REGISTRY) - exposed)
        if missing:
            print(f"WARNING: allowlisted but NOT exposed as tools, so "
                  f"uncallable: {missing}. Add an @mcp.tool() wrapper for each.",
                  file=sys.stderr)
    except Exception as exc:                                  # never fatal
        print(f"registry/tool cross-check skipped: {exc!r}", file=sys.stderr)




# ---------------------------------------------------------------------------
# git, in full.
#
# The Cowork sandbox is FORBIDDEN from running git against this repo. Not
# discouraged: forbidden. It reaches the repo over a Windows mount and is killed
# at 45 seconds, and on 2026-08-02 that combination killed a rebase mid-flight,
# left a stale .git/index.lock, and silently rolled three source files back to
# their pre-shim state while the commits themselves stayed correct. Four of the
# recovery calls also timed out.
#
# So every git operation this project needs lives here, where there is no
# ceiling and the repo is local. There is still no general `git` passthrough:
# each tool below maps to one fixed argv shape in commands_client.REGISTRY with
# validated arguments, and anything that can destroy work requires confirm=True.
# ---------------------------------------------------------------------------


@mcp.tool()
def git_log(n: int = 15, path: str = "", timeout: int = 120) -> dict:
    """Recent commits as `<sha> <author> <date> <subject>`.

    Pass path to see only the commits that touched it. Read-only."""
    return cc.run("git_log", timeout=timeout, n=n, path=path)


@mcp.tool()
def git_diff(path: str = "", staged: bool = False, ref: str = "",
             timeout: int = 120) -> dict:
    """Working-tree diff. staged=True shows the index instead; ref compares
    against a revision. Read-only."""
    return cc.run("git_diff", timeout=timeout, path=path, staged=staged, ref=ref)


@mcp.tool()
def git_diff_stat(ref: str = "", staged: bool = False,
                  timeout: int = 120) -> dict:
    """Per-file insert/delete counts. Use this before git_diff on a wide change,
    so a large diff does not have to be read to find out it is large."""
    return cc.run("git_diff_stat", timeout=timeout, ref=ref, staged=staged)


@mcp.tool()
def git_show(ref: str = "HEAD", path: str = "", timeout: int = 120) -> dict:
    """One commit: header, full message, and diff. Read-only."""
    return cc.run("git_show", timeout=timeout, ref=ref, path=path)


@mcp.tool()
def git_fetch(remote: str = "upstream", timeout: int = 300) -> dict:
    """Update remote-tracking refs. READ-ONLY with respect to the tree.

    Fetch writes only refs/remotes/*; it never touches the working tree, HEAD,
    or any branch this repo builds from, so it is safe to run at any time --
    including while the fleet is generating, which merging is NOT.

    Needed because the fork otherwise cannot measure its own drift: on
    2026-08-09 upstream/master was still f6bfa379 from a 2026-08-01 fetch, and
    "how far behind are we" had no answer. `upstream` push is disabled at the
    remote, so this cannot become a route to publishing.

    Follow with git_log_range('HEAD..upstream/master') to see what arrived.
    """
    return cc.run("git_fetch", timeout=timeout, remote=remote)


@mcp.tool()
def git_log_range(rng: str = "", n: int = 40, path: str = "",
                  timeout: int = 120) -> dict:
    """Commits in a revision range, e.g. 'HEAD..upstream/master'.

    git_log takes only a count, so it could not answer "what is upstream
    carrying that we are not". Read-only."""
    return cc.run("git_log_range", timeout=timeout, rng=rng, n=n, path=path)


@mcp.tool()
def git_diff_stat_range(rng: str = "", timeout: int = 180) -> dict:
    """Per-file churn across a revision range, e.g. 'HEAD...upstream/master'.

    Use before reading any cross-fork diff: it says how big the change is
    without paying to read it."""
    return cc.run("git_diff_stat_range", timeout=timeout, rng=rng)


@mcp.tool()
def git_rev_parse(ref: str = "HEAD", timeout: int = 60) -> dict:
    """Resolve a revision to a full sha. Read-only."""
    return cc.run("git_rev_parse", timeout=timeout, ref=ref)


@mcp.tool()
def git_state(timeout: int = 120) -> dict:
    """Porcelain v2 status with branch headers.

    Use this to find out whether a merge, rebase or cherry-pick is half-finished
    before doing anything else. That question is exactly what was unanswerable
    on 2026-08-02 without a sandbox shell. Read-only."""
    return cc.run("git_state", timeout=timeout)


@mcp.tool()
def git_branch_list(timeout: int = 60) -> dict:
    """Branches with upstream tracking info. Read-only."""
    return cc.run("git_branch_list", timeout=timeout)


@mcp.tool()
def git_remote_list(timeout: int = 60) -> dict:
    """Remotes and their URLs.

    Worth reading before assuming where a push goes: this repo has `upstream`
    pointing at the project it was forked from, with its push URL deliberately
    disabled. Read-only."""
    return cc.run("git_remote_list", timeout=timeout)


@mcp.tool()
def git_ls_files(path: str = "", timeout: int = 120) -> dict:
    """List tracked files, optionally under one path. Read-only."""
    return cc.run("git_ls_files", timeout=timeout, path=path)


@mcp.tool()
def git_stash_list(timeout: int = 60) -> dict:
    """List stash entries. Read-only."""
    return cc.run("git_stash_list", timeout=timeout)


@mcp.tool()
def git_config_get(key: str, timeout: int = 60) -> dict:
    """Read one git config key. Restricted to user.name and user.email."""
    return cc.run("git_config_get", timeout=timeout, key=key)


@mcp.tool()
def git_config_set(key: str, value: str, timeout: int = 60) -> dict:
    """Set user.name or user.email for this repo.

    Only those two keys are permitted: git config can otherwise rewrite how git
    itself behaves (core.hooksPath, alias.*, credential.helper), which is not
    something an allowlisted runner should be able to do.

    Getting the email wrong is not cosmetic. GitHub rejects pushes that would
    publish a private address (GH007), and on 2026-08-02 two commits had to be
    rewritten because of it."""
    return cc.run("git_config_set", timeout=timeout, key=key, value=value)


@mcp.tool()
def git_rm_cached(path: str, confirm: bool = False, timeout: int = 120) -> dict:
    """`git rm --cached -r <path>`: stop tracking a path, keep it on disk.

    Requires confirm=True. Use after adding something to .gitignore that was
    already committed, because .gitignore alone never untracks anything.

    Deliberately --cached and never a plain rm: the files this is for are
    usually being written by a running fleet, and deleting them from disk would
    break a worker mid-attempt."""
    return cc.run("git_rm_cached", timeout=timeout, path=path, confirm=confirm)


@mcp.tool()
def git_add(path: str, timeout: int = 120) -> dict:
    """Stage ONE path. Use git_add_all to stage everything."""
    return cc.run("git_add", timeout=timeout, path=path)


@mcp.tool()
def git_commit_amend(message: str = "", reset_author: bool = False,
                     timeout: int = 120) -> dict:
    """Amend the previous commit.

    With no message the existing one is kept (--no-edit). reset_author=True
    re-stamps author and committer from current config, which is the fix when a
    commit was made under the wrong identity.

    Rewrites history: only safe before the commit has been pushed."""
    return cc.run("git_commit_amend", timeout=timeout, message=message,
                  reset_author=reset_author)


@mcp.tool()
def git_checkout_branch(name: str, create: bool = False,
                        timeout: int = 300) -> dict:
    """Switch branches, or create one with create=True.

    Changes the working tree, so commit or stash first; git will refuse rather
    than clobber, but check git_status anyway."""
    return cc.run("git_checkout_branch", timeout=timeout, name=name,
                  create=create)


@mcp.tool()
def git_stash_push(message: str = "", timeout: int = 300) -> dict:
    """Stash tracked modifications away. Recover with git_stash_pop."""
    return cc.run("git_stash_push", timeout=timeout, message=message)


@mcp.tool()
def git_stash_pop(confirm: bool = False, timeout: int = 300) -> dict:
    """Restore the top stash entry and drop it. Requires confirm=True: it can
    conflict with current edits and it removes the entry either way."""
    return cc.run("git_stash_pop", timeout=timeout, confirm=confirm)


@mcp.tool()
def git_reset(mode: str = "mixed", ref: str = "HEAD", confirm: bool = False,
              timeout: int = 600) -> dict:
    """Move the branch pointer. Requires confirm=True.

    soft   keep index and working tree. Use to re-commit differently.
    mixed  rebuild the index from ref, keep the working tree. Use to unstage,
           or to repair an index left inconsistent by an interrupted operation.
    hard   DISCARDS working-tree changes. There is no undo for uncommitted work.

    Prefer soft or mixed. Reach for hard only when git_status has been read and
    the losses are understood."""
    return cc.run("git_reset", timeout=timeout, mode=mode, ref=ref,
                  confirm=confirm)


@mcp.tool()
def git_rebase_abort(confirm: bool = False, timeout: int = 600) -> dict:
    """Abandon an in-progress rebase and return to the pre-rebase state.

    Requires confirm=True, because abort also reverts the working tree: on
    2026-08-02 a half-completed abort is what silently rolled three shimmed
    files back while their commits stayed intact. Read git_state first, and
    verify the working tree afterwards."""
    return cc.run("git_rebase_abort", timeout=timeout, confirm=confirm)


@mcp.tool()
def git_rebase_continue(confirm: bool = False, timeout: int = 600) -> dict:
    """Resume a rebase after conflicts have been staged. Requires confirm=True."""
    return cc.run("git_rebase_continue", timeout=timeout, confirm=confirm)


@mcp.tool()
def git_merge_abort(confirm: bool = False, timeout: int = 600) -> dict:
    """Abandon an in-progress merge. Requires confirm=True."""
    return cc.run("git_merge_abort", timeout=timeout, confirm=confirm)


@mcp.tool()
def git_cherry_pick_abort(confirm: bool = False, timeout: int = 600) -> dict:
    """Abandon an in-progress cherry-pick. Requires confirm=True."""
    return cc.run("git_cherry_pick_abort", timeout=timeout, confirm=confirm)


@mcp.tool()
def git_clean(path: str, confirm: bool = False, timeout: int = 300) -> dict:
    """Delete UNTRACKED files and directories under one path. confirm=True.

    Scoped to a path and never -x, so it cannot reach ignored build output or
    the venv. Untracked files have no git copy: once removed they are gone."""
    return cc.run("git_clean", timeout=timeout, path=path, confirm=confirm)


# ---------------------------------------------------------------------------
# ENTRY POINT MUST BE LAST.
#
# mcp.run() serves forever, so ANY @mcp.tool() defined below this block is never
# executed and never registered. On 2026-08-02 this guard sat in the middle of
# the file and 25 git tools were appended after it: `commands` listed all of
# them, `mcp_tools` listed none, and the connector had to be restarted twice.
#
# The parity test greps the SOURCE, so it happily passed. It now also asserts
# that no tool is defined after this block, which is the property that actually
# matters. Keep this at the bottom of the file.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _assert_registry_is_exposed()
    mcp.run()  # stdio transport, as expected by Claude Desktop
