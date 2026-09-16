/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO2:func_us_801C39A4
   attempt: 4/4
   from   : muse-spark-1.3-contributor-free
   origin : src/st/rno2/unk_439A4.c
   verdict: BUILD FAILED:
5:src/st/rno2/unk_439A4.c:79: `D_us_80181BE4' undeclared (first use this function)
56:src/st/rno2/unk_439A4.c:104: `D_us_80181C1C' undeclared (first use this function)
57:src/st/rno2/unk_439A4.c:124: `cloudVectorOne' undeclared (first use this function)
58:src/st/rno2/unk_439A4.c:145: `explosionVariantSizes' undeclared (first use this function)
59:src/st/rno2/unk_439A4.c:173: `D_us_80181C2C' undeclared (first use this function)
60:src/st/rno2/unk_439A4.c:229: `D_us_80181BB8' undeclared (first use this function)
61:src/st/rno2/unk_439A4.c:269: `D_us_80181BF8' undeclared (first use this function)
62:src/st/rno2/unk_439A4.c:273: `D_us_80181C08' undeclared (first use this function)
63:src/st/rno2/unk_439A4.c:457: `D_us_801808FE' undeclared (first use this function)
64:src/st/rno2/unk_439A4.c:467: `g_Entities_64' undeclared (first use this function)
65:src/st/rno2/unk_439A4.c:505: `D_us_801B1E48' undeclared (first use this function)
66-[51/105] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/stdre.map -T build/us/stdre.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.stdre.txt -T build/us/config/undefined_syms_auto.us.stdre.txt -o build/us/stdre.elf
67-[52/105] psx cc src/st/top/gen/rooms.c

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
// Malachi boss update: handles patrol, jump, dive, roar and death-prism setup. Exact offsets kept via named ext roots.
void func_us_801C39A4(Entity* self) {
    DRAWENV env;
    DRAWENV* srcDraw;
    DRAWENV* dstDraw;
    DR_ENV* envOut;
    Entity* childEnt;
    Entity* spawn;
    Primitive* prim;
    Primitive* primA4;
    s16 timer82;
    s16 halfHp;
    s16 yDiff;
    s16 scrollY;
    s32 velY;
    s32 coll;
    s32 rndVal;
    s32 rndOff;
    s32 colRes;
    s16 primX0;
    s16 primX1;
    s16 primY0;
    s16 primY1;
    s16 zPri;
    u16 facing;
    u16 subStep;
    u16 animFrame;
    u16 side;
    s32 primIdx;
    s32 cond;

    if ((g_Player.status & 0x40000) && (self->step < 9)) {
        SetStep(9);
    }
    if ((self->flags & 0x100) && (self->step < 0xA)) {
        self->hitboxState = 0;
        SetStep(0xA);
    }
    timer82 = self->ext.crossBoomerang.pad82;
    if (timer82 != 0) {
        self->ext.crossBoomerang.pad82 = timer82 - 1;
    }
    switch (self->step) {
    case 0:
        InitializeEntity(&g_EInitMalachi);
        CreateEntityFromCurrentEntity(0x2C, (Entity*)((s32*)&self->ext.bat.attackTarget + 6));
        ((s16*)&self->ext.bat.attackTarget)[-14] = self->hitPoints / 2;
    case 1:
        if (UnkCollisionFunc3(D_us_80181BA8) & 1) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            SetStep(2);
        }
        break;
    case 2:
        if (self->step_s == 0) {
            self->ext.crossBoomerang.unk80 = 0x40;
            halfHp = ((s16*)&self->ext.bat.attackTarget)[-14];
            self->step_s += 1;
            if (self->hitPoints < halfHp) {
                self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
                self->ext.crossBoomerang.unk80 = 0x20;
            }
        }
        AnimateEntity(D_us_80181BE4, self);
        halfHp = ((s16*)&self->ext.bat.attackTarget)[-14];
        self->ext.crossBoomerang.unk80 -= 1;
        if (self->hitPoints < halfHp) {
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            if ((s16)self->ext.crossBoomerang.unk80 == 0) {
                SetStep(5);
            }
        } else {
            if ((s16)self->ext.crossBoomerang.unk80 == 0x20) {
                self->facingLeft ^= 1;
            }
            facing = self->facingLeft;
            if (facing == ((GetSideToPlayer() & 1) ^ 1)) {
                SetStep(3);
            }
            if ((s16)self->ext.crossBoomerang.unk80 == 0) {
                self->step_s = 0;
            }
        }
        break;
    case 3:
        subStep = self->step_s;
        switch (subStep) {
        case 0:
            if (AnimateEntity(D_us_80181C1C, self) == 0) {
                ((s32*)&self->ext.bat.attackTarget)[-2] = (self->posY.i.hi + g_Tilemap.scrollY.i.hi) - 0x20;
                SetSubStep(1);
            }
            break;
        case 1:
            self->velocityY = -0x40000;
            self->velocityX = 0;
            self->animCurFrame = 0x1A;
            self->step_s += 1;
        case 2:
            MoveEntity();
            velY = self->velocityY + 0x3000;
            self->velocityY = velY;
            yDiff = (self->posY.i.hi + g_Tilemap.scrollY.i.hi) - ((s32*)&self->ext.bat.attackTarget)[-2];
            if ((yDiff <= 0) || (velY > 0)) {
                self->step_s = self->step_s + 1;
            }
            break;
        case 3:
            AnimateEntity(cloudVectorOne, self);
            if (self->pose == 1) {
                PlaySfxPositional(0x68C);
            }
            scrollY = g_Tilemap.scrollY.i.hi;
            yDiff = (self->posY.i.hi + scrollY) - ((s32*)&self->ext.bat.attackTarget)[-2];
            if (yDiff == 0) {
                self->ext.crossBoomerang.unk80 = 0x80;
                self->velocityY = 0;
                self->step_s += 1;
            } else if (yDiff < 0) {
                self->posY.i.hi += 1;
            } else {
                self->posY.i.hi -= 1;
            }
            break;
        case 4:
            AnimateEntity(cloudVectorOne, self);
            if (self->pose == 1) {
                PlaySfxPositional(0x68C);
            }
            colRes = UnkCollisionFunc2(explosionVariantSizes);
            if (colRes & 0x80) {
                self->facingLeft ^= 1;
            }
            if (self->facingLeft == 0) {
                self->velocityX = -0xC000;
            } else {
                self->velocityX = 0xC000;
            }
            if ((s16)self->ext.crossBoomerang.pad82 == 0) {
                SetStep(7);
                ((u8*)&self->ext.crossBoomerang.unk84)[1] = 1;
            }
            if ((s16)self->ext.crossBoomerang.unk80 == 0) {
                if (colRes == 1) {
                    SetSubStep(5);
                }
            } else {
                self->ext.crossBoomerang.unk80 -= 1;
            }
            break;
        case 5:
            self->animCurFrame = 0x1C;
            if (UnkCollisionFunc3(D_us_80181BA8) & 1) {
                SetSubStep(6);
            }
            break;
        case 6:
            if (AnimateEntity(D_us_80181C2C, self) == 0) {
                if ((s16)self->ext.crossBoomerang.pad82 == 0) {
                    SetStep(7);
                    ((u8*)&self->ext.crossBoomerang.unk84)[1] = 0;
                } else {
                    SetStep(2);
                }
            }
            break;
        }
        break;
    case 5:
        subStep = self->step_s;
        if (subStep == 1) {
            MoveEntity();
            velY = self->velocityY + 0x3000;
            self->velocityY = velY;
            if (velY > 0) {
                self->step_s += 1;
                if (self->ext.crossBoomerang.unk84 == 0) {
                    self->ext.crossBoomerang.unk84 = 2;
                } else {
                    self->ext.crossBoomerang.unk84 -= 1;
                }
            }
        } else if (subStep < 2) {
            if (subStep == 0) {
                if (self->facingLeft != 0) {
                    self->velocityX = 0x1C000;
                } else {
                    self->velocityX = -0x1C000;
                }
                self->velocityY = -0x50000;
                self->animCurFrame = 0x1A;
                self->step_s += 1;
            }
        } else if (subStep == 2) {
            self->animCurFrame = 0x1C;
            if (UnkCollisionFunc3(D_us_80181BA8) & 1) {
                SetSubStep(3);
            }
        } else if (subStep == 3) {
            if (AnimateEntity(D_us_80181C2C, self) == 0) {
                self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
                SetSubStep(0);
                if ((s16)self->ext.crossBoomerang.pad82 == 0) {
                    SetStep(7);
                    ((u8*)&self->ext.crossBoomerang.unk84)[1] = 0;
                }
                if (GetDistanceToPlayerX() < 0x48) {
                    SetStep(6);
                }
            }
        }
        break;
    case 6:
        coll = AnimateEntity(D_us_80181BB8, self);
        if (coll == 0) {
            SetStep(2);
        }
        break;
    case 7:
        subStep = self->step_s;
        if (subStep == 0) {
            ((s16*)&self->ext.bat.attackTarget)[12] = 2;
            ((s16*)&self->ext.bat.attackTarget)[13] = 0;
            ((s16*)&self->ext.bat.attackTarget)[38] = 0;
            ((s16*)&self->ext.bat.attackTarget)[39] = 0;
            self->ext.crossBoomerang.unk80 = 0x80;
            PlaySfxPositional(0x6C5);
            self->step_s += 1;
        } else if (subStep == 1) {
            if (((u8*)&self->ext.crossBoomerang.unk84)[1] != 0) {
                AnimateEntity(cloudVectorOne, self);
                if (self->pose == 1) {
                    PlaySfxPositional(0x68C);
                }
            }
            self->ext.crossBoomerang.unk80 -= 1;
            if ((self->ext.crossBoomerang.unk80 << 16) == 0) {
                self->ext.crossBoomerang.pad82 = 0x180;
                SetStep(2);
                if (((u8*)&self->ext.crossBoomerang.unk84)[1] != 0) {
                    SetStep(3);
                    self->step_s = 5;
                }
            }
        }
        break;
    case 9:
        subStep = self->step_s;
        if (subStep == 0) {
            if (UnkCollisionFunc3(D_us_80181BA8) & 1) {
                self->step_s = self->step_s + 1;
            }
        } else if (subStep == 1) {
            if (AnimateEntity(D_us_80181BF8, self) == 0) {
                SetSubStep(2);
            }
        } else if (subStep == 2) {
            if (AnimateEntity(D_us_80181C08, self) == 0) {
                if (!(g_Player.status & 0x40000)) {
                    SetStep(2);
                }
            } else if (g_Player.status & 0x40000) {
            }
        }
        if (g_Player.status & 0x40000) {
            break;
        }
        if (self->step == 9) {
            break;
        }
        SetStep(2);
        break;
    case 10:
        subStep = self->step_s;
        if (subStep == 1) {
            prim = ((Primitive**)&self->ext.bat.attackTarget)[-10];
            envOut = g_api_func_800EDB08((POLY_GT4*)prim);
            srcDraw = &g_CurrentBuffer->draw;
            dstDraw = &env;
            do {
                dstDraw->clip = srcDraw->clip;
                dstDraw->ofs[0] = srcDraw->ofs[0];
                dstDraw->ofs[1] = srcDraw->ofs[1];
                dstDraw->tw = srcDraw->tw;
                srcDraw++;
                dstDraw = (DRAWENV*)((s32*)dstDraw + 4);
            } while (srcDraw != (DRAWENV*)((u8*)&g_CurrentBuffer->draw + 0x50));
            dstDraw->clip = srcDraw->clip;
            dstDraw->ofs[0] = srcDraw->ofs[0];
            dstDraw->ofs[1] = srcDraw->ofs[1];
            if (self->params == 0) {
                cond = 0x100;
            } else {
                cond = 0x180;
            }
            env.clip.y = 0;
            env.clip.w = cond;
            env.clip.h = 0x80;
            env.ofs[0] = 0x80;
            env.ofs[1] = 0x80;
            SetDrawEnv(envOut, &env);
            prim->priority = 0xF;
            if (self->params != 0) {
                prim->priority = 0x13;
            }
            prim->drawMode = 0;
            ((s32*)&self->ext.bat.attackTarget)[-2] = 0x28;
            self->ext.crossBoomerang.unk80 = 0x10;
            self->step_s += 1;
        } else if (subStep < 2) {
            if (subStep == 0) {
                DestroyEntity((Entity*)((s32*)&self->ext.bat.attackTarget + 6));
                if ((u16)(self->animCurFrame - 0xD) < 10) {
                    self->animCurFrame = 1;
                }
                primIdx = g_api_AllocPrimitives(1, 8);
                if (primIdx == -1) {
                    self->step = 0;
                    return;
                }
                prim = &g_PrimBuf[primIdx];
                self->primIndex = primIdx;
                ((Primitive**)&self->ext.bat.attackTarget)[-10] = prim;
                self->flags |= 0x800000;
                envOut = g_api_func_800EDB08((POLY_GT4*)prim);
                if (envOut == 0) {
                    DestroyEntity(self);
                    return;
                }
                prim->type = 7;
                prim->priority = 0xF;
                if (self->params == 0) {
                    prim->priority = 0x13;
                }
                prim->drawMode = 0;
                srcDraw = &g_CurrentBuffer->draw;
                dstDraw = &env;
                do {
                    dstDraw->clip = srcDraw->clip;
                    dstDraw->ofs[0] = srcDraw->ofs[0];
                    dstDraw->ofs[1] = srcDraw->ofs[1];
                    dstDraw->tw = srcDraw->tw;
                    srcDraw++;
                    dstDraw = (DRAWENV*)((s32*)dstDraw + 4);
                } while (srcDraw != (DRAWENV*)((u8*)&g_CurrentBuffer->draw + 0x50));
                dstDraw->clip = srcDraw->clip;
                dstDraw->ofs[0] = srcDraw->ofs[0];
                dstDraw->ofs[1] = srcDraw->ofs[1];
                env.clip.x = 1;
                env.clip.w = 0;
                env.tw.x = 0;
                env.tw.y = 0;
                if (self->params == 0) {
                    cond = 0x100;
                } else {
                    cond = 0x180;
                }
                env.clip.y = 0;
                env.clip.h = cond;
                env.ofs[0] = 0x80;
                env.ofs[1] = 0x80;
                SetDrawEnv(envOut, &env);
                prim = prim->next;
                envOut = g_api_func_800EDB08((POLY_GT4*)prim);
                if (envOut == 0) {
                    DestroyEntity(self);
                    return;
                }
                prim->type = 7;
                prim->priority = 0x12;
                if (self->params != 0) {
                    cond = 0x7F;
                    prim->priority = 0x16;
                }
                prim->drawMode = 0x800;
                prim = prim->next;
                self->ext.bat.attackTarget = (Entity*)prim;
                if (self->params == 0) {
                    cond = 0x100;
                } else {
                    cond = 0xFF;
                }
                prim->type = 4;
                prim->tpage = 0x110;
                prim->u3 = 0x3F;
                prim->u1 = 0x3F;
                prim->u2 = 0;
                prim->u0 = 0;
                prim->v1 = cond - 0x70;
                prim->v0 = cond - 0x70;
                prim->v3 = cond;
                prim->v2 = cond;
                primX0 = self->posX.i.hi - 0x20;
                primX1 = self->posX.i.hi + 0x20;
                prim->x2 = primX0;
                prim->x0 = primX0;
                prim->x3 = primX1;
                prim->x1 = primX1;
                primY1 = self->posY.i.hi + 0x28;
                primY0 = self->posY.i.hi - 0x48;
                prim->y3 = primY1;
                prim->y2 = primY1;
                prim->y1 = primY0;
                prim->y0 = primY0;
                prim->drawMode = 2;
                prim->priority = self->zPriority;
                prim = prim->next;
                prim->type = 1;
                prim->u0 = 0x80;
                prim->v0 = 0x80;
                prim->r0 = 0;
                prim->g0 = 0;
                prim->b0 = 0;
                if (self->params != 0) {
                    cond = cond << 0;
                }
                prim->clut = (self->params != 0) << 7;
                prim->priority = 0x11;
                if (self->params != 0) {
                    prim->priority = 0x15;
                }
                prim->drawMode = 0x51;
                prim = prim->next;
                if (prim != 0) {
                    do {
                        prim->drawMode = 8;
                        prim = prim->next;
                    } while (prim != 0);
                }
                if (self->params == 0) {
                    self->zPriority = 0x10;
                } else {
                    self->zPriority = 0x14;
                }
                if (self->params == 0) {
                    cond = 0x80;
                } else {
                    cond = 0x100;
                }
                self->posX.i.hi = 0x20;
                self->posY.i.hi = cond - 0x28;
                self->palette = D_us_801808FE;
                self->flags &= ~0x80000;
                self->step_s += 1;
            }
        } else if (subStep == 2) {
            primA4 = (Primitive*)self->ext.bat.attackTarget;
            rndVal = Random();
            if ((g_Timer & 0xF) == 0) {
                rndOff = rndVal & 0x3F;
                PlaySfxPositional(0x655);
                spawn = AllocEntity(&g_Entities_64, &g_EvHwCardEnd);
                if (spawn != 0) {
                    CreateEntityFromCurrentEntity(2, spawn);
                    spawn->posX.i.hi = primA4->x0 + rndOff;
                    spawn->params = 3;
                    spawn->posY.i.hi = primA4->y2 + ((s32*)&self->ext.bat.attackTarget)[-2] - 0x30;
                }
            }
            spawn = AllocEntity(&g_Entities_64, &g_EvHwCardEnd);
            if (spawn != 0) {
                CreateEntityFromCurrentEntity(0x2A, spawn);
                spawn->posX.i.hi = self->posX.i.hi + rndOff - 0x20;
                spawn->params = 1;
                spawn->facingLeft = coll;
                spawn->zPriority = 0x10;
                spawn->posY.i.hi = self->posY.i.hi + ((s32*)&self->ext.bat.attackTarget)[-2] + 4;
                if (self->params != 0) {
                    spawn->zPriority = 0x14;
                }
            }
            self->ext.crossBoomerang.unk80 -= 1;
            if ((self->ext.crossBoomerang.unk80 << 16) == 0) {
                self->ext.crossBoomerang.unk80 = 2;
                ((s32*)&self->ext.bat.attackTarget)[-2] -= 2;
                if (((s32*)&self->ext.bat.attackTarget)[-2] < -0x28) {
                    self->ext.crossBoomerang.unk80 = 0x40;
                    self->step_s += 1;
                }
            }
        } else if (subStep == 3) {
            self->ext.crossBoomerang.unk80 -= 1;
            if ((self->ext.crossBoomerang.unk80 << 16) == 0) {
                DestroyEntity(self);
                return;
            }
        }
        break;
    case 255:
        FntPrint(D_us_801B1E48, self->animCurFrame);
        if (g_pads_1_pressed & 0x80) {
            if (self->params == 0) {
                self->params |= 1;
                self->animCurFrame += 1;
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
    }
    if ((u16)(self->animCurFrame - 0xF) < 4) {
        self->hitboxOffX = -0x12;
        self->hitboxOffY = 0x11;
        self->hitboxWidth = 0x16;
        self->hitboxHeight = 0x16;
    } else {
        self->hitboxOffX = -1;
        self->hitboxOffY = 1;
        self->hitboxWidth = 0x13;
        self->hitboxHeight = 0x26;
    }
}
