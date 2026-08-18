// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

// EntitySlograSpear and EntitySlograSpearProjectile each failed to build on
// one of these names. D_us_80180600 is defined by THIS overlay at
// src/st/rchi/e_init.c:94; g_Entities_224 is the shared src/st/e_imp.h:9.
extern EInit D_us_80180600;
extern Entity g_Entities_224[];

INCLUDE_ASM("st/rchi/nonmatchings/e_slogra", EntitySlogra);

#define ENTITY_ROTATE 4
#define FLAG_DESTROY_IF_OUT_OF_CAMERA 2147483648
#define SFX_ARROW_SHOT_A 1573
extern s8 D_us_801815BC[];
extern u8 D_us_801815F4[];
extern EInit D_us_80180600;
extern struct Entity;
void InitializeEntity(u16 arg0[]);

void EntitySlograSpear(Entity* self) {
    s32 animFrame;
    Entity* slogra;
    s8* hitbox;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180600);

    case 1:
        slogra = self - 1;
        self->facingLeft = slogra->facingLeft;
        self->posX.i.hi = slogra->posX.i.hi;
        self->posY.i.hi = slogra->posY.i.hi;
        animFrame = slogra->animCurFrame;
        hitbox = D_us_801815BC;
        hitbox += 4 * D_us_801815F4[animFrame];
        self->hitboxOffX = *hitbox++;
        self->hitboxOffY = *hitbox++;
        self->hitboxWidth = *hitbox++;
        self->hitboxHeight = *hitbox++;
        if (slogra->ext.GS_Props.nearDeath) {
            self->step++;
        }
        break;

    case 2:
        switch (self->step_s) {
        case 0:
            self->drawFlags = ENTITY_ROTATE;
            self->hitboxState = 0;
            if (self->facingLeft) {
                self->velocityX = FIX(-2.25);
            } else {
                self->velocityX = FIX(2.25);
            }
            self->velocityY = FIX(-4);
            self->animCurFrame = 35;
            self->flags |= FLAG_DESTROY_IF_OUT_OF_CAMERA;
            self->step_s++;

        case 1:
            MoveEntity();
            self->velocityY += FIX(0.15625);
            self->rotate += 0x80;
            if (!(self->rotate & 0xFFF)) {
                PlaySfxPositional(SFX_ARROW_SHOT_A);
            }
        }
    }
}

INCLUDE_ASM("st/rchi/nonmatchings/e_slogra", EntitySlograSpearProjectile);
