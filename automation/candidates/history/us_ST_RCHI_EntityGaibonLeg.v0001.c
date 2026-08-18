/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RCHI:EntityGaibonLeg
   attempt: 3/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/st/rchi/nonmatchings/e_gaibon/EntityGaibonLeg.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

INCLUDE_ASM("st/rchi/nonmatchings/e_gaibon", EntityGaibon);

extern EInit g_EInitGaibon;
extern void DestroyEntity(Entity* self);

void EntityGaibonLeg(Entity* self) {
    Entity* parent;
    s16 parentAnimFrame;

    if (self->step == 0) {
        InitializeEntity(&g_EInitGaibon);
        self->hitboxState = 0;
    }

    parent = self - 1;

    self->palette = parent->palette;
    self->facingLeft = parent->facingLeft;
    parentAnimFrame = parent->animCurFrame;
    self->animCurFrame = 0;
    self->posX.i.hi = parent->posX.i.hi;
    self->posY.i.hi = parent->posY.i.hi;

    if ((u32)(parentAnimFrame - 0x20) < 3) {
        self->animCurFrame = 0x26;
    } else if (parentAnimFrame == 0x23) {
        self->animCurFrame = 0x27;
    } else if ((u32)(parentAnimFrame - 0x24) < 2) {
        self->animCurFrame = 0x28;
    }

    if (parent->entityId != 0x19) {
        DestroyEntity(self);
    }
}

INCLUDE_ASM("st/rchi/nonmatchings/e_gaibon", EntitySmallGaibonProjectile);

INCLUDE_ASM("st/rchi/nonmatchings/e_gaibon", EntityLargeGaibonProjectile);
