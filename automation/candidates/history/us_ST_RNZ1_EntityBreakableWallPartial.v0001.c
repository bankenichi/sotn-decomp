/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityBreakableWallPartial
   source : upstream/master:src/st/nz1/e_secrets.c
   target : src/st/rnz1/unk_276A8.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void PlaySfxPositional(s32 arg0);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s32 Random();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBackgroundGears);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysLarge);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearHorizontal);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearVertical);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysSmall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWallGear);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretAreaDoor);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWall);

void EntityBreakableWallPartial(Entity* self) {
    Entity* tempEntity;
    s32 i;
    s32 tileX, tileY;
    s32 tileIdx;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        if (g_CastleFlags[NZ1_STATUE_ROOM_BREAKABLE_WALLS] &
            (1 << self->params)) {
            tileX = self->posX.i.hi;
            tileY = self->posY.i.hi - 0x10;
            tileX += g_Tilemap.scrollX.i.hi;
            tileY += g_Tilemap.scrollY.i.hi;
            for (i = 0; i < 3; i++) {
                tileIdx =
                    (tileX >> 4) + ((tileY >> 4) * g_Tilemap.hSize * 0x10);
                g_Tilemap.fg[tileIdx] = D_us_80181078[i + 3];
                tileY += 0x10;
            }
            self->step = 0x10;
            return;
        }
        self->hitboxState = 2;
        self->hitPoints = 0x7FFF;
        self->hitboxWidth = 8;
        self->hitboxHeight = 0x18;
         
    case 1:
        if (self->hitFlags) {
            PlaySfxPositional(SFX_WALL_DEBRIS_B);
            self->step++;
        }
        break;

    case 2:
        tileX = self->posX.i.hi;
        tileY = self->posY.i.hi - 0x10;
        tileX += g_Tilemap.scrollX.i.hi;
        tileY += g_Tilemap.scrollY.i.hi;
        for (i = 0; i < 3; i++) {
            tileIdx = (tileX >> 4) + ((tileY >> 4) * g_Tilemap.hSize * 0x10);
            g_Tilemap.fg[tileIdx] = D_us_80181078[i + 3];
            tileY += 0x10;
        }
        self->hitboxState = 0;
        tempEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (tempEntity != NULL) {
            CreateEntityFromEntity(E_EXPLOSION, self, tempEntity);
            tempEntity->params = 0x13;
        }
        for (i = 0; i < 3; i++) {
            tempEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (tempEntity != NULL) {
                CreateEntityFromEntity(
                    E_ID(SECRET_WALL_DEBRIS), self, tempEntity);
                tempEntity->posY.i.hi += (Random() & 0x1F) - 0x10;
                tempEntity->params = 1;
            }
        }
        g_CastleFlags[NZ1_STATUE_ROOM_BREAKABLE_WALLS] |= (1 << self->params);
        tempEntity = AllocEntity(&g_Entities[160], &g_Entities[192]);
        if (tempEntity != NULL) {
            CreateEntityFromEntity(E_EQUIP_ITEM_DROP, self, tempEntity);
            tempEntity->params = item_drops[self->params];
        }
        self->step++;
        break;
    }
}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretWallDebris);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", func_us_801A8F7C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWaterForeground);
