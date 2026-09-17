/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:BOSS/RBO8:func_us_8019943C
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/boss/rbo8/unk_15868.c
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
void polarPlacePart(Entity* self);
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
s32 Random();
int rsin(int a);
int rcos(int a);
void MoveEntity();
u8 AnimateEntity(u8 frames[], Entity* entity);
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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180A98;

void func_us_801991D4(Entity* self) {
    if (self->step == 0) {
        InitializeEntity(D_us_80180A98);
        return;
    }
    DestroyEntity(self);
}


INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019921C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", EntityMinotaurSpitLiquid);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180AB0;
extern s32 D_us_80180C68[]; /* retained BOSS/RBO8 data asm/us/boss/rbo8/data/B74.data.s, size 0x20 */

void func_us_8019943C(Entity* self) {
    s16 angle;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180AB0);
        if (self->facingLeft) {
            self->rotate = -self->rotate;
        }
        self->facingLeft = 0;
        self->rotate += 0x100 - Random() * 2;

        angle = self->rotate;
        self->velocityX = rsin(angle) * 0x20;
        self->velocityY = rcos(angle) * -0x20;
        self->blendMode = BLEND_ADD | BLEND_TRANSP;
        /* fall through */
    case 1:
        MoveEntity();
        self->posY.i.hi--;
        if (AnimateEntity(D_us_80180C68, self) == 0) {
            DestroyEntity(self);
        }
        break;
    }
}


INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019953C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_801BA164_from_cat);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80199A58);
