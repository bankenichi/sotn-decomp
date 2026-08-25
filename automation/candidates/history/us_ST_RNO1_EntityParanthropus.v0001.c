/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNO1:EntityParanthropus
   source : upstream/master:src/st/e_paranthropus.h
   target : src/st/rno1/unk_34074.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
Entity* AllocEntity(Entity* start, Entity* end);
void DestroyEntity(Entity*);
void CreateEntityFromEntity(u16 entityId, Entity* ent1, Entity* ent2);
void InitializeEntity(u16 arg0[]);
s32 GetSideToPlayer(void);
s16 GetDistanceToPlayerX();
void PlaySfxPositional(s32 arg0);
void MoveEntity();
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int UnkCollisionFunc3();
extern int AnimateEntity();
extern int EntityExplosionVariantsSpawner();
/* End permuter-seed writer declarations. */

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

void ParanthropusSetStep(u16 step) {
    g_CurrentEntity->pose = 0;
    g_CurrentEntity->poseTimer = 0;
    g_CurrentEntity->ext.paranthropus.unk7C = 0;
    g_CurrentEntity->ext.paranthropus.unk7E = false;
    g_CurrentEntity->step = step;
}

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity g_Entities[TOTAL_ENTITY_COUNT]; // 0x060997F8;
extern EInit g_EInitParanthropus;
extern GameApi g_api;
extern Primitive g_PrimBuf[];

void EntityParanthropus(Entity* self) {
    Collider collider;
    Primitive* deathVortex;
    Entity* entity;
    s32 i;
    s16 xOffset;
    u8 var_s4;
    s16 primX;
    s16 primY;
    s32 primIndex;
    s16 posX;
    s16 posY;

    enum Attacks { BONE_THROW = 0, BONE_SWING = 1, BELLY_DIVE = 2 };

    self->ext.paranthropus.lastFacingDirection = self->facingLeft;
    if (self->flags & FLAG_DEAD && self->step < DEATH) {
        ParanthropusSetStep(DEATH);
        self->hitboxState = 0;
        (self + 1)->hitboxState = 0;

         
        entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
        if (entity != NULL) {
            DestroyEntity(entity);
            CreateEntityFromEntity(E_PARANTHROPUS, self, entity);
            entity->facingLeft = self->facingLeft;
            entity->posY.i.hi -= 0x18;
            if (self->facingLeft) {
                entity->posX.i.hi += 0x10;
            } else {
                entity->posX.i.hi -= 0x10;
            }
            entity->params = 11;
        }
    }

    switch (self->step) {
    case INIT:
        InitializeEntity(g_EInitParanthropus);
        self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        if (self->params == 11) {
            self->zPriority++;
            self->animCurFrame = 0x2A;
            self->hitboxState = 0;
            self->flags |= FLAG_DESTROY_IF_OUT_OF_CAMERA |
                           FLAG_DESTROY_IF_BARELY_OUT_OF_CAMERA |
                           FLAG_UNK_00200000 | FLAG_UNK_2000;
            self->drawFlags = ENTITY_ROTATE;
            self->step = DEATH_SKULL_REMAINS;
        } else {
            self->drawFlags |= ENTITY_SCALEY | ENTITY_SCALEX;
            self->scaleX = self->scaleY = 0x100;

            entity = self + 1;
            CreateEntityFromEntity(E_PARANTHROPUS_BONE_HITBOX, self, entity);

            entity = self + 2;
            CreateEntityFromEntity(E_PARANTHROPUS_SKULL, self, entity);
        }
        break;
    case FALL_TO_GROUND:
        UnkCollisionFunc3(sensors_ground);
        self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        if (GetDistanceToPlayerX() < 0x60) {
            self->step_s = 0;
            self->ext.paranthropus.nextAttack = BONE_THROW;
            ParanthropusSetStep(WALK);
        }
        break;
    case DIVE_RECOVERY:
        if (!AnimateEntity(anim_belly_ground_recovery, self)) {
            self->step_s = 0;
            self->ext.paranthropus.nextAttack = BONE_THROW;
            ParanthropusSetStep(WALK);
        }
        break;
    case WALK:
        if (!self->step_s) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            self->step_s++;
        }

        if (self->ext.paranthropus.unk7E) {
            if (self->poseTimer == 0) {
                if (self->facingLeft) {
                    self->posX.i.hi += walk_posX_offsets[self->animCurFrame];
                } else {
                    self->posX.i.hi -= walk_posX_offsets[self->animCurFrame];
                }

                if (self->pose == 3 || self->pose == 6) {
                    PlaySfxPositional(SFX_STOMP_HARD_B);
                }

                self->posY.i.hi += 4;
                posX = self->posX.i.hi;
                posY = self->posY.i.hi + 0x1B;
                g_api.CheckCollision(posX, posY, &collider, 0);
                if (collider.effects & EFFECT_SOLID) {
                    self->posY.i.hi += collider.unk18;
                }
            }
        } else {
            self->ext.paranthropus.unk7E = true;
        }

        if (!AnimateEntity(anim_walk, self)) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            self->ext.paranthropus.unk7C++;
        }

         
        if (self->ext.paranthropus.unk7C > 1 && GetDistanceToPlayerX() < 0x60) {
            self->step_s = 0;

             
            switch (self->ext.paranthropus.nextAttack) {
            case BONE_THROW:
                ParanthropusSetStep(THROW_BONE);
                break;
            case BONE_SWING:
                ParanthropusSetStep(SWING_BONE);
                break;
            case BELLY_DIVE:
                if (self->facingLeft) {
                    self->velocityX = FIX(2.0);
                } else {
                    self->velocityX = FIX(-2.0);
                }
                self->velocityY = FIX(-6.25);
                ParanthropusSetStep(DIVE);
                break;
            }
        }
        break;
    case THROW_BONE:
        if (self->ext.paranthropus.unk7E) {
            if (self->poseTimer == 0) {
                if (self->facingLeft) {
                    self->posX.i.hi +=
                        thrown_bone_posX_offsets[self->animCurFrame - 0x10];
                } else {
                    self->posX.i.hi -=
                        thrown_bone_posX_offsets[self->animCurFrame - 0x10];
                }
            }
        } else {
            self->ext.paranthropus.unk7E = true;
        }

        if (!AnimateEntity(anim_throw_bone, self)) {
            self->ext.paranthropus.nextAttack = BONE_SWING;
            ParanthropusSetStep(WALK);
        }

        if (self->animCurFrame == 0x17) {
            if (!self->ext.paranthropus.unk7C) {
                entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
                if (entity != NULL) {
                    PlaySfxPositional(SFX_BONE_THROW);
                    CreateEntityFromEntity(
                        E_PARANTHROPUS_THROWN_BONE, self, entity);
                    entity->facingLeft = self->facingLeft;
                    entity->posY.i.hi -= 0x20;
                    if (self->facingLeft) {
                        entity->posX.i.hi += 0x18;
                    } else {
                        entity->posX.i.hi -= 0x18;
                    }
                }
                self->ext.paranthropus.unk7C = 1;
            }
        } else {
            self->ext.paranthropus.unk7C = 0;
        }
        break;
    case SWING_BONE:
        if (self->ext.paranthropus.unk7E) {
            if (self->poseTimer == 0) {
                if (self->facingLeft) {
                    self->posX.i.hi +=
                        swing_bone_posX_offsets[self->animCurFrame - 6];
                } else {
                    self->posX.i.hi -=
                        swing_bone_posX_offsets[self->animCurFrame - 6];
                }
            }
        } else {
            self->ext.paranthropus.unk7E = true;
        }

        if (self->pose == 7 && !self->poseTimer) {
            PlaySfxPositional(SFX_EXPLODE_B);
        }

        if (!AnimateEntity(anim_swing_bone, self)) {
            self->ext.paranthropus.nextAttack = BELLY_DIVE;
            ParanthropusSetStep(WALK);
        }
        break;
    case DIVE:
         
        if (UnkCollisionFunc3(sensors_ground) & 1) {
            if (self->facingLeft) {
                EntityExplosionVariantsSpawner(self, 5, 3, 0x20, 0x1B, 0, 4);
                EntityExplosionVariantsSpawner(self, 4, 3, 0x18, 0x1B, 0, 4);
                EntityExplosionVariantsSpawner(self, 3, 3, 0x10, 0x1B, 0, 4);
                EntityExplosionVariantsSpawner(self, 2, 3, 8, 0x1B, 0, 4);
                EntityExplosionVariantsSpawner(self, 2, 3, 0, 0x1B, 0, 4);
                EntityExplosionVariantsSpawner(self, 2, 3, 0, 0x1B, 0, -4);
                EntityExplosionVariantsSpawner(self, 5, 3, -8, 0x1B, 0, -4);
            } else {
                EntityExplosionVariantsSpawner(self, 5, 3, 8, 0x1B, 0, 4);
                EntityExplosionVariantsSpawner(self, 2, 3, 0, 0x1B, 0, 4);
                EntityExplosionVariantsSpawner(self, 2, 3, 0, 0x1B, 0, -4);
                EntityExplosionVariantsSpawner(self, 2, 3, -8, 0x1B, 0, -4);
                EntityExplosionVariantsSpawner(self, 3, 3, -0x10, 0x1B, 0, -4);
                EntityExplosionVariantsSpawner(self, 4, 3, -0x18, 0x1B, 0, -4);
                EntityExplosionVariantsSpawner(self, 5, 3, -0x20, 0x1B, 0, -4);
            }
            g_api.func_80102CD8(1);
            PlaySfxPositional(SFX_EXPLODE_D);
            ParanthropusSetStep(DIVE_RECOVERY);
        } else {
            AnimateEntity(anim_dive, self);
        }
        break;
    case DEATH:
#if defined(VERSION_PSP) || defined(VERSION_HD)
        if (UnkCollisionFunc3(sensors_ground) & 1) {
            PlaySfxPositional(SFX_SKELETON_DEATH_A);
            ParanthropusSetStep(DEATH_EFFECTS);
        }
#else
        MoveEntity();
        self->velocityY += FIX(0.25);
        posX = self->posX.i.hi;
        posY = self->posY.i.hi;
        g_api.CheckCollision(posX, posY + 0x1B, &collider, 0);
        if (collider.effects & EFFECT_SOLID) {
            self->posY.i.hi += collider.unk18;
            PlaySfxPositional(SFX_SKELETON_DEATH_A);
            ParanthropusSetStep(DEATH_EFFECTS);
        }
#endif
        break;
    case DEATH_EFFECTS:
        if (self->facingLeft) {
            xOffset = 0x1B;
        } else {
            xOffset = -0x1B;
        }

        if (!AnimateEntity(anim_death, self)) {
            primIndex = g_api.AllocPrimitives(PRIM_GT4, 1);
            if (primIndex != -1) {
                 
                self->flags |= FLAG_HAS_PRIMS;
                self->primIndex = primIndex;
                deathVortex = &g_PrimBuf[primIndex];
                self->ext.paranthropus.deathVortexPrim = deathVortex;
                deathVortex->tpage = 0x1A;
                deathVortex->clut = 0x170;
                deathVortex->u0 = 0;
                deathVortex->u1 = 0x1F;
                deathVortex->u2 = 0;
                deathVortex->u3 = 0x1F;
                deathVortex->v0 = 0;
                deathVortex->v1 = 0;
                deathVortex->v2 = 0x1F;
                deathVortex->v3 = 0x1F;
                deathVortex->x0 = self->posX.i.hi + xOffset;
                deathVortex->y0 = self->posY.i.hi + 0x18;
                LOW(deathVortex->x1) = LOW(deathVortex->x0);
                LOW(deathVortex->x2) = LOW(deathVortex->x0);
                LOW(deathVortex->x3) = LOW(deathVortex->x0);
                PRED(deathVortex) = 0;
                PGRN(deathVortex) = 0;
                PBLU(deathVortex) = 0;
                deathVortex->priority = self->zPriority + 2;
                deathVortex->drawMode |= DRAW_UNK02;
                deathVortex->drawMode |= DRAW_COLORS;
                deathVortex->drawMode |= DRAW_UNK_40 | DRAW_TPAGE | DRAW_TRANSP;
                ParanthropusSetStep(DEATH_PARTS_VACUUM);
                self->ext.paranthropus.unk7C = 0;
                self->ext.paranthropus.deathVortexColor = 1;
                self->ext.paranthropus.unk84 = 0;
            } else {
                 
                 
                self->zPriority -= 2;
                if (self->facingLeft) {
                    xOffset = 0x10;
                } else {
                    xOffset = -0x10;
                }

                for (i = 0; i < 6; i++) {
                    entity = AllocEntity(&g_Entities[160], &g_Entities[192]);
                    if (entity != NULL) {
                        CreateEntityFromEntity(E_EXPLOSION, self, entity);
                        entity->params = EXPLOSION_SMALL_MULTIPLE;
                        entity->posX.i.hi +=
                            xOffset + death_flames_positions[i].x;
                        entity->posY.i.hi += death_flames_positions[i].y;
                    }
                }

                DestroyEntity(self);
            }
        }
        break;
    case DEATH_PARTS_VACUUM:
         
        self->ext.paranthropus.unk7C ^= 1;
        if (!self->ext.paranthropus.unk7C) {
            if (self->ext.paranthropus.unk7E) {
                self->ext.paranthropus.deathVortexColor--;
                if (self->scaleX > 8) {
                    self->scaleX -= 8;
                    self->posY.val += FIX(0.8125);
                    if (self->facingLeft) {
                        self->posX.val += FIX(0.8125);
                    } else {
                        self->posX.val -= FIX(0.8125);
                    }
                }
                self->scaleY = self->scaleX;
            } else {
                if (self->ext.paranthropus.deathVortexColor++ > 0x38) {
                    PlaySfxPositional(SFX_NOISE_SWEEP_DOWN_A);
                    self->ext.paranthropus.unk7E = true;
                }
            }
            if (self->ext.paranthropus.unk7E) {
                primX = -1;
                primY = -(self->ext.paranthropus.deathVortexColor % 2);
            } else {
                primX = 1;
                primY = self->ext.paranthropus.deathVortexColor % 2;
            }

             
            if (self->facingLeft) {
                xOffset = 0x1B;
            } else {
                xOffset = -0x1B;
            }

            deathVortex = self->ext.paranthropus.deathVortexPrim;
            deathVortex->x0 -= primX;
            deathVortex->x1 += primX;
            deathVortex->x2 -= primX;
            deathVortex->x3 += primX;
            deathVortex->y0 -= primY;
            deathVortex->y1 -= primY;
            deathVortex->y2 += primY;
            deathVortex->y3 += primY;

            PRED(deathVortex) = self->ext.paranthropus.deathVortexColor;
            PGRN(deathVortex) = self->ext.paranthropus.deathVortexColor;
            PBLU(deathVortex) = self->ext.paranthropus.deathVortexColor;

            if (self->ext.paranthropus.deathVortexColor == 0) {
                DestroyEntity(self);
            }
        }
        break;
    case 10:
        deathVortex = self->ext.paranthropus.deathVortexPrim;
        var_s4 = self->ext.paranthropus.deathVortexColor;
        PRED(deathVortex) = var_s4;
        PGRN(deathVortex) = var_s4;
        PBLU(deathVortex) = var_s4;
        break;
    case DEATH_SKULL_REMAINS:
        if ((!UnkCollisionFunc3(skull_sensors_ground)) & 1) {
            self->rotate += ROT(1.40625);
        }
        break;
    }

    if (self->facingLeft ^ self->ext.paranthropus.lastFacingDirection) {
        if (self->facingLeft) {
            self->posX.i.hi -= 0x10;
        } else {
            self->posX.i.hi += 0x10;
        }
    }

     
    if (self->animCurFrame >= 0x1D && self->animCurFrame < 0x22) {
        var_s4 = self->animCurFrame - 0x1D;
        self->hitboxWidth = dive_hitbox_dimensions[var_s4].x;
        self->hitboxHeight = dive_hitbox_dimensions[var_s4].y;
        self->hitboxOffX = dive_hitbox_offsets[var_s4].x;
        self->hitboxOffY = dive_hitbox_offsets[var_s4].y;
        return;
    }

    self->hitboxWidth = 0x12;
    self->hitboxHeight = 0x18;
    self->hitboxOffX = 0;
    self->hitboxOffY = 0;
}

INCLUDE_ASM("st/rno1/nonmatchings/unk_34074", EntityParanthropusThrownBone);

INCLUDE_ASM("st/rno1/nonmatchings/unk_34074", EntityParanthropusBoneHitbox);

INCLUDE_ASM("st/rno1/nonmatchings/unk_34074", EntityParanthropusSkull);
