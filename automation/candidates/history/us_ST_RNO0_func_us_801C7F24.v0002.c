/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO0:func_us_801C7F24
   attempt: 1/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (calls declared)
   origin : src/st/rno0/e_stone_skull.c
   asm    : asm/us/st/rno0/nonmatchings/e_stone_skull/func_us_801C7F24.s

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
void MoveEntity();
int FntPrint(const char* fmt, ...);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int AnimateEntity();
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitStoneSkull;
extern u16 g_pads_1_pressed;
extern Tilemap g_Tilemap;

extern EInit g_EInitStoneSkull;
extern u16 g_pads_1_pressed;
extern u8 D_us_80181E8C[];

void func_us_801C7F24(Entity* self) {
    s32 posY;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitStoneSkull);
        self->drawFlags = ENTITY_OPACITY;
        self->opacity = 0xD0;
        self->ext.stoneSkull.startingPosY =
            g_Tilemap.scrollY.i.hi + self->posY.i.hi;
        self->velocityY = FIX(1.0);
         
    case 1:
        AnimateEntity(D_us_80181E8C, self);
        MoveEntity();
        posY = self->posY.i.hi + g_Tilemap.scrollY.i.hi;
        posY = self->ext.stoneSkull.startingPosY - posY;
        if (self->velocityY > 0) {
            posY += self->params;
        } else {
            posY -= self->params;
        }

        if (posY < 0) {
            self->velocityY -= FIX(0.125);
            if (self->velocityY < FIX(-1.0)) {
                self->velocityY = FIX(-1.0);
            }
        } else {
            self->velocityY += FIX(0.125);
            if (self->velocityY > FIX(1.0)) {
                self->velocityY = FIX(1.0);
            }
        }
        break;

    case 0xFF:
        FntPrint("charal %x\n", self->animCurFrame);
        if (g_pads_1_pressed & 0x80) {
            if (self->params == 0) {
                self->animCurFrame++;
                self->params |= 1;
            }
        } else {
            self->params = 0;
        }
        if (g_pads_1_pressed & 0x20) {
            if (self->step_s == 0) {
                self->animCurFrame--;
                self->step_s |= 1;
            }
        } else {
            self->step_s = 0;
        }
        break;
    }
}
