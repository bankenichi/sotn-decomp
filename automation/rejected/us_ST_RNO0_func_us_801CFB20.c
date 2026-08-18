/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:func_us_801CFB20
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/unk_4F968.c
   verdict: BUILD FAILED:
154:src/st/rno0/unk_4F968.c:39: union has no member named `unk80'
155:src/st/rno0/unk_4F968.c:40: union has no member named `unkAA'
156:src/st/rno0/unk_4F968.c:72: union has no member named `unkAA'
157-[153/297] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/stmad.map -T build/us/stmad.ld -T config/undefined_syms.beta.txt -T build/us/config/undefined_funcs_auto.stmad

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
s32 func_us_801CFB20(Entity* arg0, Entity* arg2, u16* arg3) {
    s16 temp_a1;
    s16 var_a1;
    s32 var_a0;
    s32 var_a1_2;
    s32 var_v0;
    u16* var_a0_2;
    s16 var_a1_3;
    s32 var_a2;
    u8 temp_v1;

    temp_a1 = g_CurrentEntity->posX.i.hi;
    if (g_CurrentEntity->facingLeft != 0) {
        var_a1 = temp_a1 + 2;
    } else {
        var_a1 = temp_a1 - 2;
    }
    var_a0 = var_a1 - arg0->posX.i.hi;
    var_a1_2 = var_a1 - arg2->posX.i.hi;
    if (g_CurrentEntity->facingLeft != 0) {
        var_a1_2 = -var_a1_2;
        var_a0 = -var_a0;
    }
    if ((arg2->ext.unk80 == 0) || (var_a1_2 >= -8) || (var_v0 = 1, ((var_a0 < 9) != 0))) {
        temp_v1 = g_CurrentEntity->ext.unkAA;
        if (temp_v1 != 1) {
            if ((s32)temp_v1 < 2) {
                if (temp_v1 != 0) {
                    return 0;
                }
                StepTowards(arg3 + 1, -0x280, 0x20);
                var_a0_2 = arg3;
                var_a1_3 = -0xC0;
                var_a2 = 0x18;
                goto block_16;
            }
            if (temp_v1 != 2) {
                return 0;
            }
            var_v0 = var_a1_2 < -7;
            if (var_a1_2 < -8) {
                *arg3 += 0x14;
                var_v0 = var_a1_2 < -7;
            }
            if (var_v0 == 0) {
                *arg3 -= 0x14;
            }
            StepTowards(arg3 + 1, (s16)*arg3, 0x20);
            goto block_23;
        }
        var_a0_2 = arg3 + 1;
        var_a1_3 = (s16)*arg3;
        var_a2 = 0x20;
block_16:
        var_v0 = 0;
        if (StepTowards(var_a0_2, var_a1_3, var_a2) != 0) {
            g_CurrentEntity->ext.unkAA += 1;
block_23:
            var_v0 = 0;
        }
        return var_v0;
    }
    return var_v0;
}