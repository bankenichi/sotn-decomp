/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNO2:func_us_801B4DA4_from_bo0
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/no2_unk_34DA4.h
   target : src/st/rno2/func_us_801b4da4_from_bo0.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
void SetDrawEnv(DR_ENV* dr_env, DRAWENV* env);
/* End permuter-seed writer declarations. */


/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitSpawner;
extern GameApi g_api;
extern Primitive g_PrimBuf[];
extern GAME_IMPORT GpuBuffer* g_CurrentBuffer; // g_CurrentBuffer;

void func_us_801B4DA4_from_bo0(Entity* self) {
    DRAWENV draw;
    DR_ENV* dr_env;
    Primitive* prim;
    s32 i;
    s32 primIndex;
    u8 flag;

    RECT rect = {.x = 0, .y = 256, .w = 80, .h = 192};

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitSpawner);
        primIndex = g_api.func_800EDB58(PRIM_GT4, 8);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];
            dr_env = g_api.func_800EDB08((POLY_GT4*)prim);
            if (dr_env == NULL) {
                DestroyEntity(self);
                return;
            }
            prim->type = PRIM_ENV;
            prim->priority = 0x13F;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
            dr_env = g_api.func_800EDB08((POLY_GT4*)prim);
            if (dr_env == NULL) {
                DestroyEntity(self);
                return;
            }
            prim->type = PRIM_ENV;
            prim->priority = 0x141;
            prim->drawMode = DRAW_UNK_800;
            prim = prim->next;
            self->ext.prim = prim;
            while (prim != NULL) {
                prim->drawMode = DRAW_HIDE;
                prim = prim->next;
            }
        } else {
            DestroyEntity(self);
        }
        break;
    case 1:
        prim = &g_PrimBuf[self->primIndex];
        draw = g_CurrentBuffer->draw;
        if (draw.ofs[0] == 0) {
            flag = 0;
        } else {
            flag = 1;
        }
        draw.isbg = 1;
        draw.r0 = 0;
        draw.g0 = 0;
        draw.b0 = 0;
        draw.dtd = 1;
        draw.clip = rect;
        draw.ofs[0] = 0;
        draw.ofs[1] = 0x100;
        dr_env = *(DR_ENV**)&prim->r1;
        SetDrawEnv(dr_env, &draw);
        prim->drawMode = DRAW_DEFAULT;
        prim = prim->next;
        prim = self->ext.prim;
        for (i = 2; i >= 0; i--) {
            prim->type = PRIM_GT4;
            prim->tpage = 0x110 | TPAGE_FLAG;
            prim->u0 = prim->u2 = 0;
            prim->u1 = prim->u3 = prim->u0 + 0x28;
            prim->v0 = prim->v1 = 0;
            prim->v2 = prim->v3 = prim->v0 + 0x28;
            prim->x0 = prim->x2 = i * 0xA;
            prim->x1 = prim->x3 = prim->x0 + (0x50 - (i * 0x14));
            prim->y0 = prim->y1 = (i * 0xA) + 0x40;
            prim->y2 = prim->y3 = prim->y0 + (0x50 - (i * 0x14));
            prim->r0 = prim->g0 = prim->b0 = 0xFF;
            LOW(prim->r1) = LOW(prim->r0);
            LOW(prim->r2) = LOW(prim->r0);
            LOW(prim->r3) = LOW(prim->r0);
            prim->priority = 0x140;
            prim->drawMode = DRAW_TPAGE2 | DRAW_TPAGE | DRAW_TRANSP;
            if (i == 0) {
                prim->drawMode = DRAW_DEFAULT;
            }
            prim->drawMode |= DRAW_COLORS;
            prim = prim->next;
        }
        prim->type = PRIM_GT4;
        prim->tpage = 0x1A | TPAGE_FLAG;
        prim->clut = PAL_FILL_WHITE;
        prim->u0 = prim->u2 = 0x10;
        prim->u1 = prim->u3 = 0x20;
        prim->v0 = prim->v1 = 0xD0;
        prim->v2 = prim->v3 = 0xE0;
        prim->x0 = prim->x2 = 0;
        prim->x1 = prim->x3 = 0x28;
        prim->y0 = prim->y1 = 0;
        prim->y2 = prim->y3 = 0x28;
        prim->r0 = 0x40;
        prim->g0 = 0x38;
        prim->b0 = 0x38;
        LOW(prim->r1) = LOW(prim->r0);
        LOW(prim->r2) = LOW(prim->r0);
        LOW(prim->r3) = LOW(prim->r0);
        prim->priority = 0x140;
        prim->drawMode = DRAW_UNK_40 | DRAW_TPAGE | DRAW_COLORS | DRAW_TRANSP;
        prim = prim->next;
        prim->type = PRIM_GT4;



        if (flag) {
            prim->tpage = 0x104;
        } else {
            prim->tpage = 0x100;
        }

        prim->u0 = prim->u2 = 0x8B;
        prim->u1 = prim->u3 = 0xB3;
        prim->v0 = prim->v1 = 0x37;
        prim->v2 = prim->v3 = 0x5F;
        prim->x0 = prim->x2 = 0;
        prim->x1 = prim->x3 = 0x28;
        prim->y0 = prim->y1 = 0;
        prim->y2 = prim->y3 = 0x28;
        prim->priority = 0x140;
        prim->drawMode = DRAW_DEFAULT;
        prim = prim->next;
        prim->type = PRIM_GT4;
        prim->tpage = 0x110 | TPAGE_FLAG;
        prim->u0 = prim->u2 = 4;
        prim->u1 = prim->u3 = 0x4C;
        prim->v0 = prim->v1 = 0x44;
        prim->v2 = prim->v3 = 0x8C;
        prim->x0 = prim->x2 = 0x7B;
        prim->x1 = prim->x3 = 0xC3;
        prim->y0 = prim->y1 = 0x27;
        prim->y2 = prim->y3 = 0x6F;





        prim->r0 = 0x10;
        prim->g0 = 0x8;
        prim->b0 = 0x10;

        LOW(prim->r1) = LOW(prim->r0);
        LOW(prim->r2) = LOW(prim->r0);
        LOW(prim->r3) = LOW(prim->r0);
        prim->priority = 0x142;
        prim->drawMode = DRAW_DITHERING | DRAW_TPAGE2 | DRAW_TPAGE |
                         DRAW_COLORS | DRAW_TRANSP;
        break;
    }
}

