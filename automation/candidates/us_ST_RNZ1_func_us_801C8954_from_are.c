/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:func_us_801C8954_from_are
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
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/e_valhalla_knight", EntityValhallaKnight);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitValhallaKnightUnk3;
extern EInit g_EInitValhallaKnightUnk2;

void func_us_801C8954_from_are(Entity* self) {
    Entity* tempEntity;
    s32 curFrame;
    s8* hitboxPtr;

    if (!self->step) {
        if (self->params) {
            InitializeEntity(g_EInitValhallaKnightUnk3);
        } else {
            InitializeEntity(g_EInitValhallaKnightUnk2);
            self->parent = self - 1;
            self->nextPart = self - 1;
        }
    }
    tempEntity = self - self->params - 1;
    if (tempEntity->entityId != E_VALHALLA_KNIGHT) {
        DestroyEntity(self);
        return;
    }
    curFrame = tempEntity->animCurFrame;
    self->facingLeft = tempEntity->facingLeft;
    self->posX.val = tempEntity->posX.val;
    self->posY.val = tempEntity->posY.val;
    if (self->params) {
        hitboxPtr = D_us_801820CC;
        hitboxPtr += D_us_801820E0[curFrame] * 4;
    } else {
        hitboxPtr = D_us_80182094;
        hitboxPtr += D_us_801820B8[curFrame] * 4;
    }
    self->hitboxOffX = *hitboxPtr++;
    self->hitboxOffY = *hitboxPtr++;
    self->hitboxWidth = *hitboxPtr++;
    self->hitboxHeight = *hitboxPtr++;
}

INCLUDE_ASM("st/rnz1/nonmatchings/e_valhalla_knight", func_us_801C8AAC_from_are);
