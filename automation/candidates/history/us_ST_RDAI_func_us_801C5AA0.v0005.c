/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:ST/RDAI:func_us_801C5AA0
   attempt: 4/4
   model  : mimo-v2.5-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
   content: WHOLE FILE (directly importable)
   import : python3 tools/decomp-permuter/import.py <this file> asm/us/st/rdai/nonmatchings/func_45aa0/func_us_801C5AA0.s
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
// SPDX-License-Identifier: AGPL-3.0-or-later
#include "rdai.h"

/* Added by the permuter-seed writer. The permuter parses the complete
   translation unit, so every call needs typemap evidence. INCLUDE_ASM
   disappears under PERMUTER, and C89 implicit calls have no declaration.
   Either case otherwise raises KeyError when a mutation touches the call. */
/* Declared by the tree: */
s32 GetSideToPlayer(void);
void PlaySfxPositional(s32 arg0);
extern void (*g_api_FreePrimitives)(s32);
/* Not declared anywhere in the tree, so the real build compiles these by
   C89 implicit declaration (6.3.2.2), which is exactly `extern int f();`.
   Writing it out changes no codegen. */
extern int func_us_801C4B2C();
/* End permuter-seed writer declarations. */


void func_us_801C5AA0(void) {
    Entity* entity = g_CurrentEntity;
    Primitive* prim;
    s32 i;
    u16 facingLeft;
    s16 posX;
    s16 posY;
    u8 unk99;
    u8 unk98;

    switch (entity->step_s) {
    case 0:
        facingLeft = entity->facingLeft;
        entity->facingLeft = (GetSideToPlayer() & 1) ^ 1;
        if (facingLeft != entity->facingLeft) {
            if (entity->facingLeft) {
                entity->posX.i.hi += 0x18;
            } else {
                entity->posX.i.hi -= 0x18;
            }
        }
        prim = entity->ext.prim;
        for (i = 0; i < 8; i++) {
            prim->tpage = 0x12;
            prim->clut = 0x164;
            if (entity->facingLeft) {
                prim->u0 = 0x40;
                prim->u1 = 0;
                prim->u2 = 0x40;
                prim->u3 = 0;
            } else {
                prim->u0 = 0;
                prim->u1 = 0x40;
                prim->u2 = 0;
                prim->u3 = 0x40;
            }
            prim->v0 = -0x4B;
            prim->v1 = -0x4B;
            prim->v2 = -0x4A;
            prim->v3 = -0x4A;
            prim->r0 = 0x80;
            prim->g0 = 0x80;
            prim->b0 = 0x80;
            prim->r1 = 0x80;
            prim->g1 = 0x80;
            prim->b1 = 0x80;
            prim->r2 = 0x80;
            prim->g2 = 0x80;
            prim->b2 = 0x80;
            prim->r3 = 0x80;
            prim->g3 = 0x80;
            prim->b3 = 0x80;
            if (entity->facingLeft) {
                prim->x0 = entity->posX.i.hi - 0x30;
            } else {
                prim->x0 = entity->posX.i.hi - 0x10;
            }
            prim->x1 = prim->x0 + 0x40;
            prim->x2 = prim->x0;
            prim->x3 = prim->x1;
            posY = entity->posY.i.hi + 8;
            prim->y0 = posY;
            prim->y1 = posY;
            prim->y2 = posY;
            prim->y3 = posY;
            prim->drawMode = 2;
            prim->priority = entity->zPriority + 2;
            prim = prim->next;
        }
        func_us_801C4B2C(entity, 0x80, -0x4B, -0x4A);
        PlaySfxPositional(0x672);
        entity->ext.player.unkA6 = 8;
        entity->step_s++;
        break;
    case 1:
        prim = entity->ext.player.unkA8;
        prim->y0 -= 2;
        prim->y1 -= 2;
        unk99 = entity->ext.player.unkA6 - 1;
        entity->ext.player.unkA6 = unk99;
        if (!(unk99 & 0xFF)) {
            entity->ext.player.unkA6 = 0x10;
            entity->step_s++;
        }
        break;
    case 2:
        prim = entity->ext.player.unkA8;
        prim->y0 -= 1;
        prim->y1 -= 1;
        prim = entity->ext.prim;
        prim->y0 -= 4;
        prim->y1 -= 4;
        func_us_801C4B2C(entity);
        unk99 = entity->ext.player.unkA6 - 1;
        entity->ext.player.unkA6 = unk99;
        if (!(unk99 & 0xFF)) {
            entity->ext.player.unkA6 = 0xF;
            entity->step_s++;
        }
        break;
    case 3:
        prim = entity->ext.player.unkA8;
        prim->y0 += 2;
        prim->y1 += 2;
        if (entity->posY.i.hi < prim->y0) {
            prim->drawMode |= 8;
        }
        prim = entity->ext.prim;
        prim->y0 -= 2;
        prim->y1 -= 2;
        func_us_801C4B2C(entity);
        unk99 = entity->ext.player.unkA6 - 1;
        entity->ext.player.unkA6 = unk99;
        if (!(unk99 & 0xFF)) {
            entity->ext.player.unkA6 = 0xF;
            entity->step_s++;
        }
        break;
    case 4:
        prim = entity->ext.player.unkA8;
        prim->y0 += 2;
        prim->y1 += 2;
        if (entity->posY.i.hi < prim->y0) {
            prim->drawMode |= 8;
        }
        prim = entity->ext.prim;
        prim->y0 += 2;
        prim->y1 += 2;
        func_us_801C4B2C(entity);
        if ((entity->posY.i.hi - 6) < prim->y0) {
            entity->step_s++;
        }
        break;
    case 5:
        facingLeft = entity->palette;
        entity->animCurFrame = 1;
        entity->ext.player.unkA4 = 0x18;
        entity->palette = 0x8164;
        entity->hitEffect = facingLeft;
        g_api_FreePrimitives(entity->primIndex);
        entity->flags &= 0xFF7FFFFF;
        entity->step_s++;
        break;
    case 6:
        unk98 = entity->ext.player.unkA4 - 1;
        entity->ext.player.unkA4 = unk98;
        if (!(unk98 & 0xFF)) {
            entity->hitboxState = 3;
            entity->palette = entity->hitEffect;
            entity->step_s++;
        }
        break;
    }
}
