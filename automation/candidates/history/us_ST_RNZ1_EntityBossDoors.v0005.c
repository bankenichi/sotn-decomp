/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNZ1:EntityBossDoors
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rnz1/bossfight.c
   target : src/st/rnz1/unk_29914.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
int abs(int x);

#include "../approach_s16.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
void MoveEntity();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s32 Random();
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */



INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801A9994);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801A9DB8);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", EntityFrozenShadeCrystal);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AAF00);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB04C);

void func_801B2CF8(Primitive* prim) {
    s32 i;
    // Clear the complete object one word at a time, starting at its real first
    // member. The target uses a word loop rather than individual fields.
    s32* ptr = (s32*)&prim->next;
    s32 size = sizeof(*prim) / sizeof(*ptr);

    for (i = 0; i < size; i++) {
        *ptr++ = 0;
    }
}



void func_us_801AB16C(s32* src, s32* dst, s32 count) {
    s32 i;

    // CODEGEN: The target overwrites incoming a2 with 13, then uses a register
    // slt. Keeping the bound in the third parameter preserves that exact shape.
    count = 13;

    for (i = 0; i < count; i++) {
        *dst++ = *src++;
    }
}


INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB198);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB380);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB768);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801ABA38);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801ABB58);

void RNZ1_Unused801ABDC0(void) {}

void func_us_801ABDC8(s32* values) {
    values[0] -= 0x400;
    values[5] -= 0x400;
}


INCLUDE_RODATA("st/rnz1/nonmatchings/unk_29914", D_us_801A6050);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801ABDE4);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", EntityBossDoorTrigger);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitEnvironment;
extern GameApi g_api;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern Tilemap g_Tilemap;

void EntityBossDoors(Entity* self) {
    s16* doorTilemap;
    Entity* entity;
    s32 offsetX;
    s32 tileIndex;
    s32 i;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitEnvironment);
        self->animCurFrame = 7;
        self->zPriority = 0x78;
        break;

    case 1:
        if (g_bossDoorsLocked) {
            g_api.PlaySfx(SFX_STONE_MOVE_B);
            self->step++;












        }
        break;

    case 2:
        GetPlayerCollisionWith(self, 8, 32, 5);
        if (self->params) {
            self->velocityX = FIX(-0.5);
        } else {
            self->velocityX = FIX(0.5);
        }

        MoveEntity();
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_INTENSE_EXPLOSION, self, entity);
            entity->params = 0x10;
            entity->posY.i.hi += 32;
            entity->posX.i.hi -= (Random() & 7);
        }
        offsetX = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
        if (self->params) {
            if (offsetX < 238) {
                self->step++;
            }
        } else if (offsetX > 18) {
            self->step++;
        }
        break;

    case 3:
        doorTilemap = D_us_8018113C;
        if (self->params) {
            tileIndex = 0x9E;
        } else {
            tileIndex = 0x91;
            doorTilemap += 4;
        }
        for (i = 0; i < 4; i++, doorTilemap++, tileIndex -= 16) {
            g_Tilemap.fg[tileIndex] = *doorTilemap;
        }
        self->step++;
        // fallthrough

    case 4:
        GetPlayerCollisionWith(self, 8, 32, 5);
        if (!g_bossDoorsLocked) {



            doorTilemap = D_us_8018113C;

            if (self->params) {
                tileIndex = 0x9E;
            } else {
                tileIndex = 0x91;
                doorTilemap += 4;
            }
            for (i = 0; i < 4; i++, tileIndex -= 16) {
                g_Tilemap.fg[tileIndex] = 0;
            }
            g_api.PlaySfx(SFX_STONE_MOVE_B);
            self->step++;
        }
        break;

    case 5:
        if (self->params) {
            self->velocityX = FIX(0.75);
        } else {
            self->velocityX = FIX(-0.75);
        }
        MoveEntity();
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_INTENSE_EXPLOSION, self, entity);
            entity->params = 0x10;
            entity->posY.i.hi += 32;
            entity->posX.i.hi -= (Random() & 7);
        }
        offsetX = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
        if (self->params) {
            if (offsetX > 264) {
                DestroyEntity(self);
            }
        } else if (offsetX > 7) {
            DestroyEntity(self);
        }
        break;
    }
}
