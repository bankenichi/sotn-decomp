/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityGearVertical
   source : upstream/master:src/st/nz1/e_gear_vertical.c
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
u8 AnimateEntity(u8 frames[], Entity* entity);
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
/* End permuter-seed writer declarations. */


INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBackgroundGears);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysLarge);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearHorizontal);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitEnvironment;

void EntityGearVertical(Entity* self) {
    Entity* player;
    s32 collision;
    s32 posY;
    s32 offsetY;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitEnvironment);
        self->zPriority = 0x6C;
        self->drawFlags = ENTITY_ROTATE;
        self->rotate = 0x400;
         

    case 1:
        AnimateEntity(D_us_80180FC0, self);
#ifdef VERSION_PSP
        collision = GetPlayerCollisionWith(self, 8, 0x20, 5);
#else
        if (g_Player.vram_flag & (TOUCHING_L_WALL | TOUCHING_R_WALL)) {
            collision = 4;
        } else {
            collision = 5;
        }
        collision = GetPlayerCollisionWith(self, 8, 0x20, collision | 0x8);
#endif
        self->ext.gearPuzzle.cooldownTimer = 0x20;
        if (collision & 4) {
            self->step++;
        }
        break;

    case 2:
        AnimateEntity(&D_us_80180FC0, self);
#ifndef VERSION_PSP
        collision = 0;
#endif
        self->ext.gearPuzzle.cooldownTimer--;
        if (!self->ext.gearPuzzle.cooldownTimer) {
            self->ext.gearPuzzle.timer2 = 0x20;
            self->step = 3;
        } else {
            player = &PLAYER;
            if (self->ext.gearPuzzle.collision & 4) {
                posY = self->posY.i.hi + g_Tilemap.scrollY.i.hi -
                       self->ext.gearPuzzle.cooldownTimer;
                offsetY = posY - self->ext.gearPuzzle.offsetY;
                player->posY.i.hi += offsetY;
                g_unkGraphicsStruct.shoveY.val += offsetY;
            }
#ifdef VERSION_PSP
            collision = GetPlayerCollisionWith(
                self, 8, self->ext.gearPuzzle.cooldownTimer, 5);
#else
            if (g_Player.vram_flag & (TOUCHING_L_WALL | TOUCHING_R_WALL)) {
                collision = 4;
            } else {
                collision = 5;
            }
            collision = GetPlayerCollisionWith(
                self, 8, self->ext.gearPuzzle.cooldownTimer, collision | 0x8);
#endif
            if (!(collision & 4)) {
                self->ext.gearPuzzle.timer2 = 0x10;
                self->step = 3;
            }
        }
        break;

    case 3:
        AnimateEntity(&D_us_80180FC0, self);
        collision = 0;

        if (!--self->ext.gearPuzzle.timer2) {
            self->step = 1;
        }
        break;
    }
    self->ext.gearPuzzle.collision = collision;
    self->ext.gearPuzzle.offsetY = self->posY.i.hi + g_Tilemap.scrollY.i.hi -
                                   self->ext.gearPuzzle.cooldownTimer;
}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysSmall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWallGear);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretAreaDoor);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWallPartial);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretWallDebris);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", func_us_801A8F7C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWaterForeground);
