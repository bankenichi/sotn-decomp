"""Qualified, archive-backed m2c revision benchmarking and matrix execution.

This module is the evidence boundary between the pinned m2c provider and the
generated-lane adapter.  It never checks out a revision, reads a live checkout,
or silently treats an unavailable alternate as qualified.  Every provider
call is bound to a validated integration gate, immutable target artifacts,
explicit platform identity, and the exact executable identity resolved from
the revision provider.
"""

from __future__ import annotations

import inspect
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Optional, Protocol

try:
    from .m2c_revision_provider import (
        CURRENT_M2C_REVISION,
        M2CDraftPayload,
        M2CInvocation,
        M2CProviderError,
        M2CRevisionIdentity,
        M2CRevisionProvider,
        make_invocation,
    )
    from .search_archive import ArchiveError, ContentAddressedArchive
    from .search_supervisor import (
        IntegrationGateError,
        IntegrationGateReceipt,
        validate_integration_gate,
    )
    from .search_types import (
        ArtifactRef,
        ScoreVector,
        SearchValidationError,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
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
    from search_archive import ArchiveError, ContentAddressedArchive  # type: ignore
    from search_supervisor import (  # type: ignore
        IntegrationGateError,
        IntegrationGateReceipt,
        validate_integration_gate,
    )
    from search_types import (  # type: ignore
        ArtifactRef,
        ScoreVector,
        SearchValidationError,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
    )


M2C_MATRIX_PROTOCOL = "sotn-m2c-revision-matrix-v1"
M2C_BENCHMARK_PROTOCOL = "sotn-m2c-fixed-benchmark-v1"
M2C_BENCHMARK_ARTIFACT_PROTOCOL = "sotn-m2c-benchmark-artifact-v1"
M2C_REPORT_PROTOCOL = "sotn-m2c-benchmark-report-v1"
M2C_QUALIFICATION_PROTOCOL = "sotn-m2c-qualification-v1"
M2C_VARIANT_PROTOCOL = "sotn-m2c-variant-v1"
M2C_SPEC_ARTIFACT_PROTOCOL = "sotn-m2c-matrix-spec-artifact-v1"
M2C_VARIANT_MANIFEST_PROTOCOL = "sotn-m2c-variant-manifest-v1"
M2C_EVALUATION_PROTOCOL = "sotn-m2c-evaluation-v1"
M2C_DEDUPLICATION_PROTOCOL = "sotn-m2c-deduplication-v1"
M2C_RECEIPT_PROTOCOL = "sotn-m2c-matrix-receipt-v1"
M2C_UNAVAILABLE_PROTOCOL = "sotn-m2c-unavailable-revision-v1"
SUPPORTED_PLATFORMS = ("us", "hd", "pspeu", "saturn")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_PLATFORM_RE = re.compile(r"^(us|hd|pspeu|saturn):")


class M2CProviderErrorBoundary(ValueError):
    """Provider resolution or invocation failed at a matrix boundary."""


class M2CBenchmarkError(ValueError):
    """Fixed-benchmark input, measurement, or identity refusal."""


class M2CMatrixError(ValueError):
    """Revision-matrix enumeration, archive, or receipt refusal."""


class M2CUnavailableRevision(M2CMatrixError):
    """An explicitly named pinned revision is absent or unusable."""


def _hash(value: Any, label: str, exc_type: type[ValueError]) -> str:
    try:
        return validate_hash(value, label)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise exc_type(f"{label} must be a sha256 identity") from exc


def _id(value: Any, label: str, exc_type: type[ValueError]) -> str:
    try:
        return validate_id(value, label)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise exc_type(f"{label} must be a nonempty identifier") from exc


def _commit(value: Any, label: str, exc_type: type[ValueError]) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise exc_type(f"{label} must be a full lowercase 40-character revision")
    return value


def _artifact(value: Any, label: str, exc_type: type[ValueError]) -> ArtifactRef:
    if isinstance(value, ArtifactRef):
        return value
    try:
        return ArtifactRef.from_dict(value)
    except (AttributeError, KeyError, SearchValidationError, TypeError, ValueError) as exc:
        raise exc_type(f"{label} is not a valid artifact reference") from exc


def _sequence(
    value: Any,
    label: str,
    exc_type: type[ValueError],
    *,
    item_type: type[Any] | tuple[type[Any], ...] | None = None,
    allow_empty: bool = True,
) -> tuple[Any, ...]:
    if not isinstance(value, (tuple, list)):
        raise exc_type(f"{label} must be an explicit tuple or list")
    result = tuple(value)
    if not allow_empty and not result:
        raise exc_type(f"{label} must not be empty")
    if item_type is not None and any(not isinstance(item, item_type) for item in result):
        raise exc_type(f"{label} contains an invalid item")
    return result


def _nonnegative_int(value: Any, label: str, exc_type: type[ValueError]) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise exc_type(f"{label} must be a nonnegative integer")
    return value


def _positive_int(value: Any, label: str, exc_type: type[ValueError]) -> int:
    result = _nonnegative_int(value, label, exc_type)
    if result < 1:
        raise exc_type(f"{label} must be positive")
    return result


def _platform(recipient_id: str, exc_type: type[ValueError]) -> str:
    match = _PLATFORM_RE.match(recipient_id)
    if match is None or match.group(1) not in SUPPORTED_PLATFORMS:
        raise exc_type(
            f"recipient {recipient_id!r} must use a supported platform prefix"
        )
    return match.group(1)


def _plain(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _score(value: Any, label: str, exc_type: type[ValueError]) -> ScoreVector:
    if isinstance(value, ScoreVector):
        return value
    try:
        return ScoreVector.from_dict(value)
    except (AttributeError, KeyError, SearchValidationError, TypeError, ValueError) as exc:
        raise exc_type(f"{label} is not a valid ScoreVector") from exc


def _verify_archive(
    archive: ContentAddressedArchive,
    reference: ArtifactRef,
    label: str,
    exc_type: type[ValueError],
    *,
    media_type: str | None = None,
    path_prefixes: tuple[str, ...] = (),
) -> bytes:
    if not isinstance(archive, ContentAddressedArchive):
        raise exc_type("matrix requires a content-addressed archive")
    if media_type is not None and reference.media_type != media_type:
        raise exc_type(f"{label} media type is not canonical")
    if path_prefixes and not any(
        reference.path.startswith(prefix) for prefix in path_prefixes
    ):
        raise exc_type(f"{label} path is outside its allowed archive category")
    try:
        data = archive.verify(reference)
    except (ArchiveError, OSError, SearchValidationError, TypeError, ValueError) as exc:
        raise exc_type(f"{label} artifact is missing or corrupt") from exc
    if (
        hash_bytes(data) != reference.content_hash
        or len(data) != reference.byte_size
    ):
        raise exc_type(f"{label} artifact metadata is not self-consistent")
    return data


def _archive_exact(
    archive: ContentAddressedArchive,
    payload: Any,
    *,
    expected_identity: str | None,
    category: str,
    label: str,
    exc_type: type[ValueError],
) -> ArtifactRef:
    data = canonical_bytes(payload)
    try:
        reference = archive.put_bytes(
            data,
            category=category,
            suffix=".json",
            media_type="application/json",
        )
    except (ArchiveError, OSError, TypeError, ValueError) as exc:
        raise exc_type(f"{label} could not be archived") from exc
    if expected_identity is not None and reference.content_hash != expected_identity:
        raise exc_type(f"{label} identity differs from its canonical payload")
    verified = _verify_archive(
        archive,
        reference,
        label,
        exc_type,
        media_type="application/json",
        path_prefixes=(f"artifacts/{category}/",),
    )
    if verified != data:
        raise exc_type(f"{label} bytes differ after archival")
    return reference


def _validate_gate(
    gate: Any,
    archive: ContentAddressedArchive,
    exc_type: type[ValueError],
) -> Any:
    """Call the canonical gate validator exactly once and verify its artifact."""

    if not isinstance(gate, IntegrationGateReceipt):
        raise exc_type("matrix requires a typed integration gate receipt")
    try:
        manifest = validate_integration_gate(gate, archive=archive)
    except (
        IntegrationGateError,
        ArchiveError,
        OSError,
        SearchValidationError,
        TypeError,
        ValueError,
    ) as exc:
        raise exc_type("integration gate evidence is absent or invalid") from exc
    if manifest is None:
        raise exc_type("integration gate validator returned no manifest")
    if gate.gate_kind != "multi_record" or gate.record_count < 2:
        raise exc_type("m2c matrix requires a bounded multi-record integration gate")
    _hash(gate.gate_id, "integration gate id", exc_type)
    if gate.receipt_artifact.content_hash != gate.gate_id:
        raise exc_type("integration gate artifact identity differs from gate_id")
    _verify_archive(
        archive,
        gate.receipt_artifact,
        "integration gate receipt",
        exc_type,
        media_type="application/json",
        path_prefixes=("artifacts/receipts/",),
    )
    return manifest


def _revision(value: Any, label: str, exc_type: type[ValueError]) -> M2CRevisionIdentity:
    if not isinstance(value, M2CRevisionIdentity):
        raise exc_type(f"{label} must be a typed M2CRevisionIdentity")
    _commit(value.revision_id, label + " revision_id", exc_type)
    for name in (
        "tree_identity",
        "provider_identity",
        "executable_identity",
        "config_identity",
    ):
        _hash(getattr(value, name), label + " " + name, exc_type)
    return value


def _report_payload(report: "M2CBenchmarkReport") -> dict[str, Any]:
    return {
        "protocol": M2C_REPORT_PROTOCOL,
        "benchmark_id": report.benchmark_id,
        "benchmark_artifact_id": report.benchmark_artifact_id,
        "revision_id": report.revision_id,
        "tree_identity": report.tree_identity,
        "provider_identity": report.provider_identity,
        "tool_identity": report.tool_identity,
        "archive_identity": report.archive_identity,
        "integration_gate_id": report.integration_gate_id,
        "integration_gate_artifact_id": report.integration_gate_artifact_id,
        "subset_identity": report.subset_identity,
        "queue_evidence_identity": report.queue_evidence_identity,
        "compiler_identity": report.compiler_identity,
        "evaluator_identity": report.evaluator_identity,
        "config_identity": report.config_identity,
        "scorer_taxonomy_identity": report.scorer_taxonomy_identity,
        "observations": [item.to_dict() for item in report.observations],
        "observation_artifact_ids": list(report.observation_artifact_ids),
        "total_cost_units": report.total_cost_units,
        "unique_candidate_count": report.unique_candidate_count,
        "better_case_count": report.better_case_count,
        "complete": report.complete,
        "refusal_code": report.refusal_code,
    }


@dataclass(frozen=True)
class M2CBenchmarkCase:
    case_id: str
    recipient_id: str
    assembly_artifact: ArtifactRef
    context_artifacts: tuple[ArtifactRef, ...]
    target_identity: str
    compiler_identity: str
    evaluator_identity: str
    config_identity: str
    switches: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        cls = M2CBenchmarkError
        object.__setattr__(self, "case_id", _id(self.case_id, "case_id", cls))
        recipient = _id(self.recipient_id, "recipient_id", cls)
        _platform(recipient, cls)
        object.__setattr__(self, "recipient_id", recipient)
        object.__setattr__(
            self,
            "assembly_artifact",
            _artifact(self.assembly_artifact, "assembly_artifact", cls),
        )
        contexts = _sequence(
            self.context_artifacts,
            "context_artifacts",
            cls,
            item_type=ArtifactRef,
        )
        if len({item.content_hash for item in contexts}) != len(contexts):
            raise cls("context_artifacts must be unique")
        object.__setattr__(self, "context_artifacts", contexts)
        for name in (
            "target_identity",
            "compiler_identity",
            "evaluator_identity",
            "config_identity",
        ):
            object.__setattr__(
                self,
                name,
                _hash(getattr(self, name), name, cls),
            )
        switches = _sequence(self.switches, "switches", cls, item_type=str)
        if any(not item for item in switches):
            raise cls("switches must contain nonempty strings")
        object.__setattr__(self, "switches", switches)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "recipient_id": self.recipient_id,
            "assembly_artifact": self.assembly_artifact.to_dict(),
            "context_artifacts": [item.to_dict() for item in self.context_artifacts],
            "target_identity": self.target_identity,
            "compiler_identity": self.compiler_identity,
            "evaluator_identity": self.evaluator_identity,
            "config_identity": self.config_identity,
            "switches": list(self.switches),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M2CBenchmarkCase":
        if not isinstance(value, Mapping):
            raise M2CBenchmarkError("benchmark case must be an object")
        allowed = {
            "case_id",
            "recipient_id",
            "assembly_artifact",
            "context_artifacts",
            "target_identity",
            "compiler_identity",
            "evaluator_identity",
            "config_identity",
            "switches",
        }
        if set(value) - allowed:
            raise M2CBenchmarkError("benchmark case has unknown fields")
        required = allowed - {"switches"}
        if not required.issubset(value):
            raise M2CBenchmarkError("benchmark case is missing fields")
        return cls(
            case_id=value["case_id"],
            recipient_id=value["recipient_id"],
            assembly_artifact=_artifact(value["assembly_artifact"], "assembly_artifact", M2CBenchmarkError),
            context_artifacts=tuple(
                _artifact(item, "context_artifact", M2CBenchmarkError)
                for item in _sequence(value["context_artifacts"], "context_artifacts", M2CBenchmarkError)
            ),
            target_identity=value["target_identity"],
            compiler_identity=value["compiler_identity"],
            evaluator_identity=value["evaluator_identity"],
            config_identity=value["config_identity"],
            switches=value.get("switches", ()),
        )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": M2C_BENCHMARK_PROTOCOL + ":case",
            **self.to_dict(),
        }


@dataclass(frozen=True)
class M2CFixedBenchmark:
    benchmark_id: str
    current_revision_id: str
    cases: tuple[M2CBenchmarkCase, ...]
    scorer_taxonomy_identity: str
    evaluator_identity: str
    budget: int
    benchmark_artifact: ArtifactRef | None = None

    def __post_init__(self) -> None:
        cls = M2CBenchmarkError
        object.__setattr__(self, "benchmark_id", _hash(self.benchmark_id, "benchmark_id", cls))
        object.__setattr__(
            self,
            "current_revision_id",
            _commit(self.current_revision_id, "current_revision_id", cls),
        )
        cases = _sequence(
            self.cases,
            "cases",
            cls,
            item_type=M2CBenchmarkCase,
            allow_empty=False,
        )
        if len({item.case_id for item in cases}) != len(cases):
            raise cls("benchmark case IDs must be unique")
        object.__setattr__(self, "cases", cases)
        object.__setattr__(
            self,
            "scorer_taxonomy_identity",
            _hash(self.scorer_taxonomy_identity, "scorer_taxonomy_identity", cls),
        )
        object.__setattr__(
            self,
            "evaluator_identity",
            _hash(self.evaluator_identity, "evaluator_identity", cls),
        )
        if any(item.evaluator_identity != self.evaluator_identity for item in cases):
            raise cls("benchmark evaluator identity differs from a case")
        object.__setattr__(self, "budget", _positive_int(self.budget, "budget", cls))
        if self.benchmark_artifact is not None:
            object.__setattr__(
                self,
                "benchmark_artifact",
                _artifact(self.benchmark_artifact, "benchmark_artifact", cls),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": M2C_BENCHMARK_PROTOCOL,
            "benchmark_id": self.benchmark_id,
            "current_revision_id": self.current_revision_id,
            "cases": [item.to_dict() for item in self.cases],
            "scorer_taxonomy_identity": self.scorer_taxonomy_identity,
            "evaluator_identity": self.evaluator_identity,
            "budget": self.budget,
            "benchmark_artifact": (
                None
                if self.benchmark_artifact is None
                else self.benchmark_artifact.to_dict()
            ),
        }

    def identity_payload(self) -> dict[str, Any]:
        return self.to_dict()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M2CFixedBenchmark":
        if not isinstance(value, Mapping):
            raise M2CBenchmarkError("fixed benchmark must be an object")
        allowed = {
            "protocol",
            "benchmark_id",
            "current_revision_id",
            "cases",
            "scorer_taxonomy_identity",
            "evaluator_identity",
            "budget",
            "benchmark_artifact",
        }
        if set(value) - allowed or value.get("protocol") != M2C_BENCHMARK_PROTOCOL:
            raise M2CBenchmarkError("fixed benchmark protocol or fields are invalid")
        required = allowed - {"protocol", "benchmark_artifact"}
        if not required.issubset(value):
            raise M2CBenchmarkError("fixed benchmark is missing fields")
        raw_cases = _sequence(value["cases"], "cases", M2CBenchmarkError, allow_empty=False)
        artifact = value.get("benchmark_artifact")
        return cls(
            benchmark_id=value["benchmark_id"],
            current_revision_id=value["current_revision_id"],
            cases=tuple(M2CBenchmarkCase.from_dict(item) for item in raw_cases),
            scorer_taxonomy_identity=value["scorer_taxonomy_identity"],
            evaluator_identity=value["evaluator_identity"],
            budget=value["budget"],
            benchmark_artifact=(
                None
                if artifact is None
                else _artifact(artifact, "benchmark_artifact", M2CBenchmarkError)
            ),
        )


@dataclass(frozen=True)
class M2CEvaluation:
    case_id: str
    revision_id: str
    invocation_id: str
    source_artifact: ArtifactRef
    score: ScoreVector
    tool_identity: str
    evaluator_identity: str
    scorer_taxonomy_identity: str
    cost_units: int

    def __post_init__(self) -> None:
        cls = M2CBenchmarkError
        object.__setattr__(self, "case_id", _id(self.case_id, "evaluation case_id", cls))
        object.__setattr__(
            self,
            "revision_id",
            _commit(self.revision_id, "evaluation revision_id", cls),
        )
        object.__setattr__(
            self,
            "invocation_id",
            _hash(self.invocation_id, "evaluation invocation_id", cls),
        )
        object.__setattr__(
            self,
            "source_artifact",
            _artifact(self.source_artifact, "evaluation source_artifact", cls),
        )
        object.__setattr__(self, "score", _score(self.score, "evaluation score", cls))
        for name in (
            "tool_identity",
            "evaluator_identity",
            "scorer_taxonomy_identity",
        ):
            object.__setattr__(self, name, _hash(getattr(self, name), name, cls))
        object.__setattr__(
            self,
            "cost_units",
            _positive_int(self.cost_units, "evaluation cost_units", cls),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": M2C_EVALUATION_PROTOCOL,
            "case_id": self.case_id,
            "revision_id": self.revision_id,
            "invocation_id": self.invocation_id,
            "source_artifact": self.source_artifact.to_dict(),
            "score": self.score.to_dict(),
            "tool_identity": self.tool_identity,
            "evaluator_identity": self.evaluator_identity,
            "scorer_taxonomy_identity": self.scorer_taxonomy_identity,
            "cost_units": self.cost_units,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M2CEvaluation":
        if not isinstance(value, Mapping):
            raise M2CBenchmarkError("evaluation must be an object")
        allowed = {
            "protocol",
            "case_id",
            "revision_id",
            "invocation_id",
            "source_artifact",
            "score",
            "tool_identity",
            "evaluator_identity",
            "scorer_taxonomy_identity",
            "cost_units",
        }
        if set(value) != allowed or value.get("protocol") != M2C_EVALUATION_PROTOCOL:
            raise M2CBenchmarkError("evaluation fields or protocol are invalid")
        return cls(
            case_id=value["case_id"],
            revision_id=value["revision_id"],
            invocation_id=value["invocation_id"],
            source_artifact=_artifact(value["source_artifact"], "source_artifact", M2CBenchmarkError),
            score=_score(value["score"], "score", M2CBenchmarkError),
            tool_identity=value["tool_identity"],
            evaluator_identity=value["evaluator_identity"],
            scorer_taxonomy_identity=value["scorer_taxonomy_identity"],
            cost_units=value["cost_units"],
        )


@dataclass(frozen=True)
class M2CBenchmarkReport:
    report_id: str
    benchmark_id: str
    benchmark_artifact_id: str
    revision_id: str
    tree_identity: str
    provider_identity: str
    tool_identity: str
    archive_identity: str
    integration_gate_id: str
    integration_gate_artifact_id: str
    subset_identity: str
    queue_evidence_identity: str
    compiler_identity: str
    evaluator_identity: str
    config_identity: str
    scorer_taxonomy_identity: str
    observations: tuple[M2CEvaluation, ...]
    observation_artifact_ids: tuple[str, ...]
    total_cost_units: int
    unique_candidate_count: int
    better_case_count: int
    complete: bool
    refusal_code: str | None

    def __post_init__(self) -> None:
        cls = M2CBenchmarkError
        object.__setattr__(self, "report_id", _hash(self.report_id, "report_id", cls))
        for name in (
            "benchmark_id",
            "benchmark_artifact_id",
            "tree_identity",
            "provider_identity",
            "tool_identity",
            "archive_identity",
            "integration_gate_id",
            "integration_gate_artifact_id",
            "subset_identity",
            "queue_evidence_identity",
            "compiler_identity",
            "evaluator_identity",
            "config_identity",
            "scorer_taxonomy_identity",
        ):
            object.__setattr__(self, name, _hash(getattr(self, name), name, cls))
        object.__setattr__(
            self,
            "revision_id",
            _commit(self.revision_id, "report revision_id", cls),
        )
        observations = _sequence(
            self.observations,
            "observations",
            cls,
            item_type=M2CEvaluation,
        )
        object.__setattr__(self, "observations", observations)
        artifacts = _sequence(
            self.observation_artifact_ids,
            "observation_artifact_ids",
            cls,
            item_type=str,
        )
        if len(artifacts) != len(observations):
            raise cls("observation artifact count differs from observations")
        for item in artifacts:
            _hash(item, "observation_artifact_id", cls)
        object.__setattr__(self, "observation_artifact_ids", artifacts)
        object.__setattr__(
            self,
            "total_cost_units",
            _nonnegative_int(self.total_cost_units, "total_cost_units", cls),
        )
        object.__setattr__(
            self,
            "unique_candidate_count",
            _nonnegative_int(self.unique_candidate_count, "unique_candidate_count", cls),
        )
        object.__setattr__(
            self,
            "better_case_count",
            _nonnegative_int(self.better_case_count, "better_case_count", cls),
        )
        if not isinstance(self.complete, bool):
            raise cls("report complete must be boolean")
        if self.refusal_code is not None and (
            not isinstance(self.refusal_code, str) or not self.refusal_code
        ):
            raise cls("report refusal_code must be null or nonempty")
        expected = hash_canonical(_report_payload(self))
        if self.report_id != expected:
            raise cls("report_id differs from its complete payload")

    def identity_payload(self) -> dict[str, Any]:
        return _report_payload(self)

    def to_dict(self) -> dict[str, Any]:
        return {"report_id": self.report_id, **self.identity_payload()}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M2CBenchmarkReport":
        if not isinstance(value, Mapping):
            raise M2CBenchmarkError("benchmark report must be an object")
        fields = {
            "report_id",
            "protocol",
            "benchmark_id",
            "benchmark_artifact_id",
            "revision_id",
            "tree_identity",
            "provider_identity",
            "tool_identity",
            "archive_identity",
            "integration_gate_id",
            "integration_gate_artifact_id",
            "subset_identity",
            "queue_evidence_identity",
            "compiler_identity",
            "evaluator_identity",
            "config_identity",
            "scorer_taxonomy_identity",
            "observations",
            "observation_artifact_ids",
            "total_cost_units",
            "unique_candidate_count",
            "better_case_count",
            "complete",
            "refusal_code",
        }
        if set(value) != fields or value.get("protocol") != M2C_REPORT_PROTOCOL:
            raise M2CBenchmarkError("benchmark report fields or protocol are invalid")
        observations = _sequence(value["observations"], "observations", M2CBenchmarkError)
        artifacts = _sequence(
            value["observation_artifact_ids"],
            "observation_artifact_ids",
            M2CBenchmarkError,
        )
        return cls(
            report_id=value["report_id"],
            benchmark_id=value["benchmark_id"],
            benchmark_artifact_id=value["benchmark_artifact_id"],
            revision_id=value["revision_id"],
            tree_identity=value["tree_identity"],
            provider_identity=value["provider_identity"],
            tool_identity=value["tool_identity"],
            archive_identity=value["archive_identity"],
            integration_gate_id=value["integration_gate_id"],
            integration_gate_artifact_id=value["integration_gate_artifact_id"],
            subset_identity=value["subset_identity"],
            queue_evidence_identity=value["queue_evidence_identity"],
            compiler_identity=value["compiler_identity"],
            evaluator_identity=value["evaluator_identity"],
            config_identity=value["config_identity"],
            scorer_taxonomy_identity=value["scorer_taxonomy_identity"],
            observations=tuple(M2CEvaluation.from_dict(item) for item in observations),
            observation_artifact_ids=tuple(artifacts),
            total_cost_units=value["total_cost_units"],
            unique_candidate_count=value["unique_candidate_count"],
            better_case_count=value["better_case_count"],
            complete=value["complete"],
            refusal_code=value["refusal_code"],
        )


def make_benchmark_report(**values: Any) -> M2CBenchmarkReport:
    payload = dict(values)
    payload.pop("report_id", None)
    probe = {
        "protocol": M2C_REPORT_PROTOCOL,
        **{
            key: (
                [item.to_dict() for item in value]
                if key == "observations"
                else value
            )
            for key, value in payload.items()
        },
    }
    payload["report_id"] = hash_canonical(probe)
    return M2CBenchmarkReport(**payload)


@dataclass(frozen=True)
class M2CRevisionQualification:
    qualification_id: str
    benchmark_id: str
    baseline_report_id: str
    alternate_report_id: str
    alternate_revision_id: str
    unique_candidate_count: int
    better_case_count: int
    qualified: bool
    reason_code: str

    def __post_init__(self) -> None:
        cls = M2CBenchmarkError
        object.__setattr__(
            self,
            "qualification_id",
            _hash(self.qualification_id, "qualification_id", cls),
        )
        for name in (
            "benchmark_id",
            "baseline_report_id",
            "alternate_report_id",
        ):
            object.__setattr__(self, name, _hash(getattr(self, name), name, cls))
        object.__setattr__(
            self,
            "alternate_revision_id",
            _commit(self.alternate_revision_id, "alternate_revision_id", cls),
        )
        object.__setattr__(
            self,
            "unique_candidate_count",
            _nonnegative_int(self.unique_candidate_count, "unique_candidate_count", cls),
        )
        object.__setattr__(
            self,
            "better_case_count",
            _nonnegative_int(self.better_case_count, "better_case_count", cls),
        )
        if not isinstance(self.qualified, bool):
            raise cls("qualification qualified must be boolean")
        allowed = {
            "baseline_incomplete",
            "alternate_incomplete",
            "identity_mismatch",
            "qualified_unique",
            "qualified_better",
            "no_unique_or_better_candidate",
        }
        if self.reason_code not in allowed:
            raise cls("unknown qualification reason")
        if self.qualified != (
            self.reason_code in {"qualified_unique", "qualified_better"}
        ):
            raise cls("qualification flag differs from reason")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": M2C_QUALIFICATION_PROTOCOL,
            "benchmark_id": self.benchmark_id,
            "baseline_report_id": self.baseline_report_id,
            "alternate_report_id": self.alternate_report_id,
            "alternate_revision_id": self.alternate_revision_id,
            "unique_candidate_count": self.unique_candidate_count,
            "better_case_count": self.better_case_count,
            "qualified": self.qualified,
            "reason_code": self.reason_code,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"qualification_id": self.qualification_id, **self.identity_payload()}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M2CRevisionQualification":
        if not isinstance(value, Mapping):
            raise M2CBenchmarkError("qualification must be an object")
        fields = {
            "qualification_id",
            "protocol",
            "benchmark_id",
            "baseline_report_id",
            "alternate_report_id",
            "alternate_revision_id",
            "unique_candidate_count",
            "better_case_count",
            "qualified",
            "reason_code",
        }
        if set(value) != fields or value.get("protocol") != M2C_QUALIFICATION_PROTOCOL:
            raise M2CBenchmarkError("qualification fields or protocol are invalid")
        return cls(
            qualification_id=value["qualification_id"],
            benchmark_id=value["benchmark_id"],
            baseline_report_id=value["baseline_report_id"],
            alternate_report_id=value["alternate_report_id"],
            alternate_revision_id=value["alternate_revision_id"],
            unique_candidate_count=value["unique_candidate_count"],
            better_case_count=value["better_case_count"],
            qualified=value["qualified"],
            reason_code=value["reason_code"],
        )


def qualify_revision(
    baseline: M2CBenchmarkReport,
    alternate: M2CBenchmarkReport,
) -> M2CRevisionQualification:
    """Compare two complete reports from the same fixed benchmark."""

    cls = M2CBenchmarkError
    if not isinstance(baseline, M2CBenchmarkReport) or not isinstance(
        alternate, M2CBenchmarkReport
    ):
        raise cls("qualification requires typed benchmark reports")
    if not baseline.complete:
        return _make_qualification(
            baseline,
            alternate,
            unique=0,
            better=0,
            qualified=False,
            reason="baseline_incomplete",
        )
    if not alternate.complete:
        return _make_qualification(
            baseline,
            alternate,
            unique=0,
            better=0,
            qualified=False,
            reason="alternate_incomplete",
        )
    comparable = (
        baseline.benchmark_id == alternate.benchmark_id
        and baseline.benchmark_artifact_id == alternate.benchmark_artifact_id
        and baseline.archive_identity == alternate.archive_identity
        and baseline.integration_gate_id == alternate.integration_gate_id
        and baseline.integration_gate_artifact_id == alternate.integration_gate_artifact_id
        and baseline.subset_identity == alternate.subset_identity
        and baseline.queue_evidence_identity == alternate.queue_evidence_identity
        and baseline.tree_identity == alternate.tree_identity
        and baseline.provider_identity == alternate.provider_identity
        and baseline.tool_identity == alternate.tool_identity
        and baseline.compiler_identity == alternate.compiler_identity
        and baseline.evaluator_identity == alternate.evaluator_identity
        and baseline.config_identity == alternate.config_identity
        and baseline.scorer_taxonomy_identity == alternate.scorer_taxonomy_identity
        and baseline.revision_id != alternate.revision_id
    )
    baseline_cases = {item.case_id: item for item in baseline.observations}
    alternate_cases = {item.case_id: item for item in alternate.observations}
    if set(baseline_cases) != set(alternate_cases) or not comparable:
        return _make_qualification(
            baseline,
            alternate,
            unique=0,
            better=0,
            qualified=False,
            reason="identity_mismatch",
        )
    unique = 0
    better = 0
    for case_id in sorted(baseline_cases):
        first = baseline_cases[case_id]
        second = alternate_cases[case_id]
        if (
            first.tool_identity != alternate.tool_identity
            or first.evaluator_identity != alternate.evaluator_identity
            or first.scorer_taxonomy_identity != alternate.scorer_taxonomy_identity
            or first.score.compiler_identity != baseline.compiler_identity
            or second.score.compiler_identity != baseline.compiler_identity
        ):
            return _make_qualification(
                baseline,
                alternate,
                unique=0,
                better=0,
                qualified=False,
                reason="identity_mismatch",
            )
        if second.source_artifact.content_hash != first.source_artifact.content_hash:
            unique += 1
        if (
            first.score.compile_status == "success"
            and second.score.compile_status == "success"
            and first.score.total is not None
            and second.score.total is not None
            and second.score.total < first.score.total
        ):
            better += 1
    reason = (
        "qualified_unique"
        if unique
        else "qualified_better"
        if better
        else "no_unique_or_better_candidate"
    )
    return _make_qualification(
        baseline,
        alternate,
        unique=unique,
        better=better,
        qualified=bool(unique or better),
        reason=reason,
    )


def _make_qualification(
    baseline: M2CBenchmarkReport,
    alternate: M2CBenchmarkReport,
    *,
    unique: int,
    better: int,
    qualified: bool,
    reason: str,
) -> M2CRevisionQualification:
    payload = {
        "protocol": M2C_QUALIFICATION_PROTOCOL,
        "benchmark_id": baseline.benchmark_id,
        "baseline_report_id": baseline.report_id,
        "alternate_report_id": alternate.report_id,
        "alternate_revision_id": alternate.revision_id,
        "unique_candidate_count": unique,
        "better_case_count": better,
        "qualified": qualified,
        "reason_code": reason,
    }
    return M2CRevisionQualification(
        qualification_id=hash_canonical(payload),
        benchmark_id=baseline.benchmark_id,
        baseline_report_id=baseline.report_id,
        alternate_report_id=alternate.report_id,
        alternate_revision_id=alternate.revision_id,
        unique_candidate_count=unique,
        better_case_count=better,
        qualified=qualified,
        reason_code=reason,
    )


def _spec_payload(spec: "M2CMatrixSpec") -> dict[str, Any]:
    return {
        "protocol": M2C_MATRIX_PROTOCOL,
        "benchmark_id": spec.benchmark_id,
        "benchmark_artifact_id": spec.benchmark_artifact_id,
        "gate_id": spec.gate_id,
        "integration_gate_artifact_id": spec.integration_gate_artifact_id,
        "subset_identity": spec.subset_identity,
        "queue_evidence_identity": spec.queue_evidence_identity,
        "provider_identity": spec.provider_identity,
        "tool_identity": spec.tool_identity,
        "revision_tool_identities": [list(item) for item in spec.revision_tool_identities],
        "archive_identity": spec.archive_identity,
        "current_revision_id": spec.current_revision_id,
        "qualified_alternate_revision_ids": list(spec.qualified_alternate_revision_ids),
        "cases": [item.to_dict() for item in spec.cases],
        "switch_matrix": [list(item) for item in spec.switch_matrix],
        "context_kinds": list(spec.context_kinds),
        "compiler_identity": spec.compiler_identity,
        "evaluator_identity": spec.evaluator_identity,
        "config_identity": spec.config_identity,
        "scorer_taxonomy_identity": spec.scorer_taxonomy_identity,
        "budget": spec.budget,
    }


@dataclass(frozen=True)
class M2CMatrixSpec:
    matrix_id: str
    matrix_spec_artifact_id: str
    benchmark_id: str
    benchmark_artifact_id: str
    gate_id: str
    integration_gate_artifact_id: str
    subset_identity: str
    queue_evidence_identity: str
    provider_identity: str
    tool_identity: str
    revision_tool_identities: tuple[tuple[str, str], ...]
    archive_identity: str
    current_revision_id: str
    qualified_alternate_revision_ids: tuple[str, ...]
    cases: tuple[M2CBenchmarkCase, ...]
    switch_matrix: tuple[tuple[str, ...], ...]
    context_kinds: tuple[str, ...]
    compiler_identity: str
    evaluator_identity: str
    config_identity: str
    scorer_taxonomy_identity: str
    budget: int

    def __post_init__(self) -> None:
        cls = M2CMatrixError
        object.__setattr__(self, "matrix_id", _hash(self.matrix_id, "matrix_id", cls))
        object.__setattr__(
            self,
            "matrix_spec_artifact_id",
            _hash(self.matrix_spec_artifact_id, "matrix_spec_artifact_id", cls),
        )
        for name in (
            "benchmark_id",
            "benchmark_artifact_id",
            "gate_id",
            "integration_gate_artifact_id",
            "subset_identity",
            "queue_evidence_identity",
            "provider_identity",
            "tool_identity",
            "archive_identity",
            "compiler_identity",
            "evaluator_identity",
            "config_identity",
            "scorer_taxonomy_identity",
        ):
            object.__setattr__(self, name, _hash(getattr(self, name), name, cls))
        object.__setattr__(
            self,
            "current_revision_id",
            _commit(self.current_revision_id, "current_revision_id", cls),
        )
        pairs = _sequence(
            self.revision_tool_identities,
            "revision_tool_identities",
            cls,
            allow_empty=False,
        )
        normalized_pairs: list[tuple[str, str]] = []
        for item in pairs:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise cls("revision_tool_identities must contain revision/tool pairs")
            normalized_pairs.append(
                (
                    _commit(item[0], "revision_tool_identities revision", cls),
                    _hash(item[1], "revision_tool_identity", cls),
                )
            )
        if len({item[0] for item in normalized_pairs}) != len(normalized_pairs):
            raise cls("revision_tool_identities must be unique")
        normalized_pairs.sort()
        if dict(normalized_pairs).get(self.current_revision_id) != self.tool_identity:
            raise cls("tool_identity must bind the current revision")
        object.__setattr__(self, "revision_tool_identities", tuple(normalized_pairs))
        alternates = _sequence(
            self.qualified_alternate_revision_ids,
            "qualified_alternate_revision_ids",
            cls,
        )
        for item in alternates:
            _commit(item, "qualified alternate revision", cls)
        if self.current_revision_id in alternates:
            raise cls("current revision cannot be an alternate")
        if len(set(alternates)) != len(alternates):
            raise cls("qualified alternate revisions must be unique")
        object.__setattr__(self, "qualified_alternate_revision_ids", tuple(sorted(alternates)))
        cases = _sequence(
            self.cases,
            "matrix cases",
            cls,
            item_type=M2CBenchmarkCase,
            allow_empty=False,
        )
        if len({item.case_id for item in cases}) != len(cases):
            raise cls("matrix cases must be unique")
        object.__setattr__(self, "cases", tuple(sorted(cases, key=lambda item: item.case_id)))
        switches = _sequence(self.switch_matrix, "switch_matrix", cls, allow_empty=False)
        switch_values: list[tuple[str, ...]] = []
        for item in switches:
            values = _sequence(item, "switch tuple", cls, item_type=str)
            if any(not value for value in values):
                raise cls("switch values must be nonempty")
            switch_values.append(values)
        if len(set(switch_values)) != len(switch_values):
            raise cls("switch_matrix must be unique")
        object.__setattr__(self, "switch_matrix", tuple(sorted(switch_values)))
        contexts = _sequence(
            self.context_kinds,
            "context_kinds",
            cls,
            item_type=str,
            allow_empty=False,
        )
        if any(not item for item in contexts) or len(set(contexts)) != len(contexts):
            raise cls("context_kinds must be unique nonempty strings")
        object.__setattr__(self, "context_kinds", tuple(sorted(contexts)))
        object.__setattr__(self, "budget", _positive_int(self.budget, "budget", cls))
        if self.matrix_id != hash_canonical(_spec_payload(self)):
            raise cls("matrix_id differs from its complete specification payload")

    def identity_payload(self) -> dict[str, Any]:
        return _spec_payload(self)

    def artifact_payload(self) -> dict[str, Any]:
        return {
            "protocol": M2C_SPEC_ARTIFACT_PROTOCOL,
            "matrix_id": self.matrix_id,
            "spec": self.identity_payload(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "matrix_id": self.matrix_id,
            "matrix_spec_artifact_id": self.matrix_spec_artifact_id,
            **self.identity_payload(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M2CMatrixSpec":
        if not isinstance(value, Mapping):
            raise M2CMatrixError("matrix spec must be an object")
        fields = set(_spec_payload_fields()) | {"matrix_id", "matrix_spec_artifact_id"}
        if set(value) != fields or value.get("protocol") != M2C_MATRIX_PROTOCOL:
            raise M2CMatrixError("matrix spec fields or protocol are invalid")
        raw_pairs = _sequence(value["revision_tool_identities"], "revision_tool_identities", M2CMatrixError)
        pair_values = []
        for item in raw_pairs:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise M2CMatrixError("revision_tool_identities must contain pairs")
            pair_values.append(tuple(item))
        raw_cases = _sequence(value["cases"], "cases", M2CMatrixError)
        raw_switches = _sequence(value["switch_matrix"], "switch_matrix", M2CMatrixError)
        switch_values = []
        for item in raw_switches:
            if not isinstance(item, (tuple, list)):
                raise M2CMatrixError("switch_matrix must contain tuples or lists")
            switch_values.append(tuple(item))
        return cls(
            matrix_id=value["matrix_id"],
            matrix_spec_artifact_id=value["matrix_spec_artifact_id"],
            benchmark_id=value["benchmark_id"],
            benchmark_artifact_id=value["benchmark_artifact_id"],
            gate_id=value["gate_id"],
            integration_gate_artifact_id=value["integration_gate_artifact_id"],
            subset_identity=value["subset_identity"],
            queue_evidence_identity=value["queue_evidence_identity"],
            provider_identity=value["provider_identity"],
            tool_identity=value["tool_identity"],
            revision_tool_identities=tuple(pair_values),
            archive_identity=value["archive_identity"],
            current_revision_id=value["current_revision_id"],
            qualified_alternate_revision_ids=tuple(
                _sequence(
                    value["qualified_alternate_revision_ids"],
                    "qualified_alternate_revision_ids",
                    M2CMatrixError,
                )
            ),
            cases=tuple(M2CBenchmarkCase.from_dict(item) for item in raw_cases),
            switch_matrix=tuple(switch_values),
            context_kinds=tuple(
                _sequence(value["context_kinds"], "context_kinds", M2CMatrixError)
            ),
            compiler_identity=value["compiler_identity"],
            evaluator_identity=value["evaluator_identity"],
            config_identity=value["config_identity"],
            scorer_taxonomy_identity=value["scorer_taxonomy_identity"],
            budget=value["budget"],
        )


def _spec_payload_fields() -> tuple[str, ...]:
    return (
        "protocol",
        "benchmark_id",
        "benchmark_artifact_id",
        "gate_id",
        "integration_gate_artifact_id",
        "subset_identity",
        "queue_evidence_identity",
        "provider_identity",
        "tool_identity",
        "revision_tool_identities",
        "archive_identity",
        "current_revision_id",
        "qualified_alternate_revision_ids",
        "cases",
        "switch_matrix",
        "context_kinds",
        "compiler_identity",
        "evaluator_identity",
        "config_identity",
        "scorer_taxonomy_identity",
        "budget",
    )


def make_matrix_spec(**values: Any) -> M2CMatrixSpec:
    payload = dict(values)
    payload.pop("matrix_id", None)
    payload.pop("matrix_spec_artifact_id", None)
    # The frozen spec normalizes these collections in __post_init__. Apply the
    # same normalization before hashing so caller order cannot alter identity.
    if "cases" in payload:
        payload["cases"] = tuple(
            sorted(payload["cases"], key=lambda item: item.case_id)
        )
    if "revision_tool_identities" in payload:
        payload["revision_tool_identities"] = tuple(
            sorted(tuple(item) for item in payload["revision_tool_identities"])
        )
    if "qualified_alternate_revision_ids" in payload:
        payload["qualified_alternate_revision_ids"] = tuple(
            sorted(payload["qualified_alternate_revision_ids"])
        )
    if "switch_matrix" in payload:
        payload["switch_matrix"] = tuple(
            sorted(tuple(item) for item in payload["switch_matrix"])
        )
    if "context_kinds" in payload:
        payload["context_kinds"] = tuple(sorted(payload["context_kinds"]))
    probe = {
        "protocol": M2C_MATRIX_PROTOCOL,
        **{
            key: (
                [item.to_dict() for item in value]
                if key == "cases"
                else [list(item) for item in value]
                if key in {"revision_tool_identities", "switch_matrix"}
                else list(value)
                if key in {"qualified_alternate_revision_ids", "context_kinds"}
                else value
            )
            for key, value in payload.items()
        },
    }
    matrix_id = hash_canonical(probe)
    artifact_payload = {
        "protocol": M2C_SPEC_ARTIFACT_PROTOCOL,
        "matrix_id": matrix_id,
        "spec": probe,
    }
    return M2CMatrixSpec(
        matrix_id=matrix_id,
        matrix_spec_artifact_id=hash_canonical(artifact_payload),
        **payload,
    )


@dataclass(frozen=True)
class M2CVariant:
    variant_id: str
    ordinal: int
    revision_id: str
    case_id: str
    recipient_id: str
    assembly_artifact: ArtifactRef
    context_artifacts: tuple[ArtifactRef, ...]
    target_identity: str
    switches: tuple[str, ...]
    context_kind: str
    tool_identity: str
    evaluator_identity: str
    scorer_taxonomy_identity: str
    request_identity: str

    def __post_init__(self) -> None:
        cls = M2CMatrixError
        object.__setattr__(self, "variant_id", _hash(self.variant_id, "variant_id", cls))
        object.__setattr__(self, "ordinal", _nonnegative_int(self.ordinal, "ordinal", cls))
        object.__setattr__(self, "revision_id", _commit(self.revision_id, "variant revision_id", cls))
        object.__setattr__(self, "case_id", _id(self.case_id, "variant case_id", cls))
        object.__setattr__(self, "recipient_id", _id(self.recipient_id, "variant recipient_id", cls))
        _platform(self.recipient_id, cls)
        object.__setattr__(self, "assembly_artifact", _artifact(self.assembly_artifact, "variant assembly_artifact", cls))
        contexts = _sequence(self.context_artifacts, "variant context_artifacts", cls, item_type=ArtifactRef)
        object.__setattr__(self, "context_artifacts", contexts)
        for name in ("target_identity", "tool_identity", "evaluator_identity", "scorer_taxonomy_identity", "request_identity"):
            object.__setattr__(self, name, _hash(getattr(self, name), "variant " + name, cls))
        switches = _sequence(self.switches, "variant switches", cls, item_type=str)
        if any(not item for item in switches):
            raise cls("variant switches must be nonempty")
        object.__setattr__(self, "switches", switches)
        object.__setattr__(self, "context_kind", _id(self.context_kind, "context_kind", cls))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": M2C_VARIANT_PROTOCOL,
            "ordinal": self.ordinal,
            "revision_id": self.revision_id,
            "case_id": self.case_id,
            "recipient_id": self.recipient_id,
            "assembly_artifact": self.assembly_artifact.to_dict(),
            "context_artifacts": [item.to_dict() for item in self.context_artifacts],
            "target_identity": self.target_identity,
            "switches": list(self.switches),
            "context_kind": self.context_kind,
            "tool_identity": self.tool_identity,
            "evaluator_identity": self.evaluator_identity,
            "scorer_taxonomy_identity": self.scorer_taxonomy_identity,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "request_identity": self.request_identity,
            **self.identity_payload(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M2CVariant":
        if not isinstance(value, Mapping):
            raise M2CMatrixError("variant must be an object")
        fields = {
            "variant_id",
            "request_identity",
            *set(
                {
                    "protocol",
                    "ordinal",
                    "revision_id",
                    "case_id",
                    "recipient_id",
                    "assembly_artifact",
                    "context_artifacts",
                    "target_identity",
                    "switches",
                    "context_kind",
                    "tool_identity",
                    "evaluator_identity",
                    "scorer_taxonomy_identity",
                }
            ),
        }
        if set(value) != fields or value.get("protocol") != M2C_VARIANT_PROTOCOL:
            raise M2CMatrixError("variant fields or protocol are invalid")
        contexts = _sequence(value["context_artifacts"], "variant context_artifacts", M2CMatrixError)
        return cls(
            variant_id=value["variant_id"],
            request_identity=value["request_identity"],
            ordinal=value["ordinal"],
            revision_id=value["revision_id"],
            case_id=value["case_id"],
            recipient_id=value["recipient_id"],
            assembly_artifact=_artifact(value["assembly_artifact"], "assembly_artifact", M2CMatrixError),
            context_artifacts=tuple(_artifact(item, "context_artifact", M2CMatrixError) for item in contexts),
            target_identity=value["target_identity"],
            switches=tuple(_sequence(value["switches"], "variant switches", M2CMatrixError)),
            context_kind=value["context_kind"],
            tool_identity=value["tool_identity"],
            evaluator_identity=value["evaluator_identity"],
            scorer_taxonomy_identity=value["scorer_taxonomy_identity"],
        )


def _variant_request_payload(
    spec: M2CMatrixSpec,
    revision_id: str,
    case: M2CBenchmarkCase,
    switches: tuple[str, ...],
    context_kind: str,
) -> dict[str, Any]:
    return {
        "protocol": M2C_VARIANT_PROTOCOL + ":request",
        "matrix_id": spec.matrix_id,
        "benchmark_id": spec.benchmark_id,
        "gate_id": spec.gate_id,
        "integration_gate_artifact_id": spec.integration_gate_artifact_id,
        "subset_identity": spec.subset_identity,
        "queue_evidence_identity": spec.queue_evidence_identity,
        "provider_identity": spec.provider_identity,
        "archive_identity": spec.archive_identity,
        "revision_id": revision_id,
        "revision_tool_identity": dict(spec.revision_tool_identities)[revision_id],
        "case_id": case.case_id,
        "recipient_id": case.recipient_id,
        "assembly_artifact": case.assembly_artifact.to_dict(),
        "context_artifacts": [item.to_dict() for item in case.context_artifacts],
        "switches": list(switches),
        "context_kind": context_kind,
        "target_identity": case.target_identity,
        "compiler_identity": spec.compiler_identity,
        "evaluator_identity": spec.evaluator_identity,
        "config_identity": spec.config_identity,
        "scorer_taxonomy_identity": spec.scorer_taxonomy_identity,
    }


def enumerate_m2c_variants(
    spec: M2CMatrixSpec,
    qualifications: tuple[M2CRevisionQualification, ...] | list[M2CRevisionQualification],
) -> tuple[M2CVariant, ...]:
    """Enumerate current-first variants from the self-contained matrix spec."""

    if not isinstance(spec, M2CMatrixSpec):
        raise M2CMatrixError("variant enumeration requires a typed matrix spec")
    qualifications_tuple = _sequence(qualifications, "qualifications", M2CMatrixError, item_type=M2CRevisionQualification)
    qualification_map: dict[str, M2CRevisionQualification] = {}
    for item in qualifications_tuple:
        if item.alternate_revision_id in qualification_map:
            raise M2CMatrixError("qualifications repeat an alternate revision")
        qualification_map[item.alternate_revision_id] = item
        if (
            not item.qualified
            or item.benchmark_id != spec.benchmark_id
            or item.alternate_revision_id not in dict(spec.revision_tool_identities)
        ):
            raise M2CMatrixError("matrix contains an unqualified or mismatched alternate")
    for revision_id in spec.qualified_alternate_revision_ids:
        item = qualification_map.get(revision_id)
        if item is None or not item.qualified:
            raise M2CMatrixError("matrix alternate lacks a matching qualification")
    selected_revisions = (
        (spec.current_revision_id,)
        + tuple(sorted(spec.qualified_alternate_revision_ids))
    )
    all_variants: list[M2CVariant] = []
    ordinal = 0
    cases = tuple(sorted(spec.cases, key=lambda item: (item.recipient_id, item.case_id)))
    for revision_id in selected_revisions:
        tool_identity = dict(spec.revision_tool_identities).get(revision_id)
        if tool_identity is None:
            raise M2CMatrixError("matrix revision has no executable identity")
        for case in cases:
            for switches in spec.switch_matrix:
                for context_kind in spec.context_kinds:
                    request_payload = _variant_request_payload(
                        spec, revision_id, case, switches, context_kind
                    )
                    request_identity = hash_canonical(request_payload)
                    variant_payload = {
                        **request_payload,
                        "ordinal": ordinal,
                    }
                    variant_id = hash_canonical(variant_payload)
                    all_variants.append(
                        M2CVariant(
                            variant_id=variant_id,
                            request_identity=request_identity,
                            ordinal=ordinal,
                            revision_id=revision_id,
                            case_id=case.case_id,
                            recipient_id=case.recipient_id,
                            assembly_artifact=case.assembly_artifact,
                            context_artifacts=case.context_artifacts,
                            target_identity=case.target_identity,
                            switches=switches,
                            context_kind=context_kind,
                            tool_identity=tool_identity,
                            evaluator_identity=spec.evaluator_identity,
                            scorer_taxonomy_identity=spec.scorer_taxonomy_identity,
                        )
                    )
                    ordinal += 1
    return tuple(all_variants)


def _receipt_payload(receipt: "M2CMatrixReceipt") -> dict[str, Any]:
    return {
        "protocol": M2C_RECEIPT_PROTOCOL,
        "matrix_id": receipt.matrix_id,
        "matrix_spec_artifact_id": receipt.matrix_spec_artifact_id,
        "benchmark_id": receipt.benchmark_id,
        "benchmark_artifact_id": receipt.benchmark_artifact_id,
        "integration_gate_id": receipt.integration_gate_id,
        "integration_gate_artifact_id": receipt.integration_gate_artifact_id,
        "subset_identity": receipt.subset_identity,
        "queue_evidence_identity": receipt.queue_evidence_identity,
        "provider_identity": receipt.provider_identity,
        "revision_ids": list(receipt.revision_ids),
        "revision_tool_identities": [list(item) for item in receipt.revision_tool_identities],
        "archive_identity": receipt.archive_identity,
        "compiler_identity": receipt.compiler_identity,
        "tool_identity": receipt.tool_identity,
        "evaluator_identity": receipt.evaluator_identity,
        "config_identity": receipt.config_identity,
        "scorer_taxonomy_identity": receipt.scorer_taxonomy_identity,
        "variant_ids": list(receipt.variant_ids),
        "variant_manifest_artifact_id": receipt.variant_manifest_artifact_id,
        "evaluation_artifact_ids": list(receipt.evaluation_artifact_ids),
        "deduplication_artifact_id": receipt.deduplication_artifact_id,
        "compiled_candidate_ids": list(receipt.compiled_candidate_ids),
        "deduplicated_variant_ids": list(receipt.deduplicated_variant_ids),
        "consumed_budget": receipt.consumed_budget,
        "remaining_budget": receipt.remaining_budget,
        "status": receipt.status,
        "refusal_code": receipt.refusal_code,
    }


@dataclass(frozen=True)
class M2CMatrixReceipt:
    receipt_id: str
    matrix_id: str
    matrix_spec_artifact_id: str
    benchmark_id: str
    benchmark_artifact_id: str
    integration_gate_id: str
    integration_gate_artifact_id: str
    subset_identity: str
    queue_evidence_identity: str
    provider_identity: str
    revision_ids: tuple[str, ...]
    revision_tool_identities: tuple[tuple[str, str], ...]
    archive_identity: str
    compiler_identity: str
    tool_identity: str
    evaluator_identity: str
    config_identity: str
    scorer_taxonomy_identity: str
    variant_ids: tuple[str, ...]
    variant_manifest_artifact_id: str
    evaluation_artifact_ids: tuple[str, ...]
    deduplication_artifact_id: str
    compiled_candidate_ids: tuple[str, ...]
    deduplicated_variant_ids: tuple[str, ...]
    consumed_budget: int
    remaining_budget: int
    status: str
    refusal_code: str | None

    def __post_init__(self) -> None:
        cls = M2CMatrixError
        object.__setattr__(self, "receipt_id", _hash(self.receipt_id, "receipt_id", cls))
        for name in (
            "matrix_id",
            "matrix_spec_artifact_id",
            "benchmark_id",
            "benchmark_artifact_id",
            "integration_gate_id",
            "integration_gate_artifact_id",
            "subset_identity",
            "queue_evidence_identity",
            "provider_identity",
            "archive_identity",
            "compiler_identity",
            "tool_identity",
            "evaluator_identity",
            "config_identity",
            "scorer_taxonomy_identity",
            "variant_manifest_artifact_id",
            "deduplication_artifact_id",
        ):
            object.__setattr__(self, name, _hash(getattr(self, name), name, cls))
        revisions = _sequence(self.revision_ids, "receipt revision_ids", cls, item_type=str)
        for item in revisions:
            _commit(item, "receipt revision_id", cls)
        if tuple(sorted(set(revisions))) != revisions:
            raise cls("receipt revision_ids must be sorted and unique")
        object.__setattr__(self, "revision_ids", revisions)
        pairs = _sequence(self.revision_tool_identities, "receipt revision_tool_identities", cls)
        normalized_pairs = tuple(
            (
                _commit(item[0], "receipt revision id", cls),
                _hash(item[1], "receipt tool identity", cls),
            )
            if isinstance(item, (tuple, list)) and len(item) == 2
            else (_raise_matrix("receipt revision tool pairs are invalid"), "")
            for item in pairs
        )
        if tuple(sorted(set(normalized_pairs))) != normalized_pairs:
            raise cls("receipt revision tool pairs must be sorted and unique")
        object.__setattr__(self, "revision_tool_identities", normalized_pairs)
        for name in (
            "variant_ids",
            "evaluation_artifact_ids",
            "compiled_candidate_ids",
            "deduplicated_variant_ids",
        ):
            values = _sequence(getattr(self, name), "receipt " + name, cls, item_type=str)
            for item in values:
                _hash(item, "receipt " + name[:-1] + "_id", cls)
            object.__setattr__(self, name, values)
        object.__setattr__(
            self,
            "consumed_budget",
            _nonnegative_int(self.consumed_budget, "consumed_budget", cls),
        )
        object.__setattr__(
            self,
            "remaining_budget",
            _nonnegative_int(self.remaining_budget, "remaining_budget", cls),
        )
        if self.consumed_budget + self.remaining_budget < 0:
            raise cls("receipt budget accounting is invalid")
        if self.status not in {"complete", "budget_exhausted", "inapplicable"}:
            raise cls("receipt status is invalid")
        if self.refusal_code is not None and (
            not isinstance(self.refusal_code, str) or not self.refusal_code
        ):
            raise cls("receipt refusal_code must be null or nonempty")
        if self.receipt_id != hash_canonical(_receipt_payload(self)):
            raise cls("receipt_id differs from its complete payload")

    def identity_payload(self) -> dict[str, Any]:
        return _receipt_payload(self)

    def to_dict(self) -> dict[str, Any]:
        return {"receipt_id": self.receipt_id, **self.identity_payload()}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "M2CMatrixReceipt":
        if not isinstance(value, Mapping):
            raise M2CMatrixError("matrix receipt must be an object")
        fields = {
            "receipt_id",
            "protocol",
            "matrix_id",
            "matrix_spec_artifact_id",
            "benchmark_id",
            "benchmark_artifact_id",
            "integration_gate_id",
            "integration_gate_artifact_id",
            "subset_identity",
            "queue_evidence_identity",
            "provider_identity",
            "revision_ids",
            "revision_tool_identities",
            "archive_identity",
            "compiler_identity",
            "tool_identity",
            "evaluator_identity",
            "config_identity",
            "scorer_taxonomy_identity",
            "variant_ids",
            "variant_manifest_artifact_id",
            "evaluation_artifact_ids",
            "deduplication_artifact_id",
            "compiled_candidate_ids",
            "deduplicated_variant_ids",
            "consumed_budget",
            "remaining_budget",
            "status",
            "refusal_code",
        }
        if set(value) != fields or value.get("protocol") != M2C_RECEIPT_PROTOCOL:
            raise M2CMatrixError("matrix receipt fields or protocol are invalid")
        return cls(
            receipt_id=value["receipt_id"],
            matrix_id=value["matrix_id"],
            matrix_spec_artifact_id=value["matrix_spec_artifact_id"],
            benchmark_id=value["benchmark_id"],
            benchmark_artifact_id=value["benchmark_artifact_id"],
            integration_gate_id=value["integration_gate_id"],
            integration_gate_artifact_id=value["integration_gate_artifact_id"],
            subset_identity=value["subset_identity"],
            queue_evidence_identity=value["queue_evidence_identity"],
            provider_identity=value["provider_identity"],
            revision_ids=tuple(_sequence(value["revision_ids"], "revision_ids", M2CMatrixError)),
            revision_tool_identities=tuple(
                tuple(item)
                for item in _sequence(value["revision_tool_identities"], "revision_tool_identities", M2CMatrixError)
            ),
            archive_identity=value["archive_identity"],
            compiler_identity=value["compiler_identity"],
            tool_identity=value["tool_identity"],
            evaluator_identity=value["evaluator_identity"],
            config_identity=value["config_identity"],
            scorer_taxonomy_identity=value["scorer_taxonomy_identity"],
            variant_ids=tuple(_sequence(value["variant_ids"], "variant_ids", M2CMatrixError)),
            variant_manifest_artifact_id=value["variant_manifest_artifact_id"],
            evaluation_artifact_ids=tuple(_sequence(value["evaluation_artifact_ids"], "evaluation_artifact_ids", M2CMatrixError)),
            deduplication_artifact_id=value["deduplication_artifact_id"],
            compiled_candidate_ids=tuple(_sequence(value["compiled_candidate_ids"], "compiled_candidate_ids", M2CMatrixError)),
            deduplicated_variant_ids=tuple(_sequence(value["deduplicated_variant_ids"], "deduplicated_variant_ids", M2CMatrixError)),
            consumed_budget=value["consumed_budget"],
            remaining_budget=value["remaining_budget"],
            status=value["status"],
            refusal_code=value["refusal_code"],
        )


def _raise_matrix(message: str) -> Any:
    raise M2CMatrixError(message)


def _benchmark_artifact_payload(benchmark: M2CFixedBenchmark) -> dict[str, Any]:
    return {
        "protocol": M2C_BENCHMARK_ARTIFACT_PROTOCOL,
        "benchmark": benchmark.to_dict(),
    }


def _ensure_benchmark_artifact(
    benchmark: M2CFixedBenchmark,
    archive: ContentAddressedArchive,
) -> ArtifactRef:
    payload = _benchmark_artifact_payload(benchmark)
    expected = (
        benchmark.benchmark_artifact.content_hash
        if benchmark.benchmark_artifact is not None
        else None
    )
    if expected is not None:
        return _archive_exact(
            archive,
            payload,
            expected_identity=expected,
            category="m2c-benchmarks",
            label="fixed benchmark",
            exc_type=M2CBenchmarkError,
        )
    return _archive_exact(
        archive,
        payload,
        expected_identity=None,
        category="m2c-benchmarks",
        label="fixed benchmark",
        exc_type=M2CBenchmarkError,
    )


def _ensure_matrix_spec_artifact(
    spec: M2CMatrixSpec,
    archive: ContentAddressedArchive,
) -> ArtifactRef:
    return _archive_exact(
        archive,
        spec.artifact_payload(),
        expected_identity=spec.matrix_spec_artifact_id,
        category="m2c-matrix-specs",
        label="matrix specification",
        exc_type=M2CMatrixError,
    )


def _load_matrix_benchmark_artifact(
    spec: M2CMatrixSpec,
    archive: ContentAddressedArchive,
) -> tuple[ArtifactRef, M2CFixedBenchmark]:
    """Load the exact archived fixed benchmark named by a matrix spec."""

    expected = _hash(
        spec.benchmark_artifact_id,
        "matrix benchmark_artifact_id",
        M2CMatrixError,
    )
    category_root = archive.artifacts_root / "m2c-benchmarks"
    if category_root.is_symlink() or not category_root.is_dir():
        raise M2CMatrixError("matrix benchmark archive is missing")
    candidates: list[tuple[ArtifactRef, bytes]] = []
    for path in sorted(category_root.glob(expected[7:] + "*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            relative = path.relative_to(archive.run_root).as_posix()
            resolved = archive.resolve(
                ArtifactRef(
                    content_hash=expected,
                    path=relative,
                    media_type="application/json",
                    byte_size=0,
                )
            )
            raw = resolved.read_bytes()
            reference = ArtifactRef(
                content_hash=expected,
                path=relative,
                media_type="application/json",
                byte_size=len(raw),
            )
            if archive.verify(reference) != raw:
                raise M2CMatrixError("matrix benchmark artifact bytes changed")
        except (ArchiveError, OSError, SearchValidationError, TypeError, ValueError) as exc:
            raise M2CMatrixError(
                "matrix benchmark artifact is missing or corrupt"
            ) from exc
        if hash_bytes(raw) != expected:
            raise M2CMatrixError("matrix benchmark artifact identity differs")
        candidates.append((reference, raw))
    if len(candidates) != 1:
        raise M2CMatrixError(
            "matrix benchmark artifact is missing or ambiguous"
        )
    reference, raw = candidates[0]
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M2CMatrixError("matrix benchmark artifact is not JSON") from exc
    if raw != canonical_bytes(value):
        raise M2CMatrixError("matrix benchmark artifact is not canonical JSON")
    if (
        not isinstance(value, Mapping)
        or set(value) != {"protocol", "benchmark"}
        or value.get("protocol") != M2C_BENCHMARK_ARTIFACT_PROTOCOL
    ):
        raise M2CMatrixError("matrix benchmark artifact protocol is invalid")
    try:
        benchmark = M2CFixedBenchmark.from_dict(value["benchmark"])
    except (M2CBenchmarkError, TypeError, ValueError) as exc:
        raise M2CMatrixError("matrix benchmark artifact is malformed") from exc
    if (
        benchmark.benchmark_id != spec.benchmark_id
        or benchmark.current_revision_id != spec.current_revision_id
        or benchmark.scorer_taxonomy_identity != spec.scorer_taxonomy_identity
        or benchmark.evaluator_identity != spec.evaluator_identity
        or benchmark.cases != spec.cases
    ):
        raise M2CMatrixError("matrix benchmark artifact differs from its specification")
    return reference, benchmark


def _locate_archived_references(
    archive: ContentAddressedArchive,
    identity: str,
    categories: tuple[str, ...],
    label: str,
) -> tuple[ArtifactRef, ...]:
    """Find existing content-addressed objects without creating or repairing them."""

    expected = _hash(identity, label + " identity", M2CMatrixError)
    found: list[ArtifactRef] = []
    for category in categories:
        category_root = archive.artifacts_root / category
        if category_root.is_symlink():
            raise M2CMatrixError(label + " archive category contains a symlink")
        if not category_root.is_dir():
            continue
        try:
            paths = sorted(category_root.glob(expected[7:] + "*"))
        except OSError as exc:
            raise M2CMatrixError(label + " archive cannot be inspected") from exc
        for path in paths:
            if path.is_symlink():
                raise M2CMatrixError(label + " archive object is a symlink")
            if not path.is_file():
                continue
            try:
                relative = path.relative_to(archive.run_root).as_posix()
                resolved = archive.resolve(
                    ArtifactRef(
                        content_hash=expected,
                        path=relative,
                        media_type="application/octet-stream",
                        byte_size=0,
                    )
                )
                raw = resolved.read_bytes()
                reference = ArtifactRef(
                    content_hash=expected,
                    path=relative,
                    media_type="application/octet-stream",
                    byte_size=len(raw),
                )
                if archive.verify(reference) != raw:
                    raise M2CMatrixError(label + " artifact bytes changed")
            except (ArchiveError, OSError, SearchValidationError, TypeError, ValueError) as exc:
                raise M2CMatrixError(label + " artifact is missing or corrupt") from exc
            if hash_bytes(raw) != expected:
                raise M2CMatrixError(label + " artifact identity differs")
            found.append(reference)
    if not found:
        raise M2CMatrixError(label + " artifact is missing")
    return tuple(found)


def _verify_record_payload(
    archive: ContentAddressedArchive,
    payload: Mapping[str, Any],
    identity: str,
    categories: tuple[str, ...],
    label: str,
) -> None:
    expected = _hash(identity, label + " identity", M2CMatrixError)
    raw = canonical_bytes(payload)
    if hash_bytes(raw) != expected:
        raise M2CMatrixError(label + " identity differs from its payload")
    references = _locate_archived_references(archive, expected, categories, label)
    if not any(archive.verify(reference) == raw for reference in references):
        raise M2CMatrixError(label + " archived bytes differ from its payload")


def _provider_signature(provider: Any, exc_type: type[ValueError]) -> None:
    generate = getattr(provider, "generate_draft", None)
    resolve = getattr(provider, "resolve_revision", None)
    if not callable(generate) or not callable(resolve):
        raise exc_type("m2c provider does not implement its typed protocol")
    try:
        inspect.signature(generate).bind(
            object(),
            assembly=b"assembly",
            contexts=(b"context",),
        )
        inspect.signature(resolve).bind("0" * 40)
    except (TypeError, ValueError) as exc:
        raise exc_type("m2c provider has an unsupported call shape") from exc


def _resolve_provider_revision(
    provider: M2CRevisionProvider,
    revision_id: str,
    exc_type: type[ValueError],
) -> M2CRevisionIdentity:
    _provider_signature(provider, exc_type)
    try:
        identity = provider.resolve_revision(revision_id)
    except M2CProviderError as exc:
        raise exc_type(f"m2c revision {revision_id} is unavailable") from exc
    if not isinstance(identity, M2CRevisionIdentity):
        raise exc_type("m2c provider returned an untyped revision")
    if identity.revision_id != revision_id:
        raise exc_type("m2c provider returned the wrong revision identity")
    return _revision(identity, "resolved revision", exc_type)


def _case_input(
    archive: ContentAddressedArchive,
    case: M2CBenchmarkCase,
    exc_type: type[ValueError],
) -> tuple[bytes, tuple[bytes, ...]]:
    assembly = _verify_archive(
        archive,
        case.assembly_artifact,
        f"{case.case_id} assembly",
        exc_type,
        path_prefixes=("artifacts/",),
    )
    contexts = tuple(
        _verify_archive(
            archive,
            item,
            f"{case.case_id} context",
            exc_type,
            path_prefixes=("artifacts/",),
        )
        for item in case.context_artifacts
    )
    return assembly, contexts


def _invoke_case(
    benchmark: M2CFixedBenchmark,
    revision: M2CRevisionIdentity,
    case: M2CBenchmarkCase,
    provider: M2CRevisionProvider,
    evaluator: Callable[[M2CBenchmarkCase, ArtifactRef, str], ScoreVector],
    archive: ContentAddressedArchive,
    gate: IntegrationGateReceipt,
    *,
    archive_identity: str,
    ordinal: int,
) -> tuple[M2CEvaluation, ArtifactRef]:
    assembly, contexts = _case_input(archive, case, M2CBenchmarkError)
    try:
        invocation = make_invocation(
            revision_id=revision.revision_id,
            tree_identity=revision.tree_identity,
            provider_identity=revision.provider_identity,
            recipient_id=case.recipient_id,
            assembly_artifact=case.assembly_artifact,
            context_artifacts=case.context_artifacts,
            switches=case.switches,
            target_identity=case.target_identity,
            compiler_identity=case.compiler_identity,
            tool_identity=revision.executable_identity,
            evaluator_identity=case.evaluator_identity,
            scorer_taxonomy_identity=benchmark.scorer_taxonomy_identity,
            config_identity=case.config_identity,
            integration_gate_id=gate.gate_id,
            integration_gate_artifact_id=gate.receipt_artifact.content_hash,
            subset_identity=gate.subset_identity,
            queue_evidence_identity=gate.queue_evidence_identity,
            archive_identity=archive_identity,
            ordinal=ordinal,
        )
    except (M2CProviderError, TypeError, ValueError) as exc:
        raise M2CBenchmarkError("m2c invocation could not be bound") from exc
    try:
        draft = provider.generate_draft(
            invocation,
            assembly=assembly,
            contexts=contexts,
        )
    except M2CProviderError as exc:
        raise M2CBenchmarkError("m2c provider rejected the benchmark invocation") from exc
    if not isinstance(draft, M2CDraftPayload):
        raise M2CBenchmarkError("m2c provider returned an untyped draft payload")
    if draft.invocation_id != invocation.invocation_id or draft.revision_id != revision.revision_id:
        raise M2CBenchmarkError("m2c draft is not bound to its invocation")
    source_bytes = _verify_archive(
        archive,
        draft.source_artifact,
        f"{case.case_id} m2c draft",
        M2CBenchmarkError,
        path_prefixes=("artifacts/m2c-drafts/", "artifacts/sources/"),
    )
    try:
        measured = evaluator(case, draft.source_artifact, benchmark.scorer_taxonomy_identity)
    except (M2CBenchmarkError, SearchValidationError) as exc:
        raise M2CBenchmarkError("m2c evaluator refused the benchmark case") from exc
    score = _score(measured, f"{case.case_id} score", M2CBenchmarkError)
    if score.compiler_identity != case.compiler_identity:
        raise M2CBenchmarkError("score compiler identity differs from benchmark case")
    observation = M2CEvaluation(
        case_id=case.case_id,
        revision_id=revision.revision_id,
        invocation_id=invocation.invocation_id,
        source_artifact=draft.source_artifact,
        score=score,
        tool_identity=revision.executable_identity,
        evaluator_identity=case.evaluator_identity,
        scorer_taxonomy_identity=benchmark.scorer_taxonomy_identity,
        cost_units=max(1, score.elapsed_ms),
    )
    artifact = _archive_exact(
        archive,
        observation.to_dict(),
        expected_identity=None,
        category="m2c-evaluations",
        label=f"{case.case_id} evaluation",
        exc_type=M2CBenchmarkError,
    )
    if archive.verify(artifact) != canonical_bytes(observation.to_dict()):
        raise M2CBenchmarkError("evaluation archive failed byte verification")
    del source_bytes
    return observation, artifact


def run_fixed_benchmark(
    benchmark: M2CFixedBenchmark,
    revision: M2CRevisionIdentity,
    provider: M2CRevisionProvider,
    evaluator: Callable[[M2CBenchmarkCase, ArtifactRef, str], ScoreVector],
    archive: ContentAddressedArchive,
    *,
    archive_identity: str,
    gate: IntegrationGateReceipt,
) -> M2CBenchmarkReport:
    """Run each fixed case exactly once under one validated gate."""

    if not isinstance(benchmark, M2CFixedBenchmark):
        raise M2CBenchmarkError("benchmark must be typed")
    revision = _revision(revision, "benchmark revision", M2CBenchmarkError)
    if not callable(evaluator):
        raise M2CBenchmarkError("benchmark evaluator must be callable")
    archive_identity = _hash(archive_identity, "archive_identity", M2CBenchmarkError)
    _validate_gate(gate, archive, M2CBenchmarkError)
    if benchmark.current_revision_id != CURRENT_M2C_REVISION:
        raise M2CBenchmarkError("fixed benchmark current revision is not the pinned current revision")
    if revision.config_identity != benchmark.cases[0].config_identity:
        raise M2CBenchmarkError("benchmark revision config differs from fixed cases")
    if any(item.config_identity != revision.config_identity for item in benchmark.cases):
        raise M2CBenchmarkError("benchmark cases do not share the revision config")
    _provider_signature(provider, M2CBenchmarkError)
    benchmark_artifact = _ensure_benchmark_artifact(benchmark, archive)
    observations: list[M2CEvaluation] = []
    observation_artifacts: list[str] = []
    for ordinal, case in enumerate(sorted(benchmark.cases, key=lambda item: item.case_id)):
        observation, artifact = _invoke_case(
            benchmark,
            revision,
            case,
            provider,
            evaluator,
            archive,
            gate,
            archive_identity=archive_identity,
            ordinal=ordinal,
        )
        observations.append(observation)
        observation_artifacts.append(artifact.content_hash)
    candidate_ids = {item.source_artifact.content_hash for item in observations}
    report = make_benchmark_report(
        benchmark_id=benchmark.benchmark_id,
        benchmark_artifact_id=benchmark_artifact.content_hash,
        revision_id=revision.revision_id,
        tree_identity=revision.tree_identity,
        provider_identity=revision.provider_identity,
        tool_identity=revision.executable_identity,
        archive_identity=archive_identity,
        integration_gate_id=gate.gate_id,
        integration_gate_artifact_id=gate.receipt_artifact.content_hash,
        subset_identity=gate.subset_identity,
        queue_evidence_identity=gate.queue_evidence_identity,
        compiler_identity=benchmark.cases[0].compiler_identity,
        evaluator_identity=benchmark.evaluator_identity,
        config_identity=revision.config_identity,
        scorer_taxonomy_identity=benchmark.scorer_taxonomy_identity,
        observations=tuple(observations),
        observation_artifact_ids=tuple(observation_artifacts),
        total_cost_units=sum(item.cost_units for item in observations),
        unique_candidate_count=len(candidate_ids),
        better_case_count=0,
        complete=len(observations) == len(benchmark.cases),
        refusal_code=None,
    )
    _archive_exact(
        archive,
        report.identity_payload(),
        expected_identity=report.report_id,
        category="m2c-benchmark-reports",
        label="benchmark report",
        exc_type=M2CBenchmarkError,
    )
    return report


def _same_case_set(
    first: M2CBenchmarkReport,
    second: M2CBenchmarkReport,
) -> bool:
    return {item.case_id for item in first.observations} == {
        item.case_id for item in second.observations
    }


def _matrix_payload_fields() -> tuple[str, ...]:
    return _spec_payload_fields()


def _variant_sort_key(item: M2CVariant, current_revision_id: str) -> tuple[Any, ...]:
    return (
        0 if item.revision_id == current_revision_id else 1,
        item.revision_id,
        item.recipient_id,
        item.case_id,
        item.switches,
        item.context_kind,
        item.variant_id,
    )


def _matrix_variant_payload(
    spec: M2CMatrixSpec,
    variant: M2CVariant,
    ordinal: int,
) -> dict[str, Any]:
    return {
        "protocol": M2C_VARIANT_PROTOCOL + ":request",
        "matrix_id": spec.matrix_id,
        "variant_id": variant.variant_id,
        "ordinal": ordinal,
        "request_identity": variant.request_identity,
        "variant": variant.to_dict(),
    }


def run_m2c_matrix(
    spec: M2CMatrixSpec,
    variants: tuple[M2CVariant, ...] | list[M2CVariant],
    provider: M2CRevisionProvider,
    evaluator: Callable[[M2CBenchmarkCase, ArtifactRef, str], ScoreVector],
    archive: ContentAddressedArchive,
    gate: IntegrationGateReceipt,
) -> M2CMatrixReceipt:
    """Run bounded, deterministically ordered variants and archive its receipt."""

    if not isinstance(spec, M2CMatrixSpec):
        raise M2CMatrixError("matrix spec must be typed")
    if not callable(evaluator):
        raise M2CMatrixError("matrix evaluator must be callable")
    variants_tuple = _sequence(variants, "matrix variants", M2CMatrixError, item_type=M2CVariant)
    _validate_gate(gate, archive, M2CMatrixError)
    if (
        spec.gate_id != gate.gate_id
        or spec.integration_gate_artifact_id != gate.receipt_artifact.content_hash
        or spec.subset_identity != gate.subset_identity
        or spec.queue_evidence_identity != gate.queue_evidence_identity
    ):
        raise M2CMatrixError("matrix specification differs from integration gate")
    _provider_signature(provider, M2CMatrixError)
    _ensure_matrix_spec_artifact(spec, archive)
    _benchmark_artifact, _benchmark = _load_matrix_benchmark_artifact(
        spec,
        archive,
    )
    del _benchmark_artifact, _benchmark
    ordered = tuple(sorted(variants_tuple, key=lambda item: _variant_sort_key(item, spec.current_revision_id)))
    if tuple(item.ordinal for item in ordered) != tuple(range(len(ordered))):
        raise M2CMatrixError("matrix variants must have contiguous canonical ordinals")
    revision_tools = dict(spec.revision_tool_identities)
    selected_ids = {spec.current_revision_id, *spec.qualified_alternate_revision_ids}
    for variant in ordered:
        if variant.revision_id not in selected_ids:
            raise M2CMatrixError("variant revision is outside the qualified matrix")
        if revision_tools.get(variant.revision_id) != variant.tool_identity:
            raise M2CMatrixError("variant executable identity differs from matrix")
        if variant.evaluator_identity != spec.evaluator_identity:
            raise M2CMatrixError("variant evaluator identity differs from matrix")
        if variant.scorer_taxonomy_identity != spec.scorer_taxonomy_identity:
            raise M2CMatrixError("variant scorer identity differs from matrix")
    variant_manifest_payload = {
        "protocol": M2C_VARIANT_MANIFEST_PROTOCOL,
        "matrix_id": spec.matrix_id,
        "variants": [item.to_dict() for item in ordered],
    }
    variant_manifest = _archive_exact(
        archive,
        variant_manifest_payload,
        expected_identity=None,
        category="m2c-variant-manifests",
        label="variant manifest",
        exc_type=M2CMatrixError,
    )
    resolved: dict[str, M2CRevisionIdentity] = {}
    for revision_id in sorted({item.revision_id for item in ordered}):
        resolved[revision_id] = _resolve_provider_revision(provider, revision_id, M2CMatrixError)
        if resolved[revision_id].executable_identity != revision_tools[revision_id]:
            raise M2CMatrixError("resolved executable identity differs from matrix")
        if resolved[revision_id].provider_identity != spec.provider_identity:
            raise M2CMatrixError("resolved provider identity differs from matrix")
        if resolved[revision_id].config_identity != spec.config_identity:
            raise M2CMatrixError("resolved revision config differs from matrix")
    compiled: list[str] = []
    dedup_variants: list[str] = []
    evaluations: list[str] = []
    dedup_map: dict[str, list[str]] = {}
    consumed = 0
    budget_blocked = False
    for ordinal, variant in enumerate(ordered):
        if consumed >= spec.budget:
            budget_blocked = True
            continue
        revision = resolved[variant.revision_id]
        case = next((item for item in spec.cases if item.case_id == variant.case_id), None)
        if case is None:
            raise M2CMatrixError("variant refers to no matrix case")
        if case.recipient_id != variant.recipient_id or case.assembly_artifact != variant.assembly_artifact:
            raise M2CMatrixError("variant case binding differs from matrix case")
        case_for_variant = M2CBenchmarkCase(
            case_id=case.case_id,
            recipient_id=case.recipient_id,
            assembly_artifact=case.assembly_artifact,
            context_artifacts=case.context_artifacts,
            target_identity=case.target_identity,
            compiler_identity=case.compiler_identity,
            evaluator_identity=case.evaluator_identity,
            config_identity=case.config_identity,
            switches=variant.switches,
        )
        observation, evaluation_artifact = _invoke_case(
            M2CFixedBenchmark(
                benchmark_id=spec.benchmark_id,
                current_revision_id=spec.current_revision_id,
                cases=(case_for_variant,),
                scorer_taxonomy_identity=spec.scorer_taxonomy_identity,
                evaluator_identity=spec.evaluator_identity,
                budget=1,
            ),
            revision,
            case_for_variant,
            provider,
            evaluator,
            archive,
            gate,
            archive_identity=spec.archive_identity,
            ordinal=ordinal,
        )
        candidate_key = (
            variant.recipient_id,
            observation.source_artifact.content_hash,
            variant.target_identity,
            spec.compiler_identity,
            spec.config_identity,
            spec.scorer_taxonomy_identity,
        )
        key_identity = hash_canonical({"protocol": M2C_MATRIX_PROTOCOL + ":candidate", "key": list(candidate_key)})
        dedup_map.setdefault(key_identity, []).append(variant.variant_id)
        if key_identity in dedup_map and len(dedup_map[key_identity]) > 1:
            continue
        consumed += 1
        compiled.append(observation.source_artifact.content_hash)
        dedup_variants.append(variant.variant_id)
        evaluations.append(evaluation_artifact.content_hash)
    # Variants not reached because the immutable budget was exhausted are
    # retained in the manifest and represented by the refusal disposition.
    exhausted = budget_blocked
    dedup_map = {key: sorted(values) for key, values in sorted(dedup_map.items())}
    deduplication_payload = {
        "protocol": M2C_DEDUPLICATION_PROTOCOL,
        "matrix_id": spec.matrix_id,
        "candidate_to_variants": dedup_map,
        "compiled_candidate_ids": sorted(set(compiled)),
    }
    deduplication = _archive_exact(
        archive,
        deduplication_payload,
        expected_identity=None,
        category="m2c-deduplication",
        label="deduplication map",
        exc_type=M2CMatrixError,
    )
    status = "budget_exhausted" if exhausted else "complete"
    refusal_code = "budget_exhausted" if exhausted else None
    receipt_probe = {
        "protocol": M2C_RECEIPT_PROTOCOL,
        "matrix_id": spec.matrix_id,
        "matrix_spec_artifact_id": spec.matrix_spec_artifact_id,
        "benchmark_id": spec.benchmark_id,
        "benchmark_artifact_id": spec.benchmark_artifact_id,
        "integration_gate_id": gate.gate_id,
        "integration_gate_artifact_id": gate.receipt_artifact.content_hash,
        "subset_identity": spec.subset_identity,
        "queue_evidence_identity": spec.queue_evidence_identity,
        "provider_identity": spec.provider_identity,
        "revision_ids": sorted({item.revision_id for item in ordered}),
        "revision_tool_identities": [list(item) for item in spec.revision_tool_identities],
        "archive_identity": spec.archive_identity,
        "compiler_identity": spec.compiler_identity,
        "tool_identity": spec.tool_identity,
        "evaluator_identity": spec.evaluator_identity,
        "config_identity": spec.config_identity,
        "scorer_taxonomy_identity": spec.scorer_taxonomy_identity,
        "variant_ids": [item.variant_id for item in ordered],
        "variant_manifest_artifact_id": variant_manifest.content_hash,
        "evaluation_artifact_ids": evaluations,
        "deduplication_artifact_id": deduplication.content_hash,
        "compiled_candidate_ids": sorted(set(compiled)),
        "deduplicated_variant_ids": dedup_variants,
        "consumed_budget": consumed,
        "remaining_budget": max(0, spec.budget - consumed),
        "status": status,
        "refusal_code": refusal_code,
    }
    receipt = M2CMatrixReceipt(
        receipt_id=hash_canonical(receipt_probe),
        matrix_id=spec.matrix_id,
        matrix_spec_artifact_id=spec.matrix_spec_artifact_id,
        benchmark_id=spec.benchmark_id,
        benchmark_artifact_id=spec.benchmark_artifact_id,
        integration_gate_id=gate.gate_id,
        integration_gate_artifact_id=gate.receipt_artifact.content_hash,
        subset_identity=spec.subset_identity,
        queue_evidence_identity=spec.queue_evidence_identity,
        provider_identity=spec.provider_identity,
        revision_ids=tuple(sorted({item.revision_id for item in ordered})),
        revision_tool_identities=spec.revision_tool_identities,
        archive_identity=spec.archive_identity,
        compiler_identity=spec.compiler_identity,
        tool_identity=spec.tool_identity,
        evaluator_identity=spec.evaluator_identity,
        config_identity=spec.config_identity,
        scorer_taxonomy_identity=spec.scorer_taxonomy_identity,
        variant_ids=tuple(item.variant_id for item in ordered),
        variant_manifest_artifact_id=variant_manifest.content_hash,
        evaluation_artifact_ids=tuple(evaluations),
        deduplication_artifact_id=deduplication.content_hash,
        compiled_candidate_ids=tuple(sorted(set(compiled))),
        deduplicated_variant_ids=tuple(dedup_variants),
        consumed_budget=consumed,
        remaining_budget=max(0, spec.budget - consumed),
        status=status,
        refusal_code=refusal_code,
    )
    _archive_exact(
        archive,
        receipt.identity_payload(),
        expected_identity=receipt.receipt_id,
        category="m2c-matrix-receipts",
        label="matrix receipt",
        exc_type=M2CMatrixError,
    )
    return receipt


def verify_benchmark_report(
    report: M2CBenchmarkReport,
    *,
    archive: ContentAddressedArchive,
) -> None:
    if not isinstance(report, M2CBenchmarkReport):
        raise M2CBenchmarkError("benchmark report must be typed")
    try:
        _verify_record_payload(
            archive,
            report.identity_payload(),
            report.report_id,
            ("m2c-benchmark-reports",),
            "benchmark report",
        )
        for identity in report.observation_artifact_ids:
            _locate_archived_references(
                archive,
                identity,
                ("m2c-evaluations",),
                "benchmark evaluation",
            )
        for observation in report.observations:
            _locate_archived_references(
                archive,
                observation.source_artifact.content_hash,
                ("m2c-drafts", "sources"),
                "benchmark draft",
            )
    except M2CMatrixError as exc:
        raise M2CBenchmarkError(str(exc)) from exc


def load_benchmark_report(
    source: ArtifactRef | Mapping[str, Any],
    *,
    archive: ContentAddressedArchive,
) -> M2CBenchmarkReport:
    if isinstance(source, ArtifactRef):
        raw = _verify_archive(
            archive,
            source,
            "benchmark report",
            M2CBenchmarkError,
            media_type="application/json",
            path_prefixes=("artifacts/m2c-benchmark-reports/",),
        )
        try:
            document = json.loads(raw.decode("utf-8"))
            if isinstance(document, Mapping) and "report_id" not in document:
                document = {"report_id": source.content_hash, **document}
            report = M2CBenchmarkReport.from_dict(document)
        except (UnicodeDecodeError, ValueError, TypeError, M2CBenchmarkError) as exc:
            raise M2CBenchmarkError("benchmark report archive is malformed") from exc
        if report.report_id != source.content_hash:
            raise M2CBenchmarkError("benchmark report artifact identity differs")
    else:
        try:
            document = dict(source)
            if "report_id" not in document:
                document = {"report_id": hash_canonical(document), **document}
            report = M2CBenchmarkReport.from_dict(document)
        except (M2CBenchmarkError, TypeError, ValueError) as exc:
            raise M2CBenchmarkError("benchmark report mapping is invalid") from exc
    verify_benchmark_report(report, archive=archive)
    return report


def verify_m2c_matrix_receipt(
    receipt: M2CMatrixReceipt,
    *,
    archive: ContentAddressedArchive,
) -> None:
    if not isinstance(receipt, M2CMatrixReceipt):
        raise M2CMatrixError("matrix receipt must be typed")
    _verify_record_payload(
        archive,
        receipt.identity_payload(),
        receipt.receipt_id,
        ("m2c-matrix-receipts",),
        "matrix receipt",
    )
    _locate_archived_references(
        archive,
        receipt.integration_gate_artifact_id,
        ("receipts",),
        "integration gate receipt",
    )
    _locate_archived_references(
        archive,
        receipt.benchmark_artifact_id,
        ("m2c-benchmarks",),
        "matrix benchmark",
    )
    _locate_archived_references(
        archive,
        receipt.matrix_spec_artifact_id,
        ("m2c-matrix-specs",),
        "matrix specification",
    )
    _locate_archived_references(
        archive,
        receipt.variant_manifest_artifact_id,
        ("m2c-variant-manifests",),
        "matrix variant manifest",
    )
    for identity in receipt.evaluation_artifact_ids:
        _locate_archived_references(
            archive,
            identity,
            ("m2c-evaluations",),
            "matrix evaluation",
        )
    _locate_archived_references(
        archive,
        receipt.deduplication_artifact_id,
        ("m2c-deduplication",),
        "matrix deduplication",
    )
    for identity in receipt.compiled_candidate_ids:
        _locate_archived_references(
            archive,
            identity,
            ("m2c-drafts", "sources"),
            "matrix candidate",
        )


def load_m2c_matrix_receipt(
    source: ArtifactRef | Mapping[str, Any],
    *,
    archive: ContentAddressedArchive,
) -> M2CMatrixReceipt:
    if isinstance(source, ArtifactRef):
        raw = _verify_archive(
            archive,
            source,
            "matrix receipt",
            M2CMatrixError,
            media_type="application/json",
            path_prefixes=("artifacts/m2c-matrix-receipts/",),
        )
        try:
            document = json.loads(raw.decode("utf-8"))
            if isinstance(document, Mapping) and "receipt_id" not in document:
                document = {"receipt_id": source.content_hash, **document}
            receipt = M2CMatrixReceipt.from_dict(document)
        except (UnicodeDecodeError, ValueError, TypeError, M2CMatrixError) as exc:
            raise M2CMatrixError("matrix receipt archive is malformed") from exc
        if receipt.receipt_id != source.content_hash:
            raise M2CMatrixError("matrix receipt artifact identity differs")
    else:
        try:
            document = dict(source)
            if "receipt_id" not in document:
                document = {"receipt_id": hash_canonical(document), **document}
            receipt = M2CMatrixReceipt.from_dict(document)
        except (M2CMatrixError, TypeError, ValueError) as exc:
            raise M2CMatrixError("matrix receipt mapping is invalid") from exc
    verify_m2c_matrix_receipt(receipt, archive=archive)
    return receipt


def replay_m2c_matrix(
    spec: M2CMatrixSpec,
    variants: tuple[M2CVariant, ...] | list[M2CVariant],
    provider: M2CRevisionProvider,
    evaluator: Callable[[M2CBenchmarkCase, ArtifactRef, str], ScoreVector],
    archive: ContentAddressedArchive,
    gate: IntegrationGateReceipt,
    *,
    expected: M2CMatrixReceipt | None = None,
) -> M2CMatrixReceipt:
    result = run_m2c_matrix(spec, variants, provider, evaluator, archive, gate)
    if expected is not None and result != expected:
        raise M2CMatrixError("matrix replay differs from its archived receipt")
    return result


@dataclass(frozen=True)
class M2CRevisionPin:
    """One exact pinned revision plus immutable source/tool/runner evidence."""

    revision: M2CRevisionIdentity
    source_artifact: ArtifactRef | None
    tool_artifact: ArtifactRef | None
    runner_identity: str
    available: bool = True
    unavailable_reason: str = ""

    def __post_init__(self) -> None:
        cls = M2CMatrixError
        object.__setattr__(self, "revision", _revision(self.revision, "revision pin", cls))
        for name in ("source_artifact", "tool_artifact"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _artifact(value, name, cls))
        object.__setattr__(self, "runner_identity", _hash(self.runner_identity, "runner_identity", cls))
        if not isinstance(self.available, bool):
            raise cls("revision pin availability must be boolean")
        if self.available and (self.source_artifact is None or self.tool_artifact is None):
            raise cls("available revision pin requires source and tool artifacts")
        if not self.available and (
            not isinstance(self.unavailable_reason, str) or not self.unavailable_reason
        ):
            raise cls("unavailable revision pin requires a reason")
        if (
            self.source_artifact is not None
            and self.tool_artifact is not None
            and self.source_artifact.content_hash == self.tool_artifact.content_hash
        ):
            raise cls("revision source and tool artifacts must differ")

    @property
    def revision_id(self) -> str:
        return self.revision.revision_id

    @property
    def executable_identity(self) -> str:
        return self.revision.executable_identity

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": M2C_MATRIX_PROTOCOL + ":pin",
            "revision": self.revision.to_dict(),
            "source_artifact": None if self.source_artifact is None else self.source_artifact.to_dict(),
            "tool_artifact": None if self.tool_artifact is None else self.tool_artifact.to_dict(),
            "runner_identity": self.runner_identity,
            "available": self.available,
            "unavailable_reason": self.unavailable_reason,
        }

    @property
    def pin_identity(self) -> str:
        return hash_canonical(self.identity_payload())


@dataclass(frozen=True)
class M2CUnavailableRevisionReceipt:
    receipt_id: str
    revision_id: str
    executable_identity: str
    provider_identity: str
    runner_identity: str
    reason_code: str
    detail: str

    def __post_init__(self) -> None:
        cls = M2CMatrixError
        object.__setattr__(self, "receipt_id", _hash(self.receipt_id, "unavailable receipt_id", cls))
        object.__setattr__(self, "revision_id", _commit(self.revision_id, "unavailable revision_id", cls))
        for name in ("executable_identity", "provider_identity", "runner_identity"):
            object.__setattr__(self, name, _hash(getattr(self, name), name, cls))
        if not isinstance(self.reason_code, str) or not self.reason_code:
            raise cls("unavailable reason_code must be nonempty")
        if not isinstance(self.detail, str) or not self.detail:
            raise cls("unavailable detail must be nonempty")
        if self.receipt_id != hash_canonical(self.identity_payload()):
            raise cls("unavailable receipt identity differs from payload")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": M2C_UNAVAILABLE_PROTOCOL,
            "revision_id": self.revision_id,
            "executable_identity": self.executable_identity,
            "provider_identity": self.provider_identity,
            "runner_identity": self.runner_identity,
            "reason_code": self.reason_code,
            "detail": self.detail,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"receipt_id": self.receipt_id, **self.identity_payload()}


def make_unavailable_revision_receipt(
    revision_id: str,
    *,
    executable_identity: str,
    provider_identity: str,
    runner_identity: str,
    reason_code: str,
    detail: str,
) -> M2CUnavailableRevisionReceipt:
    payload = {
        "protocol": M2C_UNAVAILABLE_PROTOCOL,
        "revision_id": revision_id,
        "executable_identity": executable_identity,
        "provider_identity": provider_identity,
        "runner_identity": runner_identity,
        "reason_code": reason_code,
        "detail": detail,
    }
    return M2CUnavailableRevisionReceipt(
        receipt_id=hash_canonical(payload),
        revision_id=revision_id,
        executable_identity=executable_identity,
        provider_identity=provider_identity,
        runner_identity=runner_identity,
        reason_code=reason_code,
        detail=detail,
    )


def resolve_revision_pin(
    provider: M2CRevisionProvider,
    revision: M2CRevisionIdentity,
    *,
    source_artifact: ArtifactRef | None,
    tool_artifact: ArtifactRef | None,
    runner_identity: str,
    archive: ContentAddressedArchive,
) -> M2CRevisionPin | M2CUnavailableRevisionReceipt:
    """Resolve and archive-check one explicit revision without fallback."""

    pin = M2CRevisionPin(
        revision=revision,
        source_artifact=source_artifact,
        tool_artifact=tool_artifact,
        runner_identity=runner_identity,
        available=source_artifact is not None and tool_artifact is not None,
        unavailable_reason=(
            ""
            if source_artifact is not None and tool_artifact is not None
            else "pinned_source_or_tool_missing"
        ),
    )
    try:
        resolved = _resolve_provider_revision(provider, pin.revision_id, M2CMatrixError)
    except M2CMatrixError as exc:
        return make_unavailable_revision_receipt(
            pin.revision_id,
            executable_identity=pin.executable_identity,
            provider_identity=pin.revision.provider_identity,
            runner_identity=pin.runner_identity,
            reason_code="revision_unavailable",
            detail=str(exc),
        )
    if resolved != pin.revision:
        return make_unavailable_revision_receipt(
            pin.revision_id,
            executable_identity=pin.executable_identity,
            provider_identity=pin.revision.provider_identity,
            runner_identity=pin.runner_identity,
            reason_code="revision_identity_mismatch",
            detail="provider identity differs from the exact pinned record",
        )
    if not pin.available:
        return make_unavailable_revision_receipt(
            pin.revision_id,
            executable_identity=pin.executable_identity,
            provider_identity=pin.revision.provider_identity,
            runner_identity=pin.runner_identity,
            reason_code="pinned_source_or_tool_missing",
            detail=pin.unavailable_reason,
        )
    try:
        _verify_archive(
            archive,
            pin.source_artifact,
            "pinned source",
            M2CMatrixError,
            path_prefixes=("artifacts/m2c-revision-sources/",),
        )
        _verify_archive(
            archive,
            pin.tool_artifact,
            "pinned tool",
            M2CMatrixError,
            path_prefixes=("artifacts/m2c-revision-tools/",),
        )
    except M2CMatrixError as exc:
        return make_unavailable_revision_receipt(
            pin.revision_id,
            executable_identity=pin.executable_identity,
            provider_identity=pin.revision.provider_identity,
            runner_identity=pin.runner_identity,
            reason_code="pinned_artifact_unavailable",
            detail=str(exc),
        )
    return pin


def to_generated_m2c_matrix(
    pins: Sequence[M2CRevisionPin],
) -> Any:
    """Convert qualified pins into the generated-lane matrix type lazily.

    The import is deliberately inside this helper.  The matrix module remains
    usable by provider and benchmark code without importing the lane adapter,
    while generated_lanes can consume a real typed matrix when wired by the
    root factory.
    """

    if not isinstance(pins, (tuple, list)):
        raise M2CMatrixError("generated matrix pins must be a tuple or list")
    try:
        from .search_generated_lanes import M2CRevision, M2CRevisionMatrix
    except ImportError:
        from search_generated_lanes import M2CRevision, M2CRevisionMatrix  # type: ignore
    values = []
    current_seen = False
    for pin in pins:
        if not isinstance(pin, M2CRevisionPin):
            raise M2CMatrixError("generated matrix requires typed revision pins")
        if pin.available:
            values.append(
                M2CRevision(
                    revision_identity=pin.revision,
                    source_artifact=pin.source_artifact,
                    tool_artifact=pin.tool_artifact,
                    label="current" if pin.revision_id == CURRENT_M2C_REVISION else "alternate_" + pin.revision_id[:12],
                    current=pin.revision_id == CURRENT_M2C_REVISION,
                    qualified=pin.revision_id == CURRENT_M2C_REVISION or pin.available,
                    available=True,
                )
            )
            current_seen = current_seen or pin.revision_id == CURRENT_M2C_REVISION
    if not current_seen:
        raise M2CMatrixError("generated matrix requires the pinned current revision")
    return M2CRevisionMatrix(tuple(values))


def publish_m2c_revision_matrix(
    current: M2CRevisionPin,
    alternates: Sequence[M2CRevisionPin | M2CUnavailableRevisionReceipt],
    *,
    archive: ContentAddressedArchive,
) -> tuple[tuple[M2CRevisionPin, ...], tuple[M2CUnavailableRevisionReceipt, ...]]:
    """Publish an explicit current-plus-qualified pin set.

    Missing historical vendored revisions remain typed unavailable receipts.
    They are never inserted into the qualified set or silently replaced by
    the current revision.
    """

    if not isinstance(current, M2CRevisionPin) or current.revision_id != CURRENT_M2C_REVISION:
        raise M2CMatrixError("matrix current pin must be CURRENT_M2C_REVISION")
    if not current.available:
        raise M2CMatrixError("matrix current pin is unavailable")
    _verify_archive(
        archive,
        current.source_artifact,
        "current m2c source",
        M2CMatrixError,
        path_prefixes=("artifacts/m2c-revision-sources/",),
    )
    _verify_archive(
        archive,
        current.tool_artifact,
        "current m2c tool",
        M2CMatrixError,
        path_prefixes=("artifacts/m2c-revision-tools/",),
    )
    if not isinstance(alternates, (tuple, list)):
        raise M2CMatrixError("matrix alternates must be an explicit tuple or list")
    available: list[M2CRevisionPin] = [current]
    unavailable: list[M2CUnavailableRevisionReceipt] = []
    for item in alternates:
        if isinstance(item, M2CUnavailableRevisionReceipt):
            unavailable.append(item)
            continue
        if not isinstance(item, M2CRevisionPin):
            raise M2CMatrixError("matrix alternate is not a typed pin or unavailable receipt")
        if item.revision_id == CURRENT_M2C_REVISION:
            raise M2CMatrixError("matrix repeats the current revision")
        if not item.available:
            unavailable.append(
                make_unavailable_revision_receipt(
                    item.revision_id,
                    executable_identity=item.executable_identity,
                    provider_identity=item.revision.provider_identity,
                    runner_identity=item.runner_identity,
                    reason_code="pinned_source_or_tool_missing",
                    detail=item.unavailable_reason,
                )
            )
            continue
        _verify_archive(
            archive,
            item.source_artifact,
            "alternate m2c source",
            M2CMatrixError,
            path_prefixes=("artifacts/m2c-revision-sources/",),
        )
        _verify_archive(
            archive,
            item.tool_artifact,
            "alternate m2c tool",
            M2CMatrixError,
            path_prefixes=("artifacts/m2c-revision-tools/",),
        )
        available.append(item)
    if len({item.revision_id for item in available}) != len(available):
        raise M2CMatrixError("matrix revisions must be unique")
    available = [available[0], *sorted(available[1:], key=lambda item: item.revision_id)]
    if len(available) > 3:
        raise M2CMatrixError("matrix permits at most three exact pinned revisions")
    if len(available) < 2:
        # This is an explicit current-only publication, not a qualified matrix.
        # It remains useful as a baseline but cannot be mislabeled as multi-revision.
        raise M2CUnavailableRevision(
            "no qualified alternate revision is available; current-only input is not a matrix"
        )
    payload = {
        "protocol": M2C_MATRIX_PROTOCOL + ":published",
        "pins": [item.identity_payload() for item in available],
        "unavailable": [item.to_dict() for item in unavailable],
    }
    _archive_exact(
        archive,
        payload,
        expected_identity=None,
        category="m2c-revision-matrices",
        label="published m2c revision matrix",
        exc_type=M2CMatrixError,
    )
    return tuple(available), tuple(sorted(unavailable, key=lambda item: item.revision_id))


# Descriptive aliases for future factory integration.
M2CEnsembleMatrix = M2CMatrixSpec
M2CEnsembleVariant = M2CVariant
load_matrix_receipt = load_m2c_matrix_receipt
verify_matrix_receipt = verify_m2c_matrix_receipt


__all__ = [
    "CURRENT_M2C_REVISION",
    "SUPPORTED_PLATFORMS",
    "M2C_MATRIX_PROTOCOL",
    "M2CBenchmarkError",
    "M2CMatrixError",
    "M2CProviderErrorBoundary",
    "M2CUnavailableRevision",
    "M2CBenchmarkCase",
    "M2CFixedBenchmark",
    "M2CEvaluation",
    "M2CBenchmarkReport",
    "M2CRevisionQualification",
    "M2CMatrixSpec",
    "M2CVariant",
    "M2CMatrixReceipt",
    "M2CRevisionPin",
    "M2CUnavailableRevisionReceipt",
    "make_benchmark_report",
    "make_matrix_spec",
    "qualify_revision",
    "run_fixed_benchmark",
    "enumerate_m2c_variants",
    "run_m2c_matrix",
    "verify_benchmark_report",
    "load_benchmark_report",
    "verify_m2c_matrix_receipt",
    "load_m2c_matrix_receipt",
    "replay_m2c_matrix",
    "make_unavailable_revision_receipt",
    "resolve_revision_pin",
    "to_generated_m2c_matrix",
    "publish_m2c_revision_matrix",
    "M2CEnsembleMatrix",
    "M2CEnsembleVariant",
]
