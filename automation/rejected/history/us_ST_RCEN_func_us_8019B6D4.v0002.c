/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RCEN:func_us_8019B6D4
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/e_shaft.c
   verdict: BUILD FAILED:
220:src/st/rcen/e_shaft.c:61: `PrizeDrops' undeclared (first use this function)
221:src/st/rcen/e_shaft.c:61: (Each undeclared identifier is reported only once
222:src/st/rcen/e_shaft.c:61: for each function it appears in.)
223:src/st/rcen/e_shaft.c:67: `D_us_80180844' undeclared (first use this function)
224-src/st/rcen/e_shaft.c: At top level:
225:src/st/rcen/e_shaft.c:105: `PrizeDrops' used prior to declaration
226-[219/353] psx cc src/st/rno3/layers.c
227-[220/353] psx cc src/st/rno3/graphics_banks.c

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

void func_us_8019B6D4(Entity* self) {
    s16 angle;
    s32 dx;
    s32 dy;
    s32 dist;

    switch (self->step) {
    case 0:
        InitializeEntity(D_us_80180570);
        self->blendMode = 0x30;
        self->drawFlags = 8;
        self->opacity = 0x60;
        self->animCurFrame = 0x23;
        break;

    case 1:
        if (PrizeDrops & 1) {
            self->step++;
        }
        break;

    case 2:
        if (AnimateEntity(D_us_80180844, self) == 0) {
            SetStep(3);
        }
        break;

    case 3:
        MoveEntity();
        dx = g_Entities[0].posX.i.hi - self->posX.i.hi;
        dy = g_Entities[0].posY.i.hi - self->posY.i.hi;
        angle = ratan2(dy, dx);
        self->velocityX = rcos(angle) << 4;
        self->velocityY = rsin(angle) << 4;
        dist = SquareRoot0(dx * dx + dy * dy);
        if (dist < 2) {
            self->posX.i.hi = g_Entities[0].posX.i.hi;
            self->posY.i.hi = g_Entities[0].posY.i.hi;
            self->step++;
        }
        break;

    case 4:
        self->opacity -= 8;
        if (self->opacity < 0) {
            PrizeDrops |= 2;
            DestroyEntity(self);
        }
        break;
    }
}