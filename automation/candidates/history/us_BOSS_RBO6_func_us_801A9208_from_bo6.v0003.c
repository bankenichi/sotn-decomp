/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v2-top-level-seed-declarations
   record : us:BOSS/RBO6:func_us_801A9208_from_bo6
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/boss/bo6/e_cutscene_actors.c
   target : src/boss/rbo6/unk_2362C.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo6.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A362C);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A367C);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A37B4);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A399C);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A3BE0);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A4028);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern GameApi g_api;
extern EInit g_EInitInteractable;
extern Primitive g_PrimBuf[];
extern unkGraphicsStruct g_unkGraphicsStruct;
extern GAME_IMPORT bool g_PauseAllowed;
extern u32 g_CutsceneFlags;
extern u8 g_CastleFlags[];
extern GAME_IMPORT s32 D_800978B4;

void func_us_801A9208_from_bo6(Entity* self) {
    Primitive* prim;
    s16 primIndex;

    switch (self->step) {
    case 0:
        primIndex = g_api.AllocPrimitives(PRIM_G4, 1);
        if (primIndex != -1) {
            InitializeEntity(g_EInitInteractable);
            prim = &g_PrimBuf[primIndex];
            g_unkGraphicsStruct.pauseEnemies = true;
            g_PauseAllowed = false;
            self->primIndex = primIndex;
            self->animSet = 0;
            self->flags |= FLAG_HAS_PRIMS;

            prim->x0 = prim->x2 = 0;
            prim->x1 = prim->x3 = 0x100;
            prim->y0 = prim->y1 = 4;
            prim->y2 = prim->y3 = 0xE8;

            PCOL(prim) = 0x80;

            prim->priority = 0x1F8;
            prim->drawMode =
                DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS | DRAW_TRANSP;
            self->ext.utimer.t = 0;
            g_api.PlaySfx(SFX_WEAPON_APPEAR);
        }
        self->flags |= FLAG_UNK_10000;
        break;
    case 1:
        self->ext.utimer.t++;
        prim = &g_PrimBuf[self->primIndex];
        if (self->ext.utimer.t > 8) {
            self->step++;
            prim->drawMode = DRAW_HIDE;
        } else if (self->ext.utimer.t & 1) {
            prim->drawMode = DRAW_HIDE;
        } else {
            prim->drawMode =
                DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS | DRAW_TRANSP;
        }
        break;
    case 2:
        if (g_CutsceneFlags & 0x100) {
            g_unkGraphicsStruct.unk28 = 0;
            self->step++;
            self->ext.utimer.t = 0;
            prim = &g_PrimBuf[self->primIndex];
            PCOL(prim) = 0;
            prim->drawMode =
                DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS | DRAW_TRANSP;
        }
        break;
    case 3:
        prim = &g_PrimBuf[self->primIndex];
        PCOL(prim) += 1;

        if (prim->r0 == 0xFF) {
            prim->drawMode = DRAW_COLORS;
            self->step++;
        }
        break;
    case 4:
        prim = &g_PrimBuf[self->primIndex];
        PCOL(prim) -= 4;

        if (prim->r0 < 5) {
            g_PauseAllowed = true;
            if (g_unkGraphicsStruct.pauseEnemies != false) {
                g_unkGraphicsStruct.pauseEnemies = false;
            }
            if (g_CastleFlags[0xD8] != 0) {
                D_800978B4 = 2;
            } else {
                D_800978B4 = 1;
            }
            g_GameState = Game_Ending;
            g_GameStep = Play_Reset;
            self->step++;
        }
        break;
    }
}

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", DecreaseBrightness);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A4594);

INCLUDE_ASM("boss/rbo6/nonmatchings/unk_2362C", func_us_801A4F14);
