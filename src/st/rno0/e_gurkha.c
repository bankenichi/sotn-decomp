// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// Gurkha entity 15: sync rotation to parent's rotation + offset (0x300 = approx. 270 degrees)
void func_801CF778(void) {
    Entity* currEnt15;
    Entity* ent15Parent;
    currEnt15 = g_CurrentEntity + 15;
    ent15Parent = currEnt15->ext.GH_Props.parent;
    currEnt15->ext.GH_Props.rotate = ent15Parent->ext.GH_Props.rotate + 0x300;  // 0x300 angle offset
}

INCLUDE_ASM("st/rno0/nonmatchings/e_gurkha", func_801CF7A0);

INCLUDE_ASM("st/rno0/nonmatchings/e_gurkha", EntityGurkha);

INCLUDE_ASM("st/rno0/nonmatchings/e_gurkha", EntityGurkhaWeapon);
