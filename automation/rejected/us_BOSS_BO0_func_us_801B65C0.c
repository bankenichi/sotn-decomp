/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B65C0
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
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
extern u16 D_us_801CE56C;

s32 func_us_801B65C0(u16 arg0, Entity* arg1, Entity* arg2, s8 arg3) {
    Entity* var_a0;
    s16 temp_a1;
    s16 temp_s4_2;
    s16 temp_s4_4;
    s16 temp_s5;
    s16 temp_s5_2;
    s16 temp_s6;
    s16 temp_s6_2;
    s16 temp_s7_3;
    s16 var_s2_3;
    s32 temp_s0;
    s32 temp_s0_2;
    s32 temp_s4;
    s32 temp_s4_3;
    s32 temp_s7;
    s32 temp_s7_2;
    s32 var_s2;
    s32 var_s2_2;
    s32 var_v1;
    s32 var_v1_2;
    u16 var_s0;
    u16 var_s0_2;
    u16 var_s0_3;
    u16 var_s0_4;
    u8* var_fp;
    u8* var_fp_2;
    u8 temp_a0;
    Entity* temp_s1;
    s16 angle;
    s16 angle2;
    s16 angle3;
    s16 angle4;
    s16 angle5;
    s16 angle6;
    s16 angle7;
    s16 angle8;
    s16 angle9;
    s16 angle10;
    s16 angle11;
    s16 angle12;
    s16 angle13;
    s16 angle14;
    s16 angle15;
    s16 angle16;
    s16 angle17;
    s16 angle18;
    s16 angle