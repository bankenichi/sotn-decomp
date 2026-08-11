// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

extern EInit RNO0_EInitSpawner;

// Needed: 801CC750 installs this as a pfnUpdate below, before it is defined.
void func_us_801CC8F8_from_no0(Entity* self);

/* TRANSPLANTED, no model call. Both functions in this file were ported from
 * NO0's copies in src/st/no0/4C750.c by automation/transplant.py --auto, which
 * derives its substitutions from an asm-vs-asm diff rather than being told
 * them. For 801CC750 that diff was:
 *
 *     D_us_80180A88     -> RNO0_EInitSpawner
 *     func_us_801CC8F8  -> func_us_801CC8F8_from_no0
 *     0xC0 <-> 0xE0, 0x91 -> 0x5F, 0xC1 -> 0x3F, 0x8E -> 0x6A
 *
 * The four constants are the inverted castle: the sprite is mirrored, so its
 * U coordinates swap and its Y coordinates flip. Verified by the oracle, not
 * by inspection -- both overlays' artifacts hash correctly with this applied.
 */
void func_us_801CC750_from_no0(Entity* self) {
    Entity* entityPtr;
    s16 i;
    Primitive* prim;
    s32 primIndex;

    if (self->step) {
        return;
    }

    InitializeEntity(RNO0_EInitSpawner);
    primIndex = g_api.AllocPrimitives(PRIM_GT4, 9);
    if (primIndex != -1) {
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->flags |= FLAG_HAS_PRIMS;
        for (i = -0x10; prim != NULL; i += 0x1E) {
            prim->tpage = 0xF;
            prim->clut = 0x2A;
            prim->u0 = prim->u2 = 0xE0;
            prim->u1 = prim->u3 = 0xC0;
            prim->v0 = prim->v1 = 0x80;
            prim->v2 = prim->v3 = 0xB0;
            prim->x0 = prim->x2 = i;
            prim->x1 = prim->x3 = i + 0x20;
            prim->y0 = prim->y1 = 0x5F;
            prim->y2 = prim->y3 = 0x3F;
            prim->priority = 0;
            prim->drawMode = DRAW_DEFAULT;
            prim = prim->next;
        }
    }

    entityPtr = self + 1;

    for (i = -0x10; i < 0x130; i += 0x60) {
        DestroyEntity(entityPtr);
        entityPtr->entityId = E_UNK_16;
        entityPtr->pfnUpdate = func_us_801CC8F8_from_no0;
        entityPtr->posY.i.hi = 0x6A;
        entityPtr->posX.i.hi = i;
        entityPtr++;
    }
}

#define g_EInitCommon OVL_EXPORT(EInitCommon)
extern EInit RNO0_EInitCommon;

void func_us_801CC8F8_from_no0(Entity* self) {
    if (!self->step) {
        InitializeEntity(g_EInitCommon);
        self->animSet = ANIMSET_OVL(2);
        self->animCurFrame = 3;
        self->zPriority = g_unkGraphicsStruct.g_zEntityCenter - 0x54;
        self->unk68 = 0xC0;
        self->flags &= ~FLAG_UNK_20000000;
        return;
    }

    if (self->posX.i.hi < -0x40) {
        self->posX.i.hi += 0x180;
    }

    if (self->posX.i.hi > 0x140) {
        self->posX.i.hi -= 0x180;
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/e_background_pillars", func_us_801CC9B4_from_no0);
