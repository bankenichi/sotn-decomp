/* PERMUTER SEED -- compiled and linked, bytes differ.
   record : us:BOSS/BO6:BO6_RicEntitySubwpnStopwatchCircle
   attempt: 4/4
   model  : opencode/nemotron-3-ultra-free
   verdict: BUILT, CHECKSUM MISMATCH (compiled and linked; bytes differ) - permuter candidate:
--- build tail ---
  ✅ F_RBO0   ✅ RBO3     ✅ F_RBO3   ✅ RBO5     ✅ F_RBO5
  ✅
   Do NOT apply this to the tree as-is; it does not match.
   It exists so the permuter has a compiling starting point. */
void BO6_RicEntitySubwpnStopwatchCircle(Entity* self)
{
        u16 step;
        s16 prim_idx;
    // Stopwatch circle sub-weapon effect: expands ring of GT4 primitives, then destroys self
    Primitive* prim;
    s32 angle_step;
    s32 i;
    s16 radius;
    s16 cx;
    s16 cy;
    s16 sin_val;
    s16 cos_val;
    s16 next_angle;
    s32 x, y;

    step = self->step;
    if (step != 0) {
        i = 0;
        if (step != 1) {
            goto destroy;
        }
        // Step 1: animate expansion
        self->ext.stopwatch.t++;                    // 0x7C: timer
        self->ext.stopwatch.unk7E += 0x18;          // 0x7E: radius grows by 24/frame
        if ((s16)self->ext.stopwatch.t >= 0x1F) {   // 31 frames max
            goto destroy;
        }
        goto animate;
    }

    // Step 0: initialize 16 GT4 primitives forming a circle
    prim_idx = g_api_AllocPrimitives(PRIM_GT4, 0x10);
    self->primIndex = prim_idx;
    if (prim_idx != -1) {
        i = 0;
        self->flags = 0x08800000;  // set some render flags
        prim = &g_PrimBuf[prim_idx];
        angle_step = 0;

        do {
                s16 angle1;
            s16 angle = angle_step >> 16;  // angle_step = i << 24, so angle = i << 8

            prim->tpage = 0x1A;
            prim->clut = 0x15F;
            self->zPriority = 0xC2;
            prim->priority = 0xC2;
            prim->drawMode = 0x435;

            // Vertex 0 (outer)
            sin_val = rsin(angle);
            prim->u0 = ((sin_val << 5) >> 12) + 0x20;

            i++;
            angle_step = i << 24;  // next angle for vertex 1

            cos_val = rcos(angle);
            prim->v0 = -((cos_val << 5) >> 12) - 0x21;

            // Vertex 1 (outer, next segment)
            angle1 = angle_step >> 16;
            sin_val = rsin(angle1);
            prim->u1 = ((sin_val << 5) >> 12) + 0x20;
            cos_val = rcos(angle1);
            prim->v1 = -((cos_val << 5) >> 12) - 0x21;

            // Vertices 2,3 (inner, fixed UV)
            prim->v3 = 0xE0;
            prim->v2 = 0xE0;
            prim->u3 = 0x20;
            prim->u2 = 0x20;

            // Colors: vertices 0,1 = gray (0x40,0x40,0x40), vertices 2,3 = blue (0,0,0x20)
            prim->b1 = 0x40; prim->b0 = 0x40;
            prim->g1 = 0x40; prim->g0 = 0x40;
            prim->r1 = 0x40; prim->r0 = 0x40;
            prim->g3 = 0;    prim->g2 = 0;
            prim->r3 = 0;    prim->r2 = 0;
            prim->b3 = 0x20; prim->b2 = 0x20;

            prim = prim->next;
            angle_step = i << 24;
        } while (i < 0x10);

        self->ext.stopwatch.unk7E = 0x20;  // initial radius = 32
        self->step++;
    } else {
        goto destroy;
    }

animate:
    i = 0;
    cx = self->posX.i.hi;  // offset 0x2
    cy = self->posY.i.hi;  // offset 0x6
    prim = &g_PrimBuf[self->primIndex];
    angle_step = 0;

    do {
            s16 inner_radius;
            s16 radius_y;
        s16 angle = angle_step >> 16;  // angle_step = i << 8, so angle = i << 8? Wait...
        // Actually: s0 = s1 << 8, then passed to rsin/rcos as a0 = s0 (which is s1 << 8)
        // But rsin expects angle in 0x10000 = 360 degrees? Let's check...
        // In init: angle_step = i << 24, then sra 16 -> i << 8. So angle = i * 256.
        // In animate: angle_step = i << 8, then passed directly? No, look at asm:
        // Lus_801CB504: sll s0, s1, 8 -> s0 = i << 8
        // Then addu a0, s0, zero -> a0 = i << 8
        // So angle = i << 8 for animate too.

        sin_val = rsin(angle);
        cos_val = rcos(angle);
        radius = self->ext.stopwatch.unk7E;  // current radius
        inner_radius = radius - 0x20;

        // Vertex 0 (outer)
        x = cx + ((sin_val * radius) >> 12);
        prim->x0 = x;

        // Vertex 2 (inner) - x2
        x = cx + ((sin_val * inner_radius) >> 12);
        prim->x2 = x;

        // Y vertices use radius from memory again (reload)
        radius_y = self->ext.stopwatch.unk7E;
        y = cy - ((cos_val * radius_y) >> 12);
        prim->y0 = y;

        i++;
        next_angle = i << 8;

        y = cy - ((cos_val * (radius_y - 0x20)) >> 12);
        prim->y2 = y;

        // Vertex 1 (outer, next angle)
        sin_val = rsin(next_angle);
        cos_val = rcos(next_angle);
        x = cx + ((sin_val * radius) >> 12);
        prim->x1 = x;

        // Vertex 3 (inner, next angle)
        x = cx + ((sin_val * inner_radius) >> 12);
        prim->x3 = x;

        y = cy - ((cos_val * radius_y) >> 12);
        prim->y1 = y;

        y = cy - ((cos_val * inner_radius) >> 12);
        prim->y3 = y;

        prim = prim->next;
        angle_step = i << 8;
    } while (i < 0x10);

    return;

destroy:
    DestroyEntity(self);
}