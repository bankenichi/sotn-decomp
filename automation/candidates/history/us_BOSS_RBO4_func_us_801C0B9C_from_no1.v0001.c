/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO4:func_us_801C0B9C_from_no1
   source : upstream/master:src/st/no1/unk_3FA34.c
   target : src/boss/rbo4/unk_17804.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo4.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void CreateEntityFromCurrentEntity(u16, Entity*);
void MoveEntity();
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int AnimateEntity();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", EntityBreakable);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_80197938);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_8019818C);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_8019846C);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_80192B38_from_rbo3);

INCLUDE_ASM("boss/rbo4/nonmatchings/unk_17804", func_us_80198A18);

void func_us_801C0B9C_from_no1(Entity* self) {
    Entity* nextEntity;
    s32 i;
    s32 params;
    s32 fgIndex;
    s32 posX;
    s32 posY;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_801809C8);
        self->animCurFrame = 0;
        self->ext.et_801C0B9C.unk84 = 0;
        if (!self->params) {
            nextEntity = self + 1;
            for (i = 1; i < 4; i++, nextEntity++) {
                CreateEntityFromCurrentEntity(E_ID(ID_57), nextEntity);
                nextEntity->params = i;
            }

            for (i = 0; i < 4; i++, nextEntity++) {
                CreateEntityFromCurrentEntity(E_ID(ID_57), nextEntity);
                nextEntity->params = i + 0x100;
            }
        }
        self->posY.i.hi = 0x68 - g_Tilemap.scrollY.i.hi;
        if (self->params & 0x100) {
            self->posX.i.hi = 0x1F0 - g_Tilemap.scrollX.i.hi;
        } else {
            self->posX.i.hi = 0x10 - g_Tilemap.scrollX.i.hi;
        }
        break;
    case 2:
        if (!AnimateEntity(D_us_80181A04, self)) {
            self->velocityY = FIX(4);
            self->step++;
        }
        break;
    case 3:
        MoveEntity();
        self->velocityY += FIX(0.125);

        params = self->params & 0xFF;
        posY = (((3 - params) * 0x10) + 0x60) + g_Tilemap.scrollY.i.hi;
        if (posY < self->posY.i.hi) {
            if (params != 4) {
                nextEntity = self + 1;
                nextEntity->ext.et_801C0B9C.unk84 = 1;
            }
            self->posY.i.hi = posY;
            fgIndex = 0xC0;
            if (self->params & 0x100) {
                g_api.PlaySfx(SFX_EXPLODE_FAST_A);
                fgIndex = 0xDE;
            }
            fgIndex += ((3 - params) << 5);
            (&g_Tilemap.fg[fgIndex])[0] = D_us_80181A0C[7 - params][0];
            (&g_Tilemap.fg[fgIndex])[1] = D_us_80181A0C[7 - params][1];
            self->velocityY = 0;
            self->step++;
        }
        break;
    case 4:
        if (g_pads[0].pressed & PAD_UP) {
            self->step++;
        }
        break;
    case 5:
        fgIndex = 0xC0;
        params = self->params & 0xFF;
        if (self->params & 0x100) {
            fgIndex = 0xDE;
        }

        fgIndex += ((3 - params) << 5);
        (&g_Tilemap.fg[fgIndex])[0] = D_us_80181A0C[3 - params][0];
        (&g_Tilemap.fg[fgIndex])[1] = D_us_80181A0C[3 - params][1];
        self->step++;
    case 7:
        break;
    case 6:
        if (self->params & 0x100) {
            self->velocityX = FIX(0.5);
        } else {
            self->velocityX = FIX(-0.5);
        }
        MoveEntity();
        posX = g_Tilemap.scrollX.i.hi + self->posX.i.hi;
        if (posX < -0x20 || posX > 0x220) {
            self->step++;
        }
        break;
    }
}
