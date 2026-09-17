/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RCEN:func_us_8019C610
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rcen/func_us_8019c610.h
   target : src/st/rcen/e_shaft.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rcen.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
int abs(int x);
void DestroyEntity(Entity*);
void InitializeEntity(u16 arg0[]);
int rcos(int a);
int rsin(int a);
void MoveEntity();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
u8 AnimateEntity(u8 frames[], Entity* entity);
/* End permuter-seed writer declarations. */

s16 func_us_8019A98C(s16 arg0, s16 arg1, s16 arg2) {
    s16 v_s1;
    s16 v_s0;

    arg1 &= 0xFFF;

    v_s1 = arg2 - arg1;
    v_s0 = v_s1;

    if (v_s1 > ROT(180)) {
        v_s0 = v_s1 - ROT(360);
    }
    if (v_s1 < ROT(-180)) {
        v_s0 = v_s1 + ROT(360);
    }

    if (abs(v_s0) > arg0) {
        if (v_s1 < 0) {
            v_s0 = arg1 - arg0;
        } else {
            v_s0 = arg1 + arg0;
        }
        return v_s0;
    }

    return arg2;
}

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019AA04);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", EntityShaft);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019B5A4);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019B6D4);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019B8A8);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019C4EC);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180588;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern s32 D_us_80180874[]; /* retained ST/RCEN data asm/us/st/rcen/data/68C.data.s, size 0x1c */

void func_us_8019C610(Entity* self) {
    Entity* entity;
    s16 angle;

    if (g_RcenShaftFlags & 4) {
        DestroyEntity(self);
        return;
    }

    if (!self->step) {
        InitializeEntity(D_us_80180588);
        self->palette = 0x2E4;
        self->drawFlags = ENTITY_OPACITY | ENTITY_ROTATE;
        self->rotate = (s16)(self->ext.rcenShaftProjectile.angle + 0x400);
        angle = self->ext.rcenShaftProjectile.angle;
        self->velocityX = (rcos(angle) * 0x30000) >> 0xC;
        self->velocityY = (rsin(angle) * 0x30000) >> 0xC;
        self->blendMode = BLEND_ADD | BLEND_TRANSP;
    }

    MoveEntity();
    angle = self->ext.rcenShaftProjectile.angle;
    self->velocityX += (rcos(angle) << 0xA) >> 0xC;
    self->velocityY += (rsin(angle) << 0xA) >> 0xC;

    if (self->params && self->pose == 7 && !self->poseTimer) {
        entity = AllocEntity(&g_Entities[112], &g_Entities[192]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_ID(UNK_1C), self, entity);
            entity->zPriority = self->zPriority;
            entity->params = self->params - 1;
            entity->ext.rcenShaftProjectile.angle =
                self->ext.rcenShaftProjectile.angle;
        }
    }

    self->opacity -= 2;
    if (!self->opacity) {
        DestroyEntity(self);
        return;
    }
    if (!AnimateEntity(D_us_80180874, self)) {
        DestroyEntity(self);
    }
}


INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019C7B8);

extern u32 PrizeDrops;
extern EInit D_us_80180594;

// Initializes shaft prize-drop entity if its drop flag is unset, otherwise destroys it
void func_us_8019CDA0(Entity* self) {
    if (!(PrizeDrops & 4)) {
        if (self->step == 0) {
            InitializeEntity(D_us_80180594);
            return;
        }
    }
    DestroyEntity(self);
}

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019CDF8);
