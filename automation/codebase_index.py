#!/usr/bin/env python3
"""Build a structured index of the codebase: the shared ground truth.

WHY
    Both the quality audit and the model prompt need the same facts about this
    codebase, and every time we let either one GUESS those facts we shipped a
    defect: invented `D_800xxxxx` externs for addresses that already had names,
    `ext.ILLEGAL.u16[N]` where a named variant existed, magic `0xFB` where
    `~ENTITY_ROTATE` existed. Upstream review (2026-07-21) rejected all three.

    Harvest once, reference everywhere. This produces automation/index.us.json:

      symbols      name -> address, plus the reverse map
      entity       offset -> field/type for the Entity header
      ext_variants variant -> {offset -> field/type}   (fixes the ILLEGAL problem)
      constants    value -> [named constants]          (fixes magic numbers)
      functions    name -> {file, signature, body hash, shingles}
      structs      struct name -> [fields]             (fixes raw-cast problem)

    Fuzzy duplicate detection uses token shingles, because upstream's example of
    a "copy" (RIC Richter vs BO6 Richter) was *almost* identical, not identical,
    and an exact-body matcher misses exactly that case.

STRICTLY READ-ONLY. Never edits sources, never builds.

Usage:
    python3 automation/codebase_index.py                 # writes index.us.json
    python3 automation/codebase_index.py --query step    # look something up
    python3 automation/codebase_index.py --resolve 0x80076306
    python3 automation/codebase_index.py --similar <function>
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "automation" / "index.us.json"
ENTITY_SIZE = 0xBC


def _c_sources() -> list[Path]:
    return [p for p in (REPO / "src").rglob("*.c")
            if "_psp" not in str(p) and "saturn" not in str(p)]


def _headers() -> list[Path]:
    return list((REPO / "include").rglob("*.h"))


# ---------------------------------------------------------------- symbols
def build_symbols() -> dict:
    name2addr: dict[str, int] = {}
    for p in (REPO / "config").glob("symbols.us*.txt"):
        try:
            for line in p.read_text(errors="ignore").splitlines():
                m = re.match(r"^\s*([A-Za-z_]\w*)\s*=\s*(0x[0-9A-Fa-f]+)", line)
                if m:
                    name2addr.setdefault(m.group(1), int(m.group(2), 16))
        except OSError:
            continue
    return {"name_to_addr": {k: f"0x{v:08X}" for k, v in sorted(name2addr.items())},
            "addr_to_name": {f"0x{v:08X}": k for k, v in name2addr.items()}}


# ---------------------------------------------------------------- structs
_FIELD_RE = re.compile(
    r"^\s*(?:/\*\s*(0x[0-9A-Fa-f]+)\s*\*/\s*)?"
    r"([A-Za-z_][\w ]*?)\s*(\**)\s*([A-Za-z_]\w*)\s*(\[[^\]]*\])?\s*;")


def _parse_struct_bodies(text: str) -> dict[str, list[dict]]:
    """Every `typedef struct/union { ... } Name;` -> field list."""
    out: dict[str, list[dict]] = {}
    # The optional tag matters: Entity is `typedef struct Entity { ... } Entity;`
    # and a tagless-only pattern silently skipped it, yielding entity_fields=0.
    for m in re.finditer(
            r"typedef\s+(struct|union)\s+(?:[A-Za-z_]\w*\s*)?\{(.*?)\}\s*([A-Za-z_]\w*)\s*;",
            text, re.S):
        kind, body, name = m.group(1), m.group(2), m.group(3)
        fields = []
        for line in body.splitlines():
            fm = _FIELD_RE.match(line)
            if not fm:
                continue
            off, typ, stars, fname = (fm.group(1), fm.group(2).strip(),
                                      fm.group(3), fm.group(4))
            if typ in ("return", "if", "else"):
                continue
            fields.append({"offset": off, "type": (typ + stars).strip(),
                           "name": fname, "array": fm.group(5) or ""})
        if fields:
            out[name] = fields
        out.setdefault(name + "@kind", kind)  # keep kind without a second dict
    return {k: v for k, v in out.items() if not k.endswith("@kind")}


def build_structs() -> dict:
    all_structs: dict[str, list[dict]] = {}
    for p in _headers():
        try:
            all_structs.update(_parse_struct_bodies(p.read_text(errors="ignore")))
        except OSError:
            continue
    return all_structs


def build_entity(structs: dict) -> dict:
    """Entity header: offset -> field. The map that kills `->unkNN` guessing."""
    ent = structs.get("Entity", [])
    layout = {}
    for f in ent:
        if f["offset"]:
            layout[f["offset"]] = {"name": f["name"], "type": f["type"]}
    return {"size": f"0x{ENTITY_SIZE:X}", "fields": layout}


def build_ext_variants(structs: dict) -> dict:
    """ext variant name -> its struct's field layout.

    THE fix for the `ext.ILLEGAL` anti-pattern: given an entity type and a raw
    offset, this says the real field name to use instead of a generic array
    index. `ext` sits at 0x7C, so a variant field at struct-offset 0xN
    corresponds to entity offset 0x7C+N.
    """
    ext_union = None
    for p in _headers():
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        m = re.search(r"typedef\s+union\s*\{(.*?)\}\s*Ext\s*;", text, re.S)
        if m:
            ext_union = m.group(1)
            break
    variants: dict[str, dict] = {}
    if not ext_union:
        return variants
    for line in ext_union.splitlines():
        fm = re.match(r"^\s*([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*;", line)
        if not fm:
            continue
        typ, field = fm.group(1), fm.group(2)
        fields = structs.get(typ, [])
        variants[field] = {
            "type": typ,
            "fields": [{"offset": f["offset"], "name": f["name"],
                        "ctype": f["type"]} for f in fields if f["name"]],
        }
    return variants


# ---------------------------------------------------------------- constants
def build_constants() -> dict:
    """Constants indexed by value AND by enum group.

    Group matters more than value. Looking up bare `0x4` returns ~50 candidates
    (PAD_L1, DRAW_COLORS, dozens of PSP_*), and offering that list as a "fix" is
    worse than saying nothing: it invites the model to pick a plausible wrong
    constant. Knowing the ENUM the field belongs to (drawFlags -> the enum
    containing ENTITY_ROTATE) makes the answer unique.
    """
    by_value: dict[str, list[str]] = defaultdict(list)
    named: dict[str, str] = {}
    groups: dict[str, dict[str, str]] = {}          # enum name -> {const: value}
    for p in _headers():
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        # Named enum blocks, so each constant carries its family. BOTH C forms:
        #   enum Name { ... }          -> tag before the brace
        #   typedef enum { ... } Name; -> name AFTER the brace
        # Only handling the first form left EntityDrawFlags anonymous, which is
        # exactly the group needed to resolve `drawFlags &= 0xFB`.
        for em in re.finditer(
                r"(?:typedef\s+)?enum\s+([A-Za-z_]\w*)?\s*\{(.*?)\}\s*([A-Za-z_]\w*)?\s*;",
                text, re.S):
            gname = em.group(1) or em.group(3) or ""
            members = {}
            for mm in re.finditer(r"([A-Z][A-Z0-9_]{2,})\s*=\s*(0x[0-9A-Fa-f]+|\d+)",
                                  em.group(2)):
                try:
                    members[mm.group(1)] = f"0x{int(mm.group(2), 0):X}"
                except ValueError:
                    continue
            if members:
                key = gname or f"anon@{p.name}:{em.start()}"
                groups[key] = members
        for m in re.finditer(r"^\s*([A-Z][A-Z0-9_]{2,})\s*=\s*(0x[0-9A-Fa-f]+|\d+)\s*,?",
                             text, re.M):
            try:
                val = int(m.group(2), 0)
            except ValueError:
                continue
            key = f"0x{val:X}"
            if m.group(1) not in by_value[key]:
                by_value[key].append(m.group(1))
            named[m.group(1)] = key
        for m in re.finditer(r"^\s*#define\s+([A-Z][A-Z0-9_]{2,})\s+(0x[0-9A-Fa-f]+|\d+)\s*$",
                             text, re.M):
            try:
                val = int(m.group(2), 0)
            except ValueError:
                continue
            key = f"0x{val:X}"
            if m.group(1) not in by_value[key]:
                by_value[key].append(m.group(1))
            named[m.group(1)] = key
    # Authoritative field -> enum mapping, straight from the struct comments:
    #   /* 0x19 */ u8 drawFlags; // refer to enum EntityDrawFlags
    # This beats guessing by name affinity, which picked DRAW_COLORS (wrong)
    # over ENTITY_ROTATE (right) purely because "draw" appears in "drawFlags".
    field_enum: dict[str, str] = {}
    for p in _headers():
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        for m in re.finditer(
                r"\b([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*;\s*//\s*(?:refer to|see)\s+enum\s+([A-Za-z_]\w*)",
                text):
            field_enum[m.group(1)] = m.group(2)
    return {"by_value": dict(by_value), "by_name": named,
            "groups": groups, "field_enum": field_enum}


# ---------------------------------------------------------------- functions
def _normalise(body: str) -> str:
    body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
    body = re.sub(r"//[^\n]*", " ", body)
    return re.sub(r"\s+", "", body)


def _shingles(body: str, k: int = 5) -> set[str]:
    """Token k-grams, identifier-insensitive.

    Identifiers are collapsed to a placeholder so that two functions doing the
    same thing with different local/field names still look alike. That is what
    catches "almost identical, though not entirely" copies.
    """
    body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
    body = re.sub(r"//[^\n]*", " ", body)
    toks = re.findall(r"[A-Za-z_]\w*|0x[0-9A-Fa-f]+|\d+|[^\s\w]", body)
    norm = []
    for t in toks:
        if re.match(r"^[A-Za-z_]\w*$", t):
            norm.append("ID")
        elif re.match(r"^(0x[0-9A-Fa-f]+|\d+)$", t):
            norm.append("NUM")
        else:
            norm.append(t)
    return {"".join(norm[i:i + k]) for i in range(max(0, len(norm) - k + 1))}


def extract_functions(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    try:
        src = path.read_text(errors="ignore")
    except OSError:
        return out
    for m in re.finditer(
            r"^((?:[A-Za-z_][\w\*]*\s+)+\*?)([A-Za-z_]\w*)\s*\(([^;{]*)\)\s*\{",
            src, re.M):
        ret, name, args = m.group(1).strip(), m.group(2), m.group(3)
        if name in ("if", "for", "while", "switch", "return", "sizeof"):
            continue
        start = m.end() - 1
        depth, i = 0, start
        while i < len(src):
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = src[start:i + 1]
        out[name] = {"file": str(path.relative_to(REPO)),
                     "signature": f"{ret} {name}({args})",
                     "lines": body.count("\n") + 1,
                     "hash": hashlib.sha1(_normalise(body).encode()).hexdigest()[:12],
                     "shingles": sorted(_shingles(body))}
    return out


def build_functions() -> dict:
    out: dict[str, dict] = {}
    for p in _c_sources():
        for name, meta in extract_functions(p).items():
            if name in out:                     # same name in 2 overlays
                out[name].setdefault("also_in", []).append(meta["file"])
                continue
            out[name] = meta
    return out


def similar_functions(target: str, funcs: dict, threshold: float = 0.55,
                      limit: int = 5) -> list[tuple[str, float, str]]:
    """Jaccard similarity over shingles: finds near-duplicates."""
    t = funcs.get(target)
    if not t:
        return []
    ts = set(t.get("shingles", []))
    if not ts:
        return []
    scored = []
    for name, meta in funcs.items():
        if name == target:
            continue
        os_ = set(meta.get("shingles", []))
        if not os_:
            continue
        inter = len(ts & os_)
        if not inter:
            continue
        j = inter / len(ts | os_)
        if j >= threshold:
            scored.append((name, round(j, 3), meta["file"]))
    return sorted(scored, key=lambda x: -x[1])[:limit]


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--query", default="", help="find a symbol/field/constant")
    ap.add_argument("--resolve", default="", help="resolve an address to a field")
    ap.add_argument("--similar", default="", help="near-duplicates of a function")
    ap.add_argument("--no-shingles", action="store_true",
                    help="omit shingles from the written file (much smaller)")
    a = ap.parse_args()

    idx_path = Path(a.out)
    if (a.query or a.resolve or a.similar) and idx_path.exists():
        idx = json.loads(idx_path.read_text())
    else:
        print("indexing...", file=sys.stderr)
        structs = build_structs()
        idx = {
            "symbols": build_symbols(),
            "structs": structs,
            "entity": build_entity(structs),
            "ext_variants": build_ext_variants(structs),
            "constants": build_constants(),
            "functions": build_functions(),
        }
        s = idx["symbols"]["name_to_addr"]
        print(f"  symbols={len(s)} structs={len(idx['structs'])} "
              f"entity_fields={len(idx['entity']['fields'])} "
              f"ext_variants={len(idx['ext_variants'])} "
              f"constants={len(idx['constants']['by_value'])} "
              f"functions={len(idx['functions'])}", file=sys.stderr)
        to_write = idx
        if a.no_shingles:
            to_write = json.loads(json.dumps(idx))
            for meta in to_write["functions"].values():
                meta.pop("shingles", None)
        idx_path.write_text(json.dumps(to_write, indent=1))
        print(f"  wrote {idx_path} "
              f"({idx_path.stat().st_size//1024} KB)", file=sys.stderr)

    if a.resolve:
        addr = int(a.resolve, 16)
        base = int(idx["symbols"]["name_to_addr"].get("g_Entities", "0x0"), 16)
        exact = idx["symbols"]["addr_to_name"].get(f"0x{addr:08X}")
        if exact:
            print(f"{a.resolve} = {exact} (named symbol)")
        if base and base <= addr < base + ENTITY_SIZE * 256:
            off = addr - base
            i, f = divmod(off, ENTITY_SIZE)
            fld = idx["entity"]["fields"].get(f"0x{f:X}") \
                or idx["entity"]["fields"].get(f"0x{f:02X}")
            if fld:
                print(f"{a.resolve} = g_Entities[{i}].{fld['name']}  ({fld['type']})")
            elif f >= 0x7C:
                print(f"{a.resolve} = g_Entities[{i}].ext + 0x{f-0x7C:02X}")
            else:
                print(f"{a.resolve} = g_Entities[{i}] + 0x{f:02X}")
        elif not exact:
            print(f"{a.resolve}: not inside g_Entities and not a named symbol")

    if a.query:
        q = a.query.lower()
        hits = [k for k in idx["symbols"]["name_to_addr"] if q in k.lower()][:8]
        if hits:
            print("symbols:", ", ".join(hits))
        ef = [f"{o}:{v['name']}" for o, v in idx["entity"]["fields"].items()
              if q in v["name"].lower()][:8]
        if ef:
            print("entity fields:", ", ".join(ef))
        ev = [k for k in idx["ext_variants"] if q in k.lower()][:8]
        if ev:
            print("ext variants:", ", ".join(ev))
        cs = [n for n in idx["constants"]["by_name"] if q in n.lower()][:8]
        if cs:
            print("constants:", ", ".join(cs))
        fn = [k for k in idx["functions"] if q in k.lower()][:8]
        if fn:
            print("functions:", ", ".join(fn))

    if a.similar:
        sim = similar_functions(a.similar, idx["functions"])
        if not sim:
            print(f"no near-duplicates of {a.similar}")
        for name, score, f in sim:
            print(f"  {score:.2f}  {name}  ({f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
