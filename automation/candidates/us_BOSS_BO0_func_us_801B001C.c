/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO0:func_us_801B001C
   attempt: 4/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (stubs declared)
   origin : src/boss/bo0/2D26C.c
   asm    : asm/us/boss/bo0/nonmatchings/2D26C/func_us_801B001C.s

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

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

// This file covers 0x2D26C..0x3053C. Everything from 0x3053C up now lives in
// 3053C.c: see the note on that segment in config/splat.us.bobo0.yaml for why
// the split had to happen.

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AD26C);

// Checks whether the tile at (x, y) is solid ground.
s32 func_us_801AD2F0(s16 x, s16 y) {
    Collider col;

    g_api.CheckCollision(x, y, &col, 0);
    return col.effects & EFFECT_SOLID;
}

INCLUDE_RODATA("boss/bo0/nonmatchings/2D26C", D_us_801A9344);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AD338);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AE858);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF31C);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF604);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AF8C0);

INCLUDE_ASM("boss/bo0/nonmatchings/2D26C", func_us_801AFAF4);

extern EInit g_EInitOlroxAfterImage;

/* EntityOlroxAfterImage: Creates a fading afterimage effect for Olrox, */
/* sets initial appearance from params, then fades opacity each frame. */
void EntityOlroxAfterImage(Entity* entity) {
    if (entity->step == 0) {
        InitializeEntity(g_EInitOlroxAfterImage);
        entity->palette = 0x217;
        entity->drawFlags = DRAW_HIDE;
        entity->opacity = 0x80;
        entity->hitboxState = 0;
        entity->blendMode = BLEND_TRANSP | BLEND_ADD;
        entity->animCurFrame = entity->params;
        entity->zPriority -= 2;
    }
    entity->opacity -= 2;
    if (entity->opacity == 0) {
        DestroyEntity(entity);
    }
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitInteractable;
extern Entity g_Entities_224[];

extern EInit g_EInitInteractable;
void InitializeEntity(u16 arg0[]);
extern Entity g_Entities_224[];
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void MoveEntity();
void EntityExplosion(Entity*);
s32 GetSideToPlayer();
void PlaySfxPositional(s32 arg0);
s32 func_us_801AD2F0(s16 arg0, s16 arg1);
extern s32 D_us_80180BA8;
extern u8 D_us_80180D94[];

void func_us_801B001C(Entity* self) {
    s32 i;
    s32 s3;
    Entity* newEntity;
    u8 params;
    s16 hitboxData;
    s16 posX;
    s16 posY;
    s32 velocity;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        self->animSet = -0x7FFA;
        self->unk5A = 0x48;
        self->palette = 0x209;
        self->hitboxState = 2;
        if (self->params & 0x100) {
            self->facingLeft = 1;
        }
        self->zPriority -= 4;
        if (self->params == 1) {
            D_us_80180BA8 = 0;
        }
        params = (u8)self->params;
        self->animCurFrame = params;
        if (params < 5) {
            u8* data = &D_us_80180D94[(params - 1) * 12];
            self->hitboxWidth = data[0];
            self->hitboxHeight = data[2];
            self->hitboxOffX = *(u16*)(data + 4);
            self->hitboxOffY = *(u16*)(data + 6);
            self->hitPoints = *(u16*)(data + 8);
            self->zPriority = *(u16*)(data + 10);
            return;
        }
        self->step += params;
        return;

    case 1:
        if (self->flags & 0x100) {
            self->hitboxState = 0;
            self->step += (u8)self->params;
        }
        return;

    case 2:
        self->animCurFrame = 0xA;
        if (GetSideToPlayer() & 1) {
            self->velocityX = 0x10000;
        } else {
            self->velocityX = -0x10000;
        }
        self->step = 0xB;
        return;

    case 3:
        for (i = 0, s3 = 0; i < 4; i++, s3 -= 0x1E) {
            newEntity = AllocEntity(&g_Entities_224, &g_Entities_224[0x1780 / sizeof(Entity)]);
            if (newEntity != NULL) {
                CreateEntityFromEntity(0x2A, self, newEntity);
                newEntity->params = i + 5;
                newEntity->posX.i.hi += 0x30 + s3;
            }
        }
        if (newEntity != NULL) {
            newEntity->params = 0x105;
        }
        for (i = 0, s3 = 0; i < 4; i++, s3 -= 0x1E) {
            newEntity = AllocEntity(&g_Entities_224, &g_Entities_224[0x1780 / sizeof(Entity)]);
            if (newEntity != NULL) {
                CreateEntityFromEntity(2, self, newEntity);
                newEntity->params = 0x13;
                newEntity->posX.i.hi += 0x30 + s3;
            }
        }
        for (i = 0; i < 3; i++) {
            ((s32*)self)[0x3C + i] |= 0x100;
        }
        self->animCurFrame = 0;
        self->step = 0x20;
        return;

    case 4:
        for (i = 0; i < 2; i++) {
            newEntity = AllocEntity(&g_Entities_224, &g_Entities_224[0x1780 / sizeof(Entity)]);
            if (newEntity != NULL) {
                CreateEntityFromEntity(0x2A, self, newEntity);
                newEntity->params = i + 8;
                newEntity->posY.i.hi += i * 8;
                if (i != 0) {
                    if (GetSideToPlayer() & 1) {
                        newEntity->velocityX = 0x8000;
                    } else {
                        newEntity->velocityX = -0x8000;
                    }
                    newEntity->velocityY = -0x10000;
                }
            }
        }
        PlaySfxPositional(0x691);
        self->animCurFrame = 0;
        self->step = 0x20;
        return;

    case 5:
        for (i = 0, s3 = 0; i < 3; i++, s3 += 0x1C) {
            newEntity = AllocEntity(&g_Entities_224, &g_Entities_224[0x1780 / sizeof(Entity)]);
            if (newEntity != NULL) {
                CreateEntityFromEntity(0x2A, self, newEntity);
                newEntity->params = i + 0xB;
                newEntity->posY.i.hi += -0x1C + s3;
            }
        }
        PlaySfxPositional(0x67F);
        self->animCurFrame = 0;
        self->step = 0x20;
        return;

    case 7:
    case 8:
        self->zPriority = 0x6A;
        MoveEntity();
        posX = self->posX.i.hi;
        posY = self->posY.i.hi + 8;
        self->velocityY += 0x1000;
        if (func_us_801AD2F0(posX, posY) != 0) {
            self->step = 0x20;
        }
        return;

    case 9:
        self->zPriority = 0x6C;
        self->drawFlags |= 4;
        self->rotate -= 0x10;
        MoveEntity();
        posX = self->posX.i.hi;
        posY = self->posY.i.hi + 4;
        self->velocityY += 0x1800;
        if (func_us_801AD2F0(posX, posY) != 0) {
            self->entityId = 2;
            self->pfnUpdate = EntityExplosion;
            self->params = 0;
            self->step = 0;
        }
        return;

    case 10:
        self->zPriority = 0x6C;
        self->drawFlags |= 4;
        self->rotate += 0x80;
        MoveEntity();
        posX = self->posX.i.hi;
        posY = self->posY.i.hi;
        self->velocityY += 0x2000;
        if (func_us_801AD2F0(posX, posY) != 0) {
            self->entityId = 2;
            self->pfnUpdate = EntityExplosion;
            self->step = 0;
            self->params = 0;
        }
        return;

    case 11:
        self->zPriority = 0x6A;
        MoveEntity();
        posX = self->posX.i.hi;
        posY = self->posY.i.hi + 0xA;
        self->velocityY += 0x1000;
        if (func_us_801AD2F0(posX, posY) != 0) {
            self->step = 0x20;
        }
        return;

    case 12:
        self->rotate -= 0x30;
        /* fall through */
    case 13:
        self->zPriority = 0x6B;
        self->drawFlags |= 4;
        self->rotate += 0x28;
        MoveEntity();
        posX = self->posX.i.hi;
        posY = self->posY.i.hi + 6;
        self->velocityY += 0x1800;
        if (func_us_801AD2F0(posX, posY) != 0) {
            self->entityId = 2;
            self->pfnUpdate = EntityExplosion;
            self->params = 0;
            self->step = 0;
        }
        return;

    case 6:
    case 14:
        self->zPriority = 0x6A;
        return;
    }
}
