// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// func_us_801D1BF0's candidate failed to build on this name alone. Defined by
// THIS overlay at src/st/rno0/e_init.c:229, not borrowed from another one.
extern EInit g_EInitGorgon;

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CF968);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CFB20);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

// Checks wall collisions on two Y positions offset from entity center.
s32 func_us_801CFC98(Entity* arg0, s32 arg1) {
    Collider collider;
    s32 posX;
    s32 result;
    s32 counter;
    s32 checkY;

    posX = arg0->posX.i.hi;
    if (arg1 != g_CurrentEntity->facingLeft) {
        posX += 0x38;
    } else {
        posX -= 0x38;
    }
    result = 0;
    counter = 0;
    checkY = arg0->posY.i.hi + 4;
    do {
        g_api_CheckCollision(posX, checkY, &collider, 0);
        if (counter != 0) {
            if (!(collider.effects & 1)) {
                result |= 2;
            }
        } else {
            if (collider.effects & 1) {
                result |= 1;
            }
        }
        counter++;
        checkY += 4;
    } while (counter < 2);
    return result;
}

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CFD70);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CFE6C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CFEA0);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D068C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D0CFC);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D136C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D15C0);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D1BF0);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D2038);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D21C8);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D2264);
