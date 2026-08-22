# Luna xhigh advanced-context raw response

Model: `gpt-5.6-luna`
Effort: `xhigh`
Input: `advanced-context-input.md`
Stateful actions: none

Frozen benchmark baseline: commit `be31d155f4a7fca3628922c93c3c3c3d5959757c`, queue snapshot SHA-256 `d944c3a16dd7c8114772bf539bbfe44dff348ef6e4b3e22e5a5ce352defe08c3`, oracle before dispatch `81/81`. No current compile or match claim is made.

## 1. `us:BOSS/BO6:BO6_RicEntityCrashBibleBeam`

Evidence:

- Queue status `deferred`; current seed is `v0003`.
- Queue history records isolated score `60`, with one remaining scheduling difference after an exhausted search.
- Candidate and target assembly agree throughout the function except the initialization scheduling window.
- Target order near `0x49118` is:
  1. save `hitboxState`;
  2. write subweapon ID;
  3. clear `self->hitboxState`;
  4. load `g_api_AllocPrimitives`;
  5. save `D_us_801D10E8`;
  6. call allocator.
- The candidate’s local `allocPrimitives` variable permits the compiler to hoist the function-pointer load before the hitbox clear.

Diagnosis and classification: useful, declaration-complete, compiling near-match. This is a local compiler scheduling or call-surface issue, not a structural derivation failure.

Cheapest next action: remove the local allocator variable and call `g_api_AllocPrimitives(PRIM_G4, BO6_BIBLE_PAGE_COUNT)` directly, preserving the existing assignment order. This is the bounded correction justified by the frozen evidence. Do not repeat the exhausted broad search.

No complete replacement function is justified because the body already agrees with the target except for this one source-shape hypothesis.

Identifiers and assumptions to verify:

- `g_api_AllocPrimitives` must remain the direct global function-pointer surface.
- `D_us_801D10E8` is the saved hitbox state.
- `self->ext.bibleBeam.subweaponId` is the field at offset `0xB0`.
- `BO6_BIBLE_PAGE_COUNT` must remain six.

Confidence: high. Largest uncertainty: whether direct invocation alone produces the target instruction scheduling under the project compiler.

## 2. `us:ST/RDAI:func_us_801C4B2C`

Evidence:

- Queue status `deferred`; note records an exhausted permuter run after 5,362 iterations with floor `950`.
- The preserved candidate is explicitly marked as a compiling starting point, not the promoted best body.
- Target assembly performs exactly seven iterations.
- Each iteration:
  - obtains `next = prim->next`;
  - averages the first pair of corners using signed division by two;
  - moves the first edge one eighth toward the average;
  - repeats for the second pair;
  - advances `prim` to `next`.
- The candidate’s semantic algorithm agrees with those operations, but the frozen score proves its source shape is not sufficient for byte identity.

Diagnosis and classification: structural re-derivation required. The failure is not an expression-level search problem. The permuter is exhausted and must not be rerun against this seed.

A complete structurally supported replacement is:

```c
void func_us_801C4B2C(void) {
    Primitive* prim;
    s32 i;

    prim = g_CurrentEntity->ext.prim;
    i = 0;

    do {
        Primitive* next;
        s32 avgX;
        s32 avgY;
        s32 diffX;
        s32 diffY;
        s32 newX;
        s32 newY;

        next = prim->next;

        avgX = (prim->x0 + next->x2) / 2;
        avgY = (prim->y0 + next->y2) / 2;
        diffX = prim->x2 - avgX;
        diffY = prim->y2 - avgY;

        if (diffX < 0) {
            diffX += 7;
        }
        if (diffY < 0) {
            diffY += 7;
        }

        newX = (diffX >> 3) + avgX;
        newY = (diffY >> 3) + avgY;

        prim->x2 = newX;
        next->x0 = newX;
        prim->y2 = newY;
        next->y0 = newY;

        avgX = (prim->x1 + next->x3) / 2;
        avgY = (prim->y1 + next->y3) / 2;
        diffX = prim->x3 - avgX;
        diffY = prim->y3 - avgY;

        if (diffX < 0) {
            diffX += 7;
        }
        if (diffY < 0) {
            diffY += 7;
        }

        newX = (diffX >> 3) + avgX;
        newY = (diffY >> 3) + avgY;

        prim->x3 = newX;
        next->x1 = newX;
        prim->y3 = newY;

        prim = next;
        prim->y1 = newY;
        i++;
    } while (i < 7);
}
```

This is a structural re-derivation, not compile or match evidence.

Identifiers and assumptions to verify:

- `g_CurrentEntity->ext.prim` is the primitive-list pointer at offset `0x7C`.
- `Primitive::next` is offset `0`.
- `x0/y0/x1/y1/x2/y2/x3/y3` are signed halfword members at the offsets shown by the assembly.
- The seven-iteration bound is intentional.
- Signed division by two must retain the compiler’s negative-value correction.

Confidence: medium-high for the algorithm, medium for exact source shape. Largest uncertainty: declaration order and temporary types needed for the target register allocation.

## 3. `us:ST/RNO0:func_us_801CFD70`

Evidence:

- Queue status `escalated`.
- Candidate banner says built and linked, with isolated score zero but full-overlay checksum mismatch.
- Target assembly and candidate agree on the two passes, palette override, clut and priority values, primitive traversal, and signed argument handling.
- The queue explicitly says the permuter is exhausted at zero and must not be repeated.

Diagnosis and classification: isolated-function match versus full-overlay integration failure. The frozen evidence supports the function body, but not the complete overlay artifact.

Cheapest next action: inspect the built ST/RNO0 symbol boundary and surrounding overlay bytes. Confirm that:

- the candidate was inserted into the intended origin file;
- no duplicate `INCLUDE_ASM` or stale object remains;
- the function’s linked symbol size and offset match the target;
- the first full-overlay divergence is outside this function;
- neighboring objects, relocation records, and section ordering are unchanged.

No replacement function is justified. Replacing the body would discard isolated score-zero evidence without addressing the demonstrated integration problem.

Identifiers and assumptions to verify:

- `g_CurrentEntity` declaration and relocation;
- `Entity::ext.prim` at offset `0x7C`;
- `Entity::palette` at offset `0x16`;
- primitive `clut` and `priority` offsets;
- source inclusion and object ordering in ST/RNO0.

Confidence: high for the diagnosis. Largest uncertainty: which non-function overlay byte or link-context difference caused the full checksum failure.

## 4. `us:BOSS/BO6:func_us_801C9DE8`

Evidence:

- Queue status `escalated`; four attempts recorded.
- The candidate is explicitly rejected, not a permuter seed.
- Compiler errors identify `Entity.ext.unk00` and several `Primitive.unk*` members as nonexistent.
- Assembly shows the timer access at entity offset `0x7C`, and primitive coordinate reads at offsets `0x08`, `0x0A`, `0x14`, `0x16`, `0x20`, `0x22`, `0x2C`, and `0x2E`.

Diagnosis and classification: compiler rejection caused by invented structure and union members. The candidate must not be applied or treated as compiling evidence.

Cheapest next action: repair declarations before attempting codegen:

- map the timer at entity offset `0x7C` to an actual named `Entity.ext` union variant;
- replace `prim->unk8`, `unkA`, `unk14`, `unk16`, `unk20`, `unk22`, `unk2C`, and `unk2E` with verified coordinate members;
- verify the `g_Ric` field at offset `0x39E`;
- replace raw flag literals with named constants only after confirming their definitions.

No complete replacement function is justified because the authoritative union member name at offset `0x7C` is absent from the frozen evidence. Supplying one would invent a project symbol.

Identifiers and assumptions to verify:

- signed 16-bit type of the timer at `Entity.ext + 0x7C`;
- canonical `Entity.ext` union member covering that offset;
- `Primitive` coordinate member names and signedness;
- `g_Ric` field at `0x39E`;
- `g_CurrentBuffer` and `g_GpuBuffers`;
- named equivalents for `0x10800000`, `0xC2`, and draw mode `8`.

Confidence: high that the candidate is invalid. Largest uncertainty: the correct existing union variant name for the timer.

## Summary

| Case | Useful candidate | Classification confidence | Process fidelity | Estimated reconciliation effort |
|---|---|---:|---:|---:|
| CrashBibleBeam | Yes | High | Pass | Low |
| `func_us_801C4B2C` | Yes, as structural evidence | Medium-high | Pass | Medium |
| `func_us_801CFD70` | Yes, as isolated score-zero evidence | High | Pass | Medium-high |
| `func_us_801C9DE8` | No, but useful rejection evidence | High | Pass | High |
