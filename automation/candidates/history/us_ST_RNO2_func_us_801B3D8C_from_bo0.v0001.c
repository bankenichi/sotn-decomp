/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO2:func_us_801B3D8C_from_bo0
   source : upstream/master:src/st/no2_bg.h
   target : src/st/rno2/unk_322E4.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", EntityBreakable);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", EntityBreakableDebris);

void func_us_801B3D8C_from_bo0(Entity* self) {
    Primitive* prim;
    s16 offsetX;
    s16 offsetY;
    s32 i;

    if (self->params) {
        offsetX = 0;
        offsetY = -0x40;
    } else {
        offsetX = 0;
        offsetY = 0x58;
    }
    if (!self->step) {
        self->step++;
        if (self->params) {
            self->primIndex = g_api.AllocPrimitives(PRIM_GT4, 0x20);
        } else {
            self->primIndex = g_api.AllocPrimitives(PRIM_GT4, 8);
        }
        if (self->primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags = FLAG_KEEP_ALIVE_OFFCAMERA | FLAG_HAS_PRIMS;
        prim = &g_PrimBuf[self->primIndex];
        for (i = 0; prim != NULL; i++, prim = prim->next) {
            prim->x0 = prim->x2 = (i & 7) * 0x40 + offsetX;
            prim->x1 = prim->x3 = prim->x0 + 0x48;
            prim->y1 = prim->y0 = (i >> 3) * 0x64 + offsetY;
            prim->y3 = prim->y2 = prim->y0 + 0x6C;
            prim->u0 = 0x80;
            prim->v0 = 0;
            prim->u1 = 0xC8;
            prim->v1 = 0;
            prim->u2 = 0x80;
            prim->v2 = 0x68;
            prim->u3 = 0xC8;
            prim->v3 = 0x68;
            prim->tpage = 0xF;
            prim->clut = 0x36;
            prim->priority = 0x10;
            prim->drawMode = DRAW_DEFAULT;
        }
    }
}

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B3F30_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B4148_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B41A4_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B4210_from_bo0);
