// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo7.h"

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;
extern Tilemap g_Tilemap;
extern EInit g_EInitInteractable;

bool func_us_80194338_from_rbo0(s16* offsets) {
    s32 posY;

    offsets++;
    posY = g_CurrentEntity->posY.i.hi + *offsets + g_Tilemap.scrollY.i.hi;
    posY = 0xD0 - posY;
    if (posY <= 0) {
        g_CurrentEntity->posY.i.hi += posY;
        g_CurrentEntity->velocityX = 0;
        g_CurrentEntity->velocityY = 0;
        return true;
    }
    return false;
}



INCLUDE_ASM("boss/bo7/nonmatchings/unk_14CE0", func_us_80194D3C);

extern EInit D_us_8018046C;
extern s32 D_us_801807BC[];
extern s32 D_us_80180848;

// params: select which animation to play from the anim pointer table
void func_us_801959E0(Entity* self) {
    Entity* entity;

    // boss state word: the projectile parent drives bit 4
    if (D_us_80180848 & 4) {
        DestroyEntity(self);
        return;
    }

    if (self->flags & FLAG_DEAD) {
        entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_EXPLOSION, self, entity);
            entity->params = 1;
        }
        DestroyEntity(self);
        return;
    }

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_8018046C);
        if (self->facingLeft) {
            self->velocityX = FIX(6);
        } else {
            self->velocityX = FIX(-6);
        }
        /* fallthrough */
    case 1:
        MoveEntity();
        AnimateEntity(D_us_801807BC[self->params], self);
        break;
    }
}

extern EInit D_us_80180478;
extern u16 D_us_801806E8[];
extern u8 D_us_801807C8[];

// E_UNK_1E: spinning arc launcher.
// params: selects the palette entry taken from the D_us_801806E8 table.
// On pose 8 of the anim it spawns another E_UNK_1E from the first-half
// entity pool, copying params and facing so the arc repeats.
void func_us_80195AF0(Entity* self) {
    Entity* entity;
    s16 angle;

    if (D_us_80180848 & 4) {
        DestroyEntity(self);
        return;
    }

    if (self->step == 0) {
        InitializeEntity(D_us_80180478);
        self->drawFlags = 5;
        self->scaleX = 0x80;
        self->palette = D_us_801806E8[self->params];
        self->rotate = -0x280;
        if (self->facingLeft) {
            angle = -0x180;
        } else {
            angle = -0x680;
        }
        self->velocityX = ((rcos(angle) * 3) << 17) >> 12;
        self->velocityY = ((rsin(angle) * 3) << 17) >> 12;
    }

    MoveEntity();
    if (!AnimateEntity(D_us_801807C8, self)) {
        DestroyEntity(self);
    }
    if (self->pose == 8 && !self->poseTimer) {
        entity = AllocEntity(&g_Entities[128], &g_Entities[224]);
        if (entity != NULL) {
            CreateEntityFromEntity(E_UNK_1E, self, entity);
            entity->params = self->params;
            entity->facingLeft = self->facingLeft;
        }
    }
}

// Cerberus pillar of fire: allocates seven prims. The first two are ENV
// carriers for a backdrop clear rect, the third is the rcos-pulsing glow
// base, and the last four are the scrolling pillar slices. D_us_80180848
// bits drive the rig: bit 1 arms it once the player is close, bit 2 fires
// the defeat TimeAttack record, bit 4 switches the fade over to
// PrimDecreaseBrightness once the pillar sequence has finished.
INCLUDE_ASM("boss/bo7/nonmatchings/unk_14CE0", func_us_80195C50);

typedef struct {
    u16 animSet;
    u16 unk5A;
    u16 palette;
    u8 blendMode;
    u8 unk07;
    AnimateEntityFrame* frames;
} Unk801808A4;

extern Unk801808A4 D_us_801808A4[];
extern EInit g_EInitParticle;

// E_UNK_20: death-flame particle burst. params & 0xF picks one of the three
// Unk801808A4 triples (animSet, unk5A, palette, blendMode, frames) and the
// chosen step becomes index + 1. params & 0xFF00 carries an optional
// zPriority override and params & 0xF0 forces the shared PAL_FLAG(0x19F)
// tint with additive blending. Step 1 and step 3 seed their movement only
// on the first frame (step_s gate); every frame they move, add the
// deathFlames.unk8C gravity word to velocityY, fade opacity and burn out
// when the animation finishes. Step 2 is the variant without gravity or
// fade (init velocity once, plain move, plain animation).
void func_us_801963D8(Entity* self) {
    Unk801808A4* temp_v1_2;
    s32 params;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitParticle);
        params = self->params & 0xF;
        temp_v1_2 = &D_us_801808A4[params];
        self->palette = temp_v1_2->palette + 0x2E0;
        self->blendMode = temp_v1_2->blendMode;
        self->animSet = temp_v1_2->animSet;
        self->unk5A = temp_v1_2->unk5A;
        self->ext.deathFlames.frames = temp_v1_2->frames;
        self->step = params + 1;
        if (self->params & 0xFF00) {
            self->zPriority = (self->params & 0xFF00) >> 8;
        }
        if (self->params & 0xF0) {
            self->palette = PAL_FLAG(0x19F);
            self->blendMode = BLEND_TRANSP;
            self->facingLeft = true;
        }
        break;

    case 1:
        if (!self->step_s) {
            self->drawFlags = 8;
            self->opacity = 0x50;
            self->flags &= ~FLAG_POS_CAMERA_LOCKED;
            self->facingLeft = Random() & 1;
            self->velocityX = (Random() << 8) - 0x8000;
            self->velocityY = -0x18000;
            self->ext.deathFlames.unk8C = -(Random() << 4) - 0x1000;
            self->step_s++;
        }
        MoveEntity();
        self->velocityY += self->ext.deathFlames.unk8C;
        self->opacity = self->opacity + 0xFF;
        if (!AnimateEntity(self->ext.deathFlames.frames, self)) {
            DestroyEntity(self);
        }
        break;

    case 2:
        if (!self->step_s) {
            self->velocityY = -0x4000;
            self->step_s++;
        }
        MoveEntity();
        if (!AnimateEntity(self->ext.deathFlames.frames, self)) {
            DestroyEntity(self);
        }
        break;

    case 3:
        if (!self->step_s) {
            self->drawFlags = 8;
            self->opacity = 0xC0;
            self->facingLeft = Random() & 1;
            self->velocityX = (Random() << 8) - 0x8000;
            self->velocityY = -0xC000;
            self->ext.deathFlames.unk8C = -(Random() << 4) - 0x4000;
            self->step_s++;
        }
        MoveEntity();
        self->velocityY += self->ext.deathFlames.unk8C;
        self->opacity = self->opacity + 0xFF;
        if (!AnimateEntity(self->ext.deathFlames.frames, self)) {
            DestroyEntity(self);
        }
        break;
    }
}
