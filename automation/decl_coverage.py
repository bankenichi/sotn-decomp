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
    python3 automation/decl_coverage.py --use-queue --write-waves out.json
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import data_declarations

REPO = Path(__file__).resolve().parent.parent

# Mirrors worker_direct.extract_asm_symbols. Kept in sync deliberately: if the
# two drift, the ranking stops predicting what the worker will actually be
# given, which is the entire point of this script.
_ASM_SYM_RE = re.compile(
    r"%(?:hi|lo)\(\s*([A-Za-z_][A-Za-z0-9_]*)|"
    r"\bjal\s+([A-Za-z_][A-Za-z0-9_]*)")
_SYM_SKIP = {"hi", "lo"}
_C_MASK_RE = re.compile(
    r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'",
    re.DOTALL)
_LOCAL_INCLUDE_RE = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.MULTILINE)


def extract_asm_symbols(asm: str, exclude: str = "") -> list[str]:
    out: list[str] = []
    for m in _ASM_SYM_RE.finditer(asm or ""):
        s = m.group(1) or m.group(2)
        if s and s != exclude and s not in _SYM_SKIP and s not in out:
            out.append(s)
    return out


def source_for_asm(rel: str) -> Path | None:
    """Map one nonmatchings listing to the translation unit that owns it."""
    parts = Path(rel).parts
    try:
        asm_i = parts.index("asm")
        non_i = parts.index("nonmatchings")
    except ValueError:
        return None
    if non_i <= asm_i + 2 or non_i + 1 >= len(parts) - 1:
        return None
    prefix = parts[asm_i + 2:non_i]
    stem_parts = parts[non_i + 1:-1]
    source = REPO / "src" / Path(*prefix) / Path(*stem_parts)
    return source.with_suffix(".c")


def _stub_prefix(source: str, target: str) -> str | None:
    masked = _C_MASK_RE.sub(
        lambda match: "".join("\n" if ch == "\n" else " "
                              for ch in match.group(0)), source)
    stub = re.search(
        r"INCLUDE_ASM\([^;]*?,\s*" + re.escape(target) + r"\s*\)\s*;",
        masked)
    if not stub:
        return None
    return source[:stub.start()]


def _resolve_local_include(current: Path, name: str) -> Path | None:
    candidates = [current.parent / name, REPO / name,
                  REPO / "include" / name, REPO / "src" / name]
    root = REPO.resolve()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            resolved.relative_to(root)
        except (OSError, ValueError):
            continue
        if resolved.is_file():
            return resolved
    return None


def included_text_before_target(source_path: Path, source: str, target: str,
                                cache: dict[Path, str]) -> str:
    """Local include closure reachable before the target stub."""
    prefix = _stub_prefix(source, target)
    if prefix is None:
        return ""
    chunks: list[str] = []
    seen: set[Path] = set()

    def visit(current: Path, text: str) -> None:
        for name in _LOCAL_INCLUDE_RE.findall(text):
            path = _resolve_local_include(current, name)
            if path is None or path in seen:
                continue
            seen.add(path)
            if path not in cache:
                cache[path] = path.read_text(encoding="utf-8", errors="replace")
            child = cache[path]
            chunks.append(child)
            visit(path, child)

    visit(source_path, prefix)
    return "\n".join(chunks)


def lexically_visible_functions(source: str, target: str,
                                symbols: list[str],
                                included: str = "") -> list[str]:
    """Function definitions visible before a target stub, including headers."""
    prefix = _stub_prefix(source, target)
    if prefix is None:
        return []
    visible_text = prefix + "\n" + included
    masked = _C_MASK_RE.sub(
        lambda match: "".join("\n" if ch == "\n" else " "
                              for ch in match.group(0)), visible_text)
    visible = []
    for symbol in symbols:
        if re.search(r"\b" + re.escape(symbol)
                     + r"\s*\([^;{}]*\)\s*\{", masked, re.DOTALL):
            visible.append(symbol)
    return visible


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


_ASM_INDEX: dict[str, dict[str, list[Path]]] = {}


def build_asm_index(version: str = "us") -> dict[str, list[Path]]:
    """Walk asm/<version> ONCE and retain every path for each function name.

    The first version of this called rglob() per function. That is
    O(functions x files) and with ~1300 unmatched functions over the full asm
    tree it did not finish inside a tool call. One walk, then dict lookups.
    """
    global _ASM_INDEX
    if version in _ASM_INDEX:
        return _ASM_INDEX[version]
    index: dict[str, list[Path]] = {}
    base = REPO / "asm" / version
    for p in base.rglob("*.s"):
        if "nonmatchings" not in p.parts:
            continue
        index.setdefault(p.stem, []).append(p)
    _ASM_INDEX[version] = index
    return index


def asm_overlay(path: Path, version: str = "us") -> str:
    """Overlay key for an unmatched assembly path."""
    try:
        parts = path.relative_to(REPO / "asm" / version).parts
        stop = parts.index("nonmatchings")
    except (ValueError, OSError):
        return ""
    return "/".join(parts[:stop]).upper()


def find_asm(function: str, version: str = "us",
             overlay: str = "") -> Path | None:
    """Resolve one listing, refusing an ambiguous bare function name."""
    hits = build_asm_index(version).get(function, [])
    if overlay:
        wanted = overlay.strip("/").upper()
        hits = [path for path in hits if asm_overlay(path, version) == wanted]
    return hits[0] if len(hits) == 1 else None


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


def priority_map(rows: list[dict]) -> dict[str, dict]:
    """Scheduler hints keyed by full queue identity.

    Function names are not unique across overlays. Keying by `function` made a
    later duplicate overwrite an earlier record's blocked verdict, so the
    scheduler could skip workable functions or serve blocked ones first.
    """
    priority = {}
    for rank, row in enumerate(rows):
        blocked = bool(row.get("undeclared_data", row.get("blocked", False)))
        priority[row["id"]] = {"rank": rank, "blocked": blocked}
    return priority


def supplement_worker_declarations(
        index: dict[str, str], per_file: dict[str, list[str]]) -> int:
    """Resolve ordinary prototypes and definitions exactly as the worker does.

    The fast declaration index historically scanned only physical `extern`
    lines. That made ordinary prototypes such as `void InitializeEntity(...);`
    look missing even though worker_direct resolves and injects them. Rank on
    the worker's real declaration surface, not on a cheaper approximation.
    """
    unresolved = sorted({
        symbol for symbols in per_file.values() for symbol in symbols
        if symbol not in index
        and not symbol.startswith(("D_", "jtbl_"))
    })
    if not unresolved:
        return 0
    win_dir = str(REPO / "automation" / "win")
    if win_dir not in sys.path:
        sys.path.insert(0, win_dir)
    import worker_direct as wd  # noqa: E402

    wd.WIN_REPO = str(REPO)
    added = 0
    for start in range(0, len(unresolved), 40):
        chunk = unresolved[start:start + 40]
        declarations = wd.lookup_declarations(chunk, limit=len(chunk))
        for declaration in declarations:
            hits = [symbol for symbol in chunk
                    if re.search(rf"\b{re.escape(symbol)}\b", declaration)]
            if len(hits) == 1 and hits[0] not in index:
                index[hits[0]] = declaration
                added += 1
    return added


def mechanical_wave(row: dict) -> str:
    """An exclusive, evidence-only lane for deterministic queue work."""
    if row.get("undeclared_data"):
        return "data-blocked"
    instructions = int(row.get("instructions", 0))
    missing = row.get("missing", [])
    if instructions <= 32 and not missing:
        return "tiny-closed"
    if instructions <= 32 and len(missing) == 1:
        return "tiny-one-gap"
    if instructions <= 128 and not missing:
        return "small-closed"
    if instructions <= 128 and len(missing) == 1:
        return "small-one-gap"
    return "general"


def validate_instruction_rows(rows: list[dict]) -> list[str]:
    """Return report rows that cannot support size-based classification.

    Missing counts used to fall through as zero, which silently promoted an
    unknown function into the cheapest wave after a grep timeout or partial
    result. A generated work plan must fail closed instead.
    """
    return [row.get("id", row.get("asm", "<unknown>")) for row in rows
            if not isinstance(row.get("instructions"), int)
            or row["instructions"] <= 0]


def validate_start_rows(rows: list[dict]) -> list[str]:
    """Return rows that cannot support lexical dependency ordering."""
    return [row.get("id", row.get("asm", "<unknown>")) for row in rows
            if _start_value(row) is None]


def symbol_scan_error(find_rc: int, files: list[str], grep_rc: int,
                      raw_lines: list[str], record_count: int) -> str:
    """Fail closed when batched asm-symbol discovery did not actually run."""
    if find_rc != 0:
        return f"asm find failed with {find_rc}"
    if record_count and not files:
        return "asm find returned no nonmatching function files"
    if grep_rc not in (0, 1):
        return f"asm symbol grep failed with {grep_rc}"
    if grep_rc == 1 and raw_lines:
        return "asm symbol grep returned no-match status with output"
    return ""


def _start_value(row: dict) -> int | None:
    value = row.get("start_address")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None


def write_wave_plan(path: Path, rows: list[dict],
                    coverage_path: Path | None = None) -> None:
    invalid = validate_instruction_rows(rows)
    if invalid:
        raise ValueError("refusing wave plan with missing/zero instruction "
                         f"counts: {', '.join(invalid[:8])}")
    invalid_starts = validate_start_rows(rows)
    if invalid_starts:
        raise ValueError("refusing wave plan with missing start addresses: "
                         f"{', '.join(invalid_starts[:8])}")
    waves: dict[str, list[dict]] = {}
    for row in sorted(rows, key=lambda item: (
            item["instructions"], item["id"])):
        lane = mechanical_wave(row)
        waves.setdefault(lane, []).append({
            "id": row["id"],
            "function": row.get("function", ""),
            "overlay": row.get("overlay", ""),
            "asm": row.get("asm", ""),
            "start_address": row.get("start_address", ""),
            "instructions": row["instructions"],
            "symbols": row["symbols"],
            "coverage": row["coverage"],
            "missing": row["missing"],
            "implicit_calls": row.get("implicit_calls", []),
            "undeclared_data": row["undeclared_data"],
        })
    units: dict[str, list[dict]] = {}
    for row in rows:
        asm_dir = str(Path(row.get("asm", "")).parent)
        if asm_dir and asm_dir != ".":
            units.setdefault(asm_dir, []).append(row)
    translation_units = [
        {
            "asm_dir": asm_dir,
            "count": len(items),
            "instructions": sum(item["instructions"] for item in items),
            "ids": [item["id"] for item in sorted(
                items, key=lambda value: (
                    value["instructions"], value["id"]))],
        }
        for asm_dir, items in units.items() if len(items) > 1
    ]
    translation_units.sort(key=lambda item: (
        -item["count"], item["instructions"], item["asm_dir"]))

    by_unit_symbol = {
        (str(Path(row.get("asm", "")).parent),
         row.get("function", "")): row
        for row in rows
    }
    dependency_edges = []
    adjacency: dict[str, set[str]] = {}
    for row in rows:
        implicit_calls = set(row.get("implicit_calls", []))
        dependency_symbols = set(row.get("missing", [])) | implicit_calls
        for symbol in dependency_symbols:
            # A C definition only resolves a missing declaration when it is in
            # the same translation unit and appears before the consumer. Same-
            # overlay definitions in another .c file are not visible here, and
            # later same-file definitions still require a prototype.
            unit = str(Path(row.get("asm", "")).parent)
            target = by_unit_symbol.get((unit, symbol))
            if target is None or target["id"] == row["id"]:
                continue
            consumer_start = _start_value(row)
            target_start = _start_value(target)
            if (consumer_start is None or target_start is None
                    or target_start >= consumer_start):
                continue
            dependency_edges.append({
                "consumer": row["id"],
                "dependency": target["id"],
                "symbol": symbol,
                "symbol_kind": ("implicit-call" if symbol in implicit_calls
                                else "missing"),
            })
            adjacency.setdefault(row["id"], set()).add(target["id"])
            adjacency.setdefault(target["id"], set()).add(row["id"])
    dependency_edges.sort(key=lambda item: (
        item["dependency"], item["consumer"], item["symbol"]))
    components = []
    unseen = set(adjacency)
    while unseen:
        start = min(unseen)
        stack = [start]
        component = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(adjacency.get(current, set()) - component)
        unseen -= component
        if len(component) > 1:
            components.append(sorted(component))
    components.sort(key=lambda item: (-len(item), item))

    if coverage_path is not None:
        coverage_bytes = coverage_path.read_bytes()
        coverage_source = coverage_path.as_posix()
    else:
        coverage_bytes = (json.dumps(rows, indent=2) + "\n").encode("utf-8")
        coverage_source = "in-memory canonical rows"
    document = {
        "generator": "automation/decl_coverage.py --write-waves",
        "coverage_source": coverage_source,
        "coverage_sha256": hashlib.sha256(coverage_bytes).hexdigest(),
        "thresholds": {"tiny_max_instructions": 32,
                       "small_max_instructions": 128,
                       "one_gap_max_missing": 1},
        "counts": {name: len(items) for name, items in waves.items()},
        "waves": waves,
        "translation_unit_summary": {
            "multi_function_units": len(translation_units),
            "functions_in_multi_function_units": sum(
                item["count"] for item in translation_units),
        },
        "translation_units": translation_units,
        "queue_dependency_summary": {
            "edges": len(dependency_edges),
            "coupled_groups": len(components),
            "functions_in_coupled_groups": sum(
                len(component) for component in components),
        },
        "queue_dependencies": dependency_edges,
        "queue_dependency_groups": components,
    }
    path.write_text(json.dumps(document, indent=2) + "\n")


def classification_marker(coverage_sha: str, waves_sha: str) -> str:
    return (f"#256 corrected classification coverage_sha256={coverage_sha} "
            f"waves_sha256={waves_sha}")


def classification_is_current(note: str, coverage_sha: str,
                              waves_sha: str) -> bool:
    return classification_marker(coverage_sha, waves_sha) in note


def wave_matches_coverage(wave_doc: dict, coverage_sha: str) -> bool:
    return wave_doc.get("coverage_sha256") == coverage_sha


def annotate_queue(rows: list[dict], coverage_path: Path,
                   waves_path: Path) -> int:
    """Append corrected classification evidence in one queue transaction."""
    sys.path.insert(0, str(REPO / "automation"))
    import scheduler  # noqa: E402

    wave_doc = json.loads(waves_path.read_text(encoding="utf-8"))
    dependencies: dict[str, list[str]] = {}
    for edge in wave_doc.get("queue_dependencies", []):
        dependencies.setdefault(edge["consumer"], []).append(edge["dependency"])
    coverage_sha = hashlib.sha256(coverage_path.read_bytes()).hexdigest()
    if not wave_matches_coverage(wave_doc, coverage_sha):
        print("refusing queue annotation: wave report coverage_sha256 does not "
              "match the supplied coverage JSON", file=sys.stderr)
        return 1
    waves_sha = hashlib.sha256(waves_path.read_bytes()).hexdigest()
    by_id = {row["id"]: row for row in rows}
    marker = classification_marker(coverage_sha, waves_sha)

    def update(records: list[dict]):
        updated = 0
        satisfied = 0
        for record in records:
            row = by_id.get(record.get("id"))
            if row is None or record.get("status") != "todo":
                continue
            note = (
                f"{marker}; supersedes earlier #256 classifications; "
                f"wave={row['wave']}; "
                f"instructions={row['instructions']}; "
                f"start={row.get('start_address', '')}; "
                f"worker_coverage={row['resolved']}/{row['symbols']}; "
                f"missing={json.dumps(row['missing'], separators=(',', ':'))}; "
                f"lexically_visible={json.dumps(row.get('lexically_visible', []), separators=(',', ':'))}; "
                f"translation_unit={Path(row['asm']).parent.as_posix()}; "
                "dependency_rule=same translation unit and earlier definition; "
                f"queued_dependencies={json.dumps(sorted(dependencies.get(row['id'], [])), separators=(',', ':'))}"
            )
            prior = record.get("notes", "").strip()
            if classification_is_current(prior, coverage_sha, waves_sha):
                satisfied += 1
            else:
                record["notes"] = note + (" || " + prior if prior else "")
                updated += 1
                satisfied += 1
        return records, {"updated": updated, "satisfied": satisfied}

    result = scheduler.Queue().transaction(update)
    print(f"queue classification evidence appended for {result['updated']}/"
          f"{len(by_id)} rows; {result['satisfied']} current")
    return 0 if result["satisfied"] == len(by_id) else 1


def self_test() -> int:
    fixtures = [
        ({"instructions": 8, "missing": [], "undeclared_data": []},
         "tiny-closed"),
        ({"instructions": 20, "missing": ["callee"],
          "undeclared_data": []}, "tiny-one-gap"),
        ({"instructions": 80, "missing": [], "undeclared_data": []},
         "small-closed"),
        ({"instructions": 96, "missing": ["callee"],
          "undeclared_data": []}, "small-one-gap"),
        ({"instructions": 7, "missing": [],
          "undeclared_data": ["D_us_80180000"]}, "data-blocked"),
        ({"instructions": 129, "missing": [], "undeclared_data": []},
         "general"),
    ]
    failed = [expected for row, expected in fixtures
              if mechanical_wave(row) != expected]
    if validate_instruction_rows([{"id": "missing"}]) != ["missing"]:
        failed.append("missing instruction count fails closed")
    if validate_instruction_rows([{"id": "zero", "instructions": 0}]) != ["zero"]:
        failed.append("zero instruction count fails closed")
    if validate_instruction_rows([{"id": "valid", "instructions": 1}]):
        failed.append("positive instruction count is accepted")
    if validate_start_rows([{"id": "missing-start", "instructions": 1}]) != [
            "missing-start"]:
        failed.append("missing start address fails closed")
    if validate_start_rows([{"id": "valid-start", "start_address": "0x10"}]):
        failed.append("valid start address is accepted")
    if not symbol_scan_error(2, ["a.s"], 0, ["a.s:jal A"], 1):
        failed.append("a failed asm find is rejected")
    if not symbol_scan_error(0, ["a.s"], 2, [], 1):
        failed.append("a failed symbol grep is rejected")
    if not symbol_scan_error(0, [], 1, [], 1):
        failed.append("an empty asm file set with live records is rejected")
    if symbol_scan_error(0, ["a.s"], 1, [], 1):
        failed.append("grep status 1 is accepted only as an honest no-match")
    if (classification_marker("same-coverage", "old-waves")
            == classification_marker("same-coverage", "new-waves")):
        failed.append("changed wave evidence bypasses annotation dedupe")
    current_marker = classification_marker("coverage", "waves")
    if not classification_is_current(
            "prior || " + current_marker, "coverage", "waves"):
        failed.append("an exact annotation rerun is satisfied idempotently")
    if classification_is_current(current_marker, "coverage", "other-waves"):
        failed.append("a stale wave hash cannot satisfy annotation idempotence")
    with tempfile.TemporaryDirectory() as td:
        coverage_fixture = Path(td) / "coverage.json"
        coverage_fixture.write_text("[]\n")
        wave_fixture = Path(td) / "wave.json"
        write_wave_plan(wave_fixture, [], coverage_fixture)
        wave_fixture_doc = json.loads(wave_fixture.read_text())
        if (wave_fixture_doc.get("coverage_sha256")
                != hashlib.sha256(coverage_fixture.read_bytes()).hexdigest()):
            failed.append("wave reports bind the exact coverage input hash")
        if wave_matches_coverage(wave_fixture_doc, "different-coverage"):
            failed.append("queue annotation refuses a mismatched wave report")
    lexical = ("static void Earlier(void) {}\n"
               "void Later(void);\n"
               "INCLUDE_ASM(\"x\", Target);\n"
               "void Later(void) {}\n")
    if lexically_visible_functions(
            lexical, "Target", ["Earlier", "Later"]) != ["Earlier"]:
        failed.append("only earlier same-file definitions are visible")
    if lexically_visible_functions(
            "INCLUDE_ASM(\"x\", Target);\n", "Target", ["HeaderFn"],
            "static void HeaderFn(void) {}\n") != ["HeaderFn"]:
        failed.append("definitions from prior local includes are visible")
    if not re.search(rf"\b{re.escape('InitializeEntity')}\b",
                     "void InitializeEntity(u16 arg0[]);"):
        failed.append("declaration word boundary")
    with tempfile.TemporaryDirectory() as td:
        def wave_row(record_id: str, function: str, asm: str, start: str,
                     implicit_calls: list[str]) -> dict:
            return {
                "id": record_id, "function": function, "overlay": "ST/TEST",
                "asm": asm, "start_address": start, "instructions": 8,
                "symbols": len(implicit_calls), "coverage": 1.0,
                "missing": [], "implicit_calls": implicit_calls,
                "undeclared_data": [],
            }

        plan_path = Path(td) / "waves.json"
        write_wave_plan(plan_path, [
            wave_row("earlier", "Earlier", "asm/us/st/test/nonmatchings/unit/Earlier.s",
                     "0x10", []),
            wave_row("consumer", "Consumer", "asm/us/st/test/nonmatchings/unit/Consumer.s",
                     "0x20", ["Earlier", "Later", "OtherUnit"]),
            wave_row("later", "Later", "asm/us/st/test/nonmatchings/unit/Later.s",
                     "0x30", []),
            wave_row("other", "OtherUnit", "asm/us/st/test/nonmatchings/other/OtherUnit.s",
                     "0x05", []),
        ])
        edges = json.loads(plan_path.read_text())["queue_dependencies"]
        if edges != [{"consumer": "consumer", "dependency": "earlier",
                      "symbol": "Earlier", "symbol_kind": "implicit-call"}]:
            failed.append("only earlier same-TU implicit callees become dependencies")
    if failed:
        print("wave classification failed: " + ", ".join(failed))
        return 1
    print("all checks passed")
    return 0


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
    ap.add_argument("--show-missing", action="store_true",
                    help="print unresolved data and other symbols for each row")
    # The declaration grep walks the whole tree and takes ~25s on a mounted
    # filesystem, which does not fit in one automated call alongside the rest.
    # Cache it so the scan can be driven in phases. Delete the cache after
    # renaming symbols, or it will report stale coverage.
    ap.add_argument("--decl-cache", default="",
                    help="load/save the declaration index here (JSON)")
    ap.add_argument("--build-cache-only", action="store_true",
                    help="build the declaration cache, then exit")
    ap.add_argument("--sym-cache", default="",
                    help="load/save explicitly trusted, nonempty raw asm symbol refs here")
    ap.add_argument("--write-priority", default="",
                    help="write claim-order hints for scheduler.cmd_next "
                         "(normally automation/priority.us.json)")
    ap.add_argument("--write-waves", default="",
                    help="write deterministic size/dependency work lanes")
    ap.add_argument("--from-json", default="",
                    help="regenerate priority/wave reports from an existing "
                         "coverage JSON without rescanning the tree")
    ap.add_argument("--annotate-queue", action="store_true",
                    help="append corrected evidence from --from-json in one transaction")
    ap.add_argument("--wave-json", default="",
                    help="dependency report used by --annotate-queue")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    if a.from_json:
        coverage_path = Path(a.from_json)
        rows = json.loads(coverage_path.read_text())
        invalid = validate_instruction_rows(rows)
        invalid_starts = validate_start_rows(rows)
        if invalid:
            print("refusing derived reports with missing/zero instruction "
                  f"counts: {', '.join(invalid[:8])}", file=sys.stderr)
            return 1
        if (a.write_waves or a.annotate_queue) and invalid_starts:
            print("refusing wave/queue derivation with missing start addresses: "
                  f"{', '.join(invalid_starts[:8])}", file=sys.stderr)
            return 1
        if a.write_waves:
            write_wave_plan(Path(a.write_waves), rows, coverage_path)
            print(f"wrote {a.write_waves} from {a.from_json}")
        if a.write_priority:
            Path(a.write_priority).write_text(
                json.dumps(priority_map(rows), indent=1) + "\n")
            print(f"wrote {a.write_priority} from {a.from_json}")
        if a.annotate_queue:
            if not a.wave_json:
                print("--annotate-queue needs --wave-json", file=sys.stderr)
                return 2
            return annotate_queue(rows, coverage_path, Path(a.wave_json))
        if not a.write_waves and not a.write_priority:
            print("--from-json needs a derived-output or annotation action")
            return 2
        return 0

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
    per_file_calls: dict[str, list[str]] = {}
    scache = Path(a.sym_cache) if a.sym_cache else None
    raw_lines: list[str] = []
    if scache and scache.exists():
        raw_lines = scache.read_text().splitlines()
        if recs and not raw_lines:
            print("refusing empty trusted --sym-cache with live records",
                  file=sys.stderr)
            return 1
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
            scan_error = symbol_scan_error(
                fp.returncode, files, gp.returncode, raw_lines, len(recs))
            if scan_error:
                detail = fp.stderr.strip() if fp.returncode else gp.stderr.strip()
                print(f"  {scan_error}: {detail}", file=sys.stderr)
                return 1
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
                if re.search(r"\bjal\s+", match):
                    per_file_calls.setdefault(path, [])
                    if sym not in per_file_calls[path]:
                        per_file_calls[path].append(sym)
    except (subprocess.SubprocessError, OSError) as e:
        print(f"  grep failed: {e}", file=sys.stderr)
        return 1
    print(f"  symbols extracted for {len(per_file)} asm files", file=sys.stderr)
    added = supplement_worker_declarations(index, per_file)
    print(f"  worker-resolvable declarations added: {added}", file=sys.stderr)

    # One process counts real instructions in every unmatched listing. This is
    # the durable size/complexity signal for wave planning. Reading hundreds of
    # files one by one is prohibitively slow on the mounted workspace, and file
    # byte size is polluted by jump-table and rodata text.
    instruction_counts: dict[str, int] = {}
    start_addresses: dict[str, int] = {}
    asm_files = sorted({str(path.relative_to(REPO))
                        for paths in build_asm_index(a.version).values()
                        for path in paths})
    if asm_files:
        try:
            ip = subprocess.run(
                ["grep", "-HcE",
                 r"^[[:space:]]*/\* [0-9A-Fa-f]+ [0-9A-Fa-f]+ "
                 r"[0-9A-Fa-f]{8} \*/[[:space:]]+[A-Za-z]",
                 *asm_files],
                cwd=str(REPO), capture_output=True, text=True, timeout=900)
            if ip.returncode not in (0, 1):
                print(f"  instruction count grep failed with {ip.returncode}: "
                      f"{ip.stderr.strip()}", file=sys.stderr)
                return 1
            for line in ip.stdout.splitlines():
                path, _, count = line.rpartition(":")
                if path and count.isdigit():
                    instruction_counts[path] = int(count)
            sp = subprocess.run(
                ["grep", "-H", "-m", "1", "-E",
                 r"^[[:space:]]*/\* [0-9A-Fa-f]+ [0-9A-Fa-f]+ "
                 r"[0-9A-Fa-f]{8} \*/[[:space:]]+[A-Za-z]",
                 *asm_files],
                cwd=str(REPO), capture_output=True, text=True, timeout=900)
            if sp.returncode not in (0, 1):
                print(f"  instruction address grep failed with {sp.returncode}: "
                      f"{sp.stderr.strip()}", file=sys.stderr)
                return 1
            address_rx = re.compile(r"/\*\s*([0-9A-Fa-f]+)\s")
            for line in sp.stdout.splitlines():
                path, _, body = line.partition(":")
                match = address_rx.search(body)
                if path and match:
                    start_addresses[path] = int(match.group(1), 16)
        except (subprocess.SubprocessError, OSError) as e:
            print(f"  instruction count failed: {e}", file=sys.stderr)
            return 1

    rows = []
    source_cache: dict[Path, str] = {}
    include_cache: dict[Path, str] = {}
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
            asm = find_asm(fn, a.version, r.get("overlay", ""))
            if not asm:
                continue
            rel = str(asm.relative_to(REPO))
            syms = list(per_file.get(rel, []))
        # D_* and jtbl_* .s files are DATA, not functions. 803 of the 1114 files
        # under asm/us/**/nonmatchings/ are data symbols; treating them as work
        # is what produced the bogus "1277 functions remaining" figure, and is
        # the same confusion that made `make function-finder` relocate 803
        # rodata files (MATCHING-LESSONS.md 8d).
        if fn.startswith(("D_", "jtbl_")):
            continue
        syms = [s for s in syms if s != fn and not s.startswith("jtbl_")]
        retained = data_declarations.lookup_declarations(
            syms, overlay=r.get("overlay", ""), version=a.version)
        source_path = source_for_asm(rel)
        source_text = ""
        if source_path and source_path.is_file():
            if source_path not in source_cache:
                source_cache[source_path] = source_path.read_text(
                    encoding="utf-8", errors="replace")
            source_text = source_cache[source_path]
        included = (included_text_before_target(
            source_path, source_text, fn, include_cache)
            if source_path and source_text else "")
        visible = lexically_visible_functions(source_text, fn, syms, included)
        implicit_calls = [s for s in syms
                          if s in per_file_calls.get(rel, [])
                          and s not in index and s not in retained
                          and s not in visible]
        found = [s for s in syms
                 if s in index or s in retained or s in visible
                 or s in implicit_calls]
        missing = [s for s in syms
                   if s not in index and s not in retained and s not in visible
                   and s not in implicit_calls]
        data_refs = [s for s in syms if s.startswith("D_")]
        count = instruction_counts.get(rel)
        start_address = start_addresses.get(rel)
        rows.append({
            "id": r["id"], "function": fn, "overlay": r.get("overlay", ""),
            "asm": rel,
            "symbols": len(syms), "resolved": len(found),
            "instructions": count,
            "start_address": (f"0x{start_address:X}"
                              if start_address is not None else ""),
            "coverage": round(len(found) / len(syms), 3) if syms else 1.0,
            "data_refs": data_refs,
            "retained_data": [retained[s] for s in data_refs if s in retained],
            "lexically_visible": visible,
            # C89 implicit calls are not guesses. worker_direct emits the exact
            # `extern int f();` behavior the real warning-suppressed build used,
            # so they are mechanically closed even without a repository prototype.
            "implicit_calls": implicit_calls,
            "undeclared_data": [
                d for d in data_refs if d not in index and d not in retained],
            # Preserve the complete dependency set in generated evidence.
            # Display callers may truncate; durable reports must not.
            "missing": missing,
        })
    invalid = validate_instruction_rows(rows)
    missing_starts = validate_start_rows(rows)
    if invalid or missing_starts:
        if invalid:
            print("refusing report with missing/zero instruction counts: "
                  f"{', '.join(invalid[:8])}", file=sys.stderr)
        if missing_starts:
            print("refusing report with missing start addresses: "
                  f"{', '.join(missing_starts[:8])}", file=sys.stderr)
        return 1
    for row in rows:
        row["wave"] = mechanical_wave(row)

    # Rank:
    #   1. functions with NO undeclared data references first. A raw D_us_
    #      address that nothing names is a structural failure (section 1a) that
    #      neither a better model nor the permuter can fix, so those go last
    #      regardless of how good the rest of their coverage looks.
    #   2. then by RESOLVED COUNT, descending.
    #   3. then coverage, then fewest symbols as tie-breakers.
    #
    # Point 2 is deliberate and was wrong in the first version, which sorted by
    # coverage ratio and then by fewest symbols. A function referencing no
    # external symbols scores 1.0 coverage (100% of nothing) and sorted to the
    # very top, so the 2026-07-21 run handed the fleet four 0/0 functions and
    # the prompt-declaration fix was a no-op on every one of them: the logs show
    # `decls: 0` for nine of eleven functions attempted.
    #
    # The whole point of the ordering is to spend the fix where it applies, and
    # that scales with how many declarations actually get injected. Rank by the
    # absolute count, not the ratio.
    rows.sort(key=lambda x: (len(x["undeclared_data"]),
                             -x["resolved"], -x["coverage"],
                             x["instructions"], x["symbols"]))

    print(f"\n{'cov':>5}  {'res/tot':>8}  {'insn':>5}  {'overlay':<12} function")
    print("-" * 72)
    for row in rows[:a.limit]:
        print(f"{row['coverage']:>5.0%}  "
              f"{row['resolved']:>3}/{row['symbols']:<4}  "
              f"{row['instructions']:>5}  "
              f"{row['overlay']:<12} {row['function']}")
        if a.show_missing:
            if row["retained_data"]:
                print("       retained data: "
                      + " | ".join(row["retained_data"]))
            if row["undeclared_data"]:
                print("       undeclared data: "
                      + ", ".join(row["undeclared_data"]))
            other = [sym for sym in row["missing"]
                     if sym not in row["undeclared_data"]]
            if other:
                print("       other unresolved: " + ", ".join(other))

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

    if a.write_waves:
        out = Path(a.write_waves)
        write_wave_plan(out, rows, Path(a.json) if a.json else None)
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["wave"]] = counts.get(row["wave"], 0) + 1
        print(f"  wrote {out}: " + ", ".join(
            f"{name}={count}" for name, count in sorted(counts.items())))

    if a.write_priority:
        # Consumed by scheduler.cmd_next. Only the two fields it needs: keeping
        # this minimal means the ranking heuristic can change here without
        # touching the scheduler.
        prio = priority_map(rows)
        out = Path(a.write_priority)
        out.write_text(json.dumps(prio, indent=1))
        nb = sum(1 for v in prio.values() if v["blocked"])
        print(f"  wrote {out}: {len(prio)} functions, "
              f"{nb} blocked, {len(prio) - nb} workable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
