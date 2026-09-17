/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   generator: upstream-harvest-v4-preserved-overlay-conditionals
   record : us:ST/RNZ1:func_us_801AB380
   upstream: upstream/master
   source : d5e5165b67cf38746ee7f56eb3e420f7067ecdd6:src/st/rnz1/e_dw_batwings.c
   target : src/st/rnz1/unk_29914.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Compile-shaping declarations retained from the score-zero
   receipt after destination-scope filtering. */
int abs(int x);

#include "../approach_s16.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
MATRIX* RotMatrix(SVECTOR* r, MATRIX* m);
MATRIX* RotMatrixY(long r, MATRIX* m);
MATRIX* RotMatrixX(long r, MATRIX* m);
MATRIX* RotMatrixZ(long r, MATRIX* m);
void SetGeomScreen(long h);
MATRIX* TransMatrix(MATRIX* m, VECTOR* v);
void SetTransMatrix(MATRIX* m);
void SetGeomOffset(long ofx, long ofy);
long RotTransPers(SVECTOR*, long*, long*, long*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetMulMatrix();
/* End permuter-seed writer declarations. */



INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801A9994);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801A9DB8);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", EntityFrozenShadeCrystal);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AAF00);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB04C);

void func_801B2CF8(Primitive* prim) {
    s32 i;
    // Clear the complete object one word at a time, starting at its real first
    // member. The target uses a word loop rather than individual fields.
    s32* ptr = (s32*)&prim->next;
    s32 size = sizeof(*prim) / sizeof(*ptr);

    for (i = 0; i < size; i++) {
        *ptr++ = 0;
    }
}



void func_us_801AB16C(s32* src, s32* dst, s32 count) {
    s32 i;

    // CODEGEN: The target overwrites incoming a2 with 13, then uses a register
    // slt. Keeping the bound in the third parameter preserves that exact shape.
    count = 13;

    for (i = 0; i < count; i++) {
        *dst++ = *src++;
    }
}


INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB198);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

Primitive* func_us_801AB380(
    batWingStruct* arg0, Primitive* prim, SVECTOR** arg2) {
    s16 transX;
    s16 transY;
    long spA8;
    long spA4;
    long spA0;
    long sp9C;
    long sp98;
    SVECTOR rotVec;
    VECTOR transVec;
    MATRIX sp60;
    MATRIX m;
    Primitive* prevPrim;
    s16 xOffset;
    s16 yOffset;
    s16 transZ;
    s16 rotX;
    s16 rotY;
    s16 rotZ;
    s32 i;
    s32 zOffset;
    s32 stackpad1[8];
    SVECTOR sp38 = {0};
    s32 stackpad2[2];
    Entity* mainBat;

    rotVec.vx = g_CurrentEntity->ext.batwing.rotX;
    rotVec.vy = g_CurrentEntity->ext.batwing.rotY;
    rotVec.vz = g_CurrentEntity->ext.batwing.rotZ;
    RotMatrix(&sp38, &m);
    RotMatrixY(rotVec.vy, &m);
    RotMatrixX(rotVec.vx, &m);
    RotMatrixZ(rotVec.vz, &m);
    mainBat = g_CurrentEntity - 1;
    if (mainBat->facingLeft) {
        RotMatrixY(ROT(180), &m);
    }
    xOffset = arg0->unk30;
    yOffset = arg0->unk32;
    transX = 0;
    transY = 0;
    transZ = g_CurrentEntity->ext.batwing.transZ;
    rotX = arg0->unkC;
    rotY = arg0->unkE;
    rotZ = arg0->unk10 / 0x100;
    SetGeomScreen(0x180);
    for (i = 0; i < 2; i += 1) {
        rotVec.vx = rotX;
        rotVec.vy = rotY;
        if (arg0->unk2C) {
            rotVec.vy = -rotVec.vy;
        }
        rotVec.vz = rotZ;
        if (arg0->unk2C) {
            rotVec.vz = -rotVec.vz;
        }
        RotMatrix(&sp38, &sp60);
        RotMatrixY(rotVec.vy, &sp60);
        RotMatrixZ(rotVec.vz, &sp60);
        RotMatrixX(rotVec.vx, &sp60);
        SetMulMatrix(&m, &sp60);
        transVec.vx = transX;
        transVec.vy = transY;
        transVec.vz = transZ;
        TransMatrix(&sp60, &transVec);
        SetTransMatrix(&sp60);
        SetGeomOffset(xOffset, yOffset);
        zOffset = RotTransPers(*arg2, &spA8, &sp9C, &sp98);
        arg2++;
        zOffset = zOffset + RotTransPers(*arg2, &spA4, &sp9C, &sp98);
        arg2++;
        zOffset /= 2;

        rotVec.vx = rotX;
        rotVec.vy = 0;
        rotVec.vz = rotZ;
        if (arg0->unk2C) {
            rotVec.vz = -rotVec.vz;
        }
        RotMatrix(&sp38, &sp60);
        RotMatrixY(rotVec.vy, &sp60);
        RotMatrixZ(rotVec.vz, &sp60);
        RotMatrixX(rotVec.vx, &sp60);
        SetMulMatrix(&m, &sp60);
        RotTransPers(*arg2, &spA0, &sp9C, &sp98);
        arg2++;
        if (i == 0) {
            xOffset = prim->x1 = (u16)spA8;
            yOffset = prim->y1 = spA8 >> 0x10;
            LOW(prim->x0) = spA4;
            LOW(prim->x2) = spA0;
            transZ = zOffset * 4;
            rotX = arg0->unk20;
            rotY = arg0->unk24;
            rotZ = arg0->unk28 / 0x100;
        } else {
            LOW(prim->x1) = spA8;
            prim->x0 = prevPrim->x1;
            prim->y0 = prevPrim->y1;
            LOW(prim->x3) = spA4;
            LOW(prevPrim->x3) = LOW(prim->x2) = spA0;
        }
        prim->priority = ((g_CurrentEntity->zPriority +
                           g_CurrentEntity->ext.batwing.transZ / 4) -
                          zOffset);
        prevPrim = prim;
        prim = prim->next;
    }
    return prim;
}


INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801AB768);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801ABA38);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801ABB58);

void RNZ1_Unused801ABDC0(void) {}

void func_us_801ABDC8(s32* values) {
    values[0] -= 0x400;
    values[5] -= 0x400;
}


INCLUDE_RODATA("st/rnz1/nonmatchings/unk_29914", D_us_801A6050);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", func_us_801ABDE4);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", EntityBossDoorTrigger);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_29914", EntityBossDoors);
