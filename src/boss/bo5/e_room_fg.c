// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo5.h"

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
extern EInit g_EInitCommon;
extern ObjInit D_us_80181804[6];

void EntityRoomForeground(Entity* entity) {
    ObjInit* objInit = &D_us_80181804[entity->params];

    if (!entity->step) {
        InitializeEntity(g_EInitCommon);
        entity->animSet = objInit->animSet;
        entity->zPriority = objInit->zPriority;
        entity->unk5A = objInit->unk5A;
        entity->palette = objInit->palette;
        entity->drawFlags = objInit->drawFlags;
        entity->blendMode = objInit->blendMode;
        if (objInit->flags != 0) {
            entity->flags = objInit->flags;
        }
        if (entity->params > 4) {
            entity->drawFlags |= DRAW_COLORS;
            entity->rotate = ROT(180);
        }
    }
    AnimateEntity(objInit->animFrames, entity);
}


