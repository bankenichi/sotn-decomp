"""Focused tests for target-derived indexed query and rendering boundaries."""

from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive
from automation.search_donor_query import DonorSemanticClaim
from automation.search_lanes import DonorEvidence, LaneCandidate, Recipient
from automation.search_semantic_signatures import SemanticInstruction, assembly_signatures
from automation.search_target_renderer import (
    TargetContextUnsupported,
    TargetEvidenceError,
    TargetRendererInputError,
    _assembly_signatures,
    _parse_assembly,
    deterministic_local_draft,
    load_target_index,
    query_for_recipient,
    render_target_candidate,
)
from automation.search_types import RunManifest, hash_bytes, hash_canonical
from automation.test_search_donor_index import digest
from automation.test_search_lanes import make_manifest


RECIPIENT_ID = "us:ST:fn"
TARGET_ASM = b"""/* 0 80000000 24020007 */ addiu $v0, $zero, 7
/* 4 80000004 03E00008 */ jr $ra
/* 8 80000008 00000000 */ nop
"""


def _recipient() -> Recipient:
    return Recipient(
        recipient_id=RECIPIENT_ID,
        overlay="ST",
        function="fn",
        metadata={"target_file": "asm/us/st/fn.s"},
    )


def _target_fixture(
    assembly: bytes = TARGET_ASM,
    *,
    instruction_signature: str | None = None,
    cfg_signature: str | None = None,
    dataflow_signature: str | None = None,
):
    temp = tempfile.TemporaryDirectory(prefix="target-renderer-")
    archive = ContentAddressedArchive(Path(temp.name) / "run")
    assembly_ref = archive.put_bytes(
        assembly,
        category="target-assembly",
        suffix=".s",
        media_type="text/x-asm",
    )
    object_ref = archive.put_bytes(
        b"target object",
        category="target-object",
        suffix=".o",
        media_type="application/octet-stream",
    )
    derived_instruction, derived_cfg, derived_dataflow = _assembly_signatures(
        _parse_assembly(assembly.decode("utf-8"))
    )
    target_doc = {
        "artifact_type": "sotn-search-target-evidence",
        "assembly": {
            "artifact": assembly_ref.to_dict(),
            "content_hash": hash_bytes(assembly),
            "path": "asm/us/st/fn.s",
            "byte_size": len(assembly),
        },
        "object": {
            "artifact": object_ref.to_dict(),
            "content_hash": object_ref.content_hash,
            "path": "build/us/src/st/fn.o",
            "byte_size": object_ref.byte_size,
        },
        "record_id": RECIPIENT_ID,
        "schema_version": "1.0.0",
        "symbol": "fn",
        "instruction_signature": (
            derived_instruction if instruction_signature is None else instruction_signature
        ),
        "cfg_signature": derived_cfg if cfg_signature is None else cfg_signature,
        "dataflow_signature": (
            derived_dataflow if dataflow_signature is None else dataflow_signature
        ),
        "declarations": {"return_type": "int"},
    }
    target_identity = hash_canonical(target_doc)
    manifest = replace(
        RunManifest.from_dict(make_manifest(RECIPIENT_ID)),
        target_identities={RECIPIENT_ID: target_identity},
    )
    target_evidence_ref = archive.put_json(
        target_doc,
        category="target-evidence",
        suffix=".json",
    )
    target_index_document = {
        "artifact_type": "sotn-search-target-index",
        "schema_version": "1.0.0",
        "records": [
            {
                "record_id": RECIPIENT_ID,
                "target_identity": target_identity,
                "target_evidence": target_evidence_ref.to_dict(),
            }
        ],
    }
    archive.put_json(
        target_index_document,
        category="target-index",
        suffix=".json",
    )
    return temp, archive, manifest, load_target_index(archive, manifest)


def _claim() -> DonorSemanticClaim:
    evidence = DonorEvidence(
        donor_id="hd:ST:fn",
        recipient_id=RECIPIENT_ID,
        version="hd",
        source="artifacts/donor.s",
        match_kind="instruction_shape",
        signature="sig:fn",
        symbol="fn",
        instruction_signature="ins:target",
        cfg_signature="cfg:target",
        dataflow_signature="flow:target",
        declarations={"return_type": "int"},
        constants={"literal": 7},
        compatible=True,
    )
    return DonorSemanticClaim.from_evidence(evidence)


class TargetQueryTests(unittest.TestCase):
    def test_query_uses_archived_target_only_and_binds_recipient(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture()
        try:
            query = query_for_recipient(manifest, target_index, _recipient())
            self.assertEqual(query.recipient_id, RECIPIENT_ID)
            self.assertIsNone(query.version)
            self.assertEqual(query.source_path, "asm/us/st/fn.s")
            self.assertEqual(query.symbol, "fn")
            context = target_index.records[0]
            self.assertEqual(query.instruction_signature, context.instruction_signature)
            self.assertEqual(query.cfg_signature, context.cfg_signature)
            self.assertEqual(query.dataflow_signature, context.dataflow_signature)
            self.assertEqual(query.compiler_identity, manifest.compiler_identity)
            self.assertEqual(query.config_identity, manifest.config_identity)
        finally:
            temp.cleanup()

    def test_wrong_recipient_target_cannot_be_selected(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture()
        try:
            with self.assertRaises(TargetRendererInputError):
                query_for_recipient(
                    manifest,
                    target_index,
                    Recipient("us:ST:other", "ST", "other"),
                )
        finally:
            temp.cleanup()

    def test_stored_target_signatures_must_match_archived_assembly(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture(
            instruction_signature="sha256:" + "0" * 64,
        )
        try:
            with self.assertRaises(TargetEvidenceError):
                query_for_recipient(manifest, target_index, _recipient())
        finally:
            temp.cleanup()

    def test_renderer_signatures_use_shared_cross_platform_normalizer(self) -> None:
        assembly = (
            "ldr r0, [r1, #4]\n"
            "bl #0x20\n"
            "add r0, r0, r2\n"
            "ret\n"
        )
        parsed = _parse_assembly(assembly)
        expected = assembly_signatures(
            tuple(
                SemanticInstruction(item.mnemonic, item.operands, item.unsupported)
                for item in parsed
            )
        )
        self.assertEqual(_assembly_signatures(parsed), expected)
        self.assertTrue(any(item.unsupported for item in parsed))

    def test_numeric_branch_refusal_preserves_shared_cross_platform_signatures(self) -> None:
        cases = (
            "beq $a0, $zero, 4\njr $ra\nnop\n",
            "b.eq #4\nbx lr\n",
            "bt 4\nrts\n",
        )
        for assembly in cases:
            with self.subTest(assembly=assembly):
                parsed = _parse_assembly(assembly)
                expected = assembly_signatures(
                    tuple(
                        SemanticInstruction(
                            item.mnemonic,
                            item.operands,
                            item.unsupported,
                        )
                        for item in parsed
                    )
                )
                self.assertEqual(_assembly_signatures(parsed), expected)
                self.assertTrue(any(item.unsupported for item in parsed))
                self.assertIsNone(
                    deterministic_local_draft(
                        assembly,
                        symbol="numeric_branch",
                        declarations={"return_type": "int"},
                    )
                )

    def test_deterministic_draft_maps_abi_registers_to_declared_parameter_positions(self) -> None:
        one = deterministic_local_draft(
            "addiu $v0, $a0, 1\njr $ra\nnop\n",
            symbol="one",
            declarations={
                "return_type": "int",
                "parameters": [{"type": "int", "name": "count"}],
            },
        )
        self.assertEqual(
            one,
            "int one(int count) {\n    return count + 1;\n}\n",
        )
        self.assertNotIn("a0", one or "")

        many = deterministic_local_draft(
            "addu $v0, $a0, $a1\njr $ra\nnop\n",
            symbol="many",
            declarations={
                "return_type": "int",
                "parameters": [
                    {"type": "int", "name": "left_value"},
                    {"type": "int", "name": "right_value"},
                ],
            },
        )
        self.assertEqual(
            many,
            "int many(int left_value, int right_value) {\n"
            "    return left_value + right_value;\n"
            "}\n",
        )
        self.assertNotIn("a0", many or "")
        self.assertNotIn("a1", many or "")

        # Without target declaration positions the renderer must refuse rather
        # than inventing C parameters named after ABI registers.
        self.assertIsNone(
            deterministic_local_draft(
                "move $v0, $a0\njr $ra\nnop\n",
                symbol="missing_declarations",
            )
        )


class TargetRendererTests(unittest.TestCase):
    def test_rendering_is_deterministic_and_target_derived(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture()
        try:
            first = render_target_candidate(
                manifest,
                target_index,
                _recipient(),
                (_claim(),),
                lane="multi_donor",
            )
            second = render_target_candidate(
                manifest,
                target_index,
                _recipient(),
                (_claim(),),
                lane="multi_donor",
            )
            self.assertIsInstance(first, LaneCandidate)
            self.assertEqual(first.to_dict(), second.to_dict())
            self.assertIn("return 7;", first.source)
            self.assertNotIn("artifacts/donor.s", first.source)
        finally:
            temp.cleanup()

    def test_donor_evidence_and_unarchived_source_cannot_reach_renderer(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture()
        try:
            with self.assertRaises(TargetRendererInputError):
                render_target_candidate(
                    manifest,
                    target_index,
                    _recipient(),
                    (DonorEvidence(
                        donor_id="hd:ST:fn",
                        recipient_id=RECIPIENT_ID,
                        version="hd",
                        source="donor.c",
                        match_kind="instruction_shape",
                        signature="sig:fn",
                    ),),
                )
            unarchived = {
                "records": [
                    {
                        "record_id": RECIPIENT_ID,
                        "target_identity": target_index.records[0].target_identity,
                        "target_evidence": {
                            "record_id": RECIPIENT_ID,
                            "assembly": {
                                "path": "asm/us/st/fn.s",
                                "text": TARGET_ASM.decode(),
                            },
                        },
                    }
                ]
            }
            with self.assertRaises(TargetRendererInputError):
                render_target_candidate(
                    manifest, unarchived, _recipient(), (_claim(),)
                )
        finally:
            temp.cleanup()

    def test_forbidden_semantic_provenance_cannot_reach_renderer(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture()
        try:
            base_claim = _claim()
            forged_declarations = {"register": "a0"}
            forged = replace(
                base_claim,
                declarations=forged_declarations,
                claim_identity=hash_canonical(
                    {
                        **base_claim.identity_payload(),
                        "declarations": forged_declarations,
                    }
                ),
            )
            with self.assertRaises(TargetRendererInputError):
                render_target_candidate(
                    manifest,
                    target_index,
                    _recipient(),
                    (forged,),
                )
            parameter_declarations = {
                    "return_type": "int",
                    "parameters": [{"type": "int", "name": "a0"}],
            }
            forged_parameter = replace(
                base_claim,
                declarations=parameter_declarations,
                claim_identity=hash_canonical(
                    {
                        **base_claim.identity_payload(),
                        "declarations": parameter_declarations,
                    }
                ),
            )
            with self.assertRaises(TargetRendererInputError):
                render_target_candidate(
                    manifest,
                    target_index,
                    _recipient(),
                    (forged_parameter,),
                )
        finally:
            temp.cleanup()

    def test_complex_target_returns_typed_unsupported_context(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture(
            b"fn:\n\tbeq $a0, $zero, .Ldone\n\t nop\n.Ldone:\n\tjr $ra\n\t nop\n"
        )
        try:
            refusal = render_target_candidate(
                manifest, target_index, _recipient(), (_claim(),)
            )
            self.assertIsInstance(refusal, TargetContextUnsupported)
            self.assertEqual(refusal.refusal_code, "target_context_unsupported")
            self.assertEqual(refusal.query.recipient_id, RECIPIENT_ID)
            self.assertIn(refusal.query.query_identity, refusal.input_identities)
            self.assertTrue(refusal.provenance)
            self.assertEqual(refusal.provenance[0]["recipient_id"], RECIPIENT_ID)
            self.assertEqual(refusal.provenance[0]["lane"], "multi_donor")
            self.assertEqual(
                refusal.provenance[0]["claim_identities"],
                [claim.claim_identity for claim in (_claim(),)],
            )
        finally:
            temp.cleanup()

    def test_forbidden_branch_displacement_is_typed_unsupported_context(self) -> None:
        temp, _archive, manifest, target_index = _target_fixture(
            b"beq $a0, $zero, 4\n"
            b"jr $ra\n"
            b"nop\n"
        )
        try:
            refusal = render_target_candidate(
                manifest, target_index, _recipient(), (_claim(),), lane="cfg_dataflow"
            )
            self.assertIsInstance(refusal, TargetContextUnsupported)
            self.assertEqual(refusal.refusal_code, "target_context_unsupported")
            self.assertEqual(refusal.provenance[0]["lane"], "cfg_dataflow")
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
