/* VERIFIED LANDING SNAPSHOT. Kept on purpose.
   record : us:ST/RNO0:func_us_801CFC98
   attempt: 2/4
   model  : mimo-v2.5-free
   origin : src/st/rno0/unk_4F968.c
   asm    : st/rno0/nonmatchings/unk_4F968
   proof  : "build/us/RNO0.BIN sha1=125003c7fe5d3510fddee22d4f5e5390fe507acf verified against config/check.us.sha"
   content: exact stub replacement block

   This file is recovery evidence, not another build source.
   Replace the named INCLUDE_ASM stub with the block below
   only when recovering the verified landing. Never overwrite
   this snapshot; a later result gets a numeric suffix. */
/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Entity* g_CurrentEntity;

// Checks wall collisions on two Y positions offset from entity center.
s32 func_us_801CFC98(Entity* arg0, s32 arg1) {
    Collider collider;
    s32 posX;
    s32 result;
    s32 counter;
    s32 checkY;

    posX = arg0->posX.i.hi;
    if (arg1 != g_CurrentEntity->facingLeft) {
        posX += 0x38;
    } else {
        posX -= 0x38;
    }
    result = 0;
    counter = 0;
    checkY = arg0->posY.i.hi + 4;
    do {
        g_api_CheckCollision(posX, checkY, &collider, 0);
        if (counter != 0) {
            if (!(collider.effects & 1)) {
                result |= 2;
            }
        } else {
            if (collider.effects & 1) {
                result |= 1;
            }
        }
        counter++;
        checkY += 4;
    } while (counter < 2);
    return result;
}
