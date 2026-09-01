"""Production provider for the ``idiom_atlas`` lane.

The idiom atlas is a Tier 3 cheap generated lane.  It turns measured compiler
idiom evidence into deterministic source rewrites of an archived target draft,
using only evidence the project already proved:

``corpus_entries``
    Typed accepted draft-landed :class:`CorpusEvidence` records.  Each carries
    one :class:`CompilerIdiomObservation` whose improvement was measured under
    a single compiler and scorer boundary.  Selecting the accepted entries out
    of a published :class:`CorpusGeneration` is ordinary wiring and stays with
    the caller, because gate validation against the integration archive is the
    generation consumer's obligation, not this module's.

``lineage_contexts``
    Typed :class:`CompletedLineageContext` records.  An idiom may be applied
    only when a completed, artifact-verified lineage binds the same compiler
    and, when the idiom records one, the same config.  Idioms never cross
    compiler identities, and a corpus entry alone does not prove that this
    program's history observed the transformation.

Per recipient the provider replays each applicable idiom's grouped patches
over the archived draft source through the shared replay primitives, counts
every nonapplication as a typed rejection class, charges the manifest lane
budget per unique candidate, and returns the ordinary read-only lane callback
shape used by :mod:`search_lanes`.  The factory performs every archive
verification exactly once, freezes the results, and leaves a stateless
callback that never reads the queue, a checkout, or the network.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Optional

try:  # package imports
    from .search_archive import ArchiveError, ArtifactRef, ContentAddressedArchive
    from .search_evidence_corpus import CorpusEvidence
    from .search_lanes import LaneCandidate, LaneError, Recipient, SubsetViolation
    from .search_mutations import port_grouped_patch
    from .search_patterns import CompletedLineageContext, PatternInputError
    from .compiler_idioms import (
        CompilerIdiomError,
        CompilerIdiomObservation,
        deduplicate_idioms,
        replay_grouped_patch,
        source_hash,
    )
    from .search_types import (
        Budget,
        CandidateRecord,
        RunManifest,
        SearchValidationError,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
    )
except ImportError:  # direct invocation from the automation directory
    from search_archive import ArchiveError, ArtifactRef, ContentAddressedArchive  # type: ignore
    from search_evidence_corpus import CorpusEvidence  # type: ignore
    from search_lanes import LaneCandidate, LaneError, Recipient, SubsetViolation  # type: ignore
    from search_mutations import port_grouped_patch  # type: ignore
    from search_patterns import CompletedLineageContext, PatternInputError  # type: ignore
    from compiler_idioms import (  # type: ignore
        CompilerIdiomError,
        CompilerIdiomObservation,
        deduplicate_idioms,
        replay_grouped_patch,
        source_hash,
    )
    from search_types import (  # type: ignore
        Budget,
        CandidateRecord,
        RunManifest,
        SearchValidationError,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
    )


IDIOM_LANE = "idiom_atlas"
IDIOM_PROVIDER_PROTOCOL = "sotn-idiom-atlas-provider-v1"
TARGET_INPUT_PROTOCOL = "sotn-idiom-atlas-target-input-v1"
MODULE_IDENTITY = hash_canonical(
    {
        "module": "automation.search_idiom_atlas",
        "protocols": [IDIOM_PROVIDER_PROTOCOL, TARGET_INPUT_PROTOCOL],
        "version": "1.0.0",
    }
)

SUPPORTED_TARGET_PLATFORMS = ("us", "hd", "pspeu", "saturn")
_MAX_TARGETS = 4096
_MAX_IDIOMS = 4096
_MAX_SOURCE_BYTES = 16 * 1024 * 1024
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
_PROVIDER_SCHEMA_VERSION = 1
_PROVIDER_KEYS = frozenset(
    {
        "protocol",
        "schema_version",
        "lane",
        "manifest_identity",
        "config_identity",
        "tool_identity",
        "provider_identity",
        "target_inputs",
        "idioms",
        "lineage_contexts",
        "results",
        "state_identity",
    }
)
_PROVIDER_RESULT_KEYS = frozenset(
    {
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
)
_PROVIDER_CANDIDATE_KEYS = frozenset({"candidate", "source", "provenance"})
_PROVIDER_TARGET_KEYS = frozenset(
    {
        "protocol",
        "recipient_id",
        "target_identity",
        "draft_artifact",
        "draft_identity",
        "draft_bytes",
        "platform",
    }
)
_IDIOM_KEYS = frozenset(
    {
        "observation_id",
        "compiler_identity",
        "before",
        "after",
        "grouped_patches",
        "supporting_pair_hashes",
        "tool_identity",
        "config_identity",
        "operator_records",
        "measurement",
    }
)
_LINEAGE_KEYS = frozenset(
    {
        "protocol",
        "kind",
        "ledger_identity",
        "run_id",
        "compiler_identity",
        "config_identity",
        "schema_identity",
        "scorer_algorithms",
        "lane_tool_identities",
        "recipient_target_identities",
        "evaluator_identity",
    }
)
_REQUIRED_RESULT_KEYS = _RESULT_KEYS - {"refusal_code"}
_BASE_PROVENANCE_KEYS = frozenset(
    {
        "kind",
        "source",
        "source_identity",
        "input_identity",
        "lane",
        "recipient_id",
        "provider_identity",
        "manifest_identity",
        "config_identity",
        "lane_tool_identity",
        "target_identity",
        "draft_artifact_identity",
        "target_evidence_identity",
        "platform",
    }
)
_SUMMARY_PROVENANCE_KEYS = _BASE_PROVENANCE_KEYS | frozenset(
    {"corpus_idiom_count", "applicable_idiom_count", "lineage_ledger_identities"}
)
_CANDIDATE_PROVENANCE_KEYS = _BASE_PROVENANCE_KEYS | frozenset(
    {
        "candidate_identity",
        "idiom_observation_id",
        "idiom_compiler_identity",
        "idiom_support_count",
        "idiom_patch_ids",
        "idiom_lineage_ledgers",
        "base_source_identity",
        "replay_modes",
    }
)
_PROVENANCE_IDENTITY_KEYS = (
    "source_identity",
    "input_identity",
    "provider_identity",
    "manifest_identity",
    "config_identity",
    "lane_tool_identity",
    "target_identity",
    "draft_artifact_identity",
    "target_evidence_identity",
    "base_source_identity",
    "idiom_observation_id",
    "idiom_compiler_identity",
)
_REJECTION_CLASSES = frozenset(
    {
        "patch_invalid",
        "patch_conflict",
        "no_change",
        "duplicate_candidate",
        "compiler_mismatch",
        "no_lineage_support",
        "budget_exhausted",
    }
)


class IdiomAtlasError(LaneError):
    """Base class for idiom-atlas provider failures."""


class IdiomAtlasInputError(IdiomAtlasError):
    """A manifest, target input, corpus entry, or lineage context is malformed."""


class IdiomAtlasArtifactError(IdiomAtlasInputError):
    """An archive-owned input is absent, changed, or outside its contract."""


class IdiomAtlasBudgetError(IdiomAtlasInputError):
    """The immutable manifest budget cannot represent this provider."""


class IdiomAtlasSubsetViolation(SubsetViolation):
    """A callback was asked to process a recipient outside its frozen subset."""


def _identity(value: Any, label: str) -> str:
    try:
        return validate_hash(value, label)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise IdiomAtlasInputError(f"{label} must be a sha256 identity") from exc


def _freeze_json(value: Any, label: str) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise IdiomAtlasInputError(f"{label} keys must be strings")
        return MappingProxyType(
            {key: _freeze_json(item, f"{label}.{key}") for key, item in value.items()}
        )
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_json(item, f"{label}[{index}]") for index, item in enumerate(value))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise IdiomAtlasInputError(f"{label} contains a non-JSON value")


def _plain_json(value: Any, label: str) -> Any:
    """Return a fresh JSON-shaped copy, refusing executable or mutable values."""

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise IdiomAtlasInputError(f"{label} keys must be strings")
            result[key] = _plain_json(item, f"{label}.{key}")
        return result
    if isinstance(value, (tuple, list)):
        return [_plain_json(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise IdiomAtlasInputError(f"{label} contains a non-JSON value")


def _strict_mapping(value: Any, label: str) -> dict[str, Any]:
    """Accept only the plain mappings produced by JSON decoding."""

    if type(value) is not dict:
        raise IdiomAtlasInputError(f"{label} must be a plain object")
    if any(not isinstance(key, str) for key in value):
        raise IdiomAtlasInputError(f"{label} keys must be strings")
    return value


def _strict_list(value: Any, label: str) -> list[Any]:
    """Accept only JSON arrays, never caller-owned tuple or custom sequences."""

    if type(value) is not list:
        raise IdiomAtlasInputError(f"{label} must be a JSON array")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        converted = to_dict()
        if isinstance(converted, Mapping):
            return converted
    raise IdiomAtlasInputError(f"{label} must be a mapping")


def _artifact(value: Any, label: str) -> ArtifactRef:
    if isinstance(value, ArtifactRef):
        return value
    try:
        return ArtifactRef.from_dict(value)
    except (AttributeError, KeyError, SearchValidationError, TypeError, ValueError) as exc:
        raise IdiomAtlasArtifactError(f"{label} is not an ArtifactRef") from exc


def _verify_archive_bytes(
    archive: ContentAddressedArchive,
    reference: ArtifactRef,
    expected: bytes,
    label: str,
) -> None:
    if not isinstance(archive, ContentAddressedArchive):
        raise IdiomAtlasArtifactError(
            "idiom atlas requires an explicit ContentAddressedArchive"
        )
    try:
        observed = archive.verify(reference)
    except (ArchiveError, OSError, TypeError, ValueError) as exc:
        raise IdiomAtlasArtifactError(f"{label} is missing or corrupt") from exc
    if observed != expected:
        raise IdiomAtlasArtifactError(f"{label} bytes disagree with its archive")


def _verify_archive_reference(
    archive: ContentAddressedArchive,
    reference: ArtifactRef,
    label: str,
) -> None:
    if not isinstance(archive, ContentAddressedArchive):
        raise IdiomAtlasArtifactError(
            "idiom atlas requires an explicit ContentAddressedArchive"
        )
    try:
        archive.verify(reference)
    except (ArchiveError, OSError, TypeError, ValueError) as exc:
        raise IdiomAtlasArtifactError(f"{label} is missing or corrupt") from exc


def _verify_idiom_artifact(
    archive: ContentAddressedArchive,
    reference: ArtifactRef,
    label: str,
) -> bytes:
    """Verify one canonical corpus source without consulting live checkout state."""

    reference = _artifact(reference, label)
    digest = reference.content_hash.removeprefix("sha256:")
    if (
        reference.media_type != "text/x-c"
        or reference.path != f"artifacts/sources/{digest}.c"
    ):
        raise IdiomAtlasArtifactError(
            f"{label} must be the canonical archived idiom source"
        )
    if not isinstance(archive, ContentAddressedArchive):
        raise IdiomAtlasArtifactError(
            "idiom atlas requires an explicit ContentAddressedArchive"
        )
    try:
        data = archive.verify(reference)
    except (ArchiveError, OSError, TypeError, ValueError) as exc:
        raise IdiomAtlasArtifactError(f"{label} is missing or corrupt") from exc
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IdiomAtlasArtifactError(f"{label} is not UTF-8") from exc
    return data


def _coerce_manifest(value: Any) -> RunManifest:
    if isinstance(value, RunManifest):
        return value
    if isinstance(value, Mapping):
        try:
            return RunManifest.from_dict(value)
        except (SearchValidationError, TypeError, ValueError) as exc:
            raise IdiomAtlasInputError("idiom atlas needs a valid RunManifest") from exc
    raise IdiomAtlasInputError("idiom atlas needs a typed RunManifest")


def _manifest_lane_budget(manifest: RunManifest) -> Budget:
    if IDIOM_LANE not in manifest.selected_lanes:
        raise IdiomAtlasInputError(f"{IDIOM_LANE} is not selected by the manifest")
    try:
        budget = manifest.lane_budgets[IDIOM_LANE]
    except (KeyError, TypeError) as exc:
        raise IdiomAtlasBudgetError(f"manifest has no budget for {IDIOM_LANE}") from exc
    if not isinstance(budget, Budget):
        try:
            budget = Budget.from_dict(budget)
        except (SearchValidationError, TypeError, ValueError) as exc:
            raise IdiomAtlasBudgetError(f"manifest budget for {IDIOM_LANE} is invalid") from exc
    if budget.unit not in {"attempts", "candidates", "tasks"}:
        raise IdiomAtlasBudgetError(
            f"{IDIOM_LANE} requires an attempts, candidates, or tasks budget"
        )
    return budget


def _manifest_binding(manifest: RunManifest) -> tuple[str, str, str]:
    config_identity = _identity(manifest.config_identity, "manifest config identity")
    try:
        tool_identity = manifest.tool_identities[IDIOM_LANE]
    except (KeyError, TypeError) as exc:
        raise IdiomAtlasInputError(f"manifest has no tool identity for {IDIOM_LANE}") from exc
    return config_identity, _identity(tool_identity, IDIOM_LANE + " tool identity"), hash_canonical(manifest.to_dict())


# production-audit: pure-value
@dataclass(frozen=True)
class IdiomAtlasTargetInput:
    """One archive-verified recipient draft the atlas may rewrite.

    The draft bytes are supplied by the caller only so the factory can compare
    them to the exact archive object; the factory never resolves
    ``draft_artifact.path`` against a repository or another filesystem root.
    """

    recipient_id: str
    target_identity: str
    draft_artifact: ArtifactRef
    draft_bytes: bytes
    platform: Optional[str] = None

    def __post_init__(self) -> None:
        try:
            validate_id(self.recipient_id, "target recipient_id")
            target_identity = _identity(self.target_identity, "target identity")
            draft_artifact = _artifact(self.draft_artifact, "draft artifact")
        except IdiomAtlasError:
            raise
        if not isinstance(self.draft_bytes, bytes) or not self.draft_bytes:
            raise IdiomAtlasArtifactError("draft bytes must be nonempty bytes")
        if len(self.draft_bytes) > _MAX_SOURCE_BYTES:
            raise IdiomAtlasArtifactError("draft source is too large")
        if hash_bytes(self.draft_bytes) != draft_artifact.content_hash:
            raise IdiomAtlasArtifactError("draft bytes disagree with draft artifact")
        if draft_artifact.byte_size != len(self.draft_bytes):
            raise IdiomAtlasArtifactError("draft artifact byte size differs from bytes")
        digest = draft_artifact.content_hash.removeprefix("sha256:")
        if (
            draft_artifact.media_type != "text/x-c"
            or draft_artifact.path != f"artifacts/sources/{digest}.c"
        ):
            raise IdiomAtlasArtifactError(
                "draft artifact must be the canonical archived draft source"
            )
        try:
            self.draft_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise IdiomAtlasArtifactError("draft source is not UTF-8") from exc
        recipient_platform = self.recipient_id.split(":", 1)[0]
        if recipient_platform not in SUPPORTED_TARGET_PLATFORMS:
            raise IdiomAtlasInputError("target recipient platform is unsupported")
        platform = self.platform if self.platform is not None else recipient_platform
        if not isinstance(platform, str) or platform not in SUPPORTED_TARGET_PLATFORMS:
            raise IdiomAtlasInputError("target platform is unsupported")
        if platform != recipient_platform:
            raise IdiomAtlasInputError("target platform differs from recipient")
        object.__setattr__(self, "target_identity", target_identity)
        object.__setattr__(self, "draft_artifact", draft_artifact)
        object.__setattr__(self, "platform", platform)

    @property
    def draft_identity(self) -> str:
        return self.draft_artifact.content_hash

    @property
    def target_evidence_identity(self) -> str:
        return hash_canonical(self.to_dict())

    def to_dict(self, *, include_bytes: bool = False) -> dict[str, Any]:
        result = {
            "protocol": TARGET_INPUT_PROTOCOL,
            "recipient_id": self.recipient_id,
            "target_identity": self.target_identity,
            "draft_artifact": self.draft_artifact.to_dict(),
            "draft_identity": self.draft_identity,
            "platform": self.platform,
        }
        if include_bytes:
            try:
                result["draft_bytes"] = self.draft_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise IdiomAtlasArtifactError("draft source cannot be serialized as UTF-8") from exc
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "IdiomAtlasTargetInput":
        data = _strict_mapping(value, "target input")
        if set(data) != _PROVIDER_TARGET_KEYS:
            raise IdiomAtlasInputError(
                "target input fields are incomplete or unknown"
            )
        if data.get("protocol") != TARGET_INPUT_PROTOCOL:
            raise IdiomAtlasInputError("target input protocol is unsupported")
        artifact_value = data.get("draft_artifact")
        bytes_value = data.get("draft_bytes")
        if type(bytes_value) is not str:
            raise IdiomAtlasArtifactError(
                "target input draft_bytes must be a UTF-8 string"
            )
        if type(artifact_value) is not dict:
            raise IdiomAtlasArtifactError("target input draft_artifact must be an object")
        try:
            target = cls(
                recipient_id=data["recipient_id"],
                target_identity=data["target_identity"],
                draft_artifact=_artifact(artifact_value, "draft artifact"),
                draft_bytes=bytes_value.encode("utf-8"),
                platform=data["platform"],
            )
            declared_identity = data["draft_identity"]
            if declared_identity != target.draft_identity:
                raise IdiomAtlasArtifactError("draft identity differs from draft artifact")
            return target
        except (KeyError, TypeError, ValueError) as exc:
            raise IdiomAtlasInputError("target input fields are malformed") from exc


def _ordered_targets(
    manifest: RunManifest,
    target_inputs: Mapping[str, Any] | Sequence[Any],
    *,
    archive: ContentAddressedArchive,
) -> tuple[IdiomAtlasTargetInput, ...]:
    if type(target_inputs) is dict:
        raw_values = []
        for key, value in target_inputs.items():
            if not isinstance(key, str):
                raise IdiomAtlasSubsetViolation("target input keys must be recipient IDs")
            if isinstance(value, IdiomAtlasTargetInput) and value.recipient_id != key:
                raise IdiomAtlasSubsetViolation("target input key differs from recipient")
            if not isinstance(value, IdiomAtlasTargetInput):
                raw_data = _strict_mapping(value, "target input")
                raw_recipient = raw_data.get("recipient_id")
                if raw_recipient != key:
                    raise IdiomAtlasSubsetViolation("target input key differs from recipient")
            raw_values.append(value)
    elif isinstance(target_inputs, (tuple, list)):
        raw_values = list(target_inputs)
    else:
        raise IdiomAtlasSubsetViolation(
            "idiom atlas requires an explicit target-input mapping or sequence"
        )
    if not raw_values or len(raw_values) > _MAX_TARGETS:
        raise IdiomAtlasSubsetViolation("target inputs must be a bounded nonempty subset")
    normalized: list[IdiomAtlasTargetInput] = []
    for value in raw_values:
        if not isinstance(value, IdiomAtlasTargetInput):
            try:
                value = IdiomAtlasTargetInput.from_dict(value)
            except IdiomAtlasError:
                raise
            except (AttributeError, TypeError, ValueError) as exc:
                raise IdiomAtlasInputError("target inputs must be typed records") from exc
        normalized.append(value)
    by_id = {item.recipient_id: item for item in normalized}
    if len(by_id) != len(normalized):
        raise IdiomAtlasSubsetViolation("target inputs contain duplicate recipients")
    expected = set(manifest.queue_record_ids)
    if set(by_id) != expected:
        missing = sorted(expected.difference(by_id))
        extra = sorted(set(by_id).difference(expected))
        detail = []
        if missing:
            detail.append("missing=" + ",".join(missing))
        if extra:
            detail.append("extra=" + ",".join(extra))
        raise IdiomAtlasSubsetViolation(
            "target input subset must equal the manifest subset" + (" (" + "; ".join(detail) + ")" if detail else "")
        )
    ordered = tuple(sorted(normalized, key=lambda item: item.recipient_id))
    for item in ordered:
        expected_target = manifest.target_identities.get(item.recipient_id)
        if expected_target != item.target_identity:
            raise IdiomAtlasArtifactError(
                f"target identity differs from manifest for {item.recipient_id}"
            )
        _verify_archive_bytes(
            archive, item.draft_artifact, item.draft_bytes, item.recipient_id + " draft artifact"
        )
    return ordered


def _select_idioms(
    corpus_entries: Sequence[Any],
    *,
    archive: ContentAddressedArchive,
) -> tuple[CompilerIdiomObservation, ...]:
    """Select and deduplicate the measured idioms carried by accepted entries."""

    if isinstance(corpus_entries, (str, bytes, bytearray)) or not isinstance(
        corpus_entries, (tuple, list)
    ):
        raise IdiomAtlasInputError("corpus entries must be an explicit sequence")
    if not corpus_entries or len(corpus_entries) > _MAX_IDIOMS:
        raise IdiomAtlasInputError("corpus entries are empty or too large")
    observations = []
    for index, entry in enumerate(corpus_entries):
        if not isinstance(entry, CorpusEvidence):
            raise IdiomAtlasInputError(f"corpus entry {index} must be a typed CorpusEvidence")
        if entry.kind != "draft_landed" or entry.outcome != "accepted":
            continue
        if entry.idiom is None:
            raise IdiomAtlasInputError(
                f"accepted corpus entry {index} carries no idiom observation"
            )
        observation = entry.idiom
        if not isinstance(observation, CompilerIdiomObservation):
            raise IdiomAtlasInputError(f"corpus entry {index} idiom must be typed")
        # The idiom's before and after artifacts are archived corpus evidence.
        # A replay candidate must be reproducible from durable bytes, so a
        # missing object refuses the build instead of the later callback.
        _verify_idiom_artifact(archive, observation.before, "idiom before artifact")
        _verify_idiom_artifact(archive, observation.after, "idiom after artifact")
        observations.append(observation)
    if not observations:
        return ()
    if len(observations) > _MAX_IDIOMS:
        raise IdiomAtlasInputError("idiom evidence exceeds the provider bound")
    deduplicated = deduplicate_idioms(observations)
    return tuple(deduplicated[:_MAX_IDIOMS])


def _parse_idioms(
    raw_value: Any,
    *,
    archive: ContentAddressedArchive,
) -> tuple[CompilerIdiomObservation, ...]:
    """Parse the frozen corpus idioms without mining or deduplicating them."""

    raw_items = _strict_list(raw_value, "provider idioms")
    if len(raw_items) > _MAX_IDIOMS:
        raise IdiomAtlasInputError("provider idioms exceed the provider bound")
    parsed: list[CompilerIdiomObservation] = []
    for index, raw_item in enumerate(raw_items):
        data = _strict_mapping(raw_item, f"provider idiom {index}")
        if set(data) != _IDIOM_KEYS:
            raise IdiomAtlasInputError(
                f"provider idiom {index} fields are incomplete or unknown"
            )
        for name in ("before", "after"):
            if type(data[name]) is not dict:
                raise IdiomAtlasInputError(
                    f"provider idiom {index} {name} must be an object"
                )
        for name in ("grouped_patches", "supporting_pair_hashes", "operator_records"):
            if type(data[name]) is not list:
                raise IdiomAtlasInputError(
                    f"provider idiom {index} {name} must be an array"
                )
        if type(data["measurement"]) is not dict:
            raise IdiomAtlasInputError(
                f"provider idiom {index} measurement must be an object"
            )
        if any(type(item) is not dict for item in data["grouped_patches"]):
            raise IdiomAtlasInputError(
                f"provider idiom {index} grouped patches must be objects"
            )
        if any(type(item) is not dict for item in data["operator_records"]):
            raise IdiomAtlasInputError(
                f"provider idiom {index} operator records must be objects"
            )
        try:
            observation = CompilerIdiomObservation.from_dict(data)
        except (CompilerIdiomError, SearchValidationError, KeyError, TypeError, ValueError) as exc:
            raise IdiomAtlasInputError(
                f"provider idiom {index} is invalid"
            ) from exc
        _verify_idiom_artifact(
            archive, observation.before, f"provider idiom {index} before artifact"
        )
        _verify_idiom_artifact(
            archive, observation.after, f"provider idiom {index} after artifact"
        )
        parsed.append(observation)

    observation_ids = [item.observation_id for item in parsed]
    if observation_ids != sorted(set(observation_ids)):
        raise IdiomAtlasInputError("provider idioms must be sorted and unique")
    # ``deduplicate_idioms`` is deliberately not called here.  Reconstruction
    # must consume the already selected corpus evidence, not re-run selection.
    # Its pure grouping key is enough to reject two separately identified
    # observations that claim to be the same compiler operator.
    grouping_keys = [
        hash_canonical(
            {
                "compiler_identity": item.compiler_identity,
                "tool_identity": item.tool_identity,
                "config_identity": item.config_identity,
                "operator_records": item.operator_records,
            }
        )
        for item in parsed
    ]
    if len(grouping_keys) != len(set(grouping_keys)):
        raise IdiomAtlasInputError("provider idioms contain duplicate operators")
    return tuple(parsed)


def _bind_lineage_contexts(
    lineage_contexts: Sequence[Any],
) -> tuple[CompletedLineageContext, ...]:
    if isinstance(lineage_contexts, (str, bytes, bytearray)) or not isinstance(
        lineage_contexts, (tuple, list)
    ):
        raise IdiomAtlasInputError("lineage contexts must be an explicit sequence")
    normalized: list[CompletedLineageContext] = []
    for index, value in enumerate(lineage_contexts):
        if not isinstance(value, CompletedLineageContext):
            raise IdiomAtlasInputError(
                f"lineage context {index} must be a typed CompletedLineageContext"
            )
        normalized.append(value)
    if not normalized:
        raise IdiomAtlasInputError(
            "idiom atlas requires completed-lineage evidence before it may rewrite"
        )
    ledgers = [item.ledger_identity for item in normalized]
    if len(set(ledgers)) != len(ledgers):
        raise IdiomAtlasInputError("lineage contexts contain duplicate ledger identities")
    return tuple(sorted(normalized, key=lambda item: item.ledger_identity))


def _parse_lineage_contexts(raw_value: Any) -> tuple[CompletedLineageContext, ...]:
    """Parse complete lineage records from JSON-shaped values only."""

    raw_items = _strict_list(raw_value, "provider lineage contexts")
    contexts: list[CompletedLineageContext] = []
    for index, raw_item in enumerate(raw_items):
        data = _strict_mapping(raw_item, f"provider lineage context {index}")
        if set(data) != _LINEAGE_KEYS:
            raise IdiomAtlasInputError(
                f"provider lineage context {index} fields are incomplete or unknown"
            )
        if type(data["scorer_algorithms"]) is not list:
            raise IdiomAtlasInputError(
                f"provider lineage context {index} scorer_algorithms must be an array"
            )
        for name in ("lane_tool_identities", "recipient_target_identities"):
            values = data[name]
            if type(values) is not list or any(
                type(item) is not list or len(item) != 2 for item in values
            ):
                raise IdiomAtlasInputError(
                    f"provider lineage context {index} {name} must contain pairs"
                )
        try:
            contexts.append(CompletedLineageContext.from_dict(data))
        except (PatternInputError, KeyError, TypeError, ValueError) as exc:
            raise IdiomAtlasInputError(
                f"provider lineage context {index} is invalid"
            ) from exc
    if not contexts:
        raise IdiomAtlasInputError(
            "idiom atlas requires completed-lineage evidence before it may rewrite"
        )
    ledgers = [item.ledger_identity for item in contexts]
    if ledgers != sorted(set(ledgers)):
        raise IdiomAtlasInputError(
            "provider lineage contexts must be sorted and unique"
        )
    return tuple(contexts)


def _lineage_support(
    contexts: tuple[CompletedLineageContext, ...],
    observation: CompilerIdiomObservation,
) -> tuple[str, ...]:
    """Return the ledger identities whose completed runs support one idiom."""

    ledgers = tuple(
        context.ledger_identity
        for context in contexts
        if context.compiler_identity == observation.compiler_identity
        and (
            observation.config_identity is None
            or context.config_identity == observation.config_identity
        )
    )
    return tuple(sorted(ledgers))


def _candidate(
    *,
    recipient: IdiomAtlasTargetInput,
    source: str,
    base_source_identity: str,
    observation: CompilerIdiomObservation,
    replay_modes: Sequence[str],
    lineage_ledgers: Sequence[str],
    provenance: Mapping[str, Any],
) -> LaneCandidate:
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
        lane=IDIOM_LANE,
        depth=0,
        evaluation=None,
        status="materialized",
    )
    edge = dict(provenance)
    edge.update(
        {
            "lane": IDIOM_LANE,
            "recipient_id": recipient.recipient_id,
            "candidate_identity": candidate_id,
            "source_identity": candidate_id,
            "input_identity": recipient.target_evidence_identity,
            "kind": "idiom_atlas_candidate",
            "idiom_observation_id": observation.observation_id,
            "idiom_compiler_identity": observation.compiler_identity,
            "idiom_support_count": observation.support_count,
            "idiom_patch_ids": [patch.patch_id for patch in observation.grouped_patches],
            "idiom_lineage_ledgers": list(lineage_ledgers),
            "base_source_identity": base_source_identity,
            "replay_modes": list(replay_modes),
        }
    )
    return LaneCandidate(record, source, (_freeze_json(edge, "candidate provenance"),))


def _validate_planned_candidate(candidate: LaneCandidate, recipient_id: str) -> None:
    """Validate a coordinator-owned candidate reference without materializing it."""

    if not isinstance(candidate, LaneCandidate):
        raise IdiomAtlasInputError("idiom atlas candidates must be typed")
    record = candidate.record
    if record.lane != IDIOM_LANE or record.recipient_id != recipient_id:
        raise IdiomAtlasInputError("idiom atlas candidate binding differs from result")
    if hash_bytes(candidate.source.encode("utf-8")) != record.candidate_id:
        raise IdiomAtlasInputError("idiom atlas candidate source differs from its identity")
    artifact = record.source_artifact
    digest = record.candidate_id.removeprefix("sha256:")
    if (
        artifact.content_hash != record.candidate_id
        or artifact.path != f"artifacts/sources/{digest}.c"
        or artifact.media_type != "text/x-c"
        or artifact.byte_size != len(candidate.source.encode("utf-8"))
    ):
        raise IdiomAtlasArtifactError(
            "idiom atlas candidate must carry its canonical planned source reference"
        )
    if (
        record.parent_candidate_ids
        or record.mutation_id is not None
        or record.depth != 0
        or record.evaluation is not None
        or record.status != "materialized"
    ):
        raise IdiomAtlasInputError(
            "idiom atlas candidates must remain depth-zero planned records"
        )
    if len(candidate.provenance) != 1:
        raise IdiomAtlasInputError("idiom atlas candidates need one provenance edge")


def _base_provenance(
    *,
    provider_identity: str,
    manifest_identity: str,
    config_identity: str,
    tool_identity: str,
    recipient: IdiomAtlasTargetInput,
) -> dict[str, Any]:
    return {
        "kind": "idiom_atlas_provider",
        "source": "automation.search_idiom_atlas",
        "source_identity": MODULE_IDENTITY,
        "input_identity": recipient.target_evidence_identity,
        "lane": IDIOM_LANE,
        "recipient_id": recipient.recipient_id,
        "provider_identity": provider_identity,
        "manifest_identity": manifest_identity,
        "config_identity": config_identity,
        "lane_tool_identity": tool_identity,
        "target_identity": recipient.target_identity,
        "draft_artifact_identity": recipient.draft_artifact.content_hash,
        "target_evidence_identity": recipient.target_evidence_identity,
        "platform": recipient.platform,
    }


def _apply_observation(
    source: str,
    observation: CompilerIdiomObservation,
) -> tuple[str, str] | tuple[None, str]:
    """Replay one idiom over ``source``; return (text, mode) or (None, rejection)."""

    working = source
    modes: list[str] = []
    for patch in observation.grouped_patches:
        exact = patch.base_source_hash == source_hash(working)
        result = replay_grouped_patch(working, patch) if exact else port_grouped_patch(working, patch)
        if result.status == "no_change":
            modes.append("no_change")
            continue
        if result.status != "applied" or result.source is None:
            return None, ("patch_invalid" if result.status == "invalid" else "patch_conflict")
        modes.append("exact" if exact else "ported")
        working = result.source
    if working == source:
        return None, "no_change"
    return working, "+".join(modes) if modes else "exact"


def _result(
    *,
    recipient: IdiomAtlasTargetInput,
    candidates: Sequence[LaneCandidate],
    candidate_identities: Sequence[str],
    attempts: int,
    rejection_counts: Mapping[str, int],
    refusal_code: Optional[str],
    reason: str,
    completion_reason: str,
    provider_identity: str,
    manifest_identity: str,
    config_identity: str,
    tool_identity: str,
    summary_provenance: Mapping[str, Any],
) -> Mapping[str, Any]:
    ordered = tuple(sorted(candidates, key=lambda item: item.candidate_id))
    inputs = [
        manifest_identity,
        config_identity,
        tool_identity,
        recipient.target_identity,
        recipient.draft_artifact.content_hash,
        recipient.target_evidence_identity,
        MODULE_IDENTITY,
        provider_identity,
        # Only retained candidates are typed outputs.  Overflow identities
        # are deliberately represented by the rejection count rather than by
        # opaque hashes that a fresh process could not validate without
        # replaying the mining pass.
        *(item.candidate_id for item in ordered),
    ]
    provenance_items = [dict(summary_provenance)]
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
            "draft_artifact_identity",
            "target_evidence_identity",
            "base_source_identity",
            "idiom_observation_id",
            "idiom_compiler_identity",
        ):
            value = item.get(key)
            if isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value):
                inputs.append(value)
    provenance = tuple(
        _freeze_json(item, "provider provenance") for item in provenance_items
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


def _freeze_result(value: Mapping[str, Any], *, recipient_id: str) -> Mapping[str, Any]:
    """Validate and deep-freeze one ordinary lane callback result."""

    data = _mapping(value, "idiom atlas result")
    if set(data).difference(_RESULT_KEYS) or not _REQUIRED_RESULT_KEYS.issubset(data):
        raise IdiomAtlasInputError("idiom atlas result fields are incomplete or unknown")
    raw_candidates = data.get("candidates", ())
    if isinstance(raw_candidates, (str, bytes, bytearray)) or not isinstance(
        raw_candidates, (tuple, list)
    ):
        raise IdiomAtlasInputError("idiom atlas candidates must be a sequence")
    candidates = tuple(raw_candidates)
    candidate_ids = tuple(
        item.candidate_id for item in candidates if isinstance(item, LaneCandidate)
    )
    if len(candidate_ids) != len(candidates):
        raise IdiomAtlasInputError("idiom atlas candidates must be typed")
    if tuple(sorted(candidate_ids)) != candidate_ids or len(set(candidate_ids)) != len(candidate_ids):
        raise IdiomAtlasInputError("idiom atlas candidates must be canonical and unique")
    for item in candidates:
        if item.candidate.lane != IDIOM_LANE or item.recipient_id != recipient_id:
            raise IdiomAtlasInputError("idiom atlas candidate binding differs from result")
        _validate_planned_candidate(item, recipient_id)

    attempts = data.get("attempts", 0)
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < len(candidates):
        raise IdiomAtlasInputError("idiom atlas attempts are invalid")
    raw_inputs = data.get("input_identities", ())
    if isinstance(raw_inputs, (str, bytes, bytearray)) or not isinstance(
        raw_inputs, (tuple, list)
    ):
        raise IdiomAtlasInputError("idiom atlas input identities must be a sequence")
    input_identities = [_identity(item, "idiom atlas input identity") for item in raw_inputs]
    if len(set(input_identities)) != len(input_identities):
        raise IdiomAtlasInputError("idiom atlas input identities must be unique")

    raw_provenance = data.get("provenance", ())
    if isinstance(raw_provenance, (str, bytes, bytearray)) or not isinstance(
        raw_provenance, (tuple, list)
    ):
        raise IdiomAtlasInputError("idiom atlas provenance must be a sequence")
    provenance = []
    for index, item in enumerate(raw_provenance):
        edge = _mapping(item, f"idiom atlas provenance[{index}]")
        if edge.get("lane") != IDIOM_LANE or edge.get("recipient_id") != recipient_id:
            raise IdiomAtlasInputError("idiom atlas provenance binding differs from result")
        if not isinstance(edge.get("kind"), str) or not edge["kind"]:
            raise IdiomAtlasInputError("idiom atlas provenance kind is invalid")
        if not isinstance(edge.get("source"), str) or not edge["source"]:
            raise IdiomAtlasInputError("idiom atlas provenance source is invalid")
        _identity(edge.get("source_identity"), "idiom atlas provenance source identity")
        _identity(edge.get("input_identity"), "idiom atlas provenance input identity")
        provenance.append(_freeze_json(edge, f"idiom atlas provenance[{index}]"))

    raw_rejections = data.get("rejection_counts", {})
    rejection_map = _mapping(raw_rejections, "idiom atlas rejection counts")
    rejection_counts: dict[str, int] = {}
    for key, count in rejection_map.items():
        if not isinstance(key, str) or not key:
            raise IdiomAtlasInputError("idiom atlas rejection class is invalid")
        if key not in _REJECTION_CLASSES:
            raise IdiomAtlasInputError("idiom atlas rejection class is unknown")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise IdiomAtlasInputError("idiom atlas rejection count is invalid")
        rejection_counts[key] = count

    completion_reason = data.get("completion_reason")
    if completion_reason not in _COMPLETION_REASONS:
        raise IdiomAtlasInputError("idiom atlas completion reason is invalid")
    reason = data.get("reason", "")
    if not isinstance(reason, str):
        raise IdiomAtlasInputError("idiom atlas reason must be text")
    refusal_code = data.get("refusal_code")
    if refusal_code is not None and (not isinstance(refusal_code, str) or not refusal_code):
        raise IdiomAtlasInputError("idiom atlas refusal code must be text")

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


def _serialized_result(recipient_id: str, result: Mapping[str, Any]) -> dict[str, Any]:
    """Serialize one result completely, including planned candidates and edges."""

    return _plain_json(
        {
            "recipient_id": recipient_id,
            "candidates": [
                candidate.to_dict() for candidate in result.get("candidates", ())
            ],
            "candidate_ids": [
                candidate.candidate_id for candidate in result.get("candidates", ())
            ],
            "attempts": result.get("attempts", 0),
            "input_identities": list(result.get("input_identities", ())),
            "provenance": [
                _plain_json(item, "idiom atlas result provenance")
                for item in result.get("provenance", ())
            ],
            "rejection_counts": dict(result.get("rejection_counts", {})),
            "completion_reason": result.get("completion_reason"),
            "refusal_code": result.get("refusal_code"),
            "reason": result.get("reason", ""),
        },
        "idiom atlas serialized result",
    )


def _parse_candidate(value: Any, label: str) -> LaneCandidate:
    """Parse one complete planned candidate from JSON-shaped state."""

    data = _strict_mapping(value, label)
    if set(data) != _PROVIDER_CANDIDATE_KEYS:
        raise IdiomAtlasInputError(f"{label} fields are incomplete or unknown")
    if type(data["candidate"]) is not dict:
        raise IdiomAtlasInputError(f"{label}.candidate must be an object")
    if type(data["source"]) is not str:
        raise IdiomAtlasInputError(f"{label}.source must be text")
    raw_provenance = data["provenance"]
    if type(raw_provenance) is not list or any(
        type(item) is not dict for item in raw_provenance
    ):
        raise IdiomAtlasInputError(f"{label}.provenance must be an array of objects")
    try:
        candidate_record = CandidateRecord.from_dict(data["candidate"])
        return LaneCandidate(
            candidate_record,
            data["source"],
            tuple(
                _freeze_json(item, f"{label}.provenance[{index}]")
                for index, item in enumerate(raw_provenance)
            ),
        )
    except (LaneError, SearchValidationError, KeyError, TypeError, ValueError) as exc:
        raise IdiomAtlasInputError(f"{label} is invalid") from exc


def _expected_result_inputs(
    *,
    result: Mapping[str, Any],
    target: IdiomAtlasTargetInput,
    provider_identity: str,
    manifest_identity: str,
    config_identity: str,
    tool_identity: str,
) -> tuple[str, ...]:
    """Reproduce the result identity list without applying any patch."""

    candidates = result.get("candidates", ())
    inputs: list[str] = [
        manifest_identity,
        config_identity,
        tool_identity,
        target.target_identity,
        target.draft_artifact.content_hash,
        target.target_evidence_identity,
        MODULE_IDENTITY,
        provider_identity,
        *(item.candidate_id for item in candidates),
    ]
    for edge in result.get("provenance", ()):
        for key in _PROVENANCE_IDENTITY_KEYS:
            value = edge.get(key)
            if isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value):
                inputs.append(value)
    return tuple(dict.fromkeys(inputs))


def _validate_result_bindings(
    *,
    recipient_id: str,
    result: Mapping[str, Any],
    target: IdiomAtlasTargetInput,
    provider_identity: str,
    manifest_identity: str,
    config_identity: str,
    tool_identity: str,
    idioms: Sequence[CompilerIdiomObservation],
    lineage_contexts: Sequence[CompletedLineageContext],
) -> None:
    """Validate one retained result against all frozen provider evidence."""

    if set(result).difference(_RESULT_KEYS) or not _REQUIRED_RESULT_KEYS.issubset(result):
        raise IdiomAtlasInputError("idiom atlas result fields are incomplete or unknown")
    candidates = result["candidates"]
    if not isinstance(candidates, tuple):
        raise IdiomAtlasInputError("idiom atlas result candidates are not frozen")
    for candidate in candidates:
        _validate_planned_candidate(candidate, recipient_id)
    if result["input_identities"] != _expected_result_inputs(
        result=result,
        target=target,
        provider_identity=provider_identity,
        manifest_identity=manifest_identity,
        config_identity=config_identity,
        tool_identity=tool_identity,
    ):
        raise IdiomAtlasInputError("idiom atlas result input identities do not match evidence")

    provenance = result["provenance"]
    if not isinstance(provenance, tuple) or len(provenance) != len(candidates) + 1:
        raise IdiomAtlasInputError("idiom atlas result provenance does not cover its candidates")

    def _validate_common(edge: Mapping[str, Any], expected_kind: str) -> None:
        expected_fields = (
            _SUMMARY_PROVENANCE_KEYS
            if expected_kind == "idiom_atlas_summary"
            else _CANDIDATE_PROVENANCE_KEYS
        )
        if set(edge) != expected_fields:
            raise IdiomAtlasInputError("idiom atlas provenance fields are incomplete or unknown")
        if edge.get("kind") != expected_kind:
            raise IdiomAtlasInputError("idiom atlas provenance kind is invalid")
        if edge.get("source") != "automation.search_idiom_atlas":
            raise IdiomAtlasInputError("idiom atlas provenance source is invalid")
        if edge.get("lane") != IDIOM_LANE or edge.get("recipient_id") != recipient_id:
            raise IdiomAtlasInputError("idiom atlas provenance recipient binding differs")
        expected = {
            "input_identity": target.target_evidence_identity,
            "provider_identity": provider_identity,
            "manifest_identity": manifest_identity,
            "config_identity": config_identity,
            "lane_tool_identity": tool_identity,
            "target_identity": target.target_identity,
            "draft_artifact_identity": target.draft_artifact.content_hash,
            "target_evidence_identity": target.target_evidence_identity,
            "platform": target.platform,
        }
        for key, expected_value in expected.items():
            if edge.get(key) != expected_value:
                raise IdiomAtlasInputError(
                    f"idiom atlas provenance {key} differs from frozen input"
                )

    summary = provenance[0]
    _validate_common(summary, "idiom_atlas_summary")
    if summary.get("source_identity") != MODULE_IDENTITY:
        raise IdiomAtlasInputError("idiom atlas summary source identity is forged")
    if (
        isinstance(summary.get("corpus_idiom_count"), bool)
        or not isinstance(summary.get("corpus_idiom_count"), int)
        or summary.get("corpus_idiom_count") != len(idioms)
    ):
        raise IdiomAtlasInputError("idiom atlas summary corpus count differs")
    if (
        isinstance(summary.get("applicable_idiom_count"), bool)
        or not isinstance(summary.get("applicable_idiom_count"), int)
        or summary.get("applicable_idiom_count") != result["attempts"]
    ):
        raise IdiomAtlasInputError("idiom atlas summary attempt count differs")
    expected_ledgers = tuple(item.ledger_identity for item in lineage_contexts)
    if tuple(summary.get("lineage_ledger_identities", ())) != expected_ledgers:
        raise IdiomAtlasInputError("idiom atlas summary lineage evidence differs")

    observations = {item.observation_id: item for item in idioms}
    for candidate, edge in zip(candidates, provenance[1:]):
        _validate_common(edge, "idiom_atlas_candidate")
        if edge.get("source_identity") != candidate.candidate_id:
            raise IdiomAtlasInputError("idiom atlas candidate source identity is forged")
        if edge.get("candidate_identity") != candidate.candidate_id:
            raise IdiomAtlasInputError("idiom atlas candidate identity is forged")
        if dict(edge) != dict(candidate.provenance[0]):
            raise IdiomAtlasInputError("idiom atlas candidate provenance differs from result")
        observation = observations.get(edge.get("idiom_observation_id"))
        if observation is None:
            raise IdiomAtlasInputError("idiom atlas candidate names an unknown idiom")
        if edge.get("idiom_compiler_identity") != observation.compiler_identity:
            raise IdiomAtlasInputError("idiom atlas candidate compiler evidence differs")
        if (
            isinstance(edge.get("idiom_support_count"), bool)
            or not isinstance(edge.get("idiom_support_count"), int)
            or edge.get("idiom_support_count") != observation.support_count
        ):
            raise IdiomAtlasInputError("idiom atlas candidate support count differs")
        if tuple(edge.get("idiom_patch_ids", ())) != tuple(
            patch.patch_id for patch in observation.grouped_patches
        ):
            raise IdiomAtlasInputError("idiom atlas candidate patch evidence differs")
        if tuple(edge.get("idiom_lineage_ledgers", ())) != _lineage_support(
            tuple(lineage_contexts), observation
        ):
            raise IdiomAtlasInputError("idiom atlas candidate lineage evidence differs")
        if edge.get("base_source_identity") != target.draft_identity:
            raise IdiomAtlasInputError("idiom atlas depth-zero base source differs")
        modes = tuple(edge.get("replay_modes", ()))
        if not modes or any(mode not in {"exact", "ported"} for mode in modes):
            raise IdiomAtlasInputError("idiom atlas replay mode evidence is invalid")

    rejection_counts = result["rejection_counts"]
    for name in rejection_counts:
        if name not in _REJECTION_CLASSES:
            raise IdiomAtlasInputError("idiom atlas rejection class is unknown")
    duplicate_count = rejection_counts.get("duplicate_candidate", 0)
    overflow_count = rejection_counts.get("budget_exhausted", 0)
    if result["attempts"] != len(candidates) + duplicate_count + overflow_count:
        raise IdiomAtlasInputError("idiom atlas attempts do not match retained result evidence")
    has_candidates = bool(candidates)
    if has_candidates:
        expected_completion = "budget_exhausted" if overflow_count else "matched_pending_oracle"
        expected_refusal = None
        expected_reason = "idiom atlas produced deterministic measured rewrites of the archived draft"
    elif overflow_count:
        expected_completion = "budget_exhausted"
        expected_refusal = "idiom_atlas_budget_exhausted"
        expected_reason = "idiom atlas candidate budget was exhausted before a candidate could be returned"
    elif result["attempts"]:
        expected_completion = "inapplicable"
        expected_refusal = "idiom_atlas_no_candidate"
        expected_reason = "applicable idioms produced no distinct candidate"
    elif idioms:
        expected_completion = "inapplicable"
        expected_refusal = "idiom_atlas_no_applicable_idiom"
        expected_reason = "no deduplicated idiom is applicable to this draft under the run compiler"
    else:
        expected_completion = "inapplicable"
        expected_refusal = "idiom_atlas_corpus_empty"
        expected_reason = "the corpus supplied no accepted draft-landed idiom"
    if result["completion_reason"] != expected_completion:
        raise IdiomAtlasInputError("idiom atlas result completion reason differs")
    if result.get("refusal_code") != expected_refusal:
        raise IdiomAtlasInputError("idiom atlas result refusal differs")
    if result["reason"] != expected_reason:
        raise IdiomAtlasInputError("idiom atlas result reason differs")


# production-audit: pure-value
@dataclass(frozen=True)
class IdiomAtlasProvider:
    """Frozen idiom-atlas results and an ordinary replay-safe callback."""

    lane: str
    manifest_identity: str
    config_identity: str
    tool_identity: str
    provider_identity: str
    target_inputs: tuple[IdiomAtlasTargetInput, ...]
    idioms: tuple[CompilerIdiomObservation, ...]
    lineage_contexts: tuple[CompletedLineageContext, ...]
    results: tuple[tuple[str, Mapping[str, Any]], ...]

    def __post_init__(self) -> None:
        if self.lane != IDIOM_LANE:
            raise IdiomAtlasInputError("unsupported idiom atlas lane")
        _identity(self.manifest_identity, "provider manifest identity")
        _identity(self.config_identity, "provider config identity")
        _identity(self.tool_identity, "provider tool identity")
        _identity(self.provider_identity, "provider identity")
        if not isinstance(self.target_inputs, tuple):
            try:
                object.__setattr__(self, "target_inputs", tuple(self.target_inputs))
            except TypeError as exc:
                raise IdiomAtlasInputError("provider target inputs must be a sequence") from exc
        if any(not isinstance(item, IdiomAtlasTargetInput) for item in self.target_inputs):
            raise IdiomAtlasInputError("provider target inputs must be typed")
        target_ids = tuple(item.recipient_id for item in self.target_inputs)
        if len(set(target_ids)) != len(target_ids):
            raise IdiomAtlasSubsetViolation("provider target inputs contain duplicate recipients")
        if target_ids != tuple(sorted(target_ids)):
            raise IdiomAtlasInputError("provider target inputs must be canonical")
        if not self.target_inputs:
            raise IdiomAtlasInputError("provider target inputs must be nonempty")
        if not isinstance(self.idioms, tuple) or any(
            not isinstance(item, CompilerIdiomObservation) for item in self.idioms
        ):
            raise IdiomAtlasInputError("provider idioms must be typed observations")
        observation_ids = [item.observation_id for item in self.idioms]
        if observation_ids != sorted(observation_ids) or len(set(observation_ids)) != len(observation_ids):
            raise IdiomAtlasInputError("provider idioms must be canonical and unique")
        idiom_grouping_keys = [
            hash_canonical(
                {
                    "compiler_identity": item.compiler_identity,
                    "tool_identity": item.tool_identity,
                    "config_identity": item.config_identity,
                    "operator_records": item.operator_records,
                }
            )
            for item in self.idioms
        ]
        if len(idiom_grouping_keys) != len(set(idiom_grouping_keys)):
            raise IdiomAtlasInputError("provider idioms contain duplicate operators")
        if not isinstance(self.lineage_contexts, tuple) or any(
            not isinstance(item, CompletedLineageContext) for item in self.lineage_contexts
        ):
            raise IdiomAtlasInputError("provider lineage contexts must be typed")
        ledger_ids = [item.ledger_identity for item in self.lineage_contexts]
        if ledger_ids != sorted(set(ledger_ids)) or not ledger_ids:
            raise IdiomAtlasInputError("provider lineage contexts must be canonical")
        try:
            raw_results = tuple(self.results)
        except TypeError as exc:
            raise IdiomAtlasInputError("provider results must be a sequence") from exc
        result_ids: list[str] = []
        normalized_results: list[tuple[str, Mapping[str, Any]]] = []
        for item in raw_results:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise IdiomAtlasInputError("provider results must be recipient/result pairs")
            recipient_id, result = item
            if not isinstance(recipient_id, str):
                raise IdiomAtlasInputError("provider result recipient must be text")
            try:
                validate_id(recipient_id, "provider result recipient")
            except (SearchValidationError, TypeError, ValueError) as exc:
                raise IdiomAtlasInputError("provider result recipient is invalid") from exc
            result_ids.append(recipient_id)
            normalized_results.append(
                (recipient_id, _freeze_result(result, recipient_id=recipient_id))
            )
        result_ids_tuple = tuple(result_ids)
        if result_ids_tuple != tuple(sorted(result_ids_tuple)) or len(set(result_ids_tuple)) != len(result_ids_tuple):
            raise IdiomAtlasInputError("provider results must be unique and canonical")
        if set(result_ids_tuple) != set(target_ids):
            raise IdiomAtlasSubsetViolation("provider results must cover the frozen target subset")
        object.__setattr__(self, "results", tuple(normalized_results))
        expected_provider_identity = _provider_identity(
            manifest_identity=self.manifest_identity,
            config_identity=self.config_identity,
            tool_identity=self.tool_identity,
            targets=self.target_inputs,
            idioms=self.idioms,
            lineage_contexts=self.lineage_contexts,
        )
        if self.provider_identity != expected_provider_identity:
            raise IdiomAtlasInputError("provider identity differs from immutable input evidence")
        for recipient_id, result in self.results:
            target = next(item for item in self.target_inputs if item.recipient_id == recipient_id)
            _validate_result_bindings(
                recipient_id=recipient_id,
                result=result,
                target=target,
                provider_identity=self.provider_identity,
                manifest_identity=self.manifest_identity,
                config_identity=self.config_identity,
                tool_identity=self.tool_identity,
                idioms=self.idioms,
                lineage_contexts=self.lineage_contexts,
            )

    def callback(self, recipient: Recipient) -> Mapping[str, Any]:
        if not isinstance(recipient, Recipient):
            raise IdiomAtlasInputError("idiom atlas callback needs a typed Recipient")
        for recipient_id, result in self.results:
            if recipient_id == recipient.recipient_id:
                # Build a new outer mapping only.  All nested values are frozen
                # candidates, tuples, and mapping proxies, so replay cannot
                # mutate the provider's retained result.
                return dict(result)
        raise IdiomAtlasSubsetViolation(
            f"recipient {recipient.recipient_id} is outside the provider subset"
        )

    def __call__(self, recipient: Recipient) -> Mapping[str, Any]:
        return self.callback(recipient)

    def to_adapter_mapping(self) -> dict[str, Callable[[Recipient], Mapping[str, Any]]]:
        return {self.lane: self.callback}

    def _state_payload(self) -> dict[str, Any]:
        return {
            "protocol": IDIOM_PROVIDER_PROTOCOL,
            "schema_version": _PROVIDER_SCHEMA_VERSION,
            "lane": self.lane,
            "manifest_identity": self.manifest_identity,
            "config_identity": self.config_identity,
            "tool_identity": self.tool_identity,
            "provider_identity": self.provider_identity,
            "target_inputs": [
                item.to_dict(include_bytes=True) for item in self.target_inputs
            ],
            "idioms": [item.to_dict() for item in self.idioms],
            "lineage_contexts": [item.to_dict() for item in self.lineage_contexts],
            "results": [
                _serialized_result(recipient_id, result)
                for recipient_id, result in self.results
            ],
        }

    @property
    def state_identity(self) -> str:
        """Identity of the complete callback state, including frozen results."""

        return hash_canonical(self._state_payload())

    def to_dict(self) -> dict[str, Any]:
        result = self._state_payload()
        result["state_identity"] = self.state_identity
        return result

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        archive: ContentAddressedArchive,
    ) -> "IdiomAtlasProvider":
        """Reconstruct the frozen provider from complete archived state.

        This path intentionally consumes the stored candidate results.  It
        does not select corpus entries, invoke replay, consult a checkout, or
        call an executable.  The supplied archive is used only to verify the
        immutable target and corpus source artifacts that the stored state
        names.
        """

        data = _strict_mapping(value, "idiom atlas provider")
        if set(data) != _PROVIDER_KEYS:
            raise IdiomAtlasInputError(
                "idiom atlas provider fields are incomplete or unknown"
            )
        if data.get("protocol") != IDIOM_PROVIDER_PROTOCOL:
            raise IdiomAtlasInputError("idiom atlas provider protocol is unsupported")
        if (
            type(data.get("schema_version")) is not int
            or data.get("schema_version") != _PROVIDER_SCHEMA_VERSION
        ):
            raise IdiomAtlasInputError("idiom atlas provider schema version is unsupported")
        if not isinstance(archive, ContentAddressedArchive):
            raise IdiomAtlasArtifactError(
                "idiom atlas provider reconstruction requires a ContentAddressedArchive"
            )

        manifest_identity = _identity(
            data["manifest_identity"], "provider manifest identity"
        )
        config_identity = _identity(
            data["config_identity"], "provider config identity"
        )
        tool_identity = _identity(data["tool_identity"], "provider tool identity")
        provider_identity = _identity(
            data["provider_identity"], "provider identity"
        )

        raw_targets = _strict_list(data["target_inputs"], "provider target inputs")
        targets = tuple(
            IdiomAtlasTargetInput.from_dict(item)
            for item in raw_targets
        )
        for target in targets:
            _verify_archive_bytes(
                archive,
                target.draft_artifact,
                target.draft_bytes,
                target.recipient_id + " draft artifact",
            )

        idioms = _parse_idioms(data["idioms"], archive=archive)
        contexts = _parse_lineage_contexts(data["lineage_contexts"])

        raw_results = _strict_list(data["results"], "provider results")
        parsed_results: list[tuple[str, Mapping[str, Any]]] = []
        result_fields = _PROVIDER_RESULT_KEYS
        for index, raw_result in enumerate(raw_results):
            result_data = _strict_mapping(raw_result, f"provider result {index}")
            if set(result_data) != result_fields:
                raise IdiomAtlasInputError(
                    f"provider result {index} fields are incomplete or unknown"
                )
            recipient_id = result_data["recipient_id"]
            if not isinstance(recipient_id, str):
                raise IdiomAtlasInputError(
                    f"provider result {index} recipient is invalid"
                )
            try:
                validate_id(recipient_id, "provider result recipient")
            except (SearchValidationError, TypeError, ValueError) as exc:
                raise IdiomAtlasInputError(
                    f"provider result {index} recipient is invalid"
                ) from exc

            raw_candidates = _strict_list(
                result_data["candidates"],
                f"provider result {index} candidates",
            )
            candidates = tuple(
                _parse_candidate(
                    item,
                    f"provider result {index} candidate {candidate_index}",
                )
                for candidate_index, item in enumerate(raw_candidates)
            )
            raw_candidate_ids = _strict_list(
                result_data["candidate_ids"],
                f"provider result {index} candidate_ids",
            )
            if tuple(raw_candidate_ids) != tuple(item.candidate_id for item in candidates):
                raise IdiomAtlasInputError(
                    f"provider result {index} candidate ids differ from candidates"
                )
            for name in ("input_identities", "provenance"):
                if type(result_data[name]) is not list:
                    raise IdiomAtlasInputError(
                        f"provider result {index} {name} must be an array"
                    )
            if any(type(item) is not dict for item in result_data["provenance"]):
                raise IdiomAtlasInputError(
                    f"provider result {index} provenance must contain objects"
                )
            if type(result_data["rejection_counts"]) is not dict:
                raise IdiomAtlasInputError(
                    f"provider result {index} rejection_counts must be an object"
                )
            normalized_result: dict[str, Any] = {
                "candidates": candidates,
                "attempts": result_data["attempts"],
                "input_identities": result_data["input_identities"],
                "provenance": result_data["provenance"],
                "rejection_counts": result_data["rejection_counts"],
                "completion_reason": result_data["completion_reason"],
                "reason": result_data["reason"],
            }
            if result_data["refusal_code"] is not None:
                normalized_result["refusal_code"] = result_data["refusal_code"]
            parsed_results.append((recipient_id, normalized_result))

        reconstructed = cls(
            lane=data["lane"],
            manifest_identity=manifest_identity,
            config_identity=config_identity,
            tool_identity=tool_identity,
            provider_identity=provider_identity,
            target_inputs=targets,
            idioms=idioms,
            lineage_contexts=contexts,
            results=tuple(parsed_results),
        )
        declared_state_identity = _identity(
            data["state_identity"], "provider state identity"
        )
        if reconstructed.state_identity != declared_state_identity:
            raise IdiomAtlasInputError(
                "provider state identity differs from serialized state"
            )
        return reconstructed


def _provider_identity(
    *,
    manifest_identity: str,
    config_identity: str,
    tool_identity: str,
    targets: Sequence[IdiomAtlasTargetInput],
    idioms: Sequence[CompilerIdiomObservation],
    lineage_contexts: Sequence[CompletedLineageContext],
) -> str:
    return hash_canonical(
        {
            "protocol": IDIOM_PROVIDER_PROTOCOL,
            "module_identity": MODULE_IDENTITY,
            "manifest_identity": manifest_identity,
            "config_identity": config_identity,
            "tool_identity": tool_identity,
            "targets": [item.to_dict(include_bytes=True) for item in targets],
            "idioms": [item.to_dict() for item in idioms],
            "lineage_contexts": [item.to_dict() for item in lineage_contexts],
        }
    )


def _results(
    *,
    targets: Sequence[IdiomAtlasTargetInput],
    idioms: Sequence[CompilerIdiomObservation],
    lineage_contexts: tuple[CompletedLineageContext, ...],
    manifest_compiler_identity: str,
    budget: Budget,
    provider_identity: str,
    config_identity: str,
    tool_identity: str,
    manifest_identity: str,
) -> tuple[tuple[str, Mapping[str, Any]], ...]:
    limit = budget.limit
    results: list[tuple[str, Mapping[str, Any]]] = []
    for target in targets:
        draft_text = target.draft_bytes.decode("utf-8")
        draft_hash = target.draft_identity
        candidates: list[LaneCandidate] = []
        seen_candidate_ids: set[str] = set()
        unique_candidate_ids: list[str] = []
        rejection_counts: dict[str, int] = {}
        applicable = 0
        overflow = 0
        compiler_mismatch = 0
        unsupported = 0
        for observation in idioms:
            if observation.compiler_identity != manifest_compiler_identity:
                compiler_mismatch += 1
                continue
            ledgers = _lineage_support(lineage_contexts, observation)
            if not ledgers:
                unsupported += 1
                continue
            applied_text, mode = _apply_observation(draft_text, observation)
            if applied_text is None:
                rejection_counts[mode] = rejection_counts.get(mode, 0) + 1
                continue
            applicable += 1
            candidate_id = hash_bytes(applied_text.encode("utf-8"))
            if candidate_id in seen_candidate_ids:
                rejection_counts["duplicate_candidate"] = (
                    rejection_counts.get("duplicate_candidate", 0) + 1
                )
                continue
            seen_candidate_ids.add(candidate_id)
            unique_candidate_ids.append(candidate_id)
            if len(candidates) >= limit:
                overflow += 1
                continue
            provenance = _base_provenance(
                provider_identity=provider_identity,
                manifest_identity=manifest_identity,
                config_identity=config_identity,
                tool_identity=tool_identity,
                recipient=target,
            )
            candidates.append(
                _candidate(
                    recipient=target,
                    source=applied_text,
                    base_source_identity=draft_hash,
                    observation=observation,
                    replay_modes=mode.split("+"),
                    lineage_ledgers=ledgers,
                    provenance=provenance,
                )
            )
        if compiler_mismatch:
            rejection_counts["compiler_mismatch"] = compiler_mismatch
        if unsupported:
            rejection_counts["no_lineage_support"] = unsupported
        if overflow:
            rejection_counts["budget_exhausted"] = overflow
        summary = _base_provenance(
            provider_identity=provider_identity,
            manifest_identity=manifest_identity,
            config_identity=config_identity,
            tool_identity=tool_identity,
            recipient=target,
        )
        summary.update(
            {
                "kind": "idiom_atlas_summary",
                "corpus_idiom_count": len(idioms),
                "applicable_idiom_count": applicable,
                "lineage_ledger_identities": [
                    item.ledger_identity for item in lineage_contexts
                ],
            }
        )
        if candidates:
            completion = "budget_exhausted" if overflow else "matched_pending_oracle"
            refusal = None
            reason = "idiom atlas produced deterministic measured rewrites of the archived draft"
        elif overflow:
            completion = "budget_exhausted"
            refusal = "idiom_atlas_budget_exhausted"
            reason = "idiom atlas candidate budget was exhausted before a candidate could be returned"
        elif applicable:
            completion = "inapplicable"
            refusal = "idiom_atlas_no_candidate"
            reason = "applicable idioms produced no distinct candidate"
        elif idioms:
            completion = "inapplicable"
            refusal = "idiom_atlas_no_applicable_idiom"
            reason = "no deduplicated idiom is applicable to this draft under the run compiler"
        else:
            completion = "inapplicable"
            refusal = "idiom_atlas_corpus_empty"
            reason = "the corpus supplied no accepted draft-landed idiom"
        results.append(
            (
                target.recipient_id,
                _result(
                    recipient=target,
                    candidates=candidates,
                    candidate_identities=tuple(unique_candidate_ids),
                    attempts=applicable,
                    rejection_counts=rejection_counts,
                    refusal_code=refusal,
                    reason=reason,
                    completion_reason=completion,
                    provider_identity=provider_identity,
                    manifest_identity=manifest_identity,
                    config_identity=config_identity,
                    tool_identity=tool_identity,
                    summary_provenance=summary,
                ),
            )
        )
    return tuple(results)


def build_idiom_atlas_provider(
    manifest: RunManifest | Mapping[str, Any],
    target_inputs: Mapping[str, Any] | Sequence[Any],
    corpus_entries: Sequence[Any],
    lineage_contexts: Sequence[Any],
    *,
    archive: ContentAddressedArchive,
) -> IdiomAtlasProvider:
    """Build a frozen idiom-atlas provider from exact archive-owned inputs."""

    typed_manifest = _coerce_manifest(manifest)
    budget = _manifest_lane_budget(typed_manifest)
    config_identity, tool_identity, manifest_identity = _manifest_binding(typed_manifest)
    targets = _ordered_targets(typed_manifest, target_inputs, archive=archive)
    idioms = _select_idioms(corpus_entries, archive=archive)
    contexts = _bind_lineage_contexts(lineage_contexts)
    provider_identity = _provider_identity(
        manifest_identity=manifest_identity,
        config_identity=config_identity,
        tool_identity=tool_identity,
        targets=targets,
        idioms=idioms,
        lineage_contexts=contexts,
    )
    results = _results(
        targets=targets,
        idioms=idioms,
        lineage_contexts=contexts,
        manifest_compiler_identity=typed_manifest.compiler_identity,
        budget=budget,
        provider_identity=provider_identity,
        config_identity=config_identity,
        tool_identity=tool_identity,
        manifest_identity=manifest_identity,
    )
    return IdiomAtlasProvider(
        lane=IDIOM_LANE,
        manifest_identity=manifest_identity,
        config_identity=config_identity,
        tool_identity=tool_identity,
        provider_identity=provider_identity,
        target_inputs=targets,
        idioms=idioms,
        lineage_contexts=contexts,
        results=results,
    )


def idiom_atlas_adapter(
    manifest: RunManifest | Mapping[str, Any],
    target_inputs: Mapping[str, Any] | Sequence[Any],
    corpus_entries: Sequence[Any],
    lineage_contexts: Sequence[Any],
    *,
    archive: ContentAddressedArchive,
) -> Callable[[Recipient], Mapping[str, Any]]:
    """Return the ordinary one-argument idiom-atlas lane callback."""

    return build_idiom_atlas_provider(
        manifest,
        target_inputs,
        corpus_entries,
        lineage_contexts,
        archive=archive,
    ).callback


def idiom_atlas_adapters(
    manifest: RunManifest | Mapping[str, Any],
    target_inputs: Mapping[str, Any] | Sequence[Any],
    corpus_entries: Sequence[Any],
    lineage_contexts: Sequence[Any],
    *,
    archive: ContentAddressedArchive,
) -> dict[str, Callable[[Recipient], Mapping[str, Any]]]:
    """Build the atlas callback as a mapping for ``LaneAdapters``."""

    typed_manifest = _coerce_manifest(manifest)
    if IDIOM_LANE not in typed_manifest.selected_lanes:
        raise IdiomAtlasInputError("manifest selects no idiom atlas lane")
    adapter = idiom_atlas_adapter(
        typed_manifest,
        target_inputs,
        corpus_entries,
        lineage_contexts,
        archive=archive,
    )
    return {IDIOM_LANE: adapter}


# Descriptive aliases used by the later production factory integration.
make_idiom_atlas_adapter = idiom_atlas_adapter
make_idiom_atlas_provider = build_idiom_atlas_provider
IdiomAtlasTarget = IdiomAtlasTargetInput


__all__ = [
    "IDIOM_LANE",
    "IDIOM_PROVIDER_PROTOCOL",
    "IdiomAtlasArtifactError",
    "IdiomAtlasBudgetError",
    "IdiomAtlasError",
    "IdiomAtlasInputError",
    "IdiomAtlasProvider",
    "IdiomAtlasSubsetViolation",
    "IdiomAtlasTarget",
    "IdiomAtlasTargetInput",
    "MODULE_IDENTITY",
    "build_idiom_atlas_provider",
    "idiom_atlas_adapter",
    "idiom_atlas_adapters",
    "make_idiom_atlas_adapter",
    "make_idiom_atlas_provider",
]
