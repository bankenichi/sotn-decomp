# Orchestrator charter and dispatch protocol (Opus)

Read this at the start of every orchestration session. Sections 1-3 are the
operating rules. Section 4 is the literal dispatch protocol: how to queue
subagents, which model each gets, and exactly what to put in their prompt.

## 0. Verified environment (do not re-derive)

**Machine-specific values live in `ORCHESTRATOR.local.md`, which is untracked.**
Read it first. It holds the absolute repo paths, usernames, WSL distro, model
endpoint and queue location for whichever machine you are on. This file holds the
protocol; that file holds the values.

If `ORCHESTRATOR.local.md` is missing (fresh clone), create it from this table:

| Fact | Value |
|---|---|
| Repo (single tree, Windows) | `<WINDOWS_REPO_PATH>` |
| Same path as WSL sees it | `<WSL_REPO_PATH>`, i.e. `/mnt/<drive>/...` |
| WSL distro | `Ubuntu-24.04` (noble). Never the `docker-desktop` distro |
| Windows user / WSL user | may DIFFER; `~` means different things per side |
| llama-server | `http://localhost:8081/v1` by default |
| Local model id | see `ORCHESTRATOR.local.md` |
| OpenCode | reachable from BOTH sides. Never assume; run `opencode_preflight` |
| Build wrapper (Windows to WSL) | `automation\win\sotn.cmd` (derives its own paths) |
| Baseline | Phase 0 green, 77/77 hashes, full build ~40-70s |
| Queue | `~/sotn-work/queue.jsonl` on the WSL side, NOT in the repo |
| Tier 0 worker | `automation/win/worker_direct.py` |
| Connectors | `sotn-local` (model bridge) and `sotn-cmd` (allowlisted actions) |
| Dry run | **OFF**. `sotn-cmd` executes for real: builds, writes, and commits land |

Never hardcode queue counts in any document; they go stale within minutes. Read
them with `python3 automation/scheduler.py stats` or the `queue_stats` tool.

Nothing in the harness should contain an absolute home path. Every script derives
the repo root from its own location, so the tree is portable. If you find a
hardcoded path, that is a bug.

There is ONE tree. Windows tools use it natively; WSL only compiles. Nothing is
ever synced. Never introduce a second copy.

## 1. Operating principle

Everything is verified programmatically. The operator does not know the decomp
domain, is not a reviewer, and must never be asked to judge a diff, confirm a
match, or approve a merge. Correctness is measured:

- Per function: asm-differ reports 100 percent, or it does not.
- Per build: all 77 hashes in `config/check.us.sha` reproduce, or they do not.

If you want to ask the operator a decomp question, that is a bug in the
automation. Close it with a check instead.

## 2. What you own

Baseline, queue, triage, delegation, structural decisions (headers, structs,
rodata, symbol naming), merging, rollback, and reporting. This is the operator's
own fork; make the call and record why.

## 3. What actually stops for the human

1. Placing disc images in `disks/` (ownership).
2. Interactive sudo during bootstrap; registering the two MCP connectors in
   Claude Desktop.
3. Flipping `SOTN_CMD_DRYRUN=0` once.
4. Spending decisions.
5. Whether to open upstream PRs.

Nothing else.

## 4. Dispatch protocol

### 4.0 The tools you actually have

Two MCP connectors are installed in Claude Desktop. Their tool names are long
and namespaced; use them exactly as written. If they are not in your tool list,
load them first with ToolSearch (they are deferred by default).

Model bridge (`sotn-local`) - reaches the local llama-server:

    mcp__SOTN_Local_Model_Bridge__health
    mcp__SOTN_Local_Model_Bridge__local_chat
    mcp__SOTN_Local_Model_Bridge__local_draft
    mcp__SOTN_Local_Model_Bridge__local_summarize_diff
    mcp__SOTN_Local_Model_Bridge__local_transform

Build and repo actions (`sotn-cmd`) - note the THREE underscores after
`allowlisted`:

    mcp__SOTN_Build_Commands__allowlisted___list_allowed
    mcp__SOTN_Build_Commands__allowlisted___make_build
    mcp__SOTN_Build_Commands__allowlisted___make_extract
    mcp__SOTN_Build_Commands__allowlisted___make_expected
    mcp__SOTN_Build_Commands__allowlisted___make_clean
    mcp__SOTN_Build_Commands__allowlisted___make_force_symbols
    mcp__SOTN_Build_Commands__allowlisted___make_function_finder
    mcp__SOTN_Build_Commands__allowlisted___make_reports
    mcp__SOTN_Build_Commands__allowlisted___make_duplicates_report
    mcp__SOTN_Build_Commands__allowlisted___asm_diff
    mcp__SOTN_Build_Commands__allowlisted___permuter
    mcp__SOTN_Build_Commands__allowlisted___permuter_import
    mcp__SOTN_Build_Commands__allowlisted___queue_stats
    mcp__SOTN_Build_Commands__allowlisted___queue_list
    mcp__SOTN_Build_Commands__allowlisted___git_status
    mcp__SOTN_Build_Commands__allowlisted___git_add_all
    mcp__SOTN_Build_Commands__allowlisted___git_commit
    mcp__SOTN_Build_Commands__allowlisted___read_file
    mcp__SOTN_Build_Commands__allowlisted___write_file
    mcp__SOTN_Build_Commands__allowlisted___list_dir
    mcp__SOTN_Build_Commands__allowlisted___search_repo

Start any session by calling `list_allowed`. It reports the live allowlist, the
repo path, and whether dry-run is on. Dry run is currently OFF, so every one of
these executes for real.

Your own Bash tool is a sandbox VM. It is NOT the build machine and has no
toolchain. Never run make, gcc, git, or the permuter there. Everything that
touches the real repo goes through `sotn-cmd`.

### 4.0b Running the volume fleet (you start it, not the operator)

The operator does not run scripts. Start, monitor, and stop the fleet yourself
with these tools:

    fleet_start(workers=4)        # launch, returns immediately
    fleet_status(tail=2)          # who is alive + last lines of each log
    fleet_stop()                  # kill workers, RELEASE their claims

What the fleet is: N detached `worker_direct.py` processes. Each claims a
function, prepares context (m2ctx + m2c), generates C with the local model,
applies it, builds, and checks the artifact hash. Matches are recorded with
proof automatically. It needs no help from you while running.

**Choosing a backend.** `fleet_start` runs either model tier, or both at once:

    fleet_start(workers=4)                                  # local llama (free)
    fleet_start(workers=4, backend="cli")                   # OpenCode Zen free
    fleet_start(workers=2, backend="mixed", cli_workers=2)  # both, one queue

llama is free and unlimited but has plateaued on what remains. The Zen free
models draw on an **account-wide** quota shared across every model, so N cli
workers drain it about N times faster and rotating models buys nothing. Spend
that quota deliberately: a mixed fleet puts it on functions llama has already
failed instead of ones llama would have matched anyway.

Any cli worker triggers a preflight; if the OpenCode CLI is not usable, NOTHING
starts, including the llama half. Check it independently with
`opencode_preflight()` before planning a run. Logs are per backend:
`worker-llama-N.log`, `worker-oc-N.log`. Details in
`automation/opencode/ZEN-FREE-MODELS.md`.

Rules that matter:

- **Always finish with `fleet_stop()`.** Workers are killed, not signalled, so
  they cannot release their own claims. Skipping this leaves records stuck in
  `claimed`, and every later run silently skips them. If you find stranded
  claims from an earlier session, `fleet_stop()` clears them too.
- **`workers=4` is the sane default.** Generation runs in parallel, but
  apply/build/verify is serialised by a lock (one repo, one build directory).
  Past ~4 the extra workers mostly wait on that lock. Raising it only helps if
  generation is much slower than the ~40-70s build.
- **llama-server must have slots**: `--parallel N` at least equal to `workers`,
  or generation serialises regardless. If unsure, `health` shows the endpoint;
  ask the operator to confirm the launch flags rather than guessing.
- **Poll, do not babysit.** Call `fleet_status()` every few minutes. A worker
  whose log tail has not moved in ~15 minutes is stuck: `fleet_stop()`, then
  restart with fewer workers.
- **Watch the hit rate.** `queue_stats()` before and after tells you whether the
  tier is earning its time. Observed on the small-function end of the queue:
  roughly half of attempts match.

While the fleet grinds `todo`, your own work is the `near` and `escalated`
backlog it produces. Do not compete with it for the build lock unnecessarily.

### 4.1 The rule that matters most

A subagent that has to figure out WHAT to work on, WHERE it lives, or HOW to
build will waste its budget doing that instead of the task. This is not
hypothetical: the OpenCode worker once burned a whole run calling
`read_mcp_resource` and hunting for a queue file because the prompt said "use
the sotn wrapper" and it inferred an MCP server named `sotn`.

Therefore every dispatch MUST include, resolved by you beforehand:
the exact file and line, the exact commands to run, and the exact output
contract. Never hand a subagent a function name alone.

### 4.2 Resolve the target before dispatching

Find the stub location yourself, using the `sotn-cmd` connector:

    search_repo(query="INCLUDE_ASM(.*<FUNC>)", path="src")

Record `source file`, `line`, and the INCLUDE_ASM first argument (the asm path).
If it does not resolve, the function may already be decompiled but non-matching;
read the file to confirm before dispatching.

### 4.3 Model routing

| Tier | Model | Use for | Cap |
|---|---|---|---|
| CPU | permuter (no model) | any `near` record, ALWAYS try first, costs no tokens | time-bounded |
| 2 | `model: haiku` | mechanical turns: build, diff, read first divergence, apply one edit class, rebuild | 15-20 iterations |
| 3 | `model: sonnet` | closing a near-match: compiler quirks, register allocation, stack layout, scheduling; running the permuter | 10-15 iterations |
| 4 | Opus (you) | header/struct/rodata decisions, symbol naming, anything the closer escalates | n/a |

Never send last-mile matching to haiku. Never send bulk mechanical turns to
sonnet. Escalate on cap, never loop.

### 4.4 How to spawn (Claude Desktop / Cowork)

Cowork does NOT use `.claude/agents/` auto-discovery or a `--agent` flag; those
are Claude Code CLI features. Spawn with the Agent tool, passing a model
override and the agent file body as the prompt:

- mechanical: Agent tool, `model: haiku`, prompt = body of
  `.claude/agents/sotn-mechanical-loop.md` + the task block from 4.5
- closing: Agent tool, `model: sonnet`, prompt = body of
  `.claude/agents/sotn-match-closer.md` + the task block from 4.5

Subagents inherit the `sotn-cmd` and `sotn-local` connectors. Keep verbose build
and diff output inside the subagent; only the compact summary comes back to you.

### 4.5 The task block (append verbatim, filling the placeholders)

    TASK: decompile ONE function to byte-identical machine code.

    build=us  overlay=<OVERLAY>  function=<FUNC>

    Target location (already resolved, do not search):
      source file : <SRC_FILE>
      line        : <LINE>
      current stub: INCLUDE_ASM("<ASM_REL>", <FUNC>);
      original asm: asm/us/<ASM_REL>/<FUNC>.s

    Replace that stub with C, in the same position in the file. Function order
    affects output.

    Run everything through the sotn-cmd connector (these are tools, not servers):
      build : make_build(version="us")
      diff  : asm_diff(symbol="<FUNC>", version="us", overlay="<OVERLAY_SHORT>")
      commit: git_add_all() then git_commit(message="match us:<OVERLAY>:<FUNC>")
    Never run make or gcc in a shell: in Cowork the shell is a sandbox without
    the toolchain. If the connected folder is not the WSL tree, read and write
    source with read_file / write_file from the same connector.

    Iteration cap: <CAP>. Apply ONE edit class per iteration, in this order:
    types, control-flow shape, locals/stack usage, operation ordering. Revert
    anything that lowers the score.

    Do NOT look for an MCP resource named "sotn", a task queue, or config files.
    Everything you need is above.

    Return ONLY this summary (keep build/diff output in your own context):
      status: matched | near | blocked | escalate
      score: <best asm-differ percentage>
      first_divergence: <file/line or instruction, and the one-line cause>
      changed: <the edit classes you applied>
      next: <what you would try next>

### 4.6 Trust is structural. Do NOT re-verify per function.

Verifying every handoff yourself would make you the bottleneck and burn a full
build per function. That defeats the purpose. Instead the pipeline is built so
an unverified result cannot exist:

- `scheduler.py report --status matched` is REFUSED without `--proof`. Try it:
  it exits 1 and tells you to report `near` or `escalated` instead.
- The only thing that produces valid proof is `worker_direct.py`, which builds
  the target and checks the artifact's SHA-1 against `config/check.<v>.sha`
  before reporting. It records the actual hash and a `verified_at` timestamp.
- Therefore `status == "matched"` is a machine fact, not a model claim. Read it
  and move on.

So: `queue_stats()` and `queue_list(status="matched")` are sufficient. Do not
rebuild to confirm someone else's match.

Two places verification still happens, both automated and neither yours:

1. Per function, inside the worker, before the record can be written.
2. At merge, in `merge_verified.py`, which rebuilds and re-checks every hash
   after each merge and rolls back on regression. This catches interactions
   between individually-correct functions, which per-function checks cannot.

You verify by exception only: if `merge_verified.py` rolls something back, or a
record reaches `matched` with an empty `proof` field (which should be
impossible), investigate that specific record. Never sample-audit the rest.

If you ever add a new path that can set `matched`, it must supply proof the
same way, or this whole property collapses.

### 4.7 Queue operations

    queue_stats()                     # counts by status
    queue_list(status="near")         # candidates for the permuter
    queue_list(status="escalated")    # candidates for you

Workers claim and report through `automation/scheduler.py`, which is the single
writer. Never hand-edit `work/queue.jsonl`. Reclaim crashed workers with
`scheduler.py reclaim --older-than-min 60`.

### 4.8 Merging

    python3 automation/merge_verified.py run --into integration

The gate is automatic: after each merge the full build must still reproduce
every hash, or the merge is rolled back with `git reset --hard` and the function
is flipped to `escalated` with the reason. Never merge by hand, and never ask
the operator to approve one.

## 5. The loop

    phase0.sh green
      -> seed queue
      -> Windows OpenCode workers grind Tier 0/1, reporting matched/near/escalated
      -> you: permuter on every near (free)
      -> you: haiku subagent for mechanical turns (task block 4.5)
      -> you: sonnet subagent to close (task block 4.5)
      -> you: structural decisions when the closer escalates
      -> you: verify independently (4.6), then merge_verified (4.8)
      -> report progress, repeat

## 6. Honest limits

- Not every function will match. Parking one as `escalated` with a diagnosis is
  a correct outcome. Cap and move on.
- "Automated end to end" means it runs unattended and parks what it cannot
  solve. It does not mean the target reaches 100 percent.
- 441 `us` functions remain, concentrated in ST/RNO0 (219), BOSS/BO6 (123),
  BOSS/BO0 (67), ST/RCEN (23). Report progress against that, honestly.
- The local model is ~3B active. It is for volume and mechanical transforms, not
  the last mile. Do not queue hard functions to it expecting matches.

## 7. Known divergence between this document and the implementation

Recorded 2026-07-19. These are places where the protocol above is correct but the
harness does not yet enforce it. Do not assume the ladder runs itself.

### 7.1 The escalation ladder dead-ends at Tier 0

`4.3 Model routing` defines CPU -> haiku -> sonnet -> Opus. Only Tier 0/1 is
implemented. `automation/win/worker_direct.py` is llama-only: after
`MAX_ATTEMPTS` it writes `escalated` and stops. **Nothing consumes `escalated`.**
There is no automated haiku or sonnet rung.

Consequence: escalated records accumulate untouched until an orchestrator picks
them up by hand, which is exactly the token waste the tiering exists to prevent.
On 2026-07-19 all 15 escalations sat at `tier_reached=0`.

Until a Tier 2/3 consumer exists, the orchestrator must dispatch it explicitly:
parallel haiku subagents for analysis, then sonnet for whatever haiku fails, and
only then Opus. Every `Agent` call MUST pass an explicit `model`, or the subagent
inherits Opus and burns Tier 4 on mechanical work.

### 7.2 The permuter has never been run

`4.3` marks the permuter mandatory-first and free. `tools/decomp-permuter` is
installed and the connector exposes `permuter` and `permuter_import`, but:

- no permuter work directory has ever been created
- `grep permuter automation/win/worker_direct.py automation/scheduler.py` returns
  nothing; the worker has no concept of it

Note the sequencing lesson from 2026-07-19: the permuter searches for a byte-exact
variant of an already-compiling function. It cannot fix a wrong parameter type or a
missing shared implementation, because neither is a search problem. Both matches
that day came from the cheaper structural and type causes in
`MATCHING-LESSONS.md` sections 1 and 2. Exhaust those first, then permute the
residue.

### 7.3 Parallel agents must not build

`BuildLock` in `worker_direct.py` serializes apply/build/verify. The connector's
`make_build` does NOT take that lock. Parallel subagents that build will interleave
and misattribute each other's failures. Parallelize analysis, serialize the build.

### 7.4 Harness defects fixed 2026-07-19

- **Queue locking was unsound.** `scheduler.py transaction()` locked the queue file
  itself while `_write()` replaced that file via `os.replace`, so the lock was held
  on a stale inode and the next process locked the new one and entered the critical
  section concurrently. Additionally every process wrote the same temp filename.
  Under load on `/mnt/c` this killed 2 of 4 fleet workers with `FileNotFoundError`.
  Fixed with a dedicated never-replaced `queue.jsonl.lock` and per-PID temp files.
  Reproduced at 8 workers: old code 8 tracebacks and 20 of 40 claims, new code 40 of
  40 and zero tracebacks.
- **Error truncation hid the cause.** `sched()` raised `RuntimeError(out[:300])`,
  cutting off the stack trace and concealing the above for an entire session. Now
  logs the full stderr.
- **Reasoning cap widened 1200 -> 2000.** Clean generations land at 490-870 reasoning
  tokens; 1200 was clipping the slower productive tail into the forced-code path.
  Runaway loops are still caught independently by `degenerating()`.

### 7.6 The queue does NOT live in the repo (2026-07-20)

The repo sits under a cloud-synced folder (Proton Drive on `Documents\`). Every
scheduler transaction rewrites the queue via `os.replace`, creating a new inode;
under a running fleet that is hundreds of replacements per session. The sync
daemon lost that race, renamed the live file to
`queue (# Name clash 2026-07-20 ... #).jsonl` and left a zero-byte
`work/queue.jsonl`. The harness saw an empty queue while a 4-worker fleet ran
against it. Recovered intact: 438 records, 0 corrupt lines.

The queue now defaults to `~/sotn-work/queue.jsonl`, a WSL-native path outside the
synced tree. Override with `SOTN_QUEUE`.

Migration is automatic and per-environment. The fleet, the MCP connector and any
local shell may run in **different environments that share only the `/mnt/c` repo
mount**, so a home-directory path is not shared between them and cannot be seeded
remotely. `scheduler.py` therefore migrates its own copy on first touch: if the new
path is missing and the legacy in-repo file has records, it copies across and logs
to stderr. The legacy file is never deleted; it stays as a recovery point.

Anything else the harness rewrites at high frequency must also stay out of the
synced tree. Source files are fine, they are written rarely.

### 7.7 A deliberate fleet_stop is sticky (2026-07-20)

`fleet_stop(hold=True)`, the default, writes `automation/logs/FLEET_HOLD`. While
that file exists `fleet_start` refuses and returns `held=True`.

This exists because an unattended watchdog with authority to start work will
restart a fleet a human stopped on purpose, then mutate the queue underneath them.
A crashed fleet never calls `fleet_stop`, so no sentinel exists and automatic
recovery still works. Only a deliberate stop is sticky.

- Human asked for a stop: `fleet_stop()` (hold set).
- Watchdog recycling a crashed fleet: `fleet_stop(hold=False)` then `fleet_start()`.
- Resuming after a deliberate stop: `fleet_start(force=True)`, on explicit human
  instruction only. Automated callers must never pass `force`.

Note: `commands_client.py` is imported once when the MCP server starts, so changes
to it require restarting Claude Desktop before the new parameters are exposed.

### 7.8 'matched' is now verified by the scheduler, not asserted by the caller (2026-07-20)

The original invariant only checked that `--proof` was a non-empty string. That is
not proof. The expected hashes live in `config/check.<v>.sha`, which any agent can
read without compiling anything, so a caller could compose a flawless proof line
having done no work. Section 4.6 asks the orchestrator to trust the queue without
re-verifying, and that trust was resting entirely on agents choosing to be honest.

`scheduler.py report --status matched` now recomputes every artifact hash in
`config/check.<v>.sha` from the bytes on disk, at the moment the claim is recorded,
and refuses the report if the tree is not byte-exact. Accepted claims get
`[scheduler-verified: N/N artifacts byte-exact]` appended to their proof.

Verified behaviour:
- green tree, proof text "asserted without evidence" -> accepted, annotated
- one artifact corrupted, proof text citing the correct expected sha1 -> REFUSED
- `near` and other statuses -> unaffected, still need no proof

Caveat worth knowing: this proves the tree is green when the claim is made, not that
this particular function caused it. Combined with `BuildLock` serialising
apply/build/verify, that is strong in practice. It is not a substitute for one
function at a time.

Implementation note: `config/check.us.sha` contains **mixed-case** hex (CHI.BIN is
written `4ea14c8B54B8...B336a2`). `hexdigest()` is lowercase, so the comparison must
be case-insensitive. A case-sensitive compare silently rejects good artifacts.

### 7.9 Subagents do not reliably respect "analysis only"

On 2026-07-20 four haiku subagents were told, explicitly and repeatedly, to use only
Read/Grep/Glob and to run no builds and make no edits. All four instead edited source,
built, verified and filed queue reports. **The work was genuine and independently
confirmed at 77/77**, but the constraint was ignored.

Treat prompt-level restrictions as guidance, not a sandbox. If concurrent edits or
builds would be unsafe, do not rely on telling agents to abstain; either dispatch one
agent at a time, or make the unsafe path structurally impossible. This is also why
7.8 matters: the guard has to live in the single writer, not in the instructions.

### 7.5 Matching heuristics live in MATCHING-LESSONS.md

Evidence-backed heuristics that have produced verified matches. Prime Tier 0-3
agents with sections 1 to 3 of that document; those three checks accounted for
every match obtained on 2026-07-19.
