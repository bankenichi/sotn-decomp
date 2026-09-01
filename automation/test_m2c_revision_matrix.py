"""Focused tests for the qualified m2c revision matrix."""

from __future__ import annotations

import json
import tempfile
import unittest
import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.m2c_revision_matrix import (
    CURRENT_M2C_REVISION,
    M2CBenchmarkCase,
    M2CBenchmarkError,
    M2CFixedBenchmark,
    M2CMatrixError,
    M2CMatrixReceipt,
    M2CRevisionPin,
    M2CUnavailableRevisionReceipt,
    enumerate_m2c_variants,
    load_benchmark_report,
    load_m2c_matrix_receipt,
    make_benchmark_report,
    make_matrix_spec,
    make_unavailable_revision_receipt,
    publish_m2c_revision_matrix,
    qualify_revision,
    replay_m2c_matrix,
    resolve_revision_pin,
    run_fixed_benchmark,
    run_m2c_matrix,
    to_generated_m2c_matrix,
)
from automation.m2c_revision_provider import (
    M2CDraftPayload,
    M2CRevisionIdentity,
    PinnedM2CRevisionProvider,
)
from automation.search_archive import ContentAddressedArchive
from automation.search_types import (
    ArtifactRef,
    ScoreComponents,
    ScoreVector,
    hash_bytes,
    hash_canonical,
)


def ident(label: str) -> str:
    return hash_bytes(("matrix-test:" + label).encode("utf-8"))


def revision(label: str) -> M2CRevisionIdentity:
    return M2CRevisionIdentity(
        revision_id=(
            CURRENT_M2C_REVISION
            if label == "current"
            else ("a" * 39 + "1")
        ),
        tree_identity=ident("tree"),
        provider_identity=ident("provider"),
        executable_identity=ident("executable"),
        config_identity=ident("config"),
        clean=True,
        detached=True,
    )


@dataclass(frozen=True)
class FakeGate:
    gate_id: str
    run_id: str
    receipt_artifact: ArtifactRef
    subset_identity: str
    queue_evidence_identity: str
    gate_kind: str = "multi_record"
    record_count: int = 2




def make_qualification_for_test(spec, alternate_revision_id):
    from automation.m2c_revision_matrix import M2CRevisionQualification
    baseline_report_id = ident("baseline-for-variants")
    alternate_report_id = ident("alternate-for-variants")
    payload = {
        "protocol": "sotn-m2c-qualification-v1",
        "benchmark_id": spec.benchmark_id,
        "baseline_report_id": baseline_report_id,
        "alternate_report_id": alternate_report_id,
        "alternate_revision_id": alternate_revision_id,
        "unique_candidate_count": 1,
        "better_case_count": 0,
        "qualified": True,
        "reason_code": "qualified_unique",
    }
    return M2CRevisionQualification(
        qualification_id=hash_canonical(payload),
        benchmark_id=spec.benchmark_id,
        baseline_report_id=baseline_report_id,
        alternate_report_id=alternate_report_id,
        alternate_revision_id=alternate_revision_id,
        unique_candidate_count=1,
        better_case_count=0,
        qualified=True,
        reason_code="qualified_unique",
    )
class MatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="m2c-matrix-")
        self.archive = ContentAddressedArchive(Path(self.temp.name) / "archive")
        self.assembly = b"glabel target\n  jr $ra\n   nop\n"
        self.context = b"typedef int s32;\n"
        self.assembly_ref = self.archive.put_bytes(
            self.assembly,
            category="target-assembly",
            suffix=".s",
            media_type="text/x-asm",
        )
        self.context_ref = self.archive.put_bytes(
            self.context,
            category="target-context",
            suffix=".h",
            media_type="text/x-c",
        )
        self.gate = self._gate()
        self.current = revision("current")
        self.alternate = revision("alternate")
        self.provider_calls: list[str] = []
        self.provider = PinnedM2CRevisionProvider(
            (self.current, self.alternate),
            generator=self._generate,
            archive=self.archive,
            archive_identity=ident("archive"),
        )
        self.case = M2CBenchmarkCase(
            case_id="case-a",
            recipient_id="us:ST:target",
            assembly_artifact=self.assembly_ref,
            context_artifacts=(self.context_ref,),
            target_identity=ident("target"),
            compiler_identity=ident("compiler"),
            evaluator_identity=ident("evaluator"),
            config_identity=self.current.config_identity,
        )
        self.benchmark = M2CFixedBenchmark(
            benchmark_id=ident("benchmark"),
            current_revision_id=CURRENT_M2C_REVISION,
            cases=(self.case,),
            scorer_taxonomy_identity=ident("taxonomy"),
            evaluator_identity=ident("evaluator"),
            budget=8,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _gate(self, *, kind: str = "multi_record") -> FakeGate:
        raw = b'{"protocol":"matrix-test-gate","records":2}\n'
        artifact = self.archive.put_bytes(
            raw,
            category="receipts",
            suffix=".json",
            media_type="application/json",
        )
        return FakeGate(
            gate_id=artifact.content_hash,
            run_id="matrix-test-run",
            receipt_artifact=artifact,
            subset_identity=ident("subset"),
            queue_evidence_identity=ident("queue"),
            gate_kind=kind,
            record_count=2 if kind == "multi_record" else 1,
        )

    def _generate(self, invocation, *, assembly, contexts):
        self.provider_calls.append(invocation.revision_id)
        value = 1 if invocation.revision_id != CURRENT_M2C_REVISION else 0
        return f"int target(void) {{ return {value}; }}\n"

    def _score(self, case, candidate, scorer_taxonomy_identity):
        source = self.archive.verify(candidate)
        value = 1 if b"return 1" in source else 2
        compiler = case.compiler_identity
        return ScoreVector(
            compile_status="success",
            elapsed_ms=value,
            total=value,
            components=ScoreComponents(0, 0, value, 0, 0),
            weights=ScoreComponents(1, 1, 1, 1, 1),
            object_hash=hash_bytes(source),
            mismatch_signature=ident("mismatch-" + str(value)),
            first_divergence=None,
            target_instruction_count=3,
            candidate_instruction_count=3,
            diagnostic_artifact=None,
            scorer_algorithm="difflib",
            compiler_identity=compiler,
        )

    def _gate_patch(self):
        return patch(
            "automation.m2c_revision_matrix.IntegrationGateReceipt",
            FakeGate,
        ), patch(
            "automation.m2c_revision_matrix.validate_integration_gate",
            return_value=object(),
        )

    def _benchmark_artifact(self) -> ArtifactRef:
        payload = {
            "protocol": "sotn-m2c-benchmark-artifact-v1",
            "benchmark": self.benchmark.to_dict(),
        }
        return self.archive.put_json(payload, category="m2c-benchmarks")

    def _spec(self, *, alternates=(), budget=8, switches=(("--baseline",),)):
        benchmark_artifact = self._benchmark_artifact()
        return make_matrix_spec(
            matrix_id=ident("unused-matrix-id"),
            matrix_spec_artifact_id=ident("unused-spec-artifact-id"),
            benchmark_id=self.benchmark.benchmark_id,
            benchmark_artifact_id=benchmark_artifact.content_hash,
            gate_id=self.gate.gate_id,
            integration_gate_artifact_id=self.gate.receipt_artifact.content_hash,
            subset_identity=self.gate.subset_identity,
            queue_evidence_identity=self.gate.queue_evidence_identity,
            provider_identity=self.current.provider_identity,
            tool_identity=self.current.executable_identity,
            revision_tool_identities=(
                (CURRENT_M2C_REVISION, self.current.executable_identity),
                *(
                    ((self.alternate.revision_id, self.alternate.executable_identity),)
                    if alternates
                    else ()
                ),
            ),
            archive_identity=ident("archive"),
            current_revision_id=CURRENT_M2C_REVISION,
            qualified_alternate_revision_ids=tuple(alternates),
            cases=(self.case,),
            switch_matrix=switches,
            context_kinds=("target",),
            compiler_identity=self.case.compiler_identity,
            evaluator_identity=self.case.evaluator_identity,
            config_identity=self.case.config_identity,
            scorer_taxonomy_identity=self.benchmark.scorer_taxonomy_identity,
            budget=budget,
        )

    def test_current_report_is_complete_replayable_and_archive_bound(self):
        with self._gate_patch()[0], self._gate_patch()[1]:
            first = run_fixed_benchmark(
                self.benchmark,
                self.current,
                self.provider,
                self._score,
                self.archive,
                archive_identity=ident("archive"),
                gate=self.gate,
            )
            second = run_fixed_benchmark(
                self.benchmark,
                self.current,
                self.provider,
                self._score,
                self.archive,
                archive_identity=ident("archive"),
                gate=self.gate,
            )
        self.assertTrue(first.complete)
        self.assertEqual(first, second)
        self.assertEqual(first.integration_gate_id, self.gate.gate_id)
        self.assertEqual(first.tool_identity, self.current.executable_identity)
        self.assertEqual(len(first.observation_artifact_ids), 1)
        report_ref = self.archive.put_json(
            first.identity_payload(),
            category="m2c-benchmark-reports",
        )
        self.assertEqual(load_benchmark_report(report_ref, archive=self.archive), first)

    def test_gate_is_validated_once_before_provider(self):
        calls = []

        def validate(gate, *, archive):
            calls.append("gate")
            self.assertEqual(self.provider_calls, [])
            return object()

        with patch(
            "automation.m2c_revision_matrix.IntegrationGateReceipt", FakeGate
        ), patch(
            "automation.m2c_revision_matrix.validate_integration_gate",
            side_effect=validate,
        ):
            run_fixed_benchmark(
                self.benchmark,
                self.current,
                self.provider,
                self._score,
                self.archive,
                archive_identity=ident("archive"),
                gate=self.gate,
            )
        self.assertEqual(calls, ["gate"])

    def test_one_record_gate_is_refused(self):
        gate = self._gate(kind="smoke")
        with patch(
            "automation.m2c_revision_matrix.IntegrationGateReceipt", FakeGate
        ), patch(
            "automation.m2c_revision_matrix.validate_integration_gate",
            return_value=object(),
        ), self.assertRaises(M2CBenchmarkError):
            run_fixed_benchmark(
                self.benchmark,
                self.current,
                self.provider,
                self._score,
                self.archive,
                archive_identity=ident("archive"),
                gate=gate,
            )

    def test_missing_measurement_refuses(self):
        def missing(case, candidate, scorer_taxonomy_identity):
            return None

        with patch(
            "automation.m2c_revision_matrix.IntegrationGateReceipt", FakeGate
        ), patch(
            "automation.m2c_revision_matrix.validate_integration_gate",
            return_value=object(),
        ), self.assertRaises(M2CBenchmarkError):
            run_fixed_benchmark(
                self.benchmark,
                self.current,
                self.provider,
                missing,
                self.archive,
                archive_identity=ident("archive"),
                gate=self.gate,
            )

    def test_alternate_qualifies_only_for_unique_or_better_output(self):
        with patch(
            "automation.m2c_revision_matrix.IntegrationGateReceipt", FakeGate
        ), patch(
            "automation.m2c_revision_matrix.validate_integration_gate",
            return_value=object(),
        ):
            baseline = run_fixed_benchmark(
                self.benchmark,
                self.current,
                self.provider,
                self._score,
                self.archive,
                archive_identity=ident("archive"),
                gate=self.gate,
            )
            alternate = run_fixed_benchmark(
                self.benchmark,
                self.alternate,
                self.provider,
                self._score,
                self.archive,
                archive_identity=ident("archive"),
                gate=self.gate,
            )
        result = qualify_revision(baseline, alternate)
        self.assertTrue(result.qualified)
        self.assertEqual(result.reason_code, "qualified_unique")
        self.assertEqual(result.unique_candidate_count, 1)

    def test_incomplete_baseline_never_qualifies(self):
        report = make_benchmark_report(
            benchmark_id=self.benchmark.benchmark_id,
            benchmark_artifact_id=ident("benchmark-artifact"),
            revision_id=CURRENT_M2C_REVISION,
            tree_identity=self.current.tree_identity,
            provider_identity=self.current.provider_identity,
            tool_identity=self.current.executable_identity,
            archive_identity=ident("archive"),
            integration_gate_id=self.gate.gate_id,
            integration_gate_artifact_id=self.gate.receipt_artifact.content_hash,
            subset_identity=self.gate.subset_identity,
            queue_evidence_identity=self.gate.queue_evidence_identity,
            compiler_identity=self.case.compiler_identity,
            evaluator_identity=self.case.evaluator_identity,
            config_identity=self.case.config_identity,
            scorer_taxonomy_identity=self.benchmark.scorer_taxonomy_identity,
            observations=(),
            observation_artifact_ids=(),
            total_cost_units=0,
            unique_candidate_count=0,
            better_case_count=0,
            complete=False,
            refusal_code="incomplete",
        )
        alternate = make_benchmark_report(
            benchmark_id=report.benchmark_id,
            benchmark_artifact_id=report.benchmark_artifact_id,
            revision_id=self.alternate.revision_id,
            tree_identity=report.tree_identity,
            provider_identity=report.provider_identity,
            tool_identity=report.tool_identity,
            archive_identity=report.archive_identity,
            integration_gate_id=report.integration_gate_id,
            integration_gate_artifact_id=report.integration_gate_artifact_id,
            subset_identity=report.subset_identity,
            queue_evidence_identity=report.queue_evidence_identity,
            compiler_identity=report.compiler_identity,
            evaluator_identity=report.evaluator_identity,
            config_identity=report.config_identity,
            scorer_taxonomy_identity=report.scorer_taxonomy_identity,
            observations=(),
            observation_artifact_ids=(),
            total_cost_units=0,
            unique_candidate_count=0,
            better_case_count=0,
            complete=True,
            refusal_code=None,
        )
        result = qualify_revision(report, alternate)
        self.assertFalse(result.qualified)
        self.assertEqual(result.reason_code, "baseline_incomplete")

    def test_mismatched_benchmark_is_refused(self):
        first = make_benchmark_report(
            benchmark_id=ident("fixed-a"),
            benchmark_artifact_id=ident("artifact"),
            revision_id=CURRENT_M2C_REVISION,
            tree_identity=self.current.tree_identity,
            provider_identity=self.current.provider_identity,
            tool_identity=self.current.executable_identity,
            archive_identity=ident("archive"),
            integration_gate_id=self.gate.gate_id,
            integration_gate_artifact_id=self.gate.receipt_artifact.content_hash,
            subset_identity=self.gate.subset_identity,
            queue_evidence_identity=self.gate.queue_evidence_identity,
            compiler_identity=self.case.compiler_identity,
            evaluator_identity=self.case.evaluator_identity,
            config_identity=self.case.config_identity,
            scorer_taxonomy_identity=self.benchmark.scorer_taxonomy_identity,
            observations=(),
            observation_artifact_ids=(),
            total_cost_units=0,
            unique_candidate_count=0,
            better_case_count=0,
            complete=True,
            refusal_code=None,
        )
        second = make_benchmark_report(
            benchmark_id=ident("fixed-b"),
            benchmark_artifact_id=first.benchmark_artifact_id,
            revision_id=self.alternate.revision_id,
            tree_identity=first.tree_identity,
            provider_identity=first.provider_identity,
            tool_identity=first.tool_identity,
            archive_identity=first.archive_identity,
            integration_gate_id=first.integration_gate_id,
            integration_gate_artifact_id=first.integration_gate_artifact_id,
            subset_identity=first.subset_identity,
            queue_evidence_identity=first.queue_evidence_identity,
            compiler_identity=first.compiler_identity,
            evaluator_identity=first.evaluator_identity,
            config_identity=first.config_identity,
            scorer_taxonomy_identity=first.scorer_taxonomy_identity,
            observations=(),
            observation_artifact_ids=(),
            total_cost_units=0,
            unique_candidate_count=0,
            better_case_count=0,
            complete=True,
            refusal_code=None,
        )
        result = qualify_revision(first, second)
        self.assertFalse(result.qualified)
        self.assertEqual(result.reason_code, "identity_mismatch")

    def test_reversed_matrix_declarations_have_one_canonical_identity(self):
        first = self._spec(switches=(("--a",), ("--b",)))
        second = self._spec(switches=(("--b",), ("--a",)))
        self.assertEqual(first, second)

    def test_variants_are_current_first_with_contiguous_ordinals(self):
        spec = self._spec(alternates=(self.alternate.revision_id,))
        qualification = make_qualification_for_test(spec, self.alternate.revision_id)
        variants = enumerate_m2c_variants(spec, (qualification,))
        self.assertEqual(variants[0].revision_id, CURRENT_M2C_REVISION)
        self.assertEqual(
            tuple(item.ordinal for item in variants),
            tuple(range(len(variants))),
        )

    def test_unqualified_alternate_is_refused(self):
        spec = self._spec(alternates=(self.alternate.revision_id,))
        bad = make_benchmark_report(
            benchmark_id=spec.benchmark_id,
            benchmark_artifact_id=spec.benchmark_artifact_id,
            revision_id=self.alternate.revision_id,
            tree_identity=self.current.tree_identity,
            provider_identity=self.current.provider_identity,
            tool_identity=self.current.executable_identity,
            archive_identity=spec.archive_identity,
            integration_gate_id=spec.gate_id,
            integration_gate_artifact_id=spec.integration_gate_artifact_id,
            subset_identity=spec.subset_identity,
            queue_evidence_identity=spec.queue_evidence_identity,
            compiler_identity=spec.compiler_identity,
            evaluator_identity=spec.evaluator_identity,
            config_identity=spec.config_identity,
            scorer_taxonomy_identity=spec.scorer_taxonomy_identity,
            observations=(),
            observation_artifact_ids=(),
            total_cost_units=0,
            unique_candidate_count=0,
            better_case_count=0,
            complete=True,
            refusal_code=None,
        )
        qualification = qualify_revision(
            make_benchmark_report(
                benchmark_id=spec.benchmark_id,
                benchmark_artifact_id=spec.benchmark_artifact_id,
                revision_id=CURRENT_M2C_REVISION,
                tree_identity=self.current.tree_identity,
                provider_identity=self.current.provider_identity,
                tool_identity=self.current.executable_identity,
                archive_identity=spec.archive_identity,
                integration_gate_id=spec.gate_id,
                integration_gate_artifact_id=spec.integration_gate_artifact_id,
                subset_identity=spec.subset_identity,
                queue_evidence_identity=spec.queue_evidence_identity,
                compiler_identity=spec.compiler_identity,
                evaluator_identity=spec.evaluator_identity,
                config_identity=spec.config_identity,
                scorer_taxonomy_identity=spec.scorer_taxonomy_identity,
                observations=(),
                observation_artifact_ids=(),
                total_cost_units=0,
                unique_candidate_count=0,
                better_case_count=0,
                complete=True,
                refusal_code=None,
            ),
            bad,
        )
        with self.assertRaises(M2CMatrixError):
            enumerate_m2c_variants(spec, (qualification,))

    def test_duplicate_candidate_consumes_one_budget(self):
        spec = self._spec(budget=2, switches=(("--a",), ("--b",)))
        variants = enumerate_m2c_variants(spec, ())
        benchmark_payload = {
            "protocol": "sotn-m2c-benchmark-artifact-v1",
            "benchmark_id": spec.benchmark_id,
            "benchmark_artifact_id": spec.benchmark_artifact_id,
        }
        self.archive.put_json(benchmark_payload, category="m2c-benchmarks")
        with patch(
            "automation.m2c_revision_matrix.IntegrationGateReceipt", FakeGate
        ), patch(
            "automation.m2c_revision_matrix.validate_integration_gate",
            return_value=object(),
        ):
            receipt = run_m2c_matrix(
                spec,
                variants,
                self.provider,
                self._score,
                self.archive,
                self.gate,
            )
        self.assertEqual(receipt.consumed_budget, 1)
        self.assertEqual(len(receipt.compiled_candidate_ids), 1)
        self.assertEqual(len(receipt.deduplicated_variant_ids), 1)
        self.assertEqual(
            load_m2c_matrix_receipt(
                self.archive.put_json(
                    receipt.identity_payload(),
                    category="m2c-matrix-receipts",
                ),
                archive=self.archive,
            ),
            receipt,
        )

    def test_matrix_replay_is_byte_identical(self):
        spec = self._spec()
        variants = enumerate_m2c_variants(spec, ())
        self.archive.put_json(
            {
                "protocol": "sotn-m2c-benchmark-artifact-v1",
                "benchmark_id": spec.benchmark_id,
                "benchmark_artifact_id": spec.benchmark_artifact_id,
            },
            category="m2c-benchmarks",
        )
        with patch(
            "automation.m2c_revision_matrix.IntegrationGateReceipt", FakeGate
        ), patch(
            "automation.m2c_revision_matrix.validate_integration_gate",
            return_value=object(),
        ):
            first = run_m2c_matrix(
                spec, variants, self.provider, self._score, self.archive, self.gate
            )
            second = replay_m2c_matrix(
                spec,
                tuple(reversed(variants)),
                self.provider,
                self._score,
                self.archive,
                self.gate,
                expected=first,
            )
        self.assertEqual(first, second)

    def test_corrupt_receipt_refuses(self):
        spec = self._spec()
        variants = enumerate_m2c_variants(spec, ())
        self.archive.put_json(
            {
                "protocol": "sotn-m2c-benchmark-artifact-v1",
                "benchmark_id": spec.benchmark_id,
                "benchmark_artifact_id": spec.benchmark_artifact_id,
            },
            category="m2c-benchmarks",
        )
        with patch(
            "automation.m2c_revision_matrix.IntegrationGateReceipt", FakeGate
        ), patch(
            "automation.m2c_revision_matrix.validate_integration_gate",
            return_value=object(),
        ):
            receipt = run_m2c_matrix(
                spec, variants, self.provider, self._score, self.archive, self.gate
            )
        receipt_ref = self.archive.put_json(
            receipt.identity_payload(),
            category="m2c-matrix-receipts",
        )
        path = self.archive.resolve(receipt_ref)
        path.write_bytes(b"corrupt")
        with self.assertRaises(M2CMatrixError):
            load_m2c_matrix_receipt(receipt_ref, archive=self.archive)

    def test_revision_pin_requires_archived_source_tool_and_generated_conversion(self):
        source = self.archive.put_text(
            "/* current m2c source */\n",
            category="m2c-revision-sources",
        )
        tool = self.archive.put_bytes(
            b"m2c-executable",
            category="m2c-revision-tools",
            suffix=".bin",
        )
        pin = M2CRevisionPin(
            revision=self.current,
            source_artifact=source,
            tool_artifact=tool,
            runner_identity=ident("runner"),
        )
        generated = to_generated_m2c_matrix((pin,))
        self.assertEqual(generated.current.revision_id, CURRENT_M2C_REVISION)

    def test_missing_pinned_artifacts_return_typed_unavailable_receipt(self):
        result = resolve_revision_pin(
            self.provider,
            self.alternate,
            source_artifact=None,
            tool_artifact=None,
            runner_identity=ident("runner"),
            archive=self.archive,
        )
        self.assertIsInstance(result, M2CUnavailableRevisionReceipt)
        self.assertEqual(result.reason_code, "pinned_source_or_tool_missing")

    def test_current_only_publication_is_explicitly_not_a_matrix(self):
        source = self.archive.put_text(
            "/* current */\n",
            category="m2c-revision-sources",
        )
        tool = self.archive.put_bytes(
            b"current-tool",
            category="m2c-revision-tools",
        )
        pin = M2CRevisionPin(
            revision=self.current,
            source_artifact=source,
            tool_artifact=tool,
            runner_identity=ident("runner"),
        )
        with self.assertRaises(M2CMatrixError):
            publish_m2c_revision_matrix(pin, (), archive=self.archive)

    def test_unavailable_revision_has_typed_receipt(self):
        receipt = make_unavailable_revision_receipt(
            "b" * 40,
            executable_identity=ident("alternate-executable"),
            provider_identity=ident("provider"),
            runner_identity=ident("runner"),
            reason_code="pinned_revision_absent",
            detail="historical vendored checkout is not present",
        )
        self.assertIsInstance(receipt, M2CUnavailableRevisionReceipt)
        self.assertEqual(receipt.receipt_id, hash_canonical(receipt.identity_payload()))

    def test_from_dict_refuses_corrupt_protocol(self):
        spec = self._spec()
        raw = spec.to_dict()
        raw["protocol"] = "untrusted"
        with self.assertRaises(M2CMatrixError):
            type(spec).from_dict(raw)


if __name__ == "__main__":
    unittest.main()
