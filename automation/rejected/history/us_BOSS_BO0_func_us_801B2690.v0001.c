/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B2690
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
extern s32 D_us_801CE5B0;
extern GAME_IMPORT Tilemap g_Tilemap;
extern Entity* g_CurrentEntity;
extern u16 D_us_801CE56C;
int rcos(int a);
int rsin(int a);
long SquareRoot0(long a);
long ratan2(long y, long x);

void func_us_801B2690(Entity* arg0, Entity* arg1, u8 arg2) {
    s32 sp58;
    s32 sp60;
    u16 sp68;
    s16 temp_a0;
    s16 temp_a0_2;
    s16 temp_fp;
    s16 temp_fp_2;
    s16 temp_fp_3;
    s16 temp_s0_2;
    s16 temp_s1_2;
    s16 temp_s3;
    s16 temp_s3_2;
    s16 temp_s3_3;
    s16 temp_s4_2;
    s16 temp_s5_2;
    s16 temp_s6;
    s16 temp_s6_2;
    s16 temp_v0_2;
    s16 temp_v1;
    s16 var_a0;
    s16 var_a0_2;
    s16 var_a0_3;
    s16 var_a0_4;
    s16 var_s1;
    s16 var_s1_2;
    s16 var_s3;
    s16 var_s4;
    s16 var_s4_2;
    s16 var_s5;
    s16 var_s6;
    s16 var_v0;
    s32 temp_s0;
    s32 temp_s0_3;
    s32 temp_s0_4;
    s32 temp_s0_5;
    s32 temp_s0_6;
    s32 temp_s0_7;
    s32 temp_s0_8;
    s32 temp_s4_3;
    s32 temp_s4