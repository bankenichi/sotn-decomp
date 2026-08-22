#!/usr/bin/env python3
"""Which `ext` union offsets does generated code ask for that no variant names?

WHY THIS EXISTS
    #109 called the bottleneck "Entity member naming" and cited two m2c
    failures:

        `Entity` has no member `unkEC`; 0xEC falls inside `unkB8` (0xB8)
        `Entity` has no member `unk86`;  0x86 falls inside `ext`   (0x7C)

    Both descriptions are wrong, in ways that would have sent the work in the
    wrong direction.

    `Entity` is `size = 0xBC`. `unkB8` is a named 4-byte `struct Entity*`, not
    an unnamed blob, and 0xEC is not inside it -- 0xEC is 0x30 bytes PAST THE
    END of the struct. Nothing can be named at 0xEC, because whatever that
    pointer pointed at was not an Entity. That is a wrong-type diagnosis, not a
    missing-name one, and no amount of header naming would have fixed it.

    `ext` at 0x7C is not an unnamed blob either. It is a union of ~100 named
    per-entity-type variants (`ET_Dodo`, `ET_JackOBones`, ...), each declaring
    its own fields at ABSOLUTE Entity offsets from 0x7C to 0xB7. An access at
    0x86 is not unnameable; it means no variant has been declared for THIS
    entity, or the right variant is missing that one field.

    So the work is not "name the blob". It is, per entity type, either point at
    the variant that already fits or add the field that is missing. That is a
    header change, 0x3C bytes wide, and the worker prompt already tells the
    model to stop and say so rather than guess:

        "If no named field covers the offset, say so in one line and stop: the
         union needs a field added, which is a header change and not yours to
         guess."

    The model obeying that instruction is the harness working. But nobody was
    reading the refusals, so the header change never got made and the same
    functions failed again. This turns those refusals into a ranked worklist.

WHAT THIS DOES
    Parses the Ext union and every ET_ variant out of include/entity.h, exactly,
    including anonymous bitfield padding (`s16 : 16;`) which reserves space but
    covers nothing. Then scans generated C for offsets at 0x7C+ -- both m2c's
    `->unkNN`, the `ext.ILLEGAL.<type>[<i>]` placeholder, and raw byte-pointer
    offsets rooted at a declared Entity pointer. It uses the same arithmetic
    worker_direct uses and reports, per function:

        which variants already cover every offset it wants   (reuse: free)
        which named Ext expressions start at a raw offset    (replace the cast)
        which offsets no variant covers at all               (header change)

    Evidence, not speculation: it reads code a model actually produced for a
    real function, not offsets guessed from a range.

WHAT IT DOES NOT DO
    It cannot tell you the SEMANTIC name of a field, or whether two entities
    sharing an offset mean the same thing by it. It ranks and locates the work.
    Naming is a read of the asm and stays human.

    It also does not write to entity.h. Adding a union member is codegen-neutral
    only while the variant stays within 0x3C bytes; past that Entity grows and
    all 81 hashes change. That check belongs to a build, not to this.

Usage:
    python3 automation/ext_demand.py                # ranked demand report
    python3 automation/ext_demand.py --variants     # inventory of ET_ variants
    python3 automation/ext_demand.py --function NAME
    python3 automation/ext_demand.py --self-test
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENTITY_H = REPO / "include" / "entity.h"
GAME_H = REPO / "include" / "game.h"
GEN_DIRS = (REPO / "automation" / "candidates", REPO / "automation" / "rejected")

EXT_BASE = 0x7C
# ext ENDS at 0xB8, where the named `struct Entity* unkB8` begins. Entity itself
# runs to 0xBC. Using the struct end as the union end counted EntityRelicOrb's
# `->unkB8` as ext demand -- and 0xB8 is already named, so that would have sent
# someone to add a union field for a member that exists. The two constants are
# separate because they answer different questions.
EXT_END = 0xB8
ENTITY_END = 0xBC

# Widths for the `ext.ILLEGAL.<type>[<index>]` placeholder m2c emits, and for
# working out how many bytes a declared field covers.
WIDTH = {
    "u8": 1, "s8": 1, "char": 1,
    "u16": 2, "s16": 2, "short": 2,
    "u32": 4, "s32": 4, "int": 4, "long": 4, "f32": 4, "float": 4,
}

# The body must not contain a top-level `}`, or a non-greedy `(.*?)` walks from
# the FIRST `typedef struct {` in the file all the way to the first `} ET_...;`,
# swallowing every unrelated struct in between. That is how the first version
# reported `unk_PlatelordStruct`'s 0x00-based fields as ET_ variant fields, and
# then decided offset 0x00 was "covered" ext space. One nested brace level is
# allowed because a few variants declare an inline struct or union.
RX_ET_STRUCT = re.compile(
    r"typedef\s+struct\s*\{((?:[^{}]|\{[^{}]*\})*)\}\s*(ET_\w+)\s*;", re.S)
RX_EXT_UNION = re.compile(
    r"typedef\s+union\s*\{\s*//\s*offset=0x7C(.*?)\}\s*Ext\s*;", re.S)
RX_UNION_MEMBER = re.compile(r"^\s*(ET_\w+)\s+(\w+)\s*;", re.M)
# `/* 0x86 */ s16 laserTimer;` -- the offset comment is the authority. Fields
# without one are skipped rather than guessed at; entity.h annotates them all.
RX_FIELD = re.compile(r"/\*\s*(0x[0-9A-Fa-f]+)\s*\*/\s*([^;/][^;]*);")
# Anonymous bitfield: `s16 : 16;`. Reserves bytes, names nothing. Counting it as
# coverage would report a gap as already solved, which is the expensive error.
RX_ANON_BITFIELD = re.compile(r"^\s*\w+\s*:\s*\d+\s*$")
RX_NAME = re.compile(r"(\w+)\s*(?:\[[^\]]*\])*\s*$")

RX_UNK = re.compile(r"->\s*(?:ext\s*\.\s*)?unk([0-9A-Fa-f]{2,3})\b")
RX_ILLEGAL = re.compile(
    r"ext\s*\.\s*ILLEGAL\s*\.\s*(u8|s8|u16|s16|u32|s32)\s*\[\s*"
    r"(0[xX][0-9A-Fa-f]+|\d+)\s*\]")
RX_ENTITY_DECL = re.compile(r"\bEntity\s*\*\s*(\w+)")
RX_RAW_INDEX = re.compile(
    r"(?P<address>&\s*)?\(\(\s*(?P<type>u8|s8|u16|s16|u32|s32|char)\s*\*\s*\)"
    r"\s*(?P<base>\w+)\s*\)\s*\[\s*(?P<offset>0[xX][0-9A-Fa-f]+|\d+)\s*\]")
RX_RAW_ADD = re.compile(
    r"\(\s*(?:u8|s8|char)\s*\*\s*\)\s*(?P<base>\w+)\s*\+\s*"
    r"(?P<offset>0[xX][0-9A-Fa-f]+|\d+)")
RX_COMMENT_OR_LITERAL = re.compile(
    r"/\*.*?\*/|//[^\n]*|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", re.S)


def _decl_size(decl: str) -> int:
    """Bytes a declaration covers. 0 when the type is not recognised."""
    m = re.search(r"\[\s*(0[xX][0-9A-Fa-f]+|\d+)\s*\]", decl)
    count = int(m.group(1), 0) if m else 1
    if "*" in decl:
        return 4 * count
    for tok in decl.replace("*", " ").split():
        if tok in WIDTH:
            return WIDTH[tok] * count
    return 0


def parse_variants(text: str | None = None) -> dict[str, dict]:
    """ET_ name -> {"fields": {offset: name}, "covered": set(offset), "end": int}.

    `covered` is every BYTE a named field occupies, so a demand at 0x87 landing
    inside a s16 at 0x86 counts as covered. Padding is excluded deliberately.
    """
    text = ENTITY_H.read_text(encoding="utf-8", errors="replace") if text is None else text
    out: dict[str, dict] = {}
    for body, name in RX_ET_STRUCT.findall(text):
        fields: dict[int, str] = {}
        widths: dict[int, int] = {}
        covered: set[int] = set()
        end = EXT_BASE
        for off_s, decl in RX_FIELD.findall(body):
            off = int(off_s, 16)
            size = _decl_size(decl)
            end = max(end, off + max(size, 1))
            if RX_ANON_BITFIELD.match(decl):
                continue                       # padding: reserves, names nothing
            m = RX_NAME.search(decl.strip())
            if not m:
                continue
            fields[off] = m.group(1)
            widths[off] = size or 1
            covered.update(range(off, off + (size or 1)))
        if fields:
            out[name] = {"fields": fields, "widths": widths,
                         "covered": covered, "end": end}
    return out


def parse_union(text: str | None = None) -> dict[str, str]:
    """Ext member name -> ET_ type, for the variants actually reachable."""
    text = ENTITY_H.read_text(encoding="utf-8", errors="replace") if text is None else text
    m = RX_EXT_UNION.search(text)
    if not m:
        return {}
    return {member: et for et, member in RX_UNION_MEMBER.findall(m.group(1))}


def raw_entity_accesses(code: str) -> list[dict]:
    """Raw byte-pointer offsets whose base is provably an Entity pointer."""
    code = RX_COMMENT_OR_LITERAL.sub(" ", code or "")
    entity_vars = set(RX_ENTITY_DECL.findall(code)) | {"g_CurrentEntity"}
    out = []
    occupied = []
    for match in RX_RAW_INDEX.finditer(code):
        base = match.group("base")
        if base not in entity_vars:
            continue
        off = int(match.group("offset"), 0)
        if EXT_BASE <= off < EXT_END:
            out.append({"base": base, "offset": off,
                        "width": 0 if match.group("address") else
                                 WIDTH[match.group("type")],
                        "address_only": bool(match.group("address"))})
            occupied.append(match.span())
    for match in RX_RAW_ADD.finditer(code):
        if any(start <= match.start() < end for start, end in occupied):
            continue
        base = match.group("base")
        if base not in entity_vars:
            continue
        off = int(match.group("offset"), 0)
        if EXT_BASE <= off < EXT_END:
            out.append({"base": base, "offset": off, "width": 0,
                        "address_only": True})
    return out


def named_ext_expressions(off: int, width: int = 0) -> tuple[list[str], bool]:
    """Reachable named expressions starting at offset, plus width mismatch."""
    variants, union = parse_variants(), parse_union()
    expressions = []
    widths = []
    for member, et_name in union.items():
        variant = variants.get(et_name) or {}
        field = (variant.get("fields") or {}).get(off)
        if field:
            expressions.append(f"ext.{member}.{field}")
            widths.append((variant.get("widths") or {}).get(off, 0))
    mismatch = bool(width and widths and width not in widths)
    return sorted(set(expressions)), mismatch


def demanded_offsets(code: str) -> Counter:
    """Ext-range offsets from m2c placeholders and raw Entity-base views."""
    hits: Counter = Counter()
    for off_s in RX_UNK.findall(code):
        off = int(off_s, 16)
        if EXT_BASE <= off < EXT_END:
            hits[off] += 1
    for typ, idx in RX_ILLEGAL.findall(code):
        # Same arithmetic worker_direct uses when it rewrites the placeholder:
        # the index is in units of the element type, from the base of ext.
        off = EXT_BASE + int(idx, 0) * WIDTH[typ]
        if EXT_BASE <= off < EXT_END:
            hits[off] += 1
    for access in raw_entity_accesses(code):
        hits[access["offset"]] += 1
    return hits


def _gen_files() -> list[Path]:
    out = []
    for d in GEN_DIRS:
        if d.is_dir():
            out.extend(sorted(p for p in d.glob("*.c")))
    return out


def analyse(files: list[Path] | None = None) -> list[dict]:
    """Per-file demand, with covering variants and the offsets nothing covers."""
    variants = parse_variants()
    reachable = set(parse_union().values())
    files = _gen_files() if files is None else files
    rows = []
    for p in files:
        code = p.read_text(encoding="utf-8", errors="replace")
        want = demanded_offsets(code)
        if not want:
            continue
        offs = set(want)
        # A variant is a candidate only if it covers EVERY offset wanted. A
        # partial cover is not a reuse: mixing two variants means reading the
        # same bytes as two different types.
        fits = sorted(n for n, v in variants.items()
                      if n in reachable and offs <= v["covered"])
        anywhere = set()
        for v in variants.values():
            anywhere |= v["covered"]
        rows.append({
            "file": p.name,
            "offsets": want,
            "fits": fits,
            "uncovered": sorted(o for o in offs if o not in anywhere),
            "raw": raw_entity_accesses(code),
            "expressions": {o: named_ext_expressions(o)[0] for o in offs},
        })
    return rows


def report() -> str:
    variants, rows = parse_variants(), analyse()
    if not rows:
        return ("No ext-range offsets found in automation/candidates or "
                "automation/rejected. Either nothing has been generated yet, "
                "or the fleet is producing code that stays inside the fixed "
                "Entity header.")
    out = [f"{len(variants)} ET_ variants parsed from include/entity.h, "
           f"{len(parse_union())} of them reachable through the union.", ""]
    free = [r for r in rows if r["fits"]]
    stuck = [r for r in rows if not r["fits"]]

    out.append(f"REUSE, no header change ({len(free)}): every offset the code "
               f"wants is already named by an existing variant.")
    for r in free:
        offs = " ".join(f"0x{o:02X}" for o in sorted(r["offsets"]))
        out.append(f"  {r['file']}")
        out.append(f"      wants {offs}")
        out.append(f"      fits  {', '.join(r['fits'][:4])}")
    out.append("")

    out.append(f"HEADER CHANGE NEEDED ({len(stuck)}): no single variant covers "
               f"everything these ask for.")
    for r in stuck:
        offs = " ".join(f"0x{o:02X}" for o in sorted(r["offsets"]))
        gap = " ".join(f"0x{o:02X}" for o in r["uncovered"]) or "(none: the "
        out.append(f"  {r['file']}")
        out.append(f"      wants     {offs}")
        out.append(f"      unnamed   {gap}"
                   if r["uncovered"] else
                   "      unnamed   none; the offsets exist but are split "
                   "across variants, so one new variant collects them")
    out.append("")

    dem: Counter = Counter()
    who = defaultdict(set)
    for r in rows:
        for o in r["offsets"]:
            dem[o] += 1
            who[o].add(r["file"].split("_func")[0].split("_Ric")[0])
    out.append("OFFSET DEMAND, most-wanted first (files asking, not accesses):")
    for off, n in dem.most_common(12):
        named = sorted({v["fields"][off] for v in variants.values()
                        if off in v["fields"]})
        tag = ("named by " + ", ".join(named[:3])) if named else "NOT NAMED ANYWHERE"
        out.append(f"  0x{off:02X}  {n:2d} file(s)  {tag}")
    out.append("")
    out.append("Ranked by how many functions are blocked, so the top row is the "
               "one field that unblocks the most work. Naming it is still a "
               "read of the asm: this says WHERE to look, not what to call it.")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", action="store_true",
                    help="inventory every ET_ variant and its extent")
    ap.add_argument("--function", default="",
                    help="report on generated files matching this name")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.variants:
        vs, un = parse_variants(), parse_union()
        rev = {et: m for m, et in un.items()}
        print(f"{len(vs)} ET_ variants; {len(un)} reachable through Ext.")
        print(f"ext spans 0x{EXT_BASE:02X}..0x{EXT_END - 1:02X} "
              f"({EXT_END - EXT_BASE} bytes), then unkB8. A variant past that "
              f"grows Entity and changes all 81 hashes.")
        for name, v in sorted(vs.items(), key=lambda kv: -kv[1]["end"]):
            over = "  OVER" if v["end"] > EXT_END else ""
            print(f"  {name:32s} ends 0x{v['end']:02X}  "
                  f"{len(v['fields']):2d} fields  "
                  f"{rev.get(name, '(UNREACHABLE)')}{over}")
        return 0
    if a.function:
        rows = analyse([p for p in _gen_files() if a.function in p.name])
        if not rows:
            print(f"no generated file matching {a.function!r} touches ext")
            return 0
        for r in rows:
            print(f"{r['file']}")
            print("  wants " + " ".join(f"0x{o:02X}" for o in sorted(r["offsets"])))
            print("  fits  " + (", ".join(r["fits"]) or "NOTHING: header change"))
            for off, expressions in sorted(r["expressions"].items()):
                if expressions:
                    print(f"  0x{off:02X} named " + ", ".join(expressions[:8]))
            if r["uncovered"]:
                print("  unnamed anywhere: "
                      + " ".join(f"0x{o:02X}" for o in r["uncovered"]))
        return 0
    print(report())
    return 0


def self_test() -> int:
    fails = []

    def ck(c, label, detail=""):
        print(("  ok   " if c else "  FAIL ") + label
              + ("" if c else "   " + detail))
        if not c:
            fails.append(label)

    print("\nthe premise this tool corrects is checked against the header")
    game = GAME_H.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"/\*\s*0xB8\s*\*/\s*([^;]+);\s*\}\s*Entity;\s*//\s*size\s*=\s*"
                  r"(0x[0-9A-Fa-f]+)", game)
    ck(bool(m), "Entity's last member and size are both readable")
    if m:
        ck("Entity*" in m.group(1).replace(" ", ""),
           "unkB8 is a POINTER, not an unnamed blob (#109 said blob)",
           m.group(1).strip())
        size = int(m.group(2), 16)
        ck(size == ENTITY_END, f"Entity is 0x{size:02X}")
        ck(0xEC >= size,
           "0xEC is past the END of Entity, so #109's first example is a "
           "wrong-type diagnosis and not a missing name")

    print("\nvariants parse out of the real header")
    vs, un = parse_variants(), parse_union()
    ck(len(vs) > 50, f"many ET_ variants found ({len(vs)})")
    ck(len(un) > 50, f"and the union exposes them ({len(un)})")
    ck("ET_Dodo" in vs and "ET_JackOBones" in vs, "named ones are present")
    # This is the assumption the whole coverage calculation rests on. It caught
    # the body-spanning regex bug on its first run, so it stays phrased as a
    # property of the DATA rather than of the parse.
    low = {n: min(v["fields"]) for n, v in vs.items()
           if n in set(un.values()) and min(v["fields"]) < EXT_BASE}
    ck(not low,
       "every union-reachable variant's fields sit at 0x7C or later, i.e. "
       "offsets are ABSOLUTE Entity offsets and directly comparable to m2c's "
       "->unkNN",
       ", ".join(f"{n}@0x{o:02X}" for n, o in list(low.items())[:3]))

    print("\npadding reserves bytes but never counts as a name")
    fake = ("typedef struct {\n"
            "    /* 0x7C */ struct Primitive* prim;\n"
            "    /* 0x80 */ u8 movingLeft;\n"
            "    /* 0x84 */ s16 : 16;\n"
            "    /* 0x86 */ s16 laserTimer;\n"
            "} ET_Fake;\n")
    f = parse_variants(fake)["ET_Fake"]
    ck(0x84 not in f["fields"], "the anonymous bitfield is not a field")
    ck(0x84 not in f["covered"],
       "and does not count as covered; treating padding as coverage would "
       "report a real gap as already solved")
    ck(0x86 in f["covered"] and 0x87 in f["covered"],
       "a 2-byte field covers BOTH its bytes, so a demand at 0x87 resolves")
    ck(f["covered"] >= {0x7C, 0x7D, 0x7E, 0x7F}, "a pointer covers 4 bytes")
    ck(_decl_size("char pad_90[0xC]") == 0xC,
       "hexadecimal array lengths cover the complete declared field")

    print("\nboth spellings m2c produces are counted")
    d = demanded_offsets(
        "a->unk86 = 1; b->unk24 = 2; c = x->ext.ILLEGAL.u8[0x2E]; "
        "d->ext.unk90 = 3;")
    ck(d[0x86] == 1, "->unkNN in the ext range")
    ck(d[0x90] == 1, "->ext.unkNN in a rejected candidate")
    ck(0x24 not in d, "and NOT the fixed header, which is already named")
    # Found by running this against the live tree: EntityRelicOrb touches
    # ->unkB8 three times. 0xB8 is the named `struct Entity*` AFTER the union,
    # so counting it as demand would ask for a field that already exists.
    ck(0xB8 not in demanded_offsets("p->unkB8 = 0;"),
       "0xB8 is unkB8, a NAMED member past the end of ext, not demand")
    ck(demanded_offsets("p->unkB6 = 0;")[0xB6] == 1,
       "but 0xB6, the last two bytes of ext, still counts")
    ck(d[0xAA] == 1,
       "ext.ILLEGAL.u8[0x2E] resolves to 0xAA, the same arithmetic "
       "worker_direct uses when it rewrites the placeholder")
    ck(demanded_offsets("x->ext.ILLEGAL.s16[2]")[0x80] == 1,
        "and element width is honoured, so s16[2] is 0x80 not 0x7E")

    print("\nraw Entity-base offsets are evidence, not invisible pointer arithmetic")
    raw_code = "void f(Entity* self) { use(&((u8*)g_CurrentEntity)[0x90]); }"
    raw = raw_entity_accesses(raw_code)
    ck(len(raw) == 1 and raw[0]["offset"] == 0x90,
       "the #219 raw g_CurrentEntity offset is detected")
    ck(raw[0]["address_only"] and raw[0]["width"] == 0,
       "taking the address does not invent an access width")
    ck(demanded_offsets(raw_code)[0x90] == 1,
       "raw offsets enter the same ranked demand report")
    expressions, mismatch = named_ext_expressions(0x90)
    ck("ext.venusWeed.pad_90" in expressions,
       "the existing Venus Weed member is mapped automatically")
    ck(not mismatch, "an address-only view makes no false width claim")
    ck(not raw_entity_accesses("void f(u8* bytes) { use(&bytes[0x90]); }"),
       "an ordinary byte buffer is not misclassified as Entity")
    ck(not raw_entity_accesses(
        "void f(u8* bytes) { /* Entity* bytes; ((u8*)bytes)[0x90] */ return; }"),
       "comments cannot manufacture an Entity declaration or raw access")

    print("\na variant only counts as reuse when it covers EVERYTHING")
    vt = {"ET_A": {"fields": {0x7C: "a"}, "covered": {0x7C}, "end": 0x80}}
    offs = {0x7C, 0x86}
    ck(not (offs <= vt["ET_A"]["covered"]),
       "a partial cover is not a fit; mixing two variants would read the same "
       "bytes as two different types")

    print("\nand it runs against the live tree")
    rows = analyse()
    ck(isinstance(rows, list), "analyse() returns rows")
    if rows:
        ck(all(r["offsets"] for r in rows), "every row wants something")
        txt = report()
        ck("OFFSET DEMAND" in txt and "HEADER CHANGE NEEDED" in txt,
           f"the report has both halves ({len(rows)} files touch ext)")
    else:
        print("  ~~ no generated files touch ext right now; report skipped")

    print("\n" + ("all checks passed" if not fails else f"{len(fails)} FAILED"))
    for f_ in fails:
        print("  - " + f_)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
