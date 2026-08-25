/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RNO0:EntityRelicOrb
   score  : 10
   receipt: nonmatchings/.adapt-scores/20260824-235417-62298-024639/EntityRelicOrb-2/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rno0/e_collect.c
   asm    : asm/us/st/rno0/nonmatchings/e_collect/EntityRelicOrb.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void MoveEntity();
void FallEntity(void);
void DestroyEntity(Entity*);
void SetStep(u8 step);
u8 AnimateEntity(u8 frames[], Entity* entity);
void InitializeEntity(u16 arg0[]);
void CheckFieldCollision(s16* hitSensors, s16 sensorCount);
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
extern void (*g_api_LoadEquipIcon)(s32 equipIcon, s32 palette, s32 index);
extern s32 (*g_api_func_800FE044)(s32, s32);
int ClearImage(RECT* rect, u8 r, u8 g, u8 b);
s32 sprintf(char* out, char* f, ...);
extern int strlen(const char*);
u_short LoadTPage(u_long* pix, int tp, int abr, int x, int y, int w, int h);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int update();
/* End permuter-seed writer declarations. */



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
extern const char* g_RelicOrbTexts[];
extern RelicDesc* g_api_relicDefs;
extern s32 g_UserLanguage;

#define orbUnk7C isObtainedTextStored
extern char* obtainedStr;
extern const char* g_RelicOrbTexts[1];
extern s16 D_us_80181960[8];
extern s16 D_us_80181970[8];
extern s16 D_us_80181980[8];
extern s16 D_us_80181990[8];
extern s16 D_us_801819A0[8];
extern s16 D_us_801819B0[8];
extern u16 msgBoxTpage[0x600];
extern u16 PrizeDrops[];
void EntityHeartDrop(Entity* self);
void EntityMessageBox(Entity* self);

void EntityRelicOrb(Entity* self) {
#if STAGE == STAGE_ST0
    const int PrimCount = 3;
#else
    const int PrimCount = 7;
#endif
     
     

#if defined(VERSION_BETA) || STAGE == STAGE_ST0
    const int MaxItemSlots = LEN(g_ItemIconSlots);
#else
    const int MaxItemSlots = LEN(g_ItemIconSlots) - 1;
#endif
    u16 relicId;
#if defined(VERSION_PSP) || STAGE == STAGE_ST0
    u16 isObtainedTextStored;
#else
    bool isObtainedTextStored;
#endif
    RECT rect;
    Primitive* prim;
    const char* msg;
    s32 primIndex;
    s16 iconSlot;
    s32 i;
    u8* chPix;
    u16 var_s8;
    u16 msgLen;

     
    u8* var_v0_5;
    u16 var_s2;
#if defined(VERSION_PSP)
    char sp34[0x100];
#endif

 
 
#if STAGE == STAGE_ST0
#define orbUnk7C isObtainedTextStored
#else
#define orbUnk7C var_s2
#endif

#if !defined(VERSION_US) || STAGE == STAGE_ST0
    u16 vramX;
    u16* chPixSrc;
    u16* chPixDst;
    u16 ch;
#endif

    relicId = self->params & 0x7FFF;
    if (self->step && self->step < 5 && self->hitFlags) {
        self->step = 5;
    }

    switch (self->step) {
    case 0:
#if STAGE != STAGE_ST0
         
        if (g_Status.relics[relicId] & RELIC_FLAG_FOUND) {
            DestroyEntity(self);
            return;
        }
#endif
        InitializeEntity(g_EInitObtainable);
        for (iconSlot = 0; iconSlot < MaxItemSlots; iconSlot++) {
            if (!g_ItemIconSlots[iconSlot]) {
                break;
            }
        }

        if (iconSlot >= MaxItemSlots) {
            self->step = 0;
            return;
        }

        primIndex = g_api_AllocPrimitives(PRIM_GT4, PrimCount);
        if (primIndex == -1) {
            self->step = 0;
            return;
        }
        self->flags |= FLAG_HAS_PRIMS;
        self->primIndex = primIndex;
#if STAGE == STAGE_ST0
        g_api_LoadEquipIcon(g_api.equipDefs[relicId].icon,
                            g_api.equipDefs[relicId].iconPalette, iconSlot);
#else
        self->ext.relicOrb.iconSlot = iconSlot;
#if !defined(VERSION_BETA)
        g_ItemIconSlots[iconSlot] = 0x10;
#endif
        g_api_LoadEquipIcon(g_api_relicDefs[relicId].icon,
                            g_api_relicDefs[relicId].iconPalette, iconSlot);
#endif
        prim = &g_PrimBuf[primIndex];
        for (i = 0; prim != NULL; i++) {
            if (i != 0) {
#if STAGE == STAGE_ST0
                prim->type = PRIM_G4;
#endif
                prim->drawMode = DRAW_HIDE;
            } else {
                prim->tpage = 0x1A;
                prim->clut = iconSlot + 0x1D0;
                 
                prim->u0 = prim->u2 = ((iconSlot & 7) << 4) + 1;
                prim->u1 = prim->u3 = prim->u0 + 14;
                 
                prim->v0 = prim->v1 = ((iconSlot & 24) << 1) + 0x81;
                prim->v2 = prim->v3 = prim->v0 + 14;
#if STAGE != STAGE_ST0
                prim->drawMode = DRAW_COLORS | DRAW_UNK02;
#else
                prim->drawMode = DRAW_UNK02;
#endif
            }
#if STAGE == STAGE_ST0
            prim->priority = 0xC0;
#else
            prim->priority = 0x7E;
#endif
            prim = prim->next;
        }
#if STAGE != STAGE_ST0
        self->posY.i.lo = 0x8000;
        self->velocityY = FIX(0.25);
        self->ext.relicOrb.floatTimer = 64;
        self->ext.relicOrb.yFloatSpeed = -FIX(0.0078125);
#endif
        break;
#if STAGE != STAGE_ST0
    case 1:
         
        self->velocityY += self->ext.relicOrb.yFloatSpeed;
        if (!--self->ext.relicOrb.floatTimer) {
            self->ext.relicOrb.floatTimer = 64;
            self->ext.relicOrb.yFloatSpeed = -self->ext.relicOrb.yFloatSpeed;
        }
        MoveEntity();
        iconSlot = self->ext.relicOrb.iconSlot;
        g_ItemIconSlots[iconSlot] = 0x10;
        break;
#endif
    case 5:
#if STAGE != STAGE_ST0
        g_api_func_800FE044(relicId, 0x2000);
#if !defined(VERSION_BETA)
        msg = g_api_relicDefs[relicId].name;
        if (relicId >= RELIC_SWORD_CARD && relicId < RELIC_FAERIE_CARD) {
            g_Status.relics[relicId] ^= RELIC_FLAG_ACTIVE;
        }
#endif
        self->flags |= FLAG_UNK_10000;
#else
        g_api.PlaySfx(SFX_UNK_618);

        g_Status.relics[relicId] = 3;
#endif

         
         
        rect.x = 0;
        rect.y = 256;
        rect.w = 64;
        rect.h = 16;
        ClearImage(&rect, 0, 0, 0);

        prim = &g_PrimBuf[self->primIndex];
#if STAGE == STAGE_ST0
        for (i = 0; prim != NULL; i++) {
#else
        for (i = 0; i < 3; i++) {
#endif
            if (i == 0) {
                prim->type = PRIM_SPRT;
                prim->tpage = 0x10;
                prim->x0 = 0x10;
                prim->y0 = 0xA0;
                prim->u0 = 0;
                prim->v0 = 0;
                prim->u1 = 0xF0;
                prim->v1 = 0x10;
#if STAGE == STAGE_ST0
                prim->clut = 0x1F8;
#else
                prim->clut = PAL_UNK_1A1;
#endif
                prim->priority = 0x1FE;
                prim->drawMode = DRAW_HIDE;
            } else {
#if STAGE != STAGE_ST0
                prim->type = PRIM_G4;
#endif
                prim->x0 = prim->x1 = prim->x2 = prim->x3 = 0x80;
                prim->y0 = prim->y1 = prim->y2 = prim->y3 = 0xA7;
                PRED(prim) = 0;
                PGRN(prim) = 0;
                PBLU(prim) = 0;

                if (i == 1) {
                    PBLU(prim) = 0x80;
                } else {
                    PGRN(prim) = 0x80;
                }
                prim->priority = 0x1FD;
                prim->drawMode = DRAW_TPAGE | DRAW_TRANSP;
            }
            prim = prim->next;
        }

        self->step++;
        break;

    case 6:
         
         
        msgLen = 0;
        var_s2 = 0;
        isObtainedTextStored = false;
#if defined(VERSION_PSP) && STAGE != STAGE_ST0
        msg = g_api_relicDefs[relicId].name;
        switch (g_UserLanguage) {
        case LANG_EN:
        default:
            obtainedStr = "Obtained";
            break;
        case LANG_FR:
            obtainedStr = "Obtenu \xB1 ";
            break;
        case LANG_SP:
            obtainedStr = "Tienes";
            break;
        case LANG_GE:
            obtainedStr = "erhalten";
            break;
        case LANG_IT:
            obtainedStr = "Ottenuto";
            break;
        }

        if (g_UserLanguage != LANG_GE) {
            sprintf(&sp34, "%s %s", obtainedStr, msg);
        } else {
            sprintf(&sp34, "%s %s", msg, obtainedStr);
        }
        msgLen = strlen(sp34);
        BlitChar(&sp34[0], 0, 12, 0x100);
#elif !defined(VERSION_US) || STAGE == STAGE_ST0
        vramX = 0;
        msg = g_api_relicDefs[relicId].name;
        while (true) {
            ch = *msg++;
            if (ch == 0) {
                if (isObtainedTextStored) {
                    break;
                }
                isObtainedTextStored = true;
                msg = g_RelicOrbTexts[0];
            } else {
                ch = (ch << 8) | *msg++;
                chPixSrc = g_api.func_80106A28(ch, 1);
                if (chPixSrc != NULL) {
                    chPixDst = &msgBoxTpage[msgLen * 0x30];
                    for (i = 0; i < 0x30; i++) {
                        *chPixDst++ = *chPixSrc++;
                    }
                    LoadTPage((u_long*)&msgBoxTpage[msgLen * 0x30], 0, 0, vramX,
                              0x100, 0xC, 0x10);
                    vramX += 3;
                    msgLen++;
                }
            }
        }
#else
    msg = g_RelicOrbTexts[0];
    chPix = g_Pix[0];
    var_v0_5 = (u8*)chPix;
    for (i = 0; i < 0xC00; i++) {
        *var_v0_5++ = 0;
    }

    msgLen = 0;
    while (true) {
        if (*msg == 0) {
            if (isObtainedTextStored) {
                break;
            }
            msg = g_api_relicDefs[relicId].name;
            isObtainedTextStored = true;
        } else {
            msg = BlitChar(msg, &msgLen, chPix, 0xC0);
        }
    }

    LoadTPage(chPix, 0, 0, 0, 0x100, 0x180, 0x10);
#endif
        self->ext.relicOrb.unk7E = msgLen;
        self->ext.relicOrb.unk7C = 0;
        self->step++;
        break;
    case 7:
         
        prim = &g_PrimBuf[self->primIndex];
        prim = prim->next;
#if STAGE == STAGE_ST0
        for (i = 0; prim != NULL; i++) {
#else
        for (i = 0; i < 2; i++) {
#endif
            if (i == 0) {
                prim->x2 -= 3;
                prim->x3 += 3;
                prim->y0 = prim->y1 -= 4;
                prim->y2 = prim->y3 += 2;
            } else {
                prim->x0 -= 3;
                prim->x1 += 3;
                prim->y0 = prim->y1 -= 2;
                prim->y2 = prim->y3 += 4;
            }
            prim = prim->next;
        }

        if (++self->ext.relicOrb.unk7C == 8) {
            self->ext.relicOrb.unk7C = 0;
            self->step++;
        }
        break;

    case 8:
        orbUnk7C = self->ext.relicOrb.unk7C;
        prim = &g_PrimBuf[self->primIndex];
        prim = prim->next;
#if STAGE == STAGE_ST0
        for (i = 0; prim != NULL; i++) {
#else
        for (i = 0; i < 3; i++) {
#endif
            if (i == 0) {
                prim->x1 = 0x80 - (orbUnk7C + 1) * 0xC;
                prim->x0 = 0x80 + (orbUnk7C + 1) * 0xC;
                prim->x2 = 0x68 + (orbUnk7C * 0x78) / 7;
                prim->x3 = 0x98 - (orbUnk7C * 0x78) / 7;
                prim->y0 = prim->y1 = D_us_80181970[orbUnk7C] + 0xA7;
                prim->y2 = prim->y3 = D_us_80181960[orbUnk7C] + 0xA7;
                prim->b2 = prim->b3 -= 0x10;
            } else {
                prim->x0 = 0x68 + (orbUnk7C * 0x78) / 7;
                prim->x1 = 0x98 - (orbUnk7C * 0x78) / 7;
                prim->x3 = 0x80 - (orbUnk7C + 1) * 0xC;
                prim->x2 = 0x80 + (orbUnk7C + 1) * 0xC;
                prim->y0 = prim->y1 = D_us_80181980[orbUnk7C] + 0xA7;
                prim->y2 = prim->y3 = D_us_80181990[orbUnk7C] + 0xA7;
                prim->g0 = prim->g1 -= 0x10;
            }
            prim = prim->next;
        }

        if (++self->ext.relicOrb.unk7C == 8) {
            self->step++;
            self->ext.relicOrb.unk7C = 0;
        }
        break;

    case 9:
        prim = &g_PrimBuf[self->primIndex];
#if defined(VERSION_US) && !defined(VERSION_PSP) && STAGE != STAGE_ST0
        prim->x0 = 0x80 - self->ext.relicOrb.unk7E;
#else
        prim->x0 = 0x80 - self->ext.relicOrb.unk7E * 6;
#endif
        prim->drawMode = DRAW_DEFAULT;
        self->ext.relicOrb.unk7C++;
#if STAGE == STAGE_ST0
        if (self->ext.relicOrb.unk7C > 0x100) {
#else
        if (self->ext.relicOrb.unk7C > 0x60) {
#endif
            DestroyEntity(self);
            return;
        }
        break;
    }

    if (self->step < 2) {
#if STAGE == STAGE_ST0
        prim = &g_PrimBuf[self->primIndex];
        prim->x0 = prim->x2 = self->posX.i.hi - 7;
        prim->x1 = prim->x3 = prim->x0 + 14;
        prim->y0 = prim->y1 = self->posY.i.hi - 7;
        prim->y2 = prim->y3 = prim->y0 + 14;
#elif defined(VERSION_BETA)
         
        prim = &g_PrimBuf[self->primIndex];
        prim->x0 = prim->x2 = self->posX.i.hi - 7;
        prim->x1 = prim->x3 = prim->x0 + 14;
        prim->y0 = prim->y1 = self->posY.i.hi - 7;
        prim->y2 = prim->y3 = prim->y0 + 14;

        if (g_Timer & 2) {
            PCOL(prim) = 0xFF;
        } else {
            PCOL(prim) = 0x80;
        }
#else
    BlinkItem(self, g_Timer);
    prim = &g_PrimBuf[self->primIndex];
#endif
#if STAGE != STAGE_ST0
         
        for (i = 0; i < 3; i++) {  
            prim = prim->next;
        }

        if (!self->ext.relicOrb.sparkleCycle) {
            for (i = 0; i < 4; i++) {
                if (prim->drawMode == DRAW_HIDE) {
                    prim->tpage = 0x1A;
                    prim->clut = PAL_UNK_1B1;
                    prim->u0 = prim->u2 = 0;
                    prim->u1 = prim->u3 = 0x10;
                    prim->v0 = prim->v1 = 0x50;
                    prim->v2 = prim->v3 = 0x60;

                    var_s8 = self->ext.relicOrb.sparkleAnim & 7;
                    iconSlot = self->posX.i.hi;
                    iconSlot += D_us_801819A0[var_s8];
                    prim->x0 = prim->x2 = iconSlot - 6;
                    prim->x1 = prim->x3 = iconSlot + 6;

                    iconSlot = self->posY.i.hi;
                    iconSlot += D_us_801819B0[var_s8];
                    prim->y0 = prim->y1 = iconSlot - 6;
                    prim->y2 = prim->y3 = iconSlot + 6;

                    PRED(prim) = 0x80;
                    PGRN(prim) = 0x80;
                    PBLU(prim) = 0x80;
                    prim->p1 = 0;
                    prim->priority = 0x7F;
                    prim->drawMode = DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS |
                                     DRAW_UNK02 | DRAW_TRANSP;
                    break;
                }
                prim = prim->next;
            }

            self->ext.relicOrb.sparkleCycle = 4;
            self->ext.relicOrb.sparkleAnim++;
        } else {
            self->ext.relicOrb.sparkleCycle--;
        }
    }

    prim = &g_PrimBuf[self->primIndex];
    for (i = 0; i < 3; i++) {
        prim = prim->next;
    }

    while (prim != NULL) {
        if (prim->drawMode != DRAW_HIDE) {
            if (prim->p1 & 3) {
                prim->y0 = prim->y1--;
                prim->y2 = prim->y3--;
            } else {
                prim->y2 = prim->y3 -= 2;
                prim->x0 = prim->x2++;
                prim->x1 = prim->x3--;
            }
            PRED(prim) -= 6;
            PGRN(prim) -= 6;
            PBLU(prim) -= 6;
            prim->p1++;
            if (prim->p1 > 0x10) {
                prim->drawMode = DRAW_HIDE;
            }
        }
        prim = prim->next;
#endif
    }
}

#if STAGE != STAGE_ST0
 
extern u16 PrizeDrops[];

 
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
        index = PrizeDrops[index];
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

#if !defined(VERSION_BETA)
 
 
void EntityMessageBox(Entity* self) {
    const u16 VramX = 0;
    const u16 VramY = 0x180;
    const int FontW = 12;
    const int FontH = 16;
    const int FontLen = FontW * FontH / 2 / sizeof(u16);  

    Primitive* prim;
    s32 i;
    char* str;
    s32 primIndex;
    u16 xOffset;
    u8* chPix;
    u8* dstPix;
    u8 ch;
    RECT rect;

    u16 x;
    u16 y;
    u16 nCh;

    u16 chjp;
    u16* srcJpPix;
    u16* dstJpPix;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitObtainable);
        self->flags |= FLAG_UNK_10000;
        self->flags ^= FLAG_POS_CAMERA_LOCKED;
        if (!self->params) {
            self->params = 96;  
        }

        primIndex = g_api_AllocPrimitives(PRIM_GT4, 3);
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
#if defined(VERSION_US)
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
#elif defined(VERSION_PSP)
        nCh = 0;
        x = VramX;
        y = VramY;
        str = self->ext.messageBox.label;
        BlitChar(str, 0, 0, 0x180);
#elif defined(VERSION_HD)
        nCh = 0;
        x = VramX;
        y = VramY;
        str = self->ext.messageBox.label;
        while (true) {
            chjp = *str++;
            if (!chjp) {
                break;
            }
            if (chjp == 1) {
                y += FontH;
                x = 0;
            } else {
                chjp = (*str++ | (chjp << 8));
                srcJpPix = g_api.func_80106A28(chjp, 1);
                if (srcJpPix) {
                    dstJpPix = &msgBoxTpage[nCh * FontLen];
                    for (i = 0; i < FontLen; i++) {
                        *dstJpPix++ = *srcJpPix++;
                    }
                    LoadTPage(
                        &msgBoxTpage[nCh * FontLen], 0, 0, x, y, FontW, FontH);
                    x += 3;
                    nCh++;
                }
            }
        }
#endif
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
#endif

#endif


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
