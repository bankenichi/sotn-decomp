// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno1.h"

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", EntityBreakable);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", EntityBreakableDebris);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern s32 D_us_801B7424;

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GAME_IMPORT GpuBuffer* g_CurrentBuffer; // g_CurrentBuffer;

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

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
void DestroyEntity(Entity*);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GameApi g_api;

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

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define DRAW_UNK02 2
#define FLAG_HAS_PRIMS 8388608
#define PRIM_GT4 4
extern s16 D_us_80180C9C[8];
extern s32 D_us_80180CAC[6][2];
extern u8 D_us_80180D1C[14];
extern EInit g_EInitParticle;
extern struct Entity;
void InitializeEntity(u16 arg0[]);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Primitive g_PrimBuf[];

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



INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BF074_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A86A8);
