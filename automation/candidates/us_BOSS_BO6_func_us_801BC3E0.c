/* PERMUTER SEED -- compiled and linked, bytes differ by exactly -4 (one
   instruction SHORT of the original).
   record : us:BOSS/BO6:func_us_801BC3E0
   source : automation/logs/gen/func_us_801BC3E0-attempt2.c plus the five
            extern declarations it was missing (see the comment below).
   The externs were the BUILD blocker and are correct; what remains is a
   codegen shape difference worth one instruction. Do NOT apply as-is. */
// These four are FLAT scalar externs, not RIC.field accesses, and the assembly
// proves it: func_us_801BC3E0.s gives each its own lui/%lo pair, consumed
// immediately and never reused as a base. Contrast the g_Ric + 0x394 block a few
// lines below, where the base IS hoisted once and reused for both the load and
// the store. That is the rule already documented at richter.c:133.
//
// All four are real splat symbols in config/symbols.us.bobo6.txt; RIC_posX_i_hi
// is 0x800762DA, which is RIC_step - 0x2A, exactly Entity.step (0x2C) minus
// posX+2. So this was a MISSING DECLARATION, like RIC_step above, not a name to
// be rewritten as RIC.posX.i.hi.
extern s16 RIC_posX_i_hi;
extern s16 RIC_posY_i_hi;
extern u16 RIC_facingLeft;
extern s16 RIC_animCurFrame;
extern EInit D_us_80180448;   // bo6/e_init.c:53

// Handles Richter boss entity initialization and hitbox updates based on animation frame
// Called when RIC_step == 0x1B (specific boss phase)
void func_us_801BC3E0(Entity* entity) {
        u16 step;
    // Check if Richter is in the correct step (0x1B)
    if (RIC_step != 0x1B) {
        DestroyEntity(entity);
        return;
    }

    // Copy Richter's position (high word of fixed-point coordinates)
    entity->posX.i.hi = RIC_posX_i_hi;  // offset 0x02
    entity->posY.i.hi = RIC_posY_i_hi;  // offset 0x06

    step = entity->step;
    // Copy facing direction (always executed, delay slot of branch)
    entity->facingLeft = RIC_facingLeft;  // offset 0x14

    // Initialize entity on first step
    if (step == 0) {
        InitializeEntity(&D_us_80180448);
        entity->flags = 0x18000000;      // offset 0x34: set specific flags
        entity->hitboxOffX = 0x14;       // offset 0x10: hitbox X offset
        entity->hitboxHeight = 9;        // offset 0x47: hitbox height
        entity->hitboxWidth = 9;         // offset 0x46: hitbox width
        entity->step = 1;                // offset 0x2C: advance step
    }

    // Adjust hitbox Y offset based on animation frame
    // Frame 0x8C: hitbox at Y offset 0
    if (RIC_animCurFrame == 0x8C) {
        entity->hitboxOffY = 0;          // offset 0x12
    }
    // Frame 0x8D: hitbox at Y offset 0xC
    if (RIC_animCurFrame == 0x8D) {
        entity->hitboxOffY = 0xC;        // offset 0x12
    }

    // Update Richter's state flags based on entity hit status
    // g_Ric + 0x394 is a u16 flag field (accessed via lhu/sh in asm)
    if (entity->hitFlags != 0) {         // offset 0x48: entity was hit
        u16* ric_flag = (u16*)((char*)&g_Ric + 0x394);
        *ric_flag |= 0x80;               // Set bit 7
    } else {
        u16* ric_flag = (u16*)((char*)&g_Ric + 0x394);
        *ric_flag &= 0xFF7F;             // Clear bit 7
    }
    entity->hitFlags = 0;                // Clear entity hit flag
}
