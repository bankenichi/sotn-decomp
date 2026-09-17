/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNZ1:EntityMedusaHeadBlue
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/e_medusa_head.h
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
void EntityExplosionSpawn(u16 params, u16 arg1);
u8 AnimateEntity(u8 frames[], Entity* entity);
void MoveEntity();
void InitializeEntity(u16 arg0[]);
s32 Random();
extern int rand(void);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/e_medusa_head", EntityMedusaHeadSpawner);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
void EntityMedusaHeadBlue(Entity* self);

void EntityMedusaHeadYellow(Entity* self) {
    self->params = 1;
    EntityMedusaHeadBlue(self);
}



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
#ifdef STAGE_IS_RNZ1
    self->posY.i.hi = (Random() & 0x7F) + 0x40;
#endif
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
#ifdef STAGE_IS_RNZ1
    side = Random() & 1;
#endif
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
