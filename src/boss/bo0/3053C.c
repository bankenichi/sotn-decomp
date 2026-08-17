// SPDX-License-Identifier: AGPL-3.0-or-later
#include "bo0.h"

// Split out of 2D26C.c on 2026-08-16 so that upstream's func_us_801B053C,
// func_us_801B088C and func_us_801B0930 could be harvested. Merged into
// 2D26C.o their jump table landed at 0x294A4; the original has it at 0x294A8,
// which is what a fresh .rodata section gives you. See the [0x3053C, c] note
// in config/splat.us.bobo0.yaml.
//
// Upstream splits this range further (313A8, 38794, 3A030). Those boundaries
// are NOT taken here, so this file spans 0x3053C..0x3A880 and holds their
// stubs too. Taking them would be the same mechanical move if a later harvest
// needs it.
//
// The three functions below are upstream's, from src/boss/bo0/3053C.c.
// func_us_801B0930 needs Ext.et_801B0930, added to include/entity.h from
// upstream in the same commit.

extern s16 D_us_80180DC4[];
extern s16 D_us_80180EE0[];
extern Pos D_us_801CD6E4[];

extern u8 D_us_80180FFC[];
extern u8 D_us_801810BC[];

void func_us_801B053C(void) {
    s32 i;
    Primitive* prim;
    s16* var_a1;
    u8* var_a3;
    s16* var_t0;

    u8 u, v;

    prim = g_CurrentEntity->ext.et_801B0930.prim7C;
    var_a1 = D_us_80180DC4;
    var_a3 = D_us_80180FFC;

    u = 0x60;
    v = 0x40;

    for (i = 0; i < 26; i++) {
        prim->tpage = 0x13;
        prim->clut = 0x209;
        prim->u0 = u + (var_a1 + *var_a3 * 2)[0];
        prim->v0 = v + (var_a1 + *var_a3++ * 2)[1];
        prim->u1 = u + (var_a1 + *var_a3 * 2)[0];
        prim->v1 = v + (var_a1 + *var_a3++ * 2)[1];
        prim->u2 = u + (var_a1 + *var_a3 * 2)[0];
        prim->v2 = v + (var_a1 + *var_a3++ * 2)[1];
        prim->u3 = u + (var_a1 + *var_a3 * 2)[0];
        prim->v3 = v + (var_a1 + *var_a3++ * 2)[1];

        prim->r0 = prim->g0 = prim->b0 = 0x80;
        LOW(prim->r1) = LOW(prim->r0);
        LOW(prim->r2) = LOW(prim->r0);
        LOW(prim->r3) = LOW(prim->r0);
        prim->priority = 0xD0;
        prim->drawMode = DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS | DRAW_TRANSP;
        prim = prim->next;
    }
    g_CurrentEntity->ext.et_801B0930.prim0 = prim;
    var_a1 = D_us_80180EE0;
    var_a3 = D_us_801810BC;
    u = 0;
    v = 0x80;
    for (i = 0; i < 39; i++) {
        prim->tpage = 0x110;
        prim->clut = 0x20B;
        prim->u0 = u + (var_a1 + *var_a3 * 2)[0];
        prim->v0 = v + (var_a1 + *var_a3++ * 2)[1];
        prim->u1 = u + (var_a1 + *var_a3 * 2)[0];
        prim->v1 = v + (var_a1 + *var_a3++ * 2)[1];
        prim->u2 = u + (var_a1 + *var_a3 * 2)[0];
        prim->v2 = v + (var_a1 + *var_a3++ * 2)[1];
        prim->u3 = u + (var_a1 + *var_a3 * 2)[0];
        prim->v3 = v + (var_a1 + *var_a3++ * 2)[1];
        prim->r0 = prim->g0 = prim->b0 = 0;
        LOW(prim->r1) = LOW(prim->r0);
        LOW(prim->r2) = LOW(prim->r0);
        LOW(prim->r3) = LOW(prim->r0);
        prim->priority = 0xD0;
        prim->drawMode = DRAW_TPAGE2 | DRAW_TPAGE | DRAW_COLORS | DRAW_TRANSP;
        prim = prim->next;
    }

    var_a1 = D_us_80180DC4;
    for (i = 0; i < 66; i++) {
        D_us_801CD6E4[i].x.val = (*var_a1 - 0x10) * FIX(1.0);
        var_a1++;
        D_us_801CD6E4[i].y.val = (*var_a1 - 0x27) * FIX(1.0);
        var_a1++;
    }
}

// same as psp/func_pspeu_09255118
void func_us_801B088C(void) {
    s32 i;
    s32 x;
    s32 y;
    s32 t1, t2, t3, t4;
    s16* var_a1;
    s16* var_a0;

    var_a1 = D_us_80180DC4;
    var_a0 = D_us_80180EE0;

    t1 = -0x10;
    t2 = -0x27;
    t3 = -0x40;
    t4 = -0x70;

    for (i = 0; i < 66; i++) {
        x = (t3 + *var_a0) - (t1 + *var_a1);
        x = (x * FIX(1.0)) / 128;
        D_us_801CD6E4[i].x.val = D_us_801CD6E4[i].x.val + x;
        var_a1++;
        var_a0++;

        y = (t4 + *var_a0) - (t2 + *var_a1);
        y = (y * FIX(1.0)) / 128;
        D_us_801CD6E4[i].y.val = D_us_801CD6E4[i].y.val + y;
        var_a1++;
        var_a0++;
    }
}

#ifdef VERSION_PSP
extern s32 D_pspeu_09290458;
#define E_ID_UNK33 D_pspeu_09290458
#else
#define E_ID_UNK33 0x33
#endif

extern s16 D_us_8018117C[];
extern s32 D_us_801CE5B0;

extern EInit g_EInitOlroxAfterImage;

// same as psp/func_pspeu_09255288
void func_us_801B0930(Entity* self) {
    Primitive* prim;
    s32 primIndex;
    s32 i;
    s16 x;
    s16 y;
    u8* var_a2_3;
    s32* pos;
    u8 brightness;
    Entity* entity;
    DR_ENV* drEnv;
    RECT clip;
    DRAWENV drawEnv;
    GpuBuffer* buffer;

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitOlroxAfterImage);
        self->hitboxState = 0;
        self->animCurFrame = 0;
        self->blendMode |= BLEND_ADD | BLEND_TRANSP;
        self->flags &= ~FLAG_POS_CAMERA_LOCKED;
        D_us_801CE5B0 = 1;
        primIndex = g_api.AllocPrimitives(PRIM_GT4, 0x44);
        if (primIndex != -1) {
            self->flags |= FLAG_HAS_PRIMS;
            self->primIndex = primIndex;
            prim = &g_PrimBuf[primIndex];
            self->ext.et_801B0930.prim1 = prim;
            prim->tpage = 0x110;
            if (!self->facingLeft) {
                prim->u0 = prim->u2 = 0;
                prim->u1 = prim->u3 = prim->u0 + 0x80;
            } else {
                prim->u1 = prim->u3 = 0;
                prim->u0 = prim->u2 = prim->u1 + 0x7F;
            }
            prim->v0 = prim->v1 = 0;
            prim->v2 = prim->v3 = prim->v0 + 0x80;
            if (!self->facingLeft) {
                prim->x0 = prim->x2 = self->posX.i.hi - 0x3C;
                prim->x1 = prim->x3 = self->posX.i.hi + 0x44;
            } else {
                prim->x0 = prim->x2 = self->posX.i.hi - 0x44;
                prim->x1 = prim->x3 = self->posX.i.hi + 0x3C;
            }

            prim->y0 = prim->y1 = self->posY.i.hi - 0x70;
            prim->y2 = prim->y3 = self->posY.i.hi + 0x10;
            prim->drawMode = DRAW_HIDE | DRAW_UNK02;
            prim->priority = 0xE0;
            prim = prim->next;
            self->ext.et_801B0930.prim2 = prim;
            drEnv = g_api.func_800EDB08((POLY_GT4*)prim);
            if (!drEnv) {
                g_api.FreePrimitives(primIndex);
                self->step = 0;
                return;
            } else {
                prim->type = PRIM_ENV;
                prim->drawMode = DRAW_HIDE;
                prim = prim->next;
                drEnv = g_api.func_800EDB08((POLY_GT4*)prim);
                if (prim == NULL) {
                    g_api.FreePrimitives(primIndex);
                    self->step = 0;
                    return;
                }
            }
            prim->type = PRIM_ENV;
            prim->drawMode = DRAW_HIDE;
            prim = prim->next;
            self->ext.et_801B0930.prim7C = prim;
            while (prim != NULL) {
                prim->priority = 0xD0;
                prim->drawMode = DRAW_HIDE;
                prim = prim->next;
            }
        } else {
            self->step = 0;
            FntPrint("can't get effect works!\n");
            break;
        }
        // fallthrough

    case 1:
        prim = self->ext.et_801B0930.prim2;
        drawEnv = g_CurrentBuffer->draw;
        drawEnv.isbg = 1;
        clip.x = 0;
        clip.y = 0x100;
        clip.w = 0x7F;
        clip.h = 0x100;
        drawEnv.clip = clip;
        drawEnv.ofs[0] = 0;
#ifdef VERSION_PSP
        drawEnv.ofs[1] = 0x100;
#else
        drawEnv.ofs[1] = 0;
#endif
        drEnv = (DR_ENV*)LOW(prim->r1);
        SetDrawEnv(drEnv, &drawEnv);

        prim->priority = 0xCB;
        prim->drawMode = DRAW_DEFAULT;
        prim = prim->next;
        prim->priority = 0xD4;
        prim->drawMode = DRAW_UNK_800;

        entity = self + 1;
        DestroyEntity(entity);
        CreateEntityFromEntity(E_ID_UNK33, self, entity);
        entity->posX.i.hi = 0x40;
#ifdef VERSION_PSP
        entity->posY.i.hi = 0xEC;
#else
        entity->posY.i.hi = 0x1EC;
#endif
        entity->params = self->facingLeft;

        self->step++;
        break;

    case 2:
        func_us_801B053C();
        prim = (Primitive*)self->ext.et_801B0930.prim2;
        drEnv = (DR_ENV*)LOW(prim->r1);
        drawEnv = g_CurrentBuffer->draw;
        drawEnv.isbg = 1;
        drawEnv.dtd = 0;
        clip.x = 0;
        clip.y = 0x100;
        clip.w = 0x80;
        clip.h = 0x80;
        drawEnv.clip = clip;
        drawEnv.ofs[0] = 0;
        drawEnv.ofs[1] = 0x100;
        SetDrawEnv(drEnv, &drawEnv);
        prim->priority = 0xCF;
        prim->drawMode = DRAW_DEFAULT;
        prim = prim->next;
        prim->priority = 0xD1;
        prim->drawMode = DRAW_UNK_800;
        self->animCurFrame = 0;
        self->zPriority = 0xA0;
        prim = self->ext.et_801B0930.prim1;
        self->posX.i.hi = prim->x0 + 0x40;
        self->posY.i.hi = prim->y0 + 0x70;
        self->flags |= FLAG_POS_CAMERA_LOCKED;
        self->ext.et_801B0930.timer0 = 0x80;
        self->ext.et_801B0930.brightness = -0x8000;
        self->ext.et_801B0930.timer1 = D_us_8018117C[0];
        self->pose = 0;
        self->step_s = 0;
        g_api.PlaySfx(SFX_OLROX_MONSTER_PAIN);
        self->step++;
        break;

    case 3:
        prim = self->ext.et_801B0930.prim1;
        prim->drawMode = DRAW_UNK02;
        if (self->ext.et_801B0930.timer0 > 0) {
            func_us_801B088C();
        }
        brightness = self->ext.et_801B0930.brightness >> 8;
        if (brightness > 0x80) {
            brightness = 0x80;
        }
        prim = self->ext.et_801B0930.prim7C;
        x = 0x40;
        y = 0x70;
        pos = D_us_801CD6E4;
        var_a2_3 = D_us_80180FFC;

        for (i = 0; i < 26; i++) {
            prim->x0 = x + ((pos + (*var_a2_3 * 2))[0] >> 16);
            prim->y0 = y + ((pos + (*var_a2_3++ * 2))[1] >> 16);
            prim->x1 = x + ((pos + (*var_a2_3 * 2))[0] >> 16);
            prim->y1 = y + ((pos + (*var_a2_3++ * 2))[1] >> 16);
            prim->x2 = x + ((pos + (*var_a2_3 * 2))[0] >> 16);
            prim->y2 = y + ((pos + (*var_a2_3++ * 2))[1] >> 16);
            prim->x3 = x + ((pos + (*var_a2_3 * 2))[0] >> 16);
            prim->y3 = y + ((pos + (*var_a2_3++ * 2))[1] >> 16);

            prim->r0 = prim->g0 = prim->b0 = brightness;
            LOW(prim->r1) = LOW(prim->r0);
            LOW(prim->r2) = LOW(prim->r0);
            LOW(prim->r3) = LOW(prim->r0);
            prim = prim->next;
        }
        brightness = 0x80 - brightness;
        prim = self->ext.et_801B0930.prim0;
        pos = D_us_801CD6E4;
        var_a2_3 = D_us_801810BC;
        x = 0x40;
        y = 0x70;

        for (i = 0; i < 39; i++) {
            prim->x0 = x + ((pos + (*var_a2_3 * 2))[0] >> 16);
            prim->y0 = y + ((pos + (*var_a2_3++ * 2))[1] >> 16);
            prim->x1 = x + ((pos + (*var_a2_3 * 2))[0] >> 16);
            prim->y1 = y + ((pos + (*var_a2_3++ * 2))[1] >> 16);
            prim->x2 = x + ((pos + (*var_a2_3 * 2))[0] >> 16);
            prim->y2 = y + ((pos + (*var_a2_3++ * 2))[1] >> 16);
            prim->x3 = x + ((pos + (*var_a2_3 * 2))[0] >> 16);
            prim->y3 = y + ((pos + (*var_a2_3++ * 2))[1] >> 16);

            prim->r0 = prim->g0 = prim->b0 = brightness;
            LOW(prim->r1) = LOW(prim->r0);
            LOW(prim->r2) = LOW(prim->r0);
            LOW(prim->r3) = LOW(prim->r0);
            prim = prim->next;
        }
        self->ext.et_801B0930.timer0--;
        self->ext.et_801B0930.brightness =
            (self->ext.et_801B0930.timer0 + 16) * 256;
        if (self->ext.et_801B0930.timer0 < 0 &&
            self->ext.et_801B0930.brightness < 0) {
            self->ext.et_801B0930.timer0 = 0x20;
            self->step = 5;
        }
        // fallthrough

    case 4:
        if (!(g_Timer & 7)) {
            g_api.PlaySfx(SFX_OLROX_TRANSFORM);
        }

        switch (self->step_s) {
        case 0:
            if (!--self->ext.et_801B0930.timer1) {
                self->pose++;
                self->ext.et_801B0930.timer1 = D_us_8018117C[self->pose];
                self->step = 4;
                self->step_s++;
            }
            break;
        case 1:
            if (!(self->ext.et_801B0930.timer1 % 8)) {
                prim = self->ext.et_801B0930.prim1;

                if (self->ext.et_801B0930.timer1 >
                    (D_us_8018117C[self->pose] / 2)) {
                    prim->y0 = prim->y1 -= 2;
                    prim->x1 = prim->x3 += 1;
                    prim->x0 = prim->x2 -= 1;
                } else {
                    prim->y0 = prim->y1 += 2;
                    prim->x1 = prim->x3 -= 1;
                    prim->x0 = prim->x2 += 1;
                }
            }

            if (!--self->ext.et_801B0930.timer1) {
                prim = self->ext.et_801B0930.prim1;
                prim->x1 = prim->x3 = self->posX.i.hi + 0x40;
                prim->x0 = prim->x2 = self->posX.i.hi - 0x40;
                prim->y0 = prim->y1 = self->posY.i.hi - 0x70;
                self->pose++;
                self->ext.et_801B0930.timer1 = D_us_8018117C[self->pose];
                self->step = 3;
                self->step_s--;
            }
            break;
        }
        break;

    case 5:
        if (!--self->ext.et_801B0930.timer0) {
            self->step++;
        }
        break;

    case 6:
        D_us_801CE5B0 = 0;
        entity = self + 1;
        entity->posX.i.hi = self->posX.i.hi;
        entity->posY.i.hi = 0x1CC - g_Tilemap.scrollY.i.hi;
        DestroyEntity(self);
        break;
    }
}

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B13A8);

void func_us_801B1590(u8 step) {
    ET_B0_Unk* temp = (ET_B0_Unk*)g_CurrentEntity->ext.b0Unk.unk80;

    g_CurrentEntity->step = step;
    g_CurrentEntity->step_s = 0;

    temp->childPalette = 0;
    temp = (ET_B0_Unk*)temp->parent;
    temp->childPalette = 0;
}

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B15BC);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B163C);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B171C);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B17BC);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B1864);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B1950);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B19FC);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B1B30);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B1C60);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B1CE0);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B1DDC);

s32 func_us_801B1E5C(void *arg0)
{
  void *entity = arg0;
  s32 result1;
  s32 result2;
  void *child = *((void **) (((char *) entity) + 0x18));
  func_us_801B163C(&g_CurrentEntity->ext.venusWeed.pad_90, 0, 0xC);
  result1 = func_us_801B171C(entity, -0x40, 0x40, 0x60);
 do { result2 = func_us_801B171C(child, -0x200, 0x280, 0x50); return (result1 + result2) == 2; } while (0);
}

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B1EDC);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B1F5C);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B2044);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B20F4);

/* Declarations injected by the worker: used by the candidate
   below and absent from this file. Copied verbatim from the
   tree, same overlay or a shared header, never another
   overlay's. */
extern Tilemap g_Tilemap;

s16 func_us_801B2178(Entity* entity) {
    s16 tileY = g_Tilemap.scrollY.i.hi;
    s16 sum = tileY + entity->rotPivotY;
    s16 result = 0;
    s16 flag;

    if (sum >= 0x1CC) {
        result = 0x1CC - sum;
        flag = 1;
    } else {
        flag = 0;
    }
    entity->entityId = flag;
    FntPrint("hit_kind %x\n", flag);
    return result;
}

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B21F0);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B24CC);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B2690);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B30AC);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B365C);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B5470);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B551C);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B5D6C);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B5E08);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B5E8C);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B619C);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B6520);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B65C0);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B6CA4);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B76E4);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B7BAC);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B7C44);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B7CC8);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B8794);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B888C);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B8970);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B8B64);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B8D8C);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801B9BEC);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801BA030);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801BA128);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801BA4AC);

INCLUDE_ASM("boss/bo0/nonmatchings/3053C", func_us_801BA724);
