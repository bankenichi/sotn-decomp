/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNO2:func_us_801B5FB8_from_no2
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/no2/e_secrets.c
   target : src/st/rno2/unk_3459C.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
int FntPrint(const char* id, ...);
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
void PlaySfxPositional(s32 arg0);
void UnkPolyFunc2(Primitive* prim);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s32 Random();
void func_us_801B59C4(Primitive* prim);
/* End permuter-seed writer declarations. */


INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801AB9EC_from_bo0);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitEnvironment;
extern u8 g_CastleFlags[];
extern Tilemap g_Tilemap;
extern GameApi g_api;
extern Primitive g_PrimBuf[];
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void func_us_801B5FB8_from_no2(Entity* self) {
    Entity* tempEntity;
    Primitive* prim;
    s32 primIndex;
    s32 i;
    s32 tileIdx;

    FntPrint(            , self->ext.breakableNo2.unk80);
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitEnvironment);
        self->animCurFrame = 0;
        if (g_CastleFlags[NO2_SECRET_WALL_OPEN]) {
            for (i = 0; i < 10; i++) {
                tileIdx = D_us_80180DEC[i];
                g_Tilemap.fg[tileIdx] = D_us_80180E00[i];
            }
            DestroyEntity(self);
            return;
        }
        self->zPriority = 0xA8;
        self->hitboxState = 2;

        self->hitPoints = 0x7FFF;



        self->hitboxWidth = 16;
        self->hitboxHeight = 40;
        break;


    case STEP_SFX:
        if (self->hitFlags) {
            PlaySfxPositional(SFX_WALL_DEBRIS_B);
            self->ext.breakableNo2.unk80 = 0x10;
            self->ext.breakableNo2.unk88++;
            self->step++;
        }
        if (self->ext.breakableNo2.unk88 == 3) {
            self->hitboxState = 0;
            self->step = 3;
        }
        break;


    case STEP_ANIMATE:

        if (self->ext.breakableNo2.unk88 == 1) {
            self->animCurFrame = 12;
        }
        if (self->ext.breakableNo2.unk88 == 2) {
            self->animCurFrame = 13;
        }
        if (!--self->ext.breakableNo2.unk80) {
            self->step--;
        }













        break;

    case STEP_GENERATE_DEBRIS:
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 0x20);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];
            self->ext.breakableNo2.unk7C = prim;
            while (prim != NULL) {
                prim->drawMode = DRAW_HIDE;
                prim = prim->next;
            }
        } else {
            g_CastleFlags[NO2_SECRET_WALL_OPEN] |= 1;

            g_api.RevealSecretPassageAtPlayerPositionOnMap(
                NO2_SECRET_WALL_OPEN);

            for (i = 0; i < 10; i++) {
                tileIdx = D_us_80180DEC[i];
                g_Tilemap.fg[tileIdx] = D_us_80180E00[i];
            }
            DestroyEntity(self);
            return;
        }
        prim = self->ext.breakableNo2.unk7C;
        for (i = 0; i < 2; i++) {
            prim->tpage = 0xF;
            prim->clut = 0x21;
            prim->u0 = prim->u2 = 0x80;
            prim->u1 = prim->u3 = 0x97;
            prim->v0 = prim->v1 = 0xF0;
            prim->v2 = prim->v3 = 0xFF;
            prim->x0 = prim->x2 = self->posX.i.hi + 0xFFEF;
            prim->x1 = prim->x3 = prim->x0 + 0x18;
            if (i != 0) {
                prim->y0 = prim->y1 = self->posY.i.hi + 0x10008;
            } else {
                prim->y0 = prim->y1 = self->posY.i.hi + 0xFFE8;
            }
            prim->y2 = prim->y3 = prim->y0 + 0x10;
            prim->priority = 0xA8;
            prim->drawMode = DRAW_UNK02;
            prim = prim->next;
        }
        self->ext.breakableNo2.unk80 = 0x20;
        self->step++;
        break;

    case STEP_TIMER:
        if (!--self->ext.breakableNo2.unk80) {
            self->step++;
        }
        break;

    case STEP_REVEAL:
        self->animCurFrame = 0;
        g_CastleFlags[NO2_SECRET_WALL_OPEN] |= 1;

        g_api.RevealSecretPassageAtPlayerPositionOnMap(NO2_SECRET_WALL_OPEN);

        for (i = 0; i < 10; i++) {
            tileIdx = D_us_80180DEC[i];
            g_Tilemap.fg[tileIdx] = D_us_80180E00[i];
        }
        prim = self->ext.breakableNo2.unk7C;
        for (i = 0; i < 8; i++) {
            UnkPolyFunc2(prim);
            prim->next->x1 = self->posX.i.hi - 8 + ((i % 2) * 0x10);
            prim->next->y0 = self->posY.i.hi - 24 + ((i / 2) * 0x10);
            prim->next->r3 = i;
            prim = prim->next;
            prim = prim->next;
        }
        tempEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (tempEntity != NULL) {
            CreateEntityFromEntity(E_EXPLOSION, self, tempEntity);
            tempEntity->posY.i.hi += 0x20;
            tempEntity->params = 0x13;
            tempEntity->params += 0xAA00;
        }
        for (i = 0; i < 8; i++) {
            tempEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (tempEntity != NULL) {
                CreateEntityFromEntity(E_INTENSE_EXPLOSION, self, tempEntity);
                tempEntity->posX.i.hi += 0xF - (Random() & 0x1F);
                tempEntity->posY.i.hi += 0xF - (Random() & 0x1F);
                tempEntity->params = 0x10;
                tempEntity->params += 0xAA00;
            }
        }
        g_api.PlaySfx(SFX_WALL_DEBRIS_B);
        self->ext.breakableNo2.unk80 = 0x180;
        self->step++;
        break;

    case STEP_FINALIZE:
        prim = self->ext.breakableNo2.unk7C;
        while (prim != NULL) {
            if (prim->p3 & 8) {
                func_us_801B59C4(prim);
            }
            prim = prim->next;
        }
        if (!--self->ext.breakableNo2.unk80) {
            g_CastleFlags[NO2_SECRET_WALL_OPEN] |= 2;
            DestroyEntity(self);
        }
        break;
    }
}


INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801AC54C_from_bo0);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

static void func_us_801AC73C_from_bo0(Primitive* prim) {
    s32 x, y;

    if (!prim->g3) {
        prim->u0 = 1;
        prim->v0 = 1;
        prim->r0 = 0x80;
        prim->g0 = 0x80;
        prim->b0 = 0xC0;
        prim->drawMode = DRAW_UNK02;
        prim->x0 = g_CurrentEntity->posX.i.hi;
        prim->y0 = g_CurrentEntity->posY.i.hi + 8;
        prim->x1 = 0;
        prim->y1 = 0;
        LOW(prim->x2) = 0x7000 - ((Random() & 7) << 0xD);
        LOW(prim->x3) = 0x7000 - ((Random() & 7) << 0xD);
        prim->g3 = 1;
        prim->r3 = 0x20;
    }
#ifdef VERSION_US
    x = (prim->x0 << 0x10) + (u16)prim->x1;
#else
    x = (prim->x0 << 0x10) + prim->x1;
#endif
    x += LOW(prim->x2);
    prim->x0 = HIHU(x);
    prim->x1 = LOHU(x);
#ifdef VERSION_US
    y = (prim->y0 << 0x10) + (u16)prim->y1;
#else
    y = (prim->y0 << 0x10) + prim->y1;
#endif
    y += LOW(prim->x3);
    prim->y0 = HIH(y);
    prim->y1 = LOH(y);
    LOW(prim->x3) += 0x2000;
    prim->r3 -= 1;
    if (!prim->r3) {
        prim->g3 = 0;
        prim->drawMode = DRAW_HIDE;
        prim->p3 = 0;
    }
}



INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801B68EC_from_no2);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", EntityPrisoner);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801B5EE4);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", EntitySealedDoor);
