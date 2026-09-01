#!/usr/bin/env python3
"""Manifest-bound production provider reconstruction for search lanes.

The provider registry is the process-restart boundary between a canonical run
archive and ordinary :class:`LaneAdapters` callbacks.  A factory-created run
does not accept callbacks, paths, or executable objects from its caller.  It
loads one content-addressed provider-state document, reconstructs each typed
provider from that document, and verifies every binding against the supplied
typed manifest before exposing a callback.

The state document is deliberately a small envelope around the already strict
provider records.  It is useful to the factory because it can archive the
complete state after constructing providers, while reconstruction remains
read-only and does not need to mine a corpus, invoke a model, run m2c, or run
the permuter.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from .search_archive import ArchiveError, ArtifactRef, ContentAddressedArchive
    from .search_generated_lanes import GENERATED_LANES, GeneratedLaneProvider
    from .search_idiom_atlas import IDIOM_LANE, IdiomAtlasProvider
    from .search_indexed_lane import production_indexed_adapters
    from .search_indexed_runtime import load_indexed_runtime, verify_indexed_runtime
    from .search_lanes import LaneAdapters, LaneError
    from .search_model_executor import TrustedModelExecutor
    from .search_model_lanes import MODEL_LANES, ModelLaneProvider
    from .search_permuter_executor import PermuterExecutor
    from .search_permuter_lanes import PERMUTER_LANES, PermuterLaneProvider
    from .search_types import (
        LANES,
        RunManifest,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
    )
except ImportError:  # direct invocation from automation/
    from search_archive import ArchiveError, ArtifactRef, ContentAddressedArchive  # type: ignore
    from search_generated_lanes import GENERATED_LANES, GeneratedLaneProvider  # type: ignore
    from search_idiom_atlas import IDIOM_LANE, IdiomAtlasProvider  # type: ignore
    from search_indexed_lane import production_indexed_adapters  # type: ignore
    from search_indexed_runtime import (  # type: ignore
        load_indexed_runtime,
        verify_indexed_runtime,
    )
    from search_lanes import LaneAdapters, LaneError  # type: ignore
    from search_model_executor import TrustedModelExecutor  # type: ignore
    from search_model_lanes import MODEL_LANES, ModelLaneProvider  # type: ignore
    from search_permuter_executor import PermuterExecutor  # type: ignore
    from search_permuter_lanes import PERMUTER_LANES, PermuterLaneProvider  # type: ignore
    from search_types import (  # type: ignore
        LANES,
        RunManifest,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
    )


INDEXED_LANES = frozenset({"multi_donor", "cfg_dataflow"})
INDEXED_RUNTIME_TOOL_KEY = "indexed_runtime"
GENERATED_PROVIDER_LANES = tuple(GENERATED_LANES)
PERMUTER_PROVIDER_LANES = tuple(PERMUTER_LANES)
MODEL_PROVIDER_LANES = tuple(MODEL_LANES)
EXTERNAL_LANES = (
    "m2c_ensemble",
    IDIOM_LANE,
    "bounded_synthesis",
    *PERMUTER_PROVIDER_LANES,
    *MODEL_PROVIDER_LANES,
)
PROVIDER_REGISTRY_PROTOCOL = "sotn-search-provider-registry-v1"
PROVIDER_STATE_PROTOCOL = "sotn-search-provider-state-v1"
PROVIDER_STATE_SCHEMA_VERSION = 1
PROVIDER_STATE_CATEGORY = "provider-state"
PROVIDER_STATE_SUFFIX = ".json"


class ProviderRegistryError(LaneError):
    """Production provider state is absent, corrupt, or not manifest-bound."""


ProviderBuilder = Callable[[RunManifest, Path], LaneAdapters]

_STATE_FIELDS = {
    "protocol",
    "schema_version",
    "run_id",
    "manifest_identity",
    "selected_lanes",
    "providers",
    "state_identity",
}
_STATE_RECORD_FIELDS = {
    "lane",
    "provider",
    "provider_identity",
    "executor",
    "executor_identity",
}
_EXTERNAL_SET = frozenset(EXTERNAL_LANES)
_PERMUTER_SET = frozenset(PERMUTER_PROVIDER_LANES)
_MODEL_SET = frozenset(MODEL_PROVIDER_LANES)
_GENERATED_SET = frozenset(GENERATED_PROVIDER_LANES)


def _provider_state_payload(
    manifest: RunManifest,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return the state payload without its derived identity."""

    return {
        "protocol": PROVIDER_STATE_PROTOCOL,
        "schema_version": PROVIDER_STATE_SCHEMA_VERSION,
        "run_id": manifest.run_id,
        "manifest_identity": hash_canonical(manifest.to_dict()),
        "selected_lanes": list(manifest.selected_lanes),
        "providers": [dict(record) for record in records],
    }


def _provider_lane(provider: Any) -> Optional[str]:
    lane = getattr(provider, "lane", None)
    if isinstance(lane, str):
        return lane
    config = getattr(provider, "config", None)
    lane = getattr(config, "lane", None)
    return lane if isinstance(lane, str) else None


def _executor_identity(executor: Any) -> str:
    value = getattr(executor, "executor_identity", None)
    if isinstance(value, str):
        return value
    value = getattr(executor, "identity", None)
    if isinstance(value, str):
        return value
    raise ProviderRegistryError("provider executor has no typed identity")


def provider_state_document(
    manifest: RunManifest,
    providers: Mapping[str, Any],
    *,
    executors: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Serialize complete provider/executor state for factory archiving.

    ``providers`` contains typed released provider objects.  A value may be a
    provider or a two-item ``(provider, executor)`` tuple.  The optional
    ``executors`` mapping is convenient when providers and executors are
    constructed independently.  This helper is pure and never writes the
    archive; the factory owns the subsequent ``archive.put_json`` call.
    """

    if not isinstance(manifest, RunManifest):
        raise ProviderRegistryError("provider-state serialization needs a typed manifest")
    if not isinstance(providers, Mapping):
        raise ProviderRegistryError("provider-state providers must be a mapping")
    if executors is not None and not isinstance(executors, Mapping):
        raise ProviderRegistryError("provider-state executors must be a mapping")
    expected = tuple(lane for lane in EXTERNAL_LANES if lane in manifest.selected_lanes)
    if set(providers) != set(expected):
        raise ProviderRegistryError("provider-state providers do not cover selected external lanes")
    if executors is not None and set(executors).difference(expected):
        raise ProviderRegistryError("provider-state executors contain an unselected lane")

    records: list[Mapping[str, Any]] = []
    for lane in expected:
        value = providers[lane]
        executor = executors.get(lane) if executors is not None else None
        if isinstance(value, tuple) and len(value) == 2:
            if executor is not None:
                raise ProviderRegistryError("provider-state executor is supplied twice")
            value, executor = value
        if _provider_lane(value) != lane or not hasattr(value, "to_dict"):
            raise ProviderRegistryError("provider-state provider is not typed for " + lane)
        if lane in _PERMUTER_SET:
            if not isinstance(value, PermuterLaneProvider):
                raise ProviderRegistryError("permuter provider type differs for " + lane)
            if not isinstance(executor, PermuterExecutor):
                raise ProviderRegistryError("permuter executor is required for " + lane)
        elif lane in _MODEL_SET:
            if not isinstance(value, ModelLaneProvider):
                raise ProviderRegistryError("model provider type differs for " + lane)
            if not isinstance(executor, TrustedModelExecutor):
                raise ProviderRegistryError("model executor is required for " + lane)
        elif lane in _GENERATED_SET:
            if not isinstance(value, GeneratedLaneProvider):
                raise ProviderRegistryError("generated provider type differs for " + lane)
            if executor is not None:
                raise ProviderRegistryError("generated lanes do not accept an executor")
        elif lane == IDIOM_LANE:
            if not isinstance(value, IdiomAtlasProvider):
                raise ProviderRegistryError("idiom provider type differs")
            if executor is not None:
                raise ProviderRegistryError("idiom atlas does not accept an executor")
        provider_state = value.to_dict()
        if not isinstance(provider_state, Mapping):
            raise ProviderRegistryError("provider to_dict did not return an object")
        provider_state = dict(provider_state)
        provider_identity = provider_state.get("provider_identity")
        _require_hash(provider_identity, "provider identity")
        if executor is None:
            executor_state = None
            executor_identity = None
        else:
            executor_state = executor.to_dict()
            if not isinstance(executor_state, Mapping):
                raise ProviderRegistryError("executor to_dict did not return an object")
            executor_state = dict(executor_state)
            executor_identity = _executor_identity(executor)
            _require_hash(executor_identity, "executor identity")
            if executor_state.get("executor_identity") != executor_identity:
                raise ProviderRegistryError("executor state identity differs from executor")
        records.append(
            {
                "lane": lane,
                "provider": provider_state,
                "provider_identity": provider_identity,
                "executor": executor_state,
                "executor_identity": executor_identity,
            }
        )

    payload = _provider_state_payload(manifest, records)
    payload["state_identity"] = hash_canonical(payload)
    return payload


serialize_provider_state = provider_state_document


def _require_hash(value: Any, label: str) -> str:
    try:
        return validate_hash(value, label)
    except Exception as exc:
        raise ProviderRegistryError(label + " is invalid") from exc


def _repo_for_run(run_root: Path) -> Path:
    """Return the repository owning one canonical factory run root."""

    supplied = Path(run_root)
    if supplied.is_symlink():
        raise ProviderRegistryError("production run root must not be a symlink")
    try:
        root = supplied.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ProviderRegistryError("production run root cannot be resolved") from exc
    if not root.is_dir():
        raise ProviderRegistryError("production run root is not a real directory")
    try:
        nonmatchings = root.parents[2]
        repo = root.parents[3]
    except IndexError as exc:
        raise ProviderRegistryError("production run root is not canonical") from exc
    if (
        nonmatchings.name != "nonmatchings"
        or root.parent.name != "search-runs"
        or root.parent.parent.parent != nonmatchings
        or repo / "nonmatchings" != nonmatchings
    ):
        raise ProviderRegistryError("production run root is not canonical")
    return repo


def _canonical_run_root(run_root: Path | str, manifest: RunManifest) -> Path:
    supplied = Path(run_root)
    if supplied.is_symlink():
        raise ProviderRegistryError("production run root must not be a symlink")
    try:
        root = supplied.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ProviderRegistryError("production run root cannot be resolved") from exc
    if not root.is_dir() or root.name != manifest.run_id:
        raise ProviderRegistryError("production run root is not the manifest run")
    try:
        nonmatchings = root.parents[2]
    except IndexError as exc:
        raise ProviderRegistryError("production run root is not canonical") from exc
    if (
        nonmatchings.name != "nonmatchings"
        or root.parent.name != "search-runs"
        or root.parent.parent.parent != nonmatchings
    ):
        raise ProviderRegistryError("production run root is not canonical")
    return root


def _duplicate_rejecting_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field: " + key)
        result[key] = value
    return result


def _decode_state(raw: bytes) -> Mapping[str, Any]:
    try:
        decoded = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_duplicate_rejecting_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise ProviderRegistryError("provider-state artifact is not valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ProviderRegistryError("provider-state artifact must contain an object")
    return decoded


def _load_provider_state(
    manifest: RunManifest,
    run_root: Path | str,
) -> tuple[ContentAddressedArchive, Mapping[str, Any]]:
    """Read exactly one canonical provider-state artifact without writing."""

    root = _canonical_run_root(run_root, manifest)
    archive = ContentAddressedArchive(root)
    category = archive.artifacts_root / PROVIDER_STATE_CATEGORY
    if category.is_symlink() or not category.is_dir():
        raise ProviderRegistryError("provider-state artifact is missing")
    try:
        entries = sorted(category.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise ProviderRegistryError("provider-state artifact directory cannot be read") from exc
    if not entries:
        raise ProviderRegistryError("provider-state artifact is missing")

    documents: list[Mapping[str, Any]] = []
    for entry in entries:
        if entry.is_symlink() or not entry.is_file():
            raise ProviderRegistryError("provider-state directory contains a non-file")
        if not entry.name.endswith(PROVIDER_STATE_SUFFIX):
            raise ProviderRegistryError("provider-state artifact has an invalid name")
        digest_text = entry.name[: -len(PROVIDER_STATE_SUFFIX)]
        if len(digest_text) != 64 or any(char not in "0123456789abcdef" for char in digest_text):
            raise ProviderRegistryError("provider-state artifact name is not content addressed")
        try:
            raw = entry.read_bytes()
        except OSError as exc:
            raise ProviderRegistryError("provider-state artifact cannot be read") from exc
        expected_hash = hash_bytes(raw)
        if expected_hash != "sha256:" + digest_text:
            raise ProviderRegistryError("provider-state artifact content hash differs from its name")
        reference = ArtifactRef(
            content_hash=expected_hash,
            path=(Path("artifacts") / PROVIDER_STATE_CATEGORY / entry.name).as_posix(),
            media_type="application/json",
            byte_size=len(raw),
        )
        try:
            verified = archive.verify(reference)
        except (ArchiveError, OSError, ValueError) as exc:
            raise ProviderRegistryError("provider-state artifact failed archive verification") from exc
        decoded = _decode_state(raw)
        if verified != raw or raw != canonical_bytes(decoded):
            raise ProviderRegistryError("provider-state artifact is not canonical JSON")
        documents.append(decoded)

    manifest_identity = hash_canonical(manifest.to_dict())
    matching: list[Mapping[str, Any]] = []
    for document in documents:
        if set(document) != _STATE_FIELDS:
            raise ProviderRegistryError("provider-state envelope has unknown or missing fields")
        if document.get("protocol") != PROVIDER_STATE_PROTOCOL:
            raise ProviderRegistryError("provider-state protocol differs")
        if type(document.get("schema_version")) is not int or document.get("schema_version") != PROVIDER_STATE_SCHEMA_VERSION:
            raise ProviderRegistryError("provider-state schema version differs")
        if document.get("run_id") != manifest.run_id:
            raise ProviderRegistryError("provider-state run identity differs")
        if document.get("manifest_identity") != manifest_identity:
            raise ProviderRegistryError("provider-state manifest identity differs")
        selected = document.get("selected_lanes")
        if type(selected) is not list or tuple(selected) != tuple(manifest.selected_lanes):
            raise ProviderRegistryError("provider-state selected lanes differ")
        state_identity = _require_hash(document.get("state_identity"), "provider-state identity")
        payload = dict(document)
        del payload["state_identity"]
        if state_identity != hash_canonical(payload):
            raise ProviderRegistryError("provider-state identity is forged")
        matching.append(document)
    if len(matching) != 1:
        raise ProviderRegistryError("provider-state artifact is missing or ambiguous")

    document = matching[0]
    providers = document.get("providers")
    if type(providers) is not list:
        raise ProviderRegistryError("provider-state providers must be a list")
    expected_lanes = tuple(lane for lane in EXTERNAL_LANES if lane in manifest.selected_lanes)
    seen: list[str] = []
    for record in providers:
        if not isinstance(record, Mapping) or set(record) != _STATE_RECORD_FIELDS:
            raise ProviderRegistryError("provider-state record has unknown or missing fields")
        lane = record.get("lane")
        if lane not in _EXTERNAL_SET or lane not in manifest.selected_lanes:
            raise ProviderRegistryError("provider-state record lane is not selected")
        if lane in seen:
            raise ProviderRegistryError("provider-state contains duplicate lane records")
        seen.append(lane)
        _require_hash(record.get("provider_identity"), "provider-state provider identity")
        provider = record.get("provider")
        if not isinstance(provider, Mapping):
            raise ProviderRegistryError("provider-state provider record must be an object")
        provider_identity = provider.get("provider_identity")
        if provider_identity != record.get("provider_identity"):
            raise ProviderRegistryError("provider-state provider identity differs")
        executor = record.get("executor")
        executor_identity = record.get("executor_identity")
        if executor is None:
            if executor_identity is not None:
                raise ProviderRegistryError("provider-state executor identity has no executor")
        else:
            if not isinstance(executor, Mapping):
                raise ProviderRegistryError("provider-state executor record must be an object")
            _require_hash(executor_identity, "provider-state executor identity")
            if executor.get("executor_identity") != executor_identity:
                raise ProviderRegistryError("provider-state executor identity differs")
    if tuple(seen) != expected_lanes:
        raise ProviderRegistryError("provider-state records do not cover selected external lanes")
    return archive, document


def _record_for(state: Mapping[str, Any], lane: str) -> Mapping[str, Any]:
    for record in state["providers"]:
        if record["lane"] == lane:
            return record
    raise ProviderRegistryError("provider-state record is missing for " + lane)


def _target_ids(provider: Any) -> tuple[str, ...]:
    targets = getattr(provider, "target_inputs", None)
    if targets is None:
        inputs = getattr(provider, "inputs", None)
        if isinstance(inputs, Mapping):
            targets = tuple(inputs.values())
    if isinstance(targets, (str, bytes, bytearray)) or not isinstance(targets, Sequence):
        raise ProviderRegistryError("provider target subset is unavailable")
    ids: list[str] = []
    for item in targets:
        recipient_id = getattr(item, "recipient_id", None)
        if not isinstance(recipient_id, str):
            raise ProviderRegistryError("provider target subset is not typed")
        ids.append(recipient_id)
    return tuple(ids)


def _validate_provider_binding(
    manifest: RunManifest,
    lane: str,
    provider: Any,
    record: Mapping[str, Any],
) -> None:
    manifest_identity = hash_canonical(manifest.to_dict())
    if _provider_lane(provider) != lane:
        raise ProviderRegistryError("reconstructed provider lane differs for " + lane)
    if getattr(provider, "manifest_identity", None) != manifest_identity:
        raise ProviderRegistryError("reconstructed provider manifest identity differs for " + lane)
    provider_config_identity = getattr(provider, "config_identity", None)
    if provider_config_identity is None and lane in _PERMUTER_SET:
        provider_config_identity = getattr(getattr(provider, "config", None), "identity", None)
    if lane not in _PERMUTER_SET and provider_config_identity != manifest.config_identity:
        raise ProviderRegistryError("reconstructed provider config identity differs for " + lane)
    if getattr(provider, "provider_identity", None) != record["provider_identity"]:
        raise ProviderRegistryError("reconstructed provider identity differs for " + lane)
    selected_ids = tuple(manifest.queue_record_ids)
    actual_ids = _target_ids(provider)
    if actual_ids != tuple(sorted(actual_ids)) or actual_ids != selected_ids:
        raise ProviderRegistryError("reconstructed provider subset differs for " + lane)
    for item in getattr(provider, "target_inputs", ()):
        recipient_id = getattr(item, "recipient_id", None)
        target_identity = getattr(item, "target_identity", None)
        if target_identity is not None and manifest.target_identities.get(recipient_id) != target_identity:
            raise ProviderRegistryError("reconstructed target identity differs for " + lane)

    expected_tool = manifest.tool_identities.get(lane)
    if lane in _PERMUTER_SET:
        if getattr(provider, "manifest_tool_identity", None) != expected_tool:
            raise ProviderRegistryError("permuter manifest tool identity differs for " + lane)
        binding = getattr(provider, "binding", None)
        if getattr(binding, "lane", None) != lane:
            raise ProviderRegistryError("permuter binding lane differs for " + lane)
    elif getattr(provider, "tool_identity", None) != expected_tool:
        raise ProviderRegistryError("reconstructed provider tool identity differs for " + lane)

    if lane in _MODEL_SET:
        if getattr(provider, "subset_identity", None) != manifest.subset_identity:
            raise ProviderRegistryError("model subset identity differs for " + lane)
        binding = getattr(provider, "binding", None)
        if getattr(binding, "config_identity", None) != manifest.config_identity or getattr(binding, "tool_identity", None) != expected_tool:
            raise ProviderRegistryError("model binding differs from manifest for " + lane)


def _validate_permuter_executor(
    manifest: RunManifest,
    lane: str,
    provider: PermuterLaneProvider,
    executor: PermuterExecutor,
    record: Mapping[str, Any],
) -> None:
    if _executor_identity(executor) != record["executor_identity"]:
        raise ProviderRegistryError("permuter executor identity differs for " + lane)
    if executor.binding.identity != provider.binding.identity:
        raise ProviderRegistryError("permuter executor binding differs for " + lane)
    if executor.binding.lane != lane or executor.binding.vendor_revision != provider.binding.vendor_revision:
        raise ProviderRegistryError("permuter executor tool binding differs for " + lane)
    if executor.binding.algorithm_identity != provider.binding.algorithm_identity:
        raise ProviderRegistryError("permuter executor algorithm binding differs for " + lane)
    if executor.platform not in {"posix", "windows-wsl"}:
        raise ProviderRegistryError("permuter executor platform is unsupported")
    if executor.runtime is not None and executor.runtime.evaluator_identity != provider.config.evaluator_identity:
        raise ProviderRegistryError("permuter executor evaluator binding differs for " + lane)
    if executor.binding.tool_identity != provider.tool_identity:
        raise ProviderRegistryError("permuter executor tool identity differs for " + lane)
    if executor.binding.weights_identity != provider.binding.weights_identity:
        raise ProviderRegistryError("permuter executor weights identity differs for " + lane)
    if hash_canonical(manifest.to_dict()) != provider.manifest_identity:
        raise ProviderRegistryError("permuter provider is not bound to this manifest")


def _validate_model_executor(
    manifest: RunManifest,
    lane: str,
    provider: ModelLaneProvider,
    executor: TrustedModelExecutor,
    record: Mapping[str, Any],
) -> None:
    if _executor_identity(executor) != record["executor_identity"]:
        raise ProviderRegistryError("model executor identity differs for " + lane)
    binding = provider.binding
    fields = {
        "lane": lane,
        "manifest_identity": provider.manifest_identity,
        "subset_identity": provider.subset_identity,
        "config_identity": manifest.config_identity,
        "tool_identity": manifest.tool_identities.get(lane),
        "provider_identity": binding.provider_identity,
        "model_identity": binding.model_identity,
        "prompt_identity": binding.prompt_identity,
        "reasoning_identity": binding.reasoning_identity,
    }
    for name, expected in fields.items():
        if getattr(executor, name, None) != expected:
            raise ProviderRegistryError("model executor " + name + " differs for " + lane)


def _provider_adapters(mapping: Mapping[str, Any]) -> LaneAdapters:
    callbacks: dict[str, Any] = {}
    for lane, provider in mapping.items():
        callback = getattr(provider, "callback", None)
        if callback is None or not callable(callback):
            raise ProviderRegistryError("provider callback is unavailable for " + lane)
        callbacks[lane] = callback
    return LaneAdapters.from_mapping(callbacks)


def _indexed_provider(manifest: RunManifest, run_root: Path) -> LaneAdapters:
    """Reload the exact published indexed runtime and build its callbacks."""

    raw_runtime_id = manifest.tool_identities.get(INDEXED_RUNTIME_TOOL_KEY)
    try:
        runtime_id = validate_hash(raw_runtime_id, "indexed runtime identity")
    except Exception as exc:
        raise ProviderRegistryError(
            "selected indexed lanes have no valid runtime identity"
        ) from exc
    repo = _repo_for_run(run_root)
    try:
        runtime = load_indexed_runtime(runtime_id, repo=repo)
        verify_indexed_runtime(runtime, repo=repo)
        return production_indexed_adapters(
            manifest,
            runtime,
            ContentAddressedArchive(_canonical_run_root(run_root, manifest)),
        )
    except ProviderRegistryError:
        raise
    except Exception as exc:  # typed provider domains differ by module
        raise ProviderRegistryError(
            "manifest-bound indexed provider could not be reconstructed"
        ) from exc


def _generated_provider(manifest: RunManifest, run_root: Path) -> LaneAdapters:
    archive, state = _load_provider_state(manifest, run_root)
    providers: dict[str, Any] = {}
    for lane in GENERATED_PROVIDER_LANES:
        if lane not in manifest.selected_lanes:
            continue
        record = _record_for(state, lane)
        try:
            provider = GeneratedLaneProvider.from_dict(record["provider"], archive=archive)
        except Exception as exc:
            raise ProviderRegistryError("generated provider reconstruction failed for " + lane) from exc
        _validate_provider_binding(manifest, lane, provider, record)
        if record["executor"] is not None:
            raise ProviderRegistryError("generated provider unexpectedly has an executor")
        providers[lane] = provider
    return _provider_adapters(providers)


def _idiom_provider(manifest: RunManifest, run_root: Path) -> LaneAdapters:
    archive, state = _load_provider_state(manifest, run_root)
    record = _record_for(state, IDIOM_LANE)
    try:
        provider = IdiomAtlasProvider.from_dict(record["provider"], archive=archive)
    except Exception as exc:
        raise ProviderRegistryError("idiom atlas provider reconstruction failed") from exc
    _validate_provider_binding(manifest, IDIOM_LANE, provider, record)
    if record["executor"] is not None:
        raise ProviderRegistryError("idiom atlas unexpectedly has an executor")
    return _provider_adapters({IDIOM_LANE: provider})


def _permuter_provider(manifest: RunManifest, run_root: Path) -> LaneAdapters:
    archive, state = _load_provider_state(manifest, run_root)
    repo = _repo_for_run(_canonical_run_root(run_root, manifest))
    providers: dict[str, Any] = {}
    for lane in PERMUTER_PROVIDER_LANES:
        if lane not in manifest.selected_lanes:
            continue
        record = _record_for(state, lane)
        if not isinstance(record["executor"], Mapping):
            raise ProviderRegistryError("permuter executor state is missing for " + lane)
        try:
            executor = PermuterExecutor.from_dict(
                record["executor"], archive=archive, repo_root=repo
            )
            provider = PermuterLaneProvider.from_dict(
                record["provider"], archive=archive, executor_callback=executor
            )
        except Exception as exc:
            raise ProviderRegistryError("permuter provider reconstruction failed for " + lane) from exc
        _validate_provider_binding(manifest, lane, provider, record)
        _validate_permuter_executor(manifest, lane, provider, executor, record)
        providers[lane] = provider
    return _provider_adapters(providers)


def _model_provider(manifest: RunManifest, run_root: Path) -> LaneAdapters:
    archive, state = _load_provider_state(manifest, run_root)
    providers: dict[str, Any] = {}
    for lane in MODEL_PROVIDER_LANES:
        if lane not in manifest.selected_lanes:
            continue
        record = _record_for(state, lane)
        if not isinstance(record["executor"], Mapping):
            raise ProviderRegistryError("model executor state is missing for " + lane)
        try:
            executor = TrustedModelExecutor.from_dict(record["executor"])
            provider = ModelLaneProvider.from_dict(record["provider"], archive=archive)
        except Exception as exc:
            raise ProviderRegistryError("model provider reconstruction failed for " + lane) from exc
        _validate_provider_binding(manifest, lane, provider, record)
        _validate_model_executor(manifest, lane, provider, executor, record)
        providers[lane] = provider
    return _provider_adapters(providers)


# The audit requires literal lane keys, concrete callables, and a real lookup
# from this exact mapping.  Family builders are shared deliberately so one
# state envelope is reconstructed once when several lanes use the same family.
LANE_PROVIDER_REGISTRY: Mapping[str, ProviderBuilder] = {
    "multi_donor": _indexed_provider,
    "cfg_dataflow": _indexed_provider,
    "m2c_ensemble": _generated_provider,
    "idiom_atlas": _idiom_provider,
    "bounded_synthesis": _generated_provider,
    "permuter_random": _permuter_provider,
    "permuter_targeted": _permuter_provider,
    "permuter_recombine": _permuter_provider,
    "permuter_ddmin": _permuter_provider,
    "model_fleet": _model_provider,
    "model_expensive": _model_provider,
}


def reconstruct_lane_adapters(
    manifest: RunManifest,
    run_root: Path | str,
    *,
    caller_adapters: Optional[LaneAdapters | Mapping[str, Any]] = None,
) -> LaneAdapters:
    """Rebuild selected production callbacks without caller injection."""

    if not isinstance(manifest, RunManifest):
        raise ProviderRegistryError("production provider manifest must be typed")
    if caller_adapters is not None:
        try:
            supplied = (
                caller_adapters
                if isinstance(caller_adapters, LaneAdapters)
                else LaneAdapters.from_mapping(caller_adapters)
            )
        except Exception as exc:
            raise ProviderRegistryError("caller adapter override is invalid") from exc
        if any(supplied.for_lane(lane) is not None for lane in LANES):
            raise ProviderRegistryError(
                "factory-created production runs reject caller adapter overrides"
            )
    root = Path(run_root)
    callbacks: dict[str, Any] = {}
    built: dict[ProviderBuilder, LaneAdapters] = {}
    for lane in manifest.selected_lanes:
        builder = LANE_PROVIDER_REGISTRY.get(lane)
        if builder is None:
            continue
        adapters = built.get(builder)
        if adapters is None:
            try:
                adapters = builder(manifest, root)
            except ProviderRegistryError:
                raise
            except Exception as exc:
                raise ProviderRegistryError("provider builder failed for " + lane) from exc
            built[builder] = adapters
        callback = adapters.for_lane(lane)
        if callback is None or not callable(callback):
            raise ProviderRegistryError(
                "production provider did not reconstruct selected lane " + lane
            )
        callbacks[lane] = callback
    return LaneAdapters.from_mapping(callbacks)


def verify_lane_provider(manifest: RunManifest, run_root: Path | str) -> None:
    """Revalidate every registry-backed lane from immutable run evidence.

    This function only reconstructs frozen callback state.  It intentionally
    never invokes a callback and never publishes an archive artifact.
    """

    adapters = reconstruct_lane_adapters(manifest, run_root)
    for lane in manifest.selected_lanes:
        if lane in LANE_PROVIDER_REGISTRY and adapters.for_lane(lane) is None:
            raise ProviderRegistryError("selected production provider is unavailable")


revalidate_lane_provider = verify_lane_provider
reconstruct_production_adapters = reconstruct_lane_adapters


__all__ = [
    "EXTERNAL_LANES",
    "GENERATED_PROVIDER_LANES",
    "INDEXED_LANES",
    "INDEXED_RUNTIME_TOOL_KEY",
    "LANE_PROVIDER_REGISTRY",
    "MODEL_PROVIDER_LANES",
    "PERMUTER_PROVIDER_LANES",
    "PROVIDER_REGISTRY_PROTOCOL",
    "PROVIDER_STATE_CATEGORY",
    "PROVIDER_STATE_PROTOCOL",
    "PROVIDER_STATE_SCHEMA_VERSION",
    "PROVIDER_STATE_SUFFIX",
    "ProviderRegistryError",
    "provider_state_document",
    "serialize_provider_state",
    "reconstruct_lane_adapters",
    "reconstruct_production_adapters",
    "revalidate_lane_provider",
    "verify_lane_provider",
]
