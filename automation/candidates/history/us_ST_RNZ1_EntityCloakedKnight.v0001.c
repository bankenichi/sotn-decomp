/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityCloakedKnight
   source : upstream/master:src/st/nz1/e_cloaked_knight.c
   target : src/st/rnz1/e_cloaked_knight.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", StepTowards);

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
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
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
extern int StepTowards();
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

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnightCloak);

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnightAura);

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnightSword);
