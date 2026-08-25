/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:func_us_801C8AAC_from_are
   source : upstream/master:src/st/e_valhalla_knight.h
   target : src/st/rnz1/e_valhalla_knight.c
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
void MoveEntity();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s32 Random();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/e_valhalla_knight", EntityValhallaKnight);

INCLUDE_ASM("st/rnz1/nonmatchings/e_valhalla_knight", func_us_801C8954_from_are);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitValhallaKnightUnk1;

void func_us_801C8AAC_from_are(Entity* self) {
    Entity* tempEntity;
    unkStr_80182100* ptr;
    s32 delay;

    if (!self->step) {
        InitializeEntity(g_EInitValhallaKnightUnk1);
        self->animCurFrame = self->params + 18;
        self->zPriority += self->params;
        self->flags |= FLAG_DESTROY_IF_BARELY_OUT_OF_CAMERA;
        self->drawFlags |= ENTITY_ROTATE;
        ptr = D_us_80182100;
        ptr += self->params;
        if (self->facingLeft) {
            self->velocityX -= ptr->velocityX;
        } else {
            self->velocityX += ptr->velocityX;
        }
        self->velocityY += ptr->velocityY;
    }
    MoveEntity();
    self->velocityY += FIX(0.0625);
    ptr = D_us_80182100;
    ptr += self->params;
    self->rotate += ptr->rotate;
    if ((self->params & 3) == 0) {
        delay = g_Timer - (self->params >> 2);
        if ((delay & 7) == 0) {
            tempEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (tempEntity != NULL) {
                CreateEntityFromEntity(E_EXPLOSION, self, tempEntity);
                tempEntity->params = Random() & 1;
                tempEntity->zPriority = self->zPriority + 1;
            }
        }
    }
    if (!self->params && (g_Timer & 7) == 0) {
        g_api.PlaySfx(SFX_EXPLODE_FAST_B);
    }
}
