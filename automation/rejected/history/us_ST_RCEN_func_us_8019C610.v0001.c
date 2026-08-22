/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:ST/RCEN:func_us_8019C610
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/e_shaft.c
   verdict: quality reject: `Entity` has no member `unk82`; 0x82 falls inside `ext` (0x7C)

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
void func_us_8019C610(Entity* self) {
    s32 angle;
    Entity* newEntity;

    if (!(PrizeDrops & 4)) {
        if (self->step == 0) {
            InitializeEntity(D_us_80180588);
            angle = self->unk82;
            self->palette = 0x2E4;
            self->drawFlags = 0xC;
            self->rotate = angle + 0x400;
            self->velocityX = (rcos(angle) * 3) << 4;
            self->velocityY = (rsin(angle) * 3) << 4;
            self->blendMode = 0x30;
        }
        MoveEntity();
        angle = self->unk82;
        self->velocityX += (rcos(angle) << 10) >> 12;
        self->velocityY += (rsin(angle) << 10) >> 12;
        if (self->params != 0 && self->pose == 7) {
            newEntity = AllocEntity(&g_Entities[112], &g_Entities[112] + 0x3AC0);
            if (newEntity != NULL) {
                CreateEntityFromEntity(0x1C, self, newEntity);
                newEntity->zPriority = self->zPriority;
                newEntity->params = self->params - 1;
                newEntity->unk82 = self->unk82;
            }
        }
        self->opacity += 0xFE;
        if (self->opacity == 0 || AnimateEntity(D_us_80180874, self) == 0) {
            DestroyEntity(self);
        }
    } else {
        DestroyEntity(self);
    }
}