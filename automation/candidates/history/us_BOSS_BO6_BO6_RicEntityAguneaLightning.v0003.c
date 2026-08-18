/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO6:BO6_RicEntityAguneaLightning
   attempt: 4/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (stubs declared)
   origin : src/boss/bo6/us_3E79C.c
   asm    : asm/us/boss/bo6/nonmatchings/us_3E79C/BO6_RicEntityAguneaLightning.s

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
#include "bo6.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
u_long PadRead(int id);
extern s32 func_8016840C(s16 x, s16 y);
void InitializeEntity(u16 arg0[]);
extern void BO6_RicCreateEntFactoryFromEntity(Entity*, u32, s32);
int FntPrint(const char* fmt, ...);
int abs(int x);
long ratan2(long y, long x);
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int BO6_RicCheckHolyWaterCollision();
extern int func_us_801BB5BC();
extern int labs();

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
extern void DestroyEntity(Entity* entity);
extern int rand(void);
extern void srand(unsigned int);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int BO6_GetAguneaLightningAngle();
extern int rcos();
extern int rsin();

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", func_us_801BE79C);

INCLUDE_ASM(
    "boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityShrinkingPowerUpRing);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityHitByIce);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityHitByLightning);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", func_us_801C03E8);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", EntityShaft);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", func_us_801C0FE8);

extern AnimationFrame D_us_80181EDC[];

void func_us_801C13A8(Entity* self) {
    s16 params = self->params & 0x7F00;
    switch (self->step) {
    case 0:
        self->flags = FLAG_UNK_20000000 | FLAG_POS_CAMERA_LOCKED;
        self->unk5A = 0x79;
        self->animSet = ANIMSET_DRA(14);
        self->zPriority = RIC.zPriority + 6;
        self->palette = PAL_FLAG(0x25E);
        self->blendMode = BLEND_TRANSP | BLEND_QUARTER;
        self->drawFlags = ENTITY_SCALEY | ENTITY_SCALEX;
        self->scaleX = self->scaleY = 0xC0;
        self->anim = D_us_80181EDC;
        if (params) {
            self->scaleX = self->scaleY = 0x80;
            self->anim = D_us_80181EDC;
        }
        self->velocityY = -FIX(0.25);
        self->step++;
        break;

    case 1:
        self->posY.val += self->velocityY;
        if (self->poseTimer < 0) {
            DestroyEntity(self);
        }
        break;
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityWhip);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityArmBrandishWhip);

extern s16 D_us_80182870[];
// Mirrors `ric` func_80167964 (src/ric/pl_whip.c:540) but the flags differ
// beyond the g_Ric/g_Player and lookup-table swap: RIC sets
// FLAG_UNK_20000 | FLAG_POS_PLAYER_LOCKED | FLAG_KEEP_ALIVE_OFFCAMERA |
// FLAG_UNK_10000, this sets FLAG_UNK_10000000 | FLAG_POS_CAMERA_LOCKED.
// Locked to the camera rather than the player, and no off-camera keep-alive.
void func_us_801C2688(Entity* entity) {
    if (g_Ric.unk46 == 0) {
        DestroyEntity(entity);
        return;
    }
    if (entity->step == 0) {
        entity->flags = FLAG_UNK_10000000 | FLAG_POS_CAMERA_LOCKED;
    }
    if (!(entity->params & 0xFF00)) {
        g_Entities[D_us_80182870[entity->poseTimer]].palette = PAL_FLAG(0x240);
    }
    g_Entities[D_us_80182870[entity->poseTimer]].ext.player.unkA4 = 4;
    entity->poseTimer++;
    if (entity->poseTimer == 15) {
        DestroyEntity(entity);
    }
}

void func_us_801C277C(void) {}

void func_us_801C2784(void) {}

INCLUDE_ASM(
    "boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnHolyWaterBreakGlass);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityCrashHydroStorm);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_DebugShowWaitInfo);

extern void BO6_DebugShowWaitInfo(const char* msg);

// Richter (BO6) debug helper: spin while pad held, then spin while pad released
void BO6_DebugInputWait(const char* msg) {
    while (PadRead(0)) {
        BO6_DebugShowWaitInfo(msg);
    }
    while (PadRead(0) == 0) {
        BO6_DebugShowWaitInfo(msg);
    }
}

// baseY/baseX are position OFFSETS added to the entity's position, not
// dimensions; the previous names height/width invited confusion with the
// real Entity.hitboxHeight/hitboxWidth fields. Named as upstream does in
// src/ric/pl_subweapon_holywater.c. Static because every caller is in this
// file and no assembly references it across a translation unit.
static s32 OVL_EXPORT(RicCheckHolyWaterCollision)(s16 baseY, s16 baseX) {
    Collider collider;
    Collider collider2;
    s16 maskedEffects;
    s16 maskedEffects2;
    s16 posX;
    s16 posY;
    s16 newPosY;

    if ((g_CurrentEntity->posX.val + baseX) < 0 ||
        (g_CurrentEntity->posX.i.hi + baseX) > 256) {
        if ((g_CurrentEntity->posY.i.hi + baseY) >= 212) {
            g_CurrentEntity->posY.i.hi = 212 - baseY;
            return EFFECT_SOLID;
        }
        return EFFECT_NONE;
    }
    posX = g_CurrentEntity->posX.i.hi + baseX;
    posY = g_CurrentEntity->posY.i.hi + baseY;

    g_api.CheckCollision(posX, posY, &collider, 0);
    maskedEffects = collider.effects &
                    (EFFECT_UNK_8000 | EFFECT_UNK_4000 | EFFECT_UNK_2000 |
                     EFFECT_UNK_1000 | EFFECT_UNK_0800 | EFFECT_SOLID);
    posY = posY - 1 + collider.unk18;
    g_api.CheckCollision(posX, posY, &collider2, 0);

    newPosY = baseY + (g_CurrentEntity->posY.i.hi + collider.unk18);
    if ((maskedEffects & (EFFECT_UNK_8000 | EFFECT_UNK_0800 | EFFECT_SOLID)) ==
            EFFECT_SOLID ||
        (maskedEffects & (EFFECT_UNK_8000 | EFFECT_UNK_0800 | EFFECT_SOLID)) ==
            (EFFECT_UNK_0800 | EFFECT_SOLID)) {
        maskedEffects = collider2.effects &
                        (EFFECT_UNK_8000 | EFFECT_UNK_4000 | EFFECT_UNK_2000 |
                         EFFECT_UNK_1000 | EFFECT_SOLID);
        if (!(maskedEffects & EFFECT_SOLID)) {
            g_CurrentEntity->posY.i.hi = newPosY;
            return EFFECT_SOLID;
        }
        if (((s32)collider2.effects & (EFFECT_UNK_8000 | EFFECT_SOLID)) ==
            (EFFECT_UNK_8000 | EFFECT_SOLID)) {
            g_CurrentEntity->posY.i.hi = newPosY - 1 + collider2.unk18;
            return maskedEffects;
        }
        return EFFECT_NONE;
    }
    if ((maskedEffects & (EFFECT_UNK_8000 | EFFECT_SOLID)) ==
        (EFFECT_UNK_8000 | EFFECT_SOLID)) {
        g_CurrentEntity->posY.i.hi = newPosY;
        return maskedEffects &
               (EFFECT_UNK_8000 | EFFECT_UNK_4000 | EFFECT_UNK_2000 |
                EFFECT_UNK_1000 | EFFECT_SOLID);
    }
    return EFFECT_NONE;
}

static int func_8016840C() { return EFFECT_NONE; }

extern EInit D_us_80180460;

void OVL_EXPORT(RicEntitySubwpnHolyWater)(Entity* self) {
    s16 xMod;
    s32 colRes;

    if (self->step > 2) {
        self->posY.i.hi += 5;
    }
    switch (self->step) {
    case 0:
        self->ext.holywater.subweaponId = PL_W_HOLYWATER;
        InitializeEntity(D_us_80180460);
        self->flags = FLAG_POS_CAMERA_LOCKED;
        self->animSet = ANIMSET_OVL(3);
        self->animCurFrame = 0x23;
        self->zPriority = RIC.zPriority + 2;
        self->unk5A = 0x24;
        self->palette = PAL_FLAG(0x22F);
        xMod = 0;
        if (self->facingLeft) {
            xMod = -xMod;
        }
        self->posX.i.hi += xMod;
        self->posY.i.hi += -16;
        self->ext.holywater.angle = (rand() & 0x7F) + ROT(309.375);
        if (RIC.facingLeft == true) {
            self->ext.holywater.angle = (rand() & 0x7F) + ROT(219.375);
        }
        self->velocityX =
            (FLT_TO_FIX(rcos(self->ext.holywater.angle)) * FIX(3.0 / 128.0)) >>
            8;
        self->velocityY =
            -(FLT_TO_FIX(rsin(self->ext.holywater.angle)) * FIX(3.0 / 128.0)) >>
            8;
        self->hitboxWidth = 4;
        self->hitboxHeight = 4;
        self->ext.holywater.unk80 = 0x200;
        self->step = 1;
        break;

    case 1:
        self->posY.val += self->velocityY;
        colRes = BO6_RicCheckHolyWaterCollision(0, 0);
        self->posX.val += self->velocityX;

        if ((colRes & EFFECT_SOLID) || (self->hitFlags != 0)) {
            BO6_RicCreateEntFactoryFromEntity(self, 0x28, 0);
            g_api.PlaySfx(SFX_RIC_HOLY_WATER_ATTACK);
            self->ext.holywater.timer = 80;
            self->animSet = 0;
            self->step = 3;
            self->velocityX >>= 2;
        } else if (self->flags & FLAG_DEAD) {
            BO6_RicCreateEntFactoryFromEntity(self, 0x28, 0);
            g_api.PlaySfx(SFX_RIC_HOLY_WATER_ATTACK);
            self->ext.holywater.timer = 80;
            self->animSet = 0;
            self->step = 3;
            self->velocityX = -((s32)self->velocityX >> 2);
        }
        break;
    case 2:
        if (self->flags & FLAG_DEAD) {
            DestroyEntity(self);
            return;
        }
        if (--self->ext.holywater.timer == 0) {
            self->velocityX >>= 2;
            self->ext.holywater.timer = 80;
            self->step++;
        }
        break;
    case 3:
        if (self->flags & FLAG_DEAD) {
            self->velocityX = 0;
        }
        if (!(self->ext.holywater.timer & 3)) {
            BO6_RicCreateEntFactoryFromEntity(
                self, FACTORY(BP_HOLYWATER_FIRE, self->ext.holywater.unk82), 0);
            self->ext.holywater.unk82 += 1;
            self->velocityX -= (self->velocityX / 32);
        }

        self->posX.val += self->velocityX;
        colRes = OVL_EXPORT(RicCheckHolyWaterCollision)(6, 0);
        if (!(colRes & EFFECT_SOLID)) {
            self->velocityX >>= 1;
            self->step++;
        }
        break;
    case 4:
        if (self->flags & FLAG_DEAD) {
            self->velocityX = 0;
        }

        if (!(self->ext.holywater.timer & 3)) {
            BO6_RicCreateEntFactoryFromEntity(
                self, FACTORY(BP_HOLYWATER_FIRE, self->ext.holywater.unk82), 0);
            self->ext.holywater.unk82 += 1;
        }
        self->velocityY += FIX(12.0 / 128);
        if (self->velocityY > FIX(4)) {
            self->velocityY = FIX(4);
        }
        self->posY.val += self->velocityY;
        colRes = BO6_RicCheckHolyWaterCollision(0, 0);
        self->posX.val += self->velocityX;
        xMod = 4;
        if (self->velocityX < 0) {
            xMod = -xMod;
        }
        colRes |= func_8016840C(-7, xMod);
        if (colRes & EFFECT_SOLID) {
            self->velocityX <<= 1;
            self->step--;
        }
        break;
    case 5:
        break;
    }

    if (self->step > 2) {
        if (--self->ext.holywater.timer < 0) {
            DestroyEntity(self);
            return;
        }
        if (self->ext.holywater.timer == 2) {
            self->step = 5;
        }
        self->posY.i.hi -= 5;
        self->animCurFrame = 0;
    }
    g_Ric.timers[PL_T_3] = 2;
    self->hitFlags = 0;
    self->flags &= ~FLAG_DEAD;
    FntPrint("judge:%02x\n", self->hitboxState);
}

INCLUDE_ASM(
    "boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnHolyWaterFlame);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnCrashCross);

extern EInit D_us_80180454;
extern s16 D_us_801D10C8;

extern AnimationFrame anim_cross_boomerang[];
extern Point16 D_us_801D08C4[4][128];
extern s32 D_us_801D10C4;

void OVL_EXPORT(RicEntitySubwpnCross)(Entity* self) {
    s16 playerHitboxX;
    s16 playerHitboxY;
    s16 rotate;
    s16* psp_s1;
    s32 xAccel;

    rotate = self->rotate;
    switch (self->step) {
    case 0:
        self->ext.crossBoomerang.subweaponId = PL_W_CROSS;
        InitializeEntity(D_us_80180454);
        self->flags =
            FLAG_UNK_20000000 | FLAG_UNK_10000000 | FLAG_POS_CAMERA_LOCKED;
        D_us_801D10C8 = self->hitboxState;
        // gets used by shadow, must align with that entity
        self->ext.crossBoomerang.unk84 = D_us_801D08C4[D_us_801D10C4];
        D_us_801D10C4++;
        D_us_801D10C4 &= 3;
        OVL_EXPORT(RicCreateEntFactoryFromEntity)(self, BP_5, 0);
        self->animSet = ANIMSET_OVL(4);
        self->unk5A = 0x44;
        self->anim = anim_cross_boomerang;
        self->facingLeft = RIC.facingLeft;
        self->zPriority = RIC.zPriority;
        OVL_EXPORT(RicSetSpeedX)(FIX(3.5625));
        self->drawFlags = ENTITY_ROTATE;
        self->rotate = ROT(270);
        self->hitboxWidth = 8;
        self->hitboxHeight = 8;
        self->posY.i.hi -= 8;
        g_api.PlaySfx(SFX_RIC_CRASH_CROSS);
        self->step = 1;
        break;
    case 1:
        if (RIC.pose == 1) {
            self->step++;
        }
    case 2:
        // First phase. We spin at 0x80 angle units per frame.
        // Velocity gets decremented by 1/16 per frame until we slow
        // down to less than 0.75.
        self->rotate -= ROT(11.25);
        self->posX.val += self->velocityX;
        if (self->facingLeft) {
            xAccel = FIX(-1.0 / 16);
        } else {
            xAccel = FIX(1.0 / 16);
        }
        self->velocityX -= xAccel;

        if (abs(self->velocityX) < FIX(0.75)) {
            self->step = 3;
        }

        if ((self->hitFlags == 2) || (self->flags & FLAG_DEAD)) {
            if (self->velocityX < 0) {
                self->velocityX = FIX(-0.03125);
            } else {
                self->velocityX = FIX(0.03125);
            }
            self->ext.crossBoomerang.timer = 30;
            self->step = 3;
            self->ext.crossBoomerang.timer = 16;
            self->hitboxState = 0;
        }

        break;
    case 3:
        // Second phase. Once we are slow, we spin twice as fast, and then
        // wait until our speed gets higher once again (turned around).
        self->rotate -= ROT(22.50);
        self->posX.val += self->velocityX;
        if (self->facingLeft) {
            xAccel = FIX(-1.0 / 16);
        } else {
            xAccel = FIX(1.0 / 16);
        }
        if (self->hitFlags == 2 || (self->flags & FLAG_DEAD)) {
            if (self->facingLeft) {
                xAccel = FIX(-1.0 / 16);
            } else {
                xAccel = FIX(1.0 / 16);
            }
        }
        self->velocityX -= xAccel;
        if (abs(self->velocityX) > FIX(0.75)) {
            self->step++;
        }
        break;
    case 4:
        // Third phase. We've now sped up and we're coming back.
        // Increase speed until a terminal velocity of 2.5.
        if (self->facingLeft) {
            xAccel = FIX(-1.0 / 16);
        } else {
            xAccel = FIX(1.0 / 16);
        }
        self->velocityX -= xAccel;
        if (abs(self->velocityX) > FIX(2.5)) {
            self->hitboxState = D_us_801D10C8;
            self->step++;
        }
    case 5:
        if (--self->ext.crossBoomerang.timer < 0 &&
            ((self->hitFlags == 2) || (self->flags & FLAG_DEAD))) {
            self->velocityY = FIX(-3.0);
            self->ext.crossBoomerang.timer = 50;
            self->hitboxState = 0;
            self->step = 6;
            self->velocityX = -((s32)self->velocityX / 2);
        }

        // Now we check 2 conditions. If we're within the player's hitbox...
        playerHitboxX = (RIC.posX.i.hi + RIC.hitboxOffX);
        playerHitboxY = (RIC.posY.i.hi + RIC.hitboxOffY);
        if (abs(self->posX.i.hi - playerHitboxX) <
                RIC.hitboxWidth + self->hitboxWidth &&
            abs(self->posY.i.hi - playerHitboxY) <
                RIC.hitboxHeight + self->hitboxHeight) {
            // ... Then we go to step 7 to be destroyed.
            self->step = 7;
            self->ext.crossBoomerang.timer = 32;
            return;
        }
        // Alternatively, if we're offscreen, we will also be destroyed.
        if ((self->facingLeft == 0 && self->posX.i.hi < -32) ||
            (self->facingLeft && self->posX.i.hi > 0x120)) {
            self->step = 7;
            self->ext.crossBoomerang.timer = 32;
            return;
        }
        // Otherwise, we keep trucking. spin at the slower rate again.
        self->rotate -= ROT(11.25);
        self->posX.val += self->velocityX;
        break;
    case 6:
        if (--self->ext.crossBoomerang.timer == 0) {
            DestroyEntity(self);
            return;
        }
        self->velocityY += FIX(0.15625);
        self->posX.val += self->velocityX;
        self->posY.val += self->velocityY;
        self->rotate += ROT(33.75);
        break;
    case 7:
        if (--self->ext.crossBoomerang.timer == 0) {
            DestroyEntity(self);
            return;
        }
        self->hitboxState = 0;
        self->animSet = 0;
        self->posX.val += self->velocityX;
        break;
    }
    // We will increment through these states, creating trails.
    // Factory 3 is entity #4, func_80169C10. Appears to make tiny sparkles.
    // Factory 4 is entity #5, RicEntityHitByCutBlood. Appears to make a
    // "shadow" of the cross boomerang.
    self->ext.crossBoomerang.unk7E++;
    if (1 < self->step && self->step < 6) {
        if ((self->ext.crossBoomerang.unk7E & 0xF) == 1) {
            OVL_EXPORT(RicCreateEntFactoryFromEntity)
            (self, BP_SUBWPN_CROSS_PARTICLES, 0);
        }
        if ((self->ext.crossBoomerang.unk7E & 0xF) == 4) {
            OVL_EXPORT(RicCreateEntFactoryFromEntity)
            (self, FACTORY(BP_EMBERS, 6), 0);
        }
        if ((self->ext.crossBoomerang.unk7E & 0xF) == 6) {
            OVL_EXPORT(RicCreateEntFactoryFromEntity)
            (self, BP_SUBWPN_CROSS_PARTICLES, 0);
        }
        if ((self->ext.crossBoomerang.unk7E & 0xF) == 8) {
            OVL_EXPORT(RicCreateEntFactoryFromEntity)
            (self, FACTORY(BP_EMBERS, 6), 0);
        }
        if ((self->ext.crossBoomerang.unk7E & 0xF) == 12) {
            OVL_EXPORT(RicCreateEntFactoryFromEntity)
            (self, FACTORY(BP_EMBERS, 6), 0);
        }
        if ((self->ext.crossBoomerang.unk7E & 0xF) == 11) {
            OVL_EXPORT(RicCreateEntFactoryFromEntity)
            (self, BP_SUBWPN_CROSS_PARTICLES, 0);
        }
    }
    // Applies a flickering effect
    if ((g_GameTimer >> 1) & 1) {
        self->palette = PAL_FLAG(0x1B0);
    } else {
        self->palette = PAL_FLAG(0x1B1);
    }
    psp_s1 = (s16*)self->ext.crossBoomerang.unk84;
    psp_s1 = &psp_s1[self->ext.crossBoomerang.unk80 * 2];
    *psp_s1 = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
    psp_s1++;
    *psp_s1 = self->posY.i.hi + g_Tilemap.scrollY.i.hi;
    self->ext.crossBoomerang.unk80++;
    self->ext.crossBoomerang.unk80 &= 0x3F;
    rotate ^= self->rotate;
    g_Ric.timers[PL_T_3] = 2;
    self->hitFlags = 0;
    self->flags &= ~FLAG_DEAD;
}

// Richter (BO6): a single falling ember. Step 0 allocates one GT4 primitive,
// jitters the spawn point inside a 16x16 box around the parent, and seeds a
// downward velocity; every later step just falls and re-projects, destroying
// itself when func_us_801BB5BC reports it has left the screen.
//
// SHAPE WARNING, same class as func_us_801BC3E0 in us_39144.c. `new_var`,
// `new_var2` and the reuse of `idx` as the constant 4 are all load-bearing:
// they pin which values live in registers across the rand() calls. The
// `(long long)` cast on the posX store is likewise not decoration. This body
// is what scored 0; tidying it will not.
//
// Reached that score by promoting the permuter seed twice, 220 -> 70 -> 0.
// For contrast, the same function had previously run 170,002 iterations from
// the unpromoted base and never got below 220. Re-check with:
//     python3 automation/permuter_promote.py --dir nonmatchings/func_us_801C488C
void func_us_801C488C(Entity* entity) {
    int new_var;
    Primitive* prim;
    s32 idx;
    int new_var2;

    if (entity->step == 0) {
        idx = g_api.AllocPrimitives(PRIM_GT4, 1);
        entity->primIndex = (s32)idx;
        if (idx != -1) {
            entity->flags = 0x08800000;
            new_var2 = 0xF;
            entity->velocityY = 0x8000;
            entity->posX.i.hi =
                (long long)((entity->posX.i.hi - 8) + (rand() & new_var2));
            idx = 4;
            entity->posY.i.hi = (entity->posY.i.hi - idx) + (rand() & new_var2);
            prim = &g_PrimBuf[entity->primIndex];
            prim->clut = 0x1B0;
            prim->tpage = 0x1A;
            prim->b0 = 0;
            prim->b1 = 0;
            new_var = entity->zPriority + idx;
            prim->drawMode = 0x31;
            prim->priority = new_var;
            func_us_801BB5BC(prim, (s16)entity->posX.i.hi,
                             (s16)entity->posY.i.hi);
            entity->step++;
            return;
        }
        DestroyEntity(entity);
        return;
    }
    entity->posY.val += entity->velocityY;
    prim = &g_PrimBuf[entity->primIndex];
    if (func_us_801BB5BC(prim, (s16)entity->posX.i.hi,
                         (s16)entity->posY.i.hi) != 0) {
        DestroyEntity(entity);
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnCrossTrail);

INCLUDE_ASM(
    "boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnCrashCrossParticles);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnThrownAxe);

extern EInit D_us_80180490;
extern u8 D_us_8018299C[];

void OVL_EXPORT(RicEntityCrashAxe)(Entity* self) {
    Primitive* primFirst;
    Primitive* prim;
    s16 angle1;
    s16 angle2;
    s16 angle3;
    s16 angle4;
    s32 mod;
    s32 i;
    u8 r;
    u8 g;
    u8 b;
    s16 angleMod;
    s16 x;
    s16 y;
    s16 angle;
    s32 pose;
    s32 velocity;
    s32 colorRef;

    mod = 21;
    switch (self->step) {
    case 0:
        self->ext.subwpnAxe.subweaponId = 2;
        InitializeEntity(D_us_80180490);
        self->primIndex = g_api.AllocPrimitives(PRIM_GT4, 5);
        if (self->primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags =
            FLAG_UNK_10000000 | FLAG_POS_CAMERA_LOCKED | FLAG_HAS_PRIMS;
        self->facingLeft = 0;
        self->ext.subwpnAxe.unk7C = ((self->params & 0xFF) << 9) + ROT(270);
        self->posY.i.hi -= 12;
        prim = &g_PrimBuf[self->primIndex];
        i = 0;
        while (prim) {
            prim->tpage = 0x1C;
            prim->u0 = prim->v0 = prim->v1 = prim->u2 = 0;
            prim->u1 = prim->u3 = 0x18;
            prim->v2 = prim->v3 = 0x28;
            prim->priority = RIC.zPriority + 4;
            if (i != 0) {
                prim->drawMode = DRAW_UNK_100 | DRAW_TPAGE2 | DRAW_TPAGE |
                                 DRAW_HIDE | DRAW_COLORS | DRAW_TRANSP;
                self->ext.subwpnAxe.unk8C[i - 1] = 0;
                self->ext.subwpnAxe.unk90[i - 1] = 0;
                self->ext.subwpnAxe.unk94[i - 1] = 0;
            } else {
                prim->drawMode = DRAW_UNK_100 | DRAW_HIDE;
            }
            i++;
            prim = prim->next;
        }
        self->hitboxHeight = self->hitboxWidth = 12;
        self->ext.subwpnAxe.angle = (self->params & 0xFF) << 9;
        self->ext.subwpnAxe.velocity = 16;
        self->step = 1;
        break;
    case 1:
        velocity = self->ext.subwpnAxe.velocity;
        self->ext.subwpnAxe.velocity++;
        if (self->ext.subwpnAxe.velocity > 0x28) {
            self->ext.subwpnAxe.unkA2 = 16;
            self->step++;
        }
        angle = self->ext.subwpnAxe.angle;
        self->ext.subwpnAxe.angle += 0xC0;
        self->ext.subwpnAxe.unk7C += 0x80;
        self->velocityX = velocity * rcos(angle);
        self->velocityY = velocity * -rsin(angle);
        self->posX.val += self->velocityX;
        self->posY.val += self->velocityY;
        break;
    case 2:
        if (--self->ext.subwpnAxe.unkA2 == 0) {
            self->ext.subwpnAxe.unkA2 = 8;
            self->step++;
        }
        velocity = self->ext.subwpnAxe.velocity;
        angle = self->ext.subwpnAxe.angle;
        self->ext.subwpnAxe.angle += 0xC0;
        self->ext.subwpnAxe.unk7C += 0x80;
        self->velocityX = rcos(angle) * velocity;
        self->velocityY = -rsin(angle) * velocity;
        self->posX.val += self->velocityX;
        self->posY.val += self->velocityY;
        break;
    case 3:
        if (--self->ext.subwpnAxe.unkA2 == 0) {
            g_Ric.unk4E = 1;
            self->flags &= ~FLAG_UNK_10000000;
        }
        velocity = self->ext.subwpnAxe.velocity;
        self->ext.subwpnAxe.velocity += 2;
        angle = self->ext.subwpnAxe.angle;
        self->ext.subwpnAxe.angle += 0x28;
        self->ext.subwpnAxe.unk7C += 0x80;
        self->velocityX = rcos(angle) * velocity;
        self->velocityY = -rsin(angle) * velocity;
        self->posX.val += self->velocityX;
        self->posY.val += self->velocityY;
        if (self->poseTimer == 0) {
            pose = self->pose;
            self->ext.subwpnAxe.unk8C[pose] = 0;
            self->ext.subwpnAxe.unk90[pose] = 1;
            self->ext.subwpnAxe.unk94[pose] = 1;
            pose++;
            pose &= 3;
            self->pose = pose;
            self->poseTimer = 2;
        } else {
            self->poseTimer--;
        }
        if ((self->hitFlags == 2) || (self->flags & FLAG_DEAD)) {
            self->velocityY = FIX(-3.0);
            self->hitboxState = 0;
            self->step = 4;
            self->velocityX = -((s32)self->velocityX / 2);
        }

        break;
    case 4:
        if (self->facingLeft) {
            angleMod = 0xC0;
        } else {
            angleMod = -0xC0;
        }
        self->ext.subwpnAxe.unk7C += angleMod;
        self->velocityY += 0x2400;
        if (self->velocityY > FIX(8.0)) {
            self->velocityY = FIX(8.0);
        }
        self->posY.val += self->velocityY;
        self->posX.val += self->velocityX;
        if (self->posY.i.hi > 256) {
            DestroyEntity(self);
            return;
        }
        break;
    }

    prim = &g_PrimBuf[self->primIndex];
    primFirst = prim;
    pose = ((g_GameTimer >> 1) & 1) + 0x1AB;
    i = 0;
    while (prim != NULL) {
        prim->clut = pose;
        if (i == 0) {
            if (self->facingLeft) {
                angle1 = 0x800 - 0x2A0;
                angle2 = 0x2A0;
                angle3 = 0x800 + 0x2A0;
                angle4 = 0x800 + 0x800 - 0x2A0;
            } else {
                angle2 = 0x800 - 0x2A0;
                angle1 = 0x2A0;
                angle4 = 0x800 + 0x2A0;
                angle3 = 0x800 + 0x800 - 0x2A0;
            }
            x = self->posX.i.hi;
            y = self->posY.i.hi;
            angleMod = self->ext.subwpnAxe.unk7C;
            angle1 += angleMod;
            angle2 += angleMod;
            angle3 += angleMod;
            angle4 += angleMod;

            prim->x0 = x + +(((rcos(angle1) << 4) * mod) >> 0x10);
            prim->y0 = y + -(((rsin(angle1) << 4) * mod) >> 0x10);
            prim->x1 = x + +(((rcos(angle2) << 4) * mod) >> 0x10);
            prim->y1 = y + -(((rsin(angle2) << 4) * mod) >> 0x10);
            prim->x2 = x + +(((rcos(angle3) << 4) * mod) >> 0x10);
            prim->y2 = y + -(((rsin(angle3) << 4) * mod) >> 0x10);
            prim->x3 = x + +(((rcos(angle4) << 4) * mod) >> 0x10);
            prim->y3 = y + -(((rsin(angle4) << 4) * mod) >> 0x10);
            prim->drawMode &= ~DRAW_HIDE;
        } else if (self->ext.subwpnAxe.unk90[i - 1]) {
            if (self->ext.subwpnAxe.unk94[i - 1]) {
                self->ext.subwpnAxe.unk94[i - 1] = 0;
                prim->x0 = primFirst->x0;
                prim->y0 = primFirst->y0;
                prim->x1 = primFirst->x1;
                prim->y1 = primFirst->y1;
                prim->x2 = primFirst->x2;
                prim->y2 = primFirst->y2;
                prim->x3 = primFirst->x3;
                prim->y3 = primFirst->y3;
            }
            colorRef = (self->ext.subwpnAxe.unk8C[i - 1]++);
            if (colorRef < 10) {
                r = D_us_8018299C[colorRef * 4 + 0];
                g = D_us_8018299C[colorRef * 4 + 1];
                b = D_us_8018299C[colorRef * 4 + 2];
                prim->r0 = r;
                prim->g0 = g;
                prim->b0 = b;
                prim->r1 = r;
                prim->g1 = g;
                prim->b1 = b;
                prim->r2 = r;
                prim->g2 = g;
                prim->b2 = b;
                prim->r3 = r;
                prim->g3 = g;
                prim->b3 = b;
                prim->drawMode &= ~DRAW_HIDE;
            } else {
                self->ext.subwpnAxe.unk90[i - 1] = 0;
                prim->drawMode |= DRAW_HIDE;
            }
        }
        i++;
        prim = prim->next;
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnKnife);

// Reflect the stone's angle about the incoming angle, then bump the two
// bounce counters once. ext sits at 0x7C, so the fields the original touches
// are stoneAngle (+0x7C), unk80 (+0x80) and unk82 (+0x82).
void BO6_ReboundStoneBounce1(s32 arg0) {
    g_CurrentEntity->ext.reboundStone.stoneAngle =
        ((s32)(arg0 << 16) >> 15) -
        g_CurrentEntity->ext.reboundStone.stoneAngle;
    if (g_CurrentEntity->ext.reboundStone.unk82 == 0) {
        g_CurrentEntity->ext.reboundStone.unk80 += 1;
        g_CurrentEntity->ext.reboundStone.unk82 += 1;
    }
}

// Like BO6_ReboundStoneBounce1, but returns early instead of guarding the
// increments, so the angle is only updated while unk82 is still zero, i.e.
// before the stone has started bouncing.
void BO6_ReboundStoneBounce2(s32 arg0) {
    Entity* entity = g_CurrentEntity;

    // branch if non-zero (bnez) -> skip everything when the counter is set
    if (entity->ext.reboundStone.unk82 != 0)
        return;

    // sll 16 / sra 15 implements a signed 16-bit multiply by 2
    entity->ext.reboundStone.stoneAngle =
        ((s32)(arg0 << 16) >> 15) - entity->ext.reboundStone.stoneAngle;

    entity->ext.reboundStone.unk80++;
    entity->ext.reboundStone.unk82++;
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnReboundStone);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnThrownVibhuti);

// Richter (BO6) variant of PrimDecreaseBrightness: floors at 16, not 0, and returns u8
u8 BO6_PrimDecreaseBrightness(Primitive2* prim, u8 amount) {
    s32 i, j;
    u8 isEnd = 0;
    struct SubPrim* subprim = &prim->prim[0];
    u8* pColor;

    for (i = 0; i < 4; i++) {
        for (j = 0; j < 3; j++) {
            pColor = &subprim->col[j];
            *pColor -= amount;
            if (*pColor < 16) {
                *pColor = 16;   // floor brightness at 16, not 0
            } else {
                isEnd |= 1;
            }
        }
        subprim++;
    }
    return isEnd;
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnAgunea);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityAguneaHitEnemy);

extern AnimationFrame D_us_801829D4[];

void BO6_RicEntityVibhutiCrashCloud(Entity* self) {
    s32 angle;

    switch (self->step) {
    case 0:
        self->primIndex = g_api.AllocPrimitives(PRIM_GT4, 1);
        if (self->primIndex == -1) {
            DestroyEntity(self);
            return;
        }

        self->flags = FLAG_POS_CAMERA_LOCKED | FLAG_HAS_PRIMS;
        self->posX.val = self->ext.vibCrashCloud.parent->ext.vibhutiCrash.x;
        self->posY.val = self->ext.vibCrashCloud.parent->ext.vibhutiCrash.y;
        self->facingLeft =
            self->ext.vibCrashCloud.parent->ext.vibhutiCrash.facing;
        self->flags |= FLAG_UNK_20000000;
        self->unk5A = 0x64;
        self->animSet = 0xE;
        self->palette = PAL_FLAG(0x19E);
        self->anim = D_us_801829D4;
        self->blendMode = BLEND_TRANSP | BLEND_ADD;
        self->drawFlags = ENTITY_OPACITY;
        self->opacity = 0x60;
        self->hitboxWidth = 8;
        self->hitboxHeight = 8;

        angle = (rand() % 512) + 0x300;
        self->velocityX = rcos(angle) << 5;
        self->velocityY = -(rsin(angle) << 5);
        self->step++;
        break;

    case 1:
        self->ext.vibCrashCloud.unk7C++;
        if (self->ext.vibCrashCloud.unk7C > 38) {
            DestroyEntity(self);
        } else {
            self->posX.val += self->velocityX;
            self->posY.val += self->velocityY;
        }
        break;
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityCrashVibhuti);

/* BO6's rebound stone crash particles. Identified by position, not by guess:
   the blueprint table D_us_8018158C lists
     ... AguneaCircle, AguneaLightning, THIS, HitByDark, HitByHoly ...
   and RIC's equivalent table (src/ric/pl_blueprints.c:458) has exactly
     ... AguneaCircle, AguneaLightning, CrashReboundStoneParticles,
         HitByDark, HitByHoly ...
   so this slot is RicEntityCrashReboundStoneParticles (src/ric/2F8E8.c:945),
   which uses ext.subweapon.timer for the same counter. BO6 diverges from RIC
   here in two ways: it sets FLAG_UNK_10000000 rather than
   FLAG_KEEP_ALIVE_OFFCAMERA, and it does not call RicSetSubweaponParams. */
void func_us_801C8590(Entity *arg0)
{
    u16 step;

    step = arg0->step;
    switch (step) {
    case 0:
        arg0->flags = FLAG_UNK_10000000;
        arg0->hitboxWidth = 4;
        arg0->hitboxHeight = 4;
        arg0->step++;
        return;

    case 1:
        arg0->ext.subweapon.timer++;
        if (arg0->ext.subweapon.timer >= 4) {
            DestroyEntity(arg0);
        }
        return;

    default:
        return;
    }
}

extern s32 D_us_80182A0C[];

// Mirrors RIC func_8016D9C4 (src/ric/319C4.c:11) with two differences
// beyond the g_Ric/lookup-table swap: flags are
// FLAG_UNK_10000000 | FLAG_HAS_PRIMS rather than
// FLAG_KEEP_ALIVE_OFFCAMERA | FLAG_HAS_PRIMS, and case 0 does not play
// SFX_RIC_RSTONE_TINK before advancing the step.
void func_us_801C8618(Entity* self) {
    PrimLineG2* prim;
    Primitive* prim2;
    s32 i;
    long angle;
    s32 var_s6;
    s32 var_s5;
    s32 var_s7;
    s32 brightness;

    switch (self->step) {
    case 0:
        self->primIndex = g_api.AllocPrimitives(PRIM_LINE_G2, 20);
        if (self->primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags = FLAG_UNK_10000000 | FLAG_HAS_PRIMS;
        prim = (PrimLineG2*)&g_PrimBuf[self->primIndex];
        for (i = 0; i < 4; i++) {
            prim->preciseX.val = RIC.posX.val;
            prim->preciseY.val = RIC.posY.val - FIX(40);
            prim->priority = 194;
            prim->drawMode = DRAW_HIDE;
            prim->x0 = prim->x1 = RIC.posX.i.hi;
            prim->y0 = prim->y1 = RIC.posY.i.hi - 0x1C;
            prim->r0 = prim->g0 = prim->b0 = 0x80;
            prim->r1 = prim->g1 = prim->b1 = 0x70;
            prim->angle = D_us_80182A0C[i];
            prim->delay = 1;
            prim = (PrimLineG2*)prim->next;
        }
        for (brightness = 0x80; i < 20; i++) {
            if (!(i % 4)) {
                brightness -= 0x10;
                switch (i / 4) {
                case 1:
                    self->ext.et_8016D9C4.lines[0] = prim;
                    break;
                case 2:
                    self->ext.et_8016D9C4.lines[1] = prim;
                    break;
                case 3:
                    self->ext.et_8016D9C4.lines[2] = prim;
                    break;
                case 4:
                    self->ext.et_8016D9C4.lines[3] = prim;
                    break;
                }
            }
            prim->priority = 0xC2;
            prim->drawMode = DRAW_HIDE;
            prim->x0 = prim->x1 = RIC.posX.i.hi;
            prim->y0 = prim->y1 = RIC.posY.i.hi - 0x1C;
            prim->r0 = prim->g0 = prim->b0 = brightness;
            prim->r1 = prim->g1 = prim->b1 = brightness - 0x10;
            prim = (PrimLineG2*)prim->next;
        }
        self->ext.et_8016D9C4.unk90 = 4;
        self->ext.et_8016D9C4.unk8C = self->ext.et_8016D9C4.unk8E = 0;
        self->step++;
        break;
    case 1:
        self->ext.et_8016D9C4.unk8E = 1;
        switch (self->ext.et_8016D9C4.unk8C) {
        case 0:
            prim = (PrimLineG2*)&g_PrimBuf[self->primIndex];
            break;
        case 1:
            prim = self->ext.et_8016D9C4.lines[0];
            break;
        case 2:
            prim = self->ext.et_8016D9C4.lines[1];
            break;
        case 3:
            prim = self->ext.et_8016D9C4.lines[2];
            break;
        case 4:
            prim = self->ext.et_8016D9C4.lines[3];
            break;
        }
        for (i = 0; i < 4; i++) {
            prim->drawMode &= ~DRAW_HIDE;
            prim = (PrimLineG2*)prim->next;
        }
        self->ext.et_8016D9C4.unk8C++;
        if (self->ext.et_8016D9C4.unk8C > 4) {
            self->step++;
        }
        break;
    case 2:
        if (!self->ext.et_8016D9C4.unk90) {
            self->step++;
            break;
        }
        break;
    case 3:
        self->ext.et_8016D9C4.unk90++;
        if (self->ext.et_8016D9C4.unk90 > 4) {
            DestroyEntity(self);
            return;
        }
        break;
    }
    if (!self->ext.et_8016D9C4.unk8E) {
        return;
    }
    prim = (PrimLineG2*)&g_PrimBuf[self->primIndex];
    for (i = 0; i < 4; i++) {
        if (prim->delay) {
            prim->x1 = prim->x0;
            prim->y1 = prim->y0;
            prim->x0 = prim->preciseX.i.hi;
            prim->y0 = prim->preciseY.i.hi;
            var_s7 = ratan2(prim->preciseY.val, FIX(128) - prim->preciseX.val) &
                     0xFFF;
            angle = prim->angle - var_s7;
            if (labs(angle) > 0x800) {
                if (angle < 0) {
                    angle += 0x1000;
                } else {
                    angle -= 0x1000;
                }
            }
            if (angle >= 0) {
                if (angle > 0x80) {
                    var_s6 = 0x80;
                } else {
                    var_s6 = angle;
                }
                angle = var_s6;
            } else {
                if (angle < -0x80) {
                    var_s5 = -0x80;
                } else {
                    var_s5 = angle;
                }
                angle = var_s5;
            }
            prim->angle = prim->angle - angle;
            prim->angle &= 0xFFF;
            prim->velocityX.val = (rcos(prim->angle) << 4 << 4);
            prim->velocityY.val = -(rsin(prim->angle) << 4 << 4);
            prim->preciseX.val += prim->velocityX.val;
            prim->preciseY.val += prim->velocityY.val;
            self->posX.i.hi = prim->preciseX.i.hi;
            self->posY.i.hi = prim->preciseY.i.hi;
            OVL_EXPORT(RicCreateEntFactoryFromEntity)
            (self, BP_CRASH_REBOUND_STONE_PARTICLES, 0);
            if (prim->preciseY.val < 0) {
                prim->delay = 0;
                prim->drawMode |= DRAW_HIDE;
                self->ext.et_8016D9C4.unk90--;
            }
        }
        prim = (PrimLineG2*)prim->next;
    }
    prim = self->ext.et_8016D9C4.lines[0];
    prim2 = &g_PrimBuf[self->primIndex];
    for (i = 0; i < 16; i++) {
        prim->x1 = prim->x0;
        prim->y1 = prim->y0;
        prim->x0 = prim2->x1;
        prim->y0 = prim2->y1;
        prim = (PrimLineG2*)prim->next;
        prim2 = prim2->next;
    }
}

INCLUDE_ASM(
    "boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityCrashReboundStoneExplosion);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityCrashReboundStone);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityCrashBibleBeam);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityCrashBible);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", func_us_801C9DE8);

void func_us_801CA340(Entity* self) {
    OVL_EXPORT(RicCreateEntFactoryFromEntity)(self, FACTORY(0x3F, 1), 0);
    DestroyEntity(self);
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_GetAguneaLightningAngle);

// Richter (BO6): Fisher-Yates shuffle of the Agunea lightning parameter array,
// walking DOWNWARD from the last element and swapping each with a uniformly
// chosen index. `rand() % bufSize` samples the whole array rather than the
// unshuffled prefix, so this is the biased variant, which is what the assembly
// does and not something to "fix".
//
// SHAPE WARNING, same class as func_us_801BC3E0 and func_us_801C488C.
// new_var/new_var2/new_var3 pin which pointers live in which registers across
// the rand() call, and `buf - (-i)` is not the same to GCC 2.7 as `buf + i`.
// This exact body scores 0; it was reached by promoting the seed to a
// score-10 base and letting the supervisor search from there. Re-check any
// tidying with:
//     python3 automation/permuter_promote.py --dir nonmatchings/BO6_AguneaShuffleParams
void BO6_AguneaShuffleParams(s32 bufSize, s32* buf) {
    s32* new_var2;
    s32* new_var3;
    s32* new_var;
    s32 i = bufSize - 1;

    if (i > 0) {
        s32* current = buf - (-i);
        do {
            s32 temp;
            s32* randPtr;

            new_var = &(*current);
            i--;
            new_var3 = buf - (-(rand() % bufSize));
            temp = *new_var;
            new_var2 = new_var3;
            randPtr = new_var2;
            *current = *randPtr;
            current--;
            *randPtr = temp;
        } while (i > 0);
    }
}

void BO6_RicEntityAguneaLightning(Entity* self) {
        s16 sp20;
        s16 sp18;
        s16 sp10;
        s16 sp14;
        u16 step;
        u16 unk7C;
        s16 unk7E;
    Primitive* prim;
    s32 i;
    s32 primIndex;
    s32 randVal;
    s32 seed;
    s16 angle;
    s16 deltaAngle;
    s16 posX;
    s16 posY;
    s16 cosVal;
    s16 sinVal;
    s16 widthNeg;
    s16 widthPos;
    s16 x0, y0, x1, y1, x2, y2, x3, y3;

    step = self->step;
    switch (step) {
    case 0:
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 0xF);
        self->primIndex = primIndex;
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags = 0x18800000;
        prim = &g_PrimBuf[primIndex];
        for (i = 0; i < 0xF; i++) {
            prim->tpage = 0x1A;
            prim->clut = 0x194;
            randVal = (rand() % 5) * 0x10;
            prim->u0 = randVal - 0x70;
            prim->u2 = randVal - 0x70;
            prim->u1 = randVal - 0x50;
            prim->u3 = randVal - 0x50;
            if (rand() & 1) {
                prim->v0 = 0xD0;
                prim->v1 = 0xD0;
                prim->v2 = 0xE0;
                prim->v3 = 0xE0;
            } else {
                prim->v0 = 0xE0;
                prim->v1 = 0xE0;
                prim->v2 = 0xD0;
                prim->v3 = 0xD0;
            }
            prim->priority = 0xC1;
            prim->drawMode = 0xE;
            prim->r0 = 0x80;
            prim->g0 = 0x80;
            prim->b0 = 0x80;
            prim->r1 = 0x80;
            prim->g1 = 0x80;
            prim->b1 = 0x80;
            prim->r2 = 0x80;
            prim->g2 = 0x80;
            prim->b2 = 0x80;
            prim->r3 = 0x80;
            prim->g3 = 0x80;
            prim->b3 = 0x80;
            prim = prim->next;
        }
        prim = &g_PrimBuf[self->primIndex];
        sp20 = ((self->params >> 8) << 9) - 0x100 + (rand() & 0x1FF);
        seed = rand();
        for (i = 0; i < 0xF; i++) {
            srand(seed);
            posX = self->posX.i.hi;
            posY = self->posY.i.hi;
            angle = BO6_GetAguneaLightningAngle(&sp10, sp20, i, &sp18);
            deltaAngle = sp18;
            widthNeg = 8;
            if (i == 0) {
                widthNeg = 2;
            }
            widthPos = 2;
            if (i < 7) {
                widthPos = 8;
            }
            cosVal = rcos(angle);
            sinVal = rsin(angle);
            x0 = sp10 + ((-sinVal * -widthNeg) >> 12);
            y0 = sp14 + ((cosVal * -widthNeg) >> 12);
            x1 = sp10 + ((cosVal * deltaAngle - sinVal * -widthPos) >> 12);
            y1 = sp14 + ((sinVal * deltaAngle + cosVal * -widthPos) >> 12);
            x2 = sp10 + ((-sinVal * widthNeg) >> 12);
            y2 = sp14 + ((cosVal * widthNeg) >> 12);
            x3 = sp10 + ((cosVal * deltaAngle - sinVal * widthPos) >> 12);
            y3 = sp14 + ((sinVal * deltaAngle + cosVal * widthPos) >> 12);
            prim->x0 = x0;
            prim->y0 = y0;
            prim->x1 = x1;
            prim->y1 = y1;
            prim->x2 = x2;
            prim->y2 = y2;
            prim->x3 = x3;
            prim->y3 = y3;
            prim = prim->next;
        }
        self->ext.agunea.unk7E = 1;
        self->step++;
        return;
    case 1:
        prim = &g_PrimBuf[self->primIndex];
        for (i = 0; i < 0xF; i++) {
            prim->drawMode &= 0xFFF7;
            prim = prim->next;
        }
        self->step++;
        break;
    case 2:
        unk7C = self->ext.agunea.unk7C + 1;
        self->ext.agunea.unk7C = unk7C;
        if ((s16)unk7C >= 5) {
            prim = &g_PrimBuf[self->primIndex];
            for (i = 0; i < 0xF; i++) {
                prim->clut = 0x15F;
                prim->r0 = 0xFF;
                prim->g0 = 0xFF;
                prim->b0 = 0xFF;
                prim->r1 = 0xFF;
                prim->g1 = 0xFF;
                prim->b1 = 0xFF;
                prim->r2 = 0xFF;
                prim->g2 = 0xFF;
                prim->b2 = 0xFF;
                prim->r3 = 0xFF;
                prim->g3 = 0xFF;
                prim->b3 = 0xFF;
                prim->v0 -= 0x10;
                prim->v1 -= 0x10;
                prim->v2 -= 0x10;
                prim->v3 -= 0x10;
                prim = prim->next;
            }
            self->ext.agunea.unk7C = 0;
            self->step++;
        }
        return;
    case 3:
    case 5:
        prim = &g_PrimBuf[self->primIndex];
        for (i = 0; i < 0xF; i++) {
            prim->clut = 0x194;
            prim = prim->next;
        }
        self->step++;
        return;
    case 4:
        prim = &g_PrimBuf[self->primIndex];
        for (i = 0; i < 0xF; i++) {
            prim->clut = 0x15F;
            prim = prim->next;
        }
        self->step++;
        return;
    case 6:
        prim = &g_PrimBuf[self->primIndex];
        for (i = 0; i < 0xF; i++) {
            unk7C = self->ext.agunea.unk7C;
            prim->r0 = 0x60 - (unk7C * 4);
            prim->g0 = 0x60 - (unk7C * 4);
            prim->b0 = 0x60 - (unk7C * 4);
            prim->r1 = 0x60 - (unk7C * 4);
            prim->g1 = 0x60 - (unk7C * 4);
            prim->b1 = 0x60 - (unk7C * 4);
            prim->r2 = 0x60 - (unk7C * 4);
            prim->g2 = 0x60 - (unk7C * 4);
            prim->b2 = 0x60 - (unk7C * 4);
            prim->r3 = 0x60 - (unk7C * 4);
            prim->g3 = 0x60 - (unk7C * 4);
            prim->b3 = 0x60 - (unk7C * 4);
            prim = prim->next;
        }
        unk7C = self->ext.agunea.unk7C + 1;
        self->ext.agunea.unk7C = unk7C;
        if ((s16)unk7C >= 0x10) {
            DestroyEntity(self);
        }
        return;
    default:
        return;
    }
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityAguneaCircle);

INCLUDE_ASM(
    "boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnStopwatchCircle);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_EntityStopWatch);

void OVL_EXPORT(RicEntitySubwpnBibleTrail)(Entity* entity) {
    Primitive* prim;

    switch (entity->step) {
    case 0:
        entity->primIndex = g_api.AllocPrimitives(PRIM_GT4, 1);
        if (entity->primIndex == -1) {
            DestroyEntity(entity);
            return;
        }
        entity->flags = FLAG_UNK_10000000 | FLAG_HAS_PRIMS;
        prim = &g_PrimBuf[entity->primIndex];
        prim->tpage = 0x1C;
        prim->clut = 0x19D;
        prim->u0 = prim->u2 = 0x20;
        prim->v0 = prim->v1 = 0;
        prim->u1 = prim->u3 = 0x30;
        prim->v2 = prim->v3 = 0x10;
        prim->x0 = prim->x2 = entity->posX.i.hi - 8;
        prim->x1 = prim->x3 = entity->posX.i.hi + 8;
        prim->y0 = prim->y1 = entity->posY.i.hi - 8;
        prim->y2 = prim->y3 = entity->posY.i.hi + 8;
        prim->priority = entity->zPriority;
        prim->drawMode = DRAW_TPAGE | DRAW_COLORS | DRAW_TRANSP;
        entity->ext.et_BibleSubwpn.unk7E = 0x60;
        entity->step++;
        break;
    case 1:
        entity->ext.et_BibleSubwpn.unk7C++;
        if (entity->ext.et_BibleSubwpn.unk7C > 5) {
            entity->step++;
        }
        entity->ext.et_BibleSubwpn.unk7E -= 8;
        break;
    case 2:
        DestroyEntity(entity);
        return;
    }
    prim = &g_PrimBuf[entity->primIndex];
    PCOL(prim) = entity->ext.et_BibleSubwpn.unk7E;
}

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntitySubwpnBible);

INCLUDE_RODATA("boss/bo6/nonmatchings/us_3E79C", D_us_801A7028);

INCLUDE_RODATA("boss/bo6/nonmatchings/us_3E79C", D_us_801A7030);

INCLUDE_ASM("boss/bo6/nonmatchings/us_3E79C", BO6_RicEntityCrashCrossBeam);
