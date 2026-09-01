"""Focused tests for immutable m2c revision execution."""

from __future__ import annotations

import tempfile
import unittest
import sys
from dataclasses import fields, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.m2c_revision_provider import (
    CURRENT_M2C_REVISION,
    M2CProviderError,
    M2CDraftPayload,
    M2CInvocation,
    M2CRevisionIdentity,
    PinnedM2CRevisionProvider,
    make_invocation,
)
from automation.search_archive import ContentAddressedArchive
from automation.search_types import hash_bytes


def identity(label: str) -> str:
    return hash_bytes(label.encode("utf-8"))


class M2CRevisionProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="m2c-provider-")
        self.archive = ContentAddressedArchive(Path(self.temp.name) / "archive")
        self.assembly = b"glabel fn\n  jr $ra\n   nop\n"
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
        self.revision = M2CRevisionIdentity(
            revision_id=CURRENT_M2C_REVISION,
            tree_identity=identity("tree"),
            provider_identity=identity("provider"),
            executable_identity=identity("executable"),
            config_identity=identity("config"),
            clean=True,
            detached=True,
        )
        self.archive_identity = identity("archive")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def invocation(self):
        return make_invocation(
            revision_id=self.revision.revision_id,
            tree_identity=self.revision.tree_identity,
            provider_identity=self.revision.provider_identity,
            recipient_id="us:ST:fn",
            assembly_artifact=self.assembly_ref,
            context_artifacts=(self.context_ref,),
            switches=("--no-casts",),
            target_identity=identity("target"),
            compiler_identity=identity("compiler"),
            tool_identity=self.revision.executable_identity,
            evaluator_identity=identity("evaluator"),
            scorer_taxonomy_identity=identity("taxonomy"),
            config_identity=self.revision.config_identity,
            integration_gate_id=identity("gate"),
            integration_gate_artifact_id=identity("gate-artifact"),
            subset_identity=identity("subset"),
            queue_evidence_identity=identity("queue"),
            archive_identity=self.archive_identity,
            ordinal=0,
        )

    def provider(self, generator=None):
        return PinnedM2CRevisionProvider(
            (self.revision,),
            generator=generator or (
                lambda _invocation, *, assembly, contexts: (
                    "int fn(void) { return " + str(len(assembly) + len(contexts[0])) + "; }\n"
                )
            ),
            archive=self.archive,
            archive_identity=self.archive_identity,
        )

    def test_revision_is_full_clean_detached_and_explicit(self) -> None:
        self.assertEqual(
            self.provider().resolve_revision(CURRENT_M2C_REVISION),
            self.revision,
        )
        with self.assertRaises(M2CProviderError):
            self.provider().resolve_revision(CURRENT_M2C_REVISION[:7])
        with self.assertRaises(M2CProviderError):
            replace(self.revision, clean=False)
        with self.assertRaises(M2CProviderError):
            replace(self.revision, detached=False)

    def test_generation_is_replayable_and_archived(self) -> None:
        invocation = self.invocation()
        provider = self.provider()
        first = provider.generate_draft(
            invocation,
            assembly=self.assembly,
            contexts=(self.context,),
        )
        second = provider.generate_draft(
            invocation,
            assembly=self.assembly,
            contexts=(self.context,),
        )
        self.assertEqual(first, second)
        self.assertEqual(first.invocation_id, invocation.invocation_id)
        self.assertTrue(self.archive.verify(first.source_artifact).startswith(b"int fn"))
        self.assertEqual(M2CInvocation.from_dict(invocation.to_dict()), invocation)
        self.assertEqual(M2CDraftPayload.from_dict(first.to_dict()), first)

    def test_invocation_must_bind_revision_and_archive(self) -> None:
        invocation = self.invocation()
        wrong_tool = make_invocation(
            **{
                field.name: getattr(invocation, field.name)
                for field in fields(invocation)
                if field.name not in {"invocation_id", "tool_identity"}
            },
            tool_identity=identity("other-tool"),
        )
        with self.assertRaises(M2CProviderError):
            self.provider().generate_draft(
                wrong_tool,
                assembly=self.assembly,
                contexts=(self.context,),
            )
        with self.assertRaises(M2CProviderError):
            self.provider().generate_draft(
                invocation,
                assembly=self.assembly + b"nop\n",
                contexts=(self.context,),
            )

    def test_deserialization_refuses_unknown_fields_and_protocols(self) -> None:
        invocation = self.invocation()
        unknown = {**invocation.to_dict(), "unknown": "field"}
        with self.assertRaises(M2CProviderError):
            M2CInvocation.from_dict(unknown)
        wrong_protocol = {**invocation.to_dict(), "protocol": "m2c-untrusted-v0"}
        with self.assertRaises(M2CProviderError):
            M2CInvocation.from_dict(wrong_protocol)

    def test_internal_type_error_is_not_used_as_an_arity_probe(self) -> None:
        calls = []

        def broken(_invocation, *, assembly, contexts):
            calls.append((assembly, contexts))
            raise TypeError("generator defect")

        with self.assertRaisesRegex(TypeError, "generator defect"):
            self.provider(broken).generate_draft(
                self.invocation(),
                assembly=self.assembly,
                contexts=(self.context,),
            )
        self.assertEqual(len(calls), 1)

    def test_unsupported_generator_signature_is_refused_before_call(self) -> None:
        calls = []

        def wrong(one):
            calls.append(one)
            return "int fn(void) { return 0; }\n"

        with self.assertRaises(M2CProviderError):
            self.provider(wrong)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
