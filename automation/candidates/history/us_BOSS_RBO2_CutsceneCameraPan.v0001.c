/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/RBO2:CutsceneCameraPan
   source : upstream/master:src/st/cen/e_chamber.c
   target : src/boss/rbo2/e_cutscene_actors.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rbo2.h"

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

INCLUDE_ASM("boss/rbo2/nonmatchings/e_cutscene_actors", func_us_801A8FC0_from_bo6);
