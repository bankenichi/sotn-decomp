/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RCEN:func_us_8019AA04
   attempt: 3/4
   model  : opencode/nemotron-3-ultra-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
--- build tail ---
  ✅ F_RBO0   ✅ RBO3     ✅ F_RBO3   ✅ RBO5     ✅ F_RBO5
  ✅
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
void func_us_8019AA04(s16 arg0) {
        s32 a2;
        s32 v1;
        s32 a1_2;
        s32 posY_hi;
        s32 v0_2;
        s32 temp_v0_2;
        s32 v1_2;
        s32 v0_3;
        s32 v0_4;
        s32 a1_3;
    Entity* entity = g_CurrentEntity;
    s32 posX_hi = entity->posX.i.hi;           // offset 2
    s32 a1 = posX_hi - 0x80;                   // posX - 0x80
    s32 v0 = a1;
    if (a1 < 0) v0 = -a1;                      // abs(posX - 0x80)
    v0 = v0 - 0x20;
    a2 = v0 >> 5;
    v1 = (s16)a2;
    if (v1 >= 9) {
        a2 = 8;
    } else if (v1 < 0) {
        a2 = 0;
    }
    if (a1 < 0) a2 = -a2;                      // apply original sign

    // Reload entity (matches reload at 1AA78)
    entity = g_CurrentEntity;
    a1_2 = v0 - 0x60;
    // Wait, v0 at this point is (abs(posX-0x80) - 0x20) >> 5? No!
    // At 1AA80: v0 = (abs(posX-0x80) - 0x20) >> 5? No!
    // At 1AA2C: v0 = v0 - 0x20 (v0 was abs)
    // 1AA30: v0 = v0 >> 5
    // 1AA34: a2 = v0
    // Then at 1AA80: lh v0, 6(v1) - loads posY.i.hi
    // So a1 at 1AA80 is still the original a1? No, a1 was modified?
    // At 1AA1C: a1 = v0 - 0x80 (v0 = posX_hi)
    // a1 is never modified until 1AA80: addiu a1, v0, -0x60 where v0 is abs(posX-0x80) from 1AA74?
    // At 1AA70: addu v0, a1, zero (a1 is posX-0x80)
    // 1AA74: negu v0, v0 (v0 = -(posX-0x80) = 0x80-posX)
    // So at 1AA80: a1 = v0 - 0x60 = (0x80-posX) - 0x60 = 0x20 - posX if posX<0x80? No
    // v0 at 1AA74 is abs(posX_hi - 0x80)
    // So a1 at 1AA80 = abs(posX_hi - 0x80) - 0x60

    posY_hi = entity->posY.i.hi;
    v0_2 = posY_hi - 0x80;
    if (v0_2 < 0) v0_2 = -v0_2;                // abs(posY - 0x80)
    temp_v0_2 = v0_2 - 0x70;
    v1_2 = a1_2;
    if (temp_v0_2 > 0) {
        v1_2 = a1_2 + temp_v0_2;               // abs(posX-0x80)-0x60 + abs(posY-0x80)-0x70
    }

    // Sign extend v1_2 to 32-bit, check sign bit (bit 15)
    v0_3 = v1_2 << 16;
    if (v0_3 >= 0) {                           // v1_2 >= 0 as s16
        v0_4 = v0_3 >> 17;                     // v1_2 >> 1 (arithmetic)
    } else {
        v0_4 = 0;
    }

    a1_3 = 0x40 - v0_4;
    if (a1_3 > 0) {
        // Sign-extend arguments for call
        s32 arg0_se = (s16)arg0;
        s32 a2_se = (s16)a2;
        g_api_PlaySfxVolPan(arg0_se, a1_3, a2_se);
    }
}