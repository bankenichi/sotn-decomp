/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityMedusaHeadSpawner
   source : upstream/master:src/st/e_medusa_head.h
   target : src/st/rnz1/e_medusa_head.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
int FntPrint(const char* fmt, ...);
void DestroyEntity(Entity*);
void InitializeEntity(u16 arg0[]);
Entity* AllocEntity(Entity* start, Entity* end);
extern int rand(void);
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitSpawner;

void EntityMedusaHeadSpawner(Entity* self) {
    Entity* tempEntity;

    u8 index = self->params;
    MedusaHeadSpawnerParams* params = medusaHeadSpawnerParams;
    params += index;
    FntPrint("y:%02x\n", g_Tilemap.scrollY.i.hi);
    if (self->flags & FLAG_DEAD) {
        DestroyEntity(self);
        return;
    }
    if (!self->step) {
        InitializeEntity(g_EInitSpawner);
        self->flags &= ~FLAG_UNK_2000;
    }
    if ((g_Tilemap.scrollY.i.hi >= params->yMax) &&
        (g_Tilemap.scrollY.i.hi <= params->yMin) &&
        (LOH(PLAYER.posY.i.hi) >= 0x20) && (PLAYER.posY.i.hi < 0xC1)) {
        if (self->ext.medusaHead.timer) {
            self->ext.medusaHead.timer--;
            return;
        }
        tempEntity = AllocEntity(
            &g_Entities[128], &g_Entities[128 + params->spawnCount]);
        if (tempEntity != NULL) {
            DestroyEntity(tempEntity);
            if ((rand() & 0xF) < params->yellowChance) {
                tempEntity->entityId = E_MEDUSA_HEAD_YELLOW;
                tempEntity->pfnUpdate = EntityMedusaHeadYellow;
            } else {
                tempEntity->entityId = E_MEDUSA_HEAD_BLUE;
                tempEntity->pfnUpdate = EntityMedusaHeadBlue;
            }
            tempEntity->zPriority = params->zPriority;
            self->ext.medusaHead.timer = params->spawnDelay;
            return;
        }
        self->ext.medusaHead.timer++;
    }
}

INCLUDE_ASM("st/rnz1/nonmatchings/e_medusa_head", EntityMedusaHeadYellow);

INCLUDE_ASM("st/rnz1/nonmatchings/e_medusa_head", EntityMedusaHeadBlue);
