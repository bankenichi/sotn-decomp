/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/RBO4:func_us_80197938
   attempt: 4/4
   from   : muse-spark-1.3-contributor-free
   origin : src/boss/rbo4/unk_17804.c
   verdict: BUILD FAILED:
StoneSkull' undeclared (first use this function)
53-[38/427] psx cc src/dra/save_mgr.c
54-[39/427] psx cc src/dra/7879C.c
--
99:FAILED: build/us/borbo4.elf
100-mipsel-linux-gnu-ld -nostdlib --no-check-sections  -Map build/us/borbo4.map -T build/us/borbo4.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.borbo4.txt -T build/us/config/undefined_syms_auto.us.borbo4.txt -o build/us/borbo4.elf
101-mipsel-linux-gnu-ld: build/us/src/boss/rbo4/unk_17804.c.o: in function `LM52':
102:src/boss/rbo4/unk_17804.c:(.text+0x398): undefined reference to `g_EInitOwlKnight'
103:mipsel-linux-gnu-ld: src/boss/rbo4/unk_17804.c:(.text+0x39c): undefined reference to `g_EInitOwlKnight'
104-mipsel-linux-gnu-ld: build/us/src/boss/rbo4/unk_17804.c.o: in function `LM150':
105:src/boss/rbo4/unk_17804.c:(.text+0x6d8): undefined reference to `g_EInitBloodyZombie'
106:mipsel-linux-gnu-ld: src/boss/rbo4/unk_17804.c:(.text+0x6dc): undefined reference to `g_EInitBloodyZombie'
107-[84/427] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/ric.map -T build/us/ric.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.ric.txt -T build/us/config/undefined_syms_auto.us.ric.txt -o build/us/ric.elf
108-[85/427] psx cc src/st/dai/gen/e_layout.c

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
// RBO4 boss (The Creature) main update; steps drive walk, jump, slam and death.
void func_us_80197938(Entity* self) {
    Entity* newEnt;
    Entity* newEnt2;
    Entity* allocStart;
    Entity* allocEnd;
    s32 coll;
    s32 velX;
    s32 velY;
    u16 timer;
    u16 subStep;
    s16 timerS;
    u8* hitPtr;
    u8 hitIdx;
    s32 snd;

    if (self->flags & 0x100) {
        if (self->step != 6) {
            SetStep(6);
        }
    }
    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitTheCreature);
        CreateEntityFromCurrentEntity(0x17, (Entity*)((u8*)self + 0xBC));
        SetStep(1);
    case 1:
        AnimateEntity(D_us_8018067C, self);
        self->hitboxState = 0;
        if (D_us_801807EC & 1) {
            self->hitboxState = 3;
        block_68:
            SetStep(2);
        }
        break;
    case 2:
        if (self->step_s == 0) {
            ((s16*)&self->ext)[2] = 0x40;
            self->step_s++;
        }
        AnimateEntity(D_us_8018068C, self);
        coll = UnkCollisionFunc2(g_EInitLockCamera);
        if (coll & 0x60) {
            velX = self->velocityX;
            self->velocityX = 0;
            self->posX.val -= velX;
        }
        if (GetDistanceToPlayerX() < 0x68) {
            ((u8*)&self->ext)[8] = 1;
        }
        if (GetDistanceToPlayerX() >= 0x81) {
            ((u8*)&self->ext)[8] = 0;
        }
        if (self->facingLeft == ((u8*)&self->ext)[8]) {
            velX = 0x8000;
        } else {
            velX = -0x8000;
        }
        self->velocityX = velX;
        timer = self->ext.et_801CC9B4.targetAngle - 1;
        self->ext.et_801CC9B4.targetAngle = timer;
        if ((timer << 16) == 0) {
            if (GetDistanceToPlayerX() >= 0x50) {
                SetStep(4);
            } else {
                SetStep(3);
                if ((coll & 0xE0) == 0) {
                    goto block_end_check;
                }
                SetStep(4);
            }
        }
    block_end_check:
        if (self->facingLeft != (GetSideToPlayer() & 1)) {
            SetStep(5);
        }
        break;
    case 5:
        if (AnimateEntity((u8*)&D_us_801806E0, self) == 0) {
            SetStep(2);
        }
        if (self->pose == 2) {
            self->facingLeft ^= 1;
        }
        break;
    case 3:
        if (self->step_s == 0) {
            if (AnimateEntity(g_EInitOwlKnight, self) == 0) {
                g_api_func_80102CD8(1);
                PlaySfxPositional(0x7EA);
                self->ext.et_801CC9B4.targetAngle = 0x20;
                self->step_s++;
            }
            if (self->pose == 4) {
                PlaySfxPositional(0x7EB);
            }
        } else {
            timer = self->ext.et_801CC9B4.targetAngle - 1;
            self->ext.et_801CC9B4.targetAngle = timer;
            if ((timer << 16) == 0) {
                goto block_68;
            }
        }
        break;
    case 4:
        subStep = self->step_s;
        switch (subStep) {
        case 0:
            if (AnimateEntity(g_EInitParanthropus, self) == 0) {
            block_81:
            block_82:
                self->step_s++;
            }
            break;
        case 1:
            self->animCurFrame = 0x1E;
            self->drawFlags = 4;
            self->rotate = 0;
            self->ext.et_801CC9B4.targetAngle = 0x200;
            self->step_s++;
        case 2:
            if (self->facingLeft == 0) {
                velX = 0x30000;
            } else {
                velX = -0x30000;
            }
            self->velocityX = velX;
            self->rotate += 0xC0;
            coll = UnkCollisionFunc2(g_EInitDamageNum);
            if ((g_Timer & 0xF) == 0) {
                PlaySfxPositional(0x608);
            }
            if (coll & 0x80) {
                self->velocityX = 0;
                self->velocityY = -0x40000;
                PlaySfxPositional(0x84C);
                self->step_s++;
            }
            timerS = self->ext.et_801CC9B4.targetAngle;
            if (timerS != 0) {
                self->ext.et_801CC9B4.targetAngle = timerS - 1;
            } else if ((u32)((self->posX.i.hi + g_Tilemap.scrollX.i.hi) - 0xC1) < 0x7F) {
                self->ext.et_801CC9B4.targetAngle = 0x30;
                SetSubStep(4);
            }
            break;
        case 3:
            self->rotate += 0x100;
            if (UnkCollisionFunc3(D_us_8018065C) & 1) {
                PlaySfxPositional(0x654);
                velY = -self->velocityY;
                velY -= velY >> 1;
                self->velocityY = velY;
                if (velY < 0) {
                    velY = -velY;
                }
                if (velY <= 0x7FFF) {
                    self->facingLeft ^= 1;
                    self->step_s--;
                }
            }
            break;
        case 4:
            velX = self->velocityX;
            self->rotate -= 0x100;
            self->velocityX = velX - (velX >> 4);
            UnkCollisionFunc2(g_EInitDamageNum);
            timer = self->ext.et_801CC9B4.targetAngle - 1;
            self->ext.et_801CC9B4.targetAngle = timer;
            if ((timer << 16) == 0) {
                self->drawFlags = 0;
                goto block_82;
            }
            break;
        case 5:
            coll = AnimateEntity((u8*)D_us_801806D8, self);
            if (coll == 0) {
                goto block_68;
            }
            break;
        }
        break;
    case 6:
        subStep = self->step_s;
        switch (subStep) {
        case 0:
            self->hitboxState = 0;
            D_us_801807EC |= 2;
            snd = 0x7EC;
            if (self->rotate != 0) {
                self->rotate = 0;
            }
            self->animCurFrame = 1;
        block_80:
            PlaySfxPositional(snd);
            goto block_81;
        case 1:
            if (UnkCollisionFunc3(D_us_8018065C) & 1) {
                goto block_81;
            }
            break;
        case 2:
            if (AnimateEntity(D_us_801806EC, self) == 0) {
                PlaySfxPositional(0x8B9);
                ((u8*)&self->ext)[0xC5] = 1;
                goto block_82;
            }
            break;
        case 3:
            snd = 0x7C5;
            if (AnimateEntity((u8*)g_EInitBloodyZombie, self) == 0) {
                self->ext.et_801CC9B4.targetAngle = 0x50;
                goto block_80;
            }
            break;
        case 4:
            allocStart = &g_Entities[192];
            allocEnd = allocStart + 64;
            newEnt = AllocEntity(allocStart, allocEnd);
            if (newEnt != NULL) {
                CreateEntityFromEntity(0x18, self, newEnt);
                newEnt->params = 0;
                newEnt->zPriority = self->zPriority + 2;
                newEnt->posX.i.hi = newEnt->posX.i.hi - 0x10 + (Random() & 0x1F);
                newEnt->posY.i.hi = newEnt->posY.i.hi + 0x1C;
            }
            newEnt2 = AllocEntity(allocStart, allocEnd);
            if (newEnt2 != NULL) {
                CreateEntityFromEntity(0x18, self, newEnt2);
                newEnt2->params = 2;
                newEnt2->zPriority = self->zPriority + 2;
                newEnt2->posX.i.hi = newEnt2->posX.i.hi - 0x10 + (Random() & 0x1F);
                newEnt2->posY.i.hi = newEnt2->posY.i.hi + 0x1C;
            }
            timer = self->ext.et_801CC9B4.targetAngle - 1;
            self->ext.et_801CC9B4.targetAngle = timer;
            if ((timer << 16) == 0) {
                self->animCurFrame = 0;
                D_us_801807EC |= 4;
                self->step_s++;
            }
            break;
        }
        break;
    case 0xFF:
        FntPrint(D_us_801973B4, self->animCurFrame);
        if (g_pads_1_pressed & 0x80) {
            if (self->params == 0) {
                self->animCurFrame++;
                self->params |= 1;
                goto block_93;
            }
        } else {
            self->params = 0;
        block_93:
            if (g_pads_1_pressed & 0x20) {
                if (self->step_s == 0) {
                    self->animCurFrame--;
                    self->step_s |= 1;
                }
            } else {
                self->step_s = 0;
            }
        }
        break;
    }
    hitIdx = D_us_80180710[self->animCurFrame];
    hitPtr = &g_EInitStoneSkull[hitIdx * 4];
    self->hitboxOffX = (s8)*hitPtr++;
    self->hitboxOffY = (s8)*hitPtr++;
    self->hitboxWidth = *hitPtr++;
    self->hitboxHeight = *hitPtr;
}
