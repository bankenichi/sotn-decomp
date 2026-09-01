"""Immutable publication and loading for the indexed search runtime.

The runtime is the one durable boundary shared by the factory and the later
indexed-lane supervisor.  Publication consumes an explicitly named completed
integration gate and exactly one pinned revision for each supported donor
version.  It snapshots the gate, builds the real corpus and donor index, and
publishes one self-verifying content-addressed generation.  Loading and
verification only read those archived bytes; they never invoke a donor scan.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:  # package imports
    from .compiler_idioms import (
        CompilerIdiomError,
        DraftLandedObservation,
        validate_commit_identity,
    )
    from .search_archive import (
        ArchiveError,
        ArtifactRef,
        ContentAddressedArchive,
    )
    from .search_donor_index import (
        DONOR_VERSIONS,
        DonorIndexError,
        DonorIndexGeneration,
        DonorRevision,
        build_donor_index,
        revision_set_identity,
    )
    from .search_evidence_corpus import (
        AbsenceMaskingClaim,
        CorpusEvidence,
        CorpusGeneration,
        EvidenceIdentityMismatch,
        PromotionAccepted,
        PromotionRefused,
        _make_corpus_evidence,
        build_corpus_generation,
        collect_recurring_first_divergence,
        make_lesson_citation,
        make_scorer_taxonomy,
        promote_draft_landed,
    )
    from .search_ledger import AppendOnlyLedger
    from .search_patterns import (
        CompletedLineageContext,
        CompletedLineageDiagnostic,
        PatternInputError,
        SearchPatternReport,
        load_completed_lineage_contexts,
        load_report_artifact,
        mine_completed_lineages,
    )
    from .search_supervisor import (
        EVALUATOR_TOOL_KEY,
        IntegrationGateError,
        IntegrationGateReceipt,
        validate_integration_gate,
    )
    from .search_types import (
        EvaluationEvent,
        RunManifest,
        SearchValidationError,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_relative_path,
        validate_hash,
        validate_run_id,
    )
except ImportError:  # direct invocation from the automation directory
    from automation.compiler_idioms import (  # type: ignore
        CompilerIdiomError,
        DraftLandedObservation,
        validate_commit_identity,
    )
    from automation.search_archive import (  # type: ignore
        ArchiveError,
        ArtifactRef,
        ContentAddressedArchive,
    )
    from automation.search_donor_index import (  # type: ignore
        DONOR_VERSIONS,
        DonorIndexError,
        DonorIndexGeneration,
        DonorRevision,
        build_donor_index,
        revision_set_identity,
    )
    from automation.search_evidence_corpus import (  # type: ignore
        AbsenceMaskingClaim,
        CorpusEvidence,
        CorpusGeneration,
        EvidenceIdentityMismatch,
        PromotionAccepted,
        PromotionRefused,
        _make_corpus_evidence,
        build_corpus_generation,
        collect_recurring_first_divergence,
        make_lesson_citation,
        make_scorer_taxonomy,
        promote_draft_landed,
    )
    from automation.search_ledger import AppendOnlyLedger  # type: ignore
    from automation.search_patterns import (  # type: ignore
        CompletedLineageContext,
        CompletedLineageDiagnostic,
        PatternInputError,
        SearchPatternReport,
        load_completed_lineage_contexts,
        load_report_artifact,
        mine_completed_lineages,
    )
    from automation.search_supervisor import (  # type: ignore
        EVALUATOR_TOOL_KEY,
        IntegrationGateError,
        IntegrationGateReceipt,
        validate_integration_gate,
    )
    from automation.search_types import (  # type: ignore
        EvaluationEvent,
        RunManifest,
        SearchValidationError,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_relative_path,
        validate_hash,
        validate_run_id,
    )


INDEXED_RUNTIME_PROTOCOL = "sotn-indexed-runtime-v1"
INDEXED_RUNTIME_INTENT_PROTOCOL = "sotn-indexed-runtime-intent-v1"
INDEXED_RUNTIME_ROOT = Path("nonmatchings/search-evidence/indexed-runtimes")
# Completed integration gates are immutable historical evidence.  New donor
# snapshots therefore have their own canonical archive, so publishing them
# never edits a gate run that predates the snapshot protocol.
DONOR_SNAPSHOT_ARCHIVE_ROOT = Path("nonmatchings/search-evidence/donor-snapshots")
INDEXED_RUNTIME_GENERATION_FILENAME = "generation.json"
INDEXED_RUNTIME_INTENT_FILENAME = "intent.json"
SCANNER_INTERFACE = "automation.search_donor_scan.scan_repository_revision"
# Keep this value aligned with the scanner-owned manifest protocol.  The
# runtime is only the publication boundary; it must not invent a second
# snapshot format that the scanner cannot validate.
DONOR_SNAPSHOT_MANIFEST_PROTOCOL = "sotn-donor-snapshot-manifest-v1"
DONOR_SNAPSHOT_MANIFEST_FILENAME = ".sotn-donor-snapshot.json"
DONOR_SNAPSHOT_FILE_KINDS = ("assembly", "config", "source")
_STAGING_PREFIX = ".indexed-runtime-stage-"


class IndexedRuntimeError(RuntimeError):
    """Base class for indexed-runtime publication and loading failures."""


class IndexedRuntimeInputError(IndexedRuntimeError):
    """An explicit runtime input is missing, stale, or malformed."""


class IndexedRuntimeArtifactError(IndexedRuntimeError):
    """A runtime, gate, corpus, or index artifact is missing or corrupt."""


class IndexedRuntimeIdentityMismatch(IndexedRuntimeError):
    """A content-addressed runtime identity disagrees with its bytes."""


class IndexedRuntimeCollision(IndexedRuntimeError):
    """An immutable runtime path contains a different publication."""


class IndexedRuntimePartialPublication(IndexedRuntimeError):
    """A publication cannot be resumed from its durable intent and stage."""


class IndexedRuntimeScannerError(IndexedRuntimeError):
    """The Task 1 scanner is unavailable or returned an invalid result."""


# Short aliases keep the failure surface discoverable to connector callers.
RuntimeInputError = IndexedRuntimeInputError
RuntimeArtifactError = IndexedRuntimeArtifactError
RuntimeIdentityMismatch = IndexedRuntimeIdentityMismatch
RuntimeCollision = IndexedRuntimeCollision
PartialPublication = IndexedRuntimePartialPublication


@dataclass(frozen=True)
class DonorSnapshotFile:
    """Typed byte input for the separate immutable donor snapshot archive."""

    path: str
    kind: str
    data: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path:
            raise IndexedRuntimeInputError("donor snapshot file path is invalid")
        if not isinstance(self.kind, str) or self.kind not in DONOR_SNAPSHOT_FILE_KINDS:
            raise IndexedRuntimeInputError("donor snapshot file kind is invalid")
        if not isinstance(self.data, bytes):
            raise IndexedRuntimeInputError("donor snapshot file bytes are not typed")


@dataclass(frozen=True)
class DonorSnapshot:
    """One complete version snapshot to publish outside a completed gate."""

    version: str
    revision: str
    files: tuple[DonorSnapshotFile, ...]

    def __post_init__(self) -> None:
        if self.version not in DONOR_VERSIONS:
            raise IndexedRuntimeInputError("unsupported donor snapshot version")
        try:
            revision = validate_commit_identity(self.revision, "donor snapshot revision")
        except (CompilerIdiomError, TypeError, ValueError) as exc:
            raise IndexedRuntimeInputError(
                "donor snapshot revision is not a full commit identity"
            ) from exc
        object.__setattr__(self, "revision", revision)
        try:
            files = tuple(self.files)
        except (TypeError, ValueError) as exc:
            raise IndexedRuntimeInputError("donor snapshot files are invalid") from exc
        if not files or any(not isinstance(item, DonorSnapshotFile) for item in files):
            raise IndexedRuntimeInputError("donor snapshot files must be typed records")
        paths = [item.path for item in files]
        if paths != sorted(paths) or len(set(paths)) != len(paths):
            raise IndexedRuntimeInputError(
                "donor snapshot files must be sorted and unique"
            )
        if {item.kind for item in files} != set(DONOR_SNAPSHOT_FILE_KINDS):
            raise IndexedRuntimeInputError(
                "donor snapshot must bind config, source, and assembly files"
            )
        object.__setattr__(self, "files", files)


def _hash(value: Any, label: str) -> str:
    try:
        validate_hash(value, label)
    except SearchValidationError as exc:
        raise IndexedRuntimeInputError(str(exc)) from exc
    return value


def _repo_root(repo: Any) -> Path:
    if not isinstance(repo, (str, os.PathLike)):
        raise IndexedRuntimeInputError("repo must be an explicit repository path")
    try:
        root = Path(repo).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise IndexedRuntimeInputError("repo cannot be resolved") from exc
    if not root.is_dir():
        raise IndexedRuntimeInputError("repo must be a directory")
    return root


def _contained(path: Path, root: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(root.resolve(strict=False))
    except (OSError, RuntimeError, ValueError) as exc:
        raise IndexedRuntimeInputError(label + " escapes its repository root") from exc
    return resolved


def _runtime_global_root(repo: Path, *, create: bool) -> Path:
    root = _contained(repo / INDEXED_RUNTIME_ROOT, repo, "runtime archive")
    if create:
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise IndexedRuntimeArtifactError(
                "runtime archive root cannot be created"
            ) from exc
    return root


def _runtime_directory(repo: Path, runtime_id: str, *, create: bool = False) -> Path:
    _hash(runtime_id, "runtime_id")
    global_root = _runtime_global_root(repo, create=create)
    directory = _contained(
        global_root / runtime_id.removeprefix("sha256:"),
        global_root,
        "runtime generation",
    )
    if create:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise IndexedRuntimeArtifactError(
                "runtime generation directory cannot be created"
            ) from exc
    return directory


def _normalize_revisions(value: Any) -> tuple[DonorRevision, ...]:
    if isinstance(value, (str, bytes, bytearray)):
        raise IndexedRuntimeInputError(
            "revisions must contain four typed donor revision descriptors"
        )
    try:
        values = tuple(value)
    except (TypeError, ValueError) as exc:
        raise IndexedRuntimeInputError(
            "revisions must contain four typed donor revision descriptors"
        ) from exc
    if len(values) != len(DONOR_VERSIONS):
        raise IndexedRuntimeInputError(
            "exactly one pinned revision for US, HD, PSPEU, and Saturn is required"
        )
    result: list[DonorRevision] = []
    for item in values:
        if isinstance(item, DonorRevision):
            result.append(item)
            continue
        try:
            result.append(DonorRevision.from_dict(item))
        except (DonorIndexError, AttributeError, TypeError, ValueError) as exc:
            raise IndexedRuntimeInputError(
                "revisions must be typed donor revision descriptors"
            ) from exc
    ordered = tuple(
        sorted(result, key=lambda item: DONOR_VERSIONS.index(item.version))
    )
    if tuple(item.version for item in ordered) != DONOR_VERSIONS:
        raise IndexedRuntimeInputError(
            "exactly one pinned revision for US, HD, PSPEU, and Saturn is required"
        )
    return ordered


def _gate_root(repo: Path, gate_run_id: str) -> Path:
    try:
        gate_run_id = validate_run_id(gate_run_id, "gate_run_id")
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise IndexedRuntimeInputError("gate_run_id is invalid") from exc
    nonmatchings = _contained(repo / "nonmatchings", repo, "gate search root")
    candidates: list[Path] = []
    # Expand the wildcard from its concrete parent.  Calling ``glob`` on a
    # path whose parent contains a literal ``*`` searches for a directory
    # actually named ``*`` and silently misses the factory's canonical
    # ``nonmatchings/<recipient>/search-runs/<run>`` layout.
    patterns = (
        (nonmatchings, f"*/search-runs/{gate_run_id}"),
        (nonmatchings, f"search-runs/{gate_run_id}"),
        (nonmatchings, f"search-evidence/integration-runs/{gate_run_id}"),
    )
    for parent, pattern in patterns:
        matches = parent.glob(pattern) if any(char in pattern for char in "*?[") else (parent / pattern,)
        for candidate in matches:
            try:
                if not candidate.is_dir():
                    continue
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(repo)
            except (OSError, RuntimeError, ValueError) as exc:
                if candidate.exists() or candidate.is_symlink():
                    raise IndexedRuntimeInputError(
                        "gate run root is outside the repository"
                    ) from exc
                continue
            if resolved not in candidates:
                candidates.append(resolved)
    if len(candidates) != 1:
        if not candidates:
            raise IndexedRuntimeInputError(
                "the explicit integration gate run root is missing"
            )
        raise IndexedRuntimeInputError(
            "the explicit integration gate run id resolves to multiple roots"
        )
    root = candidates[0]
    if root.name != gate_run_id:
        raise IndexedRuntimeInputError("gate run root name differs from gate_run_id")
    return root


def _load_gate(
    repo: Path, gate_run_id: str
) -> tuple[Path, ContentAddressedArchive, IntegrationGateReceipt, RunManifest]:
    root = _gate_root(repo, gate_run_id)
    archive = ContentAddressedArchive(root)
    receipts = root / "artifacts" / "receipts"
    if not receipts.is_dir():
        raise IndexedRuntimeInputError("integration gate receipt archive is missing")
    candidates: list[IntegrationGateReceipt] = []
    for path in sorted(receipts.glob("*.json")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            raw = path.read_bytes()
            document = json.loads(raw.decode("utf-8"))
            if not isinstance(document, Mapping):
                continue
            # Gate publication archives the canonical identity payload, while
            # the typed receipt carries the derived id and artifact metadata.
            # Reconstruct that envelope from the bytes rather than expecting
            # the payload file to contain fields it deliberately does not
            # duplicate.
            relative = path.relative_to(root).as_posix()
            receipt_document = dict(document)
            receipt_document.pop("protocol", None)
            receipt_document["gate_id"] = hash_bytes(raw)
            receipt_document["receipt_artifact"] = ArtifactRef(
                content_hash=hash_bytes(raw),
                path=relative,
                media_type="application/json",
                byte_size=len(raw),
            ).to_dict()
            receipt = IntegrationGateReceipt.from_dict(receipt_document)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError,
                SearchValidationError, TypeError, ValueError):
            continue
        if receipt.run_id != gate_run_id:
            continue
        # The canonical validator below owns the receipt-artifact path and
        # hash checks.  Do not discard a candidate merely because an archive
        # implementation exposes a different concrete path spelling here;
        # selecting by the explicit run id still keeps unrelated receipts out
        # of the candidate set, while validation remains fail-closed.
        candidates.append(receipt)
    if not candidates:
        raise IndexedRuntimeInputError(
            "no canonical integration gate receipt names gate_run_id"
        )
    if len(candidates) != 1 or len({item.gate_id for item in candidates}) != 1:
        raise IndexedRuntimeInputError(
            "the integration gate has ambiguous valid receipts"
        )
    receipt = candidates[0]
    try:
        manifest = validate_integration_gate(receipt, archive=archive)
    except IntegrationGateError as exc:
        raise IndexedRuntimeInputError(
            "the explicit integration gate failed canonical validation"
        ) from exc
    if receipt.run_id != manifest.run_id or receipt.run_id != gate_run_id:
        raise IndexedRuntimeIdentityMismatch(
            "integration gate run identity differs from gate_run_id"
        )
    return root, archive, receipt, manifest


def _module_identity(repo: Path, module_name: str) -> str:
    candidate = repo / "automation" / module_name
    # Inspect the checkout spelling before resolving it.  A symlink into the
    # checkout would otherwise become an ordinary resolved file and could
    # make an unpinned module masquerade as the required production module.
    if candidate.is_symlink():
        raise IndexedRuntimeInputError(
            "required indexed runtime module is unavailable: " + module_name
        )
    path = _contained(candidate, repo, "indexed runtime module")
    try:
        if path.is_symlink() or not path.is_file():
            raise IndexedRuntimeInputError(
                "required indexed runtime module is unavailable: " + module_name
            )
        return hash_bytes(path.read_bytes())
    except OSError as exc:
        raise IndexedRuntimeInputError(
            "cannot read the indexed runtime module identity"
        ) from exc


def _renderer_identities(repo: Path) -> tuple[str, str]:
    """Return the renderer protocol identity and exact source-byte identity."""

    source_identity = _module_identity(repo, "search_target_renderer.py")
    try:
        try:
            from .search_target_renderer import (  # type: ignore
                TARGET_RENDERER_IDENTITY,
            )
        except ImportError:
            try:
                from automation.search_target_renderer import (  # type: ignore
                    TARGET_RENDERER_IDENTITY,
                )
            except ImportError:
                from search_target_renderer import (  # type: ignore
                    TARGET_RENDERER_IDENTITY,
                )
    except Exception as exc:  # noqa: BLE001
        raise IndexedRuntimeInputError(
            "the required target renderer identity is unavailable"
        ) from exc
    try:
        renderer_identity = validate_hash(
            TARGET_RENDERER_IDENTITY,
            "renderer_identity",
        )
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise IndexedRuntimeInputError(
            "the target renderer identity is invalid"
        ) from exc
    return renderer_identity, source_identity


def _request_identity(
    gate: IntegrationGateReceipt,
    revisions: Sequence[DonorRevision],
    *,
    scanner_identity: str,
    signature_identity: str,
    renderer_identity: str,
    renderer_source_identity: str,
) -> str:
    return hash_canonical(
        {
            "protocol": "sotn-indexed-runtime-request-v1",
            "gate_id": gate.gate_id,
            "run_id": gate.run_id,
            "revisions": [item.to_dict() for item in revisions],
            "scanner_identity": scanner_identity,
            "signature_identity": signature_identity,
            "renderer_identity": renderer_identity,
            "renderer_source_identity": renderer_source_identity,
        }
    )


def _reject_symlink(path: Path, label: str) -> None:
    if path.is_symlink():
        raise IndexedRuntimeArtifactError(label + " may not be a symlink")


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(str(path), os.O_RDONLY)
    except (OSError, ValueError):
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _write_exact(path: Path, data: bytes, *, label: str) -> None:
    """Write one immutable file, refusing a different existing winner."""

    if not isinstance(data, bytes):
        raise TypeError("immutable publication data must be bytes")
    _reject_symlink(path, label)
    parent = path.parent
    current = parent
    while current != current.parent:
        _reject_symlink(current, label + " parent")
        current = current.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise IndexedRuntimeArtifactError(label + " parent cannot be created") from exc
    _reject_symlink(parent, label + " parent")
    if path.exists():
        try:
            existing = path.read_bytes()
        except OSError as exc:
            raise IndexedRuntimeArtifactError(label + " cannot be read") from exc
        if existing != data:
            raise IndexedRuntimeCollision(label + " already contains different bytes")
        return
    temporary: Optional[Path] = None
    descriptor: Optional[int] = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="." + path.name + ".",
            suffix=".tmp",
            dir=str(parent),
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(str(temporary), str(path))
        except FileExistsError:
            try:
                existing = path.read_bytes()
            except OSError as exc:
                raise IndexedRuntimeArtifactError(
                    label + " winner cannot be read"
                ) from exc
            if existing != data:
                raise IndexedRuntimeCollision(
                    label + " concurrent winner contains different bytes"
                )
        _fsync_directory(parent)
    except IndexedRuntimeError:
        raise
    except OSError as exc:
        raise IndexedRuntimeArtifactError(label + " cannot be published") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _copy_tree(source: Path, destination: Path, *, label: str) -> None:
    _reject_symlink(source, label)
    if not source.is_dir():
        raise IndexedRuntimeArtifactError(label + " source directory is missing")
    for item in sorted(source.rglob("*")):
        relative = item.relative_to(source)
        target = destination / relative
        _contained(target, destination, label + " destination")
        _reject_symlink(item, label)
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            _reject_symlink(target, label + " destination")
        elif item.is_file():
            try:
                data = item.read_bytes()
            except OSError as exc:
                raise IndexedRuntimeArtifactError(label + " source cannot be read") from exc
            _write_exact(target, data, label=label + " file")
        else:
            raise IndexedRuntimeArtifactError(label + " contains an unsupported entry")


def _copy_gate_snapshot(source: Path, stage: Path) -> None:
    gate_destination = stage / "gate"
    gate_destination.mkdir(parents=True, exist_ok=True)
    _copy_tree(source, gate_destination, label="integration gate snapshot")
    artifacts = gate_destination / "artifacts"
    if not artifacts.is_dir():
        raise IndexedRuntimeArtifactError("integration gate snapshot lacks artifacts")
    # The gate receipt and all source evidence are mirrored at the runtime
    # archive root, so a generation can be verified without its original path.
    _copy_tree(artifacts, stage / "artifacts", label="integration gate artifact mirror")


@dataclass(frozen=True)
class _DonorSnapshotFile:
    """One immutable file bound by a donor snapshot manifest."""

    path: str
    kind: str
    artifact: ArtifactRef
    content_hash: str
    byte_size: int
    data: bytes | None = None


def _archive_artifact_path(reference: ArtifactRef, label: str) -> None:
    """Require an artifact reference to name an archive-owned object."""

    if not isinstance(reference, ArtifactRef):
        raise IndexedRuntimeInputError(label + " is not a typed artifact reference")
    path = reference.path
    try:
        relative = validate_relative_path(path, label + " path")
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise IndexedRuntimeInputError(label + " must be a safe archive-relative path") from exc
    if (
        relative != path
        or not path.startswith("artifacts/")
        or "\\" in path
        or path.endswith("/")
        or Path(path).name in {"", ".", ".."}
    ):
        raise IndexedRuntimeInputError(label + " must remain under the archive artifacts root")


def _reject_archive_symlinks(
    archive: ContentAddressedArchive,
    path: Path,
    label: str,
) -> None:
    """Reject symlinks in an archive path, including its parents."""

    root = archive.run_root
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise IndexedRuntimeArtifactError(label + " escapes its archive root") from exc
    _reject_symlink(root, label + " root")
    current = root
    for component in relative.parts:
        current = current / component
        _reject_symlink(current, label)


def _read_archive_artifact(
    archive: ContentAddressedArchive,
    reference: ArtifactRef,
    *,
    label: str,
) -> bytes:
    _archive_artifact_path(reference, label)
    try:
        path = archive.resolve(reference)
        _reject_archive_symlinks(archive, path, label)
        return archive.verify(reference)
    except (ArchiveError, SearchValidationError, TypeError, ValueError) as exc:
        raise IndexedRuntimeArtifactError(label + " is missing or corrupt") from exc


def _validate_snapshot_manifest(
    revision: DonorRevision,
    *,
    archive: ContentAddressedArchive,
    snapshot_root: Path | None = None,
) -> tuple[dict[str, Any], tuple[_DonorSnapshotFile, ...]]:
    """Validate one archive-owned full-revision snapshot manifest.

    The source artifact on ``DonorRevision`` is intentionally the manifest
    itself.  Its file entries follow the scanner-owned protocol exactly and
    each entry points at a second archive object containing the complete bytes.
    The materializer copies those verified archive bytes, never a path guessed
    from the mutable checkout.
    """

    if not isinstance(revision, DonorRevision):
        raise IndexedRuntimeInputError("donor snapshot revision is not typed")
    manifest_reference = revision.source_artifact
    _archive_artifact_path(manifest_reference, "donor snapshot manifest")
    if (
        manifest_reference.media_type != "application/json"
        or not manifest_reference.path.endswith(".json")
    ):
        raise IndexedRuntimeInputError(
            "donor snapshot source_artifact must be an archive JSON manifest"
        )
    raw_manifest = _read_archive_artifact(
        archive,
        manifest_reference,
        label="donor snapshot manifest",
    )
    try:
        manifest = json.loads(raw_manifest.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IndexedRuntimeInputError("donor snapshot manifest is not valid UTF-8 JSON") from exc
    if not isinstance(manifest, Mapping):
        raise IndexedRuntimeInputError("donor snapshot manifest must be an object")
    if set(manifest) != {"protocol", "version", "revision", "files"}:
        raise IndexedRuntimeInputError("donor snapshot manifest fields are invalid")
    try:
        canonical_manifest = canonical_bytes(manifest)
    except (TypeError, ValueError) as exc:
        raise IndexedRuntimeInputError("donor snapshot manifest cannot be canonicalized") from exc
    if raw_manifest != canonical_manifest:
        raise IndexedRuntimeIdentityMismatch(
            "donor snapshot manifest is not canonical JSON"
        )
    if manifest["protocol"] != DONOR_SNAPSHOT_MANIFEST_PROTOCOL:
        raise IndexedRuntimeInputError("unsupported donor snapshot manifest protocol")
    if manifest["version"] != revision.version:
        raise IndexedRuntimeIdentityMismatch(
            "donor snapshot manifest version differs from pinned revision"
        )
    if manifest["revision"] != revision.revision:
        raise IndexedRuntimeIdentityMismatch(
            "donor snapshot manifest revision differs from pinned revision"
        )
    files = manifest["files"]
    if not isinstance(files, list) or not files:
        raise IndexedRuntimeInputError("donor snapshot manifest files must be nonempty")
    parsed: list[_DonorSnapshotFile] = []
    paths: list[str] = []
    families = {"config": False, "source": False, "assembly": False}
    for index, item in enumerate(files):
        if not isinstance(item, Mapping) or set(item) != {
            "path",
            "kind",
            "content_hash",
            "byte_size",
            "artifact",
        }:
            raise IndexedRuntimeInputError(
                "donor snapshot file entry has invalid fields at index " + str(index)
            )
        path = item["path"]
        if (
            not isinstance(path, str)
            or "\\" in path
            or Path(path).as_posix() != path
            or path == DONOR_SNAPSHOT_MANIFEST_FILENAME
            or path.startswith("artifacts/")
        ):
            raise IndexedRuntimeInputError(
                "donor snapshot file path is not a safe repository-relative path"
            )
        try:
            validate_relative_path(path, "donor snapshot file path")
        except (SearchValidationError, TypeError, ValueError) as exc:
            raise IndexedRuntimeInputError(
                "donor snapshot file path is not a safe repository-relative path"
            ) from exc
        try:
            content_hash = _hash(item["content_hash"], "donor snapshot content_hash")
        except IndexedRuntimeInputError as exc:
            raise IndexedRuntimeInputError(
                "donor snapshot file content_hash is invalid"
            ) from exc
        byte_size = item["byte_size"]
        if isinstance(byte_size, bool) or not isinstance(byte_size, int) or byte_size < 0:
            raise IndexedRuntimeInputError("donor snapshot file byte_size is invalid")
        kind = item["kind"]
        if kind not in DONOR_SNAPSHOT_FILE_KINDS:
            raise IndexedRuntimeInputError(
                "donor snapshot file kind is unsupported: " + str(kind)
            )
        try:
            artifact = ArtifactRef.from_dict(item["artifact"])
        except (AttributeError, KeyError, SearchValidationError, TypeError, ValueError) as exc:
            raise IndexedRuntimeInputError(
                "donor snapshot file artifact is invalid"
            ) from exc
        data = _read_archive_artifact(
            archive,
            artifact,
            label="donor snapshot file artifact",
        )
        if (
            artifact.content_hash != content_hash
            or artifact.byte_size != byte_size
            or hash_bytes(data) != content_hash
            or len(data) != byte_size
        ):
            raise IndexedRuntimeIdentityMismatch(
                "donor snapshot file artifact differs from its manifest entry: " + path
            )
        paths.append(path)
        if kind == "config":
            families["config"] = True
        if kind == "source":
            families["source"] = True
        if kind == "assembly":
            families["assembly"] = True
        parsed.append(_DonorSnapshotFile(path, kind, artifact, content_hash, byte_size, data))
    if paths != sorted(paths) or len(set(paths)) != len(paths):
        raise IndexedRuntimeInputError(
            "donor snapshot manifest files must be sorted and unique"
        )
    missing_kinds = {name for name, present in families.items() if not present}
    if missing_kinds:
        raise IndexedRuntimeInputError(
            "donor snapshot manifest does not bind every scanned file family: "
            + ",".join(sorted(missing_kinds))
        )
    if snapshot_root is not None:
        _verify_materialized_snapshot(snapshot_root, raw_manifest, parsed)
    return dict(manifest), tuple(parsed)


def _verify_materialized_snapshot(
    snapshot_root: Path,
    manifest_bytes: bytes,
    files: Sequence[_DonorSnapshotFile],
) -> None:
    """Require a materialized snapshot to contain exactly its manifest files."""

    _reject_symlink(snapshot_root, "donor snapshot root")
    if not snapshot_root.is_dir():
        raise IndexedRuntimeArtifactError("donor snapshot root is missing")
    expected_files = {item.path for item in files}
    expected_files.add(DONOR_SNAPSHOT_MANIFEST_FILENAME)
    actual_files: set[str] = set()
    actual_dirs: set[str] = set()
    for path in sorted(snapshot_root.rglob("*")):
        _reject_symlink(path, "donor snapshot")
        relative = path.relative_to(snapshot_root).as_posix()
        if path.is_file():
            actual_files.add(relative)
        elif path.is_dir():
            actual_dirs.add(relative)
        else:
            raise IndexedRuntimeArtifactError(
                "donor snapshot contains an unsupported filesystem entry"
            )
    if actual_files != expected_files:
        unexpected = sorted(actual_files - expected_files)
        missing = sorted(expected_files - actual_files)
        detail: list[str] = []
        if unexpected:
            detail.append("unexpected=" + ",".join(unexpected))
        if missing:
            detail.append("missing=" + ",".join(missing))
        raise IndexedRuntimeArtifactError(
            "donor snapshot file set differs from its manifest (" + "; ".join(detail) + ")"
        )
    expected_dirs: set[str] = set()
    for relative in expected_files:
        parts = relative.split("/")[:-1]
        for index in range(1, len(parts) + 1):
            expected_dirs.add("/".join(parts[:index]))
    if actual_dirs != expected_dirs:
        raise IndexedRuntimeArtifactError(
            "donor snapshot directory set differs from its manifest"
        )
    try:
        if (snapshot_root / DONOR_SNAPSHOT_MANIFEST_FILENAME).read_bytes() != manifest_bytes:
            raise IndexedRuntimeIdentityMismatch(
                "materialized donor snapshot manifest differs from its archive bytes"
            )
    except OSError as exc:
        raise IndexedRuntimeArtifactError("materialized donor snapshot manifest cannot be read") from exc
    for item in files:
        path = _contained(snapshot_root / Path(item.path), snapshot_root, "donor snapshot file")
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise IndexedRuntimeArtifactError(
                "materialized donor snapshot file cannot be read: " + item.path
            ) from exc
        if hash_bytes(data) != item.content_hash or len(data) != item.byte_size:
            raise IndexedRuntimeIdentityMismatch(
                "materialized donor snapshot file identity differs from its manifest: "
                + item.path
            )
        if item.data is not None and data != item.data:
            raise IndexedRuntimeIdentityMismatch(
                "materialized donor snapshot file differs from its archive bytes: " + item.path
            )


def _resolve_revision_archive(
    repo: Path,
    revisions: Sequence[DonorRevision],
    gate_archive: ContentAddressedArchive,
) -> ContentAddressedArchive:
    """Resolve one immutable owner for all pinned snapshot manifests.

    Historical gates are not rewritten to add later snapshot objects.  A
    caller may therefore point revisions at the canonical sibling archive
    published by :func:`publish_donor_snapshots`; old gates that already carry
    the scanner protocol remain accepted for compatibility.  Mixed or
    ambiguous ownership is refused rather than selected by path guessing.
    """

    candidates: list[ContentAddressedArchive] = [gate_archive]
    snapshot_root = _contained(
        repo / DONOR_SNAPSHOT_ARCHIVE_ROOT,
        repo,
        "donor snapshot archive",
    )
    if snapshot_root.is_dir() and not snapshot_root.is_symlink():
        candidates.append(ContentAddressedArchive(snapshot_root))

    valid: list[ContentAddressedArchive] = []
    failures: list[IndexedRuntimeError] = []
    for archive in candidates:
        try:
            for revision in revisions:
                _validate_snapshot_manifest(revision, archive=archive)
        except IndexedRuntimeError as exc:
            failures.append(exc)
            continue
        valid.append(archive)
    if len(valid) == 1:
        return valid[0]
    if len(valid) > 1:
        raise IndexedRuntimeInputError(
            "pinned donor snapshot manifests have ambiguous archive ownership"
        )

    # If an archive contains any named object but that object is malformed or
    # corrupt, report the failure from that owner.  Do not fall through to a
    # second archive and silently mask corruption.
    for archive in candidates:
        for revision in revisions:
            try:
                path = archive.resolve(revision.source_artifact)
            except (ArchiveError, SearchValidationError, TypeError, ValueError):
                continue
            if path.exists():
                for failure in failures:
                    if failure is not None:
                        raise failure
                break
    raise IndexedRuntimeInputError(
        "no canonical donor snapshot archive contains all pinned revisions"
    )


def _materialize_revision_sources(
    revisions: Sequence[DonorRevision],
    *,
    source_archive: ContentAddressedArchive,
    destination_root: Path,
) -> dict[str, Path]:
    """Materialize scanner inputs from archive-owned bytes only.

    ``DonorRevision.source_artifact`` is the canonical manifest and each entry
    carries a separately archived byte object.  The checkout is deliberately
    absent from this function: a mutable path or a same-named file cannot
    masquerade as pinned evidence.  The scanner receives the resulting root,
    while its archive argument continues to resolve the manifest's byte
    references.
    """

    snapshots_root = _contained(
        destination_root / "snapshots",
        destination_root,
        "donor snapshot root",
    )
    _reject_symlink(snapshots_root, "donor snapshot root")
    try:
        snapshots_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise IndexedRuntimeArtifactError("donor snapshot root cannot be created") from exc
    materialized: dict[str, Path] = {}
    for revision in revisions:
        manifest, files = _validate_snapshot_manifest(
            revision,
            archive=source_archive,
        )
        snapshot_root = _contained(
            snapshots_root / revision.version,
            snapshots_root,
            "donor snapshot version root",
        )
        _reject_symlink(snapshot_root, "donor snapshot version root")
        if snapshot_root.exists():
            raise IndexedRuntimeCollision(
                "donor snapshot version root already exists"
            )
        try:
            snapshot_root.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            raise IndexedRuntimeArtifactError(
                "donor snapshot version root cannot be created"
            ) from exc
        materialized_files: list[_DonorSnapshotFile] = []
        # Mirror the manifest and every nested byte object into the runtime
        # archive.  The published generation is self-contained and can be
        # verified after the separate source archive is unavailable.
        source_references = (revision.source_artifact,) + tuple(
            item.artifact for item in files
        )
        for reference in source_references:
            data = _read_archive_artifact(
                source_archive,
                reference,
                label="donor snapshot archive object",
            )
            target = _contained(
                destination_root / Path(reference.path),
                destination_root,
                "donor snapshot archive mirror",
            )
            _write_exact(target, data, label="donor snapshot archive mirror")
        for item in files:
            if item.data is None:
                raise IndexedRuntimeArtifactError(
                    "donor snapshot archive bytes are missing: " + item.path
                )
            data = item.data
            target = _contained(
                snapshot_root / Path(item.path),
                snapshot_root,
                "donor snapshot materialization",
            )
            _write_exact(target, data, label="donor snapshot file")
            materialized_files.append(
                _DonorSnapshotFile(
                    item.path,
                    item.kind,
                    item.artifact,
                    item.content_hash,
                    item.byte_size,
                    data,
                )
            )
        _write_exact(
            snapshot_root / DONOR_SNAPSHOT_MANIFEST_FILENAME,
            canonical_bytes(manifest),
            label="donor snapshot manifest",
        )
        _verify_materialized_snapshot(
            snapshot_root,
            canonical_bytes(manifest),
            tuple(materialized_files),
        )
        materialized[revision.version] = snapshot_root
    return materialized


def publish_donor_snapshots(
    snapshots: Sequence[DonorSnapshot],
    *,
    repo: Path | str,
) -> tuple[DonorRevision, ...]:
    """Publish four typed donor snapshots in the canonical sibling archive.

    This boundary is for source snapshots that were produced after a
    historical integration gate was sealed.  It accepts complete bytes, not
    checkout paths, and returns ``DonorRevision`` values whose
    ``source_artifact`` points at the immutable scanner manifest.  The gate is
    never opened or modified.
    """

    repo_root = _repo_root(repo)
    try:
        values = tuple(snapshots)
    except (TypeError, ValueError) as exc:
        raise IndexedRuntimeInputError("donor snapshots must be typed records") from exc
    if len(values) != len(DONOR_VERSIONS) or any(
        not isinstance(item, DonorSnapshot) for item in values
    ):
        raise IndexedRuntimeInputError(
            "exactly one typed donor snapshot for each supported version is required"
        )
    ordered = tuple(sorted(values, key=lambda item: DONOR_VERSIONS.index(item.version)))
    if tuple(item.version for item in ordered) != DONOR_VERSIONS:
        raise IndexedRuntimeInputError(
            "exactly one typed donor snapshot for each supported version is required"
        )
    archive_root = _contained(
        repo_root / DONOR_SNAPSHOT_ARCHIVE_ROOT,
        repo_root,
        "donor snapshot archive",
    )
    _reject_symlink(archive_root, "donor snapshot archive")
    archive = ContentAddressedArchive(archive_root)
    revisions: list[DonorRevision] = []
    for snapshot in ordered:
        entries: list[dict[str, Any]] = []
        for item in snapshot.files:
            try:
                relative = validate_relative_path(item.path, "donor snapshot file path")
            except (SearchValidationError, TypeError, ValueError) as exc:
                raise IndexedRuntimeInputError(
                    "donor snapshot file path is not safe"
                ) from exc
            if (
                relative != item.path
                or item.path == DONOR_SNAPSHOT_MANIFEST_FILENAME
                or item.path.startswith("artifacts/")
                or "\\" in item.path
            ):
                raise IndexedRuntimeInputError(
                    "donor snapshot file path is not a repository-relative input"
                )
            artifact = archive.put_bytes(
                item.data,
                category="donor-snapshot-files",
                suffix=".bin",
                media_type="application/octet-stream",
            )
            entries.append(
                {
                    "path": item.path,
                    "kind": item.kind,
                    "content_hash": hash_bytes(item.data),
                    "byte_size": len(item.data),
                    "artifact": artifact.to_dict(),
                }
            )
        payload = {
            "protocol": DONOR_SNAPSHOT_MANIFEST_PROTOCOL,
            "version": snapshot.version,
            "revision": snapshot.revision,
            "files": entries,
        }
        manifest_ref = archive.put_json(
            payload,
            category="sources",
            suffix=".snapshot.json",
        )
        revision = DonorRevision(
            version=snapshot.version,
            revision=snapshot.revision,
            source_artifact=manifest_ref,
        )
        _validate_snapshot_manifest(revision, archive=archive)
        revisions.append(revision)
    return tuple(revisions)


def scan_repository_revision(
    revision: DonorRevision,
    *,
    repo: Path | str,
    archive: ContentAddressedArchive,
) -> Iterable[Any]:
    """Call the Task 1 scanner through its exact planned interface.

    Task 1 is intentionally allowed to land after this module.  Keeping the
    import at the call boundary lets focused runtime tests install a local
    fake while ensuring production publication fails closed until the real
    scanner module is present.
    """

    try:
        from .search_donor_scan import scan_repository_revision as scanner
    except ImportError:  # pragma: no cover - exercised until Task 1 lands
        try:
            from automation.search_donor_scan import (  # type: ignore
                scan_repository_revision as scanner,
            )
        except ImportError as exc:
            raise IndexedRuntimeScannerError(
                "the production donor scanner is unavailable"
            ) from exc
    try:
        result = scanner(revision, repo=repo, archive=archive)
        iter(result)
        return result
    except IndexedRuntimeError:
        raise
    except TypeError as exc:
        raise IndexedRuntimeScannerError(
            "the production donor scanner returned a non-iterable result"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise IndexedRuntimeScannerError(
            "the production donor scanner failed: " + str(exc)
        ) from exc


def _context_to_dict(
    value: CompletedLineageContext | CompletedLineageDiagnostic,
) -> dict[str, Any]:
    try:
        return value.to_dict()
    except AttributeError as exc:
        raise IndexedRuntimeIdentityMismatch(
            "lineage context does not expose complete serialization"
        ) from exc


def _context_from_dict(value: Mapping[str, Any]) -> CompletedLineageContext | CompletedLineageDiagnostic:
    if not isinstance(value, Mapping):
        raise IndexedRuntimeIdentityMismatch("lineage context is not an object")
    kind = value.get("kind")
    try:
        if kind == "context":
            return CompletedLineageContext.from_dict(value)
        if kind == "diagnostic":
            return CompletedLineageDiagnostic.from_dict(value)
    except PatternInputError as exc:
        raise IndexedRuntimeIdentityMismatch(
            "lineage context payload is invalid"
        ) from exc
    raise IndexedRuntimeIdentityMismatch("lineage context kind is unsupported")


def _support_for_taxonomy(taxonomy: Any) -> tuple[str, ...]:
    values: set[str] = {taxonomy.taxonomy_id}
    for vector in (taxonomy.before, taxonomy.after):
        for identity in (vector.object_hash, vector.mismatch_signature):
            if identity:
                values.add(identity)
        if vector.diagnostic_artifact is not None:
            values.add(vector.diagnostic_artifact.content_hash)
    return tuple(sorted(values))


def _corpus_entries(
    *,
    repo: Path,
    gate_root: Path,
    gate_archive: ContentAddressedArchive,
    runtime_archive: ContentAddressedArchive,
    manifest: RunManifest,
    contexts: Sequence[CompletedLineageContext | CompletedLineageDiagnostic],
    report: SearchPatternReport,
) -> tuple[CorpusEvidence, ...]:
    entries: list[CorpusEvidence] = list(
        collect_recurring_first_divergence(
            report,
            contexts,
            artifact_root=runtime_archive.run_root,
        )
    )
    context_by_run = {context.run_id: context for context in contexts}
    ledger = AppendOnlyLedger(
        gate_root / "ledger.jsonl",
        run_id=manifest.run_id,
        archive=gate_archive,
    )
    try:
        events = ledger.verify()
    except Exception as exc:  # noqa: BLE001
        raise IndexedRuntimeArtifactError(
            "completed integration gate ledger cannot be replayed"
        ) from exc
    seen: set[str] = {entry.evidence_id for entry in entries}
    for event in events:
        payload = event.payload
        # A future typed ledger event may carry a draft-landed pair and its
        # before/after scores.  The call is deliberately conditional because
        # the current coordinator schema has no such event; no synthetic pair
        # is manufactured merely to create a promotion claim.
        pair = getattr(payload, "draft_landed", None)
        before = getattr(payload, "before", None)
        after = getattr(payload, "after", None)
        if isinstance(pair, DraftLandedObservation) and before is not None and after is not None:
            context = context_by_run.get(manifest.run_id)
            target_identity = manifest.target_identities.get(pair.recipient_id)
            if isinstance(context, CompletedLineageContext) and target_identity is not None:
                promotion = promote_draft_landed(
                    pair,
                    before,
                    after,
                    evaluator_identity=context.evaluator_identity,
                    target_identity=target_identity,
                )
                evidence = (
                    promotion.evidence
                    if isinstance(promotion, (PromotionAccepted, PromotionRefused))
                    else None
                )
                if evidence is not None and evidence.evidence_id not in seen:
                    entries.append(evidence)
                    seen.add(evidence.evidence_id)
        if not isinstance(payload, EvaluationEvent) or payload.before is None:
            continue
        context = context_by_run.get(manifest.run_id)
        if not isinstance(context, CompletedLineageContext):
            # Historical missing-evaluator contexts remain diagnostics.  They
            # are serialized in the runtime binding but can never become a
            # scorer or promotion claim.
            continue
        target_identity = manifest.target_identities.get(payload.recipient_id)
        if target_identity is None:
            continue
        if (
            payload.before.compiler_identity != manifest.compiler_identity
            or payload.after.compiler_identity != manifest.compiler_identity
        ):
            raise IndexedRuntimeIdentityMismatch(
                "completed scorer evidence is bound to a different compiler"
            )
        taxonomy = make_scorer_taxonomy(
            payload.before,
            payload.after,
            evaluator_identity=context.evaluator_identity,
            target_identity=target_identity,
        )
        evidence = _make_corpus_evidence(
            kind="scorer",
            outcome="accepted",
            compiler_identity=payload.before.compiler_identity,
            evaluator_identity=context.evaluator_identity,
            target_identity=target_identity,
            scorer=taxonomy,
            support_identities=_support_for_taxonomy(taxonomy),
        )
        if evidence.evidence_id not in seen:
            entries.append(evidence)
            seen.add(evidence.evidence_id)

    # MATCHING-LESSONS is an ordinary repository input, not a copied excerpt.
    # If a test repository does not carry it, the runtime remains valid with
    # the gate's real evidence; a production repository always contributes the
    # reviewed citation below.
    lesson_path = repo / "MATCHING-LESSONS.md"
    if lesson_path.is_file() and not lesson_path.is_symlink():
        try:
            lesson_bytes = lesson_path.read_bytes()
        except OSError as exc:
            raise IndexedRuntimeArtifactError("lesson source cannot be read") from exc
        lesson_ref = ArtifactRef(
            hash_bytes(lesson_bytes),
            "sources/MATCHING-LESSONS.md",
            "text/markdown",
            len(lesson_bytes),
        )
        lesson_destination = runtime_archive.run_root / lesson_ref.path
        _write_exact(lesson_destination, lesson_bytes, label="lesson source")
        citation = make_lesson_citation(
            lesson_ref,
            lesson_bytes,
            section="§2",
            line_start=146,
            line_end=178,
            rule_id="argument-width.absent-andi",
            absence_masking=AbsenceMaskingClaim(
                opcode="andi",
                masks=("0xff", "0xffff"),
                scope="argument-use",
            ),
        )
        evidence = _make_corpus_evidence(
            kind="lesson",
            outcome="accepted",
            citations=(citation,),
            support_identities=(
                citation.citation_id,
                citation.source.content_hash,
                citation.span_identity,
            ),
        )
        if evidence.evidence_id not in seen:
            entries.append(evidence)
    return tuple(entries)


def _indexed_runtime_payload(
    *,
    binding: "IndexedRuntimeBinding",
    corpus: CorpusGeneration,
    donor_index: DonorIndexGeneration,
    pattern_report: SearchPatternReport,
    lineage_contexts: Sequence[CompletedLineageContext | CompletedLineageDiagnostic],
) -> dict[str, Any]:
    return {
        "protocol": INDEXED_RUNTIME_PROTOCOL,
        "binding": binding.to_dict(),
        "corpus": corpus.to_dict(),
        "donor_index": donor_index.to_dict(),
        "pattern_report": pattern_report.to_dict(),
        "lineage_contexts": [_context_to_dict(item) for item in lineage_contexts],
    }


# production-audit: pure-value
@dataclass(frozen=True)
class IndexedRuntimeBinding:
    """Complete gate, corpus, index, scanner, and revision provenance."""

    integration_gate: IntegrationGateReceipt
    integration_gate_id: str
    manifest_artifact_identity: str
    subset_identity: str
    queue_evidence_identity: str
    selected_lanes: tuple[str, ...]
    coordinator_identity: str
    connector_identity: str
    compiler_identity: str
    config_identity: str
    schema_identity: str
    scanner_identity: str
    scanner_source_identity: str
    signature_identity: str
    renderer_identity: str
    renderer_source_identity: str
    revision_set_identity: str
    revisions: tuple[DonorRevision, ...]
    corpus_generation_id: str
    corpus_artifact: ArtifactRef
    donor_index_generation_id: str
    donor_index_artifact: ArtifactRef
    pattern_report_id: str
    pattern_report_artifact: ArtifactRef
    gate_manifest_artifact: ArtifactRef
    gate_ledger_artifact: ArtifactRef

    def __post_init__(self) -> None:
        if not isinstance(self.integration_gate, IntegrationGateReceipt):
            raise IndexedRuntimeIdentityMismatch(
                "runtime binding needs a typed integration gate receipt"
            )
        try:
            gate = IntegrationGateReceipt.from_dict(self.integration_gate.to_dict())
        except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
            raise IndexedRuntimeIdentityMismatch("runtime gate binding is invalid") from exc
        if gate != self.integration_gate:
            raise IndexedRuntimeIdentityMismatch("runtime gate binding is not canonical")
        object.__setattr__(self, "integration_gate", gate)
        if self.integration_gate_id != gate.gate_id:
            raise IndexedRuntimeIdentityMismatch("runtime gate id differs from receipt")
        copied = (
            ("manifest_artifact_identity", self.manifest_artifact_identity),
            ("subset_identity", self.subset_identity),
            ("queue_evidence_identity", self.queue_evidence_identity),
            ("coordinator_identity", self.coordinator_identity),
            ("connector_identity", self.connector_identity),
        )
        for name, value in copied:
            _hash(value, name)
            if value != getattr(gate, name):
                raise IndexedRuntimeIdentityMismatch(
                    "runtime " + name + " differs from integration gate"
                )
        for name in (
            "compiler_identity",
            "config_identity",
            "schema_identity",
            "scanner_identity",
            "scanner_source_identity",
            "signature_identity",
            "renderer_identity",
            "renderer_source_identity",
            "revision_set_identity",
            "corpus_generation_id",
            "donor_index_generation_id",
            "pattern_report_id",
        ):
            _hash(getattr(self, name), name)
        try:
            revisions = tuple(self.revisions)
        except (TypeError, ValueError) as exc:
            raise IndexedRuntimeInputError("runtime revisions are invalid") from exc
        revisions = _normalize_revisions(revisions)
        if revision_set_identity(revisions) != self.revision_set_identity:
            raise IndexedRuntimeIdentityMismatch(
                "runtime revision set identity differs from its revisions"
            )
        object.__setattr__(self, "revisions", revisions)
        lanes = tuple(self.selected_lanes)
        if lanes != gate.selected_lanes:
            raise IndexedRuntimeIdentityMismatch(
                "runtime selected lanes differ from integration gate"
            )
        object.__setattr__(self, "selected_lanes", lanes)
        for name in (
            "corpus_artifact",
            "donor_index_artifact",
            "pattern_report_artifact",
            "gate_manifest_artifact",
            "gate_ledger_artifact",
        ):
            value = getattr(self, name)
            if not isinstance(value, ArtifactRef):
                try:
                    value = ArtifactRef.from_dict(value)
                except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
                    raise IndexedRuntimeArtifactError(
                        "runtime " + name + " is not an artifact reference"
                    ) from exc
                object.__setattr__(self, name, value)
            _hash(value.content_hash, name + ".content_hash")

    @property
    def gate_id(self) -> str:
        return self.integration_gate_id

    @property
    def corpus_id(self) -> str:
        return self.corpus_generation_id

    @property
    def donor_index_id(self) -> str:
        return self.donor_index_generation_id

    @property
    def index_id(self) -> str:
        return self.donor_index_generation_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "integration_gate": self.integration_gate.to_dict(),
            "integration_gate_id": self.integration_gate_id,
            "manifest_artifact_identity": self.manifest_artifact_identity,
            "subset_identity": self.subset_identity,
            "queue_evidence_identity": self.queue_evidence_identity,
            "selected_lanes": list(self.selected_lanes),
            "coordinator_identity": self.coordinator_identity,
            "connector_identity": self.connector_identity,
            "compiler_identity": self.compiler_identity,
            "config_identity": self.config_identity,
            "schema_identity": self.schema_identity,
            "scanner_identity": self.scanner_identity,
            "scanner_source_identity": self.scanner_source_identity,
            "signature_identity": self.signature_identity,
            "renderer_identity": self.renderer_identity,
            "renderer_source_identity": self.renderer_source_identity,
            "revision_set_identity": self.revision_set_identity,
            "revisions": [item.to_dict() for item in self.revisions],
            "corpus_generation_id": self.corpus_generation_id,
            "corpus_artifact": self.corpus_artifact.to_dict(),
            "donor_index_generation_id": self.donor_index_generation_id,
            "donor_index_artifact": self.donor_index_artifact.to_dict(),
            "pattern_report_id": self.pattern_report_id,
            "pattern_report_artifact": self.pattern_report_artifact.to_dict(),
            "gate_manifest_artifact": self.gate_manifest_artifact.to_dict(),
            "gate_ledger_artifact": self.gate_ledger_artifact.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "IndexedRuntimeBinding":
        fields = {
            "integration_gate",
            "integration_gate_id",
            "manifest_artifact_identity",
            "subset_identity",
            "queue_evidence_identity",
            "selected_lanes",
            "coordinator_identity",
            "connector_identity",
            "compiler_identity",
            "config_identity",
            "schema_identity",
            "scanner_identity",
            "scanner_source_identity",
            "signature_identity",
            "renderer_identity",
            "renderer_source_identity",
            "revision_set_identity",
            "revisions",
            "corpus_generation_id",
            "corpus_artifact",
            "donor_index_generation_id",
            "donor_index_artifact",
            "pattern_report_id",
            "pattern_report_artifact",
            "gate_manifest_artifact",
            "gate_ledger_artifact",
        }
        if not isinstance(value, Mapping) or set(value) != fields:
            raise IndexedRuntimeIdentityMismatch(
                "runtime binding fields do not match its protocol"
            )
        try:
            data = dict(value)
            data["integration_gate"] = IntegrationGateReceipt.from_dict(
                data["integration_gate"]
            )
            data["revisions"] = tuple(
                DonorRevision.from_dict(item) for item in data["revisions"]
            )
            for name in (
                "corpus_artifact",
                "donor_index_artifact",
                "pattern_report_artifact",
                "gate_manifest_artifact",
                "gate_ledger_artifact",
            ):
                data[name] = ArtifactRef.from_dict(data[name])
            return cls(**data)
        except IndexedRuntimeError:
            raise
        except (AttributeError, DonorIndexError, IntegrationGateError,
                KeyError, SearchValidationError, TypeError, ValueError) as exc:
            raise IndexedRuntimeIdentityMismatch(
                "runtime binding payload is invalid"
            ) from exc


# production-audit: pure-value
@dataclass(frozen=True)
class IndexedRuntimeGeneration:
    """One immutable indexed runtime and its complete typed contents."""

    runtime_id: str
    binding: IndexedRuntimeBinding
    corpus: CorpusGeneration
    donor_index: DonorIndexGeneration
    pattern_report: SearchPatternReport
    lineage_contexts: tuple[CompletedLineageContext | CompletedLineageDiagnostic, ...]
    artifact: ArtifactRef

    def __post_init__(self) -> None:
        _hash(self.runtime_id, "runtime_id")
        if not isinstance(self.binding, IndexedRuntimeBinding):
            try:
                object.__setattr__(
                    self,
                    "binding",
                    IndexedRuntimeBinding.from_dict(self.binding),
                )
            except (AttributeError, TypeError, ValueError) as exc:
                raise IndexedRuntimeIdentityMismatch("runtime binding is invalid") from exc
        if not isinstance(self.corpus, CorpusGeneration):
            raise IndexedRuntimeIdentityMismatch("runtime corpus is not typed")
        if not isinstance(self.donor_index, DonorIndexGeneration):
            raise IndexedRuntimeIdentityMismatch("runtime donor index is not typed")
        if not isinstance(self.pattern_report, SearchPatternReport):
            raise IndexedRuntimeIdentityMismatch("runtime pattern report is not typed")
        if self.binding.corpus_generation_id != self.corpus.generation_id:
            raise IndexedRuntimeIdentityMismatch("runtime corpus id differs from binding")
        if self.binding.corpus_artifact != self.corpus.artifact:
            raise IndexedRuntimeIdentityMismatch(
                "runtime corpus artifact differs from binding"
            )
        if self.binding.donor_index_generation_id != self.donor_index.generation_id:
            raise IndexedRuntimeIdentityMismatch(
                "runtime donor index id differs from binding"
            )
        if self.binding.donor_index_artifact != self.donor_index.artifact:
            raise IndexedRuntimeIdentityMismatch(
                "runtime donor index artifact differs from binding"
            )
        if self.binding.pattern_report_id != self.pattern_report.report_id:
            raise IndexedRuntimeIdentityMismatch(
                "runtime pattern report id differs from binding"
            )
        if self.binding.pattern_report_artifact != self.pattern_report.artifact:
            raise IndexedRuntimeIdentityMismatch(
                "runtime pattern report artifact differs from binding"
            )
        if self.corpus.integration_gate != self.binding.integration_gate:
            raise IndexedRuntimeIdentityMismatch(
                "runtime corpus gate differs from binding"
            )
        if self.corpus.schema_identity != self.binding.schema_identity:
            raise IndexedRuntimeIdentityMismatch(
                "runtime corpus schema differs from binding"
            )
        if self.donor_index.binding.integration_gate != self.binding.integration_gate:
            raise IndexedRuntimeIdentityMismatch(
                "runtime donor index gate differs from binding"
            )
        if self.donor_index.revisions != self.binding.revisions:
            raise IndexedRuntimeIdentityMismatch(
                "runtime donor index revisions differ from binding"
            )
        donor_binding = self.donor_index.binding
        for name in (
            "compiler_identity",
            "config_identity",
            "signature_identity",
            "schema_identity",
        ):
            if getattr(donor_binding, name) != getattr(self.binding, name):
                raise IndexedRuntimeIdentityMismatch(
                    "runtime donor index " + name + " differs from binding"
                )
        try:
            contexts = tuple(self.lineage_contexts)
        except (TypeError, ValueError) as exc:
            raise IndexedRuntimeIdentityMismatch("runtime lineage contexts are invalid") from exc
        for context in contexts:
            if not isinstance(context, (CompletedLineageContext, CompletedLineageDiagnostic)):
                raise IndexedRuntimeIdentityMismatch(
                    "runtime lineage contexts must be typed projections"
                )
        context_ids = [item.ledger_identity for item in contexts]
        if len(set(context_ids)) != len(context_ids):
            raise IndexedRuntimeIdentityMismatch(
                "runtime lineage contexts must not repeat a ledger identity"
            )
        if tuple(item.ledger_identity for item in contexts) != tuple(
            sorted(item.ledger_identity for item in contexts)
        ):
            raise IndexedRuntimeIdentityMismatch(
                "runtime lineage contexts must use canonical ledger order"
            )
        object.__setattr__(self, "lineage_contexts", contexts)
        context_ledger_ids = tuple(item.ledger_identity for item in contexts)
        if tuple(self.pattern_report.source_ledgers) != context_ledger_ids:
            raise IndexedRuntimeIdentityMismatch(
                "runtime pattern report sources differ from lineage contexts"
            )
        if not isinstance(self.artifact, ArtifactRef):
            try:
                object.__setattr__(self, "artifact", ArtifactRef.from_dict(self.artifact))
            except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
                raise IndexedRuntimeArtifactError("runtime artifact is invalid") from exc
        payload = self.payload()
        expected_id = hash_canonical(payload)
        if self.runtime_id != expected_id:
            raise IndexedRuntimeIdentityMismatch(
                "runtime_id does not match the complete runtime payload"
            )
        expected_bytes = canonical_bytes(payload)
        expected_path = (
            "artifacts/indexed_runtimes/"
            + self.runtime_id.removeprefix("sha256:")
            + ".json"
        )
        if (
            self.artifact.content_hash != self.runtime_id
            or self.artifact.path != expected_path
            or self.artifact.media_type != "application/json"
            or self.artifact.byte_size != len(expected_bytes)
        ):
            raise IndexedRuntimeIdentityMismatch(
                "runtime artifact identity or metadata differs from payload"
            )

    def payload(self) -> dict[str, Any]:
        return _indexed_runtime_payload(
            binding=self.binding,
            corpus=self.corpus,
            donor_index=self.donor_index,
            pattern_report=self.pattern_report,
            lineage_contexts=self.lineage_contexts,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            **self.payload(),
            "artifact": self.artifact.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "IndexedRuntimeGeneration":
        fields = {
            "runtime_id",
            "protocol",
            "binding",
            "corpus",
            "donor_index",
            "pattern_report",
            "lineage_contexts",
            "artifact",
        }
        if not isinstance(value, Mapping) or set(value) != fields:
            raise IndexedRuntimeIdentityMismatch(
                "runtime generation fields do not match its protocol"
            )
        if value["protocol"] != INDEXED_RUNTIME_PROTOCOL:
            raise IndexedRuntimeIdentityMismatch("unsupported indexed runtime protocol")
        try:
            contexts = tuple(_context_from_dict(item) for item in value["lineage_contexts"])
            return cls(
                runtime_id=value["runtime_id"],
                binding=IndexedRuntimeBinding.from_dict(value["binding"]),
                corpus=CorpusGeneration.from_dict(value["corpus"]),
                donor_index=DonorIndexGeneration.from_dict(value["donor_index"]),
                pattern_report=SearchPatternReport.from_dict(value["pattern_report"]),
                lineage_contexts=contexts,
                artifact=ArtifactRef.from_dict(value["artifact"]),
            )
        except IndexedRuntimeError:
            raise
        except (AttributeError, DonorIndexError, EvidenceIdentityMismatch,
                IntegrationGateError,
                PatternInputError, SearchValidationError, TypeError, ValueError, KeyError) as exc:
            raise IndexedRuntimeIdentityMismatch(
                "runtime generation payload is invalid"
            ) from exc


def _build_generation(
    *,
    repo: Path,
    stage: Path,
    gate_root: Path,
    gate: IntegrationGateReceipt,
    manifest: RunManifest,
    revisions: tuple[DonorRevision, ...],
    source_archive: ContentAddressedArchive,
    scanner_identity: str,
    scanner_source_identity: str,
    signature_identity: str,
    renderer_identity: str,
    renderer_source_identity: str,
) -> IndexedRuntimeGeneration:
    _copy_gate_snapshot(gate_root, stage)
    gate_snapshot_root = stage / "gate"
    gate_archive = ContentAddressedArchive(gate_snapshot_root)
    runtime_archive = ContentAddressedArchive(stage)
    snapshot_roots = _materialize_revision_sources(
        revisions,
        source_archive=source_archive,
        destination_root=stage,
    )
    # This direct loader call is a production boundary, not a fixture shortcut.
    contexts = load_completed_lineage_contexts([gate_snapshot_root])
    report = mine_completed_lineages(
        [gate_snapshot_root],
        output_root=stage,
    )
    entries = _corpus_entries(
        repo=repo,
        gate_root=gate_snapshot_root,
        gate_archive=gate_archive,
        runtime_archive=runtime_archive,
        manifest=manifest,
        contexts=contexts,
        report=report,
    )
    corpus = build_corpus_generation(
        entries,
        integration_gate=gate,
        schema_identity=manifest.schema_identity,
        archive=gate_archive,
    )
    # The corpus builder writes under the gate archive so its canonical
    # validator can inspect manifest and ledger files. Mirror the immutable
    # corpus object into the runtime archive used by later consumers.
    corpus_bytes = gate_archive.verify(corpus.artifact)
    mirrored_corpus = runtime_archive.put_bytes(
        corpus_bytes,
        category="evidence_corpus",
        suffix=".json",
        media_type="application/json",
    )
    if mirrored_corpus != corpus.artifact:
        raise IndexedRuntimeIdentityMismatch(
            "mirrored corpus artifact differs from canonical corpus reference"
        )
    scan_calls = 0

    def scan(revision: DonorRevision) -> Iterable[Any]:
        nonlocal scan_calls
        scan_calls += 1
        return scan_repository_revision(
            revision,
            # Scan only the immutable, archive-verified snapshot.  The
            # caller's checkout is mutable and must never supply pinned bytes.
            repo=snapshot_roots[revision.version],
            archive=runtime_archive,
        )

    indexer_identity = _module_identity(repo, "search_donor_index.py")
    indexer_source_identity = indexer_identity
    donor_index = build_donor_index(
        revisions,
        integration_gate=gate,
        integration_archive=gate_archive,
        scan_revision=scan,
        indexer_identity=indexer_identity,
        indexer_source_identity=indexer_source_identity,
        config_identity=manifest.config_identity,
        signature_identity=signature_identity,
        schema_identity=manifest.schema_identity,
        generation_ordinal=1,
        archive=runtime_archive,
    )
    if scan_calls != len(DONOR_VERSIONS):
        raise IndexedRuntimeScannerError(
            "production donor scanner did not run exactly once per pinned version"
        )
    gate_manifest_bytes = (gate_snapshot_root / "manifest.json").read_bytes()
    gate_ledger_bytes = (gate_snapshot_root / "ledger.jsonl").read_bytes()
    gate_manifest_artifact = runtime_archive.put_bytes(
        gate_manifest_bytes,
        category="gate-manifests",
        suffix=".json",
        media_type="application/json",
    )
    gate_ledger_artifact = runtime_archive.put_bytes(
        gate_ledger_bytes,
        category="gate-ledgers",
        suffix=".jsonl",
        media_type="application/x-ndjson",
    )
    binding = IndexedRuntimeBinding(
        integration_gate=gate,
        integration_gate_id=gate.gate_id,
        manifest_artifact_identity=gate.manifest_artifact_identity,
        subset_identity=gate.subset_identity,
        queue_evidence_identity=gate.queue_evidence_identity,
        selected_lanes=tuple(gate.selected_lanes),
        coordinator_identity=gate.coordinator_identity,
        connector_identity=gate.connector_identity,
        compiler_identity=manifest.compiler_identity,
        config_identity=manifest.config_identity,
        schema_identity=manifest.schema_identity,
        scanner_identity=scanner_identity,
        scanner_source_identity=scanner_source_identity,
        signature_identity=signature_identity,
        renderer_identity=renderer_identity,
        renderer_source_identity=renderer_source_identity,
        revision_set_identity=revision_set_identity(revisions),
        revisions=revisions,
        corpus_generation_id=corpus.generation_id,
        corpus_artifact=corpus.artifact,
        donor_index_generation_id=donor_index.generation_id,
        donor_index_artifact=donor_index.artifact,
        pattern_report_id=report.report_id,
        pattern_report_artifact=report.artifact,
        gate_manifest_artifact=gate_manifest_artifact,
        gate_ledger_artifact=gate_ledger_artifact,
    )
    payload = _indexed_runtime_payload(
        binding=binding,
        corpus=corpus,
        donor_index=donor_index,
        pattern_report=report,
        lineage_contexts=contexts,
    )
    runtime_id = hash_canonical(payload)
    runtime_artifact = ArtifactRef(
        content_hash=runtime_id,
        path=(
            "artifacts/indexed_runtimes/"
            + runtime_id.removeprefix("sha256:")
            + ".json"
        ),
        media_type="application/json",
        byte_size=len(canonical_bytes(payload)),
    )
    generation = IndexedRuntimeGeneration(
        runtime_id=runtime_id,
        binding=binding,
        corpus=corpus,
        donor_index=donor_index,
        pattern_report=report,
        lineage_contexts=tuple(contexts),
        artifact=runtime_artifact,
    )
    archived = runtime_archive.put_json(
        generation.payload(),
        category="indexed_runtimes",
        suffix=".json",
    )
    if archived != generation.artifact:
        raise IndexedRuntimeIdentityMismatch(
            "runtime artifact identity differs from canonical payload"
        )
    _write_exact(
        stage / INDEXED_RUNTIME_GENERATION_FILENAME,
        canonical_bytes(generation.to_dict()),
        label="runtime generation document",
    )
    return generation


def _artifact_manifest(root: Path) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        _reject_symlink(path, "runtime publication")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative == INDEXED_RUNTIME_INTENT_FILENAME:
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise IndexedRuntimeArtifactError(
                "runtime publication file cannot be read"
            ) from exc
        records.append(
            {
                "path": relative,
                "content_hash": hash_bytes(data),
                "byte_size": len(data),
            }
        )
    return tuple(records)


def _verify_file_manifest(
    root: Path,
    records: Sequence[Mapping[str, Any]],
    *,
    immutable_winner: bool = False,
) -> None:
    seen: set[str] = set()
    expected_paths: set[str] = set()
    ordered_paths: list[str] = []
    for record in records:
        if not isinstance(record, Mapping) or set(record) != {
            "path",
            "content_hash",
            "byte_size",
        }:
            raise IndexedRuntimePartialPublication(
                "runtime artifact manifest has an invalid entry"
            )
        relative = record["path"]
        if not isinstance(relative, str) or not relative:
            raise IndexedRuntimePartialPublication(
                "runtime artifact manifest contains an invalid path"
            )
        relative_path = Path(relative)
        if (
            relative_path.is_absolute()
            or relative_path.as_posix() != relative
            or ".." in relative_path.parts
            or relative_path.name in {"", ".", ".."}
        ):
            raise IndexedRuntimePartialPublication(
                "runtime artifact manifest contains an invalid path"
            )
        try:
            path = _contained(root / relative, root, "runtime artifact")
        except IndexedRuntimeInputError as exc:
            raise IndexedRuntimePartialPublication(
                "runtime artifact manifest escapes its root"
            ) from exc
        if relative in seen:
            raise IndexedRuntimePartialPublication(
                "runtime artifact manifest repeats a path"
            )
        seen.add(relative)
        ordered_paths.append(relative)
        expected_paths.add(relative)
        _reject_symlink(path, "runtime artifact")
        if not path.is_file():
            raise IndexedRuntimePartialPublication(
                "runtime artifact is missing: " + relative
            )
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise IndexedRuntimeArtifactError(
                "runtime artifact cannot be read: " + relative
            ) from exc
        try:
            expected_hash = _hash(record["content_hash"], "runtime artifact content_hash")
        except IndexedRuntimeInputError as exc:
            raise IndexedRuntimePartialPublication(
                "runtime artifact manifest hash is invalid"
            ) from exc
        byte_size = record["byte_size"]
        if isinstance(byte_size, bool) or not isinstance(byte_size, int) or byte_size < 0:
            raise IndexedRuntimePartialPublication(
                "runtime artifact manifest byte size is invalid"
            )
        if expected_hash != hash_bytes(data) or byte_size != len(data):
            error_type = (
                IndexedRuntimeCollision
                if immutable_winner
                else IndexedRuntimePartialPublication
            )
            raise error_type(
                "runtime artifact bytes differ from publication intent: " + relative
            )
    actual_paths: set[str] = set()
    if root.is_dir() and not root.is_symlink():
        for path in root.rglob("*"):
            _reject_symlink(path, "runtime artifact")
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                if relative == INDEXED_RUNTIME_INTENT_FILENAME:
                    continue
                actual_paths.add(relative)
    if actual_paths != expected_paths:
        unexpected = sorted(actual_paths - expected_paths)
        missing = sorted(expected_paths - actual_paths)
        detail = []
        if unexpected:
            detail.append("unexpected=" + ",".join(unexpected))
        if missing:
            detail.append("missing=" + ",".join(missing))
        raise IndexedRuntimePartialPublication(
            "runtime artifact manifest does not cover its root (" + "; ".join(detail) + ")"
        )
    if ordered_paths != sorted(ordered_paths):
        raise IndexedRuntimePartialPublication(
            "runtime artifact manifest is not in canonical path order"
        )


def _intent_document(
    *,
    request_identity: str,
    generation: IndexedRuntimeGeneration,
    stage: Path,
    global_root: Path,
) -> dict[str, Any]:
    records = _artifact_manifest(stage)
    try:
        stage_name = stage.relative_to(global_root).as_posix()
    except ValueError as exc:
        raise IndexedRuntimePartialPublication(
            "runtime staging directory is outside canonical archive"
        ) from exc
    return {
        "protocol": INDEXED_RUNTIME_INTENT_PROTOCOL,
        "request_identity": request_identity,
        "runtime_id": generation.runtime_id,
        "generation": generation.to_dict(),
        "staging_path": stage_name,
        "artifacts": list(records),
    }


def _read_intent(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IndexedRuntimePartialPublication("runtime publication intent is corrupt") from exc
    if raw != canonical_bytes(document):
        raise IndexedRuntimePartialPublication(
            "runtime publication intent is not canonical JSON"
        )
    fields = {
        "protocol",
        "request_identity",
        "runtime_id",
        "generation",
        "staging_path",
        "artifacts",
    }
    if not isinstance(document, Mapping) or set(document) != fields:
        raise IndexedRuntimePartialPublication(
            "runtime publication intent fields are invalid"
        )
    if document["protocol"] != INDEXED_RUNTIME_INTENT_PROTOCOL:
        raise IndexedRuntimePartialPublication("unsupported runtime publication intent")
    _hash(document["request_identity"], "request_identity")
    _hash(document["runtime_id"], "runtime_id")
    if not isinstance(document["staging_path"], str) or not document["staging_path"]:
        raise IndexedRuntimePartialPublication("runtime staging path is invalid")
    if not isinstance(document["artifacts"], list):
        raise IndexedRuntimePartialPublication("runtime artifact manifest is invalid")
    paths: list[str] = []
    for item in document["artifacts"]:
        if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
            raise IndexedRuntimePartialPublication(
                "runtime artifact manifest contains an invalid path"
            )
        paths.append(item["path"])
    if paths != sorted(paths):
        raise IndexedRuntimePartialPublication(
            "runtime artifact manifest is not in canonical path order"
        )
    try:
        generation = IndexedRuntimeGeneration.from_dict(document["generation"])
    except IndexedRuntimeError:
        raise
    except (TypeError, ValueError) as exc:
        raise IndexedRuntimePartialPublication("runtime intent generation is invalid") from exc
    if generation.runtime_id != document["runtime_id"]:
        raise IndexedRuntimePartialPublication(
            "runtime intent id differs from embedded generation"
        )
    expected_request = _request_identity(
        generation.binding.integration_gate,
        generation.binding.revisions,
        scanner_identity=generation.binding.scanner_identity,
        signature_identity=generation.binding.signature_identity,
        renderer_identity=generation.binding.renderer_identity,
        renderer_source_identity=generation.binding.renderer_source_identity,
    )
    if document["request_identity"] != expected_request:
        raise IndexedRuntimePartialPublication(
            "runtime intent request identity differs from its generation"
        )
    return dict(document)


def _find_intent(global_root: Path, request_identity: str) -> tuple[Path, dict[str, Any]] | None:
    matches: list[tuple[Path, dict[str, Any]]] = []
    if not global_root.is_dir():
        return None
    for child in sorted(global_root.iterdir()):
        if not child.is_dir() or child.is_symlink() or child.name.startswith("."):
            continue
        intent_path = child / INDEXED_RUNTIME_INTENT_FILENAME
        if not intent_path.is_file() or intent_path.is_symlink():
            continue
        document = _read_intent(intent_path)
        if document["request_identity"] == request_identity:
            matches.append((child, document))
    if len(matches) > 1:
        raise IndexedRuntimeCollision(
            "multiple runtime publications claim the same explicit input set"
        )
    return matches[0] if matches else None


def _stage_from_intent(
    document: Mapping[str, Any],
    *,
    global_root: Path,
) -> Path:
    relative = document["staging_path"]
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise IndexedRuntimePartialPublication("runtime staging path is not relative")
    relative_path = Path(relative)
    if (
        len(relative_path.parts) != 1
        or relative_path.name != relative
        or "\\" in relative
        or relative_path.name in {"", ".", ".."}
    ):
        raise IndexedRuntimePartialPublication("runtime staging path is not canonical")
    raw_stage = global_root / relative
    if raw_stage.is_symlink():
        raise IndexedRuntimePartialPublication("runtime staging path is a symlink")
    stage = _contained(raw_stage, global_root, "runtime staging")
    if stage.parent != global_root:
        raise IndexedRuntimePartialPublication("runtime staging path is not canonical")
    if not stage.name.startswith(_STAGING_PREFIX):
        raise IndexedRuntimePartialPublication("runtime staging path is not canonical")
    return stage


def _remove_completed_stage(stage: Path, *, global_root: Path) -> None:
    """Remove one validated publication stage after its winner is verified."""

    try:
        canonical_root = global_root.resolve(strict=True)
        relative = stage.relative_to(canonical_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise IndexedRuntimePartialPublication(
            "runtime staging path is outside the canonical archive root"
        ) from exc
    if len(relative.parts) != 1 or not stage.name.startswith(_STAGING_PREFIX):
        raise IndexedRuntimePartialPublication("runtime staging path is not canonical")
    if stage.is_symlink():
        raise IndexedRuntimePartialPublication("runtime staging path is a symlink")
    if not stage.exists():
        _fsync_directory(canonical_root)
        return
    if not stage.is_dir():
        raise IndexedRuntimePartialPublication("runtime staging path is not a directory")
    try:
        shutil.rmtree(stage)
    except OSError as exc:
        raise IndexedRuntimeArtifactError(
            "completed runtime staging directory cannot be removed"
        ) from exc
    _fsync_directory(canonical_root)


def _copy_stage(stage: Path, destination: Path) -> None:
    if not stage.is_dir() or stage.is_symlink():
        raise IndexedRuntimePartialPublication(
            "runtime publication stage is missing"
        )
    destination.mkdir(parents=True, exist_ok=True)
    _reject_symlink(destination, "runtime generation")
    for path in sorted(stage.rglob("*")):
        _reject_symlink(path, "runtime publication stage")
        relative = path.relative_to(stage)
        target = destination / relative
        _contained(target, destination, "runtime publication destination")
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            _reject_symlink(target, "runtime generation destination")
        elif path.is_file():
            try:
                data = path.read_bytes()
            except OSError as exc:
                raise IndexedRuntimePartialPublication(
                    "runtime publication stage file cannot be read"
                ) from exc
            _write_exact(target, data, label="runtime generation artifact")
        else:
            raise IndexedRuntimePartialPublication(
                "runtime publication stage contains an unsupported entry"
            )


def _resume_publication(
    runtime_directory: Path,
    document: Mapping[str, Any],
    *,
    global_root: Path,
    repo: Path,
) -> IndexedRuntimeGeneration:
    generation = IndexedRuntimeGeneration.from_dict(document["generation"])
    records = document["artifacts"]
    # A completed destination is already the immutable winner.  Retried
    # callers must be able to load it even after a successful process cleaned
    # up its private stage, and this path must not invoke any builder or scan.
    generation_path = runtime_directory / INDEXED_RUNTIME_GENERATION_FILENAME
    intent_path = runtime_directory / INDEXED_RUNTIME_INTENT_FILENAME
    if (
        runtime_directory.is_dir()
        and not runtime_directory.is_symlink()
        and intent_path.is_file()
        and not intent_path.is_symlink()
        and generation_path.is_file()
        and not generation_path.is_symlink()
    ):
        try:
            raw_generation = generation_path.read_bytes()
            generation_document = json.loads(raw_generation.decode("utf-8"))
            if raw_generation != canonical_bytes(generation_document):
                raise IndexedRuntimePartialPublication(
                    "runtime generation document is not canonical JSON"
                )
            existing = IndexedRuntimeGeneration.from_dict(generation_document)
            if existing != generation:
                raise IndexedRuntimeCollision(
                    "runtime destination contains a different canonical generation"
                )
            _verify_file_manifest(
                runtime_directory,
                records,
                immutable_winner=True,
            )
            verify_indexed_runtime(existing, repo=repo)
        except IndexedRuntimeCollision:
            raise
        except (OSError, UnicodeDecodeError, json.JSONDecodeError,
                IndexedRuntimeError, TypeError, ValueError):
            # Fall through to the durable stage.  A differing existing file
            # remains immutable and will be reported as a collision during the
            # stage copy instead of being silently replaced.
            pass
        else:
            _remove_completed_stage(
                _stage_from_intent(document, global_root=global_root),
                global_root=global_root,
            )
            return existing

    stage = _stage_from_intent(document, global_root=global_root)
    _verify_file_manifest(stage, records)
    runtime_directory.mkdir(parents=True, exist_ok=True)
    _reject_symlink(runtime_directory, "runtime generation")
    _copy_stage(stage, runtime_directory)
    _write_exact(
        runtime_directory / INDEXED_RUNTIME_INTENT_FILENAME,
        canonical_bytes(document),
        label="runtime publication intent",
    )
    _verify_file_manifest(runtime_directory, records)
    verify_indexed_runtime(generation, repo=repo)
    _remove_completed_stage(stage, global_root=global_root)
    return generation


def publish_indexed_runtime(
    gate_run_id: str,
    revisions: Sequence[DonorRevision],
    *,
    repo: Path | str,
) -> IndexedRuntimeGeneration:
    """Publish or resume one immutable runtime for explicit inputs."""

    repo_root = _repo_root(repo)
    gate_root, gate_archive, gate, manifest = _load_gate(repo_root, gate_run_id)
    ordered = _normalize_revisions(revisions)
    source_archive = _resolve_revision_archive(repo_root, ordered, gate_archive)
    scanner_identity = _module_identity(repo_root, "search_donor_scan.py")
    scanner_source_identity = scanner_identity
    # Canonical hashing and identity validation are the runtime's signature
    # authority.  Require the production module itself, instead of deriving a
    # plausible signature when that implementation is absent.
    signature_module_identities = {
        name: _module_identity(repo_root, name)
        for name in (
            "search_types.py",
            "search_patterns.py",
            "search_evidence_corpus.py",
            "search_semantic_signatures.py",
        )
    }
    signature_identity = hash_canonical(
        {
            "protocol": "sotn-indexed-runtime-signature-v1",
            "scanner_identity": scanner_identity,
            "signature_module_identities": signature_module_identities,
            "config_identity": manifest.config_identity,
            "schema_identity": manifest.schema_identity,
        }
    )
    renderer_identity, renderer_source_identity = _renderer_identities(repo_root)
    request_identity = _request_identity(
        gate,
        ordered,
        scanner_identity=scanner_identity,
        signature_identity=signature_identity,
        renderer_identity=renderer_identity,
        renderer_source_identity=renderer_source_identity,
    )
    global_root = _runtime_global_root(repo_root, create=True)
    existing = _find_intent(global_root, request_identity)
    if existing is not None:
        runtime_directory, document = existing
        return _resume_publication(
            runtime_directory,
            document,
            global_root=global_root,
            repo=repo_root,
        )

    stage: Optional[Path] = None
    intent_written = False
    try:
        stage = Path(
            tempfile.mkdtemp(prefix=_STAGING_PREFIX, dir=str(global_root))
        ).resolve(strict=True)
        generation = _build_generation(
            repo=repo_root,
            stage=stage,
            gate_root=gate_root,
            gate=gate,
            manifest=manifest,
            revisions=ordered,
            source_archive=source_archive,
            scanner_identity=scanner_identity,
            scanner_source_identity=scanner_source_identity,
            signature_identity=signature_identity,
            renderer_identity=renderer_identity,
            renderer_source_identity=renderer_source_identity,
        )
        runtime_directory = _runtime_directory(
            repo_root, generation.runtime_id, create=True
        )
        if runtime_directory.exists() and any(runtime_directory.iterdir()):
            raise IndexedRuntimeCollision(
                "runtime identity already has a publication without matching intent"
            )
        document = _intent_document(
            request_identity=request_identity,
            generation=generation,
            stage=stage,
            global_root=global_root,
        )
        _write_exact(
            runtime_directory / INDEXED_RUNTIME_INTENT_FILENAME,
            canonical_bytes(document),
            label="runtime publication intent",
        )
        intent_written = True
        return _resume_publication(
            runtime_directory,
            document,
            global_root=global_root,
            repo=repo_root,
        )
    except Exception:
        if stage is not None and not intent_written:
            try:
                shutil.rmtree(stage)
            except OSError:
                pass
        raise


def _verify_runtime_children(runtime_directory: Path) -> None:
    allowed = {
        INDEXED_RUNTIME_INTENT_FILENAME,
        INDEXED_RUNTIME_GENERATION_FILENAME,
        "artifacts",
        "gate",
        "snapshots",
        "sources",
    }
    for child in runtime_directory.iterdir():
        if child.name not in allowed:
            raise IndexedRuntimeArtifactError(
                "runtime generation contains an unexpected top-level entry: "
                + child.name
            )
        _reject_symlink(child, "runtime generation")


def _iter_artifact_refs(value: Any) -> Iterable[ArtifactRef]:
    """Yield every typed artifact reference nested in a runtime payload."""

    if isinstance(value, ArtifactRef):
        yield value
        return
    if isinstance(value, Mapping):
        if set(value) == {"content_hash", "path", "media_type", "byte_size"}:
            try:
                yield ArtifactRef.from_dict(value)
            except (AttributeError, SearchValidationError, TypeError, ValueError) as exc:
                raise IndexedRuntimeArtifactError(
                    "runtime contains an invalid embedded artifact reference"
                ) from exc
            return
        for item in value.values():
            yield from _iter_artifact_refs(item)
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            yield from _iter_artifact_refs(item)


def _verify_embedded_artifacts(
    runtime_archive: ContentAddressedArchive,
    generation: IndexedRuntimeGeneration,
) -> None:
    """Verify every artifact reference carried by the typed generation."""

    seen: set[tuple[str, str, str, int]] = set()
    for reference in _iter_artifact_refs(generation.to_dict()):
        key = (
            reference.content_hash,
            reference.path,
            reference.media_type,
            reference.byte_size,
        )
        if key in seen:
            continue
        seen.add(key)
        try:
            runtime_archive.verify(reference)
        except (ArchiveError, SearchValidationError, TypeError, ValueError) as exc:
            raise IndexedRuntimeArtifactError(
                "runtime embedded artifact is missing or corrupt: " + reference.path
            ) from exc


def _verify_renderer_bindings(
    generation: IndexedRuntimeGeneration,
    repo: Path,
) -> None:
    """Reject a runtime whose renderer code or algorithm has gone stale."""

    renderer_identity, renderer_source_identity = _renderer_identities(repo)
    binding = generation.binding
    if binding.renderer_identity != renderer_identity:
        raise IndexedRuntimeIdentityMismatch(
            "runtime renderer algorithm identity is stale"
        )
    if binding.renderer_source_identity != renderer_source_identity:
        raise IndexedRuntimeIdentityMismatch(
            "runtime renderer source identity is stale"
        )


def verify_indexed_runtime(
    generation: IndexedRuntimeGeneration,
    *,
    repo: Path | str,
) -> None:
    """Verify one runtime and every nested artifact without rescanning."""

    repo_root = _repo_root(repo)
    if not isinstance(generation, IndexedRuntimeGeneration):
        try:
            generation = IndexedRuntimeGeneration.from_dict(generation)
        except (TypeError, ValueError) as exc:
            raise IndexedRuntimeIdentityMismatch("runtime generation is not typed") from exc
    runtime_directory = _runtime_directory(repo_root, generation.runtime_id)
    if not runtime_directory.is_dir() or runtime_directory.is_symlink():
        raise IndexedRuntimeArtifactError("runtime generation directory is missing")
    _verify_renderer_bindings(generation, repo_root)
    _verify_runtime_children(runtime_directory)
    intent_path = runtime_directory / INDEXED_RUNTIME_INTENT_FILENAME
    generation_path = runtime_directory / INDEXED_RUNTIME_GENERATION_FILENAME
    document = _read_intent(intent_path)
    if document["runtime_id"] != generation.runtime_id:
        raise IndexedRuntimeIdentityMismatch("runtime intent id differs from generation")
    try:
        intent_generation = IndexedRuntimeGeneration.from_dict(document["generation"])
    except IndexedRuntimeError:
        raise
    if intent_generation != generation:
        raise IndexedRuntimeIdentityMismatch(
            "runtime intent generation differs from supplied generation"
        )
    records = document["artifacts"]
    _verify_file_manifest(runtime_directory, records)
    try:
        generation_document = json.loads(generation_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IndexedRuntimeArtifactError("runtime generation document is corrupt") from exc
    try:
        if generation_path.read_bytes() != canonical_bytes(generation_document):
            raise IndexedRuntimeIdentityMismatch(
                "runtime generation document is not canonical JSON"
            )
    except OSError as exc:
        raise IndexedRuntimeArtifactError("runtime generation document is unreadable") from exc
    if generation_document != generation.to_dict():
        raise IndexedRuntimeIdentityMismatch(
            "runtime generation document differs from its typed identity"
        )
    runtime_archive = ContentAddressedArchive(runtime_directory)
    _verify_embedded_artifacts(runtime_archive, generation)
    try:
        raw_runtime = runtime_archive.verify(generation.artifact)
    except ArchiveError as exc:
        raise IndexedRuntimeArtifactError("runtime generation artifact is missing or corrupt") from exc
    if raw_runtime != canonical_bytes(generation.payload()):
        raise IndexedRuntimeIdentityMismatch(
            "runtime generation artifact differs from its canonical payload"
        )
    for reference in (
        generation.binding.integration_gate.receipt_artifact,
        generation.binding.corpus_artifact,
        generation.binding.donor_index_artifact,
        generation.binding.pattern_report_artifact,
        generation.binding.gate_manifest_artifact,
        generation.binding.gate_ledger_artifact,
    ):
        try:
            runtime_archive.verify(reference)
        except ArchiveError as exc:
            raise IndexedRuntimeArtifactError(
                "runtime referenced artifact is missing or corrupt: " + reference.path
            ) from exc
    gate_root = runtime_directory / "gate"
    gate_archive = ContentAddressedArchive(gate_root)
    try:
        manifest = validate_integration_gate(
            generation.binding.integration_gate,
            archive=gate_archive,
        )
    except IntegrationGateError as exc:
        raise IndexedRuntimeArtifactError(
            "snapshotted integration gate failed validation"
        ) from exc
    if manifest.compiler_identity != generation.binding.compiler_identity:
        raise IndexedRuntimeIdentityMismatch("runtime compiler identity is stale")
    if manifest.config_identity != generation.binding.config_identity:
        raise IndexedRuntimeIdentityMismatch("runtime configuration identity is stale")
    if manifest.schema_identity != generation.binding.schema_identity:
        raise IndexedRuntimeIdentityMismatch("runtime schema identity is stale")
    snapshots_root = runtime_directory / "snapshots"
    _reject_symlink(snapshots_root, "donor snapshot root")
    if not snapshots_root.is_dir():
        raise IndexedRuntimeArtifactError("runtime donor snapshots are missing")
    actual_versions = {
        child.name
        for child in snapshots_root.iterdir()
        if child.is_dir() and not child.is_symlink()
    }
    expected_versions = set(DONOR_VERSIONS)
    if actual_versions != expected_versions:
        raise IndexedRuntimeArtifactError(
            "runtime donor snapshot versions differ from pinned revisions"
        )
    for revision in generation.binding.revisions:
        _validate_snapshot_manifest(
            revision,
            archive=runtime_archive,
            snapshot_root=snapshots_root / revision.version,
        )
    try:
        manifest_document = json.loads(
            runtime_archive.verify(generation.binding.gate_manifest_artifact).decode("utf-8")
        )
        archived_manifest = RunManifest.from_dict(manifest_document)
    except (ArchiveError, UnicodeDecodeError, json.JSONDecodeError,
            SearchValidationError, TypeError, ValueError) as exc:
        raise IndexedRuntimeArtifactError("runtime gate manifest artifact is corrupt") from exc
    if archived_manifest != manifest:
        raise IndexedRuntimeIdentityMismatch(
            "runtime gate manifest artifact differs from snapshotted manifest"
        )
    try:
        gate_ledger = (gate_root / "ledger.jsonl").read_bytes()
        archived_ledger = runtime_archive.verify(generation.binding.gate_ledger_artifact)
    except (OSError, ArchiveError) as exc:
        raise IndexedRuntimeArtifactError("runtime gate ledger artifact is corrupt") from exc
    if gate_ledger != archived_ledger:
        raise IndexedRuntimeIdentityMismatch(
            "runtime gate ledger artifact differs from snapshotted ledger"
        )
    try:
        corpus_raw = runtime_archive.verify(generation.corpus.artifact)
    except ArchiveError as exc:
        raise IndexedRuntimeArtifactError("runtime corpus artifact is corrupt") from exc
    if corpus_raw != canonical_bytes(generation.corpus.payload()):
        raise IndexedRuntimeIdentityMismatch("runtime corpus artifact differs from generation")
    try:
        donor_raw = runtime_archive.verify(generation.donor_index.artifact)
    except ArchiveError as exc:
        raise IndexedRuntimeArtifactError("runtime donor index artifact is corrupt") from exc
    if donor_raw != canonical_bytes(generation.donor_index.payload()):
        raise IndexedRuntimeIdentityMismatch(
            "runtime donor index artifact differs from generation"
        )
    try:
        loaded_report = load_report_artifact(
            generation.pattern_report,
            artifact_root=runtime_directory,
            expected_hash=generation.pattern_report.report_id,
        )
    except (ArchiveError, PatternInputError) as exc:
        raise IndexedRuntimeArtifactError("runtime pattern report is corrupt") from exc
    if loaded_report != generation.pattern_report:
        raise IndexedRuntimeIdentityMismatch(
            "runtime pattern report differs from generation"
        )


def load_indexed_runtime(
    runtime_id: str,
    *,
    repo: Path | str,
) -> IndexedRuntimeGeneration:
    """Load one explicitly named runtime generation and verify it."""

    repo_root = _repo_root(repo)
    _hash(runtime_id, "runtime_id")
    runtime_directory = _runtime_directory(repo_root, runtime_id)
    if not runtime_directory.is_dir() or runtime_directory.is_symlink():
        raise IndexedRuntimeArtifactError("runtime generation directory is missing")
    generation_path = runtime_directory / INDEXED_RUNTIME_GENERATION_FILENAME
    try:
        raw_generation = generation_path.read_bytes()
        value = json.loads(raw_generation.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IndexedRuntimeArtifactError("runtime generation document is unreadable") from exc
    if raw_generation != canonical_bytes(value):
        raise IndexedRuntimeIdentityMismatch(
            "runtime generation document is not canonical JSON"
        )
    try:
        generation = IndexedRuntimeGeneration.from_dict(value)
    except IndexedRuntimeError:
        raise
    except (TypeError, ValueError) as exc:
        raise IndexedRuntimeIdentityMismatch("runtime generation document is invalid") from exc
    if generation.runtime_id != runtime_id:
        raise IndexedRuntimeIdentityMismatch(
            "runtime generation document does not match requested runtime_id"
        )
    verify_indexed_runtime(generation, repo=repo_root)
    return generation


__all__ = [
    "INDEXED_RUNTIME_PROTOCOL",
    "INDEXED_RUNTIME_INTENT_PROTOCOL",
    "INDEXED_RUNTIME_ROOT",
    "DONOR_SNAPSHOT_ARCHIVE_ROOT",
    "DONOR_SNAPSHOT_MANIFEST_PROTOCOL",
    "DONOR_SNAPSHOT_MANIFEST_FILENAME",
    "SCANNER_INTERFACE",
    "IndexedRuntimeError",
    "IndexedRuntimeInputError",
    "IndexedRuntimeArtifactError",
    "IndexedRuntimeIdentityMismatch",
    "IndexedRuntimeCollision",
    "IndexedRuntimePartialPublication",
    "IndexedRuntimeScannerError",
    "RuntimeInputError",
    "RuntimeArtifactError",
    "RuntimeIdentityMismatch",
    "RuntimeCollision",
    "PartialPublication",
    "DonorSnapshotFile",
    "DonorSnapshot",
    "IndexedRuntimeBinding",
    "IndexedRuntimeGeneration",
    "scan_repository_revision",
    "publish_donor_snapshots",
    "publish_indexed_runtime",
    "load_indexed_runtime",
    "verify_indexed_runtime",
]
