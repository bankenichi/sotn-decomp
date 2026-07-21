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
