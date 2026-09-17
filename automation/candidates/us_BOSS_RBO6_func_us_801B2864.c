/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:BOSS/RBO6:func_us_801B2864
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/boss/rbo6/unk_30D68.c
   target : src/boss/rbo6/unk_30D68.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo6.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
s32 Random();
int rsin(int a);
int rcos(int a);
void MoveEntity();
u8 AnimateEntity(u8 frames[], Entity* entity);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_30D68", EntityBackgroundVortex);

INCLUDE_RODATA("boss/rbo6/nonmatchings/unk_30D68", D_us_8019D0AC);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_30D68", func_us_801B1738);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitInteractable;
extern s32 D_us_80181488[]; /* retained BOSS/RBO6 data asm/us/boss/rbo6/data/1460.data.s, size 0x4 */
extern s32 D_us_80181648[]; /* retained BOSS/RBO6 data asm/us/boss/rbo6/data/1460.data.s, size 0x1c */

void func_us_801B2864(Entity* self) {
    extern u16 g_EInitInteractable;
    extern s32 D_us_80181488;
    extern u8 D_us_80181648;
    u16 angle;

    switch (self->step) {
    case 0:
        InitializeEntity(&g_EInitInteractable);
        self->palette = 0x2E5;
        self->animSet = 0xE;
        self->unk5A = 0x79;
        self->drawFlags = ENTITY_ROTATE;
        self->flags |= FLAG_UNK_10000;
        self->blendMode = BLEND_QUARTER | BLEND_TRANSP;
        self->flags &= ~FLAG_POS_CAMERA_LOCKED;
        self->facingLeft = Random() & 1;
        angle = self->rotate;
        if (self->facingLeft != 0) {
            self->rotate = -angle;
        }
        self->velocityX = rsin((s32)(s16)angle) * 0x28;
        self->velocityY = -(rcos((s32)(s16)angle) * 0x28);
        self->scaleX = 0xE0;
        self->drawFlags |= ENTITY_SCALEY | ENTITY_SCALEX;
        self->scaleY = 0x140;
        if (D_us_80181488 != 0) {
            self->scaleX = 0x120;
            self->scaleY = 0x120;
        }
        /* fall through */
    case 1:
        MoveEntity();
        if (AnimateEntity(&D_us_80181648, self) == 0) {
            DestroyEntity(self);
        }
        break;
    }
}
