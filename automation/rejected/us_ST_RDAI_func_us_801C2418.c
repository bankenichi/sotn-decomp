/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:ST/RDAI:func_us_801C2418
   attempt: 2/4
   from   : m2c (no model call)
   origin : src/st/rdai/unk_41DE8.c
   verdict: quality reject: `Entity` has no member `unkEC`; 0xEC falls inside `unkB8` (0xB8)

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
s32 AnimateEntity(? *, Entity *);
? CreateEntityFromCurrentEntity(?, Entity *);
? CreateEntityFromEntity(?, Entity *, Entity *);
s32 GetDistanceToPlayerX();
s32 GetSideToPlayer();
? MoveEntity();
? PlaySfxPositional(?);
? SetStep(s32, s16, Primitive *, u8);
? SetSubStep(?, s16, Primitive *);
? func_us_801C21E4(?);
extern u16 D_us_801808CC;
extern u16 D_us_801808D2;
extern ? D_us_80181934;
extern ? D_us_8018195C;
extern ? D_us_8018198C;
extern ? D_us_801819A4;
extern ? D_us_801819DC;
extern ? D_us_80181A14;
extern ? D_us_80181A1C;
extern s16 PLAYER_posX_i_hi;
extern Entity g_Entities_160;
extern Entity g_Entities_224;
extern u16 g_pads_1_pressed;

void func_us_801C2418(Entity *arg0) {
     Entity *temp_v0_12;
     Entity *temp_v0_16;
     Entity *temp_v0_20;
     Entity *temp_v0_21;
     Primitive *temp_a2;
     Primitive *temp_a2_2;
     Primitive *temp_a2_3;
     Primitive *temp_a2_4;
     Primitive *temp_a2_5;
     Primitive *var_a2;
     Primitive *var_a2_2;
     Primitive *var_a2_3;
     s16 temp_a0_2;
     s16 temp_a0_3;
     s16 temp_a1;
     s16 temp_a1_2;
     s16 temp_v0;
     s16 temp_v0_10;
     s16 temp_v0_11;
     s16 temp_v0_13;
     s16 temp_v0_18;
     s16 temp_v0_22;
     s16 temp_v0_5;
     s16 temp_v0_6;
     s16 temp_v0_9;
     s16 temp_v1_10;
     s16 temp_v1_11;
     s16 temp_v1_3;
     s16 var_a1;
     s16 var_a1_2;
     s16 var_v0_9;
     s32 temp_s2;
     s32 temp_s3;
     s32 temp_v0_4;
     s32 temp_v1_2;
     s32 temp_v1_4;
     s32 var_s2;
     s32 var_s2_2;
     s32 var_v0_3;
     s32 var_v0_4;
     s32 var_v0_7;
     s32 var_v1;
     u16 temp_a0;
     u16 temp_s0;
     u16 temp_v0_17;
     u16 temp_v0_2;
     u16 temp_v0_3;
     u16 temp_v0_7;
     u16 temp_v0_8;
     u16 temp_v1;
     u16 temp_v1_12;
     u16 temp_v1_5;
     u16 temp_v1_6;
     u16 temp_v1_7;
     u16 temp_v1_8;
     u16 temp_v1_9;
     u16 var_v0_2;
     u16 var_v0_8;
     u32 temp_v0_14;
     u32 temp_v0_15;
     u32 temp_v0_19;
     u32 var_v0_5;
     u32 var_v0_6;
     u8 var_a0;
     u8 var_a3;
     u8 var_v0;
 ? var_a0_2;

 if (g_Timer & 1) {
  arg0->palette = D_us_801808D2;
 } else {
  arg0->palette = D_us_801808D2 + 3;
 }
 if ((arg0->flags & 0x100) && ((u16) arg0->step < 9U)) {
  PlaySfxPositional(0x717);
  SetStep(9);
 }
 temp_v1 = arg0->step;
 switch (temp_v1) {  /* switch 1; irregular */
 case 0x0:  /* switch 1 */
  InitializeEntity(&D_us_801808CC);
  arg0->flags |= 0x2000;
  if (arg0->params == 0) {
   CreateEntityFromCurrentEntity(0x26, arg0 + 0xBC);
   arg0->unkEC = 1;
   arg0->unkE0 = (s16) (arg0->zPriority - 1);
   CreateEntityFromCurrentEntity(0x26, arg0 + 0x178);
   arg0->unk1A8 = 2;
   arg0->unk19C = (s16) (arg0->zPriority + 2);
   temp_v0 = g_api_AllocPrimitives(PRIM_GT4, 0xC);
   if (temp_v0 != -1) {
    temp_a2 = &g_PrimBuf[temp_v0];
    var_a1 = 0;
    var_a3 = 0x30;
    arg0->primIndex = (s32) temp_v0;
    arg0->ext.prim = temp_a2;
    var_a0 = 0x28;
    arg0->flags |= 0x800000;
    temp_a2->tpage = (u16) ((u16) arg0->unk5A >> 2);
    temp_a2->u3 = 0x38;
    temp_a2->u1 = 0x38;
    temp_a2->v1 = 0xC8;
    temp_a2->v0 = 0xC8;
    temp_a2->u2 = 0;
    temp_a2->u0 = 0;
    temp_a2->v3 = 0xFF;
    temp_a2->v2 = 0xFF;
    temp_a2->clut = arg0->palette + 1;
    temp_a2->drawMode = 8;
    temp_a2->priority = arg0->zPriority + 1;
    var_a2 = temp_a2->next;
    do {
     var_a2->tpage = (u16) ((u16) arg0->unk5A >> 2);
     var_a2->v1 = var_a0;
     var_a2->v0 = var_a0;
     var_a2->u2 = 0xF0;
     var_a2->u0 = 0xF0;
     var_a2->u3 = 0xFF;
     var_a2->u1 = 0xFF;
     var_a2->v3 = var_a3;
     var_a2->v2 = var_a3;
     var_a2->clut = arg0->palette + 2;
     temp_v0_2 = (u16) arg0->posX.i.hi;
     var_a1 += 1;
     var_a2->x3 = (s16) temp_v0_2;
     var_a2->x1 = (s16) temp_v0_2;
     var_a2->x2 = (s16) temp_v0_2;
     var_a2->x0 = (s16) temp_v0_2;
     temp_v0_3 = (u16) arg0->posY.i.hi;
     var_a3 += 8;
     var_a2->y3 = (s16) temp_v0_3;
     var_a2->y2 = (s16) temp_v0_3;
     var_a2->y1 = (s16) temp_v0_3;
     var_a2->y0 = (s16) temp_v0_3;
     var_a2->drawMode = 8;
     var_a2->priority = arg0->zPriority + 0xFFFE;
     var_a2 = var_a2->next;
     var_a0 += 8;
    } while (var_a1 < 0xB);
    SetStep(3, var_a1, var_a2, var_a3);
    goto block_177;
   }
block_168:
   DestroyEntity(arg0);
   return;
  }
  arg0->hitboxState = 0;
  temp_v1_2 = arg0->flags | 0x202000;
  arg0->flags = temp_v1_2;
  if (arg0->params & 0xFF00) {
   arg0->animCurFrame = (s16) ((u16) arg0->params >> 8);
   arg0->params = (u16) (u8) arg0->params;
  } else {
   arg0->flags = temp_v1_2 & 0x7FFFFFFF;
  }
  SetStep(arg0->params + 0x10);
 default:  /* switch 1 */
block_177:
  temp_v1_3 = arg0->animCurFrame;
  if (temp_v1_3 < 0xD) {
   arg0->hitboxOffX = -6;
   arg0->hitboxOffY = 9;
   arg0->hitboxWidth = 0x14;
   var_v0 = 0x17;
  } else if (temp_v1_3 < 0x11) {
   arg0->hitboxOffX = -0xB;
   arg0->hitboxOffY = -2;
   arg0->hitboxWidth = 0x14;
   var_v0 = 0x17;
  } else {
   arg0->hitboxOffY = -5;
   arg0->hitboxWidth = 0xE;
   var_v0 = 0x16;
   arg0->hitboxOffX = 0;
  }
  arg0->hitboxHeight = var_v0;
  if (arg0->params == 0) {
   var_a2_2 = arg0->ext.prim;
   var_v0_2 = arg0->palette + 1;
loop_185:
   var_a2_2->clut = var_v0_2;
   var_a2_2 = var_a2_2->next;
   if (var_a2_2 != NULL) {
    var_v0_2 = arg0->palette + 2;
    goto loop_185;
   }
   temp_a0 = arg0->step;
   if ((temp_a0 == 3) || (var_a0_2 = 1, (temp_a0 == 6))) {
    var_a0_2 = 0;
   }
   func_us_801C21E4(var_a0_2);
  }
  return;
 case 0x3:  /* switch 1 */
  AnimateEntity(&D_us_801819A4, arg0);
  temp_s0 = arg0->step_s;
  switch (temp_s0) {  /* switch 2; irregular */
  case 0:  /* switch 2 */
   arg0->scaleX = 0x100;
   arg0->scaleY = 0x100;
   arg0->opacity = 0xFF;
   arg0->hitboxState = 0;
   arg0->drawFlags |= 3;
   arg0->rotate = 0x800;
   arg0->drawFlags |= 8;
   arg0->step_s += 1;
   arg0->drawFlags |= 4;
  case 1:  /* switch 2 */
   arg0->animCurFrame = 0;
   if (GetDistanceToPlayerX() < 0x40) {
    PlaySfxPositional(0x627);
    arg0->facingLeft = (GetSideToPlayer() & 1) ^ 1;
    arg0->posY.i.hi = -0x20;
    arg0->velocityY = 0xA0000;
    arg0->pose = 0;
    arg0->poseTimer = 0;
    arg0->animCurFrame = 0x3A;
block_47:
    arg0->step_s += 1;
   }
   break;
  case 2:  /* switch 2 */
   MoveEntity();
   arg0->animCurFrame = 0x3A;
   arg0->pose = 0;
   arg0->poseTimer = 0;
   temp_v0_4 = arg0->velocityY - 0x4000;
   arg0->velocityY = temp_v0_4;
   if (temp_v0_4 < 0xFFFD0000) {
    arg0->velocityY = -0x10000;
    arg0->scaleX = 8;
    arg0->scaleY = 0x180;
    goto block_47;
   }
   break;
  case 3:  /* switch 2 */
   MoveEntity();
   arg0->rotate = 0;
   temp_v0_5 = (u16) arg0->scaleX + 0xC;
   arg0->scaleX = temp_v0_5;
   var_v1 = 0;
   if (temp_v0_5 >= 0x101) {
    arg0->scaleX = 0x100;
    var_v1 = 1;
   }
   temp_v0_6 = (u16) arg0->scaleY - 4;
   arg0->scaleY = temp_v0_6;
   if (temp_v0_6 < 0x100) {
    arg0->scaleY = 0x100;
    var_v1 += 1;
   }
   arg0->opacity += 0xFE;
   if ((u8) arg0->opacity < 0x80U) {
    arg0->opacity = 0x80;
    var_v1 += 1;
   }
   var_a1_2 = 0;
   if (var_v1 == temp_s0) {
    arg0->drawFlags = 0;
    var_a2_3 = arg0->ext.prim->next;
    do {
     temp_v0_7 = (u16) arg0->posX.i.hi;
     var_a2_3->x3 = (s16) temp_v0_7;
     var_a2_3->x1 = (s16) temp_v0_7;
     var_a2_3->x2 = (s16) temp_v0_7;
     var_a2_3->x0 = (s16) temp_v0_7;
     temp_v0_8 = (u16) arg0->posY.i.hi;
     var_a1_2 += 1;
     var_a2_3->drawMode = 2;
     var_a2_3->y3 = (s16) temp_v0_8;
     var_a2_3->y2 = (s16) temp_v0_8;
     var_a2_3->y1 = (s16) temp_v0_8;
     var_a2_3->y0 = (s16) temp_v0_8;
     var_a2_3 = var_a2_3->next;
    } while (var_a1_2 < 0xB);
    arg0->hitboxState = 3;
    arg0->flags &= ~0x2000;
    SetStep(4, var_a1_2, var_a2_3);
   }
   break;
  }
  if (g_Timer & 1) {
   arg0->animCurFrame = 0;
  }
  goto block_177;
 case 0x4:  /* switch 1 */
  if (arg0->step_s == 0) {
   arg0->unk94 = 0x40;
   arg0->step_s += 1;
  }
  MoveEntity();
  AnimateEntity(&D_us_80181934, arg0);
  if ((s32) arg0->pose == 5) {
   PlaySfxPositional(0x68D);
  }
  if (arg0->facingLeft != 0) {
   var_s2 = PLAYER_posX_i_hi - 0x50;
  } else {
   var_s2 = PLAYER_posX_i_hi + 0x50;
  }
  temp_s3 = (g_Entities->posY.i.hi - 0x50) - arg0->posY.i.hi;
  temp_s2 = var_s2 - arg0->p