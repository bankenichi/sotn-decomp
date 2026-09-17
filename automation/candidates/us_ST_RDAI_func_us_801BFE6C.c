/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RDAI:func_us_801BFE6C
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/e_rdai_archer.h
   target : src/st/rdai/unk_3F6B4.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rdai.h"

#include "../e_spear_guard_collision.h"

#include "../approach_s16.h"

// Both candidates below failed to build on these names alone.
//
// g_EInitRdaiUnk1F IS reachable via ../e_rdai_unk1f.h, but that include sits
// BELOW this point, so a body substituted into the func_us_801BF830 stub
// cannot see it. Position is the whole problem here; declaring it above the
// stub is what makes the retry viable.
//
// D_us_80180884 is defined by THIS overlay at src/st/rdai/e_init.c:127.
extern EInit g_EInitRdaiUnk1F;
extern EInit D_us_80180884;

INCLUDE_ASM("st/rdai/nonmatchings/unk_3F6B4", func_us_801BF830);

// Child parts share one implementation; only the fixed EInit address is local.
#include "../e_rdai_unk1f.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void SetStep(u8 step);
void InitializeEntity(u16 arg0[]);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
long ratan2(long y, long x);
bool func_801CDC80(s16* arg0, s16 arg1, s16 arg2);
void PlaySfxPositional(s32 arg0);
Entity* AllocEntity(Entity* start, Entity* end);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

// These functions do not match from portable C under the PSX compiler.
/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern s16 g_RdaiArcherOffsets[][2];
extern EInit g_EInitArcher;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void func_us_801BFE6C(Entity* self) {
    Entity* entity;
    s32 i;
    s32 animIndex;
    s16 angle;
    s32 deltaX;
    s32 deltaY;

    entity = self - 4;
    self->posX.i.hi = entity->posX.i.hi + 0x28;
    self->posY.i.hi = entity->posY.i.hi + 0x10;
    animIndex = entity->animCurFrame - 0x21;
    if (animIndex >= 0) {
        s16* offsets = (s16*)g_RdaiArcherOffsets;
        offsets += animIndex * 2;
        self->posX.i.hi += offsets[0];
        self->posY.i.hi += offsets[1];
    }

    if ((self->flags & FLAG_DEAD) && self->step != 3) {
        SetStep(3);
    }

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitArcher);
        self->animCurFrame = 0x1D;













        CreateEntityFromEntity(E_UNK_1D, self, self + 1);
        (self + 1)->params = 1;
        (self + 1)->nextPart = self;
        self->nextPart = self + 1;
        CreateEntityFromEntity(E_UNK_1D, self, self + 2);
        (self + 2)->params = 2;
        CreateEntityFromEntity(E_UNK_1D, self, self + 3);
        (self + 3)->params = 3;

        // fallthrough

    case 1:
        if (!self->step_s) {
            self->ext.rdaiArcher.timer = 0x80;
            self->ext.rdaiArcher.mode = 0;
            self->step_s++;
        }
        entity = &PLAYER;
        deltaX = entity->posX.i.hi - self->posX.i.hi;
        deltaY = entity->posY.i.hi - self->posY.i.hi;
        angle = ratan2(deltaY, deltaX);
        if (angle > 0x200) {
            angle = 0x200;
        }
        if (angle < -0x200) {
            angle = -0x200;
        }
        func_801CDC80(&self->rotate, angle, 8);
        if (!--self->ext.rdaiArcher.timer) {
            SetStep(2);
        }
        break;

    case 2:
        switch (self->step_s) {
        case 0:
            self->ext.rdaiArcher.timer = 0x60;
            self->ext.rdaiArcher.mode = 1;
            self->step_s++;
            // fallthrough
        case 1:
            entity = &PLAYER;
            deltaX = entity->posX.i.hi - self->posX.i.hi;
            deltaY = entity->posY.i.hi - self->posY.i.hi;
            angle = ratan2(deltaY, deltaX);
            if (angle > 0x200) {
                angle = 0x200;
            }
            if (angle < -0x200) {
                angle = -0x200;
            }
            func_801CDC80(&self->rotate, angle, 8);
            if (!--self->ext.rdaiArcher.timer) {
                PlaySfxPositional(SFX_ARROW_SHOT_D);
                self->ext.rdaiArcher.mode = 2;
                self->ext.rdaiArcher.timer = 0x30;
                self->step_s++;
            }
            break;

        case 2:
            if (!--self->ext.rdaiArcher.timer) {
                self->ext.rdaiArcher.mode = 3;
                self->ext.rdaiArcher.timer = 0x80;
                self->step_s++;
            }
            break;

        case 3:
            if (!--self->ext.rdaiArcher.timer) {
                SetStep(1);
            }
            break;
        }
        break;

    case 3:
        for (i = 0; i < 3; i++) {
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_UNK_21, self, entity);
                entity->params = i + 0x13;
            }
        }
        DestroyEntity(self);
        break;
    }
}


INCLUDE_ASM("st/rdai/nonmatchings/unk_3F6B4", func_us_801C0240);

INCLUDE_ASM("st/rdai/nonmatchings/unk_3F6B4", func_us_801C0528);

INCLUDE_ASM("st/rdai/nonmatchings/unk_3F6B4", func_us_801C0898);
