"""Task-bound, measured candidate inputs for immutable permuter providers."""
from __future__ import annotations

import copy
import json
from dataclasses import replace

from .search_types import ArtifactRef, canonical_bytes, hash_canonical

TOOL_KEY = "search_seed_handoff"
CATEGORY = "seed-handoffs"
PROTOCOL = "sotn-evaluated-seed-handoff-v1"


class SeedHandoffError(RuntimeError):
    """A seed decision or its measured parent cannot be reconstructed."""


def _documents(archive):
    directory = archive.artifacts_root / CATEGORY
    if directory.is_symlink():
        raise SeedHandoffError("seed handoff directory is a symlink")
    if not directory.exists():
        return
    for path in sorted(directory.iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix != ".json":
            raise SeedHandoffError("unexpected seed handoff archive entry")
        raw = path.read_bytes()
        ref = ArtifactRef("sha256:" + path.stem, path.relative_to(archive.run_root).as_posix(),
                          "application/json", len(raw))
        archive.verify(ref)
        document = json.loads(raw)
        if canonical_bytes(document) != raw:
            raise SeedHandoffError("seed handoff is not canonical")
        yield ref, document


def _decision(manifest, archive, events, task, base, provider_identity):
    from .search_coordinator import validate_task_binding
    from .search_evaluator import evaluation_receipts, validate_evaluation_receipts
    validate_task_binding(manifest, task)
    if (task.operation != "execute_lane" or not task.lane.startswith("permuter_")
            or base.recipient_id != task.recipient_id
            or base.target_identity != manifest.target_identities[task.recipient_id]):
        raise SeedHandoffError("seed handoff task differs from frozen input")
    base.verify(archive)
    prefix = []
    scheduled = None
    for event in events:
        if event.event_type == "task_scheduled" and event.payload.task_id == task.task_id:
            scheduled = event
            break
        prefix.append(event)
    if scheduled is None or replace(scheduled.payload, state="scheduled") != replace(task, state="scheduled"):
        raise SeedHandoffError("seed handoff has no exact scheduled task")
    # Only measurements committed before this scheduled event are eligible.
    # Later receipts, including an interrupted child's orphan receipt, cannot
    # change the input of an already scheduled worker task.
    validate_evaluation_receipts(manifest, archive)
    receipts = list(evaluation_receipts(archive))
    candidates = {e.payload.candidate_id: e.payload for e in prefix
                  if e.event_type == "candidate_materialized"}
    choices = []
    for event in prefix:
        if event.event_type != "evaluation_completed":
            continue
        evaluation = event.payload
        if (evaluation.recipient_id != task.recipient_id
                or evaluation.candidate_id not in task.parent_candidate_ids
                or evaluation.after.compile_status != "success"
                or evaluation.after.total is None or evaluation.after.total <= 0):
            continue
        candidate = candidates.get(evaluation.candidate_id)
        if candidate is None or candidate.recipient_id != task.recipient_id:
            raise SeedHandoffError("measured seed has no recipient-bound candidate")
        matching = [(ref, doc) for ref, doc in receipts
                    if doc["binding"].get("task_id") == evaluation.task_id]
        if len(matching) != 1:
            raise SeedHandoffError("measured seed receipt is missing or ambiguous")
        ref, doc = matching[0]
        binding = doc["binding"]
        if (binding.get("candidate_id") != candidate.candidate_id
                or binding.get("source") != candidate.source_artifact.to_dict()
                or binding.get("recipient_id") != task.recipient_id
                or doc["score"] != evaluation.after.to_dict()):
            raise SeedHandoffError("measured seed receipt differs from ledger evaluation")
        choices.append((evaluation.after.total, candidate.candidate_id, evaluation.task_id,
                        candidate, ref, event))
    selected = None
    item = base
    if choices:
        _, _, _, candidate, receipt, evaluation_event = min(choices, key=lambda row: row[:3])
        source = archive.verify(candidate.source_artifact).decode("utf-8")
        selected = {"candidate_id": candidate.candidate_id,
                    "measurement": receipt.to_dict(),
                    "evaluation_event_hash": evaluation_event.event_hash}
        item = replace(base, seed_source=source, seed_artifact=candidate.source_artifact)
    binding = {"protocol": PROTOCOL, "manifest_identity": hash_canonical(manifest.to_dict()),
               "provider_identity": provider_identity, "task_id": task.task_id,
               "lane": task.lane, "recipient_id": task.recipient_id,
               "scheduled_event_hash": scheduled.event_hash,
               "frozen_input_identity": base.input_identity, "selected": selected}
    # The request already binds input_identity, so this metadata ties both the
    # selected and fallback worker sessions to their immutable task decision.
    item = replace(item, metadata={**dict(base.metadata), "seed_handoff": binding})
    return {**binding, "input": item.to_dict()}, item


def bind_task_provider(provider, task, events):
    """Return a task-local provider view; never replace its factory input map."""
    from .search_permuter_lanes import PermuterLaneProvider
    if type(provider) is not PermuterLaneProvider or provider.config.lane != task.lane:
        raise SeedHandoffError("seed handoff requires the concrete task provider")
    if TOOL_KEY not in provider.manifest.tool_identities:
        return provider
    base = provider.inputs.get(task.recipient_id)
    if base is None:
        raise SeedHandoffError("seed handoff recipient is outside the frozen provider subset")
    document, item = _decision(provider.manifest, provider.archive, events, task, base,
                               provider.provider_identity)
    existing = [(ref, doc) for ref, doc in _documents(provider.archive)
                if doc.get("task_id") == task.task_id]
    if existing and (len(existing) != 1 or existing[0][1] != document):
        raise SeedHandoffError("seed handoff decision changed for scheduled task")
    if existing:
        reference = existing[0][0]
    else:
        reference = provider.archive.put_json(document, category=CATEGORY)
    bound = copy.copy(provider)
    bound._task_input = item
    bound._seed_handoff = reference
    bound._seed_known_candidates = frozenset(task.parent_candidate_ids)
    return bound


def validate_seed_handoffs(manifest, archive, events):
    """Rederive decisions and verify actual request consumption without tools."""
    documents = list(_documents(archive))
    if TOOL_KEY not in manifest.tool_identities:
        if documents:
            raise SeedHandoffError("historical run has unbound seed handoffs")
        return
    from .search_provider_lanes import _load_provider_state
    from .search_permuter_lanes import ArchivedPermuterInput
    tasks = {e.payload.task_id: e.payload for e in events if e.event_type == "task_scheduled"}
    started = {e.payload.task_id for e in events if e.event_type == "task_started"
               and e.payload.lane.startswith("permuter_") and e.payload.operation == "execute_lane"}
    if not documents and not started:
        return
    _, state = _load_provider_state(manifest, archive.run_root)
    providers = {r["lane"]: r for r in state["providers"]}
    inputs, seen = {}, set()
    for _, doc in documents:
        task = tasks.get(doc.get("task_id"))
        if task is None or task.task_id in seen or task.lane not in providers:
            raise SeedHandoffError("seed handoff task is missing or ambiguous")
        record = providers[task.lane]
        bases = [ArchivedPermuterInput.from_dict(i) for i in record["provider"]["inputs"]
                 if i["recipient_id"] == task.recipient_id]
        if len(bases) != 1:
            raise SeedHandoffError("seed handoff has no exact factory input")
        expected, item = _decision(manifest, archive, events, task, bases[0], record["provider_identity"])
        if doc != expected:
            raise SeedHandoffError("archived seed handoff differs from its ledger prefix")
        seen.add(task.task_id)
        inputs[(record["provider_identity"], task.recipient_id, item.input_identity)] = item
    if not started <= seen:
        raise SeedHandoffError("started permuter task has no archived seed handoff")
    # Requests are independently archived before worker execution. Verify that
    # they consumed the decision, rather than merely listing it as ancestry.
    from .search_permuter_lanes import PermuterHandoffStore, PermuterRequest
    store = PermuterHandoffStore(archive)
    for request, _ in store._iter_documents("permuter-requests"):
        PermuterRequest.from_dict(request)
        key = (request["provider_identity"], request["recipient_id"], request["input_identity"])
        item = inputs.get(key)
        if (item is None or request["seed_identity"] != item.seed_identity
                or request["seed_source"] != item.seed_source
                or request["seed_artifact"] != item.seed_artifact.to_dict()
                or request["target_artifact"] != item.target_artifact.to_dict()
                or request["target_assembly"] != item.target_assembly):
            raise SeedHandoffError("permuter request did not consume its task seed")
