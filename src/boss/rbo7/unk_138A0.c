// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo7.h"

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", EntityBreakable);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801BAB18_from_bo0);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_80192B38_from_rbo3);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801940B4);

INCLUDE_ASM("boss/rbo7/nonmatchings/unk_138A0", func_us_801957C0);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define E_ID(name) E_##name
extern EInit D_us_80180444;
extern u8 D_us_8018074C[];
extern u8 D_us_80180764[];

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
