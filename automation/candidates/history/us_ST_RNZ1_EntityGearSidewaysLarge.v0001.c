/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityGearSidewaysLarge
   source : upstream/master:src/st/nz1/e_gear_large.c
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
void PlaySfxPositional(s32 arg0);
long ratan2(long y, long x);
int rcos(int a);
int rsin(int a);
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBackgroundGears);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitEnvironment;
extern GAME_IMPORT Point32 D_8006C38C;

void EntityGearSidewaysLarge(Entity* self) {
    Entity* player;
    s16 angle;
    s32 offsetX;
    s32 offsetY;
    s32 collision;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitEnvironment);
        self->zPriority = 0x6C;
        self->hitboxState = 1;
        self->hitboxWidth = 8;
        self->hitboxHeight = 3;
        self->animCurFrame = 3;
        self->drawFlags = ENTITY_ROTATE;
        self->ext.gearPuzzle.cooldownTimer = 0x80;
         

    case 1:
        self->rotate += 8;
        if (!--self->ext.gearPuzzle.cooldownTimer) {
            self->ext.gearPuzzle.cooldownTimer = 0x80;
            PlaySfxPositional(SFX_CLOCK_TOWER_GEAR);
        }

        player = &PLAYER;
        offsetX = player->posX.i.hi;
        offsetY = player->posY.i.hi + 26;
        offsetX -= self->posX.i.hi;
        offsetY -= self->posY.i.hi;
        angle = ratan2(offsetY, offsetX);
        if (angle <= 0) {
            offsetX = rcos(angle) * 54 * 16;
            offsetY = rsin(angle) * 54 * 16;
            self->hitboxOffX = offsetX >> 16;
            self->hitboxOffY = (offsetY >> 16) - 1;

            if (g_Player.status &
                (PLAYER_STATUS_MIST_FORM | PLAYER_STATUS_BAT_FORM)) {
                collision = 0;
            } else {
                collision = GetPlayerCollisionWith(self, 8, 3, 4);
            }

            if (collision & 4) {
                angle += 8;
                offsetX = (rcos(angle) * 54 * 16) - offsetX;
                offsetY = (rsin(angle) * 54 * 16) - offsetY;
                D_8006C38C.x = offsetY;

                player = &PLAYER;
                if (!(g_Player.vram_flag & TOUCHING_R_WALL)) {

                    player->posX.val += offsetX;
                    g_unkGraphicsStruct.shoveX.val += offsetX;
                }
                player->posY.val += offsetY + FIX(3);
                g_unkGraphicsStruct.shoveY.val += offsetY + FIX(3);
                self->ext.gearPuzzle.offsetX = angle;
            }
            self->ext.gearPuzzle.collision = collision;
        }
        break;
    }
}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearHorizontal);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearVertical);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysSmall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWallGear);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretAreaDoor);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWallPartial);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretWallDebris);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", func_us_801A8F7C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWaterForeground);
