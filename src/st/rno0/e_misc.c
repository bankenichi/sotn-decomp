// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

// arg0 is a pointer to X and Y offsets from the current entity.
// iterates through those locations, running CheckCollision on
// each location, returning a set of bit flags indicating which
// offset X,Y locations resulted in a collision (with EFFECT_SOLID)
u8 CheckColliderOffsets(s16* arg0, u8 facing) {
    u8 ret = 0;
    Collider collider;
    s16 posX, posY;

    while (*arg0 != 0xFF) {
        ret <<= 1;

        if (facing) {
            posX = g_CurrentEntity->posX.i.hi + *arg0++;
        } else {
            posX = g_CurrentEntity->posX.i.hi - *arg0++;
        }
        posY = g_CurrentEntity->posY.i.hi + *arg0++;

        g_api.CheckCollision(posX, posY, &collider, 0);
        if (collider.effects & EFFECT_SOLID) {
            ret |= 1;
        }
    }

    return ret;
}

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", EntityUnkId13);

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", EntityExplosionVariantsSpawner);

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", EntityGreyPuffSpawner);

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", EntityExplosionVariants);

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", EntityGreyPuff);

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", EntityOlroxDrool);

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", UnkCollisionFunc5);

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", UnkCollisionFunc4);

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", EntityIntenseExplosion);

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", InitializeUnkEntity);

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", MakeEntityFromId);

void MakeExplosions(void) {
    u8 temp_s4;
    s16 temp_s3;
    Entity* entity;
    s32 i;

    temp_s4 = Random() & 3;
    temp_s3 = ((Random() & 0xF) << 8) - 0x800;

    for (i = 0; i < 6; i++) {
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
#if defined(STAGE_IS_NO2) || defined(STAGE_IS_CAT)
            CreateEntityFromEntity(E_BIG_RED_FIREBALL, g_CurrentEntity, entity);
#else
            CreateEntityFromEntity(E_EXPLOSION, g_CurrentEntity, entity);
#endif
            // EntityExplosion does not seem to use these values.
            entity->ext.destructAnim.unk85 = 6 - i;
            entity->ext.destructAnim.unk80 = temp_s3;
            entity->ext.destructAnim.unk84 = temp_s4;
        }
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", EntityBigRedFireball);

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", UnkRecursivePrimFunc1);

INCLUDE_ASM("st/rno0/nonmatchings/e_misc", UnkRecursivePrimFunc2);

void ClutLerp(RECT* rect, u16 palIdxA, u16 palIdxB, s32 steps, u16 offset) {
    u16 buf[COLORS_PER_PAL];
    RECT bufRect;
    s32 t;
    u32 r, g, b, a;
    s32 i, j;
    u16 *palA, *palB;

    bufRect.x = rect->x;
    bufRect.w = COLORS_PER_PAL;
    bufRect.h = 1;

    palA = &g_Clut[0][palIdxA * COLORS_PER_PAL];
    palB = &g_Clut[0][palIdxB * COLORS_PER_PAL];

    for (i = 0; i < steps; i++) {
        t = i * FLT(1) / steps;
        for (j = 0; j < COLORS_PER_PAL; j++) {
            r = GET_RED(palA[j]) * (FLT(1) - t) + GET_RED(palB[j]) * t;
            g = GET_GREEN(palA[j]) * (FLT(1) - t) + GET_GREEN(palB[j]) * t;
            b = GET_BLUE(palA[j]) * (FLT(1) - t) + GET_BLUE(palB[j]) * t;

            a = palA[j] & ALPHA_MASK;
            a |= palB[j] & ALPHA_MASK;

            buf[j] = a | (r >> 12) | ((g >> 12) << 5) | ((b >> 12) << 10);
        }

        bufRect.y = rect->y + i;
        LoadImage(&bufRect, (u_long*)buf);
        g_ClutIds[offset + i] = GetClut(bufRect.x, bufRect.y);
    }
}

void PlaySfxPositional(s16 sfxId) {
    s32 posX, posY;
    s16 sfxPan;
    s16 sfxVol;

    posX = g_CurrentEntity->posX.i.hi - 128;
    sfxPan = (abs(posX) - 32) >> 5;
    if (sfxPan > 8) {
        sfxPan = 8;
    } else if (sfxPan < 0) {
        sfxPan = 0;
    }
    if (posX < 0) {
        sfxPan = -sfxPan;
    }
    sfxVol = abs(posX) - 96;
    posY = abs(g_CurrentEntity->posY.i.hi - 128) - 112;
    if (posY > 0) {
        sfxVol += posY;
    }
    if (sfxVol < 0) {
        sfxVol = 0;
    }
    sfxVol = 127 - (sfxVol >> 1);
    if (sfxVol > 0) {
        g_api.PlaySfxVolPan(sfxId, sfxVol, sfxPan);
    }
}
