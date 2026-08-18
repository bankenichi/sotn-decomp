/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:BOSS/BO0:func_us_801AFAF4
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/bo0/2D26C.c
   verdict: quality reject: `Entity` has no member `unkA4`; 0xA4 falls inside `ext` (0x7C)

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
void func_us_801AFAF4(Entity* arg0) {
    Entity* s1;
    Entity* entity;
    s16 s6;
    s16 s5;
    u16 s4;
    s32 s3;
    s32 s2;
    s32 distance;
    s16 angle;
    s16 newScale;
    s32 temp;
    s16 diffX;
    s16 diffY;
    u16 step;
    u16 parentZPri;
    s16 oldPosX;
    s16 oldPosY;

    s1 = arg0->unkA4; /* ext+0x28, parent entity */

    if (s1->flags & 0x100) {
        arg0->flags |= 0x100;
    }

    if (arg0->flags & 0x100) {
        entity = AllocEntity(g_Entities_224, &g_Entities_224[950]);
        if (entity != NULL) {
            CreateEntityFromEntity(2, arg0, entity);
            entity->params = 2;
        }
        DestroyEntity(arg0);
        PlaySfxPositional(0x64E);
        return;
    }

    step = arg0->step;
    switch (step) {
    case 0:
        InitializeEntity(&D_us_801806D8);
        s1 = arg0->unkA4;
        arg0->hitboxState = 0;
        arg0->hitboxOffX = 1;
        arg0->hitboxOffY = 1;
        arg0->palette = 0x219;
        arg0->zPriority = s1->zPriority + 2;
        arg0->pose = (Random() & 3) * 2;
        arg0->unk80 = (arg0->params + 1) * 0xE; /* ext+0x04, timer */
        arg0->drawFlags |= 3;
        arg0->params = Random() & 3;
        return;

    case 1:
        AnimateEntity(&D_us_80180D38, arg0);
        s1 = arg0->unkA4;
        oldPosX = arg0->unk02; /* inside posX, integer part */
        oldPosY = arg0->unk06; /* inside posY, integer part */
        s4 = s1->unk02; /* inside posX, integer part */
        s5 = s1->unk06; /* inside posY, integer part */
        s5 = s5 - 0x20;
        s3 = arg0->unk06 - s5; /* posY integer part */
        s2 = arg0->unk02 - s4; /* posX integer part */
        angle = ratan2(-s3, s2);
        if (s1->facingLeft != 0) {
            angle = angle + 0x10;
        } else {
            angle = angle - 0x10;
        }
        distance = SquareRoot0((s2 * s2) + (s3 * s3)) - 2;
        temp = distance * rcos(angle);
        if (temp < 0) {
            temp += 0xFFF;
        }
        arg0->unk02 = s4 + (temp >> 12); /* posX integer part */
        temp = distance * rsin(angle);
        if (temp < 0) {
            temp += 0xFFF;
        }
        arg0->unk06 = s5 - (temp >> 12); /* posY integer part */
        newScale = (distance * arg0->params) + 0x100;
        arg0->scaleX = newScale;
        if (newScale >= 0x301) {
            arg0->scaleX = 0x300;
        }
        arg0->scaleY = arg0->scaleX;
        diffX = arg0->unk02 - oldPosX; /* posX integer part */
        if (diffX <= 0) {
            arg0->facingLeft = 1;
        } else {
            arg0->facingLeft = 0;
        }
        if (distance < 8) {
            arg0->unkA8 = Random(); /* ext+0x2c */
            arg0->palette = 0x209;
            arg0->hitboxState = 3;
            arg0->drawFlags = 0;
            arg0->step += 1;
            return;
        }
        return;

    case 2:
        s1 = arg0->unkA4;
        AnimateEntity(&D_us_80180D38, arg0);
        MoveEntity();
        if (arg0->velocityX > 0) {
            arg0->facingLeft = 1;
            parentZPri = s1->zPriority + 2;
        } else {
            arg0->facingLeft = 0;
            parentZPri = s1->zPriority - 2;
        }
        arg0->zPriority = parentZPri;
        diffX = s1->unk02 - arg0->unk02; /* posX integer part */
        diffY = s1->unk06 - arg0->unk06; /* posY integer part */
        arg0->unkA8 = AdjustValueWithinThreshold(2, arg0->unkA8, Ratan2Shifted(diffX, diffY) & 0xFF); /* ext+0x2c */
        SetEntityVelocityFromAngle(arg0->unkA8, 0x10);
        if (s1->unk84 != 0) { /* ext+0x08 */
            temp = arg0->unk80 - 1; /* ext+0x04 */
            arg0->unk80 = temp;
            if ((temp << 16) == 0) {
                SetEntityVelocityFromAngle(GetAngleBetweenEntitiesShifted(arg0, g_Entities) & 0xFF, 0x20);
                arg0->step += 1;
                return;
            }
        }
        break;

    case 3:
        AnimateEntity(&D_us_80180D38, arg0);
        MoveEntity();
        if (arg0->velocityX > 0) {
            arg0->facingLeft = 0;
        } else {
            arg0->facingLeft = 1;
        }
        diffX = arg0->unk02; /* posX integer part */
        if (diffX < 0) {
            diffX = -diffX;
        }
        if (diffX < 0x201) {
            diffY = arg0->unk06; /* posY integer part */
            if (diffY < 0) {
                diffY = -diffY;
            }
            if (diffY >= 0x201) {
                DestroyEntity(arg0);
            }
        } else {
            DestroyEntity(arg0);
        }
        break;
    }
}