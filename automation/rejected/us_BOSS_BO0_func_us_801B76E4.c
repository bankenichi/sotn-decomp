/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B76E4
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/3053C.c
   verdict: quality reject: `Entity` has no member `unk94`; 0x94 falls inside `ext` (0x7C)

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
void func_us_801B76E4(Entity* self) {
    Entity* parentEntity;
    Primitive* prim;
    u16 step_s_val;
    s16 primIndex;
    s32 flagsVal;
    s32 var_v1;

    /* Determine parent entity based on params */
    if (self->params == 0) {
        parentEntity = self - 0x69C / sizeof(Entity);
    } else {
        parentEntity = self - 0x5E0 / sizeof(Entity);
    }

    /* Copy parent's facing and palette */
    self->facingLeft = parentEntity->facingLeft;
    if (parentEntity->palette & 0x8000) {
        self->palette = parentEntity->palette;
    } else if (!(self->flags & 0xF)) {
        self->palette = 0x20B;
    }

    if (self->flags & 0x100) {
        self->hitboxState = 0;
    }

    step_s_val = self->step;
    switch (step_s_val) {
    case 0:
        InitializeEntity(D_us_80180708);
        self->hitPoints = 0x80;
        self->hitboxWidth = 0xC;
        self->hitboxHeight = 0x6;
        self->parent = NULL;
        self->drawFlags |= 4;
        if (self->params != 0) {
            self->animCurFrame = 0x20;
            self->zPriority = D_us_801CE56C - 4;
        } else {
            self->animCurFrame = 0x1F;
            self->zPriority = D_us_801CE56C + 2;
        }
        break;
    case 1:
        if (self->flags & 0x100) {
            self->hitboxState = 0;
            self->step = 2;
            self->step_s = 0;
        }
        break;
    case 2:
        step_s_val = self->step_s;
        switch (step_s_val) {
        case 0:
            MakeExplosions(1, 2);
            /* unk94 is ext+0x18 */
            self->unk94 = 0x100;
            var_v1 = -0x100;
            self->animCurFrame = 0;
            self->scaleY = 0;
            self->scaleX = 0;
            self->drawFlags |= 3;
            self->step_s = self->step_s + 1;
            self->flags = self->flags & var_v1;
            break;
        case 1:
            /* unk94 is ext+0x18 */
            primIndex = self->unk94 - 1;
            /* unk94 is ext+0x18 */
            self->unk94 = primIndex;
            if ((primIndex << 0x10) != 0) {
                /* empty */
            } else {
                self->step_s = self->step_s + 1;
            }
            break;
        case 2:
            self->scaleX = self->scaleX + 2;