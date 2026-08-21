/* VERIFIED LANDING SNAPSHOT. Kept on purpose.
   record : us:BOSS/BO0:EntityOlroxAfterImage
   attempt: 1/4
   model  : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   asm    : boss/bo0/nonmatchings/2D26C
   proof  : "build/us/BO0.BIN sha1=c9e00e7555c363d11b6e451403b59d96d3e591af verified against config/check.us.sha"
   content: exact stub replacement block

   This file is recovery evidence, not another build source.
   Replace the named INCLUDE_ASM stub with the block below
   only when recovering the verified landing. Never overwrite
   this snapshot; a later result gets a numeric suffix. */
/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitOlroxAfterImage;

/* EntityOlroxAfterImage: Creates a fading afterimage effect for Olrox, */
/* sets initial appearance from params, then fades opacity each frame. */
void EntityOlroxAfterImage(Entity* entity) {
    if (entity->step == 0) {
        InitializeEntity(g_EInitOlroxAfterImage);
        entity->palette = 0x217;
        entity->drawFlags = 8;
        entity->opacity = 0x80;
        entity->hitboxState = 0;
        entity->blendMode = 0x30;
        entity->animCurFrame = entity->params;
        entity->zPriority -= 2;
    }
    entity->opacity -= 2;
    if (entity->opacity == 0) {
        DestroyEntity(entity);
    }
}