/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNO2:Entity3DHouseSpawner
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/e_background_house.h
   target : src/st/rno2/e_background_house.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", DrawFacade);

INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", DrawSides);

INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", DrawRoof);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern Tilemap g_Tilemap;

void Entity3DHouseSpawner(Entity* self) {
    Entity* tempEntity;
    s16* ptr;

    if (!self->step) {
        ptr = D_us_80180CF4;
        while (*ptr != -1) {
            tempEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (tempEntity == NULL) {
                break;
            }
            CreateEntityFromCurrentEntity(
                E_ID(3D_BACKGROUND_HOUSE), tempEntity);
            tempEntity->posX.i.hi = *ptr - g_Tilemap.scrollX.i.hi;
            ptr++;
            tempEntity->posY.i.hi = *ptr - g_Tilemap.scrollY.i.hi;
            ptr++;



            tempEntity->params = *ptr++;
        }
        self->step++;
    }
}


INCLUDE_ASM("st/rno2/nonmatchings/e_background_house", Entity3DBackgroundHouse);
