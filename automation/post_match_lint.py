#!/usr/bin/env python3
"""Report cosmetic residue in fork-added decompiled C.

This is the narrow companion to quality_audit.py. By default it checks
uncommitted source changes against HEAD, which is the state a newly matched
function occupies before it is committed. Pass --since or --all for a wider
audit. It looks for patterns left by generated matches that are mechanically
suspicious but not evidence that a binary match is wrong: duplicate externs,
shared-name macro shadows, suspicious wide scalar types, stray null statements,
undocumented switch fallthrough, trailing whitespace, and worker declaration
boilerplate.

STRICTLY READ-ONLY. Findings are advisory and the normal report exits zero.

Usage:
    python3 automation/post_match_lint.py
    python3 automation/post_match_lint.py --since <commit>
    python3 automation/post_match_lint.py --file src/st/rchi/e_gaibon.c
    python3 automation/post_match_lint.py --all
    python3 automation/post_match_lint.py --self-test
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

from quality_audit import _mask_c_comments_and_literals

REPO = Path(__file__).resolve().parent.parent
DEFAULT_REF = "HEAD"
WORKER_MARKER = "Declarations injected by the worker"


def _header_symbols(root: Path = REPO) -> dict[str, str]:
    """Return shared macro and enum names with one source location each."""
    symbols: dict[str, str] = {}
    headers = list((root / "include").rglob("*.h"))
    headers += list((root / "src").rglob("*.h"))
    for path in sorted(headers):
        try:
            lines = path.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, 1):
            match = re.match(r"^\s*#\s*define\s+([A-Za-z_]\w*)\b", line)
            if match is None:
                match = re.match(r"^\s*([A-Z][A-Z0-9_]+)\s*(?:=|,)", line)
            if match:
                rel = path.relative_to(root)
                symbols.setdefault(match.group(1), f"{rel}:{lineno}")
    return symbols


def _changed_lines(ref: str) -> dict[str, set[int]]:
    """Lines added relative to ref, including current working-tree edits."""
    try:
        result = subprocess.run(
            ["git", "diff", "-U0", ref, "--", "src/"], cwd=REPO,
            capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return {}
    changed: dict[str, set[int]] = defaultdict(set)
    current = ""
    for line in result.stdout.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            continue
        if not current or not line.startswith("@@"):
            continue
        match = re.search(r"\+(\d+)(?:,(\d+))?", line)
        if not match:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or 1)
        changed[current].update(range(start, start + count))
    return changed


def _fallthroughs(source: str) -> list[tuple[int, int]]:
    """Return case spans that reach the next label without an annotation."""
    masked = _mask_c_comments_and_literals(source)
    labels = list(re.finditer(
        r"(?m)^[ \t]*(?:case[ \t]+[^:\n]+|default)[ \t]*:[ \t]*", masked))
    findings: list[tuple[int, int]] = []
    for index, label in enumerate(labels[:-1]):
        next_label = labels[index + 1]
        body = masked[label.end():next_label.start()]
        raw_body = source[label.end():next_label.start()]
        if not body.strip() or re.search(
                r"\bfall(?:\s+|-)through\b|\bfallthrough\b", raw_body, re.I):
            continue
        # A nested switch label is not a sibling. Brace depth is enough to
        # distinguish it because comments and literals have already been masked.
        if body.count("{") != body.count("}"):
            continue
        if re.search(r"\b(?:break|return|continue|goto)\b[^;{}]*;\s*$", body):
            continue
        start = source.count("\n", 0, label.start()) + 1
        end = source.count("\n", 0, next_label.start()) + 1
        findings.append((start, end))
    return findings


def check_source(
        path: Path, source: str, shared: dict[str, str],
        only_lines: set[int] | None = None) -> list[dict]:
    """Return advisory findings for one C source."""
    rel = str(path.relative_to(REPO)) if path.is_relative_to(REPO) else path.name
    lines = source.splitlines()
    findings: list[dict] = []

    def add(kind: str, lineno: int, detail: str) -> None:
        if only_lines is not None and lineno not in only_lines:
            return
        findings.append({"file": rel, "line": lineno, "kind": kind,
                         "detail": detail})

    declarations: dict[str, list[int]] = defaultdict(list)
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if line != line.rstrip():
            add("trailing_whitespace", lineno, "line ends in whitespace")
        if WORKER_MARKER in line:
            add("worker_boilerplate", lineno,
                "temporary worker declaration banner remains in shipped source")
        if re.match(r"^\s*;\s*$", line):
            add("stray_null_statement", lineno,
                "standalone null statement outside a control header")

        extern = re.match(r"^\s*extern\s+.+;\s*$", line)
        if extern:
            declarations[re.sub(r"\s+", " ", stripped)].append(lineno)

        macro = re.match(r"^\s*#\s*define\s+([A-Za-z_]\w*)\b", line)
        if macro and macro.group(1) in shared:
            name = macro.group(1)
            add("shared_macro_shadow", lineno,
                f"{name} already exists in {shared[name]}")

        wide = re.match(
            r"^\s*(?:unsigned\s+long|long)\s+([A-Za-z_]\w*)\s*(?:[;=])", line)
        if wide and re.search(
                r"(?:anim|frame|pose|step|timer|palette|flags?)", wide.group(1), re.I):
            add("suspicious_scalar_type", lineno,
                f"{wide.group(1)} uses long for a field-like value; verify target width")

    for declaration, locations in declarations.items():
        for lineno in locations[1:]:
            add("duplicate_extern", lineno,
                f"duplicate of line {locations[0]}: {declaration}")

    for start, end in _fallthroughs(source):
        if only_lines is None or any(line in only_lines for line in range(start, end + 1)):
            findings.append({"file": rel, "line": start,
                             "kind": "missing_fallthrough",
                             "detail": f"case reaches the label at line {end} without // fallthrough"})
    return findings


def self_test() -> int:
    fixture = """\
#define ENTITY_DEFAULT 0
extern EInit thing;
extern EInit thing;
void Example(void) {
    unsigned long animFrame;
    ;
    switch (step) {
    case 0:
        use();
    case 1:
        return;
    }
}
/* Declarations injected by the worker: temporary. */
"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = root / "fixture.c"
        path.write_text(fixture)
        shared = {"ENTITY_DEFAULT": "include/game.h:1"}
        findings = check_source(path, fixture, shared)
    got = {finding["kind"] for finding in findings}
    want = {"shared_macro_shadow", "duplicate_extern",
            "suspicious_scalar_type", "stray_null_statement",
            "missing_fallthrough", "worker_boilerplate"}
    if got != want:
        print(f"FAIL expected {sorted(want)}, got {sorted(got)}")
        return 1
    annotated = """\
switch (step) {
case 0:
    use();
    // fallthrough
case 1:
    return;
}
"""
    if _fallthroughs(annotated):
        print("FAIL standard // fallthrough annotation was not recognized")
        return 1
    scoped = check_source(path, fixture, shared, only_lines={3})
    if {finding["kind"] for finding in scoped} != {"duplicate_extern"}:
        print(f"FAIL changed-line scope: {scoped}")
        return 1
    print("post_match_lint self-test: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", default=DEFAULT_REF,
                        help="compare against this ref (default HEAD)")
    parser.add_argument("--file", default="")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    shared = _header_symbols()
    scopes: list[tuple[Path, set[int] | None]] = []
    if args.file:
        scopes = [(REPO / args.file, None)]
    elif args.all:
        scopes = [(path, None) for path in sorted((REPO / "src").rglob("*.c"))]
    else:
        scopes = [(REPO / rel, lines)
                  for rel, lines in sorted(_changed_lines(args.since).items())
                  if rel.endswith(".c") and (REPO / rel).exists()]

    findings: list[dict] = []
    for path, only_lines in scopes:
        try:
            source = path.read_text(errors="ignore")
        except OSError:
            continue
        findings.extend(check_source(path, source, shared, only_lines))

    print(f"POST-MATCH LINT: {len(findings)} advisory finding(s) in {len(scopes)} file(s)")
    grouped: dict[str, list[dict]] = defaultdict(list)
    for finding in findings:
        grouped[finding["kind"]].append(finding)
    for kind in sorted(grouped):
        print(f"\n{kind} x{len(grouped[kind])}")
        for finding in grouped[kind][:args.limit]:
            print(f"  {finding['file']}:{finding['line']}  {finding['detail']}")
    print("\nRead-only advisory report; findings do not change the exit status.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
