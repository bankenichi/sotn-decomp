"""Candidate graph, recipient-local evaluation cache and bounded Pareto archive."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .search_types import (
    ArchiveDecision,
    CandidateRecord,
    EvaluationEvent,
    LedgerEvent,
    ScoreVector,
    SCORE_FIELDS,
    hash_canonical,
)


class FrontierError(RuntimeError):
    """Base class for graph and frontier errors."""


class CrossRecipientCacheError(FrontierError):
    """An attempt was made to use an evaluation for another recipient."""


@dataclass(frozen=True)
class ProvenanceEdge:
    candidate_id: str
    recipient_id: str
    parent_candidate_ids: Tuple[str, ...]
    mutation_id: Optional[str]
    lane: str


class CandidateGraph:
    """Index immutable candidates while retaining every provenance edge."""

    def __init__(self) -> None:
        self._candidates: Dict[str, CandidateRecord] = {}
        self._by_source: Dict[str, str] = {}
        self._edges: Dict[str, List[ProvenanceEdge]] = {}

    def add(self, candidate: CandidateRecord) -> CandidateRecord:
        existing = self._candidates.get(candidate.candidate_id)
        if existing is not None:
            old_identity = (
                existing.recipient_id,
                existing.source_artifact.content_hash,
                existing.parent_candidate_ids,
                existing.mutation_id,
                existing.lane,
                existing.depth,
            )
            new_identity = (
                candidate.recipient_id,
                candidate.source_artifact.content_hash,
                candidate.parent_candidate_ids,
                candidate.mutation_id,
                candidate.lane,
                candidate.depth,
            )
            if old_identity != new_identity:
                raise FrontierError("candidate id maps to conflicting metadata")
            # Evaluation and lifecycle status are the only fields that may
            # advance after materialization.  Replacing the record here keeps
            # recovery and live evaluation commits on the same graph state.
            self._candidates[candidate.candidate_id] = candidate
        else:
            self._candidates[candidate.candidate_id] = candidate
        source_hash = candidate.source_artifact.content_hash
        prior_source = self._by_source.get(source_hash)
        if prior_source is not None and prior_source != candidate.candidate_id:
            raise FrontierError("source identity maps to multiple candidate ids")
        self._by_source.setdefault(source_hash, candidate.candidate_id)
        edge = ProvenanceEdge(
            candidate_id=candidate.candidate_id,
            recipient_id=candidate.recipient_id,
            parent_candidate_ids=tuple(candidate.parent_candidate_ids),
            mutation_id=candidate.mutation_id,
            lane=candidate.lane,
        )
        edges = self._edges.setdefault(candidate.candidate_id, [])
        if edge not in edges:
            edges.append(edge)
        return self._candidates[candidate.candidate_id]

    def get(self, candidate_id: str) -> Optional[CandidateRecord]:
        return self._candidates.get(candidate_id)

    def by_source(self, source_hash: str) -> Optional[CandidateRecord]:
        candidate_id = self._by_source.get(source_hash)
        return self._candidates.get(candidate_id) if candidate_id is not None else None

    def all(self) -> Tuple[CandidateRecord, ...]:
        return tuple(self._candidates[key] for key in sorted(self._candidates))

    def provenance(self, candidate_id: str) -> Tuple[ProvenanceEdge, ...]:
        return tuple(self._edges.get(candidate_id, ()))

    @property
    def candidates(self) -> Mapping[str, CandidateRecord]:
        return dict(self._candidates)


class RecipientLocalEvaluationCache:
    """Cache values only under recipient plus candidate/mutation and evaluator."""

    def __init__(self) -> None:
        self._values: Dict[Tuple[str, str, str], Any] = {}
        self._keys: Dict[str, Tuple[str, str, str]] = {}

    @staticmethod
    def key_for(recipient_id: str, candidate_or_mutation_id: str, evaluator_identity: str) -> str:
        return hash_canonical(
            {
                "recipient_id": recipient_id,
                "candidate_or_mutation_id": candidate_or_mutation_id,
                "evaluator_identity": evaluator_identity,
            }
        )

    def put(
        self,
        recipient_id: str,
        candidate_or_mutation_id: str,
        evaluator_identity: str,
        value: Any,
    ) -> str:
        key = (recipient_id, candidate_or_mutation_id, evaluator_identity)
        cache_key = self.key_for(*key)
        self._values[key] = value
        self._keys[cache_key] = key
        return cache_key

    def get(
        self,
        recipient_id: str,
        candidate_or_mutation_id: str,
        evaluator_identity: str,
    ) -> Optional[Any]:
        return self._values.get((recipient_id, candidate_or_mutation_id, evaluator_identity))

    def get_by_key(self, cache_key: str, *, recipient_id: Optional[str] = None) -> Optional[Any]:
        key = self._keys.get(cache_key)
        if key is None:
            return None
        if recipient_id is not None and key[0] != recipient_id:
            raise CrossRecipientCacheError("cache key belongs to another recipient")
        return self._values.get(key)

    def contains(self, recipient_id: str, candidate_or_mutation_id: str, evaluator_identity: str) -> bool:
        return (recipient_id, candidate_or_mutation_id, evaluator_identity) in self._values

    def items(self) -> Tuple[Tuple[Tuple[str, str, str], Any], ...]:
        return tuple((key, self._values[key]) for key in sorted(self._values))


def component_tuple(vector: ScoreVector) -> Tuple[int, int, int, int, int]:
    return tuple(getattr(vector.components, name) for name in SCORE_FIELDS)  # type: ignore[return-value]


def dominates(left: ScoreVector, right: ScoreVector) -> bool:
    """Return whether ``left`` is no worse in all components and better in one."""
    if left.compile_status != "success" or right.compile_status != "success":
        return False
    a = component_tuple(left)
    b = component_tuple(right)
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def scalar_key(candidate: CandidateRecord) -> Tuple[int, str]:
    if candidate.evaluation is None or candidate.evaluation.total is None:
        return (10**18, candidate.candidate_id)
    return (candidate.evaluation.total, candidate.candidate_id)


class BoundedParetoFrontier:
    """Retain a deterministic, bounded non-dominated set plus a scalar elite."""

    def __init__(self, cap: int = 8) -> None:
        if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
            raise ValueError("frontier cap must be positive")
        self.cap = cap
        self._candidates: Dict[str, CandidateRecord] = {}
        # Archive decisions are local to a recipient.  Keeping the candidate
        # index global is useful for provenance, but sharing a scalar elite or
        # Pareto slot across recipients would make one function's score evict
        # another function's useful residual shape.
        self._scalar_elites: Dict[str, Optional[str]] = {}
        self._pareto_by_recipient: Dict[str, Tuple[str, ...]] = {}
        self._decisions: List[ArchiveDecision] = []

    def _eligible(self, recipient_id: str) -> List[CandidateRecord]:
        return [
            candidate
            for candidate in self._candidates.values()
            if candidate.recipient_id == recipient_id
            and candidate.evaluation is not None
            and candidate.evaluation.compile_status == "success"
        ]

    def _recompute(self, recipient_id: str) -> None:
        eligible = self._eligible(recipient_id)
        if eligible:
            scalar_elite = min(eligible, key=scalar_key).candidate_id
        else:
            scalar_elite = None
        self._scalar_elites[recipient_id] = scalar_elite

        nondominated = []
        for candidate in eligible:
            if any(
                other.candidate_id != candidate.candidate_id
                and other.evaluation is not None
                and dominates(other.evaluation, candidate.evaluation)  # type: ignore[arg-type]
                for other in eligible
            ):
                continue
            nondominated.append(candidate)

        ordered = sorted(nondominated, key=scalar_key)
        selected: List[CandidateRecord] = []
        signatures = set()
        # First use one candidate per mismatch signature.  This keeps a
        # component-wise useful sibling visible even if its scalar total is
        # worse than another non-dominated candidate.
        for candidate in ordered:
            signature = candidate.evaluation.mismatch_signature if candidate.evaluation else None
            if signature in signatures:
                continue
            selected.append(candidate)
            signatures.add(signature)
            if len(selected) == self.cap:
                break
        if len(selected) < self.cap:
            selected_ids = {candidate.candidate_id for candidate in selected}
            for candidate in ordered:
                if candidate.candidate_id in selected_ids:
                    continue
                selected.append(candidate)
                if len(selected) == self.cap:
                    break
        self._pareto_by_recipient[recipient_id] = tuple(
            sorted(candidate.candidate_id for candidate in selected)
        )

    def consider(self, candidate: CandidateRecord, reason: str = "evaluated") -> ArchiveDecision:
        self._candidates[candidate.candidate_id] = candidate
        recipient_id = candidate.recipient_id
        self._recompute(recipient_id)
        scalar_elite = self._scalar_elites[recipient_id]
        pareto = self._pareto_by_recipient[recipient_id]
        if candidate.evaluation is None or candidate.evaluation.compile_status != "success":
            decision = "reject"
        elif candidate.candidate_id == scalar_elite and candidate.candidate_id in pareto:
            decision = "retain_both"
        elif candidate.candidate_id == scalar_elite:
            decision = "retain_scalar_elite"
        elif candidate.candidate_id in pareto:
            decision = "retain_pareto"
        else:
            decision = "archive_dominated"
        if scalar_elite is None:
            # The schema requires an ID even for a rejected candidate.  A
            # rejected compile has no eligible elite, so use the candidate ID
            # as the deterministic sentinel while keeping the decision reject.
            scalar = candidate.candidate_id
        else:
            scalar = scalar_elite
        result = ArchiveDecision(
            candidate_id=candidate.candidate_id,
            recipient_id=recipient_id,
            decision=decision,
            scalar_elite_candidate_id=scalar,
            pareto_candidate_ids=pareto,
            reason=reason,
        )
        self._decisions.append(result)
        return result

    @property
    def scalar_elite_id(self) -> Optional[str]:
        recipients = sorted(self._scalar_elites)
        if len(recipients) == 1:
            return self._scalar_elites[recipients[0]]
        return None

    def scalar_elite_for(self, recipient_id: str) -> Optional[str]:
        return self._scalar_elites.get(recipient_id)

    @property
    def pareto_ids(self) -> Tuple[str, ...]:
        recipients = sorted(self._pareto_by_recipient)
        if len(recipients) == 1:
            return self._pareto_by_recipient[recipients[0]]
        return ()

    def pareto_for(self, recipient_id: str) -> Tuple[str, ...]:
        return self._pareto_by_recipient.get(recipient_id, ())

    @property
    def recipient_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self._scalar_elites))

    @property
    def decisions(self) -> Tuple[ArchiveDecision, ...]:
        return tuple(self._decisions)

    def candidates(self) -> Tuple[CandidateRecord, ...]:
        return tuple(self._candidates[key] for key in sorted(self._candidates))


class SearchFrontier:
    """Combined graph, cache and bounded archive used by coordinator recovery."""

    def __init__(self, cap: int = 8) -> None:
        self.graph = CandidateGraph()
        self.cache = RecipientLocalEvaluationCache()
        self.archive = BoundedParetoFrontier(cap)

    def add_candidate(self, candidate: CandidateRecord) -> CandidateRecord:
        return self.graph.add(candidate)

    def add_evaluation(self, event: EvaluationEvent, candidate: Optional[CandidateRecord] = None) -> Optional[ArchiveDecision]:
        if candidate is not None:
            self.add_candidate(candidate)
        self.cache.put(event.recipient_id, event.candidate_id, event.after.compiler_identity, event)
        if candidate is None:
            candidate = self.graph.get(event.candidate_id)
        if candidate is None:
            return None
        if candidate.recipient_id != event.recipient_id:
            raise FrontierError("evaluation recipient differs from candidate")
        if candidate.evaluation is not None and candidate.evaluation != event.after:
            raise FrontierError("candidate already has a conflicting evaluation")
        if candidate.evaluation is None:
            status = "zero_pending_oracle" if event.after.total == 0 else "evaluated"
            candidate = replace(candidate, evaluation=event.after, status=status)
            self.graph.add(candidate)
        return self.archive.consider(candidate)

    @property
    def scalar_elite_id(self) -> Optional[str]:
        return self.archive.scalar_elite_id

    def scalar_elite_for(self, recipient_id: str) -> Optional[str]:
        return self.archive.scalar_elite_for(recipient_id)

    @property
    def pareto_ids(self) -> Tuple[str, ...]:
        return self.archive.pareto_ids

    def pareto_for(self, recipient_id: str) -> Tuple[str, ...]:
        return self.archive.pareto_for(recipient_id)

    @property
    def decisions(self) -> Tuple[ArchiveDecision, ...]:
        return self.archive.decisions


def frontier_from_events(events: Sequence[LedgerEvent], cap: int = 8) -> SearchFrontier:
    frontier = SearchFrontier(cap)
    candidates: Dict[str, CandidateRecord] = {}
    for event in events:
        if event.event_type == "candidate_materialized":
            candidate = event.payload
            assert isinstance(candidate, CandidateRecord)
            candidates[candidate.candidate_id] = candidate
            frontier.add_candidate(candidate)
        elif event.event_type == "evaluation_completed":
            evaluation = event.payload
            assert isinstance(evaluation, EvaluationEvent)
            candidate = candidates.get(evaluation.candidate_id)
            if candidate is not None:
                if candidate.evaluation != evaluation.after:
                    candidate = CandidateRecord(
                        candidate_id=candidate.candidate_id,
                        recipient_id=candidate.recipient_id,
                        source_artifact=candidate.source_artifact,
                        parent_candidate_ids=candidate.parent_candidate_ids,
                        mutation_id=candidate.mutation_id,
                        lane=candidate.lane,
                        depth=candidate.depth,
                        evaluation=evaluation.after,
                        status=("zero_pending_oracle" if evaluation.after.total == 0 else "evaluated"),
                    )
                    candidates[candidate.candidate_id] = candidate
                frontier.add_candidate(candidate)
            frontier.cache.put(
                evaluation.recipient_id,
                evaluation.candidate_id,
                evaluation.after.compiler_identity,
                evaluation,
            )
        elif event.event_type == "archive_decided":
            # Decisions are derived from all candidate/evaluation events.  The
            # event is retained by the ledger, while recomputation makes the
            # materialized frontier independent of worker timing.
            continue
    for candidate in sorted(candidates.values(), key=lambda item: item.candidate_id):
        if candidate.evaluation is not None:
            frontier.archive.consider(candidate, reason="recovered")
    return frontier


CandidateArchive = BoundedParetoFrontier
EvaluationCache = RecipientLocalEvaluationCache
ParetoFrontier = BoundedParetoFrontier


__all__ = [
    "FrontierError", "CrossRecipientCacheError", "ProvenanceEdge", "CandidateGraph",
    "RecipientLocalEvaluationCache", "EvaluationCache", "component_tuple", "dominates",
    "scalar_key", "BoundedParetoFrontier", "ParetoFrontier", "CandidateArchive",
    "SearchFrontier", "frontier_from_events",
]
