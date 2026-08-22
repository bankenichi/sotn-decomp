#!/usr/bin/env python3
"""Evidence-bound declarations for raw data labels retained in assembly.

A raw D_* reference is not unnamed in the binary: the retained data assembly
pins its overlay, address, storage width and byte span. This module converts
that evidence into the narrow declaration a worker needs in its prompt. It
never invents semantic struct or array names, and it refuses ambiguous
cross-overlay labels whose retained definitions disagree.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

_LABEL_RE = re.compile(r"^glabel\s+(D_(?:us_)?[A-Za-z0-9_]+)\s*$", re.M)
_DIRECTIVE_RE = re.compile(
    r"^\s*(?:/\*.*?\*/\s*)?\.(byte|short|word|float|double|space|ascii|asciz)\b(.*)$",
    re.M)
_ACCESS_RE = re.compile(r"\b(lbu|lb|lhu|lh|lw|sb|sh|sw)\b")
_INDEX: dict[str, dict[tuple[str, str], "DataDefinition"]] = {}


@dataclass(frozen=True)
class DataDefinition:
    overlay: str
    symbol: str
    path: str
    unit: str
    size: int | None


def _overlay_for(path: Path, version: str) -> str:
    parts = path.relative_to(REPO / "asm" / version).parts
    if "data" not in parts:
        return ""
    return "/".join(parts[:parts.index("data")]).upper()


def _number(text: str) -> int | None:
    token = text.strip().split(",", 1)[0].strip()
    try:
        return int(token, 0)
    except ValueError:
        return None


def _definition(overlay: str, symbol: str, rel: str, body: str) -> DataDefinition:
    directives = _DIRECTIVE_RE.findall(body)
    kinds = [kind for kind, _ in directives]
    widths = {"byte": 1, "short": 2, "word": 4, "float": 4, "double": 8}
    if kinds and all(kind == kinds[0] for kind in kinds) and kinds[0] in widths:
        unit = kinds[0]
        size = len(kinds) * widths[unit]
    elif len(directives) == 1 and directives[0][0] == "space":
        unit = "space"
        size = _number(directives[0][1])
    elif kinds and all(kind in ("ascii", "asciz") for kind in kinds):
        unit, size = "byte", None
    else:
        unit, size = "mixed", None
    return DataDefinition(overlay, symbol, rel, unit, size)


def build_index(version: str = "us") -> dict[tuple[str, str], DataDefinition]:
    if version in _INDEX:
        return _INDEX[version]
    root = REPO / "asm" / version
    index: dict[tuple[str, str], DataDefinition] = {}
    for path in root.rglob("*.s"):
        if "data" not in path.parts or "nonmatchings" in path.parts:
            continue
        overlay = _overlay_for(path, version)
        if not overlay:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        matches = list(_LABEL_RE.finditer(text))
        for pos, match in enumerate(matches):
            symbol = match.group(1)
            end = matches[pos + 1].start() if pos + 1 < len(matches) else len(text)
            body = text[match.end():end]
            rel = str(path.relative_to(REPO)).replace("\\", "/")
            index[(overlay, symbol)] = _definition(
                overlay, symbol, rel, body)
    _INDEX[version] = index
    return index


def _find(symbol: str, overlay: str, version: str) -> DataDefinition | None:
    index = build_index(version)
    exact = index.get((overlay.strip("/").upper(), symbol))
    if exact:
        return exact
    matches = [item for (owner, name), item in index.items()
               if name == symbol]
    if len(matches) == 1:
        return matches[0]
    signatures = {(item.unit, item.size) for item in matches}
    if matches and len(signatures) == 1:
        return matches[0]
    return None


def _ctype(defn: DataDefinition, asm_text: str, symbol: str) -> tuple[str, str]:
    ops = []
    for line in asm_text.splitlines():
        if symbol in line:
            match = _ACCESS_RE.search(line)
            if match and match.group(1) not in ops:
                ops.append(match.group(1))
    loads = {
        "lbu": "u8", "lb": "s8", "lhu": "u16", "lh": "s16", "lw": "s32",
    }
    chosen = {loads[op] for op in ops if op in loads}
    if len(chosen) == 1:
        return chosen.pop(), ",".join(ops)
    defaults = {
        "byte": "u8", "short": "s16", "word": "s32",
        "float": "f32", "double": "f64", "space": "u8", "mixed": "u8",
    }
    return defaults[defn.unit], ",".join(ops)


def _entity_bases(version: str) -> list[tuple[int, int]]:
    path = REPO / "config" / f"symbols.{version}.txt"
    if not path.exists():
        return []
    found = []
    pattern = re.compile(
        r"^g_Entities_(\d+)\s*=\s*(0x[0-9A-Fa-f]+);", re.M)
    for match in pattern.finditer(path.read_text(
            encoding="utf-8", errors="replace")):
        found.append((int(match.group(2), 16), int(match.group(1))))
    return sorted(found)


def _entity_fields() -> dict[int, str]:
    path = REPO / "include" / "game.h"
    text = path.read_text(encoding="utf-8", errors="replace")
    start = text.find("typedef struct Entity {")
    end = text.find("} Entity;", start)
    if start < 0 or end < 0:
        return {}
    fields = {}
    pattern = re.compile(
        r"/\*\s*0x([0-9A-Fa-f]+)\s*\*/\s*[^;:]+?\b"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^]]*\])?\s*;")
    for match in pattern.finditer(text[start:end]):
        fields[int(match.group(1), 16)] = match.group(2)
    return fields


def _entity_address_alias(symbol: str, version: str) -> str:
    match = re.fullmatch(r"D_([0-9A-Fa-f]{8})", symbol)
    if not match:
        return ""
    address = int(match.group(1), 16)
    bases = [item for item in _entity_bases(version) if item[0] <= address]
    if not bases:
        return ""
    base_address, base_index = bases[-1]
    entity_size = 0xBC
    delta = address - base_address
    # Named g_Entities anchors occur every 32 slots. Refuse addresses outside
    # that calibrated window instead of treating every later global as Entity.
    if delta >= 32 * entity_size:
        return ""
    entity_index = base_index + delta // entity_size
    offset = delta % entity_size
    fields = _entity_fields()
    if offset == 0:
        expression = f"&g_Entities[{entity_index}]"
        detail = "Entity+0x0"
    elif offset in fields:
        expression = f"&g_Entities[{entity_index}].{fields[offset]}"
        detail = f"Entity+0x{offset:X}"
    else:
        prior = [(at, name) for at, name in fields.items() if at < offset]
        if not prior:
            return ""
        at, name = max(prior)
        expression = (
            f"(u8*)&g_Entities[{entity_index}] + 0x{offset:X}")
        detail = f"inside {name}+0x{offset - at:X}"
    return (
        f"extern Entity g_Entities[]; /* address alias {symbol} = "
        f"{expression}; {detail}, derived from config symbols and the "
        f"annotated Entity layout */")


def declaration(symbol: str, overlay: str = "", asm_text: str = "",
                version: str = "us") -> str:
    if not symbol.startswith("D_"):
        return ""
    defn = _find(symbol, overlay, version)
    if not defn:
        return _entity_address_alias(symbol, version)
    ctype, access = _ctype(defn, asm_text, symbol)
    size = "unknown" if defn.size is None else hex(defn.size)
    access_note = f"; target access {access}" if access else ""
    return (
        f"extern {ctype} {symbol}[]; "
        f"/* retained {defn.overlay} data {defn.path}, size {size}{access_note} */")


def lookup_declarations(symbols: list[str], overlay: str = "",
                        asm_text: str = "", version: str = "us") -> dict[str, str]:
    return {
        symbol: found
        for symbol in symbols
        if (found := declaration(symbol, overlay, asm_text, version))
    }


def self_test() -> int:
    checks = []

    def check(name: str, condition: bool) -> None:
        checks.append(condition)
        print(("  ok   " if condition else "  FAIL ") + name)

    index = build_index("us")
    check("retained data index is populated", len(index) > 100)
    byte = declaration("D_us_801812B9", "BOSS/BO6",
                       "lbu $v0, %lo(D_us_801812B9)($at)")
    check("overlay byte label uses target unsigned load", byte.startswith(
        "extern u8 D_us_801812B9[];"))
    word = declaration("D_80032E84", "MAIN",
                       "lw $v1, %lo(D_80032E84)($v1)")
    check("main word label uses target word load", word.startswith(
        "extern s32 D_80032E84[];"))
    alias = declaration("D_80078618", "ST/RCEN")
    check("address alias resolves the calibrated entity index",
          "&g_Entities[112]" in alias)
    member = declaration("D_8007C6E8", "ST/RCEN")
    check("address alias resolves an annotated Entity member",
          "&g_Entities[200].params" in member)
    interior = declaration("D_80076412", "BOSS/BO6")
    check("address alias preserves an interior field offset",
          "g_Entities[65]" in interior and "inside ext+0x2" in interior)
    check("unknown raw label is refused",
          declaration("D_us_DEADBEEF", "BOSS/BO6") == "")
    check("semantic symbols are outside this resolver",
          declaration("g_Entities", "BOSS/BO6") == "")
    print()
    print("self-test PASSED" if all(checks) else "self-test FAILED")
    return 0 if all(checks) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="")
    parser.add_argument("--overlay", default="")
    parser.add_argument("--version", default="us")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.symbol:
        parser.error("--symbol is required")
    found = declaration(args.symbol, args.overlay, version=args.version)
    if not found:
        print("unresolved")
        return 1
    print(found)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
