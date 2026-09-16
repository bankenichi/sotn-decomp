/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO0:func_us_801CFD70
   attempt: 1/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (calls declared)
   origin : src/st/rno0/unk_4F968.c
   asm    : asm/us/st/rno0/nonmatchings/unk_4F968/func_us_801CFD70.s

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
extern void (*g_api_CheckCollision)(s32 x, s32 y, Collider* res, s32 unk);
void InitializeEntity(u16 arg0[]);
void MoveEntity();
u8 AnimateEntity(u8 frames[], Entity* entity);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

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

void func_us_801CFD70(s32 arg0)
{
  Primitive *prim;
  s32 i;
  u16 palette;
  volatile short pad;
  u8 unkA8;
  prim = g_CurrentEntity->ext.prim;
  i = 0;
  if (arg0 > 0)
  {
    do
    {
      unkA8 = ((u8 *) g_CurrentEntity)[0xA8];
      if (unkA8 == 0)
      {
        prim->clut = 0x232;
        prim->priority = 0x72;
      }
      else
      {
        prim->clut = 0x233;
        prim->priority = 0x6E;
      }
      palette = g_CurrentEntity->palette;
      i++;
      if (palette & 0x8000)
      {
        prim->clut = palette & 0xFFF;
      }
      prim = prim->next;
    }
    while (i < arg0);
  }
  if ((char) (arg0 > 0))
  {
    i = 0;
    do
    {
      unkA8 = ((u8 *) g_CurrentEntity)[0xA8];
      if (unkA8 == 0)
      {
        prim->clut = 0x233;
        prim->priority = 0x6E;
      }
      else
      {
        prim->clut = 0x232;
        prim->priority = 0x72;
      }
      palette = g_CurrentEntity->palette;
      i++;
      if (palette & 0x8000)
      {
        prim->clut = palette & 0xFFF;
      }
      prim = prim->next;
    }
    while (i < arg0);
  }
}


INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CFE6C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801CFEA0);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D068C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D0CFC);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D136C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D15C0);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D1BF0);

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D2038);

extern s16 D_us_8018333C[];

void func_us_801D21C8(Entity* entity) {
    u16 step;
    s32 animResult;

    step = entity->step;
    switch (step) {
    case 0:
        InitializeEntity(g_EInitGorgon);
        entity->zPriority = 0x72;
        entity->palette = 0x8235;
        entity->velocityY = -0xC000;
        break;
    case 1:
        MoveEntity();
        animResult = AnimateEntity(D_us_8018333C, entity);
        if (animResult == 0) {
            DestroyEntity(entity);
        }
        break;
    default:
        break;
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/unk_4F968", func_us_801D2264);
