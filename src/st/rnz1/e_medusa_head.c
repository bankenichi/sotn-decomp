// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

INCLUDE_ASM("st/rnz1/nonmatchings/e_medusa_head", EntityMedusaHeadSpawner);

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
void EntityMedusaHeadBlue(Entity* self);

void EntityMedusaHeadYellow(Entity* self) {
    self->params = 1;
    EntityMedusaHeadBlue(self);
}



INCLUDE_ASM("st/rnz1/nonmatchings/e_medusa_head", EntityMedusaHeadBlue);
