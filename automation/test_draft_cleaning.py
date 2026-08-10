#!/usr/bin/env python3
"""Does the draft reach the model clean, and does the offset table tell the truth?

WHY THIS EXISTS
    Two separate defects, both of them the HARNESS producing bad C rather
    than the model inventing it.

    1. The prompt taught `ext.ILLEGAL` in three places while quality_gate
       rejected it unconditionally. The model was being instructed to write
       the thing that would get its answer thrown away, and the worker logs
       show one degenerating into a loop emitting the exact template the
       prompt supplied. Fixed by deleting the offer, not by hardening
       the gate: the gate was already right.

    2. `resolve_unk_offsets` applied the Entity layout to every `->unkNN` in
       the draft regardless of what the pointer actually was. Measured over
       45 real m2c drafts on 2026-08-09, 554 accesses:

           Entity *              20   3.6%
           another named type   473  85.4%   (void* 422, SeqStruct 26,
                                              Primitive 20, Collider 1, ...)
           undeclared            61  11.0%

       BUT DO NOT QUOTE 85% AS THE DEFECT RATE. That is per ACCESS; the table
       is per OFFSET, many accesses collapse onto one line, and `void *` is
       m2c's "I could not type this" rather than a different struct -- for an
       entity function the void* usually IS the entity. Scored per table line
       over the same 45 drafts, 262 lines:

           refused, provably wrong struct    15   6%
           hedged, mixed pointer types        4   2%
           hedged, m2c said void*           135
           confident / interior / ext       108

       So the honest claim is 6% flatly wrong and 2% unknowable, not 85%.
       On func_us_801A7DC0, 3 lines of 29 were wrong (offsets reached only
       through `u8 *` script pointers) and 2 were mixed. An earlier draft of
       this file said 24 of 29; that came from a classifier that lumped
       `void *` in with the named structs, and it was wrong.

HOW THESE TESTS ARE WRITTEN
    Every assertion runs the real function and inspects its OUTPUT. None of
    them grep worker_direct.py for a phrase. Five tests in this project have
    previously passed by matching their own docstring or assertion text, so
    source-text matching is banned here on purpose.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "win"))
os.environ.setdefault("MODEL_BACKEND", "zen")

import worker_direct as wd  # noqa: E402

FAILS = []


def check(cond, label):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


# A draft in the shape m2c really produces: the entity arrives as `void *`
# (m2ctx could not resolve it), alongside genuinely-typed other structs.
REAL_SHAPE = """void func_us_80100000(Entity *self, Primitive *prim) {
    void *temp_s1;
    u8 *script;
    Collider col;
    temp_s1 = self;
    self->unk24 = 1;
    self->unk1C = 2;
    self->unk88 = 3;
    self->unk0A = 4;
    prim->unk24 = 5;
    script->unk2 = 6;
    temp_s1->unk2C = 7;
}"""


def main():
    print("clean_draft rewrites ONLY what it can prove")
    out, notes = wd.clean_draft(REAL_SHAPE)
    check("self->zPriority" in out, "Entity-typed access is resolved in place")
    check("self->scaleY" in out, "second Entity offset resolved too")
    check(len(notes) == 2, f"and both are reported ({len(notes)} reported)")
    check("prim->unk24" in out,
          "a Primitive at the SAME offset 0x24 is left alone -- the offset "
          "does not carry its meaning, the pointer does")
    check("script->unk2" in out, "a u8* script pointer is left alone")
    check("temp_s1->unk2C" in out,
          "a void* is left alone by the in-place rewrite: an edit cannot be "
          "weighed by the model, so it must be certain, and void* is not")
    check("self->unk88" in out,
          "0x7C+ is the ext union, whose names depend on the entity variant, "
          "so it is not resolvable from the Entity layout")
    check("self->unk0A" in out,
          "an interior offset has no field to name and stays put")
    check(wd.clean_draft(out)[0] == out,
          "idempotent: the prompt is rebuilt on every retry")
    check(wd.clean_draft("")[0] == "", "empty draft does not crash")
    check(wd.clean_draft("void f(void) { return; }")[1] == [],
          "a draft with no Entity is returned untouched")

    print("\nthe offset table is honest about which pointer it read")
    cleaned, _ = wd.clean_draft(REAL_SHAPE)
    tbl = wd.resolve_unk_offsets(cleaned)
    line = {}
    for l in tbl.splitlines():
        m = re.match(r"\s*unk([0-9A-F]{2})\s", l)
        if m:
            line[int(m.group(1), 16)] = l

    check(0x24 in line and "zPriority" not in line[0x24],
          "0x24 is reached only through a Primitive here, so the table must "
          "NOT answer zPriority")
    check(0x24 in line and "NOT an Entity" in line[0x24],
          "it says so explicitly rather than staying silent")
    check(0x24 in line and "Primitive" in line[0x24],
          "and names the actual type so the model can go look it up")
    check(0x2C in line and "step" in line[0x2C],
          "a void* still gets the translation: m2c not knowing is not "
          "evidence against, and for entity functions it usually IS the entity")
    check(0x2C in line and "void" in line[0x2C],
          "but the uncertainty is stated, not hidden")
    check(0x88 in line and "ext union" in line[0x88],
          "ext offsets are named as such")
    check(0x88 in line and "ILLEGAL" not in line[0x88],
          "and the table does not hand back the placeholder")

    print("\nmixed pointers are not silently resolved one way")
    # The entity side must NOT be `Entity *`, because clean_draft would then
    # rewrite it in place and the offset would stop being mixed at all -- the
    # mixed case only exists when the entity arrives as `void *`, which is
    # exactly how it showed up on func_us_801A7DC0 (unk01, reached through
    # both a void* entity and six u8* script pointers).
    mixed = """void f(void *arg0) {
    void *ent;
    u8 *script;
    ent->unk30 = 1;
    script->unk30 = 2;
}"""
    c2, _ = wd.clean_draft(mixed)
    t2 = wd.resolve_unk_offsets(c2)
    l30 = [l for l in t2.splitlines() if re.match(r"\s*unk30\s", l)]
    check(bool(l30) and "CAUTION" in l30[0],
          "0x30 reached through BOTH a void* entity and a u8* is flagged, "
          "not quietly given the Entity answer")
    check(bool(l30) and "u8" in l30[0], "and the other type is named")

    print("\nand the Entity-only case is still answered plainly")
    solo = """void f(Entity *self) {
    self->unk34 = 1;
}"""
    c3, n3 = wd.clean_draft(solo)
    check("CAUTION" not in wd.resolve_unk_offsets(c3),
          "no caution is attached when there is nothing to be cautious about")
    check(len(n3) == 1, "the single Entity access is still resolved")

    print("\nthe prompt no longer offers ILLEGAL as a way out")
    rec = {"function": "EntityDummy", "overlay": "no0", "build": "us"}
    ctx = {"draft": REAL_SHAPE, "asm": "/* 0 0 0 */ lw $v0, 0x24($s0)\n",
           "decls": [], "src_rel": "src/st/no0/e_dummy.c"}
    prompt = wd.build_prompt(rec, ctx)
    check(re.search(r"ext\s*\.\s*ILLEGAL\s*\.\s*[us]\d+\s*\[", prompt) is None,
          "no usable ext.ILLEGAL template survives anywhere in a real prompt")
    check("ILLEGAL" not in wd.ENTITY_LAYOUT,
          "the entity layout section does not mention it at all")

    print("\nthe gate and the prompt finally agree")
    # Call the REAL gate. An earlier version of this test re-implemented the
    # check inline and so asserted only that its own `if` worked.
    asm = "/* 0 0 0 */ lw $v0, 0x88($s0)\n"
    bad = "void EntityDummy(Entity* self) { self->ext.ILLEGAL.u16[6] = 1; }"
    good = "void EntityDummy(Entity* self) { self->ext.generic.unk88 = 1; }"
    hits = [p for p in wd.quality_gate(bad, asm) if "ILLEGAL" in p]
    check(bool(hits),
          "the gate still rejects ILLEGAL -- removing it from the prompt must "
          "not be mistaken for permitting it in output")
    check(not [p for p in wd.quality_gate(good, asm) if "ILLEGAL" in p],
          "and it does not fire on code that avoids it")

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED:")
        for f in FAILS:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
