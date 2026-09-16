/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNZ1:func_us_801BCB9C
   attempt: 1/4
   model  : muse-spark-1.3-contributor-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (calls declared)
   origin : src/st/rnz1/unk_3BE58.c
   asm    : asm/us/st/rnz1/nonmatchings/unk_3BE58/func_us_801BCB9C.s

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
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void PlaySfxPositional(s32 arg0);
void SetStep(u8 step);
void InitializeEntity(u16 arg0[]);
void MoveEntity();
extern void (*g_api_CheckCollision)(s32 x, s32 y, Collider* res, s32 unk);
u8 AnimateEntity(u8 frames[], Entity* entity);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
s32 Random();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BBE58);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BC650);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCA5C);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180C60;
extern s32 D_us_8018224C[]; /* retained ST/RNZ1 data asm/us/st/rnz1/data/1E68.data.s, size 0x8 */
extern Entity g_Entities_224[];

void func_us_801BCB9C(Entity* self) {
    Collider collider;
    Entity* newEntity;
    s32 loopIndex;
    s32 velocityX;
    if (self->flags & 0x100) {
        if (self->step != 2) {
            self->hitboxState = 0;
            PlaySfxPositional(0x643);
            SetStep(2);
        }
    }
    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180C60);
        velocityX = 0x20000;
        if (self->params == 0) {
            velocityX = 0x10000;
        }
        self->velocityX = velocityX;
        self->velocityY = 0xFFFE0000;
        if (self->facingLeft == 0) {
            self->velocityX = -self->velocityX;
        }
    case 1:
        MoveEntity();
        self->velocityY += 0x2000;
        g_api_CheckCollision(self->posX.i.hi, self->posY.i.hi + 8, &collider, 0);
        if (collider.effects & 1) {
            PlaySfxPositional(0x643);
            self->hitboxState = 0;
            SetStep(2);
            return;
        }
        return;
    case 2:
        loopIndex = 0;
        if (AnimateEntity(D_us_8018224C, self) == 0) {
            do {
                newEntity = AllocEntity(g_Entities_224, g_Entities_224 + 32);
                loopIndex += 1;
                if (newEntity != NULL) {
                    CreateEntityFromEntity(0x46, self, newEntity);
                    newEntity->params = Random() & 7;
                }
            } while (loopIndex < 7);
            self->pfnUpdate = EntityExplosion;
            self->step = 0;
            self->params = 0x13;
            self->pose = 0;
            self->poseTimer = 0;
        }
        break;
    }
}


INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCD80);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCE4C);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BCFC8);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BD0EC);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BD184);

// Grindy crushy platform things.
// params 0 = one-wide, params 1 = three-wide
INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BD324);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BD398);

INCLUDE_ASM("st/rnz1/nonmatchings/unk_3BE58", func_us_801BDA24);
