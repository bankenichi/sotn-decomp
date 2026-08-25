/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityCloakedKnight
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/nz1/e_cloaked_knight.c
   target : src/st/rnz1/e_cloaked_knight.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

bool StepTowards(s16* val, s32 target, s32 step) {
    if (abs(*val - target) < step) {
        *val = target;
        return true;
    }

    if (*val > target) {
        *val -= step;
    }

    if (*val < target) {
        *val += step;
    }

    return false;
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GameApi g_api;
extern Primitive g_PrimBuf[];
extern u32 g_Timer;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityCloakedKnight(Entity* self) {
    Entity* entity;
    s32 primIndex;
    Primitive* prim;
    s32 posX;
    s32 posY;
    Pos* pos;
    s32 distance;
    s32 angle;
    s32 scale;

    if (self->flags & FLAG_DEAD && self->step != 6) {
        SetStep(6);
    }

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCloakedKnight);
        self->animCurFrame = 1;
        self->hitboxOffY = 11;
        primIndex = g_api.AllocPrimitives(PRIM_TILE, 1);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.cloakedKnight.prim = prim;
        prim->u0 = prim->v0 = 2;
        prim->r0 = prim->g0 = prim->b0 = 0xC0;
        prim->priority = 0xC0;
        prim->drawMode = DRAW_HIDE | DRAW_UNK02;
        entity = self + 1;
        CreateEntityFromCurrentEntity(E_CLOAKED_KNIGHT_CLOAK, entity);
        entity->zPriority = self->zPriority - 1;
        entity = self + 2;
        CreateEntityFromCurrentEntity(E_CLOAKED_KNIGHT_SWORD, entity);
        entity->zPriority = self->zPriority + 1;
        SetStep(2);
        break;

    case 2:
        if (GetDistanceToPlayerX() < 0x50) {
            self->ext.cloakedKnight.unkA2 = 0x20;
            SetStep(3);
        }
        break;

    case 3:
        switch (self->step_s) {
        case 0:
            self->ext.cloakedKnight.unk94 = (Random() & 3) + 1;
            self->ext.cloakedKnight.unk84 = 0;
            self->step_s++;
             

        case 1:
            angle = (Random() * 4) + FLT(0.125);
            posX = FLT_TO_I(rcos(angle) * 0x60);
            posY = FLT_TO_I(rsin(angle) * -0x60);
            entity = &PLAYER;
            prim = self->ext.cloakedKnight.prim;
            prim->x0 = entity->posX.i.hi + posX;
            prim->y0 = entity->posY.i.hi + posY;

            distance = SQ(posX) + SQ(posY);
            distance = SquareRoot0(distance);
            if (posX < 0) {
                distance = -distance;
            }
            self->ext.cloakedKnight.targetDistance = distance;
            self->ext.cloakedKnight.timer = 0x80;
            self->step_s++;
             

        case 2:
            if (StepTowards(&self->ext.cloakedKnight.unk9E,
                            self->ext.cloakedKnight.targetDistance, 4) != 0) {
                self->step_s++;
            }
            break;

        case 3:
            MoveEntity();
            if (!--self->ext.cloakedKnight.timer) {
                self->step_s = 1;
            }
            prim = self->ext.cloakedKnight.prim;
            posX = prim->x0 - self->posX.i.hi;
            posY = prim->y0 - self->posY.i.hi;
            distance = SQ(posX) + SQ(posY);
            distance = SquareRoot0(distance);
            distance *= 2;
            if (distance > 48) {
                distance = 48;
            }
            angle = ratan2(posY, posX);
            self->velocityX = distance * rcos(angle);
            self->velocityY = distance * rsin(angle);
            if (distance < 6) {
                self->step_s = 1;
                if (!--self->ext.cloakedKnight.unk94) {
                    SetStep(4);
                }
            }
            if (posX < 0) {
                distance = -distance;
            }
            StepTowards(&self->ext.cloakedKnight.unk9E, distance, 4);
#ifdef VERSION_PSP
            angle = self->hitFlags & 3;
            if (angle) {
                SetStep(5);
            }
#else
            if (self->hitFlags & 3) {
                SetStep(5);
            }
#endif
            break;
        }
        break;

    case 4:
        switch (self->step_s) {
        case 0:
            self->ext.cloakedKnight.unk86 = true;
            self->velocityX = 0;
            self->velocityY = 0;
            if (StepTowards(&self->ext.cloakedKnight.unk9E, 0x80, 4) != 0) {
                self->step_s += 1;
            }
            if (!(g_Timer & 7)) {
                PlaySfxPositional(SFX_WEAPON_SWISH_A);
            }
            entity = self + 2;
            entity->rotate += ROT(22.5);
            entity->rotate &= 0xFFF;
            break;

        case 1:
            entity = &PLAYER;
            angle = GetAngleBetweenEntities(self, entity);
            angle &= 0xFFF;
            angle -= self->rotate & 0xFFF;

            if (abs(angle) < 0x20) {
                self->ext.cloakedKnight.unk9E = 0;
            }
            if (!(g_Timer & 7)) {
                PlaySfxPositional(SFX_WEAPON_SWISH_A);
            }
            if (StepTowards(&self->ext.cloakedKnight.unk9E, 0, 1) != 0) {
                self->ext.cloakedKnight.timer = 32;
                self->step_s++;
            }
            entity = self + 2;
            entity->rotate += ROT(22.5);
            entity->rotate &= 0xFFF;
            break;

        case 2:
            entity = self + 2;
            angle = (self->rotate - 0x400) & 0xFFF;
            StepTowards(&entity->rotate, angle, 0xC0);
            if (!--self->ext.cloakedKnight.timer) {
                PlaySfxPositional(SFX_WEAPON_SCRAPE_ECHO);
                PlaySfxPositional(SFX_CLOAKED_KNIGHT_ATTACK);
                self->step_s++;
            }
            break;

        case 3:
            self->ext.cloakedKnight.unkA2 += 8;
            if (self->ext.cloakedKnight.unkA2 > 0xA0) {
                self->ext.cloakedKnight.unk86 = false;
                self->step_s++;
            }
            break;

        case 4:
            if (StepTowards(&self->ext.cloakedKnight.unkA2, 0x20, 1) != 0) {
                SetStep(3);
            }
            break;
        }
        break;

    case 5:
        switch (self->step_s) {
        case 0:
            if (self->facingLeft) {
                self->velocityX = FIX(2);
            } else {
                self->velocityX = FIX(-2);
            }
            self->velocityY = 0;
            self->ext.cloakedKnight.timer = 24;
            self->animCurFrame = 2;
            PlaySfxPositional(SFX_UNK_CLOAKED_KNIGHT_71F);
            self->step_s++;
             

        case 1:
            MoveEntity();
            self->velocityX -= self->velocityX / 32;
            self->velocityY -= self->velocityY / 32;
            if (!--self->ext.cloakedKnight.timer) {
                self->animCurFrame = 1;
                SetStep(3);
            }
            break;
        }
        break;

    case 6:  
        self->hitboxState = 0;
        PlaySfxPositional(SFX_CLOAKED_KNIGHT_DEATH);
        PlaySfxPositional(SFX_FM_THUNDER_EXPLODE);
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_EXPLOSION, self, entity);
            entity->params = EXPLOSION_SMALL_MULTIPLE;
        }
        entity = self + 2;
        entity->flags |= FLAG_UNK_2000;
        DestroyEntity(self);
        return;

    case 0xFF:
#include "../pad2_anim_debug.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void CreateEntityFromCurrentEntity(u16, Entity*);
s16 GetDistanceToPlayerX();
s32 Random();
int rcos(int a);
int rsin(int a);
long SquareRoot0(long a);
void MoveEntity();
long ratan2(long y, long x);
void PlaySfxPositional(s32 arg0);
int abs(int x);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetStep();
extern int GetAngleBetweenEntities();
/* End permuter-seed writer declarations. */
        break;
    }

    if (!(self->flags & FLAG_DEAD)) {
        self->rotate += self->ext.cloakedKnight.unk9E;
         
        entity = self + 2;
        scale = self->ext.cloakedKnight.unkA2;
        angle = self->rotate;
        posX = self->posX.val;
        posY = self->posY.val;
        posX += scale * rcos(angle) * 16;
        posY += scale * rsin(angle) * 16;
        StepTowards(&entity->rotate, (angle - FIX(1.0 / 64.0)) & 0xFFF, 0x10);
        pos = &entity->ext.cloakedKnightSword.targetPos;
        pos->x.val = posX;
        pos->y.val = posY;
        if (!(g_Timer & 0xF) && (self->step != 5)) {
             
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_CLOAKED_KNIGHT_AURA, self, entity);
                entity->ext.cloakedKnightAura.parent = self;
                entity->zPriority = self->zPriority + 1;
            }
        }
    }
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitCloakedknight;

extern AnimateEntityFrame D_us_80181F24[5];
extern EInit g_EInitCloakedknight;
bool StepTowards(s16* val, s32 target, s32 step);

void EntityCloakedKnightCloak(Entity* self) {
    Entity* prev;
    s32 velocityX;
    s32 velocityY;
    s16 temp_s0_3;
    s32 distance;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCloakedknight);
        self->hitboxState = 0;
        self->flags |= FLAG_UNK_00200000 | FLAG_UNK_2000;
        self->drawFlags = ENTITY_ROTATE;
         

    case 1:
        AnimateEntity(D_us_80181F24, self);
        prev = self - 1;
        self->posX.i.hi = prev->posX.i.hi;
        self->posY.i.hi = prev->posY.i.hi;
        velocityX = prev->velocityX;
        velocityY = prev->velocityY;
        temp_s0_3 = ratan2(velocityX, -velocityY);
        temp_s0_3 = temp_s0_3 - self->rotate;
        velocityX = FIX_TO_I(velocityX);
        velocityY = FIX_TO_I(velocityY);
        distance = SquareRoot0(SQ(velocityX) + SQ(velocityY));
        temp_s0_3 = (temp_s0_3 * distance) >> 4;
        self->rotate += temp_s0_3;
        StepTowards(&self->rotate, 0, 0x20);
        if (prev->entityId != E_CLOAKED_KNIGHT) {
            DestroyEntity(self);
        }
        break;
    }
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitCloakedKnightAura;

extern EInit g_EInitCloakedKnightAura;
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);

void EntityCloakedKnightAura(Entity* self) {
    Entity* parent;

    if (!self->step) {
        InitializeEntity(g_EInitCloakedKnightAura);
        self->hitboxState = 0;
        self->flags |= FLAG_UNK_00200000 | FLAG_UNK_2000;
        self->animCurFrame = 1;
        self->palette += 1;  
        self->drawFlags |= ENTITY_OPACITY | ENTITY_SCALEY | ENTITY_SCALEX;
        self->blendMode = BLEND_TRANSP | BLEND_ADD;
        self->scaleX = self->scaleY = 0x100;
        self->opacity = 0x80;
    }

    parent = self->ext.cloakedKnightAura.parent;
    self->posX.val = parent->posX.val;
    self->posY.val = parent->posY.val;
    self->scaleX = self->scaleY += 6;
    if (parent->ext.cloakedKnight.unk86) {
        self->scaleX = self->scaleY += 6;
    }
    self->opacity -= 4;
    if (self->opacity < 32
#ifndef VERSION_PSP
        || parent->entityId != E_CLOAKED_KNIGHT
#endif
    ) {
        DestroyEntity(self);
    }
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180BE8;

extern EInit D_us_80180BE8;

void EntityCloakedKnightSword(Entity* self) {
    Entity* entity;
    s32 scale;
    s16 rotate;
    s32 offsetX;
    s32 offsetY;
    Pos* pos;
    s32 scale1;

    if (!self->params) {
        entity = self - 2;
        if ((entity->flags & FLAG_DEAD) != 0 ||
            entity->entityId != E_CLOAKED_KNIGHT) {
            if (self->step != 4) {
                self->hitboxState = 0;
                SetStep(4);
            }
        }
    }

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180BE8);
        self->animCurFrame = 7;
        self->drawFlags = ENTITY_ROTATE;
        if (!self->params) {
            entity = self + 1;
            CreateEntityFromCurrentEntity(E_CLOAKED_KNIGHT_SWORD, entity);
            entity->params = 1;
        } else {
            self->flags |= FLAG_UNK_2000;
            self->animCurFrame = 0;
            self->step = 8;
        }
        break;

    case 1:
        if (entity->step > 2) {
            self->step++;
        }
        entity = self - 2;
        if (entity->entityId != E_CLOAKED_KNIGHT) {
            DestroyEntity(self);
        }
        break;

    case 2:
        MoveEntity();
        pos = &self->ext.cloakedKnightSword.targetPos;
        offsetX = pos->x.i.hi - self->posX.i.hi;
        offsetY = pos->y.i.hi - self->posY.i.hi;
        scale1 = SQ(offsetX) + SQ(offsetY);
        scale1 = SquareRoot0(scale1);
        scale = scale1;
        if (scale > 0x38) {
            scale = 0x38;
        }
        if (scale < 4) {
            SetStep(3);
        }
        rotate = ratan2(offsetY, offsetX);
        self->velocityX = scale * rcos(rotate);
        self->velocityY = scale * rsin(rotate);
        break;

    case 3:
        pos = &self->ext.cloakedKnightSword.targetPos;
        self->posX.i.hi = pos->x.i.hi;
        self->posY.i.hi = pos->y.i.hi;
        break;

    case 4:
        self->flags |= FLAG_DESTROY_IF_OUT_OF_CAMERA |
                       FLAG_DESTROY_IF_BARELY_OUT_OF_CAMERA;
        MoveEntity();
        self->velocityY += FIX(0.125);
        self->rotate += ROT(11.25);
        break;

    case 8:
        entity = self - 1;
        self->hitboxState = entity->hitboxState;
        self->posX.i.hi = entity->posX.i.hi;
        self->posY.i.hi = entity->posY.i.hi;
        rotate = entity->rotate + ROT(90.0);
        self->hitboxOffX = (rcos(rotate) * 3 * 8) >> 12;
        self->hitboxOffY = (rsin(rotate) * 3 * 8) >> 12;
        if (entity->entityId != E_CLOAKED_KNIGHT_SWORD) {
            DestroyEntity(self);
        }
        break;
    }
}
