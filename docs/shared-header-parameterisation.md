# Parameterising shared headers so a stage can supply its own variant

Design scope for ROADMAP task #64. **No code yet, deliberately.** Two rounds of
attempting these shims by hand have both ended in a revert, so the next attempt
should follow a design rather than another guess.

Worth roughly 22 rno0 stubs. It is also a reusable capability: every stage that
diverges slightly from a shared header hits the same wall.

## The problem, stated precisely

A shim replaces a stage's private copy with `#include "../<stem>.h"`. That works
only when the header can emit **byte-identical** code and data for that stage.
When it cannot, the build fails in one of two ways, and both were observed:

- **data too small or too large** -> the overlay shifts, `overlay_size_check`
  reports the delta, and sibling files lose labels the header swallowed.
- **text a different size** -> same symptom, localised to one function.

Five rno0 stems are blocked on exactly this:

| stem | stubs | divergence | measured |
|---|---|---|---|
| `e_misc` | 14 | data 0xB8 vs slot 0xB4 | -0x4 |
| `e_hammer` | 3 | text | +0xC per file |
| `e_gurkha` | 2 | text | +0xC per file |
| `e_blade` | 2 | text | +0xC per file |
| `e_room_fg` | 1 | data, one ObjInit entry | 0x8C vs 0x78 |

`e_collect` is a sixth candidate, not yet attempted, and the hardest: 79
preprocessor conditionals and the most raw `D_us_` externs of any of them.

## What already works, and is the model to copy

**`entity_lock_camera.h`.** It carries per-stage branches AND an escape hatch:

```c
#ifndef ENTITY_LOCK_CAMERA_DATA_DEFINED
static u8 entityLockCameraHitbox[] = { ... };
static u8 entityLockCameraData[8] = {0};
static u16 entityLockCameraTilemapProps[] = {
#if defined(STAGE_IS_NO1)
    ...
#elif defined(STAGE_IS_RNZ0)
    ...
#else
    ...
#endif
    ...
};
#endif
```

A stage that needs something the branches do not cover defines the three objects
itself and sets `ENTITY_LOCK_CAMERA_DATA_DEFINED`. `rchi` uses this for PSP.
rno0 used it on 2026-08-02 and the function **matched**.

**`clock_room_entities.h`** is the precedent for changing a shared header
safely: every parameter was introduced with `#ifndef`, so stages that did not
opt in compiled to the same bytes. NO0 and MAR stayed byte-identical and the
oracle confirmed it.

## The two mechanisms, and when each applies

**1. `#ifndef <STEM>_DATA_DEFINED` escape hatch — for DATA divergence.**
Use when a stage's tables differ in content or length. Cheap, self-contained,
already proven twice. Applies to `e_misc`, `e_room_fg`, probably `e_collect`.

**2. Behaviour parameters via `#ifndef` defaults — for TEXT divergence.**
The `clock_room_entities.h` pattern: name the varying constant or branch, give
it a default equal to today's behaviour, let the stage override. Applies to
`e_hammer` / `e_gurkha` / `e_blade`.

The text case is harder because the divergence must first be IDENTIFIED, not
just accommodated. Current evidence:

- All three files are exactly **+0xC** versus both no2 and np3, which agree with
  each other. Three unrelated files differing by the same amount is a shared
  cause, not three coincidences.
- Per-function comparison points at the main entity bodies: `EntityHammer`
  +0x8C, `EntityGurkha` +0x94, `EntityBlade` +0x8C against np3's map. Those
  figures are NOISY (np3's map gaps include intervening statics) and should be
  re-derived properly before being relied on, but they place the difference in
  the giant-bro entity bodies rather than in the helpers.

**Diagnose the +0xC once.** If one cause explains all three, three stems fall
together and the parameter is written once.

## Rules for touching a shared header

These headers have 20-30 dependent stages. The oracle covers all of them, which
makes this far safer than it sounds, but only if the process is followed.

1. **Default to today's behaviour.** Every new knob is `#ifndef`-guarded so a
   stage that does not opt in emits identical bytes.
2. **Verify the whole tree, not the stage you care about.** `verify_build` must
   report 81/81. A green rno0 with a broken no2 is a regression.
3. **Introduce one parameter at a time.** With 20+ dependents, a failed build
   carrying three new knobs is far more expensive to bisect than three builds.
4. **Prefer the escape hatch to a new `STAGE_IS_*` branch** when the stage's
   data is wholly different. A branch listing five stages is harder to read than
   one stage overriding the block.
5. **Name what the stage overrides.** rno0's `e_lock_camera.c` restates all
   three objects because the guard covers all three, and says so in a comment.

## Order of work

1. **Diagnose the +0xC** shared by `e_hammer`/`e_gurkha`/`e_blade`. Read-only,
   no build needed, and it is the single highest-leverage question here: 7 stubs
   and possibly one parameter.
2. **`e_misc`** (14 stubs, the largest prize) via the DATA_DEFINED hatch. Its
   header already has 6 conditionals, so the idiom will not look foreign.
3. **`e_room_fg`** (1 stub) only if 2 goes smoothly. Its header has zero
   conditionals today, so it is the biggest structural change for the smallest
   return.
4. **`e_collect`** last. 79 conditionals and the most raw externs.

## Acceptance criteria

- `verify_build` reports **81/81** after every single step.
- `overlay_size_check` reports **0 shifted symbols** across all 43 overlays.
- No stage other than the one being changed alters by a single byte. The
  clock-room change proved this is achievable.
- The stem's `INCLUDE_ASM` count drops to 0 and its queue records move to
  `matched`.

## What NOT to do

- Do not attempt these stems individually again without diagnosing the
  divergence first. That has now failed twice and cost several build cycles.
- Do not "fix" the shared header to match rno0. The other stages are correct;
  rno0 is the variant.
- Do not add a `STAGE_IS_RNO0` branch to a header with no existing conditionals
  purely to save one stub. `e_room_fg` is that case.
