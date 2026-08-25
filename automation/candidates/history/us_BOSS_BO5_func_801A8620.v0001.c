/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:BOSS/BO5:func_801A8620
   source : upstream/master:src/st/st0/2805C.c
   target : src/boss/bo5/unk_1FD30.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo5.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
int FntPrint(const char* fmt, ...);
void InitializeEntity(u16 arg0[]);
int abs(int x);
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitCommon;

void func_801A8620(Entity* entity) {
    s16 dist;
    s32 params = (s16)entity->params;

    FntPrint("set:%04x\n", params);
    FntPrint("sx:%04x\n", g_Tilemap.left);
    FntPrint("ex:%04x\n", g_Tilemap.right);

    switch (entity->step) {
    case 0:
        InitializeEntity(g_EInitCommon);
        entity->animSet = ANIMSET_DRA(2);
        entity->animCurFrame = 1;
        entity->zPriority = 0xB0;
        break;

    case 1:
        dist = entity->posY.i.hi - PLAYER.posY.i.hi;
        dist = abs(dist);

        if (dist < 0x20) {
            switch (params) {
            case 0:
                if (g_PlayerX > 0x280) {
                    g_Tilemap.width = 0x280;
                    g_Tilemap.right--;
                    entity->step++;
                }
                break;

            case 1:
                if (g_PlayerX < 0x180) {
                    g_Tilemap.x = 0x180;
                    g_Tilemap.left++;
                    entity->step++;
                }
                break;

            case 3:
                if (g_PlayerX < 0x100) {
                    g_Tilemap.x = 0x100;
                    g_Tilemap.left++;
                    entity->step++;
                }
                break;

            case 5:
                if (g_PlayerX < 0x80) {
                    g_Tilemap.x = 0x80;
                    entity->step++;
                }
                break;

            case 6:
                if (g_PlayerX > 0x480) {
                    g_Tilemap.width = 0x480;
                    entity->step++;
                }
                break;

            case 7:
                if (g_PlayerX > 0x480) {
                    g_Tilemap.width = 0x480;
                    entity->step++;
                }
                break;

            case 8:
                if (g_PlayerX < 0x80) {
                    g_Tilemap.x = 0x80;
                    entity->step++;
                }
                break;

            case 9:
                if (g_PlayerX > 0x280) {
                    g_Tilemap.width = 0x280;
                    entity->step++;
                }
                break;

            case 10:
                if (g_PlayerX < 0x180) {
                    g_Tilemap.x = 0x180;
                    g_Tilemap.left++;
                    entity->step++;
                }
                break;

            case 11:
                if (g_PlayerX > 0x280) {
                    g_Tilemap.width = 0x280;
                    g_Tilemap.right--;
                    entity->step++;
                }
                break;

            case 12:
                if (g_PlayerX < 0x180) {
                    g_Tilemap.x = 0x180;
                    g_Tilemap.left++;
                    entity->step++;
                }
                break;

            case 2:
            case 4:
            case 13:
            case 14:
                if (g_PlayerX > 0x300) {
                    g_Tilemap.width = 0x300;
                    g_Tilemap.right--;
                    entity->step++;
                }
                break;
            }
        }
        break;
    }
}
