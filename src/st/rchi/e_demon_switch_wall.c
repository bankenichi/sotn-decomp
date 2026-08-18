// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rchi.h"

/*
 * RCHI differs throughout these CHI-derived functions (branch layout,
 * constants, and wall control flow), so the CHI source is not byte-identical.
 */
// EntityDemonSwitchWall's candidate failed to build on this name alone.
// Declared in the shared src/st/e_fire_warg.h:11.
extern EInit g_EInitCommon;

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;

#define DRAW_HIDE 8
#define DRAW_UNK02 2
s32 Random(void);

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

INCLUDE_ASM("st/rchi/nonmatchings/e_demon_switch_wall", EntityDemonSwitch);

INCLUDE_ASM("st/rchi/nonmatchings/e_demon_switch_wall", EntityDemonSwitchWall);
