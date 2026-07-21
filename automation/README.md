# SOTN Decomp Automation

The orchestration stack from `SOTN-Orchestration-Stack.md`, built and tested.
Coordination is files and git only, no app puppeting. Two engines share one
queue: the OpenCode fleet grinds volume on local Qwen and a cheap cloud model,
and the Claude harness handles escalation, match closing, and merge review.

## Layout

    automation/
      README.md                         this file
      mcp/
        sotn_local_mcp.py               FastMCP stdio server (bridge to local llama)
        llama_client.py                 stdlib client, holds the system prompts
        sotn_cmd_mcp.py                 FastMCP stdio server (allowlisted commands)
        commands_client.py              allowlist, validation, subprocess runner
        requirements.txt                mcp>=1.2
        test_mock.py                    offline smoke test, no model needed
        claude_desktop_config.snippet.json       registration for sotn-local
        claude_desktop_config.cmd.snippet.json   registration for sotn-cmd
      qwen.sh                           zero-infra bash wrapper (Section 5.2 fallback)
      scheduler.py                      single writer to work/queue.jsonl
      worker.py                         one volume-engine worker (claim, run OpenCode, report)
      start_fleet.sh                    launch N workers in parallel
      merge_matched.py                  review and merge matched branches
      queue/
        queue.schema.json               JSON Schema for a queue record
        queue.example.jsonl             three example records
        seed.us.txt                     441 undecompiled us functions as queue ids
      tools/
        gen_seed_us.py                  regenerate seed.us.txt from src/ INCLUDE_ASM
      opencode/
        opencode.json                   provider (local Tier 0) + sotn-matcher agent
        AGENT.md                        per-function loop prompt + RESULT.json contract
      setup/
        install_wsl2.sh                 one-shot WSL2 dependency installer
        gitexclude.sh                   keep scratch state out of git
      wt/                               git worktrees, one per claimed function (created at runtime)

The live queue lives at `work/queue.jsonl` at the repo root (created on first
`scheduler.py init`). Add `work/` and `automation/wt/` to your local
`.git/info/exclude` so scratch state never lands in a commit.

## 1. The local-model bridge (FastMCP)

Your llama-server and OpenCode already run on your machine. Claude cannot reach
`localhost:8080` from its side, so the bridge runs on your machine, launched by
Claude Desktop over stdio, and reaches llama-server locally. Large asm and diff
text stay inside the bridge; only compact structured results return to Claude.

Tools exposed: `health`, `local_chat`, `local_draft`, `local_summarize_diff`,
`local_transform`. Contract matches Section 5.1 of the stack doc.

### 1.1 Install and self-test (in WSL2)

    cd ~/sotn-decomp/automation/mcp
    python3 -m venv .venv
    ./.venv/bin/pip install -r requirements.txt
    ./.venv/bin/python test_mock.py          # expect: ALL CHECKS PASSED

### 1.2 Point it at your real llama-server

    LLAMA_BASE_URL=http://localhost:8080/v1 LLAMA_MODEL=qwen \
      ./.venv/bin/python -c "import llama_client as c; print(c.health())"

Expect `{'ok': True, ... 'models': [...]}`. If `ok` is False, fix the URL or
model name before registering the server.

### 1.3 Register in Claude Desktop

Merge `mcp/claude_desktop_config.snippet.json` into your Claude Desktop config
(`%APPDATA%\Claude\claude_desktop_config.json`), then restart Claude Desktop.
The snippet launches the server inside WSL2 with `wsl.exe`, so it shares the
network namespace with llama-server. Adjust the path if your clone is not at
`~/sotn-decomp`. Set `LLAMA_MODEL` to whatever id your llama-server reports.

After restart, a new Claude session will list `sotn-local` tools. Call `health`
first to confirm the bridge reaches the model.

## 1b. The allowlisted command connector (sotn-cmd)

A second FastMCP server, `mcp/sotn_cmd_mcp.py`, lets Claude run a fixed,
hard-allowlisted set of repo actions. There is no general shell. Three groups:

- Commands: `make build/extract/expected/clean/force_symbols/function-finder/
  reports/duplicates-report`, `asm_diff`, `permuter`, `permuter_import`. Run as
  argv lists (never `shell=True`) with validated args (version enum,
  `^[A-Za-z0-9_]+$` symbols/overlays, in-repo path checks).
- Scoped git: `git_status`, `git_add_all`, `git_commit` (message 1-200 chars,
  single line). Lets the harness commit a matched function on its branch.
- Scoped filesystem: `read_file`, `write_file`, `list_dir`, `search_repo`. These
  let Claude read and edit the WSL2 tree THROUGH the connector when Cowork is not
  connected directly to the WSL2 clone. In-repo only, `.git` blocked, size
  capped; `write_file` respects dry-run.

The allowlist and validators live in `mcp/commands_client.py`. Call `list_allowed`
to see the full capability set and the dry-run state.

Safety default: the config snippet ships with `SOTN_CMD_DRYRUN=1`, so every tool
returns the exact argv it WOULD run without executing it. Review that, then set
`SOTN_CMD_DRYRUN=0` (or remove it) to actually run commands.

### Install and preview

    cd ~/sotn-decomp/automation/mcp
    SOTN_CMD_DRYRUN=1 SOTN_REPO=$HOME/sotn-decomp \
      ./.venv/bin/python -c "import commands_client as c; print(c.build_argv('make_build', version='us'))"
    # -> ['make', 'build', 'VERSION=us']

### Register in Claude Desktop

Merge `mcp/claude_desktop_config.cmd.snippet.json` into your Claude Desktop
config alongside `sotn-local`, then restart. Call `list_allowed` first to see the
exact allowlist and confirm the dry-run state. Set `SOTN_PYTHON` to the repo
`.venv` python so asm-differ and the permuter have their dependencies.

This is the scoped version of the "run my local CLI" connector discussed in
Section 5: allowlisted actions only, not an open shell.

## 2. The work queue and scheduler

`scheduler.py` is the only writer to `work/queue.jsonl`, guarded by an exclusive
file lock so concurrent workers cannot corrupt it. Workers never edit the queue;
they claim work and report results through the scheduler.

    # seed from a list of ids or full JSON records (one per line)
    python3 automation/scheduler.py init --from my_todo_ids.txt

    # a worker claims the next function and gets its own git worktree
    python3 automation/scheduler.py next --worker qwen-1 --worktree

    # report an outcome
    python3 automation/scheduler.py report --id us:ST/NO0:func_A \
      --status near --score 96 --tier 1 --add-iters 14 --notes "stack slot order"

    python3 automation/scheduler.py stats
    python3 automation/scheduler.py reclaim --older-than-min 60   # recover crashed workers

Record fields and their meaning are defined in `queue/queue.schema.json`.

### 2.1 Where the todo list comes from

A ready-made `us` seed already exists: `queue/seed.us.txt`, holding 441 queue
ids for every function still stubbed as `INCLUDE_ASM` in the sources (the
not-yet-decompiled set). Seed the queue directly:

    python3 automation/scheduler.py init --from automation/queue/seed.us.txt

Distribution: ST/RNO0 (219), BOSS/BO6 (123), BOSS/BO0 (67), ST/RCEN (23), and a
handful in ST/MAD, SERVANT/FNAME, MAIN, ST/SEL. Regenerate it any time with
`python3 automation/tools/gen_seed_us.py`.

That static list is the undecompiled set. The authoritative NON-matching list
(functions that have C but do not yet byte-match) only exists after a real
build: `make function-finder` (and `make reports`) produce per-file decomp
status and call graphs under `build/reports`. Convert those to
`<build>:<overlay>:<function>` ids and `init` them too once you have a build.

### 2.2 One-time environment install

Before any of this, install the build toolchain on WSL2 with:

    bash automation/setup/install_wsl2.sh

It installs the Debian packages, Rust, Go 1.24, dosemu2, the repo `.venv`, and
the automation bridge `.venv`. It does not need the disc assets. See
`../Getting-Started.md` for the full picture.

## 3. The OpenCode volume engine

Point your OpenCode workers at the system prompt in `opencode/AGENT.md`,
restricted to build, diff, edit, read, and the local model. Each worker claims
one function via the scheduler, works in its worktree, and reports `matched`,
`near`, or `escalated`. It must never edit the queue directly and never loop
past its iteration cap.

Escalation ladder (stack doc Section 3): Tier 0 Qwen, then Tier 1 cheap cloud,
then mark `near` or `escalated`. The Claude harness runs the permuter on any
near-match first (free CPU), then Haiku for the mechanical loop, Sonnet to close,
Opus only for hard reasoning and merge review.

### 3.0 Topology A: OpenCode on Windows (the chosen setup)

OpenCode and llama-server run natively on Windows. Only the build toolchain and
the repo live in WSL, so the VM stays small. The split:

- Scheduler, git, and the build stay in WSL. The scheduler remains the single
  writer to `work/queue.jsonl` with real POSIX locking, and git worktrees are
  created natively on ext4.
- `automation/win/worker_win.py` runs on WINDOWS with Windows Python. It drives
  the Windows OpenCode CLI and reaches the scheduler through `wsl.exe`.
- Only two things cross the boundary: OpenCode's working directory (the
  worktree, over `\\wsl$`) and the `RESULT.json` it writes there.

Windows callers use the `sotn` wrapper for anything that must run in WSL:

    automation\win\sotn.cmd build us
    automation\win\sotn.cmd diff EntityGaibonFlame us no0
    automation\win\sotn.cmd commit "match us:ST/NO0:func_X"

`sotn.cmd` is a thin passthrough; the real logic is `automation/win/
sotn_dispatch.sh`, which runs in WSL and is unit-tested. Add `automation\win`
to your PATH so agents can just call `sotn`.

Env for the Windows side: `SOTN_WSL_DISTRO` (default `Ubuntu-24.04`),
`SOTN_WSL_REPO` (auto-detected as `$HOME/sotn-decomp`), `SOTN_UNC_PREFIX`
(default `\\wsl$`; switch to `\\wsl.localhost` if your Windows prefers it).

Run the Windows worker:

    python automation\win\worker_win.py once      # one function
    python automation\win\worker_win.py loop --max 20

For several workers, start more than one shell (or a small PowerShell loop);
each claims a different function from the scheduler. Size the count to your
cores, remembering the build itself runs in WSL.

The WSL-side `automation/worker.py` and `start_fleet.sh` remain valid if you
ever install OpenCode inside WSL, but under Topology A you use the Windows
worker instead.

### 3.1 Running the fleet (WSL-resident OpenCode, alternative)

`worker.py` is the runnable driver. Each worker claims the next todo via
`scheduler.py next --worktree`, runs OpenCode headless (`opencode run` with the
`sotn-matcher` agent from `opencode/opencode.json`) inside that worktree, reads
the `RESULT.json` the agent writes, and reports the outcome to the scheduler. It
tries Tier 0 (local model) then Tier 1 (`OPENCODE_MODEL_T1`, if set) before
marking `escalated`.

    # one function, no model call (safe smoke test)
    WORKER_DRYRUN=1 python3 automation/worker.py once

    # one real function (needs llama-server + opencode up)
    python3 automation/worker.py once

    # a fleet of 3 workers grinding until the queue is empty
    automation/start_fleet.sh 3

Key env (see the header of `worker.py`): `OPENCODE_MODEL` (default `llama/qwen`),
`OPENCODE_MODEL_T1` (cloud fallback), `MAX_ITERS`, `NEAR_THRESHOLD`, `RUN_TIMEOUT`.
The worker sets `OPENCODE_CONFIG` to `automation/opencode/opencode.json` so the
provider and agent resolve even from inside a worktree.

The whole loop was verified end to end in a sandbox git repo with a mock
OpenCode: claim, worktree creation, RESULT.json read, and scheduler report all
chain correctly, and the dry-run path reports `escalated` without invoking a model.

### 3.2 Review and merge

When functions land as `matched`, review and merge their branches into an
integration branch (dry run first, then `--yes`):

    python3 automation/merge_matched.py list
    python3 automation/merge_matched.py merge --into integration --all
    python3 automation/merge_matched.py merge --into integration --all --yes

## 4. qwen.sh fallback

For shell pipelines and quick manual checks without the MCP layer:

    LLAMA_BASE_URL=http://localhost:8080/v1 LLAMA_MODEL=qwen \
      ./automation/qwen.sh system_prompt.txt user_prompt.txt

Needs `curl` and `jq`.

## 5. On giving Claude direct access to your machine

You offered to build a connector that lets Claude write the work folder freely
or drive your local CLI. Here is the honest tradeoff.

You do not need it for this workflow, and it is the higher-risk option. The
design in your own docs is deliberately file-and-git coordinated: the local
model is reached through the scoped bridge in Section 1, and everything else
moves through the queue and worktrees. That keeps each capability narrow and
auditable.

- The FastMCP bridge is scoped: it can only chat with your local model. Good.
- A "write the work folder freely" connector removes the create-only guardrail
  on this mount. Prefer instead to have Claude Desktop open the WSL2 clone
  directly as its working directory, where normal file tools already work with
  full read and write. That gets you the capability without a custom bridge.
- A "run my local CLI" connector is effectively arbitrary remote command
  execution on your machine. It is buildable as a FastMCP server exposing a
  `run(cmd)` tool, but it is a real security surface: anything driving it can run
  anything as you. If you want it, scope it hard (an allowlist of exact commands
  such as `make build`, `make extract`, asm-differ, and the permuter) rather
  than a general shell, and treat approvals seriously.

Update: the scoped, allowlisted command connector is now built and lives in
`mcp/sotn_cmd_mcp.py` (see Section 1b). It exposes only make/asm-differ/permuter
actions with validated arguments, not a general shell, and ships in dry-run mode
by default. Use it instead of any open-shell bridge. If a genuine need for a new
action appears, add it to the `REGISTRY` in `commands_client.py` with an explicit
validator rather than widening it into a passthrough.
