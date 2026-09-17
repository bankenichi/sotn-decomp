/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RCHI:EntityDemonSwitch
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rchi/e_rchi_demon_switch.h
   target : src/st/rchi/e_demon_switch_wall.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
s32 Random();
void InitializeEntity(u16 arg0[]);
extern void (*g_api_RevealSecretPassageAtPlayerPositionOnMap)(s32 arg0);
/* End permuter-seed writer declarations. */

/*
 * RCHI differs throughout these CHI-derived functions (branch layout,
 * constants, and wall control flow), so the CHI source is not byte-identical.
 */
// EntityDemonSwitchWall's candidate failed to build on this name alone.
// Declared in the shared src/st/e_fire_warg.h:11.
extern EInit g_EInitCommon;

static void UpdateFallingPebble(Primitive* prim) {
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
        // fallthrough

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
extern EInit D_us_80180648;
extern u8 g_CastleFlags[];
extern GameApi g_api;

void EntityDemonSwitch(Entity* self) {
    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180648);

        self->animCurFrame = 3;
        self->hitPoints = 32767;
        self->hitboxState = 3;
        self->hitboxWidth = 6;
        self->hitboxHeight = 8;

        if (g_CastleFlags[RCHI_DEMON_SWITCH]) {
            self->animCurFrame = 4;
        }
        /* fall through */
    case 1:
        if (self->hitParams == 7) {
            g_api.PlaySfx(SFX_ANIME_SWORD_B);
            g_CastleFlags[RCHI_DEMON_SWITCH] = 1;
            g_api_RevealSecretPassageAtPlayerPositionOnMap(RCHI_DEMON_SWITCH);
            self->animCurFrame = 4;
            self->step++;
        }
        break;
    }
}


INCLUDE_ASM("st/rchi/nonmatchings/e_demon_switch_wall", EntityDemonSwitchWall);
