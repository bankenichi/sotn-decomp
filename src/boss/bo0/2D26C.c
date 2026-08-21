// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo0.h"

// This file covers 0x2D26C..0x3053C. Everything from 0x3053C up now lives in
// 3053C.c: see the note on that segment in config/splat.us.bobo0.yaml for why
// the split had to happen.

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AD26C);

// Checks whether the tile at (x, y) is solid ground.
s32 func_us_801AD2F0(s16 x, s16 y) {
    Collider col;

    g_api.CheckCollision(x, y, &col, 0);
    return col.effects & EFFECT_SOLID;
}

INCLUDE_RODATA("boss/bo0/nonmatchings/2D26C", D_us_801A9344);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AD338);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AE858);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF31C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF604);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF8C0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AFAF4);

extern EInit g_EInitOlroxAfterImage;

/* EntityOlroxAfterImage: Creates a fading afterimage effect for Olrox, */
/* sets initial appearance from params, then fades opacity each frame. */
void EntityOlroxAfterImage(Entity* entity) {
    if (entity->step == 0) {
        InitializeEntity(g_EInitOlroxAfterImage);
        entity->palette = 0x217;
        entity->drawFlags = DRAW_HIDE;
        entity->opacity = 0x80;
        entity->hitboxState = 0;
        entity->blendMode = BLEND_TRANSP | BLEND_ADD;
        entity->animCurFrame = entity->params;
        entity->zPriority -= 2;
    }
    entity->opacity -= 2;
    if (entity->opacity == 0) {
        DestroyEntity(entity);
    }
}

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801B001C);
