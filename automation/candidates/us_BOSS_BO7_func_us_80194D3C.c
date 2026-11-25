// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo7.h"

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;
extern Tilemap g_Tilemap;
extern EInit g_EInitInteractable;

bool func_us_80194338_from_rbo0(s16* offsets) {
    s32 posY;

    offsets++;
    posY = g_CurrentEntity->posY.i.hi + *offsets + g_Tilemap.scrollY.i.hi;
    posY = 0xD0 - posY;
    if (posY <= 0) {
        g_CurrentEntity->posY.i.hi += posY;
        g_CurrentEntity->velocityX = 0;
        g_CurrentEntity->velocityY = 0;
        return true;
    }
    return false;
}



extern EInit g_EInitCerberos;
extern Entity g_Entities_128[];
extern Entity g_Entities_160[];
extern Entity g_Entities_192[];
extern s16 D_us_801806D8[];
// The three fire-arc spawn offsets form one table of (x, y) pairs. The retail
// data file splits the table at the first y into two labels (D_us_801806F0 at
// the first x, D_us_801806F2 two bytes later), but the retail object's
// references resolve to the same addresses either way: the pair form encodes
// the y access as %lo(D_us_801806F0)+2, which the linker resolves to exactly
// %lo(D_us_801806F2). Reading pairs is also the form that reproduces the
// retail instruction sequence, because splitting the table into two arrays
// makes gcc hoist a pointer walk and spill an extra callee-saved register.
typedef struct {
    u16 x;
    u16 y;
} Unk801806F0;

extern Unk801806F0 D_us_801806F0[];
extern u8 D_us_801806FC[];
extern u8 D_us_80180708[];
extern u8 D_us_8018071C[];
extern u8 D_us_8018072C[];
extern u8 D_us_8018073C[];
extern u8 D_us_80180748[];
extern u8 D_us_80180754[];
extern u8 D_us_80180760[];
extern u8 D_us_8018076C[];
extern u8 D_us_80180778[];
extern u8 D_us_80180788[];
extern u8 D_us_801807E4[];
extern u8 D_us_8018081C[];
extern u16 g_pads_1_pressed;
extern u32 g_Timer;
extern s32 D_us_80180848;

void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void PlaySfxPositional(s32 arg0);

// Cerberus main update. Step 0/2 wake up and wait for the fight trigger,
// step 3 paces and picks an attack from the player's distance, step 4/9
// lunge, step 5 lays a fire wall, step 6 breathes fire, step 8 is the
// death animation, step 0xA bites, step 0xB charges, and step 0xFF is a
// frame-stepping debugger. ext.et_80194D3C.timer paces the timed steps,
// distanceFlag remembers whether the player was close, spawnParams
// rotates the fire-breath emitters and spawnTimer counts the burst.
void func_us_80194D3C(Entity* self) {
    Entity* entity;
    s32 posX;
    s32 side;
    s32 i;

    // Getting hit by anything with this flag forces the death sequence,
    // except while already in it.
    if ((self->flags & 0x100) && self->step != 8) {
        SetStep(8);
    }

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCerberos);
        self->hitboxState = 0;
        SetStep(2);
        /* fallthrough */
    case 2:
        AnimateEntity(D_us_801806FC, self);
        // D_us_80180848 bit 1 is set by the pillar-of-fire entity once the
        // player is close enough to start the fight.
        if (D_us_80180848 & 2) {
            self->hitboxState = 3;
            SetStep(3);
        }
        break;

    case 3:
        if (!self->step_s) {
            self->ext.et_80194D3C.timer = 0x40;
            self->step_s++;
        }
        if (!AnimateEntity(D_us_80180708, self)) {
            PlaySfxPositional(SFX_WARG_GROWL);
        }
        // Track whether the player is in bite range. The two thresholds
        // differ so the flag does not chatter at the boundary.
        if (GetDistanceToPlayerX() < 0x68) {
            self->ext.et_80194D3C.distanceFlag = 1;
        }
        if (GetDistanceToPlayerX() >= 0x81) {
            self->ext.et_80194D3C.distanceFlag = 0;
        }
        if (GetDistanceToPlayerX() >= 0x31) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        }
        MoveEntity();
        // Drift toward the player while pacing.
        if (self->facingLeft == self->ext.et_80194D3C.distanceFlag) {
            self->velocityX = -0x8000;
        } else {
            self->velocityX = 0x8000;
        }
        if (--self->ext.et_80194D3C.timer == 0) {
            // Reuse the spawn variable for the player address instead of
            // declaring a local. Retail holds &g_Entities in $s0 from here to
            // the end of the function and reuses that same register for the
            // AllocEntity spawns in steps 5, 6 and 8, which only happens if
            // both are one variable. A separate local becomes its own allocno
            // with too few references to outrank posX, so posX takes $s0 and
            // the player address is pushed to $s3.
            entity = &PLAYER;

            // Freeze the pacing position before the arena-relative checks.
            // SetStep clears the pose fields, so read the position first.
            posX = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
            SetStep(0xA);
            if (self->facingLeft) {
                posX = 0x200 - posX;
            }
            side = (GetSideToPlayer() & 1) ^ 1;
            if (posX < 0xD0 && self->facingLeft == side) {
                SetStep(9);
            }
            if (abs(posX) >= 0x51 && self->facingLeft != side) {
                SetStep(9);
            }
            if (posX >= 0x141 && self->facingLeft == side) {
                SetStep(6);
            }
            if (posX >= 0x181 && self->facingLeft == side) {
                SetStep(4);
            }
            // A bat or a grounded player below the arena centre is a free
            // hit, so go straight to the fire wall.
            if ((g_Player.status & PLAYER_STATUS_BAT_FORM) ||
                (entity->posY.i.hi < 0xA0 &&
                 (g_Player.vram_flag & TOUCHING_GROUND))) {
                SetStep(5);
            }
        }
        break;

    case 0xB:
        switch (self->step_s) {
        case 0:
            if (!AnimateEntity(D_us_8018071C, self)) {
                if (self->facingLeft) {
                    self->velocityX = -0x60000;
                } else {
                    self->velocityX = 0x60000;
                }
                self->ext.et_80194D3C.timer = 0x40;
                self->step_s++;
            }
            break;
        case 1:
            MoveEntity();
            self->velocityX -= self->velocityX >> 6;
            if (--self->ext.et_80194D3C.timer == 0) {
                SetStep(3);
            }
            break;
        }
        break;

    case 5:
        switch (self->step_s) {
        case 0:
            if (!AnimateEntity(D_us_80180754, self)) {
                SetSubStep(1);
            }
            break;
        case 1:
            if (!AnimateEntity(D_us_80180748, self)) {
                PlaySfxPositional(SFX_WARG_ATTACK);
                PlaySfxPositional(SFX_SHAFT_FIRE_ATTACK);
                self->ext.et_80194D3C.timer = 0x80;
                SetSubStep(2);
            }
            break;
        case 2:
            // Every fourth frame, launch one of the three fire arcs.
            if ((self->ext.et_80194D3C.timer & 3) == 0) {
                for (i = 0; i < 3; i++) {
                    entity = AllocEntity(
                        &g_Entities_128[0],
                        &g_Entities_128[0x4680 / sizeof(Entity)]);
                    if (entity != NULL) {
                        CreateEntityFromEntity(E_UNK_1E, self, entity);
                        if (self->facingLeft) {
                            entity->posX.i.hi -= D_us_801806F0[i].x;
                        } else {
                            entity->posX.i.hi += D_us_801806F0[i].x;
                        }
                        entity->posY.i.hi += D_us_801806F0[i].y;
                        entity->params = i;
                        entity->zPriority = self->zPriority + 1;
                        entity->facingLeft = self->facingLeft;
                    }
                }
            }
            if (--self->ext.et_80194D3C.timer == 0) {
                self->step_s++;
            }
            break;
        case 3:
            if (AnimateEntity(D_us_80180760, self)) {
                SetStep(3);
            }
            break;
        }
        break;

    case 0xA:
        if (!AnimateEntity(D_us_8018073C, self)) {
            SetStep(3);
        }
        if (self->pose == 3 && !self->poseTimer) {
            PlaySfxPositional(SFX_B07_STOMP);
            PlaySfxPositional(SFX_WARG_ATTACK);
            entity = AllocEntity(
                &g_Entities_160[0], &g_Entities_160[0x1780 / sizeof(Entity)]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_UNK_1D, self, entity);
                entity->facingLeft = self->facingLeft;
                if (self->facingLeft) {
                    entity->posX.i.hi += 0x18;
                } else {
                    entity->posX.i.hi -= 0x18;
                }
                entity->params = self->ext.et_80194D3C.spawnParams;
                entity->zPriority = self->zPriority + 1;
            }
        }
        break;

    case 9:
        switch (self->step_s) {
        case 0:
            if (!AnimateEntity(D_us_80180778, self)) {
                SetSubStep(1);
            }
            break;
        case 1:
            self->velocityY = -0x60000;
            if (self->facingLeft) {
                self->velocityX = -0x28000;
            } else {
                self->velocityX = 0x28000;
            }
            self->step_s++;
            /* fallthrough */
        case 2:
            MoveEntity();
            self->velocityY += 0x3800;
            if (func_us_80194338_from_rbo0(D_us_801806D8) & 1) {
                PlaySfxPositional(SFX_START_SLAM_B);
                g_api_func_80102CD8(1);
                self->step_s++;
            }
            break;
        case 3:
            if (!AnimateEntity(D_us_80180788, self)) {
                SetStep(3);
            }
            break;
        }
        break;

    case 4:
        switch (self->step_s) {
        case 0:
            if (!AnimateEntity(D_us_80180778, self)) {
                SetSubStep(1);
            }
            break;
        case 1:
            self->velocityY = -0x60000;
            if (self->facingLeft) {
                self->velocityX = 0x28000;
            } else {
                self->velocityX = -0x28000;
            }
            self->step_s++;
            /* fallthrough */
        case 2:
            MoveEntity();
            self->velocityY += 0x3800;
            if (func_us_80194338_from_rbo0(D_us_801806D8) & 1) {
                PlaySfxPositional(SFX_START_SLAM_B);
                g_api_func_80102CD8(1);
                self->step_s++;
            }
            break;
        case 3:
            if (!AnimateEntity(D_us_80180788, self)) {
                SetStep(3);
            }
            break;
        }
        break;

    case 6:
        switch (self->step_s) {
        case 0:
            self->ext.et_80194D3C.spawnTimer = 8;
            self->step_s++;
            /* fallthrough */
        case 1:
            if (!AnimateEntity(D_us_8018072C, self)) {
                if (--self->ext.et_80194D3C.spawnTimer == 0) {
                    SetStep(3);
                }
            }
            // On the head-down pose of the breath animation, spit a flame at
            // one of the three spawn slots. This sits inside substep 1, not
            // after the switch: the retail default arm jumps straight to the
            // function tail, so a substep past 1 never reaches the pose test.
            if (self->pose == 5 && !self->poseTimer) {
                PlaySfxPositional(SFX_B07_STOMP);
                PlaySfxPositional(SFX_WARG_ATTACK);
                entity = AllocEntity(
                    &g_Entities_160[0],
                    &g_Entities_160[0x1780 / sizeof(Entity)]);
                if (entity != NULL) {
                    CreateEntityFromEntity(E_UNK_1D, self, entity);
                    entity->facingLeft = self->facingLeft;
                    if (self->facingLeft) {
                        entity->posX.i.hi += 0x18;
                    } else {
                        entity->posX.i.hi -= 0x18;
                    }
                    entity->params = self->ext.et_80194D3C.spawnParams;
                    entity->zPriority = self->zPriority + 1;
                }
                // The rotation sits inside the pose arm: the pose-false path
                // jumps straight to the function tail in the retail object.
                self->ext.et_80194D3C.spawnParams++;
                if (self->ext.et_80194D3C.spawnParams >= 3) {
                    self->ext.et_80194D3C.spawnParams = 0;
                }
            }
            break;
        }
        break;

    case 8:
        switch (self->step_s) {
        case 0:
            self->hitboxState = 0;
            D_us_80180848 |= 4;
            PlaySfxPositional(SFX_WARG_DEATH_HOWL);
            self->step_s++;
            /* fallthrough */
        case 1:
            // Scatter death flames around the body every eighth frame.
            if ((g_Timer & 7) == 0) {
                PlaySfxPositional(SFX_EXPLODE_B);
                entity = AllocEntity(
                    &g_Entities_192[0],
                    &g_Entities_192[0x2F00 / sizeof(Entity)]);
                if (entity != NULL) {
                    CreateEntityFromEntity(E_UNK_20, self, entity);
                    entity->params = 1;
                    entity->zPriority = self->zPriority + 1;
                    entity->posX.i.hi += (Random() & 0x3F) - 0x20;
                    entity->posY.i.hi += (Random() & 0x1F) - 0xC;
                }
            }
            if (!AnimateEntity(D_us_8018076C, self)) {
                PlaySfxPositional(SFX_BOSS_LARGE_FLAMES);
                self->ext.et_80194D3C.timer = 0x50;
                self->step_s++;
            }
            break;
        case 2:
            entity = AllocEntity(
                &g_Entities_192[0], &g_Entities_192[0x2F00 / sizeof(Entity)]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_UNK_20, self, entity);
                entity->params = 2;
                entity->zPriority = self->zPriority + 1;
                entity->posX.i.hi += (Random() & 0x3F) - 0x20;
                // The second burst leans away from the body.
                if (self->facingLeft) {
                    entity->posX.i.hi -= 0xC;
                } else {
                    entity->posX.i.hi += 0xC;
                }
                entity->posY.i.hi += 0x18;
            }
            if (--self->ext.et_80194D3C.timer == 0) {
                self->animCurFrame = 0;
                self->step_s++;
            }
            break;
        case 3:
            D_us_80180848 |= 8;
            self->step_s++;
            break;
        case 4:
            break;
        }
        break;

    case 0xFF:
        FntPrint("charal %x\n", self->animCurFrame);
        if (g_pads_1_pressed & 0x80) {
            if (self->params) {
                break;
            }
            self->animCurFrame++;
            self->params |= 1;
        } else {
            self->params = 0;
        }
        if (g_pads_1_pressed & 0x20) {
            if (self->step_s) {
                break;
            }
            self->animCurFrame--;
            self->step_s |= 1;
        } else {
            self->step_s = 0;
        }
        break;
    }

    // Keep the body inside the arena. The left wall is checked only while
    // moving left, and the right wall only while moving right or standing.
    posX = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
    if (self->velocityX < 0) {
        if (posX < 0x68) {
            self->posX.i.hi = 0x68 - g_Tilemap.scrollX.i.hi;
        }
    } else if (posX >= 0x1A1) {
        self->posX.i.hi = 0x1A0 - g_Tilemap.scrollX.i.hi;
    }

    // Pick the current animation frame's hitbox. The first two bytes are
    // signed offsets, the last two are the box dimensions.
    {
        u8* hitbox;
        s32 animFrame;

        // Same idiom as EntityHarpyKick: assign the table base to the pointer
        // first and then add the scaled frame index. Writing it as a single
        // subscripted address instead makes gcc target the index register for
        // the add, which reverses the retail operand order.
        hitbox = D_us_801807E4;
        animFrame = D_us_8018081C[self->animCurFrame];
        hitbox += animFrame * 4;

        self->hitboxOffX = (s8)*hitbox++;
        self->hitboxOffY = (s8)*hitbox++;
        self->hitboxWidth = *hitbox++;
        self->hitboxHeight = *hitbox;
    }
}

extern EInit D_us_8018046C;
extern s32 D_us_801807BC[];
extern s32 D_us_80180848;

// params: select which animation to play from the anim pointer table
void func_us_801959E0(Entity* self) {
    Entity* entity;

    // boss state word: the projectile parent drives bit 4
    if (D_us_80180848 & 4) {
        DestroyEntity(self);
        return;
    }

    if (self->flags & FLAG_DEAD) {
        entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_EXPLOSION, self, entity);
            entity->params = 1;
        }
        DestroyEntity(self);
        return;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_8018046C);
        if (self->facingLeft) {
            self->velocityX = FIX(6);
        } else {
            self->velocityX = FIX(-6);
        }
        /* fallthrough */
    case 1:
        MoveEntity();
        AnimateEntity(D_us_801807BC[self->params], self);
        break;
    }
}

extern EInit D_us_80180478;
extern u16 D_us_801806E8[];
extern u8 D_us_801807C8[];

// E_UNK_1E: spinning arc launcher.
// params: selects the palette entry taken from the D_us_801806E8 table.
// On pose 8 of the anim it spawns another E_UNK_1E from the first-half
// entity pool, copying params and facing so the arc repeats.
void func_us_80195AF0(Entity* self) {
    Entity* entity;
    s16 angle;

    if (D_us_80180848 & 4) {
        DestroyEntity(self);
        return;
    }

    if (self->step == 0) {
        InitializeEntity(D_us_80180478);
        self->drawFlags = 5;
        self->scaleX = 0x80;
        self->palette = D_us_801806E8[self->params];
        self->rotate = -0x280;
        if (self->facingLeft) {
            angle = -0x180;
        } else {
            angle = -0x680;
        }
        self->velocityX = ((rcos(angle) * 3) << 17) >> 12;
        self->velocityY = ((rsin(angle) * 3) << 17) >> 12;
    }

    MoveEntity();
    if (!AnimateEntity(D_us_801807C8, self)) {
        DestroyEntity(self);
    }
    if (self->pose == 8 && !self->poseTimer) {
        entity = AllocEntity(&g_Entities[128], &g_Entities[224]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_UNK_1E, self, entity);
            entity->params = self->params;
            entity->facingLeft = self->facingLeft;
        }
    }
}

// Cerberus pillar of fire: allocates seven prims. The first two are ENV
// carriers for a backdrop clear rect, the third is the rcos-pulsing glow
// base, and the last four are the scrolling pillar slices. D_us_80180848
// bits drive the rig: bit 1 arms it once the player is close, bit 2 fires
// the defeat TimeAttack record, bit 4 switches the fade over to
// PrimDecreaseBrightness once the pillar sequence has finished.
/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GameApi g_api;
extern Primitive g_PrimBuf[];
extern u32 g_Timer;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern GAME_IMPORT GpuBuffer* g_CurrentBuffer; // g_CurrentBuffer;

void func_us_80195C50(Entity* self) {
    Entity* entity;
    Entity* first;
    s32 primIndex;
    s32 i;
    u32 xAcc;
    s32 w1;
    s32 w2;
    s32 posX;
    s32 posY;
    Primitive* prim;
    DR_ENV* drEnv;
    RECT clip;
    DRAWENV drawEnv;

    // CODEGEN: A normal switch aligns its generated table to eight
    // bytes and pads one word before the target jump table at
    // 0x80192E58, shifting every later BO7 symbol by four bytes. The
    // explicit four-byte-aligned dispatch table preserves the original
    // section layout.
    static void* const jtbl[] ALIGNED4 = {
        &&case_0, &&case_1, &&case_2, &&case_3,
        &&case_4, &&case_5, &&case_6, &&case_7,
    };
    if ((u32)self->step >= 8) {
        goto step_tail;
    }
    goto *jtbl[self->step];

case_0:
        InitializeEntity(g_EInitInteractable);
        self->flags |= FLAG_UNK_10000;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 7);
        if (primIndex == -1) {
            self->step = 0;
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        drEnv = g_api.func_800EDB08((POLY_GT4*)prim);
        if (!drEnv) {
            g_api.FreePrimitives(primIndex);
            self->step = 0;
            self->flags &= ~FLAG_HAS_PRIMS;
            return;
        } else {
            prim->type = PRIM_ENV;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
            drEnv = g_api.func_800EDB08((POLY_GT4*)prim);
            if (prim == NULL) {
                g_api.FreePrimitives(primIndex);
                self->step = 0;
                self->flags &= ~FLAG_HAS_PRIMS;
                return;
            }
        }
        i = 0;
        prim->type = PRIM_ENV;
        prim->drawMode = DRAW_HIDE;
        prim = prim->next;
        self->ext.et_801B0930.prim7C = prim;
        prim->type = PRIM_G4;
        prim->r0 = prim->g0 = prim->b0 = 0;
        w1 = LOW(prim->r0);
        prim->x1 = prim->x3 = 0x42;
        prim->y2 = prim->y3 = 0xB0;
        prim->r2 = 0xFF;
        prim->g2 = prim->b2 = 0;
        w2 = LOW(prim->r2);
        prim->x0 = prim->x2 = 0;
        prim->y0 = prim->y1 = 0;
        prim->priority = 0xF;
        prim->drawMode = DRAW_DEFAULT;
        LOW(prim->r1) = w1;
        LOW(prim->r3) = w2;
        prim = prim->next;
        for (; i < 4; i++) {
            prim->tpage = 0x110;
            if (i & 1) {
                prim->u0 = prim->u2 = 0x3F;
                prim->u1 = prim->u3 = 0;
            } else {
                prim->u0 = prim->u2 = 0;
                prim->u1 = prim->u3 = 0x3F;
            }
            prim->x0 = prim->x2 = i * 0x40;
            prim->v0 = prim->v1 = 0x10;
            prim->v2 = prim->v3 = 0xF0;
            prim->x1 = prim->x3 = (xAcc = ((i * 0x40) + 0x40));
            prim->y0 = prim->y1 = 0x10;
            prim->y2 = prim->y3 = 0xF0;
            prim->drawMode = DRAW_DEFAULT;
            prim->priority = 0x13;
            prim = prim->next;
        }
        g_api.PlaySfx(SFX_BOSS_LARGE_FLAMES);
case_1:
        posX = PLAYER.posX.i.hi + g_Tilemap.scrollX.i.hi;
        if ((u32)(posX - 0x41) < 0x17F) {
            D_us_80180848 |= 1;
            self->step++;
        }
        if (g_Timer % 95 == 0) {
            g_api.PlaySfx(SFX_BOSS_LARGE_FLAMES);
        }
        goto step_tail;

case_2:
        if (g_Timer % 95 == 0) {
            g_api.PlaySfx(SFX_BOSS_LARGE_FLAMES);
        }
        posX = PLAYER.posX.i.hi + g_Tilemap.scrollX.i.hi;
        if ((u32)(posX - 0x81) < 0xFF) {
            g_api.TimeAttackController(TIMEATTACK_EVENT_CERBERUS_DEFEAT, TIMEATTACK_SET_VISITED);
            stopMusicFlag = 1;
            currentMusicId = 0x31D;
            D_us_80180848 |= 2;
            self->step++;
        }
        goto step_tail;

case_3:
        if (!g_api.func_80131F68()) {
            stopMusicFlag = 0;
            g_api.PlaySfx(currentMusicId);
            self->step++;
        }
case_4:
        if (D_us_80180848 & 4) {
            g_api.TimeAttackController(TIMEATTACK_EVENT_CERBERUS_DEFEAT, TIMEATTACK_SET_RECORD);
            g_api.PlaySfx(0x90);
            currentMusicId = 0x319;
            self->step++;
        }
        goto step_tail;

case_5:
        if (D_us_80180848 & 8) {
            self->step++;
        }
        goto step_tail;

case_6:
        posX = 0x100 - g_Tilemap.scrollX.i.hi;
        posY = 0x80 - g_Tilemap.scrollY.i.hi;
        first = &g_Entities[160];
        entity = AllocEntity(first, first + 32);
        if (entity != NULL) {
            CreateEntityFromEntity(E_LIFE_UPSPAWN, self, entity);
            entity->posX.i.hi = posX;
            entity->posY.i.hi = posY;
            entity->params = 5;
            stopMusicFlag = 1;
            currentMusicId = 0x319;
            D_us_80180848 |= 0x10;
            self->step++;
        }
case_7:
        if (!g_api.func_80131F68()) {
            stopMusicFlag = 0;
            g_api.PlaySfx(currentMusicId);
            self->step++;
        }
        goto step_tail;

step_tail:
    prim = &g_PrimBuf[self->primIndex];
    drawEnv = g_CurrentBuffer->draw;
    drawEnv.isbg = 1;
    drawEnv.r0 = 0;
    drawEnv.g0 = 0;
    drawEnv.b0 = 0;
    clip.x = 0;
    clip.y = 0x100;
    clip.w = 0x7F;
    clip.h = 0xFF;
    drawEnv.clip = clip;
    drawEnv.ofs[0] = 0;
    drawEnv.ofs[1] = 0x100;
    SetDrawEnv((DR_ENV*)LOW(prim->r1), &drawEnv);
    prim->priority = 0xE;
    prim->drawMode = DRAW_DEFAULT;
    prim = prim->next;
    prim->priority = 0x11;
    prim->drawMode = DRAW_UNK_800;

    prim = self->ext.et_801B0930.prim7C;
    self->rotate += 0x100;
    if (D_us_80180848 & 4) {
        PrimDecreaseBrightness(prim, 4);
    } else {
        prim->g2 = abs((rcos(self->rotate) << 7) >> 12);
        LOW(prim->r3) = LOW(prim->r2);
    }
    if ((D_us_80180848 & 4) == 0 && (g_Timer & 3) == 0) {
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromCurrentEntity(E_UNK_20, entity);
            entity->posX.i.hi = (Random() & 0x3F) + 0xA;
            entity->posY.i.hi = 0xB0;
            entity->zPriority = 0x10;
            entity->params = 0;
        }
    }
}


typedef struct {
    u16 animSet;
    u16 unk5A;
    u16 palette;
    u8 blendMode;
    u8 unk07;
    AnimateEntityFrame* frames;
} Unk801808A4;

extern Unk801808A4 D_us_801808A4[];
extern EInit g_EInitParticle;

// E_UNK_20: death-flame particle burst. params & 0xF picks one of the three
// Unk801808A4 triples (animSet, unk5A, palette, blendMode, frames) and the
// chosen step becomes index + 1. params & 0xFF00 carries an optional
// zPriority override and params & 0xF0 forces the shared PAL_FLAG(0x19F)
// tint with additive blending. Step 1 and step 3 seed their movement only
// on the first frame (step_s gate); every frame they move, add the
// deathFlames.unk8C gravity word to velocityY, fade opacity and burn out
// when the animation finishes. Step 2 is the variant without gravity or
// fade (init velocity once, plain move, plain animation).
void func_us_801963D8(Entity* self) {
    Unk801808A4* temp_v1_2;
    s32 params;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitParticle);
        params = self->params & 0xF;
        temp_v1_2 = &D_us_801808A4[params];
        self->palette = temp_v1_2->palette + 0x2E0;
        self->blendMode = temp_v1_2->blendMode;
        self->animSet = temp_v1_2->animSet;
        self->unk5A = temp_v1_2->unk5A;
        self->ext.deathFlames.frames = temp_v1_2->frames;
        self->step = params + 1;
        if (self->params & 0xFF00) {
            self->zPriority = (self->params & 0xFF00) >> 8;
        }
        if (self->params & 0xF0) {
            self->palette = PAL_FLAG(0x19F);
            self->blendMode = BLEND_TRANSP;
            self->facingLeft = true;
        }
        break;

    case 1:
        if (!self->step_s) {
            self->drawFlags = 8;
            self->opacity = 0x50;
            self->flags &= ~FLAG_POS_CAMERA_LOCKED;
            self->facingLeft = Random() & 1;
            self->velocityX = (Random() << 8) - 0x8000;
            self->velocityY = -0x18000;
            self->ext.deathFlames.unk8C = -(Random() << 4) - 0x1000;
            self->step_s++;
        }
        MoveEntity();
        self->velocityY += self->ext.deathFlames.unk8C;
        self->opacity = self->opacity + 0xFF;
        if (!AnimateEntity(self->ext.deathFlames.frames, self)) {
            DestroyEntity(self);
        }
        break;

    case 2:
        if (!self->step_s) {
            self->velocityY = -0x4000;
            self->step_s++;
        }
        MoveEntity();
        if (!AnimateEntity(self->ext.deathFlames.frames, self)) {
            DestroyEntity(self);
        }
        break;

    case 3:
        if (!self->step_s) {
            self->drawFlags = 8;
            self->opacity = 0xC0;
            self->facingLeft = Random() & 1;
            self->velocityX = (Random() << 8) - 0x8000;
            self->velocityY = -0xC000;
            self->ext.deathFlames.unk8C = -(Random() << 4) - 0x4000;
            self->step_s++;
        }
        MoveEntity();
        self->velocityY += self->ext.deathFlames.unk8C;
        self->opacity = self->opacity + 0xFF;
        if (!AnimateEntity(self->ext.deathFlames.frames, self)) {
            DestroyEntity(self);
        }
        break;
    }
}
