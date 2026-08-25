/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v2-top-level-seed-declarations
   record : us:BOSS/BO5:CutsceneCameraPan
   upstream: upstream/master
   source : 85c3717eb4f1a8a5419b9448c5289202a815f971:src/st/cen/e_chamber.c
   target : src/boss/bo5/e_cutscene_actors.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo5.h"

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;

void CutsceneCameraPan(s16 arg0) {
    s16 delta = arg0 - g_Tilemap.height;

    if (delta > 1) {
        g_Tilemap.height++;
    } else if (delta < -1) {
        g_Tilemap.height--;
    } else {
        g_Tilemap.height = arg0;
    }

#ifdef VERSION_PSP
    g_Tilemap.x = 0;
    g_Tilemap.width = 0x300;
#endif
}
