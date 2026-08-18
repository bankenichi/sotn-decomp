/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:func_us_801CFEA0
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/unk_4F968.c
   verdict: BUILD FAILED:
_4F968.c:218: union has no member named `unk31C'
183:src/st/rno0/unk_4F968.c:225: union has no member named `unk550'
184:src/st/rno0/unk_4F968.c:238: union has no member named `unkA4'
185:src/st/rno0/unk_4F968.c:239: union has no member named `unkA4'
186:src/st/rno0/unk_4F968.c:240: union has no member named `unkA9'
187:src/st/rno0/unk_4F968.c:241: union has no member named `unkA9'
1

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
extern EInit g_EInitGorgon;
extern Entity g_Entities_224[];
extern void DestroyEntity(Entity* entity);
extern s16 PLAYER_posX_i_hi;
extern u16 PLAYER_facingLeft;

void func_us_801CFEA0(Entity* self) {
    Entity* child;
    Entity* part;
    s32 distX;
    s16 timer;
    s16 step_s;
    s32 hit;
    s16 posX;
    s16 posY;
    s16 randX;
    s16 randY;
    s32 i;

    if ((self->flags & FLAG_UNK_100) && (self->step < 0x16)) {
        child = self;
        for (i = 0; i < 10; i++) {
            child->hitboxState = 0;
            child = (Entity*)((s8*)child + 0xBC);
        }
        if (self->step != 0x13) {
            func_us_801CFE6C(0x15);
            self->step = 0x16;
        }
    }

    if (self->step < 0x17) {
        switch (self->step) {
        case 0:
            InitializeEntity(g_EInitGorgon);
            self->facingLeft = (GetSideToPlayer() & 1) ^ 1;
            self->zPriority = 0x70;
            self->animCurFrame = 0xA;
            self->hitboxWidth = 0xC;
            self->hitboxHeight = 0xC;
            CreateEntityFromEntity(0x3F, self, self + 0xBC);
            CreateEntityFromEntity(0x40, self, self + 0x2F0);
            CreateEntityFromEntity(0x42, self, self + 0x524);
            CreateEntityFromEntity(0x43, self, self + 0x69C);
            CreateEntityFromEntity(0x44, self, self + 0x5E0);
            self->ext.unkA4 = 2;
            break;

        case 1:
            self->ext.unkA4--;
            if (self->ext.unkA4 == 0) {
                part = self;
                for (i = 1; i < 9; i++) {
                    part->parent = self;
                    part->nextPart = (Entity*)((s8*)part + 0xBC);
                    part = part->nextPart;
                }
                part->parent = self;
                part->nextPart = self;
                self->parent = NULL;
                func_us_801CFE6C(0x10);
            }
            break;

        case 16:
        case 17:
            if (self->step_s == 0) {
                self->ext.unkA4 = 0x40;
                self->step_s++;
            }
            if (self->ext.unk398 == 0) {
                child = self + 0x3AC;
            } else {
                child = self + 0x468;
            }
            hit = func_us_801CFC98(child, 0);
            if (hit) {
                if (self->ext.unkA4 != 0) {
                    self->ext.unkA9 = 0x13;
                    func_us_801CFE6C(0x15);
                }
                self->ext.unkA4 = 0x20;
            }
            if (self->ext.unkA4 != 0) {
                self->ext.unkA4--;
            } else if (GetDistanceToPlayerY() < 0x40) {
                distX = self->posX.i.hi - PLAYER_posX_i_hi;
                if (self->facingLeft) {
                    distX = -distX;
                }
                if ((u16)distX > 0xFFB0) {
                    hit = 1;
                    self->ext.unkA4 = 0x10;
                }
                if (!hit && (distX >= 0x61) && (self->step != 0x11)) {
                    func_us_801CFE6C(0x11);
                }
                if (self->ext.unkA0 == 0) {
                    if ((u16)distX < 0x50) {
                        self->ext.unkA0 = 0x80;
                        SetStep(0x14);
                    }
                } else {
                    if (self->ext.unkA0 < 0) {
                        self->ext.unkA0 = 0x80;
                    } else {
                        self->ext.unkA0--;
                    }
                }
            }
            if (hit) {
                self->ext.unkA4 = 0x20;
                self->ext.unkA9 = 0x13;
                func_us_801CFE6C(0x15);
            }
            if (self->hitParams) {
                self->ext.unkA4 = 0x40;
                func_us_801CFE6C(0x12);
            }
            break;

        case 18:
            if (self->ext.unk164 == 0) {
                child = self + 0x178;
            } else {
                child = self + 0x234;
            }
            hit = func_us_801CFC98(child, 1);
            self->ext.unkA4--;
            if (self->ext.unkA4 == 0) {
                hit = 1;
            }
            if (hit) {
                self->ext.unkA4 = 0x18;
                self->ext.unkA9 = 0x10;
                func_us_801CFE6C(0x15);
            }
            break;

        case 19:
            step_s = self->step_s;
            switch (step_s) {
            case 0:
                if (self->ext.unk164 == 0) {
                    child = self + 0x178;
                } else {
                    child = self + 0x234;
                }
                self->posY.i.hi = child->posY.i.hi - 0x16;
                if (self->facingLeft) {
                    self->posX.i.hi = self->posX.i.hi - 0xC;
                } else {
                    self->posX.i.hi = self->posX.i.hi + 0xC;
                }
                self->ext.unkAB = 1;
                self->poseTimer = 0;
                self->pose = 0;
                self->step_s++;
                /* fallthrough */
            case 1:
                if (AnimateEntity(&D_us_80183304, self) == 0) {
                    self->step_s++;
                }
                if (self->pose == 2) {
                    self->facingLeft ^= 1;
                    if (self->facingLeft) {
                        self->posX.i.hi = self->posX.i.hi - 0xC;
                    } else {
                        self->posX.i.hi = self->posX.i.hi + 0xC;
                    }
                }
                break;

            case 2:
                self->animCurFrame = 0xA;
                if (self->ext.unk164 == 0) {
                    child = self + 0x178;
                } else {
                    child = self + 0x234;
                }
                child->posX.i.hi = self->posX.i.hi;
                self->ext.unkA4 = 0x20;
                self->ext.unkAB = 0;
                self->ext.unkA9 = 0x10;
                func_us_801CFE6C(0x15);
                break;
            }
            break;

        case 20:
            step_s = self->step_s;
            switch (step_s) {
            case 0:
                if (self->ext.unk39E) {
                    self->ext.unk31C = 0x14;
                    func_us_801CFE6C(0x14);
                    self->step_s = 1;
                }
                break;

            case 1:
                if (self->ext.unk550 != 0x14) {
                    distX = self->posX.i.hi - PLAYER_posX_i_hi;
                    if ((u16)distX < 0x50) {
                        func_us_801CFE6C(0x14);
                    } else {
                        func_us_801CFE6C(0x10);
                    }
                }
                break;
            }
            break;

        case 21:
            self->ext.unkA4--;
            if (self->ext.unkA4 == 0) {
                if (self->ext.unkA9) {
                    func_us_801CFE6C(self->ext.unkA9);
                } else {
                    func_us_801CFE6C(0x10);
                }
            }
            break;

        case 22:
            step_s = self->step_s;
            switch (step_s) {
            case 0:
                self->ext.unk550 = 0x16;
                self->ext.unkA4 = 0x40;
                self->step_s++;
                /* fallthrough */
            case 1:
                if (!(self->ext.unkA4 & 7)) {
                    PlaySfxPositional(0x655);
                    posX = self->posX.i.hi;
                    posY = self->posY.i.hi;
                    if (PLAYER_facingLeft) {
                        randX = (posX + 0x10) - (Random() & 0x3F);
                    } else {
                        randX = (posX - 0x10) + (Random() & 0x3F);
                    }
                    randY = (posY - 0x10) + (Random() & 0x1F);
                    child = AllocEntity(&g_Entities_224[0], &g_Entities_224[0] + 0x1780);
                    if (child) {
                        CreateEntityFromCurrentEntity(2, child);
                        child->params = 1;
                        child->posX.i.hi = randX;
                        child->posY.i.hi = randY;
                        child->zPriority = self->zPriority + 2;
                    }
                }
                self->ext.unkA4--;
                if (self->ext.unkA4 == 0) {
                    func_us_801CFE6C(0x16);
                    self->step_s = 2;
                }
                break;

            case 2:
                if (self->ext.unk54A == 0) {
                    self->step_s++;
                }
                break;

            case 3:
                PlaySfxPositional(0x693);
                self->ext.unkAC = 1;
                self->step_s++;
                break;

            case 4:
                child = AllocEntity(&g_Entities_224[0], &g_Entities_224[0] + 0x1780);
                if (child) {
                    CreateEntityFromEntity(self, child);
                    child->params = 3;
                    child->zPriority = self->zPriority;
                }
                self->ext.unkA4 = 8;
                self->step_s++;
                break;

            case 5:
                self->ext.unkA4--;
                if (self->ext.unkA4 == 0) {
                    self->animCurFrame = 0;
                    child = self;
                    for (i = 0; i < 9; i++) {
                        DestroyEntity(child);
                        child = (Entity*)((s8*)child + 0xBC);
                    }
                }
                break;
            }
            break;
        }
    }

    self->ext.unkD0 = self->facingLeft;
    self->ext.unk304 = self->facingLeft;
}