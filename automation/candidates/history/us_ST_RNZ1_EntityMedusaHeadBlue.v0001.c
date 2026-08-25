/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityMedusaHeadBlue
   source : upstream/master:src/st/e_medusa_head.h
   target : src/st/rnz1/e_medusa_head.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void MoveEntity();
void InitializeEntity(u16 arg0[]);
extern int rand(void);
s32 Random();
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int EntityExplosionSpawn();
extern int AnimateEntity();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/e_medusa_head", EntityMedusaHeadSpawner);

INCLUDE_ASM("st/rnz1/nonmatchings/e_medusa_head", EntityMedusaHeadYellow);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitMedusaHeadBlue;
extern EInit g_EInitMedusaHeadYellow;

void EntityMedusaHeadBlue(Entity* self) {
    s32 side;
    Entity* player = &PLAYER;

    if (self->flags & FLAG_DEAD) {
        EntityExplosionSpawn(0, 0);
        return;
    }
    if (self->step) {
        AnimateEntity(anim_medusa_head, self);
        if (self->velocityY > 0) {
            self->animCurFrame += 2;
        }
        self->velocityY += self->ext.medusaHead.accelY;
        side = self->velocityY;
        if (side < 0) {
            side = -side;
        }
        if (side >= FIX(2.5)) {
            self->ext.medusaHead.accelY = -self->ext.medusaHead.accelY;
        }
        MoveEntity();
        return;
    }

    if (!self->params) {
        InitializeEntity(g_EInitMedusaHeadBlue);
    } else {
        InitializeEntity(g_EInitMedusaHeadYellow);
    }

    self->posY.i.hi = player->posY.i.hi - 0;
    side = 0;
    if (player->posX.i.hi < 0x50) {
        side = 1;
    } else if (player->posX.i.hi < 0xB1) {
        if ((rand() & 3) == 0) {
            side = player->facingLeft;
        } else {
            side = ((player->facingLeft + 1) & 1);
        }
    }
    self->posX.i.hi = medusaHeadInitParams[side].posX;
    self->velocityX = medusaHeadInitParams[side].velocityX;
    self->facingLeft = medusaHeadInitParams[side].facingLeft;
    self->velocityY = FIX(2.5) - ((Random() & 0xF) * FIX(2.5) >> 3);
    if (self->velocityY > 0) {
        self->ext.medusaHead.accelY = FIX(-5.0 / 32);
    } else {
        self->ext.medusaHead.accelY = FIX(5.0 / 32);
    }
}
