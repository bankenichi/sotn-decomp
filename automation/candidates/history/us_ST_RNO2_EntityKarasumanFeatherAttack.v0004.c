/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RNO2:EntityKarasumanFeatherAttack
   score  : 5
   receipt: nonmatchings/.adapt-scores/20260824-234301-62298-579201/EntityKarasumanFeatherAttack/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rno2/unk_439A4.c
   asm    : asm/us/st/rno2/nonmatchings/unk_439A4/EntityKarasumanFeatherAttack.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
s32 Random();
int rcos(int a);
int rsin(int a);
void MoveEntity();
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void DestroyEntity(Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int AnimateEntity();
/* End permuter-seed writer declarations. */


INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C39A4);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4960);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4C0C);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4EA8);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasuman);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180928;

extern EInit D_us_80180928;

void EntityKarasumanFeatherAttack(Entity* self) {
    Entity* entity;
    s16 angle;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180928);
        self->animCurFrame = 59;
        self->drawFlags |= ENTITY_ROTATE;
        if (Random() & 1) {
            self->facingLeft = true;
        }

        angle = (Random() * 4) - FLT(0.125);
        self->rotate = angle;
        angle = self->rotate;
        if (!self->facingLeft) {
            angle = FLT(0.5) - angle;
        }
        self->velocityX = 96 * rcos(angle);
        self->velocityY = -96 * rsin(angle);
        self->posX.i.hi += FLT_TO_I(32 * rcos(angle));
        self->posY.i.hi += FLT_TO_I(-32 * rsin(angle));
         
    case 1:
        MoveEntity();
        if (self->flags & FLAG_DEAD) {
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_EXPLOSION, self, entity);
                entity->params = 1;
            }
            DestroyEntity(self);
        }
        break;
    }
}

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasumanOrbAttack);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasumanRavenAttack);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_8018094C;

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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180940;

extern u8 D_us_80181D8C[16];
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
        AnimateEntity(D_us_80181D8C, self);
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
