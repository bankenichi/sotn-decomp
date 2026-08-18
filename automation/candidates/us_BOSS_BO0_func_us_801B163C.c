/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO0:func_us_801B163C
   attempt: 4/4
   model  : opencode/laguna-s-2.1-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/boss/bo0/nonmatchings/2D26C/func_us_801B163C.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo0.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int func_us_801B171C();

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AD26C);

// Checks whether the tile at (x, y) is solid ground.
s32 func_us_801AD2F0(s16 x, s16 y) {
    Collider col;

    g_api.CheckCollision(x, y, &col, 0);
    return col.effects & EFFECT_SOLID;
}

INCLUDE_RODATA("boss/bo0/nonmatchings/2D26C", D_us_801A9344);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AD338);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AE858);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF31C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF604);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF8C0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AFAF4);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", EntityOlroxAfterImage);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B001C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B053C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B088C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B0930);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B13A8);

void func_us_801B1590(u8 step) {
    ET_B0_Unk* temp = (ET_B0_Unk*)g_CurrentEntity->ext.b0Unk.unk80;

    g_CurrentEntity->step = step;
    g_CurrentEntity->step_s = 0;

    temp->childPalette = 0;
    temp = (ET_B0_Unk*)temp->parent;
    temp->childPalette = 0;
}

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B15BC);

// Updates a boss entity's position and velocity toward a target value with a
// scaled step.  arg0 points to the Entity, arg1 is the target position (u16),
// arg2 is the maximum step delta (s16).  Returns 1 if the target was reached
// exactly, 0 if the value is still approaching.
s32 func_us_801B163C(Entity *entity, u16 target, s16 delta) {
    s32 shift;       // temp for signed arithmetic on delta
    s32 step;        // the scaled step amount (delta >> 4, clamped to >= 1)
    s32 a0 = entity->hitboxOffX; // u16 at 0x10, reloaded below
    s32 a1 = target; // also used for the subtraction target-pos
    s32 t2 = a0;     // preserved copy of original u16 value for final store

    // Compute step = (delta >= 0 ? delta : delta + 0xF) >> 4, then ensure >= 1
    shift = (s16)delta;            // sign-extend arg2 (s16)
    if (shift < 0) {
        shift += 0xF;              // round-toward-zero bias for negatives
    }
    step = shift >> 4;             // divide by 16 (arithmetic shift of s32)
    if (step == 0) {
        step = 1;                  // never step by zero
    }

    // temp_v0 = target - entity->hitboxOffX  (s16 subtraction result kept in s32)
    a1 = (s16)(target - entity->hitboxOffX);

    // Decide whether to add or subtract the step from a0/a3
    if ((a1 << 16) > 0) {          // target > current  => moving forward
        if ((s16)a0 >= (s16)delta) {
            a0 = a0 - step;       // step toward target
        } else {
            a0 = a0 + step;
        }
    } else {                        // moving backward or stationary
        if ((s16)(-(s16)delta) < (s16)a0) {
            a0 = a0 - step;
        } else {
            a0 = a0 + step;
        }
    }

    // abs(a1) and abs(a0) for the magnitude comparison
    a1 = (s32)(s16)a1; if (a1 < 0) a1 = -a1;
    a0 = (s32)(s16)a0; if (a0 < 0) a0 = -a0;

    if (a1 < a0) {                  // |remaining| < |new value| => target reached
        s32 newval;
        newval = (s16)(entity->hitboxOffX + (s16)a0); // store sum at 0x10
        entity->hitboxOffX = (u16)newval;
        *((u16 *)((u8 *)entity + 0x2)) = (u16)a0;      // store raw a0 at offset 0x12
        return 0;
    }

    // Target not yet reached: snap exactly
    entity->hitboxOffX = target;                       // store arg1 at 0x10
    *((u16 *)((u8 *)entity + 0x2)) = (u16)(target - entity->hitboxOffX); // store difference at 0x12 (will be 0)
    return 1;
}

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B171C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B17BC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1864);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1950);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B19FC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1B30);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1C60);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1CE0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1DDC);

s32 func_us_801B1E5C(void *arg0)
{
  void *entity = arg0;
  s32 result1;
  s32 result2;
  void *child = *((void **) (((char *) entity) + 0x18));
  func_us_801B163C(&g_CurrentEntity->ext.venusWeed.pad_90, 0, 0xC);
  result1 = func_us_801B171C(entity, -0x40, 0x40, 0x60);
 do { result2 = func_us_801B171C(child, -0x200, 0x280, 0x50); return (result1 + result2) == 2; } while (0);
}

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1EDC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1F5C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B2044);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B20F4);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B2178);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B21F0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B24CC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B2690);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B30AC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B365C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B5470);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B551C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B5D6C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B5E08);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B5E8C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B619C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B6520);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B65C0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B6CA4);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B76E4);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B7BAC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B7C44);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B7CC8);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B8794);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B888C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B8970);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B8B64);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B8D8C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B9BEC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA030);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA128);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA4AC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801BA724);
