#!/usr/bin/env python3
"""Rank queue functions by how many of their symbols the repo already declares.

WHY
    build_prompt now injects real declarations harvested from the tree (see
    MATCHING-LESSONS.md 10f). That fix only helps a function if the repo
    actually declares the symbols its assembly touches. Measured on 2026-07-21:
    the two BO6 animation functions resolved 4 and 6 declarations and matched
    immediately, while the BO0/RNO0 functions the fleet was grinding resolved
    0-1 and kept missing.

    So coverage predicts which functions the fix can help. Working the queue in
    claim order spends the improvement on whatever happens to come next; working
    it in coverage order spends it where it applies.

STRICTLY READ-ONLY. Writes nothing under src/, include/, asm/ or config/, and
never builds. Safe to run while a fleet is active.

Usage:
    python3 automation/decl_coverage.py                 # rank todo records
    python3 automation/decl_coverage.py --status near
    python3 automation/decl_coverage.py --limit 40 --json out.json
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Mirrors worker_direct.extract_asm_symbols. Kept in sync deliberately: if the
# two drift, the ranking stops predicting what the worker will actually be
# given, which is the entire point of this script.
_ASM_SYM_RE = re.compile(
    r"%(?:hi|lo)\(\s*([A-Za-z_][A-Za-z0-9_]*)|"
    r"\bjal\s+([A-Za-z_][A-Za-z0-9_]*)")
_SYM_SKIP = {"hi", "lo"}


def extract_asm_symbols(asm: str, exclude: str = "") -> list[str]:
    out: list[str] = []
    for m in _ASM_SYM_RE.finditer(asm or ""):
        s = m.group(1) or m.group(2)
        if s and s != exclude and s not in _SYM_SKIP and s not in out:
            out.append(s)
    return out


_INCLUDE_ASM_RE = re.compile(
    r'INCLUDE_ASM\(\s*"([^"]+)"\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)')


def scan_asm_for_unmatched(version: str = "us") -> list[dict]:
    """Enumerate the unmatched set from asm/<version>/**/nonmatchings/*.s.

    THIS is the authoritative list. An earlier version of this scanned src/ for
    INCLUDE_ASM stubs and applied the `_psp`/`saturn` path exclusion copied from
    worker_direct.find_source. That exclusion left only 48 source files, so the
    scan reported 397 candidates when `us` actually has 1114 unmatched
    functions. The subset was an artefact of the filter, not a property of the
    work.

    Reading asm/ directly avoids the whole class of problem: a .s file under
    nonmatchings/ exists precisely because that function is not yet matched, and
    it does not depend on how the corresponding C file happens to be organised
    or whether one exists at all.
    """
    out: list[dict] = []
    base = REPO / "asm" / version
    if not base.is_dir():
        return out
    for p in base.rglob("*.s"):
        rel = p.relative_to(base)
        parts = rel.parts
        if "nonmatchings" not in parts:
            continue
        i = parts.index("nonmatchings")
        overlay = "/".join(parts[:i]).upper()      # e.g. boss/bo6 -> BOSS/BO6
        seg = "/".join(parts[i + 1:-1])            # e.g. us_39144
        out.append({"id": f"{version}:{overlay}:{p.stem}", "function": p.stem,
                    "overlay": overlay, "status": "todo",
                    "segment": seg, "asm": str(p.relative_to(REPO))})
    return out


def load_candidates(version: str = "us", use_queue: bool = False) -> list[dict]:
    """The functions to rank.

    Defaults to the FULL unmatched set from asm/, not the queue. The queue only
    ever held a subset (438 records against 1114 unmatched functions), so
    ranking it answers "which of the ones we already picked is easiest" rather
    than "which functions are easiest". The second question is the useful one.

    --use-queue restricts to queue records when you deliberately want to
    reprioritise existing work rather than discover new work.
    """
    if use_queue:
        try:
            sys.path.insert(0, str(REPO / "automation"))
            import scheduler  # noqa: E402
            recs = scheduler.Queue()._read()
            if recs:
                return recs
        except Exception as e:  # noqa: BLE001
            print(f"  queue unavailable ({type(e).__name__}), "
                  f"falling back to the full asm set", file=sys.stderr)
    return scan_asm_for_unmatched(version)


_ASM_INDEX: dict[str, Path] = {}


def build_asm_index(version: str = "us") -> dict[str, Path]:
    """Walk asm/<version> ONCE and map function name -> .s path.

    The first version of this called rglob() per function. That is
    O(functions x files) and with ~1300 unmatched functions over the full asm
    tree it did not finish inside a tool call. One walk, then dict lookups.
    """
    global _ASM_INDEX
    if _ASM_INDEX:
        return _ASM_INDEX
    base = REPO / "asm" / version
    for p in base.rglob("*.s"):
        _ASM_INDEX.setdefault(p.stem, p)
    return _ASM_INDEX


def find_asm(function: str, version: str = "us") -> Path | None:
    return build_asm_index(version).get(function)


def build_declaration_index() -> dict[str, str]:
    """One pass over src/ and include/ collecting every extern declaration.

    A grep per symbol would be thousands of subprocesses. One pass, then
    dictionary lookups.

    Implemented with one grep rather than reading every file from Python. The
    repo sits on a mounted filesystem where per-file open/read costs
    milliseconds, and there are thousands of files; the Python version did not
    finish inside a tool call. grep does the whole walk in one process.
    """
    index: dict[str, str] = {}
    try:
        p = subprocess.run(
            ["grep", "-rhE", r"^[[:space:]]*extern[[:space:]]", "src", "include",
             "--include=*.c", "--include=*.h"],
            cwd=str(REPO), capture_output=True, text=True, timeout=180)
        lines = p.stdout.splitlines()
    except (subprocess.SubprocessError, OSError) as e:
        print(f"  grep failed ({e}); no declarations indexed", file=sys.stderr)
        return index

    pat = re.compile(
        r"^\s*extern\s[^;]*?\b([A-Za-z_][A-Za-z0-9_]*)\s*"
        r"(?:\[[^\]]*\])?\s*(?:\([^;]*\))?\s*;")
    for line in lines:
        m = pat.match(line)
        if not m:
            continue
        name, decl = m.group(1), line.strip()
        # Shortest declaration wins: the plain one, not a line that merely
        # mentions the name.
        if name not in index or len(decl) < len(index[name]):
            index[name] = decl
    return index


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", default="todo",
                    help="only with --use-queue")
    ap.add_argument("--use-queue", action="store_true",
                    help="rank queue records instead of the full asm set")
    ap.add_argument("--version", default="us")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--json", default="")
    # The declaration grep walks the whole tree and takes ~25s on a mounted
    # filesystem, which does not fit in one automated call alongside the rest.
    # Cache it so the scan can be driven in phases. Delete the cache after
    # renaming symbols, or it will report stale coverage.
    ap.add_argument("--decl-cache", default="",
                    help="load/save the declaration index here (JSON)")
    ap.add_argument("--build-cache-only", action="store_true",
                    help="build the declaration cache, then exit")
    ap.add_argument("--sym-cache", default="",
                    help="load/save raw asm symbol refs here")
    ap.add_argument("--write-priority", default="",
                    help="write claim-order hints for scheduler.cmd_next "
                         "(normally automation/priority.us.json)")
    a = ap.parse_args()

    index = {}
    cache = Path(a.decl_cache) if a.decl_cache else None
    if cache and cache.exists():
        index = json.loads(cache.read_text())
        print(f"loaded {len(index)} declarations from {cache}", file=sys.stderr)
    else:
        print("indexing declarations in src/ and include/ ...", file=sys.stderr)
        index = build_declaration_index()
        print(f"  {len(index)} declared symbols", file=sys.stderr)
        if cache:
            cache.write_text(json.dumps(index))
            print(f"  cached to {cache}", file=sys.stderr)
    if a.build_cache_only:
        return 0

    recs = load_candidates(a.version, use_queue=a.use_queue)
    if a.use_queue:
        recs = [r for r in recs if r.get("status") == a.status]
    print(f"scanning {len(recs)} unmatched functions ...", file=sys.stderr)

    # Symbols for EVERY function in one grep. Opening 1114 files individually
    # from Python over a mounted filesystem does not finish in a tool call;
    # this does it in one process.
    per_file: dict[str, list[str]] = {}
    scache = Path(a.sym_cache) if a.sym_cache else None
    raw_lines: list[str] = []
    if scache and scache.exists():
        raw_lines = scache.read_text().splitlines()
        print(f"loaded {len(raw_lines)} symbol refs from {scache}",
              file=sys.stderr)
    else:
        print("extracting symbols from asm ...", file=sys.stderr)
        try:
            # Restricted to */nonmatchings/* on purpose: asm/<version> also
            # holds every already-matched function, and grepping the whole tree
            # takes minutes on a mounted filesystem.
            fp = subprocess.run(
                ["find", f"asm/{a.version}", "-path", "*/nonmatchings/*",
                 "-name", "*.s"],
                cwd=str(REPO), capture_output=True, text=True, timeout=300)
            files = fp.stdout.split()
            gp = subprocess.run(
                ["grep", "-oE",
                 r"%(hi|lo)\([A-Za-z_][A-Za-z0-9_]*|jal[[:space:]]+[A-Za-z_][A-Za-z0-9_]*",
                 *files],
                cwd=str(REPO), capture_output=True, text=True, timeout=900)
            raw_lines = gp.stdout.splitlines()
            if scache:
                scache.write_text("\n".join(raw_lines))
                print(f"  cached {len(raw_lines)} refs to {scache}",
                      file=sys.stderr)
        except (subprocess.SubprocessError, OSError) as e:
            print(f"  grep failed: {e}", file=sys.stderr)
            return 1
    try:
        for line in raw_lines:
            path, _, match = line.partition(":")
            sym = re.split(r"[(\s]+", match)[-1]
            if sym and sym not in _SYM_SKIP:
                per_file.setdefault(path, [])
                if sym not in per_file[path]:
                    per_file[path].append(sym)
    except (subprocess.SubprocessError, OSError) as e:
        print(f"  grep failed: {e}", file=sys.stderr)
        return 1
    print(f"  symbols extracted for {len(per_file)} asm files", file=sys.stderr)

    rows = []
    for r in recs:
        fn = r.get("function", "")
        rel = r.get("asm") or ""
        if rel:
            # Path already known from the asm walk. Default to [] rather than
            # falling through to find_asm: a function with no external symbol
            # references is legitimately empty here, and the fallback rglobs the
            # whole asm tree per function, which for the ~800 symbol-less files
            # never finishes.
            syms = list(per_file.get(rel, []))
        else:
            asm = find_asm(fn, a.version)   # queue records carry no asm path
            if not asm:
                continue
            syms = list(per_file.get(str(asm.relative_to(REPO)), []))
        # D_* and jtbl_* .s files are DATA, not functions. 803 of the 1114 files
        # under asm/us/**/nonmatchings/ are data symbols; treating them as work
        # is what produced the bogus "1277 functions remaining" figure, and is
        # the same confusion that made `make function-finder` relocate 803
        # rodata files (MATCHING-LESSONS.md 8d).
        if fn.startswith(("D_", "jtbl_")):
            continue
        syms = [s for s in syms if s != fn and not s.startswith("jtbl_")]
        found = [s for s in syms if s in index]
        missing = [s for s in syms if s not in index]
        data_refs = [s for s in syms if s.startswith("D_")]
        rows.append({
            "id": r["id"], "function": fn, "overlay": r.get("overlay", ""),
            "symbols": len(syms), "resolved": len(found),
            "coverage": round(len(found) / len(syms), 3) if syms else 1.0,
            "data_refs": data_refs,
            "undeclared_data": [d for d in data_refs if d not in index],
            "missing": missing[:8],
        })

    # Rank:
    #   1. functions with NO undeclared data references first. A raw D_us_
    #      address that nothing names is a structural failure (section 1a) that
    #      neither a better model nor the permuter can fix, so those go last
    #      regardless of how good the rest of their coverage looks.
    #   2. then by declaration coverage, since that is what the prompt fix
    #      (section 10f) actually improves.
    #   3. then fewest symbols: a smaller surface is less to get wrong.
    rows.sort(key=lambda x: (len(x["undeclared_data"]),
                             -x["coverage"], x["symbols"]))

    print(f"\n{'cov':>5}  {'res/tot':>8}  {'overlay':<12} function")
    print("-" * 72)
    for row in rows[:a.limit]:
        print(f"{row['coverage']:>5.0%}  "
              f"{row['resolved']:>3}/{row['symbols']:<4}  "
              f"{row['overlay']:<12} {row['function']}")

    workable = [r for r in rows if not r["undeclared_data"]]
    blocked = [r for r in rows if r["undeclared_data"]]
    print(f"\nscanned {len(rows)} real functions (data symbols excluded)")
    print(f"  workable                        : {len(workable)}")
    print(f"  blocked on unnamed data symbols : {len(blocked)}")
    print(f"  of workable, 100% covered       : "
          f"{sum(1 for r in workable if r['coverage'] == 1.0)}")

    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=2))
        print(f"  wrote {a.json}")

    if a.write_priority:
        # Consumed by scheduler.cmd_next. Only the two fields it needs: keeping
        # this minimal means the ranking heuristic can change here without
        # touching the scheduler.
        prio = {}
        for rank, row in enumerate(rows):
            undeclared_data = [d for d in row.get("data_refs", [])
                               if d not in index]
            prio[row["function"]] = {"rank": rank,
                                     "blocked": bool(undeclared_data)}
        out = Path(a.write_priority)
        out.write_text(json.dumps(prio, indent=1))
        nb = sum(1 for v in prio.values() if v["blocked"])
        print(f"  wrote {out}: {len(prio)} functions, "
              f"{nb} blocked, {len(prio) - nb} workable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
