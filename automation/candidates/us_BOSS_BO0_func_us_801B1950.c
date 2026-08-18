/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO0:func_us_801B1950
   attempt: 3/4
   model  : opencode/laguna-s-2.1-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/boss/bo0/nonmatchings/2D26C/func_us_801B1950.s
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
extern int func_us_801B163C();
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

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B163C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B171C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B17BC);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B1864);

/* BOSS/BO0 overlay: per-frame state machine driver for the boss entity at arg0.
 * Reads the current phase from the zPriority byte (offset 0x24, which holds
 * either an animSet or a phase index depending on build config - here treated
 * as a small non-negative phase tag). Based on the phase it loads a fixed
 * (start_velocity_x, target_x, param3) triple, calls the helper
 * func_us_801B171C to advance whatever motion/timer logic the phase needs,
 * and if that helper reports progress (returns non-zero) it bumps the
 * phase counter so the next frame takes the next branch.
 *
 * Phase -> args mapping (unsigned comparisons at the asm switch):
 *   case 0: start_velocity_x = -0x200, target_x = 0x300, param3 = 0x18
 *   case 1: start_velocity_x =    0,   target_x = 0x280, param3 = 0x1C
 *   case 2: start_velocity_x = 0x80,   target_x = 0x180, param3 = 0x18
 *
 * Note: although start_velocity_x is logically a signed displacement, the
 * asm loads the phase byte with `lbu` (unsigned), so the phase itself is
 * compared as an unsigned value - this preserves the irregular-switch
 * structure (0 fallthrough, 1 explicit, 2 via the >=2 / ==2 path). */
void func_us_801B1950(Entity *ent) {
    u8 phase;          /* unk24 @ 0x24 - current sub-state of the boss AI */
    s32 startVelX;     /* a1: initial velocity X passed to the helper */
    s32 targetX;       /* a2: target X position / motion parameter */
    s32 param3;       /* a3: extra parameter (motion duration or scale) */

    phase = (u8)ent->zPriority; /* lbu 0x24($s0) - unsigned phase tag */

    /* Irregular switch: branch order is 1, then >=2, then ==0, matching the
     * asm layout `beq $v1,$t1,L1 ; slti $t1,$v1,2 ; beqz $t1,Lge2 ; beqz $v1,L0`.
     * We use an explicit if-chain to reproduce that exact fallthrough order. */
    if (phase == 1) {
        startVelX = 0;
        targetX   = 0x280;
        param3    = 0x1C;
    } else if (phase >= 2) {          /* slti + beqz -> unsigned >= 2 */
        if (phase == 2) {             /* beq $v1,$t2,L2 */
            startVelX = 0x80;
            targetX   = 0x180;
        } else {
            /* Any phase byte >= 3 also lands here and reuses the phase-2 args. */
            startVelX = 0x80;
            targetX   = 0x180;
        }
        param3 = 0x18;
    } else /* phase == 0 */ {         /* beqz $v1,L0 */
        startVelX = -0x200;           /* addiu $a1,$zero,-0x200 */
        targetX   = 0x300;
        param3    = 0x18;
    }

    /* Always call the motion helper with the assembled args.
     * `jal func_us_801B171C` - delay slot is `nop`. */
    if (func_us_801B171C(ent, startVelX, targetX, param3) != 0) {
        /* Helper reported forward progress; advance the phase tag.
         * `lbu $v0,0x24($s0) ; addiu $v0,$v0,1 ; sb $v0,0x24($s0)`.
         * We cast through u8 so the byte store width is preserved. */
        ent->zPriority = (u16)((u8)(ent->zPriority + 1));
    }
}

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
