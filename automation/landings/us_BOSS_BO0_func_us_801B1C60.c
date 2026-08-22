/* VERIFIED LANDING SNAPSHOT. Kept on purpose.
   record : us:BOSS/BO0:func_us_801B1C60
   source : orchestrator closure of preserved v0004
   origin : src/boss/bo0/3053C.c
   asm    : boss/bo0/nonmatchings/3053C/func_us_801B1C60
   proof  : "build/us/BO0.BIN sha1=c9e00e7555c363d11b6e451403b59d96d3e591af verified against config/check.us.sha; permuter debug base score=0"
   content: exact stub replacement block

   This file is recovery evidence, not another build source.
   Replace the named INCLUDE_ASM stub with the block below
   only when recovering the verified landing. Never overwrite
   this snapshot; a later result gets a numeric suffix. */

s32 func_us_801B1C60(ET_B0_Unk* self) {
    ET_B0_Unk* child = (ET_B0_Unk*)self->parent;
    s32 result1;
    s32 result2;

    func_us_801B163C(&g_CurrentEntity->ext.venusWeed.pad_90, -0x100, 0xC);
    result1 = func_us_801B171C(self, -0x1C0, 0x280, 0x10);
    // CODEGEN: This wrapper makes GCC preserve the target call setup order.
    do {
        result2 = func_us_801B171C(child, -0x380, 0x140, 0x10);
        return (result1 + result2) == 2;
    } while (0);
}
