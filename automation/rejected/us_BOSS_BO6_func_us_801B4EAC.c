/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:func_us_801B4EAC
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/richter.c
   verdict: BUILD FAILED:
40:src/boss/bo6/richter.c:24: `RIC_velocityY' undeclared (first use this function)
41:src/boss/bo6/richter.c:24: (Each undeclared identifier is reported only once
42:src/boss/bo6/richter.c:24: for each function it appears in.)
43:src/boss/bo6/richter.c:40: `RIC_velocityX' undeclared (first use this function)
44-src/boss/bo6/richter.c: At top level:
45:src/boss/bo6/richter.c:77: `RIC_

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
/* Updates Richter's position based on velocity, clamps to world bounds, and sets vram_flag bits on collision. */
void func_us_801B4EAC(void) {
    s32 old_vram_flag;
    Entity* ricEntity;
    s32* posYPtr;
    s32* posXPtr;
    s32 newPosVal;
    s32 oldPosVal;

    old_vram_flag = g_Ric.vram_flag;
    g_Ric.vram_flag = 0;
    g_Ric.unk04 = old_vram_flag;

    ricEntity = &g_Entities[64];
    posYPtr = (s32*)&ricEntity->posY;
    posXPtr = posYPtr - 1;  /* posX is at offset 0x00, posY at 0x04 */

    /* Update vertical position */
    newPosVal = *posYPtr + RIC_velocityY;
    *posYPtr = newPosVal;

    /* Clamp to upper vertical bound and set bit 0 if exceeded */
    if (newPosVal > 0xB2FFFF) {
        *posYPtr = 0xB30000;
        g_Ric.vram_flag |= 1;
    }

    /* Clamp to lower vertical bound and set bit 1 if exceeded */
    if (*posYPtr <= 0x280000) {
        *posYPtr = 0x280000;
        g_Ric.vram_flag |= 2;
    }

    /* Update horizontal position */
    oldPosVal = *posXPtr + RIC_velocityX;
    *posXPtr = oldPosVal;

    /* Clamp to right horizontal bound and set bit 2 if exceeded */
    if (oldPosVal > 0xF7FFFF) {
        *posXPtr = 0xF80000;
        g_Ric.vram_flag |= 4;
    }

    /* Clamp to left horizontal bound and set bit 3 if exceeded */
    if (*posXPtr <= 0x80000) {
        *posXPtr = 0x80000;
        g_Ric.vram_flag |= 8;
    }
}