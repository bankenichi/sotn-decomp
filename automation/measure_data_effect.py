"""Read-only remeasurement of data-addressing slices over the g_api jalr pool.

Walks assembly nonmatchings for files pairing jalr with g_api hi/lo halves,
captures each file's real translation-unit plus sibling context, projects
renderer declarations, and attempts a default-limits deterministic draft.
Prints a JSON tally to stdout.

Writes nothing: no queue, lane, build, source, or landing side effects.
End-to-end matching stays deferred by the owner; this is implementation
evidence only.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_GENERIC_HI = re.compile(r"%hi\s*\(\s*([A-Za-z_][\w$.]*)(?:\s*\+\s*(?:0[xX][0-9a-fA-F]+|[0-9]+))?\s*\)")
_GENERIC_LO = re.compile(r"%lo\s*\(\s*([A-Za-z_][\w$.]*)(?:\s*\+\s*(?:0[xX][0-9a-fA-F]+|[0-9]+))?\s*\)")
_JALR = re.compile(r"(?m)^\s*jalr\b")


def _known_names(text: str) -> set[str]:
    """Every symbol named by a hi or lo relocation half in the text."""
    return set(_GENERIC_HI.findall(text)) | set(_GENERIC_LO.findall(text))


def classify_file(text: str) -> dict:
    """Sort a file's relocation names into harness classes.

    Returns a mapping with sorted lists for g_api, d_star, g_star, linker,
    jtbl, and other names. Pure helper; used for refusal attribution.
    """
    from automation.search_source_context import (
        _api_member_names,
        _data_member_names,
        _global_member_names,
        _linker_member_names,
    )
    observed = {
        "g_api": set(_api_member_names(text)),
        "d_star": set(_data_member_names(text)),
        "g_star": set(_global_member_names(text)),
        "linker": set(_linker_member_names(text)),
        "jtbl": {name for name in _known_names(text) if name.startswith("jtbl_")},
    }
    covered = set().union(*observed.values())
    observed["other"] = sorted(_known_names(text) - covered)
    return {key: sorted(value) for key, value in observed.items()}


def is_pool_member(text: str) -> bool:
    """Whether the file belongs to the g_api jalr remeasurement pool."""
    from automation.search_source_context import _api_member_names
    if not isinstance(text, str):
        return False
    return bool(_JALR.search(text)) and bool(_api_member_names(text))


def derive_record(asm_relative: str) -> tuple[str, str] | None:
    """Derive (record_id, overlay) from a repo-relative assembly path.

    Returns None when the path does not encode a US overlay and symbol.
    Pure helper; the render-time capture enforces the same binding.
    """
    try:
        parts = Path(asm_relative).as_posix().split("/")
        if len(parts) < 5 or parts[0] != "asm" or parts[1] != "us":
            return None
        area = parts[2]
        if area in ("st", "boss"):
            overlay = (area + "/" + parts[3]).upper()
        else:
            overlay = area.upper()
        symbol = Path(parts[-1]).stem
        if not symbol or not re.fullmatch(r"[A-Za-z_]\w*", symbol):
            return None
        return ("us:" + overlay + ":" + symbol, overlay)
    except (ValueError, IndexError):
        return None


def measure_pool(repo: Path, limit: int | None = None) -> dict:
    """Walk nonmatchings assembly and tally the g_api jalr pool.

    For each pool file, captures the real owning plus sibling context,
    projects renderer declarations, and attempts one default-limits draft.
    Read-only; every failure mode is tallied, never raised.
    """
    from automation.compiler_corpus import DEFAULT_CONFIG_PATH, pipeline_identity
    from automation.search_source_context import capture_target_context, renderer_declarations
    from automation.search_target_renderer import deterministic_local_draft
    identity = pipeline_identity().identity
    config_path = DEFAULT_CONFIG_PATH
    cache: dict = {}
    files = sorted((repo / "asm" / "us").rglob("*.s"))
    files = [path for path in files if "nonmatchings" in path.parts]
    pool = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if is_pool_member(text):
            pool.append(path)
    if limit is not None:
        pool = pool[:limit]
    tally: dict = {
        "pool": len(pool),
        "rendered": [],
        "unrendered": 0,
        "missing_tu": 0,
        "undeclared": 0,
        "errors": {},
        "reloc_histogram": {"g_api": 0, "d_star": 0, "g_star": 0, "linker": 0, "jtbl": 0, "other": 0},
    }

    def _count(prefix: str, exc: Exception) -> None:
        tally["errors"].setdefault(prefix + type(exc).__name__, 0)
        tally["errors"][prefix + type(exc).__name__] += 1

    for path in pool:
        rel = path.relative_to(repo).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            _count("read:", exc)
            tally["unrendered"] += 1
            continue
        for key in tally["reloc_histogram"]:
            if classify_file(text).get(key):
                tally["reloc_histogram"][key] += 1
        derived = derive_record(rel)
        if derived is None:
            tally["unrendered"] += 1
            continue
        record_id, _overlay = derived
        try:
            declarations, blobs = capture_target_context(
                repo, record_id, rel, identity, config_path, sibling_cache=cache)
        except Exception as exc:  # noqa: BLE001 - tally refusal classes, never raise
            _count("capture:", exc)
            tally["unrendered"] += 1
            continue
        evidence = dict(declarations).get("context_evidence", {})
        if evidence.get("status") == "source_missing":
            tally["missing_tu"] += 1
        own_context = cache.get(evidence.get("path", ""), (None, None))[1]
        if own_context is None and evidence.get("status") != "source_missing":
            tally["errors"].setdefault("context_cache_miss", 0)
            tally["errors"]["context_cache_miss"] += 1
            tally["unrendered"] += 1
            continue
        try:
            sibling_contexts = tuple(blob for _, _, blob in blobs)
            facts = renderer_declarations(
                dict(declarations), (repo / rel).read_bytes(), own_context, sibling_contexts)
            draft = deterministic_local_draft(text, symbol=record_id.split(":")[2], declarations=facts)
        except Exception as exc:  # noqa: BLE001 - tally refusal classes, never raise
            _count("render:", exc)
            tally["unrendered"] += 1
            continue
        if draft is None:
            tally["unrendered"] += 1
            if evidence.get("status") != "declared":
                tally["undeclared"] += 1
        else:
            tally["rendered"].append(record_id)
    tally["rendered"] = sorted(tally["rendered"])
    return tally


def main(argv=None) -> int:
    """Entry point: print the JSON tally for the pool to stdout."""
    parser = argparse.ArgumentParser(description="Remeasure data slices over the g_api jalr pool.")
    parser.add_argument("--limit", type=int, default=None, help="Measure only the first N pool files.")
    parser.add_argument("--root", default=None, help="Repository root override.")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 0:
        parser.error("--limit must be non-negative")
    repo = Path(args.root) if args.root else ROOT
    print(json.dumps(measure_pool(repo, args.limit), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
