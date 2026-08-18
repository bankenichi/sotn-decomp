/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO0:DrawLaserRing
   attempt: 1/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (stubs declared)
   origin : src/st/rno0/unk_48100.c
   asm    : asm/us/st/rno0/nonmatchings/unk_48100/DrawLaserRing.s

   IMPORT VIA THE SUPERVISOR, NOT DIRECTLY:
       permuter_supervisor.py --import-seeds

   This banner used to say `import.py <this file> <asm>`,
   and that ADVICE CANNOT WORK. The seed is the whole
   source file, so it starts with quoted includes like
   #include "bo0.h" -- and cpp resolves a quoted include
   relative to the DIRECTORY OF THE FILE. From
   automation/candidates/ there is no bo0.h, so the import
   dies with `fatal error: bo0.h: No such file or
   directory` before it ever looks at the C.

   The supervisor gets this right: it writes the body back
   into `origin` above, imports from there so the includes
   resolve, and restores the file afterwards (journalled,
   so a kill cannot leave the edit behind).

   Six BOSS/BO0 records were deferred as `seed-bug` with a
   note blaming a missing `extern func_us_801B171C`. That
   diagnosis was wrong; the seeds were fine and the import
   command in this banner was not. Verified 2026-08-10 by
   running the import and reading the actual error.

   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
void SetGeomScreen(long h);
void SetGeomOffset(long ofx, long ofy);
MATRIX* RotMatrix(SVECTOR* r, MATRIX* m);
MATRIX* RotMatrixZ(long r, MATRIX* m);
MATRIX* RotMatrixY(long r, MATRIX* m);
MATRIX* TransMatrix(MATRIX* m, VECTOR* v);
MATRIX* ScaleMatrix(MATRIX* m, VECTOR* v);
void SetRotMatrix(MATRIX* m);
void SetTransMatrix(MATRIX* m);
long RotTransPers4(
    SVECTOR* v0, SVECTOR* v1, SVECTOR* v2,
    SVECTOR* v3, // Pointers to vectors (input)
    long* v10, long* v11, long* v12,
    long* v13, // Pointers to screen coordinates
    long* p,   // Pointer to interpolated value for depth cueing
    long* flag // Pointer to flag
);
/* End permuter-seed writer declarations. */


INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", TryThrow);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityJackOBones);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityJackOBonesDeathParts);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityJackOBonesJack);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", TryShoot);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

extern SVECTOR D_us_801820F8;
extern SVECTOR D_us_80182100;
extern SVECTOR D_us_80182108;
extern SVECTOR D_us_80182110;

static void DrawLaserRing(void) {
    s32 p;
    s32 flag;
    SVECTOR sp60;
    VECTOR sp50;
    MATRIX sp30;
    SVECTOR sp28 = {0};
    s32 yVar;
    s32 xVar;
    Primitive* prim;
     
    switch (g_CurrentEntity->ext.nova.ringState) {
    case 0:
        g_CurrentEntity->ext.nova.ringSize = 0;
        prim = g_CurrentEntity->ext.nova.prim;
        prim->r0 = prim->g0 = prim->b0 = 0xC0;
        LOW(prim->r1) = LOW(prim->r0);
        LOW(prim->r2) = LOW(prim->r0);
        LOW(prim->r3) = LOW(prim->r0);
        prim->drawMode =
            DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS | DRAW_UNK02 | DRAW_TRANSP;
        g_CurrentEntity->ext.nova.ringState = 1;
        break;
    case 1:
        g_CurrentEntity->ext.nova.ringRot += 0x100;
        g_CurrentEntity->ext.nova.ringSize += 0x200;
        break;
    }
    SetGeomScreen(0x200);
    xVar = g_CurrentEntity->posX.i.hi;
    yVar = g_CurrentEntity->posY.i.hi;
    if (g_CurrentEntity->facingLeft) {
        xVar += 10;
    } else {
        xVar -= 10;
    }
    yVar -= 2;
    SetGeomOffset(xVar, yVar);
    sp60.vx = 0;
    if (g_CurrentEntity->facingLeft) {
        sp60.vy = -0x2E0;
    } else {
        sp60.vy = 0x2E0;
    }
    sp60.vz = g_CurrentEntity->ext.nova.ringRot;
    RotMatrix(&sp28, &sp30);
    RotMatrixZ(sp60.vz, &sp30);
    RotMatrixY(sp60.vy, &sp30);
    sp50.vx = 0;
    sp50.vy = 0;
    sp50.vz = 0x200;
    TransMatrix(&sp30, &sp50);
    sp50.vx = g_CurrentEntity->ext.nova.ringSize;
    sp50.vy = g_CurrentEntity->ext.nova.ringSize;
    sp50.vz = 0x1000;
    ScaleMatrix(&sp30, &sp50);
    SetRotMatrix(&sp30);
    SetTransMatrix(&sp30);
    prim = g_CurrentEntity->ext.nova.prim;
    RotTransPers4(&D_us_801820F8, &D_us_80182100, &D_us_80182108, &D_us_80182110,
                  (long*)&prim->x0, (long*)&prim->x1, (long*)&prim->x2,
                  (long*)&prim->x3, (long*)&p, (long*)&flag);
}

INCLUDE_RODATA("st/rno0/nonmatchings/unk_48100", D_us_801B5D8C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityNovaSkeleton);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityBladeSoldierDeathParts);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityNovaLaser);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityNovaLaserPulse);
