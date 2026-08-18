/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:BO6_RicEntitySubwpnReboundStone
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_3E79C.c
   verdict: BUILD FAILED:
5:src/boss/bo6/us_3E79C.c:847: conflicting types for `g_api_CreateEntFactoryFromEntity'
46:include/game.h:1803: previous declaration of `g_api_CreateEntFactoryFromEntity'
47:src/boss/bo6/us_3E79C.c:848: conflicting types for `rcos'
48:include/psxsdk/libgte.h:77: previous declaration of `rcos'
49:src/boss/bo6/us_3E79C.c:849: conflicting types for `rsin'
50:include/psxsdk/libgte.h:78: 

   This is NOT a permuter seed and must never be treated as
   one: it has never built. automation/candidates/ is for
   code that builds and merely misses on bytes.

   Why it is kept: the escalation path used to record only
   the compiler's message, so a record like `g_EInitCommon
   undeclared` described code nobody could look at any more.
   Twelve such records were assumed to be one extern away
   from building, and turned out to need a full re-attempt
   because the candidate had been discarded.

   Do NOT apply this to the tree. Read it, fix what the
   verdict names, and re-attempt. */
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
extern Primitive g_PrimBuf[];
extern u16 RIC_facingLeft;
extern int rand(void);
extern void (*g_api_CheckCollision)(s32 x, s32 y, Collider* res, s32 unk);
extern void (*g_api_PlaySfx)(s32 sfxId);
extern void DestroyEntity(Entity* entity);
extern u16 RIC_zPriority;
extern void (*g_api_CreateEntFactoryFromEntity)(Entity*, s32, s32);
extern s16 rcos(s32 angle);
extern s16 rsin(s32 angle);

/* BO6_RicEntitySubwpnReboundStone - Boss version of the rebound stone subweapon.
   Controls the rebound stone's lifecycle: spawning primitives, moving with
   collision, bouncing off walls, and handling the fadeout/destroy phase. */
void BO6_RicEntitySubwpnReboundStone(Entity* self) {
    Collider sp10;
    u16 sp38;
    Primitive* prim;
    s16 primCount;
    s32 i;
    s32 moveX;
    s32 moveY;
    s32 colResult;
    s32 colMask;
    s32 bounceVal;
    s32 fadeStep;
    s16 angle;
    s32 posX;
    s32 posY;
    s16 lifeTimer;
    s32 collideFlag;
    s32 bounceCheck;

    /* Cache frequently used entity fields */
    posX = self->posX.val;
    posY = self->posY.val;
    angle = self->ext.reboundStone.stoneAngle;
    lifeTimer = self->ext.reboundStone.lifeTimer;
    sp38 = self->posX.i.hi;
    sp10.unk0 = self->posY.i.hi;

    /* Initialize unk82 to 0 every frame */
    self->ext.reboundStone.unk82 = 0;

    if (self->step == 1) {
        goto step1;
    } else if (self->step < 2) {
        if (self->step != 0) {
            i = 0;
            goto updatePrims;
        }
        /* step 0: Allocate primitives */
        primCount = g_api_AllocPrimitives(PRIM_LINE_G2, 0x10);
        self->primIndex = primCount;
        if (primCount == -1) {
            goto destroyEntity;
        }
        i = 0;
        /* Adjust spawn position upward by 0x10 */
        self->posY.i.hi = self->posY.i.hi - 0x10;
        prim = &g_PrimBuf[self->primIndex];
        if (prim != NULL) {
            do {
                /* Initialize primitive: white, opaque */
                prim->b1 = 0xFF;
                prim->g1 = 0xFF;
                prim->r1 = 0xFF;
                prim->b0 = 0xFF;
                prim->g0 = 0xFF;
                prim->r0 = 0xFF;
                prim->drawMode = 0x33;
                prim->priority = RIC_zPriority + 2;
                if (i != 0) {
                    /* Later primitives use additive blending */
                    prim->drawMode = 0x3B;
                }
                prim->y1 = self->posY.i.hi;
                prim->y0 = self->posY.i.hi;
                prim->unk30 = 0x14;
                prim->x1 = sp38;
                prim->x0 = sp38;
                prim = prim->next;
                i++;
            } while (prim != NULL);
        }
        /* Set entity flags and priority */
        self->flags = 0x18800000;
        self->zPriority = RIC_zPriority + 2;
        /* Set initial horizontal velocity based on facing */
        if (RIC_facingLeft != 0) {
            self->ext.reboundStone.stoneAngle = 0x980;
        } else {
            self->ext.reboundStone.stoneAngle = 0xE80;
        }
        /* Randomize angle slightly */
        angle = self->ext.reboundStone.stoneAngle;
        self->ext.reboundStone.stoneAngle = (angle - 0x40) + (rand() & 0x7F);
        self->ext.reboundStone.lifeTimer = 0x40;
        self->hitboxWidth = 4;
        self->hitboxHeight = 4;
        /* Check for immediate wall collision */
        g_api_CheckCollision(
            self->posX.i.hi, self->posY.i.hi, &sp10, 0);
        i = 0;
        if ((sp10.unk0 & 1) != 0) {
            self->ext.reboundStone.unk84 = 4;
        }
        self->step++;
        g_api_PlaySfx(0x60C);
        fadeStep = 2;
        goto updatePrims;
    } else if (self->step != 2) {
        i = 0;
        goto updatePrims;
    } else {
        /* step 2: Decrement life timer */
        self->ext.reboundStone.lifeTimer--;
        if (self->ext.reboundStone.lifeTimer == 0) {
            DestroyEntity(self);
            return;
        }
        /* Disable hitbox after 0x20 ticks */
        if (self->ext.reboundStone.lifeTimer == 0x20) {
            self->hitboxState = 0;
        }
        /* Clear primitive timers */
        prim = &g_PrimBuf[self->primIndex];
        i = 0;
        if (prim != NULL) {
            do {
                prim->unk30 = 0;
                prim = prim->next;
                i = 0;
            } while (prim != NULL);
        }
        goto updatePrims;
    }

step1:
    /* step 1: Move with collision checks */
    moveX = rcos(angle) << 4;
    moveY = -(rsin(angle) << 4);
    /* Check vertical movement if no pending bounce */
    if (self->ext.reboundStone.unk84 == 0) {
        for (i = 0; i < 6; i++) {
            /* Check vertical collision */
            g_api_CheckCollision(
                posX >> 16, (posY + moveY) >> 16, &sp10, 0);
            if ((sp10.unk0 & 1) != 0) {
                colResult = sp10.unk0 & 0xF800;
                if (moveY > 0) {
                    if (colResult == 0 || (colResult & 0x800)) {
                        BO6_ReboundStoneBounce1(0x800);
                    }
                    bounceVal = 0x8000;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x200);
                    }
                    bounceVal = 0x9000;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x12E);
                    }
                    bounceVal = 0xA000;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0xA0);
                    }
                    bounceVal = 0xC000;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x600);
                    }
                    bounceVal = 0xD000;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x6D2);
                    }
                    bounceVal = 0xE000;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x760);
                    }
                }
                if (moveY < 0) {
                    if (colResult == 0 || (colResult & 0x8000)) {
                        BO6_ReboundStoneBounce1(0x800);
                    }
                    bounceVal = 0x800;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0xE00);
                    }
                    bounceVal = 0x1800;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0xED2);
                    }
                    bounceVal = 0x2800;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0xF60);
                    }
                    bounceVal = 0x4800;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0xA00);
                    }
                    bounceVal = 0x5800;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x92E);
                    }
                    bounceVal = 0x6800;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x8A0);
                    }
                }
            }
            /* Check horizontal collision */
            g_api_CheckCollision(
                (posX + moveX) >> 16, posY >> 16, &sp10, 0);
            if ((sp10.unk0 & 1) != 0) {
                colResult = sp10.unk0 & 0xF800;
                if (moveX > 0) {
                    if (colResult == 0 || (colResult & 0x4800) == 0x4800 ||
                        (colResult & 0xC000) == 0xC000) {
                        BO6_ReboundStoneBounce1(0x400);
                    }
                    bounceVal = 0x800;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0xE00);
                    }
                    bounceVal = 0x1800;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0xED2);
                    }
                    bounceVal = 0x2800;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0xF60);
                    }
                    bounceVal = 0x8000;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x200);
                    }
                    bounceVal = 0x9000;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x12E);
                    }
                    bounceVal = 0xA000;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0xA0);
                    }
                }
                if (moveX < 0) {
                    if (colResult == 0 || (colResult & 0x4800) == 0x800 ||
                        (colResult & 0xC000) == 0x8000) {
                        BO6_ReboundStoneBounce1(0x400);
                    }
                    bounceVal = 0x4800;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0xA00);
                    }
                    bounceVal = 0x5800;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x92E);
                    }
                    bounceVal = 0x6800;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x8A0);
                    }
                    bounceVal = 0xC000;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x600);
                    }
                    bounceVal = 0xD000;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x6D2);
                    }
                    bounceVal = 0xE000;
                    if (colResult == bounceVal) {
                        BO6_ReboundStoneBounce2(0x760);
                    }
                }
            }
            /* Apply movement */
            posX += moveX;
            /* Check for pending bounce flag */
            if (self->ext.reboundStone.unk82 == 0) {
                i++;
                posY += moveY;
                if (i >= 6) {
                    break;
                }
                continue;
            }
            /* Bounce occurred, exit loop */
            break;
        }
    } else {
        /* Pending bounce countdown */
        self->ext.reboundStone.unk84--;
    }

    /* Handle bounce completion */
    if (self->ext.reboundStone.unk82 != 0) {
        g_api_CreateEntFactoryFromEntity(self, 0x2002A, 0);
        g_api_PlaySfx(0x6A4);
    }

    i = 0;
    /* Check if stone is out of bounds or expired */
    if (((u16)(self->posX.i.hi + 0x40) & 0xFFFF) >= 0x181 ||
        ((u16)(self->posY.i.hi + 0x40) & 0xFFFF) >= 0x181 ||
        self->ext.reboundStone.unk80 == 0xF) {
        self->step = 2;
    } else {
        /* Update position with fixed-point scale */
        self->posX.val += (rcos(angle) << 4) * 0x400 >> 8;
        self->posY.val += -(rsin(angle) << 4) * 0x400 >> 8;
    }

updatePrims:
    fadeStep = 2;
    prim = &g_PrimBuf[self->primIndex];
    if (self->step == 2) {
        fadeStep = 4;
    }
    if (prim != NULL) {
        do {
            /* Update primitive positions and colors */
            if (self->ext.reboundStone.unk82 != 0) {
                if (i == self->ext.reboundStone.unk80) {
                    prim->y0 = self->posY.i.hi;
                    prim->x0 = sp38;
                    prim->drawMode &= ~8;
                }
            } else {
                if (i == self->ext.reboundStone.unk80) {
                    prim->x1 = self->posX.i.hi;
                    prim->y1 = self->posY.i.hi;
                }
            }
            if (!(prim->drawMode & 8)) {
                if (prim->unk30 != 0) {
                    /* Decrement timer */
                    prim->unk30--;
                } else {
                    /* Fade out primitive */
                    if (fadeStep < prim->b1) {
                        prim->b1 -= fadeStep;
                    }
                    prim->g1 = prim->b1;
                    prim->r1 = prim->b1;
                    prim->b0 = prim->b1;
                    prim->g0 = prim->b1;
                    prim->r0 = prim->b1;
                }
            }
            prim = prim->next;
            i++;
        } while (prim != NULL);
    }
    return;

destroyEntity:
    DestroyEntity(self);
}