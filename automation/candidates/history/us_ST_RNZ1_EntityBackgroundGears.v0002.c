/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityBackgroundGears
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/nz1/e_bg_gears.c
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
void DestroyEntity(Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int AnimateEntity();
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GameApi g_api;

void EntityBackgroundGears(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s32 i, j;
    s32 posX;
    s32 posY;
    s32 u;
    s32 v;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        self->posX.i.hi = 0;
        self->posY.i.hi = 0;
        self->unk68 = 0x80;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 9);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.prim = prim;
        while (prim != NULL) {
            prim->tpage = 0xF;
            prim->clut = 8;
            prim->priority = 0x20;
            prim->drawMode = DRAW_UNK02;
            prim = prim->next;
        }
         

    case 1:
        AnimateEntity(D_us_80180FB0, self);

        posX = self->posX.i.hi;
        posX &= 0x7F;
        posX -= 128;
        posY = self->posY.i.hi;
        posY &= 0x7F;
        posY -= 128;
        u = 0;
        v = 0;
        if (self->animCurFrame == 2) {
            u = 128;
        }
        if (self->animCurFrame == 3) {
            v = 128;
        }

        prim = self->ext.prim;
        for (i = 0; i < 3; i++) {
            for (j = 0; j < 3; j++) {
                prim->x0 = prim->x2 = posX + (j * 128);
                prim->x1 = prim->x3 = posX + (j * 128) + 128;
                prim->y0 = prim->y1 = posY + (i * 128);
                prim->y2 = prim->y3 = posY + (i * 128) + 128;
                prim->u0 = prim->u2 = u;
                prim->u1 = prim->u3 = u + 127;
                prim->v0 = prim->v1 = v;
                prim->v2 = prim->v3 = v + 127;
                prim->drawMode = DRAW_DEFAULT;
                prim = prim->next;
            }
        }
        while (prim != NULL) {
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
        break;
    }
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GAME_IMPORT Point32 D_8006C38C;

extern EInit g_EInitEnvironment;

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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitEnvironment;

extern EInit g_EInitEnvironment;
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

extern EInit g_EInitEnvironment;
extern AnimationFrame D_us_80180F5C[2];

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

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysSmall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWallGear);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretAreaDoor);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWallPartial);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretWallDebris);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", func_us_801A8F7C);

extern EInit g_EInitInteractable;
extern s16 D_us_80181024[7][4];

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
