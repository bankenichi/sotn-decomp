"""Lazy model execution specification for immutable production factory state."""
from __future__ import annotations

from dataclasses import dataclass

from .search_model_executor import TrustedModelExecutor
from .search_model_lanes import (
    ArchivedModelTargetInput, ModelBinding, ModelInputError, ModelSubsetViolation,
    _budget_for, _external_call_limit, _validate_target_subset, _verify_target_archives,
    build_model_provider,
)
from .search_types import RunManifest, hash_canonical

PROTOCOL = "sotn-model-lazy-provider-v1"


@dataclass(frozen=True)
class DeferredModelLaneProvider:
    manifest: RunManifest
    lane: str
    target_inputs: tuple[ArchivedModelTargetInput, ...]
    binding: ModelBinding
    archive: object
    executor: TrustedModelExecutor

    def __post_init__(self):
        if not isinstance(self.manifest, RunManifest) or not isinstance(self.executor, TrustedModelExecutor):
            raise ModelInputError("lazy model provider requires a manifest and concrete executor")
        targets = _validate_target_subset(self.manifest, self.target_inputs, self.lane)
        object.__setattr__(self, "target_inputs", targets)
        for target in targets:
            _verify_target_archives(self.archive, target)
        if self.binding.config_identity != self.config_identity or self.binding.tool_identity != self.tool_identity:
            raise ModelInputError("lazy model binding differs from manifest")
        for field, expected in {
            "lane": self.lane, "manifest_identity": self.manifest_identity,
            "subset_identity": self.subset_identity, "config_identity": self.config_identity,
            "tool_identity": self.tool_identity, "provider_identity": self.binding.provider_identity,
            "model_identity": self.binding.model_identity, "prompt_identity": self.binding.prompt_identity,
            "reasoning_identity": self.binding.reasoning_identity,
        }.items():
            if getattr(self.executor, field) != expected:
                raise ModelInputError("lazy model executor binding differs: " + field)
        _external_call_limit(_budget_for(self.manifest, self.lane), None)

    @property
    def manifest_identity(self):
        return hash_canonical(self.manifest.to_dict())

    @property
    def subset_identity(self):
        return self.manifest.subset_identity

    @property
    def config_identity(self):
        return self.manifest.config_identity

    @property
    def tool_identity(self):
        return self.manifest.tool_identities[self.lane]

    @property
    def provider_identity(self):
        return hash_canonical(self._payload())

    def _payload(self):
        return {
            "protocol": PROTOCOL, "manifest": self.manifest.to_dict(), "lane": self.lane,
            "binding": self.binding.to_dict(),
            "target_inputs": [target.to_dict() for target in self.target_inputs],
            "executor_identity": self.executor.executor_identity,
        }

    def to_dict(self):
        return {**self._payload(), "provider_identity": self.provider_identity}

    @classmethod
    def from_dict(cls, value, *, archive, executor):
        if set(value) != {"protocol", "manifest", "lane", "binding", "target_inputs", "executor_identity", "provider_identity"} or value["protocol"] != PROTOCOL:
            raise ModelInputError("lazy model provider schema differs")
        provider = cls(
            RunManifest.from_dict(value["manifest"]), value["lane"],
            tuple(ArchivedModelTargetInput.from_dict(item) for item in value["target_inputs"]),
            ModelBinding.from_dict(value["binding"]), archive, executor,
        )
        if provider.to_dict() != value:
            raise ModelInputError("lazy model provider immutable identity differs")
        return provider

    def callback(self, recipient):
        if recipient.recipient_id not in {target.recipient_id for target in self.target_inputs}:
            raise ModelSubsetViolation("model recipient is outside the frozen subset")
        return build_model_provider(
            self.lane, self.manifest, self.target_inputs, self.binding,
            archive=self.archive, provider=self.executor, _recipient=recipient.recipient_id,
        )

    def to_adapter_mapping(self):
        return {self.lane: self.callback}
