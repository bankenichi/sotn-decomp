/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/BO6:func_us_801BB5BC
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo6/us_39144.c
   verdict: BUILD FAILED:
41:src/boss/bo6/us_39144.c:553: conflicting types for `BO6_RicCreateEntFactoryFromEntity'
42:src/boss/bo6/us_39144.c:209: previous declaration of `BO6_RicCreateEntFactoryFromEntity'
43-[41/243] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/bomar.map -T build/us/bomar.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.bomar.txt -T build/us/

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
#include <game.h>
extern u8 D_us_80181524[];

s32 func_us_801BB5BC(Entity* self, s32 arg1, s32 arg2) {
    s32 temp_a0;
    s32 temp_v0;
    s32 temp_v1;
    s32 var_t1;
    s32 var_t2;
    u8* tablePtr;
    u8 temp_v0_2;
    u8 temp_v0_3;
    u8 lowByte;
    s32 temp_v0_4;

    // stepCounter is unk06, inside posY (offset 0x04, f32, 4 bytes)
    u8 stepCounter = ((u8*)&self->posY)[2];
    var_t2 = 0;

    if (stepCounter >= 6U) {
        ((u8*)&self->posY)[2] = 0;
        var_t2 = -1;
    }

    stepCounter = ((u8*)&self->posY)[2];
    var_t1 = 6;
    tablePtr = &D_us_80181524[stepCounter * 8];

    if (stepCounter >= 3U) {
        var_t1 = 4;
    }

    temp_a0 = arg1 - var_t1;
    temp_v0 = arg2 - var_t1;
    temp_v1 = arg1 + var_t1;

    // unk0A is inside velocityX (offset 0x08, s32, 4 bytes)
    ((s16*)&self->velocityX)[1] = (s16)temp_v0;
    // unk16 is palette (offset 0x16, u16)
    self->palette = (u16)temp_v0;
    // unk08 is velocityX (offset 0x08, s32)
    self->velocityX = (s32)(s16)temp_a0;
    // unk14 is facingLeft (offset 0x14, u16)
    self->facingLeft = (u16)temp_v1;
    // unk20 is rotPivotX (offset 0x20, s16)
    self->rotPivotX = (s16)temp_a0;
    // unk22 is rotPivotY (offset 0x22, s16)
    self->rotPivotY = (s16)(arg2 + var_t1);
    // unk2C is step (offset 0x2C, u16)
    self->step = (u16)temp_v1;
    // unk2E is step_s (offset 0x2E, u16)
    self->step_s = (u16)(arg2 + var_t1);

    // Read table values and write to entity fields
    temp_v0_2 = tablePtr[0];
    // unk0C is velocityY (offset 0x0C, s32, store low byte)
    ((u8*)&self->velocityY)[0] = temp_v0_2;

    temp_v0_3 = tablePtr[1];
    // unk0D is inside velocityY (offset 0x0D, store high byte of lower 16 bits)
    ((u8*)&self->velocityY)[1] = temp_v0_3;

    temp_v0_2 = tablePtr[2];
    // unk18 is blendMode (offset 0x18, u8)
    self->blendMode = temp_v0_2;

    temp_v0_3 = tablePtr[3];
    // unk19 is drawFlags (offset 0x19, u8)
    self->drawFlags = temp_v0_3;

    temp_v0_2 = tablePtr[4];
    // unk24 is zPriority (offset 0x24, u16, store low byte)
    ((u8*)&self->zPriority)[0] = temp_v0_2;

    temp_v0_3 = tablePtr[5];
    // unk25 is inside zPriority (offset 0x25, store high byte)
    ((u8*)&self->zPriority)[1] = temp_v0_3;

    temp_v0_2 = tablePtr[6];
    // unk30 is params (offset 0x30, u16, store low byte)
    ((u8*)&self->params)[0] = temp_v0_2;

    temp_v0_3 = tablePtr[7];
    // unk31 is inside params (offset 0x31, store high byte)
    ((u8*)&self->params)[1] = temp_v0_3;

    // unk12 is hitboxOffY (offset 0x12, s16, store low byte)
    lowByte = ((u8*)&self->hitboxOffY)[0];
    lowByte += 1;
    ((u8*)&self->hitboxOffY)[0] = lowByte;

    // Check low bit
    temp_v0_4 = lowByte & 1;
    if (temp_v0_4 == 0) {
        // Increment stepCounter (inside posY)
        ((u8*)&self->posY)[2] = stepCounter + 1;
    }

    return var_t2;
}