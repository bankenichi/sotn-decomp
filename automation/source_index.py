#!/usr/bin/env python3
"""Source-level indexes shared by progress, twins, and transplant tooling."""
from __future__ import annotations

import re
from pathlib import Path


_INCLUDE_ASM = re.compile(
    r'(?m)^[ \t]*INCLUDE_ASM(?:_OLD)?\s*\(\s*"([^"]+)"\s*,'
    r"\s*([A-Za-z_]\w*)\s*\)\s*;"
)


def _mask_comments(text: str) -> str:
    """Replace C comments with spaces while preserving offsets and newlines."""
    out = list(text)
    i = 0
    state = "code"
    while i < len(text):
        pair = text[i : i + 2]
        if state == "code":
            if pair == "//":
                out[i] = out[i + 1] = " "
                state = "line"
                i += 2
                continue
            if pair == "/*":
                out[i] = out[i + 1] = " "
                state = "block"
                i += 2
                continue
            if text[i] == '"':
                state = "string"
            elif text[i] == "'":
                state = "char"
        elif state == "line":
            if text[i] == "\n":
                state = "code"
            else:
                out[i] = " "
        elif state == "block":
            if pair == "*/":
                out[i] = out[i + 1] = " "
                state = "code"
                i += 2
                continue
            if text[i] != "\n":
                out[i] = " "
        elif state in ("string", "char"):
            quote = '"' if state == "string" else "'"
            if text[i] == "\\":
                i += 2
                continue
            if text[i] == quote:
                state = "code"
        i += 1
    return "".join(out)


def include_asm_symbols(src_root: Path) -> set[tuple[str, str]]:
    """Return path-aware live INCLUDE_ASM records below one source root."""
    out: set[tuple[str, str]] = set()
    for path in src_root.rglob("*.c"):
        try:
            text = _mask_comments(path.read_text(
                encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        for asm_rel, symbol in _INCLUDE_ASM.findall(text):
            out.add((asm_rel.strip("/").replace("\\", "/"), symbol))
    return out
