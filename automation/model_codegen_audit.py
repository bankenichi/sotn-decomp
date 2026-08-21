#!/usr/bin/env python3
"""Find model-contributed matches whose unusual C lacks codegen reasoning.

The queue and match_provenance.py decide which matched functions had a model
contributor. quality_audit.py decides whether a CODEGEN comment contains an
actual explanation. This tool only joins those existing authorities to source
locations and a deliberately small set of review-worthy C shapes.

Read-only and advisory. Missing explanations do not make a match incorrect;
they identify knowledge that should be recovered while the compiler constraint
or assembly reasoning is still discoverable.
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import match_provenance as provenance
from quality_audit import _has_codegen_reason, _mask_c_comments_and_literals

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"


def _source_files() -> list[Path]:
    out = []
    for suffix in ("*.c", "*.h"):
        for path in SRC.rglob(suffix):
            parts = path.relative_to(SRC).parts
            if parts[0] == "saturn" or any(part.endswith("_psp") for part in parts):
                continue
            out.append(path)
    return sorted(set(out))


def _definition_end(masked: str, brace: int) -> int | None:
    """Walk one body while treating preprocessor branches as alternatives."""
    directive_re = re.compile(
        r"^[ \t]*#[ \t]*(if|ifdef|ifndef|elif|else|endif)\b[^\n]*"
        r"(?:\\\n[^\n]*)*",
        re.MULTILINE,
    )
    directives = {match.start(): (match.end(), match.group(1))
                  for match in directive_re.finditer(masked, brace)}
    branch_stack: list[dict] = []
    depth = 0
    pos = brace
    while pos < len(masked):
        directive = directives.get(pos)
        if directive is not None:
            end, kind = directive
            if kind in ("if", "ifdef", "ifndef"):
                branch_stack.append(
                    {"base": depth, "ends": [], "has_else": False})
            elif kind in ("elif", "else") and branch_stack:
                branch = branch_stack[-1]
                branch["ends"].append(depth)
                depth = branch["base"]
                if kind == "else":
                    branch["has_else"] = True
            elif kind == "endif" and branch_stack:
                branch = branch_stack.pop()
                branch["ends"].append(depth)
                if not branch["has_else"]:
                    branch["ends"].append(branch["base"])
                if len(set(branch["ends"])) != 1:
                    return None
                depth = branch["ends"][0]
            pos = end
            continue
        if masked[pos] == "{":
            depth += 1
        elif masked[pos] == "}":
            depth -= 1
            if depth == 0:
                return pos + 1
        pos += 1
    return None


def _function_span(source: str, function: str) -> tuple[int, int] | None:
    """Return one definition span using a comment and literal-safe brace walk."""
    masked = _mask_c_comments_and_literals(source)
    for match in re.finditer(rf"\b{re.escape(function)}\s*\(", masked):
        paren = masked.find("(", match.start())
        depth = 0
        close = -1
        for pos in range(paren, len(masked)):
            if masked[pos] == "(":
                depth += 1
            elif masked[pos] == ")":
                depth -= 1
                if depth == 0:
                    close = pos
                    break
        if close < 0:
            continue
        brace = close + 1
        while brace < len(masked) and masked[brace].isspace():
            brace += 1
        if brace >= len(masked) or masked[brace] != "{":
            continue
        end = _definition_end(masked, brace)
        if end is not None:
            start = source.rfind("\n", 0, match.start()) + 1
            return start, end
    return None


def _source_aliases(source: str) -> dict[str, str]:
    """Recover explicit old-name to current-name mappings from source notes."""
    aliases = {}
    for pattern in (
        r"\b([A-Za-z_]\w*)\s+was\s+([A-Za-z_]\w*)\b",
        r"\b([A-Za-z_]\w*)\s+\(as\s+([A-Za-z_]\w*)\)",
    ):
        for match in re.finditer(pattern, source):
            current, old = match.groups()
            aliases[old] = current
    return aliases


def unusual_shapes(function_text: str) -> list[str]:
    """Strong signals that an odd source shape may be load-bearing."""
    masked = _mask_c_comments_and_literals(function_text)
    shapes = []
    if re.search(r"\bvolatile\b", masked):
        shapes.append("volatile")
    if re.search(r"\bdo\b[\s\S]*?\bwhile\s*\(\s*(?:0|1|false|true)\s*\)\s*;",
                 masked, re.I):
        shapes.append("constant-do-while")
    # quality_audit owns complete empty-loop parsing. Excluding `while` here
    # prevents a do-while terminator from being mislabeled as a null body.
    if re.search(r"\b(?:if|for)\s*\([^;{}]*\)\s*;|\belse\s*;", masked):
        shapes.append("null-control-body")
    # A goto can directly express semantics, as in a retry loop, so its mere
    # presence is not evidence of compiler shaping. A scalar `x = x` is much
    # stronger, but member-to-parameter stores such as `self->step = step`
    # must not be reduced to the final identifier on the left-hand side.
    if re.search(r"(?<![\w.>*&])([A-Za-z_]\w*)\s*=\s*\1\s*;", masked):
        shapes.append("self-assignment")
    return shapes


def _index_functions(functions: set[str]) -> dict[str, list[tuple[Path, int, str]]]:
    index: dict[str, list[tuple[Path, int, str]]] = defaultdict(list)
    sources = []
    aliases = {}
    for path in _source_files():
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        sources.append((path, source))
        aliases.update(_source_aliases(source))
    for function in functions:
        shortened = re.fullmatch(r"(func_[0-9A-Fa-f]{8})_[0-9A-Fa-f]{8}", function)
        if shortened:
            aliases.setdefault(function, shortened.group(1))
    lookup = functions | {aliases[name] for name in functions if name in aliases}
    for path, source in sources:
        for function in lookup:
            if function not in source:
                continue
            span = _function_span(source, function)
            if span is None:
                continue
            start, end = span
            line = source.count("\n", 0, start) + 1
            index[function].append((path, line, source[start:end]))
    for old, current in aliases.items():
        if old in functions and not index.get(old):
            index[old].extend(index.get(current, []))
    return index


@lru_cache(maxsize=None)
def _include_closure(directory: Path) -> frozenset[Path]:
    """Return quoted includes reachable from source files in one overlay."""
    if not directory.is_dir():
        return frozenset()
    frontier = [path for path in directory.rglob("*")
                if path.suffix in (".c", ".h")]
    visited = set()
    included = set()
    while frontier:
        path = frontier.pop()
        if path in visited:
            continue
        visited.add(path)
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in re.finditer(r'^\s*#\s*include\s+"([^"]+)"', source, re.MULTILINE):
            candidate = (path.parent / match.group(1)).resolve()
            try:
                candidate.relative_to(REPO.resolve())
            except ValueError:
                continue
            if not candidate.is_file():
                continue
            included.add(candidate)
            if candidate.suffix in (".c", ".h") and candidate not in visited:
                frontier.append(candidate)
    return frozenset(included)


def _choose_location(
        row: dict, locations: list[tuple[Path, int, str]],
        included_paths: set[Path] | frozenset[Path] | None = None
) -> tuple[Path, int, str] | None:
    overlay = str(row.get("overlay") or "").lower()
    expected = SRC / Path(*overlay.split("/")) if overlay else None
    scoped = [item for item in locations
              if expected is not None and (item[0] == expected or expected in item[0].parents)]
    choices = scoped or locations
    if len(choices) == 1:
        return choices[0]
    note = str(row.get("note") or "")
    hinted = [item for item in choices
              if item[0].relative_to(REPO).as_posix() in note]
    if len(hinted) == 1:
        return hinted[0]
    if expected is not None:
        included = included_paths if included_paths is not None else _include_closure(expected)
        reachable = [item for item in choices if item[0].resolve() in included]
        if len(reachable) == 1:
            return reachable[0]
    return None


def audit_rows(rows: list[dict]) -> tuple[list[dict], dict[str, int]]:
    model_rows = [row for row in rows if "model-fleet" in row.get("contributors", [])]
    index = _index_functions({str(row.get("function") or "") for row in model_rows} - {""})
    findings = []
    counts = {"model": len(model_rows), "unusual": 0, "explained": 0,
              "review": 0, "unlocated": 0}
    for row in model_rows:
        function = str(row.get("function") or "")
        locations = index.get(function, [])
        location = _choose_location(row, locations)
        if location is None:
            counts["unlocated"] += 1
            kind = "unlocated" if not locations else "ambiguous"
            findings.append({"id": row.get("id", ""), "function": function,
                             "kind": kind, "shapes": [], "path": "", "line": 0,
                             "candidates": [item[0].relative_to(REPO).as_posix()
                                            for item in locations]})
            continue
        path, line, function_text = location
        shapes = unusual_shapes(function_text)
        if not shapes:
            continue
        counts["unusual"] += 1
        if _has_codegen_reason(function_text):
            counts["explained"] += 1
            continue
        counts["review"] += 1
        findings.append({
            "id": row.get("id", ""), "function": function,
            "kind": "missing-codegen-reason", "shapes": shapes,
            "path": path.relative_to(REPO).as_posix(), "line": line,
        })
    return findings, counts


def self_test() -> int:
    plain = """void Example(void) {
    volatile int pad;
    do { pad = 1; } while (0);
    goto done;
done:
    return;
}
"""
    explained = plain.replace(
        "    volatile int pad;",
        "    // CODEGEN: Preserve the target stack frame and branch layout.\n"
        "    volatile int pad;")
    provenance_only = plain.replace(
        "    volatile int pad;", "    // Model-produced candidate.\n    volatile int pad;")
    conditional = """void Conditional(void) {
#ifdef VERSION_PSP
    if (one) {
#else
    if (two) {
#endif
        work();
    }
}
"""
    alias_note = "// FireWavePrimHelper1 was func_us_801D1184_from_are\n"
    shared = (SRC / "st" / "shared.h", 1, plain)
    local_copy = (SRC / "st" / "sel" / "copy.c", 1, plain)
    member_store = """void SetStep(s32 step) {
    g_CurrentEntity->step = step;
}
"""
    semantic_retry = """void Retry(void) {
retry:
    if (!ready()) {
        goto retry;
    }
}
"""
    real_self_assignment = "void Shape(void) { value = value; }\n"
    checks = [
        (_function_span(plain, "Example") is not None, "definition is located"),
        (unusual_shapes(plain) == ["volatile", "constant-do-while"],
         "strong unusual shapes are classified"),
        (_has_codegen_reason(explained), "a substantive CODEGEN reason is accepted"),
        (not _has_codegen_reason(provenance_only),
         "provenance alone does not waive missing compiler reasoning"),
        (_function_span("void Example(void);", "Example") is None,
         "a prototype is not a definition"),
        (_function_span(conditional, "Conditional") is not None,
         "mutually exclusive branches may share a closing brace"),
        (_source_aliases(alias_note).get("func_us_801D1184_from_are") ==
         "FireWavePrimHelper1", "explicit rename notes resolve old queue names"),
        (_choose_location({"overlay": "ST/RNO0"}, [shared, local_copy],
                          {shared[0].resolve()}) == shared,
         "the overlay include graph selects its shared implementation"),
        (unusual_shapes(member_store) == [],
         "a member store from a same-named parameter is not self-assignment"),
        (unusual_shapes(semantic_retry) == [],
         "a semantic retry loop is not presumed to be compiler shaping"),
        (unusual_shapes(real_self_assignment) == ["self-assignment"],
         "a genuine scalar self-assignment remains review-worthy"),
    ]
    failed = [label for ok, label in checks if not ok]
    for ok, label in checks:
        print(("  ok   " if ok else "  FAIL ") + label)
    if failed:
        print(f"model_codegen_audit self-test: {len(failed)} failure(s)")
        return 1
    print("model_codegen_audit self-test: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    records = provenance.load_queue()
    rows = provenance.analyse(records, use_git=False, jobs=1, progress=False)
    findings, counts = audit_rows(rows)
    print("MODEL CODEGEN REVIEW: "
          f"{counts['model']} model-contributed matches; "
          f"{counts['unusual']} with strong unusual shapes; "
          f"{counts['explained']} explained; {counts['review']} need review; "
          f"{counts['unlocated']} unlocated or ambiguous")
    for finding in findings[:max(0, args.limit)]:
        where = (f"{finding['path']}:{finding['line']}" if finding["path"]
                 else finding["id"])
        detail = ", ".join(finding["shapes"]) or finding["kind"]
        if finding.get("candidates"):
            detail += ": " + ", ".join(finding["candidates"])
        print(f"  {where}  {finding['function']}  [{detail}]")
    print("Read-only advisory report; a finding requests explanation, not a rewrite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
