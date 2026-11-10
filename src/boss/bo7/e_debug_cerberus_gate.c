// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo7.h"

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
s32 Random(void);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;

extern EInit D_us_80180454;
extern s32 D_us_80180848;
extern Primitive* FindFirstUnkPrim(Primitive* prim);
extern void PlaySfxPositional(s32 arg0);

// E_CERBERUS_GATE_DEBUG
// params: True to use version for right side
// func_8019CBA8
// https://decomp.me/scratch/BFa12
// PSP:func_psp_0924B458:Match
// PSP:https://decomp.me/scratch/IWYbc
// BO7's copy diverges from the CHI donor: a seventh step waits
// on bit 0x10 of the D_us_80180848 debug word, INIT falls under
// the prim loop straight into the flag wait (bit 0x1 starts the
// fall), each INIT arm places its own posX (screen-x 0x1FA or 6
// minus scrollX, tileIdx ordered before the frame), a failure
// to allocate primitives resets the step, DROP adds an impact
// SFX at the bounce, RAISE drops the g_Timer & 7 trail guard,
// and the destroy trail is folded into WAIT_TO_DESTROY, which
// then steps past its own switch instead of destroying itself.
void EntityCerberusGateDebug(Entity* self) {
    typedef enum Step {
        INIT = 0,
        WAIT_FOR_INPUT = 1,
        DROP = 2,
        ADD_COLLISION = 3,
        WAIT_FOR_FLAG = 4,
        RAISE = 5,
        WAIT_TO_DESTROY = 6,
    };

    s32 tileIdx;
    s32 primIdx;
    Primitive* prim;
    Collider collider;
    Entity* entity;

    s32 i;
    s16 x;
    s16 y;

    switch (self->step) {
    case INIT:
        InitializeEntity(D_us_80180454);
        self->zPriority = 0x6A;
        if (self->params) {
            tileIdx = 0xDF;
            self->animCurFrame = 6;
            self->posX.i.hi = 0x1FA - g_Tilemap.scrollX.i.hi;
        } else {
            tileIdx = 0xC0;
            self->animCurFrame = 5;
            self->posX.i.hi = 6 - g_Tilemap.scrollX.i.hi;
        }
        for (i = 0; i < 4; tileIdx += 0x20, i++) {
            g_Tilemap.fg[tileIdx] = 0x32E;
        }
        primIdx = g_api.AllocPrimitives(PRIM_GT4, 16);
        if (primIdx == -1) {
            self->step = INIT;
            return;
        }

        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIdx;
        prim = &g_PrimBuf[primIdx];
        self->ext.debugCerberusGate.prim = prim;

        prim->tpage = 0xF;
        prim->clut = 0x1B;
        if (self->params) {
            prim->u0 = prim->u2 = 0xE3;
            prim->u1 = prim->u3 = 0xD3;
        } else {
            prim->u0 = prim->u2 = 0xD4;
            prim->u1 = prim->u3 = 0xE4;
        }
        prim->v0 = prim->v1 = 0x9C;
        prim->v2 = prim->v3 = 0xDC;

        if (self->params) {
            x = 0x1F0;
        } else {
            x = 0;
        }
        x = x - g_Tilemap.scrollX.i.hi;
        prim->x0 = prim->x2 = x;
        prim->x1 = prim->x3 = x + 0x10;

        prim->y0 = prim->y1 = 0x1C;
        prim->y2 = prim->y3 = 0x5C;
        prim->priority = 0x6B;
        prim->drawMode = DRAW_UNK02;
        prim = prim->next;

        while (prim != NULL) {
            prim->type = PRIM_TILE;
            prim->u0 = prim->v0 = 1;
            prim->r0 = 0x20;
            prim->g0 = 0x40;
            prim->b0 = 0x20;
            prim->priority = 0x6C;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
        /* fallthrough */
    case WAIT_FOR_INPUT:
        if (!(D_us_80180848 & 1)) {
            return;
        }
        self->step++;
        return;

    case DROP:
        self->posY.val += self->velocityY;
        self->velocityY += FIX(0.5);
        x = self->posX.i.hi;
        y = self->posY.i.hi + 0x22;
        if (self->posY.i.hi <= 0x60) {
            return;
        }
        g_api.CheckCollision(x, y, &collider, 0);
        if (collider.effects == EFFECT_NONE) {
            return;
        }

        self->posY.i.hi += collider.unk18;
        self->velocityY = -self->velocityY;
        self->velocityY /= 4;
        PlaySfxPositional(SFX_EXPLODE_B);

        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_INTENSE_EXPLOSION, self, entity);
            entity->posX.i.hi += -8 + (Random() & 7) * 2;
            entity->posY.i.hi += 0x20;
            entity->params = 0x10;
        }
        if (self->velocityY > FIX(-0.125)) {
            self->step++;
        }
        return;

    case ADD_COLLISION:
        if (self->params) {
            tileIdx = 0xDF;
        } else {
            tileIdx = 0xC0;
        }
        for (i = 0; i < 4; tileIdx += 0x20, i++) {
            g_Tilemap.fg[tileIdx] = 0x3A1;
        }
        self->step++;
        return;

    case WAIT_FOR_FLAG:
        if (D_us_80180848 & 0x10) {
            self->step++;
        }
        return;

    case RAISE:
        self->posY.val -= FIX(0.25);

        if (g_Timer % 2) {
            prim = self->ext.debugCerberusGate.prim;
            prim = prim->next;
            prim = FindFirstUnkPrim(prim);
            if (prim != NULL) {
                prim->p3 = 1;

                x = (self->posX.i.hi + (Random() & 0xF)) - 8;
                y = 0x5C;
                prim->x0 = x;
                prim->y0 = y;
                prim->drawMode = DRAW_UNK02;
            }
        }

        tileIdx = 0x120;
        y = (0x7A - self->posY.i.hi) >> 4;
        if (self->params) {
            tileIdx = 0x13F;
        }

        for (i = 0; i < y; tileIdx -= 0x20, i++) {
            g_Tilemap.fg[tileIdx] = 0x32E;
        }
        self->ext.debugCerberusGate.timer = 0x20;
        if (self->posY.i.hi < 0x3A) {
            self->step++;
        }
        /* fallthrough */
    case WAIT_TO_DESTROY:
        prim = self->ext.debugCerberusGate.prim;
        while (prim != NULL) {
            if (prim->p3) {
                prim->y0 += 2;
                if (prim->y0 > 0xA0) {
                    prim->drawMode = DRAW_HIDE;
                    prim->p3 = 0;
                }
            }
            prim = prim->next;
        }
        if (--self->ext.debugCerberusGate.timer) {
            return;
        }
        self->step++;
        return;
    }
}
