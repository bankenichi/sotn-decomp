/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO1:func_us_801BE880_from_no1
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
void InitializeEntity(u16 arg0[]);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
Entity* AllocEntity(Entity* start, Entity* end);
void PlaySfxPositional(s32 arg0);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", EntityBreakable);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", EntityBreakableDebris);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", RNO1_DebugShowWaitInfo);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", RNO1_DebugInputWait);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A68AC);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A700C);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801B7CC4_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801B8F50_from_no1);

void func_us_801BE880_from_no1(Entity* self) {
    Entity* tempEntity;
    s32 tilePos;
    s32 i;
    u8 animFrame;
    Entity* tempEntity2;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_801809C8);
        self->zPriority = 0x70;
        self->hitPoints = 0x7FFF;
        self->hitboxState = 0;
        self->ext.segmentedBreakableWall.damageTaken = 0;
        if (g_CastleFlags[NO1_SECRET_WALL_BROKEN]) {
            self->step = 5;
        } else {
            tempEntity = self + 2;
            CreateEntityFromEntity(E_ID(ID_25), self, tempEntity);
            tempEntity->posY.i.hi -= 0x18;
            tempEntity->params = 2;
            tempEntity = self + 1;
            CreateEntityFromEntity(E_ID(ID_25), self, tempEntity);
            tempEntity->posY.i.hi -= 0x30;
            tempEntity->params = 1;
        }
        break;

    case 1:
        if (self->ext.segmentedBreakableWall.damageTaken > 8) {
            self->ext.segmentedBreakableWall.damageTaken = 0;
            for (i = 0; i < 5; i++) {
                tempEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (tempEntity != NULL) {
                    CreateEntityFromEntity(E_ID(ID_26), self, tempEntity);
                    tempEntity->posX.i.hi += 0x10;
                    tempEntity->posY.i.hi -= 0x30;
                    tempEntity->params = i;
                }
            }
            if (self->animCurFrame < 0x4D) {
                self->animCurFrame++;
            }
        }
        if (self->ext.segmentedBreakableWall.pieceBroken) {
            PlaySfxPositional(SFX_WALL_DEBRIS_B);
            self->step_s = 0;
            self->step = self->ext.segmentedBreakableWall.pieceBroken + 1;
            if (self->ext.segmentedBreakableWall.pieceBroken == 3) {
                self->step = 2;
            }
        }
        break;

    case 2:
        self->animCurFrame = 0x4F;
        if (self->ext.segmentedBreakableWall.pieceBroken & 2) {
            PlaySfxPositional(SFX_WALL_DEBRIS_B);
            self->step = 4;
        }
        break;

    case 3:
        self->animCurFrame = 0x4E;
#ifdef VERSION_PSP
        tempEntity2 = self + 1;
        if (tempEntity2->step == 1 && (tempEntity2->flags & FLAG_DEAD) == 0) {
            tempEntity2->flags |= FLAG_DEAD;
        }
        PlaySfxPositional(SFX_WALL_DEBRIS_B);
        self->step = 4;
#else
        if (self->ext.segmentedBreakableWall.pieceBroken & 1) {
            PlaySfxPositional(SFX_WALL_DEBRIS_B);
            self->step = 4;
        }
#endif
        break;

    case 4:
        self->animCurFrame = 0x50;
        g_CastleFlags[NO1_SECRET_WALL_BROKEN] = 1;
        tempEntity = AllocEntity(&g_Entities[160], &g_Entities[192]);
        if (tempEntity != NULL) {
            CreateEntityFromEntity(E_EQUIP_ITEM_DROP, self, tempEntity);
            tempEntity->params = ITEM_POT_ROAST;
            tempEntity->posY.i.hi -= 0x30;
        }
        self->step++;
        break;
    default:
        self->animCurFrame = 0x50;
        break;
    }
    animFrame = self->animCurFrame - 0x4B;
    for (i = 0; i < 6; i++) {
        tilePos = D_us_801815F4[i];
        g_Tilemap.fg[tilePos] = D_us_80181604[animFrame][i];
    }
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BEB54_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BEE00_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BF074_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A86A8);
