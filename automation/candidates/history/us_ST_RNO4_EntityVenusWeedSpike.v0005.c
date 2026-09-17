/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNO4:EntityVenusWeedSpike
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/e_venus_weed.h
   target : src/st/rno4/e_blue_venus_weed.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno4.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
int FntPrint(const char* id, ...);
/* End permuter-seed writer declarations. */

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define LOH(x) (*(s16*)&(x))
#define SPIKE_SPRITES D_us_801BE9C4
extern signed short* SPIKE_SPRITES[];

static Primitive* SetupPrimsForEntitySpriteParts(
    Entity* entity, Primitive* prim) {
    s16 y;
    s32 spritePartCount;
    s16 x;
    u8 spriteU0;
    u8 spriteV0;
    s16* spriteData;
    s32 i;
    u8 spriteU1;
    s16 spriteDestX;
    s16 spriteDestY;
    s16 spriteDestW;
    s16 spriteDestH;
    s16 spriteFlags;
    u8 spriteV1;
    s32 xFlip;

    spriteData = SPIKE_SPRITES[entity->animCurFrame];
    spritePartCount = *spriteData;
    spriteData++;

    for (i = 0; i < spritePartCount; i++, spriteData += 11) {
        spriteFlags = spriteData[0];
        spriteDestX = spriteData[1];
        spriteDestY = spriteData[2];
        spriteDestW = spriteData[3];
        spriteDestH = spriteData[4];

        // Adjust sprite position to respect sprite flags
        if (spriteFlags & 4) {
            spriteDestW -= 1;
            if (spriteFlags & 2) {
                spriteDestX += 1;
            }
        }
        if (spriteFlags & 8) {
            spriteDestH -= 1;
            if (spriteFlags & 1) {
                spriteDestY += 1;
            }
        }
        if (spriteFlags & 0x10) {
            spriteDestW -= 1;
            if (!(spriteFlags & 2)) {
                spriteDestX += 1;
            }
        }
        if (spriteFlags & 0x20) {
            spriteDestH -= 1;
            if (!(spriteFlags & 1)) {
                spriteDestY += 1;
            }
        }

        // Calculate sprite position to respect facing
        x = entity->posX.i.hi;
        y = entity->posY.i.hi;
        if (entity->facingLeft) {
            x -= spriteDestX;
        } else {
            x += spriteDestX;
        }
        y += spriteDestY;

        // Set sprite position to respect the above, plus sprite dimensions
        if (entity->facingLeft) {
            LOH(prim->x0) = x - spriteDestW + 1;
            LOH(prim->y0) = y;
            LOH(prim->x1) = x + 1;
            LOH(prim->y1) = y;
            LOH(prim->x2) = x - spriteDestW + 1;
            LOH(prim->y2) = y + spriteDestH;
            LOH(prim->x3) = x + 1;
            LOH(prim->y3) = y + spriteDestH;
        } else {
            LOH(prim->x0) = x;
            LOH(prim->y0) = y;
            LOH(prim->x1) = x + spriteDestW;
            LOH(prim->y1) = y;
            LOH(prim->x2) = x;
            LOH(prim->y2) = y + spriteDestH;
            LOH(prim->x3) = x + spriteDestW;
            LOH(prim->y3) = y + spriteDestH;
        }

        // Entity-relative clut
        prim->clut = entity->palette + spriteData[5];

        spriteU0 = spriteData[7];
        spriteV0 = spriteData[8];
        spriteU1 = spriteData[9];
        spriteV1 = spriteData[10];

        // Adjust sprite UVs to respect sprite flags
        if (spriteFlags & 4) {
            spriteU1--;
        }
        if (spriteFlags & 8) {
            spriteV1--;
        }
        if (spriteFlags & 0x10) {
            spriteU0++;
        }
        if (spriteFlags & 0x20) {
            spriteV0++;
        }

        // Set sprite UVs to respect the above, plus facing
        xFlip = (spriteFlags & 2) ^ entity->facingLeft;
        if (!xFlip) {
            if (!(spriteFlags & 1)) {
                prim->u0 = spriteU0;
                prim->v0 = spriteV0;
                prim->u1 = spriteU1;
                prim->v1 = spriteV0;
                prim->u2 = spriteU0;
                prim->v2 = spriteV1;
                prim->u3 = spriteU1;
                prim->v3 = spriteV1;
            } else {
                prim->u0 = spriteU0;
                prim->v0 = spriteV1 - 1;
                prim->u1 = spriteU1;
                prim->v1 = spriteV1 - 1;
                prim->u2 = spriteU0;
                prim->v2 = spriteV0 - 1;
                prim->u3 = spriteU1;
                prim->v3 = spriteV0 - 1;
            }
        } else {
            if (!(spriteFlags & 1)) {
                prim->u0 = spriteU1 - 1;
                prim->v0 = spriteV0;
                prim->u1 = spriteU0 - 1;
                prim->v1 = spriteV0;
                prim->u2 = spriteU1 - 1;
                prim->v2 = spriteV1;
                prim->u3 = spriteU0 - 1;
                prim->v3 = spriteV1;
            } else {
                prim->u0 = spriteU1 - 1;
                prim->v0 = spriteV1 - 1;
                prim->u1 = spriteU0 - 1;
                prim->v1 = spriteV1 - 1;
                prim->u2 = spriteU1 - 1;
                prim->v2 = spriteV0 - 1;
                prim->u3 = spriteU0 - 1;
                prim->v3 = spriteV0 - 1;
            }
        }

        prim->tpage = 0x14;
        // Entity-relative z priority
        prim->priority = entity->zPriority + 1;

        // Next!
        prim = prim->next;
    }
    return prim;
}


INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeed);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedFlower);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedTendril);

INCLUDE_ASM("st/rno4/nonmatchings/e_blue_venus_weed", EntityVenusWeedDart);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitVenusWeedFlower;
extern GameApi g_api;
extern Primitive g_PrimBuf[];

void EntityVenusWeedSpike(Entity* self) {
    const int SpikeParts = 5;

    enum Step {
        INIT = 0,
        EXTEND = 1,
    };

    Primitive* prim;
    Primitive* primItr;
    Primitive* primNext;
    s32 primIdx;
    Entity* entity;
    s16 clut;

    switch (self->step) {
    case INIT:
        InitializeEntity(g_EInitVenusWeedFlower);

        self->flags |= FLAG_UNK_2000 | FLAG_UNK_00200000;
        self->hitboxState = 0;
        self->palette = PAL_FLAG(SPIKE_CLUT_START);

        primIdx = g_api.AllocPrimitives(PRIM_GT4, SpikeParts);
        if (primIdx == -1) {
            DestroyEntity(self);
            break;
        } else {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIdx;
            prim = &g_PrimBuf[primIdx];
            self->ext.venusWeedSpike.firstPart = prim;

            entity = self->ext.venusWeedSpike.flower;
            entity--; // Root
            prim = self->ext.venusWeedSpike.firstPart;

            // Draw sprite parts
            prim = SetupPrimsForEntitySpriteParts(entity, prim);
            // Above returns the following prim

            // Copy prims to a later index (while maintaining linked list order)
            for (primItr = entity->ext.venusWeedSpike.firstPart;
                 primItr != NULL; primItr = primItr->next, prim = primNext) {
                primNext = prim->next;

                *prim = *primItr;
                prim->next = primNext;
                prim->priority = primItr->priority + 1;
            }
        }

        // Update to match flower
        entity = entity + 1; // Flower
        self->animCurFrame = entity->animCurFrame;
        self->zPriority = entity->zPriority + 1;
        // Fallthrough
    case EXTEND:
        clut = self->palette & 0xFFF;
#if defined(BLUE)
        FntPrint("color %x\n", self->palette);
#endif
        prim = self->ext.venusWeedSpike.firstPart;
        while (prim != NULL) {
            prim->clut = clut;
            prim->drawMode = DRAW_UNK02;

            prim = prim->next;
        }

        // Update to match flower
        entity = self->ext.venusWeedSpike.flower;
        self->animCurFrame = entity->animCurFrame;
        self->palette++;
        clut = self->palette & 0xFFF;
        if (clut > SPIKE_CLUT_END) {
            DestroyEntity(self);
        } else {
            if (entity->entityId != E_VENUS_WEED_FLOWER) {
                DestroyEntity(self);
            }
        }
        break;
    }
}
