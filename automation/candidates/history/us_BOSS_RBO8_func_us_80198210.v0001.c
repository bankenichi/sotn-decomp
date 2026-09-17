/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:BOSS/RBO8:func_us_80198210
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
u16 GetAngleBetweenEntities(Entity* a, Entity* b);
int rcos(int a);
int rsin(int a);
u8 AnimateEntity(u8 frames[], Entity* entity);
void MoveEntity();
int abs(int x);
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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern s32 D_us_80180C0C[]; /* retained BOSS/RBO8 data asm/us/boss/rbo8/data/B74.data.s, size 0x4 */
extern EInit D_us_80180A8C;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern s32 D_us_80180C20[]; /* retained BOSS/RBO8 data asm/us/boss/rbo8/data/B74.data.s, size 0x2c */

void func_us_80198210(Entity* self) {
    Entity* entities;
    s16 angle;

    if ((self->flags & FLAG_DEAD) || D_us_80180C0C != 0) {
        self->velocityX = 0;
        self->velocityY = 0;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180A8C);
        self->blendMode = BLEND_ADD | BLEND_TRANSP;
        entities = g_Entities;
        angle = GetAngleBetweenEntities(self, entities);
        self->velocityX = rcos(angle) * 0x140;
        self->velocityY = rsin(angle) * 0x140;
        /* fall through */

    case 1:
        AnimateEntity(D_us_80180C20, self);
        MoveEntity();
        self->velocityX -= self->velocityX / 0x10;
        self->velocityY -= self->velocityY / 0x10;
        if (abs(self->velocityX) < 0x4000 && abs(self->velocityY) < 0x4000) {
            self->drawFlags = ENTITY_SCALEY | ENTITY_SCALEX;
            self->scaleX = self->scaleY = 0x100;
            self->hitboxState = 0;
            self->step++;
        }
        break;

    case 2:
        AnimateEntity(D_us_80180C20, self);
        self->scaleX = self->scaleY -= 0x10;
        if (!self->scaleX) {
            DestroyEntity(self);
        }
        break;
    }
}


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

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019943C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019953C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_801BA164_from_cat);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80199A58);
