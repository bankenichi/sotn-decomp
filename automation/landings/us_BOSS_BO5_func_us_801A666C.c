/* VERIFIED LANDING SNAPSHOT. Kept on purpose.
   record : us:BOSS/BO5:func_us_801A666C
   attempt: 1/4
   model  : mimo-v2.5-free
   origin : src/boss/bo5/unk_25F88.c
   asm    : boss/bo5/nonmatchings/unk_25F88
   proof  : "build/us/BO5.BIN sha1=a90ab719a6db9ff6b72ea1a59a09c0cece69c31a verified against config/check.us.sha"
   content: exact stub replacement block

   This file is recovery evidence, not another build source.
   Replace the named INCLUDE_ASM stub with the block below
   only when recovering the verified landing. Never overwrite
   this snapshot; a later result gets a numeric suffix. */
void func_us_801A666C(Entity* self, s32 arg1) {
    s16 rotPivotX;
    u16 step;
    u16 palette;
    u16 step_s;

    rotPivotX = self->rotPivotX - arg1;
    step = self->step + arg1;
    palette = self->palette - arg1;
    step_s = self->step_s + arg1;
    self->rotPivotX = rotPivotX;
    ((s16*)&self->velocityX)[0] = rotPivotX;
    self->step = step;
    self->facingLeft = step;
    self->palette = palette;
    ((s16*)&self->velocityX)[1] = palette;
    self->step_s = step_s;
    self->rotPivotY = step_s;
}