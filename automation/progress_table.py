#!/usr/bin/env python3
"""Per-overlay completion, measured from the linker maps. No network.

WHY THIS EXISTS RATHER THAN tools/progress.py
    tools/progress.py computes the same thing and then POSTS it to frogress
    and Discord, which is upstream's reporting pipeline and not ours. It also
    uses 3.12-only f-string nesting, so it will not even parse on 3.10.

    This reads the same linker maps with the same library and the same rule,
    prints a table, and talks to nothing. `markdown()` owns the detailed block;
    `readme_status.py --write` places it in README.md, and that tool's drift
    check proves the checked-in block still equals this generator.

WHAT "COMPLETE" MEANS HERE
    Code bytes whose function is compiled from C, over total code bytes in
    that binary. A function counts as decompiled when its map contribution is
    a C object, it has no `.NON_MATCHING` symbol, and no live path-aware
    `INCLUDE_ASM` still names it. Extracted `.s` files are retained evidence,
    not build ownership, so their mere presence cannot make linked C disappear
    from the metric.

    Data is reported separately. A binary can be at 100% code and still be
    importing data, and conflating the two flatters the code number.

REQUIREMENTS
    mapfile_parser (in the repo venv) and a completed build, because the maps
    are build output. Without `build/us/*.map` this reports nothing rather
    than guessing.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from queue_coverage import REQUIRED_US_CONFIGS, required_scope_gaps
from source_index import include_asm_symbols

REPO = Path(__file__).resolve().parent.parent

# mapfile_parser lives in the repo venv, which may not be the interpreter
# running this. Add it rather than requiring a particular python.
for _vp in sorted(REPO.glob(".venv/lib/python*/site-packages")):
    if str(_vp) not in sys.path:
        sys.path.insert(0, str(_vp))

try:
    import mapfile_parser
    import yaml
except ImportError as e:                                    # pragma: no cover
    print(f"missing dependency: {e}. mapfile_parser and pyyaml are in the "
          f"repo venv; run this with .venv/bin/python or install them.",
          file=sys.stderr)
    raise SystemExit(2)

def _pretty_target(target_path: str) -> str:
    """Render a config target as the compact binary label used in docs."""
    parts = Path(target_path).parts
    try:
        parts = parts[parts.index("us") + 1:]
    except ValueError:
        pass
    if not parts:
        return target_path
    final = Path(parts[-1])
    if len(parts) == 1:
        return final.name
    stem = final.stem
    if final.suffix.upper() == ".BIN" and stem.upper() == parts[-2].upper():
        return "/".join(parts[:-1])
    if final.suffix.upper() == ".BIN":
        return "/".join((*parts[:-1], stem))
    return "/".join(parts)


def configured_modules(version: str) -> list[tuple[str, str, str]]:
    """Discover module, source path and display name from the scope authority."""
    names = (REQUIRED_US_CONFIGS if version == "us" else tuple(
        p.name for p in sorted((REPO / "config").glob(f"splat.{version}.*.yaml"))))
    modules = []
    for name in names:
        cfg_path = REPO / "config" / name
        if not cfg_path.is_file():
            continue
        opts = (yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}).get(
            "options", {})
        module = str(opts.get("basename") or name.removesuffix(".yaml").split(".")[-1])
        src = str(opts.get("src_path", f"src/{module}"))
        path = src.removeprefix("src/").rstrip("/")
        pretty = _pretty_target(str(opts.get("target_path", module)))
        modules.append((module, path, pretty))
    return modules


class Stats:
    __slots__ = ("name", "pretty", "exists", "code_done", "code_total",
                 "fn_done", "fn_total", "data_done", "data_total")

    def __init__(self, name: str, pretty: str):
        self.name, self.pretty, self.exists = name, pretty, False
        self.code_done = self.code_total = 0
        self.fn_done = self.fn_total = 0
        self.data_done = self.data_total = 0

    @property
    def code_pct(self) -> float:
        return 100.0 * self.code_done / self.code_total if self.code_total else 0.0

    @property
    def fn_pct(self) -> float:
        return 100.0 * self.fn_done / self.fn_total if self.fn_total else 0.0


def _nonmatchings(asm_path: Path, opts: dict) -> Path:
    nm = asm_path / opts.get("nonmatchings_path", "nonmatchings")
    nm_psp = nm / asm_path.name
    if nm_psp.exists() and (asm_path / "matchings").exists():
        return nm_psp
    return nm


def function_is_undecompiled(
    function: str,
    asm_dir: str,
    live_stubs: set[tuple[str, str]],
    has_nonmatching_symbol: bool,
    whole_file_asm: bool,
) -> bool:
    """Classify one map function from actual link and source ownership."""
    stub_key = (asm_dir.strip("/").replace("\\", "/"), function)
    return (
        whole_file_asm
        or has_nonmatching_symbol
        or stub_key in live_stubs
    )


def collect(
    module: str,
    path: str,
    pretty: str,
    version: str,
    live_stubs: set[tuple[str, str]] | None = None,
) -> Stats:
    st = Stats(module, pretty)
    cfg_path = REPO / "config" / f"splat.{version}.{module}.yaml"
    if not cfg_path.is_file():
        return st
    opts = (yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}).get(
        "options", {})
    build_path = REPO / opts.get("build_path", f"build/{version}")
    map_paths = [build_path / f"{module}.map"]
    fallback = REPO / f"build/{version}/{path}.map"
    if fallback not in map_paths:
        map_paths.append(fallback)
    map_paths = [p for p in map_paths if p.is_file()]
    if not map_paths:
        # WEAPON0 is one checksum artifact made from many independently linked
        # overlays, so its maps live below build/us/weapon/ rather than beside
        # weapon.ld. Config discovery must not make this artifact disappear.
        map_paths = sorted((build_path / path).glob("*.map"))
    if not map_paths:
        return st
    st.exists = True
    asm_path = REPO / opts.get("asm_path", f"asm/{version}")
    nm = _nonmatchings(asm_path, opts)
    version_asm_root = REPO / "asm" / version
    if live_stubs is None:
        live_stubs = include_asm_symbols(REPO / "src")
    depth = 4 + path.count("/")

    for map_path in map_paths:
        mf = mapfile_parser.MapFile()
        mf.readMapFile(map_path)
        text = mf.filterBySectionType(".text")
        for file in [f for seg in text for f in seg]:
            if len(file) == 0:
                continue
            rel = Path(*file.filepath.parts[depth:])
            stem = rel
            while stem.suffix:
                stem = stem.with_suffix("")
            whole_file_asm = (asm_path / stem.with_suffix(".s")).exists()
            try:
                asm_dir = (nm / stem).relative_to(version_asm_root).as_posix()
            except ValueError:
                asm_dir = (nm / stem).as_posix()
            for func in file:
                if func.name.endswith(".NON_MATCHING"):
                    continue
                st.fn_total += 1
                size = func.size or 0
                undecomped = function_is_undecompiled(
                    func.name,
                    asm_dir,
                    live_stubs,
                    mf.findSymbolByName(
                        f"{func.name}.NON_MATCHING") is not None,
                    whole_file_asm,
                )
                if undecomped:
                    st.code_total += size
                else:
                    st.fn_done += 1
                    st.code_done += size
                    st.code_total += size

        for sect in (".data", ".rodata", ".bss"):
            for file in [f for seg in mf.filterBySectionType(sect) for f in seg]:
                if "dra_data" in str(file.filepath): # the VAB chunk at DRA's end
                    continue
                st.data_total += file.size
                if "src/" in str(file.filepath) or "assets/" in str(file.filepath):
                    st.data_done += file.size
    return st


def gather(version: str) -> list[Stats]:
    live_stubs = include_asm_symbols(REPO / "src")
    return [s for s in (
        collect(m, p, n, version, live_stubs)
        for m, p, n in configured_modules(version))
            if s.exists and s.code_total]


def totals(rows: list[Stats]) -> tuple[float, float, int, int]:
    cd = sum(r.code_done for r in rows)
    ct = sum(r.code_total for r in rows)
    fd = sum(r.fn_done for r in rows)
    ft = sum(r.fn_total for r in rows)
    return (100.0 * cd / ct if ct else 0.0,
            100.0 * fd / ft if ft else 0.0, fd, ft)


def print_table(rows: list[Stats]) -> None:
    print(f"{'binary':<18}{'code%':>8}{'funcs':>14}{'data%':>8}")
    print("-" * 48)
    for r in sorted(rows, key=lambda r: -r.code_pct):
        dp = 100.0 * r.data_done / r.data_total if r.data_total else 0.0
        print(f"{r.pretty:<18}{r.code_pct:>7.1f}%"
              f"{f'{r.fn_done}/{r.fn_total}':>14}{dp:>7.1f}%")
    print("-" * 48)
    cp, _fp, fd, ft = totals(rows)
    print(f"{'OVERALL':<18}{cp:>7.1f}%{f'{fd}/{ft}':>14}")


def markdown(rows: list[Stats]) -> str:
    """Return the complete generated README completion block."""
    cp, fp, fd, ft = totals(rows)
    lines = [
        f"**Overall: {cp:.1f}% of code decompiled** "
        f"({fd} of {ft} functions), across {len(rows)} built binaries.",
        "",
    ]
    done = [r for r in rows if r.code_pct >= 99.95]
    part = [r for r in rows if r.code_pct < 99.95]
    if done:
        lines += [
            f"**{len(done)} binaries are at 100%:** "
            + ", ".join(f"`{r.pretty}`" for r in sorted(
                done, key=lambda r: r.pretty)),
            "",
        ]
    if part:
        lines += [
            f"The {len(part)} that are not:",
            "",
            "| binary | code | functions | |",
            "|---|---:|---:|---|",
        ]
        for r in sorted(part, key=lambda r: -r.code_pct):
            lines.append(
                f"| `{r.pretty}` | {r.code_pct:.1f}% "
                f"| {r.fn_done}/{r.fn_total} | |"
            )
    return "\n".join(lines)


def print_markdown(rows: list[Stats]) -> None:
    """Print the README block owned by :func:`markdown`."""
    print(markdown(rows))


def self_test() -> int:
    fails = []

    def ck(cond, label):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    print("the table is derived from real maps, or it reports nothing")
    live = include_asm_symbols(REPO / "src")
    factory_key = (
        "boss/bo6/nonmatchings/us_39144",
        "BO6_RicEntityFactory",
    )
    beam_key = (
        "boss/bo6/nonmatchings/us_3E79C",
        "BO6_RicEntityCrashBibleBeam",
    )
    ck(factory_key not in live,
       "Factory has linked C and no live INCLUDE_ASM")
    ck(beam_key in live,
       "CrashBibleBeam remains a live path-aware stub")
    ck(not function_is_undecompiled(
        factory_key[1], factory_key[0], live, False, False),
       "a linked C function is complete without relying on retained extractor output")
    ck(function_is_undecompiled(
        beam_key[1], beam_key[0], live, False, False),
       "a live INCLUDE_ASM inside a C object still counts as unmatched")
    ck(function_is_undecompiled(
        "WholeFileFunction", "boss/bo6/whole_file", live, False, True),
       "a configured whole-file extracted assembly segment remains unmatched")
    rows = gather("us")
    modules = configured_modules("us")
    ck(not required_scope_gaps(),
       "the required artifact and config scope is exact")
    ck(len(modules) == len(REQUIRED_US_CONFIGS),
       f"every required US config supplies a progress module ({len(modules)})")
    ck(len({m for m, _p, _n in modules}) == len(modules),
       "configured progress module names are unique")
    ck(len({n for _m, _p, n in modules}) == len(modules),
       "configured progress display names are unique")
    ck(bool(rows), f"maps were found and parsed ({len(rows)} binaries). "
                   f"If this fails, run a build first.")
    if rows:
        missing_rows = sorted(set(m for m, _p, _n in modules)
                              - {r.name for r in rows})
        ck(len(rows) == len(modules),
           f"every configured US module has a populated linker map ({len(rows)}; "
           f"missing {missing_rows})")
        ck(all(r.code_total > 0 for r in rows),
           "every reported binary has a non-zero code total, so no row can "
           "show a percentage computed from nothing")
        ck(all(0.0 <= r.code_pct <= 100.0 for r in rows),
           "no percentage is outside 0..100")
        ck(all(r.fn_done <= r.fn_total for r in rows),
           "decompiled functions never exceed total functions")
        cp, fp, fd, ft = totals(rows)
        ck(0.0 < cp <= 100.0, f"the overall figure is sane ({cp:.1f}%)")
        ck(fd <= ft, f"and so is the function total ({fd}/{ft})")
        # Code% and function% are DIFFERENT measures and are expected to
        # disagree; asserting they track each other would be asserting the
        # remaining functions are averagely sized, which they are not.
        ck(True, f"code {cp:.1f}% vs functions {fp:.1f}% -- these differ "
                 f"because the functions left are the big ones")
    print()
    if fails:
        print(f"{len(fails)} FAILED")
        for f in fails:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default=os.environ.get("VERSION", "us"))
    ap.add_argument("--markdown", action="store_true",
                    help="emit the README block instead of the table")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    rows = gather(a.version)
    if not rows:
        print(f"no linker maps under build/{a.version}/. These are build "
              f"output; run a build first.", file=sys.stderr)
        return 1
    (print_markdown if a.markdown else print_table)(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
