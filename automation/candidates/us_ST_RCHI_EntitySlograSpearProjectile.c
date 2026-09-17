/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RCHI:EntitySlograSpearProjectile
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rchi/e_slogra.c
   target : src/st/rchi/e_slogra.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void MoveEntity();
void PlaySfxPositional(s32 arg0);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void DestroyEntity(Entity*);
u8 AnimateEntity(u8 frames[], Entity* entity);
void SetStep(u8 step);
/* End permuter-seed writer declarations. */

// EntitySlograSpear and EntitySlograSpearProjectile each failed to build on
// one of these names. g_EInitSlograSpear is defined by THIS overlay at
// src/st/rchi/e_init.c:94; g_Entities_224 is the shared src/st/e_imp.h:9.
extern EInit g_EInitSlograSpear;
extern Entity g_Entities_224[];

INCLUDE_ASM("st/rchi/nonmatchings/e_slogra", EntitySlogra);

#define ENTITY_ROTATE 4
#define FLAG_DESTROY_IF_OUT_OF_CAMERA 2147483648
#define SFX_ARROW_SHOT_A 1573
extern s8 g_SlograSpearHitboxes[];
extern u8 g_SlograSpearHitboxIdx[];
extern struct Entity;
void InitializeEntity(u16 arg0[]);

void EntitySlograSpear(Entity* self) {
    s32 animFrame;
    Entity* slogra;
    s8* hitbox;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitSlograSpear);

    case 1:
        slogra = self - 1;
        self->facingLeft = slogra->facingLeft;
        self->posX.i.hi = slogra->posX.i.hi;
        self->posY.i.hi = slogra->posY.i.hi;
        animFrame = slogra->animCurFrame;
        hitbox = g_SlograSpearHitboxes;
        hitbox += 4 * g_SlograSpearHitboxIdx[animFrame];
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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntitySlograSpearProjectile(Entity* self) {
    Entity* entity;

    if (self->flags & FLAG_DEAD) {
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_EXPLOSION, self, entity);
            entity->params = 1;
        }
        DestroyEntity(self);
        return;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitSlograProjectile);
        if (self->facingLeft) {
            self->velocityX = FIX(4);
        } else {
            self->velocityX = FIX(-4);
        }

    case 1:
        if (AnimateEntity(g_AnimSlograSpearProjectileLaunch, self) == 0) {
            SetStep(2);
        }
        break;

    case 2:
        MoveEntity();
        AnimateEntity(g_AnimSlograSpearProjectileFly, self);
        break;
    }
}
