/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO4:func_us_801C3A04_from_no4
   source : upstream/master:src/st/no4/first_c_file.c
   target : src/st/rno4/unk_44B0C.c
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
extern int rand(void);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBreakable);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C123C_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C12B0_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C15F8_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5364);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBgColumnsParallax_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C1EE4_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5C78);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5EE4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2850_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2B78_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2E60_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3160_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C34EC_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C37C8_from_no4);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitCommon;

void func_us_801C3A04_from_no4(Entity* self) {
    Primitive* prim;
    s32 i;
    s32 var_s2;
    s32 yOffset;
    s32 posX;
    s32 primIndex;
    s32 scrollY;

    if (!self->step) {
        InitializeEntity(g_EInitCommon);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_TILE, 0x40);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;

        while (prim != NULL) {
            prim->priority = 0x6C;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    prim = self->ext.et_801C12B0.prim;
    posX = self->posX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    self->ext.et_801C12B0.unk80++;
    yOffset = 0x120;
    yOffset -= scrollY;

     
    for (i = 0; i < 2; i++) {
        while (prim != NULL) {
            if (prim->drawMode == DRAW_HIDE) {
                prim->r0 = prim->b0 = prim->g0 = 0x80;
                prim->x0 = ((rand() % 0x10) * 2) + i + posX;
                prim->y0 = yOffset - 4 + (rand() & 7);
                prim->x1 = 0;
                LOH(prim->r1) = 0;
                prim->u0 = prim->v0 = 2;
                LOW(prim->r2) = 0x40000;
                LOW(prim->u1) = 0;
                LOW(prim->x3) = 0x4000 - (rand() & 0xFF0);
                LOW(prim->r3) = (rand() & 0x1F00) - 0xF80;
                prim->clut = 0x20;
                prim->drawMode = DRAW_UNK02;
                break;
            }

            prim = prim->next;
        }
    }

     
    prim = self->ext.et_801C12B0.prim;
    while (prim != NULL) {
        if (prim->drawMode != DRAW_HIDE) {
            LOH(prim->b1) = prim->x0;
            prim->y1 = prim->y0;
            LOW(prim->x1) += LOW(prim->r2);
            LOW(prim->r1) += LOW(prim->u1);
            prim->x0 = LOH(prim->b1);
            prim->y0 = prim->y1;

            var_s2 = 0;
            if (LOW(prim->r2) >= 0) {
                var_s2 = 1;
            }
            LOW(prim->r2) -= LOW(prim->x3);
            LOW(prim->u1) -= LOW(prim->r3);
            if (!--prim->clut) {
                prim->drawMode = DRAW_HIDE;
            }
        }
        prim = prim->next;
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3CC4_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3FB0_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C4228_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityWaterBox);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C81C8);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityFloatingIcePlatform);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C4BD8_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C8668);

void RNO4_Unused801C8704(void) {}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C870C);

void RNO4_Unused801C8768(void) {}

void RNO4_Unused801C8770(void) {}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBoatElevatorChains);

void RNO4_Unused801C8BD4(void) {}

void RNO4_Unused801C8BDC(void) {}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", LoadFerrymanGateTiles);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C8C54);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801A071C_from_bo3);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801A07CC_from_bo3);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C5518_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C9048);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C909C);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityExplosionVariants);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityGreyPuff);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityIntenseExplosion);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", PlaySfxPositional);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBreakableCrystalFloor);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", EntityBreakableWall);
