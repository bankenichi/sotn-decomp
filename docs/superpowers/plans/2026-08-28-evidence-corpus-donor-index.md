# Evidence Corpus and Donor Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a shadow-gated, read-only evidence corpus and one immutable cross-version donor index whose compiler-bound hypotheses, stable lesson citations, typed refusals, and bounded semantic queries can feed ordinary search lanes without becoming a second source of truth.

**Architecture:** A corpus builder consumes exact `ScoreVector` taxonomy, content-addressed lesson citations, existing `DraftLandedObservation` and `CompilerIdiomObservation` records, and `SearchPatternReport` output from completed ledger prefixes. A donor-index builder archives semantic `DonorEvidence` for exactly pinned US, HD, PSPEU, and Saturn revisions in a generation bound to every revision, indexer, configuration, signature, schema, and shadow identity. Query results remain typed, bounded, and deterministic; an adapter hands target-context-rendered candidates to the existing lane and coordinator APIs while donor bytes, registers, relocations, and branch displacements stay out of the candidate.

**Tech Stack:** Python 3 frozen dataclasses and explicit callable contracts, `automation/search_types.py`, `automation/compiler_idioms.py`, `automation/search_patterns.py`, `automation/search_lanes.py`, `automation/search_archive.py`, `automation/search_recovery.py`, `automation/search_coordinator.py`, canonical JSON and SHA-256 identities, temporary-directory fixtures, and focused `sotn-cmd run_automation` self-tests. No new dependency, provider, queue writer, source writer, or build path is introduced.

**Spec:** `docs/superpowers/specs/2026-08-28-instrumented-search-supplement-design.md`, with the coordinator, archive, ledger, scorer, lane, recovery, and Task 9.3 and 9.5 contracts in `docs/superpowers/specs/2026-08-26-instrumented-search-system-design.md` and `docs/superpowers/specs/2026-08-26-instrumented-search-system-implementation-plan.md`.

## Global Constraints

- Complete and validate Tasks 8.1, 8.2, and 8.3 integration work before enabling the corpus or donor index. The first permitted runtime is one read-only record shadow. The second is a bounded read-only multi-record shadow.
- The Task 8.2 integration runtime supplies the only canonical integration receipt and validator. This plan imports that receipt and never defines `ShadowGateReceipt`, a second gate, a wrapper validator, or a parallel fixture.
- No queue/source/build changes.
- No implicit queue fallback or live subset drift.
- The frozen run manifest is the only scope authority. `subset_identity` is the canonical hash of sorted selected IDs, and `queue_evidence_identity` remains a separate scheduler-owned evidence identity.
- Corpus and donor artifacts retain the canonical receipt identity and complete gate binding: `manifest_artifact_identity`, `subset_identity`, `queue_evidence_identity`, `selected_lanes`, `coordinator_identity`, and `connector_identity`. Copying only a gate hash is insufficient.
- The scheduler alone writes queue state, the coordinator alone owns task identity, budgets, receipts, and ledger events, and the archive alone owns immutable artifact bytes.
- Workers and evidence producers return typed proposals or refusals. They do not edit `src/`, the live queue, an active manifest, or an existing archive generation.
- Every source, target, object, patch, score, mismatch, `FirstDivergence`, compiler, tool, evaluator, configuration, revision, indexer, signature, schema, shadow, and fixture identity is content-addressed.
- Source paths, timestamps, filesystem order, commit adjacency, abbreviated revisions, and filenames cannot establish ancestry, success, compatibility, or ordering.
- Preserve the exact scorer taxonomy: compile status, stack, register allocation, reordering, insertion, deletion, explicit weights, weighted total, instruction counts, object identity, mismatch signature, and `FirstDivergence`.
- A lower scalar score is reusable only with identical scorer, weights, compiler, tool, evaluator, configuration, target, and candidate identities.
- Promotion requires a compiler-bound measured strictly better full score vector or an exact target object or checksum identity. Similarity, a score copied from a donor, and a commit relationship are insufficient.
- A running, partial, or aborted ledger can remain diagnostic evidence but cannot produce a corpus hypothesis or donor index entry.
- `MATCHING-LESSONS.md` citations bind the full source content hash and exact line span. A changed source revision creates a new citation identity and never moves an old span silently.
- The §2 absent-masking rule is retained as explicit negative evidence about absent `andi $aN, 0xff` and `andi $aN, 0xffff` before argument use. It is not inferred from a copied excerpt.
- The donor index contains semantic evidence only. US, HD, PSPEU, and Saturn version-specific bytes, register allocations, relocations, and branch displacements are never copied into another version.
- A donor generation requires one exact pinned revision for each canonical version label `us`, `hd`, `pspeu`, and `saturn`. Any bound identity change creates a new immutable generation.
- Donor queries are bounded and deterministic in this order: exact symbol and version-aware path, instruction signature, CFG signature, then dataflow signature. Ties use immutable evidence identities, never path or modification-time order.
- The donor index is built once per generation. Query code receives only an immutable generation and never rescans a provider or source tree for an individual recipient.
- Donor provenance is carried by immutable `DonorIndexEntry` and `DonorQueryHit` references. Query code never mutates `DonorEvidence.metadata` or overwrites a scanner `donor_id` with an entry, revision, or generation identity.
- Ambiguous, incompatible, stale, corrupt, missing, or changed inputs produce typed receipts and no guessed result. Refusal evidence is retained in the corpus.
- Compatible same-rank claims from distinct pinned versions may be returned together up to the query limit. Ambiguity is reserved for conflicting indistinguishable claims, never for compatible cross-version support.
- Pattern groups bind compiler, configuration, schema, scorer algorithm, exact lane tool, recipient, target, and evaluator identities. Incompatible completed runs remain separate groups, and missing historical evaluator identity is diagnostic or refusal evidence only.
- The corpus and donor index are gated after integration shadow evidence and reuse `compiler_idioms`, `search_patterns`, `search_lanes`, `search_archive`, `search_recovery`, `search_coordinator`, and `search_types`; no parallel manifest, ledger, candidate, archive, scorer, or queue truth is permitted.
- No speculative m2c provider or tuner work is part of this plan. Data-segment search remains deferred under roadmap item #277.
- Root owns integration checks, any existing-module edits, explicit staging, commits, roadmap outcome, builds, oracle verification, queue work, and pushes. Workers do not run git, builds, queue writers, source writers, or connector edits.
- Do not add an em dash or emoji to code, comments, fixtures, or documentation.

---

## File Responsibility Map

Create these implementation and focused test files:

- `automation/search_evidence_corpus.py`: consumer of the imported canonical Task 8.2 receipt, stable lesson citations, exact scorer taxonomy envelopes, promotion/refusal records, recurring completed-lineage hypotheses, and one immutable corpus-generation artifact.
- `automation/test_search_evidence_corpus.py`: canonical gate loading, §2 absent-masking citation, scorer identity, draft-landed promotion, negative/refusal evidence, recurring hypothesis, deterministic generation, archive collision, and read-only tests.
- `automation/search_donor_index.py`: pinned four-version revision set, generation binding, semantic index records, content-addressed generation publication, bounded query hierarchy, stale/ambiguous/incompatible receipts, and the lane adapter.
- `automation/test_search_donor_index.py`: four-version generation, identity changes, archive verification, no-rescan accounting, deterministic query order, typed query receipts, target-context rendering, and coordinator handoff tests.

Make only these narrow integration extensions:

- `automation/search_patterns.py`: expose a frozen `CompletedLineageContext` projection through the existing `_load_completed_ledger` validator, bind compiler/config/schema/scorer, exact lane-tool, recipient-target, and evaluator identities, and add those identities to each recommendation key and payload so incompatible `FirstDivergence` groups cannot merge.
- `automation/test_search_patterns.py`: assert the new scorer identity field and completed-context projection, including active and partial ledger refusals.
- `automation/search_lanes.py`: when an explicit indexed-donor callback returns a `candidates` mapping, route it through `_discovery_from_values` before the structural-donor path. Keep the existing one-argument callback binding and read-only checks unchanged.
- `automation/test_search_lanes.py`: assert that a target-context candidate mapping reaches `LaneOutcome`, while donor evidence with no target renderer produces a typed refusal and never copies donor body text.

Do not edit `automation/search_types.py`, `automation/compiler_idioms.py`, `automation/search_archive.py`, `automation/search_recovery.py`, `automation/search_coordinator.py`, `run_selftests.py`, connector surfaces, `src/`, the live queue, or existing operational documents in this plan. The listed existing modules are consumed through their current typed APIs; the two narrow extensions above expose existing validated data rather than creating a second authority.

## Shared Exact Interfaces

The following names, fields, status values, and call shapes are the contract for every task. Frozen records must validate all hash, ID, path, version, and collection invariants in `__post_init__`, serialize with existing `canonical_json`, and derive their IDs from their complete immutable payload.

```python
class EvidenceCorpusError(RuntimeError):
    """Base error for corpus and shadow input failures."""

class LessonCitationError(EvidenceCorpusError):
    """A lesson source hash or review span does not verify."""

class EvidenceIdentityMismatch(EvidenceCorpusError):
    """A corpus input identity disagrees with its immutable content."""

class DonorIndexError(RuntimeError):
    """Base error for donor-index input and generation failures."""

class DonorIndexInputError(DonorIndexError):
    """A donor index input is incomplete, unsafe, or malformed."""

class DonorRevisionSetError(DonorIndexInputError):
    """The four-version pinned revision set is not complete and unique."""

class DonorIndexIdentityMismatch(DonorIndexInputError):
    """An indexed identity or immutable entry payload disagrees."""

class PatternMissingEvaluatorIdentity(PatternInputError):
    """A completed ledger has no manifest-bound evaluator identity."""

@dataclass(frozen=True)
class AbsenceMaskingClaim:
    opcode: str
    masks: tuple[str, ...]
    scope: str

@dataclass(frozen=True)
class LessonCitation:
    citation_id: str
    source: ArtifactRef
    section: str
    line_start: int
    line_end: int
    span_identity: str
    rule_id: str
    absence_masking: AbsenceMaskingClaim | None

@dataclass(frozen=True)
class ScorerTaxonomy:
    taxonomy_id: str
    before: ScoreVector
    after: ScoreVector
    evaluator_identity: str
    target_identity: str

    def identity_payload(self) -> Mapping[str, Any]:
        return {
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "evaluator_identity": self.evaluator_identity,
            "target_identity": self.target_identity,
        }

    def to_dict(self) -> Mapping[str, Any]:
        return {"taxonomy_id": self.taxonomy_id, **self.identity_payload()}

# `IntegrationGateReceipt` and `IntegrationGateError` are descriptive names
# for the canonical Task 8.2 type and refusal. They are imported from that
# integration runtime; this plan does not define a local receipt, validator,
# wrapper, or fixture. The canonical receipt's required consumer fields are
# `gate_id` (the receipt identity), its archived `receipt_artifact`,
# `manifest_artifact_identity`, `subset_identity`, `queue_evidence_identity`,
# `selected_lanes`, `coordinator_identity`, `connector_identity`,
# `execution_mode`, and `multi_record`. Consumers retain the complete receipt
# payload and verify the archived receipt artifact before using any evidence.

@dataclass(frozen=True)
class EvidenceRefusalReceipt:
    receipt_id: str
    operation: str
    reason_code: str
    input_identities: tuple[str, ...]
    observed_identities: tuple[str, ...]
    new_generation_required: bool

@dataclass(frozen=True)
class CorpusEvidence:
    evidence_id: str
    kind: str
    outcome: str
    recipient_id: str | None
    compiler_identity: str | None
    tool_identity: str | None
    target_identity: str | None
    evaluator_identity: str | None
    config_identity: str | None
    scorer: ScorerTaxonomy | None
    citations: tuple[LessonCitation, ...]
    draft_landed: tuple[DraftLandedObservation, ...]
    idiom: CompilerIdiomObservation | None
    first_divergence: FirstDivergence | None
    support_identities: tuple[str, ...]
    reason_code: str | None

@dataclass(frozen=True)
class PromotionAccepted:
    observation: CompilerIdiomObservation
    evidence: CorpusEvidence

@dataclass(frozen=True)
class PromotionRefused:
    receipt: EvidenceRefusalReceipt
    evidence: CorpusEvidence

@dataclass(frozen=True)
class CorpusGeneration:
    generation_id: str
    schema_identity: str
    integration_gate: IntegrationGateReceipt
    integration_gate_id: str
    manifest_artifact_identity: str
    subset_identity: str
    queue_evidence_identity: str
    selected_lanes: tuple[str, ...]
    coordinator_identity: str
    connector_identity: str
    source_identities: tuple[str, ...]
    entries: tuple[CorpusEvidence, ...]
    artifact: ArtifactRef

@dataclass(frozen=True)
class DonorRevision:
    version: str
    revision: str
    source_artifact: ArtifactRef

@dataclass(frozen=True)
class DonorIndexBinding:
    integration_gate: IntegrationGateReceipt
    integration_gate_id: str
    manifest_artifact_identity: str
    subset_identity: str
    queue_evidence_identity: str
    selected_lanes: tuple[str, ...]
    coordinator_identity: str
    connector_identity: str
    revision_set_identity: str
    indexer_identity: str
    indexer_source_identity: str
    config_identity: str
    signature_identity: str
    schema_identity: str
    generation_ordinal: int

@dataclass(frozen=True)
class DonorIndexEntry:
    entry_id: str
    revision: DonorRevision
    evidence: DonorEvidence

@dataclass(frozen=True)
class DonorIndexGeneration:
    generation_id: str
    binding: DonorIndexBinding
    revisions: tuple[DonorRevision, ...]
    entries: tuple[DonorIndexEntry, ...]
    artifact: ArtifactRef

@dataclass(frozen=True)
class DonorQuery:
    recipient_id: str
    version: str | None
    source_path: str | None
    symbol: str | None
    instruction_signature: str | None
    cfg_signature: str | None
    dataflow_signature: str | None
    compiler_identity: str
    config_identity: str
    limit: int

    def identity_payload(self) -> Mapping[str, Any]:
        return {
            "protocol": "donor-query-v1",
            "recipient_id": self.recipient_id,
            "version": self.version,
            "source_path": self.source_path,
            "symbol": self.symbol,
            "instruction_signature": self.instruction_signature,
            "cfg_signature": self.cfg_signature,
            "dataflow_signature": self.dataflow_signature,
            "compiler_identity": self.compiler_identity,
            "config_identity": self.config_identity,
            "limit": self.limit,
        }

    @property
    def query_identity(self) -> str:
        return hash_canonical(self.identity_payload())

@dataclass(frozen=True)
class DonorAmbiguityReceipt:
    receipt_id: str
    query_identity: str
    generation_id: str
    entry_ids: tuple[str, ...]
    reason_code: str

@dataclass(frozen=True)
class DonorIncompatibilityReceipt:
    receipt_id: str
    query_identity: str
    generation_id: str
    entry_ids: tuple[str, ...]
    reasons: tuple[str, ...]

@dataclass(frozen=True)
class DonorStaleReceipt:
    receipt_id: str
    query_identity: str
    generation_id: str
    expected_binding: DonorIndexBinding
    observed_binding: DonorIndexBinding

@dataclass(frozen=True)
class DonorQueryResult:
    status: str
    query_identity: str
    generation_id: str
    hits: tuple[DonorQueryHit, ...]
    donors: tuple[DonorEvidence, ...]
    receipt: DonorAmbiguityReceipt | DonorIncompatibilityReceipt | DonorStaleReceipt | None
    provenance_artifact: ArtifactRef
```

Exact function signatures:

- Canonical Task 8.2 validator: the implementation imports the validator and descriptive aliases `IntegrationGateReceipt` and `IntegrationGateError` from the integration runtime selected by Task 8.2. This plan does not select a second import path or define a wrapper validator.
- `make_lesson_citation(source: ArtifactRef, source_bytes: bytes, *, section: str, line_start: int, line_end: int, rule_id: str, absence_masking: AbsenceMaskingClaim | None = None) -> LessonCitation`
- `verify_lesson_citation(citation: LessonCitation, source_bytes: bytes) -> None`
- `make_scorer_taxonomy(before: ScoreVector, after: ScoreVector, *, evaluator_identity: str, target_identity: str) -> ScorerTaxonomy`
- `scorer_taxonomy_identity_payload(taxonomy: ScorerTaxonomy) -> Mapping[str, Any]`
- `promote_draft_landed(pair: DraftLandedObservation, before: ScoreVector, after: ScoreVector, *, evaluator_identity: str, target_identity: str, target_object_hash: str | None = None, target_checksum: str | None = None) -> PromotionAccepted | PromotionRefused`
- `collect_recurring_first_divergence(report: SearchPatternReport, contexts: Sequence[CompletedLineageContext | CompletedLineageDiagnostic], *, min_independent_lineages: int = 2) -> tuple[CorpusEvidence, ...]`
- `build_corpus_generation(entries: Iterable[CorpusEvidence], *, integration_gate: IntegrationGateReceipt, schema_identity: str, archive: ContentAddressedArchive) -> CorpusGeneration`
- `make_donor_binding(revisions: Sequence[DonorRevision], *, integration_gate: IntegrationGateReceipt, indexer_identity: str, indexer_source_identity: str, config_identity: str, signature_identity: str, schema_identity: str, generation_ordinal: int) -> DonorIndexBinding`
- `build_donor_index(revisions: Sequence[DonorRevision], *, integration_gate: IntegrationGateReceipt, scan_revision: Callable[[DonorRevision], Sequence[DonorEvidence]], indexer_identity: str, indexer_source_identity: str, config_identity: str, signature_identity: str, schema_identity: str, generation_ordinal: int, archive: ContentAddressedArchive) -> DonorIndexGeneration`
- `query_donor_index(index: DonorIndexGeneration, query: DonorQuery, *, expected_binding: DonorIndexBinding) -> DonorQueryResult`
- `indexed_lane_adapter(index: DonorIndexGeneration, *, expected_binding: DonorIndexBinding, query_for: Callable[[Recipient], DonorQuery], render_target_context: Callable[[Recipient, tuple[DonorEvidence, ...]], LaneCandidate | Sequence[LaneCandidate]]) -> Callable[[Recipient], Mapping[str, Any]]`
- `make_donor_query(*, recipient_id: str, version: str | None, source_path: str | None, symbol: str | None, instruction_signature: str | None, cfg_signature: str | None, dataflow_signature: str | None, compiler_identity: str, config_identity: str, limit: int) -> DonorQuery`

`EVALUATOR_TOOL_KEY` is imported from the Task 8.2 manifest contract. Examples spell its current canonical value as `"search_evaluator"`; the implementation must not define a local fallback or treat `"full_oracle"` as an evaluator key.

`DonorQueryHit` is the immutable query reference returned with every ranked
result. It is not a replacement for `DonorIndexEntry` and carries the
generation identity that surrounds that entry:

```python
@dataclass(frozen=True)
class DonorQueryHit:
    rank: int
    match_kind: str
    claim_identity: str
    entry: DonorIndexEntry
    generation_id: str
```

The query implementation uses `tuple[DonorQueryHit, ...]` and returns the
original immutable `DonorEvidence` values in `donors`; it never mutates a
`DonorEvidence`, appends generation metadata to its `metadata`, or substitutes
an `entry_id` for the scanner's `donor_id`. `DonorIndexEntry.revision` is the
full `DonorRevision`, so each hit retains entry, pinned revision, and generation
provenance. `DonorQueryResult.provenance_artifact` is always the verified
immutable generation artifact, including for `empty`, `ambiguous`,
`incompatible`, and `stale` results. A lane adapter may pass only the original
evidence to the renderer, while its returned provenance records query
identity, hit entry IDs, pinned revision identities, and the generation
artifact identity.

The four query ranks are fixed and named: `exact_symbol_path=0`,
`instruction_shape=1`, `cfg=2`, and `dataflow=3`. A `DonorQueryHit.rank` must
match its `match_kind` in this table. Compatible hits at the best rank are
grouped by semantic `claim_identity`; equivalent claims from distinct pinned
versions are all retained up to `limit`, while more than one distinct claim at
that rank returns `DonorAmbiguityReceipt` with sorted `entry_ids`.

`DonorIndexEntry.entry_id` is the canonical hash of the complete pinned
revision record and the scanner's complete immutable `DonorEvidence` payload.
`DonorQueryHit.claim_identity` deliberately excludes donor ID, version,
revision, source artifact and generation provenance so compatible support from
different pinned versions can agree. It is the canonical hash of protocol
`donor-semantic-claim-v1`, recipient, symbol, generic signature, instruction,
CFG and dataflow signatures, declarations, semantic constants, structural
differences and compatibility. No implementation-defined subset or path-based
fallback may establish semantic equivalence.

`CompletedLineageContext` and its public loader are added to `automation/search_patterns.py`:

```python
@dataclass(frozen=True)
class CompletedLineageContext:
    ledger_identity: str
    run_id: str
    compiler_identity: str
    config_identity: str
    schema_identity: str
    scorer_algorithms: tuple[str, ...]
    lane_tool_identities: tuple[tuple[str, str], ...]
    recipient_target_identities: tuple[tuple[str, str], ...]
    evaluator_identity: str

@dataclass(frozen=True)
class CompletedLineageDiagnostic:
    ledger_identity: str
    run_id: str
    reason_code: str
    observed_identities: tuple[str, ...]
```

 The loader signature is `load_completed_lineage_contexts(ledgers: Any | Sequence[Any] | None = None, *, ledger_paths: Sequence[Any] | None = None, expected_ledger_identities: Mapping[str | int, str] | None = None) -> tuple[CompletedLineageContext | CompletedLineageDiagnostic, ...]`. It must use the existing `_load_completed_ledger` path and must never catch a provider or ledger `TypeError` as an alternate invocation shape. A completed ledger missing the manifest-bound reserved evaluator/scorer tool identity (written as `search_evaluator` in examples, with the exact key imported from the Task 8.2 manifest contract) yields `CompletedLineageDiagnostic(reason_code="missing_evaluator_identity")`, not a context eligible for promotion. The separate `full_oracle` tool identity records full build/checksum authority and cannot satisfy evaluator provenance. Other identity conflicts use typed pattern refusals and do not merge into a completed context.

## Test Fixture Helper Contract

The focused tests define these helpers once and reuse them across tasks. They
construct real typed records or load the canonical Task 8.2 archived receipt;
they never construct a local integration gate, inspect the live queue, read
filesystem ordering, or put revision or generation fields into
`DonorEvidence.metadata`.

The helpers have these exact signatures and responsibilities:

- `digest(label: str) -> str` returns `hash_bytes(label.encode("utf-8"))`.
- `fixture_gate(*, queue_evidence_identity: str = digest("queue-evidence"), execution_mode: str = "instrumented", multi_record: bool = True) -> IntegrationGateReceipt` loads and validates the canonical Task 8.2 archived receipt; altered identities select a separate archived fixture and never mutate a receipt in memory.
- `fixture_gate_with_corrupt_receipt_artifact() -> IntegrationGateReceipt` uses the Task 8.2 corruption fixture to return a receipt whose archived bytes or reference do not verify; it never creates a competing receipt type or validator.
- `fixture_manifest(record_ids: Sequence[str] = ("us:ST:fn",), lanes: Sequence[str] = ("cfg_dataflow",)) -> RunManifest` constructs a real manifest using `canonical_subset_identity`, canonical `LANES` order, selected lane tool hashes, the Task 8.2 reserved evaluator/scorer tool key (shown as `search_evaluator` below), and a separate `full_oracle` landing-authority tool identity.
- `fixture_score(*, total: int, compiler_identity: str, divergence: FirstDivergence | None = None, scorer_algorithm: str = "difflib") -> ScoreVector` returns a valid successful `ScoreVector` with all required components, weights, hashes, and instruction counts.
- `fixture_pair() -> DraftLandedObservation` returns a complete provenance-strict pair with a full landing commit identity, grouped patch, and endpoint artifacts.
- `fixture_pattern_report(recommendation: Mapping[str, Any]) -> SearchPatternReport` returns a content-addressed report whose recommendation carries every grouping identity declared in Task 2.
- `fixture_completed_ledger(root: Path, *, include_evaluator: bool = True, compiler_identity: str = digest("compiler"), config_identity: str = digest("config"), schema_identity: str = digest("schema"), lane: str = "cfg_dataflow", recipient_id: str = "us:ST:fn", target_identity: str = digest("target:us:ST:fn")) -> Path` writes a completed, artifact-verified ledger fixture with the requested manifest bindings; `include_evaluator=False` omits the reserved `search_evaluator` binding while retaining separate `full_oracle` authority, modeling historical evaluator loss without making the fixture promotion-eligible.
- `fixture_corpus_entries() -> tuple[CorpusEvidence, ...]` returns one valid entry for each declared corpus kind, including positive, negative, and refusal outcomes.
- `fixture_revisions(archive: ContentAddressedArchive) -> tuple[tuple[DonorRevision, ...], Mapping[str, ArtifactRef]]` publishes one source artifact for each canonical version and returns revisions in arbitrary order plus the source map.
- `fixture_index(root: Path, *, duplicate_symbol: bool = False, compatible_versions: Sequence[str] = ("us",), config_identity: str = digest("index-config")) -> tuple[DonorIndexGeneration, Any]` returns an index and state exposing its archive, revisions, scanner-call counter, and original scanner evidence objects.
- `fixture_query(*, recipient_id: str = "us:ST:fn", version: str | None = "us", source_path: str | None = None, symbol: str | None = "fn", instruction_signature: str | None = "ins:fn", cfg_signature: str | None = "cfg:fn", dataflow_signature: str | None = "flow:fn", compiler_identity: str = digest("compiler"), config_identity: str = digest("index-config"), limit: int = 8) -> DonorQuery` calls `make_donor_query` with every field.

`fixture_gate` delegates to the Task 8.2 receipt loader and canonical
validator. The `fixture_index` state object exposes the archive, pinned
revisions, scanner-call counter, and the original scanner `DonorEvidence`
objects so tests can prove that queries return immutable entry and hit
references without changing donor metadata or IDs. `fixture_query` always
calls `make_donor_query`, so no example hand-writes a partial query identity.

## Implementation Tasks

### Task 0: Consume the canonical Task 8.2 integration prerequisite

**Files:**

- Create: `automation/search_evidence_corpus.py`
- Test: `automation/test_search_evidence_corpus.py`

**Interfaces:**

- Consumes: the canonical Task 8.2 `IntegrationGateReceipt` and its archived receipt artifact, validated by the Task 8.2 canonical validator. The receipt must carry its canonical receipt identity, `subset_identity`, `queue_evidence_identity`, `selected_lanes`, manifest artifact identity, coordinator identity, and connector identity.
- Produces: no local gate type, validator, fixture, or recovery wrapper. Corpus and donor builders accept the imported receipt, call the canonical validator before reading evidence, and retain the complete receipt payload in their returned generation or binding.

- [x] **Step 1: Write the failing canonical-gate consumer tests.** Define the compact test helpers once in `automation/test_search_evidence_corpus.py` and reuse them in later corpus tests. `fixture_gate(...)` loads the archived one-record or bounded multi-record receipt produced by Task 8.2 and invokes that runtime's canonical validator; it never constructs a local dataclass. The manifest helper still constructs a real `RunManifest`, including an explicit empty subset when `record_ids=()`, and uses canonical subset identity rather than a hand-written hash.

```python
def digest(label: str) -> str:
    return hash_bytes(label.encode("utf-8"))

def fixture_manifest(record_ids=("us:ST:fn",), lanes=("cfg_dataflow",)) -> RunManifest:
    ids = tuple(record_ids)
    selected = tuple(lane for lane in LANES if lane in tuple(lanes))
    return RunManifest(
        run_id="run-fixture",
        created_at="2026-08-28T00:00:00+00:00",
        parent_run=None,
        queue_record_ids=ids,
        function_ids=ids,
        subset_identity=canonical_subset_identity(ids),
        queue_evidence_identity=digest("queue-evidence"),
        selected_lanes=selected,
        source_identity=digest("source"),
        target_identities={item: digest("target:" + item) for item in ids},
        compiler_identity=digest("compiler"),
        tool_identities={
            **{lane: digest("tool:" + lane) for lane in selected},
            EVALUATOR_TOOL_KEY: digest("search-evaluator"),
            "full_oracle": digest("full-oracle"),
        },
        config_identity=digest("config"),
        schema_identity=digest("schema"),
        run_seed=7,
        epoch_size=1,
        frontier_cap=8,
        coordinator_budget=Budget("tasks", 8, 0),
        lane_budgets={lane: Budget("tasks", 4, 0) for lane in selected},
        tier_order=TIER_ORDER,
    )

def test_missing_canonical_gate_is_refused(tmp_path):
    with pytest.raises(IntegrationGateError, match="integration gate"):
        build_corpus_generation(
            (),
            integration_gate=None,
            schema_identity=digest("schema"),
            archive=ContentAddressedArchive(tmp_path / "archive"),
        )

def test_changed_valid_gate_creates_a_distinct_generation(tmp_path):
    original = fixture_gate()
    altered = fixture_gate(queue_evidence_identity=digest("changed-queue-evidence"))
    archive = ContentAddressedArchive(tmp_path / "archive")
    first = build_corpus_generation((), integration_gate=original, schema_identity=digest("schema"), archive=archive)
    second = build_corpus_generation((), integration_gate=altered, schema_identity=digest("schema"), archive=archive)
    assert first.generation_id != second.generation_id

def test_corrupt_canonical_gate_artifact_is_refused(tmp_path):
    corrupt = fixture_gate_with_corrupt_receipt_artifact()
    with pytest.raises(IntegrationGateError, match="receipt artifact"):
        build_corpus_generation((), integration_gate=corrupt, schema_identity=digest("schema"), archive=ContentAddressedArchive(tmp_path / "archive"))

def test_generation_retains_complete_canonical_gate_provenance(tmp_path):
    gate = fixture_gate()
    archive = ContentAddressedArchive(tmp_path / "archive")
    generation = build_corpus_generation(
        (),
        integration_gate=gate,
        schema_identity=digest("schema"),
        archive=archive,
    )
    assert generation.integration_gate.to_dict() == gate.to_dict()
    assert generation.integration_gate_id == gate.gate_id
    assert generation.manifest_artifact_identity == gate.manifest_artifact_identity
    assert generation.subset_identity == gate.subset_identity
    assert generation.queue_evidence_identity == gate.queue_evidence_identity
    assert generation.selected_lanes == gate.selected_lanes
    assert generation.coordinator_identity == gate.coordinator_identity
    assert generation.connector_identity == gate.connector_identity
    payload = json.loads(archive.verify(generation.artifact))
    assert payload["integration_gate"]["gate_id"] == gate.gate_id
    assert payload["integration_gate"]["receipt_artifact"] == gate.receipt_artifact.to_dict()
    assert payload["integration_gate"]["manifest_artifact_identity"] == gate.manifest_artifact_identity
    assert payload["integration_gate"]["subset_identity"] == gate.subset_identity
    assert payload["integration_gate"]["queue_evidence_identity"] == gate.queue_evidence_identity
    assert tuple(payload["integration_gate"]["selected_lanes"]) == gate.selected_lanes
    assert payload["integration_gate"]["coordinator_identity"] == gate.coordinator_identity
    assert payload["integration_gate"]["connector_identity"] == gate.connector_identity
```

- [x] **Step 2: Run the focused failure through the repository connector.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_evidence_corpus.py --jobs 1
```

Expected result before implementation: the focused module fails during import because `automation.search_evidence_corpus` and its canonical-gate consumer are absent.

- [x] **Step 3: Implement canonical-gate consumption.** Import the Task 8.2 receipt and refusal under the descriptive aliases `IntegrationGateReceipt` and `IntegrationGateError`, call the canonical validator exactly once before consuming any corpus or donor input, and preserve the complete validated receipt object and validator-verified archived receipt reference in every returned generation or binding. The canonical validator decides whether the receipt is the permitted one-record smoke or bounded multi-record run, and whether it is missing, changed, or otherwise invalid. Do not call `recover_run`, inspect queue state, reconstruct ledger identity, or derive a second gate identity here. The concrete Task 8.2 import path, validator name, and archived-artifact accessor remain owned by that runtime; this plan consumes them and does not wrap or redefine them.

- [x] **Step 4: Run the canonical-gate consumer tests and verify positive provenance.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_evidence_corpus.py --jobs 1
```

Expected result: the focused suite passes, including a validated canonical receipt whose complete serialized payload and archived receipt artifact are retained byte-for-byte in corpus and donor products. Assertions explicitly cover receipt identity, `subset_identity`, `queue_evidence_identity`, selected lanes, manifest artifact identity, coordinator identity, and connector identity.

- [x] **Step 5: Stop for the root-only commit boundary.** Root may commit only `automation/search_evidence_corpus.py` and `automation/test_search_evidence_corpus.py` with message `feat: consume canonical integration evidence`. The worker does not commit, build, inspect live queue state, or edit source.

### Task 1: Add stable lesson citations and exact scorer taxonomy

**Files:**

- Modify: `automation/search_evidence_corpus.py`
- Modify: `automation/test_search_evidence_corpus.py`

**Interfaces:**

- Consumes: existing `ArtifactRef`, `ScoreVector`, `FirstDivergence`, `hash_bytes`, `hash_canonical`, and `canonical_bytes`.
- Produces: `AbsenceMaskingClaim`, `LessonCitation`, `make_lesson_citation`, `verify_lesson_citation`, `ScorerTaxonomy`, and `make_scorer_taxonomy`.

- [x] **Step 1: Write the failing §2 and scorer identity tests.** The source artifact must bind the complete `MATCHING-LESSONS.md` bytes. The citation stores no copied prose and explicitly records the absent narrowing-mask claim.

```python
def test_section_two_absent_masking_is_span_bound():
    source_bytes = Path("MATCHING-LESSONS.md").read_bytes()
    source = ArtifactRef(
        hash_bytes(source_bytes),
        "sources/MATCHING-LESSONS.md",
        "text/markdown",
        len(source_bytes),
    )
    citation = make_lesson_citation(
        source,
        source_bytes,
        section="§2",
        line_start=146,
        line_end=178,
        rule_id="argument-width.absent-andi",
        absence_masking=AbsenceMaskingClaim(
            opcode="andi",
            masks=("0xff", "0xffff"),
            scope="argument-use",
        ),
    )
    verify_lesson_citation(citation, source_bytes)
    lines = source_bytes.splitlines(keepends=True)
    assert citation.span_identity == hash_bytes(b"".join(lines[145:178]))
    assert citation.absence_masking == AbsenceMaskingClaim("andi", ("0xff", "0xffff"), "argument-use")
    assert "excerpt" not in citation.to_dict()

def test_changed_lesson_bytes_are_refused():
    source_bytes = Path("MATCHING-LESSONS.md").read_bytes()
    source = ArtifactRef(hash_bytes(source_bytes), "sources/MATCHING-LESSONS.md", "text/markdown", len(source_bytes))
    citation = make_lesson_citation(source, source_bytes, section="§2", line_start=146, line_end=178, rule_id="argument-width.absent-andi", absence_masking=AbsenceMaskingClaim("andi", ("0xff", "0xffff"), "argument-use"))
    with pytest.raises(LessonCitationError, match="source content hash"):
        verify_lesson_citation(citation, source_bytes + b"\n")

def test_scorer_taxonomy_retains_components_weights_and_divergence():
    before = fixture_score(total=12, compiler_identity=digest("compiler"), divergence=FirstDivergence(1, 1, "lw", "addiu"))
    after = fixture_score(total=4, compiler_identity=digest("compiler"), divergence=None)
    taxonomy = make_scorer_taxonomy(before, after, evaluator_identity=digest("search-evaluator"), target_identity=digest("target"))
    assert taxonomy.before.components.to_dict() == before.components.to_dict()
    assert taxonomy.after.weights.to_dict() == after.weights.to_dict()
    assert taxonomy.before.first_divergence is not None
    assert taxonomy.taxonomy_id == hash_canonical(scorer_taxonomy_identity_payload(taxonomy))
    assert taxonomy.to_dict()["taxonomy_id"] == taxonomy.taxonomy_id
    assert taxonomy.to_dict()["before"] == before.to_dict()
    assert taxonomy.to_dict()["after"] == after.to_dict()
```

- [x] **Step 2: Run the focused failure.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_evidence_corpus.py --jobs 1
```

Expected result before implementation: the suite fails at import or reports that `make_lesson_citation` and `make_scorer_taxonomy` are missing.

- [x] **Step 3: Implement citation and taxonomy validation.** Decode no source excerpt into the record. Require `source.content_hash == hash_bytes(source_bytes)`, a relative path ending in `MATCHING-LESSONS.md`, positive one-based line bounds, and a span identity over exact UTF-8 lines including line endings. Require the §2 rule ID to carry `opcode == "andi"`, masks exactly `("0xff", "0xffff")`, and scope `"argument-use"`. Require taxonomy before and after vectors to have the same compiler and scorer algorithm, and validate evaluator and target hashes. Compute `taxonomy_id` from one canonical payload containing the complete `before.to_dict()`, complete `after.to_dict()`, `evaluator_identity`, and `target_identity`; `taxonomy_id` is a field name in the serialized envelope, not a second or circular identity property. `scorer_taxonomy_identity_payload` returns that payload and every mutation of any score, weight, compiler, scorer, evaluator, or target field changes the identity.

```python
span = b"".join(source_bytes.splitlines(keepends=True)[line_start - 1:line_end])
payload = {
    "source": source,
    "section": section,
    "line_start": line_start,
    "line_end": line_end,
    "span_identity": hash_bytes(span),
    "rule_id": rule_id,
    "absence_masking": absence_masking,
}
citation_id = hash_canonical(payload)
```

- [x] **Step 4: Run the citation and taxonomy tests.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_evidence_corpus.py --jobs 1
```

Expected result: the focused suite passes and changing one byte, one line bound, one scorer weight, one compiler identity, or one `FirstDivergence` changes or refuses the immutable identity.

- [x] **Step 5: Stop for the root-only commit boundary.** Root may commit only `automation/search_evidence_corpus.py` and `automation/test_search_evidence_corpus.py` with message `feat: bind evidence citations and scorer taxonomy`. The worker does not commit or modify `MATCHING-LESSONS.md`.

### Task 2: Expose completed-lineage scorer identity through the existing pattern miner

**Files:**

- Modify: `automation/search_patterns.py`
- Modify: `automation/test_search_patterns.py`

**Interfaces:**

- Consumes: the existing `_load_completed_ledger`, `SearchPatternReport`, `EvaluationEvent.after.scorer_algorithm`, `RunManifest`, its exact selected-lane tool bindings and recipient target identities, the manifest-bound reserved evaluator/scorer tool identity (`search_evaluator` in examples), the separate `full_oracle` landing-authority identity, and strict ledger/artifact validation.
- Produces: `CompletedLineageContext`, `CompletedLineageDiagnostic`, and `load_completed_lineage_contexts(...)`. Existing `mine_completed_lineages(...)` recommendations gain compiler, config, schema, scorer algorithm, exact lane-tool, recipient, target, and evaluator fields and include every one in their grouping identity.

- [x] **Step 1: Write the failing completed-context and scorer-separation tests.**

```python
def test_active_ledger_never_becomes_lineage_context(tmp_path):
    manifest = fixture_manifest()
    SearchCoordinator(tmp_path / "running", manifest)
    with pytest.raises(PatternActiveRun, match="active or resumable"):
        load_completed_lineage_contexts([tmp_path / "running"])

def test_first_divergence_recommendations_keep_scorer_identity():
    report = fixture_pattern_report(
        {
            "first_divergence": {"target_index": 2, "candidate_index": 3, "target_instruction": "lw", "candidate_instruction": "sw"},
            "lineage_ids": ["run-a:task-a", "run-b:task-b"],
            "source_ledgers": [digest("ledger-a"), digest("ledger-b")],
            "scorer_algorithm": "difflib",
            "compiler_identity": digest("compiler"),
            "config_identity": digest("config"),
            "schema_identity": digest("schema"),
            "lane_tool_identity": digest("tool:cfg_dataflow"),
            "recipient_id": "us:ST:fn",
            "target_identity": digest("target:us:ST:fn"),
            "evaluator_identity": digest("search-evaluator"),
        }
    )
    assert report.recommendations[0]["scorer_algorithm"] == "difflib"
    assert report.recommendations[0]["compiler_identity"] == digest("compiler")
    assert report.recommendations[0]["lane_tool_identity"] == digest("tool:cfg_dataflow")
    assert report.recommendations[0]["target_identity"] == digest("target:us:ST:fn")
    assert report.recommendations[0]["evaluator_identity"] == digest("search-evaluator")
    assert report.recommendations[0]["first_divergence"]["target_index"] == 2

def test_completed_context_binds_lane_target_and_evaluator(tmp_path):
    context = load_completed_lineage_contexts(
        [fixture_completed_ledger(tmp_path)]
    )[0]
    assert context.compiler_identity == digest("compiler")
    assert context.config_identity == digest("config")
    assert context.schema_identity == digest("schema")
    assert context.scorer_algorithms == ("difflib",)
    assert context.lane_tool_identities == (("cfg_dataflow", digest("tool:cfg_dataflow")),)
    assert context.recipient_target_identities == (("us:ST:fn", digest("target:us:ST:fn")),)
    assert context.evaluator_identity == digest("search-evaluator")

def test_missing_historical_evaluator_is_diagnostic(tmp_path):
    contexts = load_completed_lineage_contexts(
        [fixture_completed_ledger(tmp_path, include_evaluator=False)]
    )
    assert isinstance(contexts[0], CompletedLineageDiagnostic)
    assert contexts[0].reason_code == "missing_evaluator_identity"
```

- [x] **Step 2: Run the pattern-miner failure.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_patterns.py --jobs 1
```

Expected result before implementation: the focused suite fails because `load_completed_lineage_contexts` is not exported and generated recommendations have no `scorer_algorithm` field.

- [x] **Step 3: Implement the public projection without a second ledger parser.** Normalize the same accepted ledger input forms as `mine_completed_lineages`, call `_load_completed_ledger` once per input, reject duplicate identities, collect sorted unique `EvaluationEvent.after.scorer_algorithm` values, and expose manifest compiler, config, and schema identities. Derive `lane_tool_identities` from exactly `(lane, manifest.tool_identities[lane])` for each selected lane, `recipient_target_identities` from the exact manifest target map, and evaluator identity from required `manifest.tool_identities["search_evaluator"]` or the exact reserved evaluator key imported from the Task 8.2 contract. The separate `manifest.tool_identities["full_oracle"]` is retained as landing authority only and must never fill this field. If the evaluator binding is absent, return `CompletedLineageDiagnostic(reason_code="missing_evaluator_identity", observed_identities=(manifest.compiler_identity, manifest.config_identity, manifest.schema_identity, manifest.tool_identities.get("full_oracle", "")))` and never expose a promotion-eligible context. Add compiler, config, schema, scorer algorithm, lane-tool, recipient, target, and evaluator fields to `_lineage_key`, the grouped record, and each recommendation payload. Incompatible identity tuples remain separate before aggregation. Do not alter report source identity or write behavior.

```python
completed = tuple(_load_completed_ledger(value) for value in normalized)
contexts = []
for run in sorted(completed, key=lambda item: item.identity):
    evaluator = run.manifest.tool_identities.get(EVALUATOR_TOOL_KEY)
    if evaluator is None:
        contexts.append(CompletedLineageDiagnostic(
            ledger_identity=run.identity,
            run_id=run.manifest.run_id,
            reason_code="missing_evaluator_identity",
            observed_identities=(run.manifest.compiler_identity, run.manifest.config_identity),
        ))
        continue
    contexts.append(CompletedLineageContext(
        ledger_identity=run.identity,
        run_id=run.manifest.run_id,
        compiler_identity=run.manifest.compiler_identity,
        config_identity=run.manifest.config_identity,
        schema_identity=run.manifest.schema_identity,
        scorer_algorithms=tuple(sorted({
            event.payload.after.scorer_algorithm
            for event in run.events
            if event.event_type == "evaluation_completed"
        })),
        lane_tool_identities=tuple(sorted(
            (lane, run.manifest.tool_identities[lane])
            for lane in run.manifest.selected_lanes
        )),
        recipient_target_identities=tuple(sorted(run.manifest.target_identities.items())),
        evaluator_identity=evaluator,
    ))
return tuple(contexts)
```

- [x] **Step 4: Run the pattern tests.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_patterns.py --jobs 1
```

Expected result: the focused pattern suite passes, active and partial sources fail with their existing typed errors, and reversing ledger input order produces identical recommendation IDs and JSON bytes.

- [x] **Step 5: Stop for the root-only commit boundary.** Root may commit only `automation/search_patterns.py` and `automation/test_search_patterns.py` with message `feat: expose completed scorer lineage context`. The worker does not commit or modify a ledger.

### Task 3: Gate idiom promotion and recurring `FirstDivergence` evidence

**Files:**

- Modify: `automation/search_evidence_corpus.py`
- Modify: `automation/test_search_evidence_corpus.py`

**Interfaces:**

- Consumes: `DraftLandedObservation`, `make_idiom_observation`, `measure_improvement`, `CompilerIdiomObservation`, `ScorerTaxonomy`, `SearchPatternReport`, and `CompletedLineageContext`.
- Produces: `promote_draft_landed(...)`, `PromotionAccepted`, `PromotionRefused`, `EvidenceRefusalReceipt`, `CorpusEvidence`, and `collect_recurring_first_divergence(...)`.

- [x] **Step 1: Write refusal-first promotion and recurrence tests.** The accepted branch must prove the same compiler and scorer on both vectors and must retain the pair hash, grouped patch, evaluator, target, and measurement. The rejected branch becomes negative evidence rather than an idiom.

```python
def test_promotion_requires_compiler_bound_improvement():
    pair = fixture_pair()
    before = fixture_score(total=14, compiler_identity=pair.compiler_identity)
    after = fixture_score(total=7, compiler_identity=pair.compiler_identity)
    accepted = promote_draft_landed(
        pair,
        before,
        after,
        evaluator_identity=digest("search-evaluator"),
        target_identity=digest("target"),
        target_object_hash=digest("target-object"),
    )
    assert isinstance(accepted, PromotionAccepted)
    assert accepted.observation.measurement["improved"] is True
    assert pair.pair_hash in accepted.observation.supporting_pair_hashes

def test_worse_candidate_is_retained_as_negative_refusal_evidence():
    pair = fixture_pair()
    refused = promote_draft_landed(
        pair,
        fixture_score(total=7, compiler_identity=pair.compiler_identity),
        fixture_score(total=14, compiler_identity=pair.compiler_identity),
        evaluator_identity=digest("search-evaluator"),
        target_identity=digest("target"),
    )
    assert isinstance(refused, PromotionRefused)
    assert refused.receipt.reason_code == "no_measured_improvement"
    assert refused.evidence.kind == "negative"
    assert refused.evidence.outcome == "negative"

def test_recurring_first_divergence_needs_two_compatible_completed_lineages():
    first = FirstDivergence(2, 3, "lw", "sw")
    report = fixture_pattern_report({
        "first_divergence": first.to_dict(),
        "lineage_ids": ["run-a:task-a", "run-b:task-b"],
        "source_ledgers": [digest("ledger-a"), digest("ledger-b")],
        "scorer_algorithm": "difflib",
        "compiler_identity": digest("compiler"),
        "config_identity": digest("config"),
        "schema_identity": digest("schema"),
        "lane_tool_identity": digest("tool:cfg_dataflow"),
        "recipient_id": "us:ST:fn",
        "target_identity": digest("target:us:ST:fn"),
        "evaluator_identity": digest("search-evaluator"),
    })
    contexts = (
        CompletedLineageContext(
            ledger_identity=digest("ledger-a"),
            run_id="run-a",
            compiler_identity=digest("compiler"),
            config_identity=digest("config"),
            schema_identity=digest("schema"),
            scorer_algorithms=("difflib",),
            lane_tool_identities=(("cfg_dataflow", digest("tool:cfg_dataflow")),),
            recipient_target_identities=(("us:ST:fn", digest("target:us:ST:fn")),),
            evaluator_identity=digest("search-evaluator"),
        ),
        CompletedLineageContext(
            ledger_identity=digest("ledger-b"),
            run_id="run-b",
            compiler_identity=digest("compiler"),
            config_identity=digest("config"),
            schema_identity=digest("schema"),
            scorer_algorithms=("difflib",),
            lane_tool_identities=(("cfg_dataflow", digest("tool:cfg_dataflow")),),
            recipient_target_identities=(("us:ST:fn", digest("target:us:ST:fn")),),
            evaluator_identity=digest("search-evaluator"),
        ),
    )
    entries = collect_recurring_first_divergence(report, contexts)
    assert len(entries) == 1
    assert entries[0].first_divergence == first
    assert digest("ledger-a") in entries[0].support_identities
    assert entries[0].tool_identity == digest("tool:cfg_dataflow")
    assert entries[0].target_identity == digest("target:us:ST:fn")
    assert entries[0].evaluator_identity == digest("search-evaluator")

def test_missing_evaluator_lineage_is_typed_refusal():
    first = FirstDivergence(2, 3, "lw", "sw")
    report = fixture_pattern_report({
        "first_divergence": first.to_dict(),
        "lineage_ids": ["run-a:task-a", "run-b:task-b"],
        "source_ledgers": [digest("ledger-a"), digest("ledger-b")],
        "scorer_algorithm": "difflib",
        "compiler_identity": digest("compiler"),
        "config_identity": digest("config"),
        "schema_identity": digest("schema"),
        "lane_tool_identity": digest("tool:cfg_dataflow"),
        "recipient_id": "us:ST:fn",
        "target_identity": digest("target:us:ST:fn"),
        "evaluator_identity": digest("search-evaluator"),
    })
    diagnostic = CompletedLineageDiagnostic(
        ledger_identity=digest("ledger-a"),
        run_id="run-a",
        reason_code="missing_evaluator_identity",
        observed_identities=(
            digest("compiler"),
            digest("config"),
            digest("schema"),
            digest("tool:cfg_dataflow"),
            digest("target:us:ST:fn"),
        ),
    )
    context = CompletedLineageContext(
        ledger_identity=digest("ledger-b"),
        run_id="run-b",
        compiler_identity=digest("compiler"),
        config_identity=digest("config"),
        schema_identity=digest("schema"),
        scorer_algorithms=("difflib",),
        lane_tool_identities=(("cfg_dataflow", digest("tool:cfg_dataflow")),),
        recipient_target_identities=(("us:ST:fn", digest("target:us:ST:fn")),),
        evaluator_identity=digest("search-evaluator"),
    )
    entries = collect_recurring_first_divergence(report, (diagnostic, context))
    assert len(entries) == 1
    assert entries[0].outcome == "refused"
    assert entries[0].reason_code == "missing_evaluator_identity"
    assert entries[0].first_divergence == first
    assert entries[0].tool_identity == digest("tool:cfg_dataflow")
    assert entries[0].target_identity == digest("target:us:ST:fn")
    assert entries[0].evaluator_identity is None
```

- [x] **Step 2: Run the promotion failure.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_evidence_corpus.py --jobs 1
```

Expected result before implementation: the suite fails because `promote_draft_landed` and `collect_recurring_first_divergence` are absent.

- [x] **Step 3: Implement promotion and recurrence.** For promotion, require recipient, draft, landed, full landing commit, patch, compiler, scorer, evaluator, target, and artifact identities from the existing observation. Call `measure_improvement` exactly once with the same before and after scorer boundary, replace the pair measurement with that result, and call `make_idiom_observation` only on a proven improvement or exact target object. On mismatch or no improvement, emit an `EvidenceRefusalReceipt` and a negative `CorpusEvidence` entry. For recurrence, accept only recommendation source ledgers present in the completed contexts, at least two distinct ledger and lineage identities, and one compatible tuple of compiler, config, schema, scorer algorithm, exact lane tool, recipient, target, and evaluator identities. Bind the report artifact identity to the resulting support set and retain target, lane-tool, evaluator, `FirstDivergence`, ledger, and lineage provenance on every positive entry. A `CompletedLineageDiagnostic`, including `missing_evaluator_identity`, yields typed refusal evidence with any observed target and tool provenance, never a promotion-grade hypothesis. Incompatible runs are separated before aggregation rather than combined under a partial key.

```python
measurement = measure_improvement(
    before,
    after,
    target_object_hash=target_object_hash,
    target_checksum=target_checksum,
    evaluator_identity=evaluator_identity,
    evidence=pair.evidence,
)
if measurement is None:
    return refusal("no_measured_improvement", (pair.pair_hash, target_identity))
measured_pair = replace(pair, measurement=measurement.to_dict())
observation = make_idiom_observation(measured_pair)
```

- [x] **Step 4: Run the promotion and recurrence tests.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_evidence_corpus.py --jobs 1
```

Expected result: the focused suite passes, one incompatible or single-lineage recommendation produces no positive corpus entry, and accepted observations retain exact pair and measurement identities.

- [x] **Step 5: Stop for the root-only commit boundary.** Root may commit only `automation/search_evidence_corpus.py` and `automation/test_search_evidence_corpus.py` with message `feat: gate compiler evidence promotion`. The worker does not invoke a compiler, build, queue writer, or source writer.

### Task 4: Publish one immutable evidence-corpus generation

**Files:**

- Modify: `automation/search_evidence_corpus.py`
- Modify: `automation/test_search_evidence_corpus.py`

**Interfaces:**

- Consumes: validated `CorpusEvidence` entries, the canonical `IntegrationGateReceipt`, `ContentAddressedArchive.put_json`, and a content-addressed schema identity.
- Produces: `CorpusGeneration` and `build_corpus_generation(entries, *, integration_gate, schema_identity, archive)`.

- [x] **Step 1: Write deterministic-generation and read-only tests.** Include scorer, §2 citation, accepted draft-landed idiom, recurring `FirstDivergence`, negative, and refusal entries. Reversing entry order must not change the generation or artifact bytes.

```python
def test_generation_is_content_addressed_and_order_independent(tmp_path):
    entries = fixture_corpus_entries()
    integration_gate = fixture_gate(multi_record=True)
    first = build_corpus_generation(
        entries,
        integration_gate=integration_gate,
        schema_identity=digest("corpus-schema"),
        archive=ContentAddressedArchive(tmp_path / "archive-a"),
    )
    second = build_corpus_generation(
        tuple(reversed(entries)),
        integration_gate=integration_gate,
        schema_identity=digest("corpus-schema"),
        archive=ContentAddressedArchive(tmp_path / "archive-b"),
    )
    assert first.generation_id == second.generation_id
    assert first.artifact.content_hash == second.artifact.content_hash
    assert {entry.kind for entry in first.entries} == {"scorer", "lesson", "draft_landed", "first_divergence", "negative", "refusal"}

def test_corpus_builder_does_not_mutate_input_files(tmp_path):
    source = tmp_path / "source.json"
    source.write_text('{"evidence":"fixed"}', encoding="utf-8")
    before = source.read_bytes()
    listing_before = tuple(sorted(item.name for item in tmp_path.iterdir()))
    build_corpus_generation(fixture_corpus_entries(), integration_gate=fixture_gate(multi_record=True), schema_identity=digest("schema"), archive=ContentAddressedArchive(tmp_path / "corpus"))
    assert source.read_bytes() == before
    assert tuple(sorted(item.name for item in tmp_path.iterdir() if item.name != "corpus")) == listing_before
```

- [x] **Step 2: Run the generation failure.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_evidence_corpus.py --jobs 1
```

Expected result before implementation: the suite fails because `build_corpus_generation` and `CorpusGeneration` are absent.

- [x] **Step 3: Implement canonical generation publication.** Reject a missing or invalid canonical integration receipt, duplicate evidence IDs with different payloads, invalid source identities, and entries whose discriminated fields do not match their `kind` and `outcome`. Verify the receipt's archived artifact before consuming entries. Sort entries by `evidence_id`, derive `source_identities` from citation, scorer, pair, report, refusal, and idiom support identities, build a canonical payload containing the complete receipt payload plus `integration_gate_id`, `manifest_artifact_identity`, `subset_identity`, `queue_evidence_identity`, `selected_lanes`, `coordinator_identity`, and `connector_identity`, and publish it through `ContentAddressedArchive.put_json(category="evidence_corpus", suffix=".json")`. Existing different bytes at the same content identity must raise the archive collision error.

```python
ordered = tuple(sorted(unique_entries, key=lambda item: item.evidence_id))
gate_payload = integration_gate.to_dict()
payload = {
    "schema_identity": schema_identity,
    "integration_gate": gate_payload,
    "integration_gate_id": integration_gate.gate_id,
    "manifest_artifact_identity": integration_gate.manifest_artifact_identity,
    "subset_identity": integration_gate.subset_identity,
    "queue_evidence_identity": integration_gate.queue_evidence_identity,
    "selected_lanes": list(integration_gate.selected_lanes),
    "coordinator_identity": integration_gate.coordinator_identity,
    "connector_identity": integration_gate.connector_identity,
    "source_identities": list(source_identities),
    "entries": [item.to_dict() for item in ordered],
}
generation_id = hash_canonical(payload)
artifact = archive.put_json(payload, category="evidence_corpus", suffix=".json")
if artifact.content_hash != generation_id:
    raise EvidenceIdentityMismatch("corpus artifact identity differs from payload")
```

- [x] **Step 4: Run the corpus-generation tests.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_evidence_corpus.py --jobs 1
```

Expected result: the focused suite passes with identical replay IDs, preserved negative/refusal entries, and no writes outside the caller-owned archive root.

- [x] **Step 5: Stop for the root-only commit boundary.** Root may commit only `automation/search_evidence_corpus.py` and `automation/test_search_evidence_corpus.py` with message `feat: publish immutable evidence corpus`. The worker does not commit or publish a queue or source artifact.

### Task 5: Define and publish the four-version immutable donor generation

**Files:**

- Create: `automation/search_donor_index.py`
- Test: `automation/test_search_donor_index.py`

**Interfaces:**

- Consumes: the canonical `IntegrationGateReceipt`, existing `DonorEvidence`, `ArtifactRef`, `ContentAddressedArchive`, `validate_commit_identity`, `reject_unsafe_semantic_constant`, and exactly one `scan_revision(revision)` call for each pinned revision.
- Produces: `DonorRevision`, `DonorIndexBinding`, `DonorIndexEntry`, `DonorIndexGeneration`, `make_donor_binding`, and `build_donor_index`.

- [ ] **Step 1: Write the failing generation and identity-change tests.** Use an archive-owned source artifact for each version and a scanner that records invocation counts. Donor records carry `source=ArtifactRef`, `body=None`, symbols and signatures, declarations, and safe semantic constants.

```python
def test_generation_scans_each_pinned_version_once(tmp_path):
    archive = ContentAddressedArchive(tmp_path / "index")
    revisions, sources = fixture_revisions(archive)
    calls = Counter()

    def scan_revision(revision):
        calls[revision.version] += 1
        return (DonorEvidence(
            donor_id=digest("donor:" + revision.version),
            recipient_id="us:ST:fn",
            version=revision.version,
            source=sources[revision.version],
            match_kind="exact_symbol",
            signature="sig:fn",
            symbol="fn",
            instruction_signature="ins:fn",
            cfg_signature="cfg:fn",
            dataflow_signature="flow:fn",
            body=None,
            constants={"literal": 4},
            metadata={"fixture": "scanner"},
        ),)

    index = build_donor_index(
        revisions,
        integration_gate=fixture_gate(multi_record=True),
        scan_revision=scan_revision,
        indexer_identity=digest("indexer"),
        indexer_source_identity=digest("indexer-source"),
        config_identity=digest("index-config"),
        signature_identity=digest("signature"),
        schema_identity=digest("donor-schema"),
        generation_ordinal=1,
        archive=archive,
    )
    assert tuple(calls[version] for version in ("us", "hd", "pspeu", "saturn")) == (1, 1, 1, 1)
    assert all(entry.evidence.body is None for entry in index.entries)
    assert all(entry.evidence.metadata == {"fixture": "scanner"} for entry in index.entries)
    revision_by_version = {item.version: item for item in revisions}
    assert all(entry.revision == revision_by_version[entry.evidence.version] for entry in index.entries)

def test_changed_bound_identity_requires_new_generation(tmp_path):
    index_a, fixture = fixture_index(tmp_path, config_identity=digest("config-a"))
    index_b, _ = fixture_index(tmp_path / "second", config_identity=digest("config-b"))
    assert index_a.generation_id != index_b.generation_id
    assert index_a.artifact.content_hash != index_b.artifact.content_hash
```

- [ ] **Step 2: Run the donor-generation failure.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_donor_index.py --jobs 1
```

Expected result before implementation: the focused module fails during import because `automation.search_donor_index` and `DonorIndexGeneration` do not exist.

- [ ] **Step 3: Implement revision and entry validation.** Normalize version labels to `("us", "hd", "pspeu", "saturn")`, require one unique full 40- or 64-hex revision per label, and compute `revision_set_identity` from the complete ordered version, full revision, and source artifact set. Require the canonical gate identity and complete gate binding, plus every indexer, indexer-source, configuration, signature, schema, and ordinal identity. For each scanner result require matching version and revision object, an `ArtifactRef` source verified by `archive.verify`, no body bytes, no forbidden metadata keys `bytes`, `registers`, `relocations`, or `branch_displacements`, and safe constants through `reject_unsafe_semantic_constant`. Compute `entry_id` and semantic `claim_identity` from the exact payloads defined in Shared Exact Interfaces. Store provenance on the immutable `DonorIndexEntry.revision`, never in or over a scanner `DonorEvidence.metadata` mapping. Call the scanner directly once per revision and propagate its internal exceptions without arity retries.

```python
ordered_revisions = tuple(sorted(revisions, key=lambda item: DONOR_VERSIONS.index(item.version)))
if tuple(item.version for item in ordered_revisions) != DONOR_VERSIONS:
    raise DonorRevisionSetError("one pinned revision per US, HD, PSPEU, and Saturn is required")
records = []
for revision in ordered_revisions:
    for evidence in scan_revision(revision):
        if evidence.version != revision.version or not isinstance(evidence.source, ArtifactRef):
            raise DonorIndexIdentityMismatch("donor evidence does not match pinned revision")
        if evidence.body is not None:
            raise DonorIndexInputError("donor index cannot store version-specific body bytes")
        archive.verify(evidence.source)
        records.append(DonorIndexEntry.from_evidence(revision, evidence))
```

- [ ] **Step 4: Publish and replay the donor generation.** Sort entries by immutable `entry_id`, put a canonical payload under `donor_indexes` containing the complete integration receipt and flattened gate fields, every pinned revision and source artifact, indexer/config/signature/schema/ordinal binding, and every entry's immutable revision provenance, verify the artifact hash equals `generation_id`, and preserve the old generation when any binding changes.

```text
sotn-cmd run_automation run_selftests.py --only test_search_donor_index.py --jobs 1
```

Expected result: the focused suite passes, reversed revision input is canonicalized, all four versions are represented once, and changed receipt, manifest artifact, subset, queue evidence, selected lanes, coordinator, connector, revision, source artifact, indexer, indexer-source, configuration, signature, schema, or ordinal identities produce a distinct immutable generation.

- [ ] **Step 5: Stop for the root-only commit boundary.** Root may commit only `automation/search_donor_index.py` and `automation/test_search_donor_index.py` with message `feat: publish immutable four-version donor index`. The worker does not fetch, checkout, vendor, build, or modify any donor source.

### Task 6: Add bounded deterministic donor queries and typed receipts

**Files:**

- Modify: `automation/search_donor_index.py`
- Modify: `automation/test_search_donor_index.py`

**Interfaces:**

- Consumes: `DonorIndexGeneration`, `DonorIndexBinding`, immutable `DonorIndexEntry` values, `DonorEvidence`, and a `DonorQuery` with an explicit recipient, target compiler/config identities, at least one selector, and `1 <= limit <= 8`.
- Produces: `query_donor_index(...) -> DonorQueryResult`, with status values `matched`, `empty`, `ambiguous`, `incompatible`, and `stale`, plus `DonorAmbiguityReceipt`, `DonorIncompatibilityReceipt`, and `DonorStaleReceipt`.

- [ ] **Step 1: Write the failing query, tie, stale, and no-rescan tests.**

```python
def test_query_prefers_symbol_then_stops_without_rescanning(tmp_path):
    index, fixture = fixture_index(tmp_path)
    query = fixture_query(
        recipient_id="us:ST:fn",
        version="us",
        source_path=None,
        symbol="fn",
        instruction_signature="ins:other",
        cfg_signature="cfg:other",
        dataflow_signature="flow:other",
        compiler_identity=digest("compiler"),
        config_identity=digest("index-config"),
        limit=8,
    )
    calls_before = dict(fixture.scan_calls)
    result = query_donor_index(index, query, expected_binding=index.binding)
    again = query_donor_index(index, query, expected_binding=index.binding)
    assert result.status == "matched"
    assert result.hits[0].generation_id == index.generation_id
    assert result.hits[0].entry.evidence is result.donors[0]
    expected_revision = next(item for item in fixture.revisions if item.version == "us")
    assert result.hits[0].entry.revision == expected_revision
    assert result.donors[0].metadata == {"fixture": "scanner"}
    assert result.query_identity == again.query_identity
    assert dict(fixture.scan_calls) == calls_before

def test_query_identity_covers_every_field():
    base = fixture_query()
    mutations = {
        "recipient_id": "hd:ST:fn",
        "version": "hd",
        "source_path": "src/other.c",
        "symbol": "other",
        "instruction_signature": "ins:other",
        "cfg_signature": "cfg:other",
        "dataflow_signature": "flow:other",
        "compiler_identity": digest("other-compiler"),
        "config_identity": digest("other-config"),
        "limit": 7,
    }
    assert all(
        replace(base, **{field: value}).query_identity != base.query_identity
        for field, value in mutations.items()
    )

def test_compatible_same_rank_support_from_distinct_versions_is_bounded(tmp_path):
    index, fixture = fixture_index(tmp_path, compatible_versions=("us", "hd"))
    result = query_donor_index(
        index,
        fixture_query(version=None),
        expected_binding=index.binding,
    )
    assert result.status == "matched"
    assert len(result.hits) == 2
    assert {hit.entry.revision.version for hit in result.hits} == {"us", "hd"}
    assert len(result.hits) <= 8
    assert len({hit.claim_identity for hit in result.hits}) == 1
    assert tuple(hit.entry.evidence for hit in result.hits) == result.donors
    assert all(evidence.metadata == {"fixture": "scanner"} for evidence in fixture.original_evidence)

def test_equal_best_donors_return_ambiguity_receipt(tmp_path):
    index, _ = fixture_index(tmp_path, duplicate_symbol=True)
    result = query_donor_index(index, fixture_query(), expected_binding=index.binding)
    assert result.status == "ambiguous"
    assert isinstance(result.receipt, DonorAmbiguityReceipt)
    assert result.receipt.entry_ids == tuple(sorted(result.receipt.entry_ids))

def test_changed_revision_binding_returns_stale_receipt(tmp_path):
    index, fixture = fixture_index(tmp_path)
    changed = replace(fixture.revisions[0], source_artifact=fixture.archive.put_text("changed source"))
    expected = make_donor_binding(
        (changed, *fixture.revisions[1:]),
        integration_gate=index.binding.integration_gate,
        indexer_identity=index.binding.indexer_identity,
        indexer_source_identity=index.binding.indexer_source_identity,
        config_identity=index.binding.config_identity,
        signature_identity=index.binding.signature_identity,
        schema_identity=index.binding.schema_identity,
        generation_ordinal=2,
    )
    result = query_donor_index(index, fixture_query(), expected_binding=expected)
    assert result.status == "stale"
    assert isinstance(result.receipt, DonorStaleReceipt)
```

- [ ] **Step 2: Run the query failure.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_donor_index.py --jobs 1
```

Expected result before implementation: the focused suite fails because `DonorQuery`, `query_donor_index`, and the typed receipts are absent.

- [ ] **Step 3: Implement the query hierarchy without provider access.** Recompute the canonical identity from every `DonorQuery` field and validate the expected binding before looking at entries. Select compatible entries by exact symbol plus version and optional source path, then instruction, CFG, and dataflow signatures using the fixed rank table `exact_symbol_path=0`, `instruction_shape=1`, `cfg=2`, `dataflow=3`. Return `DonorQueryHit` values with the rank, match kind, semantic claim identity, immutable `DonorIndexEntry`, and generation identity. If no compatible entry remains but structural matches are incompatible, return `incompatible`; if the best rank contains conflicting distinct claim identities, return `ambiguous` with sorted entry IDs; otherwise return all compatible same-rank hits for one claim, including distinct pinned versions, bounded by `limit`, and sort by `(rank, entry_id)`. Return original immutable `DonorEvidence` references in `donors`, never mutate metadata or replace `donor_id`, and retain entry revision and generation provenance in hits and result artifact. A binding mismatch returns `stale` with old and expected bindings and never repairs the index.

```python
if expected_binding != index.binding:
    receipt = DonorStaleReceipt(
        receipt_id=hash_canonical({"query": query.query_identity, "expected": expected_binding.to_dict(), "observed": index.binding.to_dict()}),
        query_identity=query.query_identity,
        generation_id=index.generation_id,
        expected_binding=expected_binding,
        observed_binding=index.binding,
    )
    return DonorQueryResult(
        status="stale",
        query_identity=query.query_identity,
        generation_id=index.generation_id,
        hits=(),
        donors=(),
        receipt=receipt,
        provenance_artifact=index.artifact,
    )
matches = rank_entries(index.entries, query)
compatible = tuple(item for item in matches if item.evidence.compatible)
if not compatible:
    return incompatible_result(query, index, matches)
best_rank = compatible[0].rank
best = tuple(item for item in compatible if item.rank == best_rank)
if len({item.claim_identity for item in best}) > 1:
    return ambiguous_result(query, index, best)
bounded = best[:query.limit]
return matched_result(query, index, bounded)
```

- [ ] **Step 4: Run query and receipt tests.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_donor_index.py --jobs 1
```

Expected result: the focused suite passes with stable results under reversed entry order, explicit ambiguity and incompatibility receipts, stale receipts for changed inputs, an empty result for no match, and unchanged scanner counts after every query.

- [ ] **Step 5: Stop for the root-only commit boundary.** Root may commit only `automation/search_donor_index.py` and `automation/test_search_donor_index.py` with message `feat: query donor evidence with typed refusals`. The worker does not query a live provider or write a new generation during a query.

### Task 7: Route target-context donor results through ordinary lanes and coordinator evaluation

**Files:**

- Modify: `automation/search_donor_index.py`
- Modify: `automation/search_lanes.py`
- Modify: `automation/test_search_donor_index.py`
- Modify: `automation/test_search_lanes.py`

**Interfaces:**

- Consumes: `indexed_lane_adapter(...)`, existing `LaneAdapters.from_mapping`, `run_lane` or `run_lanes`, `Recipient`, `LaneCandidate`, `LaneOutcome`, `TaskResult`, and `SearchCoordinator`.
- Produces: a one-argument read-only lane callback that queries the immutable index once, gives only semantic donor evidence to a target-context renderer, and returns the renderer's `LaneCandidate` through the existing candidate and receipt path.

- [ ] **Step 1: Write the failing ordinary-lane integration tests.** The renderer creates target-context source text and a complete `CandidateRecord`; it never reads `DonorEvidence.body` or the donor artifact bytes. The callback returns a mapping with `candidates`, `attempts`, `input_identities`, and provenance so `_dispatch` can use the existing `_discovery_from_values` path.

```python
def test_indexed_donor_reaches_lane_and_coordinator(tmp_path):
    index, fixture = fixture_index(tmp_path)
    manifest = fixture_manifest(("us:ST:fn",), ("cfg_dataflow",))
    target_body = "int fn(void) { return 9; }\n"

    def render(recipient, donors):
        assert all(donor.body is None for donor in donors)
        candidate_id = hash_bytes(target_body.encode("utf-8"))
        candidate = CandidateRecord(
            candidate_id=candidate_id,
            recipient_id=recipient.recipient_id,
            source_artifact=ArtifactRef(candidate_id, "artifacts/sources/target.c", "text/x-c", len(target_body.encode("utf-8"))),
            parent_candidate_ids=(),
            mutation_id=None,
            lane="cfg_dataflow",
            depth=0,
            evaluation=None,
            status="materialized",
        )
        return LaneCandidate(candidate, target_body, ({"kind": "target_context", "source": "target-renderer", "source_identity": candidate_id, "input_identity": index.generation_id},))

    adapter = indexed_lane_adapter(
        index,
        expected_binding=index.binding,
        query_for=lambda recipient: fixture_query(recipient_id=recipient.recipient_id),
        render_target_context=render,
    )
    batch = run_lane(manifest, "cfg_dataflow", {"us:ST:fn": Recipient("us:ST:fn", "ST", "fn")}, adapters=LaneAdapters.from_mapping({"cfg_dataflow": adapter}), repo_root=tmp_path)
    assert len(batch.candidates) == 1
    assert batch.candidates[0].source == target_body
    assert any(item["query_identity"] == fixture_query().query_identity for item in batch[0].provenance)
    assert any(item["generation_id"] == index.generation_id for item in batch[0].provenance)
    assert all(item["revision_identity"] for item in batch[0].provenance if "revision_identity" in item)

    coordinator = SearchCoordinator(tmp_path / "run", manifest)
    task = coordinator.create_task(recipient_id="us:ST:fn", lane="cfg_dataflow", operation="indexed-donor", budget_ordinal=0)
    coordinator.schedule_task(task)
    coordinator.buffer_result(TaskResult(task_id=task.task_id, candidate=batch.candidates[0].candidate, source=target_body))
    coordinator.commit_epoch()
    assert task.task_id in recover_run(tmp_path / "run").completed_task_ids

def test_indexed_ambiguity_is_a_lane_refusal(tmp_path):
    index, _ = fixture_index(tmp_path, duplicate_symbol=True)
    adapter = indexed_lane_adapter(index, expected_binding=index.binding, query_for=lambda recipient: fixture_query(recipient_id=recipient.recipient_id), render_target_context=lambda recipient, donors: ())
    batch = run_lane(fixture_manifest(), "cfg_dataflow", {"us:ST:fn": Recipient("us:ST:fn", "ST", "fn")}, adapters=LaneAdapters.from_mapping({"cfg_dataflow": adapter}), repo_root=tmp_path)
    assert batch[0].refusal is not None
    assert batch[0].refusal.code == "donor_query_ambiguous"
```

- [ ] **Step 2: Run the integration failure.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_donor_index.py --only test_search_lanes.py --jobs 2
```

Expected result before implementation: the indexed adapter is absent and, after only its first draft exists, the lane test fails because the existing structural branch ignores a callback mapping whose authoritative value is `candidates`.

- [ ] **Step 3: Implement the adapter and the one narrow dispatch branch.** `indexed_lane_adapter` must validate the expected binding, call `query_for(recipient)` once, call `render_target_context` only for `matched`, reject renderer candidates for another recipient, and preserve query identity, hit entry IDs, each pinned revision identity, generation identity, and the verified generation artifact identity in provenance. Its returned mapping uses the existing `_discovery_from_values` fields `candidates`, `attempts`, `input_identities`, `provenance`, and `completion_reason`; every provenance entry has the lane, recipient, source, source identity, and input identity required by the current lane normalizer. Map `ambiguous`, `incompatible`, `stale`, and `empty` to explicit lane refusal codes and no candidates. In `search_lanes._dispatch`, route a callback mapping containing `candidates` to `_discovery_from_values` before the existing `multi_donor` or `cfg_dataflow` donor triangulation branch. Do not loosen `read_only=True`, subset equality, manifest lane checks, or candidate source identity checks.

```python
raw = _call_fetcher(callback, recipient)
if lane in {"multi_donor", "cfg_dataflow"} and isinstance(raw, Mapping) and "candidates" in raw:
    return _discovery_from_values(raw, lane=lane, recipient=recipient, root=root)
```

- [ ] **Step 4: Run the lane and coordinator integration tests.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_donor_index.py --only test_search_lanes.py --jobs 2
```

Expected result: both focused suites pass, a target-context candidate is accepted by the ordinary coordinator and archived under its task identity, ambiguity and incompatibility remain typed lane refusals, and no donor body bytes or version-specific registers reach the candidate.

- [ ] **Step 5: Stop for the root-only commit boundary.** Root may commit only `automation/search_donor_index.py`, `automation/test_search_donor_index.py`, `automation/search_lanes.py`, and `automation/test_search_lanes.py` with message `feat: route indexed donors through ordinary lanes`. The worker does not commit or change coordinator, archive, queue, source, or connector code.

### Task 8: Run the bounded acceptance gate and hand off to root

**Files:**

- Review only the paths listed in Tasks 0 through 7.

**Interfaces:**

- Consumes: the focused suites and their immutable receipts, plus the parent integration shadow gate.
- Produces: a root-readable report containing exact focused commands, pass/fail verdicts, refusal codes exercised, generation identities, no-rescan counts, and any dependency gap. It does not change a roadmap, connector, queue, build, source, or existing operational document.

- [ ] **Step 1: Confirm the focused scripts are callable.** Root checks the live `run_automation` allowlist. If either new test script is not callable, root reports the connector gap and does not edit connector surfaces as part of this plan.

- [ ] **Step 2: Run the complete focused non-build suite through `sotn-cmd`.**

```text
sotn-cmd run_automation run_selftests.py --only test_search_evidence_corpus.py --only test_search_patterns.py --only test_search_donor_index.py --only test_search_lanes.py --jobs 4
```

Expected result: all four selected suites pass; the result table contains no build, queue, source, connector, or provider job.

- [ ] **Step 3: Review refusal and determinism coverage.** Confirm tests cover missing or changed shadow identity, empty and nonempty subsets, altered lesson bytes or span, missing or conflicting scorer taxonomy, missing or ambiguous draft-landed provenance, no measured improvement, exact object promotion, single-lineage and incompatible `FirstDivergence`, negative/refusal retention, missing or corrupt donor artifact, all binding changes, four-version completeness, symbol/instruction/CFG/dataflow order, ambiguity, incompatibility, stale generation, source-body exclusion, no per-record rescan, target-context rendering, ordinary lane subset enforcement, and coordinator task identity.

- [ ] **Step 4: Perform the plan self-review before root integration.** Check every supplement section against the coverage table below, search this file for unassigned-task markers, open-ended implementation instructions, incomplete code markers, and em dash characters, then compare every signature and field name across tasks. Type-annotation ellipses in the shared interface block are syntax, not unfinished content.

- [ ] **Step 5: Stop for the root-only final boundary.** Root stages only the exact changed automation files from the completed tasks, reviews all diffs including pre-existing dirty paths, updates the roadmap outcome separately, and performs any required repository-level checks. No worker commit, build, queue write, `src/` edit, connector edit, or push belongs to this plan.

## Acceptance Coverage

| Supplement requirement | Plan coverage |
|---|---|
| Shadow-first integration ordering | Task 0 gate; Task 8 command and root prerequisite |
| Exact scorer taxonomy | Task 1 `ScorerTaxonomy`; Task 3 promotion identity checks |
| Stable `MATCHING-LESSONS.md` content and span citation | Task 1 full source hash, line span, and §2 absent masking test |
| Proven finalized draft-landed observations | Task 3 existing `DraftLandedObservation`, grouped patch, commit, and pair hash |
| Recurring completed-ledger `FirstDivergence` hypotheses | Task 2 public completed projection and Task 3 recurrence gate |
| Measured improvement or exact object promotion only | Task 3 calls existing `measure_improvement` and `make_idiom_observation` |
| Negative and refusal evidence | Tasks 3 and 4 typed refusal and corpus entries |
| One immutable US, HD, PSPEU, Saturn index generation | Task 5 four-version revision validation and archive publication |
| Revision, indexer, config, schema, signature binding | Task 5 `DonorIndexBinding` and identity-change tests |
| Symbol, instruction, CFG, dataflow bounded queries | Task 6 selector hierarchy and `limit <= 8` |
| Ambiguous, incompatible, stale typed receipts | Task 6 result statuses and receipt classes |
| No rescan per record | Tasks 5 and 6 scanner count fixture and query-only generation input |
| Ordinary lane and coordinator evaluation | Task 7 target renderer, `run_lane`, `TaskResult`, and recovery assertions |
| Existing module authority preserved | File map and global constraints prohibit parallel types, archives, ledgers, queue, or source paths |
| Deferred m2c and data-segment work | Global constraints explicitly exclude both |

## Gaps and Root Decisions

- This plan intentionally creates no code and edits no existing document beyond this plan file. The implementation worker must create the listed automation modules and tests in later, root-approved commits.
- The public `CompletedLineageContext` projection is the only existing-module API extension required to expose scorer identity. If root review finds an already-public equivalent, reuse it and retain the same fields and refusal behavior instead of adding a duplicate.
- The lane dispatch branch assumes the target-context renderer can return a complete `LaneCandidate` with target bytes. A renderer that can supply only donor bytes is not an acceptable implementation and must produce a typed refusal.
- `automation/run_selftests.py` is deliberately not edited. Its glob discovery is assumed; if the new test files are not discoverable through the allowlisted command, root reports that connector or discovery gap separately.
- `ROADMAP.md` is deliberately not edited because this task permits only the new plan path. Root must record the plan outcome under its normal roadmap authority after implementation.

The worker implementing this plan reports the exact plan path, focused command verdicts, pass counts, refusal codes, corpus and donor generation identities, scanner call counts, and unresolved core API dependency. It leaves the repository uncommitted and does not claim a match, source landing, queue transition, or build result.
