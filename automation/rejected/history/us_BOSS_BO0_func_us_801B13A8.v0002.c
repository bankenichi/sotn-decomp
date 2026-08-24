/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B13A8
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: BUILD FAILED:
110:src/boss/bo0/2D26C.c:48: `D_us_801A5ED4' undeclared (first use this function)
111:src/boss/bo0/2D26C.c:48: (Each undeclared identifier is reported only once
112:src/boss/bo0/2D26C.c:48: for each function it appears in.)
113-[109/245] psx cc src/st/np3/stage_data.c
114-[110/245] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/stno3.map -T build/us/stno3.ld -T confi

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
extern Entity* g_CurrentEntity;

/* Reads boss animation frame data, calculates hitbox dimensions and position offsets,
   then applies them to the target entity based on facing direction. */
/* Mechanical symbol repair from escalation_triage.py. */
extern s32 D_us_801A5ED4[]; /* retained BOSS/BO0 data asm/us/boss/bo0/data/2614.data.s, size 0x88 */

void func_us_801B13A8(Entity* target) {
    Entity* self = g_CurrentEntity;
    u16 unk5A = self->unk5A;
    s16 animCurFrame = self->animCurFrame;
    s32 var_t3 = (unk5A & 1) * 0x7F;
    s32 var_t4 = ((unk5A & 2) >> 1) * 0x7F;
    void* tablePtr = D_us_801A5ED4[animCurFrame];
    u16 posXHi;
    u16 posYHi;
    u16 offset_x;
    u16 temp_t1;
    u16 temp_t2;
    u16 velYHi;
    u16 temp_v1;
    u16 newPosXHi;
    u16 newPosYHi;
    u8 byte0;
    u8 byte1;
    u8 byte2;
    u8 byte3;
    u8 b0;
    u8 b1;
    u8 b2;
    u8 b3;

    /* Read table data - first halfword is at offset 4 */
    tablePtr = (u8*)tablePtr + 4;
    offset_x = *(u16*)tablePtr;
    tablePtr = (u16*)tablePtr + 1;
    temp_t1 = *(u16*)tablePtr;
    tablePtr = (u16*)tablePtr + 1;
    temp_t2 = *(u16*)tablePtr;
    tablePtr = (u16*)tablePtr + 1;
    velYHi = *(u16*)tablePtr;
    tablePtr = (u16*)tablePtr + 1;
    temp_v1 = *(u16*)tablePtr;
    tablePtr = (u16*)tablePtr + 1;

    /* Adjust multipliers based on table flags */
    if (temp_v1 & 1) {
        var_t3 += 0x7F;
    }
    if (temp_v1 & 2) {
        var_t4 += 0x7F;
    }

    /* Read hitbox dimension bytes */
    byte0 = *(u8*)tablePtr;
    tablePtr = (u8*)tablePtr + 2;
    byte1 = *(u8*)tablePtr;
    tablePtr = (u8*)tablePtr + 2;
    byte2 = *(u8*)tablePtr;
    tablePtr = (u8*)tablePtr + 2;
    byte3 = *(u8*)tablePtr;

    /* Get entity positions (high 16 bits of fixed-point coordinates) */
    posXHi = ((u16*)&self->posX)[1];
    posYHi = ((u16*)&self->posY)[1];

    /* Calculate new position based on facing direction */
    if (self->facingLeft) {
        newPosXHi = posXHi - offset_x;
        newPosYHi = posYHi + temp_t2;
    } else {
        newPosXHi = posXHi + offset_x;
        newPosYHi = posYHi + temp_t2;
    }

    /* Apply position and basic hitbox to target entity */
    target->velocityX = newPosXHi | (newPosYHi << 16);
    target->facingLeft = newPosXHi + temp_t1;
    target->palette = newPosYHi;
    target->rotPivotX = newPosXHi;

    /* Write velocityY high part */
    target->velocityY = (target->velocityY & 0x0000FFFF) | (velYHi << 16);

    /* Apply adjusted hitbox dimensions - same values used in different positions */
    b0 = byte0 + var_t3;
    b1 = byte1 + var_t4;
    b2 = byte2 + var_t3;
    b3 = byte3 + var_t4;

    /* Write to zPriority and velocityY low bytes */
    target->zPriority = (target->zPriority & 0xFF00) | b0;
    target->velocityY = (target->velocityY & 0xFFFFFF00) | b0;

    /* Write drawFlags and velocityY middle byte */
    target->drawFlags = b1;
    target->velocityY = (target->velocityY & 0xFFFF00FF) | (b1 << 8);

    /* Write params low byte and blendMode */
    target->params = (target->params & 0xFF00) | b2;
    target->blendMode = b2;

    /* Write params and zPriority high bytes */
    target->params = (target->params & 0x00FF) | (b3 << 8);
    target->zPriority = (target->zPriority & 0x00FF) | (b3 << 8);
}