/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RCEN:func_8018F8EC
   attempt: 3/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (stubs declared)
   origin : src/st/rcen/unk_1F0D8.c
   asm    : asm/us/st/rcen/nonmatchings/unk_1F0D8/func_8018F8EC.s

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
#include "rcen.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int InitializeEntity();

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;

void func_8018F8EC(s32 arg0) {
        u16 *dataPtr;
        s32 tileIndex;
        s32 outerCount;
        s32 innerCount;
    extern u16 D_us_801809FC[];

    dataPtr = (u16 *)((arg0 & 0xFFFF) * 0x10 + (u32)D_us_801809FC);
    tileIndex = 0x316;

    for (outerCount = 0; outerCount < 2; outerCount++) {
        for (innerCount = 0; innerCount < 4; innerCount++) {
            g_Tilemap.fg[tileIndex & 0xFFFF] = *dataPtr;
            dataPtr++;
            tileIndex++;
        }
        tileIndex += 0x2C;
    }
}

INCLUDE_ASM("st/rcen/nonmatchings/unk_1F0D8", func_us_8019F148);

INCLUDE_ASM("st/rcen/nonmatchings/unk_1F0D8", func_us_8019F5F0);

INCLUDE_ASM("st/rcen/nonmatchings/unk_1F0D8", func_us_8019F9C0);

extern EInit g_EInitCommon;
// func_us_8019F5F0's candidate failed to build on this name alone. Declared
// in the shared src/st/e_armor_lord.h:2; kept here so the retry does not hit
// the same wall. An unused extern emits no code.
extern EInit g_EInitInteractable;

// Initializes entity animation/priority on first step, mirroring func_us_801B4148 in bo0/no2_bg
// Verbatim copy of func_us_801B4148 in src/st/no2_bg.h.
// Kept in sync by hand: this file cannot include that header.
void func_us_801B4148_from_bo0(Entity* self) {
    if (self->step == 0) {
        InitializeEntity(g_EInitCommon);
        self->animSet = ANIMSET_OVL(1);
        self->animCurFrame = 6;
        self->zPriority = 0x63;
    }
}

// Initializes entity animation/rotation state on first step, mirroring the NO4 idiom
void func_us_801C123C_from_no4(Entity* self) {
    if (self->step == 0) {
        InitializeEntity(g_EInitCommon);
        // Was the magic number -0x7FFF. ANIMSET_OVL(1) is `1 | 0x8000`, which
        // as a signed 16-bit animSet is exactly -0x7FFF. Twelve lines above,
        // the same value is written the named way; this is the same constant,
        // now spelled consistently. Found by audit 2026-08-02.
        self->animSet = ANIMSET_OVL(1);
        self->animCurFrame = 7;
        self->drawFlags = ENTITY_ROTATE;
        self->rotate = 0x800;
        self->zPriority = self->zPriority + 1;
    }
}
