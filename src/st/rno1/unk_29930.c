// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno1.h"

INCLUDE_ASM("st/rno1/nonmatchings/unk_29930", func_us_801B9028_from_no1);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
#define E_ID(name) E_##name
extern EInit g_EInitInteractable;
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);

void func_us_801A9A8C(Entity* self) {
    Entity* child;
    s32 i;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        self->animSet = 0;
        self->animCurFrame = 0;
        child = self + 1;
        i = 1;
        for (; i < 2; i++) {
            CreateEntityFromEntity(E_ID(UNK_2E), self, child);
            child->params = i + 0x100;
            child++;
            CreateEntityFromEntity(E_ID(UNK_2E), self, child);
            child->params = i;
            child++;
        }
    case 1:
    default:
        break;
    }
}


INCLUDE_ASM("st/rno1/nonmatchings/unk_29930", func_us_80198A18_from_rbo4);

INCLUDE_ASM("st/rno1/nonmatchings/unk_29930", func_us_801A9BEC);
