/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNZ1:EntityGearSidewaysSmall
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/nz1/e_gear_small.c
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
u8 AnimateEntity(u8 frames[], Entity* entity);
void MoveEntity();
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */


INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBackgroundGears);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit g_EInitEnvironment;

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern PlayerState g_Player;
extern GAME_IMPORT Point32 D_8006C38C;
extern unkGraphicsStruct g_unkGraphicsStruct;

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



/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern u8 D_us_80180F54[8];

void EntityGearHorizontal(Entity* self) {
    Entity* player;
    s32 collision;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitEnvironment);
        self->zPriority = 0x6C;


    case 1:
        AnimateEntity(D_us_80180F54, self);
        collision = GetPlayerCollisionWith(self, 0x20, 8, 4);
        if (collision != 0) {
            player = &PLAYER;
            if (!self->params) {
                if (!(g_Player.vram_flag & TOUCHING_R_WALL)) {
                    player->posX.val += FIX(0.25);
                    g_unkGraphicsStruct.shoveX.val += FIX(0.25);
                }
            } else {
                if (!(g_Player.vram_flag & TOUCHING_L_WALL)) {
                    player->posX.val -= FIX(0.25);
                    g_unkGraphicsStruct.shoveX.val -= FIX(0.25);
                }
            }
        }
        break;
    }
}



/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern AnimationFrame D_us_80180F5C[2];

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;

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
        AnimateEntity(D_us_80180F5C, self);
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
        AnimateEntity(&D_us_80180F5C, self);
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
        AnimateEntity(&D_us_80180F5C, self);
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
#include
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

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit g_EInitInteractable;
extern s16 D_us_80181024[7][4];

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Primitive g_PrimBuf[];

void EntityWaterForeground(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s16* ptr;
    s32 x, y;
    s32 params;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        primIndex = g_api_AllocPrimitives(PRIM_TILE, 1);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.prim = prim;
        prim->r0 = 0x48;
        prim->g0 = 0x40;
        prim->b0 = 0xC0;
        params = self->params;
        ptr = (s16*)D_us_80181024[params];
        x = ptr[0] - g_Tilemap.scrollX.i.hi;
        y = ptr[1] - g_Tilemap.scrollY.i.hi;
        prim->x0 = x;
        prim->y0 = y;
        prim->u0 = ptr[2];
        prim->v0 = ptr[3];
        prim->priority = 0x9A;
        prim->drawMode = DRAW_TPAGE | DRAW_UNK02 | DRAW_TRANSP;
        break;
    case 1:
        break;
    }
}


