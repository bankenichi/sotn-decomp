/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RLIB:func_us_801AFC88
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rlib/unk_2DBE8.c
   target : src/st/rlib/unk_2DBE8.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rlib.h"

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801ADBE8);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", EntityHarpyKick);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AE414);

#define func_801CDC80 func_us_801AE4B4
#include "../approach_s16.h"
#undef func_801CDC80



INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AE534);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AED4C);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AEFE0);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801D8D44_from_no4);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AF11C);

#define func_801CDC80 func_us_801AF3C8
#include "../approach_s16.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void PlaySfxPositional(s32 arg0);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void DestroyEntity(Entity*);
void InitializeEntity(u16 arg0[]);
u8 GetSideToPlayer();
u8 AnimateEntity(u8 frames[], Entity* entity);
void MoveEntity();
s16 GetDistanceToPlayerX();
void SetStep(u8 step);
int abs(int x);
/* End permuter-seed writer declarations. */
#undef func_801CDC80



INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AF448);

INCLUDE_ASM("st/rlib/nonmatchings/unk_2DBE8", func_us_801AF9E8);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern EInit g_EInitSchmoo;
extern s32 D_us_8018198C[]; /* retained ST/RLIB data asm/us/st/rlib/data/1750.data.s, size 0xc */
extern s32 D_us_80181998[]; /* retained ST/RLIB data asm/us/st/rlib/data/1750.data.s, size 0x8c */

void func_us_801AFC88(Entity* self) {
    Entity* entity;
    s32 sideToPlayer;
    s32 distanceToPlayer;

    if (self->flags & FLAG_DEAD) {
        PlaySfxPositional(SFX_EXPLODE_B);
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_EXPLOSION, self, entity);
            entity->params = 1;
        }
        DestroyEntity(self);
        return;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitSchmoo);
        self->drawFlags = ENTITY_ROTATE;
        self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        /* fall through */
    case 1:
        AnimateEntity(&D_us_8018198C, self);
        MoveEntity();
        sideToPlayer = GetSideToPlayer();

        if (self->facingLeft) {
            self->velocityX += FIX(0.046875);
            if (self->velocityX > FIX(3)) {
                self->velocityX = FIX(3);
            }
        } else {
            self->velocityX -= FIX(0.046875);
            if (self->velocityX < FIX(-3)) {
                self->velocityX = FIX(-3);
            }
        }

        if (sideToPlayer & 2) {
            self->velocityY -= FIX(0.046875);
            if (self->velocityY < FIX(-1.5)) {
                self->velocityY = FIX(-1.5);
            }
        } else {
            self->velocityY += FIX(0.046875);
            if (self->velocityY > FIX(1.5)) {
                self->velocityY = FIX(1.5);
            }
        }

        sideToPlayer = (sideToPlayer & 1) ^ 1;
        distanceToPlayer = GetDistanceToPlayerX();
        if (sideToPlayer != self->facingLeft && distanceToPlayer >= 0x59) {
            SetStep(2);
        }
        break;

    case 2:
        MoveEntity();
        switch (self->step_s) {
        case 0:
            self->velocityX -= self->velocityX >> 4;
            self->velocityY -= self->velocityY >> 4;
            if (abs(self->velocityX) < FIX(0.25)) {
                self->step_s++;
            }
            break;

        case 1:
            self->velocityX -= self->velocityX >> 8;
            self->velocityY -= self->velocityY >> 8;
            if (AnimateEntity(&D_us_80181998, self) == 0) {
                SetStep(1);
            }
            if (!self->poseTimer && self->pose == 2) {
                self->facingLeft ^= 1;
            }
            break;
        }
        break;
    }

    self->rotate = -abs(self->velocityX >> 8);
}
