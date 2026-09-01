from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ArtifactRef, ContentAddressedArchive
from automation.m2c_revision_matrix import M2CMatrixReceipt
from automation.m2c_revision_provider import (
    CURRENT_M2C_REVISION,
    M2CDraftPayload,
    M2CProviderError,
    M2CRevisionIdentity,
)
from automation.search_generated_lanes import (
    ArchivedTargetInput,
    GeneratedLaneProvider,
    GeneratedProviderArtifactError,
    GeneratedProviderBudgetError,
    GeneratedProviderDeterminismError,
    GeneratedProviderInputError,
    GeneratedProviderSubsetViolation,
    GeneratedProviderUnavailable,
    M2CRevision,
    M2CRevisionMatrix,
    SynthesisBound,
    bounded_synthesis_adapter,
    build_bounded_synthesis_provider,
    build_m2c_ensemble_provider,
    generated_lane_adapters,
)
from automation.search_lanes import Recipient
from automation.search_supervisor import EVALUATOR_TOOL_KEY
from automation.search_types import (
    LANES,
    Budget,
    RunManifest,
    canonical_subset_identity,
    hash_bytes,
    hash_canonical,
)


def digest(value: str) -> str:
    return hash_bytes(value.encode("utf-8"))


def manifest(*record_ids: str, m2c_budget: int = 8, synthesis_budget: int = 8) -> RunManifest:
    ids = tuple(sorted(record_ids))
    return RunManifest(
        run_id="generated-lanes",
        created_at="2026-08-31T00:00:00Z",
        parent_run=None,
        queue_record_ids=ids,
        function_ids=ids,
        subset_identity=canonical_subset_identity(ids),
        queue_evidence_identity=digest("queue:" + ",".join(ids)),
        selected_lanes=LANES,
        source_identity=digest("source"),
        target_identities={item: digest("target:" + item) for item in ids},
        compiler_identity=digest("compiler"),
        tool_identities={
            **{lane: digest("tool:" + lane) for lane in LANES},
            EVALUATOR_TOOL_KEY: digest("evaluator"),
        },
        config_identity=digest("config"),
        schema_identity=digest("schema"),
        run_seed=11,
        epoch_size=4,
        frontier_cap=16,
        coordinator_budget=Budget("tasks", 32, 0),
        lane_budgets={
            lane: Budget(
                "attempts",
                m2c_budget if lane == "m2c_ensemble" else synthesis_budget if lane == "bounded_synthesis" else 8,
                0,
            )
            for lane in LANES
        },
        tier_order=(
            "exact_deterministic",
            "structural_dependency",
            "cheap_generated",
            "compiler_guided",
            "model",
        ),
    )


def target_fixture(
    archive: ContentAddressedArchive,
    record_id: str = "us:ST:fn",
    *,
    expressions: tuple[str, ...] = ("x + 1",),
    statements: tuple[str, ...] = ("x = x + 1",),
    declaration_shapes: tuple[str, ...] = (),
    control_flow: tuple[str, ...] = ("if",),
) -> ArchivedTargetInput:
    assembly = b"fn:\n  move $v0, $a0\n  jr $ra\n"
    artifact = archive.put_bytes(
        assembly,
        category="target-assembly",
        suffix=".s",
        media_type="text/x-asm",
    )
    return ArchivedTargetInput(
        recipient_id=record_id,
        target_identity=digest("target:" + record_id),
        target_artifact=artifact,
        target_bytes=assembly,
        symbol="fn",
        declarations={
            "return_type": "int",
            "parameters": [{"type": "int", "name": "x"}],
        },
        expressions=expressions,
        statements=statements,
        declaration_shapes=declaration_shapes,
        control_flow=control_flow,
        platform=record_id.split(":", 1)[0],
    )


def revision_fixture(
    archive: ContentAddressedArchive,
    label: str,
    outputs: tuple[str, ...],
    *,
    current: bool = False,
    qualified: bool = True,
    available: bool = True,
) -> M2CRevision:
    source = archive.put_bytes(
        ("m2c source " + label).encode("utf-8"),
        category="m2c-revision-sources",
        suffix=".bin",
    )
    tool = archive.put_bytes(
        ("m2c tool " + label).encode("utf-8"),
        category="m2c-revision-tools",
        suffix=".bin",
    )
    revision_id = CURRENT_M2C_REVISION if current else hash_bytes(
        ("revision:" + label).encode("utf-8")
    ).removeprefix("sha256:")[:40]
    identity = M2CRevisionIdentity(
        revision_id=revision_id,
        tree_identity=digest("tree:" + label),
        provider_identity=digest("provider"),
        executable_identity=digest("executable:" + label),
        config_identity=digest("config"),
        clean=True,
        detached=True,
    )
    return M2CRevision(
        revision_identity=identity,
        source_artifact=source if available else None,
        tool_artifact=tool if available else None,
        current=current,
        qualified=qualified,
        available=available,
        unavailable_reason="fixture dependency is not installed" if not available else "",
        label=label,
    )


class FakeM2CProvider:
    def __init__(
        self,
        archive: ContentAddressedArchive,
        revisions: tuple[M2CRevision, ...],
        outputs: dict[str, bytes],
    ) -> None:
        self.archive = archive
        self.revisions = {item.revision_id: item.revision_identity for item in revisions}
        self.outputs = outputs
        self.calls = []

    def resolve_revision(self, revision_id: str) -> M2CRevisionIdentity:
        return self.revisions[revision_id]

    def generate_draft(self, invocation, *, assembly, contexts):
        self.calls.append((invocation, assembly, contexts))
        source = self.outputs[invocation.revision_id]
        reference = self.archive.put_bytes(
            source,
            category="provider-output",
            suffix=".c",
            media_type="text/x-c",
        )
        return M2CDraftPayload(invocation.invocation_id, invocation.revision_id, reference)


class FabricatedOutputM2CProvider(FakeM2CProvider):
    def generate_draft(self, invocation, *, assembly, contexts):
        self.calls.append((invocation, assembly, contexts))
        source = b"int fn(int x) { return 99; }\n"
        digest_value = hash_bytes(source)
        reference = ArtifactRef(
            digest_value,
            f"artifacts/provider-output/{digest_value.removeprefix('sha256:')}.c",
            "text/x-c",
            len(source),
        )
        return M2CDraftPayload(invocation.invocation_id, invocation.revision_id, reference)


class MismatchedIdentityM2CProvider(FakeM2CProvider):
    def resolve_revision(self, revision_id: str) -> M2CRevisionIdentity:
        identity = super().resolve_revision(revision_id)
        return replace(identity, provider_identity=digest("mismatched-provider"))


def provider_fixture(
    archive: ContentAddressedArchive,
    revisions: tuple[M2CRevision, ...],
    outputs_by_label: dict[str, str],
) -> FakeM2CProvider:
    return FakeM2CProvider(
        archive,
        revisions,
        {
            item.revision_id: outputs_by_label[item.label].encode("utf-8")
            for item in revisions
            if item.label in outputs_by_label
        },
    )



class GeneratedLaneTests(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    def matrix_contract(
        self,
        archive: ContentAddressedArchive,
        typed_manifest: RunManifest,
        revisions: tuple[M2CRevision, ...],
        *,
        scorer_identity: str | None = None,
        gate_label: str = "prior-gate",
        status: str = "complete",
        refusal_code: str | None = None,
    ) -> dict[str, object]:
        """Create a complete archived prior-run receipt for lane tests."""

        def put(category: str, label: str) -> ArtifactRef:
            return archive.put_json(
                {"fixture": label, "prior_run_id": "qualification-run"},
                category=category,
            )

        gate_artifact = put("receipts", gate_label)
        benchmark_artifact = put("m2c-benchmarks", "benchmark")
        spec_artifact = put("m2c-matrix-specs", "matrix-spec")
        variant_manifest_artifact = put("m2c-variant-manifests", "variant-manifest")
        evaluation_artifact = put("m2c-evaluations", "evaluation")
        deduplication_artifact = put("m2c-deduplication", "deduplication")
        compiled_artifact = put("m2c-drafts", "compiled-candidate")
        revision_ids = tuple(sorted(item.revision_id for item in revisions))
        current = next(item for item in revisions if item.current)
        provider_identities = {item.provider_identity for item in revisions}
        self.assertEqual(len(provider_identities), 1)
        scorer = scorer_identity or digest("scorer-taxonomy")
        payload = {
            "matrix_id": digest("matrix:" + ",".join(revision_ids)),
            "matrix_spec_artifact_id": spec_artifact.content_hash,
            "benchmark_id": benchmark_artifact.content_hash,
            "benchmark_artifact_id": benchmark_artifact.content_hash,
            "integration_gate_id": digest(gate_label),
            "integration_gate_artifact_id": gate_artifact.content_hash,
            "subset_identity": digest("prior-subset:" + gate_label),
            "queue_evidence_identity": digest("prior-queue:" + gate_label),
            "provider_identity": next(iter(provider_identities)),
            "revision_ids": revision_ids,
            "revision_tool_identities": tuple(
                sorted((item.revision_id, item.executable_identity) for item in revisions)
            ),
            "archive_identity": digest("archive"),
            "compiler_identity": typed_manifest.compiler_identity,
            "tool_identity": current.executable_identity,
            "evaluator_identity": typed_manifest.tool_identities[EVALUATOR_TOOL_KEY],
            "config_identity": typed_manifest.config_identity,
            "scorer_taxonomy_identity": scorer,
            "variant_ids": (digest("variant-a"), digest("variant-b")),
            "variant_manifest_artifact_id": variant_manifest_artifact.content_hash,
            "evaluation_artifact_ids": (evaluation_artifact.content_hash,),
            "deduplication_artifact_id": deduplication_artifact.content_hash,
            "compiled_candidate_ids": (compiled_artifact.content_hash,),
            "deduplicated_variant_ids": (digest("variant-a"),),
            "consumed_budget": 1,
            "remaining_budget": 1,
            "status": status,
            "refusal_code": refusal_code,
        }
        receipt = M2CMatrixReceipt(
            receipt_id=hash_canonical(
                {"protocol": "sotn-m2c-matrix-receipt-v1", **payload}
            ),
            **payload,
        )
        archive.put_json(
            receipt.identity_payload(),
            category="m2c-matrix-receipts",
        )
        return {
            "matrix_receipt": receipt,
            "evaluator_identity": receipt.evaluator_identity,
            "scorer_taxonomy_identity": receipt.scorer_taxonomy_identity,
            "runner_identities": {
                item.revision_id: item.provider_identity for item in revisions
            },
        }

    def qualified_pair(
        self,
        archive: ContentAddressedArchive,
        *,
        current_output: str = "int fn(int x) { return x; }\n",
        alternate_output: str = "int fn(int x) { return x + 1; }\n",
        current_label: str = "reva",
        alternate_label: str = "revb",
    ) -> tuple[tuple[M2CRevision, ...], dict[str, str]]:
        current = revision_fixture(
            archive, current_label, (current_output,), current=True
        )
        alternate = revision_fixture(archive, alternate_label, (alternate_output,))
        return (current, alternate), {
            current_label: current_output,
            alternate_label: alternate_output,
        }

    def test_m2c_returns_ordinary_deterministic_candidates_with_complete_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = replace(
                manifest("us:ST:fn"), run_id="active-current-run"
            )
            target = target_fixture(archive)
            context = archive.put_bytes(
                b"extern int helper(int);\n",
                category="target-context",
                suffix=".h",
                media_type="text/x-c",
            )
            target = replace(target, context_artifacts=(context,))
            revisions, outputs = self.qualified_pair(archive)
            contract = self.matrix_contract(archive, typed_manifest, revisions)
            provider_impl = provider_fixture(archive, revisions, outputs)
            provider = build_m2c_ensemble_provider(
                typed_manifest,
                {target.recipient_id: target},
                revisions,
                archive=archive,
                provider=provider_impl,
                archive_identity=digest("archive"),
                **contract,
            )
            recipient = Recipient(target.recipient_id, "ST", "fn")
            first = provider.callback(recipient)
            second = provider.callback(recipient)
            self.assertEqual(first, second)
            self.assertEqual(first["attempts"], 2)
            self.assertEqual(len(first["candidates"]), 2)
            self.assertEqual(
                tuple(item.candidate_id for item in first["candidates"]),
                tuple(sorted(item.candidate_id for item in first["candidates"])),
            )
            self.assertEqual(first["completion_reason"], "matched_pending_oracle")
            self.assertTrue(first["input_identities"])
            invocation = provider_impl.calls[0][0]
            self.assertEqual(invocation.assembly_artifact, target.target_artifact)
            self.assertEqual(invocation.context_artifacts, target.context_artifacts)
            self.assertEqual(provider_impl.calls[0][2], (b"extern int helper(int);\n",))
            self.assertEqual(invocation.archive_identity, digest("archive"))
            self.assertEqual(invocation.config_identity, typed_manifest.config_identity)
            revisions_by_id = {item.revision_id: item for item in revisions}
            self.assertEqual(
                invocation.tool_identity,
                revisions_by_id[invocation.revision_id].executable_identity,
            )
            self.assertEqual(
                invocation.evaluator_identity,
                typed_manifest.tool_identities[EVALUATOR_TOOL_KEY],
            )
            self.assertNotEqual(invocation.tool_identity, invocation.evaluator_identity)
            self.assertEqual(invocation.scorer_taxonomy_identity, digest("scorer-taxonomy"))
            self.assertEqual(
                invocation.integration_gate_id,
                provider.matrix_receipt.integration_gate_id,
            )
            self.assertEqual(
                invocation.integration_gate_artifact_id,
                provider.matrix_receipt.integration_gate_artifact_id,
            )
            self.assertEqual(
                invocation.subset_identity,
                provider.matrix_receipt.subset_identity,
            )
            self.assertEqual(
                invocation.queue_evidence_identity,
                provider.matrix_receipt.queue_evidence_identity,
            )
            self.assertIsNone(provider.integration_gate)
            for edge in first["provenance"]:
                self.assertEqual(edge["recipient_id"], target.recipient_id)
                self.assertIn("provider_identity", edge)
                self.assertIn("target_artifact_identity", edge)

    def test_m2c_revision_order_and_duplicate_outputs_replay_identically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            target = target_fixture(archive)
            revision_a = revision_fixture(
                archive, "reva", ("int fn(int x) { return x; }\n",), current=True
            )
            revision_b = revision_fixture(
                archive, "revb", ("int fn(int x) { return x + 1; }\n",)
            )
            revisions = (revision_a, revision_b)
            outputs = {
                "reva": "int fn(int x) { return x; }\n",
                "revb": "int fn(int x) { return x + 1; }\n",
            }
            contract = self.matrix_contract(archive, typed_manifest, revisions)
            forward = build_m2c_ensemble_provider(
                typed_manifest,
                {target.recipient_id: target},
                (revision_a, revision_b),
                archive=archive,
                provider=provider_fixture(archive, revisions, outputs),
                archive_identity=digest("archive"),
                **contract,
            )
            reverse = build_m2c_ensemble_provider(
                typed_manifest,
                {target.recipient_id: target},
                (revision_b, revision_a),
                archive=archive,
                provider=provider_fixture(archive, revisions, outputs),
                archive_identity=digest("archive"),
                **contract,
            )
            recipient = Recipient(target.recipient_id, "ST", "fn")
            self.assertEqual(forward.callback(recipient), reverse.callback(recipient))
            self.assertEqual(forward.provider_identity, reverse.provider_identity)
            self.assertTrue(forward.revisions[0].current)
            self.assertEqual(
                tuple(item.label for item in forward.revisions),
                ("current", "alternate_" + revision_b.revision_id[:12]),
            )

    def test_m2c_revision_identity_is_typed_exact_and_round_trippable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            revision = revision_fixture(
                archive,
                "reva",
                ("int fn(int x) { return x; }\n",),
                current=True,
            )
            restored = M2CRevision.from_dict(revision.to_dict())
            self.assertEqual(restored, revision)
            with self.assertRaises(TypeError):
                M2CRevision(  # type: ignore[call-arg]
                    revision_identity=revision.revision_identity,
                    runner=lambda _target: (),
                )
            with self.assertRaises(M2CProviderError):
                M2CRevisionIdentity(
                    revision_id="a" * 64,
                    tree_identity=digest("tree"),
                    provider_identity=digest("provider"),
                    executable_identity=digest("executable"),
                    config_identity=digest("config"),
                    clean=True,
                    detached=True,
                )

    def test_m2c_provider_record_reconstructs_without_invoking_provider(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            target = target_fixture(archive)
            revisions, outputs = self.qualified_pair(archive)
            provider_impl = provider_fixture(archive, revisions, outputs)
            contract = self.matrix_contract(archive, typed_manifest, revisions)
            provider = build_m2c_ensemble_provider(
                typed_manifest,
                {target.recipient_id: target},
                revisions,
                archive=archive,
                provider=provider_impl,
                archive_identity=digest("archive"),
                **contract,
            )
            record = provider.to_dict()
            before_calls = len(provider_impl.calls)
            before_paths = tuple(sorted(
                str(path.relative_to(Path(directory)))
                for path in Path(directory).rglob("*")
                if path.is_file()
            ))
            restored = GeneratedLaneProvider.from_dict(record, archive=archive)
            recipient = Recipient(target.recipient_id, "ST", "fn")
            self.assertEqual(provider.callback(recipient), restored.callback(recipient))
            self.assertEqual(provider.to_dict(), restored.to_dict())
            self.assertEqual(len(provider_impl.calls), before_calls)
            self.assertEqual(
                tuple(sorted(
                    str(path.relative_to(Path(directory)))
                    for path in Path(directory).rglob("*")
                    if path.is_file()
                )),
                before_paths,
            )

    def test_m2c_requires_prior_matrix_receipt_and_explicit_identity_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            target = target_fixture(archive)
            revisions, outputs = self.qualified_pair(archive)
            common = {
                "archive": archive,
                "provider": provider_fixture(archive, revisions, outputs),
                "archive_identity": digest("archive"),
            }
            with self.assertRaises(GeneratedProviderInputError):
                build_m2c_ensemble_provider(
                    typed_manifest,
                    {target.recipient_id: target},
                    revisions,
                    matrix_receipt=None,
                    **common,
                )
            contract = self.matrix_contract(archive, typed_manifest, revisions)
            with self.assertRaises(GeneratedProviderInputError):
                build_m2c_ensemble_provider(
                    typed_manifest,
                    {target.recipient_id: target},
                    revisions,
                    integration_gate=lambda _target: (),
                    **contract,
                    **common,
                )
            forged_evaluator = dict(contract)
            forged_evaluator.pop("evaluator_identity")
            with self.assertRaises(GeneratedProviderDeterminismError):
                build_m2c_ensemble_provider(
                    typed_manifest,
                    {target.recipient_id: target},
                    revisions,
                    evaluator_identity=digest("forged-evaluator"),
                    **forged_evaluator,
                    **common,
                )
            forged_scorer = dict(contract)
            forged_scorer.pop("scorer_taxonomy_identity")
            with self.assertRaises(GeneratedProviderDeterminismError):
                build_m2c_ensemble_provider(
                    typed_manifest,
                    {target.recipient_id: target},
                    revisions,
                    scorer_taxonomy_identity=digest("forged-scorer"),
                    **forged_scorer,
                    **common,
                )

    def test_m2c_rejects_foreign_or_forged_qualification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            foreign_manifest = manifest("hd:ST:other")
            target = target_fixture(archive)
            revisions, outputs = self.qualified_pair(archive)
            foreign_revisions, _foreign_outputs = self.qualified_pair(
                archive,
                alternate_label="revc",
                alternate_output="int fn(int x) { return x - 1; }\n",
            )
            foreign_contract = self.matrix_contract(
                archive, foreign_manifest, foreign_revisions, gate_label="foreign-gate"
            )
            with self.assertRaises(GeneratedProviderSubsetViolation):
                build_m2c_ensemble_provider(
                    typed_manifest,
                    {target.recipient_id: target},
                    revisions,
                    archive=archive,
                    provider=provider_fixture(archive, revisions, outputs),
                    archive_identity=digest("archive"),
                    **foreign_contract,
                )
            contract = self.matrix_contract(archive, typed_manifest, revisions)
            forged_contract = dict(contract)
            forged_contract.pop("evaluator_identity")
            with self.assertRaises(GeneratedProviderDeterminismError):
                build_m2c_ensemble_provider(
                    typed_manifest,
                    {target.recipient_id: target},
                    revisions,
                    evaluator_identity=digest("forged-evaluator"),
                    archive=archive,
                    provider=provider_fixture(archive, revisions, outputs),
                    archive_identity=digest("archive"),
                    **forged_contract,
                )

    def test_m2c_scorer_and_qualification_bindings_change_provider_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            target = target_fixture(archive)
            revisions, outputs = self.qualified_pair(archive)
            first_contract = self.matrix_contract(archive, typed_manifest, revisions)
            first = build_m2c_ensemble_provider(
                typed_manifest,
                {target.recipient_id: target},
                revisions,
                archive=archive,
                provider=provider_fixture(archive, revisions, outputs),
                archive_identity=digest("archive"),
                **first_contract,
            )
            second_contract = self.matrix_contract(
                archive,
                typed_manifest,
                revisions,
                scorer_identity=digest("alternate-taxonomy"),
                gate_label="alternate-gate",
            )
            second = build_m2c_ensemble_provider(
                typed_manifest,
                {target.recipient_id: target},
                revisions,
                archive=archive,
                provider=provider_fixture(archive, revisions, outputs),
                archive_identity=digest("archive"),
                **second_contract,
            )
            self.assertNotEqual(first.provider_identity, second.provider_identity)
            self.assertNotEqual(
                first.matrix_receipt.receipt_id,
                second.matrix_receipt.receipt_id,
            )

    def test_m2c_reconstruction_rejects_forged_or_corrupt_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            target = target_fixture(archive)
            revisions, outputs = self.qualified_pair(archive)
            provider = build_m2c_ensemble_provider(
                typed_manifest,
                {target.recipient_id: target},
                revisions,
                archive=archive,
                provider=provider_fixture(archive, revisions, outputs),
                archive_identity=digest("archive"),
                **self.matrix_contract(archive, typed_manifest, revisions),
            )
            forged = provider.to_dict()
            forged["matrix_receipt"] = {
                **forged["matrix_receipt"],
                "matrix_id": digest("forged-matrix"),
            }
            with self.assertRaises(GeneratedProviderArtifactError):
                GeneratedLaneProvider.from_dict(forged, archive=archive)
            corrupted = provider.to_dict()
            receipt = provider.matrix_receipt
            assert receipt is not None
            gate_candidates = list((Path(directory) / "artifacts" / "receipts").glob(
                receipt.integration_gate_artifact_id.removeprefix("sha256:") + "*"
            ))
            self.assertEqual(len(gate_candidates), 1)
            gate_candidates[0].write_bytes(b"corrupt")
            with self.assertRaises(GeneratedProviderArtifactError):
                GeneratedLaneProvider.from_dict(corrupted, archive=archive)

    def test_m2c_refuses_fabricated_output_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            target = target_fixture(archive)
            revisions, _outputs = self.qualified_pair(archive)
            provider_impl = FabricatedOutputM2CProvider(
                archive,
                revisions,
                {item.revision_id: b"unused" for item in revisions},
            )
            with self.assertRaises(GeneratedProviderArtifactError):
                build_m2c_ensemble_provider(
                    typed_manifest,
                    {target.recipient_id: target},
                    revisions,
                    archive=archive,
                    provider=provider_impl,
                    archive_identity=digest("archive"),
                    **self.matrix_contract(archive, typed_manifest, revisions),
                )

    def test_m2c_refuses_provider_revision_binding_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            target = target_fixture(archive)
            revisions, outputs = self.qualified_pair(archive)
            provider_impl = MismatchedIdentityM2CProvider(
                archive,
                revisions,
                {
                    item.revision_id: outputs[item.label].encode("utf-8")
                    for item in revisions
                },
            )
            with self.assertRaises(GeneratedProviderDeterminismError):
                build_m2c_ensemble_provider(
                    typed_manifest,
                    {target.recipient_id: target},
                    revisions,
                    archive=archive,
                    provider=provider_impl,
                    archive_identity=digest("archive"),
                    **self.matrix_contract(archive, typed_manifest, revisions),
                )

    def test_m2c_budget_charges_unique_candidates_and_reports_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn", m2c_budget=1)
            target = target_fixture(archive)
            revision_current = revision_fixture(
                archive, "reva", ("int fn(int x) { return x; }\n",), current=True
            )
            revision_duplicate = revision_fixture(
                archive, "revb", ("int fn(int x) { return x; }\n",)
            )
            revision_overflow = revision_fixture(
                archive, "revc", ("int fn(int x) { return x + 1; }\n",)
            )
            revisions = (revision_current, revision_duplicate, revision_overflow)
            provider_impl = provider_fixture(
                archive,
                revisions,
                {
                    "reva": "int fn(int x) { return x; }\n",
                    "revb": "int fn(int x) { return x; }\n",
                    "revc": "int fn(int x) { return x + 1; }\n",
                },
            )
            provider = build_m2c_ensemble_provider(
                typed_manifest,
                {target.recipient_id: target},
                revisions,
                archive=archive,
                provider=provider_impl,
                archive_identity=digest("archive"),
                **self.matrix_contract(archive, typed_manifest, revisions),
            )
            raw = provider.callback(Recipient(target.recipient_id, "ST", "fn"))
            self.assertEqual(raw["attempts"], 1)
            self.assertEqual(len(raw["candidates"]), 1)
            self.assertEqual(raw["completion_reason"], "budget_exhausted")
            self.assertEqual(raw["rejection_counts"]["budget_exhausted"], 1)
            self.assertEqual(raw["rejection_counts"]["duplicate_candidate"], 1)
            self.assertEqual(len(provider_impl.calls), 3)
            self.assertTrue(any(edge["kind"] == "m2c_overflow_observation" for edge in raw["provenance"]))

    def test_m2c_inapplicable_matrix_is_a_typed_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            target = target_fixture(archive)
            revisions, outputs = self.qualified_pair(archive)
            contract = self.matrix_contract(
                archive,
                typed_manifest,
                revisions,
                status="inapplicable",
                refusal_code="m2c_dependency_unavailable",
            )
            with self.assertRaises(GeneratedProviderUnavailable):
                build_m2c_ensemble_provider(
                    typed_manifest,
                    {target.recipient_id: target},
                    revisions,
                    archive=archive,
                    provider=provider_fixture(archive, revisions, outputs),
                    archive_identity=digest("archive"),
                    **contract,
                )

    def test_bounded_synthesis_uses_only_target_forms_and_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn", synthesis_budget=3)
            target = target_fixture(
                archive,
                expressions=("x + 1", "x - 1"),
                statements=("x = x + 1",),
                declaration_shapes=("int local",),
                control_flow=("if", "if_else"),
            )
            bound = SynthesisBound(
                max_candidates=5,
                max_declarations=2,
                max_expressions=2,
                max_statements=2,
                max_control_flow=2,
                max_combinations=16,
            )
            provider = build_bounded_synthesis_provider(
                typed_manifest,
                {target.recipient_id: target},
                archive=archive,
                bound=bound,
            )
            raw = provider.callback(Recipient(target.recipient_id, "ST", "fn"))
            self.assertEqual(raw["attempts"], 10)
            self.assertEqual(len(raw["candidates"]), 3)
            self.assertEqual(raw["completion_reason"], "budget_exhausted")
            for candidate in raw["candidates"]:
                self.assertIn("int fn(int x)", candidate.source)
                self.assertNotIn("donor", candidate.source)
            self.assertTrue(any("synthesis_bound" in edge for edge in raw["provenance"]))

    def test_empty_synthesis_forms_are_inapplicable_not_live_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            target = target_fixture(archive, expressions=(), statements=(), control_flow=())
            provider = build_bounded_synthesis_provider(
                typed_manifest,
                {target.recipient_id: target},
                archive=archive,
            )
            raw = provider.callback(Recipient(target.recipient_id, "ST", "fn"))
            self.assertEqual(raw["candidates"], ())
            self.assertEqual(raw["refusal_code"], "synthesis_inputs_empty")
            self.assertEqual(raw["completion_reason"], "inapplicable")

    def test_factories_reject_subset_mismatch_and_callback_outside_subset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            target = target_fixture(archive)
            revisions, outputs = self.qualified_pair(archive)
            with self.assertRaises(GeneratedProviderSubsetViolation):
                build_bounded_synthesis_provider(
                    typed_manifest,
                    {},
                    archive=archive,
                )
            provider = build_m2c_ensemble_provider(
                typed_manifest,
                {target.recipient_id: target},
                revisions,
                archive=archive,
                provider=provider_fixture(archive, revisions, outputs),
                archive_identity=digest("archive"),
                **self.matrix_contract(archive, typed_manifest, revisions),
            )
            with self.assertRaises(GeneratedProviderSubsetViolation):
                provider.callback(Recipient("hd:ST:fn", "ST", "fn"))

    def test_corrupt_or_unarchived_target_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            assembly = b"fn:\n  jr $ra\n"
            reference = archive.put_bytes(
                assembly,
                category="target-assembly",
                suffix=".s",
                media_type="text/x-asm",
            )
            target = ArchivedTargetInput(
                recipient_id="us:ST:fn",
                target_identity=typed_manifest.target_identities["us:ST:fn"],
                target_artifact=reference,
                target_bytes=assembly,
                symbol="fn",
            )
            reference_path = Path(directory) / reference.path
            reference_path.write_bytes(b"changed")
            with self.assertRaises(GeneratedProviderArtifactError):
                build_bounded_synthesis_provider(
                    typed_manifest,
                    {target.recipient_id: target},
                    archive=archive,
                )

    def test_malformed_target_path_and_missing_archive_are_rejected(self) -> None:
        assembly = b"fn:\n  jr $ra\n"
        digest_value = hash_bytes(assembly)
        bad_artifact = ArtifactRef(
            digest_value,
            "src/target.s",
            "text/x-asm",
            len(assembly),
        )
        with self.assertRaises(GeneratedProviderArtifactError):
            ArchivedTargetInput(
                recipient_id="us:ST:fn",
                target_identity=digest("target"),
                target_artifact=bad_artifact,
                target_bytes=assembly,
                symbol="fn",
            )
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            target = target_fixture(archive)
            with self.assertRaises(GeneratedProviderArtifactError):
                build_bounded_synthesis_provider(
                    manifest("us:ST:fn"),
                    {target.recipient_id: target},
                    archive=None,  # type: ignore[arg-type]
                )

    def test_lane_budget_units_must_be_supported_by_ordinary_receipt_path(self) -> None:
        typed = manifest("us:ST:fn")
        typed = replace(
            typed,
            lane_budgets={
                **typed.lane_budgets,
                "bounded_synthesis": Budget("seconds", 10, 0),
            },
        )
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            target = target_fixture(archive)
            with self.assertRaises(GeneratedProviderBudgetError):
                build_bounded_synthesis_provider(
                    typed,
                    {target.recipient_id: target},
                    archive=archive,
                )

    def test_generated_lane_mapping_contains_both_ordinary_callbacks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            target = target_fixture(archive)
            revisions, outputs = self.qualified_pair(archive)
            adapters = generated_lane_adapters(
                typed_manifest,
                {target.recipient_id: target},
                archive=archive,
                revisions=revisions,
                provider=provider_fixture(archive, revisions, outputs),
                archive_identity=digest("archive"),
                **self.matrix_contract(archive, typed_manifest, revisions),
            )
            self.assertEqual(set(adapters), {"m2c_ensemble", "bounded_synthesis"})
            recipient = Recipient(target.recipient_id, "ST", "fn")
            self.assertIn("candidates", adapters["m2c_ensemble"](recipient))
            self.assertIn("candidates", adapters["bounded_synthesis"](recipient))

    def test_target_input_rejects_path_only_live_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            with self.assertRaises(GeneratedProviderInputError):
                build_bounded_synthesis_provider(
                    manifest("us:ST:fn"),
                    {"us:ST:fn": "src/fn.s"},  # type: ignore[dict-item]
                    archive=archive,
                )

    def test_matrix_is_strict_immutable_and_protocol_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            first = revision_fixture(
                archive,
                "reva",
                (),
                available=False,
            )
            second = revision_fixture(
                archive,
                "revb",
                (),
                available=False,
            )
            current = revision_fixture(
                archive,
                "current",
                (),
                current=True,
                available=False,
            )
            matrix = M2CRevisionMatrix((second, current))
            restored = M2CRevisionMatrix.from_dict(matrix.to_dict())
            self.assertEqual(matrix.matrix_identity, restored.matrix_identity)
            with self.assertRaises(GeneratedProviderInputError):
                M2CRevisionMatrix.from_dict({"protocol": "wrong", "revisions": []})
            with self.assertRaises(GeneratedProviderInputError):
                M2CRevisionMatrix.from_dict({"revisions": matrix.to_dict()["revisions"], "extra": True})

    def test_callback_result_is_deeply_immutable_and_target_mapping_is_strict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            typed_manifest = manifest("us:ST:fn")
            target = target_fixture(archive)
            provider = build_bounded_synthesis_provider(
                typed_manifest,
                {target.recipient_id: target},
                archive=archive,
            )
            raw = provider.callback(Recipient(target.recipient_id, "ST", "fn"))
            with self.assertRaises(TypeError):
                raw["provenance"][0]["provider_identity"] = digest("mutated")  # type: ignore[index]
            with self.assertRaises(GeneratedProviderInputError):
                ArchivedTargetInput.from_dict(
                    {
                        **target.to_dict(),
                        "target_bytes": target.target_bytes,
                        "source": "live checkout fallback",
                    }
                )

    def test_target_snapshot_is_platform_neutral_across_all_supported_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            record_ids = tuple(platform + ":ST:fn" for platform in ("us", "hd", "pspeu", "saturn"))
            typed_manifest = manifest(*record_ids)
            targets = {
                record_id: target_fixture(archive, record_id)
                for record_id in record_ids
            }
            revisions, outputs = self.qualified_pair(archive)
            provider = build_m2c_ensemble_provider(
                typed_manifest,
                targets,
                M2CRevisionMatrix(revisions),
                archive=archive,
                provider=provider_fixture(archive, revisions, outputs),
                archive_identity=digest("archive"),
                **self.matrix_contract(archive, typed_manifest, revisions),
            )
            self.assertEqual(
                tuple(item[0] for item in provider.results),
                tuple(sorted(record_ids)),
            )
            for record_id in record_ids:
                self.assertEqual(
                    len(provider.callback(Recipient(record_id, "ST", "fn")).get("candidates", ())),
                    2,
                )



if __name__ == "__main__":
    unittest.main()
