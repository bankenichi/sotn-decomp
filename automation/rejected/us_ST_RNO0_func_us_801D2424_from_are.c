/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:ST/RNO0:func_us_801D2424_from_are
   attempt: 1/4
   from   : deterministic transplant
   origin : src/st/rno0/e_gorgon.c
   verdict: BUILD FAILED:
169:FAILED: build/us/strno0.elf
170-mipsel-linux-gnu-ld -nostdlib --no-check-sections  -Map build/us/strno0.map -T build/us/strno0.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.strno0.txt -T build/us/config/undefined_syms_auto.us.strno0.txt -o build/us/strno0.elf
171-mipsel-linux-gnu-ld: build/us/src/st/rno0/unk_4F968.c.o: in function `func_us_801D15C0':
172:src/st/rno0/unk_4F968.c:(.text+0x2220): undefined reference to `func_us_801D2424_from_are'
173-ninja: build stopped: subcommand failed.
174-exit status 1

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
static void func_us_801D2424_from_are(Pos* arg0, s16 arg1, Point16* arg2, Pos* arg3,
                             s16 arg4, Point16* arg5, Primitive* prim) {
    prim->x0 = prim->x1 = arg0->x.i.hi;
    prim->y0 = prim->y1 = arg0->y.i.hi;
    prim->x2 = prim->x3 = arg3->x.i.hi;
    prim->y2 = prim->y3 = arg3->y.i.hi;
    if (g_CurrentEntity->facingLeft) {
        prim->x0 += FLT_TO_I(arg2->x * rcos(arg1));
        prim->x1 -= FLT_TO_I(arg2->y * rcos(arg1));
        prim->x2 += FLT_TO_I(arg5->x * rcos(arg4));
        prim->x3 -= FLT_TO_I(arg5->y * rcos(arg4));
    } else {
        prim->x0 -= FLT_TO_I(arg2->x * rcos(arg1));
        prim->x1 += FLT_TO_I(arg2->y * rcos(arg1));
        prim->x2 -= FLT_TO_I(arg5->x * rcos(arg4));
        prim->x3 += FLT_TO_I(arg5->y * rcos(arg4));
    }
    prim->y0 -= FLT_TO_I(arg2->x * rsin(arg1));
    prim->y1 += FLT_TO_I(arg2->y * rsin(arg1));
    prim->y2 -= FLT_TO_I(arg5->x * rsin(arg4));
    prim->y3 += FLT_TO_I(arg5->y * rsin(arg4));
}