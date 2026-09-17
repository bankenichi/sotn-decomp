/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNO2:func_us_801C4EA8
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rno2/unk_439A4.c
   target : src/st/rno2/unk_439A4.c
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
int rsin(int a);
int rcos(int a);
void MoveEntity();
u8 AnimateEntity(u8 frames[], Entity* entity);
void DestroyEntity(Entity*);
s32 Random();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C39A4);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4960);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4C0C);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitParticle;

void func_us_801C4EA8(Entity* self) {
    extern u8 g_Unk2EAnim;



    s32 angle;


    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitParticle);

        angle = self->rotate;

        self->animSet = 0xE;
        self->unk5A = 0x5C;
        self->palette = 0x2EE;
        self->drawFlags = ENTITY_ROTATE | ENTITY_SCALEX;
        self->scaleX = 0x60;
        self->scaleY = 0xC0;
        self->blendMode = BLEND_QUARTER | BLEND_TRANSP;





        self->velocityX = rsin(angle) << 4;
        self->velocityY = -(rcos(angle) << 4);

    case 1:
        MoveEntity();
        if (AnimateEntity(&g_Unk2EAnim, self) == 0) {
            DestroyEntity(self);
        }
        break;
    }
}


INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasuman);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasumanFeatherAttack);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasumanOrbAttack);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasumanRavenAttack);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit D_us_8018094C;

void EntityKarasumanFeather(Entity* self) {
    s16 angle;
    s32 scale;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_8018094C);
        self->animCurFrame = 63;
        self->drawFlags = ENTITY_ROTATE;
        self->facingLeft = Random() & 1;
        scale = (Random() & 0x1F) + 0x10;
        angle = (Random() * 6) + FLT(9.0 / 16.0);

        self->velocityX = scale * rcos(angle);
        self->velocityY = scale * rsin(angle);
        self->posX.val += 16 * self->velocityX;
        self->posY.val += 16 * self->velocityY;

        self->rotate = angle;
        self->ext.karasuman.timer = 64;


    case 1:
        MoveEntity();
        self->velocityX -= self->velocityX / 16;
        self->velocityY -= self->velocityY / 16;

        self->rotate += 64;
        if (!--self->ext.karasuman.timer) {
            self->velocityX = 0;
            self->step++;
        }
        break;

    case 2:
        MoveEntity();
        self->rotate += 32;
        if (self->velocityY < FIX(1.5)) {
            self->velocityY += FIX(1.0 / 32.0);
        }
        break;
    }
}



/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern AnimationFrame g_KarasumanRavenAbsorbAnim[];
extern EInit D_us_80180940;

void EntityKarasumanRavenAbsorb(Entity* self) {
    s16 angle;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180940);
        self->blendMode = BLEND_TRANSP;
        self->drawFlags = ENTITY_ROTATE;
        self->hitboxState = 0;

        self->flags |= FLAG_DESTROY_IF_OUT_OF_CAMERA | FLAG_UNK_2000;
        if (self->params) {
            self->animCurFrame = 0;
            self->step = 4;
            break;
        }
        angle = ROT(-22.5) - ((Random() & 0x3F) * 16);
        self->rotate = -angle;
        if (!self->facingLeft) {
            angle = FLT(0.5) - angle;
        }
        self->velocityX = 56 * rcos(angle);
        self->velocityY = 56 * rsin(angle);


    case 1:
        MoveEntity();
        AnimateEntity(g_KarasumanRavenAbsorbAnim, self);
        break;

    case 4:
        switch (self->step_s) {
        case 0:
            self->ext.karasuman.timer = 96;
            self->step_s++;


        case 1:
            if (self->ext.karasuman.timer & 1) {
                self->animCurFrame = 61;
            } else {
                self->animCurFrame = 0;
            }

            if (!--self->ext.karasuman.timer) {
                DestroyEntity(self);
            }
            break;
        }
        break;
    }
}
