/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO4:func_us_801D5E90
   attempt: 4/4
   from   : muse-spark-1.3-contributor-free
   origin : src/st/rno4/unk_52ED0.c
   verdict: BUILD FAILED:
204:src/st/rno4/unk_52ED0.c:680: invalid operands to binary *
205-[203/468] psx cc src/st/rnz1/gen/e_layout.c
206-[204/468] psx cc src/st/rtop/sprite_banks.c

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
// Cave Troll boss update: movement, jumps, aiming and rock throw, plus debug controls.
void func_us_801D5E90(Entity* self) {
        Collider collider;
        Primitive *prim;
        Primitive *nextPrim;
        Entity *newEnt;
        s16 angle;
        s16 posX;
        s16 posY;
        s16 hitY;
        s16 distX;
        s16 side;
        s32 rnd;
        s32 rndMask;
        s32 isClose;
        s32 vel;
        u16 sub;
        u16 oldFacing;
        u8 hitboxData;
        u8 *hitboxPtr;
        u8 padFlag;
    extern s32 D_us_80182344[];
    extern s32 D_us_80182364[];
    extern s32 D_us_8018236C[];
    extern s32 D_us_80182374[];
    extern s32 D_us_80182384[];
    extern s32 D_us_8018238C[];
    extern u8 D_us_801823C0[];
    extern u8 D_us_801823D4[];
    extern u16 g_EInitCaveTroll[];
    void func_us_801D5DC8(Primitive* prim);

    if (self->flags & 0x100) {
        PlaySfxPositional(0x683);
        newEnt = AllocEntity(g_Entities_224, (Entity*)((char*)g_Entities_224 + 0x1780));
        if (newEnt != NULL) {
            CreateEntityFromEntity(2, self, newEnt);
            newEnt->params = 2;
        }
        DestroyEntity(self);
        return;
    }
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCaveTroll);
        self->animCurFrame = 1;
        vel = g_api_AllocPrimitives(1, 0x20);
        if (vel == -1) {
            DestroyEntity(self);
            return;
        }
        prim = &g_PrimBuf[vel];
        self->primIndex = vel;
        self->ext.player.prim = prim;
        self->flags |= 0x800000;
        if (prim != NULL) {
            prim->v0 = 1;
        loop_prim:
            prim->u0 = 1;
            prim->r0 = 0x80;
            prim->g0 = 0x80;
            prim->b0 = 0xC0;
            prim->drawMode = 8;
            prim->priority = self->zPriority + 1;
            prim = prim->next;
            if (prim != NULL) {
                prim->v0 = 1;
                goto loop_prim;
            }
        }
        break;
    case 1:
        if (UnkCollisionFunc3((s16*)D_us_80182344) & 1) {
            SetStep(2);
        }
        break;
    case 2:
        if (GetDistanceToPlayerX() < 0x60) {
            SetStep(3);
        }
        break;
    case 3:
        sub = self->step_s;
        switch (sub) {
        case 0:
            self->velocityY = -0x20000;
            if (self->facingLeft != 0) {
                self->velocityX = 0x18000;
            } else {
                self->velocityX = -0x18000 + 0x8000;
            }
            self->step_s += 1;
        case 1:
            MoveEntity();
            vel = self->velocityY + 0x2000;
            self->velocityY = vel;
            if (vel < 0) {
                self->animCurFrame = 2;
            }
            if (self->velocityY >= -0x7FFF) {
                self->animCurFrame = 3;
            }
            if (self->velocityY > 0x8000) {
                self->animCurFrame = 4;
            }
            g_api_CheckCollision((s32)self->posX.i.hi, self->posY.i.hi + 0x19, &collider, 0);
            if ((s32)collider.effects & 1) {
                PlaySfxPositional(0x649);
                g_api_CheckCollision((s32)self->posX.i.hi, self->posY.i.hi + 0x11, &collider, 0);
                if ((s32)collider.effects & 1) {
                    SetSubStep(3);
                } else {
                    self->posY.i.hi = self->posY.i.hi + collider.unk18;
                    side = (GetSideToPlayer() & 1) ^ 1;
                    distX = GetDistanceToPlayerX();
                    vel = 2;
                    if ((side != self->facingLeft) && (distX >= 0x41)) {
                        vel = 3;
                    }
                    SetSubStep(vel);
                    if ((u32)(distX - 0x21) < 0x5FU) {
                        rnd = Random();
                        isClose = rnd < 3;
                        if (!(rnd & 1)) {
                            SetStep(4);
                            isClose = rnd < 3;
                        }
                        if ((isClose != 0) || (self->hitPoints < 0x10)) {
                            SetStep(5);
                        }
                    }
                }
            }
            break;
        case 2:
            if (AnimateEntity((u8*)D_us_80182364, self) == 0) {
                SetSubStep(0);
            }
            break;
        default:
            if (sub != 3) {
                break;
            }
            if (AnimateEntity((u8*)D_us_8018236C, self) == 0) {
                self->animCurFrame = 2;
                self->facingLeft ^= 1;
                SetSubStep(0);
            }
            break;
        }
        break;
    case 4:
        sub = self->step_s;
        switch (sub) {
        case 0:
            side = (GetSideToPlayer() & 1) ^ 1;
            if (self->facingLeft == side) {
                SetSubStep(2);
            } else {
                goto anim_turn;
            }
            break;
        case 1:
        anim_turn:
            if (AnimateEntity((u8*)D_us_8018236C, self) == 0) {
                self->animCurFrame = 1;
                self->facingLeft ^= 1;
                SetSubStep(self->facingLeft);
            }
            break;
        case 2:
            if (AnimateEntity((u8*)D_us_8018238C, self) == 0) {
                self->velocityY = -0x60000;
                self->velocityX = 0;
                self->animCurFrame = 0x13;
                PlaySfxPositional(0x64A);
                self->step_s += 1;
            }
            break;
        case 3:
            MoveEntity();
            vel = self->velocityY + 0x3000;
            self->velocityY = vel;
            if (vel > 0) {
                self->step_s += 1;
            }
            break;
        case 4:
            angle = (GetAngleBetweenEntities(self, g_Entities) - 0x400) & 0xFFF;
            if (self->facingLeft != 0) {
                angle = 0x1000 - angle;
            }
            if (angle & 0x800) {
                SetSubStep(8);
            } else {
                self->animCurFrame = 0x14;
                self->ext.player.pad[0x11] = 1;
                *(s16*)&self->ext.player.pad[0xC] = angle;
                self->velocityY = 0;
                self->rotate = 0;
                self->drawFlags |= 4;
                self->step_s += 1;
            case 5:
                FntPrint("angle %x\n", *(s16*)&self->ext.player.pad[0xC]);
                if (StepTowards(&self->rotate, (s32)(s16)(*(s16*)&self->ext.player.pad[0xC] - 0x380), 0x28) != 0) {
                    self->step_s += 1;
                }
            }
            break;
        case 6:
            newEnt = AllocEntity(&g_Entities[160], (Entity*)((char*)&g_Entities[160] + 0x1780));
            if (newEnt != NULL) {
                CreateEntityFromEntity(0x41, self, newEnt);
                newEnt->facingLeft = self->facingLeft;
                angle = *(s16*)&self->ext.player.pad[0xC];
                if (self->facingLeft != 0) {
                    newEnt->posX.i.hi = newEnt->posX.i.hi + ((rsin(angle) * 9) >> 0xC);
                } else {
                    newEnt->posX.i.hi = newEnt->posX.i.hi - ((rsin(angle) * 9) >> 0xC);
                }
                vel = (rcos(angle) * 9) >> 0xC;
                *(s16*)&newEnt->ext.player.pad[0xC] = angle;
                *(Entity**)&newEnt->ext.player.pad[0x1C] = self;
                newEnt->posY.i.hi = newEnt->posY.i.hi + vel;
            }
            *(s16*)&self->ext.player.pad[0] = 0x40;
            PlaySfxPositional(0x6AF);
            self->step_s += 1;
            break;
        case 7:
            vel = *(s16*)&self->ext.player.pad[0] - 1;
            *(s16*)&self->ext.player.pad[0] = vel;
            if (vel != 0) {
                break;
            }
            self->animCurFrame = 0x13;
            self->ext.player.pad[0x11] = 0;
            self->step_s += 1;
            break;
        case 8:
            StepTowards(&self->rotate, 0, 0x40);
            if (UnkCollisionFunc3((s16*)D_us_80182344) & 1) {
                PlaySfxPositional(0x648);
                SetSubStep(9);
                self->drawFlags = 0;
                self->pose = 1;
            }
            break;
        case 9:
            AnimateEntity((u8*)D_us_80182364, self);
        check_flag:
            if (self->ext.player.pad[0x10] != 0) {
                break;
            }
            SetStep(3);
            break;
        }
        break;
    case 5:
        sub = self->step_s;
        switch (sub) {
        case 0:
            self->ext.player.pad[0x10] = 0;
            side = (GetSideToPlayer() & 1) ^ 1;
            if (self->facingLeft == side) {
                SetSubStep(2);
            } else {
                if (AnimateEntity((u8*)D_us_8018236C, self) == 0) {
                    self->animCurFrame = 1;
                    self->facingLeft ^= 1;
                    SetSubStep(self->facingLeft);
                }
            }
            break;
        case 1:
            if (AnimateEntity((u8*)D_us_8018236C, self) == 0) {
                self->animCurFrame = 1;
                self->facingLeft ^= 1;
                SetSubStep(self->facingLeft);
            }
            break;
        case 2:
            newEnt = AllocEntity(&g_Entities[160], (Entity*)((char*)&g_Entities[160] + 0x1780));
            if (newEnt == NULL) {
                SetStep(3);
                break;
            }
            PlaySfxPositional(0x6D3);
            CreateEntityFromEntity(0x42, self, newEnt);
            newEnt->facingLeft = self->facingLeft;
            *(Entity**)&newEnt->ext.player.pad[0x1C] = self;
            SetSubStep(3);
            newEnt->zPriority = self->zPriority + 1;
        case 3:
            if (AnimateEntity((u8*)D_us_80182374, self) == 0) {
                self->ext.player.pad[0x10] = 1;
                SetSubStep(4);
            }
            break;
        case 4:
            AnimateEntity((u8*)D_us_80182384, self);
            goto check_flag;
        default:
            SetStep(3);
            break;
        }
        break;
    case 0xFF:
        FntPrint("charal %x\n", self->animCurFrame);
        if (g_pads_1_pressed & 0x80) {
            if (self->params == 0) {
                self->animCurFrame += 1;
                self->params |= 1;
            }
        } else {
            self->params = 0;
        }
        if (g_pads_1_pressed & 0x20) {
            if (self->step_s == 0) {
                self->animCurFrame -= 1;
                self->step_s |= 1;
            }
        } else {
            self->step_s = 0;
        }
        break;
    default:
        break;
    }
    hitboxPtr = &D_us_801823D4[self->animCurFrame] * 4 + D_us_801823C0;
    self->hitboxOffX = (s16)(s8)hitboxPtr[0];
    self->hitboxOffY = (s16)(s8)hitboxPtr[1];
    self->hitboxWidth = hitboxPtr[2];
    self->hitboxHeight = hitboxPtr[3];
    if (self->ext.player.pad[0x11] != 0) {
        prim = FindFirstUnkPrim(self->ext.player.prim);
        if (prim != NULL) {
            posX = self->posX.i.hi;
            posY = self->posY.i.hi;
            rnd = Random();
            rndMask = Random() & 0x1F;
            hitY = posX + ((rndMask * rcos(rnd * 0x10)) >> 0xC);
            prim->x0 = hitY;
            prim->p3 = 0;
            prim->p2 = 1;
            prim->y0 = posY + ((rndMask * rsin(rnd * 0x10)) >> 0xC);
        }
    }
    prim = self->ext.player.prim;
    if (prim != NULL) {
        do {
            if (prim->p3 != 0) {
                func_us_801D5DC8(prim);
            }
            nextPrim = prim->next;
            if (nextPrim == NULL) {
                prim->x0 = 0;
                prim->y0 = 0;
                prim->drawMode = 0x33;
            }
            prim = nextPrim;
        } while (prim != NULL);
    }
    hitboxData = 0;
    padFlag = 0;
}
