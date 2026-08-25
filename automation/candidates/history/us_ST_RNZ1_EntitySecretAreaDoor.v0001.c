/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntitySecretAreaDoor
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
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s32 Random();
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetStep();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBackgroundGears);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysLarge);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearHorizontal);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearVertical);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysSmall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWallGear);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitEnvironment;

void EntitySecretAreaDoor(Entity* self) {
    s32 i;
    Entity* entity;
    s16* var_a1;
    s32 fgIndex;
    s32 offsetX;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitEnvironment);
        self->animCurFrame = 7;
        if (D_us_80180FD0 == 0xF) {
            self->step = 2;
        } else {
            self->step = 1;
        }
        break;

    case 1:
        switch (self->step_s) {
        case 0:
            self->posX.i.hi = 8 - g_Tilemap.scrollX.i.hi;
            if (D_us_80180FD0 == 0xF) {
                PlaySfxPositional(SFX_STONE_MOVE_B);
                self->step_s++;
            }
            break;

        case 1:
            self->posX.val -= FIX(0.5);
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_INTENSE_EXPLOSION, self, entity);
                entity->params = 0x10;
                entity->posY.i.hi += 0x20;
                entity->posX.i.hi -= (Random() & 7);
            }
            offsetX = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
            if (offsetX < -15) {
                SetStep(2);
            }
            break;
        }
        break;
    case 2:
        switch (self->step_s) {
        case 0:
            self->posX.i.hi = -16 - g_Tilemap.scrollX.i.hi;
            if (D_us_80180FD0 != 0xF) {
                PlaySfxPositional(SFX_STONE_MOVE_B);
                self->step_s++;
            }
            break;
        case 1:
            self->posX.val += FIX(0.5);
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_INTENSE_EXPLOSION, self, entity);
                entity->params = 0x10;
                entity->posY.i.hi += 0x20;
                entity->posX.i.hi -= (Random() & 7);
            }
            offsetX = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
            if (offsetX > 7) {
                SetStep(1);
            }
            break;
        }
        break;
    }
    GetPlayerCollisionWith(self, 8, 0x20, 5);
    if (D_us_80180FD0 == 0xF) {
        var_a1 = &D_us_80180FDC[4];
    } else {
        var_a1 = D_us_80180FDC;
    }
    fgIndex = 0x360;
    for (i = 0; i < 4; i++, var_a1++, fgIndex += 16) {
        g_Tilemap.fg[fgIndex] = *var_a1;
    }
}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWallPartial);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretWallDebris);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", func_us_801A8F7C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWaterForeground);
