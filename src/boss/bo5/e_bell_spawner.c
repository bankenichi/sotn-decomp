// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo5.h"

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit g_EInitInteractable;
extern s16 D_us_801806C0[2][3];
extern struct Entity;
void InitializeEntity(u16 arg0[]);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;

void EntityBellSpawner(Entity* self) {
    Entity* bell;
    s32 count;
    s16* ptr = *D_us_801806C0;

    if (!self->step) {
        InitializeEntity(g_EInitInteractable);
        for (bell = self + 1, count = 0; count < 2; count++, bell++) {
            CreateEntityFromCurrentEntity(E_ID(BELL), bell);
            bell->posX.i.hi = *ptr++ - g_Tilemap.scrollX.i.hi;
            bell->posY.i.hi = *ptr++ - g_Tilemap.scrollY.i.hi;
            bell->params = *ptr++;
        }
    }
}


