/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:BOSS/RBO8:func_us_801BA164_from_cat
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/cat/unk_3A164.c
   target : src/boss/rbo8/unk_15868.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo8.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

void func_801CE3FC(s16* offsets) {
    Entity* entity;
    s32 i;

    for (i = 0; i < 4; i++) {
        entity = g_CurrentEntity + offsets[i];
        polarPlacePart(entity);
    }
    offsets += 4;

    while (*offsets) {
        if (*offsets != 0xFF) {
            entity = g_CurrentEntity + *offsets;
            polarPlacePart(entity);
        }
        offsets++;
    }
}



INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80195938);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_801D0B40);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80195AD8);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80195D80);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80197B1C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_801980E4);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80198210);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_801983EC);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80198964);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019C7B8_from_rcen);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_801991D4);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019921C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", EntityMinotaurSpitLiquid);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019943C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019953C);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitParticle;
extern GameApi g_api;
extern Primitive g_PrimBuf[];

void func_us_801BA164_from_cat(Entity* self) {
    Primitive* prim;
    s32 var_s1;
    s32 i;
    s32 var_s3;
    s16 posX;
    s16 posY;
    s32 primIndex;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitParticle);
        self->ext.et_801BA164.unk80 = 0x40;
        primIndex = g_api.func_800EDB58(PRIM_TILE_ALT, 8);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];
            self->ext.et_801BA164.prim = prim;

            for (i = 0; prim != NULL; i++, prim = prim->next) {
                prim->u0 = 2;
                prim->v0 = 2;
                prim->x0 = self->posX.i.hi;
                prim->y0 = self->posY.i.hi;
                prim->r0 = 0x60;
                prim->g0 = 0x40;
                prim->b0 = 0x60;
                LOW(prim->r2) = D_us_80181620[i].x;
                LOW(prim->x2) = D_us_80181620[i].y;
                if (self->params & 0x10) {
                    var_s3 = LOW(prim->r2);
                    LOW(prim->r2) = LOW(prim->x2);
                    LOW(prim->x2) = -var_s3;
                }

                if (self->params & 1) {
                    LOW(prim->r2) = -LOW(prim->r2);
                }

                LOW(prim->r1) = 0;
                LOW(prim->x1) = 0;
                prim->priority = self->zPriority;
                prim->drawMode = DRAW_DEFAULT;
            }
        } else {
            DestroyEntity(self);
            return;
        }

    case 1:
        posX = self->posX.i.hi;
        posY = self->posY.i.hi;
        prim = self->ext.et_801BA164.prim;
        while (prim != NULL) {
            var_s1 = (LOH(prim->b1) << 0x10) + LOH(prim->r1);
            var_s1 += LOW(prim->r2);
            LOW(prim->r1) = var_s1;
            prim->x0 = posX + LOH(prim->b1);
            var_s1 = (prim->y1 << 0x10) + prim->x1;
            var_s1 += LOW(prim->x2);
            LOW(prim->x1) = var_s1;
            prim->y0 = posY + prim->y1;
            LOW(prim->x2) += 0x1000;
            prim = prim->next;
        }
        break;
    }
}


INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80199A58);
