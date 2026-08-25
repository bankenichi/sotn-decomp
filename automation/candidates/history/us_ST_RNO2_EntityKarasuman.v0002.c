/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO2:EntityKarasuman
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/nz1/e_karasuman.c
   target : src/st/rno2/unk_439A4.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno2.h"

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C39A4);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4960);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4C0C);

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", func_us_801C4EA8);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitKarasuman;
extern u32 g_Timer;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern GameApi g_api;
extern Tilemap g_Tilemap;

void EntityKarasuman(Entity* self) {
    Entity* entity;
    s32 i;
    s32 offsetX;
    s32 offsetY;
    s8* frameProperty;

    if (self->hitFlags & 3 && self->step & 1) {
        SetStep(14);
    }
    if (self->flags & FLAG_DEAD && self->step < 16) {
        SetStep(16);
    }

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitKarasuman);
        self->flags &= ~(FLAG_UNK_800 | FLAG_UNK_400);
        self->animCurFrame = 1;
         

    case 1:
        if (UnkCollisionFunc3(D_us_8018115C) & 1) {
            SetStep(2);
        }
        break;

    case 2:
        switch (self->step_s) {
        case 0:
            AnimateEntity(D_us_80181174, self);
            if (D_us_80181138 & 1) {
                SetSubStep(1);
            }
            break;
        case 1:
            if (AnimateEntity(D_us_8018117C, self) == 0) {
                SetStep(4);
            }
            break;
        }
        break;
    case 4:
        switch (self->step_s) {
        case 0:
            if (AnimateEntity(D_us_80181194, self) == 0) {
                self->velocityX = 0;
                self->velocityY = FIX(-4);
                SetSubStep(1);
            }
            break;
        case 1:
            MoveEntity();
            self->velocityY += FIX(0.125);
            if (AnimateEntity(D_us_801811A0, self) == 0) {
                SetStep(3);
                if (self->ext.karasuman.flag2) {
                    SetStep(0xC);
                }
            }
            break;
        }
        break;

    case 3:
        if (!self->step_s) {
            self->ext.karasuman.timer = 48;
            self->velocityY = 0;
            self->step_s++;
        }
        AnimateEntity(D_us_801811A8, self);
        MoveEntity();
        if (GetSideToPlayer() & 1) {
            self->velocityX -= FIX(1.0 / 64.0);
            if (self->velocityX < FIX(-0.75)) {
                self->velocityX = FIX(-0.75);
            }
        } else {
            self->velocityX += FIX(1.0 / 64.0);
            if (self->velocityX > FIX(0.75)) {
                self->velocityX = FIX(0.75);
            }
        }
        if (!self->poseTimer && self->pose == 1) {
            PlaySfxPositional(SFX_UNK_NZ1_722);
        }

        if (!--self->ext.karasuman.timer) {
            if (self->ext.karasuman.flag0) {
                SetStep(8);
            } else {
                SetStep(6);
            }
            self->ext.karasuman.flag0 ^= 1;
        }
        break;
    case 6:
        switch (self->step_s) {
        case 0:
            if (AnimateEntity(D_us_801811CC, self) == 0) {
                self->ext.karasuman.timer = 48;
                SetSubStep(1);
            }
            break;
        case 1:
            if (!(g_Timer & 7)) {
                PlaySfxPositional(SFX_BAT_ECHO_C);
                for (i = 0; i < 8; i++) {
                    entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
                    if (entity != NULL) {
                        CreateEntityFromEntity(
                            E_ID(KARASUMAN_FEATHER_ATTACK), self, entity);
                        entity->posY.i.hi -= 28;
                    }
                }
            }
            if (!--self->ext.karasuman.timer) {
                self->step_s++;
            }
            break;
        case 2:
            if (AnimateEntity(D_us_801811D8, self) == 0) {
                SetStep(7);
                self->step_s = 2;
            }
            break;
        }
        break;
    case 7:
        switch (self->step_s) {
        case 0:
            self->velocityX = 0;
            self->velocityY = 0;
            self->step_s++;
             
        case 1:
            if (AnimateEntity(D_us_801811B8, self) == 0) {
                SetSubStep(2);
            }
            break;
        case 2:
            if (UnkCollisionFunc3(D_us_8018115C) & 1) {
                self->step_s++;
            } else {
                self->velocityY -= FIX(0.09375);
            }
            break;
        case 3:
            if (AnimateEntity(D_us_801811C0, self) == 0) {
                SetStep(4);
                SetStep(0xA);
            }
            break;
        }
        break;
    case 8:
        switch (self->step_s) {
        case 0:
            self->ext.karasuman.flag1 = 0;
            if (AnimateEntity(D_us_801811E0, self) == 0) {
                SetSubStep(1);
            }
            break;
        case 1:
            for (i = 0; i < 4; i++) {
                entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
                if (entity != NULL) {
                    CreateEntityFromEntity(
                        E_ID(KARASUMAN_ORB_ATTACK), self, entity);
                    entity->params = i;
                    entity->ext.karasuman.parent = self;
                    entity->zPriority = self->zPriority + 1;
                }
            }
            self->ext.karasuman.timer = 64;
            self->step_s++;
             
        case 2:
            AnimateEntity(D_us_801811E8, self);
            if (!(self->ext.karasuman.timer & 7)) {
                PlaySfxPositional(SFX_RAPID_SYNTH_BUBBLE_SHORT);
            }
            if (!--self->ext.karasuman.timer) {
                PlaySfxPositional(SFX_TELEPORT_BANG_A);
                self->ext.karasuman.flag1 = 1;
                self->drawFlags = ENTITY_SCALEY | ENTITY_SCALEX;
                self->scaleX = self->scaleY = 256;
                self->velocityY = FIX(-6.0);
                self->velocityX = 0;
                SetSubStep(3);
            }
            break;
        case 3:
            if (AnimateEntity(D_us_801811F0, self) == 0) {
                self->step_s++;
            }
             
        case 4:
            MoveEntity();
            self->velocityY -= self->velocityY / 8;
            if (self->scaleX > 224) {
                self->scaleX = self->scaleY -= 4;
            } else if (self->step_s == 4) {
                self->step_s++;
            }
            break;
        case 5:
            self->scaleX = self->scaleY += 8;
            if (self->scaleX > 256) {
                self->drawFlags = ENTITY_DEFAULT;
                SetStep(7);
            }
            break;
        }
        break;
    case 10:
        switch (self->step_s) {
        case 0:
            if (AnimateEntity(D_us_8018122C, self) == 0) {
                SetSubStep(1);
            }
            break;
        case 1:
            self->ext.karasuman.timer = 64;
            self->ext.karasuman.flag2 = 1;
            self->step_s++;
             
        case 2:
            if (!(self->ext.karasuman.timer & 3)) {
                entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (entity != NULL) {
                    CreateEntityFromEntity(
                        E_ID(KARASUMAN_RAVEN_ATTACK), self, entity);
                    entity->ext.karasuman.parent = self;
                    entity->params = 1;
                }
            }
            if (!(self->ext.karasuman.timer & 7)) {
                g_api.PlaySfx(SFX_WING_FLAP_A);
            }

            if (!--self->ext.karasuman.timer) {
                self->ext.karasuman.timer = 64;
                self->step_s++;
            }
            break;
        case 3:
            if (AnimateEntity(D_us_80181238, self) == 0) {
                SetStep(4);
            }
        }
        break;
    case 12:
        switch (self->step_s) {
        case 0:
            self->ext.karasuman.flag2 = 0;
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            self->step_s++;
             
        case 1:
            if (AnimateEntity(D_us_80181240, self) == 0) {
                self->ext.karasuman.timer = 96;
                if (self->facingLeft) {
                    self->velocityX = FIX(-2.0);
                } else {
                    self->velocityX = FIX(2.0);
                }
                self->velocityY = FIX(-2.0);
                self->step_s++;
            }
            break;
        case 2:
            if (self->ext.karasuman.timer > 0x48) {
                MoveEntity();
                self->velocityX -= self->velocityX / 8;
                self->velocityY -= self->velocityY / 8;
            }
            if (!(self->ext.karasuman.timer & 7)) {
                g_api.PlaySfx(SFX_WING_FLAP_A);
                entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
                if (entity != NULL) {
                    CreateEntityFromEntity(
                        E_ID(KARASUMAN_RAVEN_ATTACK), self, entity);
                    entity->facingLeft = self->facingLeft;
                    entity->ext.karasuman.parent = self;
                }
            }

            if (!--self->ext.karasuman.timer) {
                SetSubStep(3);
            }
            break;
        case 3:
            if (AnimateEntity(D_us_8018124C, self) == 0) {
                SetStep(3);
            }
            break;
        }
        break;
    case 14:
        if (!self->step_s) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            if (self->facingLeft) {
                self->velocityX = FIX(-4.0);
            } else {
                self->velocityX = FIX(4.0);
            }
            self->velocityY = FIX(-2.0);
            for (i = 0; i < 8; i++) {
                entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (entity != NULL) {
                    CreateEntityFromEntity(
                        E_ID(KARASUMAN_FEATHER), self, entity);
                    if (Random() & 1) {
                        entity->zPriority = self->zPriority + 1;
                    } else {
                        entity->zPriority = self->zPriority - 1;
                    }
                }
            };
            self->step_s++;
        }
        MoveEntity();

        self->velocityX -= self->velocityX / 16;
        self->velocityY -= self->velocityY / 16;

        if (AnimateEntity(D_us_80181264, self) == 0) {
            SetStep(7);
        }
        break;
    case 16:
        switch (self->step_s) {
        case 0:
            D_us_80181138 |= 2;
            self->hitboxState = 0;
            for (i = 0; i < 32; i++) {
                entity = AllocEntity(&g_Entities[160], &g_Entities[256]);
                if (entity != NULL) {
                    CreateEntityFromEntity(
                        E_ID(KARASUMAN_FEATHER), self, entity);
                    if (Random() & 1) {
                        entity->zPriority = self->zPriority + 1;
                    } else {
                        entity->zPriority = self->zPriority - 1;
                    }
                }
            }
            PlaySfxPositional(SFX_UNK_NZ1_723);
            self->step_s++;
             
        case 1:
            if ((AnimateEntity(D_us_80181274, self) == 0) &&
                (UnkCollisionFunc3(D_us_8018115C) & 1)) {
                self->step_s++;
            }
            break;
        case 2:
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(
                    E_ID(KARASUMAN_RAVEN_ABSORB), self, entity);
                entity->params = 1;
                entity->zPriority = self->zPriority + 1;
            }
            self->ext.karasuman.timer = 64;
            self->step_s++;
             
        case 3:
            entity = AllocEntity(&g_Entities[160], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(
                    E_ID(KARASUMAN_RAVEN_ABSORB), self, entity);
                entity->facingLeft = Random() & 1;
                entity->params = 0;
                entity->zPriority = self->zPriority + 1;
            }

            if (!(self->ext.karasuman.timer & 7)) {
                g_api.PlaySfx(SFX_UNK_NZ1_721);
            }

            if (!--self->ext.karasuman.timer) {
                self->palette = PAL_FLAG(0x2E4);
                self->blendMode = BLEND_TRANSP | BLEND_ADD;
                self->drawFlags |= ENTITY_OPACITY;
                self->opacity = 0x80;
                self->ext.karasuman.timer = 64;
                self->step_s++;
            }
            break;
        case 4:
            for (i = 0; i < 4; i++) {
                entity = AllocEntity(&g_Entities[160], &g_Entities[256]);
                if (entity != NULL) {
                    CreateEntityFromEntity(
                        E_ID(EXPLODE_PUFF_OPAQUE), self, entity);
                    entity->facingLeft = Random() & 1;
                    entity->zPriority = self->zPriority + 1;
                    entity->posY.i.hi += 32;
                    entity->params = 3;
                }
            }
            if (self->opacity) {
                self->opacity -= 2;
            }
            if (!(self->ext.karasuman.timer & 0xF)) {
                PlaySfxPositional(SFX_FIREBALL_SHOT_A);
            }

            if (!--self->ext.karasuman.timer) {
                self->animCurFrame = 0;
                D_us_80181138 |= 4;
                self->step++;
            }
            break;
        case 5:
            break;
        }
        break;
    case 0xFF:
#include "../pad2_anim_debug.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void MoveEntity();
s32 GetSideToPlayer(void);
void PlaySfxPositional(s32 arg0);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s32 Random();
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetStep();
extern int UnkCollisionFunc3();
extern int AnimateEntity();
extern int SetSubStep();
/* End permuter-seed writer declarations. */
        break;
    }

    frameProperty = (s8*)D_us_8018127C;
    frameProperty += D_us_801812B8[self->animCurFrame] * sizeof(FrameProperty);
    self->hitboxOffX = *frameProperty++;
    self->hitboxOffY = *frameProperty++;
    self->hitboxWidth = *frameProperty++;
    self->hitboxHeight = *frameProperty++;

    offsetX = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
    offsetY = self->posY.i.hi + g_Tilemap.scrollY.i.hi;
    if (self->velocityX < 0) {
        if (offsetX < 36) {
            self->posX.i.hi = 36 - g_Tilemap.scrollX.i.hi;
        }
    } else if (offsetX > 0xDC) {
        self->posX.i.hi = 0xDC - g_Tilemap.scrollX.i.hi;
    }
#ifndef VERSION_PSP
    if (self->velocityY < 0) {
        if (offsetY < 80) {
            self->posY.i.hi = 80 - g_Tilemap.scrollY.i.hi;
        }
    }
#endif
}

INCLUDE_ASM("st/rno2/nonmatchings/unk_439A4", EntityKarasumanFeatherAttack);

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
