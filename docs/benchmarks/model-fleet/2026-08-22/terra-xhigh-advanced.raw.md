# Terra xhigh advanced-context raw response

Model: `gpt-5.6-terra`
Effort: `xhigh`
Input: `advanced-context-input.md`
Stateful actions: none

## Frozen-evidence assessment

I used only the benchmark input, frozen queue snapshot, preserved/rejected candidates, and target assembly. No build, git, queue, fleet, permuter, or source mutation was performed. None of the four cases has full-overlay oracle proof here.

### 1. `us:BOSS/BO6:BO6_RicEntityCrashBibleBeam`

**Evidence used**

- Frozen queue record: deferred, `best_score: 60`; it records a compiling linked seed, an exhausted 8,980-iteration targeted search, and one remaining scheduling window.
- `automation/candidates/history/us_BOSS_BO6_BO6_RicEntityCrashBibleBeam.v0003.c`: marks the whole-file seed as compiled and linked but checksum-mismatched.
- Target assembly at `0x801C9108` through `0x801C9130`.

The target case-0 window performs, in this order:

```text
read self->hitboxState at 0x3C
store 0x11 at self+0xB0
store zero at self+0x3C
load g_api_AllocPrimitives
store saved hitboxState into D_us_801D10E8
indirect-call the allocator with (3, 6)
```

The preserved C expresses those same operations, but its local function-pointer assignment permits a different scheduling of the zero store.

**Diagnosis and classification**

Near match. This is a single compiler scheduling and indirect-call-surface issue, not evidence of a semantic re-derivation failure. The frozen score-60 result is not match proof.

**Cheapest justified next action**

Do a target-led micro-derivation of only the case-0 allocator window. Keep the existing full candidate as the baseline, but test the callee-access and local-lifetime shape that can force the `hitboxState = 0` store before loading `g_api_AllocPrimitives`, while retaining the later `D_us_801D10E8` store. Do not repeat the exhausted expression search.

**Replacement C**

Refusal: the frozen evidence identifies the instruction window but does not establish a unique C spelling that produces the required scheduling. A full replacement would overclaim.

**Must verify**

- `self->hitboxState` is the signed/unsigned halfword at `Entity+0x3C`.
- `self->ext.bibleBeam.subweaponId` is the halfword at `Entity+0xB0`.
- `D_us_801D10E8` is compatible with the saved halfword.
- The exact declared type and access form of `g_api_AllocPrimitives`.
- `PRIM_G4 == 3` and `BO6_BIBLE_PAGE_COUNT == 6`.

**Confidence:** high, about 0.92.
**Largest uncertainty:** the exact source-level local/callee spelling that causes PSYQ to retain the target scheduling.

### 2. `us:ST/RDAI:func_us_801C4B2C`

**Evidence used**

- Frozen record: deferred; notes say permuter reached a nonzero floor after 5,362 iterations and three promotions, with no improvement for 2,774 iterations.
- Preserved candidate: compiled and linked but nonmatching, explicitly not the promoted best body.
- Target assembly from `0x801C4B2C` to `0x801C4C48`.

The target performs seven smoothing passes across adjacent primitives. In each pass it:

1. Averages current `x0/y0` with next `x2/y2`.
2. Moves current `x2/y2` and next `x0/y0` one eighth toward that midpoint, with truncation toward zero for negative values.
3. Repeats for current `x1/y1` and next `x3/y3`.
4. Moves the primitive cursor to `next`.

The preserved candidate captures that apparent behavior, including the signed corrections before `>> 3`, but its large temporary set and liveness arrangement do not resemble the compact target register allocation.

**Diagnosis and classification**

Structural C-shape and liveness failure. The candidate is useful as a behavioral sketch, not as a codegen-ready base. The snapshot has both `best_score: 50.0` and prose referring to a permuter floor of 950, so those score representations must be reconciled rather than compared as one metric.

**Cheapest justified next action**

Hand-rederive the routine directly from the assembly, preserving operand order, halfword field order, and short-lived temporaries. Start from the two target blocks, not from another expression permutation. The candidate’s behavior can be retained only as a semantic cross-check.

**Replacement C**

Refusal: frozen evidence supports the algorithm but not a unique declaration, temporary, or statement-lifetime layout that would reproduce the target.

**Must verify**

- `g_CurrentEntity->ext.prim` is the pointer at `Entity+0x7C`.
- Primitive offsets map to `x0/y0`, `x1/y1`, `x2/y2`, `x3/y3`, and `next` as assumed.
- Midpoint operations use signed truncation toward zero, matching `(sum + ((u32)sum >> 31)) >> 1`.
- The candidate’s `s32` promotions and `s16` stores match the target’s signed loads.

**Confidence:** high, about 0.95.
**Largest uncertainty:** the exact original local-variable and statement structure behind the target’s all-register implementation.

### 3. `us:ST/RNO0:func_us_801CFD70`

**Evidence used**

- Frozen record: escalated, `best_score: 0.0`; it explicitly says isolated output scored zero while the full RNO0 overlay checksum still differed, and prohibits further permuter search.
- Preserved candidate: compiling whole-file seed, but marked checksum-mismatched.
- Target assembly from `0x801CFD70` to `0x801CFE68`.

The candidate matches the target algorithmically: two loops over the primitive chain, alternate clut/priority pairs based on entity byte `0xA8`, and override clut with `palette & 0xFFF` when palette bit `0x8000` is set. The second loop reverses the two clut/priority choices.

**Diagnosis and classification**

Isolated-function-zero versus full-overlay mismatch. This is an integration, link-map, section-layout, or source-selection problem until shown otherwise. It is not a candidate for more expression search and it is not full-overlay match proof.

**Cheapest justified next action**

Perform an overlay-context audit before touching the C body:

1. Confirm the real RNO0 source slot replaces the intended `INCLUDE_ASM` symbol and has no duplicate definition.
2. Compare linked symbol address, size, relocations, and surrounding section boundaries against the target overlay.
3. Check neighboring functions, data, alignment, and object/link order for the first whole-overlay divergence.

**Replacement C**

Refusal: an isolated score of zero is useful diagnostic evidence, but the frozen full-overlay mismatch means this body is not justified as a replacement.

**Must verify**

- `g_CurrentEntity->ext.prim` is the pointer at `0x7C`.
- Entity byte `0xA8` has a real named field or union member. The raw byte cast is an evidence placeholder, not a preferred final type expression.
- `palette` is the halfword at `0x16`.
- Primitive `clut`, `priority`, and `next` offsets and types are correct.
- `arg0` is signed, as the target uses `blez`.

**Confidence:** very high, about 0.98.
**Largest uncertainty:** whether the isolated comparator normalized away a context difference, or the full overlay has a separate earlier mismatch.

### 4. `us:BOSS/BO6:func_us_801C9DE8`

**Evidence used**

- Frozen record: escalated; it records the rejected candidate and the `Entity.ext` member error.
- `automation/rejected/us_BOSS_BO6_func_us_801C9DE8.c`: never compiled and must not be treated as a seed.
- Target assembly from `0x801C9DE8` to `0x801CA33C`.
- The frozen Case-1 candidate identifies `self->ext.bibleBeam.unk7C` as the named BO6 extension field at offset `0x7C`.

**Diagnosis and classification**

Rejected type-layout hallucination, with additional control-flow errors. The candidate invented `self->ext.unk00` and primitive `unk*` members. It also falls through from case 0 into case 1 and case 2, whereas the target exits the switch after case 0 initialization and advances the step for a later call.

**Cheapest justified next action**

First replace only assembly-proven invalid accesses with real fields and correct the switch flow. Then re-derive the remaining function from the target. Do not promote or permute this rejected file.

**Bounded correction**

The target proves the counter is a signed halfword at `Entity+0x7C`; the frozen neighboring BO6 candidate supports this bounded replacement:

```c
/* Not a complete replacement. */
self->ext.bibleBeam.unk7C++;
if (self->ext.bibleBeam.unk7C >= 0x18) {
    self->step++;
}
/* Return to post-switch work; do not fall through into case 3 destruction. */
```

The target’s primitive offsets support these member replacements:

```c
prim->u0 = ~(u8)prim->x0;
prim->u2 = ~(u8)prim->x2;
prim->v0 = -0x10 - (u8)prim->y0;
prim->v2 = -0x10 - (u8)prim->y2;

prim->u1 = ~(u8)prim->x1;
prim->u3 = ~(u8)prim->x3;
prim->v1 = -0x10 - (u8)prim->y1;
prim->v3 = -0x10 - (u8)prim->y3;
```

No complete replacement is justified. The rejected body still needs a full control-flow and type-correct re-derivation.

**Must verify**

- `bibleBeam.unk7C` is valid for this entity type and is the signed halfword at `0x7C`.
- Primitive fields map as target offsets indicate: `x0/y0/u0/v0` at `0x08/0x0A/0x0C/0x0D`, then the corresponding `x1`, `x2`, and `x3` fields.
- The valid named `g_Ric` member at `g_Ric + 0x39E`; `g_Ric.unk4E` is not established by this evidence.
- Types of `g_CurrentBuffer`, `g_GpuBuffers`, `tpage`, and the BO6 allocation API.
- Case-0 must break after initialization; case-1 may flow into case-2, but the threshold transition must not destroy the entity until a subsequent case-3 dispatch.

**Confidence:** very high, about 0.99.
**Largest uncertainty:** the header’s intended named member for `g_Ric + 0x39E` and any BO6-specific extension naming beyond the `0x7C` field.

| Case | Useful candidate | Classification confidence | Process fidelity | Estimated reconciliation effort |
|---|---|---:|---|---|
| CrashBibleBeam | Yes, near-match baseline | High, 0.92 | Pass | Low-medium: one target-led scheduling window |
| RDAI `801C4B2C` | Yes, semantic reference only | High, 0.95 | Pass | Medium: structural hand re-derivation |
| RNO0 `801CFD70` | Yes, overlay-diagnosis evidence | Very high, 0.98 | Pass | Low-medium: link and overlay-context audit |
| BO6 `801C9DE8` | No, rejected code only | Very high, 0.99 | Pass | Medium-high: type-correct and control-flow re-derivation |
