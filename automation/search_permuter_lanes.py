"""Durable proposal-only providers for the four permuter search lanes.

This module is a provider boundary, not a live permuter command.  A factory
binds an immutable manifest, archive-owned seed and target assembly, one pinned
vendored tool binding, and an isolated scratch identity.  The injected
executor receives exactly one typed request.  Every request, response,
checkpoint, stop request, and result is content addressed before it is
replayed.  No queue, checkout, source file, compiler, or checksum oracle is
read or written by this module.
"""

from __future__ import annotations

import dataclasses
import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Optional

try:
    from .search_archive import ArchiveError, ArtifactRef, ContentAddressedArchive
    from .search_lanes import Recipient
    from .search_types import (
        Budget,
        RunManifest,
        SearchValidationError,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
    )
except ImportError:  # pragma: no cover
    from search_archive import ArchiveError, ArtifactRef, ContentAddressedArchive  # type: ignore
    from search_lanes import Recipient  # type: ignore
    from search_types import (  # type: ignore
        Budget,
        RunManifest,
        SearchValidationError,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
    )


PERMUTER_RANDOM_LANE = "permuter_random"
PERMUTER_TARGETED_LANE = "permuter_targeted"
PERMUTER_RECOMBINE_LANE = "permuter_recombine"
PERMUTER_DDMIN_LANE = "permuter_ddmin"
PERMUTER_LANES = (
    PERMUTER_RANDOM_LANE,
    PERMUTER_TARGETED_LANE,
    PERMUTER_RECOMBINE_LANE,
    PERMUTER_DDMIN_LANE,
)
PERMUTER_PROVIDER_PROTOCOL = "sotn-permuter-provider-v1"
PERMUTER_INPUT_PROTOCOL = "sotn-permuter-input-v1"
PERMUTER_CONFIG_PROTOCOL = "sotn-permuter-config-v1"
PERMUTER_BINDING_PROTOCOL = "sotn-permuter-tool-binding-v1"
PERMUTER_REQUEST_PROTOCOL = "sotn-permuter-request-v1"
PERMUTER_RESPONSE_PROTOCOL = "sotn-permuter-response-v1"
PERMUTER_CHECKPOINT_PROTOCOL = "sotn-permuter-checkpoint-v1"
PERMUTER_RESULT_PROTOCOL = "sotn-permuter-result-v1"
PERMUTER_STOP_PROTOCOL = "sotn-permuter-stop-v1"
PERMUTER_SCRATCH_PROTOCOL = "sotn-permuter-scratch-v1"
PERMUTER_EVALUATOR_PROTOCOL = "sotn-permuter-evaluator-v1"
PERMUTER_REQUEST_CATEGORY = "permuter-requests"
PERMUTER_RESPONSE_CATEGORY = "permuter-responses"
PERMUTER_CHECKPOINT_CATEGORY = "permuter-checkpoints"
PERMUTER_RESULT_CATEGORY = "permuter-results"
PERMUTER_STOP_CATEGORY = "permuter-stops"
PERMUTER_MAX_CALLS = 4
PERMUTER_MAX_ITERATIONS = 100000
PERMUTER_MAX_CANDIDATES = 32
PERMUTER_MAX_STATE_BYTES = 1048576
PERMUTER_MAX_CANDIDATE_CHARS = 65536
MODULE_IDENTITY = hash_canonical(
    {
        "module": "automation.search_permuter_lanes",
        "protocol": PERMUTER_PROVIDER_PROTOCOL,
        "version": "1.0.0",
    }
)

_STATUS_CODES = frozenset(
    {
        "completed",
        "stopped",
        "unavailable",
        "refused",
        "timeout",
        "invalid_response",
        "handoff_pending",
    }
)
_FAILURE_CODES = frozenset({"unavailable", "refused", "timeout", "invalid_response"})
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
_PHASES = frozenset({"start", "resume"})
_CANDIDATE_SOURCE_RE = re.compile(r"^\s*(?:candidate|proposal)\s*:\s*(.+?)\s*$", re.IGNORECASE)


class PermuterProviderError(RuntimeError):
    """Base class for typed permuter provider failures."""


class PermuterProviderInputError(PermuterProviderError):
    """An immutable input, binding, budget, or serialized record is invalid."""


class PermuterProviderUnavailable(PermuterProviderError):
    """The pinned vendored tool or executor is unavailable."""

    code = "permuter_provider_unavailable"

    def __init__(self, reason: str = "permuter provider unavailable") -> None:
        super().__init__(reason)


class PermuterProviderRefused(PermuterProviderError):
    """The pinned provider refused the request."""

    code = "permuter_provider_refused"

    def __init__(self, reason: str = "permuter provider refused request", code: Optional[str] = None) -> None:
        super().__init__(reason)
        if code:
            self.code = code


class PermuterProviderTimeout(PermuterProviderError):
    """The bounded provider call timed out."""

    code = "permuter_provider_timeout"

    def __init__(self, reason: str = "permuter provider timed out") -> None:
        super().__init__(reason)


class PermuterProviderInvalidResponse(PermuterProviderError):
    """The executor returned data outside its documented callback shape."""

    code = "permuter_invalid_response"

    def __init__(self, reason: str = "permuter provider response is invalid") -> None:
        super().__init__(reason)


class PermuterProviderHandoffPending(PermuterProviderError):
    """A durable request has no response and must not be invoked again."""

    code = "permuter_handoff_pending"

    def __init__(self, reason: str = "permuter handoff is pending") -> None:
        super().__init__(reason)


class PermuterProviderHandoffError(PermuterProviderError):
    """A request, response, checkpoint, stop, or result was not durable."""


ProviderUnavailable = PermuterProviderUnavailable
ProviderRefused = PermuterProviderRefused
ProviderTimeout = PermuterProviderTimeout
ProviderInvalidResponse = PermuterProviderInvalidResponse
ProviderHandoffPending = PermuterProviderHandoffPending


def _plain(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if dataclasses.is_dataclass(value):
        return {
            item.name: _plain(getattr(value, item.name))
            for item in dataclasses.fields(value)
        }
    return value


def _freeze_json(value: Any, label: str) -> Any:
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise PermuterProviderInputError(f"{label} keys must be strings")
            frozen[key] = _freeze_json(item, f"{label}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (tuple, list)):
        return tuple(
            _freeze_json(item, f"{label}[{index}]")
            for index, item in enumerate(value)
        )
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PermuterProviderInputError(f"{label} contains a non-finite number")
        return value
    raise PermuterProviderInputError(f"{label} must contain JSON values")


def _identity(value: Any, label: str) -> str:
    try:
        return validate_hash(value, label)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise PermuterProviderInputError(f"{label} must be a sha256 identity") from exc


def _identifier(value: Any, label: str) -> str:
    try:
        return validate_id(value, label)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise PermuterProviderInputError(f"{label} must be an identifier") from exc


def _text(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        raise PermuterProviderInputError(f"{label} must be nonempty text")
    return value


def _integer(value: Any, label: str, minimum: int = 0, maximum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PermuterProviderInputError(f"{label} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        raise PermuterProviderInputError(f"{label} is outside its bound")
    return value


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PermuterProviderInputError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise PermuterProviderInputError(f"{label} must be finite")
    return result


def _artifact(value: Any, label: str) -> ArtifactRef:
    if isinstance(value, ArtifactRef):
        return value
    try:
        return ArtifactRef.from_dict(value)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise PermuterProviderInputError(f"{label} must be an ArtifactRef") from exc


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PermuterProviderInputError(f"{label} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise PermuterProviderInputError(f"{label} keys must be strings")
    return value


def _strict(
    value: Any,
    required: Sequence[str],
    optional: Sequence[str],
    label: str,
) -> dict[str, Any]:
    data = dict(_mapping(value, label))
    required_set = set(required)
    optional_set = set(optional)
    missing = required_set.difference(data)
    unknown = set(data).difference(required_set | optional_set)
    if missing:
        raise PermuterProviderInputError(
            f"{label} is missing fields: " + ", ".join(sorted(missing))
        )
    if unknown:
        raise PermuterProviderInputError(
            f"{label} has unknown fields: " + ", ".join(sorted(unknown))
        )
    return data


def _artifact_identity(ref: ArtifactRef) -> dict[str, Any]:
    return {
        "content_hash": ref.content_hash,
        "path": Path(ref.path).as_posix(),
        "media_type": ref.media_type,
        "byte_size": ref.byte_size,
    }


def _canonical_path(root: Path, relative: str) -> str:
    candidate = root / Path(relative)
    try:
        resolved_root = root.resolve(strict=False)
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise PermuterProviderInputError("derived scratch path escaped run root") from exc
    return resolved.relative_to(resolved_root).as_posix()


@dataclass(frozen=True)
class ArchivedPermuterInput:
    """One archive-owned C seed and target assembly snapshot."""

    recipient_id: str
    target_identity: str
    seed_artifact: ArtifactRef
    seed_source: str
    target_artifact: ArtifactRef
    target_assembly: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "recipient_id", _identifier(self.recipient_id, "recipient_id"))
        object.__setattr__(self, "target_identity", _identity(self.target_identity, "target_identity"))
        object.__setattr__(self, "seed_artifact", _artifact(self.seed_artifact, "seed_artifact"))
        object.__setattr__(self, "target_artifact", _artifact(self.target_artifact, "target_artifact"))
        object.__setattr__(self, "seed_source", _text(self.seed_source, "seed_source"))
        object.__setattr__(self, "target_assembly", _text(self.target_assembly, "target_assembly"))
        object.__setattr__(self, "metadata", _freeze_json(self.metadata, "metadata"))

    @property
    def seed_identity(self) -> str:
        return self.seed_artifact.content_hash

    @property
    def target_artifact_identity(self) -> str:
        return self.target_artifact.content_hash

    @property
    def metadata_identity(self) -> str:
        return hash_canonical(_plain(self.metadata))

    @property
    def input_identity(self) -> str:
        return hash_canonical(
            {
                "protocol": PERMUTER_INPUT_PROTOCOL,
                "recipient_id": self.recipient_id,
                "target_identity": self.target_identity,
                "seed_identity": self.seed_identity,
                "target_artifact_identity": self.target_artifact_identity,
                "metadata_identity": self.metadata_identity,
            }
        )

    @property
    def seed(self) -> str:
        return self.seed_source

    @property
    def target(self) -> str:
        return self.target_assembly

    def verify(self, archive: ContentAddressedArchive) -> None:
        if not isinstance(archive, ContentAddressedArchive):
            raise PermuterProviderInputError("permuter input needs a ContentAddressedArchive")
        try:
            seed_bytes = archive.verify(self.seed_artifact)
            target_bytes = archive.verify(self.target_artifact)
        except ArchiveError as exc:
            raise PermuterProviderInputError(
                f"archived permuter input could not be verified for {self.recipient_id}"
            ) from exc
        if seed_bytes != self.seed_source.encode("utf-8"):
            raise PermuterProviderInputError("seed bytes differ from archived seed artifact")
        if target_bytes != self.target_assembly.encode("utf-8"):
            raise PermuterProviderInputError("target bytes differ from archived target artifact")

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": PERMUTER_INPUT_PROTOCOL,
            "recipient_id": self.recipient_id,
            "target_identity": self.target_identity,
            "seed_artifact": _artifact_identity(self.seed_artifact),
            "seed_source": self.seed_source,
            "target_artifact": _artifact_identity(self.target_artifact),
            "target_assembly": self.target_assembly,
            "metadata": _plain(self.metadata),
            "seed_identity": self.seed_identity,
            "target_artifact_identity": self.target_artifact_identity,
            "metadata_identity": self.metadata_identity,
            "input_identity": self.input_identity,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ArchivedPermuterInput":
        data = _strict(
            value,
            (
                "protocol",
                "recipient_id",
                "target_identity",
                "seed_artifact",
                "seed_source",
                "target_artifact",
                "target_assembly",
                "metadata",
                "seed_identity",
                "target_artifact_identity",
                "metadata_identity",
                "input_identity",
            ),
            (),
            "archived permuter input",
        )
        if data["protocol"] != PERMUTER_INPUT_PROTOCOL:
            raise PermuterProviderInputError("permuter input protocol differs")
        item = cls(
            recipient_id=data["recipient_id"],
            target_identity=data["target_identity"],
            seed_artifact=_artifact(data["seed_artifact"], "seed_artifact"),
            seed_source=data["seed_source"],
            target_artifact=_artifact(data["target_artifact"], "target_artifact"),
            target_assembly=data["target_assembly"],
            metadata=data["metadata"],
        )
        if data["seed_identity"] != item.seed_identity:
            raise PermuterProviderInputError("seed identity changed")
        if data["target_artifact_identity"] != item.target_artifact_identity:
            raise PermuterProviderInputError("target artifact identity changed")
        if data["metadata_identity"] != item.metadata_identity:
            raise PermuterProviderInputError("metadata identity changed")
        if data["input_identity"] != item.input_identity:
            raise PermuterProviderInputError("permuter input identity changed")
        return item


PermuterInput = ArchivedPermuterInput
PermuterSeedInput = ArchivedPermuterInput


@dataclass(frozen=True)
class PermuterToolBinding:
    """Pinned vendored tool, weight table, and algorithm identities."""

    lane: str
    vendor_revision: str
    algorithm: str
    tool_artifact: Optional[ArtifactRef] = None
    tool_bytes: Optional[bytes] = None
    weights_artifact: Optional[ArtifactRef] = None
    weights_bytes: Optional[bytes] = None
    algorithm_identity: Optional[str] = None
    available: bool = True
    unavailable_reason: str = ""

    def __post_init__(self) -> None:
        if self.lane not in PERMUTER_LANES:
            raise PermuterProviderInputError("unsupported permuter binding lane")
        object.__setattr__(self, "vendor_revision", _identity(self.vendor_revision, "vendor_revision"))
        object.__setattr__(self, "algorithm", _text(self.algorithm, "algorithm"))
        if self.tool_artifact is not None:
            object.__setattr__(self, "tool_artifact", _artifact(self.tool_artifact, "tool_artifact"))
        if self.weights_artifact is not None:
            object.__setattr__(self, "weights_artifact", _artifact(self.weights_artifact, "weights_artifact"))
        if self.tool_bytes is not None and not isinstance(self.tool_bytes, bytes):
            raise PermuterProviderInputError("tool_bytes must be bytes")
        if self.weights_bytes is not None and not isinstance(self.weights_bytes, bytes):
            raise PermuterProviderInputError("weights_bytes must be bytes")
        if self.tool_artifact is not None and self.tool_bytes is not None:
            if hash_bytes(self.tool_bytes) != self.tool_artifact.content_hash:
                raise PermuterProviderInputError("tool bytes differ from pinned artifact")
            if len(self.tool_bytes) != self.tool_artifact.byte_size:
                raise PermuterProviderInputError("tool byte size differs from pinned artifact")
        if self.weights_artifact is not None and self.weights_bytes is not None:
            if hash_bytes(self.weights_bytes) != self.weights_artifact.content_hash:
                raise PermuterProviderInputError("weights bytes differ from pinned artifact")
            if len(self.weights_bytes) != self.weights_artifact.byte_size:
                raise PermuterProviderInputError("weights byte size differs from pinned artifact")
        if self.algorithm_identity is None:
            object.__setattr__(
                self,
                "algorithm_identity",
                hash_canonical(
                    {
                        "protocol": PERMUTER_BINDING_PROTOCOL,
                        "lane": self.lane,
                        "algorithm": self.algorithm,
                    }
                ),
            )
        else:
            object.__setattr__(self, "algorithm_identity", _identity(self.algorithm_identity, "algorithm_identity"))
        object.__setattr__(self, "unavailable_reason", _text(self.unavailable_reason, "unavailable_reason", allow_empty=True))
        if self.available and (
            self.tool_artifact is None
            or self.tool_bytes is None
            or self.weights_artifact is None
            or self.weights_bytes is None
        ):
            raise PermuterProviderUnavailable(
                "available binding needs archive-owned tool and weights bytes"
            )

    @property
    def tool_identity(self) -> str:
        if self.tool_artifact is not None:
            return self.tool_artifact.content_hash
        return hash_canonical(
            {
                "protocol": PERMUTER_BINDING_PROTOCOL,
                "kind": "tool-unavailable",
                "lane": self.lane,
            }
        )

    @property
    def weights_identity(self) -> str:
        if self.weights_artifact is not None:
            return self.weights_artifact.content_hash
        return hash_canonical(
            {
                "protocol": PERMUTER_BINDING_PROTOCOL,
                "kind": "weights-unavailable",
                "lane": self.lane,
            }
        )

    @property
    def identity(self) -> str:
        return hash_canonical(self._identity_payload())

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": PERMUTER_BINDING_PROTOCOL,
            "lane": self.lane,
            "vendor_revision": self.vendor_revision,
            "algorithm": self.algorithm,
            "algorithm_identity": self.algorithm_identity,
            "tool_artifact": (
                _artifact_identity(self.tool_artifact)
                if self.tool_artifact is not None else None
            ),
            "weights_artifact": (
                _artifact_identity(self.weights_artifact)
                if self.weights_artifact is not None else None
            ),
            "tool_identity": self.tool_identity,
            "weights_identity": self.weights_identity,
            "available": self.available,
            "unavailable_reason": self.unavailable_reason,
        }

    def verify(self, archive: ContentAddressedArchive) -> None:
        if not self.available:
            raise PermuterProviderUnavailable(
                self.unavailable_reason or "pinned permuter binding is unavailable"
            )
        if self.tool_artifact is None or self.tool_bytes is None:
            raise PermuterProviderUnavailable("pinned tool artifact is unavailable")
        if self.weights_artifact is None or self.weights_bytes is None:
            raise PermuterProviderUnavailable("pinned weights artifact is unavailable")
        try:
            tool = archive.verify(self.tool_artifact)
            weights = archive.verify(self.weights_artifact)
        except ArchiveError as exc:
            raise PermuterProviderUnavailable(
                "pinned tool or weights artifact is absent or corrupt"
            ) from exc
        if tool != self.tool_bytes or weights != self.weights_bytes:
            raise PermuterProviderInputError("pinned tool or weights bytes changed")

    def to_dict(self) -> dict[str, Any]:
        return dict(
            self._identity_payload(),
            binding_identity=self.identity,
        )

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        archive: Optional[ContentAddressedArchive] = None,
    ) -> "PermuterToolBinding":
        data = _strict(
            value,
            ("protocol", "lane", "vendor_revision", "algorithm", "available"),
            (
                "algorithm_identity",
                "tool_artifact",
                "weights_artifact",
                "tool_identity",
                "weights_identity",
                "unavailable_reason",
                "binding_identity",
            ),
            "permuter tool binding",
        )
        if data["protocol"] != PERMUTER_BINDING_PROTOCOL:
            raise PermuterProviderInputError("binding protocol differs")
        tool_artifact = (
            _artifact(data["tool_artifact"], "tool_artifact")
            if data.get("tool_artifact") is not None else None
        )
        weights_artifact = (
            _artifact(data["weights_artifact"], "weights_artifact")
            if data.get("weights_artifact") is not None else None
        )
        tool_bytes: Optional[bytes] = None
        weights_bytes: Optional[bytes] = None
        if data["available"]:
            if not isinstance(archive, ContentAddressedArchive):
                raise PermuterProviderUnavailable(
                    "available binding reconstruction needs its archive"
                )
            if tool_artifact is None or weights_artifact is None:
                raise PermuterProviderUnavailable(
                    "available binding has no pinned tool or weights artifact"
                )
            try:
                tool_bytes = archive.verify(tool_artifact)
                weights_bytes = archive.verify(weights_artifact)
            except ArchiveError as exc:
                raise PermuterProviderUnavailable(
                    "pinned tool or weights artifact is absent or corrupt"
                ) from exc
        item = cls(
            lane=data["lane"],
            vendor_revision=data["vendor_revision"],
            algorithm=data["algorithm"],
            tool_artifact=tool_artifact,
            tool_bytes=tool_bytes,
            weights_artifact=weights_artifact,
            weights_bytes=weights_bytes,
            algorithm_identity=data.get("algorithm_identity"),
            available=data["available"],
            unavailable_reason=data.get("unavailable_reason", ""),
        )
        if "tool_identity" in data and data["tool_identity"] != item.tool_identity:
            raise PermuterProviderInputError("tool identity changed")
        if "weights_identity" in data and data["weights_identity"] != item.weights_identity:
            raise PermuterProviderInputError("weights identity changed")
        if "binding_identity" in data and data["binding_identity"] != item.identity:
            raise PermuterProviderInputError("binding identity changed")
        return item



@dataclass(frozen=True)
class PermuterLaneConfig:
    """Immutable lane algorithm and bounded execution configuration."""

    lane: str
    algorithm: str
    max_calls: int = 2
    max_iterations: int = 256
    max_candidates: int = 8
    checkpoint_interval: int = 1
    evaluator_identity: Optional[str] = None

    def __post_init__(self) -> None:
        if self.lane not in PERMUTER_LANES:
            raise PermuterProviderInputError("unsupported permuter lane")
        object.__setattr__(self, "algorithm", _text(self.algorithm, "algorithm"))
        _integer(self.max_calls, "max_calls", 1, PERMUTER_MAX_CALLS)
        _integer(self.max_iterations, "max_iterations", 1, PERMUTER_MAX_ITERATIONS)
        _integer(self.max_candidates, "max_candidates", 1, PERMUTER_MAX_CANDIDATES)
        _integer(self.checkpoint_interval, "checkpoint_interval", 1, self.max_iterations)
        if self.evaluator_identity is None:
            object.__setattr__(
                self,
                "evaluator_identity",
                hash_canonical(
                    {
                        "protocol": PERMUTER_EVALUATOR_PROTOCOL,
                        "lane": self.lane,
                        "mode": "proposal_only",
                    }
                ),
            )
        else:
            object.__setattr__(self, "evaluator_identity", _identity(self.evaluator_identity, "evaluator_identity"))

    @property
    def algorithm_identity(self) -> str:
        return hash_canonical(
            {
                "protocol": PERMUTER_CONFIG_PROTOCOL,
                "lane": self.lane,
                "algorithm": self.algorithm,
            }
        )

    @property
    def identity(self) -> str:
        return hash_canonical(self._identity_payload())

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": PERMUTER_CONFIG_PROTOCOL,
            "lane": self.lane,
            "algorithm": self.algorithm,
            "algorithm_identity": self.algorithm_identity,
            "max_calls": self.max_calls,
            "max_iterations": self.max_iterations,
            "max_candidates": self.max_candidates,
            "checkpoint_interval": self.checkpoint_interval,
            "evaluator_identity": self.evaluator_identity,
        }

    def to_dict(self) -> dict[str, Any]:
        return dict(self._identity_payload(), config_identity=self.identity)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PermuterLaneConfig":
        data = _strict(
            value,
            ("protocol", "lane", "algorithm"),
            (
                "max_calls",
                "max_iterations",
                "max_candidates",
                "checkpoint_interval",
                "evaluator_identity",
                "algorithm_identity",
                "config_identity",
            ),
            "permuter lane config",
        )
        if data["protocol"] != PERMUTER_CONFIG_PROTOCOL:
            raise PermuterProviderInputError("config protocol differs")
        item = cls(
            lane=data["lane"],
            algorithm=data["algorithm"],
            max_calls=data.get("max_calls", 2),
            max_iterations=data.get("max_iterations", 256),
            max_candidates=data.get("max_candidates", 8),
            checkpoint_interval=data.get("checkpoint_interval", 1),
            evaluator_identity=data.get("evaluator_identity"),
        )
        if "algorithm_identity" in data and data["algorithm_identity"] != item.algorithm_identity:
            raise PermuterProviderInputError("algorithm identity changed")
        if "config_identity" in data and data["config_identity"] != item.identity:
            raise PermuterProviderInputError("config identity changed")
        return item


@dataclass(frozen=True)
class PermuterBudget:
    """Immutable call, iteration, and unique-candidate budget."""

    max_calls: int
    max_iterations: int
    max_candidates: int
    calls_consumed: int = 0
    iterations_consumed: int = 0
    candidates_consumed: int = 0

    def __post_init__(self) -> None:
        _integer(self.max_calls, "budget.max_calls", 1, PERMUTER_MAX_CALLS)
        _integer(self.max_iterations, "budget.max_iterations", 1, PERMUTER_MAX_ITERATIONS)
        _integer(self.max_candidates, "budget.max_candidates", 1, PERMUTER_MAX_CANDIDATES)
        _integer(self.calls_consumed, "budget.calls_consumed", 0, self.max_calls)
        _integer(self.iterations_consumed, "budget.iterations_consumed", 0, self.max_iterations)
        _integer(self.candidates_consumed, "budget.candidates_consumed", 0, self.max_candidates)

    @property
    def identity(self) -> str:
        return hash_canonical(
            {
                "protocol": "sotn-permuter-budget-v1",
                "max_calls": self.max_calls,
                "max_iterations": self.max_iterations,
                "max_candidates": self.max_candidates,
            }
        )

    @property
    def consumed_identity(self) -> str:
        return hash_canonical(
            {
                "protocol": "sotn-permuter-budget-consumption-v1",
                "max_calls": self.max_calls,
                "max_iterations": self.max_iterations,
                "max_candidates": self.max_candidates,
                "calls_consumed": self.calls_consumed,
                "iterations_consumed": self.iterations_consumed,
                "candidates_consumed": self.candidates_consumed,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_calls": self.max_calls,
            "max_iterations": self.max_iterations,
            "max_candidates": self.max_candidates,
            "calls_consumed": self.calls_consumed,
            "iterations_consumed": self.iterations_consumed,
            "candidates_consumed": self.candidates_consumed,
            "budget_identity": self.identity,
            "consumed_identity": self.consumed_identity,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PermuterBudget":
        data = _strict(
            value,
            (
                "max_calls",
                "max_iterations",
                "max_candidates",
                "calls_consumed",
                "iterations_consumed",
                "candidates_consumed",
            ),
            ("budget_identity", "consumed_identity"),
            "permuter budget",
        )
        item = cls(
            max_calls=data["max_calls"],
            max_iterations=data["max_iterations"],
            max_candidates=data["max_candidates"],
            calls_consumed=data["calls_consumed"],
            iterations_consumed=data["iterations_consumed"],
            candidates_consumed=data["candidates_consumed"],
        )
        if data.get("budget_identity", item.identity) != item.identity:
            raise PermuterProviderInputError("budget identity changed")
        if data.get("consumed_identity", item.consumed_identity) != item.consumed_identity:
            raise PermuterProviderInputError("budget consumption identity changed")
        return item


def default_permuter_config(lane: str) -> PermuterLaneConfig:
    algorithms = {
        PERMUTER_RANDOM_LANE: "random",
        PERMUTER_TARGETED_LANE: "targeted",
        PERMUTER_RECOMBINE_LANE: "recombine",
        PERMUTER_DDMIN_LANE: "ddmin",
    }
    if lane not in algorithms:
        raise PermuterProviderInputError("unsupported permuter lane")
    return PermuterLaneConfig(lane=lane, algorithm=algorithms[lane])


@dataclass(frozen=True)
class PermuterRequest:
    """The sole documented executor callback argument."""

    lane: str
    phase: str
    recipient_id: str
    target_identity: str
    manifest_identity: str
    provider_identity: str
    config_identity: str
    evaluator_identity: str
    vendor_revision: str
    tool_identity: str
    weights_identity: str
    algorithm: str
    algorithm_identity: str
    session_identity: str
    idempotency_key: str
    request_identity: str
    seed_artifact: ArtifactRef
    target_artifact: ArtifactRef
    seed_identity: str
    target_artifact_identity: str
    input_identity: str
    scratch_identity: str
    scratch_path: str
    seed_source: str
    target_assembly: str
    start_iteration: int
    prior_checkpoint_identity: Optional[str]
    max_calls: int
    max_iterations: int
    max_candidates: int
    checkpoint_interval: int

    def __post_init__(self) -> None:
        if self.lane not in PERMUTER_LANES:
            raise PermuterProviderInputError("request lane is invalid")
        if self.phase not in _PHASES:
            raise PermuterProviderInputError("request phase is invalid")
        object.__setattr__(self, "recipient_id", _identifier(self.recipient_id, "recipient_id"))
        for name in (
            "target_identity",
            "manifest_identity",
            "provider_identity",
            "config_identity",
            "evaluator_identity",
            "vendor_revision",
            "tool_identity",
            "weights_identity",
            "algorithm_identity",
            "session_identity",
            "idempotency_key",
            "request_identity",
            "seed_identity",
            "target_artifact_identity",
            "input_identity",
            "scratch_identity",
        ):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        object.__setattr__(self, "seed_artifact", _artifact(self.seed_artifact, "seed_artifact"))
        object.__setattr__(self, "target_artifact", _artifact(self.target_artifact, "target_artifact"))
        for name in ("algorithm", "scratch_path", "seed_source", "target_assembly"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        _integer(self.start_iteration, "start_iteration", 0, PERMUTER_MAX_ITERATIONS)
        if self.prior_checkpoint_identity is not None:
            object.__setattr__(
                self,
                "prior_checkpoint_identity",
                _identity(self.prior_checkpoint_identity, "prior_checkpoint_identity"),
            )
        _integer(self.max_calls, "max_calls", 1, PERMUTER_MAX_CALLS)
        _integer(self.max_iterations, "max_iterations", 1, PERMUTER_MAX_ITERATIONS)
        _integer(self.max_candidates, "max_candidates", 1, PERMUTER_MAX_CANDIDATES)
        _integer(self.checkpoint_interval, "checkpoint_interval", 1, self.max_iterations)
        expected_key = hash_canonical(self.identity_payload())
        if self.idempotency_key != expected_key:
            raise PermuterProviderInputError("request idempotency key changed")
        expected_identity = hash_canonical(
            {
                "protocol": PERMUTER_REQUEST_PROTOCOL,
                "idempotency_key": self.idempotency_key,
                "payload": self.identity_payload(),
            }
        )
        if self.request_identity != expected_identity:
            raise PermuterProviderInputError("request identity changed")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "phase": self.phase,
            "recipient_id": self.recipient_id,
            "target_identity": self.target_identity,
            "manifest_identity": self.manifest_identity,
            "provider_identity": self.provider_identity,
            "config_identity": self.config_identity,
            "evaluator_identity": self.evaluator_identity,
            "vendor_revision": self.vendor_revision,
            "tool_identity": self.tool_identity,
            "weights_identity": self.weights_identity,
            "algorithm": self.algorithm,
            "algorithm_identity": self.algorithm_identity,
            "session_identity": self.session_identity,
            "seed_artifact": _artifact_identity(self.seed_artifact),
            "target_artifact": _artifact_identity(self.target_artifact),
            "seed_identity": self.seed_identity,
            "target_artifact_identity": self.target_artifact_identity,
            "input_identity": self.input_identity,
            "scratch_identity": self.scratch_identity,
            "scratch_path": self.scratch_path,
            "seed_source": self.seed_source,
            "target_assembly": self.target_assembly,
            "start_iteration": self.start_iteration,
            "prior_checkpoint_identity": self.prior_checkpoint_identity,
            "max_calls": self.max_calls,
            "max_iterations": self.max_iterations,
            "max_candidates": self.max_candidates,
            "checkpoint_interval": self.checkpoint_interval,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": PERMUTER_REQUEST_PROTOCOL,
            "idempotency_key": self.idempotency_key,
            "request_identity": self.request_identity,
            **self.identity_payload(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PermuterRequest":
        data = _strict(
            value,
            (
                "protocol",
                "idempotency_key",
                "request_identity",
                "lane",
                "phase",
                "recipient_id",
                "target_identity",
                "manifest_identity",
                "provider_identity",
                "config_identity",
                "evaluator_identity",
                "vendor_revision",
                "tool_identity",
                "weights_identity",
                "algorithm",
                "algorithm_identity",
                "session_identity",
                "seed_artifact",
                "target_artifact",
                "seed_identity",
                "target_artifact_identity",
                "input_identity",
                "scratch_identity",
                "scratch_path",
                "seed_source",
                "target_assembly",
                "start_iteration",
                "prior_checkpoint_identity",
                "max_calls",
                "max_iterations",
                "max_candidates",
                "checkpoint_interval",
            ),
            (),
            "permuter request",
        )
        if data["protocol"] != PERMUTER_REQUEST_PROTOCOL:
            raise PermuterProviderInputError("request protocol differs")
        return cls(
            lane=data["lane"],
            phase=data["phase"],
            recipient_id=data["recipient_id"],
            target_identity=data["target_identity"],
            manifest_identity=data["manifest_identity"],
            provider_identity=data["provider_identity"],
            config_identity=data["config_identity"],
            evaluator_identity=data["evaluator_identity"],
            vendor_revision=data["vendor_revision"],
            tool_identity=data["tool_identity"],
            weights_identity=data["weights_identity"],
            algorithm=data["algorithm"],
            algorithm_identity=data["algorithm_identity"],
            session_identity=data["session_identity"],
            idempotency_key=data["idempotency_key"],
            request_identity=data["request_identity"],
            seed_artifact=_artifact(data["seed_artifact"], "seed_artifact"),
            target_artifact=_artifact(data["target_artifact"], "target_artifact"),
            seed_identity=data["seed_identity"],
            target_artifact_identity=data["target_artifact_identity"],
            input_identity=data["input_identity"],
            scratch_identity=data["scratch_identity"],
            scratch_path=data["scratch_path"],
            seed_source=data["seed_source"],
            target_assembly=data["target_assembly"],
            start_iteration=data["start_iteration"],
            prior_checkpoint_identity=data["prior_checkpoint_identity"],
            max_calls=data["max_calls"],
            max_iterations=data["max_iterations"],
            max_candidates=data["max_candidates"],
            checkpoint_interval=data["checkpoint_interval"],
        )


@dataclass(frozen=True)
class PermuterRawCandidate:
    source: str
    score: Optional[float] = None
    iteration: int = 0
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _text(self.source, "candidate source"))
        if len(self.source.encode("utf-8")) > PERMUTER_MAX_CANDIDATE_CHARS:
            raise PermuterProviderInvalidResponse("candidate source exceeds bound")
        if self.score is not None:
            object.__setattr__(self, "score", _number(self.score, "candidate score"))
        object.__setattr__(self, "iteration", _integer(self.iteration, "candidate iteration", 0, PERMUTER_MAX_ITERATIONS))
        object.__setattr__(self, "provenance", _freeze_json(self.provenance, "candidate provenance"))

    @property
    def candidate_id(self) -> str:
        return hash_bytes(self.source.encode("utf-8"))

    def key(self) -> tuple[Any, ...]:
        return (
            self.score is None,
            self.score if self.score is not None else 0.0,
            self.iteration,
            json.dumps(_plain(self.provenance), sort_keys=True, ensure_ascii=False, separators=(",", ":")),
            self.source,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source": self.source,
            "score": self.score,
            "iteration": self.iteration,
            "provenance": _plain(self.provenance),
        }


@dataclass(frozen=True)
class PermuterCheckpoint:
    """Checksummed serialized state used for stop and resume."""

    lane: str
    phase: str
    session_identity: str
    request_identity: str
    scratch_identity: str
    iterations: int
    candidates: tuple[PermuterRawCandidate, ...]
    state: Mapping[str, Any]
    stopped: bool
    stop_reason: str
    checkpoint_identity: str

    def __post_init__(self) -> None:
        if self.lane not in PERMUTER_LANES or self.phase not in _PHASES:
            raise PermuterProviderInputError("checkpoint lane or phase is invalid")
        for name in ("session_identity", "request_identity", "scratch_identity", "checkpoint_identity"):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        _integer(self.iterations, "checkpoint iterations", 0, PERMUTER_MAX_ITERATIONS)
        candidates = tuple(self.candidates)
        if any(not isinstance(item, PermuterRawCandidate) for item in candidates):
            raise PermuterProviderInputError("checkpoint candidates must be typed")
        if tuple(item.candidate_id for item in candidates) != tuple(
            sorted(item.candidate_id for item in candidates)
        ):
            raise PermuterProviderInputError("checkpoint candidates must be canonical")
        if len({item.candidate_id for item in candidates}) != len(candidates):
            raise PermuterProviderInputError("checkpoint candidates must be unique")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "state", _freeze_json(self.state, "checkpoint state"))
        if not isinstance(self.state, Mapping):
            raise PermuterProviderInputError("checkpoint state must be an object")
        if len(canonical_bytes(self.state)) > PERMUTER_MAX_STATE_BYTES:
            raise PermuterProviderInputError("checkpoint state exceeds bound")
        object.__setattr__(self, "stop_reason", _text(self.stop_reason, "stop_reason", allow_empty=True))
        expected = hash_canonical(self.identity_payload())
        if self.checkpoint_identity != expected:
            raise PermuterProviderInputError("checkpoint identity changed")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": PERMUTER_CHECKPOINT_PROTOCOL,
            "lane": self.lane,
            "phase": self.phase,
            "session_identity": self.session_identity,
            "request_identity": self.request_identity,
            "scratch_identity": self.scratch_identity,
            "iterations": self.iterations,
            "candidates": [item.to_dict() for item in self.candidates],
            "state": _plain(self.state),
            "stopped": self.stopped,
            "stop_reason": self.stop_reason,
        }

    def to_dict(self) -> dict[str, Any]:
        return dict(self.identity_payload(), checkpoint_identity=self.checkpoint_identity)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PermuterCheckpoint":
        data = _strict(
            value,
            (
                "protocol",
                "lane",
                "phase",
                "session_identity",
                "request_identity",
                "scratch_identity",
                "iterations",
                "candidates",
                "state",
                "stopped",
                "stop_reason",
                "checkpoint_identity",
            ),
            (),
            "permuter checkpoint",
        )
        if data["protocol"] != PERMUTER_CHECKPOINT_PROTOCOL:
            raise PermuterProviderInputError("checkpoint protocol differs")
        candidates = tuple(
            PermuterRawCandidate(
                source=item["source"],
                score=item.get("score"),
                iteration=item.get("iteration", 0),
                provenance=item.get("provenance", {}),
            )
            for item in data["candidates"]
        )
        return cls(
            lane=data["lane"],
            phase=data["phase"],
            session_identity=data["session_identity"],
            request_identity=data["request_identity"],
            scratch_identity=data["scratch_identity"],
            iterations=data["iterations"],
            candidates=candidates,
            state=data["state"],
            stopped=data["stopped"],
            stop_reason=data["stop_reason"],
            checkpoint_identity=data["checkpoint_identity"],
        )


@dataclass(frozen=True)
class PermuterCandidate:
    """A deterministic proposal with full tool and checkpoint provenance."""

    candidate_id: str
    source: str
    provenance: Mapping[str, Any]
    input_identity: str
    score: Optional[float] = None
    iteration: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _identity(self.candidate_id, "candidate_id"))
        object.__setattr__(self, "source", _text(self.source, "candidate source"))
        if hash_bytes(self.source.encode("utf-8")) != self.candidate_id:
            raise PermuterProviderInputError("candidate identity differs from source bytes")
        object.__setattr__(self, "input_identity", _identity(self.input_identity, "candidate input identity"))
        if self.score is not None:
            object.__setattr__(self, "score", _number(self.score, "candidate score"))
        object.__setattr__(self, "iteration", _integer(self.iteration, "candidate iteration", 0, PERMUTER_MAX_ITERATIONS))
        object.__setattr__(self, "provenance", _freeze_json(self.provenance, "candidate provenance"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source": self.source,
            "provenance": _plain(self.provenance),
            "input_identity": self.input_identity,
            "score": self.score,
            "iteration": self.iteration,
        }

    def to_mapping(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "provenance": _plain(self.provenance),
        }


@dataclass(frozen=True)
class PermuterProviderResponse:
    """Normalized response archived before checkpoint and result publication."""

    status: str
    phase: str
    session_identity: str
    idempotency_key: str
    request_identity: str
    provider_identity: str
    iterations: int
    candidates: tuple[PermuterRawCandidate, ...]
    state: Mapping[str, Any]
    response_identity: str
    attempts: int = 1
    best_score: Optional[float] = None
    reason: str = ""
    stop_reason: str = ""
    refusal_code: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status not in _STATUS_CODES - {"handoff_pending"}:
            raise PermuterProviderInputError("response status is invalid")
        if self.phase not in _PHASES:
            raise PermuterProviderInputError("response phase is invalid")
        for name in (
            "session_identity",
            "idempotency_key",
            "request_identity",
            "provider_identity",
            "response_identity",
        ):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        _integer(self.iterations, "response iterations", 0, PERMUTER_MAX_ITERATIONS)
        _integer(self.attempts, "response attempts", 0, PERMUTER_MAX_CALLS)
        candidates = tuple(self.candidates)
        if tuple(item.candidate_id for item in candidates) != tuple(
            sorted(item.candidate_id for item in candidates)
        ):
            raise PermuterProviderInputError("response candidates must be canonical")
        if len({item.candidate_id for item in candidates}) != len(candidates):
            raise PermuterProviderInputError("response candidates must be unique")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "state", _freeze_json(self.state, "response state"))
        if not isinstance(self.state, Mapping):
            raise PermuterProviderInputError("response state must be an object")
        if len(canonical_bytes(self.state)) > PERMUTER_MAX_STATE_BYTES:
            raise PermuterProviderInputError("response state exceeds bound")
        if self.best_score is not None:
            object.__setattr__(self, "best_score", _number(self.best_score, "best_score"))
        object.__setattr__(self, "reason", _text(self.reason, "response reason", allow_empty=True))
        object.__setattr__(self, "stop_reason", _text(self.stop_reason, "stop_reason", allow_empty=True))
        if self.refusal_code is not None:
            object.__setattr__(self, "refusal_code", _text(self.refusal_code, "refusal_code"))
        expected = hash_canonical(self.identity_payload())
        if self.response_identity != expected:
            raise PermuterProviderInputError("response identity changed")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": PERMUTER_RESPONSE_PROTOCOL,
            "status": self.status,
            "phase": self.phase,
            "session_identity": self.session_identity,
            "idempotency_key": self.idempotency_key,
            "request_identity": self.request_identity,
            "provider_identity": self.provider_identity,
            "iterations": self.iterations,
            "candidates": [item.to_dict() for item in self.candidates],
            "state": _plain(self.state),
            "attempts": self.attempts,
            "best_score": self.best_score,
            "reason": self.reason,
            "stop_reason": self.stop_reason,
            "refusal_code": self.refusal_code,
        }

    def to_dict(self) -> dict[str, Any]:
        return dict(self.identity_payload(), response_identity=self.response_identity)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PermuterProviderResponse":
        data = _strict(
            value,
            (
                "protocol",
                "status",
                "phase",
                "session_identity",
                "idempotency_key",
                "request_identity",
                "provider_identity",
                "iterations",
                "candidates",
                "state",
                "response_identity",
            ),
            ("attempts", "best_score", "reason", "stop_reason", "refusal_code"),
            "permuter response",
        )
        if data["protocol"] != PERMUTER_RESPONSE_PROTOCOL:
            raise PermuterProviderInputError("response protocol differs")
        candidates = tuple(
            PermuterRawCandidate(
                source=item["source"],
                score=item.get("score"),
                iteration=item.get("iteration", 0),
                provenance=item.get("provenance", {}),
            )
            for item in data["candidates"]
        )
        return cls(
            status=data["status"],
            phase=data["phase"],
            session_identity=data["session_identity"],
            idempotency_key=data["idempotency_key"],
            request_identity=data["request_identity"],
            provider_identity=data["provider_identity"],
            iterations=data["iterations"],
            candidates=candidates,
            state=data["state"],
            response_identity=data["response_identity"],
            attempts=data.get("attempts", 1),
            best_score=data.get("best_score"),
            reason=data.get("reason", ""),
            stop_reason=data.get("stop_reason", ""),
            refusal_code=data.get("refusal_code"),
        )


def _candidate_provenance(
    request: PermuterRequest,
    response_identity: str,
    candidate_id: str,
    checkpoint_identity: Optional[str],
) -> dict[str, Any]:
    return {
        "kind": "permuter_provider",
        "source": request.algorithm + ":" + request.vendor_revision,
        "source_identity": candidate_id,
        "input_identity": request.input_identity,
        "lane": request.lane,
        "recipient_id": request.recipient_id,
        "target_identity": request.target_identity,
        "manifest_identity": request.manifest_identity,
        "provider_identity": request.provider_identity,
        "config_identity": request.config_identity,
        "evaluator_identity": request.evaluator_identity,
        "vendor_revision": request.vendor_revision,
        "tool_identity": request.tool_identity,
        "weights_identity": request.weights_identity,
        "algorithm_identity": request.algorithm_identity,
        "session_identity": request.session_identity,
        "request_identity": request.request_identity,
        "idempotency_key": request.idempotency_key,
        "response_identity": response_identity,
        "scratch_identity": request.scratch_identity,
        "seed_identity": request.seed_identity,
        "target_artifact_identity": request.target_artifact_identity,
        "checkpoint_identity": checkpoint_identity,
    }


@dataclass(frozen=True)
class PermuterProviderResult:
    """Durable checkpointed result replayed into the ordinary lane callback shape."""

    status: str
    lane: str
    phase: str
    recipient_id: str
    target_identity: str
    manifest_identity: str
    provider_identity: str
    config_identity: str
    evaluator_identity: str
    vendor_revision: str
    tool_identity: str
    weights_identity: str
    algorithm: str
    algorithm_identity: str
    session_identity: str
    scratch_identity: str
    scratch_path: str
    idempotency_key: str
    request_identity: str
    response_identity: str
    checkpoint_identity: str
    result_identity: str
    request_artifact: ArtifactRef
    response_artifact: ArtifactRef
    checkpoint_artifact: ArtifactRef
    result_artifact: ArtifactRef
    seed_identity: str
    target_artifact_identity: str
    input_identity: str
    budget: PermuterBudget
    candidates: tuple[PermuterCandidate, ...]
    input_identities: tuple[str, ...]
    provenance: tuple[Mapping[str, Any], ...]
    attempts: int
    iterations: int
    completion_reason: str
    reason: str = ""
    refusal_code: Optional[str] = None
    rejection_counts: Mapping[str, int] = field(default_factory=dict)
    state: Mapping[str, Any] = field(default_factory=dict)
    best_score: Optional[float] = None

    def __post_init__(self) -> None:
        if self.status not in _STATUS_CODES:
            raise PermuterProviderInputError("result status is invalid")
        if self.lane not in PERMUTER_LANES or self.phase not in _PHASES:
            raise PermuterProviderInputError("result lane or phase is invalid")
        object.__setattr__(self, "recipient_id", _identifier(self.recipient_id, "recipient_id"))
        for name in (
            "target_identity",
            "manifest_identity",
            "provider_identity",
            "config_identity",
            "evaluator_identity",
            "vendor_revision",
            "tool_identity",
            "weights_identity",
            "algorithm_identity",
            "session_identity",
            "scratch_identity",
            "idempotency_key",
            "request_identity",
            "response_identity",
            "checkpoint_identity",
            "result_identity",
            "seed_identity",
            "target_artifact_identity",
            "input_identity",
        ):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        for name in ("algorithm", "scratch_path"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in ("request_artifact", "response_artifact", "checkpoint_artifact", "result_artifact"):
            object.__setattr__(self, name, _artifact(getattr(self, name), name))
        if not isinstance(self.budget, PermuterBudget):
            object.__setattr__(self, "budget", PermuterBudget.from_dict(self.budget))
        candidates = tuple(self.candidates)
        if any(not isinstance(item, PermuterCandidate) for item in candidates):
            raise PermuterProviderInputError("result candidates must be typed")
        if tuple(item.candidate_id for item in candidates) != tuple(sorted(item.candidate_id for item in candidates)):
            raise PermuterProviderInputError("result candidates must be canonical")
        if len({item.candidate_id for item in candidates}) != len(candidates):
            raise PermuterProviderInputError("result candidates must be unique")
        if self.budget.candidates_consumed != len(candidates):
            raise PermuterProviderInputError("result budget must charge unique candidates")
        object.__setattr__(self, "candidates", candidates)
        inputs = tuple(self.input_identities)
        if len(set(inputs)) != len(inputs):
            raise PermuterProviderInputError("result input identities must be unique")
        for item in inputs:
            _identity(item, "result input identity")
        object.__setattr__(self, "input_identities", inputs)
        object.__setattr__(
            self,
            "provenance",
            tuple(_freeze_json(item, "result provenance") for item in self.provenance),
        )
        if any(not isinstance(item, Mapping) for item in self.provenance):
            raise PermuterProviderInputError("result provenance entries must be objects")
        object.__setattr__(self, "rejection_counts", _freeze_json(self.rejection_counts, "rejection_counts"))
        if not isinstance(self.rejection_counts, Mapping):
            raise PermuterProviderInputError("rejection_counts must be an object")
        for key, count in self.rejection_counts.items():
            if not isinstance(key, str):
                raise PermuterProviderInputError("rejection class must be text")
            _integer(count, "rejection count", 0)
        object.__setattr__(self, "state", _freeze_json(self.state, "result state"))
        if not isinstance(self.state, Mapping):
            raise PermuterProviderInputError("result state must be an object")
        _integer(self.attempts, "result attempts", 0, PERMUTER_MAX_CALLS)
        _integer(self.iterations, "result iterations", 0, PERMUTER_MAX_ITERATIONS)
        if self.completion_reason not in _COMPLETION_REASONS:
            raise PermuterProviderInputError("result completion reason is invalid")
        object.__setattr__(self, "reason", _text(self.reason, "result reason", allow_empty=True))
        if self.refusal_code is not None:
            object.__setattr__(self, "refusal_code", _text(self.refusal_code, "result refusal code"))
        if self.best_score is not None:
            object.__setattr__(self, "best_score", _number(self.best_score, "best_score"))
        expected = hash_canonical(self.identity_payload())
        if self.result_identity != expected:
            raise PermuterProviderInputError(
                "result identity changed: " + self.result_identity + " != " + expected
            )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": PERMUTER_RESULT_PROTOCOL,
            "status": self.status,
            "lane": self.lane,
            "phase": self.phase,
            "recipient_id": self.recipient_id,
            "target_identity": self.target_identity,
            "manifest_identity": self.manifest_identity,
            "provider_identity": self.provider_identity,
            "config_identity": self.config_identity,
            "evaluator_identity": self.evaluator_identity,
            "vendor_revision": self.vendor_revision,
            "tool_identity": self.tool_identity,
            "weights_identity": self.weights_identity,
            "algorithm": self.algorithm,
            "algorithm_identity": self.algorithm_identity,
            "session_identity": self.session_identity,
            "scratch_identity": self.scratch_identity,
            "scratch_path": self.scratch_path,
            "idempotency_key": self.idempotency_key,
            "request_identity": self.request_identity,
            "response_identity": self.response_identity,
            "checkpoint_identity": self.checkpoint_identity,
            "request_artifact": _artifact_identity(self.request_artifact),
            "response_artifact": _artifact_identity(self.response_artifact),
            "checkpoint_artifact": _artifact_identity(self.checkpoint_artifact),
            "seed_identity": self.seed_identity,
            "target_artifact_identity": self.target_artifact_identity,
            "input_identity": self.input_identity,
            "budget": self.budget.to_dict(),
            "candidates": [item.to_dict() for item in self.candidates],
            "input_identities": list(self.input_identities),
            "provenance": [_plain(item) for item in self.provenance],
            "attempts": self.attempts,
            "iterations": self.iterations,
            "completion_reason": self.completion_reason,
            "reason": self.reason,
            "refusal_code": self.refusal_code,
            "rejection_counts": _plain(self.rejection_counts),
            "state": _plain(self.state),
            "best_score": self.best_score,
        }

    def to_dict(self) -> dict[str, Any]:
        return dict(
            self.identity_payload(),
            result_identity=self.result_identity,
            result_artifact=_artifact_identity(self.result_artifact),
        )

    def to_archive_dict(self) -> dict[str, Any]:
        return dict(self.identity_payload(), result_identity=self.result_identity)

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        result_artifact: Optional[ArtifactRef] = None,
    ) -> "PermuterProviderResult":
        data = _strict(
            value,
            (
                "protocol",
                "status",
                "lane",
                "phase",
                "recipient_id",
                "target_identity",
                "manifest_identity",
                "provider_identity",
                "config_identity",
                "evaluator_identity",
                "vendor_revision",
                "tool_identity",
                "weights_identity",
                "algorithm",
                "algorithm_identity",
                "session_identity",
                "scratch_identity",
                "scratch_path",
                "idempotency_key",
                "request_identity",
                "response_identity",
                "checkpoint_identity",
                "result_identity",
                "request_artifact",
                "response_artifact",
                "checkpoint_artifact",
                "seed_identity",
                "target_artifact_identity",
                "input_identity",
                "budget",
                "candidates",
                "input_identities",
                "provenance",
                "attempts",
                "iterations",
                "completion_reason",
                "reason",
                "rejection_counts",
                "state",
                "best_score",
            ),
            ("refusal_code", "result_artifact"),
            "permuter result",
        )
        if data["protocol"] != PERMUTER_RESULT_PROTOCOL:
            raise PermuterProviderInputError("result protocol differs")
        candidates = tuple(
            PermuterCandidate(
                candidate_id=item["candidate_id"],
                source=item["source"],
                provenance=item["provenance"],
                input_identity=item["input_identity"],
                score=item.get("score"),
                iteration=item.get("iteration", 0),
            )
            for item in data["candidates"]
        )
        parsed_result_artifact = (
            result_artifact
            if result_artifact is not None
            else _artifact(data.get("result_artifact"), "result_artifact")
        )
        return cls(
            status=data["status"],
            lane=data["lane"],
            phase=data["phase"],
            recipient_id=data["recipient_id"],
            target_identity=data["target_identity"],
            manifest_identity=data["manifest_identity"],
            provider_identity=data["provider_identity"],
            config_identity=data["config_identity"],
            evaluator_identity=data["evaluator_identity"],
            vendor_revision=data["vendor_revision"],
            tool_identity=data["tool_identity"],
            weights_identity=data["weights_identity"],
            algorithm=data["algorithm"],
            algorithm_identity=data["algorithm_identity"],
            session_identity=data["session_identity"],
            scratch_identity=data["scratch_identity"],
            scratch_path=data["scratch_path"],
            idempotency_key=data["idempotency_key"],
            request_identity=data["request_identity"],
            response_identity=data["response_identity"],
            checkpoint_identity=data["checkpoint_identity"],
            result_identity=data["result_identity"],
            request_artifact=_artifact(data["request_artifact"], "request_artifact"),
            response_artifact=_artifact(data["response_artifact"], "response_artifact"),
            checkpoint_artifact=_artifact(data["checkpoint_artifact"], "checkpoint_artifact"),
            result_artifact=parsed_result_artifact,
            seed_identity=data["seed_identity"],
            target_artifact_identity=data["target_artifact_identity"],
            input_identity=data["input_identity"],
            budget=PermuterBudget.from_dict(data["budget"]),
            candidates=candidates,
            input_identities=tuple(data["input_identities"]),
            provenance=tuple(data["provenance"]),
            attempts=data["attempts"],
            iterations=data["iterations"],
            completion_reason=data["completion_reason"],
            reason=data["reason"],
            refusal_code=data.get("refusal_code"),
            rejection_counts=data["rejection_counts"],
            state=data["state"],
            best_score=data["best_score"],
        )

    def to_discovery(self) -> dict[str, Any]:
        return {
            "candidates": [item.to_mapping() for item in self.candidates],
            "attempts": self.attempts,
            "input_identities": list(self.input_identities),
            "provenance": [_plain(item) for item in self.provenance],
            "rejection_counts": dict(self.rejection_counts),
            "best_score": self.best_score,
            "completion_reason": self.completion_reason,
            "reason": self.reason,
            "refusal_code": self.refusal_code,
            "status": self.status,
            "candidate_ids": [item.candidate_id for item in self.candidates],
            "iterations": self.iterations,
            "budget": self.budget.to_dict(),
            "checkpoint_identity": self.checkpoint_identity,
            "result_identity": self.result_identity,
            "scratch_identity": self.scratch_identity,
        }


class PermuterHandoffStore:
    """Content-addressed storage for all permuter lifecycle records."""

    def __init__(self, archive: ContentAddressedArchive) -> None:
        if not isinstance(archive, ContentAddressedArchive):
            raise PermuterProviderInputError("handoff store needs a ContentAddressedArchive")
        self.archive = archive

    def _put(self, document: Mapping[str, Any], category: str) -> ArtifactRef:
        try:
            reference = self.archive.put_json(document, category=category, suffix=".json")
        except ArchiveError as exc:
            raise PermuterProviderHandoffError(f"unable to archive {category}") from exc
        if reference.content_hash != hash_canonical(document):
            raise PermuterProviderHandoffError(f"archive identity differs for {category}")
        return reference

    def put_request(self, request: PermuterRequest) -> ArtifactRef:
        return self._put(request.to_dict(), PERMUTER_REQUEST_CATEGORY)

    def put_response(self, response: PermuterProviderResponse) -> ArtifactRef:
        return self._put(response.to_dict(), PERMUTER_RESPONSE_CATEGORY)

    def put_checkpoint(self, checkpoint: PermuterCheckpoint) -> ArtifactRef:
        return self._put(checkpoint.to_dict(), PERMUTER_CHECKPOINT_CATEGORY)

    def put_stop(self, document: Mapping[str, Any]) -> ArtifactRef:
        return self._put(document, PERMUTER_STOP_CATEGORY)

    def _iter_documents(self, category: str):
        if not isinstance(category, str) or not category or "/" in category or "\\" in category:
            raise PermuterProviderHandoffError("invalid handoff category")
        root = self.archive.artifacts_root / category
        run_root = self.archive.run_root.resolve(strict=False)
        try:
            resolved_root = root.resolve(strict=False)
            resolved_root.relative_to(run_root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise PermuterProviderHandoffError("handoff category escaped run root") from exc
        if not resolved_root.exists():
            return
        try:
            paths = sorted(resolved_root.iterdir(), key=lambda item: item.as_posix())
        except OSError as exc:
            raise PermuterProviderHandoffError("handoff category cannot be listed") from exc
        for path in paths:
            try:
                resolved = path.resolve(strict=False)
                resolved.relative_to(run_root)
            except (OSError, RuntimeError, ValueError) as exc:
                raise PermuterProviderHandoffError("handoff artifact escaped run root") from exc
            if not resolved.is_file() or resolved.suffix != ".json":
                continue
            try:
                raw = resolved.read_bytes()
                document = json.loads(raw.decode("utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise PermuterProviderHandoffError("handoff artifact is not valid JSON") from exc
            if canonical_bytes(document) != raw:
                raise PermuterProviderHandoffError("handoff artifact is not canonical JSON")
            digest = hash_bytes(raw)
            if resolved.stem != digest.removeprefix("sha256:"):
                raise PermuterProviderHandoffError("handoff artifact filename identity differs")
            yield document, ArtifactRef(
                content_hash=digest,
                path=resolved.relative_to(run_root).as_posix(),
                media_type="application/json",
                byte_size=len(raw),
            )

    def find_request(self, request_identity: str):
        _identity(request_identity, "request_identity")
        for document, reference in self._iter_documents(PERMUTER_REQUEST_CATEGORY):
            if document.get("request_identity") == request_identity:
                return document, reference
        return None

    def find_response(self, request_identity: str):
        _identity(request_identity, "request_identity")
        for document, reference in self._iter_documents(PERMUTER_RESPONSE_CATEGORY):
            if document.get("request_identity") == request_identity:
                return document, reference
        return None

    def find_result(self, session_identity: str, phase: str):
        _identity(session_identity, "session_identity")
        if phase not in _PHASES:
            raise PermuterProviderInputError("result phase is invalid")
        for document, reference in self._iter_documents(PERMUTER_RESULT_CATEGORY):
            if (
                document.get("session_identity") == session_identity
                and document.get("phase") == phase
            ):
                return document, reference
        return None

    def find_checkpoint(self, checkpoint_identity: str):
        _identity(checkpoint_identity, "checkpoint_identity")
        for document, reference in self._iter_documents(PERMUTER_CHECKPOINT_CATEGORY):
            if document.get("checkpoint_identity") == checkpoint_identity:
                return document, reference
        return None

    def find_stop(self, session_identity: str, phase: str):
        _identity(session_identity, "session_identity")
        for document, reference in self._iter_documents(PERMUTER_STOP_CATEGORY):
            if (
                document.get("session_identity") == session_identity
                and document.get("phase") == phase
            ):
                return document, reference
        return None


def _manifest_identity(manifest: RunManifest) -> str:
    if not isinstance(manifest, RunManifest):
        raise PermuterProviderInputError("permuter provider requires a typed RunManifest")
    return hash_canonical(manifest.to_dict())


def _input_map(
    manifest: RunManifest,
    inputs: Mapping[str, ArchivedPermuterInput] | Sequence[ArchivedPermuterInput],
) -> dict[str, ArchivedPermuterInput]:
    if isinstance(inputs, Mapping):
        values = list(inputs.values())
        keys = list(inputs)
        if any(not isinstance(key, str) for key in keys):
            raise PermuterProviderInputError("permuter input keys must be strings")
        if set(keys) != {item.recipient_id for item in values}:
            raise PermuterProviderInputError("permuter input keys must match recipients")
    else:
        try:
            values = list(inputs)
        except TypeError as exc:
            raise PermuterProviderInputError("permuter inputs must be a mapping or sequence") from exc
    if not values:
        raise PermuterProviderInputError("permuter inputs must not be empty")
    if any(not isinstance(item, ArchivedPermuterInput) for item in values):
        raise PermuterProviderInputError("permuter inputs must be typed")
    values.sort(key=lambda item: item.recipient_id)
    if len({item.recipient_id for item in values}) != len(values):
        raise PermuterProviderInputError("permuter inputs must have unique recipients")
    manifest_ids = set(manifest.target_identities)
    for item in values:
        if item.recipient_id not in manifest_ids:
            raise PermuterProviderInputError("permuter input is outside manifest subset")
        if manifest.target_identities[item.recipient_id] != item.target_identity:
            raise PermuterProviderInputError("permuter target identity differs from manifest")
    return {item.recipient_id: item for item in values}


def _initial_checkpoint(
    request: PermuterRequest,
) -> PermuterCheckpoint:
    payload = {
        "protocol": PERMUTER_CHECKPOINT_PROTOCOL,
        "lane": request.lane,
        "phase": request.phase,
        "session_identity": request.session_identity,
        "request_identity": request.request_identity,
        "scratch_identity": request.scratch_identity,
        "iterations": request.start_iteration,
        "candidates": [],
        "state": {},
        "stopped": True,
        "stop_reason": "operator_stop",
    }
    payload["checkpoint_identity"] = hash_canonical(
        {key: value for key, value in payload.items() if key != "checkpoint_identity"}
    )
    return PermuterCheckpoint.from_dict(payload)


def _request_for(
    *,
    manifest: RunManifest,
    config: PermuterLaneConfig,
    binding: PermuterToolBinding,
    item: ArchivedPermuterInput,
    manifest_identity: str,
    provider_identity: str,
    phase: str,
    checkpoint: Optional[PermuterCheckpoint],
) -> PermuterRequest:
    if phase not in _PHASES:
        raise PermuterProviderInputError("request phase is invalid")
    start_iteration = checkpoint.iterations if checkpoint is not None else 0
    prior_identity = checkpoint.checkpoint_identity if checkpoint is not None else None
    scratch_identity = hash_canonical(
        {
            "protocol": PERMUTER_SCRATCH_PROTOCOL,
            "lane": config.lane,
            "session_identity": hash_canonical(
                {
                    "provider_identity": provider_identity,
                    "recipient_id": item.recipient_id,
                    "input_identity": item.input_identity,
                }
            ),
            "seed_identity": item.seed_identity,
            "target_artifact_identity": item.target_artifact_identity,
            "tool_identity": binding.tool_identity,
            "weights_identity": binding.weights_identity,
            "algorithm_identity": binding.algorithm_identity,
        }
    )
    scratch_path = _canonical_path(
        Path(manifest_identity).anchor or Path("."),
        "",
    ) if False else "permuter-scratch/" + config.lane + "/" + scratch_identity.removeprefix("sha256:")
    # The path is a relative identity only.  It is checked again against the
    # actual archive root by the provider before the executor sees it.
    payload = {
        "lane": config.lane,
        "phase": phase,
        "recipient_id": item.recipient_id,
        "target_identity": item.target_identity,
        "manifest_identity": manifest_identity,
        "provider_identity": provider_identity,
        "config_identity": config.identity,
        "evaluator_identity": config.evaluator_identity,
        "vendor_revision": binding.vendor_revision,
        "tool_identity": binding.tool_identity,
        "weights_identity": binding.weights_identity,
        "algorithm": config.algorithm,
        "algorithm_identity": config.algorithm_identity,
        "session_identity": hash_canonical(
            {
                "protocol": PERMUTER_PROVIDER_PROTOCOL,
                "provider_identity": provider_identity,
                "recipient_id": item.recipient_id,
                "input_identity": item.input_identity,
            }
        ),
        "seed_artifact": _artifact_identity(item.seed_artifact),
        "target_artifact": _artifact_identity(item.target_artifact),
        "seed_identity": item.seed_identity,
        "target_artifact_identity": item.target_artifact_identity,
        "input_identity": item.input_identity,
        "scratch_identity": scratch_identity,
        "scratch_path": scratch_path,
        "seed_source": item.seed_source,
        "target_assembly": item.target_assembly,
        "start_iteration": start_iteration,
        "prior_checkpoint_identity": prior_identity,
        "max_calls": config.max_calls,
        "max_iterations": config.max_iterations,
        "max_candidates": config.max_candidates,
        "checkpoint_interval": config.checkpoint_interval,
    }
    key = hash_canonical(payload)
    request_identity = hash_canonical(
        {
            "protocol": PERMUTER_REQUEST_PROTOCOL,
            "idempotency_key": key,
            "payload": payload,
        }
    )
    return PermuterRequest(
        lane=config.lane,
        phase=phase,
        recipient_id=item.recipient_id,
        target_identity=item.target_identity,
        manifest_identity=manifest_identity,
        provider_identity=provider_identity,
        config_identity=config.identity,
        evaluator_identity=config.evaluator_identity,
        vendor_revision=binding.vendor_revision,
        tool_identity=binding.tool_identity,
        weights_identity=binding.weights_identity,
        algorithm=config.algorithm,
        algorithm_identity=config.algorithm_identity,
        session_identity=payload["session_identity"],
        idempotency_key=key,
        request_identity=request_identity,
        seed_artifact=item.seed_artifact,
        target_artifact=item.target_artifact,
        seed_identity=item.seed_identity,
        target_artifact_identity=item.target_artifact_identity,
        input_identity=item.input_identity,
        scratch_identity=scratch_identity,
        scratch_path=scratch_path,
        seed_source=item.seed_source,
        target_assembly=item.target_assembly,
        start_iteration=start_iteration,
        prior_checkpoint_identity=prior_identity,
        max_calls=config.max_calls,
        max_iterations=config.max_iterations,
        max_candidates=config.max_candidates,
        checkpoint_interval=config.checkpoint_interval,
    )


def _normalize_candidates(
    values: Any,
    max_candidates: int,
) -> tuple[PermuterRawCandidate, ...]:
    if values is None:
        values = ()
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise PermuterProviderInvalidResponse("candidates must be a sequence")
    if len(values) > max_candidates * 16:
        raise PermuterProviderInvalidResponse("raw candidate count exceeds bound")
    grouped: dict[str, PermuterRawCandidate] = {}
    for value in values:
        if isinstance(value, str):
            source = value
            score = None
            iteration = 0
            provenance = {}
        elif isinstance(value, Mapping):
            source = value.get("source", value.get("proposal", value.get("body")))
            if source is None:
                raise PermuterProviderInvalidResponse("candidate object needs source")
            score = value.get("score")
            iteration = value.get("iteration", 0)
            provenance = value.get("provenance", {})
        else:
            raise PermuterProviderInvalidResponse("candidate must be text or object")
        if not isinstance(source, str):
            raise PermuterProviderInvalidResponse("candidate source must be text")
        # Preserve the archived candidate bytes after line-ending normalization.
        # Trailing newlines are part of a C translation unit and therefore part
        # of its deterministic candidate identity.
        source = source.replace("\r\n", "\n").replace("\r", "\n")
        if not source.strip():
            raise PermuterProviderInvalidResponse("candidate source must not be empty")
        candidate = PermuterRawCandidate(
            source=source,
            score=score,
            iteration=iteration,
            provenance=provenance,
        )
        prior = grouped.get(candidate.candidate_id)
        if prior is None or candidate.key() < prior.key():
            grouped[candidate.candidate_id] = candidate
    if len(grouped) > max_candidates:
        raise PermuterProviderInvalidResponse("unique candidate count exceeds bound")
    return tuple(grouped[key] for key in sorted(grouped))


def _normalize_response(
    raw: Any,
    request: PermuterRequest,
) -> PermuterProviderResponse:
    if not isinstance(raw, Mapping):
        raise PermuterProviderInvalidResponse("executor must return one mapping")
    data = dict(raw)
    allowed = {
        "status",
        "iterations",
        "candidates",
        "state",
        "best_score",
        "reason",
        "stop_reason",
        "refusal_code",
    }
    unknown = set(data).difference(allowed)
    if unknown:
        raise PermuterProviderInvalidResponse("executor response has unknown fields")
    status = data.get("status", "completed")
    if status not in _STATUS_CODES - {"handoff_pending"}:
        raise PermuterProviderInvalidResponse("executor response status is invalid")
    iterations = _integer(
        data.get("iterations", 0),
        "response iterations",
        0,
        request.max_iterations,
    )
    candidates = _normalize_candidates(data.get("candidates", ()), request.max_candidates)
    state = _freeze_json(data.get("state", {}), "response state")
    if not isinstance(state, Mapping):
        raise PermuterProviderInvalidResponse("response state must be an object")
    if len(canonical_bytes(state)) > PERMUTER_MAX_STATE_BYTES:
        raise PermuterProviderInvalidResponse("response state exceeds bound")
    best_score = data.get("best_score")
    if best_score is not None:
        best_score = _number(best_score, "best_score")
    reason = data.get("reason", "")
    stop_reason = data.get("stop_reason", "")
    refusal_code = data.get("refusal_code")
    if not isinstance(reason, str) or not isinstance(stop_reason, str):
        raise PermuterProviderInvalidResponse("response reasons must be text")
    if refusal_code is not None and (not isinstance(refusal_code, str) or not refusal_code):
        raise PermuterProviderInvalidResponse("response refusal_code must be text")
    if status == "stopped" and not stop_reason:
        stop_reason = "operator_stop"
    payload = {
        "protocol": PERMUTER_RESPONSE_PROTOCOL,
        "status": status,
        "phase": request.phase,
        "session_identity": request.session_identity,
        "idempotency_key": request.idempotency_key,
        "request_identity": request.request_identity,
        "provider_identity": request.provider_identity,
        "iterations": iterations,
        "candidates": [item.to_dict() for item in candidates],
        "state": _plain(state),
        "attempts": 1,
        "best_score": best_score,
        "reason": reason,
        "stop_reason": stop_reason,
        "refusal_code": refusal_code,
    }
    return PermuterProviderResponse(
        status=status,
        phase=request.phase,
        session_identity=request.session_identity,
        idempotency_key=request.idempotency_key,
        request_identity=request.request_identity,
        provider_identity=request.provider_identity,
        iterations=iterations,
        candidates=candidates,
        state=state,
        response_identity=hash_canonical(payload),
        attempts=1,
        best_score=best_score,
        reason=reason,
        stop_reason=stop_reason,
        refusal_code=refusal_code,
    )


def _failure_response(
    request: PermuterRequest,
    *,
    status: str,
    reason: str,
    refusal_code: str,
    attempts: int = 1,
) -> PermuterProviderResponse:
    raw = {
        "protocol": PERMUTER_RESPONSE_PROTOCOL,
        "status": status,
        "phase": request.phase,
        "session_identity": request.session_identity,
        "idempotency_key": request.idempotency_key,
        "request_identity": request.request_identity,
        "provider_identity": request.provider_identity,
        "iterations": 0,
        "candidates": [],
        "state": {},
        "attempts": attempts,
        "best_score": None,
        "reason": reason,
        "stop_reason": "",
        "refusal_code": refusal_code,
    }
    return PermuterProviderResponse(
        status=status,
        phase=request.phase,
        session_identity=request.session_identity,
        idempotency_key=request.idempotency_key,
        request_identity=request.request_identity,
        provider_identity=request.provider_identity,
        iterations=0,
        candidates=(),
        state={},
        response_identity=hash_canonical(raw),
        attempts=attempts,
        reason=reason,
        refusal_code=refusal_code,
    )


def _response_with_stop_reason(
    response: PermuterProviderResponse,
    stop_reason: str,
) -> PermuterProviderResponse:
    normalized = _text(stop_reason, "stop_reason")
    payload = response.identity_payload()
    payload["stop_reason"] = normalized
    return dataclasses.replace(
        response,
        stop_reason=normalized,
        response_identity=hash_canonical(payload),
    )


def _checkpoint_for(
    request: PermuterRequest,
    response: PermuterProviderResponse,
    candidates: Sequence[PermuterRawCandidate],
) -> PermuterCheckpoint:
    ordered = tuple(sorted(candidates, key=lambda item: item.candidate_id))
    payload = {
        "protocol": PERMUTER_CHECKPOINT_PROTOCOL,
        "lane": request.lane,
        "phase": request.phase,
        "session_identity": request.session_identity,
        "request_identity": request.request_identity,
        "scratch_identity": request.scratch_identity,
        "iterations": request.start_iteration + response.iterations,
        "candidates": [item.to_dict() for item in ordered],
        "state": _plain(response.state),
        "stopped": response.status == "stopped",
        "stop_reason": response.stop_reason,
    }
    payload["checkpoint_identity"] = hash_canonical(payload)
    return PermuterCheckpoint.from_dict(payload)


def _result_payload(
    *,
    request: PermuterRequest,
    request_artifact: ArtifactRef,
    response: PermuterProviderResponse,
    response_artifact: ArtifactRef,
    checkpoint: PermuterCheckpoint,
    checkpoint_artifact: ArtifactRef,
    result_status: str,
    prior_candidates: Sequence[PermuterRawCandidate],
    prior_attempts: int,
    prior_iterations: int,
    prior_candidate_ids: Sequence[str],
) -> dict[str, Any]:
    grouped: dict[str, PermuterRawCandidate] = {}
    for item in [*prior_candidates, *response.candidates]:
        prior = grouped.get(item.candidate_id)
        if prior is None or item.key() < prior.key():
            grouped[item.candidate_id] = item
    ordered_raw = tuple(grouped[key] for key in sorted(grouped))
    if len(ordered_raw) > request.max_candidates:
        raise PermuterProviderInvalidResponse("cumulative unique candidate count exceeds bound")
    all_candidates: list[PermuterCandidate] = []
    candidate_edges: list[Mapping[str, Any]] = []
    checkpoint_identity = checkpoint.checkpoint_identity
    for raw in ordered_raw:
        candidate_id = raw.candidate_id
        edge = _candidate_provenance(request, response.response_identity, candidate_id, checkpoint_identity)
        if raw.provenance:
            edge = {**edge, "executor_provenance": _plain(raw.provenance)}
        all_candidates.append(
            PermuterCandidate(
                candidate_id=candidate_id,
                source=raw.source,
                provenance=edge,
                input_identity=request.input_identity,
                score=raw.score,
                iteration=raw.iteration,
            )
        )
        candidate_edges.append(edge)
    attempts = prior_attempts + response.attempts
    iterations = prior_iterations + response.iterations
    if attempts > request.max_calls:
        raise PermuterProviderInvalidResponse("cumulative call budget exceeded")
    if iterations > request.max_iterations:
        raise PermuterProviderInvalidResponse("cumulative iteration budget exceeded")
    budget = PermuterBudget(
        max_calls=request.max_calls,
        max_iterations=request.max_iterations,
        max_candidates=request.max_candidates,
        calls_consumed=attempts,
        iterations_consumed=iterations,
        candidates_consumed=len(all_candidates),
    )
    input_ids = tuple(
        dict.fromkeys(
            (
                MODULE_IDENTITY,
                request.manifest_identity,
                request.target_identity,
                request.seed_identity,
                request.target_artifact_identity,
                request.input_identity,
                request.config_identity,
                request.evaluator_identity,
                request.vendor_revision,
                request.tool_identity,
                request.weights_identity,
                request.algorithm_identity,
                request.provider_identity,
                request.session_identity,
                request.scratch_identity,
                request.request_identity,
                request.idempotency_key,
                response.response_identity,
                checkpoint.checkpoint_identity,
                checkpoint_artifact.content_hash,
                *[item.candidate_id for item in all_candidates],
                *prior_candidate_ids,
            )
        )
    )
    base_edge = _candidate_provenance(request, response.response_identity, request.provider_identity, checkpoint_identity)
    provenance = tuple([base_edge, *candidate_edges])
    completion_reason = (
        response.stop_reason if result_status == "stopped" and response.stop_reason in _COMPLETION_REASONS
        else "operator_stop" if result_status == "stopped"
        else "inapplicable"
        if result_status in _FAILURE_CODES or result_status == "handoff_pending"
        else "search_space_exhausted"
    )
    reason = response.reason or (
        "permuter provider returned bounded proposals"
        if result_status == "completed"
        else result_status
    )
    payload = {
        "protocol": PERMUTER_RESULT_PROTOCOL,
        "status": result_status,
        "lane": request.lane,
        "phase": request.phase,
        "recipient_id": request.recipient_id,
        "target_identity": request.target_identity,
        "manifest_identity": request.manifest_identity,
        "provider_identity": request.provider_identity,
        "config_identity": request.config_identity,
        "evaluator_identity": request.evaluator_identity,
        "vendor_revision": request.vendor_revision,
        "tool_identity": request.tool_identity,
        "weights_identity": request.weights_identity,
        "algorithm": request.algorithm,
        "algorithm_identity": request.algorithm_identity,
        "session_identity": request.session_identity,
        "scratch_identity": request.scratch_identity,
        "scratch_path": request.scratch_path,
        "idempotency_key": request.idempotency_key,
        "request_identity": request.request_identity,
        "response_identity": response.response_identity,
        "checkpoint_identity": checkpoint.checkpoint_identity,
        "request_artifact": _artifact_identity(request_artifact),
        "response_artifact": _artifact_identity(response_artifact),
        "checkpoint_artifact": _artifact_identity(checkpoint_artifact),
        "seed_identity": request.seed_identity,
        "target_artifact_identity": request.target_artifact_identity,
        "input_identity": request.input_identity,
        "budget": budget.to_dict(),
        "candidates": [item.to_dict() for item in all_candidates],
        "input_identities": list(input_ids),
        "provenance": [_plain(item) for item in provenance],
        "attempts": attempts,
        "iterations": iterations,
        "completion_reason": completion_reason,
        "reason": reason,
        "refusal_code": response.refusal_code,
        "rejection_counts": {},
        "state": _plain(response.state),
        "best_score": response.best_score,
    }
    payload["result_identity"] = hash_canonical(payload)
    return payload


class PermuterLaneProvider:
    """Durable, factory-bound provider for one permuter lane."""

    def __init__(
        self,
        manifest: RunManifest,
        inputs: Mapping[str, ArchivedPermuterInput] | Sequence[ArchivedPermuterInput],
        *,
        archive: ContentAddressedArchive,
        binding: PermuterToolBinding,
        config: PermuterLaneConfig,
        executor_callback: Optional[Callable[[PermuterRequest], Mapping[str, Any]]] = None,
    ) -> None:
        if not isinstance(manifest, RunManifest):
            raise PermuterProviderInputError("permuter provider requires a typed RunManifest")
        if config.lane not in PERMUTER_LANES:
            raise PermuterProviderInputError("provider config lane is invalid")
        if binding.lane != config.lane:
            raise PermuterProviderInputError("provider binding lane differs from config")
        if binding.algorithm != config.algorithm:
            raise PermuterProviderInputError("provider binding algorithm differs from config")
        if binding.algorithm_identity != config.algorithm_identity:
            raise PermuterProviderInputError(
                "provider binding algorithm identity differs from config"
            )
        if not isinstance(archive, ContentAddressedArchive):
            raise PermuterProviderInputError("permuter provider requires a ContentAddressedArchive")
        if executor_callback is not None and not callable(executor_callback):
            raise PermuterProviderInputError("executor callback must be callable")
        self.manifest = manifest
        self.config = config
        self.binding = binding
        self.archive = archive
        self.inputs = _input_map(manifest, inputs)
        self.executor_callback = executor_callback
        self.manifest_identity = _manifest_identity(manifest)
        self.manifest_tool_identity = _identity(manifest.tool_identities.get(config.lane), "permuter lane tool identity")
        self.tool_identity = binding.tool_identity
        self.provider_identity = hash_canonical(
            {
                "protocol": PERMUTER_PROVIDER_PROTOCOL,
                "module_identity": MODULE_IDENTITY,
                "lane": config.lane,
                "manifest_identity": self.manifest_identity,
                "config_identity": config.identity,
                "binding_identity": binding.identity,
                "vendor_revision": binding.vendor_revision,
                "manifest_tool_identity": self.manifest_tool_identity,
                "tool_identity": binding.tool_identity,
                "weights_identity": binding.weights_identity,
                "algorithm_identity": binding.algorithm_identity,
                "input_identities": [
                    self.inputs[key].input_identity for key in sorted(self.inputs)
                ],
            }
        )
        self._issued: set[str] = set()

    def _input_for(self, recipient: Recipient) -> ArchivedPermuterInput:
        if not isinstance(recipient, Recipient):
            raise PermuterProviderInputError("permuter callback needs a typed Recipient")
        item = self.inputs.get(recipient.recipient_id)
        if item is None:
            raise PermuterProviderInputError(
                f"recipient {recipient.recipient_id} is outside the frozen permuter subset"
            )
        return item

    def _request(
        self,
        item: ArchivedPermuterInput,
        phase: str,
        checkpoint: Optional[PermuterCheckpoint] = None,
    ) -> PermuterRequest:
        request = _request_for(
            manifest=self.manifest,
            config=self.config,
            binding=self.binding,
            item=item,
            manifest_identity=self.manifest_identity,
            provider_identity=self.provider_identity,
            phase=phase,
            checkpoint=checkpoint,
        )
        # Keep the published scratch path relative and POSIX-shaped while
        # checking it against the actual archive root on every platform.
        if _canonical_path(self.archive.run_root, request.scratch_path) != request.scratch_path:
            raise PermuterProviderInputError("derived scratch path is not canonical")
        return request

    def _decode_response(
        self,
        request: PermuterRequest,
        document: Mapping[str, Any],
    ) -> PermuterProviderResponse:
        response = PermuterProviderResponse.from_dict(document)
        if (
            response.phase != request.phase
            or response.session_identity != request.session_identity
            or response.idempotency_key != request.idempotency_key
            or response.request_identity != request.request_identity
            or response.provider_identity != request.provider_identity
        ):
            raise PermuterProviderHandoffError("archived response binding differs from request")
        return response

    def _decode_checkpoint(
        self,
        request: PermuterRequest,
        document: Mapping[str, Any],
    ) -> PermuterCheckpoint:
        checkpoint = PermuterCheckpoint.from_dict(document)
        if (
            checkpoint.phase != request.phase
            or checkpoint.session_identity != request.session_identity
            or checkpoint.request_identity != request.request_identity
            or checkpoint.scratch_identity != request.scratch_identity
        ):
            raise PermuterProviderHandoffError("archived checkpoint binding differs from request")
        return checkpoint

    def _decode_result(
        self,
        request: PermuterRequest,
        request_artifact: ArtifactRef,
        document: Mapping[str, Any],
        result_artifact: ArtifactRef,
    ) -> PermuterProviderResult:
        result = PermuterProviderResult.from_dict(document, result_artifact=result_artifact)
        if (
            result.phase != request.phase
            or result.session_identity != request.session_identity
            or result.request_identity != request.request_identity
            or result.request_artifact != request_artifact
            or result.provider_identity != request.provider_identity
            or result.config_identity != self.config.identity
            or result.tool_identity != self.binding.tool_identity
        ):
            raise PermuterProviderHandoffError("archived result binding differs from request")
        return result

    def _prior_for_resume(
        self,
        store: PermuterHandoffStore,
        item: ArchivedPermuterInput,
    ) -> tuple[Optional[PermuterProviderResult], Optional[PermuterCheckpoint]]:
        start_request = self._request(item, "start")
        start_request_ref = store.put_request(start_request)
        found = store.find_result(start_request.session_identity, "start")
        if found is None:
            return None, None
        prior = self._decode_result(
            start_request,
            start_request_ref,
            found[0],
            found[1],
        )
        checkpoint_found = store.find_checkpoint(prior.checkpoint_identity)
        if checkpoint_found is None:
            raise PermuterProviderHandoffError("stopped result has no durable checkpoint")
        checkpoint = self._decode_checkpoint(
            self._request(item, "start"),
            checkpoint_found[0],
        )
        return prior, checkpoint

    def _terminal(
        self,
        request: PermuterRequest,
        request_artifact: ArtifactRef,
        response: PermuterProviderResponse,
        *,
        prior: Optional[PermuterProviderResult] = None,
        result_status: Optional[str] = None,
    ) -> PermuterProviderResult:
        prior_candidates = tuple(
            PermuterRawCandidate(
                source=item.source,
                score=item.score,
                iteration=item.iteration,
                provenance={},
            )
            for item in (prior.candidates if prior is not None else ())
        )
        prior_attempts = prior.budget.calls_consumed if prior is not None else 0
        prior_iterations = prior.budget.iterations_consumed if prior is not None else 0
        prior_ids = tuple(item.candidate_id for item in (prior.candidates if prior is not None else ()))
        result_status = result_status or response.status
        if result_status not in _STATUS_CODES:
            raise PermuterProviderInputError("result status is invalid")
        store = PermuterHandoffStore(self.archive)
        checkpoint = _checkpoint_for(
            request,
            response,
            [*prior_candidates, *response.candidates],
        )
        try:
            response_artifact = store.put_response(response)
            checkpoint_artifact = store.put_checkpoint(checkpoint)
            document = _result_payload(
                request=request,
                request_artifact=request_artifact,
                response=response,
                response_artifact=response_artifact,
                checkpoint=checkpoint,
                checkpoint_artifact=checkpoint_artifact,
                result_status=result_status,
                prior_candidates=prior_candidates,
                prior_attempts=prior_attempts,
                prior_iterations=prior_iterations,
                prior_candidate_ids=prior_ids,
            )
            result_artifact = store._put(document, PERMUTER_RESULT_CATEGORY)
        except PermuterProviderHandoffError:
            raise
        except (ArchiveError, PermuterProviderError) as exc:
            raise PermuterProviderHandoffError("permuter handoff could not be completed") from exc
        return PermuterProviderResult.from_dict(document, result_artifact=result_artifact)

    def _pending(
        self,
        request: PermuterRequest,
        request_artifact: ArtifactRef,
    ) -> PermuterProviderResult:
        # Persist the pending receipt through the same response/checkpoint/
        # result chain as every terminal outcome.  A later process can replay
        # it without invoking the executor a second time.
        response = _failure_response(
            request,
            status="refused",
            reason=(
                "durable permuter request exists without a response; "
                "recovery must supply the response before another call"
            ),
            refusal_code=PermuterProviderHandoffPending.code,
            attempts=0,
        )
        return self._terminal(
            request,
            request_artifact,
            response,
            result_status="handoff_pending",
        )


    def _run(
        self,
        recipient: Recipient,
        *,
        resume: bool,
    ) -> PermuterProviderResult:
        item = self._input_for(recipient)
        item.verify(self.archive)
        try:
            self.binding.verify(self.archive)
        except PermuterProviderUnavailable as exc:
            # The provider identity and request are still archived before the
            # typed unavailable result, so recovery has an immutable refusal.
            store = PermuterHandoffStore(self.archive)
            request = self._request(item, "resume" if resume else "start")
            request_artifact = store.put_request(request)
            return self._terminal(
                request,
                request_artifact,
                _failure_response(
                    request,
                    status="unavailable",
                    reason=str(exc),
                    refusal_code=exc.code,
                    attempts=0,
                ),
            )
        store = PermuterHandoffStore(self.archive)
        prior: Optional[PermuterProviderResult] = None
        checkpoint: Optional[PermuterCheckpoint] = None
        phase = "resume" if resume else "start"
        if resume:
            prior, checkpoint = self._prior_for_resume(store, item)
            if prior is None:
                raise PermuterProviderInputError("resume requires a durable stopped start result")
            if prior.status == "completed":
                return prior
        request = self._request(item, phase, checkpoint)
        existing_result = store.find_result(request.session_identity, phase)
        request_found = store.find_request(request.request_identity) is not None
        request_artifact = store.put_request(request)
        if existing_result is not None:
            return self._decode_result(request, request_artifact, existing_result[0], existing_result[1])
        existing_response = store.find_response(request.request_identity)
        if existing_response is not None:
            response = self._decode_response(request, existing_response[0])
            return self._terminal(request, request_artifact, response, prior=prior)
        if request_found or request.request_identity in self._issued:
            return self._pending(request, request_artifact)
        stop = store.find_stop(request.session_identity, phase)
        if stop is not None and not resume:
            response = _failure_response(
                request,
                status="stopped",
                reason=stop.get("reason", "operator stop"),
                refusal_code="operator_stop",
                attempts=0,
            )
            response = _response_with_stop_reason(response, "operator_stop")
            return self._terminal(request, request_artifact, response, prior=prior)
        self._issued.add(request.request_identity)
        callback_started = False
        try:
            self.binding.verify(self.archive)
            if self.executor_callback is None:
                raise PermuterProviderUnavailable(
                    f"no executor callback is bound for {self.config.lane}"
                )
            callback_started = True
            raw = self.executor_callback(request)
        except TypeError:
            raise
        except PermuterProviderUnavailable as exc:
            return self._terminal(
                request,
                request_artifact,
                _failure_response(
                    request,
                    status="unavailable",
                    reason=str(exc),
                    refusal_code=exc.code,
                    attempts=1 if callback_started else 0,
                ),
                prior=prior,
            )
        except PermuterProviderRefused as exc:
            return self._terminal(
                request,
                request_artifact,
                _failure_response(
                    request,
                    status="refused",
                    reason=str(exc),
                    refusal_code=exc.code,
                ),
                prior=prior,
            )
        except PermuterProviderTimeout as exc:
            return self._terminal(
                request,
                request_artifact,
                _failure_response(
                    request,
                    status="timeout",
                    reason=str(exc),
                    refusal_code=exc.code,
                ),
                prior=prior,
            )
        except PermuterProviderInvalidResponse as exc:
            return self._terminal(
                request,
                request_artifact,
                _failure_response(
                    request,
                    status="invalid_response",
                    reason=str(exc),
                    refusal_code=exc.code,
                ),
                prior=prior,
            )
        except TimeoutError as exc:
            return self._terminal(
                request,
                request_artifact,
                _failure_response(
                    request,
                    status="timeout",
                    reason=str(exc) or "permuter provider timed out",
                    refusal_code=ProviderTimeout.code,
                ),
                prior=prior,
            )
        except ConnectionError as exc:
            return self._terminal(
                request,
                request_artifact,
                _failure_response(
                    request,
                    status="unavailable",
                    reason=str(exc) or "permuter provider unavailable",
                    refusal_code=ProviderUnavailable.code,
                ),
                prior=prior,
            )
        except ValueError as exc:
            return self._terminal(
                request,
                request_artifact,
                _failure_response(
                    request,
                    status="invalid_response",
                    reason=str(exc) or "permuter response is invalid",
                    refusal_code=ProviderInvalidResponse.code,
                ),
                prior=prior,
            )
        try:
            response = _normalize_response(raw, request)
        except (PermuterProviderError, TypeError, ValueError) as exc:
            # Validation happens after the executor callback returns.  Keep
            # callback TypeError untouched above, but archive malformed output
            # as a typed durable invalid-response outcome.
            return self._terminal(
                request,
                request_artifact,
                _failure_response(
                    request,
                    status="invalid_response",
                    reason=str(exc) or "permuter response is invalid",
                    refusal_code=ProviderInvalidResponse.code,
                ),
                prior=prior,
            )
        return self._terminal(request, request_artifact, response, prior=prior)

    def run(self, recipient: Recipient) -> PermuterProviderResult:
        return self._run(recipient, resume=False)

    def resume(self, recipient: Recipient) -> PermuterProviderResult:
        return self._run(recipient, resume=True)

    def stop(self, recipient: Recipient, reason: str = "operator stop") -> PermuterProviderResult:
        item = self._input_for(recipient)
        item.verify(self.archive)
        store = PermuterHandoffStore(self.archive)
        request = self._request(item, "start")
        request_found = store.find_request(request.request_identity) is not None
        request_artifact = store.put_request(request)
        existing = store.find_result(request.session_identity, "start")
        if existing is not None:
            result = self._decode_result(request, request_artifact, existing[0], existing[1])
            if result.status == "completed":
                return result
        if not request_found:
            stop_document = {
                "protocol": PERMUTER_STOP_PROTOCOL,
                "lane": request.lane,
                "phase": "start",
                "session_identity": request.session_identity,
                "request_identity": request.request_identity,
                "scratch_identity": request.scratch_identity,
                "reason": _text(reason, "stop reason"),
            }
            stop_document["stop_identity"] = hash_canonical(stop_document)
            store.put_stop(stop_document)
        stop = store.find_stop(request.session_identity, "start")
        stop_reason = stop[0].get("reason", reason) if stop is not None else reason
        response = _failure_response(
            request,
            status="stopped",
            reason=stop_reason,
            refusal_code="operator_stop",
            attempts=0,
        )
        response = _response_with_stop_reason(response, "operator_stop")
        return self._terminal(request, request_artifact, response)

    def replay(self, recipient: Recipient, *, resume: bool = False) -> PermuterProviderResult:
        item = self._input_for(recipient)
        store = PermuterHandoffStore(self.archive)
        phase = "resume" if resume else "start"
        checkpoint: Optional[PermuterCheckpoint] = None
        if resume:
            prior, checkpoint = self._prior_for_resume(store, item)
            if prior is None:
                raise PermuterProviderHandoffPending(
                    "no durable stopped start result is available for resume"
                )
            if prior.status == "completed":
                return prior
        request = self._request(item, phase, checkpoint)
        found = store.find_result(request.session_identity, phase)
        if found is None:
            raise PermuterProviderHandoffPending("no durable permuter result is available")
        return self._decode_result(request, store.put_request(request), found[0], found[1])

    def callback(self, recipient: Recipient) -> Mapping[str, Any]:
        return self.run(recipient).to_discovery()

    def __call__(self, recipient: Recipient) -> Mapping[str, Any]:
        return self.callback(recipient)

    def to_adapter_mapping(self) -> dict[str, Callable[[Recipient], Mapping[str, Any]]]:
        return {self.config.lane: self.callback}

    def to_dict(self) -> dict[str, Any]:
        # This is the complete factory-owned reconstruction state.  It carries
        # relative archive references and immutable typed inputs, never a live
        # callback object or a machine-specific absolute path.
        return {
            "protocol": PERMUTER_PROVIDER_PROTOCOL,
            "module_identity": MODULE_IDENTITY,
            "lane": self.config.lane,
            "manifest": self.manifest.to_dict(),
            "manifest_identity": self.manifest_identity,
            "manifest_tool_identity": self.manifest_tool_identity,
            "config": self.config.to_dict(),
            "config_identity": self.config.identity,
            "binding": self.binding.to_dict(),
            "binding_identity": self.binding.identity,
            "tool_identity": self.binding.tool_identity,
            "weights_identity": self.binding.weights_identity,
            "algorithm": self.config.algorithm,
            "algorithm_identity": self.config.algorithm_identity,
            "provider_identity": self.provider_identity,
            "inputs": [
                self.inputs[key].to_dict() for key in sorted(self.inputs)
            ],
            "input_identities": [
                self.inputs[key].input_identity for key in sorted(self.inputs)
            ],
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        archive: ContentAddressedArchive,
        executor_callback: Optional[Callable[[PermuterRequest], Mapping[str, Any]]] = None,
    ) -> "PermuterLaneProvider":
        """Reconstruct one provider only from verified factory-owned state."""
        if not isinstance(archive, ContentAddressedArchive):
            raise PermuterProviderInputError(
                "provider reconstruction requires a ContentAddressedArchive"
            )
        data = _strict(
            value,
            (
                "protocol",
                "module_identity",
                "lane",
                "manifest",
                "manifest_identity",
                "manifest_tool_identity",
                "config",
                "config_identity",
                "binding",
                "binding_identity",
                "tool_identity",
                "weights_identity",
                "algorithm",
                "algorithm_identity",
                "provider_identity",
                "inputs",
                "input_identities",
            ),
            (),
            "permuter provider reconstruction",
        )
        if data["protocol"] != PERMUTER_PROVIDER_PROTOCOL:
            raise PermuterProviderInputError("provider protocol differs")
        if data["module_identity"] != MODULE_IDENTITY:
            raise PermuterProviderInputError("provider module identity differs")
        manifest = RunManifest.from_dict(data["manifest"])
        manifest_identity = _manifest_identity(manifest)
        if data["manifest_identity"] != manifest_identity:
            raise PermuterProviderInputError("manifest identity changed")
        config = PermuterLaneConfig.from_dict(data["config"])
        if data["lane"] != config.lane:
            raise PermuterProviderInputError("provider lane differs from config")
        if data["config_identity"] != config.identity:
            raise PermuterProviderInputError("provider config identity changed")
        if data["algorithm"] != config.algorithm:
            raise PermuterProviderInputError("provider algorithm changed")
        if data["algorithm_identity"] != config.algorithm_identity:
            raise PermuterProviderInputError("provider algorithm identity changed")
        binding = PermuterToolBinding.from_dict(data["binding"], archive=archive)
        if binding.lane != config.lane:
            raise PermuterProviderInputError("provider binding lane differs from config")
        if data["binding_identity"] != binding.identity:
            raise PermuterProviderInputError("provider binding identity changed")
        if data["tool_identity"] != binding.tool_identity:
            raise PermuterProviderInputError("provider tool identity changed")
        if data["weights_identity"] != binding.weights_identity:
            raise PermuterProviderInputError("provider weights identity changed")
        if binding.available:
            binding.verify(archive)
        raw_inputs = data["inputs"]
        if (
            isinstance(raw_inputs, (str, bytes, bytearray))
            or not isinstance(raw_inputs, Sequence)
        ):
            raise PermuterProviderInputError("provider inputs must be a sequence")
        inputs = tuple(ArchivedPermuterInput.from_dict(item) for item in raw_inputs)
        for item in inputs:
            item.verify(archive)
        expected_input_ids = [item.input_identity for item in sorted(inputs, key=lambda item: item.recipient_id)]
        if list(data["input_identities"]) != expected_input_ids:
            raise PermuterProviderInputError("provider input identities changed")
        provider = cls(
            manifest,
            inputs,
            archive=archive,
            binding=binding,
            config=config,
            executor_callback=executor_callback,
        )
        if data["manifest_tool_identity"] != provider.manifest_tool_identity:
            raise PermuterProviderInputError("manifest tool identity changed")
        if data["provider_identity"] != provider.provider_identity:
            raise PermuterProviderInputError("provider identity changed")
        return provider



PermuterRandomProvider = PermuterLaneProvider
PermuterTargetedProvider = PermuterLaneProvider
PermuterRecombineProvider = PermuterLaneProvider
PermuterDdminProvider = PermuterLaneProvider


def _coerce_binding(
    lane: str,
    binding: Optional[PermuterToolBinding],
) -> PermuterToolBinding:
    if binding is not None:
        return binding
    return PermuterToolBinding(
        lane=lane,
        vendor_revision=hash_canonical({"protocol": PERMUTER_BINDING_PROTOCOL, "lane": lane, "state": "unavailable"}),
        algorithm=default_permuter_config(lane).algorithm,
        available=False,
        unavailable_reason="no pinned vendored tool binding was supplied",
    )


def build_permuter_provider(
    lane: str,
    manifest: RunManifest,
    inputs: Mapping[str, ArchivedPermuterInput] | Sequence[ArchivedPermuterInput],
    *,
    archive: ContentAddressedArchive,
    binding: Optional[PermuterToolBinding] = None,
    config: Optional[PermuterLaneConfig] = None,
    executor_callback: Optional[Callable[[PermuterRequest], Mapping[str, Any]]] = None,
) -> PermuterLaneProvider:
    if lane not in PERMUTER_LANES:
        raise PermuterProviderInputError("unsupported permuter lane")
    owned_config = config or default_permuter_config(lane)
    if owned_config.lane != lane:
        raise PermuterProviderInputError("config lane differs from requested lane")
    owned_binding = _coerce_binding(lane, binding)
    if owned_binding.lane != lane:
        raise PermuterProviderInputError("binding lane differs from requested lane")
    return PermuterLaneProvider(
        manifest,
        inputs,
        archive=archive,
        binding=owned_binding,
        config=owned_config,
        executor_callback=executor_callback,
    )


def build_permuter_random_provider(*args: Any, **kwargs: Any) -> PermuterLaneProvider:
    return build_permuter_provider(PERMUTER_RANDOM_LANE, *args, **kwargs)


def build_permuter_targeted_provider(*args: Any, **kwargs: Any) -> PermuterLaneProvider:
    return build_permuter_provider(PERMUTER_TARGETED_LANE, *args, **kwargs)


def build_permuter_recombine_provider(*args: Any, **kwargs: Any) -> PermuterLaneProvider:
    return build_permuter_provider(PERMUTER_RECOMBINE_LANE, *args, **kwargs)


def build_permuter_ddmin_provider(*args: Any, **kwargs: Any) -> PermuterLaneProvider:
    return build_permuter_provider(PERMUTER_DDMIN_LANE, *args, **kwargs)


def _adapter_builder(
    lane: str,
    manifest: RunManifest,
    inputs: Mapping[str, ArchivedPermuterInput] | Sequence[ArchivedPermuterInput],
    *,
    archive: ContentAddressedArchive,
    binding: Optional[PermuterToolBinding],
    config: Optional[PermuterLaneConfig],
    executor_callback: Optional[Callable[[PermuterRequest], Mapping[str, Any]]],
) -> Callable[[Recipient], Mapping[str, Any]]:
    return build_permuter_provider(
        lane,
        manifest,
        inputs,
        archive=archive,
        binding=binding,
        config=config,
        executor_callback=executor_callback,
    ).callback


def permuter_random_adapter(*args: Any, **kwargs: Any) -> Callable[[Recipient], Mapping[str, Any]]:
    return _adapter_builder(PERMUTER_RANDOM_LANE, *args, **kwargs)


def permuter_targeted_adapter(*args: Any, **kwargs: Any) -> Callable[[Recipient], Mapping[str, Any]]:
    return _adapter_builder(PERMUTER_TARGETED_LANE, *args, **kwargs)


def permuter_recombine_adapter(*args: Any, **kwargs: Any) -> Callable[[Recipient], Mapping[str, Any]]:
    return _adapter_builder(PERMUTER_RECOMBINE_LANE, *args, **kwargs)


def permuter_ddmin_adapter(*args: Any, **kwargs: Any) -> Callable[[Recipient], Mapping[str, Any]]:
    return _adapter_builder(PERMUTER_DDMIN_LANE, *args, **kwargs)


def build_permuter_lane_adapters(
    manifest: RunManifest,
    inputs: Mapping[str, ArchivedPermuterInput] | Sequence[ArchivedPermuterInput],
    *,
    archive: ContentAddressedArchive,
    bindings: Optional[Mapping[str, PermuterToolBinding]] = None,
    configs: Optional[Mapping[str, PermuterLaneConfig]] = None,
    executors: Optional[Mapping[str, Callable[[PermuterRequest], Mapping[str, Any]]]] = None,
) -> dict[str, Callable[[Recipient], Mapping[str, Any]]]:
    if not isinstance(manifest, RunManifest):
        raise PermuterProviderInputError("lane adapters require a typed RunManifest")
    bindings = bindings or {}
    configs = configs or {}
    executors = executors or {}
    adapters: dict[str, Callable[[Recipient], Mapping[str, Any]]] = {}
    for lane in PERMUTER_LANES:
        if lane in manifest.selected_lanes:
            callback = build_permuter_provider(
                lane,
                manifest,
                inputs,
                archive=archive,
                binding=bindings.get(lane),
                config=configs.get(lane),
                executor_callback=executors.get(lane),
            ).callback
            adapters[lane] = callback
    if not adapters:
        raise PermuterProviderInputError("manifest selects no permuter lane")
    return adapters


make_permuter_random_adapter = permuter_random_adapter
make_permuter_targeted_adapter = permuter_targeted_adapter
make_permuter_recombine_adapter = permuter_recombine_adapter
make_permuter_ddmin_adapter = permuter_ddmin_adapter
make_permuter_lane_adapters = build_permuter_lane_adapters


__all__ = [
    "ArchivedPermuterInput",
    "MODULE_IDENTITY",
    "PERMUTER_BINDING_PROTOCOL",
    "PERMUTER_CHECKPOINT_CATEGORY",
    "PERMUTER_CHECKPOINT_PROTOCOL",
    "PERMUTER_CONFIG_PROTOCOL",
    "PERMUTER_DDMIN_LANE",
    "PERMUTER_EVALUATOR_PROTOCOL",
    "PERMUTER_INPUT_PROTOCOL",
    "PERMUTER_LANES",
    "PERMUTER_MAX_CALLS",
    "PERMUTER_MAX_CANDIDATES",
    "PERMUTER_MAX_CANDIDATE_CHARS",
    "PERMUTER_MAX_ITERATIONS",
    "PERMUTER_MAX_STATE_BYTES",
    "PERMUTER_PROVIDER_PROTOCOL",
    "PERMUTER_RANDOM_LANE",
    "PERMUTER_RECOMBINE_LANE",
    "PERMUTER_REQUEST_CATEGORY",
    "PERMUTER_REQUEST_PROTOCOL",
    "PERMUTER_RESPONSE_CATEGORY",
    "PERMUTER_RESPONSE_PROTOCOL",
    "PERMUTER_RESULT_CATEGORY",
    "PERMUTER_RESULT_PROTOCOL",
    "PERMUTER_SCRATCH_PROTOCOL",
    "PERMUTER_STOP_CATEGORY",
    "PERMUTER_STOP_PROTOCOL",
    "PERMUTER_TARGETED_LANE",
    "PermuterBudget",
    "PermuterCandidate",
    "PermuterCheckpoint",
    "PermuterDdminProvider",
    "PermuterHandoffStore",
    "PermuterInput",
    "PermuterLaneConfig",
    "PermuterLaneProvider",
    "PermuterProviderError",
    "PermuterProviderHandoffError",
    "PermuterProviderHandoffPending",
    "PermuterProviderInputError",
    "PermuterProviderInvalidResponse",
    "PermuterProviderRefused",
    "PermuterProviderRequest",
    "PermuterProviderResponse",
    "PermuterProviderResult",
    "PermuterProviderTimeout",
    "PermuterProviderUnavailable",
    "PermuterRandomProvider",
    "PermuterRawCandidate",
    "PermuterRecombineProvider",
    "PermuterSeedInput",
    "PermuterTargetedProvider",
    "PermuterToolBinding",
    "ProviderHandoffPending",
    "ProviderInvalidResponse",
    "ProviderRefused",
    "ProviderTimeout",
    "ProviderUnavailable",
    "build_permuter_ddmin_provider",
    "build_permuter_lane_adapters",
    "build_permuter_provider",
    "build_permuter_random_provider",
    "build_permuter_recombine_provider",
    "build_permuter_targeted_provider",
    "default_permuter_config",
    "make_permuter_ddmin_adapter",
    "make_permuter_lane_adapters",
    "make_permuter_random_adapter",
    "make_permuter_recombine_adapter",
    "make_permuter_targeted_adapter",
    "permuter_ddmin_adapter",
    "permuter_random_adapter",
    "permuter_recombine_adapter",
    "permuter_targeted_adapter",
]
