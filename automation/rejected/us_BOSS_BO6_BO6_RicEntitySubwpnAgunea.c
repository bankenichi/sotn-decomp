/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:BO6_RicEntitySubwpnAgunea
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_3E79C.c
   verdict: BUILD FAILED:
mber named `parent'
80:src/boss/bo6/us_3E79C.c:931: union has no member named `parent'
81:src/boss/bo6/us_3E79C.c:933: union has no member named `unk7C'
82:src/boss/bo6/us_3E79C.c:935: union has no member named `unk7C'
83:src/boss/bo6/us_3E79C.c:953: union has no member named `parent'
84:src/boss/bo6/us_3E79C.c:955: union has no member named `unk7C'
85:src/boss/bo6/us_3E79C.c:976: un

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
void BO6_RicEntitySubwpnAgunea(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s16 temp_s1;
    s16 temp_s2;
    s16 temp_v0;
    u16 temp_v1;
    Entity* enemy;

    if (g_Ric.status & 0x10007) {
        DestroyEntity(self);
        return;
    }

    switch (self->step) {
    case 0:
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 1);
        self->primIndex = primIndex;
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags = 0x18800000;
        self->hitboxWidth = 4;
        self->hitboxHeight = 4;
        self->hitboxOffX = 4;
        self->hitboxOffY = 0;
        self->facingLeft = RIC_facingLeft;
        temp_v0 = (RIC_posY_i_hi + RIC_hitboxOffY) - 8;
        self->ext.unk82 = temp_v0;
        self->posY.i.hi = temp_v0;
        prim = &g_PrimBuf[self->primIndex];
        self->ext.unk80 = RIC_posX_i_hi;
        self->posX.i.hi = RIC_posX_i_hi;
        prim->type = 2;
        prim->drawMode = 0x331;
        prim->r1 = 0x60;
        prim->g1 = 0;
        prim->b1 = 0x80;
        prim->priority = RIC_zPriority + 2;
        BO6_RicSetSpeedX(0x60000);
        g_api_PlaySfx(0x60C);
        self->step++;
        break;

    case 1:
        self->posX.val += self->velocityX;
        if (((u32)((self->posX.i.hi + 0x40) & 0xFFFF) >= 0x181) ||
            ((u32)((self->posY.i.hi + 0x20) & 0xFFFF) >= 0x141)) {
            self->step = 2;
        }
        if (self->hitFlags != 0) {
            self->step = 3;
            // 0xB8 is ext offset 0x3C, no named field in ET_EntFactory
            // This stores the enemy entity pointer when a hit occurs
            self->ext.parent = *(Entity**)((s8*)self + 0xB8);
        }
        break;

    case 4:
        enemy = self->ext.parent;
        self->posX.i.hi = enemy->posX.i.hi; // unk2 is part of posX f32
        self->ext.unk7C++;
        self->posY.i.hi = enemy->posY.i.hi; // unk6 is part of posY f32
        if ((s16)self->ext.unk7C >= 0x10) {
            // Fall through to case 2
        } else {
            break;
        }
        // fallthrough
    case 2:
        prim = &g_PrimBuf[self->primIndex];
        if (prim->r1 < 5) {
            DestroyEntity(self);
            return;
        }
        break;

    case 3:
        if ((g_Ric.padPressed & 0x1080) != 0x1080) {
            self->step = 4;
        }
        enemy = self->ext.parent;
        if (enemy->entityId != 0) {
            if ((s16)self->ext.unk7C != 0) {
                if (enemy->hitPoints < 0x7001) {
                    if (enemy->hitPoints != 0) {
                        if (enemy->hitboxState != 0) {
                            goto follow_enemy;
                        }
                        goto set_step_2;
                    }
                    goto set_step_2;
                }
                goto set_step_2;
            }
        } else {
            goto set_step_2;
        }

    follow_enemy:
        temp_s1 = enemy->posX.i.hi;
        temp_s2 = enemy->posY.i.hi;
        self->posX.i.hi = temp_s1;
        self->posY.i.hi = temp_s2;
        if (((self->ext.unk7C % 12) << 0x10) == 0) {
            self->posX.i.hi = (self->posX.i.hi - 8) + (rand() & 0xF);
            self->posY.i.hi = (self->posY.i.hi - 8) + (rand() & 0xF);
            if (g_Status.hearts >= 5) {
                g_Status.hearts -= 5;
                BO6_RicCreateEntFactoryFromEntity(self, 0x34, 0, &g_Status.hearts);
                g_api_PlaySfx(0x665);
            } else if (self->ext.unk84 == 0) {
                BO6_RicCreateEntFactoryFromEntity(self, 0x34, 0, &g_Status.hearts);
                g_api_PlaySfx(0x665);
                self->ext.unk84++;
            } else {
                self->step = 4;
            }
        }
        self->posX.i.hi = temp_s1;
        self->posY.i.hi = temp_s2;
        self->ext.unk7C++;
        break;

    set_step_2:
        self->step = 2;
        return;
    }

    // Update primitive
    prim = &g_PrimBuf[self->primIndex];
    if (prim->r1 >= 4) {
        prim->r1 += 0xFC;
    }
    if (prim->g1 >= 4) {
        prim->g1 += 0xFC;
    }
    if (prim->b1 >= 4) {
        prim->b1 += 0xFC;
    }
    if (prim->b1 < 5) {
        prim->drawMode |= 8;
    }
    prim->x0 = self->ext.unk80;
    prim->y0 = self->ext.unk82;
    prim->x1 = self->posX.i.hi;
    prim->y1 = self->posY.i.hi;
}