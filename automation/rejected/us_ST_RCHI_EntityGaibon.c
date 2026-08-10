/* REJECTED CANDIDATE -- was REJECTED BEFORE THE BUILD. Kept on purpose.
   record : us:ST/RCHI:EntityGaibon
   attempt: 2/4
   from   : m2c (no model call)
   origin : src/st/rchi/e_gaibon.c
   verdict: quality reject: `->unk27B4` exists in no struct in this tree; use a field from the ENTITY LAYOUT section, or `unkNN` naming the raw offs

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
s32 GetSideToPlayer(?);
? MoveEntity(?);
? PlaySfxPositional(?);
? SetStep(?);
? SetSubStep(?);
extern u16 D_us_8018061E;
extern ? D_us_8018162C;
extern ? D_us_80181640;
extern ? D_us_80181674;
extern ? D_us_80181688;
extern ? D_us_8018169C;
extern ? D_us_801816A8;
extern ? D_us_801816B8;
extern ? D_us_801816CC;
extern ? D_us_801816D8;
extern ? D_us_801816EC;
extern ? D_us_8018171C;
extern s16 PLAYER_posX_i_hi;
extern s16 PLAYER_posY_i_hi;
extern Entity g_Entities_160;
extern Entity g_Entities_224;
extern u16 g_pads_1_pressed;

void EntityGaibon(Entity *arg0) {
     Entity *temp_s2;
     Entity *temp_v0_10;
     Entity *temp_v0_4;
     Entity *temp_v0_6;
     Entity *temp_v0_8;
     s16 temp_s3;
     s16 var_v0_4;
     s16 var_v0_7;
     s16 var_v0_8;
     s32 temp_a0;
     s32 temp_a0_2;
     s32 temp_a0_3;
     s32 temp_s0;
     s32 temp_s3_2;
     s32 temp_s5;
     s32 temp_v0_9;
     s32 temp_v1_12;
     s32 temp_v1_15;
     s32 temp_v1_6;
     s32 temp_v1_8;
     s32 var_s3;
     s32 var_v0_10;
     s32 var_v0_11;
     s32 var_v0_12;
     s32 var_v0_13;
     s32 var_v0_2;
     s32 var_v0_3;
     s32 var_v0_5;
     s32 var_v0_6;
     s32 var_v0_9;
     s32 var_v1;
     s32 var_v1_2;
     s32 var_v1_3;
     u16 temp_v0;
     u16 temp_v0_11;
     u16 temp_v0_5;
     u16 temp_v0_7;
     u16 temp_v1;
     u16 temp_v1_10;
     u16 temp_v1_11;
     u16 temp_v1_13;
     u16 temp_v1_14;
     u16 temp_v1_16;
     u16 temp_v1_17;
     u16 temp_v1_18;
     u16 temp_v1_4;
     u16 temp_v1_5;
     u16 temp_v1_7;
     u16 temp_v1_9;
     u16 var_v0;
     u32 temp_s4;
     u32 temp_s4_2;
     u32 temp_s4_3;
     u32 temp_v0_2;
     u32 temp_v0_3;
     void *temp_v1_2;
     void *temp_v1_3;
 Collider sp10;
 ? var_a0;
 ? var_a0_2;

 if ((arg0->step != 0) && (arg0->unk86 == 0)) {
  temp_v0 = g_api_enemyDefs->unk27B4;
  if (arg0->hitPoints < ((s32) ((s16) temp_v0 + ((u32) (temp_v0 << 0x10) >> 0x1F)) >> 1)) {
   arg0->unk86 = 1;
   SetStep(0xF);
  }
 }
 if ((arg0->flags & 0x100) && ((u16) arg0->step < 0xFU)) {
  arg0->hitboxState = 0;
  SetStep(0xF);
 }
 temp_v1 = arg0->step;
 switch (temp_v1) {  /* switch 1; irregular */
 case 0x0:  /* switch 1 */
  InitializeEntity(g_EInitGaibon);
  CreateEntityFromCurrentEntity(0x1A, arg0 + 0xBC);
  arg0->unkE0 = (s16) (arg0->zPriority + 4);
  SetStep(2);
 default:  /* switch 1 */
block_225:
  temp_v1_2 = (*(&D_us_8018171C + arg0->animCurFrame) * 4) + &D_us_801816EC;
  temp_v1_3 = temp_v1_2 + 1;
  arg0->hitboxOffX = (s16) (s8) temp_v1_2->unk0;
  arg0->hitboxOffY = (s16) (s8) temp_v1_2->unk1;
  arg0->hitboxWidth = temp_v1_3->unk1;
  arg0->hitboxHeight = (temp_v1_3 + 1)->unk1;
  return;
 case 0x2:  /* switch 1 */
  AnimateEntity(&D_us_8018162C, arg0);
  if (arg0->pose == 1) {
   PlaySfxPositional(0x68D);
  }
  if (GetDistanceToPlayerX() < 0x40) {
block_190:
   SetStep(3);
  }
  goto block_225;
 case 0x3:  /* switch 1 */
  temp_v1_4 = arg0->step_s;
  switch (temp_v1_4) {  /* switch 2; irregular */
  case 0:  /* switch 2 */
   arg0->facingLeft = (GetSideToPlayer(3) & 1) ^ 1;
   arg0->unk8C = ratan2((PLAYER_posY_i_hi - 0x20) - arg0->posY.i.hi, PLAYER_posX_i_hi - arg0->posX.i.hi);
   arg0->unk88 = 0;
   arg0->unk80 = 0x60;
   if (arg0->unk86 != 0) {
    arg0->unk80 = 0x30;
   }
   arg0->step_s += 1;
  case 1:  /* switch 2 */
   var_v1 = 0x20000;
   if (arg0->unk86 != 0) {
    var_v1 = 0x40000;
   }
   temp_v0_2 = arg0->unk88 + 0xA00;
   arg0->unk88 = temp_v0_2;
   if ((s32) temp_v0_2 >= var_v1) {
    arg0->unk88 = (u32) var_v1;
   }
   temp_s4 = arg0->unk88;
   arg0->velocityX = (s32) (temp_s4 * rcos((s32) (s16) arg0->unk8C)) >> 0xC;
   arg0->velocityY = (s32) (temp_s4 * rsin((s32) (s16) arg0->unk8C)) >> 0xC;
   MoveEntity();
   AnimateEntity(&D_us_8018162C, arg0);
   if (arg0->pose == 1) {
    PlaySfxPositional(0x68D);
   }
   arg0->facingLeft = (GetSideToPlayer() & 1) ^ 1;
   temp_v1_5 = arg0->unk80 - 1;
   arg0->unk80 = temp_v1_5;
   if ((temp_v1_5 << 0x10) == 0) {
    var_v0 = arg0->step_s + 1;
block_211:
    arg0->step_s = var_v0;
   }
   break;
  case 2:  /* switch 2 */
   MoveEntity(3);
   temp_v1_6 = arg0->velocityX;
   var_v0_2 = temp_v1_6;
   if (temp_v1_6 < 0) {
    var_v0_2 = temp_v1_6 + 0x1F;
   }
   temp_a0 = arg0->velocityY;
   arg0->velocityX = temp_v1_6 - (var_v0_2 >> 5);
   var_v0_3 = temp_a0;
   if (temp_a0 < 0) {
    var_v0_3 = temp_a0 + 0x1F;
   }
   arg0->velocityY = temp_a0 - (var_v0_3 >> 5);
   if (AnimateEntity(&D_us_80181640, arg0) == 0) {
    SetStep(4);
   }
   if (arg0->pose != 1) {

   } else {
block_94:
    PlaySfxPositional(0x68D);
   }
   break;
  }
  goto block_225;
 case 0x4:  /* switch 1 */
  temp_v1_7 = arg0->step_s;
  switch (temp_v1_7) {  /* switch 3; irregular */
  case 0:  /* switch 3 */
   arg0->facingLeft = (GetSideToPlayer(3) & 1) ^ 1;
   temp_s3 = PLAYER_posX_i_hi;
   if (GetSideToPlayer() & 1) {
    var_s3 = temp_s3 + 0x60;
   } else {
    var_s3 = temp_s3 - 0x60;
   }
   arg0->unk8C = ratan2((g_Entities->posY.i.hi - 0x80) - arg0->posY.i.hi, var_s3 - arg0->posX.i.hi);
   arg0->unk88 = 0;
   arg0->unk80 = 0x50;
   if (arg0->unk86 != 0) {
    arg0->unk80 = 0x28;
   }
   arg0->step_s += 1;
  case 1:  /* switch 3 */
   var_v1_2 = 0x20000;
   if (arg0->unk86 != 0) {
    var_v1_2 = 0x40000;
   }
   temp_v0_3 = arg0->unk88 + 0xA00;
   arg0->unk88 = temp_v0_3;
   if ((s32) temp_v0_3 >= var_v1_2) {
    arg0->unk88 = (u32) var_v1_2;
   }
   temp_s4_2 = arg0->unk88;
   arg0->velocityX = (s32) (temp_s4_2 * rcos((s32) (s16) arg0->unk8C)) >> 0xC;
   arg0->velocityY = (s32) (temp_s4_2 * rsin((s32) (s16) arg0->unk8C)) >> 0xC;
   MoveEntity();
   AnimateEntity(&D_us_80181674, arg0);
   if (arg0->pose == 1) {
    PlaySfxPositional(0x68D);
   }
   var_v1_3 = 0xF;
   if (arg0->unk86 != 0) {
    var_v1_3 = 7;
   }
   if (!((s16) arg0->unk80 & var_v1_3)) {
    temp_v0_4 = AllocEntity(&g_Entities_160, &g_Entities_160 + 0x1780);
    if (temp_v0_4 != NULL) {
     if (arg0->unk86 != 0) {
      CreateEntityFromEntity(0x1C, arg0, temp_v0_4);
      var_a0 = 0x655;
     } else {
      CreateEntityFromEntity(0x1B, arg0, temp_v0_4);
      var_a0 = 0x652;
     }
     PlaySfxPositional(var_a0);
     temp_v0_4->posY.i.hi = (u16) temp_v0_4->posY.i.hi - 2;
     if (arg0->facingLeft != 0) {
      temp_v0_4->rotate = 0x220;
      var_v0_4 = (u16) temp_v0_4->posX.i.hi + 0xC;
     } else {
      temp_v0_4->rotate = 0x5E0;
      var_v0_4 = (u16) temp_v0_4->posX.i.hi - 0xC;
     }
     temp_v0_4->posX.i.hi = var_v0_4;
     temp_v0_4->zPriority = arg0->zPriority + 1;
    }
   }
   temp_v0_5 = arg0->unk80 - 1;
   arg0->unk80 = temp_v0_5;
   if ((temp_v0_5 << 0x10) == 0) {
    var_v0 = arg0->step_s + 1;
    goto block_211;
   }
   break;
  case 2:  /* switch 3 */
   MoveEntity(3);
   temp_v1_8 = arg0->velocityX;
   var_v0_5 = temp_v1_8;
   if (temp_v1_8 < 0) {
    var_v0_5 = temp_v1_8 + 0x1F;
   }
   temp_a0_2 = arg0->velocityY;
   arg0->velocityX = temp_v1_8 - (var_v0_5 >> 5);
   var_v0_6 = temp_a0_2;
   if (temp_a0_2 < 0) {
    var_v0_6 = temp_a0_2 + 0x1F;
   }
   arg0->velocityY = temp_a0_2 - (var_v0_6 >> 5);
   if (AnimateEntity(&D_us_80181640, arg0) == 0) {
    SetStep(3);
    if (arg0->unk86 != 0) {
     SetStep(8);
    }
   }
   if (arg0->pose == 1) {
    goto block_94;
   }
   break;
  }
  goto block_225;
 case 0x5:  /* switch 1 */
  temp_v1_9 = arg0->step_s;
  switch (temp_v1_9) {  /* switch 4; irregular */
  case 0:  /* switch 4 */
   arg0->animCurFrame = 9;
   arg0->velocityX = 0;
   arg0->velocityY = 0;
   arg0->step_s += 1;
  case 1:  /* switch 4 */
   MoveEntity(3);
   arg0->velocityY += 0x1800;
   if ((PLAYER_posY_i_hi - arg0->posY.i.hi) < 0