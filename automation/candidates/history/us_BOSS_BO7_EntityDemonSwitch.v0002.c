/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/BO7:EntityDemonSwitch
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/chi/en_demon_switch_wall.c
   target : src/boss/bo7/e_demon_switch_wall.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo7.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
/* End permuter-seed writer declarations. */

s32 Random(void);

void UpdateFallingPebble(Primitive* prim) {
    const int FallSpeed = 2;
    const int MaxScrolledY = 160;

    s32 newYScrolled;
    u32 rand;

    switch (prim->p3) {
    case 1:  
        rand = (Random() & 1);
        prim->u0 = rand + 1;
        prim->v0 = rand + 1;
        prim->r0 = 0x60;
        prim->g0 = 0x80;
        prim->b0 = 0x30;
        prim->priority = 0xA0;
        prim->drawMode = DRAW_UNK02;
        prim->p2 = (Random() & 0x1F) + 0x10;
        prim->p3 = 2;
         
    case 2:  
        prim->y0 += FallSpeed;
        newYScrolled = g_Tilemap.scrollY.i.hi + prim->y0;
        if (!--prim->p2 || newYScrolled > MaxScrolledY) {
            prim->drawMode = DRAW_HIDE;
            prim->p3 = 0;  
        }
        return;
    }
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern u8 g_CastleFlags[];
extern GameApi g_api;

void EntityDemonSwitch(Entity* self) {
    typedef enum Step {
        INIT = 0,
        PRESS = 1,
    };

    switch (self->step) {
    case INIT:
        InitializeEntity(g_EInitSecret);

        self->animCurFrame = 3;
        self->hitPoints = 32767;
        self->hitboxState = 3;
        self->hitboxWidth = 6;
        self->hitboxHeight = 8;

        if (g_CastleFlags[CHI_DEMON_SWITCH]) {
            self->animCurFrame = 4;
        }
         
    case PRESS:
        if (self->hitParams == 7) {
            g_api.PlaySfx(SFX_ANIME_SWORD_B);
            g_CastleFlags[CHI_DEMON_SWITCH] = 1;
             
             
             
            g_api.RevealSecretPassageAtPlayerPositionOnMap(CHI_DEMON_SWITCH);
            self->animCurFrame = 4;
            self->step++;  
        }
        break;
    }
}

INCLUDE_ASM("boss/bo7/nonmatchings/e_demon_switch_wall", EntityDemonSwitchWall);
