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

### Phase 1 — See the failure — **DONE 2026-08-03**, needs one short run to collect

| # | Change | File | Status |
|---|---|---|---|
| 1.1 | Read stderr before killing the child on timeout | `win/worker_direct.py` | **done** — `_drain_stderr` reads in a thread with a 3s join, so a pipe whose writer was killed cannot hang the worker |
| 1.2 | Record time-to-first-byte in the pump thread | `win/worker_direct.py` | **done** — `ttfb_s`, `null` when no byte ever arrived |
| 1.3 | Emit one JSON line per call to `logs/calls.jsonl` | `win/worker_direct.py` | **done** — 5 emit sites, one per terminal outcome |
| 1.4 | Teach forensics to read `calls.jsonl` when present | `fleet_forensics.py` | **done** — prefers telemetry, falls back to log scraping for the 1042 historical calls |

Both the human log and the JSONL now carry the reason. A timed-out call prints:

```
!! timed out at 90s (ttfb=never, 0 chars). stderr: 429 Too Many Requests: quota exhausted
```

Verified by `test_call_telemetry.py`, which drives the real
`_opencode_run_once` against fake `opencode` binaries reproducing each failure
shape — a provider that writes to stderr then hangs, one that streams a whole
function then hangs, and one that exits rc=0 with nothing. Source review was
explicitly not enough here: the previous handler *looked* correct and threw
stderr away, because the read sat after a `raise` that never ran.

**To collect:** one short fleet run, a few minutes, 2 workers. That is enough
to populate `calls.jsonl`; then `fleet_forensics.py` reports the TTFB split and
groups the stderr messages.

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


---

## 6. Battery results, 2026-08-03 (90 generations)

6 functions (1.5k-14k of asm) x 5 Zen models x 3 reasoning configs, one
variable at a time, through the real worker path. `quality_ab.py`, resumable,
appended to `automation/logs/quality-battery.jsonl`.

Ranked on **INVENTED** — field and type names that exist nowhere in the tree —
because that is what breaks the build. `unk80` admits ignorance; `field1C`
asserts a falsehood and fails identically while surviving review.

### By model

| model | answered | avg INVENTED | avg unkNN | avg s |
|---|---:|---:|---:|---:|
| big-pickle | 18/18 | **0.8** | 3.2 | 40.4 |
| mimo-v2.5-free | 18/18 | 0.9 | 3.8 | 66.7 |
| deepseek-v4-flash-free | 18/18 | 1.1 | 2.2 | 34.6 |
| nemotron-3-ultra-free | 13/18 | **3.7** | 1.3 | 91.2 |
| north-mini-code-free | **0/18** | — | — | 0.8 |

`north-mini-code-free` returns **HTTP 401 on every call**. It is a second dead
endpoint alongside hy3-free, and it has been contributing nothing while
counting as a worker.

`nemotron-3-ultra-free` is the worst live model on every axis: fewest answers,
most fabrication, slowest.

### By config

| config | answered | avg INVENTED | avg s |
|---|---:|---:|---:|
| **none** | 23/30 | **0.9** | **10.8** |
| low9k | 23/30 | 1.4 | 79.3 |
| low3k | 21/30 | 2.1 | 50.1 |

### The aggregate hides an outlier, and the conclusion survives it

Per model x config, avg INVENTED:

| model | none | low3k | low9k |
|---|---:|---:|---:|
| big-pickle | **0.0** | 0.5 | 2.0 |
| deepseek-v4-flash-free | 0.8 | **0.3** | 2.0 |
| mimo-v2.5-free | **0.5** | 1.3 | 0.8 |
| nemotron-3-ultra-free | 2.6 | **10.3** | 0.8 |

nemotron's low3k cell (10.3) is what pushes aggregate low3k above low9k.
Excluding that one unstable model: none 0.43, low3k 0.70, low9k 1.60. The
ordering is unchanged — **`none` wins, low9k is worst** — but the aggregate
table on its own would have supported the wrong story about 3k vs 9k.

A mid-run reading at 48/126 said the opposite (low3k 0.5 vs low9k 1.8). It was
reported as provisional and it was wrong. Partial batteries are not evidence.

### Size

| asm size | avg INVENTED | avg unkNN |
|---|---:|---:|
| <= 6k | 0.7 | 1.8 |
| > 6k | **2.2** | 3.6 |

Fabrication triples on large functions. Whatever is done about reasoning, the
large end needs a different approach.

### What this says about the defaults

`REASONING_EFFORT=low` with a 9000-token cap is the current default and the
battery does not support it. `none` answered as often, invented least, and ran
**7x faster**. The premise for choosing `low` — that thinking yields more
sensible C — is measurably false on this provider.

Not changed unilaterally: the default was set deliberately. But it should be
`none`, and `big-pickle` + `none` was clean on all six functions (0.0 INVENTED,
6/6 answered).

## Correction: "big-pickle was clean on all six" was wrong (2026-08-09)

The claim immediately above is retracted. It rested on a scorer that could not
see the failure mode that actually occurred.

Re-running the battery over the four newly configured models surfaced a
generation shape none of the metrics covered: the model stops writing a
function and emits an ascending list of declarations until the token cap fires.

    s32 temp659;
    s32 temp660;
    s32 temp                       <- truncated mid-token at the cap

Eleven of the 54 `none` generations did this, with runs of 176 to 661
declarations. Every one of them scored PERFECTLY on every existing metric:
zero invented fields, zero unkNN, zero ILLEGAL, no raw offsets. They score
clean because they contain no field accesses at all, and a metric counting
wrong field accesses cannot fault code that accesses no fields.

One of those eleven was `big-pickle` on func_us_801AF8C0. So "0.0 INVENTED,
6/6 answered" was really 5/6 answered plus one runaway loop being counted as a
flawless zero.

`quality_ab.degenerate()` now detects this structurally: a run of declarations
whose names differ only by an ascending integer suffix, threshold 20. Real
decompiled C reuses temporaries; it does not number them into the hundreds.
The five self-tests include the case that matters, which is that the looping
output scores clean on every OTHER metric.

### Standings after rescoring, config=none, INVENTED over USABLE answers

| model | usable | degen | INVENTED | avg s |
|---|---:|---:|---:|---:|
| **mimo-v2.5-free** | **6/6** | 0 | **0.5** | **7.0** |
| longcat-2.0-free (new) | 6/6 | 0 | 1.8 | 14.2 |
| big-pickle | 5/6 | 1 | 0.0 | 10.0 |
| nemotron-3-ultra-free | 5/6 | 0 | 2.6 | 28.3 |
| laguna-s-2.1-free (new) | 4/6 | 2 | 0.5 | 13.9 |
| deepseek-v4-flash-free | 4/6 | 2 | 1.2 | 7.9 |
| ling-3.0-tiny-free (new) | 3/6 | 2 | 1.3 | 58.2 |
| ling-3.0-flash-free (new) | 2/6 | 4 | 5.0 | 9.1 |
| north-mini-code-free | 0/6 | 0 | - | HTTP 401 |

`mimo-v2.5-free` is the pick: the only model that answered all six usably, at
the lowest fabrication rate of any model that did, and the fastest.

### None of the four new models earns a slot

The best of them, `longcat-2.0-free`, matches mimo on usable answers but
fabricates 3.6x as much. `ling-3.0-flash-free` is the worst model measured to
date on this harness: 4 of 6 degenerate, and 5.0 invented names on the two it
completed. `ling-3.0-tiny-free` also returns HTTP 503 under load, costing 200s
of backoff per affected cell.

### Degeneration is a function-size effect, not a model defect

| asm | function | degenerate |
|---:|---|---:|
| 1,557 | func_us_801BD47C | 0/9 |
| 2,839 | BO6_RicSetSlideKick | 0/9 |
| 3,918 | func_us_801BD384 | 1/9 |
| 6,069 | func_us_801CF64C | 2/9 |
| 8,895 | func_us_801AF8C0 | 5/9 |
| 13,934 | EntityGurkhaBodyParts | 3/9 |

Nothing under 3k degenerated on any model. Above 6k, four models produced zero
usable output at all. This is the same size cliff the fabrication rate shows,
and it argues for routing by asm size rather than trying to find one model that
handles everything: send small functions to the fleet, and stop sending
functions over ~6k to it until they get a purpose-built approach.

## The quality question: is the C a decompilation, or just clean C? (2026-08-09)

Every metric to this point was NEGATIVE: invented names, unkNN, ILLEGAL, raw
offsets, runaway loops. They count ways output is wrong. None of them can
separate

    a faithful decompilation of the target function, from
    a plausible, well-formed C function about something else entirely

Both score zero defects. Ranking models on defect counts therefore ranks them
on tidiness, and the model that writes the most cautious generic code wins.

quality_ab's docstring also claimed a compile check ("does psx cc accept it at
all", "a throwaway copy in /tmp"). No such code was ever written. Nothing had
verified any output positively. Docstring corrected.

### decomp_fidelity.py: check the C against what the assembly demands

    callees    every `jal SYMBOL` is a function the C must call. Strongest
               signal available; no model invents BO6_RicCreateEntFactoryFromEntity
               by accident. Indirect calls (%hi/%lo + jalr, e.g. g_api_PlaySfx)
               count as permitted but never as required.
    constants  distinctive immediates (>=0x40) that must appear literally.
    branching  C control-flow constructs per asm branch. A ratio, never a
               pass/fail, because the compiler reorders and one `if` can emit
               several branches.

Not a match oracle. Only the build and config/check.us.sha decide a match.
This decides whether a generation is worth a build cycle.

### Three parser bugs, each of which inverted a real result

1. `hi`, `lo`, `entity` scored as fabricated calls: they were prose inside
   comments. Comments are now stripped before parsing.
2. `nemotron-3-ultra-free` scored 0.00 callee recall on a FAITHFUL generation.
   It declares `extern s32 rand(void);` and then calls `rand()`; the scorer
   subtracted declared names from the call set and so deleted the real calls.
   Prototypes are now removed as text, not by name.
3. `g_api_PlaySfx` scored as fabricated on three models that were correct. It
   is called through a pointer, so it appears as a relocation rather than a
   `jal`.

Each bug made a correct model look broken. The rule that keeps proving itself
here: when a metric disagrees with the artefact, read the artefact.

### Two further degeneration shapes, both invisible to the first check

    register dump   `temp_v0; temp_v1; temp_s0; ... temp_v0_2;` -- the model
                    transcribes the MIPS register file. Not an ascending run,
                    so the numbered-loop check missed it. big-pickle emitted
                    447 such declarations on func_us_801CF64C.
    asm echo        the model returns the disassembly listing verbatim. This
                    GAMES the fidelity scorer: output containing the assembly
                    trivially reproduces every constant and symbol in it.
                    ling-3.0-flash-free scored 1.00 constant recall this way.

Breakdown of the 54 `none` generations: 30 usable, 11 numbered loops, 3 asm
echoes, 2 register dumps, 8 empty or errored.

### Final ranking, config=none

SCORE = usable_rate x callee_recall / (1 + invented)

| model | usable | recall | INVENTED | avg s | SCORE |
|---|---:|---:|---:|---:|---:|
| **mimo-v2.5-free** | **6/6** | **1.00** | 0.5 | **7.0** | **0.67** |
| laguna-s-2.1-free | 4/6 | 1.00 | 0.5 | 13.9 | 0.44 |
| big-pickle | 4/6 | 0.67 | 0.0 | 8.0 | 0.44 |
| longcat-2.0-free | 6/6 | 1.00 | 1.8 | 14.2 | 0.35 |
| nemotron-3-ultra-free | 5/6 | 0.88 | 2.6 | 28.3 | 0.20 |
| deepseek-v4-flash-free | 3/6 | 0.50 | 1.0 | 8.4 | 0.12 |
| ling-3.0-tiny-free | 2/6 | 0.00 | 0.0 | 47.8 | 0.00 |
| ling-3.0-flash-free | 0/6 | - | - | - | 0.00 |
| north-mini-code-free | 0/6 | - | - | - | HTTP 401 |

`mimo-v2.5-free` wins on every axis independently: the only model to answer all
six usably, perfect callee recall AND precision, lowest fabrication among
models that answered, and the fastest at 7s. It is the pick, and nothing about
that conclusion depends on the weighting of the composite.

`big-pickle`, previously reported as the cleanest model, is third. Its 0.0
invented count came from writing LESS: 0.67 callee recall and a control-flow
ratio of 0.41, i.e. it drops roughly half the control flow. Zero defects
because it declines to do the work, which is precisely the failure the old
metrics could not see.

Constant recall is poor for everyone (0.10 to 0.60). That is the clearest
remaining prompt lever: the immediates are in the assembly, the harness parses
it, and the models are not carrying the values across.

## Retraction: "constant recall is poor across all models" (2026-08-09)

That was the stated next lever in the section above. It was an artefact of two
bugs in my own extractor, and it does not survive fixing them.

    counted as a constant the C must contain     what it actually is
    -------------------------------------------  ---------------------------
    0x50 in `lw $v0, 0x50($s0)`                  a STRUCT FIELD OFFSET. The
                                                 correct C writes
                                                 `self->unk50`, so the scorer
                                                 was marking models DOWN for
                                                 the one behaviour the whole
                                                 harness exists to encourage
    -0x48 in `addiu $sp, $sp, -0x48`             the compiler's stack frame
                                                 size; never in the source
    0xbc in `addiu $a0, $s0, 0xbc`               address arithmetic,
                                                 `&self->field_BC`
    missing: `lui $v0, 0x2800`                   the top half of 0x28000000.
                                                 A correct literal read as a
                                                 miss because the halves were
                                                 never recombined

Only `andi/xori/slti/sltiu/li`, and `addiu/ori` FROM $zero, carry a value the C
must reproduce. With that correction:

    constant recall   before (wrong)   after
    mimo-v2.5-free         0.36        0.88
    longcat-2.0-free       0.41        0.88
    laguna-s-2.1-free      0.60        1.00
    nemotron-3-ultra       0.29        0.82

There is no constants problem. There was a measurement problem. No prompt
section was added, because adding one would have "fixed" nothing and the
metric would have "improved" on its own.

## The lever that is real: abort degenerate calls mid-stream

16 of 54 `none` generations were loops, register dumps or asm echoes, and every
one ran to its FULL timeout. The worker did have a degeneration detector, but
it watched only the reasoning stream and only while `n_content == 0`:

    if n_reason % 40 == 0 and n_content == 0:
        why = degenerating(reason_buf)

At REASONING_EFFORT=none there is no reasoning, so nothing was watching
anything. All three shapes occur in the CONTENT stream.

The detectors moved to `automation/degeneracy.py` (worker_direct cannot import
quality_ab, which imports worker_direct; a shared module is what stops two
copies drifting), and the worker now tests accumulated content every 120
tokens.

Replayed against the real captured output:

    all 16 degenerate generations abort, cutting 82% of the wasted output
    0 of 69 good generations across every config abort falsely

The four largest cases fire after 480 of 11,230 characters, i.e. at 4%.

## Default model changed to mimo-v2.5-free

`OPENCODE_MODEL` now defaults to `opencode/mimo-v2.5-free`, was
`deepseek-v4-flash-free` (which scores 3/6 usable, 0.50 callee recall).

## Dashboard wiring

Diagnostics tab gains: model ranking by fidelity, per-function fidelity,
battery report, and a battery run over untested models. `decomp_fidelity.py`
added to ANALYSIS_SCRIPTS, without which those buttons are rejected only after
being clicked; a new dashboard self-test now fails if any button points at a
script that is not allowlisted.

## Fabricated field names caught before the build, not after (2026-08-09)

The `invented` metric was only ever an offline score. It is now a live gate.

A fabricated member is a GUARANTEED build failure -- `structure has no member
named X` -- and it was being discovered by spending a 40s build cycle. The
pre-build `quality_gate` already had five checks, but every one was a review
objection (invented externs, raw casts, wrong typedefs, `ext.ILLEGAL`, bitmask
literals). None caught the top failure class.

`invented_members()` compares every `->name` against the union of ALL struct
members in the tree (1,950 names from index.us.json), not just Entity, because
generated C legitimately touches Primitive and the ET_* variants; a check
scoped to Entity would reject correct code, and a false rejection costs a whole
attempt.

    caught          20 of the fabricating generations
    false positives 0 of the 39 that scored clean

`unkNN` is deliberately NOT flagged. It is the honest form: it states the
offset it could not resolve, and that is far easier to fix than a confident
`->field1C`.

### The feedback names the field, which the compiler cannot

    `->field1C` exists in no struct in this tree; offset 0x1C is `scaleY`
    `->valueBC` exists in no struct in this tree; 0xBC falls inside `ext`
                (0x7C, union) -- use `unkBC` if you cannot name it
    `->partA`   exists in no struct in this tree; use a field from the
                ENTITY LAYOUT section, or `unkNN` naming the raw offset

### The offset hint had to be narrowed, twice

The first pattern was `[A-Za-z_]+_?([0-9A-Fa-f]{1,3})$`. Because a-f are hex
digits, it read `subType` as `subTyp` + 0x0E and `updateFunc` as `updateFun` +
0x0C, and told the model both of them meant `velocityY`.

Wrong guidance is worse than none: it does not just fail to help, it sends the
next attempt somewhere new and equally wrong, and it does so in a confident
voice. An offset is now read only from a known prefix (`field`, `value`,
`data`, `off`, ...) or after an explicit underscore. Names with no encoded
offset get the generic pointer to the layout section instead.

Both `subType` and `updateFunc` are, for the record, genuinely absent from
include/game.h and from every .c file in the tree, so flagging them was right;
only the hint was wrong.
