/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO7:func_us_80194D3C
   attempt: 4/4
   from   : muse-spark-1.3-contributor-free
   origin : src/boss/bo7/unk_14CE0.c
   verdict: BUILD FAILED:
 this function)
53:src/boss/bo7/unk_14CE0.c:198: incompatible types in assignment
54:src/boss/bo7/unk_14CE0.c:204: `D_us_80180760' undeclared (first use this function)
55:src/boss/bo7/unk_14CE0.c:211: `D_us_8018073C' undeclared (first use this function)
56:src/boss/bo7/unk_14CE0.c:217: `g_Entities_160' undeclared (first use this function)
57:src/boss/bo7/unk_14CE0.c:245: `D_us_801806D8' undeclared (first use this function)
58:src/boss/bo7/unk_14CE0.c:252: `D_us_80180788' undeclared (first use this function)
59:src/boss/bo7/unk_14CE0.c:291: `D_us_8018072C' undeclared (first use this function)
60:src/boss/bo7/unk_14CE0.c:333: `g_Entities_192' undeclared (first use this function)
61:src/boss/bo7/unk_14CE0.c:344: `D_us_8018076C' undeclared (first use this function)
62:src/boss/bo7/unk_14CE0.c:346: incompatible types in assignment
63:src/boss/bo7/unk_14CE0.c:366: incompatible types in assignment
64:src/boss/bo7/unk_14CE0.c:379: `D_us_80192E34' undeclared (first use this function)
65:src/boss/bo7/unk_14CE0.c:409: `D_us_8018081C' undeclared (first use this function)
66:src/boss/bo7/unk_14CE0.c:410: `D_us_801807E4' undeclared (first use this function)
67-[34/108] psx cc src/st/no3/gen/sprites.c
68-[35/108] psx cc src/st/no4/gen/sprites.c

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
// Cerberus boss main update: movement, lunges, fire and debug handling.
void func_us_80194D3C(Entity* self) {
    Entity* newEnt;
    s32 scrollX;
    s32 distX;
    s32 side;
    s32 s2;
    s32 hidx;
    s32 rnd;
    s16 vel;
    u16 timer;
    u8 padIdx;
    u8* padBytes;
    s16 absDist;
    s32 condA;
    s32 condB;
    s32 condC;
    u8* hitData;
    s32 i;

    if (self->flags & 0x100) {
        if (self->step != 8) {
            SetStep(8);
        }
    }
    switch (self->step) {
    case 0:
        InitializeEntity(D_us_801806E8);
        self->hitboxState = 0;
        SetStep(2);
    case 2:
        AnimateEntity(D_us_801806FC, self);
        if (D_us_80180848[0] & 2) {
            self->hitboxState = 3;
            SetStep(3);
        }
        break;
    case 3:
        if (self->step_s == 0) {
            self->ext.player.pad = 0x40;
            self->step_s++;
        }
        if (AnimateEntity(D_us_80180708, self) == 0) {
            PlaySfxPositional(0x783);
        }
        if (GetDistanceToPlayerX() < 0x68) {
            ((u8*)&self->ext.player.pad)[4] = 1;
        }
        if (GetDistanceToPlayerX() >= 0x81) {
            ((u8*)&self->ext.player.pad)[4] = 0;
        }
        if (GetDistanceToPlayerX() >= 0x31) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        }
        MoveEntity();
        if (self->facingLeft == ((u8*)&self->ext.player.pad)[4]) {
            self->velocityX = -0x8000;
        } else {
            self->velocityX = 0x8000;
        }
        timer = self->ext.player.pad - 1;
        self->ext.player.pad = timer;
        if (timer == 0) {
            s2 = self->posX.i.hi + g_Tilemap.scrollX.i.hi;
            SetStep(10);
            if (self->facingLeft != 0) {
                s2 = 0x200 - s2;
            }
            side = (GetSideToPlayer() & 1) ^ 1;
            if ((s2 < 0xD0) && (self->facingLeft == side)) {
                SetStep(9);
            }
            absDist = s2;
            if (s2 < 0) {
                absDist = -s2;
            }
            condA = s2 < 0x141;
            if (absDist >= 0x51) {
                condA = s2 < 0x141;
                if (self->facingLeft != side) {
                    SetStep(9);
                    condA = s2 < 0x141;
                }
            }
            condB = s2 < 0x181;
            if (condA == 0) {
                condB = s2 < 0x181;
                if (self->facingLeft == side) {
                    SetStep(6);
                    condB = s2 < 0x181;
                }
            }
            if ((condB == 0) && (self->facingLeft == side)) {
                SetStep(4);
            }
            if ((g_Player.status & 1) || ((g_Entities[0].posY.i.hi < 0xA0) && (g_Player.vram_flag & 1))) {
                SetStep(5);
            }
        }
        break;
    case 11:
        switch (self->step_s) {
        case 0:
            if (AnimateEntity(D_us_8018071C, self) == 0) {
                if (self->facingLeft == 0) {
                    self->velocityX = 0x60000;
                } else {
                    self->velocityX = -0x60000;
                }
                self->ext.player.pad = 0x40;
                self->step_s++;
            }
            break;
        case 1:
            MoveEntity();
            self->velocityX = self->velocityX - (self->velocityX >> 6);
            timer = self->ext.player.pad - 1;
            self->ext.player.pad = timer;
            if (timer == 0) {
                SetStep(3);
            }
            break;
        }
        break;
    case 5:
        switch (self->step_s) {
        case 0:
            if (AnimateEntity(D_us_80180754, self) == 0) {
                SetSubStep(1);
            }
            break;
        case 1:
            if (AnimateEntity(BackgroundBlockInit, self) == 0) {
                PlaySfxPositional(0x782);
                PlaySfxPositional(0x7CF);
                self->ext.player.pad = 0x80;
                SetSubStep(2);
            }
            break;
        case 2:
            if ((self->ext.player.pad & 3) == 0) {
                i = 0;
                s2 = 0;
                do {
                    newEnt = AllocEntity(&g_Entities_128, (Entity*)((u8*)&g_Entities_128 + 0x4680));
                    if (newEnt != NULL) {
                        CreateEntityFromEntity(0x1E, self, newEnt);
                        if (self->facingLeft != 0) {
                            newEnt->posX.i.hi = newEnt->posX.i.hi - D_us_801806F0[i * 2];
                        } else {
                            newEnt->posX.i.hi = newEnt->posX.i.hi + D_us_801806F0[i * 2];
                        }
                        newEnt->params = i;
                        newEnt->posY.i.hi = newEnt->posY.i.hi + D_us_801806F2[i * 2];
                        newEnt->zPriority = self->zPriority + 1;
                        newEnt->facingLeft = self->facingLeft;
                    }
                    i++;
                    s2 += 4;
                } while (i < 3);
            }
            timer = self->ext.player.pad - 1;
            self->ext.player.pad = timer;
            if (timer == 0) {
                self->step_s++;
            }
            break;
        case 3:
            if (AnimateEntity(D_us_80180760, self) != 0) {
                SetStep(3);
            }
            break;
        }
        break;
    case 10:
        if (AnimateEntity(D_us_8018073C, self) == 0) {
            SetStep(3);
        }
        if (self->pose == 3) {
            PlaySfxPositional(0x7C6);
            PlaySfxPositional(0x782);
            newEnt = AllocEntity(&g_Entities_160, (Entity*)((u8*)&g_Entities_160 + 0x1780));
            if (newEnt != NULL) {
                CreateEntityFromEntity(0x1D, self, newEnt);
                newEnt->facingLeft = self->facingLeft;
                if (self->facingLeft != 0) {
                    newEnt->posX.i.hi = newEnt->posX.i.hi + 0x18;
                } else {
                    newEnt->posX.i.hi = newEnt->posX.i.hi - 0x18;
                }
                newEnt->params = ((u8*)&self->ext.player.pad)[5];
                newEnt->zPriority = self->zPriority + 1;
            }
        }
        break;
    case 9:
        switch (self->step_s) {
        case 1:
            self->velocityY = -0x60000;
            if (self->facingLeft != 0) {
                self->velocityX = -0x28000;
            } else {
                self->velocityX = 0x28000;
            }
            self->step_s++;
            break;
        case 2:
            MoveEntity();
            self->velocityY = self->velocityY + 0x3800;
            if (func_us_80194338_from_rbo0((s16*)D_us_801806D8) & 1) {
                PlaySfxPositional(0x63D);
                g_api_func_80102CD8(1);
                self->step_s++;
            }
            break;
        case 3:
            if (AnimateEntity(D_us_80180788, self) == 0) {
                SetStep(3);
            }
            break;
        }
        break;
    case 4:
        switch (self->step_s) {
        case 1:
            self->velocityY = -0x60000;
            if (self->facingLeft != 0) {
                self->velocityX = 0x28000;
            } else {
                self->velocityX = -0x28000;
            }
            self->step_s++;
            break;
        case 2:
            MoveEntity();
            self->velocityY = self->velocityY + 0x3800;
            if (func_us_80194338_from_rbo0((s16*)D_us_801806D8) & 1) {
                PlaySfxPositional(0x63D);
                g_api_func_80102CD8(1);
                self->step_s++;
            }
            break;
        case 3:
            if (AnimateEntity(D_us_80180788, self) == 0) {
                SetStep(3);
            }
            break;
        }
        break;
    case 6:
        switch (self->step_s) {
        case 0:
            ((u8*)&self->ext.player.pad)[6] = 8;
            self->step_s++;
        case 1:
            if (AnimateEntity(D_us_8018072C, self) == 0) {
                padBytes = (u8*)&self->ext.player.pad;
                padBytes[6]--;
                if (padBytes[6] == 0) {
                    SetStep(3);
                }
            }
            if (self->pose == 5) {
                PlaySfxPositional(0x7C6);
                PlaySfxPositional(0x782);
                newEnt = AllocEntity(&g_Entities_160, (Entity*)((u8*)&g_Entities_160 + 0x1780));
                if (newEnt != NULL) {
                    CreateEntityFromEntity(0x1D, self, newEnt);
                    newEnt->facingLeft = self->facingLeft;
                    if (self->facingLeft != 0) {
                        newEnt->posX.i.hi = newEnt->posX.i.hi + 0x18;
                    } else {
                        newEnt->posX.i.hi = newEnt->posX.i.hi - 0x18;
                    }
                    newEnt->params = ((u8*)&self->ext.player.pad)[5];
                    newEnt->zPriority = self->zPriority + 1;
                }
                padBytes = (u8*)&self->ext.player.pad;
                padBytes[5]++;
                if (padBytes[5] >= 3) {
                    padBytes[5] = 0;
                }
            }
            break;
        }
        break;
    case 8:
        switch (self->step_s) {
        case 0:
            self->hitboxState = 0;
            D_us_80180848[0] |= 4;
            PlaySfxPositional(0x780);
            self->step_s++;
            break;
        case 1:
            if ((g_Timer & 7) == 0) {
                PlaySfxPositional(0x655);
                newEnt = AllocEntity(&g_Entities_192, (Entity*)((u8*)&g_Entities_192 + 0x2F00));
                if (newEnt != NULL) {
                    CreateEntityFromEntity(0x20, self, newEnt);
                    newEnt->params = 1;
                    newEnt->zPriority = self->zPriority + 1;
                    rnd = Random();
                    newEnt->posX.i.hi = newEnt->posX.i.hi - 0x20 + (rnd & 0x3F);
                    rnd = Random();
                    newEnt->posY.i.hi = newEnt->posY.i.hi - 0xC + (rnd & 0x1F);
                }
            }
            if (AnimateEntity(D_us_8018076C, self) == 0) {
                PlaySfxPositional(0x7C5);
                self->ext.player.pad = 0x50;
                self->step_s++;
            }
            break;
        case 2:
            newEnt = AllocEntity(&g_Entities_192, (Entity*)((u8*)&g_Entities_192 + 0x2F00));
            if (newEnt != NULL) {
                CreateEntityFromEntity(0x20, self, newEnt);
                newEnt->params = 2;
                newEnt->zPriority = self->zPriority + 1;
                rnd = Random();
                newEnt->posX.i.hi = newEnt->posX.i.hi - 0x20 + (rnd & 0x3F);
                if (self->facingLeft != 0) {
                    newEnt->posX.i.hi = newEnt->posX.i.hi - 0xC;
                } else {
                    newEnt->posX.i.hi = newEnt->posX.i.hi + 0xC;
                }
                newEnt->posY.i.hi = newEnt->posY.i.hi + 0x18;
            }
            timer = self->ext.player.pad - 1;
            self->ext.player.pad = timer;
            if (timer == 0) {
                self->animCurFrame = 0;
                self->step_s++;
            }
            break;
        case 3:
            self->step_s++;
            D_us_80180848[0] |= 8;
            break;
        }
        break;
    case 255:
        FntPrint(D_us_80192E34, self->animCurFrame);
        if (g_pads_1_pressed & 0x80) {
            if (self->params == 0) {
                self->animCurFrame++;
                self->params |= 1;
            }
        } else {
            self->params = 0;
        }
        if (g_pads_1_pressed & 0x20) {
            if (self->step_s == 0) {
                self->animCurFrame--;
                self->step_s |= 1;
            }
        } else {
            self->step_s = 0;
        }
        break;
    }
    scrollX = g_Tilemap.scrollX.i.hi;
    s2 = self->posX.i.hi + scrollX;
    if (self->velocityX < 0) {
        if (s2 < 0x68) {
            self->posX.i.hi = 0x68 - scrollX;
        }
    } else {
        if (s2 >= 0x1A1) {
            self->posX.i.hi = 0x1A0 - scrollX;
        }
    }
    hidx = D_us_8018081C[self->animCurFrame] << 2;
    self->hitboxOffX = (s8)D_us_801807E4[hidx];
    self->hitboxOffY = (s8)D_us_801807E4[hidx + 1];
    self->hitboxWidth = D_us_801807E4[hidx + 2];
    self->hitboxHeight = D_us_801807E4[hidx + 3];
}
