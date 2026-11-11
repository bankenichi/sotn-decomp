/* CANDIDATE -- hand-derived, byte-verified, ready to land.
   record : us:BOSS/BO7:func_us_80195C50
   origin : src/boss/bo7/unk_14CE0.c
   asm    : asm/us/boss/bo7/nonmatchings/unk_14CE0/func_us_80195C50.s

   Whole-file working copy of the destination TU. land_match extracts only
   the func_us_80195C50 body (brace walk from its definition line) and
   apply_code re-derives the declarations the body needs from the
   destination file, where they are all already visible.

   Status 2026-11-10: the step switch is the lesson-22 ALIGNED4
   computed-goto chassis. gcc emits switch tables after ".align 3", which
   pads one zero word before the retail table boundary (rodata 0x24,
   0x80192E58) and shifts every later BO7 symbol +4; the explicit table
   preserves it. A diagnostic build with this body produced BO7.BIN
   byte-identical to disks/us/BOSS/BO7/BO7.BIN (144480 bytes, zero
   differing regions).

   This file was a permuter seed until 2026-11-10; that banner's bo0.h
   include-path lesson is recorded in
   docs/session-2026-11-09-bo7-us-stubs-log.md. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo7.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void DestroyEntity(Entity*);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void InitializeEntity(u16 arg0[]);
void MoveEntity();
u8 AnimateEntity(u8 frames[], Entity* entity);
int rcos(int a);
int rsin(int a);
void SetDrawEnv(DR_ENV* dr_env, DRAWENV* env);
s32 PrimDecreaseBrightness(Primitive* prim, u8 arg1);
int abs(int x);
void CreateEntityFromCurrentEntity(u16, Entity*);
s32 Random();
/* End permuter-seed writer declarations. */

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
/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GameApi g_api;
extern Primitive g_PrimBuf[];
extern u32 g_Timer;
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern GAME_IMPORT GpuBuffer* g_CurrentBuffer; // g_CurrentBuffer;

void func_us_80195C50(Entity* self) {
    Entity* entity;
    Entity* first;
    s32 primIndex;
    s32 i;
    u32 xAcc;
    s32 w1;
    s32 w2;
    s32 posX;
    s32 posY;
    Primitive* prim;
    DR_ENV* drEnv;
    RECT clip;
    DRAWENV drawEnv;

    // CODEGEN: A normal switch aligns its generated table to eight
    // bytes and pads one word before the target jump table at
    // 0x80192E58, shifting every later BO7 symbol by four bytes. The
    // explicit four-byte-aligned dispatch table preserves the original
    // section layout.
    static void* const jtbl[] ALIGNED4 = {
        &&case_0, &&case_1, &&case_2, &&case_3,
        &&case_4, &&case_5, &&case_6, &&case_7,
    };
    if ((u32)self->step >= 8) {
        goto step_tail;
    }
    goto *jtbl[self->step];

case_0:
        InitializeEntity(g_EInitInteractable);
        self->flags |= FLAG_UNK_10000;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 7);
        if (primIndex == -1) {
            self->step = 0;
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        drEnv = g_api.func_800EDB08((POLY_GT4*)prim);
        if (!drEnv) {
            g_api.FreePrimitives(primIndex);
            self->step = 0;
            self->flags &= ~FLAG_HAS_PRIMS;
            return;
        } else {
            prim->type = PRIM_ENV;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
            drEnv = g_api.func_800EDB08((POLY_GT4*)prim);
            if (prim == NULL) {
                g_api.FreePrimitives(primIndex);
                self->step = 0;
                self->flags &= ~FLAG_HAS_PRIMS;
                return;
            }
        }
        i = 0;
        prim->type = PRIM_ENV;
        prim->drawMode = DRAW_HIDE;
        prim = prim->next;
        self->ext.et_801B0930.prim7C = prim;
        prim->type = PRIM_G4;
        prim->r0 = prim->g0 = prim->b0 = 0;
        w1 = LOW(prim->r0);
        prim->x1 = prim->x3 = 0x42;
        prim->y2 = prim->y3 = 0xB0;
        prim->r2 = 0xFF;
        prim->g2 = prim->b2 = 0;
        w2 = LOW(prim->r2);
        prim->x0 = prim->x2 = 0;
        prim->y0 = prim->y1 = 0;
        prim->priority = 0xF;
        prim->drawMode = DRAW_DEFAULT;
        LOW(prim->r1) = w1;
        LOW(prim->r3) = w2;
        prim = prim->next;
        for (; i < 4; i++) {
            prim->tpage = 0x110;
            if (i & 1) {
                prim->u0 = prim->u2 = 0x3F;
                prim->u1 = prim->u3 = 0;
            } else {
                prim->u0 = prim->u2 = 0;
                prim->u1 = prim->u3 = 0x3F;
            }
            prim->x0 = prim->x2 = i * 0x40;
            prim->v0 = prim->v1 = 0x10;
            prim->v2 = prim->v3 = 0xF0;
            prim->x1 = prim->x3 = (xAcc = ((i * 0x40) + 0x40));
            prim->y0 = prim->y1 = 0x10;
            prim->y2 = prim->y3 = 0xF0;
            prim->drawMode = DRAW_DEFAULT;
            prim->priority = 0x13;
            prim = prim->next;
        }
        g_api.PlaySfx(SFX_BOSS_LARGE_FLAMES);
case_1:
        posX = PLAYER.posX.i.hi + g_Tilemap.scrollX.i.hi;
        if ((u32)(posX - 0x41) < 0x17F) {
            D_us_80180848 |= 1;
            self->step++;
        }
        if (g_Timer % 95 == 0) {
            g_api.PlaySfx(SFX_BOSS_LARGE_FLAMES);
        }
        goto step_tail;

case_2:
        if (g_Timer % 95 == 0) {
            g_api.PlaySfx(SFX_BOSS_LARGE_FLAMES);
        }
        posX = PLAYER.posX.i.hi + g_Tilemap.scrollX.i.hi;
        if ((u32)(posX - 0x81) < 0xFF) {
            g_api.TimeAttackController(TIMEATTACK_EVENT_CERBERUS_DEFEAT, TIMEATTACK_SET_VISITED);
            stopMusicFlag = 1;
            currentMusicId = 0x31D;
            D_us_80180848 |= 2;
            self->step++;
        }
        goto step_tail;

case_3:
        if (!g_api.func_80131F68()) {
            stopMusicFlag = 0;
            g_api.PlaySfx(currentMusicId);
            self->step++;
        }
case_4:
        if (D_us_80180848 & 4) {
            g_api.TimeAttackController(TIMEATTACK_EVENT_CERBERUS_DEFEAT, TIMEATTACK_SET_RECORD);
            g_api.PlaySfx(0x90);
            currentMusicId = 0x319;
            self->step++;
        }
        goto step_tail;

case_5:
        if (D_us_80180848 & 8) {
            self->step++;
        }
        goto step_tail;

case_6:
        posX = 0x100 - g_Tilemap.scrollX.i.hi;
        posY = 0x80 - g_Tilemap.scrollY.i.hi;
        first = &g_Entities[160];
        entity = AllocEntity(first, first + 32);
        if (entity != NULL) {
            CreateEntityFromEntity(E_LIFE_UPSPAWN, self, entity);
            entity->posX.i.hi = posX;
            entity->posY.i.hi = posY;
            entity->params = 5;
            stopMusicFlag = 1;
            currentMusicId = 0x319;
            D_us_80180848 |= 0x10;
            self->step++;
        }
case_7:
        if (!g_api.func_80131F68()) {
            stopMusicFlag = 0;
            g_api.PlaySfx(currentMusicId);
            self->step++;
        }
        goto step_tail;

step_tail:
    prim = &g_PrimBuf[self->primIndex];
    drawEnv = g_CurrentBuffer->draw;
    drawEnv.isbg = 1;
    drawEnv.r0 = 0;
    drawEnv.g0 = 0;
    drawEnv.b0 = 0;
    clip.x = 0;
    clip.y = 0x100;
    clip.w = 0x7F;
    clip.h = 0xFF;
    drawEnv.clip = clip;
    drawEnv.ofs[0] = 0;
    drawEnv.ofs[1] = 0x100;
    SetDrawEnv((DR_ENV*)LOW(prim->r1), &drawEnv);
    prim->priority = 0xE;
    prim->drawMode = DRAW_DEFAULT;
    prim = prim->next;
    prim->priority = 0x11;
    prim->drawMode = DRAW_UNK_800;

    prim = self->ext.et_801B0930.prim7C;
    self->rotate += 0x100;
    if (D_us_80180848 & 4) {
        PrimDecreaseBrightness(prim, 4);
    } else {
        prim->g2 = abs((rcos(self->rotate) << 7) >> 12);
        LOW(prim->r3) = LOW(prim->r2);
    }
    if ((D_us_80180848 & 4) == 0 && (g_Timer & 3) == 0) {
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromCurrentEntity(E_UNK_20, entity);
            entity->posX.i.hi = (Random() & 0x3F) + 0xA;
            entity->posY.i.hi = 0xB0;
            entity->zPriority = 0x10;
            entity->params = 0;
        }
    }
}


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
