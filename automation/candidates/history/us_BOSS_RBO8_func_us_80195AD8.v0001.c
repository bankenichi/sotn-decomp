/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:BOSS/RBO8:func_us_80195AD8
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/boss/rbo8/func_us_80195ad8.h
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
void func_801CE1E8(s32 step);
s32 Random();
int abs(int x);
void InitializeEntity(u16 arg0[]);
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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern Tilemap g_Tilemap;
extern PlayerState g_Player;

void func_us_80195AD8(void) {
    Entity* target;
    Entity* entities;
    s32 xDistance;
    s32 screenX;
    u32 status;
    s32 tempY;
    s32 choice;

    entities = g_Entities;

    if (g_CurrentEntity->ext.GH_Props.unk84 == 1) {
        target = g_CurrentEntity + 14;
    } else {
        target = g_CurrentEntity + 17;
    }

    xDistance = target->posX.i.hi - entities->posX.i.hi;
    if (g_CurrentEntity->facingLeft) {
        xDistance = -xDistance;
    }

    screenX = g_CurrentEntity->posX.i.hi + g_Tilemap.scrollX.i.hi;
    if (g_CurrentEntity->facingLeft) {
        screenX = 0x200 - screenX;
    }

    if (xDistance < -0x30) {
        func_801CE1E8(0xB);
        if (screenX < 0x140 && !(Random() & 3)) {
            func_801CE1E8(7);
        }
        if (!(Random() & 7)) {
            func_801CE1E8(0xC);
        }
        return;
    }

    choice = 5;
    if (screenX < 0xC0) {
        func_801CE1E8(7);
        return;
    }
    if (screenX > 0x1C0) {
        func_801CE1E8(5);
        return;
    }

    if (screenX < 0x180 && xDistance < 0x80) {
        choice = 7;
    }
    if (screenX > 0x100 && xDistance > 0xC0) {
        choice = 5;
    }

    status = g_Player.status;
    if (status & 3) {
        Entity* currentData = g_CurrentEntity + 3;

        xDistance = currentData->posX.i.hi - entities->posX.i.hi;
        tempY = currentData->posY.i.hi - entities->posY.i.hi;
        if (g_CurrentEntity->facingLeft) {
            xDistance = -xDistance;
        }

        if ((u32)xDistance < 0x70U && abs(tempY) < 0x70 && (status & 1)) {
            choice = 9;
        } else {
            choice = 0x16;
        }
        if (!(Random() & 7)) {
            choice = 0xC;
        }
    } else if (status & 0x2000) {
        if (entities->velocityY > 0) {
            choice = 0x16;
        } else {
            choice = 0xC;
        }
    } else {
        tempY = entities->posY.i.hi + g_Tilemap.scrollY.i.hi;
        if (tempY < 0x100) {
            if (Random() & 1) {
                choice = 0x16;
            } else {
                choice = 0xC;
            }
        } else {
            if (screenX > 0x100) {
                choice = 0xE;
            }
            if (xDistance < 0x70) {
                choice = 0x12;
            }
            if (xDistance < 0x40) {
                choice = 0x1A;
            }
            if (!(Random() & 3)) {
                choice = 0xC;
            }
        }
    }

    if (!(Random() & 0xF)) {
        choice = 5;
    }

    if (g_CurrentEntity->step == 5 || g_CurrentEntity->step == 7) {
        if (choice != g_CurrentEntity->step) {
            func_801CE1E8(choice);
        }
    } else {
        func_801CE1E8(choice);
    }
}


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

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019943C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_8019953C);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_801BA164_from_cat);

INCLUDE_ASM("boss/rbo8/nonmatchings/unk_15868", func_us_80199A58);
