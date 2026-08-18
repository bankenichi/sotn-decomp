/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/BO6:func_us_801BC4F8
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_39144.c
   verdict: quality reject: 1 raw byte-pointer cast(s) like `*(u16*)((u8*)p + N)`; use the real struct and named members instead

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
extern u16 D_us_80180424;

extern u16 RIC_step;
extern s16 RIC_posX_i_hi;
extern s16 RIC_posY_i_hi;
extern u16 RIC_facingLeft;
extern s16 RIC_pose;
extern void DestroyEntity(Entity* entity);

// Richter tracking entity in BO6 fight; follows player position, self-destructs when pose ends
void func_us_801BC4F8(Entity* entity) {
    if (RIC_step == 0x19) {
        entity->posX.i.hi = (u16)RIC_posX_i_hi;
        entity->posY.i.hi = (u16)RIC_posY_i_hi;
        entity->facingLeft = RIC_facingLeft;
        if (entity->step == 0) {
            InitializeEntity(&D_us_80180424);
            entity->flags = 0x18000000;
            entity->hitboxHeight = 0x14;
            entity->hitboxWidth = 0x14;
            entity->hitboxHeight = 0xC;
            entity->hitboxWidth = 0xC;
            entity->hitboxOffY = 0;
            entity->hitboxOffX = 0;
            // Entity offset 0xB0: ext + 0x34, no named variant for BO6
            *(s16*)((u8*)entity + 0xB0) = 0x11;
            entity->step++;
        }
        if ((u16)RIC_pose < 0x13) {
            return;
        }
    }
    DestroyEntity(entity);
}