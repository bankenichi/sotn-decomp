import re
import argparse
from typing import List, Optional, Tuple
from pathlib import Path


_FUNCTION = re.compile(
    r"(?m)^[ \t]*"
    r"(?P<head>[A-Za-z_][A-Za-z0-9_ \t*\n]*?[ \t*]+"
    r"(?P<name>[A-Za-z_]\w*)\s*\([^;{}]*\)\s*)\{"
)


def _find_bracket_end(input: str, start_index: int) -> int:
    """Find a function's closing brace without counting comments or literals."""
    level = 1
    assert input[start_index] == "{"
    i = start_index + 1
    state = "code"
    while i < len(input):
        pair = input[i : i + 2]
        char = input[i]
        if state == "code":
            if pair == "//":
                state = "line"
                i += 2
                continue
            if pair == "/*":
                state = "block"
                i += 2
                continue
            if char == '"':
                state = "string"
            elif char == "'":
                state = "char"
            elif char == "{":
                level += 1
            elif char == "}":
                level -= 1
                if level == 0:
                    break
        elif state == "line":
            if char == "\n":
                state = "code"
        elif state == "block":
            if pair == "*/":
                state = "code"
                i += 2
                continue
        elif state in ("string", "char"):
            quote = '"' if state == "string" else "'"
            if char == "\\":
                i += 2
                continue
            if char == quote:
                state = "code"
        i += 1

    assert level == 0, "unbalanced {}"
    return i


def _function_definitions(source: str) -> List[Tuple[int, int, int, str]]:
    """Return (start, opening brace, end, name) for top-level definitions."""
    out: List[Tuple[int, int, int, str]] = []
    cursor = 0
    while True:
        match = _FUNCTION.search(source, cursor)
        if match is None:
            break
        opening = match.end() - 1
        end = _find_bracket_end(source, opening)
        out.append((match.start(), opening, end, match.group("name")))
        cursor = end + 1
    return out


def strip_other_fns(source: str, keep_fn_name: str) -> str:
    """Replace unrelated function bodies with declarations.

    Directly called helpers are retained transitively. Removing a static inline
    helper can change the selected function's codegen even though it makes an
    unrelated GNU extension disappear, so target-only is too aggressive.
    """
    definitions = _function_definitions(source)
    names = {name for _start, _opening, _end, name in definitions}
    bodies = {
        name: source[opening : end + 1]
        for _start, opening, end, name in definitions
    }
    keep = {keep_fn_name}
    pending = [keep_fn_name]
    while pending:
        body = bodies.get(pending.pop(), "")
        for name in names - keep:
            if re.search(r"\b" + re.escape(name) + r"\s*\(", body):
                keep.add(name)
                pending.append(name)

    pieces: List[str] = []
    cursor = 0
    for start, opening, end, name in definitions:
        pieces.append(source[cursor:start])
        if name.startswith("PERM") or name in keep:
            pieces.append(source[start : end + 1])
        else:
            pieces.append(source[start:opening].rstrip() + ";")
        cursor = end + 1
    pieces.append(source[cursor:])
    return "".join(pieces)


def strip_other_fns_and_write(
    source: str, fn_name: str, out_filename: Optional[str] = None
) -> None:
    stripped = strip_other_fns(source, fn_name)

    if out_filename is None:
        print(stripped)
    else:
        with open(out_filename, "w", encoding="utf-8") as f:
            f.write(stripped)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove all but a single function definition from a file."
    )
    parser.add_argument("c_file", help="File containing the function.")
    parser.add_argument("fn_name", help="Function name.")
    args = parser.parse_args()

    source = Path(args.c_file).read_text()
    strip_other_fns_and_write(source, args.fn_name, args.c_file)


if __name__ == "__main__":
    main()
