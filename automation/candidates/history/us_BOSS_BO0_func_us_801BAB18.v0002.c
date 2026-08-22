/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO0:func_us_801BAB18
   attempt: 2/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (calls declared)
   origin : src/boss/bo0/3AB18.c
   asm    : asm/us/boss/bo0/nonmatchings/3AB18/func_us_801BAB18.s

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
#include "bo0.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void PlaySfxPositional(s32 arg0);
/* End permuter-seed writer declarations. */


/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;
extern u32 g_Timer;
extern u16 g_pads_1_pressed;

extern s32 D_us_80181190[];
extern u8 D_us_80180738[];
void InitializeEntity(u16 arg0[]);
extern GAME_IMPORT Tilemap g_Tilemap;
extern s16 D_us_801813A4[];
extern s16 D_us_80181374[];
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
void MoveEntity();
extern GAME_IMPORT u32 g_Timer;
extern s16 D_us_801813BC[];
extern s16 D_us_8018138C[];
void DestroyEntity(Entity*);
extern u8 D_us_801A9678[];
int FntPrint(const char* fmt, ...);
extern u16 g_pads_1_pressed;
extern s16 PLAYER_posX_i_hi;

/* Boss door entity: handles opening/closing animation and tilemap updates */
void func_us_801BAB18(Entity* self) {
    s32 temp_a0;
    s32 temp_a1;
    s32 var_a3;
    s32 var_t0;
    s32 var_v0;
    s16* var_a1;
    s16* var_a2;
    u16 temp_v1;

    temp_v1 = self->step;
    switch (temp_v1) {
    case 0:
        if (D_us_80181190[0] != 0) {
            DestroyEntity(self);
            return;
        }
        InitializeEntity(D_us_80180738);
        self->zPriority = 0x69;
        if (self->params != 0) {
            self->posX.i.hi = 0x218 - g_Tilemap.scrollX.i.hi;
            if (self->params != 0) {
                var_a1 = D_us_801813A4;
                var_t0 = 0xDD;
            } else {
                var_t0 = 0xC0;
                var_a1 = D_us_80181374;
            }
        } else {
            var_t0 = 0xC0;
            var_a1 = D_us_80181374;
        }
        var_a3 = 0;
        var_a2 = var_a1 + 2;
        do {
            temp_a0 = var_t0 * 2;
            var_t0 += 0x20;
            var_a3 += 1;
            *(u16*)(temp_a0 + (s32)g_Tilemap.fg) = var_a1[0];
            var_a1 += 3;
            *(u16*)(temp_a0 + (s32)g_Tilemap.fg + 2) = var_a2[-1];
            *(u16*)(temp_a0 + (s32)g_Tilemap.fg + 4) = var_a2[0];
            var_a2 += 3;
        } while (var_a3 < 4);
        return;

    case 1:
        if ((PLAYER_posX_i_hi + g_Tilemap.scrollX.i.hi) < 0x1E8) {
            if (self->params != 0) {
                CreateEntityFromEntity(0x49, self, self + 0xBC);
                self->ext.timer.t = 0;
                ((u16*)&self->ext)[0x1E / 2] = (s16)(-0x18 - g_Tilemap.scrollX.i.hi);
            }
            PlaySfxPositional(0x608);
            self->step += 1;
        }
        return;

    case 2:
        if (self->step_s == 0) {
            if (self->params == 0) {
                var_v0 = 0x8000;
            } else {
                var_v0 = -0x8000;
            }
            self->velocityX = var_v0;
            self->step_s += 1;
        }
        GetPlayerCollisionWith(self, 0x18, 0x20, 5);
        MoveEntity();
        if (!(g_Timer & 0xF)) {
            PlaySfxPositional(0x608);
        }
        temp_a1 = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
        if (self->params != 0) {
            if (temp_a1 < 0x1E8) {
                return;
            }
            var_v0 = 0x1E8;
        } else {
            if (temp_a1 < 0x19) {
                return;
            }
            var_v0 = 0x18;
        }
        self->posX.i.hi = var_v0 - g_Tilemap.scrollX.i.hi;
        self->step += 1;
        return;

    case 3:
        if (self->params != 0) {
            var_a1 = D_us_801813BC;
            var_t0 = 0xDD;
        } else {
            var_t0 = 0xC0;
            var_a1 = D_us_8018138C;
        }
        var_a3 = 0;
        var_a2 = var_a1 + 2;
        do {
            temp_a0 = var_t0 * 2;
            var_t0 += 0x20;
            var_a3 += 1;
            *(u16*)(temp_a0 + (s32)g_Tilemap.fg) = var_a1[0];
            var_a1 += 3;
            *(u16*)(temp_a0 + (s32)g_Tilemap.fg + 2) = var_a2[-1];
            *(u16*)(temp_a0 + (s32)g_Tilemap.fg + 4) = var_a2[0];
            var_a2 += 3;
        } while (var_a3 < 4);
        self->step += 1;
        return;

    case 4:
        if (D_us_80181190[0] != 0) {
            self->step += 1;
        }
        return;

    case 5:
        if (self->params != 0) {
            var_a1 = D_us_801813A4;
            var_t0 = 0xDD;
        } else {
            var_t0 = 0xC0;
            var_a1 = D_us_80181374;
        }
        var_a3 = 0;
        var_a2 = var_a1 + 2;
        do {
            temp_a0 = var_t0 * 2;
            var_t0 += 0x20;
            var_a3 += 1;
            *(u16*)(temp_a0 + (s32)g_Tilemap.fg) = var_a1[0];
            var_a1 += 3;
            *(u16*)(temp_a0 + (s32)g_Tilemap.fg + 2) = var_a2[-1];
            *(u16*)(temp_a0 + (s32)g_Tilemap.fg + 4) = var_a2[0];
            var_a2 += 3;
        } while (var_a3 < 4);
        if (self->params == 0) {
            var_v0 = -0x8000;
        } else {
            var_v0 = 0x8000;
        }
        self->velocityX = var_v0;
        self->step += 1;
        return;

    case 6:
        MoveEntity();
        temp_a1 = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
        if (self->params != 0) {
            if (temp_a1 < 0x219) {
                return;
            }
        } else {
            if (temp_a1 >= -0x18) {
                return;
            }
        }
        DestroyEntity(self);
        return;

    case 0xFF:
        FntPrint("charal %x\n", self->animCurFrame);
        if (g_pads_1_pressed & 0x80) {
            if (self->params == 0) {
                self->animCurFrame += 1;
                self->params |= 1;
            }
        } else {
            self->params = 0;
        }
        if (g_pads_1_pressed & 0x20) {
            if (self->step_s == 0) {
                self->animCurFrame -= 1;
                self->step_s |= 1;
            }
        } else {
            self->step_s = 0;
        }
        return;
    }
}
