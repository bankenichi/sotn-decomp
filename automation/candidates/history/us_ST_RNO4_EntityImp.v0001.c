/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO4:EntityImp
   source : upstream/master:src/st/e_imp.h
   target : src/st/rno4/unk_58A30.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno4.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
s16 GetDistanceToPlayerX();
void MoveEntity();
s32 GetSideToPlayer(void);
int rcos(int a);
int rsin(int a);
long ratan2(long y, long x);
int abs(int x);
Entity* AllocEntity(Entity* start, Entity* end);
void CreateEntityFromCurrentEntity(u16, Entity*);
s32 Random();
void PlaySfxPositional(s32 arg0);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void DestroyEntity(Entity*);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int SetStep();
extern int AnimateEntity();
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BBE58_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BC650_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCA5C_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCB9C_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCD80_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCE4C_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", func_us_801BCFC8_from_rnz1);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", TryThrow);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityJackOBones);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityJackOBonesDeathParts);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityJackOBonesJack);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", TryShoot);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", DrawLaserRing);

INCLUDE_RODATA("st/rno4/nonmatchings/unk_58A30", D_us_801C4800);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityNovaSkeleton);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityBladeSoldierDeathParts);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityNovaLaser);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityNovaLaserPulse);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitImp;

void EntityImp(Entity* self) {
    Entity* other;
    s16 angle;
    s32 xVar;
    s32 yVar;     
    s32 tempVar;  
    s32 playerStatus;
     
    const u32 immuneStates =
        PLAYER_STATUS_UNK40000000 | PLAYER_STATUS_AXEARMOR |
        PLAYER_STATUS_UNK800000 | PLAYER_STATUS_UNK400000 | PLAYER_STATUS_DEAD |
        PLAYER_STATUS_STONE | PLAYER_STATUS_UNK40 | PLAYER_STATUS_CROUCH |
        PLAYER_STATUS_UNK10 | PLAYER_STATUS_TRANSFORM;

    if ((self->hitFlags & 3) && (self->step < IMP_RETREAT_HIT)) {
        SetStep(IMP_RETREAT_HIT);
    }
    if ((self->flags & FLAG_DEAD) && (self->step != IMP_DEAD)) {
        SetStep(IMP_DEAD);
    }
    switch (self->step) {
    case IMP_INIT:
        InitializeEntity(g_EInitImp);
        SetStep(IMP_IDLE);
        break;
    case IMP_IDLE:
        AnimateEntity(anim_imp, self);
        if (GetDistanceToPlayerX() < 0x80) {
            SetStep(IMP_3);
        }
        break;
    case IMP_3:
        if (!self->step_s) {
            self->ext.imp.timer = 0xC0;
            self->step_s += 1;
        }
        AnimateEntity(anim_imp, self);
        MoveEntity();
         
        tempVar = GetSideToPlayer() & 1;
        self->facingLeft = tempVar;
        other = &PLAYER;
        angle = self->ext.imp.angle;
        xVar = (rcos(angle) * 0x50) >> 0xC;
        yVar = (rsin(angle) * 0x50) >> 0xC;
        if (yVar > 0) {
            yVar = -yVar;
        }

        xVar += other->posX.i.hi;
        yVar += other->posY.i.hi;
        xVar -= self->posX.i.hi;
        yVar -= self->posY.i.hi;

        angle = ratan2(yVar, xVar);
        self->velocityX = (rcos(angle) << 0x10) >> 0xC;
        self->velocityY = (rsin(angle) << 0x10) >> 0xC;
        self->ext.imp.angle += 8;

         
        tempVar = other->facingLeft;
        xVar = other->posX.i.hi - self->posX.i.hi;
        yVar = other->posY.i.hi - self->posY.i.hi;
        if (tempVar != self->facingLeft) {
            playerStatus = g_Player.status;
            if (playerStatus & PLAYER_STATUS_UNK400) {
                if ((abs(xVar) < 0x40) && (abs(yVar) < 0x20)) {
                    SetStep(IMP_FLEE_HORIZ);
                }
            }
            if (playerStatus &
                (PLAYER_STATUS_SPELLCAST | PLAYER_STATUS_SUBWPN)) {
                yVar += 12;
                if (yVar < 0x50U) {
                    SetStep(IMP_FLEE_VERT);
                }
            }
        }

        if (!--self->ext.imp.timer) {
            if (self->facingLeft == tempVar) {
                SetStep(IMP_5);
            } else {
                SetStep(IMP_4);
            }
        }
        break;
    case IMP_FLEE_HORIZ:
    case IMP_FLEE_VERT:
        if (!self->step_s) {
             
            self->facingLeft = GetSideToPlayer() & 1;
            if (!self->facingLeft) {
                self->velocityX = FIX(-8);
            } else {
                self->velocityX = FIX(8);
            }
             
            if (self->step == IMP_FLEE_VERT) {
                self->velocityX = 0;
                self->velocityY = FIX(-4);
            }
            self->ext.imp.timer = 0x20;
            self->step_s += 1;
        }
        AnimateEntity(anim_imp, self);
        MoveEntity();
        self->velocityX -= self->velocityX >> 3;
        self->velocityY -= self->velocityY >> 4;
        if (!--self->ext.imp.timer) {
            SetStep(IMP_3);
        }
        break;
    case IMP_5:
        switch (self->step_s) {
        case 0:
            other = &PLAYER;
            xVar = other->posX.i.hi - self->posX.i.hi;
            yVar = other->posY.i.hi - 0x18 - self->posY.i.hi;
            angle = ratan2(yVar, xVar);
            self->velocityX = (rcos(angle) * 0x2C000) >> 0xC;
            self->velocityY = (rsin(angle) * 0x2C000) >> 0xC;
            self->ext.imp.timer = 0x50;
            if (self->velocityX > 0) {
                self->facingLeft = 0;
            } else {
                self->facingLeft = 1;
            }
            self->step_s += 1;
             
        case 1:
            AnimateEntity(&anim_imp, self);
            MoveEntity();
            other = &PLAYER;
            xVar = other->posX.i.hi - self->posX.i.hi;
            yVar = (other->posY.i.hi - 0x18) - self->posY.i.hi;
            if (self->velocityX > 0) {
                xVar -= 4;
                xVar = -xVar;
            } else {
                xVar = xVar + 4;
            }
            if (self->velocityY > 0) {
                yVar = -yVar;
            }
            if (self->ext.imp.timer) {
                if ((xVar > 0x20) || (yVar > 0x20)) {
                    self->step_s += 1;
                    self->ext.imp.timer = 0x40;
                }
            } else {
                self->ext.imp.timer--;
            }
            if (yVar < 0) {
                yVar = -yVar;
            }
            if (xVar < 0) {
                xVar = -xVar;
            }
            if ((yVar < 6) && (xVar < 4)) {
                SetStep(IMP_JAM_PLAYER);
            }
            break;
        case 2:
            AnimateEntity(anim_imp, self);
            MoveEntity();
            self->velocityX -= self->velocityX >> 4;
            self->velocityY -= self->velocityY >> 4;
            if (!--self->ext.imp.timer) {
                SetStep(IMP_3);
            }
        }
        break;
    case IMP_4:
        switch (self->step_s) {
        case 0:
            other = &PLAYER;
            xVar = other->posX.i.hi;
            yVar = other->posY.i.hi - 0x50;
            xVar -= self->posX.i.hi;
            yVar -= self->posY.i.hi;
            angle = ratan2(yVar, xVar);
            self->velocityX = (rcos(angle) * 0x2C000) >> 0xC;
            self->velocityY = (rsin(angle) * 0x2C000) >> 0xC;
            self->ext.imp.timer = 0x200;
            self->step_s += 1;
             
        case 1:
            AnimateEntity(&anim_imp, self);
            MoveEntity();
            other = &PLAYER;
            xVar = other->posX.i.hi - self->posX.i.hi;
            if (!self->facingLeft) {
                xVar = -xVar;
            }
            if (xVar > 0) {
                self->step_s += 1;
            } else {
                tempVar = --self->ext.imp.timer;
                if (!(tempVar & 0xF)) {
                    self->step_s -= 1;
                }
                if (tempVar == 0) {
                    SetStep(IMP_3);
                }
            }
            break;
        case 2:
            other = &PLAYER;
            xVar = other->posX.i.hi;
            yVar = other->posY.i.hi - 0x18;
            if (!self->facingLeft) {
                xVar += 0x40;
            } else {
                xVar -= 0x40;
            }
            xVar -= self->posX.i.hi;
            yVar -= self->posY.i.hi;
            angle = ratan2(yVar, xVar);
            self->velocityX = (rcos(angle) * 0x2C000) >> 0xC;
            self->velocityY = (rsin(angle) * 0x2C000) >> 0xC;
            self->step_s += 1;
             
        case 3:
            AnimateEntity(&anim_imp, self);
            MoveEntity();
            other = &PLAYER;
            xVar = other->posX.i.hi - self->posX.i.hi;
            if (!self->facingLeft) {
                xVar = -xVar;
            }
            if (xVar > 0x40) {
                SetStep(IMP_5);
            } else {
                tempVar = --self->ext.imp.timer;
                if (!(tempVar & 0xF)) {
                    self->step_s -= 1;
                }
                if (tempVar == 0) {
                    SetStep(IMP_3);
                }
            }
        }
        break;
     
     
    case IMP_JAM_PLAYER:
        switch (self->step_s) {
        case 0:
            other = &PLAYER;
            if (!self->facingLeft) {
                self->ext.imp.jamOffsetX = -8;
            } else {
                self->ext.imp.jamOffsetX = 8;
            }
            if (other->facingLeft != self->facingLeft) {
                self->ext.imp.jamOffsetX <<= 1;
            }
            self->ext.imp.jamOffsetY = -24;
            if (g_Player.status & immuneStates) {
                SetStep(IMP_3);
            }
            self->hitboxState = 0;
            self->ext.imp.playerJamTimer = 0x20;
            self->step_s += 1;
             
        case 1:
            AnimateEntity(&anim_imp, self);
            other = &PLAYER;
            self->posX.i.hi = other->posX.i.hi + self->ext.imp.jamOffsetX;
            self->posY.i.hi = other->posY.i.hi + self->ext.imp.jamOffsetY;
            if (!(g_Timer & 0xF)) {
                other = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (other != NULL) {
                    CreateEntityFromCurrentEntity(E_IMP_SMOKE, other);
                }
            }
            g_Player.demo_timer = 1;
            if (g_Timer & 1) {
                if (Random() & 1) {
                    g_Player.padSim = PAD_SQUARE;
                } else {
                    g_Player.padSim = PAD_CIRCLE;
                }
            } else {
                g_Player.padSim = 0;
            }
             
            tempVar = g_pads[0].pressed & PAD_DIRECTION_MASK;
             
            if (tempVar != self->ext.imp.prevDirsPressed) {
                 
                if (!--self->ext.imp.playerJamTimer) {
                    SetStep(IMP_RETREAT_ESCAPE);
                }
            }
             
            self->ext.imp.prevDirsPressed = tempVar;
            if (g_Player.status & immuneStates) {
                SetStep(IMP_RETREAT_ESCAPE);
            }
        }
        break;
     
    case IMP_RETREAT_ESCAPE:
    case IMP_RETREAT_HIT:
        switch (self->step_s) {
        case 0:
            self->facingLeft = GetSideToPlayer() & 1;
            if (!self->facingLeft) {
                self->velocityX = FIX(-4);
            } else {
                self->velocityX = FIX(4);
            }
            self->velocityY = FIX(-2.5);
            self->ext.imp.timer = 0x30;
            self->step_s += 1;
             
        case 1:
            if (self->ext.imp.timer < 0x28) {
                self->hitboxState = 3;
            }
            AnimateEntity(anim_imp, self);
            MoveEntity();
            self->velocityX -= self->velocityX >> 3;
            self->velocityY -= self->velocityY >> 3;
            if (!--self->ext.imp.timer) {
                self->step_s += 1;
            }
            break;
        case 2:
            self->facingLeft = ((GetSideToPlayer() & 1) ^ 1);
            if (!self->facingLeft) {
                self->velocityX = FIX(2.5);
            } else {
                self->velocityX = FIX(-2.5);
            }
            self->step_s += 1;
             
        case 3:
            AnimateEntity(anim_imp, self);
            MoveEntity();
            if (GetDistanceToPlayerX() > 0x60) {
                SetStep(IMP_3);
            }
        }
        break;
    case IMP_DEAD:
        switch (self->step_s) {
        case 0:
            self->hitboxState = 0;
            self->drawFlags = ENTITY_ROTATE;
            self->velocityX = 0;
            self->velocityY = 0;
            self->ext.imp.timer = 0x30;
            self->step_s += 1;
             
        case 1:
            AnimateEntity(&anim_imp, self);
            self->rotate += 0x40;
            MoveEntity();
            self->velocityY += FIX(0.03125);
            if (!--self->ext.imp.timer) {
                PlaySfxPositional(SFX_EXPLODE_E);
                other = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (other != NULL) {
                    CreateEntityFromEntity(E_EXPLOSION, self, other);
                    other->params = EXPLOSION_FIREBALL;
                }
                DestroyEntity(self);
            }
        }
        break;
    }
}

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityImpSmoke);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityRdaiUnk33);

INCLUDE_ASM("st/rno4/nonmatchings/unk_58A30", EntityImpDeathParticle);
