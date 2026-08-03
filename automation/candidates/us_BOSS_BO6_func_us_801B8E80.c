/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO6:func_us_801B8E80
   attempt: 4/4
   model  : opencode/nemotron-3-ultra-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
--- build tail ---
  ✅ F_RBO0   ✅ RBO3     ✅ F_RBO3   ✅ RBO5     ✅ F_RBO5
  ✅
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
extern void BO6_RicCreateEntFactoryFromEntity(Entity* entity, u32 arg1, s32 arg2);
extern u16 RIC_facingLeft;     /* 0x800762EC */
extern u16 RIC_posX_i_hi;      /* 0x800762DA */
extern u16 RIC_posY_i_hi;      /* 0x800762DE */
extern s32 RIC_velocityX;
extern s32 RIC_velocityY;
extern Entity* g_CurrentEntity;
extern void (*g_api_func_80102CD8)(s32 arg0);
extern void (*g_api_PlaySfx)(s32 sfxId);

/* Ric boss projectile spawn helper: adjusts spawn origin based on facing,
 * creates an entity factory, plays SFX if flagged, and optionally halts velocity. */
void func_us_801B8E80(s32 arg0)
{
    s32 offsetX;   /* s0: horizontal spawn offset (±3) */
    s32 flags;     /* s1: copy of arg0 */

    offsetX = 3;
    /* Assembly uses beqz: if facingLeft == 0, offsetX = -3 */
    if (RIC_facingLeft == 0) {
        offsetX = -3;
    }

    /* Temporarily shift spawn position up and toward facing direction */
    RIC_posY_i_hi -= 0x10;
    RIC_posX_i_hi += offsetX;

    /* Create entity factory at adjusted position */
    BO6_RicCreateEntFactoryFromEntity(g_CurrentEntity, 0x10004, 0);

    /* Restore original spawn position */
    RIC_posY_i_hi += 0x10;
    RIC_posX_i_hi -= offsetX;

    flags = arg0;
    /* Bit 0: play spawn SFX and call api func */
    if (flags & 1) {
        g_api_func_80102CD8(3);
        g_api_PlaySfx(0x644);
    }
    /* Bit 1: zero velocity */
    if (flags & 2) {
        RIC_velocityX = 0;
        RIC_velocityY = 0;
    }
}