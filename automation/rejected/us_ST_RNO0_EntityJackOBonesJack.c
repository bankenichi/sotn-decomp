/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:EntityJackOBonesJack
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/unk_48100.c
   verdict: BUILD FAILED:
48:src/boss/bo6/us_39144.c:454: conflicting types for `BO6_RicCreateEntFactoryFromEntity'
49:src/boss/bo6/us_39144.c:209: previous declaration of `BO6_RicCreateEntFactoryFromEntity'
50-[48/295] psx cc src/st/are/gfx_data.c
51-[49/295] psx cc src/st/cat/gfx_data.c
--
148:src/st/rno0/unk_48100.c:53: structure has no member named `unk0'
149:src/st/rno0/unk_48100.c:73: structure has no m

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
extern void (*g_api_CheckCollision)(s32 x, s32 y, Collider* res, s32 unk);
extern void InitializeEntity(u16[]);
extern void MoveEntity(void);
extern void PlaySfxPositional(s32);
extern void EntityExplosion(Entity*);

void EntityJackOBonesJack(Entity* self) {
    Collider sp10;
    s32 var_a0;
    s32 var_a1;
    s32 var_v1;

    if (self->step == 0) {
        InitializeEntity(D_us_80180B4C);
        if (self->params != 0) {
            self->palette++;
        }
        self->animCurFrame = 0x15;
        self->drawFlags |= 4;
        if (self->params != 0) {
            var_a1 = 0x40000;
            var_a0 = 0x10000;
        } else {
            var_a1 = -0x10000;
            var_a0 = 0x28000;
        }
        if (self->facingLeft) {
            self->velocityX = var_a0;
        } else {
            self->velocityX = -var_a0;
        }
        self->velocityY = var_a1;
    }
    MoveEntity();
    self->velocityY += 0x3000;
    self->rotate -= 0x40;
    g_api_CheckCollision(self->posX.i.hi, self->posY.i.hi + 5, &sp10, 0);
    if (sp10.unk0 & 1) {
        PlaySfxPositional(0x6A5);
        var_v1 = self->velocityY;
        if (var_v1 < 0) {
            var_v1 = -var_v1;
        }
        self->ext.jackoBones.bouncesDone++;
        self->velocityY = -var_v1;
        self->posY.i.hi += sp10.unk18;
        if (self->params != 0) {
            self->velocityY = 0xFFF90000 / self->ext.jackoBones.bouncesDone;
        } else {
            var_v1 = -var_v1;
            if (var_v1 < 0) {
                var_v1 += 0xF;
            }
            self->velocityY = -var_v1 - (var_v1 >> 4);
        }
    }
    g_api_CheckCollision(self->posX.i.hi, self->posY.i.hi - 5, &sp10, 0);
    if (sp10.unk0 & 1) {
        var_v1 = self->velocityY;
        if (var_v1 < 0) {
            var_v1 = -var_v1;
        }
        self->posY.i.hi += sp10.unk20;
        self->velocityY = var_v1;
    }
    if (self->velocityX > 0) {
        var_a0 = self->posX.i.hi + 5;
    } else {
        var_a0 = self->posX.i.hi - 5;
    }
    g_api_CheckCollision(var_a0, self->posY.i.hi, &sp10, 0);
    if (sp10.unk0 & 1) {
        self->velocityX = -self->velocityX;
    }
    if (self->params != 0 && self->ext.jackoBones.bouncesDone >= 9) {
        self->flags |= 0x100;
    }
    if (self->flags & 0x100) {
        self->entityId = 2;
        self->drawFlags = 0;
        self->pfnUpdate = EntityExplosion;
        self->params = 0;
        self->step = 0;
    }
}