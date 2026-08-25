/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v2-top-level-seed-declarations
   record : us:ST/RNO1:func_us_801BF074_from_no1
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/no1/e_secrets.c
   target : src/st/rno1/unk_26178.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void MoveEntity();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int UnkPolyFunc2();
extern int UnkPrimHelper();
extern int AnimateEntity();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", EntityBreakable);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", EntityBreakableDebris);

extern s32 D_us_801B7424;

void RNO1_DebugShowWaitInfo(const char* msg) {
    g_CurrentBuffer = g_CurrentBuffer->next;
    FntPrint(msg);
    if (D_us_801B7424++ & 4) {
        FntPrint("\no\n");
    }
    DrawSync(0);
    VSync(0);
    PutDrawEnv(&g_CurrentBuffer->draw);
    PutDispEnv(&g_CurrentBuffer->disp);
    FntFlush(-1);
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", RNO1_DebugInputWait);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A68AC);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A700C);

void DestroyEntity(Entity*);

void func_us_801B7CC4_from_no1(Entity* self) {
    if (self->step == 0) {
        g_api.PlaySfx(SET_RELEASE_RATE_HIGH_20_21);
        self->step++;
    }
    DestroyEntity(self);
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801B8F50_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BE880_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BEB54_from_no1);

#define DRAW_UNK02 2
#define FLAG_HAS_PRIMS 8388608
#define PRIM_GT4 4
extern s16 D_us_80180C9C[8];
extern s32 D_us_80180CAC[6][2];
extern u8 D_us_80180D1C[14];
extern EInit g_EInitParticle;
extern struct Entity;
void DestroyEntity(Entity*);
void InitializeEntity(u16 arg0[]);

void func_us_801BEE00_from_no1(Entity* self) {
    Primitive* prim;
    s32 primIndex;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitParticle);
        self->animSet = 8;
        self->animCurFrame = 1;
        self->palette = PAL_FLAG(4);
        break;

    case 1:
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 2);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];
            self->ext.segmentedBreakableWall.prim = prim;
            UnkPolyFunc2(prim);
            prim->tpage = 0xE;
            prim->clut = 2;
            prim->u0 = 0x70;
            prim->u1 = 0x78;
            prim->u2 = prim->u0;
            prim->u3 = prim->u1;
            prim->v0 = 0xF6;
            prim->v1 = prim->v0;
            prim->v2 = 0xFD;
            prim->v3 = prim->v2;
            prim->priority = self->zPriority;
            prim->drawMode = DRAW_UNK02;
            prim->next->x1 = self->posX.i.hi;
            prim->next->y0 = self->posY.i.hi;
            LOH(prim->next->r2) = 4;
            LOH(prim->next->b2) = 4;
            prim->next->b3 = 0x80;
        } else {
            DestroyEntity(self);
            return;
        }
        self->velocityX = D_us_80180CAC[self->params][0];
        self->velocityY = D_us_80180CAC[self->params][1];
        self->step++;
        break;

    case 2:
        prim = self->ext.segmentedBreakableWall.prim;
        LOH(prim->next->tpage) += 0x180;
        prim->next->x1 = self->posX.i.hi;
        prim->next->y0 = self->posY.i.hi;
        UnkPrimHelper(prim);
        if (!AnimateEntity(D_us_80180D1C, self)) {
            self->animCurFrame = 0;
        }
        if (UnkCollisionFunc5(D_us_80180C9C) != 0) {
            DestroyEntity(self);
            return;
        }
        self->velocityY -= FIX(0.0625);
        break;
    }
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void func_us_801BF074_from_no1(Entity* self) {
    Collider collider;
    Entity* tempEntity;
    Primitive* prim;
    s32 primIndex;
    s16 posX, posY;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitParticle);
        self->animSet = 8;
        self->animCurFrame = 1;
        self->palette = PAL_FLAG(4);
        break;

    case 1:
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 2);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];
            self->ext.segmentedBreakableWall.prim = prim;
            UnkPolyFunc2(prim);
            prim->tpage = 0xE;
            prim->clut = 2;
            prim->u0 = 0x70;
            prim->u1 = 0x78;
            prim->u2 = prim->u0;
            prim->u3 = prim->u1;
            prim->v0 = 0xF6;
            prim->v1 = prim->v0;
            prim->v2 = 0xFD;
            prim->v3 = prim->v2;
            prim->priority = self->zPriority;
            prim->drawMode = DRAW_UNK02;

            prim->next->x1 = self->posX.i.hi;
            prim->next->y0 = self->posY.i.hi;
            LOH(prim->next->r2) = D_us_801816D0[self->params];
            LOH(prim->next->b2) = LOH(prim->next->r2);
            prim->next->b3 = 0x80;
        } else {
            DestroyEntity(self);
            return;
        }
        self->velocityX = D_us_801816A8[self->params][0];
        self->velocityY = D_us_801816A8[self->params][1];
        self->step++;
        break;

    case 2:
        prim = self->ext.segmentedBreakableWall.prim;
        LOH(prim->next->tpage) += D_us_801816DC[self->params];
        prim->next->x1 = self->posX.i.hi;
        prim->next->y0 = self->posY.i.hi;
        UnkPrimHelper(prim);
        if (!AnimateEntity(D_us_801816E8, self)) {
            self->animCurFrame = 0;
        }
        MoveEntity();
        self->velocityY += FIX(0.125);
        if (self->velocityY < 0) {
            break;
        }
        posX = self->posX.i.hi;
        posY = self->posY.i.hi;
        posY += (LOH(prim->next->r2) / 2) - 2;
        g_api.CheckCollision(posX, posY, &collider, 0);
        if (collider.effects & EFFECT_SOLID) {
            self->posY.i.hi += collider.unk18;
            self->velocityX += FIX(0.25);
            self->velocityY = -self->velocityY / 2;
            if (self->velocityY > FIX(-0.25)) {
                if (LOH(prim->next->r2) > 6) {
                    tempEntity =
                        AllocEntity(&g_Entities[224], &g_Entities[256]);
                    if (tempEntity != NULL) {
                        CreateEntityFromEntity(
                            E_INTENSE_EXPLOSION, self, tempEntity);
                        tempEntity->params = 0x10;
                    }
                }
                DestroyEntity(self);
                return;
            }
        }
        break;
    }
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A86A8);
