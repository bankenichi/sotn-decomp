// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno1.h"

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

void ParanthropusSetStep(u16 step) {
    g_CurrentEntity->pose = 0;
    g_CurrentEntity->poseTimer = 0;
    g_CurrentEntity->ext.paranthropus.unk7C = 0;
    g_CurrentEntity->ext.paranthropus.unk7E = false;
    g_CurrentEntity->step = step;
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_34074", EntityParanthropus);

INCLUDE_ASM("st/rno1/nonmatchings/unk_34074", EntityParanthropusThrownBone);

INCLUDE_ASM("st/rno1/nonmatchings/unk_34074", EntityParanthropusBoneHitbox);

INCLUDE_ASM("st/rno1/nonmatchings/unk_34074", EntityParanthropusSkull);
