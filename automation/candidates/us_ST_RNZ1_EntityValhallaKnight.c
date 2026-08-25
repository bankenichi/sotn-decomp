/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v3-us-conditional-extraction
   record : us:ST/RNZ1:EntityValhallaKnight
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/e_valhalla_knight.h
   target : src/st/rnz1/e_valhalla_knight.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void SetStep(u8 step);
void InitializeEntity(u16 arg0[]);
void CreateEntityFromCurrentEntity(u16, Entity*);
s32 UnkCollisionFunc3(s16* sensors);
u8 GetSideToPlayer();
u8 AnimateEntity(u8 frames[], Entity* entity);
void PlaySfxPositional(s32 arg0);
s32 UnkCollisionFunc2(s16* posX);
void EntityGreyPuffSpawner(
    Entity* self, u8 count, u8 params, s16 x, s16 y, u8 index, s16 xGap);
s16 GetDistanceToPlayerX();
void SetSubStep(u8 step_s);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */


/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitValhallaKnight;
extern Tilemap g_Tilemap;
extern GameApi g_api;
extern u8 D_us_80182064[20];
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;

void EntityValhallaKnight(Entity* self) {
    Entity* part;
    Entity* tempEntity2;
    s32 i;
    s32 posX;
    s8* hitboxPtr;
    s32 temp_a0_2;

    if (self->flags & FLAG_DEAD) {
        SetStep(6);
    }
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitValhallaKnight);
        self->animCurFrame = 1;
        self->ext.valhallaKnight.unk84 =
            g_Tilemap.scrollX.i.hi + self->posX.i.hi;
        part = self + 1;
        CreateEntityFromCurrentEntity(E_VALHALLA_KNIGHT_UNK1, part);
        part->params = 0;
        self->nextPart = part;
        self->parent = NULL;
        part = self + 2;
        CreateEntityFromCurrentEntity(E_VALHALLA_KNIGHT_UNK1, part);
        part->params = 1;

    case 1:
        if (UnkCollisionFunc3(D_us_80182028) & 1) {
            self->facingLeft = GetSideToPlayer() & 1;



            SetStep(2);
        }
        break;

    case 2:
        if (!self->step_s) {
            self->ext.valhallaKnight.unk80 = 0x80;
            self->step_s++;
        }
        if (!AnimateEntity(D_us_8018204C, self)) {
            PlaySfxPositional(SFX_VALHALLA_KNIGHT_GALLOP);
        }
        temp_a0_2 = UnkCollisionFunc2(D_us_80182038);
        if (self->facingLeft) {
            self->velocityX = FIX(-2.5);
        } else {
            self->velocityX = FIX(2.5);
        }
        if (temp_a0_2 == 0x80) {
            SetStep(5);
            self->step_s = 2;
        }
        posX = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
        if (self->facingLeft) {
            posX = self->ext.valhallaKnight.unk84 - posX;
        } else {
            posX = posX - self->ext.valhallaKnight.unk84;
        }



        if (posX > 0x60) {

            SetStep(3);
        }
        break;

    case 3:
        if (!self->step_s) {
            PlaySfxPositional(SFX_VALHALLA_KNIGHT_NEIGH);
            self->step_s++;
        }
        UnkCollisionFunc2(D_us_80182038);
        self->velocityX -= self->velocityX / 0x20;
        if (!self->poseTimer) {
            if (self->facingLeft) {
                EntityGreyPuffSpawner(self, 5, 3, -4, 40, 0, 4);
            } else {
                EntityGreyPuffSpawner(self, 5, 3, 4, 40, 0, -4);
            }
        }
        if (!AnimateEntity(D_us_80182058, self)) {
            self->facingLeft ^= 1;
            tempEntity2 = &PLAYER;
            if (tempEntity2->velocityY != 0 && GetDistanceToPlayerX() < 0x80) {
                self->animCurFrame = 1;
                SetStep(5);
            } else {
                self->animCurFrame = 6;
                SetStep(2);
            }
        }
        break;

    case 5:
        switch (self->step_s) {
        case 0:
            if (self->facingLeft) {
                self->velocityX = FIX(-2.5);
            } else {
                self->velocityX = FIX(2.5);
            }
            self->ext.valhallaKnight.unk80 = 0x10;
            self->step_s++;

        case 1:
            if (!AnimateEntity(D_us_80182040, self)) {
                PlaySfxPositional(SFX_VALHALLA_KNIGHT_GALLOP);
            }
            UnkCollisionFunc2(D_us_80182038);
            if (!self->ext.valhallaKnight.unk80) {
                if (GetDistanceToPlayerX() < 0x50) {
                    self->step_s = 2;
                }
            } else {
                self->ext.valhallaKnight.unk80--;
            }
            posX = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
            if (self->facingLeft) {
                posX = self->ext.valhallaKnight.unk84 - posX;
            } else {
                posX = posX - self->ext.valhallaKnight.unk84;
            }



            if (posX > 0x60) {

                SetStep(3);
            }
            break;

        case 2:
            self->velocityY = FIX(-3.0);
            if (self->facingLeft) {
                self->velocityX = FIX(-3.5);
            } else {
                self->velocityX = FIX(3.5);
            }
            self->animCurFrame = 15;
            self->step_s++;

        case 3:
            UnkCollisionFunc3(D_us_80182028);
            self->velocityY -= FIX(5.0 / 32);
            if (self->velocityY > FIX(-0.75)) {
                self->animCurFrame = 16;
            }
            if (self->velocityY > FIX(0.75)) {
                self->animCurFrame = 17;
                self->step_s++;
            }
            break;
        case 4:
            if (UnkCollisionFunc3(D_us_80182028) & 1) {
                g_api.PlaySfx(SFX_STOMP_HARD_B);
                if (self->facingLeft) {
                    EntityGreyPuffSpawner(self, 5, 3, -4, 40, 0, 4);
                } else {
                    EntityGreyPuffSpawner(self, 5, 3, 4, 40, 0, -4);
                }
                if (self->facingLeft) {
                    self->velocityX = FIX(-2.5);
                } else {
                    self->velocityX = FIX(2.5);
                }
                SetSubStep(5);
            }
            break;
        case 5:
            UnkCollisionFunc2(D_us_80182038);
            if (!AnimateEntity(D_us_80182064, self)) {
                SetStep(2);
            }
            break;
        }
        break;

    case 6:
        for (i = 0; i < 3; i++) {
            part = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (part != NULL) {
                CreateEntityFromEntity(E_EXPLOSION, self, part);
                if (self->facingLeft) {
                    part->posX.i.hi -= D_us_801820F4[i].x;
                } else {
                    part->posX.i.hi += D_us_801820F4[i].x;
                }
                part->posY.i.hi += D_us_801820F4[i].y;
                part->params = 3;
            }
        }
        for (i = 0; i < 13; i++) {
            part = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (part != NULL) {
                CreateEntityFromEntity(E_VALHALLA_KNIGHT_UNK2, self, part);
                part->params = i;
                part->facingLeft = self->facingLeft;
                part->velocityX = self->velocityX;
                part->velocityY = self->velocityY;
            }
        }
        g_api.PlaySfx(SFX_EXPLODE_A);
        DestroyEntity(self);
        return;

    case 0xFF:
#include
    }
    hitboxPtr = D_us_80182074;
    if (self->animCurFrame == 11 || self->animCurFrame == 12) {
        hitboxPtr += 4;
    }
    if (self->animCurFrame == 13 || self->animCurFrame == 14) {
        hitboxPtr += 8;
    }
    self->hitboxOffX = *hitboxPtr++;
    self->hitboxOffY = *hitboxPtr++;
    self->hitboxWidth = *hitboxPtr++;
    self->hitboxHeight = *hitboxPtr++;
}


/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit D_us_80180C24;
extern EInit D_us_80180C30;
extern s8 D_us_80182018[36];
extern u8 D_us_8018203C[20];
extern s8 D_us_80182050[20];
extern u8 D_us_80182064[20];

void func_us_801C8954_from_are(Entity* self) {
    Entity* tempEntity;
    s32 curFrame;
    s8* hitboxPtr;

    if (!self->step) {
        if (self->params) {
            InitializeEntity(D_us_80180C30);
        } else {
            InitializeEntity(D_us_80180C24);
            self->parent = self - 1;
            self->nextPart = self - 1;
        }
    }
    tempEntity = self - self->params - 1;
    if (tempEntity->entityId != E_VALHALLA_KNIGHT) {
        DestroyEntity(self);
        return;
    }
    curFrame = tempEntity->animCurFrame;
    self->facingLeft = tempEntity->facingLeft;
    self->posX.val = tempEntity->posX.val;
    self->posY.val = tempEntity->posY.val;
    if (self->params) {
        hitboxPtr = D_us_80182050;
        hitboxPtr += D_us_80182064[curFrame] * 4;
    } else {
        hitboxPtr = D_us_80182018;
        hitboxPtr += D_us_8018203C[curFrame] * 4;
    }
    self->hitboxOffX = *hitboxPtr++;
    self->hitboxOffY = *hitboxPtr++;
    self->hitboxWidth = *hitboxPtr++;
    self->hitboxHeight = *hitboxPtr++;
}



INCLUDE_ASM("st/rnz1/nonmatchings/e_valhalla_knight", func_us_801C8AAC_from_are);
