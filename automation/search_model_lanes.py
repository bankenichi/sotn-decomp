"""Durable, proposal-only adapters for the two model search lanes.

The model lanes are deliberately boring at this boundary.  They receive a
manifest and an explicit set of archive-backed target inputs, materialize a
request record before invoking a typed provider, and return the same ordinary
mapping consumed by :mod:`search_lanes`.  They never claim queue records,
inspect a checkout, write source, or call a compiler or oracle.

The provider object is a narrow protocol rather than a public callback.  A
production integration can implement the protocol, while tests can use a
small typed double.  Provider responses are archived before parsing and the
request, response, and parsed result are all reconstructable after a process
loss.  A durable handoff is preferred over invoking the provider again.
"""

from __future__ import annotations

import json
import re
import string
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence, Tuple, runtime_checkable

try:
    from .search_archive import ArchiveError, ContentAddressedArchive
    from .search_coordinator import LANE_TIERS
    from .search_lanes import LaneCandidate, LaneError, Recipient, SubsetViolation
    from .search_types import (
        ArtifactRef,
        Budget,
        CandidateRecord,
        RunManifest,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_lane,
    )
except ImportError:  # pragma: no cover - direct script compatibility
    from search_archive import ArchiveError, ContentAddressedArchive  # type: ignore
    from search_coordinator import LANE_TIERS  # type: ignore
    from search_lanes import LaneCandidate, LaneError, Recipient, SubsetViolation  # type: ignore
    from search_types import (  # type: ignore
        ArtifactRef,
        Budget,
        CandidateRecord,
        RunManifest,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_id,
        validate_lane,
    )


MODEL_FLEET_LANE = "model_fleet"
MODEL_EXPENSIVE_LANE = "model_expensive"
MODEL_LANES = (MODEL_FLEET_LANE, MODEL_EXPENSIVE_LANE)
MODEL_TIER = "model"
MODEL_PROVIDER_PROTOCOL = "sotn-model-provider-v1"
MODEL_TARGET_PROTOCOL = "sotn-model-target-input-v1"
MODEL_REQUEST_PROTOCOL = "sotn-model-request-v1"
MODEL_RESPONSE_PROTOCOL = "sotn-model-response-v1"
MODEL_RESULT_PROTOCOL = "sotn-model-result-v1"
MODEL_HANDOFF_PROTOCOL = "sotn-model-handoff-v1"
ARCHIVE_PROTOCOL = "content-addressed-sha256-v1"
ARCHIVE_IDENTITY = hash_canonical({"protocol": ARCHIVE_PROTOCOL})
MODULE_IDENTITY = hash_canonical(
    {"module": "automation.search_model_lanes", "version": "1.0.0"}
)
SUPPORTED_TARGET_PLATFORMS = frozenset({"us", "hd", "pspeu", "saturn"})

_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_MAX_SYMBOL_BYTES = 512
_MAX_TARGET_BYTES = 512 * 1024
_MAX_CONTEXT_ARTIFACTS = 64
_MAX_CONTEXT_BYTES = 2 * 1024 * 1024
_MAX_PROMPT_BYTES = 3 * 1024 * 1024
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_SOURCE_BYTES = 512 * 1024
_MAX_PARSED_CANDIDATES = 256
_MAX_REASON_BYTES = 2048
_MAX_ERROR_BYTES = 256
_MAX_METADATA_DEPTH = 8

# A model request is a reservation, not merely a log entry.  These names are
# intentionally public so a recovery test can inject a process loss at every
# durability boundary without knowing the implementation's private helpers.
MODEL_FAULT_BEFORE_REQUEST = "before_model_request"
MODEL_FAULT_AFTER_REQUEST = "after_model_request"
MODEL_FAULT_BEFORE_CALLBACK = "before_model_callback"
MODEL_FAULT_AFTER_CALLBACK = "after_model_callback"
MODEL_FAULT_AFTER_RESPONSE = "after_model_response"
MODEL_FAULT_AFTER_RESULT = "after_model_result"
MODEL_FAULT_POINTS = (
    MODEL_FAULT_BEFORE_REQUEST,
    MODEL_FAULT_AFTER_REQUEST,
    MODEL_FAULT_BEFORE_CALLBACK,
    MODEL_FAULT_AFTER_CALLBACK,
    MODEL_FAULT_AFTER_RESPONSE,
    MODEL_FAULT_AFTER_RESULT,
)

ModelFaultHook = Callable[[str], None]

_MODEL_RESPONSE_STATUSES = frozenset(
    {"ok", "unavailable", "timeout", "refused", "invalid"}
)
_MODEL_FAILURE_CODES = {
    "unavailable": "model_provider_unavailable",
    "timeout": "model_provider_timeout",
    "refused": "model_provider_refused",
    "invalid": "model_provider_invalid_response",
}
_RESULT_COMPLETION = frozenset(
    {
        "budget_exhausted",
        "search_space_exhausted",
        "inapplicable",
    }
)


class ModelLaneError(LaneError):
    """Base class for model lane validation failures."""


class ModelInputError(ModelLaneError):
    """A manifest, binding, or archived input is malformed."""


class ModelArtifactError(ModelLaneError):
    """An archive-backed model input or handoff is missing or corrupt."""


class ModelUnavailable(ModelLaneError):
    """The configured model dependency is unavailable."""


class ModelTimeout(ModelLaneError):
    """A typed model provider timeout."""


class ModelRefused(ModelLaneError):
    """A typed provider refusal."""


class ModelInvalidResponse(ModelLaneError):
    """The provider returned a response outside its typed contract."""


class ModelReplayError(ModelLaneError):
    """A durable request/result handoff does not match this run."""


class ModelSubsetViolation(SubsetViolation, ModelLaneError):
    """A target or callback recipient is outside the frozen manifest subset."""


class ModelBudgetError(ModelLaneError):
    """The selected model lane has an unsupported budget."""


class ModelProviderProtocolError(ModelLaneError):
    """An object does not implement the typed provider protocol."""


def _call_fault(hook: Optional[ModelFaultHook], point: str) -> None:
    """Invoke one optional one-shot process-loss hook."""

    if hook is not None:
        hook(point)


@runtime_checkable
class ModelProvider(Protocol):
    """The only invocation surface accepted by a model lane.

    Implementations must return :class:`ModelResponse` and must not mutate
    repository state.  The request already contains all identity bindings;
    prompt and contexts are passed as immutable values so a provider cannot
    infer a path or query a live queue.
    """

    def invoke(
        self,
        request: "ModelRequest",
        *,
        prompt: str,
        contexts: Tuple[bytes, ...],
    ) -> "ModelResponse":
        ...


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, ArtifactRef):
        return value.to_dict()
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _plain(value.to_dict())
    raise ModelInputError("model record contains a non-JSON value")


def _freeze_json(value: Any, label: str, depth: int = 0) -> Any:
    if depth > _MAX_METADATA_DEPTH:
        raise ModelInputError(f"{label} exceeds metadata nesting bound")
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ModelInputError(f"{label} mapping keys must be strings")
        return MappingProxyType(
            {
                key: _freeze_json(item, f"{label}.{key}", depth + 1)
                for key, item in value.items()
            }
        )
    if isinstance(value, (tuple, list)):
        return tuple(
            _freeze_json(item, f"{label}[{index}]", depth + 1)
            for index, item in enumerate(value)
        )
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ModelInputError(f"{label} must contain JSON-compatible values")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_thaw(item) for item in value]
    return value


def _identity(value: Any, label: str) -> str:
    try:
        return validate_hash(value, label)
    except Exception as exc:
        raise ModelInputError(f"{label} must be a sha256 identity") from exc


def _text(value: Any, label: str, maximum: int, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        raise ModelInputError(f"{label} must be {'nonempty ' if nonempty else ''}text")
    if len(value.encode("utf-8")) > maximum:
        raise ModelInputError(f"{label} exceeds its size bound")
    return value


def _artifact(value: Any, label: str) -> ArtifactRef:
    try:
        result = value if isinstance(value, ArtifactRef) else ArtifactRef.from_dict(value)
    except Exception as exc:
        raise ModelArtifactError(f"{label} is not an artifact reference") from exc
    return result


def _artifact_dict(value: ArtifactRef) -> dict[str, Any]:
    return value.to_dict()


def _archive_verify(
    archive: ContentAddressedArchive,
    reference: ArtifactRef,
    expected: Optional[bytes],
    label: str,
) -> bytes:
    try:
        actual = archive.verify(reference)
    except (ArchiveError, OSError, ValueError) as exc:
        raise ModelArtifactError(f"{label} is missing or corrupt") from exc
    if expected is not None and actual != expected:
        raise ModelArtifactError(f"{label} bytes disagree with its artifact identity")
    return actual


def _verify_target_archives(
    archive: ContentAddressedArchive,
    target: ArchivedModelTargetInput,
) -> None:
    """Require every model input to exist in the immutable run archive."""

    _archive_verify(archive, target.target_artifact, target.target_bytes, "model target artifact")
    for index, (reference, data) in enumerate(
        zip(target.context_artifacts, target.context_bytes)
    ):
        _archive_verify(archive, reference, data, f"model context artifact {index}")


def _safe_artifact_path(reference: ArtifactRef, prefix: str, label: str) -> None:
    if not reference.path.startswith(prefix) or ".." in reference.path.split("/"):
        raise ModelArtifactError(f"{label} must use the canonical {prefix} archive")


def _is_hex_identity(value: str) -> bool:
    return isinstance(value, str) and (
        _HEX_64.fullmatch(value.removeprefix("sha256:")) is not None
    )


@dataclass(frozen=True)
class ArchivedModelTargetInput:
    """One immutable target and all context the model is allowed to see."""

    recipient_id: str
    target_identity: str
    target_artifact: ArtifactRef
    target_bytes: bytes
    symbol: str
    platform: str = ""
    context_artifacts: Tuple[ArtifactRef, ...] = ()
    context_bytes: Tuple[bytes, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            validate_id(self.recipient_id, "model target recipient_id")
            _identity(self.target_identity, "model target_identity")
        except Exception as exc:
            if isinstance(exc, ModelLaneError):
                raise
            raise ModelInputError("invalid model target identity") from exc
        if not isinstance(self.target_artifact, ArtifactRef):
            object.__setattr__(self, "target_artifact", _artifact(self.target_artifact, "target_artifact"))
        _safe_artifact_path(
            self.target_artifact,
            "artifacts/target-assembly/",
            "target_artifact",
        )
        if not isinstance(self.target_bytes, bytes) or not self.target_bytes:
            raise ModelArtifactError("target_bytes must be nonempty bytes")
        if len(self.target_bytes) > _MAX_TARGET_BYTES:
            raise ModelArtifactError("target_bytes exceeds the immutable bound")
        if hash_bytes(self.target_bytes) != self.target_artifact.content_hash:
            raise ModelArtifactError("target bytes disagree with target artifact")
        try:
            self.target_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ModelArtifactError("target bytes must be UTF-8 text") from exc
        if not isinstance(self.symbol, str) or not self.symbol:
            raise ModelInputError("model target symbol must be nonempty")
        if len(self.symbol.encode("utf-8")) > _MAX_SYMBOL_BYTES:
            raise ModelInputError("model target symbol is too long")
        recipient_platform = self.recipient_id.split(":", 1)[0]
        if recipient_platform not in SUPPORTED_TARGET_PLATFORMS:
            raise ModelInputError("model target recipient platform is unsupported")
        if not isinstance(self.platform, str) or len(self.platform.encode("utf-8")) > 64:
            raise ModelInputError("model target platform is invalid")
        if self.platform and self.platform != recipient_platform:
            raise ModelInputError("model target platform differs from recipient")
        if not self.platform:
            object.__setattr__(self, "platform", recipient_platform)
        artifacts = tuple(self.context_artifacts)
        contexts = tuple(self.context_bytes)
        if len(artifacts) != len(contexts):
            raise ModelArtifactError("context artifacts and bytes must have equal length")
        if len(artifacts) > _MAX_CONTEXT_ARTIFACTS:
            raise ModelArtifactError("too many context artifacts")
        total = 0
        normalized_artifacts = []
        normalized_contexts = []
        for index, (reference, data) in enumerate(zip(artifacts, contexts)):
            reference = _artifact(reference, f"context_artifacts[{index}]")
            if not isinstance(data, bytes):
                raise ModelArtifactError(f"context_bytes[{index}] must be bytes")
            total += len(data)
            if total > _MAX_CONTEXT_BYTES:
                raise ModelArtifactError("context bytes exceed the immutable bound")
            if hash_bytes(data) != reference.content_hash:
                raise ModelArtifactError(f"context {index} bytes disagree with artifact")
            try:
                data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ModelArtifactError(f"context {index} bytes must be UTF-8 text") from exc
            normalized_artifacts.append(reference)
            normalized_contexts.append(data)
        if len({item.content_hash for item in normalized_artifacts}) != len(normalized_artifacts):
            raise ModelArtifactError("context artifacts must be unique")
        object.__setattr__(self, "context_artifacts", tuple(normalized_artifacts))
        object.__setattr__(self, "context_bytes", tuple(normalized_contexts))
        if not isinstance(self.metadata, Mapping):
            raise ModelInputError("model target metadata must be a mapping")
        object.__setattr__(
            self,
            "metadata",
            _freeze_json(dict(self.metadata), "model target metadata"),
        )

    @property
    def evidence_identity(self) -> str:
        return hash_canonical(self._evidence_payload())

    @property
    def input_identity(self) -> str:
        return self.evidence_identity

    def _evidence_payload(self) -> dict[str, Any]:
        return {
            "protocol": MODEL_TARGET_PROTOCOL,
            "recipient_id": self.recipient_id,
            "target_identity": self.target_identity,
            "target_artifact": _artifact_dict(self.target_artifact),
            "symbol": self.symbol,
            "platform": self.platform,
            "context_artifacts": [_artifact_dict(item) for item in self.context_artifacts],
            "metadata": _thaw(self.metadata),
        }

    def to_dict(self, *, include_bytes: bool = True) -> dict[str, Any]:
        value = self._evidence_payload()
        if include_bytes:
            value["target_bytes"] = self.target_bytes.decode("utf-8", errors="surrogateescape")
            value["target_bytes_encoding"] = "utf-8-surrogateescape"
            value["context_bytes"] = [
                item.decode("utf-8", errors="surrogateescape") for item in self.context_bytes
            ]
            value["context_bytes_encoding"] = "utf-8-surrogateescape"
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ArchivedModelTargetInput":
        if not isinstance(value, Mapping):
            raise ModelInputError("model target input must be an object")
        required = {
            "protocol", "recipient_id", "target_identity", "target_artifact", "target_bytes",
            "target_bytes_encoding", "symbol", "platform", "context_artifacts", "context_bytes",
            "context_bytes_encoding", "metadata",
        }
        if set(value) != required or value.get("protocol") != MODEL_TARGET_PROTOCOL:
            raise ModelInputError("model target input has the wrong schema")
        if value["target_bytes_encoding"] != "utf-8-surrogateescape" or value["context_bytes_encoding"] != "utf-8-surrogateescape":
            raise ModelInputError("model target input has an unsupported byte encoding")
        if not isinstance(value["target_bytes"], str) or not isinstance(value["context_bytes"], (list, tuple)):
            raise ModelInputError("model target input byte fields are malformed")
        if any(not isinstance(item, str) for item in value["context_bytes"]):
            raise ModelInputError("model target context byte fields are malformed")
        try:
            target_bytes = str(value["target_bytes"]).encode("utf-8", errors="surrogateescape")
            context_values = tuple(value["context_bytes"])
            context_bytes = tuple(
                str(item).encode("utf-8", errors="surrogateescape") for item in context_values
            )
        except (TypeError, UnicodeError) as exc:
            raise ModelInputError("model target input bytes are malformed") from exc
        artifacts = tuple(_artifact(item, "context_artifact") for item in value["context_artifacts"])
        return cls(
            recipient_id=value["recipient_id"],
            target_identity=value["target_identity"],
            target_artifact=_artifact(value["target_artifact"], "target_artifact"),
            target_bytes=target_bytes,
            symbol=value["symbol"],
            platform=value["platform"],
            context_artifacts=artifacts,
            context_bytes=context_bytes,
            metadata=value["metadata"],
        )


ModelTargetInput = ArchivedModelTargetInput


@dataclass(frozen=True)
class ModelBinding:
    """Exact identities and immutable limits for one model configuration."""

    provider_identity: str
    model_identity: str
    model_name: str
    prompt_identity: str
    prompt_template: str
    reasoning_identity: str
    reasoning: str
    config_identity: str
    tool_identity: str
    max_candidates: int = 8
    max_response_bytes: int = _MAX_RESPONSE_BYTES

    def __post_init__(self) -> None:
        for name in (
            "provider_identity", "model_identity", "prompt_identity", "reasoning_identity",
            "config_identity", "tool_identity",
        ):
            _identity(getattr(self, name), f"model binding {name}")
        _text(self.model_name, "model_name", 256)
        _text(self.prompt_template, "prompt_template", _MAX_PROMPT_BYTES)
        _text(self.reasoning, "reasoning", 256)
        if hash_bytes(self.prompt_template.encode("utf-8")) != self.prompt_identity:
            raise ModelInputError("prompt_identity does not identify prompt_template")
        if isinstance(self.max_candidates, bool) or not isinstance(self.max_candidates, int) or not 0 <= self.max_candidates <= _MAX_PARSED_CANDIDATES:
            raise ModelInputError("max_candidates is outside the immutable bound")
        if isinstance(self.max_response_bytes, bool) or not isinstance(self.max_response_bytes, int) or not 1 <= self.max_response_bytes <= _MAX_RESPONSE_BYTES:
            raise ModelInputError("max_response_bytes is outside the immutable bound")

    @property
    def binding_identity(self) -> str:
        return hash_canonical(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": MODEL_PROVIDER_PROTOCOL,
            "provider_identity": self.provider_identity,
            "model_identity": self.model_identity,
            "model_name": self.model_name,
            "prompt_identity": self.prompt_identity,
            "prompt_template": self.prompt_template,
            "reasoning_identity": self.reasoning_identity,
            "reasoning": self.reasoning,
            "config_identity": self.config_identity,
            "tool_identity": self.tool_identity,
            "max_candidates": self.max_candidates,
            "max_response_bytes": self.max_response_bytes,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelBinding":
        if not isinstance(value, Mapping):
            raise ModelInputError("model binding must be an object")
        fields = {
            "protocol", "provider_identity", "model_identity", "model_name", "prompt_identity",
            "prompt_template", "reasoning_identity", "reasoning", "config_identity",
            "tool_identity", "max_candidates", "max_response_bytes",
        }
        if set(value) != fields or value.get("protocol") != MODEL_PROVIDER_PROTOCOL:
            raise ModelInputError("model binding has the wrong schema")
        return cls(
            provider_identity=value["provider_identity"],
            model_identity=value["model_identity"],
            model_name=value["model_name"],
            prompt_identity=value["prompt_identity"],
            prompt_template=value["prompt_template"],
            reasoning_identity=value["reasoning_identity"],
            reasoning=value["reasoning"],
            config_identity=value["config_identity"],
            tool_identity=value["tool_identity"],
            max_candidates=value["max_candidates"],
            max_response_bytes=value["max_response_bytes"],
        )


def _render_prompt(binding: ModelBinding, target: ArchivedModelTargetInput) -> str:
    """Render only a fixed placeholder vocabulary into a bounded prompt."""

    allowed = {"symbol", "target_identity", "platform", "context"}
    formatter = string.Formatter()
    for _, field_name, format_spec, conversion in formatter.parse(binding.prompt_template):
        if field_name is None:
            continue
        if field_name not in allowed or format_spec or conversion:
            raise ModelInputError("prompt_template contains an unsupported placeholder")
    context_parts = [
        "context[{}] {}\n{}".format(
            index,
            reference.content_hash,
            data.decode("utf-8", errors="replace"),
        )
        for index, (reference, data) in enumerate(
            zip(target.context_artifacts, target.context_bytes)
        )
    ]
    context = "\n".join(context_parts)
    try:
        rendered = binding.prompt_template.format(
            symbol=target.symbol,
            target_identity=target.target_identity,
            platform=target.platform,
            context=(
                target.target_bytes.decode("utf-8", errors="replace")
                + ("\n" + context if context else "")
            ),
        )
    except (IndexError, KeyError, ValueError) as exc:
        raise ModelInputError("prompt_template cannot be rendered") from exc
    _text(rendered, "rendered prompt", _MAX_PROMPT_BYTES)
    return rendered


@dataclass(frozen=True)
class ModelRequest:
    """The exact durable handoff sent to one typed provider."""

    request_id: str
    lane: str
    recipient_id: str
    manifest_identity: str
    subset_identity: str
    target_identity: str
    context_artifact_identities: Tuple[str, ...]
    provider_identity: str
    model_identity: str
    model_name: str
    prompt_identity: str
    reasoning_identity: str
    reasoning: str
    config_identity: str
    tool_identity: str
    budget_identity: str
    prompt_artifact: ArtifactRef
    ordinal: int
    external_call_limit: Optional[int] = None
    call_charge_identity: str = ""
    request_artifact: Optional[ArtifactRef] = None

    def __post_init__(self) -> None:
        if self.lane not in MODEL_LANES:
            raise ModelInputError("model request lane is not a model lane")
        for name in (
            "request_id", "manifest_identity", "subset_identity", "target_identity",
            "provider_identity", "model_identity", "prompt_identity", "reasoning_identity",
            "config_identity", "tool_identity", "budget_identity",
        ):
            _identity(getattr(self, name), f"model request {name}")
        _text(self.model_name, "model request model_name", 256)
        _text(self.reasoning, "model request reasoning", 256)
        try:
            validate_id(self.recipient_id, "model request recipient_id")
        except Exception as exc:
            raise ModelInputError("invalid model request recipient") from exc
        contexts = tuple(self.context_artifact_identities)
        if len(contexts) > _MAX_CONTEXT_ARTIFACTS:
            raise ModelInputError("model request has too many contexts")
        for item in contexts:
            _identity(item, "model request context identity")
        object.__setattr__(self, "context_artifact_identities", contexts)
        if isinstance(self.ordinal, bool) or not isinstance(self.ordinal, int) or self.ordinal < 0:
            raise ModelInputError("model request ordinal must be nonnegative")
        if (
            isinstance(self.external_call_limit, bool)
            or not isinstance(self.external_call_limit, int)
            or self.external_call_limit < 0
        ):
            raise ModelBudgetError("model request external call limit is invalid")
        if self.call_charge_identity:
            _identity(self.call_charge_identity, "model request call_charge_identity")
        object.__setattr__(self, "prompt_artifact", _artifact(self.prompt_artifact, "prompt_artifact"))
        _safe_artifact_path(self.prompt_artifact, "artifacts/model-prompts/", "prompt_artifact")
        if self.request_artifact is not None:
            object.__setattr__(self, "request_artifact", _artifact(self.request_artifact, "request_artifact"))
            _safe_artifact_path(self.request_artifact, "artifacts/model-requests/", "request_artifact")
        if self.request_id != hash_canonical(self.identity_payload()):
            raise ModelReplayError("model request_id does not match its exact identities")
        if self.call_charge_identity and self.call_charge_identity != hash_canonical(
            {
                "protocol": "sotn-model-call-charge-v1",
                "request_id": self.request_id,
                "external_call_limit": self.external_call_limit,
            }
        ):
            raise ModelReplayError("model request call charge does not match its identity")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": MODEL_REQUEST_PROTOCOL,
            "lane": self.lane,
            "recipient_id": self.recipient_id,
            "manifest_identity": self.manifest_identity,
            "subset_identity": self.subset_identity,
            "target_identity": self.target_identity,
            "context_artifact_identities": list(self.context_artifact_identities),
            "provider_identity": self.provider_identity,
            "model_identity": self.model_identity,
            "model_name": self.model_name,
            "prompt_identity": self.prompt_identity,
            "reasoning_identity": self.reasoning_identity,
            "reasoning": self.reasoning,
            "config_identity": self.config_identity,
            "tool_identity": self.tool_identity,
            "budget_identity": self.budget_identity,
            "prompt_artifact": _artifact_dict(self.prompt_artifact),
            "ordinal": self.ordinal,
            "external_call_limit": self.external_call_limit,
        }

    def to_dict(self) -> dict[str, Any]:
        value = self.identity_payload()
        value["request_id"] = self.request_id
        value["request_artifact"] = (
            _artifact_dict(self.request_artifact) if self.request_artifact is not None else None
        )
        value["call_charge_identity"] = self.call_charge_identity
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelRequest":
        if not isinstance(value, Mapping):
            raise ModelReplayError("model request must be an object")
        fields = {
            "protocol", "lane", "recipient_id", "manifest_identity", "subset_identity",
            "target_identity", "context_artifact_identities", "provider_identity",
            "model_identity", "model_name", "prompt_identity", "reasoning_identity", "reasoning",
            "config_identity", "tool_identity", "budget_identity", "prompt_artifact", "ordinal", "request_id",
            "request_artifact", "external_call_limit", "call_charge_identity",
        }
        # Requests written by the pre-budget implementation remain readable so
        # a legacy run can be refused safely instead of silently re-invoking a
        # provider.  New requests always carry the explicit charge fields.
        legacy_fields = fields - {"external_call_limit", "call_charge_identity"}
        if set(value) not in (fields, legacy_fields) or value.get("protocol") != MODEL_REQUEST_PROTOCOL:
            raise ModelReplayError("model request has the wrong schema")
        prompt_artifact = _artifact(value["prompt_artifact"], "prompt_artifact")
        request_artifact = value["request_artifact"]
        if request_artifact is not None:
            request_artifact = _artifact(request_artifact, "request_artifact")
        return cls(
            request_id=value["request_id"],
            lane=value["lane"],
            recipient_id=value["recipient_id"],
            manifest_identity=value["manifest_identity"],
            subset_identity=value["subset_identity"],
            target_identity=value["target_identity"],
            context_artifact_identities=tuple(value["context_artifact_identities"]),
            provider_identity=value["provider_identity"],
            model_identity=value["model_identity"],
            model_name=value["model_name"],
            prompt_identity=value["prompt_identity"],
            reasoning_identity=value["reasoning_identity"],
            reasoning=value["reasoning"],
            config_identity=value["config_identity"],
            tool_identity=value["tool_identity"],
            budget_identity=value["budget_identity"],
            prompt_artifact=prompt_artifact,
            ordinal=value["ordinal"],
            external_call_limit=value.get("external_call_limit"),
            call_charge_identity=value.get("call_charge_identity", ""),
            request_artifact=request_artifact,
        )


@dataclass(frozen=True)
class ModelResponse:
    """A typed response body before the lane assigns its archive reference."""

    request_id: str
    status: str
    response_text: str = ""
    error_code: str = ""
    detail: str = ""
    response_identity: str = ""
    response_artifact: Optional[ArtifactRef] = None

    def __post_init__(self) -> None:
        _identity(self.request_id, "model response request_id")
        if self.status not in _MODEL_RESPONSE_STATUSES:
            raise ModelInvalidResponse("unknown model response status")
        _text(self.response_text, "response_text", _MAX_RESPONSE_BYTES, nonempty=False)
        error_code = self.error_code
        if self.status != "ok" and not error_code:
            error_code = _MODEL_FAILURE_CODES[self.status]
            object.__setattr__(self, "error_code", error_code)
        _text(error_code, "error_code", _MAX_ERROR_BYTES, nonempty=False)
        _text(self.detail, "response detail", _MAX_REASON_BYTES, nonempty=False)
        expected = hash_canonical(self.identity_payload_without_identity())
        if self.response_identity and self.response_identity != expected:
            raise ModelReplayError("response_identity does not match response body")
        object.__setattr__(self, "response_identity", expected)
        if self.status == "ok" and (self.error_code or self.detail and not self.response_text):
            raise ModelInvalidResponse("successful response carries failure metadata")
        if self.response_artifact is not None:
            object.__setattr__(self, "response_artifact", _artifact(self.response_artifact, "response_artifact"))
            _safe_artifact_path(self.response_artifact, "artifacts/model-responses/", "response_artifact")

    def identity_payload_without_identity(self) -> dict[str, Any]:
        return {
            "protocol": MODEL_RESPONSE_PROTOCOL,
            "request_id": self.request_id,
            "status": self.status,
            "body_identity": hash_bytes(self.response_text.encode("utf-8")),
            "response_text": self.response_text,
            "error_code": self.error_code,
            "detail": self.detail,
        }

    def archive_payload(self) -> dict[str, Any]:
        return {
            **self.identity_payload_without_identity(),
            "response_identity": self.response_identity,
        }

    def to_dict(self) -> dict[str, Any]:
        value = self.archive_payload()
        value["response_artifact"] = (
            _artifact_dict(self.response_artifact) if self.response_artifact is not None else None
        )
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelResponse":
        if not isinstance(value, Mapping):
            raise ModelReplayError("model response must be an object")
        fields = {"protocol", "request_id", "status", "body_identity", "response_text", "error_code", "detail", "response_identity", "response_artifact"}
        if set(value) != fields or value.get("protocol") != MODEL_RESPONSE_PROTOCOL:
            raise ModelReplayError("model response has the wrong schema")
        text = value["response_text"]
        if hash_bytes(str(text).encode("utf-8")) != value["body_identity"]:
            raise ModelReplayError("model response body identity is wrong")
        reference = value["response_artifact"]
        return cls(
            request_id=value["request_id"],
            status=value["status"],
            response_text=text,
            error_code=value["error_code"],
            detail=value["detail"],
            response_identity=value["response_identity"],
            response_artifact=(_artifact(reference, "response_artifact") if reference is not None else None),
        )


@dataclass(frozen=True)
class ModelParsedResult:
    """Bounded, serializable parse output retained in a durable result."""

    status: str
    candidate_sources: Tuple[str, ...] = ()
    duplicate_count: int = 0
    refusal_code: str = ""
    reason: str = ""

    def __post_init__(self) -> None:
        if self.status not in _MODEL_RESPONSE_STATUSES:
            raise ModelReplayError("parsed result status is invalid")
        sources = tuple(self.candidate_sources)
        if len(sources) > _MAX_PARSED_CANDIDATES:
            raise ModelReplayError("parsed result exceeds candidate bound")
        for source in sources:
            _text(source, "candidate source", _MAX_SOURCE_BYTES)
        object.__setattr__(self, "candidate_sources", sources)
        if isinstance(self.duplicate_count, bool) or not isinstance(self.duplicate_count, int) or self.duplicate_count < 0:
            raise ModelReplayError("duplicate_count must be nonnegative")
        _text(self.refusal_code, "parsed refusal_code", _MAX_ERROR_BYTES, nonempty=False)
        _text(self.reason, "parsed reason", _MAX_REASON_BYTES, nonempty=False)
        if self.status == "ok" and self.refusal_code:
            raise ModelReplayError("successful parse cannot carry refusal_code")

    @property
    def result_identity(self) -> str:
        return hash_canonical(self.to_dict(include_identity=False))

    def to_dict(self, *, include_identity: bool = True) -> dict[str, Any]:
        value = {
            "protocol": MODEL_RESULT_PROTOCOL,
            "status": self.status,
            "candidate_sources": list(self.candidate_sources),
            "duplicate_count": self.duplicate_count,
            "refusal_code": self.refusal_code,
            "reason": self.reason,
        }
        if include_identity:
            value["result_identity"] = self.result_identity
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelParsedResult":
        if not isinstance(value, Mapping):
            raise ModelReplayError("parsed result must be an object")
        fields = {"protocol", "status", "candidate_sources", "duplicate_count", "refusal_code", "reason", "result_identity"}
        if set(value) != fields or value.get("protocol") != MODEL_RESULT_PROTOCOL:
            raise ModelReplayError("parsed result has the wrong schema")
        if not isinstance(value["candidate_sources"], (list, tuple)):
            raise ModelReplayError("parsed result candidates must be a sequence")
        result = cls(
            status=value["status"],
            candidate_sources=tuple(value["candidate_sources"]),
            duplicate_count=value["duplicate_count"],
            refusal_code=value["refusal_code"],
            reason=value["reason"],
        )
        if value["result_identity"] != result.result_identity:
            raise ModelReplayError("parsed result identity is wrong")
        return result


@dataclass(frozen=True)
class ModelHandoff:
    """Request, response, and parsed result archived as one replay unit."""

    request: ModelRequest
    response: ModelResponse
    result: ModelParsedResult
    result_artifact: ArtifactRef

    def __post_init__(self) -> None:
        if not isinstance(self.request, ModelRequest) or not isinstance(self.response, ModelResponse) or not isinstance(self.result, ModelParsedResult):
            raise ModelReplayError("handoff records must use typed model records")
        if self.response.request_id != self.request.request_id:
            raise ModelReplayError("response does not belong to request")
        object.__setattr__(self, "result_artifact", _artifact(self.result_artifact, "result_artifact"))
        _safe_artifact_path(self.result_artifact, "artifacts/model-results/", "result_artifact")

    def archive_payload(self) -> dict[str, Any]:
        return {
            "protocol": MODEL_HANDOFF_PROTOCOL,
            "request_id": self.request.request_id,
            "response_identity": self.response.response_identity,
            "result": self.result.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": MODEL_HANDOFF_PROTOCOL,
            "request": self.request.to_dict(),
            "response": self.response.to_dict(),
            "result": self.result.to_dict(),
            "result_artifact": _artifact_dict(self.result_artifact),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelHandoff":
        if not isinstance(value, Mapping):
            raise ModelReplayError("model handoff must be an object")
        fields = {"protocol", "request", "response", "result", "result_artifact"}
        if set(value) != fields or value.get("protocol") != MODEL_HANDOFF_PROTOCOL:
            raise ModelReplayError("model handoff has the wrong schema")
        return cls(
            request=ModelRequest.from_dict(value["request"]),
            response=ModelResponse.from_dict(value["response"]),
            result=ModelParsedResult.from_dict(value["result"]),
            result_artifact=_artifact(value["result_artifact"], "result_artifact"),
        )


def _request_artifact_payload(request: ModelRequest) -> dict[str, Any]:
    return {"protocol": MODEL_REQUEST_PROTOCOL, "request": request.identity_payload()}


def _response_from_provider(
    request: ModelRequest,
    response: ModelResponse,
    archive: ContentAddressedArchive,
) -> ModelResponse:
    if not isinstance(response, ModelResponse):
        raise ModelInvalidResponse("provider returned an untyped response")
    if response.request_id != request.request_id:
        raise ModelInvalidResponse("provider response is bound to a different request")
    payload = canonical_bytes(response.archive_payload())
    reference = archive.put_bytes(
        payload,
        category="model-responses",
        suffix=".json",
        media_type="application/json",
    )
    return ModelResponse(
        request_id=response.request_id,
        status=response.status,
        response_text=response.response_text,
        error_code=response.error_code,
        detail=response.detail,
        response_identity=response.response_identity,
        response_artifact=reference,
    )


def _verify_request_archive(archive: ContentAddressedArchive, request: ModelRequest) -> None:
    if request.request_artifact is None:
        raise ModelReplayError("durable request has no request artifact")
    _archive_verify(
        archive,
        request.request_artifact,
        canonical_bytes(_request_artifact_payload(request)),
        "model request artifact",
    )
    _archive_verify(
        archive,
        request.prompt_artifact,
        None,
        "model prompt artifact",
    )


def _verify_response_archive(archive: ContentAddressedArchive, response: ModelResponse) -> None:
    if response.response_artifact is None:
        raise ModelReplayError("durable response has no response artifact")
    data = _archive_verify(
        archive,
        response.response_artifact,
        canonical_bytes(response.archive_payload()),
        "model response artifact",
    )
    try:
        decoded = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ModelReplayError("model response artifact is not canonical JSON") from exc
    if decoded != response.archive_payload():
        raise ModelReplayError("model response artifact payload disagrees with response")


def _verify_result_archive(archive: ContentAddressedArchive, handoff: ModelHandoff) -> None:
    data = _archive_verify(
        archive,
        handoff.result_artifact,
        canonical_bytes(handoff.archive_payload()),
        "model result artifact",
    )
    try:
        decoded = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ModelReplayError("model result artifact is not canonical JSON") from exc
    if decoded != handoff.archive_payload():
        raise ModelReplayError("model result artifact payload disagrees with handoff")


def _parse_model_text(text: str, *, max_response_bytes: int) -> ModelParsedResult:
    if len(text.encode("utf-8")) > max_response_bytes:
        raise ModelInvalidResponse("model response exceeds configured bound")
    try:
        decoded = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ModelInvalidResponse("model response is not JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ModelInvalidResponse("model response must be a JSON object")
    allowed = {"status", "candidates", "reason", "refusal_code"}
    if set(decoded).difference(allowed):
        raise ModelInvalidResponse("model response contains unknown fields")
    status = decoded.get("status", "ok")
    if status != "ok":
        if status not in _MODEL_RESPONSE_STATUSES - {"ok"}:
            raise ModelInvalidResponse("model response status is invalid")
        reason = _text(decoded.get("reason", ""), "model response reason", _MAX_REASON_BYTES, nonempty=False)
        refusal = _text(decoded.get("refusal_code", _MODEL_FAILURE_CODES[status]), "model response refusal_code", _MAX_ERROR_BYTES)
        return ModelParsedResult(status=status, refusal_code=refusal, reason=reason)
    candidates = decoded.get("candidates", [])
    if not isinstance(candidates, (list, tuple)):
        raise ModelInvalidResponse("model response candidates must be a list")
    if len(candidates) > _MAX_PARSED_CANDIDATES:
        raise ModelInvalidResponse("model response exceeds candidate bound")
    unique: dict[str, str] = {}
    duplicate_count = 0
    for item in candidates:
        if isinstance(item, str):
            source = item
        elif isinstance(item, Mapping) and set(item) == {"source"}:
            source = item["source"]
        else:
            raise ModelInvalidResponse("each model candidate must contain only source")
        source = _text(source, "model candidate source", _MAX_SOURCE_BYTES)
        candidate_id = hash_bytes(source.encode("utf-8"))
        if candidate_id in unique:
            duplicate_count += 1
        else:
            unique[candidate_id] = source
    ordered = tuple(unique[key] for key in sorted(unique))
    reason = _text(decoded.get("reason", ""), "model response reason", _MAX_REASON_BYTES, nonempty=False)
    return ModelParsedResult(
        status="ok",
        candidate_sources=ordered,
        duplicate_count=duplicate_count,
        reason=reason,
    )


def _failure_result(status: str, detail: str = "") -> ModelParsedResult:
    if status not in _MODEL_RESPONSE_STATUSES - {"ok"}:
        raise ModelInputError("unknown model failure status")
    return ModelParsedResult(
        status=status,
        refusal_code=_MODEL_FAILURE_CODES[status],
        reason=_text(detail, "model failure detail", _MAX_REASON_BYTES, nonempty=False),
    )


def _build_candidate(
    *,
    lane: str,
    target: ArchivedModelTargetInput,
    source: str,
    provenance: Mapping[str, Any],
) -> LaneCandidate:
    candidate_id = hash_bytes(source.encode("utf-8"))
    artifact = ArtifactRef(
        content_hash=candidate_id,
        path="artifacts/sources/" + candidate_id.removeprefix("sha256:") + ".c",
        media_type="text/x-c",
        byte_size=len(source.encode("utf-8")),
    )
    record = CandidateRecord(
        candidate_id=candidate_id,
        recipient_id=target.recipient_id,
        source_artifact=artifact,
        parent_candidate_ids=(),
        mutation_id=None,
        lane=lane,
        depth=0,
        evaluation=None,
        status="archived",
    )
    return LaneCandidate(record, source, (provenance,))


def _base_provenance(
    *,
    lane: str,
    target: ArchivedModelTargetInput,
    manifest_identity: str,
    provider_identity: str,
    binding: ModelBinding,
    request: Optional[ModelRequest],
    response: Optional[ModelResponse],
    budget_identity: str,
    external_call_limit: int,
    external_calls_consumed: int,
    external_call_consumed: int,
    call_charge_identity: str = "",
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "kind": "model_proposal",
        "lane": lane,
        "recipient_id": target.recipient_id,
        "source": "automation.search_model_lanes",
        "source_identity": MODULE_IDENTITY,
        "input_identity": target.evidence_identity,
        "manifest_identity": manifest_identity,
        "target_identity": target.target_identity,
        "target_artifact_identity": target.target_artifact.content_hash,
        "context_artifact_identities": tuple(item.content_hash for item in target.context_artifacts),
        "archive_identity": ARCHIVE_IDENTITY,
        "provider_identity": provider_identity,
        "model_provider_identity": binding.provider_identity,
        "model_identity": binding.model_identity,
        "prompt_identity": binding.prompt_identity,
        "reasoning_identity": binding.reasoning_identity,
        "config_identity": binding.config_identity,
        "tool_identity": binding.tool_identity,
        "budget_identity": budget_identity,
        "external_call_limit": external_call_limit,
        "external_calls_consumed": external_calls_consumed,
        "external_call_consumed": external_call_consumed,
        "artifact_durability": "proposal_only",
    }
    if call_charge_identity:
        value["call_charge_identity"] = call_charge_identity
    if request is not None:
        value["request_identity"] = request.request_id
        value["rendered_prompt_identity"] = request.prompt_artifact.content_hash
    if response is not None:
        value["response_identity"] = response.response_identity
    return value


def _manifest_identity(manifest: RunManifest) -> str:
    return hash_canonical(manifest.to_dict())


def _budget_for(manifest: RunManifest, lane: str) -> Budget:
    try:
        budget = manifest.lane_budgets[lane]
    except KeyError as exc:
        raise ModelBudgetError("manifest has no budget for the selected model lane") from exc
    if not isinstance(budget, Budget):
        budget = Budget.from_dict(budget)
    if budget.unit not in {"attempts", "candidates", "tasks"}:
        raise ModelBudgetError("model lane requires an attempts, candidates, or tasks budget")
    if budget.consumed != 0:
        raise ModelBudgetError("manifest model budget must start at zero")
    return budget


def _external_call_limit(
    budget: Budget,
    requested: Optional[int],
) -> int:
    """Resolve the manifest-bound cap for paid or hosted provider calls.

    The lane budget is the authority.  A caller may request a smaller cap for
    a deliberately bounded experiment, but may never enlarge the immutable
    manifest reservation.  Candidate fan-out is accounted for separately by
    ``_candidate_limit`` and does not spend this cap.
    """

    limit = budget.limit if requested is None else requested
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or limit < 0
        or limit > budget.limit
    ):
        raise ModelBudgetError("external call budget must be within the manifest budget")
    return limit


def _budget_identity(
    lane: str,
    budget: Budget,
    binding: ModelBinding,
    external_call_limit: Optional[int] = None,
) -> str:
    if external_call_limit is None:
        external_call_limit = budget.limit
    return hash_canonical(
        {
            "protocol": "sotn-model-budget-v1",
            "lane": lane,
            "unit": budget.unit,
            "limit": budget.limit,
            "external_call_limit": external_call_limit,
            "binding_identity": binding.binding_identity,
        }
    )


def _validate_target_subset(
    manifest: RunManifest,
    targets: Sequence[ArchivedModelTargetInput] | Mapping[str, ArchivedModelTargetInput],
    lane: str,
) -> Tuple[ArchivedModelTargetInput, ...]:
    if lane not in MODEL_LANES or lane not in manifest.selected_lanes:
        raise ModelInputError("selected manifest does not enable the requested model lane")
    if isinstance(targets, Mapping):
        normalized = tuple(targets.values())
        if any(not isinstance(item, ArchivedModelTargetInput) for item in normalized):
            raise ModelInputError("model targets must be typed archived inputs")
        if set(targets) != {item.recipient_id for item in normalized}:
            raise ModelSubsetViolation("model target mapping keys do not match typed recipients")
    else:
        normalized = tuple(targets)
    if not normalized:
        raise ModelInputError("model provider requires a nonempty explicit target subset")
    if any(not isinstance(target, ArchivedModelTargetInput) for target in normalized):
        raise ModelInputError("model targets must be typed archived inputs")
    if len({target.recipient_id for target in normalized}) != len(normalized):
        raise ModelSubsetViolation("model target subset contains duplicate recipients")
    expected = set(manifest.queue_record_ids)
    for target in normalized:
        if target.recipient_id not in expected:
            raise ModelSubsetViolation("model target is outside the manifest subset")
        if manifest.target_identities.get(target.recipient_id) != target.target_identity:
            raise ModelArtifactError("model target identity differs from manifest evidence")
    # The provider's identity and replay state must not depend on caller order.
    return tuple(sorted(normalized, key=lambda item: item.recipient_id))


def _validate_provider(provider: Optional[ModelProvider]) -> Optional[ModelProvider]:
    if provider is None:
        return None
    if not isinstance(provider, ModelProvider):
        raise ModelProviderProtocolError(
            "provider must implement typed ModelProvider.invoke(request, prompt, contexts)"
        )
    return provider


def _make_request(
    *,
    lane: str,
    target: ArchivedModelTargetInput,
    manifest: RunManifest,
    manifest_identity: str,
    binding: ModelBinding,
    budget_identity: str,
    archive: ContentAddressedArchive,
    ordinal: int,
    external_call_limit: int,
) -> ModelRequest:
    prompt = _render_prompt(binding, target)
    prompt_artifact = archive.put_bytes(
        prompt.encode("utf-8"),
        category="model-prompts",
        suffix=".txt",
        media_type="text/plain",
    )
    identity_payload = {
        "protocol": MODEL_REQUEST_PROTOCOL,
        "lane": lane,
        "recipient_id": target.recipient_id,
        "manifest_identity": manifest_identity,
        "subset_identity": manifest.subset_identity,
        "target_identity": target.target_identity,
        "context_artifact_identities": [item.content_hash for item in target.context_artifacts],
        "provider_identity": binding.provider_identity,
        "model_identity": binding.model_identity,
        "model_name": binding.model_name,
        "prompt_identity": binding.prompt_identity,
        "reasoning_identity": binding.reasoning_identity,
        "reasoning": binding.reasoning,
        "config_identity": binding.config_identity,
        "tool_identity": binding.tool_identity,
        "budget_identity": budget_identity,
        "prompt_artifact": _artifact_dict(prompt_artifact),
        "ordinal": ordinal,
        "external_call_limit": external_call_limit,
    }
    request_id = hash_canonical(identity_payload)
    provisional = ModelRequest(
        request_id=request_id,
        lane=lane,
        recipient_id=target.recipient_id,
        manifest_identity=manifest_identity,
        subset_identity=manifest.subset_identity,
        target_identity=target.target_identity,
        context_artifact_identities=tuple(item.content_hash for item in target.context_artifacts),
        provider_identity=binding.provider_identity,
        model_identity=binding.model_identity,
        model_name=binding.model_name,
        prompt_identity=binding.prompt_identity,
        reasoning_identity=binding.reasoning_identity,
        reasoning=binding.reasoning,
        config_identity=binding.config_identity,
        tool_identity=binding.tool_identity,
        budget_identity=budget_identity,
        prompt_artifact=prompt_artifact,
        ordinal=ordinal,
        external_call_limit=external_call_limit,
    )
    charge_identity = hash_canonical(
        {
            "protocol": "sotn-model-call-charge-v1",
            "request_id": provisional.request_id,
            "external_call_limit": external_call_limit,
        }
    )
    request_artifact = archive.put_bytes(
        canonical_bytes(_request_artifact_payload(provisional)),
        category="model-requests",
        suffix=".json",
        media_type="application/json",
    )
    return ModelRequest(
        request_id=provisional.request_id,
        lane=provisional.lane,
        recipient_id=provisional.recipient_id,
        manifest_identity=provisional.manifest_identity,
        subset_identity=provisional.subset_identity,
        target_identity=provisional.target_identity,
        context_artifact_identities=provisional.context_artifact_identities,
        provider_identity=provisional.provider_identity,
        model_identity=provisional.model_identity,
        model_name=provisional.model_name,
        prompt_identity=provisional.prompt_identity,
        reasoning_identity=provisional.reasoning_identity,
        reasoning=provisional.reasoning,
        config_identity=provisional.config_identity,
        tool_identity=provisional.tool_identity,
        budget_identity=provisional.budget_identity,
        prompt_artifact=provisional.prompt_artifact,
        ordinal=provisional.ordinal,
        external_call_limit=provisional.external_call_limit,
        call_charge_identity=charge_identity,
        request_artifact=request_artifact,
    )


def _make_handoff(
    request: ModelRequest,
    response: ModelResponse,
    result: ModelParsedResult,
    archive: ContentAddressedArchive,
) -> ModelHandoff:
    handoff_without_ref = {
        "protocol": MODEL_HANDOFF_PROTOCOL,
        "request_id": request.request_id,
        "response_identity": response.response_identity,
        "result": result.to_dict(),
    }
    reference = archive.put_bytes(
        canonical_bytes(handoff_without_ref),
        category="model-results",
        suffix=".json",
        media_type="application/json",
    )
    handoff = ModelHandoff(request, response, result, reference)
    _verify_result_archive(archive, handoff)
    return handoff


def _load_durable_handoffs(
    archive: ContentAddressedArchive,
    values: Sequence[ModelHandoff],
) -> Mapping[str, ModelHandoff]:
    result: dict[str, ModelHandoff] = {}
    for value in values:
        if not isinstance(value, ModelHandoff):
            raise ModelReplayError("durable_results must contain ModelHandoff values")
        _verify_request_archive(archive, value.request)
        _verify_response_archive(archive, value.response)
        _verify_result_archive(archive, value)
        key = value.request.request_id
        if key in result and result[key].to_dict() != value.to_dict():
            raise ModelReplayError("two durable handoffs claim one request differently")
        result[key] = value
    return MappingProxyType(result)


@dataclass(frozen=True)
class ModelArchiveRecords:
    """All model handoff records discovered from immutable archive bytes.

    This is intentionally independent of a caller-provided state object.  A
    restart can therefore recover a completed handoff, or observe a durable
    request with no terminal response, using only the run archive.
    """

    requests: Mapping[str, ModelRequest]
    responses: Mapping[str, ModelResponse]
    handoffs: Mapping[str, ModelHandoff]
    pending: Mapping[str, ModelRequest]


@dataclass(frozen=True)
class _ArchivedResult:
    request_id: str
    response_identity: str
    result: ModelParsedResult
    result_artifact: ArtifactRef

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "response_identity": self.response_identity,
            "result": self.result.to_dict(),
            "result_artifact": self.result_artifact.to_dict(),
        }


def _archive_json_reference(
    archive: ContentAddressedArchive,
    path: Path,
    data: bytes,
    label: str,
) -> ArtifactRef:
    """Build and verify the canonical reference for one archive JSON file."""

    try:
        relative = path.resolve(strict=False).relative_to(archive.run_root).as_posix()
    except (OSError, RuntimeError, ValueError) as exc:
        raise ModelArtifactError(f"{label} is outside the run archive") from exc
    reference = ArtifactRef(
        content_hash=hash_bytes(data),
        path=relative,
        media_type="application/json",
        byte_size=len(data),
    )
    _archive_verify(archive, reference, data, label)
    return reference


def _read_canonical_json(
    archive: ContentAddressedArchive,
    path: Path,
    label: str,
) -> tuple[ArtifactRef, Mapping[str, Any]]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ModelArtifactError(f"{label} cannot be read") from exc
    reference = _archive_json_reference(archive, path, data, label)
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ModelArtifactError(f"{label} is not canonical JSON") from exc
    if not isinstance(value, Mapping) or canonical_bytes(value) != data:
        raise ModelArtifactError(f"{label} is not canonical JSON")
    return reference, value


def _scan_model_json_category(
    archive: ContentAddressedArchive,
    category: str,
    label: str,
) -> list[tuple[ArtifactRef, Mapping[str, Any]]]:
    root = archive.run_root / "artifacts" / category
    try:
        entries = sorted(root.iterdir(), key=lambda item: item.name) if root.is_dir() else []
    except OSError as exc:
        raise ModelArtifactError(f"model {label} archive cannot be listed") from exc
    records = []
    for path in entries:
        if not path.is_file() or path.suffix != ".json":
            continue
        records.append(_read_canonical_json(archive, path, f"model {label} artifact"))
    return records


def _put_unique_record(
    table: dict[str, Any],
    key: str,
    value: Any,
    label: str,
) -> None:
    previous = table.get(key)
    if previous is not None and previous.to_dict() != value.to_dict():
        raise ModelReplayError(f"two model {label} artifacts claim one identity differently")
    table[key] = value


def discover_model_archive(archive: ContentAddressedArchive) -> ModelArchiveRecords:
    """Discover requests, responses, and terminal results without injection.

    The archive is scanned in request-first order.  Every response/result must
    be linked to a request, and every terminal result must link to its exact
    response identity.  A request lacking a terminal result is returned as a
    pending reservation, so callers can refuse safely after process loss.
    """

    if not isinstance(archive, ContentAddressedArchive):
        raise ModelInputError("archive must be a ContentAddressedArchive")
    request_records = _scan_model_json_category(archive, "model-requests", "request")
    response_records = _scan_model_json_category(archive, "model-responses", "response")
    result_records = _scan_model_json_category(archive, "model-results", "result")

    requests: dict[str, ModelRequest] = {}
    for reference, value in request_records:
        if set(value) != {"protocol", "request"} or value.get("protocol") != MODEL_REQUEST_PROTOCOL:
            raise ModelReplayError("model request artifact has the wrong schema")
        identity = value["request"]
        if not isinstance(identity, Mapping):
            raise ModelReplayError("model request identity is malformed")
        request_id = hash_canonical(identity)
        full = dict(identity)
        full["request_id"] = request_id
        full["request_artifact"] = reference.to_dict()
        if full.get("external_call_limit", 0):
            full["call_charge_identity"] = hash_canonical(
                {
                    "protocol": "sotn-model-call-charge-v1",
                    "request_id": request_id,
                    "external_call_limit": full["external_call_limit"],
                }
            )
        request = ModelRequest.from_dict(full)
        if request.request_id != request_id:
            raise ModelReplayError("model request artifact identity is forged")
        _put_unique_record(requests, request_id, request, "request")

    responses: dict[str, ModelResponse] = {}
    for reference, value in response_records:
        expected = {
            "protocol", "request_id", "status", "body_identity", "response_text",
            "error_code", "detail", "response_identity",
        }
        if set(value) != expected or value.get("protocol") != MODEL_RESPONSE_PROTOCOL:
            raise ModelReplayError("model response artifact has the wrong schema")
        full = dict(value)
        full["response_artifact"] = reference.to_dict()
        response = ModelResponse.from_dict(full)
        _put_unique_record(responses, response.request_id, response, "response")

    result_records_by_request: dict[str, _ArchivedResult] = {}
    for reference, value in result_records:
        expected = {"protocol", "request_id", "response_identity", "result"}
        if set(value) != expected or value.get("protocol") != MODEL_HANDOFF_PROTOCOL:
            raise ModelReplayError("model result artifact has the wrong schema")
        request_id = value["request_id"]
        if not _is_hex_identity(request_id):
            raise ModelReplayError("model result request identity is malformed")
        result = ModelParsedResult.from_dict(value["result"])
        response_identity = value["response_identity"]
        _identity(response_identity, "model result response_identity")
        _put_unique_record(
            result_records_by_request,
            request_id,
            _ArchivedResult(
                request_id=request_id,
                response_identity=response_identity,
                result=result,
                result_artifact=reference,
            ),
            "result",
        )

    handoffs: dict[str, ModelHandoff] = {}
    for request_id, request in requests.items():
        response = responses.get(request_id)
        result_stub = result_records_by_request.get(request_id)
        if result_stub is None:
            continue
        if response is None:
            raise ModelReplayError("model result exists without its durable response")
        response_identity = result_stub.response_identity
        if response.response_identity != response_identity:
            raise ModelReplayError("model result response identity does not match response")
        handoff = ModelHandoff(
            request=request,
            response=response,
            result=result_stub.result,
            result_artifact=result_stub.result_artifact,
        )
        _verify_request_archive(archive, request)
        _verify_response_archive(archive, response)
        _verify_result_archive(archive, handoff)
        _put_unique_record(handoffs, request_id, handoff, "handoff")

    for request_id in set(responses).difference(requests):
        raise ModelReplayError("model response exists without its durable request")
    for request_id in set(result_records_by_request).difference(requests):
        raise ModelReplayError("model result exists without its durable request")

    pending = {
        request_id: request
        for request_id, request in requests.items()
        if request_id not in handoffs
    }
    return ModelArchiveRecords(
        requests=MappingProxyType(requests),
        responses=MappingProxyType(responses),
        handoffs=MappingProxyType(handoffs),
        pending=MappingProxyType(pending),
    )


def _provider_identity(
    lane: str,
    manifest_identity: str,
    binding: ModelBinding,
    targets: Sequence[ArchivedModelTargetInput],
    budget_identity: str,
    external_call_limit: Optional[int] = None,
    include_external_call_limit: bool = True,
) -> str:
    if external_call_limit is None:
        external_call_limit = 0
    payload = {
            "protocol": "sotn-model-lane-v1",
            "module_identity": MODULE_IDENTITY,
            "lane": lane,
            "manifest_identity": manifest_identity,
            "binding_identity": binding.binding_identity,
            "budget_identity": budget_identity,
            "target_identities": [item.evidence_identity for item in targets],
            "archive_identity": ARCHIVE_IDENTITY,
        }
    if include_external_call_limit:
        payload["external_call_limit"] = external_call_limit
    return hash_canonical(payload)


def _request_matches_target(
    request: ModelRequest,
    *,
    lane: str,
    target: ArchivedModelTargetInput,
    manifest: RunManifest,
    manifest_identity: str,
    binding: ModelBinding,
    budget_identity: str,
    external_call_limit: int,
    expected_prompt_identity: str,
    ordinal: int,
) -> bool:
    """Return whether an archived request is the exact current reservation."""

    return (
        request.lane == lane
        and request.recipient_id == target.recipient_id
        and request.manifest_identity == manifest_identity
        and request.subset_identity == manifest.subset_identity
        and request.target_identity == target.target_identity
        and request.context_artifact_identities
        == tuple(item.content_hash for item in target.context_artifacts)
        and request.provider_identity == binding.provider_identity
        and request.model_identity == binding.model_identity
        and request.model_name == binding.model_name
        and request.prompt_identity == binding.prompt_identity
        and request.reasoning_identity == binding.reasoning_identity
        and request.reasoning == binding.reasoning
        and request.config_identity == binding.config_identity
        and request.tool_identity == binding.tool_identity
        and request.budget_identity == budget_identity
        and request.external_call_limit in {0, external_call_limit}
        and request.ordinal == ordinal
        and request.prompt_artifact.content_hash == expected_prompt_identity
        and request.request_artifact is not None
        and (request.call_charge_identity or request.external_call_limit == 0)
    )


def _candidate_limit(
    budget: Budget,
    binding: ModelBinding,
    used_candidates: int,
) -> int:
    """Keep model candidate fan-out accounting independent from call count."""

    if budget.unit == "candidates":
        return max(0, budget.limit - used_candidates)
    return binding.max_candidates


def _active_archive_records(
    records: ModelArchiveRecords,
    *,
    lane: str,
    manifest_identity: str,
    targets: Sequence[ArchivedModelTargetInput],
) -> None:
    """Reject current-run requests that cross the frozen subset boundary."""

    recipients = {item.recipient_id for item in targets}
    for request in records.requests.values():
        if request.lane != lane:
            continue
        if request.manifest_identity != manifest_identity and request.recipient_id in recipients:
            raise ModelReplayError("archived model request crosses the manifest boundary")
        if request.manifest_identity == manifest_identity and request.recipient_id not in recipients:
            raise ModelReplayError("archived model request crosses the active subset")
    for request_id, handoff in records.handoffs.items():
        request = handoff.request
        if request.lane != lane or request.manifest_identity != manifest_identity:
            continue
        if request.recipient_id not in recipients:
            raise ModelReplayError("archived model handoff crosses the active subset")


def _result_mapping(
    *,
    lane: str,
    target: ArchivedModelTargetInput,
    parsed: ModelParsedResult,
    handoff: Optional[ModelHandoff],
    provider_identity: str,
    manifest_identity: str,
    binding: ModelBinding,
    budget: Budget,
    budget_identity: str,
    external_call_limit: int,
    external_calls_consumed: int,
    external_call_consumed: int = 0,
    pending_request: Optional[ModelRequest] = None,
    candidate_limit: Optional[int] = None,
) -> dict[str, Any]:
    if candidate_limit is None:
        candidate_limit = budget.limit
    if isinstance(candidate_limit, bool) or not isinstance(candidate_limit, int) or candidate_limit < 0:
        raise ModelBudgetError("candidate_limit must be a nonnegative integer")
    if (
        isinstance(external_call_limit, bool)
        or not isinstance(external_call_limit, int)
        or external_call_limit < 0
        or isinstance(external_calls_consumed, bool)
        or not isinstance(external_calls_consumed, int)
        or external_calls_consumed < 0
        or external_calls_consumed > external_call_limit
        or external_call_consumed not in (0, 1)
    ):
        raise ModelBudgetError("model external call accounting is invalid")
    if pending_request is not None and handoff is not None:
        raise ModelReplayError("model result cannot be both pending and terminal")
    limit = min(binding.max_candidates, candidate_limit)
    sources = parsed.candidate_sources
    accepted = sources[:limit]
    overflow = max(0, len(sources) - len(accepted))
    attempts = len(accepted)
    rejections = Counter()
    if parsed.duplicate_count:
        rejections["duplicate_candidate"] += parsed.duplicate_count
    if overflow:
        rejections["budget_exhausted"] += overflow
    candidates = []
    provenance_entries = []
    for source in accepted:
        provenance = _base_provenance(
            lane=lane,
            target=target,
            manifest_identity=manifest_identity,
            provider_identity=provider_identity,
            binding=binding,
            request=handoff.request if handoff else None,
            response=handoff.response if handoff else None,
            budget_identity=budget_identity,
            external_call_limit=external_call_limit,
            external_calls_consumed=external_calls_consumed,
            external_call_consumed=external_call_consumed,
            call_charge_identity=(
                handoff.request.call_charge_identity if handoff is not None else
                pending_request.call_charge_identity if pending_request is not None else ""
            ),
        )
        candidate = _build_candidate(
            lane=lane,
            target=target,
            source=source,
            provenance=provenance,
        )
        candidates.append(candidate)
        provenance_entries.extend(candidate.provenance)
    if external_call_consumed and not accepted:
        # Preserve the reservation even when the provider returned no usable
        # candidate.  This is the evidence that makes an unavailable,
        # refused, timeout, invalid, or empty response count against the cap.
        provenance_entries.append(
            _base_provenance(
                lane=lane,
                target=target,
                manifest_identity=manifest_identity,
                provider_identity=provider_identity,
                binding=binding,
                request=(
                    handoff.request if handoff is not None else pending_request
                ),
                response=handoff.response if handoff is not None else None,
                budget_identity=budget_identity,
                external_call_limit=external_call_limit,
                external_calls_consumed=external_calls_consumed,
                external_call_consumed=external_call_consumed,
                call_charge_identity=(
                    handoff.request.call_charge_identity
                    if handoff is not None
                    else pending_request.call_charge_identity
                    if pending_request is not None
                    else ""
                ),
            )
        )
    if pending_request is not None:
        completion = "inapplicable"
        refusal = "model_request_pending"
        reason = "model request is durable and has no terminal response"
    elif parsed.refusal_code == "model_external_call_budget_exhausted":
        completion = "budget_exhausted"
        refusal = parsed.refusal_code
        reason = parsed.reason
    elif limit == 0:
        completion = "budget_exhausted"
        refusal = "model_budget_exhausted"
        reason = "model candidate budget is zero"
    elif accepted:
        completion = "budget_exhausted" if overflow else "search_space_exhausted"
        refusal = None
        reason = parsed.reason or (
            "model candidates remain observed beyond the immutable budget"
            if overflow else "model provider response parsed"
        )
    elif parsed.status != "ok":
        completion = "inapplicable"
        refusal = parsed.refusal_code or _MODEL_FAILURE_CODES.get(parsed.status, "model_provider_invalid_response")
        reason = parsed.reason or "model provider did not produce a usable response"
    else:
        completion = "inapplicable"
        refusal = "model_no_candidate"
        reason = parsed.reason or "model response contained no unique candidate"
    input_ids = [target.evidence_identity, provider_identity, binding.binding_identity, budget_identity]
    if handoff is not None:
        input_ids.extend(
            [
                handoff.request.request_id,
                handoff.request.request_artifact.content_hash if handoff.request.request_artifact else "",
                handoff.response.response_identity,
                handoff.response.response_artifact.content_hash if handoff.response.response_artifact else "",
                handoff.result.result_identity,
                handoff.result_artifact.content_hash,
            ]
        )
    if pending_request is not None:
        input_ids.extend(
            [
                pending_request.request_id,
                pending_request.request_artifact.content_hash
                if pending_request.request_artifact is not None else "",
                pending_request.call_charge_identity,
            ]
        )
    input_ids = [item for item in input_ids if item]
    return {
        "candidates": tuple(candidates),
        "attempts": attempts,
        "input_identities": tuple(dict.fromkeys(input_ids)),
        "provenance": tuple(provenance_entries),
        "rejection_counts": dict(sorted(rejections.items())),
        "completion_reason": completion,
        "refusal_code": refusal,
        "reason": reason,
        "model_result_identity": parsed.result_identity,
        "model_overflow_observations": overflow,
        "model_provider_identity": binding.provider_identity,
        "model_identity": binding.model_identity,
        "prompt_identity": binding.prompt_identity,
        "rendered_prompt_identity": (
            handoff.request.prompt_artifact.content_hash
            if handoff is not None
            else pending_request.prompt_artifact.content_hash
            if pending_request is not None
            else ""
        ),
        "reasoning_identity": binding.reasoning_identity,
        "config_identity": binding.config_identity,
        "tool_identity": binding.tool_identity,
        "budget_identity": budget_identity,
        "external_call_limit": external_call_limit,
        "external_calls_consumed": external_calls_consumed,
        "external_call_consumed": external_call_consumed,
    }


def _normalize_result_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Rebuild a callback result without leaving mutable aliases in state."""

    if not isinstance(value, Mapping):
        raise ModelReplayError("model lane result must be a mapping")
    # Accept state produced by the pre-call-budget implementation.  The
    # provider constructor fills the legacy zero values from its durable
    # handoffs, while all newly written state carries the explicit fields.
    value = dict(value)
    value.setdefault("external_call_limit", 0)
    value.setdefault("external_calls_consumed", 0)
    value.setdefault("external_call_consumed", 0)
    required = {
        "candidates", "attempts", "input_identities", "provenance", "rejection_counts",
        "completion_reason", "refusal_code", "reason", "model_result_identity",
        "model_overflow_observations", "model_provider_identity", "model_identity",
        "prompt_identity", "reasoning_identity", "config_identity", "tool_identity",
        "budget_identity", "rendered_prompt_identity",
        "external_call_limit", "external_calls_consumed", "external_call_consumed",
    }
    if set(value) != required:
        raise ModelReplayError("model lane result has the wrong schema")
    raw_candidates = value["candidates"]
    if not isinstance(raw_candidates, (list, tuple)):
        raise ModelReplayError("model lane candidates must be a sequence")
    candidates = []
    for index, item in enumerate(raw_candidates):
        if isinstance(item, LaneCandidate):
            candidates.append(item)
            continue
        if not isinstance(item, Mapping) or set(item) != {"candidate", "source", "provenance"}:
            raise ModelReplayError(f"model candidate {index} has the wrong schema")
        try:
            record = CandidateRecord.from_dict(item["candidate"])
            candidates.append(
                LaneCandidate(record, item["source"], tuple(item["provenance"]))
            )
        except Exception as exc:
            raise ModelReplayError(f"model candidate {index} cannot be reconstructed") from exc
    try:
        attempts = value["attempts"]
        if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 0:
            raise ValueError("attempts")
        overflow = value["model_overflow_observations"]
        if isinstance(overflow, bool) or not isinstance(overflow, int) or overflow < 0:
            raise ValueError("overflow")
        external_limit = value["external_call_limit"]
        external_consumed = value["external_calls_consumed"]
        external_call_consumed = value["external_call_consumed"]
        if (
            isinstance(external_limit, bool)
            or not isinstance(external_limit, int)
            or external_limit < 0
            or isinstance(external_consumed, bool)
            or not isinstance(external_consumed, int)
            or external_consumed < 0
            or external_consumed > external_limit
            or isinstance(external_call_consumed, bool)
            or external_call_consumed not in (0, 1)
        ):
            raise ValueError("external call accounting")
        input_ids = tuple(value["input_identities"])
        if not input_ids:
            raise ValueError("input identities")
        if len(set(input_ids)) != len(input_ids):
            raise ValueError("duplicate input identities")
        for item in input_ids:
            _identity(item, "model result input identity")
        rejections = dict(value["rejection_counts"])
        for key, item in rejections.items():
            if not isinstance(key, str) or isinstance(item, bool) or not isinstance(item, int) or item < 0:
                raise ValueError("rejection count")
        completion = value["completion_reason"]
        if completion not in _RESULT_COMPLETION:
            raise ValueError("completion reason")
        refusal = value["refusal_code"]
        if refusal is not None:
            _text(refusal, "model result refusal_code", _MAX_ERROR_BYTES)
        reason = _text(value["reason"], "model result reason", _MAX_REASON_BYTES, nonempty=False)
        for name in (
            "model_result_identity", "model_provider_identity", "model_identity", "prompt_identity",
            "reasoning_identity", "config_identity", "tool_identity", "budget_identity",
        ):
            _identity(value[name], f"model result {name}")
        rendered_prompt_identity = value["rendered_prompt_identity"]
        if rendered_prompt_identity:
            _identity(rendered_prompt_identity, "model result rendered_prompt_identity")
        provenance = tuple(value["provenance"])
        for item in provenance:
            if not isinstance(item, Mapping):
                raise ValueError("provenance")
    except (KeyError, TypeError, ValueError, ModelLaneError) as exc:
        raise ModelReplayError("model lane result contains invalid accounting") from exc
    return MappingProxyType(
        {
            "candidates": tuple(candidates),
            "attempts": attempts,
            "input_identities": input_ids,
            "provenance": tuple(MappingProxyType(dict(item)) for item in provenance),
            "rejection_counts": MappingProxyType(dict(sorted(rejections.items()))),
            "completion_reason": completion,
            "refusal_code": refusal,
            "reason": reason,
            "model_result_identity": value["model_result_identity"],
            "model_overflow_observations": overflow,
            "model_provider_identity": value["model_provider_identity"],
            "model_identity": value["model_identity"],
            "prompt_identity": value["prompt_identity"],
            "rendered_prompt_identity": rendered_prompt_identity,
            "reasoning_identity": value["reasoning_identity"],
            "config_identity": value["config_identity"],
            "tool_identity": value["tool_identity"],
            "budget_identity": value["budget_identity"],
            "external_call_limit": external_limit,
            "external_calls_consumed": external_consumed,
            "external_call_consumed": external_call_consumed,
        }
    )


def _validate_result_provenance(
    result: Mapping[str, Any],
    *,
    lane: str,
    target: ArchivedModelTargetInput,
    provider_identity: str,
    manifest_identity: str,
    binding: ModelBinding,
    budget_identity: str,
    handoff: Optional[ModelHandoff],
    pending_request: Optional[ModelRequest] = None,
    external_call_limit: Optional[int] = None,
    external_calls_consumed: Optional[int] = None,
) -> None:
    """Check that a reconstructed result retained every immutable binding."""

    required_inputs = {
        target.evidence_identity,
        provider_identity,
        binding.binding_identity,
        budget_identity,
    }
    if not required_inputs.issubset(set(result["input_identities"])):
        raise ModelReplayError("model result dropped a required input identity")
    if handoff is not None:
        required_inputs.update(
            {
                handoff.request.request_id,
                handoff.request.request_artifact.content_hash
                if handoff.request.request_artifact is not None else "",
                handoff.response.response_identity,
                handoff.response.response_artifact.content_hash
                if handoff.response.response_artifact is not None else "",
                handoff.result.result_identity,
                handoff.result_artifact.content_hash,
            }
        )
        if not required_inputs.issubset(set(result["input_identities"])):
            raise ModelReplayError("model result dropped a durable handoff identity")
    if pending_request is not None:
        if pending_request.request_id not in result["input_identities"]:
            raise ModelReplayError("pending model result dropped its request identity")
        if (
            result["completion_reason"] != "inapplicable"
            or result["refusal_code"] != "model_request_pending"
            or result["rendered_prompt_identity"] != pending_request.prompt_artifact.content_hash
        ):
            raise ModelReplayError("pending model result has the wrong refusal binding")
    if external_call_limit is not None and result["external_call_limit"] != external_call_limit:
        raise ModelReplayError("model result external call limit differs from provider state")
    if external_calls_consumed is not None and result["external_calls_consumed"] > external_calls_consumed:
        raise ModelReplayError("model result overstates external calls consumed")
    for edge in result["provenance"]:
        if (
            edge.get("kind") != "model_proposal"
            or edge.get("lane") != lane
            or edge.get("recipient_id") != target.recipient_id
            or edge.get("source") != "automation.search_model_lanes"
            or edge.get("source_identity") != MODULE_IDENTITY
            or edge.get("input_identity") != target.evidence_identity
            or edge.get("manifest_identity") != manifest_identity
            or edge.get("target_identity") != target.target_identity
            or edge.get("provider_identity") != provider_identity
            or edge.get("model_provider_identity") != binding.provider_identity
            or edge.get("model_identity") != binding.model_identity
            or edge.get("prompt_identity") != binding.prompt_identity
            or edge.get("reasoning_identity") != binding.reasoning_identity
            or edge.get("config_identity") != binding.config_identity
            or edge.get("tool_identity") != binding.tool_identity
            or edge.get("budget_identity") != budget_identity
            or edge.get("external_call_limit") != result["external_call_limit"]
            or edge.get("external_calls_consumed") != result["external_calls_consumed"]
            or edge.get("external_call_consumed") != result["external_call_consumed"]
            or edge.get("archive_identity") != ARCHIVE_IDENTITY
            or edge.get("artifact_durability") != "proposal_only"
        ):
            raise ModelReplayError("model result provenance does not match its bindings")
        if handoff is not None and (
            edge.get("request_identity") != handoff.request.request_id
            or edge.get("rendered_prompt_identity") != handoff.request.prompt_artifact.content_hash
            or edge.get("response_identity") != handoff.response.response_identity
        ):
            raise ModelReplayError("model result provenance does not match its handoff")
        if pending_request is not None and (
            edge.get("request_identity") != pending_request.request_id
            or edge.get("rendered_prompt_identity") != pending_request.prompt_artifact.content_hash
            or edge.get("response_identity") is not None
        ):
            raise ModelReplayError("pending model result provenance is forged")
        if handoff is not None and handoff.request.call_charge_identity and (
            edge.get("call_charge_identity") != handoff.request.call_charge_identity
        ):
            raise ModelReplayError("model result provenance does not match its call charge")


@dataclass(frozen=True)
class ModelLaneProvider:
    """A stateless callback plus all durable model handoff state."""

    lane: str
    manifest_identity: str
    subset_identity: str
    config_identity: str
    tool_identity: str
    provider_identity: str
    binding: ModelBinding
    budget: Budget
    budget_identity: str
    target_inputs: Tuple[ArchivedModelTargetInput, ...]
    handoffs: Tuple[ModelHandoff, ...]
    results: Tuple[Tuple[str, Mapping[str, Any]], ...]
    external_call_limit: int = 0
    external_calls_consumed: int = 0
    pending_requests: Tuple[ModelRequest, ...] = ()

    def __post_init__(self) -> None:
        if self.lane not in MODEL_LANES:
            raise ModelInputError("invalid model provider lane")
        for name in ("manifest_identity", "subset_identity", "config_identity", "tool_identity", "provider_identity", "budget_identity"):
            _identity(getattr(self, name), f"model provider {name}")
        if not isinstance(self.binding, ModelBinding):
            raise ModelReplayError("model provider binding must be typed")
        if self.binding.config_identity != self.config_identity or self.binding.tool_identity != self.tool_identity:
            raise ModelReplayError("model binding does not match manifest config/tool identities")
        if not isinstance(self.budget, Budget):
            raise ModelBudgetError("model provider budget must be typed")
        if self.budget.consumed != 0 or self.budget.unit not in {"attempts", "candidates", "tasks"}:
            raise ModelBudgetError("model provider budget is not an unconsumed model budget")
        external_limit = (
            self.budget.limit
            if self.external_call_limit is None
            else self.external_call_limit
        )
        if (
            isinstance(external_limit, bool)
            or not isinstance(external_limit, int)
            or external_limit < 0
            or external_limit > self.budget.limit
        ):
            raise ModelBudgetError("model provider external call limit is invalid")
        external_consumed = self.external_calls_consumed
        if (
            isinstance(external_consumed, bool)
            or not isinstance(external_consumed, int)
            or external_consumed < 0
            or external_consumed > external_limit
        ):
            raise ModelBudgetError("model provider external call consumption is invalid")
        object.__setattr__(self, "external_call_limit", external_limit)
        targets = tuple(self.target_inputs)
        if not targets:
            raise ModelInputError("model provider needs at least one target")
        if any(not isinstance(item, ArchivedModelTargetInput) for item in targets):
            raise ModelReplayError("model provider targets must be typed")
        if tuple(sorted(targets, key=lambda item: item.recipient_id)) != targets:
            raise ModelReplayError("model targets are not in canonical order")
        if len({item.recipient_id for item in targets}) != len(targets):
            raise ModelReplayError("model targets contain duplicate recipients")
        object.__setattr__(self, "target_inputs", targets)
        targets_by_recipient = {item.recipient_id: item for item in targets}
        handoffs = tuple(self.handoffs)
        if any(not isinstance(item, ModelHandoff) for item in handoffs):
            raise ModelReplayError("model provider handoffs must be typed")
        if tuple(sorted(handoffs, key=lambda item: item.request.recipient_id)) != handoffs:
            raise ModelReplayError("model handoffs are not in canonical order")
        seen_handoff_recipients = set()
        target_ordinals = {
            target.recipient_id: ordinal for ordinal, target in enumerate(targets)
        }
        for handoff in handoffs:
            request = handoff.request
            target = targets_by_recipient.get(request.recipient_id)
            if target is None or request.recipient_id in seen_handoff_recipients:
                raise ModelReplayError("model handoff does not cover one target exactly once")
            seen_handoff_recipients.add(request.recipient_id)
            if (
                request.lane != self.lane
                or request.manifest_identity != self.manifest_identity
                or request.subset_identity != self.subset_identity
                or request.target_identity != target.target_identity
                or request.provider_identity != self.binding.provider_identity
                or request.model_identity != self.binding.model_identity
                or request.model_name != self.binding.model_name
                or request.prompt_identity != self.binding.prompt_identity
                or request.reasoning_identity != self.binding.reasoning_identity
                or request.reasoning != self.binding.reasoning
                or request.config_identity != self.config_identity
                or request.tool_identity != self.tool_identity
                or request.budget_identity != self.budget_identity
                or request.ordinal != target_ordinals[request.recipient_id]
            ):
                raise ModelReplayError("model handoff identity bindings disagree with provider state")
            if handoff.response.response_artifact is None or request.request_artifact is None:
                raise ModelReplayError("model handoff is missing a durable request or response")
            if handoff.result.result_identity == "":
                raise ModelReplayError("model handoff has no parsed result identity")
        object.__setattr__(self, "handoffs", handoffs)
        pending_requests = tuple(self.pending_requests)
        if any(not isinstance(item, ModelRequest) for item in pending_requests):
            raise ModelReplayError("model pending requests must be typed")
        if tuple(sorted(pending_requests, key=lambda item: item.recipient_id)) != pending_requests:
            raise ModelReplayError("model pending requests are not in canonical order")
        if len({item.recipient_id for item in pending_requests}) != len(pending_requests):
            raise ModelReplayError("model pending requests contain duplicate recipients")
        handoff_recipients = {item.request.recipient_id for item in handoffs}
        pending_recipients = set()
        for request in pending_requests:
            target = targets_by_recipient.get(request.recipient_id)
            if target is None or request.recipient_id in handoff_recipients:
                raise ModelReplayError("model pending request does not cover one target exactly once")
            pending_recipients.add(request.recipient_id)
            if (
                request.lane != self.lane
                or request.manifest_identity != self.manifest_identity
                or request.subset_identity != self.subset_identity
                or request.target_identity != target.target_identity
                or request.provider_identity != self.binding.provider_identity
                or request.model_identity != self.binding.model_identity
                or request.model_name != self.binding.model_name
                or request.prompt_identity != self.binding.prompt_identity
                or request.reasoning_identity != self.binding.reasoning_identity
                or request.reasoning != self.binding.reasoning
                or request.config_identity != self.config_identity
                or request.tool_identity != self.tool_identity
                or request.budget_identity != self.budget_identity
                or request.ordinal != target_ordinals[request.recipient_id]
                or request.external_call_limit != self.external_call_limit
            ):
                raise ModelReplayError("model pending request identity bindings disagree with provider state")
            if request.request_artifact is None:
                raise ModelReplayError("model pending request is missing its durable charge")
            if request.external_call_limit and not request.call_charge_identity:
                raise ModelReplayError("model pending request is missing its durable charge identity")
        object.__setattr__(self, "pending_requests", pending_requests)
        expected_consumed = len(handoffs) + len(pending_requests)
        if self.external_calls_consumed == 0 and expected_consumed:
            external_consumed = expected_consumed
        else:
            external_consumed = self.external_calls_consumed
        if external_consumed != expected_consumed:
            raise ModelReplayError("model external call consumption does not match durable requests")
        object.__setattr__(self, "external_calls_consumed", external_consumed)
        results = tuple(self.results)
        if any(not isinstance(item, tuple) or len(item) != 2 for item in results):
            raise ModelReplayError("model results must be recipient/result pairs")
        try:
            for item in results:
                validate_id(item[0], "model result recipient_id")
        except Exception as exc:
            raise ModelReplayError("model result recipient is invalid") from exc
        if len({item[0] for item in results}) != len(results):
            raise ModelReplayError("model results contain duplicate recipients")
        if tuple(sorted(item[0] for item in results)) != tuple(item[0] for item in results):
            raise ModelReplayError("model results are not in canonical order")
        if {item[0] for item in results} != {item.recipient_id for item in targets}:
            raise ModelReplayError("model results do not cover exactly the target subset")
        handoffs_by_recipient = {
            item.request.recipient_id: item for item in handoffs
        }
        pending_by_recipient = {
            item.recipient_id: item for item in pending_requests
        }
        normalized_results = tuple(
            (recipient, _normalize_result_mapping(result))
            for recipient, result in results
        )
        total_attempts = 0
        for _, result in normalized_results:
            attempts = result["attempts"]
            if attempts > len(result["candidates"]):
                raise ModelReplayError("model result attempts exceed unique candidates")
            if attempts > self.binding.max_candidates:
                raise ModelReplayError("model result attempts exceed candidate fan-out bound")
            total_attempts += attempts
        if self.budget.unit == "candidates" and total_attempts > self.budget.limit:
            raise ModelReplayError("model result attempts exceed the immutable budget")
        for recipient, result in normalized_results:
            target = targets_by_recipient[recipient]
            if (
                result["model_provider_identity"] != self.binding.provider_identity
                or result["model_identity"] != self.binding.model_identity
                or result["prompt_identity"] != self.binding.prompt_identity
                or result["reasoning_identity"] != self.binding.reasoning_identity
                or result["config_identity"] != self.config_identity
                or result["tool_identity"] != self.tool_identity
                or result["budget_identity"] != self.budget_identity
                or result["external_call_limit"] != self.external_call_limit
                or result["external_calls_consumed"] > self.external_calls_consumed
                or result["rendered_prompt_identity"]
                != (
                    handoffs_by_recipient[recipient].request.prompt_artifact.content_hash
                    if recipient in handoffs_by_recipient
                    else pending_by_recipient[recipient].prompt_artifact.content_hash
                    if recipient in pending_by_recipient
                    else result["rendered_prompt_identity"]
                )
            ):
                raise ModelReplayError("model result identity bindings disagree with provider state")
            for candidate in result["candidates"]:
                if candidate.recipient_id != recipient or candidate.candidate.lane != self.lane:
                    raise ModelReplayError("model candidate crosses lane or recipient boundary")
                if not candidate.provenance:
                    raise ModelReplayError("model candidate is missing provenance")
            candidate_ids = [candidate.candidate_id for candidate in result["candidates"]]
            if len(set(candidate_ids)) != len(candidate_ids):
                raise ModelReplayError("model result contains duplicate candidates")
            if result["candidates"] and not result["provenance"]:
                raise ModelReplayError("model result is missing candidate provenance")
            handoff = handoffs_by_recipient.get(recipient)
            if handoff is not None and result["model_result_identity"] != handoff.result.result_identity:
                raise ModelReplayError("model result does not match its durable handoff")
            pending = pending_by_recipient.get(recipient)
            if result["external_call_consumed"] != int(handoff is not None or pending is not None):
                raise ModelReplayError("model result call charge does not match durable state")
            if pending is not None and result["candidates"]:
                raise ModelReplayError("pending model request cannot produce candidates")
            if handoff is None and pending is None and result["candidates"]:
                raise ModelReplayError("model candidate has no durable model handoff")
            if handoff is None and pending is None and (
                result["rendered_prompt_identity"]
                or result["completion_reason"] != "budget_exhausted"
                or result["refusal_code"] not in {
                    "model_budget_exhausted",
                    "model_external_call_budget_exhausted",
                }
            ):
                raise ModelReplayError("model result without a handoff is not a budget refusal")
            _validate_result_provenance(
                result,
                lane=self.lane,
                target=target,
                provider_identity=self.provider_identity,
                manifest_identity=self.manifest_identity,
                binding=self.binding,
                budget_identity=self.budget_identity,
                handoff=handoff,
                pending_request=pending,
                external_call_limit=self.external_call_limit,
                external_calls_consumed=self.external_calls_consumed,
            )
        object.__setattr__(
            self,
            "results",
            normalized_results,
        )
        expected_identity = _provider_identity(
            self.lane,
            self.manifest_identity,
            self.binding,
            self.target_inputs,
            self.budget_identity,
            self.external_call_limit,
        )
        legacy_identity = _provider_identity(
            self.lane,
            self.manifest_identity,
            self.binding,
            self.target_inputs,
            self.budget_identity,
            self.external_call_limit,
            include_external_call_limit=False,
        )
        if expected_identity != self.provider_identity and legacy_identity != self.provider_identity:
            raise ModelReplayError("model provider identity does not match its state")

    def callback(self, recipient: Recipient) -> Mapping[str, Any]:
        if not isinstance(recipient, Recipient):
            raise ModelInputError("model callback requires a typed Recipient")
        if recipient.recipient_id not in {item[0] for item in self.results}:
            raise ModelSubsetViolation("model callback recipient is outside the frozen subset")
        for key, result in self.results:
            if key == recipient.recipient_id:
                return dict(result)
        raise ModelSubsetViolation("model callback recipient is outside the frozen subset")

    @property
    def external_call_budget(self) -> int:
        """The immutable manifest-bound cap for provider invocations."""

        return int(self.external_call_limit)

    @property
    def calls_consumed(self) -> int:
        """Number of durable reservations, including typed failures."""

        return self.external_calls_consumed

    @property
    def candidate_attempts(self) -> int:
        """Accepted candidate fan-out, kept separate from call reservations."""

        return sum(result["attempts"] for _, result in self.results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": "sotn-model-lane-state-v1",
            "lane": self.lane,
            "manifest_identity": self.manifest_identity,
            "subset_identity": self.subset_identity,
            "config_identity": self.config_identity,
            "tool_identity": self.tool_identity,
            "provider_identity": self.provider_identity,
            "binding": self.binding.to_dict(),
            "budget": self.budget.to_dict(),
            "budget_identity": self.budget_identity,
            "target_inputs": [item.to_dict() for item in self.target_inputs],
            "handoffs": [item.to_dict() for item in self.handoffs],
            "pending_requests": [item.to_dict() for item in self.pending_requests],
            "external_call_limit": self.external_call_limit,
            "external_calls_consumed": self.external_calls_consumed,
            "results": [
                {"recipient_id": recipient, "result": _plain(result)}
                for recipient, result in self.results
            ],
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        archive: ContentAddressedArchive,
    ) -> "ModelLaneProvider":
        if not isinstance(value, Mapping):
            raise ModelReplayError("model lane state must be an object")
        fields = {"protocol", "lane", "manifest_identity", "subset_identity", "config_identity", "tool_identity", "provider_identity", "binding", "budget", "budget_identity", "target_inputs", "handoffs", "results"}
        extended_fields = fields | {"pending_requests", "external_call_limit", "external_calls_consumed"}
        if set(value) not in (fields, extended_fields) or value.get("protocol") != "sotn-model-lane-state-v1":
            raise ModelReplayError("model lane state has the wrong schema")
        targets = tuple(ArchivedModelTargetInput.from_dict(item) for item in value["target_inputs"])
        for target in targets:
            _verify_target_archives(archive, target)
        handoffs = tuple(ModelHandoff.from_dict(item) for item in value["handoffs"])
        for handoff in handoffs:
            _verify_request_archive(archive, handoff.request)
            _verify_response_archive(archive, handoff.response)
            _verify_result_archive(archive, handoff)
        pending_requests = tuple(
            ModelRequest.from_dict(item) for item in value.get("pending_requests", ())
        )
        for request in pending_requests:
            _verify_request_archive(archive, request)
        results = []
        for item in value["results"]:
            if not isinstance(item, Mapping) or set(item) != {"recipient_id", "result"}:
                raise ModelReplayError("model lane result entry has the wrong schema")
            if not isinstance(item["result"], Mapping):
                raise ModelReplayError("model lane result must be a mapping")
            results.append((item["recipient_id"], item["result"]))
        return cls(
            lane=value["lane"],
            manifest_identity=value["manifest_identity"],
            subset_identity=value["subset_identity"],
            config_identity=value["config_identity"],
            tool_identity=value["tool_identity"],
            provider_identity=value["provider_identity"],
            binding=ModelBinding.from_dict(value["binding"]),
            budget=Budget.from_dict(value["budget"]),
            budget_identity=value["budget_identity"],
            target_inputs=targets,
            handoffs=handoffs,
            pending_requests=pending_requests,
            external_call_limit=value.get("external_call_limit", 0),
            external_calls_consumed=value.get("external_calls_consumed", 0),
            results=tuple(results),
        )


def build_model_provider(
    lane: str,
    manifest: RunManifest,
    target_inputs: Sequence[ArchivedModelTargetInput] | Mapping[str, ArchivedModelTargetInput],
    binding: ModelBinding,
    *,
    archive: ContentAddressedArchive,
    provider: Optional[ModelProvider] = None,
    durable_results: Sequence[ModelHandoff] = (),
    external_call_budget: Optional[int] = None,
    fault_hook: Optional[ModelFaultHook] = None,
    fault_injector: Optional[ModelFaultHook] = None,
) -> ModelLaneProvider:
    """Build one model lane against an explicit manifest-bound subset.

    Construction is request-first: the archive is discovered before any new
    request is materialized.  A completed request is reconstructed directly;
    a request without a terminal result is returned as a durable pending
    refusal.  The optional ``durable_results`` argument is retained only as a
    compatibility assertion and can never supply replay state by itself.
    """

    validate_lane(lane)
    if lane not in MODEL_LANES:
        raise ModelInputError("build_model_provider only accepts model_fleet or model_expensive")
    if not isinstance(manifest, RunManifest):
        raise ModelInputError("manifest must be a typed RunManifest")
    if not isinstance(binding, ModelBinding):
        raise ModelInputError("binding must be a typed ModelBinding")
    if not isinstance(archive, ContentAddressedArchive):
        raise ModelInputError("archive must be a ContentAddressedArchive")
    if fault_hook is not None and fault_injector is not None:
        raise ModelInputError("fault_hook and fault_injector are mutually exclusive")
    fault = fault_hook if fault_hook is not None else fault_injector
    provider = _validate_provider(provider)
    targets = _validate_target_subset(manifest, target_inputs, lane)
    for target in targets:
        _verify_target_archives(archive, target)
    manifest_identity = _manifest_identity(manifest)
    if binding.config_identity != manifest.config_identity:
        raise ModelInputError("model binding config_identity differs from manifest")
    expected_tool = manifest.tool_identities.get(lane)
    if expected_tool != binding.tool_identity:
        raise ModelInputError("model binding tool_identity differs from manifest lane binding")
    budget = _budget_for(manifest, lane)
    external_limit = _external_call_limit(budget, external_call_budget)
    budget_identity = _budget_identity(lane, budget, binding, external_limit)
    provider_identity = _provider_identity(
        lane,
        manifest_identity,
        binding,
        targets,
        budget_identity,
        external_limit,
    )

    # Archive discovery is authoritative.  Caller-provided handoffs are
    # checked against it for compatibility, but never used to fill a missing
    # request or result.
    records = discover_model_archive(archive)
    _active_archive_records(
        records,
        lane=lane,
        manifest_identity=manifest_identity,
        targets=targets,
    )
    injected = _load_durable_handoffs(archive, durable_results)
    for request_id, handoff in injected.items():
        discovered = records.handoffs.get(request_id)
        if discovered is None or discovered.to_dict() != handoff.to_dict():
            raise ModelReplayError(
                "caller-supplied durable result is not present in the canonical archive"
            )

    handoffs: list[ModelHandoff] = []
    pending_requests: list[ModelRequest] = []
    results = []
    used_candidate_count = 0
    calls_consumed = 0
    used_request_ids: set[str] = set()
    target_recipients = {item.recipient_id for item in targets}
    for ordinal, target in enumerate(targets):
        rendered_prompt = _render_prompt(binding, target)
        expected_prompt_identity = hash_bytes(rendered_prompt.encode("utf-8"))
        scoped_requests = [
            request
            for request in records.requests.values()
            if request.lane == lane
            and request.manifest_identity == manifest_identity
            and request.recipient_id == target.recipient_id
        ]
        matching_requests = [
            request
            for request in scoped_requests
            if _request_matches_target(
                request,
                lane=lane,
                target=target,
                manifest=manifest,
                manifest_identity=manifest_identity,
                binding=binding,
                budget_identity=budget_identity,
                external_call_limit=external_limit,
                expected_prompt_identity=expected_prompt_identity,
                ordinal=ordinal,
            )
        ]
        if len(matching_requests) > 1:
            raise ModelReplayError("multiple archived requests claim one model recipient")
        if scoped_requests and not matching_requests:
            raise ModelReplayError("archived model request does not match current invocation")

        if matching_requests:
            request = matching_requests[0]
            used_request_ids.add(request.request_id)
            calls_consumed += 1
            if calls_consumed > external_limit:
                raise ModelReplayError("archived model requests exceed the external call budget")
            handoff = records.handoffs.get(request.request_id)
            if handoff is None:
                pending_requests.append(request)
                parsed = _failure_result("refused", "model request is durable and pending")
                parsed = ModelParsedResult(
                    status=parsed.status,
                    refusal_code="model_request_pending",
                    reason=parsed.reason,
                )
                result = _result_mapping(
                    lane=lane,
                    target=target,
                    parsed=parsed,
                    handoff=None,
                    pending_request=request,
                    provider_identity=provider_identity,
                    manifest_identity=manifest_identity,
                    binding=binding,
                    budget=budget,
                    budget_identity=budget_identity,
                    external_call_limit=external_limit,
                    external_calls_consumed=calls_consumed,
                    external_call_consumed=1,
                    candidate_limit=_candidate_limit(
                        budget, binding, used_candidate_count
                    ),
                )
                results.append((target.recipient_id, result))
                continue
            if handoff.request.to_dict() != request.to_dict():
                raise ModelReplayError("archived model handoff request does not match its request")
            handoffs.append(handoff)
            result = _result_mapping(
                lane=lane,
                target=target,
                parsed=handoff.result,
                handoff=handoff,
                provider_identity=provider_identity,
                manifest_identity=manifest_identity,
                binding=binding,
                budget=budget,
                budget_identity=budget_identity,
                external_call_limit=external_limit,
                external_calls_consumed=calls_consumed,
                external_call_consumed=1,
                candidate_limit=_candidate_limit(
                    budget, binding, used_candidate_count
                ),
            )
            results.append((target.recipient_id, result))
            used_candidate_count += result["attempts"]
            continue

        # A completed or pending archive reservation is charged already.  A
        # new reservation is allowed only while the explicit external cap has
        # room, and the charge is established before the provider callback.
        if calls_consumed >= external_limit:
            parsed = _failure_result("refused", "model budget is zero")
            parsed = ModelParsedResult(
                status=parsed.status,
                refusal_code=(
                    "model_budget_exhausted"
                    if budget.limit == 0
                    else "model_external_call_budget_exhausted"
                ),
                reason=parsed.reason,
            )
            results.append(
                (
                    target.recipient_id,
                    _result_mapping(
                        lane=lane,
                        target=target,
                        parsed=parsed,
                        handoff=None,
                        provider_identity=provider_identity,
                        manifest_identity=manifest_identity,
                        binding=binding,
                        budget=budget,
                        budget_identity=budget_identity,
                        external_call_limit=external_limit,
                        external_calls_consumed=calls_consumed,
                        external_call_consumed=0,
                        candidate_limit=0,
                    ),
                )
            )
            continue
        _call_fault(fault, MODEL_FAULT_BEFORE_REQUEST)
        request = _make_request(
            lane=lane,
            target=target,
            manifest=manifest,
            manifest_identity=manifest_identity,
            binding=binding,
            budget_identity=budget_identity,
            archive=archive,
            ordinal=ordinal,
            external_call_limit=external_limit,
        )
        _verify_request_archive(archive, request)
        _call_fault(fault, MODEL_FAULT_AFTER_REQUEST)
        calls_consumed += 1
        _call_fault(fault, MODEL_FAULT_BEFORE_CALLBACK)
        prompt = _archive_verify(
            archive,
            request.prompt_artifact,
            rendered_prompt.encode("utf-8"),
            "model prompt artifact",
        ).decode("utf-8")
        if provider is None:
            response = ModelResponse(
                request_id=request.request_id,
                status="unavailable",
                error_code="model_provider_unavailable",
                detail="no typed model provider was configured",
            )
        else:
            try:
                response = provider.invoke(
                    request,
                    prompt=prompt,
                    contexts=tuple(target.context_bytes),
                )
            except ModelUnavailable as exc:
                response = ModelResponse(request.request_id, "unavailable", detail=str(exc))
            except ModelTimeout as exc:
                response = ModelResponse(request.request_id, "timeout", detail=str(exc))
            except ModelRefused as exc:
                response = ModelResponse(request.request_id, "refused", detail=str(exc))
            except ModelInvalidResponse as exc:
                response = ModelResponse(request.request_id, "invalid", detail=str(exc))
            except Exception as exc:  # provider failures are typed and charged
                response = ModelResponse(
                    request.request_id,
                    "invalid",
                    detail=f"provider raised {type(exc).__name__}: {exc}",
                )
        _call_fault(fault, MODEL_FAULT_AFTER_CALLBACK)
        try:
            response = _response_from_provider(request, response, archive)
        except ModelInvalidResponse as exc:
            response = ModelResponse(
                request_id=request.request_id,
                status="invalid",
                detail=str(exc),
            )
            response = _response_from_provider(request, response, archive)
        _verify_response_archive(archive, response)
        _call_fault(fault, MODEL_FAULT_AFTER_RESPONSE)
        if response.status == "ok":
            try:
                parsed = _parse_model_text(
                    response.response_text,
                    max_response_bytes=binding.max_response_bytes,
                )
            except ModelInvalidResponse as exc:
                parsed = _failure_result("invalid", str(exc))
        else:
            parsed = _failure_result(response.status, response.detail)
        handoff = _make_handoff(request, response, parsed, archive)
        _call_fault(fault, MODEL_FAULT_AFTER_RESULT)
        used_request_ids.add(request.request_id)
        handoffs.append(handoff)
        result = _result_mapping(
            lane=lane,
            target=target,
            parsed=handoff.result,
            handoff=handoff,
            provider_identity=provider_identity,
            manifest_identity=manifest_identity,
            binding=binding,
            budget=budget,
            budget_identity=budget_identity,
            external_call_limit=external_limit,
            external_calls_consumed=calls_consumed,
            external_call_consumed=1,
            candidate_limit=_candidate_limit(budget, binding, used_candidate_count),
        )
        results.append((target.recipient_id, result))
        used_candidate_count += result["attempts"]
    unused_archive_requests = {
        request_id
        for request_id, request in records.requests.items()
        if request.lane == lane
        and (
            request.manifest_identity == manifest_identity
            or request.recipient_id in target_recipients
        )
        and request_id not in used_request_ids
    }
    if unused_archive_requests:
        raise ModelReplayError("archived model request is outside the active invocation")
    return ModelLaneProvider(
        lane=lane,
        manifest_identity=manifest_identity,
        subset_identity=manifest.subset_identity,
        config_identity=manifest.config_identity,
        tool_identity=binding.tool_identity,
        provider_identity=provider_identity,
        binding=binding,
        budget=budget,
        budget_identity=budget_identity,
        target_inputs=targets,
        handoffs=tuple(sorted(handoffs, key=lambda item: item.request.recipient_id)),
        pending_requests=tuple(
            sorted(pending_requests, key=lambda item: item.recipient_id)
        ),
        external_call_limit=external_limit,
        external_calls_consumed=calls_consumed,
        results=tuple(sorted(results, key=lambda item: item[0])),
    )


def build_model_fleet_provider(
    manifest: RunManifest,
    target_inputs: Sequence[ArchivedModelTargetInput] | Mapping[str, ArchivedModelTargetInput],
    binding: ModelBinding,
    *,
    archive: ContentAddressedArchive,
    provider: Optional[ModelProvider] = None,
    durable_results: Sequence[ModelHandoff] = (),
    external_call_budget: Optional[int] = None,
    fault_hook: Optional[ModelFaultHook] = None,
    fault_injector: Optional[ModelFaultHook] = None,
) -> ModelLaneProvider:
    return build_model_provider(
        MODEL_FLEET_LANE,
        manifest,
        target_inputs,
        binding,
        archive=archive,
        provider=provider,
        durable_results=durable_results,
        external_call_budget=external_call_budget,
        fault_hook=fault_hook,
        fault_injector=fault_injector,
    )


def build_model_expensive_provider(
    manifest: RunManifest,
    target_inputs: Sequence[ArchivedModelTargetInput] | Mapping[str, ArchivedModelTargetInput],
    binding: ModelBinding,
    *,
    archive: ContentAddressedArchive,
    provider: Optional[ModelProvider] = None,
    durable_results: Sequence[ModelHandoff] = (),
    external_call_budget: Optional[int] = None,
    fault_hook: Optional[ModelFaultHook] = None,
    fault_injector: Optional[ModelFaultHook] = None,
) -> ModelLaneProvider:
    return build_model_provider(
        MODEL_EXPENSIVE_LANE,
        manifest,
        target_inputs,
        binding,
        archive=archive,
        provider=provider,
        durable_results=durable_results,
        external_call_budget=external_call_budget,
        fault_hook=fault_hook,
        fault_injector=fault_injector,
    )


def model_fleet_adapter(
    manifest: RunManifest,
    target_inputs: Sequence[ArchivedModelTargetInput] | Mapping[str, ArchivedModelTargetInput],
    binding: ModelBinding,
    *,
    archive: ContentAddressedArchive,
    provider: Optional[ModelProvider] = None,
    durable_results: Sequence[ModelHandoff] = (),
    external_call_budget: Optional[int] = None,
    fault_hook: Optional[ModelFaultHook] = None,
    fault_injector: Optional[ModelFaultHook] = None,
):
    return build_model_fleet_provider(
        manifest,
        target_inputs,
        binding,
        archive=archive,
        provider=provider,
        durable_results=durable_results,
        external_call_budget=external_call_budget,
        fault_hook=fault_hook,
        fault_injector=fault_injector,
    ).callback


def model_expensive_adapter(
    manifest: RunManifest,
    target_inputs: Sequence[ArchivedModelTargetInput] | Mapping[str, ArchivedModelTargetInput],
    binding: ModelBinding,
    *,
    archive: ContentAddressedArchive,
    provider: Optional[ModelProvider] = None,
    durable_results: Sequence[ModelHandoff] = (),
    external_call_budget: Optional[int] = None,
    fault_hook: Optional[ModelFaultHook] = None,
    fault_injector: Optional[ModelFaultHook] = None,
):
    return build_model_expensive_provider(
        manifest,
        target_inputs,
        binding,
        archive=archive,
        provider=provider,
        durable_results=durable_results,
        external_call_budget=external_call_budget,
        fault_hook=fault_hook,
        fault_injector=fault_injector,
    ).callback


def model_lane_adapters(
    manifest: RunManifest,
    target_inputs: Sequence[ArchivedModelTargetInput] | Mapping[str, ArchivedModelTargetInput],
    bindings: Mapping[str, ModelBinding],
    *,
    archive: ContentAddressedArchive,
    providers: Optional[Mapping[str, ModelProvider]] = None,
    durable_results: Optional[Mapping[str, Sequence[ModelHandoff]]] = None,
    external_call_budgets: Optional[Mapping[str, int]] = None,
    fault_hooks: Optional[Mapping[str, ModelFaultHook]] = None,
) -> Mapping[str, Any]:
    """Return ordinary lane callbacks for selected model lanes only."""

    providers = {} if providers is None else dict(providers)
    durable_results = {} if durable_results is None else dict(durable_results)
    external_call_budgets = {} if external_call_budgets is None else dict(external_call_budgets)
    fault_hooks = {} if fault_hooks is None else dict(fault_hooks)
    unknown = set(bindings).difference(MODEL_LANES)
    if unknown:
        raise ModelInputError("bindings contain unknown model lanes")
    unknown = set(providers).difference(MODEL_LANES)
    if unknown:
        raise ModelInputError("providers contain unknown model lanes")
    unknown = set(durable_results).difference(MODEL_LANES)
    if unknown:
        raise ModelInputError("durable_results contain unknown model lanes")
    unknown = set(external_call_budgets).difference(MODEL_LANES)
    if unknown:
        raise ModelInputError("external_call_budgets contain unknown model lanes")
    unknown = set(fault_hooks).difference(MODEL_LANES)
    if unknown:
        raise ModelInputError("fault_hooks contain unknown model lanes")
    result = {}
    for lane in MODEL_LANES:
        if lane not in manifest.selected_lanes:
            continue
        if lane not in bindings:
            raise ModelInputError("selected model lane has no typed binding")
        provider = build_model_provider(
            lane,
            manifest,
            target_inputs,
            bindings[lane],
            archive=archive,
            provider=providers.get(lane),
            durable_results=durable_results.get(lane, ()),
            external_call_budget=external_call_budgets.get(lane),
            fault_hook=fault_hooks.get(lane),
        )
        result[lane] = provider.callback
    return MappingProxyType(result)


# These descriptive aliases mirror the other production lane modules and keep
# registry wiring independent of the internal builder name.
make_model_fleet_adapter = model_fleet_adapter
make_model_expensive_adapter = model_expensive_adapter
make_model_lane_adapters = model_lane_adapters


__all__ = [
    "ARCHIVE_IDENTITY",
    "ArchivedModelTargetInput",
    "MODEL_FAULT_AFTER_REQUEST",
    "MODEL_FAULT_AFTER_RESPONSE",
    "MODEL_FAULT_AFTER_RESULT",
    "MODEL_FAULT_AFTER_CALLBACK",
    "MODEL_FAULT_BEFORE_REQUEST",
    "MODEL_FAULT_BEFORE_CALLBACK",
    "MODEL_FAULT_POINTS",
    "MODEL_EXPENSIVE_LANE",
    "MODEL_FLEET_LANE",
    "MODEL_LANES",
    "SUPPORTED_TARGET_PLATFORMS",
    "ModelBinding",
    "ModelBudgetError",
    "ModelHandoff",
    "ModelInputError",
    "ModelInvalidResponse",
    "ModelLaneError",
    "ModelLaneProvider",
    "ModelArchiveRecords",
    "ModelParsedResult",
    "ModelProvider",
    "ModelProviderProtocolError",
    "ModelRefused",
    "ModelReplayError",
    "ModelRequest",
    "ModelResponse",
    "ModelSubsetViolation",
    "ModelTargetInput",
    "ModelTimeout",
    "build_model_expensive_provider",
    "build_model_fleet_provider",
    "build_model_provider",
    "discover_model_archive",
    "make_model_expensive_adapter",
    "make_model_fleet_adapter",
    "make_model_lane_adapters",
    "model_expensive_adapter",
    "model_fleet_adapter",
    "model_lane_adapters",
]
