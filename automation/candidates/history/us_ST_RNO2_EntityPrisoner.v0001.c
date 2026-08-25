/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO2:EntityPrisoner
   source : upstream/master:src/st/e_prisoner.h
   target : src/st/rno2/unk_3459C.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801AB9EC_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801B5FB8_from_no2);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801AC54C_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801AC73C_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801B68EC_from_no2);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitPrisoner;

void EntityPrisoner(Entity* self) {
    Entity* tempEntity;
    u8 rand;

    tempEntity = self + 1;
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitPrisoner);
        self->animCurFrame = 0;
        self->zPriority = 0x1E;
        if (self->params & 1) {
            self->palette++;
        }
        if ((self->params & 0x10) == 0) {
            tempEntity = self + 1;
            CreateEntityFromEntity(E_ID(PRISONER), self, tempEntity);
            tempEntity->params = self->params + 0x10;
            self->step = 1;
            return;
        }
        self->blendMode = BLEND_TRANSP | BLEND_SUB;
        self->drawFlags |= ENTITY_OPACITY;
        self->opacity = 0x80;
        self->zPriority += 1;
        self->step = 8;
        break;

    case 1:
        if (GetDistanceToPlayerX() < 0x40) {
            if (self->ext.prisoner.unk80) {
                rand = Random() & 0xF;
            } else {
                rand = Random() & 1;
            }
            if (!rand) {
                self->ext.prisoner.unk80 |= 1;
                self->ext.prisoner.unk84 = (Random() & 3) * 7;
                if (Random() & 1) {
                    self->ext.prisoner.unk84 = -self->ext.prisoner.unk84;
                }
                self->posX.i.hi += self->ext.prisoner.unk84;
                self->step++;
            } else {
                self->step = 6;
            }
        }
        self->animCurFrame = 0;
        tempEntity->animCurFrame = 0;
        break;

    case 2:
        AnimateEntity(D_us_80180E44, self);
        tempEntity->animCurFrame = self->animCurFrame;
        tempEntity->opacity -= 1;
        if (!tempEntity->opacity) {
            SetStep(3);
        }
        break;

    case 3:
#ifndef BOSS_IS_BO0
        if (!AnimateEntity(D_us_80180E58, self)) {
            PlaySfxPositional(SFX_DUNGEON_PRISONER_RATTLE);
        }
#else  
        AnimateEntity(D_us_80180E58, self);
#endif
        tempEntity->animCurFrame = self->animCurFrame + 2;
        tempEntity->zPriority = 0x6A;
        tempEntity->blendMode = BLEND_NO;
        tempEntity->drawFlags = ENTITY_DEFAULT;
        if (GetDistanceToPlayerX() > 0x40) {
            tempEntity->blendMode = BLEND_TRANSP | BLEND_SUB;
            tempEntity->drawFlags |= ENTITY_OPACITY;
            tempEntity->zPriority = self->zPriority + 1;
            SetStep(4);
        }
        break;

    case 4:
        switch (self->step_s) {
        case 0:
            if (!AnimateEntity(D_us_80180E68, self)) {
                if (Random() & 1) {
                    SetStep(5);
                } else {
                    SetSubStep(1);
                }
            }
            break;

        case 1:
            if (!AnimateEntity(D_us_80180E7C, self)) {
                if (GetDistanceToPlayerX() < 0x40) {
                    SetSubStep(2);
                } else {
                    SetSubStep(3);
                }
            }
            break;

        case 2:
            if (!AnimateEntity(D_us_80180E8C, self)) {
                SetStep(3);
            }
            break;

        case 3:
            if (!AnimateEntity(D_us_80180E84, self)) {
                SetStep(5);
            }
            break;
        }
        tempEntity->animCurFrame = 0;
        break;

    case 5:
        AnimateEntity(D_us_80180E94, self);
        tempEntity->animCurFrame = self->animCurFrame;
        tempEntity->opacity++;
        if (tempEntity->opacity > 0x80) {
            self->posX.i.hi -= self->ext.prisoner.unk84;
            SetStep(1);
        }
        break;

    case 6:
        self->animCurFrame = 0;
        tempEntity->animCurFrame = 0;
        if (GetDistanceToPlayerX() > 0x40) {
            self->step = 1;
        }
        break;

    case 8:
        tempEntity = self - 1;
        self->posX.i.hi = tempEntity->posX.i.hi;
        self->posY.i.hi = tempEntity->posY.i.hi;
        break;

    case 16:
#include "pad2_anim_debug.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s16 GetDistanceToPlayerX();
s32 Random();
void PlaySfxPositional(s32 arg0);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int AnimateEntity();
extern int SetStep();
extern int SetSubStep();
/* End permuter-seed writer declarations. */
    }
}

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801B5EE4);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", EntitySealedDoor);
