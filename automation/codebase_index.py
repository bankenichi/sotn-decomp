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
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "automation" / "index.us.json"
ENTITY_SIZE = 0xBC

# The last UPSTREAM commit before this fork's automated work.
#
# The index is built from THIS ref, not the working tree, and the distinction is
# load-bearing rather than tidy:
#
#   - Our own files declare `extern u16 D_80076306;`. Built from the working
#     tree, `declared_globals` contains that fake symbol, so the index reports
#     it as legitimately declared and SUPPRESSES the warning whose entire job is
#     to catch it. The database would certify our own defect as ground truth.
#   - `functions` feeds the "precedent" shown to models. Built from the working
#     tree, a model can be pointed at our own unreviewed output as the example
#     to imitate, laundering a mistake into a convention.
#
# The database is what the fixes are checked against, so it must not be derived
# from the thing being fixed. asm/ is exempt: a .s file under nonmatchings/ is
# produced by the extractor from the original binary, not by us.
UPSTREAM_REF = os.environ.get("SOTN_INDEX_REF", "2472557")

_TREE_CACHE: dict[str, list[str]] = {}
_BLOB_CACHE: dict[str, str] = {}


def _git(*args: str, timeout: int = 300) -> str:
    try:
        p = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True,
                           text=True, errors="replace", timeout=timeout)
        return p.stdout if p.returncode == 0 else ""
    except (subprocess.SubprocessError, OSError):
        return ""


def _ref_files(ref: str) -> list[str]:
    """Paths present at `ref`."""
    if ref not in _TREE_CACHE:
        out = _git("ls-tree", "-r", "--name-only", ref)
        _TREE_CACHE[ref] = [l for l in out.splitlines() if l.strip()]
    return _TREE_CACHE[ref]


def prefetch(paths: list[str], ref: str | None = None) -> None:
    """Read many blobs in ONE process.

    One `git show` per file is ~2100 subprocess spawns and takes minutes; a
    single `git cat-file --batch` streams the same content in about a second.
    """
    ref = ref or UPSTREAM_REF
    want = [p for p in paths if f"{ref}:{p}" not in _BLOB_CACHE]
    if not want:
        return
    try:
        p = subprocess.run(["git", "cat-file", "--batch"], cwd=str(REPO),
                           input=("\n".join(f"{ref}:{w}" for w in want)
                                  + "\n").encode(),
                           capture_output=True, timeout=600)
    except (subprocess.SubprocessError, OSError):
        return
    buf, pos = p.stdout, 0
    for w in want:
        nl = buf.find(b"\n", pos)
        if nl < 0:
            break
        header = buf[pos:nl].decode("utf-8", "replace").split()
        pos = nl + 1
        if len(header) < 3:                 # "<oid> missing"
            _BLOB_CACHE[f"{ref}:{w}"] = ""
            continue
        size = int(header[2])
        _BLOB_CACHE[f"{ref}:{w}"] = buf[pos:pos + size].decode("utf-8", "replace")
        pos += size + 1                     # payload plus trailing newline


def read_source(path: str, ref: str | None = None) -> str:
    """File contents AT the upstream ref, never the working tree."""
    ref = ref or UPSTREAM_REF
    key = f"{ref}:{path}"
    if key not in _BLOB_CACHE:
        _BLOB_CACHE[key] = _git("show", key)
    return _BLOB_CACHE[key]


def _c_sources(ref: str = UPSTREAM_REF) -> list[str]:
    return [f for f in _ref_files(ref)
            if f.startswith("src/") and f.endswith(".c")
            and "_psp" not in f and "saturn" not in f]


def _headers(ref: str = UPSTREAM_REF) -> list[str]:
    """All headers at the upstream ref, including PER-OVERLAY ones under src/.

    src/ headers are not optional: `extern PlayerState g_Ric;` lives in
    src/boss/bo6/bo6.h, not include/. Scanning only include/ made g_Ric look
    undeclared, and a checker built on that would have emitted
    `extern u16 g_Ric;`, conflicting with the real struct declaration.
    """
    return [f for f in _ref_files(ref)
            if f.endswith(".h")
            and (f.startswith("include/") or f.startswith("src/"))
            and "_psp" not in f and "saturn" not in f]


# ---------------------------------------------------------------- symbols
def build_symbols() -> dict:
    name2addr: dict[str, int] = {}
    for p in _ref_files(UPSTREAM_REF):
        if not (p.startswith("config/symbols.us") and p.endswith(".txt")):
            continue
        for line in read_source(p).splitlines():
            m = re.match(r"^\s*([A-Za-z_]\w*)\s*=\s*(0x[0-9A-Fa-f]+)", line)
            if m:
                name2addr.setdefault(m.group(1), int(m.group(2), 16))
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
        all_structs.update(_parse_struct_bodies(read_source(p)))
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
        text = read_source(p)
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
        text = read_source(p)
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
                key = gname or f"anon@{p.rsplit('/', 1)[-1]}:{em.start()}"
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
        text = read_source(p)
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


def extract_functions(path: str, src: str | None = None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if src is None:
        src = read_source(path)
    if not src:
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
        out[name] = {"file": path,
                     "signature": f"{ret} {name}({args})",
                     "lines": body.count("\n") + 1,
                     "hash": hashlib.sha1(_normalise(body).encode()).hexdigest()[:12],
                     "shingles": sorted(_shingles(body))}
    return out


def build_shared_impls() -> dict:
    """The src/st shared-implementation architecture.

    THE gap that cost this fork the most. src/st deduplicates by putting one
    implementation in src/st/<name>.h and reducing each stage's .c to a shim:

        // src/st/rcen/st_common.c -- the entire file
        #include "rcen.h"
        #include "../st_common.h"

    Nothing in the index described this, so the pipeline treated every
    INCLUDE_ASM as an isolated target and regenerated 707 lines into
    src/st/rno0/st_common.c that already existed one directory up. 76 functions
    were re-implemented this way.

    Records, per shared header: the functions it defines, which of those are
    `static` (file-local, so a stage that drops `static` turns them into global
    exports and silently couples its files together), and which stages already
    shim it versus carry a private copy.

    This is the ONE entry that deliberately reads both trees, because the
    interesting quantity is the DIFFERENCE between them:

      upstream_copies  private copies that upstream itself ships. rno3 carries
                       894 lines of water_effects and nz1 carries 323 of
                       e_breakable; a private copy is therefore not per se a
                       defect, and a checker that assumed otherwise would file
                       17 false positives against untouched upstream code.
      our_copies       copies present in the working tree but NOT upstream.
                       These are ours, and this is the actual finding.

    Upstream data still comes from the ref, so "is this normal here?" is never
    answered using our own output.
    """
    out: dict[str, dict] = {}
    fn_re = re.compile(
        r"^(static\s+)?[A-Za-z_][\w \*]*?\s+\*?([A-Za-z_]\w*)\s*\([^;{]*\)\s*\{",
        re.M)
    ref_files = _ref_files(UPSTREAM_REF)
    headers = [f for f in ref_files
               if re.fullmatch(r"src/st/[^/]+\.h", f)]

    # THREE states, not two. A two-state shim/copy split reported "0 copies we
    # added" for rno0, because upstream also ships src/st/rno0/st_common.c and
    # the aggregation only asked whether a file existed. Upstream's is a 70-line
    # INCLUDE_ASM STUB; ours is 707 lines of implementation. Conflating "stub
    # awaiting work" with "private implementation" hides precisely the
    # stub -> private_impl transition that is the defect.
    def _classify(stem: str, path: str, body: str) -> tuple[str, dict] | None:
        if not body:
            return None
        stage = path.split("/")[2]        # src/st/<stage>/<stem>.c
        info = {"stage": stage, "lines": body.count("\n") + 1}
        if re.search(rf'#include\s+"\.\./{re.escape(stem)}\.h"', body):
            return "shim", info
        info["include_asm"] = len(re.findall(r"\bINCLUDE_ASM\b", body))
        info["bodies"] = len(fn_re.findall(body))
        # A stub is mostly unimplemented: more INCLUDE_ASM than real bodies.
        kind = "stub" if info["include_asm"] > info["bodies"] else "private_impl"
        return kind, info

    for hdr in headers:
        text = read_source(hdr)
        funcs, statics = [], []
        for m in fn_re.finditer(text):
            name = m.group(2)
            if name in ("if", "for", "while", "switch", "sizeof", "return"):
                continue
            funcs.append(name)
            if m.group(1):
                statics.append(name)
        if not funcs:
            continue
        stem = hdr.rsplit("/", 1)[-1][:-2]
        pat = re.compile(rf"src/st/[^/]+/{re.escape(stem)}\.c")

        shims, up_copies, up_state = [], [], {}
        for path in ref_files:
            if not pat.fullmatch(path):
                continue
            r = _classify(stem, path, read_source(path))
            if not r:
                continue
            up_state[r[1]["stage"]] = r
            if r[0] == "shim":
                shims.append(r[1]["stage"])
            elif r[0] == "private_impl":
                up_copies.append(r[1])

        # Ours: judged by the TRANSITION from upstream's state, not by presence.
        our_copies = []
        for path in sorted((REPO / "src" / "st").glob(f"*/{stem}.c")):
            rel = path.relative_to(REPO).as_posix()
            try:
                body = path.read_text(errors="ignore")
            except OSError:
                continue
            r = _classify(stem, rel, body)
            if not r or r[0] != "private_impl":
                continue
            was = up_state.get(r[1]["stage"])
            if was and was[0] == "private_impl":
                continue                      # upstream already implemented it
            rec = dict(r[1])
            rec["was"] = was[0] if was else "absent"
            rec["upstream_lines"] = was[1]["lines"] if was else 0
            our_copies.append(rec)

        out[stem] = {
            "header": hdr,
            "functions": sorted(set(funcs)),
            "static_functions": sorted(set(statics)),
            "shimmed_by": sorted(shims),
            "upstream_copies": sorted(up_copies, key=lambda c: -c["lines"]),
            "our_copies": sorted(our_copies, key=lambda c: -c["lines"]),
        }
    return out


def build_unmatched(version: str = "us") -> dict:
    """What is still an INCLUDE_ASM stub, i.e. the real remaining work.

    Enumerated from asm/<version>/**/nonmatchings/*.s, which is authoritative:
    a .s file exists there precisely because that function is not yet matched.
    D_*/jtbl_* entries are DATA, not code; counting them is what produced the
    bogus "1277 functions remaining" figure (the real number is ~311).
    """
    out: dict[str, dict] = {}
    base = REPO / "asm" / version
    if not base.is_dir():
        return out
    for p in base.rglob("*.s"):
        parts = p.relative_to(base).parts
        if "nonmatchings" not in parts:
            continue
        if p.stem.startswith(("D_", "jtbl_")):
            continue                      # data, not a function
        i = parts.index("nonmatchings")
        out[p.stem] = {
            "overlay": "/".join(parts[:i]).upper(),
            "asm": str(p.relative_to(REPO)),
        }
    return out


def build_declared_globals() -> dict:
    """Every symbol that ALREADY has a C declaration, name -> where.

    Needed to answer "does this symbol need declaring?" without re-grepping the
    tree per function. Without it, a checker that only compares against the
    per-function DECLARATIONS list reports `g_CurrentEntity` as undeclared,
    because that list is capped and locally scoped, which would tell the model
    to redeclare things the headers already provide.

    Read at UPSTREAM_REF, and that is the whole point of this entry. Built from
    the working tree it would ingest our own `extern u16 D_80076306;`, report
    that fake symbol as legitimately declared, and suppress the warning whose
    only job is to catch it.
    """
    out: dict[str, str] = {}
    # Three shapes, and all three occur in this tree:
    #   extern Entity g_Entities[];          -> plain object
    #   extern void Foo(s32);                -> function
    #   extern void (*g_api_PlaySfx)(s32);   -> FUNCTION POINTER
    # Missing the third made 56 uses of g_api_PlaySfx look undeclared, which
    # would have told the model to redeclare a symbol the headers already have.
    pat = re.compile(
        r"^\s*extern\s+[^;()]*?\b([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*;")
    fnpat = re.compile(
        r"^\s*extern\s+[^;]*?\b([A-Za-z_]\w*)\s*\([^;]*\)\s*;")
    fnptr = re.compile(
        r"^\s*extern\s+[^;]*?\(\s*\*+\s*([A-Za-z_]\w*)\s*\)\s*\(")
    for p in _headers() + _c_sources():
        for line in read_source(p).splitlines():
            if "extern" not in line:
                continue
            m = fnptr.match(line) or fnpat.match(line) or pat.match(line)
            if m:
                out.setdefault(m.group(1), p)
    return out


def build_functions() -> dict:
    """Every function upstream already implements, at UPSTREAM_REF.

    This feeds "precedent" in the model prompt. Built from the working tree it
    would offer our own unreviewed output as the example to imitate, laundering
    a mistake into a house convention.
    """
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
    global UPSTREAM_REF          # must precede any read of the name in scope
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--query", default="", help="find a symbol/field/constant")
    ap.add_argument("--resolve", default="", help="resolve an address to a field")
    ap.add_argument("--similar", default="", help="near-duplicates of a function")
    ap.add_argument("--no-shingles", action="store_true",
                    help="omit shingles from the written file (much smaller)")
    ap.add_argument("--ref", default=UPSTREAM_REF,
                    help="git ref to index (default: the upstream baseline; "
                         "the index must not be derived from our own output)")
    a = ap.parse_args()

    UPSTREAM_REF = a.ref
    if not _ref_files(UPSTREAM_REF):
        print(f"error: ref {UPSTREAM_REF!r} has no files (bad ref, or shallow "
              f"clone missing history)", file=sys.stderr)
        return 2

    idx_path = Path(a.out)
    if (a.query or a.resolve or a.similar) and idx_path.exists():
        idx = json.loads(idx_path.read_text())
    else:
        print(f"indexing from {UPSTREAM_REF} (upstream, not working tree)...",
              file=sys.stderr)
        prefetch([f for f in _ref_files(UPSTREAM_REF)
                  if f.endswith((".h", ".c", ".txt"))])
        structs = build_structs()
        idx = {
            "provenance": {
                "ref": _git("rev-parse", UPSTREAM_REF).strip() or UPSTREAM_REF,
                "ref_name": UPSTREAM_REF,
                "note": "Built from the upstream ref, NOT the working tree. "
                        "Our own matches may be wrong and the fixes are checked "
                        "against this index, so it must not be derived from the "
                        "thing being fixed. Exceptions, both binary-derived or "
                        "explicitly diffed: unmatched (from asm/, extractor "
                        "output) and shared_impls.our_copies.",
            },
            "symbols": build_symbols(),
            "structs": structs,
            "entity": build_entity(structs),
            "ext_variants": build_ext_variants(structs),
            "constants": build_constants(),
            "functions": build_functions(),
            "declared_globals": build_declared_globals(),
            "shared_impls": build_shared_impls(),
            "unmatched": build_unmatched(),
        }
        s = idx["symbols"]["name_to_addr"]
        print(f"  symbols={len(s)} structs={len(idx['structs'])} "
              f"entity_fields={len(idx['entity']['fields'])} "
              f"ext_variants={len(idx['ext_variants'])} "
              f"constants={len(idx['constants']['by_value'])} "
              f"functions={len(idx['functions'])} "
              f"declared_globals={len(idx['declared_globals'])} "
              f"shared_impls={len(idx['shared_impls'])} "
              f"unmatched={len(idx['unmatched'])}",
              file=sys.stderr)
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
