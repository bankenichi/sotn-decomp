/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO2:func_us_801AC54C_from_bo0
   source : upstream/master:src/boss/bo0/e_secrets.c
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
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int UnkPolyFunc2();
extern int func_us_801B59C4();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801AB9EC_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801B5FB8_from_no2);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitEnvironment;

void func_us_801AC54C_from_bo0(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s32 i;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitEnvironment);
        self->hitboxState = 0;
        self->animCurFrame = 0;
        break;

    case 1:
        if (g_CastleFlags[NO2_SECRET_WALL_OPEN] & 2) {
            DestroyEntity(self);
            return;
        }
        if (g_CastleFlags[NO2_SECRET_WALL_OPEN]) {
            g_CastleFlags[NO2_SECRET_WALL_OPEN] |= 2;
        }
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 8);
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
            DestroyEntity(self);
            return;
        }
        prim = self->ext.breakableNo2.unk7C;
        for (i = 0; i < 4; i++) {
            UnkPolyFunc2(prim);
            prim->next->x1 = self->posX.i.hi;
            prim->next->y0 = self->posY.i.hi;
            prim->next->r3 = i + 8;
            prim = prim->next;
            prim = prim->next;
        }
        self->step++;
        break;

    case 2:
        i = 1;
        prim = self->ext.breakableNo2.unk7C;
        while (prim != NULL) {
            if (prim->p3 & 8) {
                i = 0;
                func_us_801B59C4(prim);
            }
            prim = prim->next;
        }
        if (i != 0) {
            DestroyEntity(self);
            return;
        }
        break;
    }
}

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801AC73C_from_bo0);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801B68EC_from_no2);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", EntityPrisoner);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", func_us_801B5EE4);

INCLUDE_ASM("st/rno2/nonmatchings/unk_3459C", EntitySealedDoor);
