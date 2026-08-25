/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityCloakedKnightSword
   source : upstream/master:src/st/nz1/e_cloaked_knight.c
   target : src/st/rnz1/e_cloaked_knight.c
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
void CreateEntityFromCurrentEntity(u16, Entity*);
void DestroyEntity(Entity*);
void MoveEntity();
long SquareRoot0(long a);
long ratan2(long y, long x);
int rcos(int a);
int rsin(int a);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetStep();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", StepTowards);

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnight);

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnightCloak);

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnightAura);

void EntityCloakedKnightSword(Entity* self) {
    Entity* entity;
    s32 scale;
    s16 rotate;
    s32 offsetX;
    s32 offsetY;
    Pos* pos;
    s32 scale1;

    if (!self->params) {
        entity = self - 2;
        if ((entity->flags & FLAG_DEAD) != 0 ||
            entity->entityId != E_CLOAKED_KNIGHT) {
            if (self->step != 4) {
                self->hitboxState = 0;
                SetStep(4);
            }
        }
    }

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCloakedKnightSword);
        self->animCurFrame = 7;
        self->drawFlags = ENTITY_ROTATE;
        if (!self->params) {
            entity = self + 1;
            CreateEntityFromCurrentEntity(E_CLOAKED_KNIGHT_SWORD, entity);
            entity->params = 1;
        } else {
            self->flags |= FLAG_UNK_2000;
            self->animCurFrame = 0;
            self->step = 8;
        }
        break;

    case 1:
        if (entity->step > 2) {
            self->step++;
        }
        entity = self - 2;
        if (entity->entityId != E_CLOAKED_KNIGHT) {
            DestroyEntity(self);
        }
        break;

    case 2:
        MoveEntity();
        pos = &self->ext.cloakedKnightSword.targetPos;
        offsetX = pos->x.i.hi - self->posX.i.hi;
        offsetY = pos->y.i.hi - self->posY.i.hi;
        scale1 = SQ(offsetX) + SQ(offsetY);
        scale1 = SquareRoot0(scale1);
        scale = scale1;
        if (scale > 0x38) {
            scale = 0x38;
        }
        if (scale < 4) {
            SetStep(3);
        }
        rotate = ratan2(offsetY, offsetX);
        self->velocityX = scale * rcos(rotate);
        self->velocityY = scale * rsin(rotate);
        break;

    case 3:
        pos = &self->ext.cloakedKnightSword.targetPos;
        self->posX.i.hi = pos->x.i.hi;
        self->posY.i.hi = pos->y.i.hi;
        break;

    case 4:
        self->flags |= FLAG_DESTROY_IF_OUT_OF_CAMERA |
                       FLAG_DESTROY_IF_BARELY_OUT_OF_CAMERA;
        MoveEntity();
        self->velocityY += FIX(0.125);
        self->rotate += ROT(11.25);
        break;

    case 8:
        entity = self - 1;
        self->hitboxState = entity->hitboxState;
        self->posX.i.hi = entity->posX.i.hi;
        self->posY.i.hi = entity->posY.i.hi;
        rotate = entity->rotate + ROT(90.0);
        self->hitboxOffX = (rcos(rotate) * 3 * 8) >> 12;
        self->hitboxOffY = (rsin(rotate) * 3 * 8) >> 12;
        if (entity->entityId != E_CLOAKED_KNIGHT_SWORD) {
            DestroyEntity(self);
        }
        break;
    }
}
