/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v2-top-level-seed-declarations
   record : us:BOSS/BO2:EntityBossDoors
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/boss/bo0/e_boss_doors.c
   target : src/boss/bo2/unk_224DC.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo2.h"

extern u8* g_eBreakableAnimations[];
extern u8 g_eBreakableHitboxes[];
extern u8 g_eBreakableExplosionTypes[];
extern u16 g_eBreakableanimSets[];
extern u8 blend_modes[];

#include "../../st/e_breakable.h"

INCLUDE_ASM("boss/bo2/nonmatchings/unk_224DC", func_us_801A2610);

INCLUDE_ASM("boss/bo2/nonmatchings/unk_224DC", func_us_801A269C);

#include "e_minotaur.h"

INCLUDE_ASM("boss/bo2/nonmatchings/unk_224DC", func_us_801A3E04);

INCLUDE_ASM("boss/bo2/nonmatchings/unk_224DC", func_us_801A460C);

// Shared body vendored with the overlay so this source remains self-contained.
#include "e_unk_29.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void DestroyEntity(Entity*);
void InitializeEntity(u16 arg0[]);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void PlaySfxPositional(s32 arg0);
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
void MoveEntity();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/bo2/nonmatchings/unk_224DC", EntityBossTorch);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;
extern u32 g_Timer;

void EntityBossDoors(Entity* self) {
    Entity* entity;
    s32 offsetX;
    s32 i;
    s32 fgIndex;
    s16* fgTiles;

    switch (self->step) {
    case 0:
        if (D_us_80181190) {
            DestroyEntity(self);
            return;
        }

        InitializeEntity(g_EInitBossDoors);
        self->zPriority = 0x69;
        if (self->params) {
            self->posX.i.hi = 0x218 - g_Tilemap.scrollX.i.hi;
        }
        if (self->params) {
            fgIndex = 0xDD;
            fgTiles = D_us_801813A4;
        } else {
            fgIndex = 0xC0;
            fgTiles = D_us_80181374;
        }

        for (i = 0; i < 4; i++, fgTiles += 3) {
            (&g_Tilemap.fg[fgIndex])[0] = fgTiles[0];
            (&g_Tilemap.fg[fgIndex])[1] = fgTiles[1];
            (&g_Tilemap.fg[fgIndex])[2] = fgTiles[2];
            fgIndex += 32;
        }

        break;
    case 1:
        entity = &PLAYER;
        offsetX = entity->posX.i.hi + g_Tilemap.scrollX.i.hi;
        if (offsetX < 0x1E8) {
            if (self->params) {
                entity = self + 1;
                CreateEntityFromEntity(E_ID(BOSS_DOORS), self, entity);
                entity->posX.i.hi = -0x18 - g_Tilemap.scrollX.i.hi;
                entity->params = 0;
            }
            PlaySfxPositional(SFX_STONE_MOVE_B);
            self->step++;
        }
        break;
    case 2:
        if (!self->step_s) {
            if (self->params) {
                self->velocityX = FIX(-0.5);
            } else {
                self->velocityX = FIX(0.5);
            }
            self->step_s++;
        }
        GetPlayerCollisionWith(self, 0x18, 0x20, 5);
        MoveEntity();
        if (!(g_Timer & 0xF)) {
            PlaySfxPositional(SFX_STONE_MOVE_B);
        }
        offsetX = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
        if (self->params) {
            if (offsetX < 0x1E8) {
                self->posX.i.hi = 0x1E8 - g_Tilemap.scrollX.i.hi;
                self->step++;
            }
        } else if (offsetX > 0x18) {
            self->posX.i.hi = 0x18 - g_Tilemap.scrollX.i.hi;
            self->step++;
        }
        break;
    case 3:
        if (self->params) {
            fgIndex = 0xDD;
            fgTiles = D_us_801813BC;
        } else {
            fgIndex = 0xC0;
            fgTiles = D_us_8018138C;
        }
        for (i = 0; i < 4; i++, fgTiles += 3) {
            (&g_Tilemap.fg[fgIndex])[0] = fgTiles[0];
            (&g_Tilemap.fg[fgIndex])[1] = fgTiles[1];
            (&g_Tilemap.fg[fgIndex])[2] = fgTiles[2];
            fgIndex += 32;
        }
        self->step++;
        break;
    case 4:
        if (D_us_80181190) {
            self->step++;
        }
        break;
    case 5:
        if (self->params) {
            fgIndex = 0xDD;
            fgTiles = D_us_801813A4;
        } else {
            fgIndex = 0xC0;
            fgTiles = D_us_80181374;
        }
        for (i = 0; i < 4; i++, fgTiles += 3) {
            (&g_Tilemap.fg[fgIndex])[0] = fgTiles[0];
            (&g_Tilemap.fg[fgIndex])[1] = fgTiles[1];
            (&g_Tilemap.fg[fgIndex])[2] = fgTiles[2];
            fgIndex += 32;
        }
        if (self->params) {
            self->velocityX = FIX(0.5);
        } else {
            self->velocityX = FIX(-0.5);
        }
        self->step++;
        break;
    case 6:
        MoveEntity();
        offsetX = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
        if (self->params) {
            if (offsetX > 0x218) {
                DestroyEntity(self);
                return;
            }
        } else if (offsetX < -0x18) {
            DestroyEntity(self);
            return;
        }
        break;

    case 0xFF:
#include "../../st/pad2_anim_debug.h"
        break;
    }
}
