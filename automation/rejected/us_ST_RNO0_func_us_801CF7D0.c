/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:func_us_801CF7D0
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/e_gorgon.c
   verdict: BUILD FAILED:
98:src/st/rno0/e_gorgon.c:87: union has no member named `unk80'
99:src/st/rno0/e_gorgon.c:88: union has no member named `unkAA'
100:src/st/rno0/e_gorgon.c:116: union has no member named `unkAA'
101-[97/245] psx cc src/st/rno3/layers.c
102-[98/245] psx cc src/st/rno3/graphics_banks.c

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
s32 func_us_801CF7D0(Entity* arg0, Entity* arg2, s16* arg3, void* arg4) {
    s16* var_a0;
    s16 temp_a0;
    s16 temp_v1;
    s16 var_a1;
    s16 var_v0_2;
    s32 temp_v0;
    s32 temp_v1_2;
    s32 var_a3;
    s32 var_t2;
    s32 var_v0;
    u16 temp_a1;
    u16 temp_s1;
    u16 temp_t1;
    u8 temp_v1_3;

    temp_a0 = arg0->posX.i.hi; // unk02 is inside posX (0x00, f32)
    temp_v1 = g_CurrentEntity->posX.i.hi;
    temp_a1 = g_CurrentEntity->facingLeft;
    var_t2 = temp_v1 - arg2->posX.i.hi;
    temp_t1 = *(u16*)arg4;
    temp_s1 = *((u16*)arg4 + 1);
    var_a3 = temp_v1 - temp_a0;
    if (temp_a1 != 0) {
        var_t2 = -var_t2;
        var_a3 = -var_a3;
    }
    temp_v1_2 = -(temp_t1 + 6);
    if (var_a3 < temp_v1_2) {
        temp_v0 = temp_v1_2 - var_a3;
        if (temp_a1 != 0) {
            var_v0_2 = temp_a0 + temp_v0;
        } else {
            var_v0_2 = temp_a0 - temp_v0;
        }
        arg0->posX.i.hi = var_v0_2;
    }
    if ((arg2->ext.unk80 == 0) || ((s32)temp_t1 >= var_t2) || (var_v0 = 1, ((var_a3 < -(s32)temp_t1) == 0))) {
        temp_v1_3 = g_CurrentEntity->ext.unkAA; // ext union, 0x2e bytes in
        if (temp_v1_3 != 1) {
            if ((s32)temp_v1_3 < 2) {
                if (temp_v1_3 != 0) {
                    return 0;
                }
                StepTowards(arg3 + 1, -0x240, (s32)temp_s1);
                var_a0 = arg3;
                var_a1 = 0x1C0;
                goto block_18;
            }
            if (temp_v1_3 != 2) {
                return 0;
            }
            if ((s32)temp_t1 < var_t2) {
                *arg3 -= temp_s1 >> 1;
            }
            if (var_t2 < (s32)temp_t1) {
                *arg3 += temp_s1 >> 1;
            }
            StepTowards(arg3 + 1, (s32)(s16)*arg3, (s32)temp_s1);
            goto block_25;
        }
        var_a0 = arg3 + 1;
        var_a1 = (s16)*arg3;
block_18:
        var_v0 = 0;
        if (StepTowards(var_a0, (s32)var_a1, (s32)temp_s1) != 0) {
            g_CurrentEntity->ext.unkAA += 1;
block_25:
            var_v0 = 0;
        }
        return var_v0;
    }
    return var_v0;
}