/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNO2:EntityFlyingZombie2
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/lib/e_flying_zombie.c
   target : src/st/rno2/unk_47A9C.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void PlaySfxPositional(s32 arg0);
void InitializeEntity(u16 arg0[]);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s32 GetSideToPlayer(void);
u8 CheckColliderOffsets(s16* arg0, s32 facing);
Entity* AllocEntity(Entity* start, Entity* end);
void DestroyEntity(Entity*);
s32 Random();
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetStep();
extern int UnkCollisionFunc3();
extern int AnimateEntity();
extern int UnkCollisionFunc2();
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GameApi g_api;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityFlyingZombie2(Entity* self) {
    Entity* tempEntity;
    s32 i;

    if (!self->ext.flyingZombie.unk81 && (self->hitFlags & 3) &&
        self->step != 3) {
        self->hitboxState = 0;
        self->hitPoints = g_api.enemyDefs[15].hitPoints;
        SetStep(3);
        PlaySfxPositional(SFX_FLYING_ZOMBIE_PAIN);
    }
    if (self->flags & FLAG_DEAD) {
        if (!self->ext.flyingZombie.unk81) {
            self->hitboxState = 0;
            self->flags &= ~FLAG_DEAD;
            self->hitPoints = g_api.enemyDefs[15].hitPoints;
            SetStep(3);
            PlaySfxPositional(SFX_FLYING_ZOMBIE_PAIN);
        } else if (self->step != 7) {
            self->hitboxState = 0;
            SetStep(7);
        }
    }
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitFlyingZombie2);
        self->zPriority -= 2;
        self->hitboxOffX = 1;
        self->hitboxOffY = 10;
        tempEntity = self + 1;
        CreateEntityFromEntity(E_ID_1C, self, tempEntity);
        self->animCurFrame = 1;

    case 1:
        if (UnkCollisionFunc3(D_us_8018280C) & 1) {
            self->step_s = 0;
            self->step++;
        }
        break;

    case 2:
        switch (self->step_s) {
        case 0:
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            if (self->facingLeft) {
                self->velocityX = FIX(0.125);
            } else {
                self->velocityX = FIX(-0.125);
            }
            self->step_s++;
            break;

        case 1:
            AnimateEntity(D_us_8018283C, self);
            UnkCollisionFunc2(D_us_80182834);
            if (CheckColliderOffsets(D_us_8018282C, self->facingLeft)) {
                self->velocityX = 0;
            }
            if (self->ext.flyingZombie.unk7C++ > 0x80) {
                self->ext.flyingZombie.unk7C = 0;
                self->step_s--;
            }
            if (self->animCurFrame == 7) {
                if (self->facingLeft) {
                    self->velocityX -= FIX(1.0 / 128);
                } else {
                    self->velocityX += FIX(1.0 / 128);
                }
            }
            if (self->animCurFrame == 8) {
                if (self->facingLeft) {
                    self->velocityX += FIX(1.0 / 128);
                } else {
                    self->velocityX -= FIX(1.0 / 128);
                }
            }
            break;
        }
        break;

    case 3:
        if (!self->step_s) {
            PlaySfxPositional(SFX_FLYING_ZOMBIE_BODY_RIP);
            self->ext.flyingZombie.unk81 = 1;
            for (i = 0; i < 2; i++) {
                tempEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (tempEntity != NULL) {
                    CreateEntityFromEntity(E_BLOOD_SPLATTER, self, tempEntity);
                    tempEntity->facingLeft = i;
                    tempEntity->posX.i.hi += 4 - (i * 8);
                }
            }
            tempEntity = self + 1;
            tempEntity->step = 2;
            tempEntity->hitboxState = 0;
            self->step_s++;
        }
        if (!AnimateEntity(D_us_80182874, self)) {
            tempEntity = self + 1;
            tempEntity->step = 3;
            tempEntity->step_s = 0;
            tempEntity->hitboxOffX = 0;
            tempEntity->hitboxOffY = 0;
            tempEntity->facingLeft = self->facingLeft;
            tempEntity->posY.i.hi = self->posY.i.hi - 0x1A;
            tempEntity->flags &= ~FLAG_DEAD;
            self->hitPoints = g_api.enemyDefs[14].hitPoints;
            self->animCurFrame = 0x12;
            self->hitboxState = 3;
            SetStep(5);
        }
        break;

    case 4:
        switch (self->step_s) {
        case 0:
            (self + 1)->step = 3;
            (self + 1)->animCurFrame = 0x10;
            (self + 1)->pose = 0;
            (self + 1)->poseTimer = 0;
            (self + 1)->facingLeft = self->facingLeft;
            (self + 1)->zPriority -= 8;
            (self + 1)->posY.i.hi = self->posY.i.hi - 0xA;
            self->ext.flyingZombie.unk81 = 1;
            self->animCurFrame = 0x12;
            self->ext.flyingZombie.unk7C = 8;
            self->ext.flyingZombie.unk7E = 0;
            self->step_s++;
            break;

        case 1:
            if (!--self->ext.flyingZombie.unk7C) {
                self->ext.flyingZombie.unk7E = 0;
                self->ext.flyingZombie.unk7C = 2;
                self->step_s++;
            }
            break;

        case 2:
            if (!--self->ext.flyingZombie.unk7C) {
                tempEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (tempEntity != NULL) {
                    CreateEntityFromEntity(E_EXPLOSION, self, tempEntity);
                    tempEntity->params = 1;
                    tempEntity->posY.i.hi -= self->ext.flyingZombie.unk7E * 8;
                }
                self->ext.flyingZombie.unk7C = 6;
                self->ext.flyingZombie.unk7E++;
                if (self->ext.flyingZombie.unk7E > 1) {
                    PlaySfxPositional(SFX_FM_STUTTER_EXPLODE);
                    DestroyEntity(self + 1);
                    SetStep(5);
                }
            }
            break;
        }
        break;

    case 5:
        if (!AnimateEntity(D_us_8018288C, self)) {
            self->pose = 0;
            self->poseTimer = 0;
            self->step++;
        }
        break;

    case 6:
        switch (self->step_s) {
        case 0:
            self->ext.flyingZombie.unk7C = D_us_80182898[Random() & 3];
            if (self->facingLeft) {
                self->velocityX = FIX(1.0 / 16);
            } else {
                self->velocityX = FIX(-1.0 / 16);
            }
            self->step_s++;
            break;

        case 1:
            AnimateEntity(D_us_80182854, self);
            UnkCollisionFunc2(D_us_80182834);
            if (CheckColliderOffsets(D_us_8018282C, self->facingLeft)) {
                self->velocityX = 0;
            }
            if (self->animCurFrame == 1) {
                if (self->facingLeft) {
                    self->velocityX -= FIX(5.0 / 2048);
                } else {
                    self->velocityX += FIX(5.0 / 2048);
                }
            }
            if (self->animCurFrame == 2) {
                if (self->facingLeft) {
                    self->velocityX += FIX(5.0 / 2048);
                } else {
                    self->velocityX -= FIX(5.0 / 2048);
                }
            }
            if (!--self->ext.flyingZombie.unk7C) {
                self->pose = 0;
                self->poseTimer = 0;
                self->step_s++;
            }
            break;

        case 2:
            if (!AnimateEntity(D_us_80182868, self)) {
                self->facingLeft = Random() & 1;
                self->pose = 0;
                self->poseTimer = 0;
                self->step_s = 0;
            }
            break;
        }
        break;

    case 7:
        tempEntity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (tempEntity != NULL) {
            CreateEntityFromEntity(E_EXPLOSION, self, tempEntity);
            tempEntity->params = 2;
        }
        PlaySfxPositional(SFX_FM_STUTTER_EXPLODE);
        DestroyEntity(self);
        break;

    case 16:
#include
    }
}


INCLUDE_ASM("st/rno2/nonmatchings/unk_47A9C", EntityFlyingZombie1);
