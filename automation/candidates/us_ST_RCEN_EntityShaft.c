/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RCEN:EntityShaft
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/boss/bo6/us_3E79C.c
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
int FntPrint(const char* id, ...);
void CreateEntityFromCurrentEntity(u16, Entity*);
int rsin(int a);
void DestroyEntity(Entity*);
void InitializeEntity(u16 arg0[]);
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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern u32 g_CutsceneFlags;
extern GAME_IMPORT DemoMode g_DemoMode;

void EntityShaft(Entity* self) {
    Entity* entity;
    FntPrint("I AM SHAFT\n");
    switch (self->step) {
    case 0:



        self->flags = FLAG_UNK_10000000;

        self->animSet = -0x7FFB;
        self->animCurFrame = 0x8B;
        self->unk5A = 0x48;
        self->palette = PAL_FLAG(0x250);
        self->zPriority = RIC.zPriority + 2;
        self->opacity = 0;
        self->drawFlags = ENTITY_OPACITY;
        self->blendMode = BLEND_ADD | BLEND_TRANSP;
        self->step++;
        break;

    case 1:
        self->opacity += 4;
        if (self->opacity > 48) {
            self->step++;
            entity = &g_Entities[0xC8];
            CreateEntityFromCurrentEntity(E_ID(ID_17), entity);
            entity->params = 3;
            self->ext.shaft.timer = 0x100;
        }
        self->posY.val += rsin(self->ext.shaft.bobAngle) * 4;
        self->ext.shaft.bobAngle += 0x20;
        break;

    case 2:
        if (!self->ext.shaft.timer) {
            if ((g_CutsceneFlags & 0x40) || (g_DemoMode != Demo_None)) {
                self->drawFlags |= ENTITY_SCALEY | ENTITY_SCALEX;
                self->scaleX = self->scaleY = 0x100;
                self->step++;
            }
        } else {
            self->ext.shaft.timer--;
        }
        self->posY.val += rsin(self->ext.shaft.bobAngle) * 4;
        self->ext.shaft.bobAngle += 0x20;
        break;

    case 3:
        self->scaleX -= 0x20;
        if (self->scaleX < 0x10) {
            self->scaleX = 0x10;
        }

        self->scaleY += 64;
        if (self->scaleY > 0x800) {
            self->scaleY = 0x800;
        }
        self->opacity += 6;
        if (self->opacity > 0xF0) {
            self->step++;
        }
        break;

    case 4:
        self->opacity -= 3;
        if (self->opacity < 4) {
            DestroyEntity(self);
        }
        break;
    }
}


INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019B5A4);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019B6D4);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019B8A8);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019C4EC);

INCLUDE_ASM("st/rcen/nonmatchings/e_shaft", func_us_8019C610);

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
