/* UPSTREAM CANDIDATE -- complete target translation unit.
   method : METHOD=UPSTREAM-HARVEST
   record : us:ST/RNZ1:EntityCloakedKnightAura
   source : upstream/master:src/st/nz1/e_cloaked_knight.c
   target : src/st/rnz1/e_cloaked_knight.c
   content: WHOLE FILE (stub substituted, declarations complete)
   verdict: candidate evidence only; isolated score and verify_build remain required. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rnz1.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
void InitializeEntity(u16 arg0[]);
void DestroyEntity(Entity*);
/* End permuter-seed writer declarations. */

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", StepTowards);

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnight);

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnightCloak);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern EInit g_EInitCloakedKnightAura;

void EntityCloakedKnightAura(Entity* self) {
    Entity* parent;

    if (!self->step) {
        InitializeEntity(g_EInitCloakedKnightAura);
        self->hitboxState = 0;
        self->flags |= FLAG_UNK_00200000 | FLAG_UNK_2000;
        self->animCurFrame = 1;
        self->palette += 1;  
        self->drawFlags |= ENTITY_OPACITY | ENTITY_SCALEY | ENTITY_SCALEX;
        self->blendMode = BLEND_TRANSP | BLEND_ADD;
        self->scaleX = self->scaleY = 0x100;
        self->opacity = 0x80;
    }

    parent = self->ext.cloakedKnightAura.parent;
    self->posX.val = parent->posX.val;
    self->posY.val = parent->posY.val;
    self->scaleX = self->scaleY += 6;
    if (parent->ext.cloakedKnight.unk86) {
        self->scaleX = self->scaleY += 6;
    }
    self->opacity -= 4;
    if (self->opacity < 32
#ifndef VERSION_PSP
        || parent->entityId != E_CLOAKED_KNIGHT
#endif
    ) {
        DestroyEntity(self);
    }
}

INCLUDE_ASM("st/rnz1/nonmatchings/e_cloaked_knight", EntityCloakedKnightSword);
