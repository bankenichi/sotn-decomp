/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:BOSS/RBO8:func_us_8019921C
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
void MoveEntity();
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int func_us_801955A0();
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


/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitGalamothLvl50;

void func_us_8019921C(Entity* self) {
    s32 args[9];

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitGalamothLvl50);
        self->animCurFrame = self->params;
        self->drawFlags = ENTITY_ROTATE;
        /* fall through */
    case 1:
        MoveEntity();
        self->rotate -= ROT(2.8125);
        self->velocityY += FIX(0.125);
        if (self->facingLeft) {
            self->velocityX = FIX(0.5);
        } else {
            self->velocityX = FIX(-0.5);
        }
        args[6] = 0x20;
        func_us_801955A0(self, args);
        if (self->ext.et_8019921C.hitFloor) {
            self->flags |= FLAG_DESTROY_IF_OUT_OF_CAMERA;
            self->zPriority = 0x5F;
        }
        break;
    }
}


INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", EntityMinotaurSpitLiquid);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019943C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019953C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_801BA164_from_cat);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80199A58);
