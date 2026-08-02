/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RCEN:func_us_8019AA04
   attempt: 2/4
   model  : opencode/nemotron-3-ultra-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
--- build tail ---
  ✅ F_RBO0   ✅ RBO3     ✅ F_RBO3   ✅ RBO5     ✅ F_RBO5
  ✅
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
void func_us_8019AA04(s16 sfxId) {
        s16 pan;
        s32 dx_vol;
        s32 dy;
        s32 abs_dy;
        s32 dy_vol;
        s32 dist;
        s32 volume;
    Entity* entity = g_CurrentEntity;
    
    // Get high 16 bits of fixed-point position (16.16 format)
    s16 posX_hi = entity->posX.i.hi;
    s16 posY_hi = entity->posY.i.hi;

    // --- Pan calculation (horizontal distance from 0x80) ---
    s32 dx = posX_hi - 0x80;
    s32 abs_dx = dx < 0 ? -dx : dx;
    s32 pan_raw = (abs_dx - 0x20) >> 5;  // Divide by 32, arithmetic shift
    
    // Clamp to [0, 8]
    if (pan_raw < 0) pan_raw = 0;
    else if (pan_raw > 8) pan_raw = 8;
    
    // Apply sign based on original direction
    pan = (dx < 0) ? -pan_raw : pan_raw;

    // --- Volume calculation (distance from 0x80,0x80 with deadzones) ---
    dx_vol = abs_dx - 0x60;
    
    dy = posY_hi - 0x80;
    abs_dy = dy < 0 ? -dy : dy;
    dy_vol = abs_dy - 0x70;

    // Combined distance: dx_vol + max(dy_vol, 0)
    dist = dx_vol;
    if (dy_vol > 0) dist += dy_vol;

    // Volume = 64 - dist/2 (if dist >= 0), else max volume 64
    if (dist >= 0) {
        volume = 0x40 - (dist >> 1);  // Arithmetic shift right 1
    } else {
        volume = 0x40;
    }

    // Play sound if audible
    if (volume > 0) {
        g_api_PlaySfxVolPan(sfxId, volume, pan);
    }
}