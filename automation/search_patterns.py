"""Read-only mining of completed instrumented-search lineages.

The miner deliberately has no queue or coordinator write path.  A source run
is accepted only when its manifest, complete ledger, referenced artifacts and
terminal task state all describe one immutable completed prefix.  The report
artifact is written to a separate content-addressed archive and can therefore
be handed to a later run without changing the run that produced the evidence.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union

from .search_archive import ArchiveError, ContentAddressedArchive
from .search_ledger import AppendOnlyLedger, LedgerIntegrityError
from .search_types import (
    ArtifactRef,
    CandidateRecord,
    EvaluationEvent,
    LANES,
    LedgerEvent,
    MutationEvent,
    RunManifest,
    RunStop,
    SearchTask,
    SearchValidationError,
    TaskTerminal,
    canonical_bytes,
    canonical_json,
    hash_bytes,
    hash_canonical,
    iter_artifact_refs,
    validate_hash,
    validate_id,
    validate_run_id,
)


class SearchPatternError(RuntimeError):
    """Base class for typed pattern-miner failures."""


class PatternInputError(SearchPatternError):
    """The miner was given an invalid or ambiguous source description."""


class PatternLedgerCorrupt(PatternInputError):
    """A ledger or manifest is not a valid immutable prefix."""


class PatternPartialLedger(PatternLedgerCorrupt):
    """The ledger has an unterminated trailing JSON line."""


class PatternActiveRun(PatternInputError):
    """The source run has not reached its non-resumable completed boundary."""


class PatternArtifactError(PatternInputError):
    """A referenced content-addressed artifact is missing or corrupt."""


class PatternIdentityMismatch(PatternInputError):
    """A supplied identity does not match immutable source content."""


class PatternAmbiguousLineage(PatternInputError):
    """The same identity maps to conflicting lineage records."""


class PatternInsufficientEvidence(SearchPatternError):
    """A report request does not contain enough observations for a pattern."""


# Short aliases make the typed failure surface convenient for callers that use
# the noun form from the design documents.
LedgerCorrupt = PatternLedgerCorrupt
PartialLedger = PatternPartialLedger
ActiveRun = PatternActiveRun
ArtifactIdentityMismatch = PatternIdentityMismatch
AmbiguousLineage = PatternAmbiguousLineage


REPORT_VERSION = "1.0.0"
DEFAULT_MIN_SAMPLES = 2
DEFAULT_MIN_SUCCESSES = 2
DEFAULT_MAX_RECOMMENDATIONS = 32
DEFAULT_SUMMARY_LIMIT = 4096
MAX_SUMMARY_LIMIT = 16384


def _evaluator_tool_key() -> str:
    """Return the reserved evaluator key from its single owning module.

    Function-level import: search_coordinator imports this module and the
    supervisor imports search_coordinator, so a module-level import would
    close an initialization cycle for a constant that has exactly one owner.
    """

    try:
        from .search_supervisor import EVALUATOR_TOOL_KEY
    except ImportError:  # pragma: no cover - direct invocation from automation/
        from automation.search_supervisor import EVALUATOR_TOOL_KEY  # type: ignore
    return EVALUATOR_TOOL_KEY


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    return value


def _freeze(value: Any, label: str) -> Any:
    """Deep-freeze JSON-shaped report data and reject non-JSON values."""
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise PatternInputError(f"{label} keys must be strings")
        return MappingProxyType({
            key: _freeze(value[key], f"{label}.{key}")
            for key in sorted(value)
        })
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item, label) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise PatternInputError(f"{label} must contain JSON values")


def _tuple_unique_hashes(values: Iterable[str], label: str) -> Tuple[str, ...]:
    result = tuple(values)
    if not result:
        raise PatternInputError(f"{label} must not be empty")
    if len(set(result)) != len(result):
        raise PatternInputError(f"{label} contains duplicate identities")
    for value in result:
        try:
            validate_hash(value, label)
        except SearchValidationError as exc:
            raise PatternInputError(str(exc)) from exc
    return tuple(sorted(result))


def _report_payload(
    source_ledgers: Sequence[str],
    recommendations: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    return {
        "report_version": REPORT_VERSION,
        "source_ledgers": list(source_ledgers),
        "recommendations": [_plain(item) for item in recommendations],
    }


@dataclass(frozen=True)
class SearchPatternReport:
    """Immutable, content-addressed summary of completed search evidence."""

    report_id: str
    source_ledgers: Tuple[str, ...]
    recommendations: Tuple[Mapping[str, object], ...]
    artifact: ArtifactRef

    def __post_init__(self) -> None:
        try:
            validate_hash(self.report_id, "report_id")
        except SearchValidationError as exc:
            raise PatternInputError(str(exc)) from exc
        source_ledgers = _tuple_unique_hashes(self.source_ledgers, "source_ledgers")
        object.__setattr__(self, "source_ledgers", source_ledgers)
        recommendations = tuple(_freeze(item, "recommendation") for item in self.recommendations)
        if any(not isinstance(item, Mapping) for item in recommendations):
            raise PatternInputError("recommendations must be objects")
        object.__setattr__(self, "recommendations", recommendations)
        artifact = self.artifact
        if not isinstance(artifact, ArtifactRef):
            try:
                artifact = ArtifactRef.from_dict(artifact)  # type: ignore[arg-type]
            except SearchValidationError as exc:
                raise PatternInputError(str(exc)) from exc
            object.__setattr__(self, "artifact", artifact)
        payload = _report_payload(source_ledgers, recommendations)
        expected = hash_canonical(payload)
        if self.report_id != expected:
            raise PatternIdentityMismatch("report_id does not match canonical report content")
        if artifact.content_hash != self.report_id:
            raise PatternIdentityMismatch("report artifact hash differs from report_id")

    def payload(self) -> Dict[str, Any]:
        """Return the canonical artifact payload without mutable containers."""
        return _report_payload(self.source_ledgers, self.recommendations)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "source_ledgers": list(self.source_ledgers),
            "recommendations": [_plain(item) for item in self.recommendations],
            "artifact": self.artifact.to_dict(),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SearchPatternReport":
        if not isinstance(value, Mapping):
            raise PatternInputError("search pattern report must be an object")
        fields = {"report_id", "source_ledgers", "recommendations", "artifact"}
        unknown = set(value).difference(fields)
        missing = fields.difference(value)
        if missing:
            raise PatternInputError(
                "search pattern report is missing fields: " + ", ".join(sorted(missing))
            )
        if unknown:
            raise PatternInputError(
                "search pattern report has unknown fields: " + ", ".join(sorted(unknown))
            )
        try:
            artifact = ArtifactRef.from_dict(value["artifact"])
        except SearchValidationError as exc:
            raise PatternInputError(str(exc)) from exc
        try:
            source_ledgers = tuple(value["source_ledgers"])
            recommendations = tuple(value["recommendations"])
        except TypeError as exc:
            raise PatternInputError("report collections must be arrays") from exc
        return cls(
            report_id=value["report_id"],
            source_ledgers=source_ledgers,
            recommendations=recommendations,
            artifact=artifact,
        )

    @classmethod
    def from_json(cls, text: str) -> "SearchPatternReport":
        try:
            value = json.loads(text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise PatternInputError("invalid search pattern report JSON") from exc
        return cls.from_dict(value)


@dataclass(frozen=True)
class _CompletedLedger:
    root: Path
    ledger_path: Path
    manifest: RunManifest
    events: Tuple[LedgerEvent, ...]
    identity: str


@dataclass(frozen=True)
class _LedgerInput:
    path: Path
    expected_identity: Optional[str] = None


def _path_from_input(value: Any) -> _LedgerInput:
    expected: Optional[str] = None
    candidate = value
    if isinstance(value, Mapping):
        allowed = {"path", "ledger", "ledger_path", "run_root", "identity", "ledger_identity", "ledger_hash"}
        unknown = set(value).difference(allowed)
        if unknown:
            raise PatternInputError(
                "ledger input has unknown fields: " + ", ".join(sorted(unknown))
            )
        candidate = value.get("path", value.get("ledger", value.get("ledger_path", value.get("run_root"))))
        expected = value.get("identity", value.get("ledger_identity", value.get("ledger_hash")))
        if candidate is None:
            raise PatternInputError("ledger input needs a path")
    elif isinstance(value, (tuple, list)) and len(value) == 2:
        candidate, expected = value
    try:
        path = Path(candidate)
    except TypeError as exc:
        raise PatternInputError("ledger input path is invalid") from exc
    if expected is not None:
        try:
            validate_hash(expected, "ledger identity")
        except SearchValidationError as exc:
            raise PatternIdentityMismatch(str(exc)) from exc
    return _LedgerInput(path, expected)


def _load_manifest(path: Path) -> RunManifest:
    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw)
        return RunManifest.from_dict(value)
    except FileNotFoundError as exc:
        raise PatternLedgerCorrupt("run manifest is missing") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, SearchValidationError) as exc:
        raise PatternLedgerCorrupt("run manifest is invalid") from exc


def _validate_task_prefix(events: Sequence[LedgerEvent]) -> None:
    tasks: Dict[str, SearchTask] = {}
    started: Set[str] = set()
    terminals: Dict[str, TaskTerminal] = {}
    for event in events:
        if event.event_type == "task_scheduled":
            task = event.payload
            assert isinstance(task, SearchTask)
            if task.task_id in tasks:
                raise PatternAmbiguousLineage("task was scheduled more than once")
            tasks[task.task_id] = task
        elif event.event_type == "task_started":
            task = event.payload
            assert isinstance(task, SearchTask)
            prior = tasks.get(task.task_id)
            if prior is None:
                raise PatternLedgerCorrupt("task started before it was scheduled")
            if task.task_id in started:
                raise PatternAmbiguousLineage("task was started more than once")
            # Only lifecycle state is allowed to differ between the two
            # envelopes.  Comparing a reconstruction of ``prior`` to itself
            # would let every identity-bearing field change under one task id.
            if replace(prior, state="scheduled") != replace(task, state="scheduled"):
                raise PatternIdentityMismatch("task identity changed between schedule and start")
            if task.state != "started":
                raise PatternLedgerCorrupt("task_started payload is not started")
            started.add(task.task_id)
            tasks[task.task_id] = task
        elif event.event_type == "task_interrupted":
            interruption = event.payload
            if interruption.task_id not in tasks:  # type: ignore[union-attr]
                raise PatternLedgerCorrupt("interruption names an unknown task")
        elif event.event_type == "task_completed":
            terminal = event.payload
            assert isinstance(terminal, TaskTerminal)
            if terminal.task_id not in tasks:
                raise PatternLedgerCorrupt("terminal result names an unknown task")
            prior_terminal = terminals.get(terminal.task_id)
            if prior_terminal is not None and prior_terminal != terminal:
                raise PatternAmbiguousLineage("task has conflicting terminal results")
            if prior_terminal is not None:
                raise PatternAmbiguousLineage("task has duplicate terminal results")
            terminals[terminal.task_id] = terminal
    if set(tasks).difference(terminals):
        raise PatternActiveRun("completed run has non-terminal tasks")


def _validate_artifacts(events: Sequence[LedgerEvent], archive: ContentAddressedArchive) -> None:
    for event in events:
        for reference in iter_artifact_refs(event.payload):
            try:
                archive.verify(reference)
            except (ArchiveError, OSError) as exc:
                raise PatternArtifactError(
                    f"missing or corrupt artifact: {reference.path}"
                ) from exc
        if event.event_type == "run_stopped":
            stop = event.payload
            assert isinstance(stop, RunStop)
            digest = stop.budget_snapshot_hash.removeprefix("sha256:")
            matches = []
            receipts = archive.artifacts_root / "receipts"
            if receipts.is_dir():
                matches = sorted(
                    path for path in receipts.rglob(digest + "*") if path.is_file()
                )
            valid = False
            for path in matches:
                try:
                    data = path.read_bytes()
                except OSError:
                    continue
                if hash_bytes(data) == stop.budget_snapshot_hash:
                    valid = True
                    break
            if not valid:
                raise PatternArtifactError("missing or corrupt run-stop budget snapshot")


def _load_completed_ledger(value: Any) -> _CompletedLedger:
    source = _path_from_input(value)
    path = source.path
    if path.is_dir():
        root = path
        ledger_path = root / "ledger.jsonl"
    else:
        ledger_path = path
        root = path.parent
    manifest = _load_manifest(root / "manifest.json")
    archive = ContentAddressedArchive(root)
    ledger = AppendOnlyLedger(ledger_path, run_id=manifest.run_id, archive=archive)
    try:
        events = ledger.verify()
    except (LedgerIntegrityError, OSError) as exc:
        raise PatternLedgerCorrupt("ledger integrity validation failed") from exc
    if ledger.partial_bytes:
        raise PatternPartialLedger("ledger has an unterminated trailing event")
    if not events:
        raise PatternLedgerCorrupt("ledger is empty")
    if not isinstance(events[0].payload, RunManifest) or events[0].payload != manifest:
        raise PatternIdentityMismatch("manifest and run_started disagree")
    stop_events = [event for event in events if event.event_type == "run_stopped"]
    if len(stop_events) != 1 or events[-1] != stop_events[0]:
        raise PatternActiveRun("source ledger is active or resumable: no single completed prefix")
    stop = stop_events[0].payload
    assert isinstance(stop, RunStop)
    if stop.reason != "completed" or stop.resumable or stop.pending_task_ids:
        raise PatternActiveRun("source run is active or resumable")
    _validate_task_prefix(events)
    # The canonical semantic pass: replay ordering and cross-record bindings
    # exactly as the coordinator enforces them for recovery, including score
    # provenance against the manifest. Function-level import because
    # search_coordinator imports this module. Artifact bytes are verified by
    # _validate_artifacts below, which also owns the run-stop snapshot check.
    try:
        from .search_coordinator import CoordinatorError, validate_ledger_prefix
    except ImportError:  # pragma: no cover - direct invocation from automation/
        from automation.search_coordinator import (  # type: ignore
            CoordinatorError,
            validate_ledger_prefix,
        )
    try:
        validate_ledger_prefix(
            manifest, events, archive=archive, verify_artifacts=False
        )
    except CoordinatorError as exc:
        raise PatternLedgerCorrupt(
            "ledger fails coordinator semantic validation: " + str(exc)
        ) from exc
    _validate_artifacts(events, archive)
    try:
        raw = ledger_path.read_bytes()
    except OSError as exc:
        raise PatternLedgerCorrupt("ledger cannot be read") from exc
    identity = hash_bytes(raw)
    if source.expected_identity is not None and identity != source.expected_identity:
        raise PatternIdentityMismatch("ledger identity differs from supplied identity")
    return _CompletedLedger(root, ledger_path, manifest, tuple(events), identity)


@dataclass(frozen=True)
class CompletedLineageContext:
    """One completed, artifact-verified ledger bound to its exact identities.

    A context is promotion eligible: its manifest carries the reserved
    evaluator tool binding, so its score evidence can be attributed to the
    evaluator that produced it rather than to the landing oracle.
    """

    ledger_identity: str
    run_id: str
    compiler_identity: str
    config_identity: str
    schema_identity: str
    scorer_algorithms: Tuple[str, ...]
    lane_tool_identities: Tuple[Tuple[str, str], ...]
    recipient_target_identities: Tuple[Tuple[str, str], ...]
    evaluator_identity: str

    def __post_init__(self) -> None:
        try:
            validate_hash(self.ledger_identity, "ledger_identity")
            validate_run_id(self.run_id, "run_id")
            for name in (
                "compiler_identity",
                "config_identity",
                "schema_identity",
                "evaluator_identity",
            ):
                validate_hash(getattr(self, name), name)
            if not isinstance(self.scorer_algorithms, (tuple, list)):
                raise SearchValidationError(
                    "scorer algorithms must be a sequence of strings"
                )
            algorithms = tuple(self.scorer_algorithms)
            if any(not isinstance(item, str) or not item for item in algorithms):
                raise SearchValidationError(
                    "scorer algorithms must be nonempty strings"
                )
            if algorithms != tuple(sorted(set(algorithms))):
                raise SearchValidationError(
                    "scorer algorithms must be sorted and unique"
                )
            object.__setattr__(self, "scorer_algorithms", algorithms)

            def _pairs(values: Any, label: str, keyed_by_lane: bool) -> Tuple[Tuple[str, str], ...]:
                if not isinstance(values, (tuple, list)):
                    raise SearchValidationError(
                        f"{label} must be a sequence of (name, identity) pairs"
                    )
                pairs: List[Tuple[str, str]] = []
                names: Set[str] = set()
                for item in values:
                    if not isinstance(item, (tuple, list)) or len(item) != 2:
                        raise SearchValidationError(
                            f"{label} entries must be (name, identity) pairs"
                        )
                    name, identity = item
                    if not isinstance(name, str) or not isinstance(identity, str):
                        raise SearchValidationError(
                            f"{label} entries must be (name, identity) strings"
                        )
                    if name in names:
                        raise SearchValidationError(
                            f"{label} names {name!r} more than once"
                        )
                    names.add(name)
                    if keyed_by_lane:
                        if name not in LANES:
                            raise SearchValidationError(
                                f"{label} names the unknown lane {name!r}"
                            )
                    else:
                        validate_id(name, label)
                    validate_hash(identity, label)
                    pairs.append((name, identity))
                if tuple(pairs) != tuple(sorted(set(pairs))):
                    raise SearchValidationError(
                        f"{label} must be sorted and unique"
                    )
                return tuple(pairs)

            object.__setattr__(
                self,
                "lane_tool_identities",
                _pairs(self.lane_tool_identities, "lane tool identity", True),
            )
            object.__setattr__(
                self,
                "recipient_target_identities",
                _pairs(
                    self.recipient_target_identities,
                    "recipient target identity",
                    False,
                ),
            )
        except SearchValidationError as exc:
            raise PatternInputError(str(exc)) from exc


@dataclass(frozen=True)
class CompletedLineageDiagnostic:
    """A completed ledger that cannot become a promotion-eligible context.

    Historical ledgers lost their evaluator binding before the reserved key
    existed. They stay diagnostic evidence with the identities that were
    present, instead of being silently promoted with unknown provenance.
    """

    ledger_identity: str
    run_id: str
    reason_code: str
    observed_identities: Tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            validate_hash(self.ledger_identity, "ledger_identity")
            validate_run_id(self.run_id, "run_id")
            if self.reason_code != "missing_evaluator_identity":
                raise SearchValidationError(
                    "unsupported diagnostic reason: " + str(self.reason_code)
                )
            if not isinstance(self.observed_identities, (tuple, list)):
                raise SearchValidationError(
                    "observed identities must be a sequence of hashes"
                )
            observed = tuple(self.observed_identities)
            for item in observed:
                if not isinstance(item, str):
                    raise SearchValidationError(
                        "observed identities must be strings"
                    )
                # Every retained observed identity must actually exist; the
                # projection drops absent bindings instead of recording an
                # empty placeholder.
                validate_hash(item, "observed identity")
            if observed != tuple(sorted(set(observed))):
                raise SearchValidationError(
                    "observed identities must be sorted and unique"
                )
            object.__setattr__(self, "observed_identities", observed)
        except SearchValidationError as exc:
            raise PatternInputError(str(exc)) from exc


def _normalize_ledger_inputs(
    ledgers: Optional[Union[Any, Sequence[Any]]],
    ledger_paths: Optional[Sequence[Any]],
    expected_ledger_identities: Optional[Mapping[Union[str, int], str]],
) -> List[Any]:
    """Normalize the shared ledger input forms without loading anything."""

    if ledgers is None:
        if ledger_paths is None:
            raise PatternInputError("at least one ledger is required")
        ledgers = ledger_paths
    elif ledger_paths is not None:
        raise PatternInputError("provide ledgers or ledger_paths, not both")
    if isinstance(ledgers, (str, os.PathLike, Mapping)):
        values: Sequence[Any] = (ledgers,)
    else:
        try:
            values = tuple(ledgers)
        except TypeError as exc:
            raise PatternInputError("ledgers must be a path or sequence of paths") from exc
    if not values:
        raise PatternInputError("at least one ledger is required")
    if expected_ledger_identities is None:
        return list(values)
    normalized: List[Any] = []
    for index, value in enumerate(values):
        expected = expected_ledger_identities.get(index)
        if expected is None:
            expected = expected_ledger_identities.get(str(index))
        if expected is not None:
            if isinstance(value, Mapping):
                value = dict(value)
                value.setdefault("ledger_hash", expected)
            else:
                value = (value, expected)
        normalized.append(value)
    return normalized


def _lineage_projection(
    run: _CompletedLedger,
) -> Union[CompletedLineageContext, CompletedLineageDiagnostic]:
    """Project one loaded ledger as a context or a diagnostic, once.

    Both the public loader and the miner share this single projection so a
    ledger missing its evaluator binding can never be a promotion-eligible
    context in one path and a recommendation sample in another.
    """

    evaluator_key = _evaluator_tool_key()
    evaluator = run.manifest.tool_identities.get(evaluator_key)
    if evaluator is None:
        # Only identities that actually exist are recorded. A manifest with
        # no full-oracle binding contributes no placeholder to the
        # diagnostic; an absent binding is the absence of evidence, not an
        # empty identity.
        observed = tuple(
            sorted(
                identity
                for identity in (
                    run.manifest.compiler_identity,
                    run.manifest.config_identity,
                    run.manifest.schema_identity,
                    run.manifest.tool_identities.get("full_oracle", ""),
                )
                if identity
            )
        )
        return CompletedLineageDiagnostic(
            ledger_identity=run.identity,
            run_id=run.manifest.run_id,
            reason_code="missing_evaluator_identity",
            observed_identities=observed,
        )
    return CompletedLineageContext(
        ledger_identity=run.identity,
        run_id=run.manifest.run_id,
        compiler_identity=run.manifest.compiler_identity,
        config_identity=run.manifest.config_identity,
        schema_identity=run.manifest.schema_identity,
        scorer_algorithms=tuple(
            sorted(
                {
                    event.payload.after.scorer_algorithm
                    for event in run.events
                    if event.event_type == "evaluation_completed"
                }
            )
        ),
        lane_tool_identities=tuple(
            sorted(
                (lane, run.manifest.tool_identities[lane])
                for lane in run.manifest.selected_lanes
            )
        ),
        recipient_target_identities=tuple(
            sorted(run.manifest.target_identities.items())
        ),
        evaluator_identity=evaluator,
    )


def load_completed_lineage_contexts(
    ledgers: Optional[Union[Any, Sequence[Any]]] = None,
    *,
    ledger_paths: Optional[Sequence[Any]] = None,
    expected_ledger_identities: Optional[Mapping[Union[str, int], str]] = None,
) -> Tuple[Union[CompletedLineageContext, CompletedLineageDiagnostic], ...]:
    """Load terminal, artifact-verified ledgers as typed lineage contexts.

    Accepts exactly the input forms of ``mine_completed_lineages`` and runs
    the same ``_load_completed_ledger`` validation. Ledgers are projected in
    ascending immutable ledger identity order regardless of input order, so
    the output is a deterministic function of the ledger set.
    """

    normalized = _normalize_ledger_inputs(
        ledgers, ledger_paths, expected_ledger_identities
    )
    runs = [_load_completed_ledger(value) for value in normalized]
    seen: Set[str] = set()
    for run in runs:
        if run.identity in seen:
            raise PatternAmbiguousLineage(
                "the same source ledger identity was supplied twice"
            )
        seen.add(run.identity)
    runs.sort(key=lambda run: run.identity)
    return tuple(_lineage_projection(run) for run in runs)


def _overlay(recipient_id: str) -> str:
    parts = [part for part in recipient_id.split(":") if part]
    if len(parts) >= 2 and parts[0].lower() in {"us", "hd", "pspeu", "saturn"}:
        return parts[1]
    for part in parts:
        if "/" in part:
            return part
    return "unknown"


_HEX_SUFFIX = re.compile(r"(?:^|[_-])(?:0x)?[0-9a-f]{6,}$", re.IGNORECASE)
_FUNC_PREFIX = re.compile(r"^func_(?:us|hd|pspeu|saturn)_", re.IGNORECASE)


def _function_archetype(recipient_id: str) -> str:
    symbol = recipient_id.split(":")[-1]
    if _FUNC_PREFIX.match(symbol):
        return "generic"
    symbol = _FUNC_PREFIX.sub("", symbol)
    symbol = _HEX_SUFFIX.sub("", symbol)
    lower = symbol.lower()
    categories = (
        (("entity", "spawn", "factory"), "entity"),
        (("step", "setstep", "state"), "state"),
        (("draw", "render", "prim"), "render"),
        (("load", "init", "setup", "create"), "lifecycle"),
        (("check", "get", "find", "test"), "query"),
        (("attack", "hit", "damage", "crash"), "gameplay"),
        (("update", "apply", "move", "anim"), "update"),
    )
    for needles, category in categories:
        if any(needle in lower for needle in needles):
            return category
    if not symbol or symbol == recipient_id:
        return "unknown"
    return "function"


def _first_divergence(value: Optional[Any]) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    data = value.to_dict() if hasattr(value, "to_dict") else dict(value)
    return {
        "target_index": data["target_index"],
        "candidate_index": data["candidate_index"],
        "target_instruction": data.get("target_instruction"),
        "candidate_instruction": data.get("candidate_instruction"),
    }


def _lineage_key(
    *,
    pass_kind: Optional[str],
    patch_id: Optional[str],
    lane: str,
    overlay: str,
    archetype: str,
    first_divergence: Optional[Mapping[str, Any]],
    compiler_identity: str,
    config_identity: str,
    schema_identity: str,
    scorer_algorithm: str,
    lane_tool_identity: str,
    recipient_id: str,
    target_identity: str,
    evaluator_identity: str,
) -> Tuple[Any, ...]:
    # Every identity the corpus binds a hypothesis with is part of the group
    # key, so recommendations from incompatible compilers, configurations,
    # scorers, evaluator bindings or targets can never merge into one
    # pattern.
    return (
        pass_kind or "",
        patch_id or "",
        lane,
        overlay,
        archetype,
        canonical_json(first_divergence) if first_divergence is not None else "",
        compiler_identity,
        config_identity,
        schema_identity,
        scorer_algorithm,
        lane_tool_identity,
        recipient_id,
        target_identity,
        evaluator_identity,
    )


def _success(evaluation: Optional[EvaluationEvent], terminal: TaskTerminal) -> bool:
    if terminal.state != "completed" or evaluation is None:
        return False
    score = evaluation.after
    if score.compile_status != "success":
        return False
    if score.total == 0:
        return True
    if evaluation.decision in {"scalar_elite", "pareto", "zero_pending_oracle"}:
        return True
    return evaluation.deltas.total is not None and evaluation.deltas.total < 0


def _recommendations(
    runs: Sequence[_CompletedLedger],
    *,
    min_samples: int,
    min_successes: int,
    max_recommendations: int,
) -> Tuple[Mapping[str, object], ...]:
    groups: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    evaluator_key = _evaluator_tool_key()
    for run in runs:
        manifest = run.manifest
        run_compiler = manifest.compiler_identity
        run_config = manifest.config_identity
        run_schema = manifest.schema_identity
        run_evaluator = manifest.tool_identities.get(evaluator_key, "")
        tasks: Dict[str, SearchTask] = {}
        candidates: Dict[str, CandidateRecord] = {}
        mutations: Dict[str, MutationEvent] = {}
        evaluations: Dict[str, EvaluationEvent] = {}
        terminals: Dict[str, TaskTerminal] = {}
        for event in run.events:
            if event.event_type in {"task_scheduled", "task_started"}:
                task = event.payload
                assert isinstance(task, SearchTask)
                tasks[task.task_id] = task
            elif event.event_type == "candidate_materialized":
                candidate = event.payload
                assert isinstance(candidate, CandidateRecord)
                previous = candidates.get(candidate.candidate_id)
                if previous is not None and previous != candidate:
                    raise PatternAmbiguousLineage("candidate identity maps to conflicting records")
                candidates[candidate.candidate_id] = candidate
            elif event.event_type == "mutation_materialized":
                mutation = event.payload
                assert isinstance(mutation, MutationEvent)
                previous = mutations.get(mutation.mutation_id)
                if previous is not None and previous != mutation:
                    raise PatternAmbiguousLineage("mutation identity maps to conflicting records")
                mutations[mutation.mutation_id] = mutation
            elif event.event_type == "evaluation_completed":
                evaluation = event.payload
                assert isinstance(evaluation, EvaluationEvent)
                previous = evaluations.get(evaluation.task_id)
                if previous is not None and previous != evaluation:
                    raise PatternAmbiguousLineage("task has conflicting evaluations")
                if previous is not None:
                    raise PatternAmbiguousLineage("task has duplicate evaluations")
                evaluations[evaluation.task_id] = evaluation
            elif event.event_type == "task_completed":
                terminal = event.payload
                assert isinstance(terminal, TaskTerminal)
                terminals[terminal.task_id] = terminal

        for task_id in sorted(tasks):
            task = tasks[task_id]
            terminal = terminals.get(task_id)
            if terminal is None:
                raise PatternActiveRun("completed prefix lost a task terminal")
            evaluation = evaluations.get(task_id)
            candidate: Optional[CandidateRecord] = None
            mutation: Optional[MutationEvent] = None
            if evaluation is not None:
                if evaluation.recipient_id != task.recipient_id:
                    raise PatternIdentityMismatch("evaluation recipient differs from task")
                candidate = candidates.get(evaluation.candidate_id)
                if candidate is None:
                    raise PatternIdentityMismatch("evaluation names a missing candidate")
                if candidate.recipient_id != task.recipient_id:
                    raise PatternIdentityMismatch("candidate recipient differs from task")
                if candidate.lane != task.lane:
                    raise PatternIdentityMismatch("candidate lane differs from task")
                for parent_id in candidate.parent_candidate_ids:
                    if parent_id not in candidates:
                        raise PatternIdentityMismatch("candidate names a missing parent candidate")
                if candidate.mutation_id is not None:
                    mutation = mutations.get(candidate.mutation_id)
                    if mutation is None:
                        raise PatternIdentityMismatch("candidate names a missing mutation")
                    if mutation.recipient_id != task.recipient_id or mutation.lane != task.lane:
                        raise PatternIdentityMismatch("mutation recipient or lane differs from task")
                    parent = candidates.get(mutation.parent_candidate_id)
                    if parent is None:
                        raise PatternIdentityMismatch("mutation names a missing parent candidate")
                    if parent.recipient_id != task.recipient_id:
                        raise PatternIdentityMismatch("mutation parent recipient differs from task")
                    if parent.source_artifact.content_hash != mutation.grouped_patch.base_source_hash:
                        raise PatternIdentityMismatch("mutation patch base differs from parent source")
                    if mutation.replay_status == "applied" and mutation.result_source_hash != candidate.source_artifact.content_hash:
                        raise PatternIdentityMismatch("mutation result differs from candidate source")
                    for donor_id in mutation.donor_candidate_ids:
                        if donor_id not in candidates:
                            raise PatternIdentityMismatch("mutation names a missing donor candidate")
            pass_kind = mutation.pass_kind if mutation is not None else None
            patch_id = mutation.grouped_patch.patch_id if mutation is not None else None
            lane = mutation.lane if mutation is not None else (
                candidate.lane if candidate is not None else task.lane
            )
            overlay = _overlay(task.recipient_id)
            archetype = _function_archetype(task.recipient_id)
            divergence = _first_divergence(evaluation.after.first_divergence) if evaluation is not None else None
            scorer_algorithm = (
                evaluation.after.scorer_algorithm if evaluation is not None else ""
            )
            recipient_id = task.recipient_id
            target_identity = manifest.target_identities.get(recipient_id, "")
            lane_tool_identity = manifest.tool_identities.get(lane, "")
            key = _lineage_key(
                pass_kind=pass_kind,
                patch_id=patch_id,
                lane=lane,
                overlay=overlay,
                archetype=archetype,
                first_divergence=divergence,
                compiler_identity=run_compiler,
                config_identity=run_config,
                schema_identity=run_schema,
                scorer_algorithm=scorer_algorithm,
                lane_tool_identity=lane_tool_identity,
                recipient_id=recipient_id,
                target_identity=target_identity,
                evaluator_identity=run_evaluator,
            )
            group = groups.setdefault(
                key,
                {
                    "pass_kind": pass_kind,
                    "patch_id": patch_id,
                    "lane": lane,
                    "overlay": overlay,
                    "function_archetype": archetype,
                    "first_divergence": divergence,
                    "compiler_identity": run_compiler,
                    "config_identity": run_config,
                    "schema_identity": run_schema,
                    "scorer_algorithm": scorer_algorithm,
                    "lane_tool_identity": lane_tool_identity,
                    "recipient_id": recipient_id,
                    "target_identity": target_identity,
                    "evaluator_identity": run_evaluator,
                    "sample_count": 0,
                    "successes": 0,
                    "failures": 0,
                    "source_ledgers": set(),
                    "lineage_ids": set(),
                },
            )
            group["sample_count"] += 1
            if _success(evaluation, terminal):
                group["successes"] += 1
            else:
                group["failures"] += 1
            group["source_ledgers"].add(run.identity)
            group["lineage_ids"].add(f"{run.manifest.run_id}:{task_id}")

    ranked: List[Mapping[str, object]] = []
    for key, group in groups.items():
        if group["sample_count"] < min_samples or group["successes"] < min_successes:
            continue
        sample_count = group["sample_count"]
        recommendation = {
            "pattern_id": hash_canonical({"key": list(key)}),
            "pass_kind": group["pass_kind"],
            "patch_id": group["patch_id"],
            "lane": group["lane"],
            "overlay": group["overlay"],
            "function_archetype": group["function_archetype"],
            "first_divergence": group["first_divergence"],
            "compiler_identity": group["compiler_identity"],
            "config_identity": group["config_identity"],
            "schema_identity": group["schema_identity"],
            "scorer_algorithm": group["scorer_algorithm"],
            "lane_tool_identity": group["lane_tool_identity"],
            "recipient_id": group["recipient_id"],
            "target_identity": group["target_identity"],
            "evaluator_identity": group["evaluator_identity"],
            "sample_count": sample_count,
            "successes": group["successes"],
            "failures": group["failures"],
            "success_rate": round(group["successes"] / sample_count, 6),
            "source_ledgers": sorted(group["source_ledgers"]),
            "lineage_ids": sorted(group["lineage_ids"]),
        }
        ranked.append(recommendation)
    ranked.sort(
        key=lambda item: (
            -int(item["successes"]),
            -float(item["success_rate"]),
            -int(item["sample_count"]),
            int(item["failures"]),
            str(item["pattern_id"]),
        )
    )
    return tuple(ranked[:max_recommendations])


def mine_completed_lineages(
    ledgers: Optional[Union[Any, Sequence[Any]]] = None,
    *,
    ledger_paths: Optional[Sequence[Any]] = None,
    output_root: Optional[Union[str, os.PathLike[str]]] = None,
    expected_ledger_identities: Optional[Mapping[Union[str, int], str]] = None,
    min_samples: int = DEFAULT_MIN_SAMPLES,
    min_successes: int = DEFAULT_MIN_SUCCESSES,
    max_recommendations: int = DEFAULT_MAX_RECOMMENDATIONS,
) -> SearchPatternReport:
    """Mine only terminal, artifact-verified ledger prefixes.

    ``ledgers`` accepts run roots, ``ledger.jsonl`` paths, ``(path, hash)``
    pairs, or mappings with ``path`` and optional ``ledger_hash``.  A report
    is written under ``output_root`` (a sibling archive is selected when it is
    omitted).  The output root may not be one of the source run roots.
    """
    values = _normalize_ledger_inputs(ledgers, ledger_paths, expected_ledger_identities)
    if isinstance(min_samples, bool) or not isinstance(min_samples, int) or min_samples < 2:
        raise PatternInputError("min_samples must be at least two")
    if isinstance(min_successes, bool) or not isinstance(min_successes, int) or min_successes < 1:
        raise PatternInputError("min_successes must be positive")
    if min_successes > min_samples:
        raise PatternInputError("min_successes cannot exceed min_samples")
    if isinstance(max_recommendations, bool) or not isinstance(max_recommendations, int) or max_recommendations < 1:
        raise PatternInputError("max_recommendations must be positive")

    runs = tuple(_load_completed_ledger(value) for value in values)
    identities = [run.identity for run in runs]
    if len(set(identities)) != len(identities):
        raise PatternAmbiguousLineage("the same source ledger identity was supplied twice")
    roots = [run.root.resolve() for run in runs]
    if output_root is None:
        output_path = roots[0].parent / "search-pattern-reports"
    else:
        output_path = Path(output_root)
    try:
        output_resolved = output_path.resolve()
    except OSError as exc:
        raise PatternInputError("output root cannot be resolved") from exc
    for root in roots:
        if output_resolved == root or root in output_resolved.parents:
            raise PatternIdentityMismatch("report output must not mutate a source run")
    # One shared projection with the public loader, applied after the source
    # guard so a diagnostic-only run set still refuses a hostile output root.
    # A ledger without its evaluator binding is diagnostic evidence and is
    # excluded from recommendation aggregation entirely; it is never
    # re-parsed here.
    runs = tuple(
        run
        for run in runs
        if isinstance(_lineage_projection(run), CompletedLineageContext)
    )
    source_ledgers = tuple(sorted(identities))
    recommendations = _recommendations(
        runs,
        min_samples=min_samples,
        min_successes=min_successes,
        max_recommendations=max_recommendations,
    )
    payload = _report_payload(source_ledgers, recommendations)
    report_id = hash_canonical(payload)
    archive = ContentAddressedArchive(output_path)
    artifact = archive.put_bytes(
        canonical_bytes(payload),
        category="pattern_reports",
        suffix=".json",
        media_type="application/json",
    )
    if artifact.content_hash != report_id:
        raise PatternIdentityMismatch("report artifact identity differs from canonical report")
    return SearchPatternReport(report_id, source_ledgers, recommendations, artifact)


def load_report_artifact(
    value: Union[SearchPatternReport, ArtifactRef, Mapping[str, Any], str, os.PathLike[str]],
    *,
    artifact_root: Optional[Union[str, os.PathLike[str]]] = None,
    expected_hash: Optional[str] = None,
) -> SearchPatternReport:
    """Load and verify one immutable report artifact without writing state."""
    if isinstance(value, SearchPatternReport):
        report = value
        if expected_hash is not None and report.artifact.content_hash != expected_hash:
            raise PatternIdentityMismatch("report artifact hash differs from expected identity")
        if artifact_root is not None:
            archive = ContentAddressedArchive(artifact_root)
            try:
                raw = archive.verify(report.artifact)
            except ArchiveError as exc:
                raise PatternArtifactError("report artifact is missing or corrupt") from exc
            loaded = _report_from_payload(raw, report.artifact)
            if loaded != report:
                raise PatternIdentityMismatch("report object differs from immutable artifact")
        return report
    if isinstance(value, Mapping) and {"report_id", "source_ledgers", "recommendations", "artifact"}.issubset(value):
        report = SearchPatternReport.from_dict(value)
        return load_report_artifact(report, artifact_root=artifact_root, expected_hash=expected_hash)
    if isinstance(value, ArtifactRef):
        if artifact_root is None:
            raise PatternArtifactError("artifact root is required for an artifact reference")
        archive = ContentAddressedArchive(artifact_root)
        try:
            raw = archive.verify(value)
        except ArchiveError as exc:
            raise PatternArtifactError("report artifact is missing or corrupt") from exc
        if expected_hash is not None and value.content_hash != expected_hash:
            raise PatternIdentityMismatch("report artifact hash differs from expected identity")
        return _report_from_payload(raw, value)
    try:
        path = Path(value)
        raw = path.read_bytes()
    except (TypeError, OSError) as exc:
        raise PatternArtifactError("report artifact cannot be read") from exc
    digest = hash_bytes(raw)
    if expected_hash is not None and digest != expected_hash:
        raise PatternIdentityMismatch("report artifact bytes differ from expected identity")
    if artifact_root is not None:
        try:
            relative = path.resolve().relative_to(Path(artifact_root).resolve()).as_posix()
        except ValueError as exc:
            raise PatternArtifactError("report artifact is outside its archive root") from exc
    else:
        relative = path.name
    artifact = ArtifactRef(digest, relative, "application/json", len(raw))
    return _report_from_payload(raw, artifact)


def _report_from_payload(raw: bytes, artifact: ArtifactRef) -> SearchPatternReport:
    if hash_bytes(raw) != artifact.content_hash or len(raw) != artifact.byte_size:
        raise PatternArtifactError("report artifact content hash or size differs")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PatternArtifactError("report artifact is not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise PatternArtifactError("report artifact payload is not an object")
    required = {"report_version", "source_ledgers", "recommendations"}
    if set(payload) != required:
        raise PatternIdentityMismatch("report artifact payload fields differ")
    if payload["report_version"] != REPORT_VERSION:
        raise PatternIdentityMismatch("unsupported report version")
    report_id = hash_canonical(payload)
    try:
        return SearchPatternReport(
            report_id,
            tuple(payload["source_ledgers"]),
            tuple(payload["recommendations"]),
            artifact,
        )
    except (KeyError, TypeError, PatternInputError) as exc:
        raise PatternArtifactError("report artifact content is invalid") from exc


def render_derivation_summary(
    report: SearchPatternReport,
    *,
    max_chars: int = DEFAULT_SUMMARY_LIMIT,
    max_items: int = 8,
) -> str:
    """Render bounded evidence text; this function never publishes a queue note."""
    if not isinstance(report, SearchPatternReport):
        report = SearchPatternReport.from_dict(report)  # type: ignore[arg-type]
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1 or max_chars > MAX_SUMMARY_LIMIT:
        raise PatternInputError(f"max_chars must be between 1 and {MAX_SUMMARY_LIMIT}")
    if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
        raise PatternInputError("max_items must be positive")
    lines = [
        f"search-pattern-report {report.report_id} sources={len(report.source_ledgers)} recommendations={len(report.recommendations)}"
    ]
    for index, recommendation in enumerate(report.recommendations[:max_items], 1):
        first = recommendation.get("first_divergence")
        if isinstance(first, Mapping):
            divergence = f"{first.get('target_index')}->{first.get('candidate_index')}"
        else:
            divergence = "none"
        lines.append(
            f"{index}. lane={recommendation.get('lane')} pass={recommendation.get('pass_kind') or 'none'} "
            f"patch={recommendation.get('patch_id') or 'none'} overlay={recommendation.get('overlay')} "
            f"archetype={recommendation.get('function_archetype')} divergence={divergence} "
            f"samples={recommendation.get('sample_count')} successes={recommendation.get('successes')} "
            f"failures={recommendation.get('failures')}"
        )
    text = "\n".join(lines)
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return text[: max_chars - 3] + "..."


# Names used by small callers and by the operator-facing design language.
mine = mine_completed_lineages
mine_search_patterns = mine_completed_lineages
mine_completed_ledger_prefixes = mine_completed_lineages
load_report = load_report_artifact
render_summary = render_derivation_summary


__all__ = [
    "REPORT_VERSION", "SearchPatternError", "PatternInputError", "PatternLedgerCorrupt",
    "PatternPartialLedger", "PatternActiveRun", "PatternArtifactError", "PatternIdentityMismatch",
    "PatternAmbiguousLineage", "PatternInsufficientEvidence", "LedgerCorrupt", "PartialLedger",
    "ActiveRun", "ArtifactIdentityMismatch", "AmbiguousLineage", "SearchPatternReport",
    "mine_completed_lineages", "mine_search_patterns", "mine_completed_ledger_prefixes", "mine",
    "load_report_artifact", "load_report", "render_derivation_summary", "render_summary",
]
