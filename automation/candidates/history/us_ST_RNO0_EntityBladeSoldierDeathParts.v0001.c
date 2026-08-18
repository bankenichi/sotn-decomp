/* PERMUTER SEED -- deterministic isolated-score candidate.
   record : us:ST/RNO0:EntityBladeSoldierDeathParts
   score  : 15
   receipt: nonmatchings/.adapt-scores/20260818-193739-71274-358878/EntityBladeSoldierDeathParts/adapt-score.json
   producer: compiled-donor transplant, no model
   content: WHOLE FILE (isolated adaptable draft)
   origin : src/st/rno0/unk_48100.c
   asm    : asm/us/st/rno0/nonmatchings/unk_48100/EntityBladeSoldierDeathParts.s
   verdict: the exact target function compiled under the project
            compiler and flags but did not score zero. A full game
            build was intentionally not run. Import and search via
            permuter_supervisor.py; never treat this as a match. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rno0.h"

/* Added by the permuter-seed writer. INCLUDE_ASM expands to nothing under
   PERMUTER, so these same-file stubs lose their only mention and the
   permuter's typemap raises KeyError on every mutation touching them. */
/* Declared by the tree: */
void FallEntity(void);
void MoveEntity();
void InitializeEntity(u16 arg0[]);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", TryThrow);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityJackOBones);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityJackOBonesDeathParts);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityJackOBonesJack);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", TryShoot);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", DrawLaserRing);

INCLUDE_RODATA("st/rno0/nonmatchings/unk_48100", D_us_801B5D8C);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityNovaSkeleton);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitNovaSkeleton;

extern EInit g_EInitNovaSkeleton;
extern u16 D_us_8018206C[];

void EntityBladeSoldierDeathParts(Entity* self) {
    if (self->step) {
        if (--self->ext.bladeSoldier.deathPartFallDuration) {
            self->rotate += D_us_8018206C[self->params];
            FallEntity();
            MoveEntity();
            return;
        }

        self->entityId = E_EXPLOSION;
        self->pfnUpdate = EntityExplosion;
        self->params = EXPLOSION_SMALL;
        self->step = 0;
        return;
    }

    InitializeEntity(g_EInitNovaSkeleton);
    self->hitboxState = 0;
    self->flags |=
        FLAG_DESTROY_IF_OUT_OF_CAMERA | FLAG_DESTROY_IF_BARELY_OUT_OF_CAMERA |
        FLAG_UNK_00200000 | FLAG_UNK_2000;
    self->animCurFrame = self->params + 0x23;
    self->drawFlags = ENTITY_ROTATE;
    if (self->facingLeft) {
        self->velocityX = -self->velocityX;
    }
}

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityNovaLaser);

INCLUDE_ASM("st/rno0/nonmatchings/unk_48100", EntityNovaLaserPulse);
