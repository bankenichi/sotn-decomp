/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:BOSS/RBO6:func_us_801A1B38
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/boss/rbo6/unk_1D690.c
   target : src/boss/rbo6/unk_1D690.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo6.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void DestroyEntity(Entity*);
void InitializeEntity(u16 arg0[]);
u8 AnimateEntity(u8 frames[], Entity* entity);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", EntityBreakable);

// decompiled in src/boss/bo1/e_explosion_flame.c
INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019D260_from_rcen);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019D330_from_rcen);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019DB9C);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019EADC);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019EE30);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019F1CC);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019FA78);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019FB04);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019FBC0);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_8019FCB4);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A01A4);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A0710);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A0860);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A0AB4);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A0DC0);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A1150);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_1D690", func_us_801A11DC);

void func_us_801A1B38(Entity* self) {
    Entity* real;

    if (*(s32*)0x801806E4 & 1) {
        DestroyEntity(self);
        return;
    }

    if (!self->step) {
        InitializeEntity((u16*)((u32)func_us_801A1B38 - 0x215F8));
        self->blendMode = BLEND_ADD | BLEND_TRANSP;
    }

    AnimateEntity((u8*)((u32)func_us_801A1B38 - 0x2134C), self);

    real = self->ext.succubus.real;
    self->posX.i.hi = real->posX.i.hi;
    self->posY.i.hi = real->posY.i.hi + 0xC;

    if (*(s32*)0x80180700 == 5) {
        DestroyEntity(self);
    }
}
