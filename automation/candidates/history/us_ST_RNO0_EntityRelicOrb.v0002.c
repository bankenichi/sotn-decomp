/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RNO0:EntityRelicOrb
   attempt: 4/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (stubs declared)
   origin : src/st/rno0/e_collect.c
   asm    : asm/us/st/rno0/nonmatchings/e_collect/EntityRelicOrb.s

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

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
extern void (*g_api_LoadEquipIcon)(s32 equipIcon, s32 palette, s32 index);
extern s32 (*g_api_func_800FE044)(s32, s32);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int PrizeDropFall();
extern int PrizeDropFall2();
extern int MoveEntity();
extern int FallEntity();
extern int CollectHeart();
extern int CollectSubweapon();
extern int SetStep();
extern int CollectLifeVessel();
extern int CollectDummy();
extern int AnimateEntity();
extern int CheckFieldCollision();
extern int BlinkItem();
extern int update();

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
extern void DestroyEntity(Entity* entity);
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
extern void (*g_api_LoadEquipIcon)(s32 equipIcon, s32 palette, s32 index);
extern s32 (*g_api_func_800FE044)(s32, s32);
extern int ClearImage(RECT* rect, u_char r, u_char g, u_char b);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int InitializeEntity();
extern int LoadTPage();

#define HEART_DROP_CASTLE_FLAG 0x138

// Local index -> global castle-collectible index base for this room's heart
// drops. Storage lives in an undecompiled data blob.
extern u16 D_us_80180F8C[];

// Heart pickup values, indexed by CollectHeart's heartIdx. Storage lives in an
// undecompiled data blob.
extern s8 D_us_80181898[];

// Gold pickup values, indexed by (goldSize - 2). Storage lives in the
// undecompiled data blob.
extern u32 D_us_80181808[];

extern const char* g_goldCollectTexts[];

extern void BottomCornerText(u8* str, u8 leftAlign);

// aluric_subweapons_idx, pre-shifted by -14 elements so it can be indexed
// directly by subWeaponIdx (14..22). Storage lives in the undecompiled data
// blob.
extern u16 D_us_8018179C[];

// aluric_subweapons_id, indexed by g_Status.subWeapon. Storage lives in the
// undecompiled data blob.
extern u16 D_us_801817CC[];

// InitializeEntity descriptors used by the entities below.
extern EInit g_EInitObtainable;
extern EInit OVL_EXPORT(EInitParticle);

// EntityExplosion's per-type Y velocity and animation-list tables. Storage
// lives in undecompiled data blobs.
extern s32 D_us_8018189C[];
extern u8* D_us_80181948[];

// g_SubweaponAnimPrizeDrop: per-item animation script pointers, indexed by
// itemId. Storage lives in an undecompiled data blob.
extern u8* D_us_80181830[];

// D_80180EB8: field-collision check offsets shared by the drop entities.
// Storage lives in an undecompiled data blob.
extern s16 D_us_80181890[];

// Icon-slot allocation table. Was `extern u16 D_us_801D4B4C[32]`, a raw
// address. It is g_ItemIconSlots, declared by src/st/st_update.h as
// `u16 g_ItemIconSlots[ICON_SLOT_NUM]` (32 u16 = 0x40) and now DEFINED by
// rno0's st_update shim rather than extracted as anonymous bss.
extern u16 g_ItemIconSlots[];

// EntityRelicOrb's support tables. Storage lives in undecompiled data blobs.
extern const char* D_us_8018195C[];  // g_RelicOrbTexts
extern s16 D_us_80181960[];          // g_RelicOrbTextBg1EY
extern s16 D_us_80181970[];          // g_RelicOrbTextBg1SY
extern s16 D_us_80181980[];          // g_RelicOrbTextBg2SY
extern s16 D_us_80181990[];          // g_RelicOrbTextBg2EY
extern s16 D_us_801819A0[];          // g_RelicOrbSparkleX
extern s16 D_us_801819B0[];          // g_RelicOrbSparkleY

// Verbatim copy of PrizeDropFall in src/st/e_collect.h.
// Kept in sync by hand: this file cannot include that header.
static void PrizeDropFall(void) {
    if (g_CurrentEntity->velocityY >= 0) {
        g_CurrentEntity->ext.equipItemDrop.fallSpeed +=
            g_CurrentEntity->ext.equipItemDrop.gravity;
        g_CurrentEntity->velocityX =
            g_CurrentEntity->ext.equipItemDrop.fallSpeed;
        if (g_CurrentEntity->velocityX == FIX(1) ||
            g_CurrentEntity->velocityX == FIX(-1)) {
            g_CurrentEntity->ext.equipItemDrop.gravity =
                -g_CurrentEntity->ext.equipItemDrop.gravity;
        }
    }

    if (g_CurrentEntity->velocityY < FIX(0.25)) {
        g_CurrentEntity->velocityY += FIX(0.125);
    }
}

// Verbatim copy of PrizeDropFall2 in src/st/e_collect.h.
// Kept in sync by hand: this file cannot include that header.
static void PrizeDropFall2(u16 arg0) {
    Collider collider;

    if (g_CurrentEntity->velocityX < 0) {
        g_api.CheckCollision(g_CurrentEntity->posX.i.hi,
                             g_CurrentEntity->posY.i.hi - 7, &collider, 0);
        if (collider.effects & EFFECT_NOTHROUGH) {
            g_CurrentEntity->velocityY = 0;
        }
    }

    g_api.CheckCollision(g_CurrentEntity->posX.i.hi,
                         g_CurrentEntity->posY.i.hi + 7, &collider, 0);

    if (arg0) {
        if (!(collider.effects & EFFECT_NOTHROUGH)) {
            MoveEntity();
            FallEntity();
            return;
        }

        g_CurrentEntity->velocityX = 0;
        g_CurrentEntity->velocityY = 0;

        if (collider.effects & EFFECT_QUICKSAND) {
            g_CurrentEntity->posY.val += FIX(0.125);
            return;
        }

        g_CurrentEntity->posY.i.hi += collider.unk18;
        return;
    }

    if (!(collider.effects & EFFECT_NOTHROUGH)) {
        MoveEntity();
        PrizeDropFall();
    }
}

// This function is messy, maybe there's a better way.
static void CollectHeart(u16 heartIdx) {
    g_api.PlaySfx(SFX_HEART_PICKUP);
    g_Status.hearts += D_us_80181898[heartIdx];

    if (g_Status.hearts > g_Status.heartsMax) {
        g_Status.hearts = g_Status.heartsMax;
    }

    DestroyEntity(g_CurrentEntity);
}

void CollectGold(u16 goldSize) {
    g_api.PlaySfx(SFX_GOLD_PICKUP);
    goldSize -= 2;
    g_Status.gold += D_us_80181808[goldSize];
    if (g_Status.gold > MAX_GOLD) {
        g_Status.gold = MAX_GOLD;
    }
    if (g_unkGraphicsStruct.BottomCornerTextTimer) {
        g_api.FreePrimitives(g_unkGraphicsStruct.BottomCornerTextPrims);
        g_unkGraphicsStruct.BottomCornerTextTimer = 0;
    }

    BottomCornerText((u8*)g_goldCollectTexts[goldSize], true);
    DestroyEntity(g_CurrentEntity);
}

static void CollectSubweapon(u16 subWeaponIdx) {
    Entity* player = &PLAYER;
    u16 subWeapon;

    g_api.PlaySfx(SFX_ITEM_PICKUP);
    subWeapon = g_Status.subWeapon;
    g_Status.subWeapon = D_us_8018179C[subWeaponIdx];

    if (subWeapon == g_Status.subWeapon) {
        subWeapon = 1;
        g_CurrentEntity->unk6D[0] = 0x10;
    } else {
        subWeapon = D_us_801817CC[subWeapon];
        g_CurrentEntity->unk6D[0] = 0x60;
    }

    if (subWeapon) {
        g_CurrentEntity->params = subWeapon;
        g_CurrentEntity->posY.i.hi = player->posY.i.hi + 12;
        SetStep(7);
        g_CurrentEntity->velocityY = FIX(-2.5);
        g_CurrentEntity->animCurFrame = 0;
        g_CurrentEntity->ext.equipItemDrop.sparkleTimer = 5;
        if (player->facingLeft ^ 1) {
            g_CurrentEntity->velocityX = FIX(-2);
        } else {
            g_CurrentEntity->velocityX = FIX(2);
        }
    } else {
        DestroyEntity(g_CurrentEntity);
    }
}

void CollectHeartVessel(void) {
    if (g_PlayableCharacter != PLAYER_ALUCARD) {
        g_api.PlaySfx(SFX_HEART_PICKUP);
        g_Status.hearts += HEART_VESSEL_RICHTER;

        if (g_Status.hearts > g_Status.heartsMax) {
            g_Status.hearts = g_Status.heartsMax;
        }
    } else {
        // Alucard's version
        g_api.PlaySfx(SFX_HEART_PICKUP);
        g_api.func_800FE044(HEART_VESSEL_INCREASE, 0x4000);
    }
    DestroyEntity(g_CurrentEntity);
}

// Verbatim copy of CollectLifeVessel in src/st/e_collect.h.
// Kept in sync by hand: this file cannot include that header.
static void CollectLifeVessel(void) {
    g_api.PlaySfx(SFX_HEART_PICKUP);
    g_api.func_800FE044(LIFE_VESSEL_INCREASE, 0x8000);
    DestroyEntity(g_CurrentEntity);
}

static void CollectDummy(u16 id) {
    DestroyEntity(g_CurrentEntity);
}

INCLUDE_RODATA("st/rno0/nonmatchings/e_collect", D_us_801B5B18);

INCLUDE_RODATA("st/rno0/nonmatchings/e_collect", D_us_801B5B20);

INCLUDE_RODATA("st/rno0/nonmatchings/e_collect", D_us_801B5B28);

INCLUDE_RODATA("st/rno0/nonmatchings/e_collect", D_us_801B5B30);

INCLUDE_RODATA("st/rno0/nonmatchings/e_collect", D_us_801B5B38);

INCLUDE_RODATA("st/rno0/nonmatchings/e_collect", D_us_801B5B40);

INCLUDE_RODATA("st/rno0/nonmatchings/e_collect", D_us_801B5B48);

INCLUDE_RODATA("st/rno0/nonmatchings/e_collect", D_us_801B5B50);

INCLUDE_RODATA("st/rno0/nonmatchings/e_collect", D_us_801B5B58);

INCLUDE_RODATA("st/rno0/nonmatchings/e_collect", D_us_801B5B60);

// if self->params & 0x8000 then the item will not disappear
// ST0 seems to contain the earliest known version of this entity.
// MAD has some very minor enhancements that brings it closer to the US build,
// such as Life/Heart upgrade drops.
// US essentially adds castle flags for unique drops
// PSP iterates on top of the US version by adding drops for Maria
// PSP ST0 iterates on top of ST0 with the only change on CollectDummy params
void EntityPrizeDrop(Entity* self) {
    Primitive* prim;
    u16 itemId;
    s16 index;
    s32 primIndex;
    Collider collider;

    itemId = self->params & 0x7FFF;
    if (self->step) {
        AnimateEntity(D_us_80181830[itemId], self);
    }
    if (self->step > 1 && self->step < 5 && self->hitFlags) {
        self->step = 5;
    }
    self->palette = 0;
    if (self->unk6D[0] >= 0x18 && !(g_GameTimer & 2) && self->params != 1) {
        self->palette = PAL_FLAG(PAL_FILL_WHITE);
    }
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitObtainable);
        self->zPriority = g_unkGraphicsStruct.g_zEntityCenter - 0x14;
        self->blendMode = BLEND_NO;
        if (itemId > 23) {
            itemId = self->params = 0;
        }

        if (itemId >= 14 && itemId < 23 &&
            itemId == D_us_801817CC[g_Status.subWeapon]) {
            itemId = 1;
            self->params = 1;
        }
        if (!itemId || itemId == 2) {
            self->hitboxWidth = 4;
        }
        break;
    case 1:
        g_api.CheckCollision(self->posX.i.hi, self->posY.i.hi, &collider, 0);
        if (collider.effects & EFFECT_NOTHROUGH_PLUS) {
            DestroyEntity(self);
        } else {
            self->step++;
            index = self->ext.equipItemDrop.castleFlag;
            if (index) {
                index--;
                g_CastleFlags[(index >> 3) + ENEMY_LIST_RAREDROP_1B0] |=
                    1 << (index & 7);
            }
        }
        if (!itemId) {
            self->ext.equipItemDrop.fallSpeed = FIX(-1);
            self->ext.equipItemDrop.gravity = 0x800;
        }
        break;
    case 2:
        if (self->velocityY < 0) {
            g_api.CheckCollision(
                self->posX.i.hi, self->posY.i.hi - 7, &collider, 0);
            if (collider.effects & EFFECT_NOTHROUGH) {
                self->velocityY = 0;
            }
        }
        MoveEntity();
        g_api.CheckCollision(
            self->posX.i.hi, self->posY.i.hi + 7, &collider, 0);
        if (itemId) {
            if (collider.effects & EFFECT_NOTHROUGH && self->velocityY > 0) {
                self->velocityX = 0;
                self->velocityY = 0;
                self->posY.i.hi += collider.unk18;
                self->ext.equipItemDrop.aliveTimer = 0xF0;
                self->step++;
            } else {
                FallEntity();
            }
            CheckFieldCollision(D_us_80181890, 2);
        } else if (collider.effects & EFFECT_NOTHROUGH) {
            self->posY.i.hi += collider.unk18;
            self->ext.equipItemDrop.aliveTimer = 0x60;
            self->step++;
        } else {
            PrizeDropFall();
        }
        break;
    case 3:
        PrizeDropFall2(itemId);
        if (!(self->params & 0x8000) && !--self->ext.equipItemDrop.aliveTimer) {
            if (itemId) {
                self->ext.equipItemDrop.aliveTimer = 80;
            } else {
                self->ext.equipItemDrop.aliveTimer = 64;
            }
            self->step++;
        }
        break;
    case 4:
        PrizeDropFall2(itemId);
        if (--self->ext.equipItemDrop.aliveTimer) {
            if (self->ext.equipItemDrop.aliveTimer & 2) {
                self->animCurFrame = 0;
            }
        } else {
            DestroyEntity(self);
            return;
        }
        break;
    case 5:
        if (itemId < 2) {
            CollectHeart(itemId);
        } else if (itemId < 12) {
            CollectGold(itemId);
        } else if (itemId == 12) {
            CollectHeartVessel();
        } else if (itemId < 14) {
            CollectDummy(itemId);
        } else if (itemId < 23) {
            CollectSubweapon(itemId);
        } else if (itemId == 23) {
            CollectLifeVessel();
        } else {
            DestroyEntity(self);
            return;
        }
        break;
    case 6:
    case 7:
        switch (self->step_s) {
        case 0:
            self->animCurFrame = 0;
            if (itemId >= 14 && itemId < 23 &&
                itemId == D_us_801817CC[g_Status.subWeapon]) {
                itemId = 1;
                self->params = 1;
            }
            primIndex = g_api.AllocPrimitives(PRIM_GT4, 1);
            if (primIndex != -1) {
                self->primIndex = primIndex;
                self->flags |= FLAG_HAS_PRIMS;
                prim = &g_PrimBuf[primIndex];
                prim->tpage = 0x1A;
                prim->clut = 0x170;
                prim->u0 = prim->u2 = prim->v0 = prim->v1 = 0;
                prim->u1 = prim->u3 = prim->v2 = prim->v3 = 0x20;
                PCOL(prim) = 0x80;
                prim->drawMode = DRAW_HIDE;
                prim->priority = self->zPriority + 1;
                self->step_s++;
            }
            break;
        case 1:
            MoveEntity();
            g_api.CheckCollision(
                self->posX.i.hi, self->posY.i.hi + 7, &collider, 0);
            if (collider.effects & EFFECT_NOTHROUGH && self->velocityY > 0) {
                self->velocityX = 0;
                self->velocityY = 0;
                self->posY.i.hi += collider.unk18;
                self->step_s++;
            } else {
                FallEntity();
            }
            CheckFieldCollision(D_us_80181890, 2);
            self->animCurFrame = 0;
            if (self->ext.equipItemDrop.sparkleTimer) {
                self->ext.equipItemDrop.sparkleTimer--;
            } else {
                prim = &g_PrimBuf[self->primIndex];
                prim->x0 = prim->x2 = self->posX.i.hi - 1;
                prim->x1 = prim->x3 = self->posX.i.hi + 1;
                prim->y0 = prim->y1 = self->posY.i.hi - 1;
                prim->y2 = prim->y3 = self->posY.i.hi + 1;
                prim->drawMode = DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS |
                                 DRAW_UNK02 | DRAW_TRANSP;
            }
            break;
        case 2:
            PrizeDropFall2(itemId);
            prim = &g_PrimBuf[self->primIndex];
            self->ext.equipItemDrop.sparkleTimer++;
            if (self->ext.equipItemDrop.sparkleTimer < 17) {
                index = self->ext.equipItemDrop.sparkleTimer;
                self->animCurFrame = 0;
            } else {
                index = 32 - self->ext.equipItemDrop.sparkleTimer;
                PRED(prim) -= 8;
                PGRN(prim) -= 8;
                PBLU(prim) -= 8;
            }
            prim->x0 = prim->x2 = self->posX.i.hi - index;
            prim->x1 = prim->x3 = self->posX.i.hi + index;
            prim->y0 = prim->y1 = self->posY.i.hi - index;
            prim->y2 = prim->y3 = self->posY.i.hi + index;
            if (self->ext.equipItemDrop.sparkleTimer == 32) {
                g_api.FreePrimitives(self->primIndex);
                self->flags &= ~FLAG_HAS_PRIMS;
                self->ext.equipItemDrop.aliveTimer = 208;
                self->step = 3;
                self->step_s = 0;
            }
            break;
        }
        break;
    }
}

// params: (& 0xFF) The explosion type
//         (& 0xF0) These explosion types use a different (hardcoded) palette
//                  and drawMode
//         (& 0xFF00) If non-zero, ((& 0xFF00) >> 8) will override zPriority
void EntityExplosion(Entity* entity) {
    if (!entity->step) {
        InitializeEntity(OVL_EXPORT(EInitParticle));
        entity->pose = 0;
        entity->poseTimer = 0;
        entity->animSet = ANIMSET_DRA(2);
        entity->blendMode = BLEND_TRANSP | BLEND_ADD;
        if (entity->params & 0xF0) {
            entity->palette = PAL_FLAG(PAL_UNK_195);
            entity->blendMode = BLEND_TRANSP;
        }

        if (entity->params & 0xFF00) {
            entity->zPriority = (entity->params & 0xFF00) >> 8;
        }
        entity->params &= 15;
        entity->velocityY = D_us_8018189C[entity->params];
    } else {
        entity->posY.val += entity->velocityY;

        if (!AnimateEntity(D_us_80181948[entity->params], entity)) {
            DestroyEntity(entity);
        }
    }
}

// Verbatim copy of BlinkItem in src/st/e_collect.h.
// Kept in sync by hand: this file cannot include that header.
static void BlinkItem(Entity* self, u16 timer) {
    Primitive* prim;
    s32 temp;
    prim = &g_PrimBuf[self->primIndex];

    prim->x0 = prim->x2 = self->posX.i.hi - 7;
    prim->x1 = prim->x3 = prim->x0 + 14;

    prim->y0 = prim->y1 = self->posY.i.hi - 7;
    prim->y2 = prim->y3 = prim->y0 + 14;

    if (timer & 2) {
        PCOL(prim) = 0xFF;
    } else {
        PCOL(prim) = 0x80;
    }
}

void EntityEquipItemDrop(Entity* self) {
    Collider collider;
    Primitive* prim;
    s16 i;
    u16 itemId;
    s16 index;
    s32 primIndex;
    const char* name;

    itemId = self->params & 0x7FFF;
    if (self->step >= 2 && self->step < 5 && self->hitFlags) {
        self->step = 5;
    }

    switch (self->step) {
    case 0:
        if (g_PlayableCharacter != PLAYER_ALUCARD) {
            self->params = 0;
            self->pfnUpdate = EntityPrizeDrop;
            self->entityId = 3;
            SetStep(0);
            EntityPrizeDrop(self);
            return;
        }
        InitializeEntity(g_EInitObtainable);
        self->ext.equipItemDrop.timer = 0;
        break;
    case 1:
        g_api.CheckCollision(self->posX.i.hi, self->posY.i.hi, &collider, 0);
        if (collider.effects & EFFECT_NOTHROUGH_PLUS) {
            DestroyEntity(self);
            break;
        }

        for (i = 0; i < ICON_SLOT_NUM; i++) {
            if (!g_ItemIconSlots[i]) {
                break;
            }
        }
        if (i >= ICON_SLOT_NUM) {
            DestroyEntity(self);
            return;
        }
        index = self->ext.equipItemDrop.castleFlag;
        if (index) {
            index--;
            g_CastleFlags[(index >> 3) + ENEMY_LIST_RAREDROP_1B0] |=
                1 << (index & 7);
        }
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 1);
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        g_ItemIconSlots[i] = 0x1E0;
        self->ext.equipItemDrop.iconSlot = i;
        if (itemId < NUM_HAND_ITEMS) {
            g_api.LoadEquipIcon(g_api.equipDefs[itemId].icon,
                                g_api.equipDefs[itemId].iconPalette, i);
        } else {
            itemId -= NUM_HAND_ITEMS;
            g_api.LoadEquipIcon(g_api.accessoryDefs[itemId].icon,
                                g_api.accessoryDefs[itemId].iconPalette, i);
        }

        prim = &g_PrimBuf[primIndex];
        prim->tpage = 0x1A;
        prim->clut = i + 464;

        prim->u0 = prim->u2 = (u8)(i & 7) * 0x10 + 1;
        prim->u1 = prim->u3 = prim->u0 + 0xE;

        prim->v0 = prim->v1 = (u8)(i & 0x18) * 2 + 0x81;
        prim->v2 = prim->v3 = prim->v0 + 0xE;

        prim->priority = 0x80;
        prim->drawMode = DRAW_UNK02 | DRAW_COLORS;

        self->ext.equipItemDrop.timer = 128;
        self->step++;
        break;
    case 2:
        if (self->velocityY < 0) {
            g_api.CheckCollision(
                self->posX.i.hi, self->posY.i.hi - 7, &collider, 0);
            if (collider.effects & EFFECT_NOTHROUGH) {
                self->velocityY = 0;
            }
        }
        MoveEntity();
        g_api.CheckCollision(
            self->posX.i.hi, self->posY.i.hi + 7, &collider, 0);
        if ((collider.effects & EFFECT_NOTHROUGH) && self->velocityY > 0) {
            self->velocityX = 0;
            self->velocityY = 0;
            self->posY.i.hi += collider.unk18;
            self->ext.equipItemDrop.aliveTimer = 240;
            self->step++;
        } else {
            FallEntity();
        }
        CheckFieldCollision(D_us_80181890, 2);
        break;
    case 3:
        PrizeDropFall2(1);
        if (!(self->params & 0x8000)) {
            if (!--self->ext.equipItemDrop.aliveTimer) {
                self->ext.equipItemDrop.aliveTimer = 80;
                self->step++;
            }
        } else {
            i = self->ext.equipItemDrop.iconSlot;
            g_ItemIconSlots[i] = 0x10;
        }
        break;
    case 4:
        PrizeDropFall2(1);
        if (--self->ext.equipItemDrop.aliveTimer) {
            prim = &g_PrimBuf[self->primIndex];
            if (self->ext.equipItemDrop.aliveTimer & 2) {
                prim->drawMode = DRAW_HIDE;
            } else {
                prim->drawMode = DRAW_UNK02;
            }
        } else {
            DestroyEntity(self);
        }
        break;
    case 5:
        if (g_unkGraphicsStruct.BottomCornerTextTimer) {
            g_api.FreePrimitives(g_unkGraphicsStruct.BottomCornerTextPrims);
            g_unkGraphicsStruct.BottomCornerTextTimer = 0;
        }
        g_api.PlaySfx(SFX_ITEM_PICKUP);
        if (itemId < NUM_HAND_ITEMS) {
            name = g_api.equipDefs[itemId].name;
            g_api.AddToInventory(itemId, EQUIP_HAND);
        } else {
            itemId -= NUM_HAND_ITEMS;
            name = g_api.accessoryDefs[itemId].name;
            g_api.AddToInventory(itemId, EQUIP_ARMOR);
        }
        BottomCornerText((u8*)name, true);
        DestroyEntity(self);
        break;
    }

    if (self->step > 1) {
        if (self->ext.equipItemDrop.timer) {
            self->ext.equipItemDrop.timer--;
        }
        BlinkItem(self, self->ext.equipItemDrop.timer);
    }
}

// Verbatim copy of BlitChar in src/st/blit_char.h.
// Kept in sync by hand: this file cannot include that header.
char* BlitChar(char* str, u16* xOffset, u8* pix, u16 stride) {
    const u16 DOUBLE_SPACE = 0x8140;
    const u16 RIGHT_DOUBLE_QUOTATION_MARK = 0x8168;

    const int FontWidth = 12;
    const int FontHeight = 16;
    const int FontStride = FontWidth / 2;

    u16 ch;
    s32 chSize;
    s32 i, j;
    s32 letterWidth;
    u8* chPix;
    u8* ptr;

    // converts the ASCII character into Shift-JIS
    ch = *str++;
    chSize = 0;
    if (ch >= 'a' && ch <= 'z') {
        ch += 0x8220;
    } else if (ch >= 'A' && ch <= 'Z') {
        ch += 0x821F;
    } else {
        if (ch == ' ') {
            ch = DOUBLE_SPACE;
            chSize = 2;
        } else {
            ch = *str++ | (ch << 8);
            if (ch == DOUBLE_SPACE) {
                chSize = 2;
            }
        }
    }

    if (ch == RIGHT_DOUBLE_QUOTATION_MARK) {
        str += 2;
    }

    // use the converted Shift-JIS character to retrieve the font data
    chPix = g_api.func_80106A28(ch, 1);
    while (true) {
        if (ch == DOUBLE_SPACE) {
            break;
        }

        for (i = 0; i < FontHeight; i++) {
            if (chPix[i * FontStride]) {
                break;
            }
        }
        if (i != FontHeight) {
            break;
        }

        // Trim character width from the left-hand side
        for (i = 0; i < FontHeight; i++) {
            ptr = &chPix[i * FontStride];
            for (j = 0; j < 5; j++) {
                ptr[0] = ptr[1];
                ptr++;
            }
            *ptr = 0;
        }
    }

    // scroll every pixel of the letter and finds the furthest horizontal pixel
    // to calculate what the width is
    for (i = 0, letterWidth = 0; i < FontHeight; i++) {
        for (j = 0; j < FontStride; j++) {
            if (chPix[i * FontStride + j] && letterWidth < j) {
                letterWidth = j;
            }
        }
    }

    // Check the very last vertical pixel
    for (i = 0; i < FontHeight; i++) {
        if (chPix[letterWidth + i * FontStride] & 0xF0) {
            break;
        }
    }
    if (i != FontHeight) {
        letterWidth++;
    }

    // Adds at least a vertical pixel of padding at the end of the character
    if (letterWidth < FontStride) {
        letterWidth++;
    }

    // Copy content to destination
    for (i = 0; i < FontHeight; i++) {
        ptr = &pix[*xOffset + i * stride];
        *ptr++ = *chPix++;
        *ptr++ = *chPix++;
        *ptr++ = *chPix++;
        *ptr++ = *chPix++;
        *ptr++ = *chPix++;
        *ptr++ = *chPix++;
    }

    *xOffset += letterWidth + chSize;
    return str;
}

INCLUDE_RODATA("st/rno0/nonmatchings/e_collect", D_us_801B5BA0);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern RelicDesc* g_api_relicDefs;

void EntityRelicOrb(Entity* self) {
    Primitive* prim;
    s32 relicId;
    s32 iconSlot;
    s32 i;
    s32 var_a3;
    s16 var_s0;
    s16 temp_v0;
    u16 step;
    u16 params;
    RelicDesc* relicDef;
    u8* pix;
    s16 sp20;
    s16 sp22;
    s16 sp24;
    s16 sp26;
    u16 sp28;

    step = self->step;
    params = self->params & 0x7FFF;
    relicId = params;

    if (step == 0) {
        if (g_Status.relics[relicId] & 1) {
            DestroyEntity(self);
            return;
        }
        InitializeEntity(g_EInitObtainable);
        iconSlot = 0;
        for (i = 0; i < 0x1F; i++) {
            if (g_ItemIconSlots[i] == 0) {
                iconSlot = i;
                break;
            }
        }
        if (iconSlot >= 0x1F) {
            self->step = 0;
            return;
        }
        prim = g_api_AllocPrimitives(PRIM_GT4, 7);
        if (prim == (void*)-1) {
            self->step = 0;
            return;
        }
        self->primIndex = (s32)prim;
        self->ext.relicOrb.iconSlot = iconSlot;
        self->flags |= 0x800000;
        g_ItemIconSlots[iconSlot] = 0x10;
        relicDef = &g_api_relicDefs[relicId];
        g_api_LoadEquipIcon(relicDef->icon, relicDef->iconPalette, iconSlot);
        prim = &g_PrimBuf[self->primIndex];
        var_a3 = 0;
        if (prim != NULL) {
            temp_v0 = (iconSlot & 7) * 0x10;
            do {
                if (var_a3 != 0) {
                    prim->drawMode = 8;
                } else {
                    prim->tpage = 0x1A;
                    prim->clut = iconSlot + 0x1D0;
                    prim->u0 = temp_v0 | 1;
                    prim->u2 = temp_v0 | 1;
                    prim->u1 = temp_v0 | 0xF;
                    prim->u3 = temp_v0 | 0xF;
                    prim->v0 = (iconSlot & 0x18) * 2 | 0x81;
                    prim->v1 = (iconSlot & 0x18) * 2 | 0x81;
                    prim->v2 = (iconSlot & 0x18) * 2 | 0x8F;
                    prim->v3 = (iconSlot & 0x18) * 2 | 0x8F;
                    prim->drawMode = 6;
                }
                prim->priority = 0x7E;
                prim = prim->next;
                var_a3++;
            } while (prim != NULL);
        }
        self->posY.i.lo = -0x8000;
        self->velocityY = 0x4000;
        self->ext.relicOrb.floatTimer = 0x40;
        self->ext.relicOrb.yFloatSpeed = -0x200;
        self->step++;
    } else if (step < 5) {
        if (self->hitFlags != 0) {
            self->step = 5;
        }
    } else if (step == 5) {
        g_api_func_800FE044(relicId, 0x2000);
        if (relicId >= 0x16) {
            if (relicId < 0x14) {
                g_Status.relics[relicId] ^= 2;
            }
        }
        self->flags |= 0x10000;
        sp22 = 0x100;
        sp24 = 0x40;
        sp20 = 0;
        sp26 = 0x10;
        ClearImage((RECT*)&sp20, 0, 0, 0);
        prim = &g_PrimBuf[self->primIndex];
        var_a3 = 0;
        do {
            if (var_a3 == 0) {
                prim->type = 6;
                prim->y0 = 0xA0;
                prim->u1 = 0xF0;
                prim->clut = 0x1A1;
                prim->priority = 0x1FE;
                prim->tpage = 0x10;
                prim->x0 = 0x10;
                prim->u0 = 0;
                prim->v0 = 0;
                prim->v1 = 0x10;
            } else {
                prim->type = 3;
                prim->x3 = 0x80;
                prim->x2 = 0x80;
                prim->x1 = 0x80;
                prim->x0 = 0x80;
                prim->y3 = 0xA7;
                prim->y2 = 0xA7;
                prim->y1 = 0xA7;
                prim->y0 = 0xA7;
                prim->r3 = 0;
                prim->r2 = 0;
                prim->r1 = 0;
                prim->r0 = 0;
                prim->g3 = 0;
                prim->g2 = 0;
                prim->g1 = 0;
                prim->g0 = 0;
                prim->b3 = 0;
                prim->b2 = 0;
                prim->b1 = 0;
                prim->b0 = 0;
                if (var_a3 == 1) {
                    prim->b3 = 0x80;
                    prim->b2 = 0x80;
                    prim->b1 = 0x80;
                    prim->b0 = 0x80;
                } else {
                    prim->g3 = 0x80;
                    prim->g2 = 0x80;
                    prim->g1 = 0x80;
                    prim->g0 = 0x80;
                }
                prim->priority = 0x1FD;
                prim->drawMode = 0x11;
            }
            prim = prim->next;
            var_a3++;
        } while (var_a3 < 3);
        self->step++;
    } else if (step == 6) {
        pix = g_Pix;
        for (i = 0; i < 0xC00; i++) {
            pix[i] = 0;
        }
        sp28 = 0;
        var_s0 = 0;
        do {
            if (*D_us_8018195C[var_s0] != 0) {
                BlitChar(D_us_8018195C[var_s0], &sp28, g_Pix, 0xC0);
            } else {
                if (var_s0 == 0) {
                    var_s0 = 1;
                    continue;
                } else {
                    break;
                }
            }
            var_s0++;
        } while (1);
        LoadTPage(g_Pix, 0, 0, 0, 0x100, 0x180, 0x10);
        self->ext.relicOrb.sparkleCycle = 0;
        self->ext.relicOrb.sparkleAnim = sp28;
        self->step++;
    } else if (step == 7) {
        prim = &g_PrimBuf[self->primIndex];
        var_a3 = 0;
        do {
            if (var_a3 == 0) {
                prim->y1 -= 4;
                prim->y3 += 2;
                prim->x2 -= 3;
                prim->x3 += 3;
            } else {
                prim->y1 -= 2;
                prim->y3 += 4;
                prim->x0 -= 3;
                prim->x1 += 3;
            }
            prim->y0 = prim->y1;
            prim->y2 = prim->y3;
            prim = prim->next;
            var_a3++;
        } while (var_a3 < 2);
        self->ext.relicOrb.sparkleCycle++;
        if (self->ext.relicOrb.sparkleCycle == 8) {
            self->ext.relicOrb.sparkleCycle = 0;
            self->step++;
        }
    } else if (step == 8) {
        prim = &g_PrimBuf[self->primIndex];
        var_a3 = 0;
        temp_v0 = self->ext.relicOrb.sparkleCycle;
        do {
            if (var_a3 == 0) {
                prim->x2 = (temp_v0 * 0x78) / 7 + 0x68;
                prim->x1 = 0x80 - (temp_v0 + 1) * 0xC;
                prim->x0 = (temp_v0 + 1) * 0xC + 0x80;
                prim->x3 = 0x98 - (temp_v0 * 0x78) / 7;
                prim->y1 = D_us_80181970[temp_v0] + 0xA7;
                prim->y0 = prim->y1;
                prim->b3 -= 0x10;
                prim->b2 = prim->b3;
                prim->y3 = D_us_80181960[temp_v0] + 0xA7;
                prim->y2 = prim->y3;
            } else {
                prim->x0 = (temp_v0 * 0x78) / 7 + 0x68;
                prim->x1 = 0x98 - (temp_v0 * 0x78) / 7;
                prim->x3 = 0x80 - (temp_v0 + 1) * 0xC;
                prim->x2 = (temp_v0 + 1) * 0xC + 0x80;
                prim->y1 = D_us_80181980[temp_v0] + 0xA7;
                prim->y0 = prim->y1;
                prim->g1 -= 0x10;
                prim->g0 = prim->g1;
                prim->y3 = D_us_80181990[temp_v0] + 0xA7;
                prim->y2 = prim->y3;
            }
            prim = prim->next;
            var_a3++;
        } while (var_a3 < 3);
        self->ext.relicOrb.sparkleCycle++;
        if (self->ext.relicOrb.sparkleCycle == 8) {
            self->ext.relicOrb.sparkleCycle = 0;
            self->step++;
        }
    } else if (step == 9) {
        prim = &g_PrimBuf[self->primIndex];
        prim->drawMode = 0;
        prim->x0 = 0x80 - self->ext.relicOrb.sparkleAnim;
        self->ext.relicOrb.sparkleCycle++;
        if (self->ext.relicOrb.sparkleCycle >= 0x61) {
            DestroyEntity(self);
        }
    }
}

// params: Local index of this drop
// Verbatim copy of EntityHeartDrop in src/st/e_collect.h.
// Kept in sync by hand: this file cannot include that header.
void EntityHeartDrop(Entity* self) {
    u16 index;
    u8 value;
    PfnEntityUpdate update;

    if (!self->step) {
        index = self->ext.heartDrop.unkB4 =
            self->params + HEART_DROP_CASTLE_FLAG;
        value = g_CastleFlags[(index >> 3) + CASTLE_COLLECTIBLES_100] >>
                (index & 7);
        if (value & 1) {
            DestroyEntity(self);
            return;
        }

        index -= HEART_DROP_CASTLE_FLAG;
        index = D_us_80180F8C[index];
        if (index < 128) {
            self->unkB8 = (Entity*)EntityPrizeDrop;
        } else {
            self->unkB8 = (Entity*)EntityEquipItemDrop;
            index -= 128;
        }
        self->params = index + 0x8000;
    } else {
        index = self->ext.heartDrop.unkB4;
        if (self->step < 5) {
            if (self->hitFlags) {
                g_CastleFlags[(index >> 3) + CASTLE_COLLECTIBLES_100] |=
                    1 << (index & 7);
                self->step = 5;
            }
        }
    }
    update = (PfnEntityUpdate)self->unkB8;
    update(self);
}

// params: message box duration, in frames
// ext.messageBox.label: box size and text to render
void EntityMessageBox(Entity* self) {
    const u16 VramX = 0;
    const u16 VramY = 0x180;

    Primitive* prim;
    s32 i;
    char* str;
    s32 primIndex;
    u16 xOffset;
    u8* chPix;
    u8* dstPix;
    u8 ch;
    RECT rect;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitObtainable);
        self->flags |= FLAG_UNK_10000;
        self->flags ^= FLAG_POS_CAMERA_LOCKED;
        if (!self->params) {
            self->params = 96; // default to 96 frames, or 1.5 seconds
        }

        primIndex = g_api.AllocPrimitives(PRIM_GT4, 3);
        if (primIndex == -1) {
            self->step = 0;
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
        prim = &g_PrimBuf[primIndex];
        while (prim != NULL) {
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
        }

        str = self->ext.messageBox.label;
        self->ext.messageBox.width = *str++;
        self->ext.messageBox.height = *str++;
        self->ext.messageBox.label += 2;
        break;
    case 1:
        rect.x = 0;
        rect.y = 0x180;
        rect.w = 0x40;
        rect.h = self->ext.messageBox.height;
        ClearImage(&rect, 0, 0, 0);

        prim = &g_PrimBuf[self->primIndex];
        for (i = 0; prim != NULL; i++) {
            if (i == 0) {
                prim->type = PRIM_SPRT;
                prim->tpage = 0x10;
                prim->x0 = self->posX.i.hi - self->ext.messageBox.width / 2;
                prim->y0 = self->posY.i.hi - self->ext.messageBox.height / 2;
                prim->u0 = 0;
                prim->v0 = 0x80;
                prim->u1 = self->ext.messageBox.width;
                prim->v1 = self->ext.messageBox.height;
                prim->clut = PAL_UNK_1A1;
                prim->priority = 0x1FD;
                prim->drawMode = DRAW_HIDE;
            } else {
                prim->type = PRIM_G4;
                prim->x0 = prim->x2 =
                    self->posX.i.hi - self->ext.messageBox.width / 2 - 4;
                prim->x1 = prim->x3 =
                    self->posX.i.hi + self->ext.messageBox.width / 2 + 4;
                PRED(prim) = 0;
                PGRN(prim) = 0;
                PBLU(prim) = 0;
                if (i == 1) {
                    prim->y0 = prim->y1 = prim->y2 = prim->y3 =
                        self->posY.i.hi - self->ext.messageBox.height / 2 - 4;
                    PBLU(prim) = 0x80;
                } else {
                    prim->y0 = prim->y1 = prim->y2 = prim->y3 =
                        self->posY.i.hi + self->ext.messageBox.height / 2 + 4;
                    PGRN(prim) = 0x80;
                }
                prim->priority = 0x1FC;
                prim->drawMode = DRAW_TPAGE | DRAW_TRANSP;
            }
            prim = prim->next;
        }
        self->step++;
        break;
    case 2:
        dstPix = g_Pix[0];
        chPix = dstPix;
        str = self->ext.messageBox.label;
        xOffset = 0;
        for (i = 0;
             i < self->ext.messageBox.width / 2 * self->ext.messageBox.height;
             i++) {
            *chPix++ = 0;
        }

        chPix = dstPix;
        while (true) {
            if (*str == 0) {
                break;
            }
            if (*str == 1) {
                str++;
                xOffset = 0;
                chPix = &dstPix[self->ext.messageBox.width * 8];
            } else {
                str = BlitChar(
                    str, &xOffset, chPix, self->ext.messageBox.width >> 1);
            }
        }
        LoadTPage((u_long*)dstPix, 0, 0, VramX, VramY,
                  self->ext.messageBox.width, self->ext.messageBox.height);
        self->ext.messageBox.duration = 0;
        self->step++;
        break;
    case 3:
        self->ext.messageBox.duration++;
        prim = &g_PrimBuf[self->primIndex];
        prim = prim->next;
        for (i = 0; prim != NULL; i++) {
            if (i == 0) {
                prim->y2 = prim->y3 =
                    prim->y0 + (self->ext.messageBox.height + 8) *
                                   self->ext.messageBox.duration / 8;
                prim->b0 = prim->b1 -= 0x10;
            } else {
                prim->y0 = prim->y1 =
                    prim->y2 - (self->ext.messageBox.height + 8) *
                                   self->ext.messageBox.duration / 8;
                prim->g2 = prim->g3 -= 0x10;
            }
            prim = prim->next;
        }
        if (self->ext.messageBox.duration == 8) {
            self->ext.messageBox.duration = 0;
            self->step++;
        }
        break;
    case 4:
        prim = &g_PrimBuf[self->primIndex];
        prim->drawMode = DRAW_DEFAULT;
        self->ext.messageBox.duration++;
        if (self->ext.messageBox.duration > self->params) {
            DestroyEntity(self);
        }
        break;
    }
}
