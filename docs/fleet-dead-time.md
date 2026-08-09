# Fleet dead time: diagnosis and plan

**Status:** diagnosis complete enough to act; fix not yet implemented.
**Do not run the fleet until Phase 1 lands.** A run today burns quota and
produces logs that cannot answer the remaining question.

---

## 1. What is actually happening

Measured with `automation/fleet_forensics.py` over 1042 recorded calls
(2026-08-03). Every number below comes from replaying logs already on disk.

| outcome | count | share | meaning |
|---|---:|---:|---|
| produced | 96 | 9% | a candidate came back |
| empty | 154 | 15% | rc=0 and zero bytes |
| **timeout_no_bytes** | **724** | **69%** | **cut off having streamed nothing** |
| timeout_complete | 2 | 0% | cut off, answer already whole |
| genfail | 24 | 2% | raised before finishing |
| abandoned | 42 | 4% | fleet stopped mid-call |

**878 of 946 dead calls, 93%, returned not one byte.**

This is the finding. It is not a model-quality problem. It is not the prompt
being too long to read, not the model rambling past the deadline, not
truncation. The overwhelming majority of requests never yield a single token.
No prompt engineering changes the behaviour of a request that produces no
output.

### What it rules out

| hypothesis | test | result |
|---|---|---|
| Slow warm-up / session init | success rate of the first call in each log | 12% vs 10% overall. **No.** |
| The model rambles past the cap | how many timeouts held a complete answer | 2 of 726. **No.** |
| Output arrives but we mishandle it | how many timeouts held *any* text | 0 partial, 2 complete. **No.** |
| A session breaks and stays broken | mean consecutive-failure run vs chance | **Bursty on both readings**: 12.8 vs 9.9 expected counting everything, 12.4 vs 9.2 counting only real model answers. Not an outlier artefact — dropping the single longest run of 81 still leaves 11.9. **This is the live hypothesis.** |

### Per-model shape (this matters)

| model | produced | empty | timeout_no_bytes | genfail |
|---|---:|---:|---:|---:|
| mimo-v2.5-free | 36 | 22 | 179 | 0 |
| ling-3.0-flash-free | 22 | **101** | 66 | 1 |
| nemotron-3-ultra-free | 10 | 4 | 116 | 5 |
| laguna-s-2.1-free | 15 | 3 | 106 | 1 |
| deepseek-v4-flash-free | 3 | 10 | 106 | 0 |
| north-mini-code-free | 9 | 7 | 80 | 1 |
| big-pickle | 1 | 7 | 71 | 0 |
| hy3-free | 0 | 0 | 0 | **16** |

`ling-3.0-flash-free` is the outlier: it fails **empty** (fast, rc=0) where
every other model fails by **timeout** (slow, silent). Two different provider
behaviours. `hy3-free` is 100% genfail, already removed.

### Prompt size

Split by failure mode, `empty_response_audit.py --by-prompt-size`:

| prompt | calls | empty% | timeout% | dead% |
|---|---:|---:|---:|---:|
| 0-5k | 431 | 3% | 85% | 88% |
| 5-10k | 493 | 19% | 62% | 82% |
| 10-20k | 118 | 37% | 47% | 84% |

The **empty** rate tracks size (3 → 37%). The **timeout** rate inverts.
The combined figure is flat, which is why "prompt size predicts dead calls"
and "prompt size is irrelevant" have both been asserted from the same data.
Quote the split, never the total. Caveat: the timeout column straddles the
191s→90s cap change and is partly an artefact of when the call ran.

---

## 2. What we cannot see, and why

Two instrumentation gaps. Both are cheap. Together they are the whole
remaining diagnosis.

1. **stderr is discarded on the timeout path.** `_opencode_run_once` kills the
   child and re-raises without reading stderr, so if `opencode run` printed a
   reason — rate limit, auth failure, model unavailable, gateway error — it
   died with the process. 724 silent timeouts may all carry an explanation we
   have been throwing away.

2. **No time-to-first-byte.** "The provider never answered" and "the provider
   answered at 89s and we cut it off at 90s" are the same log line today.

---

## 3. Plan

### Phase 1 — See the failure (no fleet run needed to build; one short run to collect)

| # | Change | File | Done when |
|---|---|---|---|
| 1.1 | Read stderr before killing the child on timeout; log first 500 chars | `win/worker_direct.py` | A timed-out call logs `stderr: ...` or `stderr: (empty)` |
| 1.2 | Record time-to-first-byte in the pump thread | `win/worker_direct.py` | Every call logs `ttfb=Ns` or `ttfb=never` |
| 1.3 | Emit one JSON line per call to `logs/calls.jsonl` | `win/worker_direct.py` | Schema below validates |
| 1.4 | Teach forensics to read `calls.jsonl` when present | `fleet_forensics.py` | Same report, richer fields |

**Per-call record schema** (`automation/logs/calls.jsonl`, one JSON object per line):

```json
{
  "ts": 1786288823.0,        "worker": "fleet-oc-1",
  "function": "func_us_801B21F0",
  "model": "opencode/mimo-v2.5-free",
  "attempt": 2,              "prompt_chars": 8307,
  "ttfb_s": null,            "total_s": 90.0,
  "stream_chars": 0,         "rc": null,
  "outcome": "timeout_no_bytes",
  "stderr_head": "",         "concurrency": 4
}
```

`ttfb_s: null` means no byte ever arrived — that is the field the whole
exercise exists to populate.

### Phase 2 — Characterise the provider, off the queue

`automation/probe_provider.py` (new). Sends synthetic prompts, touches
neither the queue nor `src/`, so it can run while the fleet is stopped.

| # | Experiment | Answers |
|---|---|---|
| 2.1 | Same 2k prompt, 20 times, 1 worker | Base failure rate with no other variable |
| 2.2 | Same prompt padded to 2/4/8/16k, 10 each | Is size causal, or a proxy? |
| 2.3 | Fixed prompt, concurrency 1 / 2 / 4 / 8 | Is it contention or quota? **Highest priority** — burstiness points here. |
| 2.5 | 60 calls back to back, 1 worker, record run lengths | Does the burst reproduce in isolation? If it does with concurrency 1, it is provider-side, not our contention. |
| 2.4 | Fixed prompt, one model at a time | Is `ling`'s empty-vs-timeout split a provider difference? |

2.2 is the experiment ChatGPT proposed and the one that settles the prompt-size
argument for good. Vary **inert padding**, not the task.

### Phase 3 — Act on what Phase 2 says

Not written yet on purpose; the fix depends on the answer.

| if Phase 2 shows | then |
|---|---|
| Failure independent of size and concurrency | It is provider quota. Add a circuit breaker: N consecutive silent calls on a model parks it for M minutes. Rotate rather than retry. |
| Failure rises with concurrency | Cap in-flight calls per provider; workers queue instead of racing. |
| Failure rises with size | Route >Nk prompts to llama; the draft compaction already halves the biggest contributor. |
| One model is disproportionately healthy | Weight selection by measured yield instead of round-robin. |

**Do not implement any of these before Phase 2.** Every one of them is a
plausible story for the same 94%, and picking on plausibility is what produced
the last three wrong model verdicts in this project.

---

## 4. Test criteria

| Component | Passes when |
|---|---|
| `fleet_forensics.py --self-test` | Classifies all five outcome shapes from a synthetic log; burst detector separates a 20-run burst from strict alternation; a log ending mid-call yields `abandoned` |
| stderr capture (1.1) | A deliberately-killed call records non-empty `stderr_head` when the child wrote to stderr, and `""` when it did not — never a missing key |
| TTFB (1.2) | A call that streams records `ttfb_s > 0`; a call that never streams records `null`. Asserted against a fake child that writes after a delay |
| `calls.jsonl` (1.3) | Every line parses; every record has all schema keys; a killed worker leaves no partial line (write whole lines, append mode) |
| `probe_provider.py` | Refuses to run if the queue lock is held or a fleet worker is alive; makes zero writes outside `logs/probe-*.jsonl` |
| Phase 3 circuit breaker | Given a synthetic sequence of N silent calls, parks the model; given a success, resets the counter |

---

## 5. Corrections this exercise forced

Recorded because they were each asserted confidently and were each wrong.

- **"Prompt size is the strongest predictor of a dead call"** (my repo, from
  123 calls). At 1042 calls the combined dead rate is flat. Corrected in three
  docstrings; it predicts the **empty** rate specifically.
- **"The model finishes the code then keeps talking, so timeout salvage is the
  common case"** (my comment, from one observed instance). It is 2 calls in
  1042. Salvage is kept because it is free, not because it is a lever.
- **"Remarkably flat, so prompt size is not the mechanism"** (ChatGPT, from
  the same 1042 calls). Flat because two opposing slopes cancel.
- **"Failures are independent, not bursty"** (my own throwaway script, before
  the tool existed). It dropped aborted calls from the sequence entirely
  instead of ending a run at them, which shortened every run it measured.
  `fleet_forensics.py --streaks` says bursty on both of its readings. The
  lesson is the reason the throwaway became a tool: an ad-hoc count that
  nobody can re-run is not evidence.
