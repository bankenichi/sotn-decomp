# Terra medium raw response

Model: `gpt-5.6-terra`
Effort: `medium`
Input: `advanced-context-input.md`
Stateful actions: none

Analysis used only the frozen benchmark packet, its named queue snapshot, candidates, and target assembly. I did not build, diff, search, mutate state, or make any oracle claim.

### 1. `us:BOSS/BO6:BO6_RicEntityCrashBibleBeam`

Evidence used:

- `automation/queue/snapshots/queue.20260822-004016.be31d15.jsonl`, record 375.
- `automation/candidates/history/us_BOSS_BO6_BO6_RicEntityCrashBibleBeam.v0003.c`.
- `asm/us/boss/bo6/nonmatchings/us_3E79C/BO6_RicEntityCrashBibleBeam.s`.

Diagnosis and classification:

- **Classification:** near-match, one local instruction-scheduling residue.
- The frozen record says the immutable declaration-complete seed isolates at score 60, with stack and register differences zero, exactly one reordering, and no insertions or deletions. Its targeted search ran about 8,980 iterations with no improvement and was stopped by the no-improvement policy.
- The record identifies the exact window: target BO6 `0x49118` stores zero to `0x3C(self)` before loading `g_api_AllocPrimitives`; the candidate loads the allocator pointer first and performs the store two instructions later. Everything thereafter realigns.
- This is not a semantic re-derivation problem and it is not a justification for another general expression search.

Cheapest justified next action:

- Make one bounded, isolated source-shape experiment around case-0 initialization: force the zero store corresponding to `sh $zero, 0x3C(self)` to appear immediately after `self->unkB0 = 0x11` and before the allocator function-pointer load. Preserve the existing `g_api.AllocPrimitives(PRIM_GT4, 6)` call surface and all surrounding declaration order.
- If that does not produce the desired schedule, stop the local experiment and record the exact generated window. Do not restart the exhausted broad permuter search.

Bounded correction, not a replacement function:

```c
/* In case 0, preserve this source ordering around the allocation call:
 * self->unkB0 = 0x11;
 * <the named member at Entity+0x3C> = 0;
 * <save prior value as required>;
 * self->primIndex = g_api.AllocPrimitives(PRIM_GT4, 6);
 *
 * The frozen evidence establishes the ordering, but not the correct named
 * member for offset 0x3C, so it does not support inventing a complete body.
 */
```

Identifiers/type assumptions to verify:

- The named `Entity` member at offset `0x3C`; do not introduce a raw offset cast or a guessed extension-union member.
- The exact declaration and expansion of `g_api.AllocPrimitives`, including whether call syntax changes the load schedule.
- `D_us_801D10E8`, `D_us_801D10D0`, and `D_us_801804CC` retain the declarations and placement used by the frozen seed.

Confidence: **high, 0.93**.
Largest uncertainty: the frozen evidence names the target offset but not the source-level member responsible for `0x3C(self)`.

### 2. `us:ST/RDAI:func_us_801C4B2C`

Evidence used:

- `automation/queue/snapshots/queue.20260822-004016.be31d15.jsonl`, record 467.
- `automation/candidates/us_ST_RDAI_func_us_801C4B2C.c`.
- `asm/us/st/rdai/nonmatchings/func_44b2c/func_us_801C4B2C.s`.

Diagnosis and classification:

- **Classification:** structural/code-generation re-derivation required.
- The candidate has the apparent high-level smoothing algorithm, but the target is a compact frameless seven-iteration loop that carries only the current primitive and its `next` through registers. The preserved candidate introduces numerous scoped temporaries, which is a materially different compiler shape.
- The target specifically smooths two adjoining edges per iteration:
  - `(prim->x0 + next->x2) / 2`, then moves `prim->x2` and `next->x0` one eighth toward that average.
  - `(prim->x1 + next->x3) / 2`, then moves `prim->x3` and `next->x1` one eighth toward that average.
  - Equivalent y-coordinate work follows each x-coordinate pair.
- The frozen record and candidate banner say the expression-only search plateaued at 950 after 5,362 iterations and three promotions, with no improvement for 2,774 iterations. A new expression permutation pass would repeat an exhausted method.
- There is a frozen-data inconsistency worth preserving: the record’s scalar `best_score` is `50.0`, while its note and the candidate banner report `950`. The prose is internally consistent with the benchmark packet, but the score units or metadata need reconciliation before reporting a quantitative improvement.

Cheapest justified next action:

- Re-derive a minimal, frameless source shape from the target assembly before any new search:
  - retain only `Primitive* prim`, `Primitive* next`, and a loop counter;
  - avoid helper functions and persistent intermediate locals;
  - compute each signed `/ 2` average and signed `/ 8` correction in direct expressions;
  - preserve target store order: current x2, next x0, current y2, next y0; then current x3, next x1, current y3, next y1.
- Run no permuter until this structural seed has a fresh isolated baseline.

Explicit refusal to provide a complete replacement function:

- The frozen evidence proves the intended data flow but does not establish a compiling, codegen-compatible C spelling. Supplying a complete replacement would present an unverified re-derivation as stronger evidence than exists.

Identifiers/type assumptions to verify:

- `Entity.ext.prim` is indeed the pointer at `Entity + 0x7C`.
- Primitive offsets map as assumed: `x0/y0/x1/y1` at `0x08/0x0A/0x14/0x16`, `x2/y2/x3/y3` at `0x20/0x22/0x2C/0x2E`, and `next` at `0x00`.
- PSYQ signed-division lowering for direct `/ 2` and correction division by eight remains consistent with the target.

Confidence: **high, 0.90**.
Largest uncertainty: why the frozen record’s numeric score is 50 while both narrative sources call the plateau 950.

### 3. `us:ST/RNO0:func_us_801CFD70`

Evidence used:

- `automation/queue/snapshots/queue.20260822-004016.be31d15.jsonl`, record 198.
- `automation/candidates/us_ST_RNO0_func_us_801CFD70.c`.
- `asm/us/st/rno0/nonmatchings/unk_4F968/func_us_801CFD70.s`.

Diagnosis and classification:

- **Classification:** isolated-function match with overlay/link-context failure.
- The frozen record explicitly says the preserved output scored zero in isolated compilation, while the applied full-overlay checksum still differed. It correctly classifies additional permutation as structurally inapplicable.
- The candidate’s two loops correspond to the target:
  - first pass assigns `0x232/0x72` when `Entity + 0xA8` is zero and `0x233/0x6E` otherwise;
  - second pass swaps those pairings;
  - both override `prim->clut` with `palette & 0xFFF` when palette bit `0x8000` is set.
- The target reloads `g_CurrentEntity` before the second loop, while the candidate also rereads it through the global expression. An isolated score of zero is frozen evidence that this source shape was adequate for the isolated object, not evidence that the overlay matched.

Cheapest justified next action:

- Diagnose the translation-unit and overlay boundary, not this function’s arithmetic:
  1. compare the applied source translation unit against the preserved seed for surrounding replacements, declaration insertions, function order, and preprocessor context;
  2. compare the linked overlay’s symbol/address context and the adjacent functions that share `unk_4F968.c`;
  3. confirm that the exact zero-score body, rather than a later or differently declared copy, was what entered the full overlay.
- Do not rerun the permuter. It cannot improve a score below zero.

Explicit refusal to provide a replacement function:

- The frozen evidence already supports this candidate as an isolated zero-score body, but it simultaneously proves that treating it as an overlay-level replacement is insufficient. A rewritten body would be needless invention and would distract from the link-context diagnosis.

Identifiers/type assumptions to verify:

- `g_CurrentEntity->ext.prim` is the primitive pointer at offset `0x7C`.
- `Entity + 0xA8` has a valid named field in the appropriate RNO0 extension variant; the candidate’s byte cast is evidence of an unresolved type name, not a safe long-term declaration.
- `Entity.palette` is the halfword at `0x16`; `Primitive.clut` and `Primitive.priority` are offsets `0x0E` and `0x26`.
- The actual applied translation unit is `src/st/rno0/unk_4F968.c`, with the preserved candidate’s includes and injected declarations reproduced only where appropriate.

Confidence: **high, 0.96**.
Largest uncertainty: the frozen material does not include the linked overlay diff or map, so it cannot identify which surrounding symbol, ordering, or context difference caused the checksum mismatch.

### 4. `us:BOSS/BO6:func_us_801C9DE8`

Evidence used:

- `automation/queue/snapshots/queue.20260822-004016.be31d15.jsonl`, record 369.
- `automation/rejected/us_BOSS_BO6_func_us_801C9DE8.c`.
- `asm/us/boss/bo6/nonmatchings/us_3E79C/func_us_801C9DE8.s`.

Diagnosis and classification:

- **Classification:** compiler-rejected, invalid type/member model, requiring type-correct structural re-derivation.
- The rejected candidate is not a seed. It never compiled, and the banner explicitly forbids treating it as a permuter input.
- Its core invented-member error is visible both in the compiler record and source: `self->ext.unk00`. The target uses a halfword at `Entity + 0x7C` as its active timer, but physical offset alone does not identify the valid extension-union variant or member name.
- The candidate also invents primitive members `unk8`, `unk20`, `unkA`, `unk22`, `unk14`, `unk2C`, `unk16`, and `unk2E`. The target assembly instead demonstrates accesses that should be represented through real primitive fields or a known named compatible view:
  - stores to `0x08`, `0x0A`, `0x14`, `0x16`, `0x20`, `0x22`, `0x2C`, `0x2E`;
  - byte reads/writes at `0x08/0x0C/0x0D`, `0x0A`, `0x14/0x18/0x19`, `0x20/0x24/0x25`, `0x22`, `0x2C/0x30/0x31`, and draw mode at `0x1A`.
- The target is substantially larger than the rejected case-switch model. It allocates 16 primitives, initializes their priority/draw mode, advances a signed counter at `self + 0x7C`, and then performs two angular primitive-generation phases. The rejected source does not establish a valid complete reconstruction.

Cheapest justified next action:

- First perform a type lookup, not a code rewrite:
  - identify the correct `Entity.ext` union member whose first halfword maps to offset `0x7C` for this BO6 entity;
  - map every primitive access in the target to declared `Primitive` fields or an existing named subtype;
  - identify the named `g_Ric` member at `g_Ric + 0x39E`.
- Then derive only the initialization and counter-state portion as a fresh, type-correct attempt. Do not salvage the rejected function by replacing invented names mechanically.

Bounded correction:

```c
/* Do not retain these invented accesses:
 * self->ext.unk00
 * prim->unk8, prim->unk20, prim->unkA, prim->unk22
 * prim->unk14, prim->unk2C, prim->unk16, prim->unk2E
 *
 * Replace them only after mapping the target offsets to existing named Entity
 * extension and Primitive fields. No complete replacement is justified by the
 * frozen rejected candidate.
 */
```

Identifiers/type assumptions to verify:

- The BO6-specific `Entity.ext` variant beginning at offset `0x7C`.
- `g_Ric` member at offset `0x39E`.
- `g_api.AllocPrimitives`, `DestroyEntity`, `rsin`, `rcos`, `g_PrimBuf`, `g_CurrentBuffer`, and `g_GpuBuffers`.
- Exact Primitive field names for all offsets noted above, especially the byte-component layout and draw-mode field at `0x1A`.

Confidence: **high, 0.97**.
Largest uncertainty: the correct extension-union variant is not identified in the frozen evidence, so naming it would be speculation.

| Case | Useful candidate | Classification confidence | Process-fidelity | Estimated reconciliation effort |
|---|---|---:|---|---|
| BO6 CrashBibleBeam | Yes, as a near-match seed | High | Pass | Low: one bounded scheduling experiment, then record outcome |
| RDAI `func_us_801C4B2C` | Yes, semantic evidence only | High | Pass | Medium: fresh minimal structural derivation before any search |
| RNO0 `func_us_801CFD70` | Yes, isolated zero-score evidence | High | Pass | Medium: overlay/map and translation-unit context diagnosis |
| BO6 `func_us_801C9DE8` | No, rejected evidence only | High | Pass | High: type mapping plus fresh structural derivation |
