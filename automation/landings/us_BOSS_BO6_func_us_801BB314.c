/* VERIFIED LANDING SNAPSHOT. Kept on purpose.
   record : us:BOSS/BO6:func_us_801BB314
   attempt: 3/4
   model  : mimo-v2.5-free
   origin : src/boss/bo6/us_39144.c
   asm    : boss/bo6/nonmatchings/us_39144
   proof  : "build/us/BO6.BIN sha1=fe067af9b7adca08dc99b108129a0f45a7ad45cd verified against config/check.us.sha"
   content: exact stub replacement block

   This file is recovery evidence, not another build source.
   Replace the named INCLUDE_ASM stub with the block below
   only when recovering the verified landing. Never overwrite
   this snapshot; a later result gets a numeric suffix. */
/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern u8 D_us_801812B9[];
extern u8 D_us_801812BA[];
extern u8 D_us_801812BB[];

extern AnimationFrame* D_us_801812B8[];
extern u8 D_us_801D07FC;
extern u8 D_us_801812B9[];
extern u8 D_us_801D0800;
extern u8 D_us_801812BA[];
extern u8 D_us_801D0804;
extern u8 D_us_801812BB[];
extern u8 D_us_801D0808;

// Copies boss animation frame data into working variables for the current frame index
void func_us_801BB314(s32 arg0) {
    s32 index;

    // arg0 is the frame index; multiply by 4 to get byte offset into pointer arrays
    index = arg0 * 4;

    // D_us_801812B8 is AnimationFrame*[], so D_us_801812B8[arg0] loads the pointer value
    // The asm treats it as a byte load from the pointer array entry (low byte of pointer)
    D_us_801D07FC = (u8)(s32)D_us_801812B8[arg0];

    // D_us_801812B9/BA/BB are u8 arrays indexed by the same scaled index
    D_us_801D0800 = D_us_801812B9[index];
    D_us_801D0804 = D_us_801812BA[index];
    D_us_801D0808 = D_us_801812BB[index];
}