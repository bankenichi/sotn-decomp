"""Isolated PSX candidate evaluation with immutable restart receipts.

Discovery remains read-only. The supervisor calls this evaluator only for a
scheduled candidate child, before committing its ordinary evaluation event.
A zero score retains the coordinator's existing durable full-oracle handoff.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Mapping

from .compiler_corpus import DEFAULT_CONFIG_PATH, compile_against_object
from .search_archive import ContentAddressedArchive
from .search_coordinator import SearchCoordinator, TaskResult
from .search_types import (
    ArtifactRef, EvaluationEvent, RunManifest, ScoreDeltas, ScoreVector,
    canonical_bytes, hash_bytes, hash_canonical, iter_artifact_refs,
)

PROTOCOL = "sotn-search-isolated-evaluation-v1"
TOOL_KEY = "search_evaluator"


class EvaluationError(RuntimeError):
    """The measurement instrument or its archived evidence is invalid."""


def evaluation_receipts(archive: ContentAddressedArchive):
    raw_directory = archive.artifacts_root / "evaluations"
    if raw_directory.is_symlink():
        raise EvaluationError("evaluation archive must not be a symlink")
    directory = archive._checked_path(raw_directory)
    if not directory.exists():
        return
    for path in sorted(directory.iterdir()):
        if path.is_symlink():
            raise EvaluationError("evaluation receipt must not be a symlink")
        path = archive._checked_path(path)
        if not path.is_file() or path.suffix != ".json":
            raise EvaluationError("evaluation archive contains an unexpected entry")
        raw = path.read_bytes()
        reference = ArtifactRef(
            hash_bytes(raw), path.relative_to(archive.run_root).as_posix(),
            "application/json", len(raw),
        )
        archive.verify(reference)
        document = json.loads(raw)
        if canonical_bytes(document) != raw:
            raise EvaluationError("evaluation receipt is not canonical")
        if set(document).difference({"binding", "score", "object", "disassembly", "diagnostic", "reused_from", "preprocessed_source"}) or not {"binding", "score", "object", "disassembly", "diagnostic"}.issubset(document):
            raise EvaluationError("evaluation receipt fields differ")
        for artifact in iter_artifact_refs(document):
            archive.verify(artifact)
        yield reference, document


class IsolatedEvaluator:
    def __init__(
        self, manifest: RunManifest, archive: ContentAddressedArchive,
        targets: Mapping[str, ArtifactRef], *, symbols: Mapping[str, str],
        config_path: Path = DEFAULT_CONFIG_PATH,
    ) -> None:
        if set(targets) != set(manifest.queue_record_ids) or set(symbols) != set(targets):
            raise EvaluationError("evaluator targets differ from the manifest subset")
        if TOOL_KEY not in manifest.tool_identities:
            raise EvaluationError("manifest has no evaluator tool binding")
        self.manifest = manifest
        self.archive = archive
        self.targets = dict(targets)
        self.symbols = dict(symbols)
        self.config_path = config_path
        from .weight_tuner import weights_for_run
        self.weights = weights_for_run(manifest, archive)

    @classmethod
    def from_factory(cls, manifest: RunManifest, archive: ContentAddressedArchive):
        # Factory validation also verifies current compiler/source/tool inputs.
        # Reconstruction resolves only explicit archived references.
        from .search_run_factory import verify_factory_runtime
        verify_factory_runtime(archive.run_root, manifest)
        return cls._from_verified_factory(manifest, archive)

    @classmethod
    def _from_verified_factory(cls, manifest: RunManifest, archive: ContentAddressedArchive):
        # The supervisor calls this only after its full runtime check under the
        # run lease. Avoid hashing the entire unchanged checkout a second time.
        from .search_run_factory import _load_index, _safe_repo_file
        root = archive.run_root
        index, _ = _load_index(root)
        tools = json.loads(archive.verify(ArtifactRef.from_dict(index["tools"])))
        repo = root.parents[3]
        config = _safe_repo_file(repo, str(repo / tools["config"]["path"]), "evaluator config")
        targets = {}
        for recipient, reference in index["target_evidence"].items():
            evidence = json.loads(archive.verify(ArtifactRef.from_dict(reference)))
            if hash_canonical(evidence) != manifest.target_identities[recipient]:
                raise EvaluationError("target evidence differs from manifest")
            targets[recipient] = ArtifactRef.from_dict(evidence["object"]["artifact"])
        return cls(
            manifest, archive, targets,
            symbols={recipient: recipient.split(":", 2)[2] for recipient in targets},
            config_path=config,
        )

    def _binding(self, result: TaskResult) -> dict:
        candidate = result.candidate
        if candidate is None:
            raise EvaluationError("evaluation requires a candidate")
        if candidate.recipient_id not in self.targets:
            raise EvaluationError("candidate is outside evaluator subset")
        return {
            "protocol": PROTOCOL,
            "manifest_identity": hash_canonical(self.manifest.to_dict()),
            "task_id": result.task_id,
            "recipient_id": candidate.recipient_id,
            "candidate_id": candidate.candidate_id,
            "source": candidate.source_artifact.to_dict(),
            "target_identity": self.manifest.target_identities[candidate.recipient_id],
            "target": self.targets[candidate.recipient_id].to_dict(),
            "symbol": self.symbols[candidate.recipient_id],
            "compiler_identity": self.manifest.compiler_identity,
            "evaluator_identity": self.manifest.tool_identities[TOOL_KEY],
            **({"scorer_weights": self.manifest.tool_identities["scorer_weights"]}
               if "scorer_weights" in self.manifest.tool_identities else {}),
        }

    def measure(self, result: TaskResult):
        binding = self._binding(result)
        candidate = result.candidate
        assert candidate is not None
        source = self.archive.verify(candidate.source_artifact)
        if result.source is not None and result.source.encode("utf-8") != source:
            raise EvaluationError("candidate source differs from its archive")
        target = self.archive.verify(self.targets[candidate.recipient_id])
        prior = []
        reusable = []
        for reference, document in evaluation_receipts(self.archive):
            if document["binding"].get("task_id") == result.task_id:
                if document["binding"] != binding:
                    raise EvaluationError("evaluation receipt input binding differs")
                prior.append((reference, document))
            elif {key: value for key, value in document["binding"].items() if key != "task_id"} == {key: value for key, value in binding.items() if key != "task_id"}:
                reusable.append((reference, document))
        if len(prior) > 1:
            raise EvaluationError("task has ambiguous evaluation receipts")
        if prior:
            reference, document = prior[0]
        elif reusable:
            previous, document = reusable[0]
            document = {**document, "binding": binding, "reused_from": previous.to_dict()}
            reference = self.archive.put_json(document, category="evaluations")
        else:
            observation = compile_against_object(
                source.decode("utf-8"), target,
                expected_pipeline_identity=self.manifest.compiler_identity,
                symbol=binding["symbol"], config_path=self.config_path,
                recipient_id=candidate.recipient_id if candidate.recipient_id.count(":") == 2 else None,
                weights=self.weights,
            )
            obj = self.archive.put_object(observation.object_bytes) if observation.object_bytes is not None else None
            disassembly = self.archive.put_text(
                observation.disassembly, category="disassembly", suffix=".txt",
            ) if observation.disassembly is not None else None
            diagnostic = self.archive.put_text(
                observation.diagnostic, category="diagnostics", suffix=".txt",
            ) if observation.diagnostic is not None else None
            score = dict(observation.score)
            score["diagnostic_artifact"] = diagnostic.to_dict() if diagnostic else None
            document = {
                "binding": binding, "score": score,
                "object": obj.to_dict() if obj else None,
                "disassembly": disassembly.to_dict() if disassembly else None,
                "diagnostic": diagnostic.to_dict() if diagnostic else None,
            }
            if observation.preprocessed_source is not None:
                document["preprocessed_source"] = self.archive.put_source(observation.preprocessed_source).to_dict()
            reference = self.archive.put_json(document, category="evaluations")
        score = ScoreVector.from_dict(document["score"])
        if score.compiler_identity != self.manifest.compiler_identity:
            raise EvaluationError("evaluation receipt compiler identity differs")
        if (score.compile_status == "success") != (document["object"] is not None):
            raise EvaluationError("evaluation receipt object contradicts compile status")
        return score, reference

    def evaluate(self, coordinator: SearchCoordinator, result: TaskResult) -> TaskResult:
        if coordinator.manifest != self.manifest:
            raise EvaluationError("coordinator differs from evaluator manifest")
        after, receipt = self.measure(result)
        candidate = result.candidate
        assert candidate is not None
        # The archive owns elite/Pareto admission. A measurement without a
        # measured parent has no fabricated improvement delta.
        event = EvaluationEvent(
            result.task_id, candidate.recipient_id, candidate.candidate_id,
            None, None, after, ScoreDeltas(None, 0, 0, 0, 0, 0),
            coordinator.frontier.cache.key_for(
                candidate.recipient_id, candidate.candidate_id, after.compiler_identity,
            ),
            "compile_failed" if after.compile_status != "success" else (
                "zero_pending_oracle" if after.total == 0 else "measured"
            ),
        )
        return replace(
            result, candidate=replace(candidate, evaluation=after, status="evaluated"),
            evaluation=event, result_artifacts=(*result.result_artifacts, receipt),
            reason="candidate evaluated against archived target",
        )


def validate_evaluation_receipts(manifest: RunManifest, archive: ContentAddressedArchive) -> None:
    """Verify transitive measurement artifacts without executing the compiler."""
    if TOOL_KEY not in manifest.tool_identities:
        return
    from .weight_tuner import weights_for_run
    weights = weights_for_run(manifest, archive)
    for _, document in evaluation_receipts(archive):
        binding = document["binding"]
        if (
            binding.get("protocol") != PROTOCOL
            or binding.get("manifest_identity") != hash_canonical(manifest.to_dict())
            or binding.get("evaluator_identity") != manifest.tool_identities[TOOL_KEY]
            or binding.get("compiler_identity") != manifest.compiler_identity
            or binding.get("recipient_id") not in manifest.queue_record_ids
            or binding.get("target_identity") != manifest.target_identities.get(binding.get("recipient_id"))
        ):
            raise EvaluationError("archived evaluation is not manifest-bound")
        score = ScoreVector.from_dict(document["score"])
        if score.weights.to_dict() != weights or binding.get("scorer_weights") != manifest.tool_identities.get("scorer_weights"):
            raise EvaluationError("archived score weights differ from manifest")
        if score.compiler_identity != manifest.compiler_identity:
            raise EvaluationError("archived score compiler differs")
        source = ArtifactRef.from_dict(binding["source"])
        if source.content_hash != binding.get("candidate_id"):
            raise EvaluationError("archived evaluation source identity differs")
        if (score.compile_status == "success") != (document["object"] is not None):
            raise EvaluationError("archived evaluation object contradicts compile status")
        if document["diagnostic"] != (
            score.diagnostic_artifact.to_dict() if score.diagnostic_artifact else None
        ):
            raise EvaluationError("archived score diagnostic differs")



def measured_lane_report(manifest, lane_task, outcome, events):
    """Project measured selection without treating a deterministic sample as best."""
    scheduled = {
        event.payload.task_id: event.payload
        for event in events if event.event_type == "task_scheduled"
    }
    candidates = {item.candidate_id for item in outcome.candidates}
    measured = {}
    for event in events:
        if event.event_type != "evaluation_completed":
            continue
        evaluation = event.payload
        task = scheduled.get(evaluation.task_id)
        if (
            task is not None and task.lane == lane_task.lane
            and task.recipient_id == lane_task.recipient_id
            and task.operation == "materialize_candidate:" + evaluation.candidate_id
            and evaluation.candidate_id in candidates
        ):
            measured[evaluation.candidate_id] = evaluation
    ranked = sorted(
        (key for key, value in measured.items()
         if value.after.compile_status == "success" and value.after.total is not None),
        key=lambda key: (measured[key].after.total, key),
    )
    best = [key for key in ranked if measured[key].after.total == measured[ranked[0]].after.total]
    unexamined = sorted(candidates.difference(measured))
    return {
        "protocol": "sotn-search-measured-lane-v1",
        "manifest_identity": hash_canonical(manifest.to_dict()),
        "task_id": lane_task.task_id, "recipient_id": lane_task.recipient_id, "lane": lane_task.lane,
        "selection_policy": "canonical_sample_then_measured_minimum",
        "discovery_complete": (outcome.receipt.completion_reason in {
            "search_space_exhausted", "inapplicable", "matched_pending_oracle",
        }) if hasattr(outcome, "receipt") else False,
        "evaluation_complete": not unexamined,
        "generated_unique": len(candidates), "evaluated": len(measured),
        "compile_failed": sum(value.after.compile_status != "success" for value in measured.values()),
        "zero_pending_oracle": sum(value.after.total == 0 for value in measured.values()),
        "best_measured_candidate_ids": best,
        "candidates": [{
            "candidate_id": key,
            "disposition": ("evaluated" if key in measured else "unexamined_candidate_budget"),
            "evaluation": measured[key].to_dict() if key in measured else None,
        } for key in sorted(candidates)],
    }


def measured_lane_proposal(coordinator, lane_task, outcome):
    report = measured_lane_report(coordinator.manifest, lane_task, outcome, coordinator.events)
    reference = coordinator.archive.put_json(report, category="lane-measurements")
    unexamined = report["generated_unique"] - report["evaluated"]
    counts = dict(outcome.receipt.rejection_counts)
    if unexamined:
        counts["unexamined_candidate_budget"] = unexamined
    return replace(
        outcome.receipt,
        input_identities=(*outcome.receipt.input_identities, reference.content_hash),
        best_candidate_ids=tuple(report["best_measured_candidate_ids"]),
        rejection_counts=counts,
        completion_reason="budget_exhausted" if unexamined else outcome.receipt.completion_reason,
        reason="lane outcome, measured candidates and unexamined dispositions archived",
    )


def permuter_measurements(manifest, archive):
    """Read verified worker prefixes, including work before a failed response.

    Requests bind session ownership. Stray files never acquire a recipient or
    lane merely because their event happens to name a known strategy.
    """
    from .search_permuter_lanes import PermuterRequest
    from .search_permuter_worker import load_events
    directory = archive.artifacts_root / "permuter-requests"
    if directory.is_symlink():
        raise EvaluationError("permuter requests must not be symlinked")
    sessions = {}
    if not directory.exists():
        return {}
    for path in sorted(directory.iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix != ".json":
            raise EvaluationError("unexpected permuter request entry")
        raw = path.read_bytes()
        reference = ArtifactRef(hash_bytes(raw), path.relative_to(archive.run_root).as_posix(),
                                "application/json", len(raw))
        archive.verify(reference)
        request = PermuterRequest.from_dict(json.loads(raw))
        if raw != canonical_bytes(request.to_dict()) or (
            request.manifest_identity != hash_canonical(manifest.to_dict())
            or request.recipient_id not in manifest.queue_record_ids
            or request.lane not in manifest.selected_lanes
            or request.target_identity != manifest.target_identities[request.recipient_id]
            or request.evaluator_identity != manifest.compiler_identity
        ):
            raise EvaluationError("permuter request is not manifest-bound")
        sessions[request.session_identity] = request
    measured = {}
    for session, request in sessions.items():
        observations = measured.setdefault((request.recipient_id, request.lane), {})
        for reference, event in load_events(archive, session):
            if (event["target_identity"] != request.target_identity
                    or event["evaluator_identity"] != request.evaluator_identity
                    or event["strategy"] != request.algorithm):
                raise EvaluationError("permuter measurement differs from request")
            score = ScoreVector.from_dict(event["score"])
            if score.compiler_identity != manifest.compiler_identity or (
                (score.compile_status == "success") != (event["object"] is not None)
            ):
                raise EvaluationError("permuter measurement compiler/object differs")
            observations[event["source"]["content_hash"]] = (score, reference)
    return measured


def search_funnel(manifest, events, archive):
    """Project actual lane outputs and measurements from one verified prefix.

    Scheduling, output production and measurement are separate counters. Missing
    outcomes remain unknown. A checksum match comes only from an oracle result.
    This reader also works at an interrupted candidate or oracle handoff.
    """
    from types import SimpleNamespace
    from .search_supervisor import _load_task_outcome

    view = SimpleNamespace(events=events, archive=archive)
    worker_measurements = permuter_measurements(manifest, archive)
    tasks = {event.payload.task_id: event.payload for event in events
             if event.event_type == "task_scheduled"}
    started = {event.payload.task_id for event in events if event.event_type == "task_started"}
    terminals = {event.payload.task_id for event in events
                 if event.event_type in {"task_completed", "task_failed", "task_cancelled"}}
    evaluations = [event.payload for event in events if event.event_type == "evaluation_completed"]
    requests = {event.payload.request_id: event.payload for event in events
                if event.event_type == "oracle_requested"}
    oracle_results = {event.payload.request_id: event.payload for event in events
                      if event.event_type == "oracle_result_recorded"}
    reused_tasks = {document["binding"]["task_id"] for _, document in evaluation_receipts(archive)
                    if "reused_from" in document}
    receipts = {(event.payload.recipient_id, event.payload.lane): event.payload for event in events
                if event.event_type == "exhaustion_recorded"}
    rows, all_generated, all_evaluated = [], set(), set()
    for recipient in manifest.queue_record_ids:
        for lane in manifest.selected_lanes:
            base = [task for task in tasks.values() if task.recipient_id == recipient
                    and task.lane == lane and task.operation == "execute_lane"]
            if len(base) > 1:
                raise EvaluationError("ambiguous base lane tasks in funnel")
            loaded = _load_task_outcome(view, base[0]) if base else None
            outcome = loaded[0] if loaded else None
            generated = {item.candidate_id for item in outcome.candidates} if outcome else set()
            measured = {item.candidate_id: item for item in evaluations
                        if item.recipient_id == recipient and item.task_id in tasks
                        and tasks[item.task_id].lane == lane}
            applicable = None if outcome is None else not outcome.inapplicable
            worker = worker_measurements.get((recipient, lane), {})
            scores = {key: item[0] for key, item in worker.items()}
            scores.update({key: item.after for key, item in measured.items()})
            generated.update(worker)
            if worker:
                applicable = True
            receipt = receipts.get((recipient, lane))
            matching_requests = {key: value for key, value in requests.items()
                                 if value.task_id in tasks and tasks[value.task_id].lane == lane
                                 and tasks[value.task_id].recipient_id == recipient}
            verified = {request.candidate_id for key, request in matching_requests.items()
                        if key in oracle_results and oracle_results[key].outcome == "matched"}
            rejected = {request.candidate_id for key, request in matching_requests.items()
                        if key in oracle_results and oracle_results[key].outcome == "not_matched"}
            zero = {key for key, score in scores.items()
                    if score.compile_status == "success" and score.total == 0}
            row = {
                "recipient_id": recipient, "lane": lane,
                "scheduled": bool(base), "started": bool(base and base[0].task_id in started),
                "task_terminal": bool(base and base[0].task_id in terminals),
                "applicable": applicable,
                "completion_reason": receipt.completion_reason if receipt else None,
                "attempts": outcome.receipt.attempts if outcome else None,
                "execution_failed": bool(outcome and outcome.receipt.completion_reason == "execution_failed"),
                "refusal_code": outcome.refusal.code if outcome and outcome.refusal else None,
                "provider_evaluated_unique": len(worker),
                "coordinator_evaluated_unique": len(measured),
                "generated_unique": len(generated), "evaluated_unique": len(scores),
                "unexamined": len(generated.difference(scores)),
                "compile_failed": sum(score.compile_status != "success" for score in scores.values()),
                "score_reused": sum(item.task_id in reused_tasks for item in measured.values()),
                "improved": sum(item.before is not None and item.before.total is not None
                                and item.after.total is not None and item.after.total < item.before.total
                                for item in measured.values()),
                "idiom_candidates_generated": len(generated) if lane == "idiom_atlas" else 0,
                "oracle_requests": len(matching_requests), "oracle_verified_matches": len(verified),
                "oracle_rejected": len(rejected),
                "zero_pending_oracle": len(zero.difference(verified | rejected)),
                "rejections": dict(outcome.receipt.rejection_counts) if outcome else {},
            }
            rows.append(row)
            all_generated.update((recipient, key) for key in generated)
            all_evaluated.update((recipient, key) for key in scores)
    return {
        "protocol": "sotn-search-funnel-v1", "run_id": manifest.run_id,
        "manifest_identity": hash_canonical(manifest.to_dict()),
        "ledger_prefix": {"events": len(events), "last_event_hash": events[-1].event_hash if events else None},
        "denominators": {"recipients": len(manifest.queue_record_ids), "lanes": len(manifest.selected_lanes),
                         "recipient_lane_pairs": len(rows)},
        "totals": {
            "scheduled_pairs": sum(row["scheduled"] for row in rows),
            "started_pairs": sum(row["started"] for row in rows),
            "terminal_pairs": sum(row["task_terminal"] for row in rows),
            "applicable_pairs": sum(row["applicable"] is True for row in rows),
            "inapplicable_pairs": sum(row["applicable"] is False for row in rows),
            "unknown_applicability_pairs": sum(row["applicable"] is None for row in rows),
            "generated_unique_across_lanes": len(all_generated),
            "evaluated_unique_across_lanes": len(all_evaluated),
            "duplicate_candidates_across_lanes": sum(row["generated_unique"] for row in rows) - len(all_generated),
            **{key: sum(row[key] for row in rows) for key in (
                "unexamined", "compile_failed", "score_reused", "improved", "idiom_candidates_generated",
                "execution_failed", "provider_evaluated_unique", "coordinator_evaluated_unique",
                "oracle_requests", "oracle_verified_matches", "oracle_rejected", "zero_pending_oracle")},
        },
        "rows": rows,
    }
