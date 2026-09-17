/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RCEN:EntityUnkId1B
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rcen/e_elevator.c
   target : src/st/rcen/e_elevator.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rcen.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
/* End permuter-seed writer declarations. */

// Unused on PSP, see UnusedPrimFunction in CEN
INCLUDE_ASM("st/rcen/nonmatchings/e_elevator", func_us_8019FD4C);

static s16 func_801904B8(Primitive* prim, s16 dy) {
    prim->drawMode = DRAW_UNK02;
    prim->u0 = prim->u2 = 0x50;
    prim->u1 = prim->u3 = 0x60;
    prim->x0 = prim->x2 = g_CurrentEntity->posX.i.hi - 8;
    prim->x1 = prim->x3 = g_CurrentEntity->posX.i.hi + 8;
    prim->v2 = prim->v3 = 38;
    prim->y2 = prim->y3 = dy;
    dy += 32;
    prim->v0 = prim->v1 = 6;
    prim->y0 = prim->y1 = dy;
    if (dy >= 0x101) {
        dy = 0;
    }
    return dy;
}

INCLUDE_ASM("st/rcen/nonmatchings/e_elevator", func_us_8019FE9C);

void EntityUnkId1B(Entity* self) {
    Entity* entity = self + self->params;
    u8 isTouchingPlayer;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitElevator);
        if (self->params & 16) {
            self->animCurFrame = self->params & 15;
            self->zPriority = 0x6A;
            self->step = 2;
            return;
        }
        self->animCurFrame = 0;
        break;

    case 1:
        self->posX.i.hi = entity->posX.i.hi;
        if (self->params == 1) {
            self->posY.i.hi = entity->posY.i.hi + 27;
            isTouchingPlayer = GetPlayerCollisionWith(self, 12, 8, 4);
        } else {
            self->posY.i.hi = entity->posY.i.hi - 32;
            isTouchingPlayer = GetPlayerCollisionWith(self, 12, 8, 6);
        }
        self->ext.cenElevator.playerCollision = isTouchingPlayer;
        break;
    }
}
