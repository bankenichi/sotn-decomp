/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO0:func_us_801C7F24
   attempt: 2/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (stubs declared)
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

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitStoneSkull;
extern Tilemap g_Tilemap;
extern u16 g_pads_1_pressed;

extern EInit g_EInitStoneSkull;
void InitializeEntity(u16 arg0[]);
extern GAME_IMPORT Tilemap g_Tilemap;
void MoveEntity();
int FntPrint(const char* fmt, ...);
extern u16 g_pads_1_pressed;
extern u8 D_us_80181E8C[];
void AnimateEntity(u8* anim, Entity* entity);

/* Stone skull entity: moves vertically, bounces off boundaries, debug mode for animation */
void func_us_801C7F24(Entity* self) {
    s32 scrollY;
    s32 diff;
    s32 vel;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitStoneSkull);
        self->drawFlags = 8;
        self->opacity = 0xD0;
        self->velocityY = 0x10000;
        self->ext.stoneSkull.startingPosY = g_Tilemap.scrollY.i.hi + self->posY.i.hi;
        /* fall through */
    case 1:
        AnimateEntity(D_us_80181E8C, self);
        MoveEntity();
        scrollY = g_Tilemap.scrollY.i.hi;
        diff = self->ext.stoneSkull.startingPosY - (self->posY.i.hi + scrollY);
        if (self->velocityY > 0) {
            diff += self->params;
        } else {
            diff -= self->params;
        }
        vel = 0x10000;
        if (diff < 0) {
            vel = -0x10000;
            self->velocityY -= 0x2000;
            if (self->velocityY < -0x10000) {
                self->velocityY = vel;
            }
        } else {
            self->velocityY += 0x2000;
            if (self->velocityY > 0x10000) {
                self->velocityY = vel;
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
