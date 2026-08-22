/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RCEN:EntityShaft
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/e_shaft.c
   verdict: BUILD FAILED:
ction it appears in.)
232:src/st/rcen/e_shaft.c:104: structure has no member named `_align_unkA8'
233:src/st/rcen/e_shaft.c:106: incompatible types in assignment
234:src/st/rcen/e_shaft.c:120: `PrizeDrops' undeclared (first use this function)
235:src/st/rcen/e_shaft.c:145: structure has no member named `unkA4E'
236:src/st/rcen/e_shaft.c:146: structure has no member named `unkA4A'
237:src/st/rcen/e_shaft.c:147: structure has no member named `unkA6C'
238:src/st/rcen/e_shaft.c:149: incompatible types in assignment
239:src/st/rcen/e_shaft.c:151: structure has no member named `_align_unkA8'
240:src/st/rcen/e_shaft.c:155: structure has no member named `_align_unkA8'
241:src/st/rcen/e_shaft.c:160: structure has no member named `_align_unkA8'
242:src/st/rcen/e_shaft.c:164: incompatible types in assignment
243:src/st/rcen/e_shaft.c:181: `PLAYER_posX_i_hi' undeclared (first use this function)
244:src/st/rcen/e_shaft.c:185: `PLAYER_posY_i_hi' undeclared (first use this function)
245:src/st/rcen/e_shaft.c:273: `D_us_80180690' undeclared (first use this function)
246-src/st/rcen/e_shaft.c: At top level:
247:src/st/rcen/e_shaft.c:300: `PrizeDrops' used prior to declaration
248-[228/356] psx cc src/st/rno3/stage_data.c
249-[229/356] psx cc src/st/rnz0/sprite_banks.c

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
/* Mechanical symbol repair from escalation_triage.py. */
extern AnimationFrame PrizeDrops[];

void EntityShaft(Entity* self) {
    s32 angle;
    s32 distX;
    s32 distY;
    s32 temp;
    s16 timer;
    s16 playerX;
    s16 playerY;
    s32 i;
    Entity* newEntity;
    s32 primIndex;
    s32 s4;
    s32 s5;
    s32 s6;
    Entity* s0;
    Entity* s2;
    u16 step;
    u16 step_s;

    if (self->flags & FLAG_UNK_100) {
        if (self->step != 4) {
            SetStep(4);
        }
    }

    step = self->step;
    if (step == 2) {
        goto step_2;
    }
    if (step < 3) {
        if (step == 0) {
            goto step_0;
        }
        if (step == 1) {
            goto step_1;
        }
        goto end;
    }
    if (step == 4) {
        goto step_4;
    }
    if (step == 0xFF) {
        goto step_FF;
    }
    goto end;

step_0:
    InitializeEntity(g_EInitShaft);
    self->drawFlags = 8;
    self->animCurFrame = 0x8B;
    self->opacity = 0;
    self->ext.player.unkA6 = -0x400;
    self->hitboxState = 0;
    CreateEntityFromCurrentEntity(0x18, self + 0xBC);
    self->ext.player.unkA8 = self->zPriority + 1;
    CreateEntityFromCurrentEntity(0x17, self + 0x178);
    self->ext.player.anim = (u16)self->zPriority;
    CreateEntityFromCurrentEntity(0x19, self + 0xA48);
    self->ext.player._align_unkA8 = self->zPriority + 2;
    self->ext.player.unkA4 = 0x1C0 - g_Tilemap.scrollX.i.hi;
    self->ext.player.pad = 0x1C0 - g_Tilemap.scrollY.i.hi;
    SetStep(1);

step_1:
    step_s = self->step_s;
    switch (step_s) {
    case 0:
        if ((g_CastleFlags[0xE0] != 0) || (g_PlayableCharacter != 0) || (g_DemoMode != Demo_None)) {
            if ((GetDistanceToPlayerX() < 0x30) && (GetDistanceToPlayerY() < 0x40)) {
                goto advance_step_s;
            }
        } else if (g_CutsceneFlags & 2) {
        advance_step_s:
            self->step_s++;
            PrizeDrops |= 1;
        }
        break;
    case 1:
        if (PrizeDrops & 2) {
            stopMusicFlag = step_s;
            currentMusicId = 0x334;
            self->step_s++;
        }
        break;
    case 2:
        if (g_api_func_80131F68() == 0) {
            stopMusicFlag = 0;
            g_api_PlaySfx(currentMusicId);
            self->step_s++;
        }
        break;
    case 3:
        self->opacity += 4;
        if (self->opacity >= 0x81) {
            self->drawFlags = 0;
            self->hitboxState = 3;
            CreateEntityFromCurrentEntity(0x1A, self + 0x234);
            s2 = self + 0x3AC;
            s4 = 0;
            self->ext.player.unkA4E = 0;
            self->ext.player.unkA4A = self->zPriority + 8;
            self->ext.player.unkA6C = 0x140;
            self->ext.player.unkA4 = (s32)self;
            self->ext.player.pad = 0x140 - g_Tilemap.scrollX.i.hi;
            CreateEntityFromCurrentEntity(0x1A, self + 0x2F0);
            self->ext.player._align_unkA8 = 1;
            self->ext.player.unkA8 = self->zPriority + 8;
            s0 = self + 0x3AE;
            self->ext.player.anim = 0x140;
            self->ext.player._align_unkA8 = (s32)self;
            self->ext.player.unkA4 = 0x1C0 - g_Tilemap.scrollX.i.hi;
            do {
                CreateEntityFromCurrentEntity(0x1F, s2);
                s4++;
                s0->ext.player._align_unkA8 = (s32)self;
                s0->ext.player.unkA8 = 0x140;
                s0->ext.player.unkA6 = self->zPriority + 0xFFFC;
                s2 += 0xBC;
                s0->ext.player.pad = (s0->ext.player.pad + 0x40) - (Random() & 0x7F);
                s0 += 0xBC;
            } while (s4 < 4);
            self->hitboxState = 3;
            g_api_PlaySfx(0x845);
            SetStep(2);
        }
        break;
    }
    goto end;

step_2:
    if (self->step_s == 0) {
        self->ext.player.unkA4 = 0x100;
        self->step_s++;
    }
    MoveEntity();
    playerX = PLAYER_posX_i_hi;
    angle = ((playerX / 2) * -0x10);
    distX = (rcos(angle) * 0x90) >> 12;
    distY = (rsin(angle) * 0x90) >> 12;
    temp = ratan2((distY + PLAYER_posY_i_hi) - self->posY.i.hi, (distX + playerX) - self->posX.i.hi);
    angle = func_us_8019A98C(0x20, self->ext.player.unkA6, temp);
    self->velocityX = (rcos(angle) * 0x1C000) >> 12;
    self->velocityY = (rsin(angle) * 0x1C000) >> 12;
    self->ext.player.unkA6 = angle;
    self->ext.player.unkA4--;
    if (self->ext.player.unkA4 == 0) {
        SetStep(3);
    }
    goto end;

step_4:
    step_s = self->step_s;
    switch (step_s) {
    case 0:
        CreateEntityFromCurrentEntity(0x21, &g_Entities[200].posX);
        g_Entities[200].params = 1;
        g_Entities[200].flags = 0x10000;
        self->palette = 0x200;
        self->step_s++;
        break;
    case 1:
        if ((g_CastleFlags[0xE0] != 0) || (g_PlayableCharacter != 0) || (g_DemoMode != Demo_None) || (g_CutsceneFlags & 0x100)) {
            self->hitboxState = 0;
            PrizeDrops |= 4;
            self->drawFlags = 8;
            self->opacity = 0x80;
            self->step_s++;
        } else {
            self->palette = 0x200;
        }
        break;
    case 2:
        MoveEntity();
        distX = 0x80 - self->posX.i.hi;
        distY = 0x80 - self->posY.i.hi;
        angle = ratan2(distY, distX);
        self->velocityX = rcos(angle) * 0xC;
        self->velocityY = rsin(angle) * 0xC;
        s4 = 1;
        if (SquareRoot0((distX * distX) + (distY * distY)) < 4) {
            self->velocityX = 0;
            self->velocityY = 0;
        } else {
            s4 = 0;
        }
        timer = self->opacity - 1;
        if (timer < 0) {
            timer = 0;
        }
        self->opacity = timer;
        if ((timer == 0) && (s4 != 0)) {
            self->ext.player.unkA4 = 0x60;
            g_api_PlaySfx(0x7CE);
            self->step_s++;
        }
        break;
    case 3:
        s4 = 0;
        do {
            newEntity = AllocEntity(&g_Entities[96], &g_Entities[96] + 0x7580);
            s4++;
            if (newEntity != NULL) {
                CreateEntityFromEntity(0x20, self, newEntity);
                newEntity->params = 2;
                newEntity->zPriority = self->zPriority + 0x10;
            }
        } while (s4 < 2);
        self->ext.player.unkA4--;
        if (self->ext.player.unkA4 == 0) {
            self->ext.player.unkA4 = 0x20;
            self->animCurFrame = 0;
            g_api_PlaySfx(0x660);
            self->step_s++;
            PrizeDrops |= 8;
        }
        break;
    case 4:
        if (!(self->ext.player.unkA4 & 1)) {
            newEntity = AllocEntity(&g_Entities[96], &g_Entities[96] + 0x7580);
            if (newEntity != NULL) {
                CreateEntityFromEntity(0x20, self, newEntity);
                newEntity->params = 3;
                newEntity->zPriority = self->zPriority + 0x10;
            }
        }
        self->ext.player.unkA4--;
        if (self->ext.player.unkA4 == 0) {
            D_us_80180690[0] = 0;
            SetStep(2);
        }
        break;
    }
    goto end;

step_FF:
    /* Debug mode: not implemented in this port */
    goto end;

end:
    return;
}