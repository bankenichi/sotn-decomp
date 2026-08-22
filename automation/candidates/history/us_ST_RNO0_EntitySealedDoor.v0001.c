/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO0:EntitySealedDoor
   attempt: 2/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (calls declared)
   origin : src/st/rno0/unk_5289C.c
   asm    : asm/us/st/rno0/nonmatchings/unk_5289C/EntitySealedDoor.s

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
int abs(int x);
/* End permuter-seed writer declarations. */

bool func_us_801D289C(Entity* self) {
    s16 distanceX;
    s16 diffX;
    s16 distanceY;
    s16 diffY;

    diffX = PLAYER.posX.i.hi - self->posX.i.hi;
    distanceX = abs(diffX);
    if (distanceX > 24) {
        return false;
    }

    diffY = PLAYER.posY.i.hi - self->posY.i.hi;
    distanceY = abs(diffY);
    if (distanceY > 32) {
        return false;
    }

    return true;
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Primitive g_PrimBuf[];
extern PlayerState g_Player;
extern s32 g_PlayableCharacter;
extern PlayerStatus g_Status;
extern Entity g_Entities_224[];

extern EInit RNO0_EInitCommon;
void InitializeEntity(u16 arg0[]);
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
void DestroyEntity(Entity*);
extern u8 D_us_801833CC[];
extern GAME_IMPORT Primitive g_PrimBuf[];
extern GAME_IMPORT PlayerState g_Player;
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags);
extern GAME_IMPORT s32 g_PlayableCharacter;
extern GAME_IMPORT PlayerStatus g_Status;
extern Entity g_Entities_224[];
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
extern s32 D_us_80183424[];
extern void (*g_api_PlaySfx)(s32 sfxId);
extern u16 PLAYER_zPriority;
extern s32 PLAYER_velocityY;
extern u16 PLAYER_facingLeft;
extern u16 PLAYER_step;

s32 GetSideToPlayer(void);
s32 func_us_801D289C(Entity*);

void EntitySealedDoor(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s32 i;
    s16 angle;
    s16 angleTarget;
    s16 posX;
    s16 posY;
    s16 temp;
    u8* dataPtr;
    u8* dataPtr2;
    Entity* newEntity;
    s32 sideToPlayer;
    s32 playerStep;
    s32 primIndexCalc;

    switch (self->step) {
    case 0:
        InitializeEntity(&RNO0_EInitCommon);
        self->animSet = 0;
        self->animCurFrame = 1;
        self->palette = 0x259;
        self->facingLeft = 0;
        self->zPriority = PLAYER_zPriority - 0x20;
        self->posY.i.hi += 0x1F;
        if (self->params & 0x100) {
            self->ext.sealedDoor.unk86 = -4;
        } else {
            self->ext.sealedDoor.unk86 = 4;
        }
        self->posX.i.hi += self->ext.sealedDoor.unk86;
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 4);
        self->primIndex = primIndex;
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        dataPtr = D_us_801833CC;
        prim = &g_PrimBuf[self->primIndex];
        self->flags |= 0x800000;
        posY = self->posY.i.hi;
        i = 0;
        if (prim->next != NULL) {
            dataPtr2 = &D_us_801833CC[7];
            do {
                prim->u0 = dataPtr[0];
                prim->u1 = dataPtr2[-6];
                prim->u2 = dataPtr2[-5];
                prim->u3 = dataPtr2[-4];
                prim->v0 = dataPtr2[-3];
                prim->v1 = dataPtr2[-2];
                prim->v2 = dataPtr2[-1];
                prim->tpage = 0x15;
                prim->clut = 0x258;
                prim->v3 = dataPtr2[0];
                prim->y1 = posY - 0x1F;
                prim->y0 = posY - 0x1F;
                prim->y3 = posY + 0x1F;
                prim->y2 = posY + 0x1F;
                prim->priority = PLAYER_zPriority - 0x20;
                if (i == 0) {
                    prim->y1 = posY - 0x1F;
                    prim->y0 = posY - 0x1F;
                    prim->y3 = posY + 0x1F;
                    prim->y2 = posY + 0x1F;
                }
                prim->g0 = 0x7F;
                prim->b0 = 0x7F;
                prim->r0 = 0x7F;
                prim->drawMode = 6;
                prim->r1 = prim->r0;
                prim->r2 = prim->r0;
                prim->r3 = prim->r0;
                if (i == 2) {
                    if (!(self->params & 0x100)) {
                        prim->drawMode |= 8;
                    }
                }
                dataPtr2 += 8;
                if ((i == 1) && (self->params & 0x100)) {
                    prim->drawMode |= 8;
                }
                i++;
                prim = prim->next;
                dataPtr += 8;
            } while (prim->next != NULL);
        }
        prim->tpage = 0x15;
        prim->u2 = 0x40;
        prim->u0 = 0x40;
        prim->u3 = 0x50;
        prim->u1 = 0x50;
        prim->v1 = 0;
        prim->v0 = 0;
        prim->v3 = 0x48;
        prim->v2 = 0x48;
        prim->clut = self->palette;
        posX = self->posX.i.hi - 8;
        prim->x2 = posX;
        prim->x0 = posX;
        posX = self->posX.i.hi + 8;
        prim->x3 = posX;
        prim->x1 = posX;
        posY = self->posY.i.hi - 0x24;
        prim->y1 = posY;
        prim->y0 = posY;
        prim->priority = 0xAA;
        prim->drawMode = 0x33;
        posY = self->posY.i.hi + 0x24;
        prim->y3 = posY;
        prim->y2 = posY;
        if (func_us_801D289C(self) != 0) {
            if (!(self->params & 0x100)) {
                self->ext.sealedDoor.angle = 0x1000;
            } else {
                self->ext.sealedDoor.angle = 0x800;
            }
            g_Player.demo_timer = 0x18;
            PLAYER_velocityY = 0;
            g_Player.padSim = 0;
            self->animCurFrame = 0;
            self->step = 4;
            return;
        }
        /* fall through */
    case 1:
        GetPlayerCollisionWith(self, 8, 0x20, 5);
        self->ext.sealedDoor.angle = 0xC00;
        prim = &g_PrimBuf[self->primIndex];
        i = 0;
        if (prim->next != NULL) {
            do {
                if (i != 0) {
                    prim->drawMode |= 8;
                } else {
                    prim->drawMode = 6;
                }
                prim = prim->next;
                i++;
            } while (prim->next != NULL);
        }
        prim->drawMode = 0x33;
        sideToPlayer = PLAYER_facingLeft;
        if ((sideToPlayer != GetSideToPlayer()) &&
            (((PLAYER_step == 0x19) && (g_PlayableCharacter != 0)) ||
             (PLAYER_step == 1)) &&
            (func_us_801D289C(self) != 0)) {
            if (!(g_Status.relics[0x10] & 2)) {
                if (self->ext.sealedDoor.showedMessage == 0) {
                    newEntity = AllocEntity(&g_Entities_224, &g_Entities_224[0x1780]);
                    if (newEntity != NULL) {
                        self->ext.sealedDoor.showedMessage = 1;
                        CreateEntityFromCurrentEntity(0xE, newEntity);
                        newEntity->posX.i.hi = 0x80;
                        newEntity->posY.i.hi = 0xB0;
                        newEntity->ext.prim = (Primitive*)&D_us_80183424;
                    }
                }
            } else {
                prim = &g_PrimBuf[self->primIndex];
                i = 0;
                if (prim != NULL) {
                    do {
                        if ((i == 1) && !(self->params & 0x100)) {
                            prim->drawMode &= ~8;
                        }
                        if ((i == 2) && (self->params & 0x100)) {
                            prim->drawMode &= ~8;
                        }
                        if (i == 0) {
                            prim->drawMode &= ~8;
                        }
                        prim = prim->next;
                        i++;
                    } while (prim != NULL);
                }
                self->animCurFrame = 0;
                g_Player.padSim = 0;
                g_Player.demo_timer = 2;
                self->ext.sealedDoor.sideToPlayer = (GetSideToPlayer() & 1) ^ 1;
                g_api_PlaySfx(0x642);
                self->step++;
            }
        }
        break;
    case 2:
        g_Player.padSim = 0;
        g_Player.demo_timer = 0x18;
        if (!(self->params & 0x100)) {
            self->ext.sealedDoor.angle += 0x20;
            if (self->ext.sealedDoor.angle >= 0x1000) {
                self->ext.sealedDoor.angle = 0x1000;
            }
            if (self->ext.sealedDoor.angle == 0x1000) {
                self->step++;
            }
        } else {
            self->ext.sealedDoor.angle -= 0x20;
            if (self->ext.sealedDoor.angle < 0x801) {
                self->ext.sealedDoor.angle = 0x800;
            }
            if (self->ext.sealedDoor.angle == 0x800) {
                self->step++;
            }
        }
        break;
    case 3:
        if (g_Player.demo_timer < 4) {
            return;
        }
        if (self->ext.sealedDoor.sideToPlayer) {
            PLAYER_velocityY = 0x8000;
        } else {
            PLAYER_velocityY = 0x2000;
        }
        g_Player.demo_timer = 3;
        self->step++;
        break;
    case 4:
        if (self->ext.sealedDoor.sideToPlayer) {
            PLAYER_velocityY = 0x8000;
        } else {
            PLAYER_velocityY = 0x2000;
        }
        g_Player.demo_timer = 4;
        if (func_us_801D289C(self) != 0) {
            return;
        }
        g_api_PlaySfx(0x642);
        self->step++;
        g_Player.demo_timer = 0;
        break;
    case 5:
        g_Player.padSim = 0;
        g_Player.demo_timer = 4;
        if (!(self->params & 0x100)) {
            self->ext.sealedDoor.angle -= 0x20;
            if (self->ext.sealedDoor.angle < 0xC01) {
                self->ext.sealedDoor.angle = 0xC00;
            }
        } else {
            self->ext.sealedDoor.angle += 0x20;
            if (self->ext.sealedDoor.angle >= 0xC00) {
                self->ext.sealedDoor.angle = 0xC00;
            }
        }
        if (self->ext.sealedDoor.angle == 0xC00) {
            prim = &g_PrimBuf[self->primIndex];
            i = 0;
            if (prim != NULL) {
                do {
                    if (!(self->params & 0x1000) || i == 0) {
                        prim->drawMode |= 8;
                    }
                    prim = prim->next;
                    i++;
                } while (prim != NULL);
            }
            self->animCurFrame = 1;
            self->step = 1;
        }
        break;
    }
}
