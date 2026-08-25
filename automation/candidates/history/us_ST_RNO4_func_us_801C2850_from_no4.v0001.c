/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO4:func_us_801C2850_from_no4
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

void func_us_801C2850_from_no4(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s32 scrollX;
    s32 scrollY;
    s32 var_s4;
    s32 var_s3;
    s32 var_s2;
    s32 var_s1;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_G4, 3);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;

        while (prim != NULL) {
            prim->priority = 0x9E;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    prim = self->ext.et_801C12B0.prim;
    scrollX = g_Tilemap.scrollX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    self->ext.et_801C12B0.unk80++;
    if (scrollY > 0x300) {
        var_s4 = 0x3E0;
        var_s3 = 0x5E0;
        var_s4 -= scrollY;
        var_s3 -= scrollY;
        var_s1 = scrollY & 7;
        if (var_s4 < -0x10) {
            var_s4 = -0x10 - var_s1;
        }
        if (var_s3 > 0xF0) {
            var_s3 = (-var_s1 & 7) + 0xF0;
        }
        var_s1 = (var_s4 + scrollY) - 0x3E0;
        var_s2 = (var_s3 + scrollY) - 0x3E0;
        if (self->ext.et_801C12B0.unk80 & 1) {
            var_s1 *= 0x13;
            var_s1 /= 40;
            var_s2 *= 0x13;
            var_s2 /= 40;
        } else {
            var_s1 *= 0x12;
            var_s1 /= 40;
            var_s2 *= 0x12;
            var_s2 /= 40;
        }

         
        prim->r0 = prim->r1 = prim->b0 = prim->b1 = prim->g0 = prim->g1 =
            var_s1;
        prim->r2 = prim->r3 = prim->b2 = prim->b3 = prim->g2 = prim->g3 =
            var_s2;
        prim->x0 = prim->x2 = 0x80 - scrollX;
        prim->x1 = prim->x3 = 0x120 - scrollX;
        prim->y0 = prim->y1 = var_s4;
        prim->y2 = prim->y3 = var_s3;
        prim->drawMode = DRAW_DITHERING | DRAW_TPAGE2 | DRAW_TPAGE |
                         DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
        prim = prim->next;

         
        prim->r0 = prim->r2 = prim->b0 = prim->b2 = prim->g0 = prim->g2 = 0;
        prim->r1 = prim->b1 = prim->g1 = var_s1;
        prim->r3 = prim->b3 = prim->g3 = var_s2;
        prim->x0 = prim->x2 = 0x20 - scrollX;
        prim->x1 = prim->x3 = 0x80 - scrollX;
        prim->y0 = prim->y1 = var_s4;
        prim->y2 = prim->y3 = var_s3;
        prim->drawMode = DRAW_DITHERING | DRAW_TPAGE2 | DRAW_TPAGE |
                         DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
        prim = prim->next;

         
        prim->r0 = prim->b0 = prim->g0 = var_s1;
        prim->r2 = prim->b2 = prim->g2 = var_s2;
        prim->r1 = prim->b1 = prim->g1 = prim->r3 = prim->b3 = prim->g3 = 0;
        prim->x0 = prim->x2 = 0x120 - scrollX;
        prim->x1 = prim->x3 = 0x180 - scrollX;
        prim->y0 = prim->y1 = var_s4;
        prim->y2 = prim->y3 = var_s3;
        prim->drawMode = DRAW_DITHERING | DRAW_TPAGE2 | DRAW_TPAGE |
                         DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
        prim = prim->next;
    }

    while (prim != NULL) {
        prim->drawMode = DRAW_HIDE;
        prim = prim->next;
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2B78_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C2E60_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3160_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C34EC_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C37C8_from_no4);

INCLUDE_ASM("st/rno4/nonmatchings/unk_44B0C", func_us_801C3A04_from_no4);

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
