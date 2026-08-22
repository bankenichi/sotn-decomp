/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:ST/RCEN:func_us_801ABD24
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rcen/unk_2BD24.c
   verdict: quality reject: candidate is not usable C: unbalanced braces: 2 unclosed `{`

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
void func_us_801ABD24(Entity* self) {
    s32 sp10;
    MATRIX* sp18;
    s32* sp20;
    s32* sp28;
    u8* sp30;
    s32* sp38;
    Primitive* prim;
    Primitive* prim2;
    s16 temp_s0_2;
    s16 temp_s1_2;
    s16 temp_s3;
    s16 temp_v0;
    s32 temp_a3;
    s32 temp_s0;
    s32 temp_s0_3;
    s32 temp_s1;
    s32 temp_s3_2;
    s32 temp_t0;
    s32 temp_v1_4;
    u16* var_a1;
    u16* var_a1_2;
    u16* var_fp;
    u16* var_s5;
    u16 temp_v0_2;
    u16 temp_v0_3;
    u16 temp_v0_4;
    u16 temp_v1;
    u16 temp_v1_2;
    u16 temp_v1_3;
    u16 var_v0;
    u16 var_v0_2;
    u16 var_v0_3;
    u16 var_v0_4;
    u8* var_fp_2;
    u8* var_s4;
    u8 temp_v0_5;
    u8 temp_v0_6;
    u8 temp_v0_7;
    u8 temp_v0_8;
    u8 temp_v0_9;
    u8 temp_v0_10;
    u8 temp_v0_11;
    u8 temp_v0_12;
    u8 temp_v0_13;
    u8 temp_v0_14;

    temp_v1 = self->step;
    switch (temp_v1) {
    case 0:
        InitializeEntity(&g_EInitInteractable);
        temp_v0 = g_api_AllocPr