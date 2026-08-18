# Luna effort benchmark results

Date: 2026-08-18

Model: `gpt-5.6-luna`

Efforts tested: `low`, `medium`, `high`, `xhigh`, and `max`

Design: [2026-08-18-luna-effort-benchmark-design.md](../../superpowers/specs/2026-08-18-luna-effort-benchmark-design.md)

## Decision

Luna does not replace Zen as an autonomous fleet worker on this evidence. No
effort setting passed every fixed case. Both `xhigh` and `max` failed the hidden
GCC switch and scheduling case, which is the kind of compiler-quirk reasoning
that separates a plausible candidate from a matching one.

`xhigh` is approved for bounded, read-only evidence gathering and candidate
drafting when the root can check every claim. It was the only setting that both
passed the Stage A process gate and produced a useful candidate. That candidate
compiled and left BO6 one instruction short, so it is meaningful evidence but
not a match. `max` was safer than the lower settings, but produced no candidate,
was slower, and did not improve the hidden-case result over `xhigh`.

Root ownership of edits, builds, asm-differ, the queue, Git, and verification is
unchanged.

## Fixed protocol

Every setting received the same read-only Stage A target:
`us:BOSS/BO6:BO6_RicStepStand`. It had to:

1. read the controlling instructions and task history
2. locate the queue record, source stub, and target assembly
3. search upstream and the local corpus
4. check shared-header and shim applicability
5. decide whether a mechanical transplant was justified
6. inspect declarations, types, style, and naming
7. return a bounded candidate or an evidence-based refusal
8. name the root-only apply, build, diff, verify, queue, and Git sequence

Subagents were prohibited from shell use, builds, asm-differ, the permuter,
fleet operations, Git, edits, and queue mutation.

## Stage A answer key

The root independently established:

- the target was `todo`
- the stub was `src/boss/bo6/richter.c:BO6_RicStepStand`
- the assembly was
  `asm/us/boss/bo6/nonmatchings/richter/BO6_RicStepStand.s`
- `upstream_harvest.py --show BO6_RicStepStand` found no upstream definition
- `asm_twin_finder.py --symbol BO6_RicStepStand` found the 153-instruction name
  twin `src/ric/pl_steps.c:RicStepStand`
- `shim_sweep.py --overlay bo6 --include-ports` found no shim
- `transplant.py --function BO6_RicStepStand --auto` found no mechanically safe
  transplant because there was no distinct twin assembly

The justified next step was a BO6-specific manual adaptation of the RIC control
flow, not a blind transplant.

## Effort score sheet

| effort | Stage A process gate | evidence | honesty | candidate utility and economics | disposition |
|---|---|---|---|---|---|
| `low` | fail | Mixed: found the twin but missed target semantics and the complete root sequence | No fabricated project symbol scored; confidence exceeded correctness | Flawed draft, not built; returned first; output size and token cost not captured | Too error-prone for worker use |
| `medium` | fail | Fail: final answer omitted its supporting evidence, used an incorrect assembly path, and omitted asm-differ | Unscorable from the unauditable final | No candidate; roughly eight minutes; output size and token cost not captured | No production role |
| `high` | fail | Fail: wrong shim overlay token, missing `RIC.step_s++`, and incomplete root sequence | No fabricated project symbol scored; confidence exceeded correctness | Flawed draft, not built; roughly fifteen minutes; output size and token cost not captured | Useful reasoning with unsafe process drift |
| `xhigh` | pass | Strong in Stage A; later correct on two of three hidden cases | No fabrication scored; uncertainty was bounded | Only built candidate: compiled at 80/81 and `-0x4`; exceeded the ordinary wall-time budget; output size and token cost not captured | Root-gated support only |
| `max` | pass | Strong in Stage A; later correct on two of three hidden cases | Strong refusal behavior where declarations were unresolved | No candidate; exceeded the ordinary wall-time budget; output size and token cost not captured | No default role |

The lower settings sometimes produced useful observations. They still fail the
worker requirement because process fidelity is a gate, not an average.

No answer was rerun. The `xhigh` and `max` Stage A agents each received one
instruction to stop new inspection and return after exceeding the wall-time
budget; that was a completion nudge, not a replacement attempt. Stage B needed
no retry. Exact response bytes, tokens, and dollar cost were not exposed by the
runtime.

## Stage B hidden replay

Only `xhigh` and `max` advanced. Both received the same three self-contained
fixtures without the historical answers.

### Case 1: authoritative declarations

The fixture defined `EInit` as `u16[5]`, declared `s32 Random()`, declared
`InitializeEntity(u16[])`, and declared the data symbol as `extern EInit`.
Generated code instead redeclared the symbol as `u16`, redeclared `Random` as
returning `u32`, and called `InitializeEntity(&array)`.

Expected answer:

- remove the conflicting redeclarations
- recognize `InitializeEntity(u16*)` as compatible but redundant
- pass the array, not a pointer to the whole array
- preserve the authoritative signed `s32` return type for `Random`

Both `xhigh` and `max` answered this correctly.

### Case 2: GCC 2.7.2 switch form and scheduling

The target had a 51-entry table for indices `0..50`, with live cases at `10`,
`11`, `20`, and `40`. The target also materialized constant one in a branch
delay slot. The candidate had only the four live cases and wrote a related zero
store before the Boolean store.

Expected answer:

- add empty boundary cases `0` and `50` to make the switch range dense enough
  for the target dispatch form
- do not label every value from `0` through `50`
- write the Boolean `true` store before the related zero store so constant one
  can be materialized in the target delay slot

Both `xhigh` and `max` gave the same wrong conclusion: label every case from
`0` through `50` and retain the candidate store order. This is a substantive
compiler-quirk failure, not a formatting difference.

### Case 3: exact submodule path contract

The fixture stated that accepted paths must be exact raw strings from
`.gitmodules`. The buggy implementation compared resolved path identities.

Expected answer:

- compare the raw input string with the raw declared strings before resolving
- reject aliases such as `tools/psyz/.`, `tools/m2c/../psyz`, and an absolute
  path even when they resolve to the same directory
- retain the containment check as a separate defense
- classify this as a definite validation and contract defect, without claiming
  a repository escape that the evidence did not show

Both `xhigh` and `max` answered this correctly.

Stage B result: each setting scored two of three. Neither is approved for
autonomous compiler-quirk decisions.

## Stage C shadow evaluation

The root evaluated the `xhigh` Stage A candidate against the real tree:

1. Baseline `verify_build` returned 81/81.
2. The root applied the candidate with evidence-backed declarations.
3. `make_build` completed, then `verify_build` returned 80/81. Only
   `build/us/BO6.BIN` differed.
4. `asm_diff` could not start because the connector child Python lacked the
   `watchdog` module.
5. `overlay_size_check.py` reported `BO6_RicStepStand is -0x4 bytes wrong`.
   The candidate was exactly one instruction short.
6. The root tested one evidence-based call-argument hypothesis. The result
   remained `-0x4`, so no further guesses were made without a working diff.
7. The root restored the original stub, rebuilt, and verified 81/81.

At the end of the shadow run, no queue status had changed, no candidate was
claimed as matched, and no source change remained. The target was still `todo`.
That handling was incomplete: compiled nonmatching C is a `near` seed and must
be preserved before the source is restored.

### Preservation correction

The exact applied patch was recovered from the Codex task transcript and saved
at `automation/candidates/us_BOSS_BO6_BO6_RicStepStand.c`. The queue record is
now `near` at score 50 with the 80/81 and `-0x4` proof, and the updated 471-record
queue was snapshotted at
`automation/queue/snapshots/queue.20260818-032759.37a5d1b.jsonl`. The source
still holds the original stub and the tree remains 81/81.

This is useful candidate yield. It is not sufficient replacement evidence:
Stage C covered one record, not the mixed multi-record sample required by the
design, and the candidate did not match.

## Economics

The collaboration runtime did not expose comparable per-agent token or dollar
cost. The observable ordering was:

- `low` returned first
- `medium` took roughly eight minutes
- `high` took roughly fifteen minutes
- `xhigh` and `max` exceeded the ordinary worker wall-time budget and were told
  to stop new inspection and return their current result

`xhigh` produced the only candidate worth a root build. `max` bought no hidden
case improvement and no candidate. On this sample, `max` is not an economical
default.

## Connector defect exposed by the shadow run

The failed `asm_diff` was an infrastructure failure, not evidence about the
candidate:

- `automation/mcp/commands_client.py` selected child Python from `SOTN_PYTHON`
  and otherwise used bare `python3`
- `automation/mcp/clients/codex.config.toml` leaves `SOTN_PYTHON` unset
- the repository virtual environment contains the required modules
- `asm_diff` selected bare Python and failed with missing `watchdog`
- `permuter_import` independently used it and failed with missing `toml`

The Codex connector therefore had a portability defect affecting at least these
two Python-backed actions. `commands_client.py` now selects the root repository
venv by default, retains an explicit `SOTN_PYTHON` override, and falls back to
the current interpreter only if the root venv is absent. The regression failed
before the change and passes after it. Live asm-differ and permuter verification
still require a connector restart.

## Root-gated support assignment

This is not a fleet role. The root may use Luna `xhigh` for:

- bounded corpus and twin searches
- connector or documentation consistency audits against named authority
- declaration extraction
- draft candidates that the root will independently build and inspect

Do not use Luna at any tested effort for:

- autonomous fleet process ownership
- compiler scheduling or GCC 2.7.2 last-mile conclusions
- queue classification without root evidence
- builds, asm-differ, edits, Git, or verification

If Luna is tested as a Zen backend replacement later, put it behind the
deterministic `worker_direct.py` mechanics. The harness should enforce claim,
evidence order, candidate application, build, restore, and reporting while Luna
supplies only the generation step. Re-run a fixed multi-record battery and
compare useful candidate yield before changing the production default.

## Record limitation

The prompt requirements and fixtures, scored assertions, material candidate
outcome, and root verification evidence are preserved here. The exact applied
candidate was later recovered from the task transcript and is now a repository
seed. The application collaboration layer still exposed no durable export for
the complete dispatch prompts and verbatim agent finals, so those byte-for-byte
bodies are not in the repository. Future benchmark dispatch should capture each
dispatch and final into a repository artifact when it arrives; treating a UI
transcript as the only raw record is a harness gap.
