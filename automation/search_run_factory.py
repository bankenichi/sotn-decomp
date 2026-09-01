"""Bounded production creator for instrumented search runs.

The planner deliberately remains read-only.  This module is the narrow write
boundary that turns an explicit planner selection into the canonical run tree
used by :mod:`search_cli` and the instrumented supervisor.  It accepts logical
values only: the queue, target paths, compiler and tool identities are resolved
from repository-owned evidence.

The canonical anchor for a multi-record subset is the lexicographically first
function ID in the normalized subset.  The anchor is only a location for the
manifest; the subset identity and every target binding still cover every queue
record.  Keeping the rule here makes the resolver's one-function search tree
deterministic without making a function name carry subset authority.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import tempfile
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path, PureWindowsPath
from typing import Any, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover - the production queue runs in WSL
    fcntl = None  # type: ignore[assignment]

try:  # package imports
    from .search_archive import ArtifactRef, ContentAddressedArchive
    from .search_supervisor import INSTRUMENTED_MODE, MODE_TOOL_KEY, mode_identity
    from .search_types import (
        Budget,
        LANES,
        MAX_CHILD_TASKS_PER_BASE,
        MAX_COORDINATOR_TASKS,
        TIER_ORDER,
        RunManifest,
        SearchValidationError,
        canonical_json,
        canonical_subset_identity,
        canonical_subset_payload,
        hash_bytes,
        hash_canonical,
        validate_run_id,
        validate_hash,
    )
except ImportError:  # direct invocation from automation/
    from automation.search_archive import ArtifactRef, ContentAddressedArchive  # type: ignore
    from automation.search_supervisor import (  # type: ignore
        INSTRUMENTED_MODE,
        MODE_TOOL_KEY,
        mode_identity,
    )
    from automation.search_types import (  # type: ignore
        Budget,
        LANES,
        MAX_CHILD_TASKS_PER_BASE,
        MAX_COORDINATOR_TASKS,
        TIER_ORDER,
        RunManifest,
        SearchValidationError,
        canonical_json,
        canonical_subset_identity,
        canonical_subset_payload,
        hash_bytes,
        hash_canonical,
        validate_run_id,
        validate_hash,
    )


_FUNCTION_RX = re.compile(r"^[A-Za-z0-9_]{1,64}$")
_MANIFEST_FILENAME = "manifest.json"
_SCHEMA_PATH_PARTS = ("automation", "search-ledger.schema.json")
_CONFIG_PATH_PARTS = (
    "tools", "sotn_permuter", "permuter_settings.us.toml"
)
_TARGET_ASM_FIELDS = (
    "target_assembly", "target_asm", "assembly_path", "asm_path", "assembly", "asm",
)
_TARGET_OBJECT_FIELDS = (
    "target_object", "target_object_path", "object_path", "object", "target_o",
)
_MAX_SOURCE_FILES = 200_000
# Compatibility aliases retained for focused callers.  Admission uses the
# shared limits imported from search_types below.
_MAX_COORDINATOR_TASKS = MAX_COORDINATOR_TASKS
_MAX_CHILD_TASKS_PER_BASE = MAX_CHILD_TASKS_PER_BASE
# Base lane tasks are admitted only when their bounded candidate allowance
# still fits the one global coordinator budget.
_MAX_TASKS = MAX_COORDINATOR_TASKS // (1 + MAX_CHILD_TASKS_PER_BASE)
_DEFAULT_LANE_ATTEMPTS = 1
_DEFAULT_EPOCH_SIZE = 64
_DEFAULT_FRONTIER_CAP = 64
_FACTORY_PROTOCOL = "sotn-search-run-factory-v1"
_FACTORY_TOOL_KEY = "search_run_factory"
_FACTORY_MARKER_KEY = "search_run_factory_marker"
_FACTORY_MARKER_PROTOCOL = "sotn-search-run-factory-created-v1"
_FACTORY_MODULE = ("automation/search_run_factory.py", _FACTORY_TOOL_KEY)
_INDEXED_LANES = frozenset({"multi_donor", "cfg_dataflow"})
_INDEXED_RUNTIME_TOOL_KEY = "indexed_runtime"
_TARGET_RENDERER_SOURCE_TOOL_KEY = "target_renderer_source"
_CORE_MODULES = (
    ("automation/search_lanes.py", "search_lanes"),
    ("automation/search_supervisor.py", "search_supervisor"),
    ("automation/search_coordinator.py", "search_coordinator"),
    ("automation/search_types.py", "search_types"),
    ("automation/search_archive.py", "search_archive"),
    ("automation/search_recovery.py", "search_recovery"),
)
_LANE_MODULES = {
    "upstream_current": ("automation/upstream_harvest.py",),
    "upstream_pinned": ("automation/upstream_harvest.py",),
    "upstream_open_pr": ("automation/upstream_harvest.py",),
    "shared_header": ("automation/shim_sweep.py",),
    "transplant": ("automation/asm_twin_finder.py", "automation/transplant.py"),
    "multi_donor": (
        "automation/search_provider_lanes.py",
        "automation/search_indexed_lane.py",
        "automation/search_donor_query.py",
        "automation/search_target_renderer.py",
    ),
    "cfg_dataflow": (
        "automation/search_provider_lanes.py",
        "automation/search_indexed_lane.py",
        "automation/search_donor_query.py",
        "automation/search_target_renderer.py",
    ),
}


class SearchRunFactoryError(RuntimeError):
    """Base class for typed run-creation refusals."""


class InputRefusal(SearchRunFactoryError):
    """The requested name, IDs, lanes or queue state is not admissible."""


class EvidenceRefusal(SearchRunFactoryError):
    """A required repository-owned identity could not be measured exactly."""


class RunNameCollision(SearchRunFactoryError):
    """The requested run name already names different immutable evidence."""


class PartialRunRefusal(SearchRunFactoryError):
    """An existing run root is incomplete or corrupt and cannot be repaired."""


QueueReader = Callable[[], Sequence[Mapping[str, Any]]]
IdentityResolver = Callable[[Path], Any]
Clock = Callable[[], str]
FactoryFaultHook = Callable[[str], None]


@contextmanager
def _creation_lock(repo: Path):
    """Serialize creators for one repository before name allocation.

    The resolver treats a run name as global across all function anchors.  A
    lock only around the selected anchor would let two concurrent creators put
    the same name under different anchors and make the resolver ambiguous.  A
    stable lock in the host temporary directory keeps this coordination state
    out of the repository and is shared by all callers for this repository.
    """

    lock_key = hashlib.sha256(str(repo).encode("utf-8")).hexdigest()
    lock_path = Path(tempfile.gettempdir()) / f"sotn-search-factory-{lock_key}.lock"
    try:
        if lock_path.is_symlink() or (lock_path.exists() and not lock_path.is_file()):
            raise PartialRunRefusal("search-run creation lock is not a regular file")
        with lock_path.open("a+", encoding="utf-8") as lock:
            if fcntl is not None:
                fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(lock, fcntl.LOCK_UN)
    except PartialRunRefusal:
        raise
    except OSError as exc:
        raise SearchRunFactoryError("search-run creation lock is unavailable") from exc


def _component(value: Any, label: str) -> str:
    try:
        return validate_run_id(value, label)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise InputRefusal(
            f"{label} must be one safe component with no separators, traversal, globs or shell text"
        ) from exc


def _sequence(values: Any, label: str) -> tuple[Any, ...]:
    if values is None or isinstance(values, (str, bytes, bytearray)):
        raise InputRefusal(f"{label} must be an explicit sequence")
    try:
        result = tuple(values)
    except TypeError as exc:
        raise InputRefusal(f"{label} must be an explicit sequence") from exc
    return result


def _queue_id(value: Any) -> str:
    """Call the one canonical queue-ID validator owned by the connector."""

    try:
        from .mcp.commands_client import _queue_id as validator
    except ImportError:  # direct invocation from automation/
        from automation.mcp.commands_client import _queue_id as validator  # type: ignore
    try:
        return validator(value)
    except (TypeError, ValueError) as exc:
        raise InputRefusal("record_ids contains an invalid canonical queue id") from exc


def _normalize_inputs(
    name: Any,
    record_ids: Any,
    lanes: Any,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    run_id = _component(name, "name/run_id")
    raw_ids = _sequence(record_ids, "record_ids")
    if not raw_ids:
        raise InputRefusal("record_ids must not be empty")
    normalized_ids = tuple(sorted(_queue_id(value) for value in raw_ids))
    if len(set(normalized_ids)) != len(normalized_ids):
        raise InputRefusal("record_ids must not contain duplicates")

    raw_lanes = _sequence(lanes, "lanes")
    if not raw_lanes:
        raise InputRefusal("lanes must not be empty")
    if any(not isinstance(lane, str) for lane in raw_lanes):
        raise InputRefusal("lanes must contain strings")
    if len(set(raw_lanes)) != len(raw_lanes):
        raise InputRefusal("lanes must not contain duplicates")
    unknown = sorted(set(raw_lanes).difference(LANES))
    if unknown:
        raise InputRefusal(f"unknown lane: {unknown[0]}")
    selected = tuple(lane for lane in LANES if lane in raw_lanes)
    return run_id, normalized_ids, selected


def _normalize_indexed_runtime_id(
    runtime_id: Any,
    selected_lanes: Sequence[str],
) -> Optional[str]:
    indexed = any(lane in _INDEXED_LANES for lane in selected_lanes)
    if runtime_id is None:
        if indexed:
            raise InputRefusal(
                "indexed lanes require one explicit indexed runtime identity"
            )
        return None
    if not indexed:
        raise InputRefusal(
            "an indexed runtime is irrelevant when no indexed lane is selected"
        )
    try:
        return validate_hash(runtime_id, "indexed runtime identity")
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise InputRefusal("indexed runtime identity is invalid") from exc


def _load_indexed_runtime_generation(runtime_id: str, repo: Path) -> Any:
    """Load and verify one exact published runtime without accepting a path."""

    try:
        from .search_indexed_runtime import (
            IndexedRuntimeGeneration,
            IndexedRuntimeError,
            load_indexed_runtime,
            verify_indexed_runtime,
        )
    except ImportError:
        try:  # direct invocation from automation/
            from search_indexed_runtime import (  # type: ignore
                IndexedRuntimeGeneration,
                IndexedRuntimeError,
                load_indexed_runtime,
                verify_indexed_runtime,
            )
        except ImportError as exc:
            raise EvidenceRefusal(
                "indexed runtime implementation is unavailable"
            ) from exc
    try:
        generation = load_indexed_runtime(runtime_id, repo=repo)
        if type(generation) is not IndexedRuntimeGeneration:
            raise EvidenceRefusal("indexed runtime loader returned a noncanonical value")
        verify_indexed_runtime(generation, repo=repo)
    except EvidenceRefusal:
        raise
    except (IndexedRuntimeError, OSError, TypeError, ValueError) as exc:
        raise EvidenceRefusal(
            "indexed runtime is missing, corrupt, or outside the canonical archive"
        ) from exc
    if generation.runtime_id != runtime_id:
        raise EvidenceRefusal("indexed runtime identity differs from the request")
    return generation


def canonical_anchor_function(function_ids: Iterable[str]) -> str:
    """Return the stable manifest location for a normalized function subset."""

    values = tuple(sorted(set(function_ids)))
    if not values:
        raise InputRefusal("at least one function is required for a run anchor")
    for value in values:
        if _FUNCTION_RX.fullmatch(value) is None:
            raise EvidenceRefusal("queue function is not a safe canonical component")
    return values[0]


def _repo_root(repo: Optional[Path | str]) -> Path:
    if repo is None:
        configured = os.environ.get("SOTN_REPO")
        repo = configured if configured else Path(__file__).resolve().parents[1]
    try:
        lexical = Path(repo)
        if lexical.is_symlink():
            raise EvidenceRefusal("repository root must not be a symlink")
        value = lexical.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise EvidenceRefusal("repository root cannot be resolved") from exc
    if not value.is_dir() or value.is_symlink():
        raise EvidenceRefusal("repository root must be a real directory")
    return value


def _assert_no_symlink_components(path: Path, *, root: Optional[Path] = None) -> None:
    """Reject symlinked path components before any factory write."""

    resolved_root = (root or Path(path.anchor or os.sep)).resolve()
    try:
        lexical = Path(path)
        parts = lexical.parts
        current = Path(lexical.anchor) if lexical.anchor else Path()
        start = 1 if lexical.anchor else 0
        for part in parts[start:]:
            current = current / part
            if current.is_symlink():
                raise EvidenceRefusal("symlink path component is refused")
        resolved = lexical.resolve(strict=False)
        resolved.relative_to(resolved_root)
    except EvidenceRefusal:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise EvidenceRefusal("path could not be inspected") from exc


def _safe_repo_file(repo: Path, raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise EvidenceRefusal(f"{label} is not a path")
    # Queue evidence is serialized with POSIX repository-relative paths.  On
    # the production WSL host a backslash is a filename character, not a
    # separator, so accepting it would make a Windows traversal such as
    # ``asm\\us\\..\\outside`` look harmless while allowing a differently
    # named file to be selected.  Keep the native Windows case usable for
    # local focused tests, but apply the matching Windows lexical checks there.
    lexical = Path(raw)
    if os.name == "nt":
        windows_path = PureWindowsPath(raw)
        # Absolute paths are accepted only so the factory can remeasure its
        # own resolved configuration path.  Containment below still rejects a
        # caller-supplied absolute path outside this repository.
        if windows_path.drive and not lexical.is_absolute():
            raise EvidenceRefusal(f"{label} contains a drive-qualified path")
        raw_parts = windows_path.parts
    else:
        if "\\" in raw or re.match(r"^[A-Za-z]:", raw):
            raise EvidenceRefusal(f"{label} contains an unsupported path separator")
        raw_parts = lexical.parts
    if any(part in ("", ".", "..") for part in raw_parts) or any(
        marker in raw for marker in ("*", "?", "[")
    ) or "\x00" in raw:
        raise EvidenceRefusal(f"{label} contains unsafe path text")
    candidate = lexical
    if not candidate.is_absolute():
        candidate = repo / candidate
    _assert_no_symlink_components(candidate, root=repo)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(repo)
    except (OSError, RuntimeError, ValueError) as exc:
        raise EvidenceRefusal(f"{label} is outside the repository") from exc
    if resolved.is_symlink() or not resolved.is_file():
        raise EvidenceRefusal(f"{label} must be a regular file")
    return resolved


def _path_under_any(path: Path, roots: Sequence[Path], *, repo: Path, label: str) -> bool:
    """Return whether an evidence path is below one of its typed roots."""

    for root in roots:
        if root.exists() or root.is_symlink():
            _assert_no_symlink_components(root, root=repo)
        try:
            path.resolve(strict=True).relative_to(root.resolve(strict=False))
            return True
        except (OSError, RuntimeError, ValueError):
            continue
    raise EvidenceRefusal(f"{label} is outside the record's canonical tree")


def _relative(repo: Path, path: Path) -> str:
    try:
        return path.resolve(strict=True).relative_to(repo).as_posix()
    except (OSError, RuntimeError, ValueError) as exc:
        raise EvidenceRefusal("evidence path escaped the repository") from exc


def _read_evidence_bytes(path: Path, label: str) -> bytes:
    """Read one already-vetted regular file as typed evidence."""

    try:
        return path.read_bytes()
    except OSError as exc:
        raise EvidenceRefusal(f"{label} could not be read") from exc


def _dedupe_candidate_paths(
    paths: Iterable[Path], repo: Path, label: str
) -> list[Path]:
    """Collapse repeated filesystem spellings without hiding distinct files."""
    ordered = sorted(paths, key=lambda path: _relative(repo, path))
    unique: list[Path] = []
    seen_relative: set[str] = set()
    seen_stat: set[tuple[int, int]] = set()
    for path in ordered:
        try:
            canonical = path.resolve(strict=True)
            relative = _relative(repo, canonical)
            normalized_relative = os.path.normcase(relative)
            stat = canonical.stat()
        except (OSError, RuntimeError, ValueError) as exc:
            raise EvidenceRefusal(
                f"{label} could not be canonically identified"
            ) from exc
        stat_key = (
            (int(stat.st_dev), int(stat.st_ino))
            if int(stat.st_ino) != 0
            else None
        )
        duplicate = (
            normalized_relative in seen_relative
            or (stat_key is not None and stat_key in seen_stat)
        )
        if not duplicate:
            for prior in unique:
                try:
                    if canonical.samefile(prior):
                        duplicate = True
                        break
                except OSError:
                    # The path was already vetted.  If samefile is unavailable,
                    # retain the candidate and let normal ambiguity checks apply.
                    continue
        if duplicate:
            continue
        seen_relative.add(normalized_relative)
        if stat_key is not None:
            seen_stat.add(stat_key)
        unique.append(canonical)
    return unique


def _canonical_mapping(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if any(not isinstance(key, str) for key in value):
        raise EvidenceRefusal(f"{label} keys must be strings")
    try:
        result = json.loads(canonical_json(value))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise EvidenceRefusal(f"{label} is not canonical JSON") from exc
    if not isinstance(result, dict):
        raise EvidenceRefusal(f"{label} must be an object")
    return result


def _read_queue_from_scheduler() -> Sequence[Mapping[str, Any]]:
    """Read the scheduler-owned queue under its stable shared lock.

    ``Queue.transaction`` always calls ``_write`` even for an unchanged
    callback, so it is intentionally not used here.  Constructing ``Queue``
    would also touch a missing queue file.  The scheduler class and its path
    are authoritative, but this read-only boundary borrows an object without
    invoking its writer-oriented initializer.
    """

    # Avoid importing scheduler until the configured live queue already exists:
    # scheduler's module import may migrate a legacy snapshot, which would be
    # an unintended queue write on this creation boundary.
    configured_path = Path(
        os.environ.get("SOTN_QUEUE", os.path.expanduser("~/sotn-work/queue.jsonl"))
    )
    try:
        # An empty configured file is not imported either.  scheduler imports
        # perform legacy migration when the queue is empty, which would turn a
        # read-only evidence capture into an implicit queue write.
        if (
            configured_path.is_symlink()
            or not configured_path.is_file()
            or configured_path.stat().st_size == 0
        ):
            raise EvidenceRefusal("scheduler queue does not exist or is empty")
    except OSError as exc:
        raise EvidenceRefusal("scheduler queue cannot be inspected") from exc
    try:
        # Borrow the stable queue lock before importing scheduler.  Its module
        # import may migrate an empty legacy queue; holding the writer's shared
        # lock closes the race with a normal scheduler transaction between the
        # preflight stat above and that import, without invoking Queue.__init__.
        lock_path = configured_path.with_suffix(".jsonl.lock")
        if lock_path.is_symlink():
            raise EvidenceRefusal("scheduler queue lock path is a symlink")
        with lock_path.open("a+", encoding="utf-8") as lock:
            if fcntl is not None:
                fcntl.flock(lock, fcntl.LOCK_SH)
            try:
                from . import scheduler
            except ImportError:
                from automation import scheduler  # type: ignore
            queue_path = Path(scheduler.QUEUE)
            if queue_path.resolve() != configured_path.resolve() or not queue_path.is_file():
                raise EvidenceRefusal("scheduler queue path changed during creation")
            try:
                queue = object.__new__(scheduler.Queue)
                queue.path = queue_path
                queue.lock_path = lock_path
                records = queue._read()
            finally:
                if fcntl is not None:
                    fcntl.flock(lock, fcntl.LOCK_UN)
    except SearchRunFactoryError:
        raise
    except (ImportError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise EvidenceRefusal("scheduler queue evidence could not be read") from exc
    if not isinstance(records, list):
        raise EvidenceRefusal("scheduler queue evidence is not a list")
    return records


def _status_bound_records(
    record_ids: tuple[str, ...],
    reader: QueueReader,
) -> tuple[dict[str, Any], ...]:
    try:
        records = reader()
    except SearchRunFactoryError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise EvidenceRefusal("scheduler queue evidence could not be read") from exc
    if isinstance(records, (str, bytes)) or not isinstance(records, Sequence):
        raise EvidenceRefusal("scheduler queue evidence must be a sequence")
    wanted = set(record_ids)
    found: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise EvidenceRefusal("scheduler queue contains a non-object record")
        canonical = _canonical_mapping(record, "queue record")
        raw_id = canonical.get("id")
        if not isinstance(raw_id, str):
            continue
        if raw_id not in wanted:
            continue
        try:
            canonical_id = _queue_id(raw_id)
        except InputRefusal:
            raise EvidenceRefusal("requested queue evidence has an invalid record id")
        if canonical_id != raw_id:
            raise EvidenceRefusal("requested queue evidence changed its record id")
        if raw_id in found:
            raise EvidenceRefusal(f"scheduler queue contains duplicate record {raw_id}")
        found[raw_id] = canonical

    missing = tuple(record_id for record_id in record_ids if record_id not in found)
    if missing:
        raise InputRefusal("requested queue record is missing: " + missing[0])
    result = []
    for record_id in record_ids:
        record = found[record_id]
        if record.get("status") != "todo":
            raise InputRefusal(
                f"requested queue record {record_id} has status {record.get('status')!r}, expected 'todo'"
            )
        try:
            build, overlay, function = record_id.split(":", 2)
        except ValueError as exc:
            raise EvidenceRefusal("queue id cannot be decomposed") from exc
        if (
            record.get("build") != build
            or record.get("overlay") != overlay
            or record.get("function") != function
        ):
            raise EvidenceRefusal(
                f"queue record {record_id} does not bind its canonical id fields"
            )
        if not isinstance(function, str) or _FUNCTION_RX.fullmatch(function) is None:
            raise EvidenceRefusal("queue function is not a safe component")
        result.append(record)
    return tuple(result)


def _walk_regular_files(root: Path, repo: Path, label: str) -> list[Path]:
    _assert_no_symlink_components(root, root=repo)
    if not root.is_dir() or root.is_symlink():
        raise EvidenceRefusal(f"{label} root is not a real directory")
    result: list[Path] = []
    try:
        for current, directories, files in os.walk(root, followlinks=False):
            current_path = Path(current)
            for directory in directories:
                candidate = current_path / directory
                if candidate.is_symlink():
                    raise EvidenceRefusal(f"{label} contains a symlink")
            for filename in files:
                candidate = current_path / filename
                if candidate.is_symlink() or not candidate.is_file():
                    raise EvidenceRefusal(f"{label} contains a non-regular file")
                result.append(candidate.resolve(strict=True))
                if len(result) > _MAX_SOURCE_FILES:
                    raise EvidenceRefusal(f"{label} exceeds the bounded file count")
    except SearchRunFactoryError:
        raise
    except OSError as exc:
        raise EvidenceRefusal(f"{label} could not be inspected") from exc
    return sorted(result, key=lambda path: _relative(repo, path))


def _source_identity(repo: Path) -> tuple[str, dict[str, Any]]:
    roots = []
    for name in ("src", "include"):
        root = repo / name
        if not root.exists() or root.is_symlink() or not root.is_dir():
            raise EvidenceRefusal(f"repository source root is unavailable: {name}")
        roots.extend(_walk_regular_files(root, repo, f"repository source {name}"))
    files = []
    for path in roots:
        data = _read_evidence_bytes(path, "repository source file")
        files.append({
            "path": _relative(repo, path),
            "content_hash": hash_bytes(data),
            "byte_size": len(data),
        })
    payload = {
        "artifact_type": "sotn-search-source-evidence",
        "files": files,
        "protocol": "sotn-search-source-v1",
        "schema_version": "1.0.0",
    }
    return hash_canonical(payload), payload


def _explicit_path(record: Mapping[str, Any], fields: Iterable[str]) -> list[str]:
    result = []
    for field in fields:
        value = record.get(field)
        if value is not None:
            if not isinstance(value, str) or not value:
                raise EvidenceRefusal(f"queue record field {field} is not a path")
            result.append(value)
    return result


def _note_paths(record: Mapping[str, Any], prefix: str) -> list[str]:
    notes = record.get("notes")
    if not isinstance(notes, str):
        return []
    paths = []
    for token in notes.split():
        if token.startswith(prefix + "="):
            value = token[len(prefix) + 1:]
            if value:
                paths.append(value.rstrip(",.;"))
    return paths


def _find_target_files(
    repo: Path,
    record: Mapping[str, Any],
    record_id: str,
) -> tuple[Path, Path]:
    build, overlay, function = record_id.split(":", 2)
    # The queue's target hints are evidence, not authority to select an
    # arbitrary in-repository file.  Bind both explicit hints and discovered
    # files to the build/overlay trees implied by the canonical record ID.
    overlay_names = (overlay, overlay.lower())
    asm_roots = []
    asm_base = repo / "asm" / build
    for overlay_name in overlay_names:
        candidate = asm_base / Path(*overlay_name.split("/")) / "nonmatchings"
        if candidate not in asm_roots:
            asm_roots.append(candidate)
    assembly_candidates: list[Path] = []
    for raw in _explicit_path(record, _TARGET_ASM_FIELDS) + _note_paths(record, "asm"):
        assembly = _safe_repo_file(repo, raw, "target assembly")
        _path_under_any(assembly, asm_roots, repo=repo, label="target assembly")
        assembly_candidates.append(assembly)
    for root in asm_roots:
        if not root.exists():
            continue
        for candidate in _walk_regular_files(root, repo, "target assembly tree"):
            if candidate.name == function + ".s":
                assembly_candidates.append(candidate)
    unique_assembly = _dedupe_candidate_paths(
        assembly_candidates, repo, "target assembly"
    )
    if len(unique_assembly) != 1:
        if not unique_assembly:
            raise EvidenceRefusal(f"target assembly is missing for {record_id}")
        raise EvidenceRefusal(f"target assembly is ambiguous for {record_id}")
    assembly = unique_assembly[0]
    if assembly.name != function + ".s":
        raise EvidenceRefusal(f"target assembly does not name {function}")

    object_candidates: list[Path] = []
    object_roots = []
    build_base = repo / "build" / build / "src"
    for overlay_name in overlay_names:
        candidate = build_base / Path(*overlay_name.split("/"))
        if candidate not in object_roots:
            object_roots.append(candidate)
    for raw in _explicit_path(record, _TARGET_OBJECT_FIELDS) + _note_paths(record, "object"):
        target_object = _safe_repo_file(repo, raw, "target object")
        _path_under_any(target_object, object_roots, repo=repo, label="target object")
        object_candidates.append(target_object)
    translation_unit = assembly.parent.name
    object_names = {translation_unit + ".c.o", translation_unit + ".o"}
    for root in object_roots:
        if not root.exists():
            continue
        for candidate in _walk_regular_files(root, repo, "target object tree"):
            if candidate.name in object_names:
                object_candidates.append(candidate)
    unique_object = _dedupe_candidate_paths(
        object_candidates, repo, "target object"
    )
    if len(unique_object) != 1:
        if not unique_object:
            raise EvidenceRefusal(f"target object is missing for {record_id}")
        raise EvidenceRefusal(f"target object is ambiguous for {record_id}")
    target_object = unique_object[0]
    if target_object.name not in object_names:
        raise EvidenceRefusal(f"target object does not match translation unit for {record_id}")
    return assembly, target_object


def _target_measurement(
    repo: Path,
    record_id: str,
    record: Mapping[str, Any],
) -> tuple[str, dict[str, Any], bytes, bytes]:
    assembly, target_object = _find_target_files(repo, record, record_id)
    assembly_bytes = _read_evidence_bytes(assembly, "target assembly")
    object_bytes = _read_evidence_bytes(target_object, "target object")
    payload = {
        "artifact_type": "sotn-search-target-evidence",
        "assembly": {
            "content_hash": hash_bytes(assembly_bytes),
            "path": _relative(repo, assembly),
            "byte_size": len(assembly_bytes),
        },
        "object": {
            "content_hash": hash_bytes(object_bytes),
            "path": _relative(repo, target_object),
            "byte_size": len(object_bytes),
        },
        "record_id": record_id,
        "schema_version": "1.0.0",
    }
    return hash_canonical(payload), payload, assembly_bytes, object_bytes


def _planned_artifact_ref(
    data: bytes,
    *,
    category: str,
    suffix: str,
    media_type: str,
) -> ArtifactRef:
    """Calculate the archive reference without creating or changing files."""

    digest = hash_bytes(data)
    return ArtifactRef(
        content_hash=digest,
        path=f"artifacts/{category}/{digest[7:]}{suffix}",
        media_type=media_type,
        byte_size=len(data),
    )


def _artifact_ref_for_path(path: Path, run_root: Path) -> ArtifactRef:
    """Read and validate an existing content-addressed artifact reference."""

    try:
        relative = path.resolve(strict=True).relative_to(run_root.resolve(strict=True)).as_posix()
        data = path.read_bytes()
    except (OSError, RuntimeError, ValueError) as exc:
        raise PartialRunRefusal("existing evidence index cannot be read") from exc
    if not relative.startswith("artifacts/"):
        raise PartialRunRefusal("existing evidence index is outside the archive")
    suffix = path.suffix or ".bin"
    media_type = "application/json" if suffix == ".json" else "application/octet-stream"
    return _artifact_ref_from_dict({
        "content_hash": hash_bytes(data),
        "path": relative,
        "media_type": media_type,
        "byte_size": len(data),
    }, "run evidence index")


def _config_identity(
    repo: Path, config_path: Optional[Path | str]
) -> tuple[str, Path, dict[str, Any], bytes]:
    configured = Path(config_path) if config_path is not None else repo.joinpath(*_CONFIG_PATH_PARTS)
    if not configured.is_absolute():
        configured = repo / configured
    path = _safe_repo_file(repo, str(configured), "compiler configuration")
    data = _read_evidence_bytes(path, "compiler configuration")
    payload = {
        "artifact_type": "sotn-search-config-evidence",
        "content_hash": hash_bytes(data),
        "path": _relative(repo, path),
        "byte_size": len(data),
        "schema_version": "1.0.0",
    }
    return hash_bytes(data), path, payload, data


def _schema_identity(repo: Path) -> tuple[str, Path, dict[str, Any], bytes]:
    path = _safe_repo_file(
        repo, str(repo.joinpath(*_SCHEMA_PATH_PARTS)), "search schema"
    )
    data = _read_evidence_bytes(path, "search schema")
    payload = {
        "artifact_type": "sotn-search-schema-evidence",
        "content_hash": hash_bytes(data),
        "path": _relative(repo, path),
        "byte_size": len(data),
        "schema_version": "1.0.0",
    }
    return hash_bytes(data), path, payload, data


def _compiler_identity(
    config_path: Path,
    resolver: Optional[IdentityResolver],
) -> tuple[str, dict[str, Any]]:
    try:
        measured = resolver(config_path) if resolver is not None else None
        if resolver is None:
            try:
                from .compiler_corpus import pipeline_identity
            except ImportError:
                from automation.compiler_corpus import pipeline_identity  # type: ignore
            measured = pipeline_identity(config_path=config_path)
        if isinstance(measured, str):
            identity = measured
            descriptor: dict[str, Any] = {"identity": identity}
        else:
            identity = getattr(measured, "identity", None)
            if not isinstance(identity, str):
                raise EvidenceRefusal("compiler identity resolver returned no identity")
            raw_descriptor = getattr(measured, "to_dict", lambda: {})()
            if raw_descriptor is None:
                descriptor = {}
            elif isinstance(raw_descriptor, Mapping):
                descriptor = _canonical_mapping(raw_descriptor, "compiler identity")
            else:
                raise EvidenceRefusal("compiler identity resolver returned an invalid descriptor")
            # The resolver's measured identity is authoritative.  Do not let a
            # stale or self-reported ``identity`` field in its descriptor
            # silently disagree with the value bound by the manifest.
            descriptor = {**descriptor, "identity": identity}
            descriptor_identity = {
                key: value for key, value in descriptor.items()
                if key != "identity"
            }
            if descriptor_identity and hash_canonical(descriptor_identity) != identity:
                raise EvidenceRefusal(
                    "compiler identity resolver returned a descriptor with a mismatched identity"
                )
        validate_hash(identity, "compiler_identity")
    except SearchRunFactoryError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise EvidenceRefusal("compiler identity could not be measured") from exc
    return identity, descriptor


def _upstream_ref_state(repo: Path) -> dict[str, Any]:
    """Capture the current upstream ref without invoking a git command.

    Creation is intentionally a read-only boundary.  A lightweight checkout
    stores the remote-tracking ref as a loose file or in ``packed-refs``; when
    neither exists the result is an explicit inapplicable state rather than an
    invented provider identity.
    """
    ref_name = "upstream/master"
    module = repo / "automation" / "upstream_harvest.py"
    try:
        text = module.read_text(encoding="utf-8")
        match = re.search(r"^UPSTREAM\s*=\s*[\"']([^\"']+)[\"']", text, re.MULTILINE)
        if match:
            ref_name = match.group(1)
    except (OSError, UnicodeDecodeError):
        pass
    commit = ""
    git = repo / ".git"
    candidates: list[Path] = []
    if git.is_dir() and not git.is_symlink():
        candidates.append(git / "refs" / "remotes" / Path(*ref_name.split("/")))
        candidates.append(git / "packed-refs")
    elif git.is_file() and not git.is_symlink():
        # Worktrees point at a git directory.  Resolve only a relative gitdir
        # that remains below the repository, so this metadata cannot become a
        # path escape or an external provider input.
        try:
            raw = git.read_text(encoding="ascii").strip()
            if raw.startswith("gitdir:"):
                gitdir = Path(raw.split(":", 1)[1].strip())
                if not gitdir.is_absolute():
                    gitdir = repo / gitdir
                gitdir = gitdir.resolve(strict=True)
                gitdir.relative_to(repo.resolve(strict=True))
                candidates.append(gitdir / "refs" / "remotes" / Path(*ref_name.split("/")))
                candidates.append(gitdir / "packed-refs")
        except (OSError, UnicodeDecodeError, RuntimeError, ValueError):
            pass
    for path in candidates:
        if path.name == "packed-refs":
            try:
                for line in path.read_text(encoding="ascii").splitlines():
                    bits = line.split()
                    if len(bits) == 2 and bits[1] == "refs/remotes/" + ref_name:
                        if re.fullmatch(r"[0-9a-fA-F]{40}", bits[0]):
                            commit = bits[0].lower()
                            break
            except (OSError, UnicodeDecodeError):
                pass
        else:
            try:
                value = path.read_text(encoding="ascii").strip()
                if re.fullmatch(r"[0-9a-fA-F]{40}", value):
                    commit = value.lower()
                    break
            except (OSError, UnicodeDecodeError):
                pass
        if commit:
            break
    if not commit:
        return {
            "kind": "inapplicable",
            "reason": "current upstream ref is unavailable",
            "ref": ref_name,
        }
    return {"kind": "upstream_ref", "ref": ref_name, "commit": commit}


def _candidate_file_manifest(repo: Path) -> dict[str, Any]:
    """Return a bounded, canonical input manifest for preserved candidates."""
    root = repo / "automation" / "candidates"
    if not root.exists() or root.is_symlink() or not root.is_dir():
        return {
            "kind": "inapplicable",
            "reason": "automation/candidates tree is unavailable",
        }
    files = []
    for path in _walk_regular_files(root, repo, "automation candidate inputs"):
        data = _read_evidence_bytes(path, "automation candidate input")
        files.append({
            "path": _relative(repo, path),
            "content_hash": hash_bytes(data),
            "byte_size": len(data),
        })
    payload = {
        "kind": "canonical_file_manifest",
        "root": "automation/candidates",
        "files": files,
        "schema_version": "1.0.0",
    }
    return {**payload, "identity": hash_canonical(payload)}


def _lane_input_state(
    repo: Path,
    lane: str,
    *,
    indexed_runtime: Any = None,
) -> dict[str, Any]:
    if lane == "upstream_current":
        return _upstream_ref_state(repo)
    if lane in {"upstream_pinned", "upstream_open_pr"}:
        return {
            "kind": "inapplicable",
            "reason": "no explicit immutable upstream input was supplied",
        }
    if lane == "preserved_candidate":
        return _candidate_file_manifest(repo)
    if lane in _INDEXED_LANES:
        if indexed_runtime is None:
            raise EvidenceRefusal("indexed lane has no immutable runtime binding")
        binding = indexed_runtime.binding
        return {
            "kind": "indexed_runtime",
            "runtime_id": indexed_runtime.runtime_id,
            "binding_identity": hash_canonical(binding.to_dict()),
            "corpus_generation_id": binding.corpus_generation_id,
            "donor_index_generation_id": binding.donor_index_generation_id,
            "renderer_identity": binding.renderer_identity,
            "renderer_source_identity": binding.renderer_source_identity,
        }
    return {"kind": "none"}


def _factory_marker_identity() -> str:
    """Stable marker proving a run was created by this factory boundary."""
    return hash_canonical({"marker": _FACTORY_MARKER_PROTOCOL})


def _tool_identities(
    repo: Path,
    lanes: tuple[str, ...],
    *,
    config_path: Optional[Path] = None,
    schema_path: Optional[Path] = None,
    indexed_runtime: Any = None,
) -> tuple[dict[str, str], dict[str, Any]]:
    core_modules: dict[str, dict[str, Any]] = {}
    core_hashes: dict[str, str] = {}
    for relative, key in _CORE_MODULES:
        path = _safe_repo_file(repo, str(repo / Path(*relative.split("/"))), key)
        data = _read_evidence_bytes(path, key)
        digest = hash_bytes(data)
        core_hashes[key] = digest
        core_modules[relative] = {
            "content_hash": digest,
            "path": relative,
            "byte_size": len(data),
        }

    lane_modules: dict[str, list[dict[str, Any]]] = {}
    lane_inputs: dict[str, dict[str, Any]] = {}
    factory_relative, factory_key = _FACTORY_MODULE
    factory_path = _safe_repo_file(
        repo,
        str(repo / Path(*factory_relative.split("/"))),
        factory_key,
    )
    factory_bytes = _read_evidence_bytes(factory_path, factory_key)
    factory_identity = hash_bytes(factory_bytes)
    factory_entry = {
        "content_hash": factory_identity,
        "path": factory_relative,
        "byte_size": len(factory_bytes),
    }
    identities: dict[str, str] = {
        key: core_hashes[key] for _relative_path, key in _CORE_MODULES
    }
    identities[factory_key] = factory_identity
    identities[_FACTORY_MARKER_KEY] = _factory_marker_identity()
    for lane in lanes:
        entries = []
        for relative in _LANE_MODULES.get(lane, ()):
            path = _safe_repo_file(
                repo, str(repo / Path(*relative.split("/"))), lane + " lane tool"
            )
            data = _read_evidence_bytes(path, lane + " lane tool")
            entries.append({
                "content_hash": hash_bytes(data),
                "path": relative,
                "byte_size": len(data),
            })
        lane_modules[lane] = entries
        input_state = _lane_input_state(
            repo,
            lane,
            indexed_runtime=indexed_runtime,
        )
        lane_inputs[lane] = input_state
        identities[lane] = hash_canonical({
            "core_modules": core_hashes,
            "input_state": input_state,
            "lane": lane,
            "lane_modules": {
                item["path"]: item["content_hash"] for item in entries
            },
            "protocol": "sotn-search-lane-tool-v2",
        })
    mode = mode_identity(INSTRUMENTED_MODE)
    identities[MODE_TOOL_KEY] = mode
    if indexed_runtime is not None:
        identities[_INDEXED_RUNTIME_TOOL_KEY] = indexed_runtime.runtime_id
        identities[_TARGET_RENDERER_SOURCE_TOOL_KEY] = (
            indexed_runtime.binding.renderer_source_identity
        )
    if config_path is None:
        config_path = repo.joinpath(*_CONFIG_PATH_PARTS)
    if schema_path is None:
        schema_path = repo.joinpath(*_SCHEMA_PATH_PARTS)
    evidence = {
        "artifact_type": "sotn-search-tool-evidence",
        "core_modules": core_modules,
        "factory": {
            "identity": factory_identity,
            "marker": _factory_marker_identity(),
            "module": factory_entry,
            "protocol": _FACTORY_PROTOCOL,
        },
        "lane_inputs": lane_inputs,
        "lane_modules": lane_modules,
        "lane_module": core_modules["automation/search_lanes.py"],
        "mode": {
            "identity": mode,
            "mode": INSTRUMENTED_MODE,
            "tool_key": MODE_TOOL_KEY,
        },
        "config": {"path": _relative(repo, config_path)},
        "schema": {"path": _relative(repo, schema_path)},
        "schema_version": "1.0.0",
        "selected_lanes": list(lanes),
        "supervisor_module": core_modules["automation/search_supervisor.py"],
    }
    return identities, evidence


def _now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _manifest_identity(manifest: RunManifest | Mapping[str, Any]) -> dict[str, Any]:
    data = manifest.to_dict() if isinstance(manifest, RunManifest) else dict(manifest)
    data.pop("created_at", None)
    return json.loads(canonical_json(data))


def _find_canonical_manifests(
    repo: Path,
    run_id: str,
    *,
    allow_unpublished_root: Optional[Path] = None,
) -> tuple[Path, ...]:
    """Find every resolver-visible manifest for ``run_id`` without writing."""

    nonmatchings = repo / "nonmatchings"
    if not nonmatchings.exists():
        return ()
    if nonmatchings.is_symlink() or not nonmatchings.is_dir():
        raise PartialRunRefusal("canonical nonmatchings root is not a directory")
    matches: list[Path] = []
    try:
        function_dirs = sorted(nonmatchings.iterdir(), key=lambda path: path.name)
        for function_dir in function_dirs:
            if function_dir.is_symlink():
                raise PartialRunRefusal("canonical search-run path contains a symlink")
            if not function_dir.is_dir():
                continue
            search_runs = function_dir / "search-runs"
            if search_runs.is_symlink():
                raise PartialRunRefusal("canonical search-run path contains a symlink")
            if not search_runs.is_dir():
                continue
            run_root = search_runs / run_id
            if run_root.is_symlink():
                raise PartialRunRefusal("canonical run root is a symlink")
            if run_root.exists() and not run_root.is_dir():
                raise PartialRunRefusal("canonical run root is not a directory")
            manifest_path = run_root / _MANIFEST_FILENAME
            if not manifest_path.exists() and not manifest_path.is_symlink():
                if run_root.exists() and any(run_root.iterdir()):
                    if (
                        allow_unpublished_root is not None
                        and run_root.resolve(strict=False)
                        == allow_unpublished_root.resolve(strict=False)
                    ):
                        continue
                    raise PartialRunRefusal(
                        "canonical run root contains artifacts but no manifest"
                    )
                continue
            if manifest_path.is_symlink() or not manifest_path.is_file():
                raise PartialRunRefusal("canonical manifest is not a regular file")
            try:
                resolved = manifest_path.resolve(strict=True)
                resolved.relative_to(repo)
                document = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise PartialRunRefusal("canonical manifest is not durable JSON") from exc
            if not isinstance(document, Mapping) or document.get("run_id") != run_id:
                raise PartialRunRefusal("canonical manifest run_id does not match its path")
            matches.append(resolved)
    except PartialRunRefusal:
        raise
    except OSError as exc:
        raise PartialRunRefusal("canonical search-run tree could not be inspected") from exc
    return tuple(matches)


def _safe_canonical_root(repo: Path, anchor: str, run_id: str) -> tuple[Path, bool]:
    nonmatchings = repo / "nonmatchings"
    if nonmatchings.is_symlink():
        raise PartialRunRefusal("canonical nonmatchings root is a symlink")
    try:
        nonmatchings.mkdir(parents=True, exist_ok=True)
        anchor_dir = nonmatchings / anchor
        if anchor_dir.is_symlink():
            raise PartialRunRefusal("canonical function anchor is a symlink")
        if anchor_dir.exists() and not anchor_dir.is_dir():
            raise PartialRunRefusal("canonical function anchor is not a directory")
        anchor_dir.mkdir(exist_ok=True)
        search_runs = anchor_dir / "search-runs"
        if search_runs.is_symlink():
            raise PartialRunRefusal("canonical search-runs directory is a symlink")
        if search_runs.exists() and not search_runs.is_dir():
            raise PartialRunRefusal("canonical search-runs path is not a directory")
        search_runs.mkdir(exist_ok=True)
        run_root = search_runs / run_id
        if run_root.is_symlink():
            raise PartialRunRefusal("canonical run root is a symlink")
        if run_root.exists() and not run_root.is_dir():
            raise PartialRunRefusal("canonical run root is not a directory")
        existed = run_root.exists()
        run_root.mkdir(exist_ok=True)
    except PartialRunRefusal:
        raise
    except OSError as exc:
        raise SearchRunFactoryError("canonical run root could not be created") from exc
    _assert_no_symlink_components(run_root, root=repo)
    return run_root, existed


def _remove_empty_unpublished_root(root: Path) -> None:
    """Remove only a newly allocated, still-empty run root after failure."""
    try:
        if root.is_symlink() or not root.is_dir():
            return
        if any(root.iterdir()):
            return
        root.rmdir()
    except OSError:
        # Cleanup is best effort.  Any remaining entry is audited and refused
        # or recovered by the next creation attempt.
        return


def _audit_root(root: Path) -> None:
    try:
        for current, directories, files in os.walk(root, followlinks=False):
            for name in tuple(directories) + tuple(files):
                candidate = Path(current) / name
                if candidate.is_symlink():
                    raise PartialRunRefusal("run output contains a symlink")
                # Both the archive and supervisor use hidden, fsynced
                # temporary files before publication.  Seeing one on a retry
                # means the prior writer may have died between durable write
                # and rename; do not silently accept or overwrite that state.
                if (
                    name.endswith(".tmp")
                    or name.startswith(f".{_MANIFEST_FILENAME}.tmp-")
                ):
                    raise PartialRunRefusal("run output contains an unpublished temporary")
    except PartialRunRefusal:
        raise
    except OSError as exc:
        raise PartialRunRefusal("run output could not be inspected") from exc


def _read_existing_manifest(root: Path) -> RunManifest:
    path = root / _MANIFEST_FILENAME
    if path.is_symlink() or not path.is_file():
        raise PartialRunRefusal("existing manifest is not a regular file")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        return RunManifest.from_dict(document)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, SearchValidationError, TypeError, ValueError) as exc:
        raise PartialRunRefusal("existing manifest is corrupt") from exc


def _artifact_ref_from_dict(value: Any, label: str) -> ArtifactRef:
    try:
        reference = ArtifactRef.from_dict(value)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise PartialRunRefusal(f"{label} reference is invalid") from exc
    # The archive is content-addressed, not merely hash-checked.  A reference
    # whose bytes happen to verify under an arbitrary filename would permit an
    # edited index to turn an immutable artifact into a mutable path alias.
    # Every factory-produced reference is exactly one category component below
    # ``artifacts`` and names the digest followed by its optional extension.
    parts = reference.path.split("/")
    digest = reference.content_hash[7:]
    if (
        reference.path != "/".join(parts)
        or len(parts) != 3
        or parts[0] != "artifacts"
        or not parts[1]
        or parts[1] in (".", "..")
        or not parts[2].startswith(digest)
        or parts[2][len(digest):] not in ("", ".bin", ".json", ".s", ".o", ".toml", ".c", ".txt")
    ):
        raise PartialRunRefusal(f"{label} reference is not content-addressed")
    return reference


def _load_index(root: Path) -> tuple[dict[str, Any], Path]:
    artifact_root = root / "artifacts"
    if artifact_root.is_symlink() or not artifact_root.is_dir():
        raise PartialRunRefusal("run evidence archive is missing")
    candidates = []
    try:
        for path in artifact_root.rglob("*.json"):
            if path.is_symlink() or not path.is_file():
                raise PartialRunRefusal("run evidence archive contains a symlink")
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise PartialRunRefusal("run evidence archive contains corrupt JSON") from exc
            if isinstance(document, Mapping) and document.get("artifact_type") == "sotn-search-run-evidence-index":
                candidates.append((dict(document), path))
    except PartialRunRefusal:
        raise
    except OSError as exc:
        raise PartialRunRefusal("run evidence archive could not be inspected") from exc
    if len(candidates) != 1:
        raise PartialRunRefusal("run evidence index is missing or ambiguous")
    return candidates[0]


def _verify_existing_artifacts(
    root: Path,
    index: Mapping[str, Any],
    *,
    expected_anchor_function: Optional[str] = None,
    expected_record_ids: Optional[Sequence[str]] = None,
    expected_target_identities: Optional[Mapping[str, str]] = None,
    expected_queue_evidence_identity: Optional[str] = None,
    expected_subset_identity: Optional[str] = None,
    expected_source_identity: Optional[str] = None,
    expected_config_identity: Optional[str] = None,
    expected_schema_identity: Optional[str] = None,
    expected_compiler_identity: Optional[str] = None,
    expected_tool_identities: Optional[Mapping[str, str]] = None,
    index_path: Optional[Path] = None,
) -> None:
    archive = ContentAddressedArchive(root)
    expected_index_fields = {
        "artifact_type", "manifest_hash", "manifest_identity", "run_id",
        "schema_version", "anchor_function", "subset", "queue_evidence",
        "target_evidence", "target_index", "source", "config", "schema",
        "tools", "compiler", "manifest_intent",
    }
    expected_runtime_id = (
        (expected_tool_identities or {}).get(_INDEXED_RUNTIME_TOOL_KEY)
    )
    if expected_runtime_id is not None:
        expected_index_fields.add("indexed_runtime")
    if set(index) != expected_index_fields:
        raise PartialRunRefusal("run evidence index has unknown or missing fields")
    required = (
        "subset", "queue_evidence", "target_evidence", "target_index",
        "source", "config", "schema", "tools", "compiler", "manifest_intent",
    )
    for key in required:
        if key not in index:
            raise PartialRunRefusal(f"run evidence index is missing {key}")
    refs: list[tuple[str, Any]] = [
        ("subset", index["subset"]),
        ("queue_evidence", index["queue_evidence"]),
        ("target_index", index["target_index"]),
        ("source", index["source"]),
        ("config", index["config"]),
        ("schema", index["schema"]),
        ("tools", index["tools"]),
        ("compiler", index["compiler"]),
        ("manifest_intent", index["manifest_intent"]),
    ]
    if expected_runtime_id is not None:
        refs.append(("indexed_runtime", index["indexed_runtime"]))
    targets = index["target_evidence"]
    if not isinstance(targets, Mapping) or not targets:
        raise PartialRunRefusal("run evidence index target coverage is missing")
    if expected_record_ids is not None and set(targets) != set(expected_record_ids):
        raise PartialRunRefusal("run evidence index target coverage does not match the manifest")
    refs.extend((f"target_evidence:{key}", value) for key, value in targets.items())
    expected_media_types = {
        "subset": "application/json",
        "queue_evidence": "application/json",
        "target_index": "application/json",
        "source": "application/json",
        "config": "application/toml",
        "schema": "application/json",
        "tools": "application/json",
        "compiler": "application/json",
        "manifest_intent": "application/json",
        "indexed_runtime": "application/json",
    }
    for label, raw in refs:
        reference = _artifact_ref_from_dict(raw, label)
        expected_media_type = expected_media_types.get(
            label.split(":", 1)[0], "application/json"
        )
        if reference.media_type != expected_media_type:
            raise PartialRunRefusal(f"{label} reference media type is invalid")
        if label == "subset" and expected_subset_identity is not None:
            try:
                subset_document = json.loads(
                    archive.resolve(reference).read_text(encoding="utf-8")
                )
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise PartialRunRefusal("subset artifact is missing or corrupt") from exc
            if not isinstance(subset_document, Mapping):
                raise PartialRunRefusal("subset artifact is not a JSON object")
            if subset_document.get("artifact_hash") != expected_subset_identity:
                raise PartialRunRefusal("subset artifact identity is not manifest-bound")
        if label == "queue_evidence" and expected_queue_evidence_identity is not None:
            if reference.content_hash != expected_queue_evidence_identity:
                raise PartialRunRefusal("queue evidence identity is not manifest-bound")
        try:
            data = archive.verify(reference)
        except Exception as exc:  # noqa: BLE001
            raise PartialRunRefusal(f"{label} artifact is missing or corrupt") from exc
        if label.startswith("target_evidence:"):
            target_record_id = label.split(":", 1)[1]
            if (
                expected_target_identities is not None
                and reference.content_hash != expected_target_identities.get(target_record_id)
            ):
                raise PartialRunRefusal("target evidence identity is not manifest-bound")
            try:
                target_document = json.loads(data.decode("utf-8"))
                if target_document.get("record_id") != target_record_id:
                    raise PartialRunRefusal("target evidence record binding is invalid")
                assembly = _artifact_ref_from_dict(
                    target_document["assembly"]["artifact"], label + ".assembly"
                )
                target_object = _artifact_ref_from_dict(
                    target_document["object"]["artifact"], label + ".object"
                )
                if (
                    assembly.media_type != "text/x-asm"
                    or target_object.media_type != "application/octet-stream"
                ):
                    raise PartialRunRefusal(
                        "target assembly/object media types are invalid"
                    )
                assembly_data = archive.verify(assembly)
                object_data = archive.verify(target_object)
                if (
                    target_document["assembly"].get("content_hash") != hash_bytes(assembly_data)
                    or target_document["assembly"].get("byte_size") != len(assembly_data)
                    or target_document["object"].get("content_hash") != hash_bytes(object_data)
                    or target_document["object"].get("byte_size") != len(object_data)
                ):
                    raise PartialRunRefusal("target assembly/object identity is invalid")
            except Exception as exc:  # noqa: BLE001
                raise PartialRunRefusal(
                    f"{label} target assembly/object evidence is missing or corrupt"
                ) from exc

    # The content-addressed hash check above catches byte replacement.  These
    # semantic checks also catch an edited evidence index that points at a
    # different, otherwise valid artifact, or a JSON artifact whose internal
    # bindings no longer agree with the manifest.
    try:
        subset_ref = _artifact_ref_from_dict(index["subset"], "subset")
        subset_document = json.loads(archive.verify(subset_ref).decode("utf-8"))
        if not isinstance(subset_document, Mapping):
            raise PartialRunRefusal("subset artifact is not a JSON object")
        subset_ids = subset_document.get("record_ids")
        if (
            set(subset_document) != {
                "artifact_type", "record_ids", "schema_version", "artifact_hash"
            }
            or
            subset_document.get("artifact_type") != "sotn-search-subset"
            or subset_document.get("schema_version") != "1.0.0"
            or not isinstance(subset_ids, list)
            or subset_document.get("artifact_hash") != expected_subset_identity
            or canonical_subset_identity(subset_ids) != expected_subset_identity
        ):
            raise PartialRunRefusal("subset artifact binding is invalid")

        queue_ref = _artifact_ref_from_dict(index["queue_evidence"], "queue_evidence")
        queue_document = json.loads(archive.verify(queue_ref).decode("utf-8"))
        if not isinstance(queue_document, Mapping):
            raise PartialRunRefusal("queue evidence is not a JSON object")
        queue_records = queue_document.get("records")
        queue_ids = queue_document.get("record_ids")
        if (
            queue_document.get("artifact_type") != "sotn-search-queue-evidence"
            or queue_document.get("schema_version") != "1.0.0"
            or queue_document.get("status_binding") != "todo"
            or queue_ids != list(expected_record_ids or ())
            or not isinstance(queue_records, list)
            or [record.get("id") for record in queue_records if isinstance(record, Mapping)]
            != list(expected_record_ids or ())
            or any(
                not isinstance(record, Mapping) or record.get("status") != "todo"
                for record in queue_records
            )
        ):
            raise PartialRunRefusal("queue evidence binding is invalid")

        target_index_ref = _artifact_ref_from_dict(index["target_index"], "target_index")
        target_index_document = json.loads(archive.verify(target_index_ref).decode("utf-8"))
        if not isinstance(target_index_document, Mapping):
            raise PartialRunRefusal("target index is not a JSON object")
        target_entries = target_index_document.get("records")
        expected_target_entries = [
            {
                "record_id": record_id,
                "target_identity": expected_target_identities[record_id],
                "target_evidence": index["target_evidence"][record_id],
            }
            for record_id in (expected_record_ids or ())
        ]
        if (
            set(target_index_document) != {
                "artifact_type", "records", "schema_version"
            }
            or
            target_index_document.get("artifact_type") != "sotn-search-target-index"
            or target_index_document.get("schema_version") != "1.0.0"
            or target_entries != expected_target_entries
        ):
            raise PartialRunRefusal("target index binding is invalid")

        source_ref = _artifact_ref_from_dict(index["source"], "source")
        source_document = json.loads(archive.verify(source_ref).decode("utf-8"))
        if not isinstance(source_document, Mapping):
            raise PartialRunRefusal("source evidence is not a JSON object")
        if (
            source_document.get("artifact_type") != "sotn-search-source-evidence"
            or source_document.get("schema_version") != "1.0.0"
            or expected_source_identity is None
            or hash_canonical(source_document) != expected_source_identity
        ):
            raise PartialRunRefusal("source evidence binding is invalid")

        config_ref = _artifact_ref_from_dict(index["config"], "config")
        schema_ref = _artifact_ref_from_dict(index["schema"], "schema")
        if (
            expected_config_identity is None
            or config_ref.content_hash != expected_config_identity
            or expected_schema_identity is None
            or schema_ref.content_hash != expected_schema_identity
        ):
            raise PartialRunRefusal("configuration or schema binding is invalid")

        compiler_ref = _artifact_ref_from_dict(index["compiler"], "compiler")
        compiler_document = json.loads(archive.verify(compiler_ref).decode("utf-8"))
        if (
            not isinstance(compiler_document, Mapping)
            or expected_compiler_identity is None
            or compiler_document.get("identity") != expected_compiler_identity
        ):
            raise PartialRunRefusal("compiler evidence binding is invalid")
        # ``pipeline_identity`` hashes its measured descriptor.  Production
        # evidence carries that descriptor plus a convenience ``identity``
        # field; when the descriptor is present, verify that its bytes really
        # recompute the bound compiler identity instead of trusting the field
        # alone.  Test/injected identities may intentionally be identity-only.
        compiler_descriptor = {
            key: value for key, value in compiler_document.items()
            if key != "identity"
        }
        if compiler_descriptor and hash_canonical(compiler_descriptor) != expected_compiler_identity:
            raise PartialRunRefusal("compiler descriptor does not match its identity")

        if expected_runtime_id is not None:
            runtime_ref = _artifact_ref_from_dict(
                index["indexed_runtime"], "indexed_runtime"
            )
            runtime_document = json.loads(
                archive.verify(runtime_ref).decode("utf-8")
            )
            try:
                try:
                    from .search_indexed_runtime import IndexedRuntimeGeneration
                except ImportError:  # direct invocation from automation/
                    from search_indexed_runtime import IndexedRuntimeGeneration  # type: ignore
                runtime = IndexedRuntimeGeneration.from_dict(runtime_document)
            except Exception as exc:  # noqa: BLE001
                raise PartialRunRefusal(
                    "indexed runtime binding artifact is invalid"
                ) from exc
            if (
                runtime.runtime_id != expected_runtime_id
                or runtime.binding.renderer_source_identity
                != (expected_tool_identities or {}).get(
                    _TARGET_RENDERER_SOURCE_TOOL_KEY
                )
            ):
                raise PartialRunRefusal(
                    "indexed runtime binding differs from the manifest"
                )

        intent_ref = _artifact_ref_from_dict(
            index["manifest_intent"], "manifest_intent"
        )
        intent_document = json.loads(archive.verify(intent_ref).decode("utf-8"))
        intent_manifest = RunManifest.from_dict(intent_document)
        if (
            intent_manifest.run_id != index.get("run_id")
            or hash_canonical(intent_manifest.to_dict()) != index.get("manifest_hash")
            or _manifest_identity(intent_manifest) != index.get("manifest_identity")
        ):
            raise PartialRunRefusal("manifest intent does not bind the evidence index")
        if (
            expected_record_ids is not None
            and tuple(intent_manifest.queue_record_ids) != tuple(expected_record_ids)
        ):
            raise PartialRunRefusal("manifest intent subset is not archive-bound")
        if (
            expected_tool_identities is not None
            and tuple(intent_manifest.selected_lanes) != tuple(
                lane for lane in LANES if lane in expected_tool_identities
            )
        ):
            raise PartialRunRefusal("manifest intent lanes are not archive-bound")

        tools_ref = _artifact_ref_from_dict(index["tools"], "tools")
        tools_document = json.loads(archive.verify(tools_ref).decode("utf-8"))
        # RunManifest serialisation sorts object keys, so derive the selected
        # lane order from the schema's canonical LANES tuple rather than from
        # Mapping insertion order in a reloaded manifest.
        selected_tool_lanes = tuple(
            lane for lane in LANES if lane in (expected_tool_identities or {})
        )
        if not isinstance(tools_document, Mapping):
            raise PartialRunRefusal("tool evidence is not a JSON object")
        lane_module = tools_document.get("lane_module", {})
        supervisor_module = tools_document.get("supervisor_module", {})
        mode_document = tools_document.get("mode", {})
        core_modules = tools_document.get("core_modules", {})
        lane_modules = tools_document.get("lane_modules", {})
        lane_inputs = tools_document.get("lane_inputs", {})
        config_document = tools_document.get("config", {})
        schema_document = tools_document.get("schema", {})
        factory_document = tools_document.get("factory", {})
        if (
            set(tools_document) != {
                "artifact_type", "core_modules", "factory", "lane_inputs",
                "lane_modules", "lane_module", "mode", "config", "schema",
                "schema_version", "selected_lanes", "supervisor_module"
            }
            or tools_document.get("artifact_type") != "sotn-search-tool-evidence"
            or tools_document.get("schema_version") != "1.0.0"
            or tools_document.get("selected_lanes") != list(selected_tool_lanes)
            or not isinstance(core_modules, Mapping)
            or not isinstance(lane_modules, Mapping)
            or not isinstance(lane_inputs, Mapping)
            or not isinstance(config_document, Mapping)
            or not isinstance(schema_document, Mapping)
            or not isinstance(factory_document, Mapping)
            or not isinstance(lane_module, Mapping)
            or not isinstance(supervisor_module, Mapping)
            or not isinstance(mode_document, Mapping)
            or lane_module != core_modules.get("automation/search_lanes.py")
            or supervisor_module != core_modules.get("automation/search_supervisor.py")
            or mode_document.get("identity") != (expected_tool_identities or {}).get(MODE_TOOL_KEY)
            or mode_document.get("mode") != INSTRUMENTED_MODE
            or set(factory_document) != {"identity", "marker", "module", "protocol"}
            or factory_document.get("protocol") != _FACTORY_PROTOCOL
            or factory_document.get("identity") != (expected_tool_identities or {}).get(_FACTORY_TOOL_KEY)
            or factory_document.get("marker") != (expected_tool_identities or {}).get(_FACTORY_MARKER_KEY)
            or not isinstance(factory_document.get("module"), Mapping)
            or set(factory_document["module"]) != {"content_hash", "path", "byte_size"}
            or factory_document["module"].get("content_hash") != (expected_tool_identities or {}).get(_FACTORY_TOOL_KEY)
            or factory_document["module"].get("path") != _FACTORY_MODULE[0]
            or not isinstance(factory_document["module"].get("byte_size"), int)
            or factory_document["module"].get("byte_size") < 0
            or not isinstance(config_document.get("path"), str)
            or schema_document.get("path") != "automation/search-ledger.schema.json"
        ):
            raise PartialRunRefusal("tool evidence binding is invalid")
        expected_core_paths = {path for path, _key in _CORE_MODULES}
        if set(core_modules) != expected_core_paths:
            raise PartialRunRefusal("core tool evidence coverage is invalid")
        core_hashes: dict[str, str] = {}
        for relative, key in _CORE_MODULES:
            entry = core_modules.get(relative)
            if (
                not isinstance(entry, Mapping)
                or set(entry) != {"content_hash", "path", "byte_size"}
                or entry.get("path") != relative
                or not isinstance(entry.get("byte_size"), int)
                or entry.get("byte_size") < 0
                or not isinstance(entry.get("content_hash"), str)
                or (expected_tool_identities or {}).get(key) != entry.get("content_hash")
            ):
                raise PartialRunRefusal("core tool identity is invalid")
            try:
                validate_hash(entry["content_hash"], "core tool identity")
            except SearchValidationError as exc:
                raise PartialRunRefusal("core tool identity is invalid") from exc
            core_hashes[key] = entry["content_hash"]
        if set(lane_modules) != set(selected_tool_lanes) or set(lane_inputs) != set(selected_tool_lanes):
            raise PartialRunRefusal("selected lane tool evidence coverage is invalid")
        for lane in selected_tool_lanes:
            entries = lane_modules.get(lane)
            input_state = lane_inputs.get(lane)
            if not isinstance(entries, list) or not isinstance(input_state, Mapping):
                raise PartialRunRefusal("selected lane tool evidence is invalid")
            expected_paths = tuple(_LANE_MODULES.get(lane, ()))
            if tuple(item.get("path") for item in entries if isinstance(item, Mapping)) != expected_paths:
                raise PartialRunRefusal("selected lane module coverage is invalid")
            lane_hashes = {}
            for entry, relative in zip(entries, expected_paths):
                if (
                    not isinstance(entry, Mapping)
                    or set(entry) != {"content_hash", "path", "byte_size"}
                    or entry.get("path") != relative
                    or not isinstance(entry.get("byte_size"), int)
                    or entry.get("byte_size") < 0
                    or not isinstance(entry.get("content_hash"), str)
                ):
                    raise PartialRunRefusal("selected lane module identity is invalid")
                try:
                    validate_hash(entry["content_hash"], "lane module identity")
                except SearchValidationError as exc:
                    raise PartialRunRefusal("selected lane module identity is invalid") from exc
                lane_hashes[relative] = entry["content_hash"]
            expected_lane_identity = hash_canonical({
                "core_modules": core_hashes,
                "input_state": dict(input_state),
                "lane": lane,
                "lane_modules": lane_hashes,
                "protocol": "sotn-search-lane-tool-v2",
            })
            if (expected_tool_identities or {}).get(lane) != expected_lane_identity:
                raise PartialRunRefusal("selected lane tool identity is invalid")
    except PartialRunRefusal:
        raise
    except (KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError, SearchValidationError, TypeError, ValueError) as exc:
        raise PartialRunRefusal("run evidence semantic bindings are corrupt") from exc
    if index_path is not None:
        index_reference = _artifact_ref_for_path(index_path, root)
        try:
            archive.verify(index_reference)
        except Exception as exc:  # noqa: BLE001
            raise PartialRunRefusal("run evidence index is missing or corrupt") from exc
    if expected_anchor_function is not None and index.get("anchor_function") != expected_anchor_function:
        raise PartialRunRefusal("run evidence index anchor binding is invalid")


def _archive_json(
    archive: ContentAddressedArchive,
    raw_reference: Any,
    label: str,
) -> dict[str, Any]:
    reference = _artifact_ref_from_dict(raw_reference, label)
    try:
        value = json.loads(archive.verify(reference).decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PartialRunRefusal(label + " artifact is missing or corrupt") from exc
    if not isinstance(value, Mapping):
        raise PartialRunRefusal(label + " artifact is not a JSON object")
    return dict(value)


def _factory_manifest_marker(manifest: RunManifest) -> bool:
    # The stable marker survives a factory protocol/module change.  A manifest
    # carrying either factory key is factory evidence; a missing or altered
    # marker must fail closed instead of silently becoming a legacy run.
    marker = manifest.tool_identities.get(_FACTORY_MARKER_KEY)
    module_identity = manifest.tool_identities.get(_FACTORY_TOOL_KEY)
    if marker is None and module_identity is None:
        return False
    if marker != _factory_marker_identity() or not isinstance(module_identity, str):
        raise PartialRunRefusal("factory manifest marker is invalid")
    return True


def verify_factory_archive(
    run_root: Path | str,
    manifest: Optional[RunManifest] = None,
) -> RunManifest:
    """Validate a factory run's durable archive without reading live inputs."""
    root = Path(run_root).resolve(strict=True)
    if manifest is None:
        manifest = _read_existing_manifest(root)
    if not isinstance(manifest, RunManifest):
        raise PartialRunRefusal("factory archive requires a typed manifest")
    if not _factory_manifest_marker(manifest):
        return manifest
    index, index_path = _load_index(root)
    if (
        index.get("run_id") != manifest.run_id
        or index.get("manifest_hash") != hash_canonical(manifest.to_dict())
        or index.get("manifest_identity") != _manifest_identity(manifest)
    ):
        raise PartialRunRefusal("run evidence index does not bind the manifest")
    anchor = canonical_anchor_function(manifest.function_ids)
    _verify_existing_artifacts(
        root,
        index,
        expected_anchor_function=anchor,
        expected_record_ids=manifest.queue_record_ids,
        expected_target_identities=manifest.target_identities,
        expected_queue_evidence_identity=manifest.queue_evidence_identity,
        expected_subset_identity=manifest.subset_identity,
        expected_source_identity=manifest.source_identity,
        expected_config_identity=manifest.config_identity,
        expected_schema_identity=manifest.schema_identity,
        expected_compiler_identity=manifest.compiler_identity,
        expected_tool_identities=manifest.tool_identities,
        index_path=index_path,
    )
    return manifest


def verify_factory_runtime(
    run_root: Path | str,
    manifest: Optional[RunManifest] = None,
    *,
    repo: Optional[Path | str] = None,
) -> RunManifest:
    """Verify current execution inputs against one factory-created run.

    The queue is deliberately absent from this check.  Its exact status and
    notes were frozen in the archived queue evidence at creation time; live
    queue changes must not turn a valid immutable run into a different run.
    """
    root = Path(run_root).resolve(strict=True)
    manifest = verify_factory_archive(root, manifest)
    if not _factory_manifest_marker(manifest):
        return manifest
    root_repo = _repo_root(repo) if repo is not None else root.parents[3]
    index, _index_path = _load_index(root)
    archive = ContentAddressedArchive(root)
    current_source_identity, _current_source_document = _source_identity(root_repo)
    if current_source_identity != manifest.source_identity:
        raise EvidenceRefusal("current repository source differs from the frozen run")
    queue_document = _archive_json(archive, index["queue_evidence"], "queue evidence")
    queue_records = queue_document.get("records")
    if (
        queue_document.get("record_ids") != list(manifest.queue_record_ids)
        or not isinstance(queue_records, list)
    ):
        raise EvidenceRefusal("archived queue evidence cannot be used for runtime binding")
    records_by_id = {
        record.get("id"): record
        for record in queue_records
        if isinstance(record, Mapping)
    }
    if set(records_by_id) != set(manifest.queue_record_ids):
        raise EvidenceRefusal("archived queue evidence has incomplete record coverage")
    for record_id in manifest.queue_record_ids:
        try:
            identity, payload, assembly_bytes, object_bytes = _target_measurement(
                root_repo, record_id, records_by_id[record_id]
            )
            # Creation binds deterministic archive references into the target
            # payload before hashing.  Reproduce that binding for the runtime
            # measurement so unchanged target bytes have the exact same identity.
            assembly_ref = _planned_artifact_ref(
                assembly_bytes,
                category="target-assembly",
                suffix=".s",
                media_type="text/x-asm",
            )
            object_ref = _planned_artifact_ref(
                object_bytes,
                category="target-object",
                suffix=".o",
                media_type="application/octet-stream",
            )
            payload = {
                **payload,
                "assembly": {
                    **payload["assembly"],
                    "artifact": assembly_ref.to_dict(),
                },
                "object": {
                    **payload["object"],
                    "artifact": object_ref.to_dict(),
                },
            }
            identity = hash_canonical(payload)
        except SearchRunFactoryError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise EvidenceRefusal("current target evidence could not be measured") from exc
        if identity != manifest.target_identities[record_id]:
            raise EvidenceRefusal("current target evidence differs from the frozen run")

    tools_document = _archive_json(archive, index["tools"], "tool evidence")
    config_document = tools_document.get("config")
    schema_document = tools_document.get("schema")
    if (
        not isinstance(config_document, Mapping)
        or not isinstance(config_document.get("path"), str)
        or not isinstance(schema_document, Mapping)
        or schema_document.get("path") != "automation/search-ledger.schema.json"
    ):
        raise EvidenceRefusal("archived configuration paths are invalid")
    config_identity, config_path, _config_payload, _config_bytes = _config_identity(
        root_repo, config_document["path"]
    )
    schema_identity, schema_path, _schema_payload, _schema_bytes = _schema_identity(root_repo)
    if (
        config_identity != manifest.config_identity
        or _relative(root_repo, config_path) != config_document["path"]
        or schema_identity != manifest.schema_identity
        or _relative(root_repo, schema_path) != schema_document["path"]
    ):
        raise EvidenceRefusal("current configuration or schema differs from the frozen run")

    compiler_document = _archive_json(archive, index["compiler"], "compiler evidence")
    # Creation may use an injected resolver for isolated tests, but a run may
    # execute only after the current compiler pipeline is measured again.
    compiler_identity, _compiler_payload = _compiler_identity(config_path, None)
    if compiler_identity != manifest.compiler_identity:
        raise EvidenceRefusal("current compiler differs from the frozen run")

    runtime_id = manifest.tool_identities.get(_INDEXED_RUNTIME_TOOL_KEY)
    indexed_runtime = (
        _load_indexed_runtime_generation(runtime_id, root_repo)
        if runtime_id is not None
        else None
    )
    current_tools, _current_tool_document = _tool_identities(
        root_repo,
        tuple(manifest.selected_lanes),
        config_path=config_path,
        schema_path=schema_path,
        indexed_runtime=indexed_runtime,
    )
    if current_tools != dict(manifest.tool_identities):
        raise EvidenceRefusal("current search tools or bound lane inputs differ from the frozen run")
    return manifest


verify_factory_run = verify_factory_runtime


def _publish_manifest(root: Path, manifest: RunManifest) -> None:
    path = root / _MANIFEST_FILENAME
    payload = (canonical_json(manifest.to_dict()) + "\n").encode("utf-8")
    temporary = root / f".{_MANIFEST_FILENAME}.tmp-{os.getpid()}-{time.time_ns()}"
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(str(temporary), flags, 0o644)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(str(temporary), str(path))
        except FileExistsError as exc:
            raise RunNameCollision("run manifest appeared during creation") from exc
        except OSError as exc:
            raise SearchRunFactoryError("immutable manifest publication is unavailable") from exc
        temporary.unlink()
        try:
            directory_descriptor = os.open(str(root), os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except OSError:
            pass
    except SearchRunFactoryError:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise
    except OSError as exc:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise SearchRunFactoryError("manifest publication failed") from exc


def _create_instrumented_run_locked(
    name: str,
    record_ids: Sequence[str],
    lanes: Sequence[str],
    *,
    repo: Optional[Path | str] = None,
    queue_reader: Optional[QueueReader] = None,
    compiler_identity_resolver: Optional[IdentityResolver] = None,
    config_path: Optional[Path | str] = None,
    runtime_id: Optional[str] = None,
    now: Optional[Clock] = None,
    fault_hook: Optional[FactoryFaultHook] = None,
) -> dict[str, Any]:
    """Create or return one immutable, instrumented run from exact todo IDs.

    A retry is resolved from the normalized logical subset and the archived
    manifest before the live queue is read.  Only a new name may consult live
    todo eligibility.
    """
    run_id, normalized_ids, selected_lanes = _normalize_inputs(name, record_ids, lanes)
    normalized_runtime_id = _normalize_indexed_runtime_id(
        runtime_id,
        selected_lanes,
    )
    task_count = len(normalized_ids) * len(selected_lanes)
    if task_count > _MAX_TASKS:
        raise InputRefusal("requested subset exceeds the bounded task budget")
    coordinator_limit = task_count * (1 + _MAX_CHILD_TASKS_PER_BASE)
    if coordinator_limit > MAX_COORDINATOR_TASKS:
        raise InputRefusal(
            "requested subset cannot fit the bounded coordinator fan-out budget"
        )

    root_repo = _repo_root(repo)
    reader = queue_reader or _read_queue_from_scheduler
    function_ids = tuple(
        sorted({record_id.split(":", 2)[2] for record_id in normalized_ids})
    )
    anchor = canonical_anchor_function(function_ids)
    expected_root = (
        root_repo / "nonmatchings" / anchor / "search-runs" / run_id
    )
    existing_manifests = _find_canonical_manifests(
        root_repo, run_id, allow_unpublished_root=expected_root
    )
    expected_manifest_path = (expected_root / _MANIFEST_FILENAME).resolve(strict=False)
    if any(path != expected_manifest_path for path in existing_manifests):
        raise RunNameCollision("run name already exists under another canonical anchor")
    run_root, _existed = _safe_canonical_root(root_repo, anchor, run_id)
    _audit_root(run_root)

    def existing_result(
        existing_manifest: RunManifest,
        *,
        recovered: bool = False,
    ) -> dict[str, Any]:
        """Verify one archived winner and return its idempotent result."""
        if (
            tuple(existing_manifest.queue_record_ids) != normalized_ids
            or tuple(existing_manifest.selected_lanes) != selected_lanes
            or tuple(existing_manifest.function_ids) != function_ids
        ):
            raise RunNameCollision(
                "run name already binds a different subset or lane set"
            )
        if (
            existing_manifest.tool_identities.get(_INDEXED_RUNTIME_TOOL_KEY)
            != normalized_runtime_id
        ):
            raise RunNameCollision(
                "run name already binds a different indexed runtime"
            )
        if canonical_anchor_function(existing_manifest.function_ids) != anchor:
            raise RunNameCollision("run name already binds a different canonical anchor")
        verify_factory_archive(run_root, existing_manifest)
        _existing_index, existing_index_path = _load_index(run_root)
        return {
            "command": "create-instrumented",
            "ok": True,
            "idempotent": True,
            "run_id": run_id,
            "run_root": str(run_root),
            "anchor_function": anchor,
            "manifest": existing_manifest.to_dict(),
            "evidence_index": _artifact_ref_for_path(
                existing_index_path, run_root
            ).to_dict(),
            **({"recovered": True} if recovered else {}),
        }

    entries = tuple(run_root.iterdir())
    manifest_path = run_root / _MANIFEST_FILENAME
    if manifest_path.is_file() or manifest_path.is_symlink():
        return existing_result(_read_existing_manifest(run_root))
    if entries:
        # The immutable intent is written before the evidence index.  If the
        # process dies after the index write, retry can publish exactly those
        # bytes without consulting changed live inputs or wall-clock time.
        index, _index_path = _load_index(run_root)
        intent_document = _archive_json(
            ContentAddressedArchive(run_root),
            index.get("manifest_intent"),
            "manifest intent",
        )
        try:
            intent_manifest = RunManifest.from_dict(intent_document)
        except (SearchValidationError, TypeError, ValueError) as exc:
            raise PartialRunRefusal("manifest intent is corrupt") from exc
        if (
            tuple(intent_manifest.queue_record_ids) != normalized_ids
            or tuple(intent_manifest.selected_lanes) != selected_lanes
            or tuple(intent_manifest.function_ids) != function_ids
        ):
            raise RunNameCollision(
                "unpublished run name binds a different subset or lane set"
            )
        if canonical_anchor_function(intent_manifest.function_ids) != anchor:
            raise PartialRunRefusal("manifest intent anchor is invalid")
        verify_factory_archive(run_root, intent_manifest)
        _publish_manifest(run_root, intent_manifest)
        return existing_result(intent_manifest, recovered=True)

    # Only a genuinely new name may consult live queue eligibility.
    records = _status_bound_records(normalized_ids, reader)
    if tuple(sorted({record["function"] for record in records})) != function_ids:
        raise EvidenceRefusal(
            "queue function evidence does not bind the requested anchor"
        )
    subset_identity = canonical_subset_identity(normalized_ids)
    queue_payload = {
        "artifact_type": "sotn-search-queue-evidence",
        "record_ids": list(normalized_ids),
        "records": list(records),
        "schema_version": "1.0.0",
        "status_binding": "todo",
    }
    queue_evidence_identity = hash_canonical(queue_payload)
    source_identity, source_payload = _source_identity(root_repo)
    (
        config_identity,
        resolved_config,
        _config_payload,
        config_bytes,
    ) = _config_identity(root_repo, config_path)
    (
        schema_identity,
        resolved_schema,
        _schema_payload,
        schema_bytes,
    ) = _schema_identity(root_repo)
    compiler_identity, compiler_payload = _compiler_identity(
        resolved_config, compiler_identity_resolver
    )
    indexed_runtime = (
        _load_indexed_runtime_generation(normalized_runtime_id, root_repo)
        if normalized_runtime_id is not None
        else None
    )
    if indexed_runtime is not None and (
        indexed_runtime.binding.compiler_identity != compiler_identity
        or indexed_runtime.binding.config_identity != config_identity
    ):
        raise EvidenceRefusal(
            "indexed runtime compiler or configuration differs from the new run"
        )
    tool_identities, tool_payload = _tool_identities(
        root_repo,
        selected_lanes,
        config_path=resolved_config,
        schema_path=resolved_schema,
        indexed_runtime=indexed_runtime,
    )

    target_payloads: dict[str, dict[str, Any]] = {}
    target_identities: dict[str, str] = {}
    target_bytes: dict[str, tuple[bytes, bytes]] = {}
    for record_id, record in zip(normalized_ids, records):
        _identity, payload, assembly_bytes, object_bytes = _target_measurement(
            root_repo, record_id, record
        )
        target_payloads[record_id] = payload
        target_bytes[record_id] = (assembly_bytes, object_bytes)

    # Planned references make target evidence identities deterministic before
    # any archive path is materialized.
    target_artifact_refs: dict[str, tuple[ArtifactRef, ArtifactRef]] = {}
    for record_id in normalized_ids:
        assembly_bytes, object_bytes = target_bytes[record_id]
        assembly_ref = _planned_artifact_ref(
            assembly_bytes,
            category="target-assembly",
            suffix=".s",
            media_type="text/x-asm",
        )
        object_ref = _planned_artifact_ref(
            object_bytes,
            category="target-object",
            suffix=".o",
            media_type="application/octet-stream",
        )
        target_artifact_refs[record_id] = (assembly_ref, object_ref)
        target_payloads[record_id] = {
            **target_payloads[record_id],
            "assembly": {
                **target_payloads[record_id]["assembly"],
                "artifact": assembly_ref.to_dict(),
            },
            "object": {
                **target_payloads[record_id]["object"],
                "artifact": object_ref.to_dict(),
            },
        }
        target_identities[record_id] = hash_canonical(target_payloads[record_id])

    seed_payload = {
        "compiler_identity": compiler_identity,
        "config_identity": config_identity,
        "lanes": list(selected_lanes),
        "mode_identity": tool_identities[MODE_TOOL_KEY],
        "protocol": "sotn-search-seed-v1",
        "queue_evidence_identity": queue_evidence_identity,
        "run_id": run_id,
        "schema_identity": schema_identity,
        "source_identity": source_identity,
        "subset_identity": subset_identity,
        "target_identities": target_identities,
    }
    if normalized_runtime_id is not None:
        seed_payload["indexed_runtime_id"] = normalized_runtime_id
    run_seed = int(
        hash_canonical(seed_payload)[7:23],
        16,
    )
    manifest = RunManifest(
        run_id=run_id,
        created_at=(now or _now_utc)(),
        parent_run=None,
        queue_record_ids=normalized_ids,
        function_ids=function_ids,
        subset_identity=subset_identity,
        queue_evidence_identity=queue_evidence_identity,
        selected_lanes=selected_lanes,
        source_identity=source_identity,
        target_identities=target_identities,
        compiler_identity=compiler_identity,
        tool_identities=tool_identities,
        config_identity=config_identity,
        schema_identity=schema_identity,
        run_seed=run_seed,
        epoch_size=min(_DEFAULT_EPOCH_SIZE, max(1, task_count)),
        frontier_cap=min(_DEFAULT_FRONTIER_CAP, max(1, task_count)),
        coordinator_budget=Budget("tasks", coordinator_limit, 0),
        lane_budgets={
            lane: Budget("attempts", _DEFAULT_LANE_ATTEMPTS, 0)
            for lane in selected_lanes
        },
        tier_order=TIER_ORDER,
    )

    archive = ContentAddressedArchive(run_root)
    subset_ref = archive.put_json(
        {
            **canonical_subset_payload(normalized_ids),
            "artifact_hash": subset_identity,
        },
        category="subset",
        suffix=".json",
    )
    queue_ref = archive.put_json(
        queue_payload, category="queue-evidence", suffix=".json"
    )
    target_ref_map: dict[str, ArtifactRef] = {}
    for record_id in normalized_ids:
        assembly_bytes, object_bytes = target_bytes[record_id]
        assembly_ref, object_ref = target_artifact_refs[record_id]
        assembly_actual = archive.put_bytes(
            assembly_bytes,
            category="target-assembly",
            suffix=".s",
            media_type="text/x-asm",
        )
        object_actual = archive.put_bytes(
            object_bytes,
            category="target-object",
            suffix=".o",
            media_type="application/octet-stream",
        )
        if assembly_actual != assembly_ref or object_actual != object_ref:
            raise SearchRunFactoryError("archive path is not deterministic")
        target_ref_map[record_id] = archive.put_json(
            target_payloads[record_id], category="target-evidence", suffix=".json"
        )
    target_index_ref = archive.put_json(
        {
            "artifact_type": "sotn-search-target-index",
            "records": [
                {
                    "record_id": record_id,
                    "target_identity": target_identities[record_id],
                    "target_evidence": target_ref_map[record_id].to_dict(),
                }
                for record_id in normalized_ids
            ],
            "schema_version": "1.0.0",
        },
        category="target-index",
        suffix=".json",
    )
    source_ref = archive.put_json(
        source_payload, category="source-evidence", suffix=".json"
    )
    config_ref = archive.put_bytes(
        config_bytes,
        category="config",
        suffix=".toml",
        media_type="application/toml",
    )
    schema_ref = archive.put_bytes(
        schema_bytes,
        category="schema",
        suffix=".json",
        media_type="application/json",
    )
    tools_ref = archive.put_json(
        tool_payload, category="tool-evidence", suffix=".json"
    )
    compiler_ref = archive.put_json(
        compiler_payload, category="compiler-evidence", suffix=".json"
    )
    indexed_runtime_ref = (
        archive.put_json(
            indexed_runtime.to_dict(),
            category="indexed-runtime",
            suffix=".json",
        )
        if indexed_runtime is not None
        else None
    )
    # Preserve exact manifest bytes across a crash between index and publication.
    manifest_intent_ref = archive.put_json(
        manifest.to_dict(), category="manifest-intent", suffix=".json"
    )
    index_payload = {
        "artifact_type": "sotn-search-run-evidence-index",
        "manifest_hash": hash_canonical(manifest.to_dict()),
        "manifest_identity": _manifest_identity(manifest),
        "run_id": run_id,
        "schema_version": "1.0.0",
        "anchor_function": anchor,
        "subset": subset_ref.to_dict(),
        "queue_evidence": queue_ref.to_dict(),
        "target_evidence": {
            record_id: target_ref_map[record_id].to_dict()
            for record_id in normalized_ids
        },
        "target_index": target_index_ref.to_dict(),
        "source": source_ref.to_dict(),
        "config": config_ref.to_dict(),
        "schema": schema_ref.to_dict(),
        "tools": tools_ref.to_dict(),
        "compiler": compiler_ref.to_dict(),
        "manifest_intent": manifest_intent_ref.to_dict(),
    }
    if indexed_runtime_ref is not None:
        index_payload["indexed_runtime"] = indexed_runtime_ref.to_dict()
    index_ref = archive.put_json(index_payload, category="run-index", suffix=".json")
    for reference in (
        subset_ref,
        queue_ref,
        target_index_ref,
        source_ref,
        config_ref,
        schema_ref,
        tools_ref,
        compiler_ref,
        manifest_intent_ref,
        *((indexed_runtime_ref,) if indexed_runtime_ref is not None else ()),
        index_ref,
        *target_ref_map.values(),
    ):
        try:
            archive.verify(reference)
        except Exception as exc:  # noqa: BLE001
            raise SearchRunFactoryError(
                "archived evidence failed durable verification"
            ) from exc

    # This named boundary is after the immutable evidence index and manifest
    # intent are durable, but before the manifest is published.  A caller can
    # inject a one-shot process-loss fault here and retry without rereading the
    # live queue or clock.
    if fault_hook is not None:
        fault_hook("after_durable_index")

    try:
        _publish_manifest(run_root, manifest)
    except RunNameCollision:
        if manifest_path.is_file() and not manifest_path.is_symlink():
            return existing_result(_read_existing_manifest(run_root))
        raise
    return {
        "command": "create-instrumented",
        "ok": True,
        "idempotent": False,
        "run_id": run_id,
        "run_root": str(run_root),
        "anchor_function": anchor,
        "manifest": manifest.to_dict(),
        "evidence_index": index_ref.to_dict(),
    }


def create_instrumented_run(
    name: str,
    record_ids: Sequence[str],
    lanes: Sequence[str],
    *,
    repo: Optional[Path | str] = None,
    queue_reader: Optional[QueueReader] = None,
    compiler_identity_resolver: Optional[IdentityResolver] = None,
    config_path: Optional[Path | str] = None,
    runtime_id: Optional[str] = None,
    now: Optional[Clock] = None,
    fault_hook: Optional[FactoryFaultHook] = None,
) -> dict[str, Any]:
    """Create one bounded run while reserving its repository-wide name.

    The lock is acquired only after logical inputs and task bounds are
    validated, then held through manifest publication.  This closes the race
    where different concurrent subsets could allocate the same run name under
    different canonical function anchors.
    """

    run_id, normalized_ids, selected_lanes = _normalize_inputs(name, record_ids, lanes)
    _normalize_indexed_runtime_id(runtime_id, selected_lanes)
    if len(normalized_ids) * len(selected_lanes) > _MAX_TASKS:
        raise InputRefusal("requested subset exceeds the bounded task budget")
    root_repo = _repo_root(repo)
    expected_root = (
        root_repo / "nonmatchings" / canonical_anchor_function(
            record_id.split(":", 2)[2] for record_id in normalized_ids
        ) / "search-runs" / run_id
    )
    with _creation_lock(root_repo):
        root_was_present = expected_root.exists()
        try:
            return _create_instrumented_run_locked(
                name,
                record_ids,
                lanes,
                repo=root_repo,
                queue_reader=queue_reader,
                compiler_identity_resolver=compiler_identity_resolver,
                config_path=config_path,
                runtime_id=runtime_id,
                now=now,
                fault_hook=fault_hook,
            )
        except BaseException:
            if not root_was_present:
                _remove_empty_unpublished_root(expected_root)
            raise


create_run = create_instrumented_run
create_instrumented = create_instrumented_run


__all__ = [
    "SearchRunFactoryError", "InputRefusal", "EvidenceRefusal",
    "RunNameCollision", "PartialRunRefusal", "canonical_anchor_function",
    "create_instrumented_run", "create_run", "create_instrumented",
]
