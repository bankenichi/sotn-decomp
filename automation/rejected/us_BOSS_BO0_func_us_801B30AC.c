/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B30AC
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/3053C.c
   verdict: quality reject: candidate is not usable C: unbalanced braces: 1 unclosed `{`

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
int rcos(int a);
int rsin(int a);

extern u16 D_us_80181194[];
extern u16 D_us_801CE56C;

void func_us_801B30AC(Entity* self) {
    Entity* entity;
    Entity* child;
    s32 angle;
    s32 angle2;
    s32 posX;
    s32 posY;
    s32 posX2;
    s32 posY2;
    s32 posX3;
    s32 posY3;
    s32 posX4;
    s32 posY4;
    s32 posX5;
    s32 posY5;
    s32 posX6;
    s32 posY6;
    s32 posX7;
    s32 posY7;
    s32 posX8;
    s32 posY8;
    s32 posX9;
    s32 posY9;
    s32 posX10;
    s32 posY10;
    s32 posX11;
    s32 posY11;
    s32 posX12;
    s32 posY12;
    s32 posX13;
    s32 posY13;
    s32 posX14;
    s32 posY14;
    s32 posX15;
    s32 posY15;
    s32 posX16;
    s32 posY16;
    s32 posX17;
    s32 posY17;
    s32 posX18;
    s32 posY18;
    s32 posX19;
    s32 posY19;
    s32 posX20;
    s32 posY20;
    s32 posX21;
    s32 posY21;
    s32 posX22;
    s32 posY22;
    s32 posX2