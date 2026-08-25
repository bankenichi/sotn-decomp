/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO0:func_us_801D2264
   attempt: 3/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (stubs declared)
   origin : src/st/rno0/unk_4F968.c
   asm    : asm/us/st/rno0/nonmatchings/unk_4F968/func_us_801D2264.s

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

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
void DestroyEntity(Entity*);
void UnkPolyFunc2(Primitive* prim);
void MoveEntity();
void UnkPrimHelper(Primitive* prim);
/* End permuter-seed writer declarations. */



// func_us_801D1BF0's candidate failed to build on this name alone. Defined by
// THIS overlay at src/st/rno0/e_init.c:229, not borrowed from another one.
extern EInit g_EInitGorgon;

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CF968);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CFB20);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CFC98);

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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180BE8;
extern Primitive g_PrimBuf[];

void func_us_801D2264(Entity* entity) {
    Primitive* prim;
    Primitive* next;
    s32 primIndex;

    switch (entity->step) {
    case 0:
        InitializeEntity(&D_us_80180BE8);
        entity->drawFlags = 3;
        entity->scaleY = 0;
        entity->scaleX = 0;
        entity->velocityX = -0x18000;
        if (entity->facingLeft) {
            entity->velocityX = 0x18000;
        }
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 2);
        if (primIndex == -1) {
            DestroyEntity(entity);
            return;
        }
        prim = &g_PrimBuf[primIndex];
        entity->primIndex = primIndex;
        entity->ext.prim = prim;
        entity->flags |= 0x800000;
        UnkPolyFunc2(prim, primIndex);
        prim->tpage = 0x1A;
        prim->clut = 0x19C;
        prim->u3 = 0xFF;
        prim->u1 = 0xFF;
        prim->v1 = 0x40;
        prim->v0 = 0x40;
        prim->v3 = 0x5F;
        prim->v2 = 0x5F;
        prim->u2 = 0xE0;
        prim->u0 = 0xE0;
        next = prim->next;
        next->clut = 0x20;
        next->b2 = 0x20;
        next->x2 = 0x300;
        next->y2 = 0x300;
        prim->drawMode = 0x17;
        prim->priority = entity->zPriority;
        break;
    case 1:
        MoveEntity(entity);
        prim = entity->ext.prim;
        next = prim->next;
        next->x1 = entity->posX.i.hi;
        next->y0 = entity->posY.i.hi;
        next->x2 += 0x60;
        next->y2 = next->x2;
        next->b3 -= 6;
        next->tpage += 0x20;
        if (next->b3 < 0x40) {
            next->b3 = 0x40;
        }
        UnkPrimHelper(prim);
        if (next->x2 >= 0xE01) {
            DestroyEntity(entity);
        }
        break;
    }
}
