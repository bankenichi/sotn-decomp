// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

INCLUDE_ASM("st/rno0/nonmatchings/e_medusa_head", EntityMedusaHeadSpawner);

void EntityMedusaHeadBlue(Entity* self);

// Medusa head (yellow variant): set params to 1 and delegate to blue variant
void EntityMedusaHeadYellow(Entity* self) {
    self->params = 1;
    EntityMedusaHeadBlue(self);
}

INCLUDE_ASM("st/rno0/nonmatchings/e_medusa_head", EntityMedusaHeadBlue);
