/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/BO0:func_us_801BB08C
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/3B014.c
   verdict: quality reject: candidate is not usable C: unbalanced braces: 6 unclosed `{`

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
extern EInit g_EInitCommon;
void InitializeEntity(u16 arg0[]);
extern s16 (*g_api_AllocPrimitives)(PrimitiveType type, s32 count);
void DestroyEntity(Entity*);
extern GAME_IMPORT Primitive g_PrimBuf[MAX_PRIM_COUNT];
extern void (*g_api_PlaySfx)(s32 sfxId);
extern GAME_IMPORT PlayerState g_Player;
extern void (*g_api_func_8010E168)(s32 arg0, s16 arg1);
extern void (*g_api_func_8010DFF0)(s32 arg0, s32 arg1);
int rcos(int a);
int rsin(int a);
extern u16 PLAYER_zPriority;
extern u16 PLAYER_step;
extern s32 PLAYER_velocityY;
extern u16 PLAYER_facingLeft;
extern u8 D_us_801813D4;
s32 GetSideToPlayer();
s32 func_us_801BB014(Entity*);

void func_us_801BB08C(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s32 i;
    s16 angle;
    s16 posX;
    s16 posY;
    s16 var_s4;
    s16 var_s7;
    u8* t0;
    u16 params;
    s32 temp;
    s32 temp2;
    s32 temp3;
    u8 temp_fp;
    u8 temp_s5;
    s32 sp10;
    s32 sp18;
    s32 sp20;

    params = self->params;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitCommon);
        self->animSet = 7;
        self->animCurFrame = 1;
        if (params & 0x1000) {
            self->animSet = 0;
        }
        self->facingLeft = 0;
        self->zPriority = PLAYER_zPriority - 0x20;
        self->posY.i.hi += 0x1F;
        if (params & 0x100) {
            self->ext.player.unkA6 = -4;
        } else {
            self->ext.player.unkA6 = 4;
        }
        self->posX.i.hi += self->ext.player.unkA6;
        primIndex = g_api_AllocPrimitives(PRIM_GT4, 3);
        self->primIndex = primIndex;
        if (primIndex == -1) {
            DestroyEntity(self);
            return;
        }
        self->flags |= 0x800000;
        t0 = &D_us_801813D4;
        if (params & 0x1000) {
            t0 = &D_us_801813D4 + 0x18;
        }
        i = 0;
        posY = self->posY.i.hi;
        prim = &g_PrimBuf[self->primIndex];
        if (prim != NULL) {
            do {
                prim->u0 = t0[0];
                prim->u1 = t0[1];
                prim->u2 = t0[2];
                prim->u3 = t0[3];
                prim->v0 = t0[4];
                prim->v1 = t0[5];
                prim->v2 = t0[6];
                prim->tpage = 0x1F;
                prim->clut = 0x198;
                prim->v3 = t0[7];
                if (params & 0x1000) {
                    prim->tpage = 0x12;
                    prim->clut = 0x21B;
                }
                prim->y1 = posY - 0x1F;
                prim->y0 = posY - 0x1F;
                prim->y3 = posY + 0x1F;
                prim->y2 = posY + 0x1F;
                prim->priority = PLAYER_zPriority - 0x20;
                if (i == 0) {
                    prim->y1 = posY - 0x1F;
                    prim->y0 = posY - 0x1F;
                    prim->y3 = posY + 0x1F;
                    prim->y2 = posY + 0x1F;
                }
                prim->drawMode = 6;
                prim->r0 = 0x7F;
                prim->g0 = 0x7F;
                prim->b0 = 0x7F;
                prim->r1 = 0x7F;
                prim->g1 = 0x7F;
                prim->b1 = 0x7F;
                prim->r2 = 0x7F;
                prim->g2 = 0x7F;
                prim->b2 = 0x7F;
                prim->r3 = 0x7F;
                prim->g3 = 0x7F;
                prim->b3 = 0x7F;
                if (i == 2) {
                    if (!(params & 0x100)) {
                        prim->drawMode |= 8;
                    }
                }
                if (i == 1) {
                    if (params & 0x100) {
                        prim->drawMode |= 8;
                    }
                }
                i++;
                prim = prim->next;
                t0 += 8;
            } while (prim != NULL);
        }
        if (func_us_801BB014(self) != 0) {
            if (!(params & 0x100)) {
                self->ext.player.unkA4 = 0x1000;
            }
            if (params & 0x100) {
                self->ext.player.unkA4 = 0x800;
            }
            self->animCurFrame = 0;
            self->step = 4;
            PLAYER_step = 0;
            PLAYER_velocityY = 0;
        } else {
            self->ext.player.unkA4 = 0xC00;
            prim = &g_PrimBuf[self->primIndex];
            i = 0;
            if (prim != NULL) {
                do {
                    if (!(params & 0x1000) || (i != 0)) {
                        prim->drawMode |= 8;
                    }
                    i++;
                    if (i != 3) {
                        prim = prim->next;
                        if (prim != NULL) {
                            continue;
                        }
                    }
                    break;
                } while (1);
            }
        }
        break;

    case 1:
        break;

    case 2:
        if (PLAYER_step != 1) {
            break;
        }
        if (PLAYER_facingLeft == GetSideToPlayer()) {
            break;
        }
        if (func_us_801BB014(self) == 0) {
            break;
        }
        prim = &g_PrimBuf[self->primIndex];
        i = 0;
        if (prim != NULL) {
            do {
                if (i == 1) {
                    if (!(params & 0x100)) {
                        prim->drawMode &= ~8;
                    }
                }
                if (i == 2) {
                    if (params & 0x100) {
                        prim->drawMode &= ~8;
                    }
                }
                if (i == 0) {
                    prim->drawMode &= ~8;
                }
                prim = prim->next;
                i++;
            } while (prim != NULL);
        }
        self->animCurFrame = 0;
        g_api_PlaySfx(0x642);
        g_Player.unk0C = 0;
        g_Player.unk14 = 2;
        self->step++;
        break;

    case 3:
        g_Player.unk0C = 0;
        g_Player.unk14 = 0x18;
        if (!(params & 0x100)) {
            self->ext.player.unkA4 += 0x20;
            if ((s16)self->ext.player.unkA4 >= 0x1000) {
                self->ext.player.unkA4 = 0x1000;
            }
            if ((s16)self->ext.player.unkA4 == 0x1000) {
                self->step++;
            }
        } else {
            self->ext.player.unkA4 -= 0x20;
            if ((s16)self->ext.player.unkA4 < 0x801) {
                self->ext.player.unkA4 = 0x800;
            }
            if ((s16)self->ext.player.unkA4 == 0x800) {
                self->step++;
            }
        }
        break;

    case 4:
        if (g_Player.unk14 < 4) {
            DestroyEntity(self);
            return;
        }
        if (!(params & 0x100)) {
            g_Player.unk0C = 0x8000;
        } else {
            g_Player.unk0C = 0x2000;
        }
        g_Player.unk14 = 3;
        break;

    case 5:
        if (!(params & 0x100)) {
            g_Player.unk0C = 0x2000;
        } else {
            g_Player.unk0C = 0x8000;
        }
        g_Player.unk14 = 4;
        if (func_us_801BB014(self) != 0) {
            break;
        }
        g_api_PlaySfx(0x642);
        self->step++;
        g_Player.unk14 = 0;
        break;

    case 6:
        g_Player.unk0C = 0;
        g_Player.unk14 = 4;
        if (!(params & 0x100)) {
            self->ext.player.unkA4 -= 0x20;
            if ((s16)self->ext.player.unkA4 < 0xC01) {
                self->ext.player.unkA4 = 0xC00;
            }
        } else {
            self->ext.player.unkA4 += 0x20;
            if ((s16)self->ext.player.unkA4 >= 0xC00) {
                self->ext.player.unkA4 = 0xC00;
            }
        }
        if ((s16)self->ext.player.unkA4 == 0xC00) {
            prim = &g_PrimBuf[self->primIndex];
            i = 0;
            if (prim != NULL) {
                do {
                    if (!(params & 0x1000) || (i != 0)) {
                        prim->drawMode |= 8;
                    }
                    prim = prim->next;
                    i++;
                } while (prim != NULL);
            }
            self->animCurFrame = 1;
            self->step++;
        }
        break;
    }

    if (self->step != 1) {
        g_api_func_8010E168(1, 0x20);
        g_api_func_8010DFF0(1, 1);
    }

    posX = self->posX.i.hi - self->ext.player.unkA6;
    if (params & 0x100) {
        var_s4 = posX - 1;
    } else {
        var_s4 = posX + 1;
    }

    prim = &g_PrimBuf[self->primIndex];
    angle = self->ext.player.unkA4;
    i = 0;
    if (prim != NULL) {
        temp_fp = (angle & 0x3FF) >> 4;
        sp10 = (s16)angle < 0xE01;
        sp18 = (s16)angle < 0xA00;
        temp_s5 = temp_fp + 0x3F;
        sp20 = (s16)angle < 0xA01;
        do {
            if (!(prim->drawMode & 8)) {
                if (!(params & 0x100)) {
                    if (i == 0) {
                        var_s7 = var_s4 + ((rcos(angle) >> 8) * 2);
                        prim->x2 = var_s7;
                        prim->x0 = var_s7;
                        temp = var_s7 - (((rsin(angle) >> 4) * 3) >> 7);
                        prim->x3 = temp;
                        prim->x1 = temp;
                        if ((s16)angle >= 0xF81) {
                            temp = var_s7 + 1;
                            prim->x3 = temp;
                            prim->x1 = temp;
                        }
                        if (sp10 == 0) {
                            prim->u0 = 0xB2;
                            prim->u2 = 0xB2;
                            prim->u1 = 0xB6;
                            prim->u3 = 0xB6;
                            if (params & 0x1000) {
                                prim->u0 = 4;
                                prim->u2 = 4;
                                prim->u1 = 0xC;
                                prim->u3 = 0xC;
                            }
                        } else {
                            prim->u0 = 0xB1;
                            prim->u2 = 0xB1;
                            prim->u1 = 0xB7;
                            prim->u3 = 0xB7;
                            if (params & 0x1000) {
                                prim->u0 = 3;
                                prim->u2 = 3;
                                prim->u1 = 0xD;
                                prim->u3 = 0xD;
                            }
                        }
                        if ((s16)angle == 0x1000) {
                            prim->r0 = 0x3F;
                            prim->g0 = 0x3F;
                            prim->b0 = 0x3F;
                            prim->r2 = 0x3F;
                            prim->g2 = 0x3F;
                            prim->b2 = 0x3F;
                        } else {
                            prim->r0 = 0x7F;
                            prim->g0 = 0x7F;
                            prim->b0 = 0x7F;
                            prim->r2 = 0x7F;
                            prim->g2 = 0x7F;
                            prim->b2 = 0x7F;
                        }
                    } else {
                        prim->x0 = var_s4;
                        prim->x2 = var_s4;
                        prim->x1 = var_s7;
                        prim->x3 = var_s7;
                        if ((s16)angle == 0x1000) {
                            prim->r0 = 0x3F;
                            prim->g0 = 0x3F;
                            prim->b0 = 0x3F;
                            prim->r2 = 0x3F;
                            prim->g2 = 0x3F;
                            prim->b2 = 0x3F;
                        } else {
                            prim->r0 = temp_fp;
                            prim->g0 = temp_fp;
                            prim->b0 = temp_fp;
                            prim->r2 = temp_fp;
                            prim->g2 = temp_fp;
                            prim->b2 = temp_fp;
                        }
                    }
                } else {
                    if (i == 0) {
                        var_s7 = var_s4 + ((rcos(angle) >> 8) * 2);
                        prim->x3 = var_s7;
                        prim->x1 = var_s7;
                        temp = var_s7 + (((rsin(angle) >> 4) * 3) >> 7);
                        prim->x2 = temp;
                        prim->x0 = temp;
                        if ((s16)angle < 0x880) {
                            temp = var_s7 - 1;
                            prim->x2 = temp;
                            prim->x0 = temp;
                        }
                        if (sp18 != 0) {
                            prim->u0 = 0xB2;
                            prim->u2 = 0xB2;
                            prim->u1 = 0xB6;
                            prim->u3 = 0xB6;
                            if (params & 0x1000) {
                                prim->u0 = 4;
                                prim->u2 = 4;
                                prim->u1 = 0xC;
                                prim->u3 = 0xC;
                            }
                        }
                        if (sp20 == 0) {
                            prim->u0 = 0xB1;
                            prim->u2 = 0xB1;
                            prim->u1 = 0xB7;
                            prim->u3 = 0xB7;
                            if (params & 0x1000) {
                                prim->u0 = 3;
                                prim->u2 = 3;
                                prim->u1 = 0xD;
                                prim->u3 = 0xD;
                            }
                        }
                        if ((s16)angle == 0x800) {
                            prim->r0 = 0x7F;
                            prim->g0 = 0x7F;
                            prim->b0 = 0x7F;
                            prim->r2 = 0x7F;
                            prim->g2 = 0x7F;
                            prim->b2 = 0x7F;
                        } else {
                            prim->r0 = temp_s5;
                            prim->g0 = temp_s5;
                            prim->b0 = temp_s5;
                            prim->r2 = temp_s5;
                            prim->g2 = temp_s5;
                            prim->b2 = temp_s5;
                        }
                    } else {
                        temp = var_s7 - 1;
                        prim->