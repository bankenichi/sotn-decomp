"""Concrete immutable provider construction owned by the search run factory."""
from __future__ import annotations

import re
import json
from pathlib import Path

from .search_generated_lanes import ArchivedTargetInput, build_bounded_synthesis_provider
from .search_permuter_executor import (
    PermuterExecutor, PermuterRuntimeBinding, REPOSITORY_COMPILE_WRAPPER_BYTES,
    vendored_tree_identity,
)
from .search_permuter_lanes import ArchivedPermuterInput, PermuterLaneConfig, PermuterToolBinding, build_permuter_provider
from .search_provider_lanes import EXTERNAL_LANES, PROVIDER_STATE_CATEGORY, provider_state_document
from .search_target_renderer import deterministic_local_draft
from .search_types import hash_bytes
from .search_types import hash_canonical
from .search_model_executor import TrustedModelExecutor
from .search_model_lanes import ArchivedModelTargetInput, ModelBinding
from .search_model_provider import DeferredModelLaneProvider
from .search_idiom_atlas import IdiomAtlasTargetInput, build_idiom_atlas_provider
from .search_patterns import CompletedLineageContext
from .search_archive import ContentAddressedArchive
from .search_indexed_runtime import INDEXED_RUNTIME_ROOT
from .search_source_context import candidate_belongs_to_recipient

PERMUTER_STRATEGIES = {
    "permuter_random": "random", "permuter_targeted": "targeted",
    "permuter_recombine": "recombine", "permuter_ddmin": "ddmin",
}
MODEL_LANES = frozenset({"model_fleet", "model_expensive"})
IMPLEMENTED_LANES = frozenset({"bounded_synthesis", "idiom_atlas", *PERMUTER_STRATEGIES, *MODEL_LANES})
MODEL_PROMPT = "Recover the target {symbol} for {platform}. Return JSON containing candidates with source fields. Use only the archived target context.\n{context}"


def model_input_state(repo, lane):
    path = repo / "automation/search-provider-settings.json"
    if path.is_symlink():
        raise ValueError("model settings must not be a symlink")
    settings = json.loads(path.read_text())
    if set(settings) != {"protocol", "models"} or settings["protocol"] != "sotn-search-provider-settings-v1":
        raise ValueError("model settings schema differs")
    profile = settings["models"].get(lane)
    if not isinstance(profile, dict):
        raise ValueError("select an explicit model profile in automation/search-provider-settings.json for " + lane)
    required = {"endpoint", "model_name", "provider", "reasoning", "paid", "timeout_seconds", "max_tokens", "api_key_env"}
    if set(profile) != required:
        raise ValueError("model profile has missing or unknown fields")
    return {"kind": "explicit_model_profile", "profile": profile, "settings_identity": hash_bytes(path.read_bytes())}


def prepare_provider_inputs(repo, lanes, targets, lane_inputs, *, indexed_runtime=None, target_declarations=None):
    """Resolve missing-input refusals before the factory writes any artifacts."""
    external = set(lanes).intersection(EXTERNAL_LANES)
    unsupported = external.difference(IMPLEMENTED_LANES)
    if unsupported:
        raise ValueError("provider factory still requires qualified runtime inputs for: " + ", ".join(sorted(unsupported)))
    seed_lanes = external.intersection({"idiom_atlas", *PERMUTER_STRATEGIES})
    if "idiom_atlas" in external:
        if indexed_runtime is None or not indexed_runtime.corpus.entries:
            raise ValueError("idiom atlas requires an explicit nonempty evidence corpus")
        if not any(isinstance(item, CompletedLineageContext) for item in indexed_runtime.lineage_contexts):
            raise ValueError("idiom atlas requires a completed measured lineage in the selected runtime")
    prepared = {}
    for recipient, (assembly, _) in targets.items():
        symbol = recipient.split(":", 2)[2]
        declarations = {key: value for key, value in (target_declarations or {}).get(recipient, {}).items()
                        if key != "context_evidence"}
        draft = deterministic_local_draft(assembly, symbol=symbol, declarations=declarations)
        seed, seed_origin = draft, "deterministic_target_renderer"
        for lane in sorted(seed_lanes):
            if seed is not None:
                break
            for entry in lane_inputs[lane]["candidate_inputs"].get("files", ()):
                path = repo / entry["path"]
                if path.suffix != ".c":
                    continue
                raw = path.read_bytes()
                if hash_bytes(raw) != entry["content_hash"]:
                    raise ValueError("programmatic seed changed during factory capture")
                source = raw.decode("utf-8")
                if not candidate_belongs_to_recipient(source, path, recipient):
                    continue
                if re.search(r"\b" + re.escape(symbol) + r"\s*\([^;{}]*\)\s*\{", source):
                    seed, seed_origin = source, entry["path"]
                    break
        if seed_lanes and seed is None:
            raise ValueError("programmatic rewriting requires a preserved seed or supported target draft for " + recipient)
        # A branch-local return is not the whole function. Only a complete
        # single-return draft may supply the synthesis expression provider.
        expression = re.fullmatch(r"[^{}]+\{\s*return\s+([^;{}]+);\s*\}\s*", draft) if draft else None
        prepared[recipient] = {
            "seed": seed, "seed_origin": seed_origin, "declarations": declarations,
            "expressions": (expression.group(1),) if expression else (),
        }
    return prepared


def publish_provider_state(manifest, archive, repo, targets, target_refs, prepared, lane_inputs, *, indexed_runtime=None):
    """Publish concrete providers; construction performs no external dispatch."""
    external = set(manifest.selected_lanes).intersection(EXTERNAL_LANES)
    if not external:
        return None
    providers = {}
    if "idiom_atlas" in external:
        corpus_archive = ContentAddressedArchive(
            repo / INDEXED_RUNTIME_ROOT / indexed_runtime.runtime_id.removeprefix("sha256:")
        )
        for entry in indexed_runtime.corpus.entries:
            if entry.kind == "draft_landed" and entry.outcome == "accepted" and entry.idiom is not None:
                for reference in (entry.idiom.before, entry.idiom.after):
                    copied = archive.put_source(corpus_archive.verify(reference).decode("utf-8"))
                    if copied != reference:
                        raise ValueError("idiom evidence source is not canonical")
        inputs = [IdiomAtlasTargetInput(
            recipient_id=recipient, target_identity=manifest.target_identities[recipient],
            draft_artifact=archive.put_source(prepared[recipient]["seed"]),
            draft_bytes=prepared[recipient]["seed"].encode("utf-8"),
            platform=recipient.split(":", 1)[0],
        ) for recipient in manifest.queue_record_ids]
        providers["idiom_atlas"] = build_idiom_atlas_provider(
            manifest, inputs, indexed_runtime.corpus.entries,
            tuple(item for item in indexed_runtime.lineage_contexts if isinstance(item, CompletedLineageContext)),
            archive=archive,
        )
    if "bounded_synthesis" in external:
        inputs = [ArchivedTargetInput(
            recipient, manifest.target_identities[recipient], target_refs[recipient][0],
            targets[recipient][0], recipient.split(":", 2)[2],
            expressions=prepared[recipient]["expressions"],
            declarations=prepared[recipient]["declarations"],
        ) for recipient in manifest.queue_record_ids]
        providers["bounded_synthesis"] = build_bounded_synthesis_provider(manifest, inputs, archive=archive)
    for lane in sorted(external.intersection(MODEL_LANES)):
        profile = lane_inputs[lane]["profile"]
        executor = TrustedModelExecutor(
            **profile, lane=lane, selected=True,
            prompt_identity=hash_bytes(MODEL_PROMPT.encode()),
            manifest_identity=hash_canonical(manifest.to_dict()), subset_identity=manifest.subset_identity,
            config_identity=manifest.config_identity, tool_identity=manifest.tool_identities[lane],
        )
        binding = ModelBinding(
            provider_identity=executor.provider_identity, model_identity=executor.model_identity,
            model_name=executor.model_name, prompt_identity=executor.prompt_identity,
            prompt_template=MODEL_PROMPT, reasoning_identity=executor.reasoning_identity,
            reasoning=executor.reasoning, config_identity=manifest.config_identity,
            tool_identity=manifest.tool_identities[lane], max_candidates=2,
        )
        inputs = tuple(ArchivedModelTargetInput(
            recipient, manifest.target_identities[recipient], target_refs[recipient][0],
            targets[recipient][0], recipient.split(":", 2)[2], recipient.split(":", 1)[0],
        ) for recipient in manifest.queue_record_ids)
        providers[lane] = (DeferredModelLaneProvider(manifest, lane, inputs, binding, archive, executor), executor)
    for lane in sorted(external.intersection(PERMUTER_STRATEGIES)):
        vendor = repo / "tools/decomp-permuter"
        revision = vendored_tree_identity(vendor)
        if revision != lane_inputs[lane]["vendor_revision"]:
            raise ValueError("vendored permuter changed during factory capture")
        runner, weights = (vendor / "permuter.py").read_bytes(), (vendor / "default_weights.toml").read_bytes()
        config = PermuterLaneConfig(
            lane=lane, algorithm=PERMUTER_STRATEGIES[lane], max_iterations=8,
            checkpoint_interval=8, max_candidates=8, evaluator_identity=manifest.compiler_identity,
        )
        binding = PermuterToolBinding(
            lane=lane, vendor_revision=revision, algorithm=config.algorithm,
            algorithm_identity=config.algorithm_identity,
            tool_artifact=archive.put_bytes(runner, category="permuter-vendor", suffix=".py", media_type="text/x-python"),
            tool_bytes=runner,
            weights_artifact=archive.put_bytes(weights, category="permuter-vendor", suffix=".toml", media_type="application/toml"),
            weights_bytes=weights,
        )
        wrapper = archive.put_bytes(REPOSITORY_COMPILE_WRAPPER_BYTES, category="permuter-runtime", suffix=".sh", media_type="text/x-shellscript")
        inputs, runtimes = [], {}
        for recipient in manifest.queue_record_ids:
            seed = prepared[recipient]["seed"]
            assembly, obj = targets[recipient]
            inputs.append(ArchivedPermuterInput(
                recipient_id=recipient, target_identity=manifest.target_identities[recipient],
                seed_artifact=archive.put_source(seed), seed_source=seed,
                target_artifact=target_refs[recipient][0], target_assembly=assembly.decode("utf-8"),
                metadata={"seed_origin": prepared[recipient]["seed_origin"]},
            ))
            runtimes[recipient] = PermuterRuntimeBinding(
                evaluator_identity=manifest.compiler_identity,
                compile_script_artifact=wrapper, compile_script_bytes=REPOSITORY_COMPILE_WRAPPER_BYTES,
                compiler_type="gcc", function_name=recipient.split(":", 2)[2],
                target_object_artifact=target_refs[recipient][1], target_object_bytes=obj,
            )
        executor = PermuterExecutor(archive, binding, runtimes=runtimes, repo_root=repo)
        provider = build_permuter_provider(lane, manifest, inputs, archive=archive, binding=binding,
                                          config=config, executor_callback=executor)
        providers[lane] = (provider, executor)
    return archive.put_json(provider_state_document(manifest, providers), category=PROVIDER_STATE_CATEGORY)
