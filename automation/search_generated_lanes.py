"""Production providers for the generated search lanes.

The generated lanes are intentionally proposal-only.  They consume an explicit,
archive-verified target snapshot and return the ordinary read-only callback
shape used by :mod:`search_lanes`.  They never read the queue, inspect a
checkout, invoke a compiler, or write an artifact.  A factory performs all
external work once, freezes the resulting values, and leaves a stateless
callback behind for deterministic replay.

Two providers live here because they have different input contracts:

``m2c_ensemble``
    Runs an explicitly pinned matrix of m2c revisions over target assembly
    bytes.  A revision is unavailable unless its source and tool artifacts are
    present in the supplied content-addressed archive and its immutable
    qualification identity is bound to the typed revision provider.

``bounded_synthesis``
    Enumerates only declarations, expressions, statements, declaration shapes,
    and control-flow forms already present in the target snapshot.  A frozen
    :class:`SynthesisBound` limits every product before candidates reach the
    ordinary lane normalizer.

The callbacks are deliberately ordinary one-argument functions.  The later
factory and supervisor layers can place them in ``LaneAdapters`` without a
second result or receipt protocol.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Optional

try:  # package imports
    from .m2c_revision_provider import (
        CURRENT_M2C_REVISION,
        M2CDraftPayload,
        M2CInvocation,
        M2CProviderError,
        M2CRevisionIdentity,
        M2CRevisionProvider,
        make_invocation,
    )
    from .search_archive import ArchiveError, ArtifactRef, ContentAddressedArchive
    from .m2c_revision_matrix import (
        M2CMatrixError,
        M2CMatrixReceipt,
        M2CRevisionPin,
        load_m2c_matrix_receipt,
        to_generated_m2c_matrix,
        verify_m2c_matrix_receipt,
    )
    from .search_supervisor import EVALUATOR_TOOL_KEY
    from .search_lanes import (
        LaneCandidate,
        LaneError,
        Recipient,
        SubsetViolation,
    )
    from .search_types import (
        Budget,
        CandidateRecord,
        LANES,
        RunManifest,
        SearchValidationError,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_relative_path,
    )
except ImportError:  # direct invocation from the automation directory
    from m2c_revision_provider import (  # type: ignore
        CURRENT_M2C_REVISION,
        M2CDraftPayload,
        M2CInvocation,
        M2CProviderError,
        M2CRevisionIdentity,
        M2CRevisionProvider,
        make_invocation,
    )
    from search_archive import ArchiveError, ArtifactRef, ContentAddressedArchive  # type: ignore
    from m2c_revision_matrix import (  # type: ignore
        M2CMatrixError,
        M2CMatrixReceipt,
        M2CRevisionPin,
        load_m2c_matrix_receipt,
        to_generated_m2c_matrix,
        verify_m2c_matrix_receipt,
    )
    from search_supervisor import EVALUATOR_TOOL_KEY  # type: ignore
    from search_lanes import LaneCandidate, LaneError, Recipient, SubsetViolation  # type: ignore
    from search_types import (  # type: ignore
        Budget,
        CandidateRecord,
        LANES,
        RunManifest,
        SearchValidationError,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_relative_path,
    )


M2C_LANE = "m2c_ensemble"
SYNTHESIS_LANE = "bounded_synthesis"
GENERATED_LANES = frozenset({M2C_LANE, SYNTHESIS_LANE})
SUPPORTED_TARGET_PLATFORMS = ("us", "hd", "pspeu", "saturn")
M2C_PROVIDER_PROTOCOL = "sotn-m2c-ensemble-provider-v1"
SYNTHESIS_PROVIDER_PROTOCOL = "sotn-bounded-synthesis-provider-v1"
TARGET_INPUT_PROTOCOL = "sotn-generated-target-input-v1"
SYNTHESIS_BOUND_PROTOCOL = "sotn-bounded-synthesis-bound-v1"
MODULE_IDENTITY = hash_canonical(
    {
        "module": "automation.search_generated_lanes",
        "protocols": [M2C_PROVIDER_PROTOCOL, SYNTHESIS_PROVIDER_PROTOCOL],
        "version": "1.0.0",
    }
)

_C_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PLATFORM_RE = re.compile(r"^(us|hd|pspeu|saturn)$")
_HEX_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_MAX_TARGET_BYTES = 16 * 1024 * 1024
_MAX_FRAGMENT_BYTES = 4096
_MAX_RAW_OUTPUTS_PER_REVISION = 512
_MAX_REVISIONS = 32
_MAX_TARGETS = 4096
_DEFAULT_SYNTHESIS_BOUND = 32

_FORBIDDEN_TARGET_KEYS = frozenset(
    {
        "body",
        "source",
        "source_code",
        "source_bytes",
        "register",
        "registers",
        "relocation",
        "relocations",
        "branch_displacement",
        "branch_displacements",
        "displacement",
        "displacements",
        "raw_bytes",
        "object_bytes",
    }
)
_ALLOWED_DECLARATION_KEYS = frozenset(
    {
        "return_type",
        "result_type",
        "parameters",
        "params",
        "prototype",
        "signature",
        "locals",
        "declaration_shapes",
    }
)


class GeneratedProviderError(LaneError):
    """Base class for generated-provider failures."""


class GeneratedProviderInputError(GeneratedProviderError):
    """A target, manifest, bound, or revision is malformed."""


class GeneratedProviderArtifactError(GeneratedProviderInputError):
    """An archive-owned input is absent, changed, or outside its contract."""


class GeneratedProviderUnavailable(GeneratedProviderError):
    """A provider cannot run because an explicitly named dependency is absent."""


class GeneratedProviderDeterminismError(GeneratedProviderError):
    """A provider runner returned a non-deterministic or stateful result."""


class GeneratedProviderBudgetError(GeneratedProviderInputError):
    """The immutable manifest budget cannot represent this provider."""


class GeneratedProviderSubsetViolation(SubsetViolation):
    """A callback was asked to process a recipient outside its frozen subset."""


def _identity(value: Any, label: str) -> str:
    try:
        return validate_hash(value, label)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise GeneratedProviderInputError(f"{label} must be a sha256 identity") from exc


def _freeze_json(value: Any, label: str) -> Any:
    """Freeze JSON-shaped input while refusing donor-only context."""

    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise GeneratedProviderInputError(f"{label} keys must be strings")
            lowered = key.lower()
            if lowered in _FORBIDDEN_TARGET_KEYS or any(
                token in lowered
                for token in ("register", "relocat", "displacement", "raw_bytes")
            ):
                raise GeneratedProviderInputError(
                    f"{label}.{key} contains forbidden donor-specific context"
                )
            frozen[key] = _freeze_json(item, f"{label}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_json(item, f"{label}[{index}]") for index, item in enumerate(value))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise GeneratedProviderInputError(f"{label} contains a non-JSON value")


def _freeze_provenance(value: Any, label: str) -> Any:
    """Deep-freeze already validated provenance without key filtering."""

    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise GeneratedProviderInputError(f"{label} keys must be strings")
        return MappingProxyType(
            {key: _freeze_provenance(item, f"{label}.{key}") for key, item in value.items()}
        )
    if isinstance(value, (tuple, list)):
        return tuple(
            _freeze_provenance(item, f"{label}[{index}]")
            for index, item in enumerate(value)
        )
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise GeneratedProviderInputError(f"{label} contains a non-JSON value")


def _plain(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if isinstance(value, bytes):
        return {"sha256": hash_bytes(value), "byte_size": len(value)}
    if dataclasses.is_dataclass(value):
        return {
            item.name: _plain(getattr(value, item.name))
            for item in dataclasses.fields(value)
        }
    return value


def _safe_fragment(value: Any, label: str, *, allow_semicolon: bool = False) -> str:
    if not isinstance(value, str):
        raise GeneratedProviderInputError(f"{label} must be nonempty text")
    value = value.strip()
    if not value:
        raise GeneratedProviderInputError(f"{label} must be nonempty text")
    encoded = value.encode("utf-8")
    if len(encoded) > _MAX_FRAGMENT_BYTES:
        raise GeneratedProviderInputError(f"{label} is too large")
    if "\x00" in value or "/*" in value or "//" in value or "#include" in value:
        raise GeneratedProviderInputError(f"{label} contains unsafe source syntax")
    if not allow_semicolon and ";" in value:
        raise GeneratedProviderInputError(f"{label} must not contain a semicolon")
    return value.strip()


def _unique_fragments(values: Any, label: str, *, allow_semicolon: bool = False) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, (tuple, list)):
        raise GeneratedProviderInputError(f"{label} must be an explicit list or tuple")
    result = tuple(
        _safe_fragment(value, f"{label}[{index}]", allow_semicolon=allow_semicolon)
        for index, value in enumerate(values)
    )
    if len(set(result)) != len(result):
        raise GeneratedProviderInputError(f"{label} must not contain duplicates")
    return tuple(sorted(result))


def _artifact(value: Any, label: str) -> ArtifactRef:
    if isinstance(value, ArtifactRef):
        return value
    try:
        return ArtifactRef.from_dict(value)
    except (AttributeError, KeyError, SearchValidationError, TypeError, ValueError) as exc:
        raise GeneratedProviderArtifactError(f"{label} is not an ArtifactRef") from exc


def _validate_target_artifact(reference: ArtifactRef) -> None:
    digest = reference.content_hash.removeprefix("sha256:")
    if reference.media_type != "text/x-asm" or reference.path != f"artifacts/target-assembly/{digest}.s":
        raise GeneratedProviderArtifactError(
            "target artifact must be the canonical archived target assembly"
        )


def _verify_archive_bytes(
    archive: ContentAddressedArchive,
    reference: ArtifactRef,
    expected: bytes,
    label: str,
) -> None:
    if not isinstance(archive, ContentAddressedArchive):
        raise GeneratedProviderArtifactError(
            "generated providers require an explicit ContentAddressedArchive"
        )
    try:
        observed = archive.verify(reference)
    except (ArchiveError, OSError, TypeError, ValueError) as exc:
        raise GeneratedProviderArtifactError(f"{label} is missing or corrupt") from exc
    if observed != expected:
        raise GeneratedProviderArtifactError(f"{label} bytes disagree with its archive")


def _verify_archive_reference(
    archive: ContentAddressedArchive,
    reference: ArtifactRef,
    label: str,
) -> bytes:
    """Verify an archive-owned dependency and normalize archive errors."""

    if not isinstance(archive, ContentAddressedArchive):
        raise GeneratedProviderArtifactError(
            "generated providers require an explicit ContentAddressedArchive"
        )
    try:
        observed = archive.verify(reference)
    except (ArchiveError, OSError, TypeError, ValueError) as exc:
        raise GeneratedProviderArtifactError(f"{label} is missing or corrupt") from exc
    if hash_bytes(observed) != reference.content_hash or len(observed) != reference.byte_size:
        raise GeneratedProviderArtifactError(f"{label} identity does not match its bytes")
    return observed


def _coerce_manifest(value: Any) -> RunManifest:
    if isinstance(value, RunManifest):
        return value
    if isinstance(value, Mapping):
        try:
            return RunManifest.from_dict(value)
        except (SearchValidationError, TypeError, ValueError) as exc:
            raise GeneratedProviderInputError("generated provider needs a valid RunManifest") from exc
    raise GeneratedProviderInputError("generated provider needs a typed RunManifest")


@dataclass(frozen=True)
class _M2CQualificationBinding:
    """Validated prior matrix qualification and its canonical generated matrix."""

    receipt: M2CMatrixReceipt
    matrix: M2CRevisionMatrix
    matrix_identity: str
    runner_identities: tuple[tuple[str, str], ...]
    evaluator_identity: str
    scorer_taxonomy_identity: str


def _load_m2c_matrix_receipt(
    value: Any,
    *,
    archive: ContentAddressedArchive,
) -> M2CMatrixReceipt:
    """Load and archive-verify a completed prior matrix receipt.

    This boundary is intentionally read-only.  The matrix module's verifier
    checks the receipt payload and every archived object it references.  It
    never repairs a missing object or replays a matrix.
    """

    if not isinstance(archive, ContentAddressedArchive):
        raise GeneratedProviderArtifactError(
            "m2c qualification requires a ContentAddressedArchive"
        )
    try:
        if isinstance(value, M2CMatrixReceipt):
            receipt = value
            verify_m2c_matrix_receipt(receipt, archive=archive)
        elif isinstance(value, (ArtifactRef, Mapping)):
            receipt = load_m2c_matrix_receipt(value, archive=archive)
        else:
            raise GeneratedProviderInputError(
                "m2c qualification requires a typed matrix receipt or archive reference"
            )
    except GeneratedProviderError:
        raise
    except (M2CMatrixError, ArchiveError, OSError, SearchValidationError, TypeError, ValueError) as exc:
        raise GeneratedProviderArtifactError(
            "m2c qualification receipt is missing, corrupt, or unverifiable"
        ) from exc
    if receipt.status != "complete" or receipt.refusal_code is not None:
        raise GeneratedProviderUnavailable(
            "m2c qualification receipt is not a completed qualification"
        )
    if len(receipt.revision_ids) not in (2, 3):
        raise GeneratedProviderUnavailable(
            "m2c qualification receipt is not a qualified two-or-three revision matrix"
        )
    return receipt


def _explicit_runner_identities(
    value: Any,
    label: str,
) -> dict[str, str]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        items = tuple(value.items())
    elif isinstance(value, (tuple, list)):
        items = tuple(value)
    else:
        raise GeneratedProviderInputError(
            f"{label} must be a mapping or sequence of revision/runner pairs"
        )
    result: dict[str, str] = {}
    for item in items:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            revision_id, runner_identity = item
        else:
            raise GeneratedProviderInputError(
                f"{label} must contain revision/runner pairs"
            )
        if not isinstance(revision_id, str):
            raise GeneratedProviderInputError(f"{label} revision id must be text")
        if revision_id in result:
            raise GeneratedProviderInputError(
                f"{label} must not repeat a revision id"
            )
        result[revision_id] = _identity(runner_identity, f"{label} runner identity")
    return result


def _generated_matrix_from_inputs(
    revisions: Sequence[M2CRevision] | M2CRevisionMatrix | Sequence[M2CRevisionPin],
    *,
    runner_identities: Any = None,
) -> tuple[M2CRevisionMatrix, tuple[tuple[str, str], ...]]:
    """Convert typed pins through the canonical matrix conversion path."""

    if isinstance(revisions, M2CRevisionMatrix):
        raw = revisions.revisions
    elif isinstance(revisions, (tuple, list)):
        raw = tuple(revisions)
    else:
        raise GeneratedProviderInputError(
            "m2c revisions must be an explicit typed sequence"
        )
    if not raw:
        raise GeneratedProviderInputError("m2c revisions must not be empty")
    explicit_runners = _explicit_runner_identities(
        runner_identities, "m2c runner identities"
    )
    pins: list[M2CRevisionPin] = []
    runner_pairs: dict[str, str] = {}
    if all(isinstance(item, M2CRevisionPin) for item in raw):
        for pin in raw:
            runner = _identity(pin.runner_identity, f"m2c runner {pin.revision_id}")
            declared = explicit_runners.get(pin.revision_id)
            if declared is not None and declared != runner:
                raise GeneratedProviderDeterminismError(
                    f"m2c runner identity differs for revision {pin.revision_id}"
                )
            runner_pairs[pin.revision_id] = runner
            pins.append(pin)
    elif all(isinstance(item, M2CRevision) for item in raw):
        for item in raw:
            runner = explicit_runners.get(item.revision_id, item.provider_identity)
            runner = _identity(runner, f"m2c runner {item.revision_id}")
            runner_pairs[item.revision_id] = runner
            try:
                pins.append(
                    M2CRevisionPin(
                        revision=item.revision_identity,
                        source_artifact=item.source_artifact,
                        tool_artifact=item.tool_artifact,
                        runner_identity=runner,
                        available=item.available,
                        unavailable_reason=item.unavailable_reason,
                    )
                )
            except (M2CMatrixError, TypeError, ValueError) as exc:
                raise GeneratedProviderInputError(
                    f"m2c revision {item.revision_id} cannot become a typed pin"
                ) from exc
    else:
        raise GeneratedProviderInputError(
            "m2c revisions must contain only typed revision pins or revisions"
        )
    try:
        # Do not duplicate matrix ordering here.  This is the canonical
        # conversion owned by the qualified matrix module.
        matrix = to_generated_m2c_matrix(tuple(pins))
    except (M2CMatrixError, TypeError, ValueError) as exc:
        raise GeneratedProviderInputError(
            "m2c revisions cannot be converted through the canonical matrix path"
        ) from exc
    if not isinstance(matrix, M2CRevisionMatrix):
        raise GeneratedProviderDeterminismError(
            "canonical matrix conversion returned an untyped matrix"
        )
    ordered_runners = tuple(
        sorted(
            (
                item.revision_id,
                runner_pairs[item.revision_id],
            )
            for item in matrix.revisions
            if item.revision_id in runner_pairs
        )
    )
    if len(ordered_runners) != len(matrix.revisions):
        raise GeneratedProviderInputError(
            "canonical matrix conversion dropped a qualified runner identity"
        )
    return matrix, ordered_runners


def _validate_matrix_receipt_revision_binding(
    receipt: M2CMatrixReceipt,
    matrix: M2CRevisionMatrix,
    runner_pairs: tuple[tuple[str, str], ...],
    *,
    archive: ContentAddressedArchive,
    archive_identity: str,
    config_identity: Optional[str] = None,
    compiler_identity: Optional[str] = None,
    evaluator_identity: Optional[str] = None,
    scorer_taxonomy_identity: Optional[str] = None,
) -> None:
    """Validate receipt identities, pins, and archive-owned revision evidence."""

    if receipt.status != "complete" or receipt.refusal_code is not None:
        raise GeneratedProviderUnavailable(
            "m2c qualification receipt is not a completed qualification"
        )
    if len(receipt.revision_ids) not in (2, 3):
        raise GeneratedProviderUnavailable(
            "m2c qualification receipt is not a qualified two-or-three revision matrix"
        )
    revision_ids = {item.revision_id for item in matrix.revisions}
    if set(receipt.revision_ids) != revision_ids or len(receipt.revision_ids) != len(revision_ids):
        raise GeneratedProviderSubsetViolation(
            "m2c revisions differ from the qualified receipt"
        )
    if matrix.current.revision_id != CURRENT_M2C_REVISION:
        raise GeneratedProviderDeterminismError(
            "m2c matrix conversion did not retain the pinned current revision"
        )
    if receipt.archive_identity != archive_identity:
        raise GeneratedProviderDeterminismError(
            "m2c archive identity differs from the qualified receipt"
        )
    if config_identity is not None and receipt.config_identity != config_identity:
        raise GeneratedProviderDeterminismError(
            "current m2c config differs from the qualified receipt"
        )
    if compiler_identity is not None and receipt.compiler_identity != compiler_identity:
        raise GeneratedProviderDeterminismError(
            "current m2c compiler differs from the qualified receipt"
        )
    if evaluator_identity is not None and receipt.evaluator_identity != evaluator_identity:
        raise GeneratedProviderDeterminismError(
            "current m2c evaluator differs from the qualified receipt"
        )
    if scorer_taxonomy_identity is not None and receipt.scorer_taxonomy_identity != scorer_taxonomy_identity:
        raise GeneratedProviderDeterminismError(
            "current m2c scorer taxonomy differs from the qualified receipt"
        )
    if receipt.tool_identity != matrix.current.executable_identity:
        raise GeneratedProviderDeterminismError(
            "m2c current executable identity differs from the qualified receipt"
        )
    receipt_pairs = dict(receipt.revision_tool_identities)
    expected_pairs = {
        item.revision_id: item.executable_identity for item in matrix.revisions
    }
    if receipt_pairs != expected_pairs:
        raise GeneratedProviderDeterminismError(
            "m2c revision executable identities differ from the qualified receipt"
        )
    if any(item.provider_identity != receipt.provider_identity for item in matrix.revisions):
        raise GeneratedProviderDeterminismError(
            "m2c provider identity differs from the qualified receipt"
        )
    if any(item.config_identity != receipt.config_identity for item in matrix.revisions):
        raise GeneratedProviderDeterminismError(
            "m2c revision config differs from the qualified receipt"
        )
    declared_runners = dict(runner_pairs)
    if set(declared_runners) != revision_ids:
        raise GeneratedProviderInputError(
            "m2c runner identities must cover every qualified revision"
        )
    for item in matrix.revisions:
        if item.source_artifact is None or item.tool_artifact is None:
            raise GeneratedProviderUnavailable(
                f"m2c revision {item.label} lacks archived source/tool evidence"
            )
        if not item.source_artifact.path.startswith(
            "artifacts/m2c-revision-sources/"
        ):
            raise GeneratedProviderArtifactError(
                f"m2c source artifact {item.label} is outside the canonical archive category"
            )
        if not item.tool_artifact.path.startswith(
            "artifacts/m2c-revision-tools/"
        ):
            raise GeneratedProviderArtifactError(
                f"m2c tool artifact {item.label} is outside the canonical archive category"
            )
        _verify_archive_reference(
            archive, item.source_artifact, f"m2c source artifact {item.label}"
        )
        _verify_archive_reference(
            archive, item.tool_artifact, f"m2c tool artifact {item.label}"
        )


def _m2c_qualification_binding(
    manifest: RunManifest,
    *,
    archive: ContentAddressedArchive,
    archive_identity: str,
    revisions: Sequence[M2CRevision] | M2CRevisionMatrix | Sequence[M2CRevisionPin],
    matrix_receipt: Any,
    evaluator_identity: Any,
    scorer_taxonomy_identity: Any,
    runner_identities: Any = None,
) -> _M2CQualificationBinding:
    """Bind current-run inputs to one independently qualified matrix."""

    receipt = _load_m2c_matrix_receipt(matrix_receipt, archive=archive)
    matrix, runner_pairs = _generated_matrix_from_inputs(
        revisions, runner_identities=runner_identities
    )
    try:
        reserved_evaluator = _identity(
            manifest.tool_identities[EVALUATOR_TOOL_KEY],
            "manifest evaluator identity",
        )
    except (KeyError, TypeError) as exc:
        raise GeneratedProviderInputError(
            "manifest has no reserved evaluator identity"
        ) from exc
    qualified_evaluator = _identity(
        receipt.evaluator_identity, "qualified evaluator identity"
    )
    if qualified_evaluator != reserved_evaluator:
        raise GeneratedProviderDeterminismError(
            "qualified evaluator differs from the current manifest reservation"
        )
    chosen_evaluator = (
        qualified_evaluator
        if evaluator_identity is None
        else _identity(evaluator_identity, "m2c evaluator identity")
    )
    if chosen_evaluator != qualified_evaluator:
        raise GeneratedProviderDeterminismError(
            "current evaluator differs from the qualified receipt"
        )
    qualified_scorer = _identity(
        receipt.scorer_taxonomy_identity, "qualified scorer taxonomy identity"
    )
    chosen_scorer = (
        qualified_scorer
        if scorer_taxonomy_identity is None
        else _identity(scorer_taxonomy_identity, "m2c scorer taxonomy identity")
    )
    if chosen_scorer != qualified_scorer:
        raise GeneratedProviderDeterminismError(
            "current scorer taxonomy differs from the qualified receipt"
        )
    _validate_matrix_receipt_revision_binding(
        receipt,
        matrix,
        runner_pairs,
        archive=archive,
        archive_identity=archive_identity,
        config_identity=manifest.config_identity,
        compiler_identity=manifest.compiler_identity,
        evaluator_identity=chosen_evaluator,
        scorer_taxonomy_identity=chosen_scorer,
    )
    return _M2CQualificationBinding(
        receipt=receipt,
        matrix=matrix,
        matrix_identity=matrix.matrix_identity,
        runner_identities=runner_pairs,
        evaluator_identity=chosen_evaluator,
        scorer_taxonomy_identity=chosen_scorer,
    )

def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        converted = to_dict()
        if isinstance(converted, Mapping):
            return converted
    raise GeneratedProviderInputError(f"{label} must be a mapping")


def _target_value(value: Any, *names: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        for name in names:
            if name in value:
                return value[name]
        return default
    for name in names:
        observed = getattr(value, name, None)
        if observed is not None:
            return observed
    return default


@dataclass(frozen=True)
class ArchivedTargetInput:
    """One immutable target assembly and its derived semantic fragments.

    The assembly bytes are supplied by the caller only so the factory can
    compare them to the exact archive object.  The factory retains the bytes in
    this value object and never resolves ``target_artifact.path`` against a
    repository or another filesystem root.
    """

    recipient_id: str
    target_identity: str
    target_artifact: ArtifactRef
    target_bytes: bytes
    symbol: str
    context_artifacts: tuple[ArtifactRef, ...] = ()
    declarations: Mapping[str, Any] = field(default_factory=dict)
    expressions: tuple[str, ...] = ()
    statements: tuple[str, ...] = ()
    declaration_shapes: tuple[str, ...] = ()
    control_flow: tuple[str, ...] = ()
    platform: Optional[str] = None

    def __post_init__(self) -> None:
        try:
            validate_id(self.recipient_id, "target recipient_id")
            _identity(self.target_identity, "target identity")
            target_artifact = _artifact(self.target_artifact, "target artifact")
            _validate_target_artifact(target_artifact)
        except (GeneratedProviderError, SearchValidationError, TypeError, ValueError) as exc:
            if isinstance(exc, GeneratedProviderError):
                raise
            raise GeneratedProviderArtifactError("target input identity is invalid") from exc
        if not isinstance(self.target_bytes, bytes) or not self.target_bytes:
            raise GeneratedProviderArtifactError("target bytes must be nonempty bytes")
        if len(self.target_bytes) > _MAX_TARGET_BYTES:
            raise GeneratedProviderArtifactError("target assembly is too large")
        if hash_bytes(self.target_bytes) != target_artifact.content_hash:
            raise GeneratedProviderArtifactError("target bytes disagree with target artifact")
        if target_artifact.byte_size != len(self.target_bytes):
            raise GeneratedProviderArtifactError("target artifact byte size differs from bytes")
        try:
            self.target_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise GeneratedProviderArtifactError("target assembly is not UTF-8") from exc
        if not isinstance(self.symbol, str) or not _C_IDENTIFIER.fullmatch(self.symbol):
            raise GeneratedProviderInputError("target symbol must be a C identifier")
        recipient_platform = self.recipient_id.split(":", 1)[0]
        if recipient_platform not in SUPPORTED_TARGET_PLATFORMS:
            raise GeneratedProviderInputError("target recipient platform is unsupported")
        platform = self.platform if self.platform is not None else recipient_platform
        if not isinstance(platform, str) or not _PLATFORM_RE.fullmatch(platform):
            raise GeneratedProviderInputError("target platform is unsupported")
        if platform != recipient_platform:
            raise GeneratedProviderInputError("target platform differs from recipient")
        declarations = _mapping(self.declarations, "target declarations")
        _freeze_json(declarations, "target declarations")
        unknown = set(declarations).difference(_ALLOWED_DECLARATION_KEYS)
        if unknown:
            raise GeneratedProviderInputError(
                "target declarations have unknown fields: " + ", ".join(sorted(unknown))
            )
        object.__setattr__(self, "target_identity", _identity(self.target_identity, "target identity"))
        object.__setattr__(self, "target_artifact", target_artifact)
        if not isinstance(self.context_artifacts, (tuple, list)):
            raise GeneratedProviderArtifactError("target context artifacts must be a sequence")
        contexts = tuple(_artifact(item, "target context artifact") for item in self.context_artifacts)
        if len({item.content_hash for item in contexts}) != len(contexts):
            raise GeneratedProviderArtifactError("target context artifacts must be unique")
        for item in contexts:
            validate_relative_path(item.path)
        object.__setattr__(self, "context_artifacts", contexts)
        object.__setattr__(self, "declarations", _freeze_json(declarations, "target declarations"))
        object.__setattr__(self, "expressions", _unique_fragments(self.expressions, "target expressions"))
        object.__setattr__(self, "statements", _unique_fragments(self.statements, "target statements", allow_semicolon=True))
        object.__setattr__(self, "declaration_shapes", _unique_fragments(self.declaration_shapes, "target declaration_shapes"))
        object.__setattr__(self, "control_flow", _unique_fragments(self.control_flow, "target control_flow"))
        object.__setattr__(self, "platform", platform)

    @property
    def assembly_artifact(self) -> ArtifactRef:
        return self.target_artifact

    @property
    def assembly_bytes(self) -> bytes:
        return self.target_bytes

    @property
    def target_evidence_identity(self) -> str:
        return hash_canonical(self.to_dict())

    def to_dict(self, *, include_bytes: bool = False) -> dict[str, Any]:
        result = {
            "protocol": TARGET_INPUT_PROTOCOL,
            "recipient_id": self.recipient_id,
            "target_identity": self.target_identity,
            "target_artifact": self.target_artifact.to_dict(),
            "context_artifacts": [item.to_dict() for item in self.context_artifacts],
            "symbol": self.symbol,
            "declarations": _plain(self.declarations),
            "expressions": list(self.expressions),
            "statements": list(self.statements),
            "declaration_shapes": list(self.declaration_shapes),
            "control_flow": list(self.control_flow),
            "platform": self.platform,
        }
        if include_bytes:
            try:
                result["target_bytes"] = self.target_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise GeneratedProviderArtifactError(
                    "target assembly cannot be serialized as UTF-8"
                ) from exc
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ArchivedTargetInput":
        data = _mapping(value, "target input")
        allowed = {
            "protocol",
            "recipient_id",
            "record_id",
            "id",
            "target_identity",
            "target_id",
            "target_artifact",
            "assembly_artifact",
            "context_artifacts",
            "target_context_artifacts",
            "target_bytes",
            "assembly_bytes",
            "symbol",
            "function",
            "declarations",
            "target_declarations",
            "expressions",
            "statements",
            "declaration_shapes",
            "control_flow",
            "control_flow_forms",
            "platform",
            "version",
        }
        unknown = set(data).difference(allowed)
        if unknown:
            raise GeneratedProviderInputError("target input has unknown fields")
        protocol = data.get("protocol")
        if protocol is not None and protocol != TARGET_INPUT_PROTOCOL:
            raise GeneratedProviderInputError("target input protocol is unsupported")
        artifact_value = data.get("target_artifact", data.get("assembly_artifact"))
        bytes_value = data.get("target_bytes", data.get("assembly_bytes"))
        if isinstance(bytes_value, str):
            bytes_value = bytes_value.encode("utf-8")
        fields = {
            "recipient_id": data.get("recipient_id", data.get("record_id", data.get("id"))),
            "target_identity": data.get("target_identity", data.get("target_id")),
            "target_artifact": artifact_value,
            "context_artifacts": data.get(
                "context_artifacts", data.get("target_context_artifacts", ())
            ),
            "target_bytes": bytes_value,
            "symbol": data.get("symbol", data.get("function")),
            "declarations": data.get("declarations", data.get("target_declarations", {})),
            "expressions": data.get("expressions", ()),
            "statements": data.get("statements", ()),
            "declaration_shapes": data.get("declaration_shapes", ()),
            "control_flow": data.get("control_flow", data.get("control_flow_forms", ())),
            "platform": data.get("platform", data.get("version")),
        }
        if fields["target_artifact"] is None or fields["target_bytes"] is None:
            raise GeneratedProviderArtifactError(
                "target input must carry archive-resolved target artifact and bytes"
            )
        try:
            fields["target_artifact"] = _artifact(fields["target_artifact"], "target artifact")
            fields["context_artifacts"] = tuple(
                _artifact(item, "target context artifact")
                for item in fields["context_artifacts"]
            )
            return cls(**fields)
        except TypeError as exc:
            raise GeneratedProviderInputError("target input fields are malformed") from exc


def _ordered_targets(
    manifest: RunManifest,
    target_inputs: Mapping[str, ArchivedTargetInput] | Sequence[ArchivedTargetInput],
    *,
    archive: ContentAddressedArchive,
) -> tuple[ArchivedTargetInput, ...]:
    if isinstance(target_inputs, Mapping):
        raw_values = []
        for key, value in target_inputs.items():
            if not isinstance(key, str):
                raise GeneratedProviderSubsetViolation("target input keys must be recipient IDs")
            if isinstance(value, ArchivedTargetInput) and value.recipient_id != key:
                raise GeneratedProviderSubsetViolation("target input key differs from recipient")
            if not isinstance(value, ArchivedTargetInput):
                if not isinstance(value, Mapping):
                    raise GeneratedProviderInputError(
                        "target input values must be typed archive-bound records"
                    )
                raw_recipient = _target_value(value, "recipient_id", "record_id", "id")
                if raw_recipient != key:
                    raise GeneratedProviderSubsetViolation("target input key differs from recipient")
            raw_values.append(value)
    elif isinstance(target_inputs, (tuple, list)):
        raw_values = list(target_inputs)
    else:
        raise GeneratedProviderSubsetViolation(
            "generated providers require an explicit target-input mapping or sequence"
        )
    if not raw_values or len(raw_values) > _MAX_TARGETS:
        raise GeneratedProviderSubsetViolation("target inputs must be a bounded nonempty subset")
    normalized: list[ArchivedTargetInput] = []
    for value in raw_values:
        if not isinstance(value, ArchivedTargetInput):
            try:
                value = ArchivedTargetInput.from_dict(value)
            except GeneratedProviderError:
                raise
            except (AttributeError, TypeError, ValueError) as exc:
                raise GeneratedProviderInputError("target inputs must be typed records") from exc
        normalized.append(value)
    by_id = {item.recipient_id: item for item in normalized}
    if len(by_id) != len(normalized):
        raise GeneratedProviderSubsetViolation("target inputs contain duplicate recipients")
    expected = set(manifest.queue_record_ids)
    if set(by_id) != expected:
        missing = sorted(expected.difference(by_id))
        extra = sorted(set(by_id).difference(expected))
        detail = []
        if missing:
            detail.append("missing=" + ",".join(missing))
        if extra:
            detail.append("extra=" + ",".join(extra))
        raise GeneratedProviderSubsetViolation(
            "target input subset must equal the manifest subset" + (" (" + "; ".join(detail) + ")" if detail else "")
        )
    ordered = tuple(sorted(normalized, key=lambda item: item.recipient_id))
    for item in ordered:
        expected_target = manifest.target_identities.get(item.recipient_id)
        if expected_target != item.target_identity:
            raise GeneratedProviderArtifactError(
                f"target identity differs from manifest for {item.recipient_id}"
            )
        _verify_archive_bytes(archive, item.target_artifact, item.target_bytes, item.recipient_id + " target artifact")
        for index, context in enumerate(item.context_artifacts):
            _verify_archive_reference(
                archive,
                context,
                f"{item.recipient_id} target context artifact {index}",
            )
    return ordered


def _manifest_lane_budget(manifest: RunManifest, lane: str) -> Budget:
    if lane not in manifest.selected_lanes:
        raise GeneratedProviderInputError(f"{lane} is not selected by the manifest")
    try:
        budget = manifest.lane_budgets[lane]
    except (KeyError, TypeError) as exc:
        raise GeneratedProviderBudgetError(f"manifest has no budget for {lane}") from exc
    if not isinstance(budget, Budget):
        try:
            budget = Budget.from_dict(budget)
        except (SearchValidationError, TypeError, ValueError) as exc:
            raise GeneratedProviderBudgetError(f"manifest budget for {lane} is invalid") from exc
    if budget.unit not in {"attempts", "candidates", "tasks"}:
        raise GeneratedProviderBudgetError(
            f"{lane} requires an attempts, candidates, or tasks budget"
        )
    return budget


def _manifest_binding(manifest: RunManifest, lane: str) -> tuple[str, str, str]:
    config_identity = _identity(manifest.config_identity, "manifest config identity")
    try:
        tool_identity = manifest.tool_identities[lane]
    except (KeyError, TypeError) as exc:
        raise GeneratedProviderInputError(f"manifest has no tool identity for {lane}") from exc
    return config_identity, _identity(tool_identity, lane + " tool identity"), hash_canonical(manifest.to_dict())


@dataclass(frozen=True)
class M2CRevision:
    """One qualified revision identity and its immutable archive evidence.

    Execution is deliberately absent from this record.  The root-owned
    :class:`M2CRevisionProvider` is the only authority allowed to generate a
    draft.  Keeping the provider out of this value makes serialization a real
    round trip instead of silently dropping a callable from the identity.
    """

    revision_identity: M2CRevisionIdentity
    source_artifact: Optional[ArtifactRef] = None
    tool_artifact: Optional[ArtifactRef] = None
    label: str = "m2c"
    current: bool = False
    qualified: bool = True
    available: bool = True
    unavailable_reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.revision_identity, M2CRevisionIdentity):
            raise GeneratedProviderInputError(
                "m2c revision requires a typed M2CRevisionIdentity"
            )
        if not isinstance(self.label, str) or not _C_IDENTIFIER.fullmatch(self.label):
            raise GeneratedProviderInputError("m2c revision label must be a C identifier")
        for name in ("current", "qualified", "available"):
            if not isinstance(getattr(self, name), bool):
                raise GeneratedProviderInputError("m2c revision flags must be boolean")
        if self.current and self.revision_identity.revision_id != CURRENT_M2C_REVISION:
            raise GeneratedProviderInputError(
                "the current m2c revision must use CURRENT_M2C_REVISION"
            )
        for name in ("source_artifact", "tool_artifact"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, ArtifactRef):
                object.__setattr__(self, name, _artifact(value, "m2c " + name))
        if self.available:
            if not self.qualified:
                raise GeneratedProviderInputError(
                    f"available m2c revision {self.label} is not qualified"
                )
            if self.source_artifact is None or self.tool_artifact is None:
                raise GeneratedProviderUnavailable(
                    f"m2c revision {self.label} has no archived source/tool qualification"
                )
        elif not isinstance(self.unavailable_reason, str) or not self.unavailable_reason:
            raise GeneratedProviderInputError(
                f"unavailable m2c revision {self.label} needs a reason"
            )
        if self.source_artifact is not None:
            validate_relative_path(self.source_artifact.path)
        if self.tool_artifact is not None:
            validate_relative_path(self.tool_artifact.path)
        if (
            self.source_artifact is not None
            and self.tool_artifact is not None
            and self.source_artifact.content_hash == self.tool_artifact.content_hash
        ):
            raise GeneratedProviderInputError(
                f"m2c revision {self.label} source and tool artifacts must differ"
            )

    @property
    def revision_id(self) -> str:
        return self.revision_identity.revision_id

    @property
    def revision(self) -> str:
        return self.revision_id

    @property
    def tree_identity(self) -> str:
        return self.revision_identity.tree_identity

    @property
    def provider_identity(self) -> str:
        return self.revision_identity.provider_identity

    @property
    def executable_identity(self) -> str:
        return self.revision_identity.executable_identity

    @property
    def config_identity(self) -> str:
        return self.revision_identity.config_identity

    @property
    def source_identity(self) -> Optional[str]:
        return None if self.source_artifact is None else self.source_artifact.content_hash

    @property
    def tool_identity(self) -> Optional[str]:
        return None if self.tool_artifact is None else self.tool_artifact.content_hash

    @property
    def qualification_identity(self) -> str:
        return hash_canonical(self._identity_payload())

    @property
    def identity(self) -> str:
        return self.qualification_identity

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": M2C_PROVIDER_PROTOCOL,
            "revision_identity": self.revision_identity.to_dict(),
            "source_artifact": None if self.source_artifact is None else self.source_artifact.to_dict(),
            "tool_artifact": None if self.tool_artifact is None else self.tool_artifact.to_dict(),
            "label": self.label,
            "current": self.current,
            "qualified": self.qualified,
            "available": self.available,
            "unavailable_reason": self.unavailable_reason,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._identity_payload(),
            "qualification_identity": self.qualification_identity,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M2CRevision":
        data = _mapping(value, "m2c revision")
        allowed = {
            "protocol",
            "revision_identity",
            "source_artifact",
            "tool_artifact",
            "label",
            "current",
            "qualified",
            "available",
            "unavailable_reason",
            "qualification_identity",
        }
        if set(data) != allowed:
            raise GeneratedProviderInputError("m2c revision fields are incomplete or unknown")
        if data.get("protocol") != M2C_PROVIDER_PROTOCOL:
            raise GeneratedProviderInputError("m2c revision protocol is unsupported")
        raw_identity = data.get("revision_identity")
        if not isinstance(raw_identity, M2CRevisionIdentity):
            try:
                raw_identity = M2CRevisionIdentity.from_dict(raw_identity)
            except (M2CProviderError, TypeError, ValueError) as exc:
                raise GeneratedProviderInputError("m2c revision identity is malformed") from exc
        source = data.get("source_artifact")
        tool = data.get("tool_artifact")
        if source is not None:
            source = _artifact(source, "m2c source artifact")
        if tool is not None:
            tool = _artifact(tool, "m2c tool artifact")
        try:
            result = cls(
                revision_identity=raw_identity,
                source_artifact=source,
                tool_artifact=tool,
                label=data.get("label", "m2c"),
                current=data.get("current", False),
                qualified=data.get("qualified", True),
                available=data.get("available", True),
                unavailable_reason=data.get("unavailable_reason", ""),
            )
        except TypeError as exc:
            raise GeneratedProviderInputError("m2c revision fields are malformed") from exc
        declared = data.get("qualification_identity")
        if declared is not None and _identity(declared, "m2c qualification identity") != result.qualification_identity:
            raise GeneratedProviderDeterminismError(
                "m2c qualification identity differs from its fields"
            )
        return result


@dataclass(frozen=True)
class M2CRevisionMatrix:
    """Canonical immutable current-plus-qualified-alternates matrix."""

    revisions: tuple[M2CRevision, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.revisions, tuple):
            try:
                object.__setattr__(self, "revisions", tuple(self.revisions))
            except TypeError as exc:
                raise GeneratedProviderInputError("m2c revision matrix must be a sequence") from exc
        if not self.revisions or len(self.revisions) > _MAX_REVISIONS:
            raise GeneratedProviderInputError("m2c revision matrix is empty or too large")
        if any(not isinstance(item, M2CRevision) for item in self.revisions):
            raise GeneratedProviderInputError("m2c revision matrix contains an untyped revision")
        currents = tuple(item for item in self.revisions if item.current)
        if len(currents) != 1:
            raise GeneratedProviderInputError(
                "m2c revision matrix must contain exactly one current revision"
            )
        if any(not item.current and not item.qualified for item in self.revisions):
            raise GeneratedProviderInputError(
                "m2c revision matrix refuses an unqualified alternate"
            )
        if len({item.revision_id for item in self.revisions}) != len(self.revisions):
            raise GeneratedProviderInputError("m2c revision matrix commits must be unique")
        if len({item.label for item in self.revisions}) != len(self.revisions):
            raise GeneratedProviderInputError("m2c revision matrix labels must be unique")
        current = currents[0]
        alternates = tuple(
            sorted(
                (item for item in self.revisions if not item.current),
                key=lambda item: (item.revision_id, item.label, item.qualification_identity),
            )
        )
        object.__setattr__(self, "revisions", (current, *alternates))

    @property
    def current(self) -> M2CRevision:
        return self.revisions[0]

    @property
    def matrix_identity(self) -> str:
        return hash_canonical(
            {
                "protocol": M2C_PROVIDER_PROTOCOL,
                "revisions": [item.to_dict() for item in self.revisions],
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": M2C_PROVIDER_PROTOCOL,
            "revisions": [item.to_dict() for item in self.revisions],
            "matrix_identity": self.matrix_identity,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M2CRevisionMatrix":
        data = _mapping(value, "m2c revision matrix")
        if set(data) != {"protocol", "revisions", "matrix_identity"}:
            raise GeneratedProviderInputError("m2c revision matrix fields are incomplete or unknown")
        if data.get("protocol") != M2C_PROVIDER_PROTOCOL:
            raise GeneratedProviderInputError("m2c revision matrix protocol is unsupported")
        raw = data.get("revisions")
        if not isinstance(raw, (tuple, list)):
            raise GeneratedProviderInputError("m2c revision matrix needs an explicit revisions list")
        matrix = cls(
            tuple(item if isinstance(item, M2CRevision) else M2CRevision.from_dict(item) for item in raw)
        )
        declared = data.get("matrix_identity")
        if declared is not None and _identity(declared, "m2c matrix identity") != matrix.matrix_identity:
            raise GeneratedProviderDeterminismError("m2c matrix identity differs from its revisions")
        return matrix


def _ordered_revisions(
    revisions: Sequence[M2CRevision] | M2CRevisionMatrix,
    *,
    archive: ContentAddressedArchive,
) -> tuple[M2CRevision, ...]:
    if isinstance(revisions, M2CRevisionMatrix):
        matrix = revisions
    else:
        if not isinstance(revisions, (tuple, list)):
            raise GeneratedProviderInputError("m2c revisions must be an explicit tuple or list")
        values = tuple(
            value if isinstance(value, M2CRevision) else M2CRevision.from_dict(value)
            for value in revisions
        )
        matrix = M2CRevisionMatrix(values)
    if not matrix.revisions:
        raise GeneratedProviderInputError("m2c revisions must be an explicit tuple or list")
    if len(matrix.revisions) > _MAX_REVISIONS:
        raise GeneratedProviderInputError("m2c revision matrix is empty or too large")
    for value in matrix.revisions:
        if value.available:
            assert value.source_artifact is not None
            assert value.tool_artifact is not None
            _verify_archive_reference(
                archive, value.source_artifact, f"m2c source artifact {value.label}"
            )
            _verify_archive_reference(
                archive, value.tool_artifact, f"m2c tool artifact {value.label}"
            )
    return matrix.revisions


@dataclass(frozen=True)
class SynthesisBound:
    """Immutable limits applied before bounded-synthesis enumeration."""

    max_candidates: int = _DEFAULT_SYNTHESIS_BOUND
    max_declarations: int = 8
    max_expressions: int = 8
    max_statements: int = 8
    max_control_flow: int = 8
    max_combinations: int = 64

    def __post_init__(self) -> None:
        values = (
            ("max_candidates", self.max_candidates),
            ("max_declarations", self.max_declarations),
            ("max_expressions", self.max_expressions),
            ("max_statements", self.max_statements),
            ("max_control_flow", self.max_control_flow),
            ("max_combinations", self.max_combinations),
        )
        for name, value in values:
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise GeneratedProviderInputError(f"{name} must be a nonnegative integer")
        if self.max_candidates == 0:
            raise GeneratedProviderInputError("max_candidates must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": SYNTHESIS_BOUND_PROTOCOL,
            "max_candidates": self.max_candidates,
            "max_declarations": self.max_declarations,
            "max_expressions": self.max_expressions,
            "max_statements": self.max_statements,
            "max_control_flow": self.max_control_flow,
            "max_combinations": self.max_combinations,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SynthesisBound":
        data = _mapping(value, "synthesis bound")
        fields = (
            "max_candidates",
            "max_declarations",
            "max_expressions",
            "max_statements",
            "max_control_flow",
            "max_combinations",
        )
        unknown = set(data).difference(set(fields) | {"protocol"})
        if unknown:
            raise GeneratedProviderInputError("synthesis bound has unknown fields")
        protocol = data.get("protocol")
        if protocol is not None and protocol != SYNTHESIS_BOUND_PROTOCOL:
            raise GeneratedProviderInputError("synthesis bound protocol is unsupported")
        try:
            return cls(**{name: data.get(name, getattr(cls, name, None)) for name in fields})
        except TypeError as exc:
            raise GeneratedProviderInputError("synthesis bound fields are malformed") from exc


def _candidate(
    *,
    lane: str,
    recipient: ArchivedTargetInput,
    source: str,
    provenance: Mapping[str, Any],
) -> LaneCandidate:
    if not isinstance(source, str) or not source:
        raise GeneratedProviderInputError("generated candidate source must be nonempty text")
    source_bytes = source.encode("utf-8")
    candidate_id = hash_bytes(source_bytes)
    artifact = ArtifactRef(
        candidate_id,
        f"artifacts/sources/{candidate_id.removeprefix('sha256:')}.c",
        "text/x-c",
        len(source_bytes),
    )
    record = CandidateRecord(
        candidate_id=candidate_id,
        recipient_id=recipient.recipient_id,
        source_artifact=artifact,
        parent_candidate_ids=(),
        mutation_id=None,
        lane=lane,
        depth=0,
        evaluation=None,
        status="materialized",
    )
    edge = dict(provenance)
    edge.update(
        {
            "lane": lane,
            "recipient_id": recipient.recipient_id,
            "candidate_identity": candidate_id,
            "source_identity": candidate_id,
            "input_identity": recipient.target_evidence_identity,
        }
    )
    return LaneCandidate(record, source, (_freeze_provenance(edge, "candidate provenance"),))


def _archived_candidate(
    *,
    lane: str,
    recipient: ArchivedTargetInput,
    source_artifact: ArtifactRef,
    source_bytes: bytes,
    provenance: Mapping[str, Any],
) -> LaneCandidate:
    """Build a candidate from the exact provider-published source artifact."""

    if not isinstance(source_artifact, ArtifactRef):
        raise GeneratedProviderArtifactError("m2c provider returned an untyped source artifact")
    if source_artifact.media_type != "text/x-c":
        raise GeneratedProviderArtifactError("m2c provider source artifact is not C text")
    if not isinstance(source_bytes, bytes) or not source_bytes:
        raise GeneratedProviderArtifactError("m2c provider source artifact is empty or untyped")
    if hash_bytes(source_bytes) != source_artifact.content_hash:
        raise GeneratedProviderArtifactError("m2c provider source artifact hash differs from bytes")
    if len(source_bytes) != source_artifact.byte_size:
        raise GeneratedProviderArtifactError("m2c provider source artifact size differs from bytes")
    try:
        source = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GeneratedProviderArtifactError("m2c provider source artifact is not UTF-8") from exc
    if not source:
        raise GeneratedProviderArtifactError("m2c provider source artifact is empty")
    candidate_id = source_artifact.content_hash
    record = CandidateRecord(
        candidate_id=candidate_id,
        recipient_id=recipient.recipient_id,
        source_artifact=source_artifact,
        parent_candidate_ids=(),
        mutation_id=None,
        lane=lane,
        depth=0,
        evaluation=None,
        status="materialized",
    )
    edge = dict(provenance)
    edge.update(
        {
            "lane": lane,
            "recipient_id": recipient.recipient_id,
            "candidate_identity": candidate_id,
            "source_identity": candidate_id,
            "input_identity": recipient.target_evidence_identity,
            "output_artifact_identity": source_artifact.content_hash,
        }
    )
    return LaneCandidate(record, source, (_freeze_provenance(edge, "candidate provenance"),))


def _base_provenance(
    *,
    lane: str,
    provider_identity: str,
    manifest_identity: str,
    config_identity: str,
    tool_identity: str,
    target: ArchivedTargetInput,
    evaluator_identity: Optional[str] = None,
    scorer_taxonomy_identity: Optional[str] = None,
    integration_gate_id: Optional[str] = None,
    integration_gate_artifact_id: Optional[str] = None,
    subset_identity: Optional[str] = None,
    queue_evidence_identity: Optional[str] = None,
) -> dict[str, Any]:
    result = {
        "kind": "generated_provider",
        "source": "automation.search_generated_lanes",
        "source_identity": MODULE_IDENTITY,
        "input_identity": target.target_evidence_identity,
        "lane": lane,
        "recipient_id": target.recipient_id,
        "provider_identity": provider_identity,
        "manifest_identity": manifest_identity,
        "config_identity": config_identity,
        "lane_tool_identity": tool_identity,
        "target_identity": target.target_identity,
        "target_artifact_identity": target.target_artifact.content_hash,
        "target_evidence_identity": target.target_evidence_identity,
        "platform": target.platform,
    }
    if evaluator_identity is not None:
        result["m2c_evaluator_identity"] = evaluator_identity
    if scorer_taxonomy_identity is not None:
        result["m2c_scorer_taxonomy_identity"] = scorer_taxonomy_identity
    if integration_gate_id is not None:
        result["m2c_integration_gate_id"] = integration_gate_id
    if integration_gate_artifact_id is not None:
        result["m2c_integration_gate_artifact_id"] = integration_gate_artifact_id
    if subset_identity is not None:
        result["m2c_subset_identity"] = subset_identity
    if queue_evidence_identity is not None:
        result["m2c_queue_evidence_identity"] = queue_evidence_identity
    return result


def _result(
    *,
    lane: str,
    target: ArchivedTargetInput,
    candidates: Sequence[LaneCandidate],
    provider_identity: str,
    manifest_identity: str,
    config_identity: str,
    tool_identity: str,
    extra_provenance: Sequence[Mapping[str, Any]],
    candidate_identities: Sequence[str] = (),
    attempts: int,
    rejection_counts: Mapping[str, int],
    refusal_code: Optional[str],
    reason: str,
    completion_reason: str,
    evaluator_identity: Optional[str] = None,
    scorer_taxonomy_identity: Optional[str] = None,
    integration_gate_id: Optional[str] = None,
    integration_gate_artifact_id: Optional[str] = None,
    subset_identity: Optional[str] = None,
    queue_evidence_identity: Optional[str] = None,
) -> Mapping[str, Any]:
    ordered = tuple(sorted(candidates, key=lambda item: item.candidate_id))
    inputs = [
        manifest_identity,
        config_identity,
        tool_identity,
        target.target_identity,
        target.target_artifact.content_hash,
        target.target_evidence_identity,
        MODULE_IDENTITY,
        provider_identity,
        *candidate_identities,
    ]
    inputs.extend(
        value
        for value in (
            evaluator_identity,
            scorer_taxonomy_identity,
            integration_gate_id,
            integration_gate_artifact_id,
            subset_identity,
            queue_evidence_identity,
        )
        if value is not None
    )
    provenance_items = [dict(item) for item in extra_provenance]
    provenance_items.extend(dict(item.provenance[0]) for item in ordered)
    for item in provenance_items:
        for key in (
            "source_identity",
            "input_identity",
            "provider_identity",
            "manifest_identity",
            "config_identity",
            "lane_tool_identity",
            "target_identity",
            "target_artifact_identity",
            "target_evidence_identity",
            "m2c_revision_identity",
            "m2c_source_identity",
            "m2c_tool_identity",
            "m2c_archive_identity",
            "m2c_output_artifact_identity",
            "overflow_candidate_identity",
            "m2c_compiler_identity",
            "m2c_evaluator_identity",
            "m2c_scorer_taxonomy_identity",
            "m2c_integration_gate_id",
            "m2c_integration_gate_artifact_id",
            "m2c_subset_identity",
            "m2c_queue_evidence_identity",
            "synthesis_bound_identity",
        ):
            value = item.get(key)
            if isinstance(value, str) and _HEX_HASH.fullmatch(value):
                inputs.append(value)
    provenance = tuple(
        _freeze_provenance(item, "provider provenance") for item in provenance_items
    )
    result: dict[str, Any] = {
        "candidates": ordered,
        "attempts": attempts,
        "input_identities": tuple(dict.fromkeys(inputs)),
        "provenance": provenance,
        "rejection_counts": MappingProxyType(dict(sorted(rejection_counts.items()))),
        "completion_reason": completion_reason,
        "reason": reason,
    }
    if refusal_code is not None:
        result["refusal_code"] = refusal_code
    return MappingProxyType(result)


_RESULT_KEYS = frozenset(
    {
        "candidates",
        "attempts",
        "input_identities",
        "provenance",
        "rejection_counts",
        "completion_reason",
        "refusal_code",
        "reason",
    }
)
_COMPLETION_REASONS = frozenset(
    {
        "budget_exhausted",
        "search_space_exhausted",
        "inapplicable",
        "matched_pending_oracle",
        "operator_stop",
        "superseded_by_stronger_evidence",
    }
)


def _freeze_result(
    value: Mapping[str, Any],
    *,
    lane: str,
    recipient_id: str,
    provider_identity: str,
    manifest_identity: str,
    config_identity: str,
    tool_identity: str,
    evaluator_identity: Optional[str] = None,
    scorer_taxonomy_identity: Optional[str] = None,
    integration_gate_id: Optional[str] = None,
    integration_gate_artifact_id: Optional[str] = None,
    subset_identity: Optional[str] = None,
    queue_evidence_identity: Optional[str] = None,
) -> Mapping[str, Any]:
    """Validate and deep-freeze one ordinary lane callback result."""

    data = _mapping(value, "generated provider result")
    if set(data).difference(_RESULT_KEYS):
        raise GeneratedProviderInputError("generated provider result has unknown fields")
    raw_candidates = data.get("candidates", ())
    if isinstance(raw_candidates, (str, bytes, bytearray)) or not isinstance(
        raw_candidates, (tuple, list)
    ):
        raise GeneratedProviderInputError("generated provider candidates must be a sequence")
    candidates = tuple(raw_candidates)
    candidate_ids = tuple(
        item.candidate_id for item in candidates if isinstance(item, LaneCandidate)
    )
    if len(candidate_ids) != len(candidates):
        raise GeneratedProviderInputError("generated provider candidates must be typed")
    if tuple(sorted(candidate_ids)) != candidate_ids or len(set(candidate_ids)) != len(candidate_ids):
        raise GeneratedProviderInputError("generated provider candidates must be canonical and unique")
    for item in candidates:
        if item.candidate.lane != lane or item.recipient_id != recipient_id:
            raise GeneratedProviderInputError("generated provider candidate binding differs from result")

    attempts = data.get("attempts", 0)
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < len(candidates):
        raise GeneratedProviderInputError("generated provider attempts are invalid")
    raw_inputs = data.get("input_identities", ())
    if isinstance(raw_inputs, (str, bytes, bytearray)) or not isinstance(
        raw_inputs, (tuple, list)
    ):
        raise GeneratedProviderInputError("generated provider input identities must be a sequence")
    input_identities: list[str] = []
    for item in raw_inputs:
        input_identities.append(_identity(item, "generated provider input identity"))
    if len(set(input_identities)) != len(input_identities):
        raise GeneratedProviderInputError("generated provider input identities must be unique")
    required_inputs = {
        manifest_identity,
        config_identity,
        tool_identity,
        provider_identity,
    }
    if not required_inputs.issubset(input_identities):
        raise GeneratedProviderInputError("generated provider input identities are incomplete")

    raw_provenance = data.get("provenance", ())
    if isinstance(raw_provenance, (str, bytes, bytearray)) or not isinstance(
        raw_provenance, (tuple, list)
    ):
        raise GeneratedProviderInputError("generated provider provenance must be a sequence")
    provenance: list[Mapping[str, Any]] = []
    for index, item in enumerate(raw_provenance):
        edge = _mapping(item, f"generated provider provenance[{index}]")
        if edge.get("lane") != lane or edge.get("recipient_id") != recipient_id:
            raise GeneratedProviderInputError("generated provider provenance binding differs from result")
        if not isinstance(edge.get("kind"), str) or not edge["kind"]:
            raise GeneratedProviderInputError("generated provider provenance kind is invalid")
        if not isinstance(edge.get("source"), str) or not edge["source"]:
            raise GeneratedProviderInputError("generated provider provenance source is invalid")
        if (
            edge.get("provider_identity") != provider_identity
            or edge.get("manifest_identity") != manifest_identity
            or edge.get("config_identity") != config_identity
            or edge.get("lane_tool_identity") != tool_identity
        ):
            raise GeneratedProviderInputError("generated provider provenance identity binding differs from result")
        expected_m2c = {
            "m2c_evaluator_identity": evaluator_identity,
            "m2c_scorer_taxonomy_identity": scorer_taxonomy_identity,
            "m2c_integration_gate_id": integration_gate_id,
            "m2c_integration_gate_artifact_id": integration_gate_artifact_id,
            "m2c_subset_identity": subset_identity,
            "m2c_queue_evidence_identity": queue_evidence_identity,
        }
        for key, expected in expected_m2c.items():
            if expected is not None and edge.get(key) != expected:
                raise GeneratedProviderInputError(
                    "generated provider m2c provenance identity differs from result"
                )
        _identity(edge.get("source_identity"), "generated provider provenance source identity")
        _identity(edge.get("input_identity"), "generated provider provenance input identity")
        provenance.append(_freeze_provenance(edge, f"generated provider provenance[{index}]"))

    raw_rejections = data.get("rejection_counts", {})
    rejection_map = _mapping(raw_rejections, "generated provider rejection counts")
    rejection_counts: dict[str, int] = {}
    for key, count in rejection_map.items():
        if not isinstance(key, str) or not key:
            raise GeneratedProviderInputError("generated provider rejection class is invalid")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise GeneratedProviderInputError("generated provider rejection count is invalid")
        rejection_counts[key] = count

    completion_reason = data.get("completion_reason")
    if completion_reason not in _COMPLETION_REASONS:
        raise GeneratedProviderInputError("generated provider completion reason is invalid")
    reason = data.get("reason", "")
    if not isinstance(reason, str):
        raise GeneratedProviderInputError("generated provider reason must be text")
    refusal_code = data.get("refusal_code")
    if refusal_code is not None and (not isinstance(refusal_code, str) or not refusal_code):
        raise GeneratedProviderInputError("generated provider refusal code must be text")

    frozen: dict[str, Any] = {
        "candidates": candidates,
        "attempts": attempts,
        "input_identities": tuple(input_identities),
        "provenance": tuple(provenance),
        "rejection_counts": MappingProxyType(dict(sorted(rejection_counts.items()))),
        "completion_reason": completion_reason,
        "reason": reason,
    }
    if refusal_code is not None:
        frozen["refusal_code"] = refusal_code
    return MappingProxyType(frozen)


@dataclass(frozen=True)
class GeneratedLaneProvider:
    """Frozen provider results and an ordinary replay-safe callback."""

    lane: str
    manifest_identity: str
    config_identity: str
    tool_identity: str
    provider_identity: str
    target_inputs: tuple[ArchivedTargetInput, ...]
    results: tuple[tuple[str, Mapping[str, Any]], ...]
    bound: Optional[SynthesisBound] = None
    revisions: tuple[M2CRevision, ...] = ()
    archive_identity: Optional[str] = None
    evaluator_identity: Optional[str] = None
    scorer_taxonomy_identity: Optional[str] = None
    matrix_receipt: Optional[M2CMatrixReceipt] = None
    matrix_identity: Optional[str] = None
    runner_identities: tuple[tuple[str, str], ...] = ()
    # Retained as serialized compatibility slots.  New m2c providers leave the
    # gate object empty and carry the prior gate IDs from matrix_receipt.
    integration_gate: Any = None
    integration_gate_artifact_id: Optional[str] = None
    subset_identity: Optional[str] = None
    queue_evidence_identity: Optional[str] = None

    def __post_init__(self) -> None:
        if self.lane not in GENERATED_LANES:
            raise GeneratedProviderInputError("unsupported generated lane")
        _identity(self.manifest_identity, "provider manifest identity")
        _identity(self.config_identity, "provider config identity")
        _identity(self.tool_identity, "provider tool identity")
        _identity(self.provider_identity, "provider identity")
        if self.evaluator_identity is not None:
            object.__setattr__(
                self,
                "evaluator_identity",
                _identity(self.evaluator_identity, "provider evaluator identity"),
            )
        if self.scorer_taxonomy_identity is not None:
            object.__setattr__(
                self,
                "scorer_taxonomy_identity",
                _identity(
                    self.scorer_taxonomy_identity,
                    "provider scorer taxonomy identity",
                ),
            )
        if self.integration_gate_artifact_id is not None:
            object.__setattr__(
                self,
                "integration_gate_artifact_id",
                _identity(
                    self.integration_gate_artifact_id,
                    "provider integration gate artifact identity",
                ),
            )
        if self.subset_identity is not None:
            object.__setattr__(
                self,
                "subset_identity",
                _identity(self.subset_identity, "provider subset identity"),
            )
        if self.queue_evidence_identity is not None:
            object.__setattr__(
                self,
                "queue_evidence_identity",
                _identity(
                    self.queue_evidence_identity,
                    "provider queue evidence identity",
                ),
            )
        if self.archive_identity is not None:
            object.__setattr__(
                self,
                "archive_identity",
                _identity(self.archive_identity, "provider archive identity"),
            )
        if not isinstance(self.target_inputs, tuple):
            try:
                object.__setattr__(self, "target_inputs", tuple(self.target_inputs))
            except TypeError as exc:
                raise GeneratedProviderInputError("provider target inputs must be a sequence") from exc
        if any(not isinstance(item, ArchivedTargetInput) for item in self.target_inputs):
            raise GeneratedProviderInputError("provider target inputs must be typed")
        target_ids = tuple(item.recipient_id for item in self.target_inputs)
        if target_ids != tuple(sorted(target_ids)) or len(set(target_ids)) != len(target_ids):
            raise GeneratedProviderInputError("provider target inputs must be canonical")
        if not self.target_inputs:
            raise GeneratedProviderInputError("provider target inputs must be nonempty")
        try:
            raw_results = tuple(self.results)
        except TypeError as exc:
            raise GeneratedProviderInputError("provider results must be a sequence") from exc
        result_ids: list[str] = []
        normalized_results: list[tuple[str, Mapping[str, Any]]] = []
        for item in raw_results:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise GeneratedProviderInputError("provider results must be recipient/result pairs")
            recipient_id, result = item
            if not isinstance(recipient_id, str):
                raise GeneratedProviderInputError("provider result recipient must be text")
            validate_id(recipient_id, "provider result recipient")
            result_ids.append(recipient_id)
            normalized_results.append(
                (
                    recipient_id,
                    _freeze_result(
                        result,
                        lane=self.lane,
                        recipient_id=recipient_id,
                        provider_identity=self.provider_identity,
                        manifest_identity=self.manifest_identity,
                        config_identity=self.config_identity,
                        tool_identity=self.tool_identity,
                        evaluator_identity=self.evaluator_identity,
                        scorer_taxonomy_identity=self.scorer_taxonomy_identity,
                        integration_gate_id=(
                            None
                            if not isinstance(self.matrix_receipt, M2CMatrixReceipt)
                            else self.matrix_receipt.integration_gate_id
                        ),
                        integration_gate_artifact_id=self.integration_gate_artifact_id,
                        subset_identity=self.subset_identity,
                        queue_evidence_identity=self.queue_evidence_identity,
                    ),
                )
            )
        result_ids_tuple = tuple(result_ids)
        if result_ids_tuple != tuple(sorted(result_ids_tuple)) or len(set(result_ids_tuple)) != len(result_ids_tuple):
            raise GeneratedProviderInputError("provider results must be unique and canonical")
        if set(result_ids_tuple) != set(target_ids):
            raise GeneratedProviderSubsetViolation("provider results must cover the frozen target subset")
        object.__setattr__(self, "results", tuple(normalized_results))
        if self.lane == M2C_LANE:
            if (
                self.bound is not None
                or not self.revisions
                or self.archive_identity is None
                or self.evaluator_identity is None
                or self.scorer_taxonomy_identity is None
                or not isinstance(self.matrix_receipt, M2CMatrixReceipt)
                or self.matrix_identity is None
                or self.integration_gate is not None
                or self.integration_gate_artifact_id is None
                or self.subset_identity is None
                or self.queue_evidence_identity is None
            ):
                raise GeneratedProviderInputError("m2c provider metadata is incomplete")
            receipt = self.matrix_receipt
            if receipt.status != "complete" or receipt.refusal_code is not None:
                raise GeneratedProviderUnavailable(
                    "m2c provider metadata does not contain a completed qualification"
                )
            if (
                receipt.integration_gate_artifact_id != self.integration_gate_artifact_id
                or receipt.subset_identity != self.subset_identity
                or receipt.queue_evidence_identity != self.queue_evidence_identity
                or receipt.archive_identity != self.archive_identity
                or receipt.config_identity != self.config_identity
                or receipt.evaluator_identity != self.evaluator_identity
                or receipt.scorer_taxonomy_identity != self.scorer_taxonomy_identity
            ):
                raise GeneratedProviderSubsetViolation(
                    "m2c provider qualification metadata differs from its binding"
                )
            try:
                revisions = tuple(self.revisions)
            except TypeError as exc:
                raise GeneratedProviderInputError("m2c provider revisions must be a sequence") from exc
            if any(not isinstance(item, M2CRevision) for item in revisions):
                raise GeneratedProviderInputError("m2c provider revisions must be typed")
            expected_revisions = M2CRevisionMatrix(revisions).revisions
            if revisions != expected_revisions:
                raise GeneratedProviderInputError("m2c provider revisions must be canonical")
            if set(receipt.revision_ids) != {item.revision_id for item in revisions}:
                raise GeneratedProviderSubsetViolation(
                    "m2c provider revisions differ from its qualified receipt"
                )
            if receipt.tool_identity != revisions[0].executable_identity:
                raise GeneratedProviderDeterminismError(
                    "m2c current executable differs from its qualified receipt"
                )
            if any(
                item.provider_identity != receipt.provider_identity
                or item.config_identity != receipt.config_identity
                for item in revisions
            ):
                raise GeneratedProviderDeterminismError(
                    "m2c revision identity differs from its qualified receipt"
                )
            if self.matrix_identity != M2CRevisionMatrix(revisions).matrix_identity:
                raise GeneratedProviderDeterminismError(
                    "m2c generated matrix identity differs from its revisions"
                )
            try:
                runner_values = tuple(self.runner_identities)
            except TypeError as exc:
                raise GeneratedProviderInputError(
                    "m2c runner identities must be a sequence"
                ) from exc
            runner_map: dict[str, str] = {}
            for item in runner_values:
                if not isinstance(item, (tuple, list)) or len(item) != 2:
                    raise GeneratedProviderInputError(
                        "m2c runner identities must contain pairs"
                    )
                revision_id, runner = item
                if revision_id in runner_map:
                    raise GeneratedProviderInputError(
                        "m2c runner identities must be unique"
                    )
                runner_map[revision_id] = _identity(
                    runner, "m2c runner identity"
                )
            if set(runner_map) != {item.revision_id for item in revisions}:
                raise GeneratedProviderInputError(
                    "m2c runner identities must cover every revision"
                )
            object.__setattr__(
                self,
                "runner_identities",
                tuple(sorted(runner_map.items())),
            )
            object.__setattr__(self, "revisions", revisions)
        else:
            if self.bound is None or not isinstance(self.bound, SynthesisBound):
                raise GeneratedProviderInputError("synthesis provider bound is incomplete")
            if self.revisions:
                raise GeneratedProviderInputError("synthesis provider cannot carry m2c revisions")
            if self.archive_identity is not None:
                raise GeneratedProviderInputError("synthesis provider cannot carry an archive identity")
            if (
                self.evaluator_identity is not None
                or self.scorer_taxonomy_identity is not None
                or self.matrix_receipt is not None
                or self.matrix_identity is not None
                or self.runner_identities
                or self.integration_gate is not None
                or self.integration_gate_artifact_id is not None
                or self.subset_identity is not None
                or self.queue_evidence_identity is not None
            ):
                raise GeneratedProviderInputError(
                    "synthesis provider cannot carry m2c integration metadata"
                )

    def callback(self, recipient: Recipient) -> Mapping[str, Any]:
        if not isinstance(recipient, Recipient):
            raise GeneratedProviderInputError("generated provider callback needs a typed Recipient")
        for recipient_id, result in self.results:
            if recipient_id == recipient.recipient_id:
                # Build a new outer mapping only.  All nested values are frozen
                # candidates, tuples, and mapping proxies, so replay cannot
                # mutate the provider's retained result.
                return dict(result)
        raise GeneratedProviderSubsetViolation(
            f"recipient {recipient.recipient_id} is outside the provider subset"
        )

    def __call__(self, recipient: Recipient) -> Mapping[str, Any]:
        return self.callback(recipient)

    def to_adapter_mapping(self) -> dict[str, Callable[[Recipient], Mapping[str, Any]]]:
        return {self.lane: self.callback}

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": M2C_PROVIDER_PROTOCOL if self.lane == M2C_LANE else SYNTHESIS_PROVIDER_PROTOCOL,
            "lane": self.lane,
            "manifest_identity": self.manifest_identity,
            "config_identity": self.config_identity,
            "tool_identity": self.tool_identity,
            "provider_identity": self.provider_identity,
            "archive_identity": self.archive_identity,
            "evaluator_identity": self.evaluator_identity,
            "scorer_taxonomy_identity": self.scorer_taxonomy_identity,
            "matrix_receipt": (
                None
                if self.matrix_receipt is None
                else self.matrix_receipt.to_dict()
            ),
            "matrix_identity": self.matrix_identity,
            "runner_identities": [list(item) for item in self.runner_identities],
            "integration_gate": (
                None
                if self.integration_gate is None
                else self.integration_gate.to_dict()
            ),
            "integration_gate_artifact_id": self.integration_gate_artifact_id,
            "subset_identity": self.subset_identity,
            "queue_evidence_identity": self.queue_evidence_identity,
            "target_inputs": [item.to_dict(include_bytes=True) for item in self.target_inputs],
            "results": [
                {
                    "recipient_id": recipient_id,
                    "candidates": [item.to_dict() for item in result.get("candidates", ())],
                    "candidate_ids": [item.candidate_id for item in result.get("candidates", ())],
                    "attempts": result.get("attempts", 0),
                    "input_identities": list(result.get("input_identities", ())),
                    "provenance": [_plain(item) for item in result.get("provenance", ())],
                    "rejection_counts": dict(result.get("rejection_counts", {})),
                    "completion_reason": result.get("completion_reason"),
                    "refusal_code": result.get("refusal_code"),
                    "reason": result.get("reason", ""),
                }
                for recipient_id, result in self.results
            ],
            "bound": None if self.bound is None else self.bound.to_dict(),
            "revisions": [item.to_dict() for item in self.revisions],
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        archive: ContentAddressedArchive,
    ) -> "GeneratedLaneProvider":
        """Reconstruct a frozen provider from its complete archived record.

        Reconstruction never invokes a generator.  It verifies every target,
        context, revision qualification artifact, and candidate output against
        the supplied archive before rebuilding the ordinary callback state.
        """

        data = _mapping(value, "generated lane provider")
        fields = {
            "protocol",
            "lane",
            "manifest_identity",
            "config_identity",
            "tool_identity",
            "provider_identity",
            "archive_identity",
            "evaluator_identity",
            "scorer_taxonomy_identity",
            "matrix_receipt",
            "matrix_identity",
            "runner_identities",
            "integration_gate",
            "integration_gate_artifact_id",
            "subset_identity",
            "queue_evidence_identity",
            "target_inputs",
            "results",
            "bound",
            "revisions",
        }
        missing_fields = fields.difference(data)
        legacy_synthesis_metadata = {
            "evaluator_identity",
            "scorer_taxonomy_identity",
            "matrix_receipt",
            "matrix_identity",
            "runner_identities",
            "integration_gate",
            "integration_gate_artifact_id",
            "subset_identity",
            "queue_evidence_identity",
        }
        if set(data).difference(fields) or (
            missing_fields
            and not (
                data.get("lane") == SYNTHESIS_LANE
                and missing_fields.issubset(legacy_synthesis_metadata)
            )
        ):
            raise GeneratedProviderInputError("generated lane provider record is incomplete")
        lane = data.get("lane")
        protocol = data.get("protocol")
        expected_protocol = M2C_PROVIDER_PROTOCOL if lane == M2C_LANE else SYNTHESIS_PROVIDER_PROTOCOL
        if lane not in GENERATED_LANES or protocol != expected_protocol:
            raise GeneratedProviderInputError("generated lane provider protocol is unsupported")
        if not isinstance(archive, ContentAddressedArchive):
            raise GeneratedProviderArtifactError(
                "generated provider reconstruction requires a ContentAddressedArchive"
            )
        raw_targets = data.get("target_inputs")
        if isinstance(raw_targets, (str, bytes, bytearray)) or not isinstance(raw_targets, (tuple, list)):
            raise GeneratedProviderInputError("generated provider target_inputs must be a list")
        targets = tuple(
            item if isinstance(item, ArchivedTargetInput) else ArchivedTargetInput.from_dict(item)
            for item in raw_targets
        )
        for target in targets:
            _verify_archive_bytes(
                archive,
                target.target_artifact,
                target.target_bytes,
                target.recipient_id + " target artifact",
            )
            for index, context in enumerate(target.context_artifacts):
                _verify_archive_reference(
                    archive,
                    context,
                    f"{target.recipient_id} target context artifact {index}",
                )

        # A reconstructed m2c provider is bound to a completed prior matrix
        # receipt.  No current-run integration gate is loaded or replayed here.
        raw_gate = data.get("integration_gate")
        if raw_gate is not None:
            raise GeneratedProviderInputError(
                "serialized generated provider cannot carry an integration gate"
            )
        integration_gate = None
        matrix_receipt = None
        if lane == M2C_LANE:
            raw_receipt = data.get("matrix_receipt")
            if raw_receipt is None:
                raise GeneratedProviderInputError(
                    "serialized m2c provider is missing its matrix receipt"
                )
            matrix_receipt = _load_m2c_matrix_receipt(
                raw_receipt, archive=archive
            )

        raw_results = data.get("results")
        if isinstance(raw_results, (str, bytes, bytearray)) or not isinstance(raw_results, (tuple, list)):
            raise GeneratedProviderInputError("generated provider results must be a list")
        parsed_results: list[tuple[str, Mapping[str, Any]]] = []
        result_fields = {
            "recipient_id",
            "candidates",
            "candidate_ids",
            "attempts",
            "input_identities",
            "provenance",
            "rejection_counts",
            "completion_reason",
            "refusal_code",
            "reason",
        }
        for index, raw_result in enumerate(raw_results):
            result_data = _mapping(raw_result, f"generated provider results[{index}]")
            if set(result_data) != result_fields:
                raise GeneratedProviderInputError(
                    "generated provider result fields are incomplete or unknown"
                )
            recipient_id = result_data.get("recipient_id")
            if not isinstance(recipient_id, str):
                raise GeneratedProviderInputError("generated provider result recipient is invalid")
            raw_candidates = result_data.get("candidates")
            if isinstance(raw_candidates, (str, bytes, bytearray)) or not isinstance(raw_candidates, (tuple, list)):
                raise GeneratedProviderInputError("serialized candidates must be a list")
            candidates: list[LaneCandidate] = []
            for candidate_index, raw_candidate in enumerate(raw_candidates):
                candidate_data = _mapping(
                    raw_candidate,
                    f"generated provider result {recipient_id} candidate {candidate_index}",
                )
                candidate_fields = {"candidate", "source", "provenance"}
                if set(candidate_data).difference(candidate_fields) or not candidate_fields.issubset(candidate_data):
                    raise GeneratedProviderInputError("serialized candidate is incomplete")
                candidate_record = CandidateRecord.from_dict(candidate_data["candidate"])
                raw_provenance = candidate_data["provenance"]
                if isinstance(raw_provenance, (str, bytes, bytearray)) or not isinstance(raw_provenance, (tuple, list)):
                    raise GeneratedProviderInputError("serialized candidate provenance must be a list")
                candidates.append(
                    LaneCandidate(
                        candidate_record,
                        candidate_data["source"],
                        tuple(raw_provenance),
                    )
                )
                if lane == M2C_LANE:
                    archived_source = _verify_archive_reference(
                        archive,
                        candidate_record.source_artifact,
                        f"serialized m2c candidate {candidate_record.candidate_id}",
                    )
                    if archived_source != candidate_data["source"].encode("utf-8"):
                        raise GeneratedProviderArtifactError(
                            f"serialized m2c candidate {candidate_record.candidate_id} differs from its archive"
                        )
            candidate_ids = tuple(item.candidate_id for item in candidates)
            declared_candidate_ids = result_data.get("candidate_ids")
            if declared_candidate_ids is not None:
                if isinstance(declared_candidate_ids, (str, bytes, bytearray)) or not isinstance(
                    declared_candidate_ids, (tuple, list)
                ):
                    raise GeneratedProviderInputError("serialized candidate_ids must be a list")
                if tuple(declared_candidate_ids) != candidate_ids:
                    raise GeneratedProviderDeterminismError(
                        f"serialized candidate ids differ for {recipient_id}"
                    )
            normalized_result: dict[str, Any] = {
                "candidates": tuple(candidates),
                "attempts": result_data.get("attempts"),
                "input_identities": result_data.get("input_identities"),
                "provenance": result_data.get("provenance"),
                "rejection_counts": result_data.get("rejection_counts"),
                "completion_reason": result_data.get("completion_reason"),
                "reason": result_data.get("reason", ""),
            }
            if result_data.get("refusal_code") is not None:
                normalized_result["refusal_code"] = result_data["refusal_code"]
            parsed_results.append((recipient_id, normalized_result))

        raw_revisions = data.get("revisions")
        if isinstance(raw_revisions, (str, bytes, bytearray)) or not isinstance(raw_revisions, (tuple, list)):
            raise GeneratedProviderInputError("generated provider revisions must be a list")
        revisions = tuple(
            item if isinstance(item, M2CRevision) else M2CRevision.from_dict(item)
            for item in raw_revisions
        )
        bound_value = data.get("bound")
        bound = None if bound_value is None else (
            bound_value if isinstance(bound_value, SynthesisBound) else SynthesisBound.from_dict(bound_value)
        )
        archive_identity = data.get("archive_identity")
        if archive_identity is not None:
            archive_identity = _identity(archive_identity, "provider archive identity")
        matrix_identity = data.get("matrix_identity")
        runner_identities = data.get("runner_identities", ())
        if lane == M2C_LANE:
            if not isinstance(matrix_receipt, M2CMatrixReceipt):
                raise GeneratedProviderInputError(
                    "serialized m2c provider is missing its matrix receipt"
                )
            try:
                reconstructed_matrix, reconstructed_runners = (
                    _generated_matrix_from_inputs(
                        revisions, runner_identities=runner_identities
                    )
                )
            except GeneratedProviderError:
                raise
            if matrix_identity is None:
                raise GeneratedProviderInputError(
                    "serialized m2c provider is missing its matrix identity"
                )
            matrix_identity = _identity(
                matrix_identity, "serialized m2c matrix identity"
            )
            if matrix_identity != reconstructed_matrix.matrix_identity:
                raise GeneratedProviderDeterminismError(
                    "serialized m2c matrix identity differs from its revisions"
                )
            _validate_matrix_receipt_revision_binding(
                matrix_receipt,
                reconstructed_matrix,
                reconstructed_runners,
                archive=archive,
                archive_identity=archive_identity,  # type: ignore[arg-type]
                config_identity=data["config_identity"],
                evaluator_identity=data.get("evaluator_identity"),
                scorer_taxonomy_identity=data.get("scorer_taxonomy_identity"),
            )
            if (
                data.get("integration_gate") is not None
                or data.get("integration_gate_artifact_id")
                != matrix_receipt.integration_gate_artifact_id
                or data.get("subset_identity") != matrix_receipt.subset_identity
                or data.get("queue_evidence_identity")
                != matrix_receipt.queue_evidence_identity
            ):
                raise GeneratedProviderSubsetViolation(
                    "serialized m2c provider carries a mismatched prior gate binding"
                )
            runner_identities = reconstructed_runners
        else:
            matrix_identity = None
            runner_identities = ()
        reconstructed = cls(
            lane=lane,
            manifest_identity=data["manifest_identity"],
            config_identity=data["config_identity"],
            tool_identity=data["tool_identity"],
            provider_identity=data["provider_identity"],
            target_inputs=targets,
            results=tuple(parsed_results),
            bound=bound,
            revisions=revisions,
            archive_identity=archive_identity,
            evaluator_identity=data.get("evaluator_identity"),
            scorer_taxonomy_identity=data.get("scorer_taxonomy_identity"),
            matrix_receipt=matrix_receipt,
            matrix_identity=matrix_identity,
            runner_identities=runner_identities,
            integration_gate=integration_gate,
            integration_gate_artifact_id=data.get("integration_gate_artifact_id"),
            subset_identity=data.get("subset_identity"),
            queue_evidence_identity=data.get("queue_evidence_identity"),
        )
        if lane == M2C_LANE:
            matrix = M2CRevisionMatrix(reconstructed.revisions)
            if reconstructed.provider_identity != _m2c_provider_identity(
                manifest_identity=reconstructed.manifest_identity,
                config_identity=reconstructed.config_identity,
                tool_identity=reconstructed.tool_identity,
                archive_identity=reconstructed.archive_identity,  # type: ignore[arg-type]
                target_inputs_identity=_target_inputs_identity(
                    reconstructed.target_inputs
                ),
                revisions=matrix.revisions,
                evaluator_identity=reconstructed.evaluator_identity,  # type: ignore[arg-type]
                scorer_taxonomy_identity=reconstructed.scorer_taxonomy_identity,  # type: ignore[arg-type]
                matrix_receipt_id=reconstructed.matrix_receipt.receipt_id,  # type: ignore[union-attr]
                qualification_matrix_id=reconstructed.matrix_receipt.matrix_id,  # type: ignore[union-attr]
                matrix_identity=reconstructed.matrix_identity,  # type: ignore[arg-type]
                runner_identities=reconstructed.runner_identities,
                integration_gate_id=reconstructed.matrix_receipt.integration_gate_id,  # type: ignore[union-attr]
                integration_gate_artifact_id=reconstructed.integration_gate_artifact_id,  # type: ignore[arg-type]
                subset_identity=reconstructed.subset_identity,  # type: ignore[arg-type]
                queue_evidence_identity=reconstructed.queue_evidence_identity,  # type: ignore[arg-type]
            ):
                raise GeneratedProviderDeterminismError(
                    "serialized m2c provider identity differs from its metadata"
                )
        else:
            if reconstructed.provider_identity != _synthesis_provider_identity(
                manifest_identity=reconstructed.manifest_identity,
                config_identity=reconstructed.config_identity,
                tool_identity=reconstructed.tool_identity,
                bound=reconstructed.bound,  # type: ignore[arg-type]
            ):
                raise GeneratedProviderDeterminismError(
                    "serialized synthesis provider identity differs from its metadata"
                )
        return reconstructed


def _effective_candidate_limit(budget: Budget, requested: int) -> int:
    if requested <= 0:
        raise GeneratedProviderBudgetError("candidate bound must be positive")
    # All generated candidates are charged as unique candidate attempts.  A
    # task budget still supplies a hard immutable cap so a provider cannot
    # silently exceed the run's declared budget.
    return min(requested, budget.limit)


def _target_inputs_identity(
    targets: Sequence[ArchivedTargetInput],
) -> str:
    return hash_canonical(
        {
            "protocol": TARGET_INPUT_PROTOCOL + ":ordered",
            "targets": [
                item.to_dict(include_bytes=True)
                for item in targets
            ],
        }
    )


def _m2c_provider_identity(
    *,
    manifest_identity: str,
    config_identity: str,
    tool_identity: str,
    archive_identity: str,
    target_inputs_identity: str,
    revisions: Sequence[M2CRevision],
    evaluator_identity: str,
    scorer_taxonomy_identity: str,
    matrix_receipt_id: str,
    qualification_matrix_id: str,
    matrix_identity: str,
    runner_identities: Sequence[tuple[str, str]],
    integration_gate_id: str,
    integration_gate_artifact_id: str,
    subset_identity: str,
    queue_evidence_identity: str,
) -> str:
    return hash_canonical(
        {
            "protocol": M2C_PROVIDER_PROTOCOL,
            "module_identity": MODULE_IDENTITY,
            "manifest_identity": manifest_identity,
            "config_identity": config_identity,
            "tool_identity": tool_identity,
            "archive_identity": archive_identity,
            "target_inputs_identity": target_inputs_identity,
            "evaluator_identity": evaluator_identity,
            "scorer_taxonomy_identity": scorer_taxonomy_identity,
            "matrix_receipt_id": matrix_receipt_id,
            "qualification_matrix_id": qualification_matrix_id,
            "matrix_identity": matrix_identity,
            "runner_identities": [list(item) for item in runner_identities],
            "integration_gate_id": integration_gate_id,
            "integration_gate_artifact_id": integration_gate_artifact_id,
            "subset_identity": subset_identity,
            "queue_evidence_identity": queue_evidence_identity,
            "revisions": [item.to_dict() for item in revisions],
        }
    )



def _synthesis_provider_identity(
    *,
    manifest_identity: str,
    config_identity: str,
    tool_identity: str,
    bound: SynthesisBound,
) -> str:
    return hash_canonical(
        {
            "protocol": SYNTHESIS_PROVIDER_PROTOCOL,
            "module_identity": MODULE_IDENTITY,
            "manifest_identity": manifest_identity,
            "config_identity": config_identity,
            "tool_identity": tool_identity,
            "bound": bound.to_dict(),
        }
    )


def _require_m2c_provider(provider: Any) -> M2CRevisionProvider:
    if provider is None:
        raise GeneratedProviderUnavailable("m2c provider is required")
    resolve = getattr(provider, "resolve_revision", None)
    generate = getattr(provider, "generate_draft", None)
    if not callable(resolve) or not callable(generate):
        raise GeneratedProviderInputError(
            "m2c provider must implement the typed revision-provider protocol"
        )
    return provider


def _resolve_m2c_revisions(
    provider: M2CRevisionProvider,
    revisions: Sequence[M2CRevision],
    manifest: RunManifest,
) -> Mapping[str, M2CRevisionIdentity]:
    resolved: dict[str, M2CRevisionIdentity] = {}
    for revision in revisions:
        if not revision.available:
            continue
        try:
            identity = provider.resolve_revision(revision.revision_id)
        except M2CProviderError as exc:
            raise GeneratedProviderUnavailable(
                f"m2c provider cannot resolve revision {revision.revision_id}"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise GeneratedProviderDeterminismError(
                f"m2c provider failed while resolving revision {revision.revision_id}"
            ) from exc
        if not isinstance(identity, M2CRevisionIdentity):
            raise GeneratedProviderInputError(
                "m2c provider returned an untyped revision identity"
            )
        if identity != revision.revision_identity:
            raise GeneratedProviderDeterminismError(
                f"m2c provider identity differs for revision {revision.revision_id}"
            )
        if identity.config_identity != manifest.config_identity:
            raise GeneratedProviderDeterminismError(
                f"m2c revision {revision.revision_id} is not bound to the manifest config"
            )
        resolved[revision.revision_id] = identity
    return MappingProxyType(resolved)


def _m2c_invocation(
    *,
    manifest: RunManifest,
    target: ArchivedTargetInput,
    revision: M2CRevision,
    manifest_identity: str,
    archive_identity: str,
    ordinal: int,
    evaluator_identity: str,
    scorer_taxonomy_identity: str,
    integration_gate_id: str,
    integration_gate_artifact_id: str,
    subset_identity: str,
    queue_evidence_identity: str,
) -> M2CInvocation:
    return make_invocation(
        revision_id=revision.revision_id,
        tree_identity=revision.tree_identity,
        provider_identity=revision.provider_identity,
        recipient_id=target.recipient_id,
        assembly_artifact=target.target_artifact,
        context_artifacts=target.context_artifacts,
        switches=(),
        target_identity=target.target_identity,
        compiler_identity=manifest.compiler_identity,
        tool_identity=revision.executable_identity,
        evaluator_identity=evaluator_identity,
        scorer_taxonomy_identity=scorer_taxonomy_identity,
        config_identity=revision.config_identity,
        integration_gate_id=integration_gate_id,
        integration_gate_artifact_id=integration_gate_artifact_id,
        subset_identity=subset_identity,
        queue_evidence_identity=queue_evidence_identity,
        archive_identity=archive_identity,
        ordinal=ordinal,
    )


def _m2c_revision_evidence(
    *,
    target: ArchivedTargetInput,
    revision: M2CRevision,
    provider_identity: str,
    manifest_identity: str,
    config_identity: str,
    tool_identity: str,
    archive_identity: str,
    kind: str,
    evaluator_identity: Optional[str] = None,
    scorer_taxonomy_identity: Optional[str] = None,
    integration_gate_id: Optional[str] = None,
    integration_gate_artifact_id: Optional[str] = None,
    subset_identity: Optional[str] = None,
    queue_evidence_identity: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict[str, Any]:
    evidence = _base_provenance(
        lane=M2C_LANE,
        provider_identity=provider_identity,
        manifest_identity=manifest_identity,
        config_identity=config_identity,
        tool_identity=tool_identity,
        target=target,
        evaluator_identity=evaluator_identity,
        scorer_taxonomy_identity=scorer_taxonomy_identity,
        integration_gate_id=integration_gate_id,
        integration_gate_artifact_id=integration_gate_artifact_id,
        subset_identity=subset_identity,
        queue_evidence_identity=queue_evidence_identity,
    )
    evidence.update(
        {
            "kind": kind,
            "source": "m2c:" + revision.label,
            "source_identity": revision.qualification_identity,
            "input_identity": target.target_evidence_identity,
            "m2c_revision_id": revision.revision_id,
            "m2c_revision_identity": revision.qualification_identity,
            "m2c_root_revision_identity": hash_canonical(revision.revision_identity.to_dict()),
            "m2c_tree_identity": revision.tree_identity,
            "m2c_provider_identity": revision.provider_identity,
            "m2c_executable_identity": revision.executable_identity,
            "m2c_source_identity": revision.source_identity,
            "m2c_tool_identity": revision.tool_identity,
            "m2c_archive_identity": archive_identity,
            "m2c_qualified": revision.qualified,
            "m2c_current": revision.current,
        }
    )
    if reason is not None:
        evidence["reason"] = reason
    return evidence


def _m2c_results(
    *,
    manifest: RunManifest,
    targets: Sequence[ArchivedTargetInput],
    revisions: Sequence[M2CRevision],
    resolved_revisions: Mapping[str, M2CRevisionIdentity],
    provider: M2CRevisionProvider,
    archive: ContentAddressedArchive,
    archive_identity: str,
    budget: Budget,
    provider_identity: str,
    config_identity: str,
    tool_identity: str,
    manifest_identity: str,
    evaluator_identity: str,
    scorer_taxonomy_identity: str,
    integration_gate_id: str,
    integration_gate_artifact_id: str,
    subset_identity: str,
    queue_evidence_identity: str,
) -> tuple[tuple[str, Mapping[str, Any]], ...]:
    # A zero limit is a valid exhausted manifest budget.  It blocks generation
    # without pretending that an output was observed.
    limit = _effective_candidate_limit(budget, max(1, budget.limit))
    results: list[tuple[str, Mapping[str, Any]]] = []
    for target in targets:
        candidates_by_id: dict[str, LaneCandidate] = {}
        seen_candidate_ids: set[str] = set()
        accepted_candidate_ids: list[str] = []
        evidence: list[Mapping[str, Any]] = []
        rejection_counts: dict[str, int] = {}
        unavailable = 0
        overflow = 0
        if limit == 0:
            evidence.append(
                {
                    **_base_provenance(
                        lane=M2C_LANE,
                        provider_identity=provider_identity,
                        manifest_identity=manifest_identity,
                        config_identity=config_identity,
                        tool_identity=tool_identity,
                        target=target,
                        evaluator_identity=evaluator_identity,
                        scorer_taxonomy_identity=scorer_taxonomy_identity,
                        integration_gate_id=integration_gate_id,
                        integration_gate_artifact_id=integration_gate_artifact_id,
                        subset_identity=subset_identity,
                        queue_evidence_identity=queue_evidence_identity,
                    ),
                    "kind": "m2c_budget_gate",
                    "source": "m2c-budget",
                    "m2c_archive_identity": archive_identity,
                    "reason": "manifest m2c candidate budget is zero",
                }
            )
        else:
            for ordinal, revision in enumerate(revisions):
                if not revision.available:
                    unavailable += 1
                    evidence.append(
                        _m2c_revision_evidence(
                            target=target,
                            revision=revision,
                            provider_identity=provider_identity,
                            manifest_identity=manifest_identity,
                            config_identity=config_identity,
                            tool_identity=tool_identity,
                            archive_identity=archive_identity,
                            evaluator_identity=evaluator_identity,
                            scorer_taxonomy_identity=scorer_taxonomy_identity,
                            integration_gate_id=integration_gate_id,
                            integration_gate_artifact_id=integration_gate_artifact_id,
                            subset_identity=subset_identity,
                            queue_evidence_identity=queue_evidence_identity,
                            kind="m2c_dependency_unavailable",
                            reason=revision.unavailable_reason,
                        )
                    )
                    continue
                identity = resolved_revisions[revision.revision_id]
                invocation = _m2c_invocation(
                    manifest=manifest,
                    target=target,
                    revision=revision,
                    manifest_identity=manifest_identity,
                    archive_identity=archive_identity,
                    ordinal=ordinal,
                    evaluator_identity=evaluator_identity,
                    scorer_taxonomy_identity=scorer_taxonomy_identity,
                    integration_gate_id=integration_gate_id,
                    integration_gate_artifact_id=integration_gate_artifact_id,
                    subset_identity=subset_identity,
                    queue_evidence_identity=queue_evidence_identity,
                )
                context_bytes = tuple(
                    _verify_archive_reference(
                        archive,
                        context,
                        f"{target.recipient_id} target context artifact {index}",
                    )
                    for index, context in enumerate(target.context_artifacts)
                )
                try:
                    draft = provider.generate_draft(
                        invocation,
                        assembly=target.target_bytes,
                        contexts=context_bytes,
                    )
                except M2CProviderError as exc:
                    raise GeneratedProviderDeterminismError(
                        f"m2c provider rejected invocation for {revision.label}"
                    ) from exc
                if not isinstance(draft, M2CDraftPayload):
                    raise GeneratedProviderInputError(
                        "m2c provider must return a typed M2CDraftPayload"
                    )
                if draft.invocation_id != invocation.invocation_id:
                    raise GeneratedProviderDeterminismError(
                        f"m2c draft invocation identity differs for {revision.label}"
                    )
                if draft.revision_id != identity.revision_id:
                    raise GeneratedProviderDeterminismError(
                        f"m2c draft revision identity differs for {revision.label}"
                    )
                source_bytes = _verify_archive_reference(
                    archive,
                    draft.source_artifact,
                    f"m2c draft artifact {revision.label}",
                )
                revision_evidence = _m2c_revision_evidence(
                    target=target,
                    revision=revision,
                    provider_identity=provider_identity,
                    manifest_identity=manifest_identity,
                    config_identity=config_identity,
                    tool_identity=tool_identity,
                    archive_identity=archive_identity,
                    evaluator_identity=evaluator_identity,
                    scorer_taxonomy_identity=scorer_taxonomy_identity,
                    integration_gate_id=integration_gate_id,
                    integration_gate_artifact_id=integration_gate_artifact_id,
                    subset_identity=subset_identity,
                    queue_evidence_identity=queue_evidence_identity,
                    kind="m2c_invocation",
                )
                revision_evidence.update(
                    {
                        "invocation_id": invocation.invocation_id,
                        "m2c_invocation_identity": invocation.invocation_id,
                        "m2c_output_artifact_identity": draft.source_artifact.content_hash,
                        "m2c_compiler_identity": invocation.compiler_identity,
                        "m2c_evaluator_identity": invocation.evaluator_identity,
                        "m2c_scorer_taxonomy_identity": invocation.scorer_taxonomy_identity,
                        "m2c_integration_gate_id": invocation.integration_gate_id,
                        "m2c_integration_gate_artifact_id": invocation.integration_gate_artifact_id,
                        "m2c_subset_identity": invocation.subset_identity,
                        "m2c_queue_evidence_identity": invocation.queue_evidence_identity,
                        "m2c_archive_identity": invocation.archive_identity,
                        "output_byte_size": len(source_bytes),
                        "variant_ordinal": ordinal,
                    }
                )
                evidence.append(revision_evidence)
                candidate_id = draft.source_artifact.content_hash
                if candidate_id in seen_candidate_ids:
                    rejection_counts["duplicate_candidate"] = rejection_counts.get(
                        "duplicate_candidate", 0
                    ) + 1
                    continue
                seen_candidate_ids.add(candidate_id)
                if len(accepted_candidate_ids) >= limit:
                    overflow += 1
                    evidence.append(
                        {
                            **revision_evidence,
                            "kind": "m2c_overflow_observation",
                            "source": "m2c-overflow:" + revision.label,
                            "source_identity": candidate_id,
                            "overflow_candidate_identity": candidate_id,
                        }
                    )
                    continue
                provenance = _base_provenance(
                    lane=M2C_LANE,
                    provider_identity=provider_identity,
                    manifest_identity=manifest_identity,
                    config_identity=config_identity,
                    tool_identity=tool_identity,
                    target=target,
                    evaluator_identity=evaluator_identity,
                    scorer_taxonomy_identity=scorer_taxonomy_identity,
                    integration_gate_id=integration_gate_id,
                    integration_gate_artifact_id=integration_gate_artifact_id,
                    subset_identity=subset_identity,
                    queue_evidence_identity=queue_evidence_identity,
                )
                provenance.update(
                    {
                        "m2c_revision_identity": revision.qualification_identity,
                        "m2c_revision_id": revision.revision_id,
                        "m2c_root_revision_identity": hash_canonical(
                            revision.revision_identity.to_dict()
                        ),
                        "m2c_tree_identity": revision.tree_identity,
                        "m2c_provider_identity": revision.provider_identity,
                        "m2c_executable_identity": revision.executable_identity,
                        "m2c_source_identity": revision.source_identity,
                        "m2c_tool_identity": revision.tool_identity,
                        "m2c_archive_identity": archive_identity,
                        "m2c_invocation_id": invocation.invocation_id,
                        "m2c_output_artifact_identity": draft.source_artifact.content_hash,
                        "m2c_compiler_identity": invocation.compiler_identity,
                        "m2c_evaluator_identity": invocation.evaluator_identity,
                        "m2c_scorer_taxonomy_identity": invocation.scorer_taxonomy_identity,
                        "m2c_integration_gate_id": invocation.integration_gate_id,
                        "m2c_integration_gate_artifact_id": invocation.integration_gate_artifact_id,
                        "m2c_subset_identity": invocation.subset_identity,
                        "m2c_queue_evidence_identity": invocation.queue_evidence_identity,
                        "m2c_qualified": revision.qualified,
                        "m2c_current": revision.current,
                    }
                )
                candidates_by_id[candidate_id] = _archived_candidate(
                    lane=M2C_LANE,
                    recipient=target,
                    source_artifact=draft.source_artifact,
                    source_bytes=source_bytes,
                    provenance=provenance,
                )
                accepted_candidate_ids.append(candidate_id)
        if unavailable:
            rejection_counts["dependency_unavailable"] = unavailable
        if overflow:
            rejection_counts["budget_exhausted"] = overflow
        candidates = tuple(sorted(candidates_by_id.values(), key=lambda item: item.candidate_id))
        if candidates:
            completion = "budget_exhausted" if overflow else "matched_pending_oracle"
            refusal = None
            reason = "m2c ensemble produced deterministic archived candidates"
        elif overflow or (limit == 0 and any(item.available for item in revisions)):
            completion = "budget_exhausted"
            refusal = "m2c_budget_exhausted"
            reason = "m2c candidate budget was exhausted before a candidate could be returned"
        elif unavailable == len(revisions):
            completion = "inapplicable"
            refusal = "m2c_dependency_unavailable"
            reason = "every pinned m2c dependency is unavailable"
        else:
            completion = "inapplicable"
            refusal = "m2c_no_candidate"
            reason = "pinned m2c revisions produced no archived candidate"
        results.append(
            (
                target.recipient_id,
                _result(
                    lane=M2C_LANE,
                    target=target,
                    candidates=candidates,
                    provider_identity=provider_identity,
                    manifest_identity=manifest_identity,
                    config_identity=config_identity,
                    tool_identity=tool_identity,
                    evaluator_identity=evaluator_identity,
                    scorer_taxonomy_identity=scorer_taxonomy_identity,
                    integration_gate_id=integration_gate_id,
                    integration_gate_artifact_id=integration_gate_artifact_id,
                    subset_identity=subset_identity,
                    queue_evidence_identity=queue_evidence_identity,
                    extra_provenance=evidence,
                    candidate_identities=tuple(accepted_candidate_ids),
                    attempts=len(accepted_candidate_ids),
                    rejection_counts=rejection_counts,
                    refusal_code=refusal,
                    reason=reason,
                    completion_reason=completion,
                ),
            )
        )
    return tuple(results)


def _safe_type(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise GeneratedProviderInputError(f"{label} must be a nonempty type")
    value = " ".join(value.split())
    if not re.fullmatch(
        r"(?:(?:const|volatile|unsigned|signed|short|long)\s+)*(?:void|char|short|int|long|float|double|u8|s8|u16|s16|u32|s32|f32|[A-Za-z_]\w*)(?:\s*\*)*",
        value,
    ):
        raise GeneratedProviderInputError(f"{label} is not a safe C type")
    return value


def _declaration_parts(target: ArchivedTargetInput, bound: SynthesisBound) -> tuple[str, tuple[tuple[str, str], ...], tuple[str, ...]]:
    values = dict(target.declarations)
    return_type = _safe_type(values.get("return_type", values.get("result_type", "int")), "target return type")
    raw_params = values.get("parameters", values.get("params", ()))
    if not isinstance(raw_params, (tuple, list)):
        raise GeneratedProviderInputError("target parameters must be a sequence")
    params: list[tuple[str, str]] = []
    for index, value in enumerate(raw_params):
        if isinstance(value, str):
            bits = value.strip().split()
            if len(bits) < 2:
                raise GeneratedProviderInputError(f"target parameter {index} lacks a name")
            name = bits[-1]
            type_name = " ".join(bits[:-1])
        elif isinstance(value, Mapping):
            name = value.get("name")
            type_name = value.get("type", value.get("declaration"))
        else:
            raise GeneratedProviderInputError(f"target parameter {index} is malformed")
        if not isinstance(name, str) or not _C_IDENTIFIER.fullmatch(name):
            raise GeneratedProviderInputError(f"target parameter {index} has an invalid name")
        params.append((_safe_type(type_name, f"target parameter {index}"), name))
    if len(params) > bound.max_declarations:
        params = params[: bound.max_declarations]
    raw_shapes = values.get("declaration_shapes", values.get("locals", ()))
    shapes = _unique_fragments(raw_shapes, "target declaration shapes", allow_semicolon=True)
    return return_type, tuple(params), shapes[: bound.max_declarations]


def _function_header(target: ArchivedTargetInput, return_type: str, params: Sequence[tuple[str, str]]) -> str:
    parameter_text = "void" if not params else ", ".join(type_name + " " + name for type_name, name in params)
    return f"{return_type} {target.symbol}({parameter_text})"


def _statement_text(statement: str) -> str:
    statement = statement.strip()
    if statement.endswith(";"):
        return statement
    return statement + ";"


def _synthesis_sources(target: ArchivedTargetInput, bound: SynthesisBound) -> tuple[str, ...]:
    return_type, params, declaration_shapes = _declaration_parts(target, bound)
    expressions = target.expressions[: bound.max_expressions]
    statements = target.statements[: bound.max_statements]
    control_flow = target.control_flow[: bound.max_control_flow]
    declared_shapes = tuple(dict.fromkeys((*declaration_shapes, *target.declaration_shapes)))[: bound.max_declarations]
    if not expressions and not statements and not control_flow and not declared_shapes:
        return ()
    header = _function_header(target, return_type, params)
    sources: list[str] = []
    expression_values = expressions or ("0",)

    def add(body_lines: Sequence[str]) -> None:
        if len(sources) >= bound.max_combinations:
            return
        body = "\n".join("    " + line.strip() for line in body_lines if line.strip())
        if not body:
            return
        candidate = header + " {\n" + body + "\n}\n"
        if candidate not in sources:
            sources.append(candidate)

    for expression in expression_values:
        if return_type == "void":
            add((_statement_text(expression), "return;"))
        else:
            add((f"return {expression};",))
        if len(sources) >= bound.max_combinations:
            break
    for statement in statements:
        body = [_statement_text(statement)]
        if return_type == "void":
            body.append("return;")
        else:
            body.append("return 0;")
        add(body)
        if len(sources) >= bound.max_combinations:
            break
    for form in control_flow:
        condition = expression_values[0]
        if form in {"if", "if_return"}:
            if return_type == "void":
                add((f"if ({condition}) return;", "return;"))
            else:
                add((f"if ({condition}) return 1;", "return 0;"))
        elif form in {"if_else", "ifelse"}:
            if return_type == "void":
                add((f"if ({condition}) return; else return;",))
            else:
                add((f"if ({condition}) return 1; else return 0;",))
        elif form in {"while", "loop"}:
            if return_type == "void":
                add((f"while ({condition}) {{ return; }}", "return;"))
            else:
                add((f"while ({condition}) {{ return 1; }}", "return 0;"))
        elif form in {"do_while", "dowhile"}:
            if return_type == "void":
                add((f"do {{ return; }} while ({condition});", "return;"))
            else:
                add((f"do {{ return 1; }} while ({condition});", "return 0;"))
        else:
            raise GeneratedProviderInputError(f"unsupported target control-flow form: {form}")
        if len(sources) >= bound.max_combinations:
            break
    # Declaration shapes are target-derived local declarations.  Prefixing a
    # bounded subset to each existing body makes declaration shape an actual
    # input to synthesis rather than a provenance-only field.
    if declared_shapes and sources:
        expanded: list[str] = []
        for shape in declared_shapes:
            shape_text = _statement_text(shape)
            for source in sources:
                marker = " {\n"
                position = source.find(marker)
                if position < 0:
                    continue
                candidate = source[: position + len(marker)] + "    " + shape_text + "\n" + source[position + len(marker) :]
                expanded.append(candidate)
                if len(expanded) >= bound.max_combinations:
                    break
            if len(expanded) >= bound.max_combinations:
                break
        if expanded:
            sources.extend(expanded)
    unique = tuple(sorted(set(sources), key=lambda value: hash_bytes(value.encode("utf-8"))))
    return unique[: bound.max_combinations]


def _synthesis_results(
    *,
    targets: Sequence[ArchivedTargetInput],
    budget: Budget,
    bound: SynthesisBound,
    provider_identity: str,
    config_identity: str,
    tool_identity: str,
    manifest_identity: str,
) -> tuple[tuple[str, Mapping[str, Any]], ...]:
    limit = _effective_candidate_limit(budget, bound.max_candidates)
    results: list[tuple[str, Mapping[str, Any]]] = []
    for target in targets:
        all_sources = _synthesis_sources(target, bound)
        candidates: list[LaneCandidate] = []
        rejection_counts: dict[str, int] = {}
        overflow = max(0, len(all_sources) - limit)
        evidence = _base_provenance(
            lane=SYNTHESIS_LANE,
            provider_identity=provider_identity,
            manifest_identity=manifest_identity,
            config_identity=config_identity,
            tool_identity=tool_identity,
            target=target,
        )
        evidence.update(
            {
                "synthesis_bound_identity": hash_canonical(bound.to_dict()),
                "synthesis_bound": bound.to_dict(),
                "target_derived_inputs": {
                    "expressions": list(target.expressions),
                    "statements": list(target.statements),
                    "declaration_shapes": list(target.declaration_shapes),
                    "control_flow": list(target.control_flow),
                },
            }
        )
        for source in all_sources[:limit]:
            provenance = _base_provenance(
                lane=SYNTHESIS_LANE,
                provider_identity=provider_identity,
                manifest_identity=manifest_identity,
                config_identity=config_identity,
                tool_identity=tool_identity,
                target=target,
            )
            provenance.update(
                {
                    "synthesis_bound_identity": hash_canonical(bound.to_dict()),
                    "synthesis_bound": bound.to_dict(),
                    "target_derived_inputs": {
                        "expressions": list(target.expressions),
                        "statements": list(target.statements),
                        "declaration_shapes": list(target.declaration_shapes),
                        "control_flow": list(target.control_flow),
                    },
                }
            )
            candidates.append(
                _candidate(
                    lane=SYNTHESIS_LANE,
                    recipient=target,
                    source=source,
                    provenance=provenance,
                )
            )
        if overflow:
            rejection_counts["budget_exhausted"] = overflow
        candidates = list(sorted(candidates, key=lambda item: item.candidate_id))
        if candidates:
            completion = "budget_exhausted" if overflow else "matched_pending_oracle"
            refusal = None
            reason = "bounded synthesis produced deterministic target-derived candidates"
        elif overflow:
            completion = "budget_exhausted"
            refusal = "synthesis_budget_exhausted"
            reason = "bounded synthesis candidate budget was exhausted"
        else:
            completion = "inapplicable"
            refusal = "synthesis_inputs_empty"
            reason = "target snapshot supplied no supported synthesis forms"
        results.append(
            (
                target.recipient_id,
                _result(
                    lane=SYNTHESIS_LANE,
                    target=target,
                    candidates=candidates,
                    provider_identity=provider_identity,
                    manifest_identity=manifest_identity,
                    config_identity=config_identity,
                    tool_identity=tool_identity,
                    extra_provenance=(evidence,),
                    candidate_identities=tuple(
                        hash_bytes(source.encode("utf-8")) for source in all_sources
                    ),
                    attempts=len(all_sources),
                    rejection_counts=rejection_counts,
                    refusal_code=refusal,
                    reason=reason,
                    completion_reason=completion,
                ),
            )
        )
    return tuple(results)


def build_m2c_ensemble_provider(
    manifest: RunManifest | Mapping[str, Any],
    target_inputs: Mapping[str, ArchivedTargetInput] | Sequence[ArchivedTargetInput],
    revisions: Sequence[M2CRevision] | M2CRevisionMatrix | Sequence[M2CRevisionPin],
    *,
    archive: ContentAddressedArchive,
    provider: M2CRevisionProvider,
    archive_identity: str,
    matrix_receipt: M2CMatrixReceipt | ArtifactRef | Mapping[str, Any],
    runner_identities: Any = None,
    integration_gate: Any = None,
    integration_gate_artifact_id: Optional[str] = None,
    evaluator_identity: Optional[str] = None,
    scorer_taxonomy_identity: Optional[str] = None,
) -> GeneratedLaneProvider:
    """Build a frozen m2c provider from prior matrix qualification evidence.

    The receipt belongs to an earlier completed qualification run.  It is
    independent of the current manifest run ID, while the provider identity
    separately binds that current manifest and its target snapshot.
    """

    typed_manifest = _coerce_manifest(manifest)
    budget = _manifest_lane_budget(typed_manifest, M2C_LANE)
    config_identity, tool_identity, manifest_identity = _manifest_binding(
        typed_manifest, M2C_LANE
    )
    archive_identity = _identity(archive_identity, "m2c archive identity")
    if integration_gate is not None or integration_gate_artifact_id is not None:
        raise GeneratedProviderInputError(
            "m2c provider accepts a prior matrix receipt, not a current integration gate"
        )
    qualification = _m2c_qualification_binding(
        typed_manifest,
        archive=archive,
        archive_identity=archive_identity,
        revisions=revisions,
        matrix_receipt=matrix_receipt,
        evaluator_identity=evaluator_identity,
        scorer_taxonomy_identity=scorer_taxonomy_identity,
        runner_identities=runner_identities,
    )
    provider = _require_m2c_provider(provider)
    targets = _ordered_targets(typed_manifest, target_inputs, archive=archive)
    target_inputs_identity = _target_inputs_identity(targets)
    ordered_revisions = qualification.matrix.revisions
    resolved_revisions = _resolve_m2c_revisions(
        provider, ordered_revisions, typed_manifest
    )
    receipt = qualification.receipt
    provider_identity = _m2c_provider_identity(
        manifest_identity=manifest_identity,
        config_identity=config_identity,
        tool_identity=tool_identity,
        archive_identity=archive_identity,
        target_inputs_identity=target_inputs_identity,
        revisions=ordered_revisions,
        evaluator_identity=qualification.evaluator_identity,
        scorer_taxonomy_identity=qualification.scorer_taxonomy_identity,
        matrix_receipt_id=receipt.receipt_id,
        qualification_matrix_id=receipt.matrix_id,
        matrix_identity=qualification.matrix_identity,
        runner_identities=qualification.runner_identities,
        integration_gate_id=receipt.integration_gate_id,
        integration_gate_artifact_id=receipt.integration_gate_artifact_id,
        subset_identity=receipt.subset_identity,
        queue_evidence_identity=receipt.queue_evidence_identity,
    )
    results = _m2c_results(
        manifest=typed_manifest,
        targets=targets,
        revisions=ordered_revisions,
        resolved_revisions=resolved_revisions,
        provider=provider,
        archive=archive,
        archive_identity=archive_identity,
        budget=budget,
        provider_identity=provider_identity,
        config_identity=config_identity,
        tool_identity=tool_identity,
        manifest_identity=manifest_identity,
        evaluator_identity=qualification.evaluator_identity,
        scorer_taxonomy_identity=qualification.scorer_taxonomy_identity,
        integration_gate_id=receipt.integration_gate_id,
        integration_gate_artifact_id=receipt.integration_gate_artifact_id,
        subset_identity=receipt.subset_identity,
        queue_evidence_identity=receipt.queue_evidence_identity,
    )
    return GeneratedLaneProvider(
        lane=M2C_LANE,
        manifest_identity=manifest_identity,
        config_identity=config_identity,
        tool_identity=tool_identity,
        provider_identity=provider_identity,
        target_inputs=targets,
        results=results,
        revisions=ordered_revisions,
        archive_identity=archive_identity,
        evaluator_identity=qualification.evaluator_identity,
        scorer_taxonomy_identity=qualification.scorer_taxonomy_identity,
        matrix_receipt=receipt,
        matrix_identity=qualification.matrix_identity,
        runner_identities=qualification.runner_identities,
        integration_gate=None,
        integration_gate_artifact_id=receipt.integration_gate_artifact_id,
        subset_identity=receipt.subset_identity,
        queue_evidence_identity=receipt.queue_evidence_identity,
    )



def build_bounded_synthesis_provider(
    manifest: RunManifest | Mapping[str, Any],
    target_inputs: Mapping[str, ArchivedTargetInput] | Sequence[ArchivedTargetInput],
    *,
    archive: ContentAddressedArchive,
    bound: SynthesisBound | Mapping[str, Any] | None = None,
) -> GeneratedLaneProvider:
    """Build a frozen bounded-synthesis provider from target evidence only."""

    typed_manifest = _coerce_manifest(manifest)
    budget = _manifest_lane_budget(typed_manifest, SYNTHESIS_LANE)
    config_identity, tool_identity, manifest_identity = _manifest_binding(typed_manifest, SYNTHESIS_LANE)
    targets = _ordered_targets(typed_manifest, target_inputs, archive=archive)
    if bound is None:
        bound = SynthesisBound()
    elif not isinstance(bound, SynthesisBound):
        bound = SynthesisBound.from_dict(bound)
    provider_identity = _synthesis_provider_identity(
        manifest_identity=manifest_identity,
        config_identity=config_identity,
        tool_identity=tool_identity,
        bound=bound,
    )
    results = _synthesis_results(
        targets=targets,
        budget=budget,
        bound=bound,
        provider_identity=provider_identity,
        config_identity=config_identity,
        tool_identity=tool_identity,
        manifest_identity=manifest_identity,
    )
    return GeneratedLaneProvider(
        lane=SYNTHESIS_LANE,
        manifest_identity=manifest_identity,
        config_identity=config_identity,
        tool_identity=tool_identity,
        provider_identity=provider_identity,
        target_inputs=targets,
        results=results,
        bound=bound,
    )


def m2c_ensemble_adapter(
    manifest: RunManifest | Mapping[str, Any],
    target_inputs: Mapping[str, ArchivedTargetInput] | Sequence[ArchivedTargetInput],
    revisions: Sequence[M2CRevision] | M2CRevisionMatrix | Sequence[M2CRevisionPin],
    *,
    archive: ContentAddressedArchive,
    provider: M2CRevisionProvider,
    archive_identity: str,
    matrix_receipt: M2CMatrixReceipt | ArtifactRef | Mapping[str, Any],
    runner_identities: Any = None,
    integration_gate: Any = None,
    integration_gate_artifact_id: Optional[str] = None,
    evaluator_identity: Optional[str] = None,
    scorer_taxonomy_identity: Optional[str] = None,
) -> Callable[[Recipient], Mapping[str, Any]]:
    """Return the ordinary one-argument m2c lane callback."""

    return build_m2c_ensemble_provider(
        manifest,
        target_inputs,
        revisions,
        archive=archive,
        provider=provider,
        archive_identity=archive_identity,
        matrix_receipt=matrix_receipt,
        runner_identities=runner_identities,
        integration_gate=integration_gate,
        integration_gate_artifact_id=integration_gate_artifact_id,
        evaluator_identity=evaluator_identity,
        scorer_taxonomy_identity=scorer_taxonomy_identity,
    ).callback


def bounded_synthesis_adapter(
    manifest: RunManifest | Mapping[str, Any],
    target_inputs: Mapping[str, ArchivedTargetInput] | Sequence[ArchivedTargetInput],
    *,
    archive: ContentAddressedArchive,
    bound: SynthesisBound | Mapping[str, Any] | None = None,
) -> Callable[[Recipient], Mapping[str, Any]]:
    """Return the ordinary one-argument bounded-synthesis lane callback."""

    return build_bounded_synthesis_provider(
        manifest,
        target_inputs,
        archive=archive,
        bound=bound,
    ).callback


def generated_lane_adapters(
    manifest: RunManifest | Mapping[str, Any],
    target_inputs: Mapping[str, ArchivedTargetInput] | Sequence[ArchivedTargetInput],
    *,
    archive: ContentAddressedArchive,
    revisions: Sequence[M2CRevision] | M2CRevisionMatrix | Sequence[M2CRevisionPin] | None = None,
    provider: M2CRevisionProvider | None = None,
    archive_identity: Optional[str] = None,
    matrix_receipt: M2CMatrixReceipt | ArtifactRef | Mapping[str, Any] | None = None,
    runner_identities: Any = None,
    integration_gate: Any = None,
    integration_gate_artifact_id: Optional[str] = None,
    evaluator_identity: Optional[str] = None,
    scorer_taxonomy_identity: Optional[str] = None,
    synthesis_bound: SynthesisBound | Mapping[str, Any] | None = None,
) -> dict[str, Callable[[Recipient], Mapping[str, Any]]]:
    """Build both generated callbacks as a mapping for ``LaneAdapters``."""

    typed_manifest = _coerce_manifest(manifest)
    adapters: dict[str, Callable[[Recipient], Mapping[str, Any]]] = {}
    if M2C_LANE in typed_manifest.selected_lanes:
        if (
            revisions is None
            or provider is None
            or archive_identity is None
            or matrix_receipt is None
        ):
            raise GeneratedProviderUnavailable(
                "selected m2c lane needs an explicit matrix, provider, and archive identity"
            )
        m2c = build_m2c_ensemble_provider(
            typed_manifest,
            target_inputs,
            revisions,
            archive=archive,
            provider=provider,
            archive_identity=archive_identity,
            matrix_receipt=matrix_receipt,
            runner_identities=runner_identities,
            integration_gate=integration_gate,
            integration_gate_artifact_id=integration_gate_artifact_id,
            evaluator_identity=evaluator_identity,
            scorer_taxonomy_identity=scorer_taxonomy_identity,
        )
        adapters[M2C_LANE] = m2c.callback
    if SYNTHESIS_LANE in typed_manifest.selected_lanes:
        synthesis = build_bounded_synthesis_provider(
            typed_manifest,
            target_inputs,
            archive=archive,
            bound=synthesis_bound,
        )
        adapters[SYNTHESIS_LANE] = synthesis.callback
    if not adapters:
        raise GeneratedProviderInputError("manifest selects no generated lane")
    return adapters


# Descriptive aliases used by the later production factory integration.
make_m2c_ensemble_adapter = m2c_ensemble_adapter
make_bounded_synthesis_adapter = bounded_synthesis_adapter
make_generated_lane_adapters = generated_lane_adapters
M2CEnsembleRevision = M2CRevision
M2CEnsembleMatrix = M2CRevisionMatrix
GeneratedTargetInput = ArchivedTargetInput


__all__ = [
    "ArchivedTargetInput",
    "GeneratedLaneProvider",
    "GeneratedProviderArtifactError",
    "GeneratedProviderBudgetError",
    "GeneratedProviderDeterminismError",
    "GeneratedProviderError",
    "GeneratedProviderInputError",
    "GeneratedProviderSubsetViolation",
    "GeneratedProviderUnavailable",
    "GeneratedTargetInput",
    "M2CMatrixReceipt",
    "M2CRevisionPin",
    "M2CEnsembleRevision",
    "M2CEnsembleMatrix",
    "M2CRevision",
    "M2CRevisionMatrix",
    "SynthesisBound",
    "bounded_synthesis_adapter",
    "build_bounded_synthesis_provider",
    "build_m2c_ensemble_provider",
    "generated_lane_adapters",
    "m2c_ensemble_adapter",
    "make_bounded_synthesis_adapter",
    "make_generated_lane_adapters",
    "make_m2c_ensemble_adapter",
]
