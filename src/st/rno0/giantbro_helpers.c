// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CD658);

// unused debug function
void func_801CD734() {
    while (PadRead(0))
        func_801CD658();
    while (!PadRead(0))
        func_801CD658();
}

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CD78C_801C9A60);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", polarPlacePart);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CD91C);

// unused
void func_801CDA14(Entity* ent1, Entity* ent2) {
    Entity* temp_a0;

    temp_a0 = ent1->ext.GH_Props.parent;
    // Need to cast the entities to Point32 to account for PosX/PosY actually
    // being a Point of two F32 values.
    func_801CD78C_801C9A60((Point32*)temp_a0, temp_a0->ext.GH_Props.length,
                  temp_a0->ext.GH_Props.rotate, (Point32*)ent1);
    func_801CD78C_801C9A60((Point32*)ent1, ent2->ext.GH_Props.length,
                  ent2->ext.GH_Props.rotate, (Point32*)ent2);
}

// unused
void func_801CDA6C(Entity* self, s32 arg1) {
    Entity* temp_s0;

    temp_s0 = self->ext.GH_Props.parent;
    func_801CD78C_801C9A60((Point32*)self, -self->ext.GH_Props.length,
                  self->ext.GH_Props.rotate, (Point32*)temp_s0);
    func_801CD78C_801C9A60((Point32*)temp_s0, -temp_s0->ext.GH_Props.length,
                  temp_s0->ext.GH_Props.rotate, (Point32*)arg1);
}

void func_801CDAC8(Entity* ent1, Entity* ent2) {
    Point32 sp10;
    s16 temp_s6;
    Point32* parentPos;
    s32 temp_s4;
    s32 temp_s3;
    s32 temp_s2;
    s32 ratanX;
    s32 ratanY;

    parentPos = (Point32*)ent1->ext.GH_Props.parent;
    ratanX = ent2->posX.val - parentPos->x;
    if (g_CurrentEntity->facingLeft) {
        ratanX = -ratanX;
    }
    ratanY = ent2->posY.val - parentPos->y;
    temp_s6 = ratan2(-ratanX, ratanY);
    temp_s4 = ent1->ext.GH_Props.length << 8;
    temp_s3 = ent2->ext.GH_Props.length << 8;
    ratanX = ratanX >> 8;
    ratanY = ratanY >> 8;
    temp_s2 = SquareRoot0((ratanX * ratanX) + (ratanY * ratanY));
    if (((temp_s4 + temp_s3) << 8) < temp_s2) {
        temp_s2 = ((temp_s4 + temp_s3) << 8);
    }
    temp_s2 = (temp_s2 * temp_s4) / (temp_s4 + temp_s3);
    temp_s3 = (temp_s4 * temp_s4) - (temp_s2 * temp_s2);
    temp_s3 = SquareRoot0(temp_s3);
    temp_s6 += ratan2(temp_s3, temp_s2);
    ent1->ext.GH_Props.unkA4 = temp_s6;
    func_801CD78C_801C9A60(parentPos, ent1->ext.GH_Props.length, temp_s6, &sp10);
    ratanX = ent2->posX.val - sp10.x;
    if (g_CurrentEntity->facingLeft) {
        ratanX = -ratanX;
    }
    ratanY = ent2->posY.val - sp10.y;
    ent2->ext.GH_Props.unkA4 = ratan2(-ratanX, ratanY);
}

bool func_801CDC80(s16* arg0, s16 arg1, s16 arg2) {
    if (abs(*arg0 - arg1) < arg2) {
        *arg0 = arg1;
        return true;
    }

    if (*arg0 > arg1) {
        *arg0 -= arg2;
    }

    if (*arg0 < arg1) {
        *arg0 += arg2;
    }

    return false;
}

void func_801CDD00(Entity* entity, s16 arg1, s16 arg2) {
    s16 temp_t0 = arg1 - entity->ext.GH_Props.rotate;

    if (temp_t0 > 0x800) {
        temp_t0 = temp_t0 - 0x1000;
    }

    if (temp_t0 < -0x800) {
        temp_t0 = temp_t0 + 0x1000;
    }

    temp_t0 = temp_t0 / arg2;
    entity->ext.GH_Props.rotVel = temp_t0;
    entity->ext.GH_Props.unkA4 = arg1;
}

void func_801CDD80(s16* entOffsets, unkStr_801CDD80* arg1) {
    Entity* var_s1;
    s16* ptr = arg1->unk4;

    while (*entOffsets) {
        if (*entOffsets != 0xFF) {
            var_s1 = g_CurrentEntity + *entOffsets;
            func_801CDD00(var_s1, *ptr, arg1->unk0);
        }
        ptr++;
        entOffsets++;
    }
}

void func_801CDE10(s16* entOffsets) {
    Entity* ent;

    while (*entOffsets) {
        if (*entOffsets != 0xFF) {
            ent = g_CurrentEntity + *entOffsets;
            ent->ext.GH_Props.rotate += ent->ext.GH_Props.rotVel;
        }
        entOffsets++;
    }
}

void polarPlacePartsWithAngvel(s16* entOffsets) {
    Entity* ent;

    while (*entOffsets) {
        if (*entOffsets != 0xFF) {
            ent = g_CurrentEntity + *entOffsets;
            ent->ext.GH_Props.rotate += ent->ext.GH_Props.rotVel;
            polarPlacePart(ent);
        }
        entOffsets++;
    }
}

void func_801CDF1C(s16 entIndices[], unkStr_801CDD80* arg1, s32 arg2) {

    arg1 += (u16)g_CurrentEntity->ext.GH_Props.unkB0[arg2];

    if (!g_CurrentEntity->ext.GH_Props.unkB4[arg2]) {
        func_801CDD80(entIndices, arg1);
        g_CurrentEntity->ext.GH_Props.unkB4[arg2] = arg1->unk0;
    }
    if (!--g_CurrentEntity->ext.GH_Props.unkB4[arg2]) {
        arg1++;
        if (!arg1->unk0) {
            g_CurrentEntity->ext.GH_Props.unkB0[arg2] = 0;
        } else {
            ++g_CurrentEntity->ext.GH_Props.unkB0[arg2];
        }
    }
}

void func_801CDFD8(Entity* self, s32 arg1) {
    if (!self->ext.GH_Props.unkB4[0]) {
        func_801CDD00(self, self->ext.GH_Props.unkA4, arg1);
        self->ext.GH_Props.unkB4[0] = arg1;
    }
    self->ext.GH_Props.unkB4[0]--;
    self->ext.GH_Props.rotate += self->ext.GH_Props.rotVel;
    polarPlacePart(self);
}

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CE04C);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CE120);

// Resets a Giant Brother's step/pose state and clears its per-limb timers.
// See func_801CE228 below for the matching out-of-bounds write: unkB0 and
// unkB4 are each only 2 elements, but this loop runs 4 times, so the last
// two iterations spill unkB0 writes into unkB4 (and unkB4 out past the end).
void func_801CE1E8(s32 step) {
    s32 i;
    g_CurrentEntity->step = step;
    g_CurrentEntity->step_s = 0;
    g_CurrentEntity->pose = 0;
    g_CurrentEntity->poseTimer = 0;
    for (i = 0; i < 4; i++) {
        g_CurrentEntity->ext.GH_Props.unkB0[i] = 0;
        g_CurrentEntity->ext.GH_Props.unkB4[i] = 0;
    }
}

void func_801CE228() {
    s32 i;
    // BUG: Array out of bounds writing. Possible explanation:
    // unkB0 was originally a 4-element array. This loop would iterate
    // through the 4 elements and write each to zero.
    // At some point, unkB0 got split to two arrays, unkB0 and unkB4.
    // Now we zero out both arrays. But since each one is only 2 elements,
    // the loop should only be `i < 2`. They forgot to change it. This means
    // that for i = 2 and i = 3, the unkB0 writes are writing into unkB4,
    // and the unkB4 is writing totally out of bounds.
    // As far as we know, this bug does not have any consequences.
    for (i = 0; i < 4; i++) {
        g_CurrentEntity->ext.GH_Props.unkB0[i] = 0;
        g_CurrentEntity->ext.GH_Props.unkB4[i] = 0;
    }
}

// Polar Knight parts placement: iterates through a sentinel-terminated list
// of sub-entity indices and calls polarPlacePart for any entity whose ext
// initialization byte (offset 0x2C) is still zero.
void polarPlacePartsList(s16* partsList) {
    s16* iter = partsList;
    s16 index;
    Entity* entity;

    while (*iter != 0) {
        index = *iter;
        entity = &g_CurrentEntity[index];
        iter++;
        if (entity->ext.ILLEGAL.u8[0x2C] == 0) {
            polarPlacePart(entity);
        }
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CE2CC);

INCLUDE_ASM("st/rno0/nonmatchings/giantbro_helpers", func_801CE3FC);
