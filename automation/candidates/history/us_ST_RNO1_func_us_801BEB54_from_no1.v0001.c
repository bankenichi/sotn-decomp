/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO1:func_us_801BEB54_from_no1
   source : upstream/master:src/st/no1/e_secrets.c
   target : src/st/rno1/unk_26178.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void PlaySfxPositional(s32 arg0);
void InitializeEntity(u16 arg0[]);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s32 Random();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", EntityBreakable);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", EntityBreakableDebris);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", RNO1_DebugShowWaitInfo);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", RNO1_DebugInputWait);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A68AC);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A700C);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801B7CC4_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801B8F50_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BE880_from_no1);

void func_us_801BEB54_from_no1(Entity* self) {
    Entity* tempEntity;
    s32 i;

    if (self->hitParams) {
        PlaySfxPositional(SFX_EXPLODE_FAST_B);
    }
    switch (self->step) {
    case 0:
        InitializeEntity(D_us_801809D4);
        self->hitPoints = 0x18;
        self->hitboxWidth = 0x10;
        self->hitboxHeight = 0xC;
        self->hitboxState = 2;
        self->ext.segmentedBreakableWall.hitPoints = self->hitPoints;
        self->hitboxOffY = -0xC;
        break;

    case 1:
        if (self->hitPoints ^ self->ext.segmentedBreakableWall.hitPoints) {
            (self - self->params)->ext.segmentedBreakableWall.damageTaken +=
                self->ext.segmentedBreakableWall.hitPoints - self->hitPoints;
            self->ext.segmentedBreakableWall.hitPoints = self->hitPoints;
        }
        if (self->flags & FLAG_DEAD) {
            (self - self->params)->ext.segmentedBreakableWall.pieceBroken |=
                self->params;
            self->step++;
        }
        break;

    case 2:
        switch (self->step_s) {
        case 0:
            tempEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (tempEntity != NULL) {
                CreateEntityFromEntity(E_EXPLOSION, self, tempEntity);
                tempEntity->posY.i.hi -= 8;
                tempEntity->params = 0x13;
            }
            for (i = 0; i < 3; i++) {
                tempEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (tempEntity != NULL) {
                    CreateEntityFromEntity(
                        E_INTENSE_EXPLOSION, self, tempEntity);
                    tempEntity->posX.i.hi += (i * 0x10) - 0x10;
                    tempEntity->params = 0x10;
                }
            }
            for (i = 0; i < 5; i++) {
                tempEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (tempEntity != NULL) {
                    CreateEntityFromEntity(E_ID(ID_27), self, tempEntity);
                    tempEntity->posX.i.hi += (i * 8) - 0x10 + (Random() & 3);
                    tempEntity->posY.i.hi -= (Random() & 7) + 0x14;
                    tempEntity->params = i;
                }
            }
            self->step_s++;
            break;
        }
        break;
    }
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BEE00_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BF074_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A86A8);
