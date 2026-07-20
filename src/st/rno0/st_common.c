// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

INCLUDE_ASM("st/rno0/nonmatchings/st_common", DestroyEntity);

#ifndef HARD_LINK
void DestroyEntitiesFromIndex(s16 index) {
    Entity* entity = &g_Entities[index];

    while (entity < &g_Entities[TOTAL_ENTITY_COUNT - 1]) {
        DestroyEntity(entity);
        entity++;
    }
}
#endif

void PreventEntityFromRespawning(Entity* entity) {
    if (entity->entityRoomIndex) {
        u16 index = entity->entityRoomIndex - 1 >> 5;
        g_unkGraphicsStruct.D_80097428[index] |=
            1 << ((entity->entityRoomIndex - 1) & 0x1F);
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/st_common", AnimateEntity);

// Notably, this is completely unused.
// The use of the 0xBB offset in the entity, which does not match the current
// entity struct, suggests that this was for an older form of Entity.
// When the Entity was changed, this function was already unused, so was never
// updated. This is just a theory though.

#define SELF_BB (*((u8*)&self->unkB8 + 3))

u8 UnkAnimFunc(u8 frames[], Entity* self, u8 arg2) {
    u16 animFrameStart = self->pose * 2;
    u8* var_s1 = &frames[animFrameStart];
    s16 var_a1 = 0;

    if (self->poseTimer == 0) {
        if (*var_s1 != 0) {
            if (*var_s1 == 0xFF) {
                return 0;
            }
            self->poseTimer = *var_s1++ + SELF_BB;
            self->animCurFrame = *var_s1++;
            self->pose++;
            var_a1 = 128;
        } else {
            var_s1 = frames;
            self->pose = 0;
            self->poseTimer = 0;
            SELF_BB = (arg2 * Random()) >> 8;
            self->poseTimer = *var_s1++ + SELF_BB;
            self->animCurFrame = *var_s1;
            self->pose++;
            return 0;
        }
    }
    self->poseTimer--;
    self->animCurFrame = var_s1[-1];
    var_a1 |= 1;
    return var_a1;
}

// Absolute distance from g_CurrentEntity to the player in the X Axis
s16 GetDistanceToPlayerX(void) {
    Entity* player = &PLAYER;
    s16 xDistance = g_CurrentEntity->posX.i.hi - player->posX.i.hi;

    if (xDistance < 0) {
        xDistance = -xDistance;
    }
    return xDistance;
}

// Absolute distance from g_CurrentEntity to the player in the Y Axis
s32 GetDistanceToPlayerY(void) {
    Entity* player = &PLAYER;
    s32 yDistance = g_CurrentEntity->posY.i.hi - player->posY.i.hi;

    if (yDistance < 0) {
        yDistance = -yDistance;
    }
    return yDistance;
}

// Bit-packed side comparison: bit 0 = entity is right of player, bit 1 = entity is below player
u8 GetSideToPlayer() {
    u8 side = 0;
    Entity* player = &PLAYER;

    if (g_CurrentEntity->posX.i.hi > player->posX.i.hi) {
        side |= 1;  // entity is to the right
    }

    if (g_CurrentEntity->posY.i.hi > player->posY.i.hi) {
        side |= 2;  // entity is below
    }
    return side;
}

// Apply velocity to entity position
void MoveEntity(void) {
    g_CurrentEntity->posX.val += g_CurrentEntity->velocityX;
    g_CurrentEntity->posY.val += g_CurrentEntity->velocityY;
}

// Apply gravity/downward acceleration, with terminal velocity cap
void FallEntity(void) {
    s32 velocityY;

    velocityY = g_CurrentEntity->velocityY;
    if (velocityY <= 0x5FFFF) {  // 0x5FFFF = terminal velocity cap
        g_CurrentEntity->velocityY = velocityY + 0x4000;  // gravity acceleration
    }
}

s32 UnkCollisionFunc3(s16* sensors) {
    Collider col;
    Collider colBack;
    s16 x;
    s16 y;
    s16 i;

    MoveEntity();
    FallEntity();
    if (g_CurrentEntity->velocityY >= 0) {
        x = g_CurrentEntity->posX.i.hi;
        y = g_CurrentEntity->posY.i.hi;
        for (i = 0; i < 4; i++) {
            x += *sensors++;
            y += *sensors++;
            g_api.CheckCollision(x, y, &col, 0);
            if (col.effects & EFFECT_UNK_8000) {
                if (i == 1) {
                    if (col.effects & EFFECT_SOLID) {
                        g_api.CheckCollision(x, y - 8, &colBack, 0);
                        if (!(colBack.effects & EFFECT_SOLID)) {
                            g_CurrentEntity->posY.i.hi += 4 + col.unk18;
                            g_CurrentEntity->velocityX = 0;
                            g_CurrentEntity->velocityY = 0;
                            g_CurrentEntity->flags &= ~FLAG_UNK_10000000;
                            return 1;
                        }
                    }
                    continue;
                }
            }
            if (col.effects & EFFECT_NOTHROUGH && i != 1) {
                if (col.effects & EFFECT_QUICKSAND) {
                    g_CurrentEntity->flags &= ~FLAG_UNK_10000000;
                    return 4;
                }
                g_api.CheckCollision(x, y - 8, &colBack, 0);
                if (!(colBack.effects & EFFECT_SOLID)) {
                    g_CurrentEntity->posY.i.hi += col.unk18;
                    g_CurrentEntity->velocityX = 0;
                    g_CurrentEntity->velocityY = 0;
                    g_CurrentEntity->flags &= ~FLAG_UNK_10000000;
                    return 1;
                }
            }
        }
    }
    g_CurrentEntity->flags |= FLAG_UNK_10000000;
    return 0;
}

s32 UnkCollisionFunc2(s16* posX) {
    Collider collider;
    s16 x, y;

    g_CurrentEntity->posX.val += g_CurrentEntity->velocityX;
    g_CurrentEntity->posY.i.hi += 3;
    x = g_CurrentEntity->posX.i.hi + *posX++;
    y = g_CurrentEntity->posY.i.hi + *posX++;
    g_api.CheckCollision(x, y, &collider, 0);

    if (collider.effects & EFFECT_SOLID) {
        g_CurrentEntity->posY.i.hi += collider.unk18;
    } else {
        return 0;
    }

    if (g_CurrentEntity->velocityX != 0) {
        if (g_CurrentEntity->velocityX < 0) {
            x -= *posX++;
        } else {
            x += *posX++;
        }
        y += *posX;
        y -= 7;
        g_api.CheckCollision(x, y, &collider, 0);
        if (collider.effects & EFFECT_SOLID) {
            if (collider.effects & EFFECT_UNK_8000 ||
                !(collider.effects & EFFECT_UNK_0002)) {
                return 0x61;
            }
            g_CurrentEntity->posX.val -= g_CurrentEntity->velocityX;
            g_CurrentEntity->velocityX = 0;
            return 0xFF;
        }
        y += 15;
        g_api.CheckCollision(x, y, &collider, 0);
        if (collider.effects & EFFECT_SOLID) {
            if (collider.effects & EFFECT_UNK_8000) {
                return 0x61;
            }
            return 1;
        }
        g_CurrentEntity->posX.val -= g_CurrentEntity->velocityX;
        g_CurrentEntity->velocityX = 0;

        return 0x80;
    }
    return 1;
}

Entity* AllocEntity(Entity* start, Entity* end) {
    Entity* current = start;

    while (current < end) {
        if (!current->entityId) {
            DestroyEntity(current);
            return current;
        }
        current++;
    }
    return NULL;
}

extern s16 g_SineTable[];

// Look up sine from table and scale by a magnitude
s32 GetSineScaled(u8 angle, s16 scale) {
    s32 sine = g_SineTable[angle];
    return sine * scale;
}

// Look up sine from table (wrapped to 256 entries)
s16 GetSine(s32 angle) {
    return g_SineTable[angle & 0xFF];  // mask to 8 bits for 256-entry table
}

void SetEntityVelocityFromAngle(u8 arg0, s16 arg1) {
    g_CurrentEntity->velocityX = GetSineScaled(arg0, arg1);
    g_CurrentEntity->velocityY = GetSineScaled(arg0 - 0x40, arg1);
}

// Compute arctangent of (y/x), shift-scaled and wrapped to 8-bit angle
s32 Ratan2Shifted(s16 x, s16 y) {
    return ((ratan2(y, x) >> 4) + 0x40) & 0xFF;  // >> 4 is shift-scale, & 0xFF wraps to 256
}

u8 GetAngleBetweenEntitiesShifted(Entity* a, Entity* b) {
    s16 dx = b->posX.i.hi - a->posX.i.hi;
    s16 dy = b->posY.i.hi - a->posY.i.hi;
    return Ratan2Shifted(dx, dy);
}

// original name: search_point
u8 GetAnglePointToEntityShifted(s16 x, s16 y) {
    s16 dx = x - g_CurrentEntity->posX.i.hi;
    s16 dy = y - g_CurrentEntity->posY.i.hi;
    return Ratan2Shifted(dx, dy);
}

u8 AdjustValueWithinThreshold(u8 threshold, u8 currentValue, u8 targetValue) {
    u8 absoluteDifference;
    s8 relativeDifference = targetValue - currentValue;

    if (relativeDifference < 0) {
        absoluteDifference = -relativeDifference;
    } else {
        absoluteDifference = relativeDifference;
    }

    if (absoluteDifference > threshold) {
        if (relativeDifference < 0) {
            absoluteDifference = currentValue - threshold;
        } else {
            absoluteDifference = currentValue + threshold;
        }

        return absoluteDifference;
    }

    return targetValue;
}

void UnkEntityFunc0(u16 slope, s16 speed) {
    g_CurrentEntity->velocityX = rcos(slope) * speed / 16;
    g_CurrentEntity->velocityY = rsin(slope) * speed / 16;
}

// Compute arctangent of (y/x), result masked to 16 bits
s32 Ratan2(s16 x, s16 y) {
    return ratan2((s32) y, (s32) x) & 0xFFFF;
}

// Compute angle from source entity to target entity
u16 GetAngleBetweenEntities(Entity* src, Entity* dst) {
    s32 dx = dst->posX.i.hi - src->posX.i.hi;
    s32 dy = dst->posY.i.hi - src->posY.i.hi;
    return ratan2(dy, dx);
}

u16 GetAnglePointToEntity(s32 x, s32 y) {
    s16 dx = x - (u16)g_CurrentEntity->posX.i.hi;
    s16 dy = y - (u16)g_CurrentEntity->posY.i.hi;
    return ratan2(dy, dx);
}

// Restricts an angle to be within a certain delta of an initial angle
// Often used for entities which need to go through a smooth rotation.
// The current angle will be the base, and the target will be found by
// some function (perhaps pointing toward the player). The limited delta
// forces the angle to only rotate by a certain amount per frame.
// Enables smooth rotation from one angle to another.
u16 LimitAngleChange(u16 delta, u16 base, u16 target) {
    u16 diff = (s16)(target - base);
    u16 ret;

    // Angles are 0 to 0xFFF, or -0x800 to +0x7FF
    // Equivalent to 0-360 versus -180 to 180.
    // This converts the absolute diff into signed.
    if (diff & 0x800) {
#if STAGE == STAGE_ST0
        ret = diff & 0x7FF;
#else
        ret = (0x800 - diff) & 0x7FF;
#endif
    } else {
        ret = diff;
    }
    // If we exceed the delta, then return a value which differs in the right
    // direction by precisely that delta.
    if (ret > delta) {
        if (diff & 0x800) {
            ret = base - delta;
        } else {
            ret = base + delta;
        }

        return ret;
    }
    // If we're not over the delta, then we can directly adopt the target angle.
    return target;
}

// Set entity state machine step and clear sub-step, pose, and timer
void SetStep(s32 step) {
    g_CurrentEntity->step = step & 0xFF;  // wrap to 8 bits
    g_CurrentEntity->step_s = 0;
    g_CurrentEntity->pose = 0;
    g_CurrentEntity->poseTimer = 0;
}

// Set entity sub-step and clear pose and timer
void SetSubStep(u8 step_s) {
    g_CurrentEntity->step_s = step_s;
    g_CurrentEntity->pose = 0;
    g_CurrentEntity->poseTimer = 0;
}

void EntityExplosionSpawn(u16 params, u16 arg1) {
#if STAGE != STAGE_ST0
    if (arg1) {
#if defined VERSION_BETA
        g_api.PlaySfx(arg1);
#else
        PlaySfxPositional(arg1);
#endif
    }
#endif
    if (params == 0xFF) {
        DestroyEntity(g_CurrentEntity);
        return;
    }

    g_CurrentEntity->entityId = E_EXPLOSION;
    g_CurrentEntity->pfnUpdate = (PfnEntityUpdate)EntityExplosion;
    g_CurrentEntity->params = params;
    g_CurrentEntity->animCurFrame = 0;
    g_CurrentEntity->drawFlags = ENTITY_DEFAULT;
    g_CurrentEntity->step = 0;
    g_CurrentEntity->step_s = 0;
}

void InitializeEntity(u16 arg0[]) {
    u16 enemyId;
    EnemyDef* enemyDef;

    g_CurrentEntity->animSet = *arg0++;
    g_CurrentEntity->animCurFrame = *arg0++;
    g_CurrentEntity->unk5A = *arg0++;
    g_CurrentEntity->palette = *arg0++;

    // n.b.! the post increment of arg0 is optimized out
    // on the PS1 version, but not on the PSP version.
    enemyId = g_CurrentEntity->enemyId = *arg0++;
    enemyDef = &g_api.enemyDefs[enemyId];
    g_CurrentEntity->hitPoints = enemyDef->hitPoints;
    g_CurrentEntity->attack = enemyDef->attack;
    g_CurrentEntity->attackElement = enemyDef->attackElement;
    g_CurrentEntity->hitboxState = enemyDef->hitboxState;
    g_CurrentEntity->hitboxWidth = enemyDef->hitboxWidth;
    g_CurrentEntity->hitboxHeight = enemyDef->hitboxHeight;
    g_CurrentEntity->flags = enemyDef->flags;
    g_CurrentEntity->hitboxOffX = 0;
    g_CurrentEntity->hitboxOffY = 0;
    g_CurrentEntity->step++;
    g_CurrentEntity->step_s = 0;
    if (!g_CurrentEntity->zPriority) {
        g_CurrentEntity->zPriority = g_unkGraphicsStruct.g_zEntityCenter - 0xC;
    }
}

// Dummy entity function: just advance step from 0 to 1 on first call
void EntityDummy(Entity *entity) {
    if (entity->step == 0) {
        entity->step += 1;
    }
}

s32 UnkCollisionFunc(s16* hitSensors, s16 sensorCount) {
    Collider collider;
    s32 velocityX;
    s16 i;
    s16 x;
    s16 y;

    velocityX = g_CurrentEntity->velocityX;
    if (velocityX != 0) {
        x = g_CurrentEntity->posX.i.hi;
        y = g_CurrentEntity->posY.i.hi;
        for (i = 0; i < sensorCount; i++) {
            if (velocityX < 0) {
                x += *hitSensors++;
            } else {
                x -= *hitSensors++;
            }

            y += *hitSensors++;
            g_api.CheckCollision(x, y, &collider, 0);
            if (collider.effects & EFFECT_UNK_0002 &&
                ((!(collider.effects & EFFECT_UNK_8000)) || i)) {
                return 2;
            }
        }
        return 0;
    }

    // implicit return
}

void CheckFieldCollision(s16* hitSensors, s16 sensorCount) {
    Collider collider;
    s32 velocityX;
    s16 i;
    s16 x;
    s16 y;

    velocityX = g_CurrentEntity->velocityX;
    if (velocityX == 0) {
        return;
    }

    x = g_CurrentEntity->posX.i.hi;
    y = g_CurrentEntity->posY.i.hi;
    for (i = 0; i < sensorCount; i++) {
        if (velocityX < 0) {
            x += *hitSensors++;
        } else {
            x -= *hitSensors++;
        }

        y += *hitSensors++;
        g_api.CheckCollision(x, y, &collider, 0);
        if (collider.effects & EFFECT_UNK_0002 &&
            (!(collider.effects & EFFECT_UNK_8000) || i)) {
            if (velocityX < 0) {
                g_CurrentEntity->posX.i.hi += collider.unk1C;
            } else {
                g_CurrentEntity->posX.i.hi += collider.unk14;
            }
            break;
        }
    }
}

// This function checks if the player collides with the specified entity
// and from which direction.
// w and h holds the collider size of the entity
// while flags stores which sides are solid
u8 GetPlayerCollisionWith(Entity* self, u16 w, u16 h, u16 flags) {
    Entity* player = &PLAYER;
    s16 x, y;
    u16 checks;

#if STAGE != STAGE_ST0
    s32 plStatus = g_Player.status;
    Collider col;

    x = self->posX.i.hi;
    y = self->posY.i.hi;
    if (x > 0x120 || x < -0x20 || y < -0x180 || y > 0x180) {
        return 0;
    }

    x = player->posX.i.hi - x;
    y = player->posY.i.hi - y;
#else
    if (self->posX.i.hi & 0x100) {
        return 0;
    }
    if (self->posY.i.hi & 0x100) {
        return 0;
    }

    x = player->posX.i.hi - self->posX.i.hi;
    y = player->posY.i.hi - self->posY.i.hi;
#endif

    if (self->facingLeft) {
        x += self->hitboxOffX;
    } else {
        x -= self->hitboxOffX;
    }
    y -= self->hitboxOffY;

#if STAGE != STAGE_ST0
    g_api.GetPlayerSensor(&col); // get player collision size
    w += col.unk14;
    h += col.unk18;
#endif

    if (x > 0) {
        checks = 1;
    } else {
        checks = 0;
    }
    if (y > 0) {
        checks |= 2;
    }

#if STAGE == STAGE_ST0
    w += 8;
    h += 24;
#endif

    x += w;
    y += h;
    w += w;
    h += h;

    if ((u16)x <= w && (u16)y <= h) {

        if (x && x != w) {
            // check collision from top
            if (flags & 4 && checks ^ 2 && player->velocityY >= 0 && y < 8) {
                player->posY.i.hi -= y;
#if STAGE == STAGE_ST0
                g_Player.vram_flag |= VRAM_FLAG_UNK40 | TOUCHING_GROUND;
#else
                g_unkGraphicsStruct.shoveY.i.hi -= y;
                g_Player.vram_flag |= VRAM_FLAG_UNK40 | TOUCHING_GROUND;
                if (plStatus &
                    (PLAYER_STATUS_BAT_FORM | PLAYER_STATUS_MIST_FORM)) {
                    return 0;
                }
#endif

                return 4;
            }

            // check collision from bottom
            if (flags & 2 && checks & 2 &&
                (player->velocityY <= 0 || flags & 0x10)) {
                y = (s16)h - y;
                if (y < 0x10) {
                    player->posY.i.hi += y;
#if STAGE == STAGE_ST0
                    g_Player.vram_flag |= VRAM_FLAG_UNK40 | TOUCHING_CEILING;
#else
                    g_unkGraphicsStruct.shoveY.i.hi += y;
                    g_Player.vram_flag |= VRAM_FLAG_UNK40 | TOUCHING_CEILING;
                    if (plStatus &
                        (PLAYER_STATUS_BAT_FORM | PLAYER_STATUS_MIST_FORM)) {
                        return 0;
                    }
#endif
                    return 2;
                }
            }
        }

        // check collision from the sides
        if (y && y != h && flags & 1) {
            if (checks & 1) {
                x = (s16)w - x;
                if (flags & 8 && x > 2) {
                    x = 2;
                }
                player->posX.i.hi += x;
#if STAGE != STAGE_ST0
                g_unkGraphicsStruct.shoveX.i.hi += x;
                g_Player.vram_flag |= VRAM_FLAG_UNK40 | TOUCHING_L_WALL;
#endif
                return 1;
            } else {
                if (flags & 8 && x > 2) {
                    x = 2;
                }
                player->posX.i.hi -= x;
#if STAGE != STAGE_ST0

                g_unkGraphicsStruct.shoveX.i.hi -= x;
                g_Player.vram_flag |= VRAM_FLAG_UNK40 | TOUCHING_R_WALL;
#endif
                return 1;
            }
        }
    }
    return 0;
}

void ReplaceBreakableWithItemDrop(Entity* self) {
    u16 params;

    PreventEntityFromRespawning(self);

#if STAGE != STAGE_ST0
    if (!(g_Status.relics[RELIC_CUBE_OF_ZOE] & 2)) {
        DestroyEntity(self);
        return;
    }
#endif

    params = self->params &= 0xFFF;

    if (params < 0x80) {
        self->entityId = E_PRIZE_DROP;
        self->pfnUpdate = (PfnEntityUpdate)EntityPrizeDrop;
        self->poseTimer = 0;
        self->pose = 0;
    } else {
        self->entityId = E_EQUIP_ITEM_DROP;
        self->pfnUpdate = (PfnEntityUpdate)EntityEquipItemDrop;
        params -= 0x80;
    }

    self->params = params;
    self->unk6D[0] = 0x10;
    self->step = 0;
}
