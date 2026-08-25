/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNO4:EntityVenusWeed
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/e_venus_weed.h
   target : src/st/rno4/e_blue_venus_weed.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno4.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
s16 GetDistanceToPlayerX();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void PlaySfxPositional(s32 arg0);
void CreateEntityFromCurrentEntity(u16, Entity*);
s32 GetSideToPlayer(void);
int rcos(int a);
int rsin(int a);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetStep();
extern int UnkCollisionFunc3();
extern int AnimateEntity();
extern int PreventEntityFromRespawning();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", SetupPrimsForEntitySpriteParts);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitVenusWeedRoot;
extern GameApi g_api;
extern Primitive g_PrimBuf[];
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern u32 g_Timer;

void EntityVenusWeed(Entity* self) {

    const int SpriteLeavesX = 0x48;
    const int SpriteLeavesY = 0x00;
    const int SpriteLeavesW = 0x38;
    const int SpriteLeavesH = 0x22;
    const int SpriteStemX = 0x00;
    const int SpriteStemY = 0x30;
    const int SpriteStemW = 0x18;
    const int SpriteStemH = 0x22;




    const int ActivateDistanceX = 0x70;

    const int LeavesWidthMax = 0x38;
    const int LeavesHeightMax = 0x22;
    const int StemWidthMax = 0xC;
    const int StemHeightMax = 0x22;
    const int FlowerOffsetY = 0x1B;
    const int WiggleLeavesSpeed = 0x180;
    const int AttackDuration = 0x30;
    const int DeathFinalClut = DEATH_CLUT;

    typedef enum Grow_Substep {
        GROW_LEAVES = 0,
        GROW_STEM = 1,
        GROW_FLOWER = 2,
        GROW_TENDRILS = 3,
        GROW_DONE = 4,
    };

    typedef enum Death_Substep {
        DEATH_INIT = 0,
        DEATH_COLOR_CYCLE = 1,
        DEATH_SHRINK = 2,
        DEATH_DONE = 3,
    };

    Entity* entity;
    s32 x;
    s32 primIdx;
    s32 y;
    Primitive* prim;
    s32 checkCount;
    s32 i;
    s16 rot;


    if ((self->flags & FLAG_DEAD) && (self->step < VENUS_WEED_DEATH)) {
        SetStep(VENUS_WEED_DEATH);
    }

    switch (self->step) {
    case VENUS_WEED_INIT:
        InitializeEntity(g_EInitVenusWeedRoot);
        self->hitboxOffX = 1;
        self->hitboxOffY = -7;




        primIdx = g_api.AllocPrimitives(PRIM_GT4, 3);
        if (primIdx == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIdx;
        prim = &g_PrimBuf[primIdx];
        self->ext.venusWeed.prim = prim;


        for (i = 0; i < 2; i++) {
            prim->tpage = 0x14;
            prim->clut = PLANT_CLUT;
            prim->u0 = prim->u2 = SpriteLeavesX;
            prim->u1 = prim->u3 = SpriteLeavesX + SpriteLeavesW;
            prim->v0 = prim->v1 = SpriteLeavesY;
            prim->v2 = prim->v3 = SpriteLeavesY + SpriteLeavesH;
            prim->priority = self->zPriority - 1;
            prim->drawMode = DRAW_HIDE;

            prim = prim->next;
        }


        self->ext.venusWeed.stemPrim = prim;
        prim->tpage = 0x14;
        prim->clut = PLANT_CLUT;
        prim->u0 = prim->u2 = SpriteStemX;
        prim->u1 = prim->u3 = SpriteStemX + SpriteStemW;
        prim->v0 = prim->v1 = SpriteStemY;
        prim->v2 = prim->v3 = SpriteStemY + SpriteStemH;
        prim->priority = self->zPriority - 2;
        prim->drawMode = DRAW_HIDE;

        prim = prim->next;
        break;

    case VENUS_WEED_DROP_TO_GROUND:
        if (UnkCollisionFunc3(&PhysicsSensors) & 1) {
            SetStep(VENUS_WEED_THORNWEED_DISGUISE);
        }
        break;

    case VENUS_WEED_THORNWEED_DISGUISE:
        AnimateEntity(&AnimFrames_ThornweedDisguise, self);
        if (GetDistanceToPlayerX() < ActivateDistanceX) {
            self->hitboxState = 0;
            SetStep(VENUS_WEED_GROW);
        }


        if (self->flags & FLAG_DEAD) {
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_EXPLOSION, self, entity);
                entity->posY.i.hi -= 4;
                entity->params = 0;
            }

            PlaySfxPositional(SFX_STUTTER_EXPLODE_LOW);
            DestroyEntity(self);
            return;
        }
        break;

    case VENUS_WEED_GROW:
        AnimateEntity(&AnimFrames_ThornweedQuickWiggle, self);

        checkCount = 0;
        switch (self->step_s) {
        case GROW_LEAVES:

            self->ext.venusWeed.leavesWidth += GROWTH_SPEED;
            if (self->ext.venusWeed.leavesWidth > LeavesWidthMax) {
                self->ext.venusWeed.leavesWidth = LeavesWidthMax;
                checkCount += 1;
            }


            self->ext.venusWeed.leavesHeight += GROWTH_SPEED;
            if (self->ext.venusWeed.leavesHeight > LeavesHeightMax) {
                self->ext.venusWeed.leavesHeight = LeavesHeightMax;
                checkCount += 1;
            }


            prim = self->ext.venusWeed.prim;
            x = self->posX.i.hi;
            y = self->posY.i.hi;
            y -= self->ext.venusWeed.leavesHeight;

            for (i = -1; i < 2; i += 2) {
                prim->x0 = prim->x2 = x;
                prim->x1 = prim->x3 = x + self->ext.venusWeed.leavesWidth * i;
                prim->y0 = prim->y1 = y;
                prim->y2 = prim->y3 = self->posY.i.hi;
                prim->drawMode = DRAW_UNK02;

                prim = prim->next;
            }


            if (checkCount == 2) {
                self->step_s++;
            }
            break;

        case GROW_STEM:

            self->ext.venusWeed.stemWidth += GROWTH_SPEED;
            if (self->ext.venusWeed.stemWidth > StemWidthMax) {
                self->ext.venusWeed.stemWidth = StemWidthMax;
                checkCount += 1;
            }


            self->ext.venusWeed.stemHeight += GROWTH_SPEED;
            if (self->ext.venusWeed.stemHeight > StemHeightMax) {
                self->ext.venusWeed.stemHeight = StemHeightMax;
                checkCount += 1;
            }


            prim = self->ext.venusWeed.stemPrim;
            x = self->posX.i.hi;
            y = self->posY.i.hi - self->ext.venusWeed.stemHeight;
            prim->x0 = prim->x2 = x - self->ext.venusWeed.stemWidth;
            prim->x1 = prim->x3 = x + self->ext.venusWeed.stemWidth;
            prim->y0 = prim->y1 = y;
            prim->y2 = prim->y3 = self->posY.i.hi;
            prim->drawMode = DRAW_UNK02;


            if (checkCount == 2) {
                self->step_s++;
            }
            break;

        case GROW_FLOWER:
            entity = self + 1;


            CreateEntityFromCurrentEntity(E_VENUS_WEED_FLOWER, entity);
            entity->posX.i.hi = self->posX.i.hi;
            entity->posY.i.hi = self->posY.i.hi - FlowerOffsetY;


            entity->facingLeft = GetSideToPlayer() & 1;
            entity->zPriority = (s32)self->zPriority;

            self->step_s++;
            break;

        case GROW_TENDRILS:
            entity = self + 2;
            for (i = 0; i < TENDRIL_COUNT; i++, entity++) {
                CreateEntityFromCurrentEntity(E_VENUS_WEED_TENDRIL, entity);
                entity->params = i;
                entity->zPriority = self->zPriority + 1;
            }

            self->step_s++;
            break;

        case GROW_DONE:
            break;
        }
        break;

    case VENUS_WEED_IDLE:
        AnimateEntity(&AnimFrames_ThornweedDisguise, self);
        break;

    case VENUS_WEED_ATTACK:
        if (self->ext.venusWeed.triggerAttack) {
            self->ext.venusWeed.triggerAttack = false;
            self->ext.venusWeed.timer = AttackDuration;
        }
        if (self->ext.venusWeed.timer) {
            AnimateEntity(&AnimFrames_ThornweedQuickWiggle, self);
            self->ext.venusWeed.timer--;
        }
        break;

    case VENUS_WEED_DEATH:
        switch (self->step_s) {
        case DEATH_INIT:
            self->ext.venusWeed.wiggleT = 0;
            self->step_s++;

        case DEATH_COLOR_CYCLE:

            if (!(g_Timer & 7)) {

                self->palette += 1;

                prim = self->ext.venusWeed.prim;
                while (prim != NULL) {
                    prim->clut += 1;
                    prim = prim->next;
                }
                if (self->palette == DeathFinalClut) {
                    self->step_s++;
                }
            }
            break;

        case DEATH_SHRINK:
            checkCount = 0;
            self->ext.venusWeed.timer++;

            if (self->ext.venusWeed.timer & 1) {
                prim = self->ext.venusWeed.prim;
                x = self->posX.i.hi;


                if (self->ext.venusWeed.leavesWidth) {
                    self->ext.venusWeed.leavesWidth--;
                    if (self->ext.venusWeed.leavesWidth < 0) {
                        self->ext.venusWeed.leavesWidth = 0;
                    }
                }

                for (i = -1; i < 2; i += 2) {


                    prim->x1 =
                        x + (self->ext.venusWeed.leavesWidth + 0x38) / 2 * i;
                    prim->x3 = x + (self->ext.venusWeed.leavesWidth * i);
                    prim->y0++;
                    prim->y1++;
                    if (prim->y1 > prim->y2) {
                        prim->drawMode = DRAW_HIDE;
                        checkCount += 1;
                    }
                    prim = prim->next;
                }
            }


            prim = self->ext.venusWeed.stemPrim;
            prim->y0 = ++prim->y1;
            if (prim->y0 > prim->y2) {
                prim->drawMode = DRAW_HIDE;
                checkCount += 1;
            }


            if (checkCount == 3) {
                self->step_s += 1;
            }
            break;

        case DEATH_DONE:

            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_EXPLOSION, self, entity);
                entity->params = 2;
                entity->posY.i.hi -= 0xC;
            }

            PlaySfxPositional(SFX_EXPLODE_B);


            PreventEntityFromRespawning(self);
            DestroyEntity(self);
            return;
        }
    }


    if (self->ext.venusWeed.wiggleT) {
        rot = self->rotate;
        self->rotate += WiggleLeavesSpeed;
        x = rcos(rot) * 3 >> 0xC;
        y = rsin(rot) * 3 >> 0xC;
        prim = self->ext.venusWeed.prim;


        for (i = -1; i < 2; i += 2) {


            prim->x1 = self->posX.i.hi + (x + 0x38) * i;
            prim->y1 = self->posY.i.hi - LeavesHeightMax + y * i;

            prim = prim->next;
        }


        x /= 2;
        entity = self + 1;
        prim = self->ext.venusWeed.stemPrim;
        self->ext.venusWeed.wiggleT--;
        if (!self->ext.venusWeed.wiggleT) {
            entity->posX.i.hi = self->posX.i.hi;
            prim->x0 = self->posX.i.hi - StemWidthMax;
            prim->x1 = self->posX.i.hi + StemWidthMax;
        } else {


            prim->x0 = self->posX.i.hi - 0xC + x;
            prim->x1 = self->posX.i.hi + 0xC + x;
            entity->posX.i.hi = self->posX.i.hi + x;
        }
    }
}


INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedFlower);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedTendril);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedDart);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedSpike);
