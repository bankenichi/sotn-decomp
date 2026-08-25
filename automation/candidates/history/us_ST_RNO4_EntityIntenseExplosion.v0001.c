/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO4:EntityIntenseExplosion
   source : upstream/master:src/boss/bo3/e_misc.c
   target : src/st/rno4/unk_44B0C.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno4.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBreakable);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C123C_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C12B0_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C15F8_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5364);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBgColumnsParallax_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C1EE4_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5C78);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5EE4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2850_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2B78_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2E60_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3160_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C34EC_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C37C8_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3A04_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3CC4_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3FB0_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C4228_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityWaterBox);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C81C8);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityFloatingIcePlatform);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C4BD8_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C8668);

void RNO4_Unused801C8704(void) {}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C870C);

void RNO4_Unused801C8768(void) {}

void RNO4_Unused801C8770(void) {}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBoatElevatorChains);

void RNO4_Unused801C8BD4(void) {}

void RNO4_Unused801C8BDC(void) {}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", LoadFerrymanGateTiles);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C8C54);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801A071C_from_bo3);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801A07CC_from_bo3);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5518_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C9048);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C909C);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityExplosionVariants);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityGreyPuff);

void EntityIntenseExplosion(Entity* self) {
    if (!self->step) {
        InitializeEntity(g_EInitParticle);
        self->palette = PAL_FLAG(PAL_UNK_170);
        self->animSet = ANIMSET_DRA(5);
        self->animCurFrame = 1;
        self->blendMode = BLEND_TRANSP | BLEND_ADD;
        if (self->params & 0xF0) {
            self->palette = PAL_FLAG(PAL_UNK_195);
            self->blendMode = BLEND_TRANSP;
        }

        if (self->params & 0xFF00) {
            self->zPriority = (self->params & 0xFF00) >> 8;
        }
        self->zPriority += 8;
    } else {
        self->poseTimer++;
        self->posY.val -= FIX(0.25);
        if ((self->poseTimer % 2) == 0) {
            self->animCurFrame++;
        }

        if (self->poseTimer > 36) {
            DestroyEntity(self);
        }
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", PlaySfxPositional);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBreakableCrystalFloor);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBreakableWall);
