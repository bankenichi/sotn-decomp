# m2c Revision Benchmark and Weight Tuner Implementation Plan

> **For agentic workers:** Execute the checked tasks in order, stop at each
> stated root-review boundary, and report the exact changed paths and focused
> verdict. Workers do not build, run git, write the queue, edit `src/`, or push.

**Goal:** Build an immutable, benchmark-gated m2c revision matrix and a later-manifest-only scorer weight tuner. The current pinned m2c revision is always the first benchmark candidate. Alternate revisions become usable only after the same fixed benchmark produces a unique candidate or a measured improvement. Weight tuning is blocked until integration shadows and a real archived draft-target corpus exist.

**Architecture:** An integration receipt freezes the selected lanes, explicit record subset, scheduler-owned queue evidence, and connector/coordinator identity before any revision work. A strict provider resolves the clean detached current revision and any explicitly named alternate by immutable identity. A fixed benchmark archives every input, output, invocation, score vector, compiler identity, tool identity, and config identity before qualification. The matrix enumerates the current revision first, then only qualified alternates, with deterministic deduplication and bounded cost. A separate tuner creates a lineage-safe train/holdout dataset from immutable archived cases, runs fixed trials, ranks exact rediscovery first, and publishes an immutable weight artifact that later manifests may reference.

**Tech Stack:** Python 3 with frozen dataclasses and explicit protocols, existing automation/search_types.py score and artifact types, ContentAddressedArchive, AppendOnlyLedger, existing coordinator and scorer identity helpers, JSON fixtures under automation/fixtures/search/, and focused sotn-cmd run_automation self-tests. No worker invokes git, a build, queue writers, or source mutation.

**Spec:** docs/superpowers/specs/2026-08-28-instrumented-search-supplement-design.md, docs/superpowers/specs/2026-08-26-instrumented-search-system-design.md, and docs/superpowers/specs/2026-08-26-instrumented-search-system-implementation-plan.md. This plan adds the independent revision benchmark and Task 9.6 weight tuner while preserving the integration-first ordering in the supplement.

## Global Constraints

- Complete and verify Tasks 8.1, 8.2, and 8.3 integration work before enabling the m2c matrix or tuner. The first permitted runtime is one read-only record shadow. The second is a bounded read-only multi-record shadow. A tuner also requires real archived draft-target cases, not synthetic-only fixtures.
- Use tools/m2c at the clean, detached revision 94098d4de68c2fcc13fb8cf1096a1520eb171abe as the current provider input. The plan treats any claim that this checkout is already modified as stale unless a provider returns a fresh immutable identity proving otherwise.
- A direct-ID plan is syntactic and read-only. Run creation resolves those IDs through scheduler-owned todo evidence, archives the status-bound evidence, and binds queue_evidence_identity. subset_identity is the canonical hash of sorted selected IDs only. They are separate identities. Resume verifies the archived identities and never reselects live queue state.
- Require explicit selected lanes and explicit record IDs. No queue fallback, rank drift, implicit lane expansion, or current-state re-selection is allowed after run creation. Legacy and instrumented execution are mutually exclusive.
- Workers return typed result or refusal proposals. The coordinator owns task IDs, budgets, deduplication, ledger append, manifest creation, and adoption. The scheduler remains the only queue writer.
- Every input, output, invocation, score, measurement, provider identity, commit or revision identity, compiler identity, tool identity, config identity, scorer taxonomy identity, and fixture identity is content-addressed. Do not use mtimes, path hashes, filename order, commit adjacency, or abbreviated revisions as evidence. All `*_identity`, `*_artifact_id`, report, receipt, dataset, trial, qualification, invocation, and variant identity fields use `sha256:<64 lowercase hex>` unless the provider contract explicitly requires a full 40-character lowercase revision ID.
- A ScoreVector retains the exact five scorer components: stack, regalloc, reordering, insertion, and deletion. A lower score is meaningful only when scorer_algorithm, compiler_identity, target identity, candidate identity, and weights are identical.
- A score of zero is a candidate for the existing full build and verify handoff. It is not a matched result. The first score-zero handoff performs the full gate; a retry may reuse a valid unchanged receipt only when its source, compiler, tool, config, target, and scorer identities still match.
- The current revision is benchmarked before any alternate. An alternate is available to the matrix only when its complete fixed-benchmark report is bound to the same benchmark, scorer taxonomy, compiler, tool, config, target cases, and integration receipt and has unique_candidate_count greater than zero or better_case_count greater than zero. No speculative vendoring or exposure of an alternate occurs before that result.
- Archives are append-only and collision refusing. Reports, datasets, trial results, and weight artifacts are immutable. A replay of the same identities produces byte-identical canonical JSON and the same ordering, counts, scores, and refusal codes.
- Tuner data is immutable and lineage grouped. A draft and every target or derived variant from one source lineage enter one split only. Missing, corrupt, ambiguous, or mixed-identity evidence fails closed.
- If a benchmark is seeded from compiler idioms or MATCHING-LESSONS.md, require the exact lesson source identity and span plus a proven draft-landed observation. Text resemblance is not evidence.
- Fixed trial seeds, iteration limits, compiler identity, tool identity, config identity, scorer taxonomy, and cost accounting are part of trial identity. Ranking is exact holdout rediscovery first, then lower median best score, then lower measured cost, then immutable weight artifact identity. The selected weights are for later manifests only and never rewrite or revert matched source.
- Workers do not build, run git, touch queues, edit src, or modify existing documentation. Root owns integration checks, any coordinator/schema edits, explicit staging, commits, builds, and oracle verification.
- Do not add an em dash or emoji to code, comments, fixtures, or documentation.

## File Responsibility Map

The Task 8.2 integration runtime supplies the canonical typed shadow receipt and archived receipt artifact consumed by this plan. It is a prerequisite, not a file created here. This plan does not define a second gate module, type, or fixture.

Create these implementation and test files:
- automation/m2c_revision_provider.py: strict pinned revision provider protocol, identities, invocation archive, and typed refusals.
- automation/test_m2c_revision_provider.py: current and alternate revision fixtures, dirty or attached refusal cases, replay, and provider-call accounting tests.
- automation/fixtures/search/m2c_matrix/current_revision.json and automation/fixtures/search/m2c_matrix/alternate_revision.json: immutable provider metadata and deterministic draft payloads.
- automation/m2c_revision_matrix.py: fixed benchmark, qualification, variant enumeration, deduplication, and budget receipt logic.
- automation/test_m2c_revision_matrix.py: baseline, alternate qualification, ordering, duplicate, budget, and refusal tests.
- automation/fixtures/search/m2c_matrix/fixed_benchmark.json: fixed cases, scorer taxonomy, target identities, and bounded budget.
- automation/weight_tuner.py: archived dataset, fixed trials, ranking, immutable report, weight artifact, and later-manifest binding.
- automation/test_weight_tuner.py: dataset leakage, identity, replay, trial, ranking, artifact, adoption, and gate tests.
- automation/fixtures/search/weight_tuner/archived_cases.json and automation/fixtures/search/weight_tuner/trials.json: real-shape archived-case metadata and fixed trial specs.

Modify only after root review of the implementation:

- automation/search_types.py: add and validate the nullable, explicitly serialized weight_artifact_identity field while reusing the existing queue_evidence_identity binding and rejecting pre-migration manifests.
- automation/search-ledger.schema.json: require weight_artifact_identity in the new manifest schema, allow only null or a sha256 archive hash, and bind the new schema identity.
- automation/search_coordinator.py: verify archived subset and queue evidence at run creation and resume, enforce integration and tuner gates, include the weight identity in immutable manifest comparisons, and refuse active-run weight mutation.
- automation/search_recovery.py: include the weight identity in recovery identity comparisons and reject a pre-migration manifest without rewriting its bytes.
- automation/test_search_coordinator.py: exercise manifest migration, identity, and adoption refusal paths.
- automation/test_search_schema.py: update event and manifest fixtures for the new schema and test the required nullable field.
- automation/test_search_lanes.py: update its direct RunManifest fixture to emit explicit `weight_artifact_identity=None` under schema 1.1.0.

## Shared Exact Interfaces

All interfaces below are Python 3 signatures. Implementations use frozen dataclasses, canonical JSON, and the existing archive and search_types primitives. Exception names are part of the refusal API. The integration receipt type and validator are owned by the Task 8.2 integration runtime. This plan refers to the imported canonical type as IntegrationGateReceipt and to its canonical refusal as IntegrationGateError for readability only. The final module and concrete type names are selected by the integration plan; no local replacement may be created here.

The canonical gate consumer must expose these existing Task 8.2 fields through
its imported type: `gate_id`, the verified archived receipt artifact, the
`subset_identity`, and the `queue_evidence_identity`. `integration_gate_id`
below is exactly `gate.gate_id`. `integration_gate_artifact_id` is exactly the
`sha256:` content hash of that validator-verified receipt artifact. These are
copied scalar bindings, not a second gate type or validator. Every consumer
calls the canonical validator and verifies that artifact before creating a
report, dataset, or receipt.

`M2CRevisionIdentity.executable_identity` is the content identity of the exact
m2c executable used by the provider. For a per-revision benchmark report,
`tool_identity` is exactly that field and cannot be supplied independently.
The matrix carries a `(revision_id, executable_identity)` pair for every
revision so alternate executables cannot be hidden behind one baseline value.
`provider_identity` identifies the provider implementation, while
`scorer_taxonomy_identity` identifies the scorer algorithm, component weights,
and evaluator configuration. No report or invocation may invent another
meaning for `tool_identity`.

`M2CInvocation` carries the same binding at the call boundary: its
`tree_identity`, `provider_identity`, `tool_identity`, `compiler_identity`,
`evaluator_identity`, `scorer_taxonomy_identity`, `config_identity`,
`integration_gate_id`, `integration_gate_artifact_id`, `subset_identity`,
`queue_evidence_identity`, and `archive_identity` are copied from the resolved
revision, benchmark case, canonical gate, and archive. Its `tool_identity`
must equal `revision.executable_identity`; it is not an evaluator or scorer
identity. `M2CBenchmarkReport` repeats those bindings so the archived report
can be verified without trusting an unbound invocation argument. Matrix
specifications use `tool_identity` only as the current-revision alias and
`revision_tool_identities` as the complete per-revision executable map. The
evaluator and scorer identities are explicit fields in every benchmark,
invocation, evaluation, matrix spec, variant, receipt, trial, dataset, and
tuning report; no orphan `tool_identity` field may be invented by an
implementation. A benchmark case's `config_identity` must equal the resolved
revision's `config_identity`; the invocation, report, matrix, dataset, and
trial copies are that one validated configuration identity, not separate
provider and evaluator configuration values.
`M2CMatrixSpec.gate_id` is the sole gate-ID field in that spec and is exactly
`gate.gate_id`; `M2CMatrixReceipt.integration_gate_id` is the corresponding
canonical copy, not a second identity.

Every report and receipt ID is `hash_canonical` over its complete canonical
payload with the ID field excluded. Referenced artifact IDs are verified by
`ContentAddressedArchive` before the record is archived. Thus a path, an
unverified call argument, or a nested object that was not archived cannot
establish provenance.

~~~python
from automation.search_archive import ContentAddressedArchive
from automation.search_types import ArtifactRef, RunManifest, ScoreComponents, ScoreVector

CURRENT_M2C_REVISION = "94098d4de68c2fcc13fb8cf1096a1520eb171abe"

class M2CProviderError(ValueError):
    """Provider identity, revision, or invocation refusal."""

class M2CBenchmarkError(ValueError):
    """Fixed-benchmark input, measurement, or identity refusal."""

class M2CMatrixError(ValueError):
    """Revision-matrix enumeration or receipt refusal."""

class TunerDataError(ValueError):
    """Tuner corpus, split, or evidence refusal."""

class WeightTuningError(ValueError):
    """Trial, report, or later-manifest adoption refusal."""

@dataclass(frozen=True)
class M2CRevisionIdentity:
    revision_id: str
    tree_identity: str
    provider_identity: str
    executable_identity: str
    config_identity: str
    clean: bool
    detached: bool

@dataclass(frozen=True)
class M2CInvocation:
    invocation_id: str
    revision_id: str
    tree_identity: str
    provider_identity: str
    recipient_id: str
    assembly_artifact: ArtifactRef
    context_artifacts: tuple[ArtifactRef, ...]
    switches: tuple[str, ...]
    target_identity: str
    compiler_identity: str
    tool_identity: str
    evaluator_identity: str
    scorer_taxonomy_identity: str
    config_identity: str
    integration_gate_id: str
    integration_gate_artifact_id: str
    subset_identity: str
    queue_evidence_identity: str
    archive_identity: str
    ordinal: int

@dataclass(frozen=True)
class M2CDraftPayload:
    invocation_id: str
    revision_id: str
    source_artifact: ArtifactRef

class M2CRevisionProvider(Protocol):
    def resolve_revision(self, revision_id: str) -> M2CRevisionIdentity:
        """Resolve one explicitly named immutable revision."""

    def generate_draft(
        self,
        invocation: M2CInvocation,
        *,
        assembly: bytes,
        contexts: tuple[bytes, ...],
    ) -> M2CDraftPayload:
        """Generate and archive one draft for the exact invocation."""
~~~

The provider protocol has one accepted call shape. A provider adapter inspects a callable signature before invocation when it must adapt a legacy fixture, or rejects it as M2CProviderError. It never invokes once, catches TypeError, and retries with another shape. An internal TypeError is surfaced after exactly one call.

~~~python
@dataclass(frozen=True)
class M2CBenchmarkCase:
    case_id: str
    recipient_id: str
    assembly_artifact: ArtifactRef
    context_artifacts: tuple[ArtifactRef, ...]
    target_identity: str
    compiler_identity: str
    evaluator_identity: str
    config_identity: str

@dataclass(frozen=True)
class M2CFixedBenchmark:
    benchmark_id: str
    current_revision_id: str
    cases: tuple[M2CBenchmarkCase, ...]
    scorer_taxonomy_identity: str
    evaluator_identity: str
    budget: int

@dataclass(frozen=True)
class M2CEvaluation:
    case_id: str
    revision_id: str
    invocation_id: str
    source_artifact: ArtifactRef
    score: ScoreVector
    tool_identity: str
    evaluator_identity: str
    scorer_taxonomy_identity: str
    cost_units: int

@dataclass(frozen=True)
class M2CBenchmarkReport:
    report_id: str
    benchmark_id: str
    benchmark_artifact_id: str
    revision_id: str
    tree_identity: str
    provider_identity: str
    tool_identity: str
    archive_identity: str
    integration_gate_id: str
    integration_gate_artifact_id: str
    subset_identity: str
    queue_evidence_identity: str
    compiler_identity: str
    evaluator_identity: str
    config_identity: str
    scorer_taxonomy_identity: str
    observations: tuple[M2CEvaluation, ...]
    observation_artifact_ids: tuple[str, ...]
    total_cost_units: int
    unique_candidate_count: int
    better_case_count: int
    complete: bool
    refusal_code: str | None

def run_fixed_benchmark(
    benchmark: M2CFixedBenchmark,
    revision: M2CRevisionIdentity,
    provider: M2CRevisionProvider,
    evaluator: Callable[[M2CBenchmarkCase, ArtifactRef, str], ScoreVector],
    archive: ContentAddressedArchive,
    *,
    archive_identity: str,
    gate: IntegrationGateReceipt,
) -> M2CBenchmarkReport:
    """Run the fixed cases once and return the complete immutable report."""

@dataclass(frozen=True)
class M2CRevisionQualification:
    qualification_id: str
    benchmark_id: str
    baseline_report_id: str
    alternate_report_id: str
    alternate_revision_id: str
    unique_candidate_count: int
    better_case_count: int
    qualified: bool
    reason_code: str

def qualify_revision(
    baseline: M2CBenchmarkReport,
    alternate: M2CBenchmarkReport,
) -> M2CRevisionQualification:
    """Compare two complete reports from the same fixed benchmark."""
~~~

For qualification, unique_candidate_count is the count of alternate source artifact identities absent from the corresponding complete baseline case. better_case_count is the count of cases with a strictly lower total score under identical scorer, compiler, target, config, and weight identities. Incomplete reports never qualify, even if a partial result looks better.

~~~python
@dataclass(frozen=True)
class M2CMatrixSpec:
    matrix_id: str
    matrix_spec_artifact_id: str
    benchmark_id: str
    benchmark_artifact_id: str
    gate_id: str
    integration_gate_artifact_id: str
    subset_identity: str
    queue_evidence_identity: str
    provider_identity: str
    tool_identity: str
    revision_tool_identities: tuple[tuple[str, str], ...]
    archive_identity: str
    current_revision_id: str
    qualified_alternate_revision_ids: tuple[str, ...]
    cases: tuple[M2CBenchmarkCase, ...]
    switch_matrix: tuple[tuple[str, ...], ...]
    context_kinds: tuple[str, ...]
    compiler_identity: str
    evaluator_identity: str
    config_identity: str
    scorer_taxonomy_identity: str
    budget: int

@dataclass(frozen=True)
class M2CVariant:
    variant_id: str
    ordinal: int
    revision_id: str
    case_id: str
    recipient_id: str
    assembly_artifact: ArtifactRef
    context_artifacts: tuple[ArtifactRef, ...]
    target_identity: str
    switches: tuple[str, ...]
    context_kind: str
    tool_identity: str
    evaluator_identity: str
    scorer_taxonomy_identity: str
    request_identity: str

@dataclass(frozen=True)
class M2CMatrixReceipt:
    receipt_id: str
    matrix_id: str
    matrix_spec_artifact_id: str
    benchmark_id: str
    benchmark_artifact_id: str
    integration_gate_id: str
    integration_gate_artifact_id: str
    subset_identity: str
    queue_evidence_identity: str
    provider_identity: str
    revision_ids: tuple[str, ...]
    revision_tool_identities: tuple[tuple[str, str], ...]
    archive_identity: str
    compiler_identity: str
    tool_identity: str
    evaluator_identity: str
    config_identity: str
    scorer_taxonomy_identity: str
    variant_ids: tuple[str, ...]
    variant_manifest_artifact_id: str
    evaluation_artifact_ids: tuple[str, ...]
    deduplication_artifact_id: str
    compiled_candidate_ids: tuple[str, ...]
    deduplicated_variant_ids: tuple[str, ...]
    consumed_budget: int
    remaining_budget: int
    status: str
    refusal_code: str | None

def enumerate_m2c_variants(
    spec: M2CMatrixSpec,
    qualifications: tuple[M2CRevisionQualification, ...],
) -> tuple[M2CVariant, ...]:
    """Enumerate current-first variants from the self-contained matrix spec."""

def run_m2c_matrix(
    spec: M2CMatrixSpec,
    variants: tuple[M2CVariant, ...],
    provider: M2CRevisionProvider,
    evaluator: Callable[[M2CBenchmarkCase, ArtifactRef, str], ScoreVector],
    archive: ContentAddressedArchive,
    gate: IntegrationGateReceipt,
) -> M2CMatrixReceipt:
    """Run the bounded variants and return their complete immutable receipt."""
~~~

Variant order is current revision first, then qualified alternate revisions sorted by revision identity, then recipient ID, switch tuple, and context kind. A compile deduplication key is the exact tuple of recipient, source artifact, target identity, compiler identity, config identity, and scorer taxonomy identity. It does not normalize identifiers or discard provenance.

~~~python
@dataclass(frozen=True)
class ArchivedDraftTarget:
    case_id: str
    recipient_id: str
    lineage_identity: str
    draft_artifact: ArtifactRef
    target_artifact: ArtifactRef
    target_object_identity: str
    compiler_identity: str
    tool_identity: str
    evaluator_identity: str
    config_identity: str
    scorer_taxonomy_identity: str
    source_ledger_identity: str

@dataclass(frozen=True)
class TunerDataset:
    dataset_id: str
    dataset_artifact_id: str
    source_archive_identity: str
    source_archive_artifact_id: str
    split_identity: str
    integration_gate_id: str
    integration_gate_artifact_id: str
    subset_identity: str
    queue_evidence_identity: str
    train_case_ids: tuple[str, ...]
    holdout_case_ids: tuple[str, ...]
    cases: tuple[ArchivedDraftTarget, ...]
    compiler_identity: str
    tool_identity: str
    evaluator_identity: str
    config_identity: str
    scorer_taxonomy_identity: str
    split_seed: int

def build_tuner_dataset(
    cases: tuple[ArchivedDraftTarget, ...],
    *,
    split_seed: int,
    holdout_ratio: float,
    gate: IntegrationGateReceipt,
    archive: ContentAddressedArchive,
    source_archive_identity: str,
) -> TunerDataset:
    """Build and archive one deterministic, lineage-grouped dataset."""

@dataclass(frozen=True)
class WeightTrialSpec:
    trial_id: str
    dataset_id: str
    weights: ScoreComponents
    seed: int
    iterations: int
    compiler_identity: str
    tool_identity: str
    evaluator_identity: str
    config_identity: str
    scorer_taxonomy_identity: str

@dataclass(frozen=True)
class WeightCaseResult:
    case_id: str
    status: str
    exact_rediscovered: bool
    best_score: int | None
    cost_units: int
    object_identity: str | None

@dataclass(frozen=True)
class WeightTrialResult:
    trial_id: str
    weight_artifact_identity: str
    train_results: tuple[WeightCaseResult, ...]
    holdout_results: tuple[WeightCaseResult, ...]
    total_cost_units: int

class WeightTrialRunner(Protocol):
    def run(
        self,
        trial: WeightTrialSpec,
        dataset: TunerDataset,
    ) -> WeightTrialResult:
        """Run one fixed trial without changing the dataset or manifest."""

@dataclass(frozen=True)
class WeightArtifact:
    artifact: ArtifactRef
    weights: ScoreComponents
    dataset_id: str
    selected_trial_id: str

@dataclass(frozen=True)
class WeightTuningReport:
    report_id: str
    dataset_id: str
    dataset_artifact_id: str
    source_archive_identity: str
    source_archive_artifact_id: str
    split_identity: str
    integration_gate_id: str
    integration_gate_artifact_id: str
    subset_identity: str
    queue_evidence_identity: str
    report_archive_identity: str
    trial_ids: tuple[str, ...]
    trial_result_artifact_ids: tuple[str, ...]
    selected_trial_id: str
    selected_trial_result_artifact_id: str
    weight_artifact_id: str
    weight_artifact: WeightArtifact
    holdout_exact_rediscoveries: int
    holdout_case_count: int
    holdout_median_best_score: int | None
    total_cost_units: int
    compiler_identity: str
    tool_identity: str
    evaluator_identity: str
    config_identity: str
    scorer_taxonomy_identity: str

def rank_weight_trials(
    results: tuple[WeightTrialResult, ...],
) -> tuple[WeightTrialResult, ...]:
    """Order trials by rediscovery, score, cost, and weight artifact identity."""

def tune_weights(
    dataset: TunerDataset,
    trials: tuple[WeightTrialSpec, ...],
    runner: WeightTrialRunner,
    archive: ContentAddressedArchive,
    gate: IntegrationGateReceipt,
    *,
    report_archive_identity: str,
) -> WeightTuningReport:
    """Run fixed trials and publish one immutable report and weight artifact."""

def verify_tuning_report(
    report: WeightTuningReport,
    archive: ContentAddressedArchive,
) -> None:
    """Verify every report, dataset, trial, and weight artifact reference."""

def bind_weights_to_later_manifest(
    manifest: RunManifest,
    report: WeightTuningReport,
    archive: ContentAddressedArchive,
    *,
    run_root: Path,
) -> RunManifest:
    """Bind verified weights before a new run root has been materialized."""
~~~

The dataset builder verifies every artifact and ledger identity before splitting, groups all cases by `lineage_identity`, sorts canonical case identities, and deterministically assigns whole groups to train or holdout. It refuses mixed compiler, tool, evaluator, config, scorer, or archive identities. The tuner ranks exact holdout rediscoveries first, then lower median best score, then lower total cost, then immutable weight artifact identity. It archives the weight artifact before the report and binds the report identity into later manifests only.

`M2CBenchmarkReport.report_id` is the hash of its complete canonical payload:
the archived benchmark artifact, revision and tree identities, provider and
executable identities, archive binding, canonical gate identity and verified
gate-artifact identity, subset and queue-evidence identities, compiler,
evaluator, config and scorer taxonomy identities, ordered observations and
observation-artifact identities, counts, total cost, completion, and refusal
code. The report must verify `benchmark_id` and `benchmark_artifact_id` against
the archived fixed benchmark before it is returned.

`M2CMatrixReceipt.receipt_id` is the hash of its complete canonical payload:
the archived matrix spec and fixed benchmark identities, canonical gate and
verified gate-artifact identities, subset and queue-evidence identities,
provider identity, every revision and revision-to-executable binding, archive,
compiler, evaluator, baseline tool, config and scorer taxonomy identities,
ordered variant IDs and variant-manifest artifact, evaluation artifact IDs,
deduplication artifact, compiled candidates, cost accounting, status, and
refusal code. The receipt must verify `matrix_id` and
`matrix_spec_artifact_id` against that archived spec before it is returned.

`WeightTuningReport.report_id` is the hash of its complete canonical payload:
dataset and dataset-artifact identities, source archive and source-artifact
identities, split identity, canonical gate and verified gate-artifact
identities, subset and queue-evidence identities, report archive identity,
ordered trial IDs and trial-result artifact IDs, selected trial and selected
trial-result artifact, weight-artifact identity and complete `WeightArtifact`,
all ranking metrics, total cost, compiler, tool, evaluator, config, scorer
taxonomy, and refusal state. The selected trial result must be a member of the
archived trial-result set, and `weight_artifact_id` must equal the nested
artifact's content hash. No provenance supplied only as a call argument may be
omitted from a returned identity-bearing record.

Manifest evolution contract: the existing
`RunManifest.queue_evidence_identity` remains required and unchanged. Task 7
adds `RunManifest.weight_artifact_identity: Optional[str]` as the final
dataclass field. The new event and manifest schema requires that property, with
`null` meaning that no tuner artifact was adopted and a non-null value required
to be a verified `sha256:<64 lowercase hex>` archive content hash. New
`RunManifest` objects always serialize the property explicitly. A manifest or
ledger event written under the pre-migration schema, where the property is
absent, is rejected by the typed `SearchValidationError` migration refusal;
the loader does not map it to `None` and no historical bytes are rewritten.
The exact new `search_types.SCHEMA_VERSION` and event-schema `const` are
`1.1.0` (the subset schema remains `1.0.0`), and the bound schema identity is
updated to the content hash of that `1.1.0` schema. Resume requires that new
schema identity. A new run or explicit fork must materialize the field as
`null` or as the verified `WeightArtifact` hash.
Adoption tests cover old-schema refusal, explicit null serialization, exact
hash round-trip, altered or missing artifact refusal, and immutable old-event
hash preservation.

## Test Fixture Helper Contract

The focused tests use deterministic helpers defined in their named test modules. These helpers are part of the plan, so implementation workers must provide these exact signatures and load only the JSON fixtures named in the responsibility map. Fixture helpers never inspect live queue state, tools/m2c, source files, mtimes, or git refs. The canonical integration receipt helper imports the Task 8.2 receipt and archived artifact; it does not construct, mutate, or validate a parallel receipt type. `fixture_name` selects one receipt artifact already owned by the Task 8.2 runtime, including separate valid receipts with different queue evidence and deliberately corrupt receipt-artifact fixtures. Every content identity, artifact identity, report ID, receipt ID, dataset ID, trial ID, qualification ID, invocation ID, variant ID, and weight artifact identity is produced by `fixture_hash`. The default sha256 form is prefixed `sha256:`. Revision fixtures are the sole format exception: `fixture_hash(..., algorithm="sha1")` produces the provider-required full 40-character lowercase revision ID, which the revision validator checks separately.

~~~python
import hashlib
from pathlib import Path
from typing import Optional

def fixture_hash(label: str, *, algorithm: str = "sha256") -> str:
    if algorithm not in ("sha256", "sha1"):
        raise ValueError("fixture identities use sha256 or provider revision sha1")
    payload = ("fixture:" + label).encode("utf-8")
    digest = hashlib.new(algorithm, payload).hexdigest()
    return "sha256:" + digest if algorithm == "sha256" else digest

def fixture_gate(
    *,
    multi_record: bool = True,
    fixture_name: Optional[str] = None,
) -> IntegrationGateReceipt:
    """Load the canonical Task 8.2 receipt and run its validator."""

def fixture_gate_artifact_identity(gate: IntegrationGateReceipt) -> str:
    """Return the validator-verified archived receipt content hash."""

def fixture_provider(
    *,
    clean: bool = True,
    detached: bool = True,
) -> M2CRevisionProvider:
    """Return a deterministic provider fixture."""

def fixture_revision(
    revision_id: str = CURRENT_M2C_REVISION,
    *,
    clean: bool = True,
    detached: bool = True,
) -> M2CRevisionIdentity:
    """Return an immutable revision fixture."""

def fixture_invocation() -> M2CInvocation:
    """Return an invocation bound to fixture revision, gate, archive, and case identities."""

def fixture_archive() -> ContentAddressedArchive:
    """Return an isolated content-addressed archive fixture."""

def fixture_benchmark(
    *,
    missing_measurement: bool = False,
) -> M2CFixedBenchmark:
    """Return the fixed benchmark with archived cases and evaluator identity."""

def fixture_evaluator(
    case: M2CBenchmarkCase,
    candidate: ArtifactRef,
    scorer_taxonomy_identity: str,
) -> ScoreVector:
    """Return the deterministic score vector for one fixture case."""

def fixture_report(
    revision_id: str,
    *,
    benchmark_id: str = fixture_hash("fixed-benchmark"),
    complete: bool = True,
    unique: int = 1,
    better: int = 1,
) -> M2CBenchmarkReport:
    """Return a report with hash-validated identities and a full sha1 revision ID."""

def fixture_alternate_revision_id() -> str:
    return fixture_hash("alternate-revision", algorithm="sha1")
def fixture_qualified_alternate() -> M2CRevisionQualification:
    """Return a qualified alternate bound to the fixed benchmark."""

def fixture_unqualified_alternate() -> M2CRevisionQualification:
    """Return an alternate with a non-qualifying measured result."""

def fixture_matrix_spec(
    *,
    qualified_alternate_revision_ids: tuple[str, ...] = (),
    provider_identity: str = fixture_hash("provider"),
    tool_identity: str = fixture_hash("tool"),
    evaluator_identity: str = fixture_hash("evaluator"),
    archive_identity: str = fixture_hash("matrix-archive"),
    budget: int = 8,
) -> M2CMatrixSpec:
    """Return a self-contained spec with canonical gate artifact and benchmark bindings."""

def fixture_duplicate_variants() -> tuple[M2CVariant, ...]:
    """Return variants with identical compile keys and distinct provenance."""

def fixture_archive_identity() -> str:
    """Return the fixture source-archive identity."""

def fixture_source_archive_artifact_identity() -> str:
    """Return the archived source-corpus artifact content identity."""

def fixture_dataset_artifact_identity() -> str:
    """Return the archived tuner-dataset artifact content identity."""

def fixture_split_identity() -> str:
    """Return the fixture split identity."""

def fixture_report_archive_identity() -> str:
    """Return the fixture report-archive identity."""

def fixture_archived_cases(
    *,
    shared_lineage: bool = False,
    single_lineage: bool = False,
) -> tuple[ArchivedDraftTarget, ...]:
    """Return archived cases with valid lineage and evidence identities."""

def fixture_dataset(*, gate: IntegrationGateReceipt) -> TunerDataset:
    """Build a deterministic dataset bound to the exact valid gate receipt."""

def fixture_trial(seed: int = 11, iterations: int = 100) -> WeightTrialSpec:
    """Return a fixed trial specification."""

def fixture_trial_result(
    *,
    weight_artifact_identity: str = fixture_hash("weight"),
    exact_rediscoveries: int = 2,
    median_best_score: int = 10,
    cost_units: int = 10,
) -> WeightTrialResult:
    """Return a result fixture whose cases realize the requested metrics."""

def fixture_tuning_report(
    dataset_id: str = fixture_hash("dataset"),
) -> WeightTuningReport:
    """Return a complete tuning report fixture."""

def fixture_manifest(
    *,
    compiler_identity: str = fixture_hash("compiler"),
) -> RunManifest:
    """Return a new-schema manifest with explicit null weight adoption."""

def fixture_unstarted_run_root() -> Path:
    """Return an isolated proposed run root with no manifest or ledger."""

def fixture_started_run_root() -> Path:
    """Return an isolated run root whose manifest and run_started event exist."""

def fixture_legacy_manifest_bytes() -> bytes:
    """Return pre-migration manifest bytes with the weight field absent."""

def fixture_legacy_event_bytes() -> bytes:
    """Return pre-migration event bytes with the weight field absent."""

def fixture_trials(dataset_id: str) -> tuple[WeightTrialSpec, ...]:
    """Return trial specifications bound to one dataset."""

def fixture_trial_runner() -> WeightTrialRunner:
    """Return a deterministic trial runner fixture."""
~~~

fixture_report, fixture_matrix_spec, fixture_archived_cases, and fixture_tuning_report must populate every newly explicit provenance field. `fixture_invocation` must set `tree_identity`, `provider_identity`, `tool_identity` equal to the resolved revision executable identity, compiler, evaluator, scorer, config, canonical gate and verified gate-artifact identities, subset, queue evidence, and archive identity before deriving `invocation_id`. `fixture_matrix_spec` must archive its canonical spec and populate `matrix_spec_artifact_id`, `benchmark_artifact_id`, `gate_id`, and `integration_gate_artifact_id`; its `tool_identity` is the current revision executable alias and must equal the corresponding entry in `revision_tool_identities`, while every alternate has its own pair. Their gate, subset, queue evidence, provider, revision, archive, compiler, tool, evaluator, config, scorer, split, and trial-result identities are fixture_hash values, except revision_id values, which use the full sha1 form from fixture_hash.
The fixture revision provider uses `fixture_hash("tool")` for the current
`executable_identity`, so the default matrix `tool_identity` is that exact
current executable binding rather than an independent evaluator or scorer
label. Any helper identity override is validated as the required sha256 form
before constructing a record; only provider revision IDs use the explicitly
validated full sha1 form. JSON fixture labels are inputs to `fixture_hash`, not
identity values themselves.

## Implementation Tasks

### Task 0: Consume the canonical integration prerequisite

Files: the Task 8.2 integration runtime's canonical typed shadow receipt and archived receipt artifact, plus consumer assertions in automation/test_m2c_revision_matrix.py and automation/test_weight_tuner.py. This plan creates no integration gate module, type, or fixture. The concrete import path and type name remain owned by the integration plan; the descriptive IntegrationGateReceipt annotation below must resolve to that canonical type when Task 8.2 lands.

- [ ] Before implementing consumers, import the canonical receipt and its validator from the Task 8.2 runtime. Verify the one-record and bounded multi-record receipt bytes, selected lanes, subset_identity, archived queue_evidence_identity, legacy exclusion, connector identity, and coordinator identity. The consumer must verify the archived artifact and must not construct a local receipt.
- [ ] Write the failing consumer assertions in the existing matrix and tuner test modules:

~~~python
def test_matrix_rejects_a_canonical_one_record_receipt(self):
    with self.assertRaises(M2CBenchmarkError):
        run_fixed_benchmark(
            fixture_benchmark(),
            fixture_revision(CURRENT_M2C_REVISION),
            fixture_provider(),
            fixture_evaluator,
            fixture_archive(),
            archive_identity=fixture_archive_identity(),
            gate=fixture_gate(multi_record=False),
        )

def test_different_valid_gate_produces_a_distinct_dataset(self):
    gate = fixture_gate(multi_record=True)
    altered = fixture_gate(
        multi_record=True,
        fixture_name="altered-queue-evidence",
    )
    original = fixture_dataset(gate=gate)
    changed = fixture_dataset(gate=altered)
    self.assertNotEqual(gate.queue_evidence_identity, altered.queue_evidence_identity)
    self.assertNotEqual(original.dataset_id, changed.dataset_id)
~~~

- [ ] Run the focused failure through the repository connector:

~~~text
sotn-cmd run_automation run_selftests.py --only test_m2c_revision_matrix.py --only test_weight_tuner.py --jobs 2
~~~

Expected result before implementation: the consumer modules or canonical receipt checks are absent and the focused suites fail.

- [ ] Implement only consumer verification: call the canonical Task 8.2 validator, require the bounded multi-record receipt for matrix and tuner work, compare the archived receipt identity to gate_id, and refuse legacy mode, missing evidence, corrupt archived receipt bytes, or internal identity drift. A different valid receipt is accepted as a different immutable input and therefore produces different downstream identities. Do not add a second validator or write a parallel fixture.
- [ ] Define fixture_gate in the test modules as a loader for the Task 8.2 archived receipt. Identity variants must be represented by separate valid canonical fixture artifacts. Corruption tests alter or misbind the archived artifact and must be rejected by the canonical validator. Add reversed-input replay equality for the imported receipt and its provenance.
- [ ] Rerun the same focused command. Expected result: 2 focused suites pass with canonical receipt verification, corrupt-evidence refusal, and distinct identities for distinct valid receipts.

Root-only commit boundary: root owns the Task 8.2 integration runtime commit. This plan may modify only the consumer test assertions listed above and must not commit a new search_integration_gate path or fixture. The worker does not commit.

### Task 1: Implement the pinned m2c revision provider

Files: automation/m2c_revision_provider.py, automation/test_m2c_revision_provider.py, automation/fixtures/search/m2c_matrix/current_revision.json, and automation/fixtures/search/m2c_matrix/alternate_revision.json.

- [ ] Write tests for exact revision and invocation identity:

~~~python
def test_current_revision_requires_clean_detached_identity(self):
    provider = fixture_provider(clean=False, detached=True)
    with self.assertRaises(M2CProviderError):
        provider.resolve_revision(CURRENT_M2C_REVISION)

def test_attached_or_abbreviated_revision_is_refused(self):
    provider = fixture_provider(clean=True, detached=False)
    with self.assertRaises(M2CProviderError):
        provider.resolve_revision("94098d4")

def test_generate_draft_is_replayable(self):
    provider = fixture_provider()
    invocation = fixture_invocation()
    revision = fixture_revision(invocation.revision_id)
    self.assertEqual(invocation.tree_identity, revision.tree_identity)
    self.assertEqual(invocation.provider_identity, revision.provider_identity)
    self.assertEqual(
        invocation.tool_identity,
        revision.executable_identity,
    )
    first = provider.generate_draft(invocation, assembly=b"asm", contexts=(b"ctx",))
    second = provider.generate_draft(invocation, assembly=b"asm", contexts=(b"ctx",))
    self.assertEqual(first, second)
~~~

- [ ] Run the focused failure:

~~~text
sotn-cmd run_automation run_selftests.py --only test_m2c_revision_provider.py --jobs 1
~~~

Expected result before implementation: import failure for m2c_revision_provider.py and a failing focused suite.

- [ ] Require a full 40-character lowercase hexadecimal revision ID, a clean tree identity, detached state, executable identity, provider identity, and config identity. A revision ID is immutable content identity, never a path or timestamp.
- [ ] Resolve only explicitly named revisions. The current fixture must bind CURRENT_M2C_REVISION exactly. An alternate fixture must carry its own full immutable identity and may not be inferred from adjacency to current.
- [ ] Archive assembly and context bytes before provider invocation. Derive invocation_id from revision, tree, provider, recipient, all artifact identities, ordered switches, target, compiler, executable/tool, evaluator, scorer, config, canonical gate and verified gate-artifact identities, subset, queue evidence, archive, and ordinal. The invocation record must carry those same fields, with tool_identity exactly equal to revision.executable_identity.
- [ ] Use the one protocol call shape shown above. If a test double has an unsupported signature, inspect it before invocation and raise M2CProviderError. Do not catch an invocation TypeError and retry. Add a counter-based test proving an internal TypeError reaches the caller after one call.
- [ ] Never checkout, mutate tools/m2c, append to donor files, or write a draft into a source path. The provider returns an archived source artifact.
- [ ] Rerun:

~~~text
sotn-cmd run_automation run_selftests.py --only test_m2c_revision_provider.py --jobs 1
~~~

Expected result: 1 focused suite passes, including altered clean, detached, identity, and internal-TypeError refusals.

Root-only commit boundary: root may commit only the four Task 1 paths with message feat: add pinned m2c revision provider. The worker does not run git or inspect the checkout through shell commands.

### Task 2: Benchmark the current revision with fixed evidence

Files: automation/m2c_revision_matrix.py, automation/test_m2c_revision_matrix.py, and automation/fixtures/search/m2c_matrix/fixed_benchmark.json.

- [ ] Write the baseline and fail-closed tests:

~~~python
def test_current_report_is_complete_and_replayable(self):
    benchmark = fixture_benchmark()
    gate = fixture_gate(multi_record=True)
    first = run_fixed_benchmark(
        benchmark,
        fixture_revision(CURRENT_M2C_REVISION),
        fixture_provider(),
        fixture_evaluator,
        fixture_archive(),
        archive_identity=fixture_archive_identity(),
        gate=gate,
    )
    second = run_fixed_benchmark(
        benchmark,
        fixture_revision(CURRENT_M2C_REVISION),
        fixture_provider(),
        fixture_evaluator,
        fixture_archive(),
        archive_identity=fixture_archive_identity(),
        gate=gate,
    )
    self.assertTrue(first.complete)
    self.assertEqual(first, second)

def test_report_retains_all_benchmark_provenance(self):
    benchmark = fixture_benchmark()
    revision = fixture_revision(CURRENT_M2C_REVISION)
    gate = fixture_gate(multi_record=True)
    report = run_fixed_benchmark(
        benchmark,
        revision,
        fixture_provider(),
        fixture_evaluator,
        fixture_archive(),
        archive_identity=fixture_archive_identity(),
        gate=gate,
    )
    self.assertEqual(report.integration_gate_id, gate.gate_id)
    self.assertEqual(
        report.integration_gate_artifact_id,
        fixture_gate_artifact_identity(gate),
    )
    self.assertEqual(report.subset_identity, gate.subset_identity)
    self.assertEqual(report.queue_evidence_identity, gate.queue_evidence_identity)
    self.assertEqual(report.revision_id, revision.revision_id)
    self.assertEqual(report.tree_identity, revision.tree_identity)
    self.assertEqual(report.provider_identity, revision.provider_identity)
    self.assertEqual(report.tool_identity, revision.executable_identity)
    self.assertEqual(report.benchmark_artifact_id, fixture_hash("fixed-benchmark-artifact"))
    self.assertEqual(report.archive_identity, fixture_archive_identity())
    self.assertEqual(report.compiler_identity, benchmark.cases[0].compiler_identity)
    self.assertEqual(report.evaluator_identity, benchmark.evaluator_identity)
    self.assertEqual(report.config_identity, benchmark.cases[0].config_identity)
    self.assertEqual(report.scorer_taxonomy_identity, benchmark.scorer_taxonomy_identity)
    self.assertEqual(len(report.observation_artifact_ids), len(benchmark.cases))
    self.assertEqual(report.total_cost_units, sum(item.cost_units for item in report.observations))
    changed = run_fixed_benchmark(
        benchmark,
        revision,
        fixture_provider(),
        fixture_evaluator,
        fixture_archive(),
        archive_identity=fixture_archive_identity(),
        gate=fixture_gate(
            multi_record=True,
            fixture_name="changed-queue-evidence",
        ),
    )
    self.assertNotEqual(report.report_id, changed.report_id)

def test_missing_measurement_refuses_complete_report(self):
    with self.assertRaises(M2CBenchmarkError):
        run_fixed_benchmark(
            fixture_benchmark(missing_measurement=True),
            fixture_revision(CURRENT_M2C_REVISION),
            fixture_provider(),
            fixture_evaluator,
            fixture_archive(),
            archive_identity=fixture_archive_identity(),
            gate=fixture_gate(multi_record=True),
        )
~~~

- [ ] Run the focused failure:

~~~text
sotn-cmd run_automation run_selftests.py --only test_m2c_revision_matrix.py --jobs 1
~~~

Expected result before implementation: import failure or M2CBenchmarkError because the fixed benchmark implementation is absent.

- [ ] Load the fixed benchmark fixture and refuse empty cases, duplicate case IDs, mixed compiler/config/target identities, a case config that differs from the resolved revision config, an evaluator identity that differs from the benchmark identity, invalid scorer taxonomy, nonpositive budget, or absent gate proof.
- [ ] Sort cases by case_id before invocation. For each case archive assembly and contexts, invoke the provider once, archive the exact source bytes, evaluate with the exact five-component scorer taxonomy, and archive the full ScoreVector and measured cost_units.
- [ ] Require compile status and all score identity fields. Never turn a missing score or failed provider call into a score of zero. Preserve a typed refusal and incomplete report instead.
- [ ] Return explicit integration_gate_id, integration_gate_artifact_id, subset_identity, queue_evidence_identity, revision_id, tree_identity, provider_identity, tool_identity (exactly revision.executable_identity), archive_identity, compiler_identity, evaluator_identity, config_identity, and scorer_taxonomy_identity on M2CBenchmarkReport. Also return benchmark_artifact_id and observation_artifact_ids. Compute report_id from those fields, the canonical benchmark, ordered observations, counts, completion, refusal code, and measured cost. A complete report requires one valid observation per case.
- [ ] Use a fixed baseline report for the current revision. Do not compare an alternate until this report is complete and immutable.
- [ ] Rerun:

~~~text
sotn-cmd run_automation run_selftests.py --only test_m2c_revision_matrix.py --jobs 1
~~~

Expected result: 1 focused suite passes with complete current report replay equality, exact cost, and missing-measurement refusal.

Root-only commit boundary: root may commit only automation/m2c_revision_matrix.py, automation/test_m2c_revision_matrix.py, and automation/fixtures/search/m2c_matrix/fixed_benchmark.json with message feat: benchmark current m2c revision. The worker does not build or invoke a live scorer.

### Task 3: Qualify alternate revisions by measured improvement

Files: automation/m2c_revision_matrix.py and automation/test_m2c_revision_matrix.py.

- [ ] Add failing qualification tests:

~~~python
def test_incomplete_baseline_never_qualifies(self):
    result = qualify_revision(
        fixture_report(CURRENT_M2C_REVISION, complete=False),
            fixture_report(fixture_hash("alternate-revision", algorithm="sha1"), complete=True),
    )
    self.assertFalse(result.qualified)
    self.assertEqual(result.reason_code, "baseline_incomplete")

def test_no_unique_or_better_candidate_is_rejected(self):
    result = qualify_revision(
        fixture_report(CURRENT_M2C_REVISION, complete=True),
            fixture_report(fixture_hash("alternate-revision", algorithm="sha1"), unique=0, better=0),
    )
    self.assertFalse(result.qualified)
    self.assertEqual(result.reason_code, "no_unique_or_better_candidate")

def test_mismatched_benchmark_is_refused(self):
    with self.assertRaises(M2CBenchmarkError):
        qualify_revision(
            fixture_report(CURRENT_M2C_REVISION, benchmark_id=fixture_hash("fixed-a")),
            fixture_report(fixture_hash("alternate-revision", algorithm="sha1"), benchmark_id=fixture_hash("fixed-b")),
        )
~~~

- [ ] Run the focused failure:

~~~text
sotn-cmd run_automation run_selftests.py --only test_m2c_revision_matrix.py --jobs 1
~~~

Expected result before implementation: qualification symbols are absent or the new refusal assertions fail.

- [ ] Require complete baseline and alternate reports with equal benchmark and benchmark-artifact IDs, case set, scorer taxonomy, compiler, evaluator, executable/tool, config, target identities, archive identity, provider and tree identities, and canonical integration gate, verified gate-artifact, subset, and queue-evidence identities. Require distinct full revision identities for the compared reports.
- [ ] Count unique candidates only from full source artifact identities absent in the corresponding baseline case. Count better cases only from complete measured ScoreVectors with identical identity fields and strictly lower total score. Do not use revision adjacency or commit order.
- [ ] Produce an immutable qualification record with reason codes baseline_incomplete, alternate_incomplete, identity_mismatch, qualified_unique, qualified_better, or no_unique_or_better_candidate. A qualification never vendors or exposes an alternate itself.
- [ ] Add reversed report order and altered compiler or scorer identity tests. Reversed input must produce the same canonical refusal or qualification bytes.
- [ ] Rerun the same focused command. Expected result: the matrix suite passes with deterministic qualification and typed refusal coverage.

Root-only commit boundary: root may commit only automation/m2c_revision_matrix.py and automation/test_m2c_revision_matrix.py with message feat: gate alternate m2c revisions by benchmark. The worker does not fetch, checkout, or vendor a revision.

### Task 4: Enumerate and run the deterministic revision matrix

Files: automation/m2c_revision_matrix.py and automation/test_m2c_revision_matrix.py.

- [ ] Add failing ordering and deduplication tests:

~~~python
def test_current_revision_is_first_and_ordinals_are_contiguous(self):
    spec = fixture_matrix_spec()
    variants = enumerate_m2c_variants(spec, (fixture_qualified_alternate(),))
    self.assertEqual(variants[0].revision_id, CURRENT_M2C_REVISION)
    self.assertEqual(tuple(item.ordinal for item in variants), tuple(range(len(variants))))

def test_unqualified_alternate_is_refused(self):
    with self.assertRaises(M2CMatrixError):
        enumerate_m2c_variants(
            fixture_matrix_spec(qualified_alternate_revision_ids=(fixture_hash("unqualified-alternate", algorithm="sha1"),)),
            (fixture_unqualified_alternate(),),
        )

def test_identical_candidate_consumes_one_compile_budget(self):
    gate = fixture_gate(multi_record=True)
    receipt = run_m2c_matrix(
        fixture_matrix_spec(budget=2),
        fixture_duplicate_variants(),
        fixture_provider(),
        fixture_evaluator,
        fixture_archive(),
        gate,
    )
    self.assertEqual(receipt.consumed_budget, 1)
    self.assertEqual(len(receipt.compiled_candidate_ids), 1)
    self.assertEqual(len(receipt.deduplicated_variant_ids), 1)

def test_receipt_retains_all_matrix_provenance(self):
    spec = fixture_matrix_spec(budget=2)
    gate = fixture_gate(multi_record=True)
    receipt = run_m2c_matrix(
        spec,
        fixture_duplicate_variants(),
        fixture_provider(),
        fixture_evaluator,
        fixture_archive(),
        gate,
    )
    self.assertEqual(receipt.matrix_id, spec.matrix_id)
    self.assertEqual(receipt.matrix_spec_artifact_id, spec.matrix_spec_artifact_id)
    self.assertEqual(receipt.benchmark_id, spec.benchmark_id)
    self.assertEqual(receipt.benchmark_artifact_id, spec.benchmark_artifact_id)
    self.assertEqual(receipt.integration_gate_id, spec.gate_id)
    self.assertEqual(receipt.integration_gate_artifact_id, spec.integration_gate_artifact_id)
    self.assertEqual(receipt.integration_gate_artifact_id, fixture_gate_artifact_identity(gate))
    self.assertEqual(receipt.subset_identity, spec.subset_identity)
    self.assertEqual(receipt.queue_evidence_identity, spec.queue_evidence_identity)
    self.assertEqual(receipt.provider_identity, spec.provider_identity)
    self.assertEqual(
        receipt.revision_ids,
        tuple(sorted({variant.revision_id for variant in fixture_duplicate_variants()})),
    )
    self.assertEqual(receipt.archive_identity, spec.archive_identity)
    self.assertEqual(receipt.compiler_identity, spec.compiler_identity)
    self.assertEqual(receipt.tool_identity, spec.tool_identity)
    self.assertEqual(receipt.revision_tool_identities, spec.revision_tool_identities)
    self.assertEqual(receipt.evaluator_identity, spec.evaluator_identity)
    self.assertEqual(receipt.config_identity, spec.config_identity)
    self.assertEqual(receipt.scorer_taxonomy_identity, spec.scorer_taxonomy_identity)
    self.assertEqual(receipt.variant_manifest_artifact_id, fixture_hash("variant-manifest"))
    self.assertTrue(receipt.evaluation_artifact_ids)
    self.assertTrue(receipt.deduplication_artifact_id)
~~~

- [ ] Run the focused failure:

~~~text
sotn-cmd run_automation run_selftests.py --only test_m2c_revision_matrix.py --jobs 1
~~~

Expected result before implementation: matrix enumeration and receipt assertions fail because the deterministic matrix is not implemented.

- [ ] Validate that M2CMatrixSpec gate_id, integration_gate_artifact_id, subset_identity, queue_evidence_identity, provider, current-revision tool alias, complete revision_tool_identities map, archive, compiler, evaluator, config, and scorer taxonomy identities match the archived prerequisite. Resolve gate_id to the canonical archived receipt, not to live queue state.
- [ ] Enumerate current revision variants first. Enumerate only qualification records whose benchmark and identity fields match the spec. Sort alternate revision IDs, recipients, exact switch tuples, and context kinds. Assign ordinals after sorting.
- [ ] Derive request_identity from the complete revision, tree, provider, executable/tool, recipient, assembly and context artifact identities, switches, target, compiler, evaluator, config, scorer taxonomy, archive, canonical gate and verified gate-artifact identities, subset, and queue evidence. Retain every variant identity even when its candidate deduplicates.
- [ ] Deduplicate only exact candidate keys containing recipient, source artifact, target identity, compiler identity, config identity, and scorer taxonomy identity. Preserve all supporting variant IDs and provenance. Never normalize identifiers or call equal text from different targets equal.
- [ ] Charge one measured budget unit per actual compile or evaluation. On exhaustion return a typed receipt with completed observations, refusal_code budget_exhausted, and deterministic remaining budget. Do not silently drop variants.
- [ ] Return explicit integration_gate_id, integration_gate_artifact_id, subset_identity, queue_evidence_identity, provider_identity, revision_ids, revision_tool_identities, archive_identity, compiler_identity, current-revision tool alias, evaluator_identity, config_identity, and scorer_taxonomy_identity on M2CMatrixReceipt. Bind those fields, archived matrix spec and benchmark artifacts, ordered variants and variant manifest, candidate source artifacts, evaluation artifacts and score vectors, dedup map, cost measurements, status, and refusal code into receipt_id. Archive and verify the matrix spec, variant manifest, evaluations, deduplication map, and receipt before returning. A replay with the same provider and fixtures must be byte-identical.
- [ ] Rerun:

~~~text
sotn-cmd run_automation run_selftests.py --only test_m2c_revision_matrix.py --jobs 1
~~~

Expected result: 1 focused suite passes, including current-first ordering, exact dedup, qualification, budget, and reversed-input determinism.

Root-only commit boundary: root may commit only automation/m2c_revision_matrix.py and automation/test_m2c_revision_matrix.py with message feat: add deterministic m2c revision matrix. The worker does not build, write a queue record, or edit source.

### Task 5: Build the immutable, lineage-safe tuner dataset

Files: automation/weight_tuner.py, automation/test_weight_tuner.py, automation/fixtures/search/weight_tuner/archived_cases.json, and automation/fixtures/search/weight_tuner/trials.json.

- [ ] Write failing dataset tests:

~~~python
def test_tuner_requires_multi_record_integration_shadow(self):
    with self.assertRaises(TunerDataError):
        build_tuner_dataset(
            fixture_archived_cases(),
            split_seed=17,
            holdout_ratio=0.25,
            gate=fixture_gate(multi_record=False),
            archive=fixture_archive(),
            source_archive_identity=fixture_archive_identity(),
        )

def test_shared_lineage_is_grouped_wholly_into_one_split(self):
    dataset = build_tuner_dataset(
        fixture_archived_cases(shared_lineage=True),
        split_seed=17,
        holdout_ratio=0.25,
        gate=fixture_gate(multi_record=True),
        archive=fixture_archive(),
        source_archive_identity=fixture_archive_identity(),
    )
    lineage_splits = {}
    for case in dataset.cases:
        split = "train" if case.case_id in dataset.train_case_ids else "holdout"
        lineage_splits.setdefault(case.lineage_identity, set()).add(split)
    self.assertTrue(all(len(splits) == 1 for splits in lineage_splits.values()))

def test_insufficient_independent_lineages_are_refused(self):
    with self.assertRaises(TunerDataError):
        build_tuner_dataset(
            fixture_archived_cases(single_lineage=True),
            split_seed=17,
            holdout_ratio=0.25,
            gate=fixture_gate(multi_record=True),
            archive=fixture_archive(),
            source_archive_identity=fixture_archive_identity(),
        )

def test_dataset_retains_canonical_receipt_provenance(self):
    gate = fixture_gate(multi_record=True)
    dataset = build_tuner_dataset(
        fixture_archived_cases(),
        split_seed=17,
        holdout_ratio=0.25,
        gate=gate,
        archive=fixture_archive(),
        source_archive_identity=fixture_archive_identity(),
    )
    self.assertEqual(dataset.integration_gate_id, gate.gate_id)
    self.assertEqual(
        dataset.integration_gate_artifact_id,
        fixture_gate_artifact_identity(gate),
    )
    self.assertEqual(dataset.subset_identity, gate.subset_identity)
    self.assertEqual(dataset.queue_evidence_identity, gate.queue_evidence_identity)
    self.assertEqual(dataset.source_archive_identity, fixture_archive_identity())
    self.assertEqual(
        dataset.source_archive_artifact_id,
        fixture_source_archive_artifact_identity(),
    )
    self.assertEqual(dataset.dataset_artifact_id, fixture_dataset_artifact_identity())
    self.assertEqual(dataset.evaluator_identity, fixture_archived_cases()[0].evaluator_identity)

def test_reversed_case_input_replays_the_same_dataset(self):
    kwargs = dict(
        split_seed=17,
        holdout_ratio=0.25,
        gate=fixture_gate(multi_record=True),
        archive=fixture_archive(),
        source_archive_identity=fixture_archive_identity(),
    )
    self.assertEqual(
        build_tuner_dataset(tuple(reversed(fixture_archived_cases())), **kwargs),
        build_tuner_dataset(fixture_archived_cases(), **kwargs),
    )
~~~

- [ ] Run the focused failure:

~~~text
sotn-cmd run_automation run_selftests.py --only test_weight_tuner.py --jobs 1
~~~

Expected result before implementation: import failure for weight_tuner.py and a failing focused suite.

- [ ] Call the canonical Task 8.2 receipt validator with require_multi_record=True and require a real archive identity. Reject empty case sets, duplicate case IDs, missing or corrupt draft or target artifacts, missing source ledger identities, invalid lineage identities, mixed compiler/tool/evaluator/config/scorer identities, and an archive identity not verified by ContentAddressedArchive.
- [ ] Sort cases by canonical case identity, group by lineage_identity, and use a deterministic hash of split_seed plus lineage identity to assign whole groups to train or holdout. Shared lineage cases are never split. Refuse explicit preassigned split conflicts and enforce both splits when the corpus has enough independent lineages; otherwise return TunerDataError rather than fabricate a split.
- [ ] Define leakage as any lineage, target object identity, source ledger identity, or derived candidate identity crossing splits. Refuse it before any trial runs.
- [ ] Return explicit integration_gate_id, integration_gate_artifact_id, subset_identity, queue_evidence_identity, source_archive_identity, source_archive_artifact_id, compiler_identity, tool_identity, evaluator_identity, config_identity, and scorer_taxonomy_identity on TunerDataset. Archive the canonical case list, all artifact verification results, split assignment, those receipt identities, and the source archive artifact. Derive dataset_id, dataset_artifact_id, and split_identity from these bytes and preserve the exact sorted IDs.
- [ ] Add tests for altered target, compiler, tool, config, scorer, archive, gate, and queue evidence identities. Each must refuse before invoking a trial runner.
- [ ] Rerun:

~~~text
sotn-cmd run_automation run_selftests.py --only test_weight_tuner.py --jobs 1
~~~

Expected result: 1 focused suite passes with deterministic split and typed evidence refusal.

Root-only commit boundary: root may commit only the four Task 5 paths with message feat: add immutable tuner dataset contract. The worker does not read live queue state or source files.

### Task 6: Run fixed trials and rank by exact rediscovery

Files: automation/weight_tuner.py, automation/test_weight_tuner.py, and automation/fixtures/search/weight_tuner/trials.json.

- [ ] Add failing trial and ranking tests:

~~~python
def test_trial_identity_binds_seed_and_iteration_budget(self):
    first = fixture_trial(seed=11, iterations=100)
    second = fixture_trial(seed=12, iterations=100)
    self.assertNotEqual(first.trial_id, second.trial_id)

def test_exact_holdout_rediscovery_beats_lower_nonexact_score(self):
    exact = fixture_trial_result(exact_rediscoveries=2, median_best_score=40, cost_units=50)
    nonexact = fixture_trial_result(exact_rediscoveries=1, median_best_score=1, cost_units=1)
    self.assertEqual(rank_weight_trials((nonexact, exact))[0], exact)

def test_median_score_beats_cost_after_exact_tie(self):
    lower_median_score = fixture_trial_result(exact_rediscoveries=2, median_best_score=10, cost_units=100)
    cheaper = fixture_trial_result(exact_rediscoveries=2, median_best_score=20, cost_units=1)
    self.assertEqual(rank_weight_trials((cheaper, lower_median_score))[0], lower_median_score)

def test_weight_artifact_identity_is_the_final_tie_break(self):
    higher = fixture_trial_result(weight_artifact_identity=fixture_hash("weight-b"))
    lower = fixture_trial_result(weight_artifact_identity=fixture_hash("weight-a"))
    self.assertEqual(rank_weight_trials((higher, lower))[0], lower)
~~~

- [ ] Run the focused failure:

~~~text
sotn-cmd run_automation run_selftests.py --only test_weight_tuner.py --jobs 1
~~~

Expected result before implementation: fixed trial identity and ranking assertions fail.

- [ ] Require each WeightTrialSpec identity to include dataset_id, all five ScoreComponents weights, seed, iterations, compiler, tool, evaluator, config, and scorer taxonomy. Reject a trial that differs only in an omitted identity field.
- [ ] Sort trial specs by trial_id, call the runner once per trial, and retain completed, timed-out, and refused case results with explicit status and measured cost. A runner TypeError is surfaced after one invocation and becomes a typed trial refusal, not a retry.
- [ ] Define exact rediscovery as the candidate object or checksum matching target_object_identity under the same compiler, tool, config, and scorer identities. Do not infer it from a zero-like score or commit relationship.
- [ ] Compute holdout median from the fixed case order and integer score values. Use the total measured cost of train and holdout evaluations. Precompute each canonical weight artifact identity from the trial weights and immutable dataset provenance before ranking. Rank by descending exact rediscoveries, ascending median best score, ascending cost, and ascending immutable weight artifact identity as the final deterministic tie-break required by the specification.
- [ ] Archive every trial spec and result before ranking. A failure is evidence and remains in the report. No trial may change the dataset, source, queue, or existing manifest.
- [ ] Rerun:

~~~text
sotn-cmd run_automation run_selftests.py --only test_weight_tuner.py --jobs 1
~~~

Expected result: 1 focused suite passes with fixed trial identities, one-call runner behavior, cost accounting, and ranking assertions.

Root-only commit boundary: root may commit only automation/weight_tuner.py, automation/test_weight_tuner.py, and automation/fixtures/search/weight_tuner/trials.json with message feat: rank immutable weight trials by rediscovery. The worker does not build or alter matched source.

### Task 7: Publish an immutable report and bind weights to later manifests

Files: automation/weight_tuner.py, automation/test_weight_tuner.py, automation/search_types.py, automation/search-ledger.schema.json, automation/search_coordinator.py, automation/search_recovery.py, automation/test_search_coordinator.py, and automation/test_search_schema.py. Every manifest constructor and serialized manifest must supply the required nullable field explicitly; there is no constructor default that can silently bypass the migration boundary.

- [ ] Add failing adoption tests:

~~~python
import json

from automation.search_types import LedgerEvent, RunManifest, SearchValidationError

def test_report_requires_archived_dataset_and_weight_artifact(self):
    report = fixture_tuning_report(dataset_id=fixture_hash("missing-dataset"))
    with self.assertRaises(WeightTuningError):
        verify_tuning_report(report, fixture_archive())

def test_active_manifest_cannot_adopt_weights(self):
    with self.assertRaises(WeightTuningError):
        bind_weights_to_later_manifest(
            fixture_manifest(),
            fixture_tuning_report(),
            fixture_archive(),
            run_root=fixture_started_run_root(),
        )

def test_changed_compiler_identity_cannot_adopt_weights(self):
    with self.assertRaises(WeightTuningError):
        bind_weights_to_later_manifest(
            fixture_manifest(compiler_identity=fixture_hash("compiler-other")),
            fixture_tuning_report(),
            fixture_archive(),
            run_root=fixture_unstarted_run_root(),
        )

def test_report_retains_dataset_and_receipt_provenance(self):
    report = fixture_tuning_report()
    gate = fixture_gate(multi_record=True)
    self.assertEqual(report.source_archive_identity, fixture_archive_identity())
    self.assertEqual(report.split_identity, fixture_split_identity())
    self.assertEqual(report.integration_gate_id, gate.gate_id)
    self.assertEqual(
        report.integration_gate_artifact_id,
        fixture_gate_artifact_identity(gate),
    )
    self.assertEqual(report.subset_identity, gate.subset_identity)
    self.assertEqual(report.queue_evidence_identity, gate.queue_evidence_identity)
    self.assertEqual(report.report_archive_identity, fixture_report_archive_identity())
    self.assertEqual(report.dataset_artifact_id, fixture_dataset_artifact_identity())
    self.assertEqual(
        report.source_archive_artifact_id,
        fixture_source_archive_artifact_identity(),
    )
    self.assertEqual(
        report.selected_trial_result_artifact_id,
        report.trial_result_artifact_ids[0],
    )
    self.assertEqual(
        report.weight_artifact_id,
        report.weight_artifact.artifact.content_hash,
    )
    self.assertTrue(report.trial_result_artifact_ids)

def test_historical_manifest_without_weight_field_requires_migration(self):
    raw = fixture_legacy_manifest_bytes()
    before = bytes(raw)
    with self.assertRaises(SearchValidationError):
        RunManifest.from_json(
            raw.decode("utf-8")
        )
    self.assertEqual(raw, before)

def test_historical_event_without_weight_field_requires_migration(self):
    raw = fixture_legacy_event_bytes()
    before = bytes(raw)
    with self.assertRaises(SearchValidationError):
        LedgerEvent.from_json(raw.decode("utf-8"))
    self.assertEqual(raw, before)

def test_new_manifest_serializes_nullable_weight_field_explicitly(self):
    document = json.loads(fixture_manifest().to_json())
    self.assertIn("weight_artifact_identity", document)
    self.assertIsNone(document["weight_artifact_identity"])

def test_new_manifest_round_trips_the_exact_weight_artifact_hash(self):
    report = fixture_tuning_report()
    adopted = bind_weights_to_later_manifest(
        fixture_manifest(),
        report,
        fixture_archive(),
        run_root=fixture_unstarted_run_root(),
    )
    loaded = RunManifest.from_json(adopted.to_json())
    self.assertEqual(
        loaded.weight_artifact_identity,
        report.weight_artifact.artifact.content_hash,
    )
~~~

- [ ] Run the focused failure:

~~~text
sotn-cmd run_automation run_selftests.py --only test_weight_tuner.py --only test_search_coordinator.py --jobs 2
~~~

Expected result before implementation: report verification and manifest fields are absent or the adoption refusal assertions fail.

- [ ] Archive the selected WeightArtifact first, then archive the canonical WeightTuningReport. Return and bind dataset_artifact_id, source_archive_identity, source_archive_artifact_id, split_identity, integration_gate_id, integration_gate_artifact_id, subset_identity, queue_evidence_identity, report_archive_identity, trial IDs, trial_result_artifact_ids, selected trial, selected_trial_result_artifact_id, weight_artifact_id, the complete WeightArtifact, compiler, tool, evaluator, config, scorer taxonomy, ranking metrics, and cost into report_id. Refuse a report whose archived bytes do not hash to report_id.
- [ ] Reuse the existing RunManifest.queue_evidence_identity binding without adding or recomputing that field. At run creation, the coordinator continues to resolve explicit record IDs through scheduler-owned todo evidence, archive the status-bound evidence, and bind that existing identity alongside subset_identity. Resume verifies those archived artifacts and never selects current queue state.
- [ ] Add `RunManifest.weight_artifact_identity: Optional[str]` as the final required frozen dataclass field. New manifests serialize `null` when no tuner artifact is adopted, or a verified `sha256:<64 lowercase hex>` content hash when one is adopted. `bind_weights_to_later_manifest` receives the archive and proposed run root, calls `verify_tuning_report`, and refuses if `manifest.json` or `ledger.jsonl` already exists. The coordinator invokes it only before `_write_manifest` and `run_started`; it does not trust a caller-supplied active/inactive boolean. Adoption also requires identical compiler/tool/config/scorer identities and refuses mutation of source, queue, old manifest, or archived report.
- [ ] Update `search_types.SCHEMA_VERSION` and the event-schema `const` exactly from `1.0.0` to `1.1.0`, and bind the new schema identity to the content hash of that schema while leaving the subset schema at `1.0.0`. The new schema lists `weight_artifact_identity` in `run_manifest.required` and accepts only `null` or a `sha256:<64 lowercase hex>` hash. Update every manifest and event fixture and constructor call to emit explicit `null` or a verified hash; no new fixture may omit the property. `RunManifest.from_dict` requires the field, so a pre-migration manifest or event fails with a typed `SearchValidationError` migration refusal instead of being normalized. Update `search_recovery` identity comparisons and the coordinator's immutable manifest write/compare path to include the field; reject before `_write_manifest` and never rewrite old bytes. Add tests for old-schema refusal with unchanged bytes, new-manifest explicit-null serialization, new-schema round-trip, altered or missing artifact hashes, each identity independently, and resume after live queue changes.
- [ ] Enforce integration-first behavior in the coordinator: a one-record shadow can produce a receipt, but matrix and tuner calls require the bounded multi-record receipt. Legacy and instrumented runs cannot overlap. A score-zero proposal enters the existing full build and verify gate once; an unchanged valid receipt may be reused on retry without repeated unchanged build.
- [ ] Rerun:

~~~text
sotn-cmd run_automation run_selftests.py --only test_weight_tuner.py --only test_search_coordinator.py --jobs 2
~~~

Expected result: 2 focused suites pass with immutable publication, separate subset and queue evidence identities, inactive-manifest-only adoption, and coordinator refusal coverage.

Root-only commit boundary: root may commit only the six listed Task 7 paths with message feat: publish immutable tuner weights for later manifests. The worker does not run a build, invoke a queue writer, or edit src.

### Task 8: Execute end-to-end acceptance and stop at root review

Files: automation/test_m2c_revision_provider.py, automation/test_m2c_revision_matrix.py, automation/test_weight_tuner.py, and automation/test_search_coordinator.py, using the canonical Task 8.2 integration receipt and archived artifact.

- [ ] Add one end-to-end fixture test that creates a complete integration receipt, resolves the exact current revision, runs the fixed current benchmark, qualifies one alternate only when the fixture has a unique or better candidate, enumerates current-first variants, builds a lineage-safe dataset, runs fixed trials, and binds the selected artifact to an inactive later manifest.

~~~python
def test_current_first_matrix_and_later_manifest_adoption(self):
    gate = fixture_gate(multi_record=True)
    baseline = run_fixed_benchmark(
        fixture_benchmark(),
        fixture_revision(CURRENT_M2C_REVISION),
        fixture_provider(),
        fixture_evaluator,
        fixture_archive(),
        archive_identity=fixture_archive_identity(),
        gate=gate,
    )
    alternate = run_fixed_benchmark(
        fixture_benchmark(),
        fixture_revision(fixture_alternate_revision_id()),
        fixture_provider(),
        fixture_evaluator,
        fixture_archive(),
        archive_identity=fixture_archive_identity(),
        gate=gate,
    )
    qualification = qualify_revision(baseline, alternate)
    spec = fixture_matrix_spec(
        qualified_alternate_revision_ids=(alternate.revision_id,),
    )
    variants = enumerate_m2c_variants(
        spec,
        (qualification,),
    )
    self.assertEqual(variants[0].revision_id, CURRENT_M2C_REVISION)
    receipt = run_m2c_matrix(
        spec,
        variants,
        fixture_provider(),
        fixture_evaluator,
        fixture_archive(),
        gate=gate,
    )
    self.assertGreater(receipt.consumed_budget, 0)
    dataset = build_tuner_dataset(
        fixture_archived_cases(),
        split_seed=17,
        holdout_ratio=0.25,
        gate=gate,
        archive=fixture_archive(),
        source_archive_identity=fixture_archive_identity(),
    )
    report = tune_weights(
        dataset,
        fixture_trials(dataset.dataset_id),
        fixture_trial_runner(),
        fixture_archive(),
        gate=gate,
        report_archive_identity=fixture_report_archive_identity(),
    )
    adopted = bind_weights_to_later_manifest(
        fixture_manifest(),
        report,
        fixture_archive(),
        run_root=fixture_unstarted_run_root(),
    )
    self.assertEqual(adopted.weight_artifact_identity, report.weight_artifact.artifact.content_hash)
~~~

- [ ] Run the exact focused acceptance command once after all final edits:

~~~text
sotn-cmd run_automation run_selftests.py --only test_m2c_revision_provider.py --only test_m2c_revision_matrix.py --only test_weight_tuner.py --jobs 3
~~~

Expected result: 3 focused suites pass. The test run is read-only with respect to queue, source, git, and build output.

- [ ] Review refusal coverage for missing or corrupt archive bytes, ambiguous duplicate case evidence, altered revision or commit identity, dirty or attached provider state, missing measurement, scorer or compiler mismatch, unqualified alternate, budget exhaustion, leakage, internally misbound queue evidence, active-manifest adoption, legacy overlap, and repeated unchanged build. Also verify that a different valid gate creates distinct downstream identities instead of being rejected.
- [ ] Stop for root review. Root runs any broader automation tests required by the parent implementation plan, owns the exact explicit commit paths, and owns all build, oracle, roadmap, queue, and push work.

Root-only commit boundary: root may commit only the implementation and test paths that passed review. No worker commit, build, git operation, queue mutation, source edit, or existing-document edit is part of this plan.

## Verification and Handoff

The worker implementing this plan reports the exact focused command, pass count, refusal cases exercised, archive identities, and any unresolved contract question. The worker leaves the tree uncommitted. Root then performs the repository-level automation checks, reviews the coordinator and schema diff, stages explicit paths, and handles any required build or oracle gate. The worker does not claim a matched result from a score, a benchmark report, or a tuner report.

## Plan Self-Review

- Spec coverage: integration-first 8.1, 8.2, and 8.3 prerequisite, canonical Task 8.2 one-record then bounded multi-record shadow receipt, selected lanes, frozen explicit subset, separate subset_identity and queue_evidence_identity, no queue fallback or drift, legacy exclusion, coordinator ownership, typed result and refusal proposals, score-zero handoff, exact scorer taxonomy, proven draft-landed evidence, fixed current-first m2c benchmark, qualified alternates, immutable donor and trial provenance, Task 9.6 archive dataset, lineage-safe split, exact rediscovery ranking, and later-manifest-only weights are all stated.
- Placeholder scan: the plan contains no unassigned task, open-ended implementation note, or instruction to fill in missing behavior. Every task names files, signatures, a failing test, an exact command, an expected result, implementation constraints, a passing command, and a root-only commit boundary.
- Type consistency: all cross-task names are defined in Shared Exact Interfaces or in the task that introduces their fixture module, with IntegrationGateReceipt intentionally imported from the canonical Task 8.2 runtime. M2CInvocation binds tree, provider, executable/tool, compiler, evaluator, scorer, config, gate, subset, queue, and archive identities; M2CEvaluation carries ScoreVector and cost_units. Qualification consumes reports. Matrix variants consume qualifications, while the matrix spec and receipt retain the current executable alias plus the complete revision-to-executable map. Tuner reports consume TunerDataset and WeightTrialResult and explicitly retain source archive, split, gate artifact, subset, queue, compiler, tool, evaluator, config, scorer, selected trial-result, and weight-artifact identities. Benchmark reports and matrix receipts carry their verified gate artifact and all benchmark/archive/compiler/tool/evaluator/config/scorer provenance. Manifest adoption consumes WeightTuningReport, sets RunManifest.weight_artifact_identity to str | None under the exact 1.1.0 migration contract, and returns a later RunManifest. The existing queue_evidence_identity remains unchanged.
- Determinism audit: canonical sorting, fixture_hash content identities, full provenance, fixed seeds, fixed iterations, immutable archives, no retry-after-invocation, no mtime or path hashing, no commit adjacency, and reversed-input tests are required.
- Scope audit: the only file created by this planning task is docs/superpowers/plans/2026-08-28-m2c-matrix-weight-tuner.md. Implementation workers must consume the canonical Task 8.2 receipt rather than create a parallel gate module, use only the paths in the responsibility map, and root must approve any coordinator or schema change before staging.

Plan complete and saved at docs/superpowers/plans/2026-08-28-m2c-matrix-weight-tuner.md. Execution is intentionally left to root review, which can dispatch the checked tasks sequentially or run them inline with the listed focused commands.
