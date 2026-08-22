# Terra xhigh full-sweep raw response

Model: `gpt-5.6-terra`
Effort: `xhigh`
Input: `terra-effort-input.md`
Stateful actions: none

## Benchmark result

**Process gate: FAIL.** I made no writes, builds, diffs, queue mutations, fleet calls, permuter calls, shell calls, or Git calls. However, I mistakenly ran a broad repository search under `docs/` for `BO6_RicStepStand`; its returned matches exposed prohibited historical Terra benchmark-result files. I did not open those files and did not rely on their contents below, but the search itself violates the brief’s no-historical-results boundary. This run is therefore disqualified from production recommendation despite the otherwise read-only evidence trail.

### Stage A: `us:BOSS/BO6:BO6_RicStepStand`

Evidence trail, in required cheapest-first order:

1. Controlling process evidence:
   - `AGENTS.md` requires the queue and `ROADMAP.md` to be the scope record, requires the cheapest-first route, reserves builds for the BuildLock owner, and defines `verify_build` 81/81 as the only match proof.
   - `docs/TOOLING.md` confirms `upstream_harvest.py`, `asm_twin_finder.py`, and `shim_sweep.py` are read-only discovery gates before transplant, manual derivation, or permutation.
   - `docs/STYLE.md` requires project typedefs, named constants where available, brace-form conditionals, and standard naming. `docs/NAMING.md` identifies entity state machines as `step`-driven.

2. Queue/history:
   - Live `queue_list` views were queried for every exposed status. Connector output caps prevented retrieving this exact record from the live queue.
   - The latest in-repository queue snapshot checked, `automation/queue/snapshots/queue.20260822-004016.be31d15.jsonl:296`, records the target as `deferred`, with a best isolated score of 230 and a completed non-improving search. That is historical routing evidence, not a fresh compile or match claim.

3. Target location:
   - Stub: `src/boss/bo6/richter.c:810`, `INCLUDE_ASM("boss/bo6/nonmatchings/richter", BO6_RicStepStand);`.
   - Target assembly: `asm/us/boss/bo6/nonmatchings/richter/BO6_RicStepStand.s:4`.
   - `asm_twin_finder.py --symbol BO6_RicStepStand` reports 153 target instructions.

4. Upstream:
   - `upstream_harvest.py --show BO6_RicStepStand` returned: no upstream definition. There is no upstream body to harvest.

5. Local corpus:
   - `asm_twin_finder.py --symbol BO6_RicStepStand` found one credible local donor: `src/ric/pl_steps.c:RicStepStand`.
   - Its other token-only hits are animation helpers, not credible whole-function donors.

6. Shared-header/shim:
   - `shim_sweep.py --overlay bo6 --json` returned `[]`.
   - The donor is a `.c` function, not a shared implementation header. A shim is not applicable.

7. Mechanical transplant:
   - **Not justified.** The playable-Richter donor includes its own initial idle/ember behavior and uses playable-Richter helpers/data. The target starts directly with `BO6_RicCheckInput(0x4305C)`, uses BO6 helper names and BO6 animation data, and has an independently shaped state machine.
   - The target’s branches establish state-substep handling for `0`, `1`, `0x40`, `0x41`, and `0x42`; it must be derived as a BO6 adaptation, not copied verbatim.

8. Declarations, types, style:
   - Current source declares `BO6_RicCheckInput(s32)`, `DecelerateX(s32)`, `BO6_RicCheckFacing(void)`, `BO6_RicSetStand(s32)`, and `BO6_DisableAfterImage(s32, s32)` near the stub.
   - `func_us_801B9DE4` is declared in current BO6 source as `void func_us_801B9DE4(s32)`. The target assembly explicitly materializes `$a0 = 0` in its call delay slot. Any applied body should therefore call `func_us_801B9DE4(0)`, not declare it parameterless.
   - `bo6.h` supplies the BO6 `RicSteps` enum and `RIC` alias. The implementation should use those types, the existing named pad/blueprint constants, named `g_Ric` members, and BO6-specific animation symbols.

Bounded handoff:

- `automation/candidates/history/us_BOSS_BO6_BO6_RicStepStand.v0005.c` is a preserved bounded candidate, not a match. Do not treat its embedded historical receipt as current oracle evidence.
- Start from its BO6-specific five-case body, but reconcile the `func_us_801B9DE4` declaration and both calls with the current source and target delay slot: `extern void func_us_801B9DE4(s32);` and `func_us_801B9DE4(0);`.
- Preserve the target-visible ordering: check input, decelerate, then switch on `RIC.step_s`; retain all five state labels and BO6 helper/data names.
- The remaining work is assembly-led codegen diagnosis, not another blind transplant or routine expression-only permuter run.

Root-only landing sequence:

1. Inspect state through the connector, then establish the required 81/81 baseline under the BuildLock owner.
2. Replace only the `INCLUDE_ASM` stub in `src/boss/bo6/richter.c` with the reconciled bounded candidate.
3. Run `make_build`, then `verify_build`.
4. If not 81/81, run `asm_diff` scoped to `BOSS/BO6` and `BO6_RicStepStand`; revise only from the first proven divergence. Do not report a match.
5. On an actual 81/81 result, run `make_build` immediately followed by `verify_build` again.
6. Only then call `queue_report` with the exact 81/81 proof and `keep_note=True`, update the applicable `ROADMAP.md` record, stage every changed path individually, commit, and push only to `origin`.

Confidence: medium-high on source, donor, no-upstream, and no-shim conclusions. Largest uncertainty: the final four-byte and remaining instruction-level divergence cannot be resolved without a root-owned build and scoped `asm_diff`.

### Stage B1: authoritative declarations

Defects:

1. `extern u16 g_EInitExample;` conflicts with the authoritative `extern EInit g_EInitExample;`.
   - `EInit` is `u16[5]`, an array object, not one `u16`.
   - The candidate’s scalar declaration is not compatible with the authoritative declaration.

2. `u32 Random(void);` conflicts with authoritative `s32 Random(void);`.
   - The return type is incompatible.
   - It also changes the meaning of `Random() < 0`: signed `s32` can be negative; unsigned `u32` cannot.

3. `InitializeEntity(&g_EInitExample);` has the wrong call shape.
   - With the authoritative array declaration, `g_EInitExample` decays to `u16*`, matching `InitializeEntity(u16*)`.
   - `&g_EInitExample` is `u16 (*)[5]`, a pointer to the whole array, and is incompatible.

Minimal corrected lines:

```c
extern EInit g_EInitExample;
s32 Random(void);

InitializeEntity(g_EInitExample);
```

Better, remove the first two lines entirely when the authoritative header is included.

Compatible redundancy versus conflict:

- Repeating `extern EInit g_EInitExample;` and `s32 Random(void);` exactly is compatible but redundant.
- Repeating the candidate’s scalar object declaration or unsigned function declaration is a real conflict.
- No defect is established for `Entity* self` or `self->step++` from the supplied fixture alone.

Confidence: high. Largest uncertainty: none material.

### Stage B2: GCC 2.7.2 dispatch and scheduling

Required switch shape:

- Preserve the range `0..50`, not merely the four live labels.
- Add explicit empty labels for:
  - `0..9`
  - `12..19`
  - `21..39`
  - `41..50`
- Group each contiguous empty range into an intentional fallthrough to a no-op `break`.

Why each group matters:

- `0` and `50` establish the target table’s lower and upper bounds.
- The interior labels make the source switch dense enough for GCC 2.7.2 to select and populate a 51-entry jump table rather than a compare chain.
- A `default` arm does not substitute for explicit interior cases in this codegen decision. The target’s table proves the compiler saw a dense `0..50` dispatch space even though only four values have live behavior.

Required scheduling shape:

- Reverse the nearby stores so the Boolean-true field is written before the related zero field, retaining the condition and destination forms that allow GCC to place the `1` materialization in the branch delay slot.
- Do not introduce a temporary Boolean or fold the writes into an expression. The target’s delay-slot `li 1` is source-shape-sensitive.

This is a likely minimal form:

```c
if (condition) {
    self->booleanField = 1;
    self->relatedField = 0;
}
```

with the exact target condition and fields retained. It requires assembly comparison after compilation.

Confidence: medium. Largest uncertainty: the exact field aliases and enclosing condition are intentionally omitted, so only the required relative source shape can be stated.

### Stage B3: exact submodule path contract

| Input | Raw-contract result | Resolved identity | Classification |
|---|---|---|---|
| `tools/psyz` | Exact match | Same directory | Accept |
| `tools/psyz/.` | Mismatch | Same directory | Reject: contract defect if accepted |
| `tools/m2c/../psyz` | Mismatch | Same directory | Reject: contract defect if accepted |
| Absolute path resolving to `tools/psyz` | Mismatch | Same directory | Reject: contract defect if accepted |

The acceptance predicate must require all of:

```text
raw_input == raw_declared_path
AND resolved_input is contained by repository_root
AND resolved_input identifies resolved_declared_path
```

Correct validation order:

1. Read the declared raw path from `.gitmodules`.
2. Compare the user’s raw string to that raw declaration before normalization.
3. Resolve accepted-form input and the declared path.
4. Perform containment on the resolved input before using it.
5. Compare resolved filesystem identities as an additional integrity check, never as a replacement for raw-string equality.

The evidence proves **a contract defect only** if aliases are accepted. It does not prove a repository escape: all listed aliases resolve to the declared directory and the independent containment check rejects outside-repository paths.

Confidence: high. Largest uncertainty: whether the current implementation short-circuits raw mismatches or incorrectly uses identity as its acceptance test.

### Scorecard

| Dimension | Score | Rationale |
|---|---:|---|
| Process fidelity | 0/5 | Hard failure: prohibited broad search exposed historical benchmark-result material. |
| Evidence correctness | 3/5 | Independent current stub, assembly, donor, upstream, shim, and declaration evidence were gathered; no fresh oracle or diff was run. |
| Honesty | 5/5 | The process failure is explicit; no historical candidate receipt is represented as a current match. |
| Candidate utility | 3/5 | The BO6-specific candidate is bounded and actionable, but needs declaration repair and root-owned assembly diagnosis. |
| Expected economics | 2/5 | Harvest and shim routes are exhausted; remaining work is manual codegen with a build/diff loop, not economical autonomous iteration. |

Recommendation: **no production role for this run** because the forbidden historical-result search is a process failure. Absent that failure, the substantive result would support only root-gated, read-only triage, never an autonomous worker.
