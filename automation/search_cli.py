#!/usr/bin/env python3
"""Safe operator boundary for the instrumented search system.

The search core owns manifests, ledgers, archives and recovery.  This module
only validates command input, selects an explicit subset and delegates run
lifecycle operations to those typed APIs.  In particular, it never asks the
queue for a default population.  An omitted subset is an error, while an
explicit ``--records`` with no values is a valid empty subset.

The command output is one canonical JSON object per invocation.  Planning is
read-only: it returns a deterministic selection description and does not
instantiate a coordinator or touch the queue.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent

try:  # package import when called as ``python -m automation.search_cli``
    from .search_coordinator import SearchCoordinator
    from .search_recovery import fork_run as core_fork_run
    from .search_recovery import recover_run
    from .search_types import (
        ArtifactRef,
        LANES,
        RunManifest,
        SearchValidationError,
        SUBSET_ARTIFACT_TYPE,
        SUBSET_SCHEMA_VERSION,
        canonical_json,
        canonical_subset_identity,
        canonical_subset_payload,
        hash_canonical,
        hash_bytes,
        validate_hash,
        validate_id,
        validate_lane,
    )
except ImportError:  # direct invocation from the automation directory
    if str(_REPO) not in sys.path:
        sys.path.insert(0, str(_REPO))
    from automation.search_coordinator import SearchCoordinator  # type: ignore
    from automation.search_recovery import fork_run as core_fork_run  # type: ignore
    from automation.search_recovery import recover_run  # type: ignore
    from automation.search_types import (  # type: ignore
        ArtifactRef,
        LANES,
        RunManifest,
        SearchValidationError,
        SUBSET_ARTIFACT_TYPE,
        SUBSET_SCHEMA_VERSION,
        canonical_json,
        canonical_subset_identity,
        canonical_subset_payload,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_lane,
    )


MANIFEST_FILENAME = "manifest.json"


class SearchCliError(RuntimeError):
    """Base class for deterministic command failures."""

    code = "search_cli_error"


class ArgumentFailure(SearchCliError):
    code = "invalid_arguments"


class PathSafetyError(SearchCliError):
    code = "unsafe_path"


class SubsetArtifactError(SearchCliError):
    code = "invalid_subset_artifact"


class ManifestError(SearchCliError):
    code = "invalid_manifest"


class CoreDependencyError(SearchCliError):
    code = "core_dependency_missing"


class RunInputError(SearchCliError):
    code = "invalid_run"


_DONOR_VERSIONS = ("us", "hd", "pspeu", "saturn")
_FULL_REVISION_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def _normalize_revision_pairs(value: Any) -> Tuple[Tuple[str, str], ...]:
    """Normalize exactly four platform/full-revision pairs.

    The command accepts logical pair values only. Source manifests are resolved
    from the immutable donor archives below the repository, so a caller cannot
    smuggle a checkout path or an alternate argv into publication.
    """

    if isinstance(value, (str, bytes, bytearray)) or value is None:
        raise ArgumentFailure(
            "--revisions must contain exactly four platform/full-revision pairs"
        )
    try:
        groups = tuple(value)
    except (TypeError, ValueError) as exc:
        raise ArgumentFailure(
            "--revisions must contain exactly four platform/full-revision pairs"
        ) from exc
    tokens: list[str] = []
    for group in groups:
        if isinstance(group, (tuple, list)):
            if not group:
                raise ArgumentFailure("--revisions cannot contain an empty group")
            pieces = tuple(group)
        elif isinstance(group, str):
            pieces = (group,)
        else:
            raise ArgumentFailure("--revisions pairs must be strings")
        for piece in pieces:
            if not isinstance(piece, str):
                raise ArgumentFailure("--revisions pairs must be strings")
            for token in piece.split(","):
                token = token.strip()
                if not token:
                    raise ArgumentFailure("--revisions contains an empty pair")
                tokens.append(token)
    if len(tokens) != len(_DONOR_VERSIONS):
        raise ArgumentFailure(
            "--revisions must contain exactly one pair for US, HD, PSPEU, and Saturn"
        )
    parsed: dict[str, str] = {}
    for token in tokens:
        if "=" in token:
            version, revision = token.split("=", 1)
        elif ":" in token:
            version, revision = token.split(":", 1)
        else:
            raise ArgumentFailure(
                "each revision pair must be written platform=full-revision"
            )
        version = version.strip()
        revision = revision.strip()
        if version not in _DONOR_VERSIONS:
            raise ArgumentFailure("revision pair names an unsupported platform")
        if version in parsed:
            raise ArgumentFailure("revision pairs must name each platform once")
        if _FULL_REVISION_RE.fullmatch(revision) is None:
            raise ArgumentFailure(
                "each revision must be a lowercase full 40- or 64-character commit id"
            )
        parsed[version] = revision
    if set(parsed) != set(_DONOR_VERSIONS):
        raise ArgumentFailure(
            "revision pairs must include US, HD, PSPEU, and Saturn exactly once"
        )
    return tuple((version, parsed[version]) for version in _DONOR_VERSIONS)


def _revision_source_references(
    gate_run_id: str,
    pairs: Sequence[Tuple[str, str]],
) -> Tuple[Any, ...]:
    """Resolve each requested revision to one archive-owned donor manifest."""

    try:
        from .search_archive import ContentAddressedArchive
        from .search_donor_index import DonorRevision
        from .search_indexed_runtime import (
            DONOR_SNAPSHOT_ARCHIVE_ROOT,
            DONOR_SNAPSHOT_MANIFEST_PROTOCOL,
            _gate_root,
        )
    except ImportError:
        from automation.search_archive import ContentAddressedArchive  # type: ignore
        from automation.search_donor_index import DonorRevision  # type: ignore
        from automation.search_indexed_runtime import (  # type: ignore
            DONOR_SNAPSHOT_ARCHIVE_ROOT,
            DONOR_SNAPSHOT_MANIFEST_PROTOCOL,
            _gate_root,
        )

    try:
        repo = _REPO.resolve(strict=True)
        gate_root = _gate_root(repo, gate_run_id)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise RunInputError("the explicit integration gate cannot be resolved") from exc

    roots: list[Path] = []
    for candidate in (gate_root, repo / DONOR_SNAPSHOT_ARCHIVE_ROOT):
        try:
            root = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if root.is_symlink() or not root.is_dir():
            continue
        if root not in roots:
            roots.append(root)

    wanted = dict(pairs)
    matches: dict[str, list[Tuple[Path, ArtifactRef]]] = {
        version: [] for version, _revision in pairs
    }
    for root in roots:
        source_root = root / "artifacts" / "sources"
        if source_root.is_symlink():
            raise RunInputError("donor source archive contains a symlink")
        if not source_root.is_dir():
            continue
        archive = ContentAddressedArchive(root)
        try:
            paths = sorted(source_root.rglob("*.json"))
        except OSError as exc:
            raise RunInputError("donor source archive cannot be inspected") from exc
        for path in paths:
            if path.is_symlink() or not path.is_file():
                continue
            try:
                relative = path.relative_to(root).as_posix()
                raw = path.read_bytes()
                document = json.loads(raw.decode("utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(document, Mapping):
                continue
            if document.get("protocol") != DONOR_SNAPSHOT_MANIFEST_PROTOCOL:
                continue
            version = document.get("version")
            revision = document.get("revision")
            if version not in wanted or revision != wanted[version]:
                continue
            reference = ArtifactRef(
                hash_bytes(raw),
                relative,
                "application/json",
                len(raw),
            )
            try:
                if archive.verify(reference) != raw:
                    raise RunInputError("donor source archive bytes changed")
            except (OSError, RuntimeError, SearchValidationError, TypeError, ValueError) as exc:
                raise RunInputError(
                    "requested donor source manifest is missing or corrupt"
                ) from exc
            matches[version].append((root, reference))

    missing = [version for version in _DONOR_VERSIONS if not matches[version]]
    if missing:
        raise RunInputError(
            "no immutable donor source manifest is available for: "
            + ", ".join(missing)
        )
    ambiguous = [version for version in _DONOR_VERSIONS if len(matches[version]) != 1]
    if ambiguous:
        raise RunInputError(
            "requested donor source manifest is ambiguous for: "
            + ", ".join(ambiguous)
        )
    revisions = tuple(
        DonorRevision(
            version=version,
            revision=wanted[version],
            source_artifact=matches[version][0][1],
        )
        for version in _DONOR_VERSIONS
    )
    return revisions


def publish_indexed_runtime(
    gate_run_id: str,
    revisions: Sequence[str] | Sequence[Sequence[str]],
) -> dict[str, Any]:
    """Publish one verified indexed runtime from a gate and four pinned pairs."""

    try:
        from .search_indexed_runtime import publish_indexed_runtime as publish
    except ImportError:
        from automation.search_indexed_runtime import publish_indexed_runtime as publish  # type: ignore
    try:
        gate_run_id = validate_run_id(gate_run_id, "gate_run_id")
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise RunInputError("gate_run_id is invalid") from exc
    pairs = _normalize_revision_pairs(revisions)
    typed_revisions = _revision_source_references(gate_run_id, pairs)
    try:
        generation = publish(gate_run_id, typed_revisions, repo=_REPO)
    except (OSError, RuntimeError, SearchValidationError, TypeError, ValueError) as exc:
        raise RunInputError("indexed runtime publication was refused") from exc
    try:
        runtime_id = validate_hash(generation.runtime_id, "runtime_id")
        document = generation.to_dict()
    except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
        raise RunInputError("indexed runtime publisher returned an invalid generation") from exc
    return {
        "command": "publish-indexed-runtime",
        "ok": True,
        "gate_run_id": gate_run_id,
        "revisions": [f"{version}={revision}" for version, revision in pairs],
        "runtime_id": runtime_id,
        "runtime": document,
    }


def verify_indexed_runtime(runtime_id: str) -> dict[str, Any]:
    """Load and verify one immutable indexed runtime without rescanning."""

    try:
        from .search_indexed_runtime import load_indexed_runtime as load
    except ImportError:
        from automation.search_indexed_runtime import load_indexed_runtime as load  # type: ignore
    try:
        runtime_id = validate_hash(runtime_id, "runtime_id")
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise RunInputError("runtime_id is invalid") from exc
    try:
        generation = load(runtime_id, repo=_REPO)
    except (OSError, RuntimeError, SearchValidationError, TypeError, ValueError) as exc:
        raise RunInputError("indexed runtime verification was refused") from exc
    try:
        if validate_hash(generation.runtime_id, "runtime_id") != runtime_id:
            raise RunInputError("indexed runtime identity differs from request")
        document = generation.to_dict()
    except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
        raise RunInputError("indexed runtime returned an invalid generation") from exc
    return {
        "command": "verify-indexed-runtime",
        "ok": True,
        "runtime_id": runtime_id,
        "runtime": document,
        "verdict": "valid",
    }


@dataclass(frozen=True)
class SubsetSelection:
    """The explicit selection accepted by ``plan``.

    This is an operator result, not a second source of run authority.  A run
    still consumes a typed :class:`RunManifest`, whose immutable fields bind
    the selected record IDs and lanes.
    """

    record_ids: Tuple[str, ...]
    lanes: Tuple[str, ...]
    subset_identity: str
    input_kind: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": "plan",
            "input_kind": self.input_kind,
            "lanes": list(self.lanes),
            "lane_count": len(self.lanes),
            "read_only": True,
            "record_count": len(self.record_ids),
            "record_ids": list(self.record_ids),
            "subset_identity": self.subset_identity,
        }


def subset_artifact(record_ids: Iterable[str]) -> dict[str, Any]:
    """Return the canonical, hash-bound saved-subset representation."""

    normalized = _normalize_ids(tuple(record_ids), label="record IDs")
    payload = canonical_subset_payload(normalized)
    return {**payload, "artifact_hash": canonical_subset_identity(normalized)}


def subset_artifact_text(record_ids: Iterable[str]) -> str:
    """Serialize a saved subset artifact without timestamps or paths."""

    return canonical_json(subset_artifact(record_ids)) + "\n"


def _has_parent_traversal(value: Path) -> bool:
    return any(part == ".." for part in value.parts)


def _lexical_absolute(value: str | os.PathLike[str], *, base: Optional[Path] = None) -> Path:
    try:
        raw = Path(value)
    except TypeError as exc:
        raise PathSafetyError("path is not valid") from exc
    if raw == Path(""):
        raise PathSafetyError("path is empty")
    if _has_parent_traversal(raw):
        raise PathSafetyError("path traversal is refused")
    if raw.is_absolute():
        return Path(os.path.abspath(os.fspath(raw)))
    anchor = (base or Path.cwd()).resolve()
    return Path(os.path.abspath(os.fspath(anchor / raw)))


def _assert_no_symlink_components(path: Path) -> None:
    """Reject symlink components, including a symlink at the final path."""

    current = Path(path.anchor)
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current = current / part
        try:
            if current.is_symlink():
                raise PathSafetyError("symlink path component is refused")
        except OSError as exc:
            raise PathSafetyError("path could not be inspected") from exc


def _safe_existing_file(value: str | os.PathLike[str], *, label: str) -> Path:
    path = _lexical_absolute(value)
    _assert_no_symlink_components(path)
    try:
        if not path.is_file():
            raise PathSafetyError(f"{label} must be a regular file")
    except OSError as exc:
        raise PathSafetyError(f"{label} could not be inspected") from exc
    return path


def _safe_run_root(value: str | os.PathLike[str], *, allow_missing: bool = False) -> Path:
    path = _lexical_absolute(value)
    if path.name in ("", ".", ".."):
        raise PathSafetyError("run root is invalid")
    if path.exists() and not path.is_dir():
        raise PathSafetyError("run root must be a directory")
    # Inspect existing ancestors before a caller can hand the coordinator a
    # symlinked directory.  Missing leaves are allowed only for ``run`` and
    # are created by the coordinator below this exact lexical root.
    _assert_no_symlink_components(path)
    if not path.exists() and not allow_missing:
        raise PathSafetyError("run root does not exist")
    return path


def _audit_run_root(root: Path) -> None:
    """Reject symlinked output entries before or after core operations."""

    _assert_no_symlink_components(root)
    if not root.exists():
        return
    try:
        for current, directories, files in os.walk(root, followlinks=False):
            for name in tuple(directories) + tuple(files):
                candidate = Path(current) / name
                if candidate.is_symlink():
                    raise PathSafetyError("run output contains a symlink")
    except OSError as exc:
        raise PathSafetyError("run output could not be inspected") from exc


def _normalize_ids(values: Sequence[str], *, label: str) -> Tuple[str, ...]:
    normalized = []
    for value in values:
        if not isinstance(value, str):
            raise SubsetArtifactError(f"{label} must contain strings")
        try:
            normalized.append(validate_id(value.strip(), label.rstrip("s")))
        except (SearchValidationError, ValueError) as exc:
            raise SubsetArtifactError(f"invalid {label.lower()} entry") from exc
    if len(set(normalized)) != len(normalized):
        raise SubsetArtifactError(f"duplicate {label.lower()} are not allowed")
    return tuple(sorted(normalized))


def _flatten_option_groups(
    groups: Optional[Sequence[Sequence[str]]],
    *,
    label: str,
    allow_explicit_empty: bool,
) -> Optional[Tuple[str, ...]]:
    if groups is None:
        return None
    values: list[str] = []
    saw_empty = False
    for group in groups:
        if not group:
            saw_empty = True
            continue
        for raw in group:
            if not isinstance(raw, str):
                raise ArgumentFailure(f"{label} values must be strings")
            pieces = raw.split(",")
            for piece in pieces:
                piece = piece.strip()
                if not piece:
                    saw_empty = True
                else:
                    values.append(piece)
    if saw_empty and values:
        raise ArgumentFailure(f"empty and nonempty {label.lower()} cannot be mixed")
    if saw_empty:
        if not allow_explicit_empty:
            raise ArgumentFailure(f"at least one {label.lower()} is required")
        return ()
    return _normalize_ids(values, label=label)


def _normalize_lanes(groups: Optional[Sequence[Sequence[str]]]) -> Tuple[str, ...]:
    if groups is None:
        raise ArgumentFailure("--lanes is required and must be explicit")
    try:
        flattened = _flatten_option_groups(
            groups,
            label="lanes",
            allow_explicit_empty=False,
        )
    except SubsetArtifactError as exc:
        raise ArgumentFailure(str(exc)) from exc
    assert flattened is not None
    unknown = [lane for lane in flattened if lane not in LANES]
    if unknown:
        raise ArgumentFailure("unknown lane: " + unknown[0])
    try:
        for lane in flattened:
            validate_lane(lane)
    except (SearchValidationError, ValueError) as exc:
        raise ArgumentFailure("invalid lane") from exc
    # Lane order is part of deterministic planning.  It is the canonical
    # schema order, not argv order, while duplicate rejection remains explicit.
    if len(set(flattened)) != len(flattened):
        raise ArgumentFailure("duplicate lanes are not allowed")
    return tuple(sorted(flattened, key=LANES.index))


def _load_subset_artifact(
    value: str | os.PathLike[str],
    *,
    expected_hash: Optional[str] = None,
) -> Tuple[Tuple[str, ...], str]:
    path = _safe_existing_file(value, label="subset artifact")
    try:
        raw = path.read_text(encoding="utf-8")
        document = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SubsetArtifactError("subset artifact is not valid UTF-8 JSON") from exc
    if not isinstance(document, Mapping):
        raise SubsetArtifactError("subset artifact must be a JSON object")
    allowed = {"artifact_hash", "artifact_type", "record_ids", "schema_version"}
    unknown = set(document).difference(allowed)
    if unknown:
        raise SubsetArtifactError("subset artifact has unknown fields")
    if document.get("artifact_type") != SUBSET_ARTIFACT_TYPE:
        raise SubsetArtifactError("subset artifact type is invalid")
    if document.get("schema_version") != SUBSET_SCHEMA_VERSION:
        raise SubsetArtifactError("subset artifact schema version is invalid")
    if "artifact_hash" not in document or "record_ids" not in document:
        raise SubsetArtifactError("subset artifact needs artifact_hash and record_ids")
    record_ids = document["record_ids"]
    if not isinstance(record_ids, list):
        raise SubsetArtifactError("subset artifact record_ids must be an array")
    normalized = _normalize_ids(record_ids, label="record IDs")
    payload = canonical_subset_payload(normalized)
    declared = document["artifact_hash"]
    try:
        validate_hash(declared, "artifact_hash")
    except (SearchValidationError, ValueError) as exc:
        raise SubsetArtifactError("subset artifact hash is invalid") from exc
    calculated = canonical_subset_identity(normalized)
    if declared != calculated:
        raise SubsetArtifactError("subset artifact content changed")
    if expected_hash is not None:
        try:
            validate_hash(expected_hash, "expected subset hash")
        except (SearchValidationError, ValueError) as exc:
            raise ArgumentFailure("expected subset hash is invalid") from exc
        if expected_hash != declared:
            raise SubsetArtifactError("subset artifact hash differs from the bound identity")
    return normalized, declared


def plan_selection(
    *,
    record_groups: Optional[Sequence[Sequence[str]]] = None,
    subset_path: Optional[str | os.PathLike[str]] = None,
    subset_hash: Optional[str] = None,
    lane_groups: Optional[Sequence[Sequence[str]]] = None,
) -> SubsetSelection:
    """Validate one explicit subset and lane selection without writing state."""

    if (record_groups is None) == (subset_path is None):
        raise ArgumentFailure("provide exactly one of --records or --subset")
    if subset_path is not None:
        records, identity = _load_subset_artifact(subset_path, expected_hash=subset_hash)
        input_kind = "saved_artifact"
    else:
        records = _flatten_option_groups(
            record_groups,
            label="record IDs",
            allow_explicit_empty=True,
        )
        assert records is not None
        if subset_hash is not None:
            raise ArgumentFailure("--subset-hash requires --subset")
        identity = canonical_subset_identity(records)
        input_kind = "explicit"
    lanes = _normalize_lanes(lane_groups)
    return SubsetSelection(records, lanes, identity, input_kind)


def create_instrumented_run(
    name: str,
    record_ids: Sequence[str],
    lanes: Sequence[str],
    *,
    runtime_id: Optional[str] = None,
) -> dict[str, Any]:
    """Create one bounded canonical instrumented run from exact todo IDs."""

    try:
        from .search_run_factory import create_instrumented_run as create_run
    except ImportError:  # direct invocation from the automation directory
        from automation.search_run_factory import create_instrumented_run as create_run  # type: ignore
    try:
        return create_run(name, record_ids, lanes, runtime_id=runtime_id)
    except RuntimeError as exc:
        raise RunInputError(str(exc) or "run creation refused") from exc


def _manifest_field_names() -> set[str]:
    try:
        return {field.name for field in dataclasses.fields(RunManifest)}
    except TypeError as exc:
        raise CoreDependencyError("RunManifest is not a dataclass value type") from exc


def _require_selected_lanes(manifest: RunManifest) -> Tuple[str, ...]:
    fields = _manifest_field_names()
    if "selected_lanes" not in fields:
        raise CoreDependencyError(
            "RunManifest.selected_lanes is required; the core lane-binding API is not available"
        )
    try:
        selected = tuple(getattr(manifest, "selected_lanes"))
    except (AttributeError, TypeError) as exc:
        raise ManifestError("manifest selected_lanes is invalid") from exc
    if not selected and getattr(manifest, "queue_record_ids", ()):
        raise ManifestError("manifest selected_lanes must be explicit for a nonempty subset")
    if len(set(selected)) != len(selected):
        raise ManifestError("manifest selected_lanes contain duplicates")
    for lane in selected:
        if lane not in LANES:
            raise ManifestError("manifest contains an unknown selected lane")
    fields = _manifest_field_names()
    if "subset_identity" not in fields:
        raise CoreDependencyError(
            "RunManifest.subset_identity is required; the core subset-binding API is not available"
        )
    try:
        declared_identity = getattr(manifest, "subset_identity")
        expected_identity = canonical_subset_identity(
            tuple(manifest.queue_record_ids)
        )
        validate_hash(declared_identity, "subset_identity")
    except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
        raise ManifestError("manifest subset_identity is invalid") from exc
    if declared_identity != expected_identity:
        raise ManifestError("manifest subset_identity differs from its frozen record subset")
    if "queue_evidence_identity" not in fields:
        raise CoreDependencyError(
            "RunManifest.queue_evidence_identity is required; the core queue-evidence API is not available"
        )
    try:
        validate_hash(
            getattr(manifest, "queue_evidence_identity"),
            "queue_evidence_identity",
        )
    except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
        raise ManifestError("manifest queue_evidence_identity is invalid") from exc
    return selected


def _validate_manifest_value(document: Any) -> RunManifest:
    if not isinstance(document, Mapping):
        raise ManifestError("manifest must be a JSON object")
    try:
        manifest = RunManifest.from_dict(document)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise ManifestError("manifest does not conform to the typed schema") from exc
    _require_selected_lanes(manifest)
    try:
        queue_ids = tuple(manifest.queue_record_ids)
    except (AttributeError, TypeError) as exc:
        raise ManifestError("manifest has no explicit queue subset") from exc
    if len(set(queue_ids)) != len(queue_ids):
        raise ManifestError("manifest queue subset contains duplicates")
    # Empty is intentionally retained as a valid explicit no-op once the core
    # API supports it.  Never replace it with a queue status query.
    return manifest


def _load_manifest_file(value: str | os.PathLike[str]) -> Tuple[Path, RunManifest]:
    path = _safe_existing_file(value, label="manifest")
    if path.name != MANIFEST_FILENAME:
        raise ManifestError("manifest path must name manifest.json")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError("manifest is not valid UTF-8 JSON") from exc
    return path, _validate_manifest_value(document)


def _run_root_from_manifest(value: str | os.PathLike[str]) -> Tuple[Path, RunManifest]:
    path, manifest = _load_manifest_file(value)
    root = _safe_run_root(path.parent)
    _audit_run_root(root)
    return root, manifest


def _state_ids(state: Any, attribute: str) -> list[str]:
    value = getattr(state, attribute, ())
    return sorted(str(item) for item in value)


def _manifest_summary(manifest: RunManifest) -> dict[str, Any]:
    lanes = _require_selected_lanes(manifest)
    return {
        "function_ids": list(sorted(manifest.function_ids)),
        "lanes": list(lanes),
        "record_ids": list(sorted(manifest.queue_record_ids)),
        "run_id": manifest.run_id,
        "subset_identity": manifest.subset_identity,
        "queue_evidence_identity": manifest.queue_evidence_identity,
    }


def run_manifest(value: str | os.PathLike[str]) -> dict[str, Any]:
    """Initialize or reopen one manifest-owned run.

    Task execution remains the coordinator's responsibility.  This boundary
    deliberately performs no implicit lane scheduling: selected lanes and the
    exact record subset are validated before the coordinator is constructed.
    """

    root, manifest = _run_root_from_manifest(value)
    try:
        coordinator = SearchCoordinator(root, manifest)
    except (SearchValidationError, CoreDependencyError, TypeError, ValueError, RuntimeError) as exc:
        if isinstance(exc, SearchCliError):
            raise
        raise RunInputError("coordinator refused the manifest") from exc
    _audit_run_root(root)
    state = coordinator.state_dict()
    return {
        "command": "run",
        "ok": True,
        "run_root": str(root),
        "manifest": _manifest_summary(manifest),
        "state": state,
    }


def resume_run(value: str | os.PathLike[str]) -> dict[str, Any]:
    """Recover and reissue legacy tasks with their original identity.

    Instrumented runs have a lease-owned stop/resume transition and an oracle
    landing callback.  This generic command cannot safely provide either, so
    it refuses that mode instead of reporting a resume that leaves the durable
    run stopped.
    """

    root = _safe_run_root(value)
    _audit_run_root(root)
    try:
        state = recover_run(root)
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        raise RunInputError("run recovery refused the run") from exc
    _require_selected_lanes(state.manifest)
    try:
        from .search_supervisor import INSTRUMENTED_MODE, MODE_TOOL_KEY, mode_identity
    except ImportError:  # direct invocation from the automation directory
        from automation.search_supervisor import (  # type: ignore
            INSTRUMENTED_MODE,
            MODE_TOOL_KEY,
            mode_identity,
        )
    if state.manifest.tool_identities.get(MODE_TOOL_KEY) == mode_identity(INSTRUMENTED_MODE):
        raise RunInputError(
            "instrumented runs must be resumed through "
            "permuter_supervisor.py --resume --mode instrumented --manifest"
        )
    if state.stopped is not None and not state.stopped.resumable:
        raise RunInputError("run stop is not resumable")
    reissued = tuple(state.reissue_tasks())
    original = state.tasks
    for task in reissued:
        prior = original.get(task.task_id)
        if prior is None or task != dataclasses.replace(prior, state="scheduled"):
            raise RunInputError("recovery changed task identity")
    return {
        "command": "resume",
        "ok": True,
        "run_id": state.manifest.run_id,
        "run_root": str(root),
        "reissued_tasks": [task.to_dict() for task in reissued],
        "pending_task_ids": sorted(task.task_id for task in state.incomplete_tasks),
    }


def status_run(value: str | os.PathLike[str]) -> dict[str, Any]:
    root = _safe_run_root(value)
    _audit_run_root(root)
    try:
        state = recover_run(root)
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        raise RunInputError("run recovery refused the run") from exc
    _verify_factory_archive_only(root, state.manifest)
    _require_selected_lanes(state.manifest)
    stopped = state.stopped.to_dict() if state.stopped is not None else None
    return {
        "command": "status",
        "ok": True,
        "run_id": state.manifest.run_id,
        "run_root": str(root),
        "scheduled_task_ids": _state_ids(state, "scheduled_task_ids"),
        "completed_task_ids": _state_ids(state, "completed_task_ids"),
        "incomplete_task_ids": sorted(task.task_id for task in state.incomplete_tasks),
        "last_sequence": state.last_sequence,
        "last_event_hash": state.last_event_hash,
        "stopped": stopped,
    }


def _verify_factory_archive_only(root: Path, manifest: RunManifest) -> None:
    """Validate factory evidence without measuring mutable execution inputs."""
    try:
        from .search_run_factory import verify_factory_archive
    except ImportError:  # direct invocation from the automation directory
        from automation.search_run_factory import verify_factory_archive  # type: ignore
    try:
        verify_factory_archive(root, manifest)
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        raise RunInputError("factory archive verification failed") from exc


def verify_ledger(value: str | os.PathLike[str]) -> dict[str, Any]:
    root = _safe_run_root(value)
    _audit_run_root(root)
    try:
        state = recover_run(root)
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        raise RunInputError("ledger verification failed") from exc
    _verify_factory_archive_only(root, state.manifest)
    _require_selected_lanes(state.manifest)
    return {
        "command": "verify-ledger",
        "ok": True,
        "run_id": state.manifest.run_id,
        "run_root": str(root),
        "event_count": len(state.events),
        "last_sequence": state.last_sequence,
        "last_event_hash": state.last_event_hash,
        "verdict": "valid",
    }


def stop_run(value: str | os.PathLike[str]) -> dict[str, Any]:
    root = _safe_run_root(value)
    _audit_run_root(root)
    try:
        state = recover_run(root)
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        raise RunInputError("run recovery refused the run") from exc
    _verify_factory_archive_only(root, state.manifest)
    manifest = _validate_manifest_value(state.manifest.to_dict())
    try:
        from .search_supervisor import (
            INSTRUMENTED_MODE,
            MODE_TOOL_KEY,
            mode_identity,
            request_instrumented_stop,
        )
    except ImportError:  # direct invocation from the automation directory
        from automation.search_supervisor import (  # type: ignore
            INSTRUMENTED_MODE,
            MODE_TOOL_KEY,
            mode_identity,
            request_instrumented_stop,
        )
    if manifest.tool_identities.get(MODE_TOOL_KEY) == mode_identity(INSTRUMENTED_MODE):
        return request_instrumented_stop(root / MANIFEST_FILENAME)
    try:
        coordinator = SearchCoordinator(root, manifest)
        event = coordinator.stop(reason="graceful_stop")
    except (SearchValidationError, TypeError, ValueError, RuntimeError) as exc:
        raise RunInputError("coordinator refused the stop") from exc
    _audit_run_root(root)
    return {
        "command": "stop",
        "ok": True,
        "run_id": manifest.run_id,
        "run_root": str(root),
        "receipt": event.to_dict(),
    }


def _read_fork_config(value: str | os.PathLike[str]) -> Tuple[RunManifest, Optional[str]]:
    path = _safe_existing_file(value, label="fork config")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError("fork config is not valid UTF-8 JSON") from exc
    if not isinstance(document, Mapping):
        raise ManifestError("fork config must be a JSON object")
    fields = _manifest_field_names()
    unknown = set(document).difference(fields | {"destination_root"})
    if unknown:
        raise ManifestError("fork config has unknown fields")
    raw_manifest = {key: document[key] for key in fields if key in document}
    destination = document.get("destination_root")
    manifest = _validate_manifest_value(raw_manifest)
    if destination is not None and not isinstance(destination, str):
        raise ManifestError("destination_root must be a string")
    return manifest, destination


def fork_run(value: str | os.PathLike[str], config: str | os.PathLike[str]) -> dict[str, Any]:
    source_root = _safe_run_root(value)
    _audit_run_root(source_root)
    try:
        source_state = recover_run(source_root)
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        raise RunInputError("source run recovery refused the fork") from exc
    manifest, configured_destination = _read_fork_config(config)
    if manifest.run_id == source_state.manifest.run_id:
        raise ManifestError("fork child run_id must differ from the parent run")
    if configured_destination is None:
        # Derive a path from the immutable child identity without embedding an
        # arbitrary run id in a filesystem component.  The result is stable
        # for one source/config pair and remains beside the source run.
        child_key = hash_canonical(
            {"parent": source_state.manifest.run_id, "child": manifest.run_id}
        )[7:19]
        destination = source_root.parent / f"{source_root.name}-fork-{child_key}"
    else:
        destination = _safe_run_root(configured_destination, allow_missing=True)
    if destination == source_root:
        raise PathSafetyError("fork destination must differ from source run")
    if destination.exists():
        _audit_run_root(destination)
        try:
            if any(destination.iterdir()):
                raise PathSafetyError("fork destination must be empty")
        except OSError as exc:
            raise PathSafetyError("fork destination could not be inspected") from exc
    try:
        child = core_fork_run(source_root, destination, manifest=manifest)
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        raise RunInputError("core fork refused the configuration") from exc
    _audit_run_root(destination)
    return {
        "command": "fork",
        "ok": True,
        "parent_run_id": source_state.manifest.run_id,
        "parent_last_sequence": source_state.last_sequence,
        "run_id": child.manifest.run_id,
        "run_root": str(destination),
    }


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # pragma: no cover - exercised via main
        raise ArgumentFailure(message)


def build_parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(prog="search_cli.py")
    commands = parser.add_subparsers(dest="command", required=True)

    plan = commands.add_parser("plan", help="plan one explicit subset")
    plan.add_argument(
        "--records",
        action="append",
        nargs="*",
        help="explicit record IDs, optionally comma-separated; no values means an explicit empty subset",
    )
    plan.add_argument(
        "--subset",
        "--subset-artifact",
        dest="subset_path",
        help="path to a hash-bound saved subset artifact",
    )
    plan.add_argument("--subset-hash", help="expected hash binding for --subset")
    plan.add_argument(
        "--lanes",
        action="append",
        nargs="+",
        required=True,
        help="explicit lane names, optionally comma-separated",
    )

    create = commands.add_parser("create", help="create one canonical instrumented run")
    create.add_argument("--name", required=True)
    create.add_argument("--records", action="append", nargs="+", required=True)
    create.add_argument("--lanes", action="append", nargs="+", required=True)
    create.add_argument(
        "--runtime-id",
        help="exact indexed runtime identity required by indexed lanes",
    )

    run = commands.add_parser("run", help="initialize a manifest-owned run")
    run.add_argument("--manifest", required=True)

    for name, function in (
        ("resume", "resume"),
        ("stop", "stop"),
        ("status", "status"),
        ("verify-ledger", "verify-ledger"),
    ):
        command = commands.add_parser(name, help=f"{function} a run")
        command.add_argument("--run", required=True)

    fork = commands.add_parser("fork", help="fork one immutable run")
    fork.add_argument("--run", required=True)
    fork.add_argument("--config", required=True)

    publish = commands.add_parser(
        "publish-indexed-runtime",
        help="publish one immutable indexed runtime",
    )
    publish.add_argument("--gate-run-id", required=True)
    publish.add_argument(
        "--revisions",
        action="append",
        nargs="+",
        required=True,
        help="exactly four platform=full-revision pairs",
    )

    verify = commands.add_parser(
        "verify-indexed-runtime",
        help="verify one immutable indexed runtime",
    )
    verify.add_argument("--runtime-id", required=True)
    return parser


def _dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "plan":
        return plan_selection(
            record_groups=args.records,
            subset_path=args.subset_path,
            subset_hash=args.subset_hash,
            lane_groups=args.lanes,
        ).to_dict()
    if args.command == "create":
        records = _flatten_option_groups(
            args.records, label="record IDs", allow_explicit_empty=False
        )
        lanes = _flatten_option_groups(
            args.lanes, label="lanes", allow_explicit_empty=False
        )
        assert records is not None and lanes is not None
        return create_instrumented_run(
            args.name,
            records,
            lanes,
            runtime_id=args.runtime_id,
        )
    if args.command == "run":
        return run_manifest(args.manifest)
    if args.command == "resume":
        return resume_run(args.run)
    if args.command == "stop":
        return stop_run(args.run)
    if args.command == "status":
        return status_run(args.run)
    if args.command == "verify-ledger":
        return verify_ledger(args.run)
    if args.command == "fork":
        return fork_run(args.run, args.config)
    if args.command == "publish-indexed-runtime":
        return publish_indexed_runtime(args.gate_run_id, args.revisions)
    if args.command == "verify-indexed-runtime":
        return verify_indexed_runtime(args.runtime_id)
    raise ArgumentFailure("unknown command")


def _error_document(error: SearchCliError) -> dict[str, Any]:
    return {
        "error": {"code": error.code, "message": str(error)},
        "ok": False,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        result = _dispatch(args)
    except SearchCliError as exc:
        print(canonical_json(_error_document(exc)))
        return 2
    except (OSError, SearchValidationError, TypeError, ValueError, RuntimeError) as exc:
        # Core implementations intentionally expose typed runtime errors.  Do
        # not leak a traceback or retry with a different call signature.
        error = SearchCliError(str(exc) or "operation failed")
        print(canonical_json(_error_document(error)))
        return 2
    print(canonical_json(result))
    return 0


__all__ = [
    "SUBSET_ARTIFACT_TYPE",
    "SUBSET_SCHEMA_VERSION",
    "SearchCliError",
    "ArgumentFailure",
    "PathSafetyError",
    "SubsetArtifactError",
    "ManifestError",
    "CoreDependencyError",
    "RunInputError",
    "SubsetSelection",
    "subset_artifact",
    "subset_artifact_text",
    "plan_selection",
    "create_instrumented_run",
    "run_manifest",
    "resume_run",
    "status_run",
    "verify_ledger",
    "stop_run",
    "fork_run",
    "publish_indexed_runtime",
    "verify_indexed_runtime",
    "_normalize_revision_pairs",
    "build_parser",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
