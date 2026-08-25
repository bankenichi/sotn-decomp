/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityGearSidewaysSmall
   source : upstream/master:src/st/nz1/e_gear_small.c
   target : src/st/rnz1/unk_276A8.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBackgroundGears);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysLarge);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearHorizontal);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearVertical);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitEnvironment;

void EntityGearSidewaysSmall(Entity* self) {
    Entity* player;
    s16 angle;
    s32 offsetX;
    s32 offsetY;
    s32 collision;
    s32 params;  

    switch (self->step) {
    case 0x0:
        InitializeEntity(g_EInitEnvironment);
        self->zPriority = 0x6C;
        self->animCurFrame = 0xC;
        self->drawFlags = ENTITY_ROTATE;
        self->velocityY = FIX(0.5);
         

    case 0x1:

        player = &PLAYER;
        if (self->ext.gearPuzzle.collision & 4) {
            offsetY = self->posY.i.hi + g_Tilemap.scrollY.i.hi;
            params = offsetY - self->ext.gearPuzzle.offsetY;
            player->posY.i.hi += params;
            g_unkGraphicsStruct.shoveY.i.hi += params;
        }

        self->rotate += 64;

        MoveEntity();
        offsetY = self->posY.i.hi + g_Tilemap.scrollY.i.hi;
        params = self->params;
        if (offsetY < D_us_80180FC8[params].x) {
            self->velocityY = FIX(0.5);
        }
        if (D_us_80180FC8[params].y < offsetY) {
            self->velocityY = -FIX(0.5);
        }

        offsetX = player->posX.i.hi;
        offsetY = player->posY.i.hi + 25;
        offsetX -= self->posX.i.hi;
        offsetY -= self->posY.i.hi;

        angle = ratan2(offsetY, offsetX);
        if (angle <= 0) {
            offsetX = (14 * rcos(angle)) << 4;
            offsetY = (14 * rsin(angle)) << 4;
            self->hitboxOffX = (s16)(offsetX >> 0x10);
            self->hitboxOffY = (s16)(offsetY >> 0x10);
            collision = GetPlayerCollisionWith(self, 6, 2, 4);
            if (collision & 4) {
                angle += 64;
                offsetX = (rcos(angle) * 14 * 16) - offsetX;
                offsetY = (rsin(angle) * 14 * 16) - offsetY;

                player = &PLAYER;
                player->posX.val += offsetX;
                player->posY.val += FIX(1) + offsetY;
                g_unkGraphicsStruct.shoveX.val += offsetX;
                g_unkGraphicsStruct.shoveY.val += offsetY;
            }
        }
        break;
    case 0xFF:
#include "../pad2_anim_debug.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void MoveEntity();
long ratan2(long y, long x);
int rcos(int a);
int rsin(int a);
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
/* End permuter-seed writer declarations. */
        break;
    }
    self->ext.gearPuzzle.collision = collision;
    self->ext.gearPuzzle.offsetY = self->posY.i.hi + g_Tilemap.scrollY.i.hi;
}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWallGear);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretAreaDoor);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWallPartial);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretWallDebris);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", func_us_801A8F7C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWaterForeground);
