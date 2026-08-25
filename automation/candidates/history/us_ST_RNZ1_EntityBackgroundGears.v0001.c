/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityBackgroundGears
   source : upstream/master:src/st/nz1/e_bg_gears.c
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
void DestroyEntity(Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int AnimateEntity();
/* End permuter-seed writer declarations. */

void EntityBackgroundGears(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s32 i, j;
    s32 posX;
    s32 posY;
    s32 u;
    s32 v;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        self->posX.i.hi = 0;
        self->posY.i.hi = 0;
        self->unk68 = 0x80;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 9);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        self->ext.prim = prim;
        while (prim != NULL) {
            prim->tpage = 0xF;
            prim->clut = 8;
            prim->priority = 0x20;
            prim->drawMode = DRAW_UNK02;
            prim = prim->next;
        }
         

    case 1:
        AnimateEntity(D_us_80180FB0, self);

        posX = self->posX.i.hi;
        posX &= 0x7F;
        posX -= 128;
        posY = self->posY.i.hi;
        posY &= 0x7F;
        posY -= 128;
        u = 0;
        v = 0;
        if (self->animCurFrame == 2) {
            u = 128;
        }
        if (self->animCurFrame == 3) {
            v = 128;
        }

        prim = self->ext.prim;
        for (i = 0; i < 3; i++) {
            for (j = 0; j < 3; j++) {
                prim->x0 = prim->x2 = posX + (j * 128);
                prim->x1 = prim->x3 = posX + (j * 128) + 128;
                prim->y0 = prim->y1 = posY + (i * 128);
                prim->y2 = prim->y3 = posY + (i * 128) + 128;
                prim->u0 = prim->u2 = u;
                prim->u1 = prim->u3 = u + 127;
                prim->v0 = prim->v1 = v;
                prim->v2 = prim->v3 = v + 127;
                prim->drawMode = DRAW_DEFAULT;
                prim = prim->next;
            }
        }
        while (prim != NULL) {
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }
        break;
    }
}

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysLarge);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearHorizontal);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearVertical);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityGearSidewaysSmall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWallGear);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretAreaDoor);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWall);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityBreakableWallPartial);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntitySecretWallDebris);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", func_us_801A8F7C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_276A8", EntityWaterForeground);
