/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO0:func_us_801B6520
   attempt: 3/4
   model  : opencode/nemotron-3-ultra-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
--- build tail ---
  ✅ F_RBO0   ✅ RBO3     ✅ F_RBO3   ✅ RBO5     ✅ F_RBO5
  ✅
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
s32 func_us_801B6520(s32 arg0, s32 arg1, s32 arg2, s32 arg3)
{
    Entity* entity = g_CurrentEntity;
    s32 sum = 0;

    /* Check four fields in the entity's ext data (VenusWeedFlower layout at 0x7C+):
     * 0x88 = ext+0x0C (unkC), 0x8C = ext+0x10 (triggerAttack),
     * 0x80 = ext+0x04 (unk4), 0x84 = ext+0x08 (unk8).
     * Each 32-bit argument is split into two s16 halves (lo/hi) and passed to the helper. */
    sum += func_us_801B163C((void*)((u8*)entity + 0x88), (s16)arg2, (s16)(arg2 >> 16));
    sum += func_us_801B163C((void*)((u8*)entity + 0x8C), (s16)arg3, (s16)(arg3 >> 16));
    sum += func_us_801B163C((void*)((u8*)entity + 0x80), (s16)arg0, (s16)(arg0 >> 16));
    sum += func_us_801B163C((void*)((u8*)entity + 0x84), (s16)arg1, (s16)(arg1 >> 16));

    /* Return 1 if all four checks succeeded (sum == 4), else 0.
     * Assembly: xori sum,4 then sltiu v0,sum,1 (unsigned) -> v0 = (sum^4)==0. */
    return ((u32)(sum ^ 4) < 1);
}