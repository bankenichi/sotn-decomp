// SPDX-License-Identifier: AGPL-3.0-or-later
/*
 * Overlay: BO7
 * Breakable entity (candles and braziers) plus its debris particles.
 *
 * Donor shape: src/st/e_breakable_with_lighting.h, whose compiled twin is
 * asm/us/st/rchi/matchings/e_breakable/EntityBreakable{,Debris}.s. BO7 is a
 * plain (non-INVERTED_STAGE) pack, so the Y offsets subtract downward, and
 * BO7's break plays two sounds (SFX_CANDLE_HIT then SFX_WALL_DEBRIS_B) where
 * CHI plays one (SFX_FIRE_SHOT). All tables live in the overlay's data
 * segment, so the C references them by address instead of defining them.
 */
#include "bo7.h"

enum {
    INIT,
    UPDATE,
};

extern EInit g_EInitBreakable;

/* BO7's breakable-family tables live in the overlay data segment
 * (asm/us/boss/bo7/data/56C.data.s); the extern element types mirror the
 * retail load widths: lbu for the u8 tables, lhu for the u16 tables and
 * lw for the pointer table. */
extern s32 D_us_8018058C[]; // animations[]
extern u8 D_us_801805AC[];  // hitbox_heights[]
extern u8 D_us_801805B4[];  // explosion_types[]
extern u16 D_us_801805BC[]; // anim_sets[]
extern u8 D_us_801805CC[];  // blend_modes[]
extern u16 D_us_801805D4[]; // debris offsets, lhu-loaded in retail

#define BREAKABLE_ZPRIORITY 112
#define LIGHT_AURA 1
#define LIGHT_AURA_Y_OFFSET 16
#define LIGHT_AURA_Y_OFFSET_TALL 32
#define BASE_DEBRIS_COUNT 4
#define DEBRIS_Y_OFFSET_TALL 20
#define TALL_EXTRA_DEBRIS 3

// params: (>> 12) represents the breakable type.
//                 Any non-zero value is considered a "tall" breakable,
//                 meaning it breaks into more debris,
//                 some of which spawns higher up
void EntityBreakable(Entity* self) {
    Entity* entity;
    u16* debrisOffsetsY;
    u16 breakableType;
    s32 debrisCount;

    breakableType = self->params >> 12;
    if (!self->step) {
        InitializeEntity(g_EInitBreakable);
        self->zPriority = BREAKABLE_ZPRIORITY;
        // The four per-type tables are overlay data; retail loads them as
        // lbu for the two u8 tables and lhu for the anim set table.
        self->blendMode = D_us_801805CC[breakableType];
        self->hitboxHeight = D_us_801805AC[breakableType];
        self->animSet = D_us_801805BC[breakableType];

        entity = self + 1;
        DestroyEntity(entity);
        CreateEntityFromEntity(E_BACKGROUND_BLOCK, self, entity);
        if (breakableType) {
            entity->posY.i.hi -= LIGHT_AURA_Y_OFFSET_TALL;
        } else {
            entity->posY.i.hi -= LIGHT_AURA_Y_OFFSET;
        }
        entity->params = LIGHT_AURA;
    }

    AnimateEntity(D_us_8018058C[breakableType], self);

    if (self->hitParams) {
        g_api.PlaySfx(SFX_CANDLE_HIT);
        g_api.PlaySfx(SFX_WALL_DEBRIS_B);
        entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
        if (entity != NULL) {
            CreateEntityFromCurrentEntity(E_EXPLOSION, entity);
            entity->params = D_us_801805B4[breakableType];
            entity->params |= 16;
        }
        debrisOffsetsY = D_us_801805D4;
        for (debrisCount = 0; debrisCount < BASE_DEBRIS_COUNT; debrisCount++) {
            entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
            if (entity != NULL) {
                CreateEntityFromEntity(E_BREAKABLE_DEBRIS, self, entity);
                entity->posX.i.hi += *debrisOffsetsY++;
                entity->posY.i.hi += *debrisOffsetsY++;
                if (breakableType) {
                    entity->posY.i.hi -= DEBRIS_Y_OFFSET_TALL;
                }
                entity->params = debrisCount;
            }
        }

        if (breakableType) {
            for (debrisCount = 0; debrisCount < TALL_EXTRA_DEBRIS;
                 debrisCount++) {
                entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (entity != NULL) {
                    CreateEntityFromEntity(E_BREAKABLE_DEBRIS, self, entity);
                    entity->posX.i.hi += *debrisOffsetsY++;
                    entity->posY.i.hi += *debrisOffsetsY++;
                    entity->params = debrisCount + BASE_DEBRIS_COUNT;
                }
            }
        }
        entity = self + 1;
        DestroyEntity(entity);
        ReplaceBreakableWithItemDrop(self);
    }
}

// params: Index of breakable debris to use
//         (>= 4) Considered a "tall" breakable debris
//         (== 6) The "last standing" debris, that doesn't move
void EntityBreakableDebris(Entity* self) {
    Collider collider;
    Entity* entity;
    Primitive* prim;
    u32 primIndex;
    s32 facingLeft;
    u32 posX;
    u32 posY;

    switch (self->step) {
    case INIT:
        InitializeEntity(g_EInitBreakable);
        self->hitboxState = 0;
        self->zPriority = BREAKABLE_ZPRIORITY;
        self->drawFlags = ENTITY_ROTATE;
        self->animCurFrame = self->params + 28;
        facingLeft = GetSideToPlayer() & 1;

        self->ext.breakableDebris.angle = (Random() & 30) + 8;
        if (self->facingLeft) {
            self->ext.breakableDebris.angle = -self->ext.breakableDebris.angle;
        }

        if (self->params > BASE_DEBRIS_COUNT - 1) {
            self->ext.breakableDebris.angle = -self->ext.breakableDebris.angle;
        }

        if (facingLeft) {
            self->velocityX = FIX(1);
        } else {
            self->velocityX = FIX(-1);
        }

        self->velocityX += FIX(0.5) - (Random() << 8);
        self->velocityY = FIX(-3);
        self->velocityY += (self->params >> 1) * FIX(0.375);

        // "Last standing" debris just sits there (tall breakables only)
        if (self->params == 6) {
            self->velocityX = 0;
            self->velocityY = 0;
            self->step = 2;
        }

        self->primIndex = 0;
        if (!self->params) {
            primIndex = g_api.AllocPrimitives(PRIM_GT4, 2);
            if (primIndex != -1) {
                self->flags |= FLAG_HAS_PRIMS;
                self->primIndex = primIndex;
                prim = &g_PrimBuf[primIndex];

                UnkPolyFunc2(prim);

                prim->tpage = 26;
                prim->clut = 0x159; // PAL_BREAKABLE_DEBRIS for BO7
                prim->u0 = prim->u2 = 64;
                prim->u1 = prim->u3 = 96;
                prim->v0 = prim->v1 = 0;
                prim->v2 = prim->v3 = 32;

                prim->next->x1 = self->posX.i.hi + 4;
                prim->next->y0 = self->posY.i.hi - 8;
                LOH(prim->next->r2) = 32;
                LOH(prim->next->b2) = 32;
                prim->next->b3 = 16;

                prim->priority = BREAKABLE_ZPRIORITY + 2;
                prim->drawMode = DRAW_TRANSP | DRAW_UNK02 | DRAW_COLORS |
                                 DRAW_TPAGE | DRAW_TPAGE2;
            }
        }
        break;

    case UPDATE:
        MoveEntity();
        self->rotate += self->ext.breakableDebris.angle;
        self->velocityY += FIX(0.25);
        posX = self->posX.i.hi;
        posY = self->posY.i.hi + 6;
        g_api.CheckCollision(posX, posY, &collider, 0);
        if (collider.effects & EFFECT_SOLID) {
            self->posY.i.hi += collider.unk18;
            self->velocityY = -self->velocityY / 2;
            self->velocityX -= self->velocityX / 3;
            if (self->velocityY > FIX(-0.625)) {
                entity = AllocEntity(&g_Entities[224], &g_Entities[256]);
                if (entity != NULL) {
                    CreateEntityFromEntity(E_INTENSE_EXPLOSION, self, entity);
                    entity->params = 16;
                }
                DestroyEntity(self);
                break;
            }
        }

        if (self->primIndex != 0) {
            prim = &g_PrimBuf[self->primIndex];
            UnkPrimHelper(prim);
            LOH(prim->next->r2) = LOH(prim->next->b2) += 4;
            if (LOH(prim->next->r2) > 64) {
                prim->next->b3 -= 4;
                if (!prim->next->b3) {
                    g_api.FreePrimitives(self->primIndex);
                    self->flags &= ~FLAG_HAS_PRIMS;
                    self->primIndex = 0;
                }
            }
        }
        break;
    }
}
