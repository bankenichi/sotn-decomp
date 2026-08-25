/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO1:func_us_801BEE00_from_no1
   source : upstream/master:src/st/no1/e_secrets.c
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
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int UnkPolyFunc2();
extern int UnkPrimHelper();
extern int AnimateEntity();
extern int UnkCollisionFunc5();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", EntityBreakable);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", EntityBreakableDebris);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", RNO1_DebugShowWaitInfo);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", RNO1_DebugInputWait);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A68AC);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A700C);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801B7CC4_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801B8F50_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BE880_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BEB54_from_no1);

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
            LOH(prim->next->r2) = 4;
            LOH(prim->next->b2) = 4;
            prim->next->b3 = 0x80;
        } else {
            DestroyEntity(self);
            return;
        }
        self->velocityX = D_us_80181678[self->params][0];
        self->velocityY = D_us_80181678[self->params][1];
        self->step++;
        break;

    case 2:
        prim = self->ext.segmentedBreakableWall.prim;
        LOH(prim->next->tpage) += 0x180;
        prim->next->x1 = self->posX.i.hi;
        prim->next->y0 = self->posY.i.hi;
        UnkPrimHelper(prim);
        if (!AnimateEntity(D_us_801816E8, self)) {
            self->animCurFrame = 0;
        }
        if (UnkCollisionFunc5(D_us_80181668) != 0) {
            DestroyEntity(self);
            return;
        }
        self->velocityY -= FIX(0.0625);
        break;
    }
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801BF074_from_no1);

INCLUDE_ASM("st/rno1/nonmatchings/unk_26178", func_us_801A86A8);
