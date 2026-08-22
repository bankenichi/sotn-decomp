#!/usr/bin/env python3
"""Does `x->field` exist in the struct `x` actually points at?

WHY THIS EXISTS
    The first member gate compared every `->name` against a UNION of every
    struct member in the tree. It caught names that exist NOWHERE (`field1C`,
    `partA`) and missed everything else, which is to say it missed what the
    fleet actually produces.

    First live run on mimo, 2026-08-09: 20 generations, 20 build failures, and
    the gate caught ZERO of them.

        4x  structure has no member named `unk1C
        3x  structure has no member named `unk1E
        1x  structure has no member named `scaleY
        1x  structure has no member named `scaleX

    Every one of those names is legal somewhere. `scaleX` and `scaleY` are
    real Entity fields at 0x1A and 0x1C. The code that failed was

        Primitive* prim;
        ...
        prim->next->scaleX = 0x20;

    The model took Entity's field names and applied them to a Primitive. The
    name is real; the STRUCT is wrong. No union-of-all-names check can see
    that, because both sides of the mistake are in the union.

WHAT THIS DOES
    Resolves the declared type of each pointer variable and validates the
    member against THAT struct, following chains through typed fields, so
    `prim->next->scaleX` is checked against Primitive rather than against
    everything.

    Conservative by construction. A variable whose type cannot be resolved is
    skipped entirely: a false rejection costs a whole attempt, and this runs
    before the build where nothing else can catch a mistake it makes.

Usage:
    python3 automation/member_types.py --check <file.c>
    python3 automation/member_types.py --self-test
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX = REPO / "automation" / "index.us.json"

# `Entity* self`, `Entity *self`, `struct Primitive *p` -- declarations and
# parameters both.
RX_DECL = re.compile(
    r"\b(?:struct\s+|const\s+)*([A-Z]\w+)\s*\*\s*(\w+)\s*(?=[,;)=\[])")
# Stack values use `.`, and missing them let `Collider col; col.hit` reach the
# compiler even though Collider is a trusted, completely modelled struct.
RX_VALUE_DECL = re.compile(
    r"\b(?:struct\s+|const\s+)*([A-Z]\w+)\s+(\w+)\s*(?=[,;=\[])")
RX_ACCESS = re.compile(r"\b(\w+)((?:\s*(?:->|\.)\s*\w+)+)")
RX_HOP = re.compile(r"(?:->|\.)\s*(\w+)")
RX_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
RX_FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*$", re.M)
RX_PTR_TYPE = re.compile(r"^(?:struct\s+|const\s+)*([A-Z]\w+)\s*\*+$")
# `#define prevTailPart ext.diploTail.prevPart` makes `self->prevTailPart`
# legal without any such member existing. Without this, e_diplocephalus_tail.c
# -- which builds -- produced two findings.
RX_DEFINE = re.compile(r"^\s*#\s*define\s+(\w+)", re.M)

# Structs the index models FAITHFULLY, DERIVED BY MEASUREMENT, not assumed:
# each produced ZERO findings across every .c file outside src/saturn in a
# tree sitting at 81/81 -- code the compiler has already accepted.
#
# THIS LIST IS THE ENTIRE SAFETY ARGUMENT. Unrestricted, the check reported 348
# findings on known-good code. Two causes, one mine and one the index's:
#
#   mine    declarations were pooled per FILE, so a `PrimLineG2* prim` in one
#           function retyped the `Primitive* prim` in another. Scoping per
#           function removed 108 of them and took Entity to ZERO.
#   index   the PSY-Q types (SVECTOR, TILE, LINE_G2/G4, POLY_FT4, DRAWENV,
#           CVECTOR) come from SDK headers the index models badly. Gating on
#           those would reject correct code and burn an attempt each time.
#
# Entity is the one that matters: 48,951 uses, zero false positives, and the
# type nearly every generated function takes as its parameter.
#
# NOT trusted, and worth stating plainly: `Primitive`, at 2 false positives in
# 35,402 uses. That is the struct in the live failure this file was written
# for (`prim->next->scaleX`), so THAT case is still not caught. Trading a
# certain false rejection for a possible catch is the wrong way round when the
# gate runs before the build and nothing downstream can undo it.
#
# Regenerate after any index rebuild; src/saturn is excluded because it has
# its own 0xB8 Entity in sattypes.h.
TRUSTED = frozenset({
    "Accessory", "AnimParam", "AnimationFrame", "CdFile", "Collider",
    "DECENV", "DISPENV", "DamageParam", "DopWeaponAnimation", "EnemyDef",
    "Entity", "EntranceCascadePrim", "EquipMenuHelper", "Equipment",
    "FireShieldDragon", "FrozenShadePrim", "GfxBank", "GfxLoad",
    "ItemPrimitiveParams", "LayerDef", "LayoutEntity", "MenuContext",
    "NowLoadingModel", "ObjInit", "ObjInit2", "POLY_G4", "POLY_GT3", "Pad",
    "PlayerDraw", "Point16", "Pos", "PrimLineG2", "PrimWeapon017",
    "PspUtilitySavedataParam", "RECT", "RicSubwpnIconParams", "RoomHeader",
    "SPRT", "SPRT_16", "SVEC4", "SaveData", "ServantSfxEventDesc",
    "SimFile", "SpritePart", "SpuCommonAttr", "SpuReverbAttr",
    "SpuVoiceAttr", "StHEADER", "SubweaponDef", "Unkstruct_8006C3C4",
    "Unkstruct_800ADEF0", "VagAtr", "WeaponAnimation", "WeaponParams",
})

_INDEX_CACHE: dict | None = None


def _index() -> dict:
    global _INDEX_CACHE
    if _INDEX_CACHE is None:
        try:
            _INDEX_CACHE = json.loads(INDEX.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _INDEX_CACHE = {}
    return _INDEX_CACHE


def struct_fields() -> dict[str, dict[str, str]]:
    """{struct name: {member name: member type}}, Entity included."""
    idx = _index()
    out: dict[str, dict[str, str]] = {}
    for name, flds in (idx.get("structs") or {}).items():
        out[name] = {f["name"]: (f.get("type") or "")
                     for f in (flds or []) if f.get("name")}
    ent = {}
    for _off, f in (idx.get("entity", {}).get("fields") or {}).items():
        if isinstance(f, dict) and f.get("name"):
            ent[f["name"]] = f.get("type") or ""
    if ent:
        # The index carries Entity separately from `structs`; merge rather than
        # replace so a struct-table Entity, if one appears, is not lost.
        out.setdefault("Entity", {}).update(ent)
    return out


def entity_offsets() -> dict[int, str]:
    """{offset: field name} for Entity, used to turn unkNN into a real name."""
    out = {}
    for off, f in (_index().get("entity", {}).get("fields") or {}).items():
        if isinstance(f, dict) and f.get("name"):
            try:
                out[int(off, 16)] = f["name"]
            except ValueError:
                continue
    return out


def declared_types(code: str) -> dict[str, str]:
    """{variable: struct name} for pointer and stack-value declarations."""
    known = struct_fields()
    out = {}
    for typ, var in RX_DECL.findall(code):
        if typ in known:
            out[var] = typ
    for typ, var in RX_VALUE_DECL.findall(code):
        if typ in known:
            out[var] = typ
    return out


def _declared_type_ranges(code: str) -> list[tuple[str, str, int, int]]:
    """Declarations with the lexical range in which each one is visible."""
    known = struct_fields()
    stack: list[int] = []
    closes: dict[int, int] = {}
    for pos, char in enumerate(code):
        if char == "{":
            stack.append(pos)
        elif char == "}" and stack:
            closes[stack.pop()] = pos

    def scope_end(pos: int) -> int:
        active = [(start, end) for start, end in closes.items()
                  if start < pos < end]
        return max(active, default=(-1, len(code)))[1]

    out = []
    for rx in (RX_DECL, RX_VALUE_DECL):
        for match in rx.finditer(code):
            typ, var = match.groups()
            if typ in known:
                out.append((var, typ, match.start(), scope_end(match.start())))
    return sorted(out, key=lambda item: item[2])


def _declared_type_at(ranges: list[tuple[str, str, int, int]],
                      var: str, pos: int) -> str | None:
    visible = [(start, typ) for name, typ, start, end in ranges
               if name == var and start <= pos < end]
    return max(visible, default=(-1, None))[1]


RX_FUNC_HEAD = re.compile(
    r"^[A-Za-z_][\w \t*]*\b(\w+)\s*\([^;{]*\)\s*\{", re.M)


def function_bodies(code: str) -> list[str]:
    """Each top-level function body, separately.

    DECLARATIONS ARE FUNCTION-SCOPED AND SO IS THE CHECK. Building one map per
    FILE lets a `PrimLineG2* prim` in one function silently retype the
    `Primitive* prim` in another. src/boss/bo6/us_3E79C.c declares both, and
    the flat version produced 16 findings there against code that compiles
    -- a self-inflicted false positive, not a gap in the index.
    """
    out = []
    for m in RX_FUNC_HEAD.finditer(code):
        i = code.index("{", m.start())
        depth, j = 0, i
        while j < len(code):
            if code[j] == "{":
                depth += 1
            elif code[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append(code[m.start():j + 1])
    return out or [code]


def check(code: str) -> list[str]:
    """Members used on a struct that does not have them.

    Returns human-readable findings, empty when clean.
    """
    known = struct_fields()
    if not known:
        return []                        # no index: do not guess, do not reject
    code = RX_COMMENT.sub(" ", RX_FENCE.sub("", code or ""))
    macros = set(RX_DEFINE.findall(code))
    offs = entity_offsets()
    seen: set[tuple[str, str]] = set()
    out: list[str] = []
    for body in function_bodies(code):
        out += _check_scope(body, known, macros, offs, seen)
    return out


def _check_scope(code: str, known: dict, macros: set, offs: dict,
                 seen: set) -> list[str]:
    ranges = _declared_type_ranges(code)
    if not ranges:
        return []
    out: list[str] = []
    for access in RX_ACCESS.finditer(code):
        var, chain = access.groups()
        cur = _declared_type_at(ranges, var, access.start())
        if not cur or cur not in TRUSTED:
            continue                     # unknown or unmodelled: never guess
        for member in RX_HOP.findall(chain):
            fields = known.get(cur)
            if fields is None or cur not in TRUSTED:
                break                    # unmodelled struct: stop, no report
            if member in macros:
                break                    # a macro, not a member
            if member not in fields:
                if (cur, member) in seen:
                    break
                seen.add((cur, member))
                out.append(_finding(cur, member, known, offs))
                break                    # one report per chain; the rest is
                                         # meaningless once the type is wrong
            nxt = RX_PTR_TYPE.match((fields.get(member) or "").strip())
            if nxt and nxt.group(1) in known:
                cur = nxt.group(1)       # follow prim->next->...
            else:
                break                    # not a struct pointer: chain ends
    return out


def _finding(struct: str, member: str, known: dict, offs: dict) -> str:
    msg = f"`{struct}` has no member `{member}`"
    # ORDER MATTERS. `unkNN` names an OFFSET, so resolving it against the
    # Entity layout is the answer. Falling through to "which struct owns this
    # name" instead produced `unk1C belongs to AxePrim, Collider, MenuContext`
    # -- three unrelated structs that merely happen to have their own unk1C.
    # That is noise dressed as guidance.
    m = re.match(r"^unk([0-9A-Fa-f]{1,3})$", member)
    if m and struct == "Entity":
        off = int(m.group(1), 16)
        if off in offs:
            return msg + f"; offset 0x{off:02X} is `{offs[off]}`"
        prior = [o for o in sorted(offs) if o <= off]
        if prior:
            return (msg + f"; 0x{off:02X} falls inside `{offs[prior[-1]]}` "
                    f"(0x{prior[-1]:02X})")
        return msg
    # Otherwise the most useful thing is which struct DOES have it, because the
    # mistake is nearly always a field borrowed from the wrong type.
    owners = [s for s, f in known.items() if member in f and s != struct]
    if owners:
        msg += (f"; `{member}` belongs to "
                + ", ".join(sorted(owners)[:3])
                + ". Use a member of " + struct)
    else:
        sample = sorted(known.get(struct, {}))[:6]
        if sample:
            msg += f"; its members include {', '.join(sample)}"
    return msg


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    known = struct_fields()
    print("\nthe index gives us the structs to check against")
    ck("Entity" in known and "scaleX" in known["Entity"],
       f"Entity has scaleX ({len(known.get('Entity', {}))} fields)")
    ck("Primitive" in known and "scaleX" not in known["Primitive"],
       "Primitive does NOT have scaleX")

    print("\nTHE LIVE FAILURE IS NOT COVERED, AND THE TEST SAYS SO")
    # src/st/rchi/e_breakable.c:66-67. `Primitive` is NOT in TRUSTED (2 false
    # positives in 35,402 uses), so this is knowingly missed. Asserting the
    # catch here would be asserting against a wish.
    real = ("void EntityBreakableDebris(Entity* self) {\n"
            "    Primitive* prim;\n"
            "    prim->next->scaleX = 0x20;\n"
            "    prim->priority = 0x72;\n"
            "}\n")
    ck(check(real) == [],
       f"Primitive is untrusted, so nothing is claimed ({check(real)})")
    ck("Primitive" not in TRUSTED, "and TRUSTED reflects that")
    # It IS caught the moment the index models Primitive well enough to trust.
    import copy
    saved = globals()["TRUSTED"]
    try:
        globals()["TRUSTED"] = frozenset(set(saved) | {"Primitive"})
        r = check(real)
        ck(len(r) == 1 and "scaleX" in r[0] and "Primitive" in r[0],
           f"trusting Primitive would catch it ({r})")
        ck(not any("priority" in x for x in r),
           "and a real Primitive member is still not reported")
    finally:
        globals()["TRUSTED"] = saved

    print("\nthe chain is followed through typed pointer fields")
    # PrimLineG2 IS trusted and its `next` is a typed pointer, so the hop must
    # stay in that struct rather than falling back to a union of everything.
    ck(check("void f(void) { PrimLineG2* p; p->next->x0 = 1; }") == [],
       "a valid two-hop access passes")

    print("\ndeclarations are FUNCTION-scoped, not file-scoped")
    # Pooling them per file let one function's `PrimLineG2* prim` retype
    # another's, which alone produced 108 of the original 348 false positives.
    two = ("void a(void) { Entity* p; p->posX = 1; }\n"
           "void b(void) { PrimLineG2* p; p->x0 = 2; }\n")
    ck(check(two) == [], f"each `p` keeps its own type ({check(two)})")

    print("\nEntity's own members still validate")
    ck(check("void f(Entity* e) { e->scaleX = 1; e->posX = 2; }") == [],
       "real Entity fields pass")
    bad = check("void f(Entity* e) { e->unk1C = 1; }")
    ck(bad and "0x1C" in bad[0] and "scaleY" in bad[0],
       f"unk1C is resolved to scaleY ({bad[0] if bad else ''})")

    print("\nvalue-member accesses validate against their declared struct")
    bad_dot = check("void f(void) { Collider col; if (col.hit & 1) return; }")
    ck(bad_dot and "Collider" in bad_dot[0] and "hit" in bad_dot[0],
       f"Collider col; col.hit is rejected before compilation ({bad_dot})")
    ck(check("void f(void) { Collider col; if (col.effects & 1) return; }")
       == [], "the real Collider.effects member still passes")
    shadowed = """void f(Collider* item) {
        if (item->effects & 1) return;
        { Primitive item; item.drawMode = 0; }
        if (item->effects & 2) return;
    }"""
    ck(check(shadowed) == [],
       "a nested value declaration does not retype the outer pointer")

    print("\nunresolvable things are SKIPPED, never guessed at")
    # A false rejection costs a whole attempt, and this gate runs before the
    # build where nothing downstream can correct it.
    ck(check("void f(void) { mystery->whatever = 1; }") == [],
       "an undeclared variable is skipped")
    ck(check("void f(UnknownType* u) { u->whatever = 1; }") == [],
       "an unknown struct type is skipped")
    ck(check("void f(Entity* e) { e->ext.breakableDebris.rotSpeed = 1; }")
       == [], "an ext union hop is not misreported")

    print("\nthe same mistake is reported once, not once per use")
    dup = check("void f(Entity* e) { e->nope = 1; e->nope = 2; }")
    ck(len(dup) == 1, f"deduplicated ({len(dup)})")

    print("\ncomments cannot create a finding")
    ck(check("/* p->scaleX is wrong */\nvoid f(void) { Primitive* p;"
             " p->priority = 1; }") == [],
       "prose in a comment is ignored")

    print()
    if fails:
        print(f"{len(fails)} FAILED:")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", help="a .c file to validate")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.check:
        p = Path(a.check)
        if not p.is_file():
            print(f"no such file: {p}", file=sys.stderr)
            return 2
        found = check(p.read_text(errors="ignore"))
        for f in found:
            print("  " + f)
        print(f"\n{len(found)} finding(s)")
        return 1 if found else 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
