/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:BOSS/RBO7:EntityHarpyKick
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/boss/rbo7/unk_138A0.c
   target : src/boss/rbo7/unk_138A0.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo7.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", EntityBreakable);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801BAB18_from_bo0);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_80192B38_from_rbo3);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801940B4);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801957C0);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180444;
extern u8 D_us_8018074C[]; /* retained BOSS/RBO7 data asm/us/boss/rbo7/data/568.data.s, size 0x18 */
extern u8 D_us_80180764[]; /* retained BOSS/RBO7 data asm/us/boss/rbo7/data/568.data.s, size 0x8 */

void EntityHarpyKick(Entity* self) {
    s32 animFrame;
    s8* hitbox;
    Entity* harpy;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180444);
        /* fall through */
    case 1:
        harpy = self - 1;
        self->facingLeft = harpy->facingLeft;
        self->posX.val = harpy->posX.val;
        self->posY.val = harpy->posY.val;

        animFrame = harpy->animCurFrame;
        animFrame -= 0x23;
        if (animFrame < 0) {
            animFrame = 0;
        }

        hitbox = D_us_8018074C;
        animFrame = D_us_80180764[animFrame];
        hitbox += animFrame * 4;
        self->hitboxOffX = *hitbox++;
        self->hitboxOffY = *hitbox++;
        self->hitboxWidth = *hitbox++;
        self->hitboxHeight = *hitbox++;

        if (harpy->entityId != E_ID(UNK_19)) {
            DestroyEntity(self);
        }
        break;
    }
}


INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_80195A8C);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_80195D04);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", EntityCtulhuDeath);
