/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityCloakedKnightCloak
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
bool StepTowards(s16* val, s32 target, s32 step);
void InitializeEntity(u16 arg0[]);
u8 AnimateEntity(u8 frames[], Entity* entity);
long ratan2(long y, long x);
long SquareRoot0(long a);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */



INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", StepTowards);

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnight);

void EntityCloakedKnightCloak(Entity* self) {
    Entity* prev;
    s32 velocityX;
    s32 velocityY;
    s16 temp_s0_3;
    s32 distance;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCloakedKnight);
        self->hitboxState = 0;
        self->flags |= FLAG_UNK_00200000 | FLAG_UNK_2000;
        self->drawFlags = ENTITY_ROTATE;
         

    case 1:
        AnimateEntity(anim_cloak, self);
        prev = self - 1;
        self->posX.i.hi = prev->posX.i.hi;
        self->posY.i.hi = prev->posY.i.hi;
        velocityX = prev->velocityX;
        velocityY = prev->velocityY;
        temp_s0_3 = ratan2(velocityX, -velocityY);
        temp_s0_3 = temp_s0_3 - self->rotate;
        velocityX = FIX_TO_I(velocityX);
        velocityY = FIX_TO_I(velocityY);
        distance = SquareRoot0(SQ(velocityX) + SQ(velocityY));
        temp_s0_3 = (temp_s0_3 * distance) >> 4;
        self->rotate += temp_s0_3;
        StepTowards(&self->rotate, 0, 0x20);
        if (prev->entityId != E_CLOAKED_KNIGHT) {
            DestroyEntity(self);
        }
        break;
    }
}

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnightAura);

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnightSword);
