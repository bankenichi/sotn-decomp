/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:EntityCorpseweed
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/st/rno0/e_thornweed_corpseweed.c
   verdict: BUILD FAILED:
st use this function)
135:src/st/rno0/e_thornweed_corpseweed.c:35: (Each undeclared identifier is reported only once
136:src/st/rno0/e_thornweed_corpseweed.c:35: for each function it appears in.)
137:src/st/rno0/e_thornweed_corpseweed.c:35: `FLAG_DRAW_ROTX' undeclared (first use this function)
138:src/st/rno0/e_thornweed_corpseweed.c:49: structure has no member named `prim'
139:src/s

   This is NOT a permuter seed and must never be treated as
   one: it has never built. automation/candidates/ is for
   code that builds and merely misses on bytes.

   Why it is kept: the escalation path used to record only
   the compiler's message, so a record like `g_EInitCommon
   undeclared` described code nobody could look at any more.
   Twelve such records were assumed to be one extern away
   from building, and turned out to need a full re-attempt
   because the candidate had been discarded.

   Do NOT apply this to the tree. Read it, fix what the
   verdict names, and re-attempt. */
void EntityCorpseweed(Entity* self) {
    Collider collider;
    Entity* newEntity;
    Primitive* prim;
    s16 temp_s1;
    s32 temp_s0;
    s32 temp_v0;
    s32 temp_v1;
    s32 var_a0;
    s32 var_a1;
    s32 var_a2;
    s32 var_v0;
    s32 var_v1;

    if ((self->flags & FLAG_DEAD) && (self->step < 6)) {
        SetStep(6);
    }

    switch (self->step) {
    case 0:
        InitializeEntity(&g_EInitCorpseweed);
        self->hitboxOffY = 9;
        self->drawFlags = FLAG_DRAW_ROTY | FLAG_DRAW_ROTX;
        self->animCurFrame = 0;
        self->hitboxOffX = 2;
        self->scaleY = 0;
        self->scaleX = 0;
        self->hitboxState = 0;
        self->ext.corpseweed.bobbingAngle = 8;

        prim = g_api_AllocPrimitives(PRIM_GT4, 2);
        if (prim == -1) {
            DestroyEntity(self);
            return;
        }
        self->primIndex = prim;
        self->ext.corpseweed.prim = prim;
        self->flags |= FLAG_HAS_PRIMS;

        // First primitive (stalk)
        prim->tpage = 0x14;
        prim->clut = 0x219;
        prim->u0 = prim->u2 = 0;
        prim->u1 = prim->u3 = 0x18;
        prim->v0 = prim->v1 = 0x28;
        prim->v2 = prim->v3 = 0x50;
        prim->x0 = prim->x1 = prim->x2 = prim->x3 = self->posX.i.hi;
        prim->y0 = prim->y1 = prim->y2 = prim->y3 = self->posY.i.hi;
        prim->r0 = prim->g0 = prim->b0 = 0x80;
        prim->priority = self->zPriority - 1;
        prim->drawMode = DRAW_UNK_20;

        // Second primitive (leaves)
        prim = prim->next;
        prim->tpage = 0x14;
        prim->clut = 0x219;
        prim->u0 = prim->u2 = 0x40;
        prim->u1 = prim->u3 = 0x18;
        prim->v0 = prim->v1 = 0;
        prim->v2 = prim->v3 = 0x70;
        prim->x0 = prim->x1 = prim->x2 = prim->x3 = self->posX.i.hi;
        prim->y0 = prim->y1 = prim->y2 = prim->y3 = self->posY.i.hi;
        prim->r0 = prim->g0 = prim->b0 = 0x80;
        prim->priority = self->zPriority - 2;
        prim->drawMode = DRAW_UNK_20;

        if (self->facingLeft) {
            prim->x2 = self->posX.i.hi - 0x14;
            prim->x3 = self->posX.i.hi + 0x14;
        } else {
            prim->x2 = self->posX.i.hi + 0x14;
            prim->x3 = self->posX.i.hi - 0x14;
        }
        // fallthrough
    case 1:
        prim = self->ext.corpseweed.prim;
        switch (self->step_s) {
        case 0:
            prim->x2--;
            prim->x0 = prim->x2;
            prim->x3++;
            prim->x1 = prim->x3;
            if ((prim->x1 - prim->x0) >= 0x18) {
                self->step_s++;
            }
            break;
        case 1:
            prim->y1--;
            prim->y0 = prim->y1;
            if ((prim->y2 - prim->y0) < 0x28) {
                break;
            }
            self->step_s++;
            break;
        case 2:
            self->ext.corpseweed.leavesDoneGrowing = 1;
            SetStep(2);
            break;
        }
        break;
    case 2:
        prim = self->ext.corpseweed.prim->next;
        switch (self->step_s) {
        case 0:
            prim->y0 -= 2;
            prim->y1 = prim->y0;
            var_a1 = prim->x0 - self->posX.i.hi;
            if (var_a1 < 0) {
                var_a1 = -var_a1;
            }
            if (var_a1 < 0xA) {
                if (self->facingLeft) {
                    prim->x0--;
                } else {
                    prim->x0++;
                }
            }
            if (self->facingLeft) {
                prim->x1++;
            } else {
                prim->x1--;
            }
            var_a1 = prim->y0 - self->posY.i.hi;
            if (var_a1 < 0) {
                var_a1 = -var_a1;
            }
            if (var_a1 < 0x10) {
                if (self->facingLeft) {
                    prim->x1++;
                } else {
                    prim->x1--;
                }
            }
            break;
        case 1:
            if (self->facingLeft) {
                prim->y1--;
                var_a0 = prim->y3 - prim->y1;
                if (var_a0 < 0x59) {
                    prim->y3--;
                }
            } else {
                prim->y3--;
                var_a0 = prim->y3 - prim->y1;
                if (var_a0 < 0x59) {
                    prim->y1--;
                }
            }
            if (var_a0 < 0x70) {
                break;
            }
            self->step_s++;
            break;
        case 2:
            if (self->facingLeft) {
                prim->y3--;
                var_a0 = prim->y3 - prim->y1;
            } else {
                prim->y1--;
                var_a0 = prim->y3 - prim->y1;
            }
            if (var_a0 < 0x70) {
                break;
            }
            self->step_s++;
            break;
        case 3:
            var_a0 = 0;
            var_a1 = prim->x0 - self->posX.i.hi;
            if (var_a1 < 0) {
                var_a1 = -var_a1;
            }
            if (var_a1 < 0x14) {
                if (self->facingLeft) {
                    prim->x0--;
                } else {
                    prim->x0++;
                }
            } else {
                var_a0 = 1;
            }
            var_a1 = self->posX.i.hi - prim->x1;
            if (var_a1 < 0) {
                var_a1 = -var_a1;
            }
            if (var_a1 < 0x14) {
                if (self->facingLeft) {
                    prim->x1++;
                } else {
                    prim->x1--;
                }
            } else {
                var_a0++;
            }
            if (var_a0 != 2) {
                break;
            }
            self->ext.corpseweed.stalkDoneGrowing = 1;
            self->hitboxState = 3;
            SetStep(3);
            break;
        }
        break;
    case 3:
        if (self->scaleX < 0x100) {
            self->scaleX += 8;
            self->scaleY = self->scaleX;
            self->animCurFrame = 0x13;
        } else {
            self->drawFlags = 0;
            SetStep(4);
        }
        break;
    case 4:
        if (self->step_s == 0) {
            self->ext.corpseweed.timer = 0x80;
            self->step_s++;
        }
        self->animCurFrame = 0x13;
        self->ext.corpseweed.timer--;
        if (self->ext.corpseweed.timer == 0) {
            temp_v0 = GetSideToPlayer();
            if ((temp_v0 & 1) == self->facingLeft) {
                SetStep(5);
            } else {
                self->ext.corpseweed.timer = 0x20;
            }
        }
        if (self->hitFlags & 2) {
            self->ext.corpseweed.bobbingTimer = 0x20;
        }
        break;
    case 5:
        switch (self->step_s) {
        case 0:
            self->ext.corpseweed.timer = 0x20;
            self->step_s++;
            // fallthrough
        case 1:
            AnimateEntity(D_us_80181E14, self);
            self->ext.corpseweed.timer--;
            if (self->ext.corpseweed.timer == 0) {
                SetSubStep(2);
            }
            break;
        case 2:
            self->animCurFrame = 0x15;
            newEntity = AllocEntity(&g_Entities_160, &g_Entities_160[23]);
            if (newEntity != NULL) {
                PlaySfxPositional(SFX_STOMP);
                CreateEntityFromEntity(0x29, self, newEntity);
                newEntity->zPriority = self->zPriority + 1;
                newEntity->posY.i.hi = self->posY.i.hi + 0xD;
                newEntity->facingLeft = self->facingLeft;
                if (self->facingLeft) {
                    newEntity->posX.i.hi = self->posX.i.hi - 4;
                } else {
                    newEntity->posX.i.hi = self->posX.i.hi + 4;
                }
            }
            self->ext.corpseweed.timer = 0x10;
            self->step_s++;
            // fallthrough
        case 3:
            self->ext.corpseweed.timer--;
            if (self->ext.corpseweed.timer == 0) {
                SetStep(4);
            }
            break;
        }
        break;
    case 6:
        switch (self->step_s) {
        case 0:
            self->ext.corpseweed.leavesDoneGrowing = 0;
            self->ext.corpseweed.stalkDoneGrowing = 0;
            self->hitboxState = 0;
            self->drawFlags = FLAG_DRAW_ROTY | FLAG_DRAW_ROTX;
            self->step_s++;
            // fallthrough
        case 1:
            MoveEntity();
            self->velocityY += 0x1800;
            self->rotate += 0x20;
            g_api_CheckCollision(
                self->posX.i.hi, self->posY.i.hi + 8, &collider, 0);
            if (collider.effects & EFFECT_SOLID) {
                g_api_PlaySfx(SFX_THUD);
                newEntity = AllocEntity(&g_Entities_224, &g_Entities_224[23]);
                if (newEntity != NULL) {
                    self->posY.i.hi += collider.unk18;
                    CreateEntityFromEntity(0x29, self, newEntity);
                    newEntity->zPriority = self->zPriority + 1;
                    newEntity->posY.i.hi = self->posY.i.hi + 0xD;
                    newEntity->facingLeft = self->facingLeft;
                    if (self->facingLeft) {
                        newEntity->posX.i.hi = self->posX.i.hi - 4;
                    } else {
                        newEntity->posX.i.hi = self->posX.i.hi + 4;
                    }
                }
                DestroyEntity(self);
            }
            break;
        }
        break;
    }

    // Common bobbing logic for steps 1-4
    if (self->step >= 1 && self->step <= 4) {
        if (self->ext.corpseweed.bobbingTimer != 0) {
            self->ext.corpseweed.bobbingTimer--;
            if (self->ext.corpseweed.bobbingTimer & 0x10) {
                self->ext.corpseweed.bobbingAngle++;
            } else {
                self->ext.corpseweed.bobbingAngle--;
            }
        } else {
            self->ext.corpseweed.bobbingAngle = 8;
        }

        if (self->ext.corpseweed.leavesDoneGrowing) {
            prim = self->ext.corpseweed.prim;
            self->ext.corpseweed.bobbingLeavesXT += 0x100;
            var_a1 = (rcos(self->ext.corpseweed.bobbingLeavesXT) * 2) >> 12;
            temp_s0 = (prim->x2 + prim->x3) / 2;
            prim->x0 = temp_s0 + (var_a1 - 0xC);
            prim->x1 = temp_s0 + (var_a1 + 0xC);
            self->ext.corpseweed.bobbingLeavesYT += 0x200;
            var_a0 = (rsin(self->ext.corpseweed.bobbingLeavesYT) * 4) >> 12;
            prim->y0 = prim->y2 + (var_a0 - 0x28);
            prim->y1 = prim->y2 - (var_a0 + 0x28);
        }

        if (self->ext.corpseweed.stalkDoneGrowing) {
            prim = self->ext.corpseweed.prim->next;
            self->ext.corpseweed.bobbingStalkXT += 0x38;
            temp_s0 = (prim->x2 + prim->x3) / 2;
            var_a1 = (self->ext.corpseweed.bobbingAngle * rsin(self->ext.corpseweed.bobbingStalkXT)) >> 12;
            if (self->facingLeft) {
                prim->x1 = temp_s0 + (var_a1 + 0x14);
                prim->x0 = temp_s0 + (var_a1 - 0x14);
            } else {
                prim->x1 = temp_s0 + (var_a1 - 0x14);
                prim->x0 = temp_s0 + (var_a1 + 0x14);
            }
            self->ext.corpseweed.bobbingStalkYT += 0x64;
            var_a0 = (rsin(self->ext.corpseweed.bobbingStalkYT) * 4) >> 12;
            prim->y0 = prim->y2 + (var_a0 - 0x70);
            prim->y1 = prim->y2 - (var_a0 + 0x70);
            if (self->facingLeft) {
                self->posX.i.hi = prim->x0 + 0xC;
            } else {
                self->posX.i.hi = prim->x0 - 0xC;
            }
            self->posY.i.hi = prim->y0 + 0xC;
        }
    }
}