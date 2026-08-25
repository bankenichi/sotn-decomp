/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/BO3:func_us_801C2E60_from_no4
   source : upstream/master:src/st/no4/first_c_file.c
   target : src/boss/bo3/unk_1CEEC.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo3.h"

static u8 D_us_801806E4[] = {0x04, 0x01, 0x04, 0x02, 0x00};
static u8 D_us_801806EC[] = {0x04, 0x00, 0x04, 0x00, 0x00};
static u8 D_us_801806F4[] = {
    0x05, 0x01, 0x05, 0x02, 0x05, 0x03, 0x05, 0x04, 0x00};
static u8 D_us_80180700[] = {
    0x05, 0x05, 0x05, 0x06, 0x05, 0x07, 0x05, 0x08, 0x00};
static u8 D_us_8018070C[] = {0x00, 0x00, 0x00, 0x00};
static u8 D_us_80180710[] = {
    0x05, 0x0D, 0x05, 0x0E, 0x05, 0x0F, 0x05, 0x10, 0x00};
static u8 D_us_8018071C[] = {0x05, 0x11, 0x05, 0x12, 0x05, 0x13, 0x00};
static u8 D_us_80180724[] = {0x05, 0x17, 0x00, 0x00};
static u8 D_us_80180728[] = {0x05, 0x16, 0x00, 0x00};
static u8 D_us_8018072C[] = {
    0x05, 0x14, 0xFF, 0xFF, 0x05, 0x15, 0x05, 0x15, 0xFF, 0x00, 0x00, 0x00};
static u8* anims[] = {
    D_us_801806E4, D_us_801806EC, D_us_801806F4, D_us_80180700, D_us_8018070C,
    D_us_80180710, D_us_8018071C, D_us_80180724, D_us_80180728, D_us_8018072C};

static u8 hitbox_heights[] = {
    0x08, 0x08, 0x28, 0x18, 0x10, 0x10, 0x08, 0x08, 0x08, 0x08, 0x08, 0x00};
static u8 params_arr[] = {
    0x00, 0x00, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x00, 0x00};
static u16 palettes[] = {
    PAL_NULL, PAL_NULL, 0x228, 0x228, 0x228, 0x228, 0x228, 0x228, 0x228, 0x228};
static u16 anim_sets[] = {
    ANIMSET_DRA(0x3), ANIMSET_DRA(0x3), ANIMSET_OVL(0xB), ANIMSET_OVL(0xB),
    ANIMSET_OVL(0xB), ANIMSET_OVL(0xB), ANIMSET_OVL(0xB), ANIMSET_OVL(0xB),
    ANIMSET_OVL(0xB), ANIMSET_OVL(0xB)};
static u16 unk5a_arr[] = {0x0000, 0x007C, 0x005B, 0x005B, 0x005B,
                          0x005B, 0x005B, 0x005B, 0x005B, 0x005B};
static u8 blend_modes[] = {
    DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE,
    DRAW_TPAGE2 | DRAW_TPAGE,
    DRAW_TPAGE2 | DRAW_TPAGE,
    DRAW_TPAGE2 | DRAW_TPAGE,
    DRAW_TPAGE2 | DRAW_TPAGE,
    DRAW_TPAGE2 | DRAW_TPAGE,
    DRAW_TPAGE2 | DRAW_TPAGE,
    DRAW_TPAGE2 | DRAW_TPAGE,
    DRAW_TPAGE2 | DRAW_TPAGE,
    DRAW_TPAGE2 | DRAW_TPAGE};
static u16 hitbox_y_offsets[] = {0x0000, 0x0000, 0xFFE8, 0xFFF0, 0x0000,
                                 0x0000, 0x0000, 0x0000, 0x0000, 0x0000};

#define E_BREAKABLE_RELIC E_ID(UNK_43)

#include "../../st/e_breakable_no4.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
extern int rand(void);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C123C_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C12B0_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C15F8_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C1844_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", EntityBgColumnsParallax_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C1EE4_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C21AC_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_8019E398);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C2850_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C2B78_from_no4);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitInteractable;

void func_us_801C2E60_from_no4(Entity* self) {
    s32 var_s5;
#ifdef VERSION_PSP
    u32 scrollX;
#else
    s32 scrollX;
#endif
    s32 scrollY;
    s32 var_s2;
    s32 primIndex;
    Primitive* prim;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 32);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.et_801C12B0.prim = prim;
        while (prim != NULL) {
            prim->clut = PAL_CC_STONE_EFFECT;
            prim->tpage = 0x1A;
            prim->u0 = prim->u2 = 0;
            prim->u1 = prim->u3 = 0x1E;
            prim->v0 = prim->v1 = 0x60;
            prim->v2 = prim->v3 = 0x7C;
            prim->priority = 0x9D;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
    }

    prim = self->ext.et_801C12B0.prim;
    scrollX = g_Tilemap.scrollX.i.hi;
    scrollY = g_Tilemap.scrollY.i.hi;
    self->ext.et_801C12B0.unk80++;
    if (self->ext.et_801C12B0.unk80 >= LEN(D_us_8018152C)) {
        self->ext.et_801C12B0.unk80 = 0;
    }
    if (scrollY > 0x480) {
        var_s2 = 0x5B0;
        var_s2 -= scrollY;

        while (prim != NULL) {
            if (prim->drawMode == DRAW_HIDE) {
                prim->y0 = prim->y1 = prim->y2 = prim->y3 = var_s2;
#ifdef VERSION_PSP
                var_s5 = (D_us_8018152C[self->ext.et_801C12B0.unk80] * 4) +
                         0xBB - scrollX - 9;
                prim->x2 = prim->x0 = var_s5 + (rand() & 3);
#else
                var_s5 = (rand() & 3) - 9;
                prim->x2 = prim->x0 =
                    (D_us_8018152C[self->ext.et_801C12B0.unk80] * 4) + 0xBB -
                    scrollX + var_s5;
#endif
                prim->x3 = prim->x1 = prim->x0 + 0x12;
                PGREY(prim, 0) = PGREY(prim, 1) = 0xFF;
                PGREY(prim, 2) = PGREY(prim, 3) = 0x80;
                prim->p1 = 0;
                prim->drawMode = DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE |
                                 DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
                break;
            }

            prim = prim->next;
        }
    }
    prim = self->ext.et_801C12B0.prim;
    while (prim != NULL) {
        if (prim->drawMode != DRAW_HIDE) {
            prim->y0--;
            if (rand() & 7) {
                prim->y0--;
            }
            prim->y1 = prim->y0;
            prim->p1++;
            prim->b1 -= 0x10;
            PGREY(prim, 0) = PGREY(prim, 1);
            prim->b3 -= 8;
            PGREY(prim, 2) = PGREY(prim, 3);
            if (prim->r0 < 0x11) {
                prim->drawMode = DRAW_HIDE;
            }
        }

        prim = prim->next;
    }
}

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_8019F03C);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C34EC_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C37C8_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C3A04_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C3CC4_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C3FB0_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C4228_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", EntityWaterBox);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A051C);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A069C);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A071C);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A07CC);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A09DC);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A0A80);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A1120);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A16E4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C5518_from_no4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801B5004_from_rbo5);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A1BE8);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", EntitySplashWater);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", EntityWaterDrop);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A2A90);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A2AEC);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A365C);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A3CD8);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A3EE0);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A42A8);

INCLUDE_RODATA("boss/bo3/nonmatchings/unk_1CEEC", D_us_8019CA94);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A4680);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A4988);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A4C0C);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A4E24);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A4FB8);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A516C);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A51E4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A5338);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A57A4);

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801A5948);
