/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityWallGear
   source : upstream/master:src/st/nz1/e_gear_puzzle.c
   target : src/st/rnz1/unk_276A8.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void PlaySfxPositional(s32 arg0);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBackgroundGears);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysLarge);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearHorizontal);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearVertical);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysSmall);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitEnvironment;

void EntityWallGear(Entity* self) {
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitEnvironment);
        self->zPriority = 0x6C;
        self->animCurFrame = 0xC;
        self->drawFlags = ENTITY_ROTATE;
        self->velocityY = FIX(0.5);
        self->hitboxState = 2;
        self->hitPoints = S16_MAX;
        self->hitboxWidth = self->hitboxHeight = 0x10;
        self->rotate = D_us_801C1680[self->params];
        self->rotate &= 0xF00;
         

    case 1:
        self->hitboxState = 2;
#ifdef VERSION_PSP
        if (self->params != 1 || self->posY.i.hi >= 97)
#endif
        {
            if (self->hitFlags) {
                self->ext.gearPuzzle.cooldownTimer = 16;
                self->step++;
            }
            D_us_801C1680[self->params] = self->rotate;
        }
        break;

    case 2:
        self->hitboxState = 0;
        self->rotate += 16;
        if (!--self->ext.gearPuzzle.cooldownTimer) {
            self->rotate &= 0xFFF;
            if (self->rotate == D_us_80180FD4[self->params]) {
                D_us_80180FD0 |= 1 << self->params;
                PlaySfxPositional(SFX_SWITCH_CLICK);
            } else {
                D_us_80180FD0 &= 0xFF - (1 << self->params);
                PlaySfxPositional(SFX_LEVER_METAL_BANG);
            }
            self->step = 1;
        }
        break;
    }
}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretAreaDoor);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWallPartial);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretWallDebris);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", func_us_801A8F7C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWaterForeground);
