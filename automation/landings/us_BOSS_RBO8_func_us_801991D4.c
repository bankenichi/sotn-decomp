/* VERIFIED LANDING SNAPSHOT. Kept on purpose.
   record : us:BOSS/RBO8:func_us_801991D4
   attempt: 2/4
   model  : mimo-v2.5-free
   origin : src/boss/rbo8/unk_15868.c
   asm    : boss/rbo8/nonmatchings/unk_15868
   proof  : "build/us/RBO8.BIN sha1=6f80107a6fe58c0ec18ffd504c911f01ddfb3cfe verified against config/check.us.sha"
   content: exact stub replacement block

   This file is recovery evidence, not another build source.
   Replace the named INCLUDE_ASM stub with the block below
   only when recovering the verified landing. Never overwrite
   this snapshot; a later result gets a numeric suffix. */
/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit D_us_80180A98;

void func_us_801991D4(Entity* self) {
    if (self->step == 0) {
        InitializeEntity(D_us_80180A98);
        return;
    }
    DestroyEntity(self);
}