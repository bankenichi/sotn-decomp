/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/BO5:EntityRbo3Door
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/func_80192d64.h
   target : src/boss/bo5/unk_2159C.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo5.h"

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;

void EntityRbo3Door(Entity* self) {
    s32 i;
    s32 fg;
    s32 fgIndex;
    s32 y;
    Entity* next;

    switch (self->step) {
    case 0:
        InitializeEntity(RBO3_DOOR_INIT);
        self->zPriority = 0x5C;
        if (self->params & 2) {
            self->animCurFrame = 0xE;
            return;
        }
        if (self->params & 1) {
            self->animCurFrame = 13;
            self->posX.i.hi = 48 - g_Tilemap.scrollX.i.hi;
            self->posY.i.hi = 224 - g_Tilemap.scrollY.i.hi;
        } else {
            self->animCurFrame = 12;
            self->posX.i.hi = 496 - g_Tilemap.scrollX.i.hi;
            self->posY.i.hi = 224 - g_Tilemap.scrollY.i.hi;
        }

        next = self + 1;
        CreateEntityFromEntity(RBO3_DOOR_CHILD_ID, self, next);

        next->params = 2;
        next->posY.i.hi = 96;
        if (self->params) {
            next->posX.i.hi -= 16;
        }
        break;

    case 1:
        if (RBO3_DOOR_FLAG) {
            if (self->params & 2) {
                self->step = 8;
                break;
            }
            if (self->params) {
                fgIndex = 0xC1;
            } else {
                fgIndex = 0xDE;
            }
            for (i = 0; i < 4; i++) {
                g_Tilemap.fg[fgIndex] = 0x4B3;
                fgIndex += 0x20;
            }
            self->step = 2;
        }
        break;
    case 2:
        self->posY.val -= FIX(1.125);
        if (self->posY.i.hi < 186) {
            self->posY.i.hi = 186;
            self->step++;
        }
        break;
    case 3:
        if (RBO3_DOOR_FLAG == 0) {
            if (self->params) {
                fgIndex = 0xC1;
            } else {
                fgIndex = 0xDE;
            }
            for (i = 0; i < 4; i++) {
                g_Tilemap.fg[fgIndex] = 0;
                fgIndex += 0x20;
            }
            self->step++;
        }
        break;
    case 4:
        self->posY.val += FIX(0.75);
        y = self->posY.i.hi + g_Tilemap.scrollY.i.hi;
        if (y > 0xE0) {
            self->posY.i.hi = 0xE0 - g_Tilemap.scrollY.i.hi;
            self->step++;
        }
        break;
    case 5:
    case 6:
    case 7:
        break;
    case 8:
        self->posY.val += FIX(1.125);
        if (self->posY.i.hi > 127) {
            self->posY.i.hi = 127;
            self->step++;
        }
        break;
    case 9:
        if (RBO3_DOOR_FLAG == 0) {
            self->step++;
        }
        break;
    case 10:
        self->posY.val -= FIX(0.75);
        y = self->posY.i.hi + g_Tilemap.scrollY.i.hi;
        if (y < 96) {
            self->posY.i.hi = 96 - g_Tilemap.scrollY.i.hi;
            self->step++;
        }
        break;
    case 11:
        break;
    }
}

#include "../../st/e_background_sky_land.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/bo5/nonmatchings/unk_2159C", func_us_801A19CC);

INCLUDE_ASM("boss/bo5/nonmatchings/unk_2159C", func_us_801A19FC);

INCLUDE_ASM("boss/bo5/nonmatchings/unk_2159C", func_us_801A1BA0);

INCLUDE_ASM("boss/bo5/nonmatchings/unk_2159C", func_us_801A1C14);

INCLUDE_ASM("boss/bo5/nonmatchings/unk_2159C", func_us_801A3B88);

extern EInit g_EInitParticle;
extern AnimateEntityFrame D_us_80180A18[];

void func_us_801A3E78(Entity* self) {
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitParticle);
        self->animSet = 2;
        self->animCurFrame = 1;
        self->drawFlags |= ENTITY_SCALEX | ENTITY_SCALEY | ENTITY_OPACITY;
        self->drawFlags |= ENTITY_ROTATE;
        self->blendMode |= BLEND_TRANSP | BLEND_ADD;
        self->opacity = 0x80;
        if (self->facingLeft) {
            self->velocityX = FIX(1);
        } else {
            self->velocityX = -FIX(1);
        }
        if (self->params) {
            self->velocityY = FIX(0.5);
            return;
        }
        self->velocityY = -FIX(1);
        return;

    case 1:
        MoveEntity();
        if (self->facingLeft) {
            self->velocityX -= FIX(0.125);
        } else {
            self->velocityX += FIX(0.125);
        }
        self->velocityY -= FIX(0.0625);
        if (self->params) {
            self->rotate -= 0x40;
        } else {
            self->rotate += 0x40;
        }
        self->scaleX -= 0xA;
        self->opacity -= 6;
        if (!AnimateEntity(D_us_80180A18, self)) {
            DestroyEntity(self);
        }
        return;
    }
}

extern s32 D_us_801806E0;
extern EInit D_us_801804E4;
extern s16 D_us_80180ABC[];
extern AnimateEntityFrame D_us_801809F0[];
extern AnimateEntityFrame D_us_801809F8[];

void func_us_801A3FD4(Entity* self) {
    Entity* entity;

    if (D_us_801806E0 & 2) {
        self->flags |= FLAG_DEAD;
    }

    if (self->flags & FLAG_DEAD) {
        entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
        if (entity != NULL) {
            DestroyEntity(entity);
            CreateEntityFromEntity(E_EXPLOSION, self, entity);
            entity->params = 0;
        }
        DestroyEntity(self);
        return;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_801804E4);
        self->hitboxState = 2;
        self->drawFlags |= ENTITY_ROTATE;
        self->rotate = ((Random() & 3) << 9) - 0x300;
        self->ext.et_801A3FD4.rotateDir = 1;
        return;

    case 1:
        if (UnkCollisionFunc3(D_us_80180ABC) & 1) {
            self->step++;
        }

    case 2:
        if (!self->ext.et_801A3FD4.timer) {
            if (AnimateEntity(D_us_801809F0, self)) {
                return;
            }
            entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
            if (entity != NULL) {
                DestroyEntity(entity);
                CreateEntityFromEntity(E_EXPLOSION, self, entity);
                entity->params = 0;
            }
            self->facingLeft = GetSideToPlayer() & 1;
            self->drawFlags = ENTITY_DEFAULT;
            if (self->facingLeft) {
                self->velocityX = -FIX(2.5);
            } else {
                self->velocityX = FIX(2.5);
            }
            self->velocityY = -FIX(0.25);
            self->pose = 0;
            self->poseTimer = 0;
            self->hitboxState = 3;
            PlaySfxPositional(SFX_NO1_BIRD_CYCLE);
            self->step++;
            return;
        } else if (self->ext.et_801A3FD4.timer-- < 8) {
            self->rotate += self->ext.et_801A3FD4.rotateDir << 9;
            self->ext.et_801A3FD4.rotateDir = -self->ext.et_801A3FD4.rotateDir;
            return;
        }
        break;

    case 3:
        AnimateEntity(D_us_801809F8, self);
        MoveEntity();
        self->velocityY -= FIX(0.0390625);
        break;
    }
}

INCLUDE_ASM("boss/bo5/nonmatchings/unk_2159C", func_us_801A425C);

INCLUDE_ASM("boss/bo5/nonmatchings/unk_2159C", func_us_801A4430);

INCLUDE_ASM("boss/bo5/nonmatchings/unk_2159C", func_us_801A4494);
