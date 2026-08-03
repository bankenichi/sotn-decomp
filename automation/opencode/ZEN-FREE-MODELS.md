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

## Is it concurrency throttling? No, on three independent checks

A reasonable hypothesis: Zen free is unauthenticated, so maybe it throttles
concurrent streams and our timeouts are really queueing. Checked 2026-08-03.

**1. We have never been rate-limited, once.** Zero occurrences of `429`,
`rate limit`, `FreeUsageLimitError`, `usage exceeded` or `too many requests`
across every worker log and archive. A throttled call says so; ours just
return empty or run the clock out.

**2. We are already an "official client".** earendil-works/pi#2824 documents
that the Zen backend distinguishes clients by header: without
`x-opencode-client: cli` and friends, requests are treated as anonymous and get
`fallbackValue` limits instead of `dailyRequests`. That issue is about a THIRD
PARTY tool missing those headers. We shell out to the real `opencode run`
binary, so we send them by construction. This is a bug we do not have.

**3. Dead rate does not rise with worker count.** If concurrency were the
cause, more workers would mean more dead calls. The opposite:

| workers | calls | dead% |
|---|---|---|
| 3 | 25 | 72% |
| 4 | 110 | 71% |
| **13** | 24 | **50%** |

The 13-worker run has the LOWEST dead rate. That is confounded by date and
model mix, so it does not prove concurrency helps -- but it rules out
concurrency as the driver, because the effect points the wrong way.

### What the same data does support

Comparing two 4-worker runs on the SAME day, differing only in prompt size:

| run | workers | prompt | dead% |
|---|---|---|---|
| 20260803-165330 | 4 | uncompacted | **76%** |
| current | 4 | compacted | **44%** |

Concurrency held constant, prompt size cut by ~60%, dead rate down 32 points.
Small sample (18 calls) and worth re-checking as the archive fills, but it is
the same direction as the prompt-size correlation and the only variable that
changed.

Rate limits on Zen ARE real and are reported even on paid models
(anomalyco/opencode#13318), so this may still bite later. It is simply not
what is happening to us now.

## RETRACTION 2026-08-03: three "do not use" verdicts were wrong

`empty_response_audit.py` over 20 logs and 123 calls, with logs now archived
rather than deleted:

| model | calls | empty | timeout | ok | dead% |
|---|---|---|---|---|---|
| ling-3.0-flash-free | 32 | 20 | 0 | **10** | 62% |
| mimo-v2.5-free | 29 | 12 | 7 | 7 | 66% |
| nemotron-3-ultra-free | 25 | 2 | 16 | 4 | 72% |
| north-mini-code-free | 19 | 3 | 9 | **2** | 63% |
| deepseek-v4-flash-free | 10 | 5 | 4 | **0** | 90% |
| laguna-s-2.1-free | 8 | 0 | 6 | **1** | 75% |

**`ling-3.0-flash-free` is the best model measured**, not a do-not-use model.
Ten real generations, zero timeouts, and the fastest productive median at 68s.
This file called it "New 2026-08; rc=0 with 0 chars" on the strength of a
handful of calls. `laguna-s-2.1-free` and `north-mini-code-free` also produce C.

Meanwhile **`deepseek-v4-flash-free`, the model this file tells you to run, is
the worst in the set**: 10 calls, zero successes, 90% dead.

That is now three model verdicts overturned by counting, all from the same
mistake: a small sample repeated until it sounded like a fact. The operational
rule below is left in place as a record but should not be followed; run
`empty_response_audit.py` and use the table it prints.

## Timing: the real lever is the timeout, not the model

| | n | min | median | p75 | p90 | max |
|---|---|---|---|---|---|---|
| produced | 24 | 30s | **70s** | 122s | 249s | 374s |
| dead | 86 | 48s | **347s** | 382s | 382s | 382s |

The two populations barely overlap. Productive work finishes fast; dead work
runs the clock out, and almost every dead call sat exactly at the 382s ceiling.

| cap | good calls lost | dead time saved |
|---|---|---|
| 120s | 6/24 | 226m |
| 180s | 4/24 | 168m |
| 300s | 2/24 | 59m |

`FUNC_BUDGET` on the cli backend is now **900s** (was 1800s), giving ~191s per
attempt instead of 382s. That covers p75 of productive calls and removes roughly
160 of the 383 wasted minutes. A cut good call is not a lost function: a record
with no candidate is requeued to `todo` and retried, so the cost is a retry.

Refresh all of this with:

```
run_analysis(script="empty_response_audit.py", args="--timing --by-prompt-size")
```

## Measured waste, 2026-08-03

Run `python3 automation/empty_response_audit.py --by-prompt-size` to refresh.
Over 17 worker logs and 54 model calls:

| model | calls | empty | timeout | ok | dead% | wasted | useful |
|---|---|---|---|---|---|---|---|
| nemotron-3-ultra-free | 22 | 2 | 14 | 3 | 73% | 96.7m | 10.1m |
| north-mini-code-free | 19 | 3 | 9 | 2 | 63% | 60.6m | 1.6m |
| mimo-v2.5-free | 7 | 1 | 1 | 3 | 29% | 11.0m | 9.6m |
| deepseek-v4-flash-free | 6 | 3 | 2 | 0 | 83% | 23.3m | 0.0m |

**90% of all model time produced nothing.** 191.7 minutes wasted against 21.2
minutes of useful generation.

Two things this overturns:

**The dominant failure is TIMEOUT, not an empty body.** 26 timeouts against 9
empty responses. Those are different faults needing different fixes, and
lumping them together as "coming up empty" points at the wrong lever.

**Prompt size predicts it almost perfectly:**

| prompt | calls | dead | dead% |
|---|---|---|---|
| 0-5k | 3 | 0 | **0%** |
| 5-10k | 35 | 22 | 63% |
| 10-20k | 16 | 13 | **81%** |

This is the same variable that broke the argv path, and it still dominates now
that the prompt goes on stdin. Size is the lever, not model choice.

### Mitigations, by expected value

1. **Shrink the prompt.** Nothing under 5k chars has ever failed. The m2c draft
   and the twin section are the two largest blocks and the draft is the more
   expendable. Highest value by a wide margin.
2. **Cut the per-attempt timeout.** 382s x 4 attempts is 25 minutes to learn
   nothing. At 5-10k the failure rate is 63%, so most of that budget buys
   nothing. A 120s cap loses few real generations and returns the function to
   the queue three times sooner.
3. **Route by size.** Send >10k-char prompts to llama, or hold them for a
   human. On the cli tier they are 81% dead.
4. **Circuit-break a failing model.** N consecutive dead calls should retire
   that model for the run rather than spending the account-wide pool on it.
5. **Do NOT re-rank models on this table yet.** deepseek shows 83% dead on six
   calls and mimo 29% on seven. Both are under the 10-call line, and this file
   already records one wrong model conclusion drawn from exactly that kind of
   unbalanced tally.

### Queue damage: none

Worth stating because it is the natural worry. `worker_direct.py:3238` already
requeues a function to `todo` when no candidate was produced, so a broken model
cannot escalate work it never evaluated. Confirmed live in the logs:
`[worker] REQUEUE BO6_RicStepSlide: no candidate produced in 4 error(s); back
to todo`. The cost of an empty response is time and quota, not queue state.

### Logs are now archived, not deleted

`fleet_start` used to `rm -f` each worker log before relaunching, which is why
the first audit could see only 4 logs. Non-empty logs now move to
`automation/logs/archive/<timestamp>/` on launch, so history accumulates.
Archiving happens on START rather than on stop deliberately: logs stay readable
in place after a stop, and are preserved the moment the next run begins, so
nothing is ever lost either way.

## Free models (2026-07-20)

All at `https://opencode.ai/zen/v1/chat/completions`:

| Model ID | Notes |
|---|---|
| `big-pickle` | **DO NOT USE.** Empty body on real prompts. |
| `deepseek-v4-flash-free` | **USE THIS.** Best of the set; tolerates 12k prompts. |
| `nemotron-3-ultra-free` | **USE THIS.** Produces real C, retries cleanly. |
| `mimo-v2.5-free` | lower volume but produces real C |
| `north-mini-code-free` | **DO NOT USE.** Empty body; also streams tool-call roleplay. |
| `ling-3.0-flash-free` | **DO NOT USE.** New 2026-08; `rc=0` with 0 chars. |
| `laguna-s-2.1-free` | **DO NOT USE.** New 2026-08; no output at all. |

### RESOLVED 2026-08-02: it IS model-specific, and the fix is model choice

A 4-worker cli fleet run one model per worker, on real queue functions, split
the free tier cleanly in two:

| Model | Prompt | Result |
|---|---|---|
| `nemotron-3-ultra-free` | 5180 | **real C in 145s**, compiled, checksum failed, retried |
| `deepseek-v4-flash-free` | 6089 | **real C in 213s**, clean and commented |
| `ling-3.0-flash-free` (new) | 9936 | `rc=0`, **0 chars** after 93s |
| `laguna-s-2.1-free` (new) | 11249 | **nothing at all** after 7+ minutes |

So the harness was never broken. `worker_direct.py` streams, echoes, hoists C89
declarations, compiles and checksums exactly as designed; the entire pipeline
was being fed by models that return an empty body.

This also retracts the "Not the model" line below, which was wrong. It was
inferred from `big-pickle` and `north-mini-code-free` failing identically, and
identical failure across two members of the SAME class is not evidence that the
class does not exist. The 2026-07-21 bake-off had it right the first time.

### The SECOND cause: the 32767-char Windows command-line limit

Model choice was only half of it, which is why this resisted diagnosis for so
long. `opencode` here is a Windows `.exe` invoked from WSL, and the prompt was
passed as an argv element, so the whole command line had to fit inside Windows
`CreateProcess`'s 32767-character limit. Past that the process never started.

Bisected with `automation/opencode_size_bisect.py` on 2026-08-02, one model,
same two-character question at every size, varying only length:

| Prompt | on argv | on stdin |
|---|---|---|
| 32000 | ok, 7.7s | ok |
| 32700 | `rc=1 opencode.exe: Invalid argument` in **0.0s** | ok |
| 40000 | `Invalid argument` | ok, 7.0s |
| 80000 | `Invalid argument` | ok, 7.6s |
| 120000 | `Invalid argument` | ok, 10.2s |

A failure to *exec* looks exactly like a model returning an empty body, which is
what sent four earlier investigations at quota, auth, agent resolution and
stdout routing.

This mattered far more than the 6k-11k prompts we happened to observe suggested.
Measured over the 308 us functions still on `INCLUDE_ASM` (the worker feeds the
`.s` verbatim, so asm chars == raw file size):

```
p50 asm  8.8k -> ~13k prompt      59% of remaining exceed 32767
p75 asm   21k -> ~29k prompt      37% exceed 20k
p90 asm   41k -> ~55k prompt      15% exceed 40k
max asm  120k -> ~156k prompt     func_us_801B365C, 1974 instructions
```

So on argv, the majority of the remaining work was unreachable by any model.
`worker_direct.py` now pipes the prompt on stdin, writing from its own thread
and closing the pipe afterwards. Do not move it back onto argv.

Re-check any of this with:

```
run_analysis(script="opencode_size_bisect.py", args="--top 3 --big")
run_analysis(script="opencode_size_bisect.py", args="--top 1 --stdin --big")
```

**Operational rule: run cli fleets on `deepseek-v4-flash-free` and
`nemotron-3-ultra-free` only.** Both new promotions are in the failing class, so
"it's new, try it" is not a reason to add a model to a fleet.

### Original diagnosis, kept for the reasoning trail

**This is NOT model-specific.** An earlier version of this note blamed
`big-pickle` on the strength of a per-model tally of empty responses. That tally
was confounded: `big-pickle` simply had 16 runs to the others' 2-4, so it
accumulated more visible failures. Switching the default to
`north-mini-code-free` and relaunching reproduced the failure exactly:

```
worker-oc-1  north-mini-code-free  11249 chars -> done in 103s: 0 chars
                                   11373 chars -> done in  50s: 0 chars
                                   11373 chars -> done in  48s: 0 chars
                                   11373 chars -> timeout 382s  (x2)
worker-oc-2  north-mini-code-free   9936/10060 chars -> timeout 382s (x4)
worker-oc-3  north-mini-code-free   6089/6213  chars -> timeout 382s (x4)
```

Every call either exits `rc=0` with zero bytes or hits the 382s timeout. Twelve
attempts, three functions, zero output.

Ruled out, with evidence. Do not revisit these:

- **Not quota.** A throttled call does not run 250s and exit 0, and it would not
  affect two different models identically.
- **Not auth or config.** stderr shows `> raw · north-mini-code-free`, so the
  `raw` agent and the model both resolved.
- **Not the CLI's stdout routing.** By hand it answers normally:
  `opencode run --model opencode/big-pickle --agent raw --auto "Reply with the
  single word OK"` prints `OK` with `rc=0`.
- **Not the model.** Both `big-pickle` and `north-mini-code-free` fail the same
  way on the same prompts.

The one variable that tracks the failure is PROMPT SIZE. A 27-character prompt
answers instantly; every prompt in the 6k-11k range that a real function
generates returns nothing. The next step is to bisect on size alone, holding the
model and agent fixed:

```bash
cd /mnt/c/Users/kenic/Documents/SOTN-Decomp
for n in 500 2000 4000 6000 9000; do
  p=$(python3 -c "print('Reply with the single word OK. ' + 'x'*$n)")
  printf '%6s chars: ' "$n"
  OPENCODE_CONFIG=automation/opencode/opencode.json \
    timeout 120 opencode run --model opencode/north-mini-code-free \
      --agent raw --auto "$p" </dev/null | head -c 40
  echo "  rc=$?"
done
```

If it breaks at a threshold, the fix is to shrink the prompt (the twin section
and the m2c draft are the two largest blocks and the draft is the more
expendable) or to pass the prompt on stdin rather than argv. If every size
answers, the trigger is prompt CONTENT, and the next bisect is over the prompt
sections rather than their length.

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
