/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNO2:EntityBreakable
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/boss/bo1/e_breakable.c
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
u8 AnimateEntity(u8 frames[], Entity* entity);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
void ReplaceBreakableWithItemDrop(Entity*);
int abs(int x);
u_short LoadClut(u_long* clut, int x, int y);
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GameApi g_api;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern EInit g_EInitBreakable;
extern unkGraphicsStruct g_unkGraphicsStruct;

void EntityBreakable(Entity* self) {
    u16 breakableType = self->params >> 12;
    if (self->step) {
        AnimateEntity(g_eBreakableAnimations[breakableType], self);
        if (self->hitParams) {
            Entity* entityDropItem;
            g_api.PlaySfx(SFX_CANDLE_HIT);
            entityDropItem = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entityDropItem != NULL) {
                CreateEntityFromCurrentEntity(E_EXPLOSION, entityDropItem);
                entityDropItem->params =
                    g_eBreakableExplosionTypes[breakableType];
            }
            ReplaceBreakableWithItemDrop(self);
        }
    } else {
        InitializeEntity(g_EInitBreakable);
        self->zPriority = g_unkGraphicsStruct.g_zEntityCenter - 20;
        self->zPriority = g_eBreakableZPriority[breakableType];
        self->blendMode = blend_modes[breakableType];
        self->hitboxHeight = g_eBreakableHitboxes[breakableType];
        self->animSet = g_eBreakableanimSets[breakableType];
    }
}


INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", EntityBreakableDebris);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B3D8C_from_bo0);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern u16 D_us_80180B74[7];
extern u32 D_us_80180B84[7];
extern EInit g_EInitCommon;

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;
extern u16 g_Clut[3][0x1000];

void func_us_801B3F30_from_bo0(Entity* self) {
    u8 colorLo;
    u16 color;
    s16 deltaPosXHi;
    s16 absDeltaPosXHi;
    u32 curPal;
    s32 i;
    s32 j;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCommon);
        self->animSet = ANIMSET_OVL(2);
        self->animCurFrame = 3;
        self->ext.et_801B3F30.unk7C = 2;
        self->ext.et_801B3F30.unk80 = 0x10;
        self->zPriority = 0x80;
        self->blendMode = BLEND_TRANSP | BLEND_QUARTER;
        break;
    case 1:
        if (g_Tilemap.scrollY.i.hi >= 0x304) {
            deltaPosXHi = self->posX.i.hi - PLAYER.posX.i.hi;
            absDeltaPosXHi = abs(deltaPosXHi);
            if (absDeltaPosXHi < 0x80)
                self->step++;
        }
        break;
    case 2:
        if (--self->ext.et_801B3F30.unk80 == 0) {
            for (i = 0; i < 7; i++) {
                curPal = D_us_80180B84[i];
                for (j = 1; j < 16; j++) {
                    color = g_Clut[0][0x400 + curPal * COLORS_PER_PAL + j];
                    colorLo = color & 0x1F;
                    colorLo++;
                    if (colorLo > 0x1F) {
                        colorLo = 0x1F;
                    }
                    g_Clut[0][0x400 + curPal * COLORS_PER_PAL + j] =
                        (color & ~0x1F) + colorLo;
                }
            }
            LoadClut((void*)&(g_Clut[0][0x400]), 0x200, 0xF4);
            self->ext.et_801B3F30.unk80 = 0x10;
        }
        break;
    }
    if (--self->ext.et_801B3F30.unk7C == 0) {
        self->ext.et_801B3F30.unk7E++;
        self->ext.et_801B3F30.unk7C = 2;
    }
    if (self->ext.et_801B3F30.unk7E > 6) {
        self->ext.et_801B3F30.unk7E = 0;
    }
    self->palette = D_us_80180B74[self->ext.et_801B3F30.unk7E];
}


/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit g_EInitCommon;
void InitializeEntity(u16 arg0[]);

void func_us_801B4148_from_bo0(Entity* self) {
    if (self->step == 0) {
        InitializeEntity(g_EInitCommon);
        self->animSet = ANIMSET_OVL(2);
        self->animCurFrame = 1;
        self->zPriority = 0xA0;
    }
}



INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B41A4_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_322E4", func_us_801B4210_from_bo0);
