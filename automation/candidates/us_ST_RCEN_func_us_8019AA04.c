/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RCEN:func_us_8019AA04
   attempt: 4/4
   model  : opencode/nemotron-3-ultra-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:

   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
void func_us_8019AA04(s32 arg0) {
        s32 dist_x;
        s32 dy_raw;
        s32 dy_abs;
        s32 dy_adj;
        s32 dist;
        s32 vol_raw;
        s32 vol;
    Entity* entity = g_CurrentEntity;

    // Horizontal distance from screen center (0x80) in fixed-point integer pixels
    s32 dx_raw = entity->posX.i.hi - 0x80;
    s32 dx_abs = dx_raw >= 0 ? dx_raw : -dx_raw;

    // Pan: (|dx| - 0x20) / 32, clamped to [-8, 8], sign follows dx_raw
    s32 pan = (dx_abs - 0x20) >> 5;            // arithmetic shift = divide by 32
    if (pan > 8) pan = 8;
    else if (pan < 0) pan = 0;
    if (dx_raw < 0) pan = -pan;

    // Volume distance components
    dist_x = dx_abs - 0x60;
    dy_raw = entity->posY.i.hi - 0x80;
    dy_abs = dy_raw >= 0 ? dy_raw : -dy_raw;
    dy_adj = dy_abs - 0x70;

    // Total distance: horizontal + positive vertical excess
    dist = dist_x;
    if (dy_adj > 0) dist += dy_adj;

    // Volume raw: (dist >> 1) if dist >= 0 (as s16), else 0
    // Assembly checks bit 15 of dist via sll 16 / bgez, so 16-bit sign matters.
    // Dist fits in 16 bits here, so 32-bit compare is equivalent.
    vol_raw = (dist >= 0) ? (dist >> 1) : 0;

    // Final volume: 0x40 - vol_raw, play only if > 0
    vol = 0x40 - vol_raw;
    if (vol > 0) {
        // API takes s32 args; low 16 bits of arg0/pan are sign-extended in asm
        g_api_PlaySfxVolPan((s16)arg0, vol, (s16)pan);
    }
}