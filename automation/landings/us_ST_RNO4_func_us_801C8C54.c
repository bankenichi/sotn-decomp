/* VERIFIED LANDING SNAPSHOT. Kept on purpose.
   record : us:ST/RNO4:func_us_801C8C54
   attempt: 1/4
   model  : mimo-v2.5-free
   origin : src/st/rno4/unk_44B0C.c
   asm    : st/rno4/nonmatchings/unk_44B0C
   proof  : "build/us/RNO4.BIN sha1=7fde040adf8bf5c9a8f22fba694249cf9278dcf7 verified against config/check.us.sha"
   content: exact stub replacement block

   This file is recovery evidence, not another build source.
   Replace the named INCLUDE_ASM stub with the block below
   only when recovering the verified landing. Never overwrite
   this snapshot; a later result gets a numeric suffix. */
void func_us_801C8C54(Entity* self) {
    LoadFerrymanGateTiles();
    DestroyEntity(self);
}