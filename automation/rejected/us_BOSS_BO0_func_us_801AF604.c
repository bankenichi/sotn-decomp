/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801AF604
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: BUILD FAILED:
37:src/boss/bo0/2D26C.c:68: structure has no member named `unkAA'
38:src/boss/bo0/2D26C.c:99: structure has no member named `unkAA'
39:src/boss/bo0/2D26C.c:105: structure has no member named `unkAA'
40-[36/155] psx cc src/boss/bo4/unk_46E7C.c
41-[37/155] psx cc src/dra/save_mgr.c

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
extern s32 D_us_80180BA8[];
extern Entity g_Entities_224[];
extern u8 D_us_801806E4[];
extern s32 D_us_80180D74[];
extern u8 D_us_80180D68[];
extern u16 PLAYER_posY_i_hi;
extern u16 PLAYER_posX_i_hi;

void func_us_801AF604(Entity* self) {
    Entity* newEntity;
    s16 angle;
    s16 temp;
    u16 step;

    if (D_us_80180BA8[0] != 0) {
        self->flags |= 0x100;
    }

    if (self->flags & 0x100) {
        PlaySfxPositional(0x655);
        newEntity = AllocEntity(&g_Entities_224[0], &g_Entities_224[230]);
        if (newEntity != NULL) {
            CreateEntityFromEntity(0x47, self, newEntity);
            newEntity->params = 2;
        }
        DestroyEntity(self);
        return;
    }

    step = self->step;
    switch (step) {
    case 0:
        InitializeEntity(D_us_801806E4);
        self->hitboxState = 0;
        self->hitboxOffY = -1;
        self->drawFlags |= 8;
        self->ext.player.unkAA = ((Random() & 0x3F) * 0x10) + 0x200;
        if (self->params != 0) {
            self->step = 2;
            self->hitboxState = 0;
            self->zPriority -= 1;
            self->blendMode |= 0x30;
            return;
        }
        newEntity = AllocEntity(&g_Entities_224[0], &g_Entities_224[230]);
        if (newEntity != NULL) {
            CreateEntityFromEntity(0x2F, self, newEntity);
            newEntity->params = 1;
            newEntity->ext.player.unkA4 = (s32)self;
        }
        return;

    case 1:
        if (self->opacity < 0x80) {
            self->hitboxState = 0;
            self->opacity += 4;
        } else {
            self->hitboxState = 3;
        }
        AnimateEntity(D_us_80180D74, self);
        MoveEntity();
        if (self->velocityX > 0) {
            self->facingLeft = 1;
        } else {
            self->facingLeft = 0;
        }
        angle = func_us_801AD26C(
            8, self->ext.player.unkAA,
            ratan2(
                -(((s16)PLAYER_posY_i_hi - (s16)self->posY.i.hi) - 0x20),
                (s16)PLAYER_posX_i_hi - (s16)self->posX.i.hi));
        self->velocityX = rcos(angle) * 0x10;
        self->velocityY = -(rsin(angle) * 0x10);
        self->ext.player.unkAA = angle;
        return;

    case 2:
        AnimateEntity(D_us_80180D68, self);
        newEntity = (Entity*)self->ext.player.unkA4;
        self->posX.i.hi = newEntity->posX.i.hi;
        self->posY.i.hi = newEntity->posY.i.hi;
        self->opacity = newEntity->opacity;
        if (newEntity->entityId == 0) {
            DestroyEntity(self);
        }
        break;
    }
}