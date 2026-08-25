/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/BO3:EntityWaterDrop
   source : upstream/master:src/st/water_effects.h
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

INCLUDE_ASM("boss/bo3/nonmatchings/unk_1CEEC", func_us_801C2E60_from_no4);

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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitCommon;

void EntityWaterDrop(Entity* self) {
    s16 x = self->posX.i.hi;
    s16 y = self->posY.i.hi;
    FakePrim* prim;
    s32 primIndex;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCommon);
        primIndex = g_api.func_800EDB58(PRIM_TILE_ALT, 0x21);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        self->ext.timer.t = 0x2F;
        prim = (FakePrim*)&g_PrimBuf[primIndex];

        while (1) {
            prim->drawMode = DRAW_UNK_40 | DRAW_TPAGE2 | DRAW_TPAGE |
                             DRAW_UNK02 | DRAW_TRANSP;
            prim->priority = self->zPriority + 2;

            if (prim->next == NULL) {
                prim->drawMode &= ~DRAW_HIDE;
                prim->y0 = prim->x0 = prim->w = 0;
                break;
            }

            prim->posX.i.lo = prim->posY.i.lo = 0;
            prim->velocityY.val = (rand() & PSP_RANDMASK) * 8 + self->velocityY;
            prim->posY.i.hi = y + (rand() & 15);
            prim->posX.i.hi = x + (rand() & 31) - 16;
            prim->delay = (rand() & 15) + 32;
            prim->x0 = prim->posX.i.hi;
            prim->y0 = prim->posY.i.hi;
            prim->r0 = 255;
            prim->g0 = 255;
            prim->b0 = 255;
            prim->w = 2;
            prim->h = 2;
            prim = prim->next;
        }
        break;

    case 1:
        if (--self->ext.timer.t == 0) {
            DestroyEntity(self);
            return;
        }

        prim = (FakePrim*)&g_PrimBuf[self->primIndex];

        while (1) {
            if (prim->next == NULL) {
                prim->drawMode &= ~DRAW_HIDE;
                prim->y0 = prim->x0 = prim->w = 0;
                return;
            }
            prim->posX.i.hi = prim->x0;
            prim->posY.i.hi = prim->y0;
            if (!--prim->delay) {
                prim->drawMode |= DRAW_HIDE;
            }
            prim->posY.val += prim->velocityY.val;
            if (prim->velocityY.val > FIX(0.5)) {
                prim->r0 -= 4;
                prim->g0 -= 4;
                prim->b0 -= 4;
            } else {
                prim->velocityY.val += FIX(28.0 / 128);
            }
            prim->x0 = prim->posX.i.hi;
            prim->y0 = prim->posY.i.hi;
            prim = prim->next;
        }
        break;
    }
}

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
