#!/usr/bin/env python3
"""Checks distilled from a full manual review of all 134 matched functions.

WHY THIS EXISTS
    automation/quality_audit.py catches the defect SHAPES upstream named in its
    2026-07-21 review. A manual pass over every matched function on 2026-08-01
    found five more classes, and every one of them had survived the automated
    audit untouched. Each check below exists because a human found a real defect
    the machine had cleared.

    Two of these were also self-inflicted during that same session, which is the
    better argument for automating them:

      - `static` was added to StepTowards on a reviewer's advice that "nothing
        in the overlay references it". Nothing in the *C* did. INCLUDE_ASM stubs
        in a sibling translation unit `jal StepTowards`, and the link broke.
        check_linkage_vs_asm() now answers that question the way the linker
        does, before the build rather than after.
      - a wrong `ext` union variant produced byte-identical output because the
        two fields alias at the same offset, so nothing that compares bytes
        could ever have found it. check_ext_variant_outlier() finds it by
        looking at how the rest of the function refers to the same entity.

STRICTLY READ-ONLY. Never edits sources, never builds.

Usage:
    python3 automation/review_checks.py                # all checks, our files
    python3 automation/review_checks.py --check ext    # one check
    python3 automation/review_checks.py --self-test    # fixtures only
    python3 automation/review_checks.py --json out.json
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UPSTREAM = "upstream/master"
EXT_BASE = 0x7C          # Entity.ext lives here; every ext offset is relative

_ASM_REFS: dict[str, dict] = {}   # asm_root -> {symbol: {owning .c}}


def _our_c_files() -> list[Path]:
    """The .c files we changed relative to upstream."""
    try:
        out = subprocess.run(["git", "diff", "--name-only", f"{UPSTREAM}..HEAD",
                              "--", "src/"], cwd=REPO, capture_output=True,
                             text=True, timeout=120).stdout
    except (subprocess.SubprocessError, OSError):
        return []
    return [REPO / f for f in out.split()
            if f.endswith(".c") and (REPO / f).exists()]


def _functions(src: str) -> list[tuple[str, int, str]]:
    """(name, start_line, body) for brace-balanced top-level definitions."""
    out = []
    for m in re.finditer(
            r"^(?:static\s+)?[A-Za-z_][\w \*]*?\**\s*"
            r"(?:OVL_EXPORT\(\s*(\w+)\s*\)|([A-Za-z_]\w*))\s*\([^;{]*\)\s*\{",
            src, re.M):
        name = m.group(1) or m.group(2)
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
        out.append((name, src[:m.start()].count("\n") + 1, src[start:i + 1]))
    return out


# ---------------------------------------------------------------- checks

def check_ext_variant_outlier(path: Path, src: str) -> list[dict]:
    """One odd `ext.<variant>` in a function that otherwise uses another.

    THE defect this exists for: BO6_RicEntitySubwpnCross referred to
    `self->ext.holywater.timer` once, in a Cross Boomerang state machine whose
    other ~15 ext accesses all said `crossBoomerang`. ET_HolyWater.timer and
    ET_CrossBoomerang.timer are both s16 at ext+0x00, so it compiled to
    identical bytes and every byte-comparing check passed it. It is a
    copy/paste artifact from the neighbouring holy-water function.

    Heuristic, deliberately conservative: only fire when one variant clearly
    dominates (>=4 accesses and >=80% of them) and another appears exactly
    once. ILLEGAL is ignored -- it is its own finding in quality_audit.
    """
    out = []
    for name, line0, body in _functions(src):
        uses = re.findall(r"ext\.(\w+)\.", body)
        uses = [u for u in uses if u != "ILLEGAL"]
        if len(uses) < 5:
            continue
        counts = defaultdict(int)
        for u in uses:
            counts[u] += 1
        top, n = max(counts.items(), key=lambda kv: kv[1])
        if n < 4 or n / len(uses) < 0.8:
            continue
        for variant, c in counts.items():
            if variant == top or c != 1:
                continue
            off = body.find(f"ext.{variant}.")
            ln = line0 + body[:off].count("\n")
            out.append({
                "check": "ext_variant_outlier", "file": str(path.relative_to(REPO)),
                "line": ln, "function": name,
                "detail": f"ext.{variant} used once; ext.{top} used {n}x in the "
                          f"same function",
                "fix": f"almost certainly ext.{top}; if the fields alias, the "
                       f"bytes will not change and the name will stop lying",
            })
    return out


def check_linkage_vs_asm(path: Path, src: str) -> list[dict]:
    """`static` on a symbol that assembly in ANOTHER translation unit calls.

    Adding `static` to StepTowards broke the link during this very session. A
    reviewer had grepped the C sources, found no other caller, and concluded it
    was file-local. The callers were INCLUDE_ASM stubs in a sibling .c, so they
    are invisible to a source grep and entirely visible to the linker.

    Rule: for each `static` function, search the overlay's asm tree for
    `jal <name>` or `.word <name>`. Map each hit back to the .c that
    INCLUDE_ASMs it. If any owning .c is a different file, `static` is wrong.
    """
    out = []
    rel = path.relative_to(REPO)
    parts = rel.parts
    if len(parts) < 3 or parts[0] != "src":
        return out
    asm_root = REPO / "asm" / "us" / Path(*parts[1:-1])
    if not asm_root.is_dir():
        return out

    # stem -> owning .c, from every INCLUDE_ASM in this overlay
    owner: dict[str, str] = {}
    for c in (REPO / Path(*parts[:-1])).glob("*.c"):
        try:
            t = c.read_text(errors="ignore")
        except OSError:
            continue
        for m in re.finditer(r'INCLUDE_ASM\(\s*"[^"]*/([^"/]+)"\s*,\s*(\w+)', t):
            owner[m.group(2)] = c.name

    # Scan the overlay's asm ONCE and cache it. Re-walking it per function was
    # O(functions x asm files) of file reads over a mounted filesystem, which
    # did not finish. Build symbol -> {owning .c} in a single pass instead.
    key = str(asm_root)
    refs = _ASM_REFS.get(key)
    if refs is None:
        refs = defaultdict(set)
        ref_re = re.compile(r"\b(?:jal|\.word)\s+([A-Za-z_]\w*)")
        for s in asm_root.rglob("*.s"):
            try:
                t = s.read_text(errors="ignore")
            except OSError:
                continue
            own = owner.get(s.stem, "")
            for sym in set(ref_re.findall(t)):
                refs[sym].add(own)
        _ASM_REFS[key] = refs

    for name, line0, _ in _functions(src):
        decl = re.search(rf"^[ \t]*static\b[^;{{\n]*\b{re.escape(name)}\s*\(",
                         src, re.M)
        if not decl:
            continue
        foreign = {c for c in refs.get(name, set()) if c and c != path.name}
        if foreign:
            out.append({
                "check": "linkage_vs_asm", "file": str(rel), "line": line0,
                "function": name,
                "detail": f"declared static but assembly in {sorted(foreign)} "
                          f"references it across a translation unit",
                "fix": "remove static; the callers are INCLUDE_ASM stubs, which "
                       "a C-source grep cannot see",
            })
    return out


def check_angle_comment(path: Path, src: str) -> list[dict]:
    """A comment claiming a hex angle equals some number of degrees.

    This codebase uses 4096 units per full turn (FLT/ROT in include/common.h).
    A comment read `0x300 = approx. 270 degrees`; 0x300 is 768/4096 of a turn,
    which is 67.5. Arithmetic a script does perfectly and a reader does not.
    """
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        if "//" not in line and "/*" not in line:
            continue
        m = re.search(r"(0x[0-9A-Fa-f]+)[^\n]{0,40}?(-?\d+(?:\.\d+)?)\s*degrees",
                      line)
        if not m:
            continue
        real = int(m.group(1), 16) / 4096.0 * 360.0
        claimed = float(m.group(2))
        if abs(real - claimed) > 1.0:
            out.append({
                "check": "angle_comment", "file": str(path.relative_to(REPO)),
                "line": i, "function": "?",
                "detail": f"comment says {m.group(1)} is {claimed:g} degrees; "
                          f"at 4096 units per turn it is {real:g}",
                "fix": f"state {real:g} degrees, or drop the degree claim",
            })
    return out


def check_entity_stub_signature(path: Path, src: str) -> list[dict]:
    """An entity update function declared `(void)` instead of `(Entity*)`.

    `RNO0_Unused801C2338` was defined `(void)` while e_init.c declares it
    `(Entity* self)` and stores it in `EntityUpdates[]`, whose element type is
    `PfnEntityUpdate = void (*)(struct Entity*)`. Harmless only because the body
    is empty; it stops being harmless the moment anyone fills it in. The same
    shape exists in a sibling file, so it is systemic rather than a one-off.
    """
    out = []
    rel = path.relative_to(REPO)
    einit = REPO / rel.parent / "e_init.c"
    if not einit.exists():
        return out
    try:
        decl_src = einit.read_text(errors="ignore")
    except OSError:
        return out
    declared = set(re.findall(
        r"OVL_EXPORT\(\s*(\w+)\s*\)\s*\(\s*Entity\s*\*", decl_src))
    for m in re.finditer(
            r"^\s*(?:static\s+)?void\s+(?:OVL_EXPORT\(\s*(\w+)\s*\)|(\w+))\s*"
            r"\(\s*void\s*\)\s*\{", src, re.M):
        raw = m.group(1) or m.group(2)
        short = re.sub(r"^[A-Z0-9]+_", "", raw)
        if short in declared or raw in declared:
            out.append({
                "check": "entity_stub_signature", "file": str(rel),
                "line": src[:m.start()].count("\n") + 1, "function": raw,
                "detail": "defined (void) but e_init.c declares it "
                          "(Entity* self) and puts it in EntityUpdates[]",
                "fix": "define it as (Entity* self) to match PfnEntityUpdate",
            })
    return out


def check_lost_comment(path: Path, src: str) -> list[dict]:
    """Provenance comments present in the shared header, dropped in our copy.

    `CheckFieldCollision` lost `// original name: v_side_hosei`, which is the
    game's own symbol name and the only route back to it. `EntityPrizeDrop`
    lost four lines describing how the ST0/MAD/PSP versions relate. Neither
    affects a byte; both are exactly what a decomp is FOR.

    Only `// original name:` is reported. Broader comment diffing produced too
    much noise to be worth acting on, and a check people ignore is worse than
    no check -- the same reason the "noise comment" experiment was deleted.
    """
    out = []
    rel = path.relative_to(REPO)
    if rel.parts[:2] != ("src", "st") or len(rel.parts) < 4:
        return out
    shared = REPO / "src" / "st" / rel.name.replace(".c", ".h")
    if not shared.exists():
        return out
    try:
        hsrc = shared.read_text(errors="ignore")
    except OSError:
        return out
    ours = {n for n, _, _ in _functions(src)}
    for m in re.finditer(r"^[ \t]*//\s*(original name:[^\n]*)\n"
                         r"(?:[ \t]*//[^\n]*\n)*"
                         r"[^\n]*?\b(\w+)\s*\(", hsrc, re.M):
        note, fn = m.group(1).strip(), m.group(2)
        if fn in ours and note not in src:
            out.append({
                "check": "lost_comment", "file": str(rel), "line": 0,
                "function": fn,
                "detail": f"shared {shared.name} records `// {note}` above "
                          f"{fn}; our copy dropped it",
                "fix": f"restore `// {note}` above {fn}",
            })
    return out



# ---------------------------------------------------------------- shared-copy

def _us_source(text: str) -> str:
    """Resolve VERSION_* guards down to the US PSX branch.

    Without this, "does our signature match the shared one" degrades to
    "does it match ANY branch", which is too weak to be useful: e_collect.h
    defines CollectDummy as both `(void)` (ST0/BETA) and `(u16 id)` (US), so a
    copy that dropped the parameter matched the ST0 branch and looked clean.

    Reuses codebase_index.preprocess_us so there is one implementation of this
    and not two that can drift apart.
    """
    try:
        sys.path.insert(0, str(REPO / "automation"))
        from codebase_index import preprocess_us
        return preprocess_us(text)
    except Exception:
        return text          # degrade to the weaker "any branch" behaviour


def _shared_header(path: Path) -> Path | None:
    """src/st/<stage>/<name>.c  ->  src/st/<name>.h, if it exists."""
    rel = path.relative_to(REPO)
    if rel.parts[:2] != ("src", "st") or len(rel.parts) < 4:
        return None
    h = REPO / "src" / "st" / (rel.stem + ".h")
    return h if h.exists() else None


def _header_defs(hsrc: str) -> dict[str, list[dict]]:
    """name -> LIST of definitions in a shared header, one per version branch.

    A list, not a single entry, and that is load-bearing. e_collect.h defines
    CollectDummy twice:

        #if defined VERSION_BETA || (STAGE == STAGE_ST0 && !defined(VERSION_PSP))
        static void CollectDummy(void)
        #else
        static void CollectDummy(u16 id)
        #endif

    Keeping only the first made signature_drift compare our correct US-branch
    `(u16 id)` against the ST0 branch's `(void)` and report a defect on code
    that had just been fixed to match. Version guards are not resolved here, so
    every check must treat "matches ANY branch" as clean.
    """
    out: dict[str, list[dict]] = {}
    for m in re.finditer(
            r"((?:^[ \t]*//[^\n]*\n)*)"
            r"^[ \t]*(static\s+)?[A-Za-z_][\w \*]*?\**\s*"
            r"([A-Za-z_]\w*)\s*\(([^;{]*)\)\s*\{", hsrc, re.M):
        name = m.group(3)
        if name in ("if", "for", "while", "switch", "return", "sizeof"):
            continue
        out.setdefault(name, []).append({
            "static": bool(m.group(2)),
            "params": " ".join(m.group(4).split()),
            "comment": m.group(1),
        })
    return out


def _our_defs(src: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for m in re.finditer(
            r"((?:^[ \t]*//[^\n]*\n)*)"
            r"^[ \t]*(static\s+)?[A-Za-z_][\w \*]*?\**\s*"
            r"([A-Za-z_]\w*)\s*\(([^;{]*)\)\s*\{", src, re.M):
        name = m.group(3)
        if name in ("if", "for", "while", "switch", "return", "sizeof"):
            continue
        out.setdefault(name, {
            "static": bool(m.group(2)),
            "params": " ".join(m.group(4).split()),
            "comment": m.group(1),
            "line": src[:m.start()].count("\n") + 1,
        })
    return out


def check_static_dropped(path: Path, src: str) -> list[dict]:
    """We dropped `static` that the shared implementation has.

    Caught func_801CF778, CollectLifeVessel and CollectDummy. Widening a
    symbol's linkage for no reason is how a generic address-derived name like
    func_801CF778 ends up colliding with an unrelated one at link time.

    Pairs with check_linkage_vs_asm, which is the SAFETY side: this says the
    header wants it static, that one says whether assembly elsewhere would
    break if we did it. Act on this only when that one is silent -- exactly
    the mistake made with StepTowards.
    """
    h = _shared_header(path)
    if not h:
        return []
    try:
        hdefs = _header_defs(_us_source(h.read_text(errors="ignore")))
    except OSError:
        return []
    out = []
    for name, ours in _our_defs(src).items():
        variants = hdefs.get(name) or []
        if variants and all(v["static"] for v in variants) and not ours["static"]:
            out.append({
                "check": "static_dropped", "file": str(path.relative_to(REPO)),
                "line": ours["line"], "function": name,
                "detail": f"shared {h.name} declares it static in every version "
                          f"branch; our copy does not",
                "fix": "restore static -- but confirm check_linkage_vs_asm is "
                       "silent for this symbol first",
            })
    return out


def check_signature_drift(path: Path, src: str) -> list[dict]:
    """Our parameter list differs from the shared implementation's.

    CollectDummy lost its `u16 id` parameter and the matching call-site
    argument. It kept working only because the compiled caller happened to
    leave the value in $a0 already, which is a property of one codegen run and
    not of the source.
    """
    h = _shared_header(path)
    if not h:
        return []
    try:
        hdefs = _header_defs(_us_source(h.read_text(errors="ignore")))
    except OSError:
        return []
    out = []
    for name, ours in _our_defs(src).items():
        variants = hdefs.get(name) or []
        if not variants or not ours["params"]:
            continue
        b = ours["params"]
        shapes = [v["params"] for v in variants if v["params"]]
        if not shapes:
            continue
        def same(a: str) -> bool:
            return a == b or (a.count(",") == b.count(",")
                              and (a == "void") == (b == "void"))
        if not any(same(a) for a in shapes):
            out.append({
                "check": "signature_drift", "file": str(path.relative_to(REPO)),
                "line": ours["line"], "function": name,
                "detail": f"shared {h.name} has ({' | '.join(shapes)}), "
                          f"ours has ({b}) -- matches no version branch",
                "fix": "match one of the shared signatures, and fix every call site",
            })
    return out


def check_param_argN(path: Path, src: str) -> list[dict]:
    """A descriptive parameter name in the header, replaced by argN in ours.

    CollectHeart(u16 heartIdx) became CollectHeart(u16 arg0). argN is what the
    decompiler emits when it knows nothing; replacing a name that WAS known
    throws away information for free.
    """
    h = _shared_header(path)
    if not h:
        return []
    try:
        hdefs = _header_defs(_us_source(h.read_text(errors="ignore")))
    except OSError:
        return []
    out = []
    for name, ours in _our_defs(src).items():
        variants = hdefs.get(name) or []
        if not variants:
            continue
        want = max(variants, key=lambda v: len(v["params"]))
        hn = re.findall(r"(\w+)\s*(?:\[\s*\])?\s*(?:,|$)", want["params"])
        on = re.findall(r"(\w+)\s*(?:\[\s*\])?\s*(?:,|$)", ours["params"])
        if len(hn) != len(on):
            continue
        for a, b in zip(hn, on):
            if re.fullmatch(r"arg\d+", b) and not re.fullmatch(r"arg\d+", a):
                out.append({
                    "check": "param_argN", "file": str(path.relative_to(REPO)),
                    "line": ours["line"], "function": name,
                    "detail": f"shared {h.name} names this parameter `{a}`; "
                              f"ours calls it `{b}`",
                    "fix": f"rename {b} back to {a}",
                })
    return out


def check_lost_comment_block(path: Path, src: str) -> list[dict]:
    """Comment lines above a function in the shared header, absent from ours.

    EntityPrizeDrop lost four lines describing how the ST0, MAD and PSP
    versions relate. Deliberately narrow: only reports when the header's block
    is at least 3 lines and we kept FEWER THAN HALF of them, so ordinary
    condensation (which create_entity.c does throughout, losing nothing) stays
    quiet. Substring matching, so a reworded line still counts as kept.
    """
    h = _shared_header(path)
    if not h:
        return []
    try:
        hdefs = _header_defs(_us_source(h.read_text(errors="ignore")))
    except OSError:
        return []
    out = []
    for name, ours in _our_defs(src).items():
        variants = hdefs.get(name) or []
        if not variants:
            continue
        want = max(variants, key=lambda v: len(v["comment"]))
        hlines = [l.strip().lstrip("/ ").strip()
                  for l in want["comment"].splitlines() if l.strip()]
        hlines = [l for l in hlines if len(l) > 20]
        if len(hlines) < 3:
            continue
        kept = sum(1 for l in hlines if l[:40] in src)
        if kept * 2 < len(hlines):
            out.append({
                "check": "lost_comment_block", "file": str(path.relative_to(REPO)),
                "line": ours["line"], "function": name,
                "detail": f"shared {h.name} has a {len(hlines)}-line note above "
                          f"{name}; only {kept} line(s) survive in our copy",
                "fix": "restore the dropped lines, or say why they do not apply",
            })
    return out


CHECKS = {
    "ext": check_ext_variant_outlier,
    "static": check_static_dropped,
    "signature": check_signature_drift,
    "argn": check_param_argN,
    "block": check_lost_comment_block,
    "linkage": check_linkage_vs_asm,
    "angle": check_angle_comment,
    "stub": check_entity_stub_signature,
    "comment": check_lost_comment,
}


# ---------------------------------------------------------------- self-test

def self_test() -> int:
    """Fixtures taken from the real defects. A check that cannot reproduce its
    own founding bug is not a check."""
    ok = True

    def run(fn, text, expect, label, name="t.c"):
        nonlocal ok
        got = len(fn(REPO / "src" / "st" / "rno0" / name, text))
        good = (got > 0) == expect
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {label}  (fired={got})")

    print("ext_variant_outlier:")
    run(check_ext_variant_outlier, """
void f(Entity* self) {
    self->ext.crossBoomerang.a = 1; self->ext.crossBoomerang.b = 2;
    self->ext.crossBoomerang.c = 3; self->ext.crossBoomerang.d = 4;
    self->ext.holywater.timer = 50;
    self->ext.crossBoomerang.e = 5;
}""", True, "the real Cross Boomerang bug")
    run(check_ext_variant_outlier, """
void f(Entity* self) {
    self->ext.holywater.a = 1; self->ext.holywater.b = 2;
    self->ext.holywater.c = 3; self->ext.holywater.d = 4;
    self->ext.holywater.timer = 50;
}""", False, "consistent variant, must stay quiet")
    run(check_ext_variant_outlier, """
void f(Entity* self) { self->ext.a.x = 1; self->ext.b.y = 2; }
""", False, "too few accesses to judge")

    print("angle_comment:")
    run(check_angle_comment,
        "// offset (0x300 = approx. 270 degrees)\n", True, "the real 0x300 bug")
    run(check_angle_comment,
        "// offset (0x300 = 67.5 degrees)\n", False, "correct value, quiet")
    run(check_angle_comment,
        "// 0x800 is 180 degrees\n", False, "correct value, quiet")

    print("entity_stub_signature: (needs a real e_init.c, exercised in the live run)")
    print("linkage_vs_asm:        (needs the asm tree, exercised in the live run)")
    print("lost_comment:          (needs the shared header, exercised in the live run)")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", default="", choices=[""] + list(CHECKS))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", default="")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    which = [a.check] if a.check else list(CHECKS)
    # findings carry the check function's full name, not the short CLI key
    LONG = {"ext": "ext_variant_outlier", "linkage": "linkage_vs_asm",
            "angle": "angle_comment", "stub": "entity_stub_signature",
            "comment": "lost_comment", "static": "static_dropped",
            "signature": "signature_drift", "argn": "param_argN",
            "block": "lost_comment_block"}
    findings: list[dict] = []
    files = _our_c_files()
    for p in files:
        try:
            src = p.read_text(errors="ignore")
        except OSError:
            continue
        for k in which:
            findings += CHECKS[k](p, src)

    print(f"\n{'='*70}\nREVIEW CHECKS: {len(findings)} findings "
          f"over {len(files)} changed files\n{'='*70}")
    by = defaultdict(list)
    for f in findings:
        by[f["check"]].append(f)
    for k in which:
        items = by.get(LONG[k], [])
        print(f"\n{LONG[k]}  x{len(items)}")
        for f in items:
            loc = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
            print(f"  {loc}  [{f['function']}]")
            print(f"      {f['detail']}")
            print(f"      FIX: {f['fix']}")
    if a.json:
        Path(a.json).write_text(json.dumps(findings, indent=2))
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
