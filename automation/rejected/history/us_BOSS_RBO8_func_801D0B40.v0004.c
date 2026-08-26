/* REJECTED CANDIDATE -- did NOT compile. Kept on purpose.
   record : us:BOSS/RBO8:func_801D0B40
   attempt: 4/4
   from   : mimo-v2.5-free
   origin : src/boss/rbo8/unk_15868.c
   verdict: BUILD FAILED:
17:src/boss/rbo8/unk_15868.c:35: union has no member named `unk5C4'
18:src/boss/rbo8/unk_15868.c:36: union has no member named `unk8B4'
19:src/boss/rbo8/unk_15868.c:37: union has no member named `unk9C'
20:src/boss/rbo8/unk_15868.c:38: union has no member named `unk9C'
21:src/boss/rbo8/unk_15868.c:39: union has no member named `unk5C0'
22:src/boss/rbo8/unk_15868.c:40: union has no member named `unk8B0'
23-[16/31] mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map build/us/bobo1.map -T build/us/bobo1.ld -T config/undefined_syms.us.txt -T build/us/config/undefined_funcs_auto.us.bobo1.txt -T build/us/config/undefined_syms_auto.us.bobo1.txt -o build/us/bobo1.elf
24-[17/31] psx strip build/us/bobo1.elf

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
// Copies angle values from child entities to parent entity's ext fields with offsets
void func_801D0B40(void) {
    Entity* self = g_CurrentEntity;
    Entity* child1 = self->ext.unk5C4; // ext union, 0x548 bytes in
    Entity* child2 = self->ext.unk8B4; // ext union, 0x838 bytes in
    s16 angle1 = child1->ext.unk9C; // ext union, 0x20 bytes in
    s16 angle2 = child2->ext.unk9C; // ext union, 0x20 bytes in
    self->ext.unk5C0 = angle1 + 0x100; // ext union, 0x544 bytes in
    self->ext.unk8B0 = angle2 + 0x180; // ext union, 0x834 bytes in
}