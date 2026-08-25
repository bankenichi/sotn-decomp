/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RNZ1:func_us_801C8AAC_from_are
   score  : 5
   receipt: nonmatchings/.adapt-scores/20260824-235222-62298-992210/func_us_801C8AAC_from_are/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rnz1/e_valhalla_knight.c
   asm    : asm/us/st/rnz1/nonmatchings/e_valhalla_knight/func_us_801C8AAC_from_are.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
void MoveEntity();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s32 Random();
extern void (*g_api_PlaySfx)(s32 sfxId);
/* End permuter-seed writer declarations. */


INCLUDE_ASM("st/rnz1/nonmatchings/e_valhalla_knight", EntityValhallaKnight);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180C24;
extern EInit D_us_80180C30;

extern EInit D_us_80180C24;
extern EInit D_us_80180C30;
extern s8 D_us_80182018[36];
extern u8 D_us_8018203C[20];
extern s8 D_us_80182050[20];
extern u8 D_us_80182064[20];

void func_us_801C8954_from_are(Entity* self) {
    Entity* tempEntity;
    s32 curFrame;
    s8* hitboxPtr;

    if (!self->step) {
        if (self->params) {
            InitializeEntity(D_us_80180C30);
        } else {
            InitializeEntity(D_us_80180C24);
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
        hitboxPtr = D_us_80182050;
        hitboxPtr += D_us_80182064[curFrame] * 4;
    } else {
        hitboxPtr = D_us_80182018;
        hitboxPtr += D_us_8018203C[curFrame] * 4;
    }
    self->hitboxOffX = *hitboxPtr++;
    self->hitboxOffY = *hitboxPtr++;
    self->hitboxWidth = *hitboxPtr++;
    self->hitboxHeight = *hitboxPtr++;
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180C18;

extern EInit D_us_80180C18;
extern unkStr_80182100 D_us_80182084[13];

void func_us_801C8AAC_from_are(Entity* self) {
    Entity* tempEntity;
    unkStr_80182100* ptr;
    s32 delay;

    if (!self->step) {
        InitializeEntity(D_us_80180C18);
        self->animCurFrame = self->params + 18;
        self->zPriority += self->params;
        self->flags |= FLAG_DESTROY_IF_BARELY_OUT_OF_CAMERA;
        self->drawFlags |= ENTITY_ROTATE;
        ptr = D_us_80182084;
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
    ptr = D_us_80182084;
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
        g_api_PlaySfx(SFX_EXPLODE_FAST_B);
    }
}
