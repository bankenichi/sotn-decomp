# Running the fleet on OpenCode Zen free models

The local llama fleet stopped producing matches. This switches the volume tier to
OpenCode Zen's free hosted models. Verified against the Zen docs on 2026-07-20.

## Why this needed almost no code

`worker_direct.py` already speaks the OpenAI chat-completions shape, and every
Zen free model is served through `@ai-sdk/openai-compatible` at the same endpoint.
So the switch is environment variables, not a rewrite.

Two things WERE missing and have been added:

- `MODEL_API_KEY` -> sent as `Authorization: Bearer <key>`. Local llama needed no
  auth, so the worker never sent a header and any hosted endpoint would have
  returned 401.
- Rate-limit handling. Free tiers throttle; local llama never did. The worker now
  retries on 429 and 5xx with linear backoff, honouring `Retry-After`.
  Tunable via `RATE_LIMIT_RETRIES` (default 5) and `RATE_LIMIT_BACKOFF` (default 20s).

## Free models (2026-07-20)

All at `https://opencode.ai/zen/v1/chat/completions`:

| Model ID | Notes |
|---|---|
| `big-pickle` | stealth model, free for a limited time |
| `deepseek-v4-flash-free` | free for a limited time |
| `mimo-v2.5-free` | free for a limited time |
| `north-mini-code-free` | Cohere-backed |
| `nemotron-3-ultra-free` | NVIDIA trial endpoints |

These are time-limited promotions. If a model 404s, re-check
<https://opencode.ai/docs/zen/> and refresh this list.

## Setup

Use the installed CLI. **No API key and no billing are required.** Verified
2026-07-20: `opencode auth list` reported **0 credentials** and
`opencode run --model opencode/big-pickle` still answered.

```bash
export MODEL_BACKEND=cli
export OPENCODE_MODEL=opencode/big-pickle
python3 automation/win/worker_direct.py once     # smoke test ONE function first
```

Then start the fleet from the same shell. Optional but worth it for a fleet: run
`opencode serve` in another terminal and set
`OPENCODE_ATTACH=http://localhost:4096` so each call skips MCP cold boot.

Because these are hosted, the local `--parallel` constraint is gone. The Zen
usage limit is the binding constraint now, not VRAM.

## Launching a cli or mixed fleet from the connector

`fleet_start` takes a `backend` parameter, so no terminal is required:

```
fleet_start(workers=4, backend="cli")                     # 4 OpenCode workers
fleet_start(workers=2, backend="mixed", cli_workers=2)    # 2 llama + 2 OpenCode
fleet_start(workers=4, backend="cli", opencode_model="opencode/hy3-free")
```

Workers are named and logged by backend, so a mixed run stays legible:
`automation/logs/worker-llama-N.log` and `worker-oc-N.log`. Both shapes are
picked up by `fleet_status` and reaped by `fleet_stop`.

Env is set per worker on the command line, not exported once for the whole
launch. That matters for `mixed`: a single export would give every worker
whichever `MODEL_BACKEND` was set last, silently making a "mixed" fleet
uniform. This was the original defect, where `fleet_start` passed only
`WORKER_NAME` and so could never launch anything but llama.

### Preflight

Any `cli` worker triggers a preflight first (`opencode_preflight`, or
`worker_direct.py preflight`). If the CLI is not usable, **nothing** starts,
including the llama half of a mixed fleet.

This is not politeness. A cli worker that cannot reach the CLI still claims a
queue record and fails every attempt, marking the function `escalated` for
reasons that have nothing to do with the function. Four such workers poison the
queue faster than they fail. Check once, refuse, start nothing.

### Binary resolution

The worker resolves the CLI via `resolve_opencode()`, trying bare `opencode`
first and falling back to `opencode.cmd` / `.CMD` / `.exe` / `.bat`. Override
with `OPENCODE_BIN` (an absolute path is trusted as given).

The fallbacks exist because WSL appends the Windows PATH but has no `PATHEXT`,
so an extensionless name will not match a `.CMD`. A native Linux install of
OpenCode inside WSL resolves on the first candidate and never reaches them.

### Parallelism and shared quota

The Zen limit is account-wide (see below), so `cli_workers` divides one pool
rather than multiplying throughput: 4 workers exhaust the day's quota roughly 4x
sooner. Prefer fewer cli workers running longer unless you are deliberately
spending the pool in one sitting.

A mixed fleet is the useful shape here: llama is free and unlimited but has
plateaued, so pairing a couple of llama workers with a couple of cli workers
spends scarce quota on functions llama has already failed rather than on ones it
would have matched anyway.

### Model triage (bake-off, 2026-07-21)

Six models were run one-per-worker against comparable functions. They split hard
into working and useless. Use only the working three; the others waste
account-wide quota producing nothing.

WORKING (produce real C, stream cleanly):
- `opencode/deepseek-v4-flash-free` - best of the set. Streamed 132 lines of C
  and tolerated even a 12k-char prompt that made big-pickle drop empty.
- `opencode/nemotron-3-ultra-free` - streams, produces candidates.
- `opencode/mimo-v2.5-free` - lower volume but produces real C.

USELESS (do not use):
- `opencode/big-pickle` - returns rc=0 with EMPTY output on large prompts
  (gateway drop). Zero candidates.
- `opencode/hy3-free` - server-side `UnknownError` (rc=1) on nearly every call;
  80 errors in one run. Broken or overloaded upstream, not a harness fault.
- `opencode/north-mini-code-free` - a Cohere tool-trained model that ignores
  "emit only C" and streams tool-call roleplay (`<function=read_file>` ...)
  instead of a function. clean_code cannot rescue it. Not fixable by prompt.

Streaming NOTE: contrary to an earlier claim in this file, `opencode run` DOES
stream to stdout incrementally in a non-TTY. worker_direct.py now reads it via
Popen, so the degeneration detector and live echo work on the cli backend too.
See the "What the CLI backend gives up" section, now largely obsolete.

Launch the survivors:

```
fleet_start(workers=3, backend="cli", force=true,
  opencode_model="opencode/deepseek-v4-flash-free,opencode/nemotron-3-ultra-free,opencode/mimo-v2.5-free")
```

### The HTTP path still works

`MODEL_BACKEND=http` (the default) keeps the original OpenAI-compatible path for
local llama-server, unchanged. `MODEL_API_KEY` exists for hosted OpenAI-compatible
endpoints but is NOT needed for the CLI route; leave it unset.

### What the CLI backend gives up

`opencode run` returns output only when the run completes, so there is no token
stream. The live degeneration detector and `REASON_CAP` both watch that stream and
are inert on this backend. `FUNC_BUDGET` (default 900s) is the only remaining
guard against a wedged generation. If a model loops, lower `FUNC_BUDGET` rather
than trying to restore streaming.

### Usage limits

Free models DO have a usage limit; exceeding it returns
`Free usage exceeded, add credits`.

Whether that limit is shared across all free models or is per-model is NOT
documented anywhere we could find. The error is account-scoped in wording and
points at adding credits, which suggests shared, but this is unconfirmed.

Cheap way to settle it: when one model reports the limit, immediately try a
different free model. If it also refuses, the limit is shared and rotating models
is pointless. If it answers, limits are per-model and rotation buys more runs.

## Do NOT rotate models to farm quota

The Zen rate limit is account-wide, shared across every model. Switching models
does not grant fresh quota; it only changes which model spends the same pool.

So the goal is not "run each model dry". It is: find the model that matches best
at this task, then spend the whole shared quota on that one.

### Picking the model

Run a short bake-off on a handful of functions of KNOWN difficulty, then commit.
The bake-off costs quota, so keep it small: 3 functions across 3 candidates is
enough signal without burning the budget.

Use functions we have already solved by other means as the yardstick, because we
know they are matchable and we know what the answer looks like. A model that
cannot reproduce a function we already matched by hand is not going to do better
on the 44 unsolved ones.

Record the model in each queue record's `notes` so hit rate per model stays
measurable rather than anecdotal.

### Live model list

Verified with `opencode models opencode` on 2026-07-20. Note this differs from the
published docs, which omit `hy3-free`:

```
opencode/big-pickle
opencode/deepseek-v4-flash-free
opencode/hy3-free
opencode/mimo-v2.5-free
opencode/nemotron-3-ultra-free
opencode/north-mini-code-free
```

Always trust `opencode models opencode` over the docs page.

## Privacy, read before running

Every model on the free tier collects data. Per Zen's docs, Big Pickle,
DeepSeek V4 Flash Free, MiMo V2.5 Free, North Mini Code Free and Nemotron 3 Ultra
Free all retain requests to improve the models. North Mini Code and Nemotron
explicitly say not to submit confidential data.

For this project the payload is MIPS assembly and C from a public decompilation
repo, so there is nothing personal in it. Just do not point this harness at
anything private while a free model is selected.

## Expectation setting

The local model plateaued because the remaining work is genuinely hard, not
because the model was slow. Of the 307 `todo` records, the cheap structural wins
are already gone (see MATCHING-LESSONS.md sections 1 and 1a). A stronger hosted
model may lift the hit rate, but the 72 functions rejected for raw-address data
references will not yield to any model, because that failure is structural.
