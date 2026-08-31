"""Task 5 tests: the four-version immutable donor index generation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from collections import Counter
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive, ArtifactRef
from automation.search_donor_index import (
    DONOR_VERSIONS,
    DonorIndexBinding,
    DonorIndexEntry,
    DonorIndexGeneration,
    DonorIndexIdentityMismatch,
    DonorIndexInputError,
    DonorRevision,
    DonorRevisionSetError,
    build_donor_index,
    make_donor_binding,
)
from automation.search_supervisor import IntegrationGateError
from automation.search_lanes import DonorEvidence
from automation.search_types import RunManifest, hash_bytes
from automation.test_search_evidence_corpus import _factory_gate


def digest(label: str) -> str:
    return hash_bytes(label.encode("utf-8"))


def revision_identity(label: str) -> str:
    """A full 64-hex commit identity for one pinned version."""

    return hash_bytes(label.encode("utf-8")).removeprefix("sha256:")


def donor_evidence(revision: DonorRevision, source, *, constants=None, metadata=None):
    return DonorEvidence(
        donor_id=digest("donor:" + revision.version),
        recipient_id="us:ST:fn",
        version=revision.version,
        source=source,
        match_kind="exact_symbol",
        signature="sig:fn",
        symbol="fn",
        instruction_signature="ins:fn",
        cfg_signature="cfg:fn",
        dataflow_signature="flow:fn",
        body=None,
        constants=constants if constants is not None else {"literal": 4},
        metadata=metadata if metadata is not None else {"fixture": "scanner"},
    )


def fixture_revisions(archive: ContentAddressedArchive):
    """Pin one archive-owned source artifact per supported version."""

    revisions = []
    sources = {}
    for index, version in enumerate(DONOR_VERSIONS):
        source = archive.put_text(
            f"int donor_{version}(void) {{ return {index + 1}; }}\n",
            category="sources",
            suffix=".c",
            media_type="text/x-c",
        )
        sources[version] = source
        revisions.append(
            DonorRevision(
                version=version,
                revision=revision_identity("revision-" + version),
                source_artifact=source,
            )
        )
    return tuple(revisions), sources


_GATE_COUNTER: Counter = Counter()


def mint_gate(directory: Path):
    """Mint one multi-record gate with its own fresh run archive.

    ``_factory_gate`` moves its completed run root onto the archive root, so
    every minting needs an untouched archive. Returns the receipt and that
    archive: R19 requires the canonical integration-run archive at the donor
    boundary, separate from the donor output archive.
    """

    _GATE_COUNTER[str(directory)] += 1
    gate_archive = ContentAddressedArchive(
        Path(directory) / f"gate-archive-{_GATE_COUNTER[str(directory)]}"
    )
    return _factory_gate(gate_archive, multi_record=True), gate_archive


def counting_scanner(calls: Counter, sources):
    def scan_revision(revision):
        calls[revision.version] += 1
        return (
            donor_evidence(revision, sources[revision.version]),
        )

    return scan_revision


class DonorIndexGenerationTests(unittest.TestCase):
    def test_generation_scans_each_pinned_version_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            calls: Counter = Counter()

            gate, gate_archive = mint_gate(Path(directory))
            index = build_donor_index(
                revisions,
                integration_gate=gate,
                integration_archive=gate_archive,
                scan_revision=counting_scanner(calls, sources),
                indexer_identity=digest("indexer"),
                indexer_source_identity=digest("indexer-source"),
                config_identity=digest("index-config"),
                signature_identity=digest("signature"),
                schema_identity=digest("donor-schema"),
                generation_ordinal=1,
                archive=archive,
            )
            self.assertEqual(
                tuple(calls[version] for version in ("us", "hd", "pspeu", "saturn")),
                (1, 1, 1, 1),
            )
            self.assertEqual(len(index.entries), 4)
            self.assertTrue(
                all(entry.evidence.body is None for entry in index.entries)
            )
            self.assertTrue(
                all(
                    entry.evidence.metadata == {"fixture": "scanner"}
                    for entry in index.entries
                )
            )
            revision_by_version = {item.version: item for item in revisions}
            self.assertTrue(
                all(
                    entry.revision == revision_by_version[entry.evidence.version]
                    for entry in index.entries
                )
            )
            self.assertEqual(
                index.generation_id, index.artifact.content_hash
            )
            # The published bytes replay as an equal generation.
            replayed = DonorIndexGeneration.from_dict(index.to_dict())
            self.assertEqual(replayed, index)

    def test_generation_uses_compiler_from_verified_manifest_return(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            gate, gate_archive = mint_gate(Path(directory))
            archived_manifest = RunManifest.from_dict(
                json.loads((gate_archive.run_root / "manifest.json").read_text())
            )
            verified_manifest = replace(
                archived_manifest,
                compiler_identity=digest("verified-compiler"),
            )

            # The stub isolates propagation of the canonical validator return;
            # supervisor tests prove that the real return is the archived
            # manifest. This test must not imply that an in-memory generation
            # proves an archive relationship by itself.
            with patch(
                "automation.search_donor_index.validate_integration_gate",
                return_value=verified_manifest,
            ) as validate:
                index = build_donor_index(
                    revisions,
                    integration_gate=gate,
                    integration_archive=gate_archive,
                    scan_revision=counting_scanner(Counter(), sources),
                    indexer_identity=digest("indexer"),
                    indexer_source_identity=digest("indexer-source"),
                    config_identity=digest("index-config"),
                    signature_identity=digest("signature"),
                    schema_identity=digest("donor-schema"),
                    generation_ordinal=1,
                    archive=archive,
                )

            validate.assert_called_once_with(gate, archive=gate_archive)
            self.assertEqual(
                index.binding.compiler_identity,
                verified_manifest.compiler_identity,
            )

    def test_compiler_identity_is_content_addressed_on_direct_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index, _archive = self.build_index(
                Path(directory) / "index",
                config_identity=digest("index-config"),
            )

            with self.assertRaises(DonorIndexIdentityMismatch):
                replace(index.binding, compiler_identity="not-a-hash")

            forged_binding = replace(
                index.binding,
                compiler_identity=digest("forged-compiler"),
            )
            with self.assertRaises(DonorIndexIdentityMismatch):
                DonorIndexGeneration(
                    generation_id=index.generation_id,
                    binding=forged_binding,
                    revisions=index.revisions,
                    entries=index.entries,
                    artifact=index.artifact,
                )

            replay = index.to_dict()
            replay_binding = dict(replay["binding"])
            replay_binding["compiler_identity"] = digest("forged-compiler")
            replay["binding"] = replay_binding
            with self.assertRaises(DonorIndexIdentityMismatch):
                DonorIndexGeneration.from_dict(replay)

    def test_nested_evidence_aliases_cannot_change_generation_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            gate, gate_archive = mint_gate(Path(directory))
            declarations = {"return": {"types": ["int"]}}
            constants = {"literals": [{"value": 4}]}
            metadata = {"scanner": {"tags": ["semantic"]}}

            def scan_revision(revision):
                return (
                    DonorEvidence(
                        donor_id=digest("deep:" + revision.version),
                        recipient_id="us:ST:fn",
                        version=revision.version,
                        source=sources[revision.version],
                        match_kind="exact_symbol",
                        signature="sig:deep",
                        symbol="fn",
                        instruction_signature="ins:deep",
                        declarations=declarations,
                        constants=constants,
                        metadata=metadata,
                    ),
                )

            index = build_donor_index(
                revisions,
                integration_gate=gate,
                integration_archive=gate_archive,
                scan_revision=scan_revision,
                indexer_identity=digest("indexer"),
                indexer_source_identity=digest("indexer-source"),
                config_identity=digest("index-config"),
                signature_identity=digest("signature"),
                schema_identity=digest("donor-schema"),
                generation_ordinal=1,
                archive=archive,
            )
            before_bytes = archive.verify(index.artifact)
            before_generation = index.generation_id
            before_entries = tuple(entry.to_dict() for entry in index.entries)

            # These are the exact caller-owned containers supplied to the
            # scanner. They must not alias the published donor evidence.
            declarations["return"]["types"].append("void")
            constants["literals"][0]["value"] = 9
            metadata["scanner"]["tags"].append("forged")

            self.assertEqual(archive.verify(index.artifact), before_bytes)
            self.assertEqual(index.generation_id, before_generation)
            self.assertEqual(
                tuple(entry.to_dict() for entry in index.entries), before_entries
            )

    def test_changed_bound_identity_requires_new_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index_a, _fixture_a = self.build_index(
                Path(directory) / "index-a", config_identity=digest("config-a")
            )
            index_b, _fixture_b = self.build_index(
                Path(directory) / "index-b", config_identity=digest("config-b")
            )
            self.assertNotEqual(index_a.generation_id, index_b.generation_id)
            self.assertNotEqual(
                index_a.artifact.content_hash, index_b.artifact.content_hash
            )
            self.assertNotEqual(
                index_a.binding.config_identity, index_b.binding.config_identity
            )

    def test_reversed_revision_input_is_canonicalized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            calls: Counter = Counter()
            gate, gate_archive = mint_gate(Path(directory))
            forward = build_donor_index(
                revisions,
                integration_gate=gate,
                integration_archive=gate_archive,
                scan_revision=counting_scanner(calls, sources),
                indexer_identity=digest("indexer"),
                indexer_source_identity=digest("indexer-source"),
                config_identity=digest("index-config"),
                signature_identity=digest("signature"),
                schema_identity=digest("donor-schema"),
                generation_ordinal=1,
                archive=archive,
            )
            backward = build_donor_index(
                tuple(reversed(revisions)),
                integration_gate=gate,
                integration_archive=gate_archive,
                scan_revision=counting_scanner(calls, sources),
                indexer_identity=digest("indexer"),
                indexer_source_identity=digest("indexer-source"),
                config_identity=digest("index-config"),
                signature_identity=digest("signature"),
                schema_identity=digest("donor-schema"),
                generation_ordinal=1,
                archive=archive,
            )
            self.assertEqual(forward.generation_id, backward.generation_id)
            self.assertEqual(forward.revisions, backward.revisions)
            self.assertEqual(forward.entries, backward.entries)
            self.assertEqual(
                tuple(calls.values()),
                (2,) * 4,
                "canonical order must not rescan a pinned version",
            )

    def test_incomplete_revision_sets_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, _sources = fixture_revisions(archive)
            with self.assertRaises(DonorRevisionSetError):
                gate, gate_archive = mint_gate(Path(directory))
                build_donor_index(
                    revisions[:3],
                    integration_gate=gate,
                    integration_archive=gate_archive,
                    scan_revision=lambda _revision: (),
                    indexer_identity=digest("indexer"),
                    indexer_source_identity=digest("indexer-source"),
                    config_identity=digest("index-config"),
                    signature_identity=digest("signature"),
                    schema_identity=digest("donor-schema"),
                    generation_ordinal=1,
                    archive=archive,
                )
            with self.assertRaises(DonorRevisionSetError):
                gate, gate_archive = mint_gate(Path(directory))
                build_donor_index(
                    revisions + (DonorRevision(
                        version="pspeu",
                        revision=revision_identity("duplicate-pspeu"),
                        source_artifact=revisions[2].source_artifact,
                    ),),
                    integration_gate=gate,
                    integration_archive=gate_archive,
                    scan_revision=lambda _revision: (),
                    indexer_identity=digest("indexer"),
                    indexer_source_identity=digest("indexer-source"),
                    config_identity=digest("index-config"),
                    signature_identity=digest("signature"),
                    schema_identity=digest("donor-schema"),
                    generation_ordinal=1,
                    archive=archive,
                )

    def test_version_mismatch_and_body_bytes_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            gate, gate_archive = mint_gate(Path(directory))

            def scan_swapped(revision):
                other = next(
                    item for item in revisions if item.version != revision.version
                )
                return (donor_evidence(revision, sources[other.version]),)

            with self.assertRaises(DonorIndexIdentityMismatch):
                build_donor_index(
                    revisions,
                    integration_gate=gate,
                    integration_archive=gate_archive,
                    scan_revision=scan_swapped,
                    indexer_identity=digest("indexer"),
                    indexer_source_identity=digest("indexer-source"),
                    config_identity=digest("index-config"),
                    signature_identity=digest("signature"),
                    schema_identity=digest("donor-schema"),
                    generation_ordinal=1,
                    archive=archive,
                )

            def scan_with_body(revision):
                evidence = donor_evidence(revision, sources[revision.version])
                return (
                    DonorEvidence(
                        donor_id=evidence.donor_id,
                        recipient_id=evidence.recipient_id,
                        version=evidence.version,
                        source=evidence.source,
                        match_kind=evidence.match_kind,
                        signature=evidence.signature,
                        symbol=evidence.symbol,
                        instruction_signature=evidence.instruction_signature,
                        cfg_signature=evidence.cfg_signature,
                        dataflow_signature=evidence.dataflow_signature,
                        body="int stolen(void) { return 1; }\n",
                        constants=dict(evidence.constants),
                        metadata=dict(evidence.metadata),
                    ),
                )

            with self.assertRaises(DonorIndexInputError):
                gate, gate_archive = mint_gate(Path(directory))
                build_donor_index(
                    revisions,
                    integration_gate=gate,
                    integration_archive=gate_archive,
                    scan_revision=scan_with_body,
                    indexer_identity=digest("indexer"),
                    indexer_source_identity=digest("indexer-source"),
                    config_identity=digest("index-config"),
                    signature_identity=digest("signature"),
                    schema_identity=digest("donor-schema"),
                    generation_ordinal=1,
                    archive=archive,
                )

    def test_forbidden_metadata_and_unsafe_constants_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            gate, gate_archive = mint_gate(Path(directory))

            def scan_forbidden_metadata(revision):
                evidence = donor_evidence(
                    revision,
                    sources[revision.version],
                    metadata={"registers": {"a0": 4}},
                )
                return (evidence,)

            with self.assertRaises(DonorIndexInputError):
                build_donor_index(
                    revisions,
                    integration_gate=gate,
                    integration_archive=gate_archive,
                    scan_revision=scan_forbidden_metadata,
                    indexer_identity=digest("indexer"),
                    indexer_source_identity=digest("indexer-source"),
                    config_identity=digest("index-config"),
                    signature_identity=digest("signature"),
                    schema_identity=digest("donor-schema"),
                    generation_ordinal=1,
                    archive=archive,
                )

            def scan_unsafe_constant(revision):
                return (
                    donor_evidence(
                        revision,
                        sources[revision.version],
                        constants={"branch_displacement": "-0x7ffe"},
                    ),
                )

            with self.assertRaises(DonorIndexInputError):
                build_donor_index(
                    revisions,
                    integration_gate=gate,
                    integration_archive=gate_archive,
                    scan_revision=scan_unsafe_constant,
                    indexer_identity=digest("indexer"),
                    indexer_source_identity=digest("indexer-source"),
                    config_identity=digest("index-config"),
                    signature_identity=digest("signature"),
                    schema_identity=digest("donor-schema"),
                    generation_ordinal=1,
                    archive=archive,
                )

    def test_binding_identity_changes_produce_distinct_generations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            base_kwargs = dict(
                indexer_identity=digest("indexer"),
                indexer_source_identity=digest("indexer-source"),
                config_identity=digest("index-config"),
                signature_identity=digest("signature"),
                schema_identity=digest("donor-schema"),
                generation_ordinal=1,
            )
            gate, gate_archive = mint_gate(Path(directory))
            base = build_donor_index(
                revisions,
                integration_gate=gate,
                integration_archive=gate_archive,
                scan_revision=counting_scanner(Counter(), sources),
                archive=archive,
                **base_kwargs,
            )
            variants = (
                dict(base_kwargs, indexer_identity=digest("indexer-b")),
                dict(base_kwargs, indexer_source_identity=digest("indexer-source-b")),
                dict(base_kwargs, signature_identity=digest("signature-b")),
                dict(base_kwargs, schema_identity=digest("donor-schema-b")),
                dict(base_kwargs, generation_ordinal=2),
            )
            for variant in variants:
                # One gate across every build: the only delta in each pair is
                # the named binding field, so a distinct generation proves
                # that field alone changed the immutable identity.
                changed = build_donor_index(
                    revisions,
                    integration_gate=gate,
                    integration_archive=gate_archive,
                    scan_revision=counting_scanner(Counter(), sources),
                    archive=archive,
                    **variant,
                )
                self.assertNotEqual(base.generation_id, changed.generation_id)

    def build_index(self, root: Path, *, config_identity: str):
        archive = ContentAddressedArchive(root)
        revisions, sources = fixture_revisions(archive)
        gate, gate_archive = mint_gate(root)
        index = build_donor_index(
            revisions,
            integration_gate=gate,
            integration_archive=gate_archive,
            scan_revision=counting_scanner(Counter(), sources),
            indexer_identity=digest("indexer"),
            indexer_source_identity=digest("indexer-source"),
            config_identity=config_identity,
            signature_identity=digest("signature"),
            schema_identity=digest("donor-schema"),
            generation_ordinal=1,
            archive=archive,
        )
        return index, archive


class DonorIndexCorrectionTests(unittest.TestCase):
    """Assigned corrections: binding lanes, entry provenance, metadata."""

    def test_binding_forged_selected_lanes_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            gate_archive = ContentAddressedArchive(Path(directory) / "gate-archive")
            gate = _factory_gate(gate_archive, multi_record=True)
            index_archive = ContentAddressedArchive(Path(directory) / "index-archive")
            revisions, _sources = fixture_revisions(index_archive)
            binding = make_donor_binding(
                revisions,
                integration_gate=gate,
                compiler_identity=digest("compiler"),
                indexer_identity=digest("indexer"),
                indexer_source_identity=digest("indexer-source"),
                config_identity=digest("index-config"),
                signature_identity=digest("signature"),
                schema_identity=digest("donor-schema"),
                generation_ordinal=1,
            )
            # A forged lane set refuses inside the record itself: replace()
            # cannot smuggle a mismatched lane list past __post_init__.
            with self.assertRaises(DonorIndexIdentityMismatch):
                replace(
                    binding,
                    selected_lanes=("cfg_dataflow",),
                )
            self.assertEqual(binding.selected_lanes, gate.selected_lanes)

    def test_entry_revision_must_equal_the_pinned_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            gate, gate_archive = mint_gate(Path(directory))
            index = build_donor_index(
                revisions,
                integration_gate=gate,
                integration_archive=gate_archive,
                scan_revision=counting_scanner(Counter(), sources),
                indexer_identity=digest("indexer"),
                indexer_source_identity=digest("indexer-source"),
                config_identity=digest("index-config"),
                signature_identity=digest("signature"),
                schema_identity=digest("donor-schema"),
                generation_ordinal=1,
                archive=archive,
            )
            evidence = index.entries[0].evidence
            wrong_revision = DonorRevision(
                version=evidence.version,
                revision=revision_identity("forged-" + evidence.version),
                source_artifact=evidence.source,
            )
            forged_entry = DonorIndexEntry.from_evidence(wrong_revision, evidence)
            with self.assertRaises(DonorIndexIdentityMismatch):
                DonorIndexGeneration(
                    generation_id=index.generation_id,
                    binding=index.binding,
                    revisions=index.revisions,
                    entries=(forged_entry,),
                    artifact=index.artifact,
                )

    def test_duplicate_entry_ids_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            gate, gate_archive = mint_gate(Path(directory))

            def scan_twice(revision):
                evidence = donor_evidence(revision, sources[revision.version])
                return (evidence, evidence)

            with self.assertRaises(DonorIndexIdentityMismatch):
                build_donor_index(
                    revisions,
                    integration_gate=gate,
                    integration_archive=gate_archive,
                    scan_revision=scan_twice,
                    indexer_identity=digest("indexer"),
                    indexer_source_identity=digest("indexer-source"),
                    config_identity=digest("index-config"),
                    signature_identity=digest("signature"),
                    schema_identity=digest("donor-schema"),
                    generation_ordinal=1,
                    archive=archive,
                )
            index, _fixture = DonorIndexGenerationTests.build_index(self, Path(directory) / "index", config_identity=digest("index-config"))
            with self.assertRaises(DonorIndexIdentityMismatch):
                DonorIndexGeneration(
                    generation_id=index.generation_id,
                    binding=index.binding,
                    revisions=index.revisions,
                    entries=(index.entries[0], index.entries[0]),
                    artifact=index.artifact,
                )

    def test_artifact_metadata_must_match_canonical_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            gate, gate_archive = mint_gate(Path(directory))
            index = build_donor_index(
                revisions,
                integration_gate=gate,
                integration_archive=gate_archive,
                scan_revision=counting_scanner(Counter(), sources),
                indexer_identity=digest("indexer"),
                indexer_source_identity=digest("indexer-source"),
                config_identity=digest("index-config"),
                signature_identity=digest("signature"),
                schema_identity=digest("donor-schema"),
                generation_ordinal=1,
                archive=archive,
            )
            tampered_path = ArtifactRef(
                content_hash=index.artifact.content_hash,
                path="artifacts/donor_indexes/wrong.json",
                media_type="application/json",
                byte_size=index.artifact.byte_size,
            )
            with self.assertRaises(DonorIndexIdentityMismatch):
                DonorIndexGeneration(
                    generation_id=index.generation_id,
                    binding=index.binding,
                    revisions=index.revisions,
                    entries=index.entries,
                    artifact=tampered_path,
                )
            tampered_size = ArtifactRef(
                content_hash=index.artifact.content_hash,
                path=index.artifact.path,
                media_type="application/json",
                byte_size=index.artifact.byte_size + 1,
            )
            with self.assertRaises(DonorIndexIdentityMismatch):
                DonorIndexGeneration(
                    generation_id=index.generation_id,
                    binding=index.binding,
                    revisions=index.revisions,
                    entries=index.entries,
                    artifact=tampered_size,
                )

    def test_malformed_nested_parsers_raise_donor_domain_errors(self) -> None:
        with self.assertRaises(DonorIndexInputError):
            DonorRevision.from_dict({"version": "us"})
        with self.assertRaises(DonorIndexInputError):
            DonorIndexEntry.from_dict(
                {
                    "entry_id": digest("entry"),
                    "revision": {"version": "us"},
                    "evidence": {},
                }
            )
        with self.assertRaises(DonorIndexInputError):
            DonorIndexGeneration.from_dict({"generation_id": "garbage"})

    def test_full_shape_nested_parsers_translate_foreign_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index, _archive = DonorIndexGenerationTests.build_index(
                self,
                Path(directory) / "index", config_identity=digest("index-config")
            )
            revision_payload = index.revisions[0].to_dict()
            revision_payload["source_artifact"] = None
            with self.assertRaises(DonorIndexInputError):
                DonorRevision.from_dict(revision_payload)

            binding_payload = index.binding.to_dict()
            for invalid_gate in (None, "not-a-gate"):
                forged = dict(binding_payload)
                forged["integration_gate"] = invalid_gate
                with self.subTest(binding=invalid_gate):
                    with self.assertRaises(DonorIndexInputError):
                        DonorIndexBinding.from_dict(forged)

            entry_payload = index.entries[0].to_dict()
            for invalid_revision in (None, "not-a-revision"):
                forged = dict(entry_payload)
                forged["revision"] = invalid_revision
                with self.subTest(entry_revision=invalid_revision):
                    with self.assertRaises(DonorIndexInputError):
                        DonorIndexEntry.from_dict(forged)
            forged = dict(entry_payload)
            forged["evidence"] = None
            with self.assertRaises(DonorIndexInputError):
                DonorIndexEntry.from_dict(forged)
            for invalid_source in (None, "mutable/source.c"):
                forged = dict(entry_payload)
                forged_evidence = dict(entry_payload["evidence"])
                forged_evidence["source"] = invalid_source
                forged["evidence"] = forged_evidence
                with self.subTest(entry_source=invalid_source):
                    with self.assertRaises(DonorIndexInputError):
                        DonorIndexEntry.from_dict(forged)

            generation_payload = index.to_dict()
            for name, invalid in (
                ("revisions", None),
                ("revisions", "not-a-sequence"),
                ("entries", None),
                ("entries", "not-a-sequence"),
                ("artifact", None),
            ):
                forged = dict(generation_payload)
                forged[name] = invalid
                with self.subTest(generation_field=name, value=invalid):
                    with self.assertRaises(DonorIndexInputError):
                        DonorIndexGeneration.from_dict(forged)


class DonorGateArchiveTests(unittest.TestCase):
    """R19: the canonical integration-run archive gates every scan."""

    def build_args(self, directory: Path, *, integration_archive):
        archive = ContentAddressedArchive(Path(directory) / "index")
        revisions, sources = fixture_revisions(archive)
        gate, gate_archive = mint_gate(directory)
        return {
            "revisions": revisions,
            "sources": sources,
            "gate": gate,
            "gate_archive": gate_archive,
            "archive": archive,
            "integration_archive": integration_archive,
        }

    @staticmethod
    def build(args, calls: Counter):
        return build_donor_index(
            args["revisions"],
            integration_gate=args["gate"],
            integration_archive=args["integration_archive"],
            scan_revision=counting_scanner(calls, args["sources"]),
            indexer_identity=digest("indexer"),
            indexer_source_identity=digest("indexer-source"),
            config_identity=digest("index-config"),
            signature_identity=digest("signature"),
            schema_identity=digest("donor-schema"),
            generation_ordinal=1,
            archive=args["archive"],
        )

    def test_missing_integration_archive_is_refused_without_scanning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = self.build_args(Path(directory), integration_archive=None)
            calls: Counter = Counter()
            with self.assertRaises(IntegrationGateError):
                self.build(args, calls)
            self.assertEqual(sum(calls.values()), 0)

    def test_validated_gate_and_separate_output_archive_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = self.build_args(Path(directory), integration_archive=None)
            calls: Counter = Counter()
            args["integration_archive"] = args["gate_archive"]
            index = self.build(args, calls)
            self.assertEqual(
                tuple(calls[version] for version in DONOR_VERSIONS),
                (1, 1, 1, 1),
            )
            self.assertEqual(len(index.entries), 4)

    def test_corrupt_gate_receipt_is_refused_without_scanning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = self.build_args(Path(directory), integration_archive=None)
            path = args["gate_archive"].resolve(args["gate"].receipt_artifact)
            path.write_bytes(b"x" * args["gate"].receipt_artifact.byte_size)
            calls: Counter = Counter()
            with self.assertRaises(IntegrationGateError):
                self.build(args, calls)
            self.assertEqual(sum(calls.values()), 0)

    def test_wrong_run_root_archive_is_refused_without_scanning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = self.build_args(Path(directory), integration_archive=None)
            unrelated = ContentAddressedArchive(Path(directory) / "unrelated-run")
            unrelated.put_text("seed", category="sources")
            calls: Counter = Counter()
            args["integration_archive"] = unrelated
            with self.assertRaises(IntegrationGateError):
                self.build(args, calls)
            self.assertEqual(sum(calls.values()), 0)

    def test_receipt_from_another_run_is_refused_without_scanning(self) -> None:
        # A receipt that is internally self-consistent but belongs to a
        # different archived run must not authorize this scan: the archive
        # verification inside the canonical validator refuses it.
        with tempfile.TemporaryDirectory() as directory:
            args = self.build_args(Path(directory), integration_archive=None)
            other_gate, _other_archive = mint_gate(directory)
            calls: Counter = Counter()
            with self.assertRaises(IntegrationGateError):
                build_donor_index(
                    args["revisions"],
                    integration_gate=other_gate,
                    integration_archive=args["gate_archive"],
                    scan_revision=counting_scanner(calls, args["sources"]),
                    indexer_identity=digest("indexer"),
                    indexer_source_identity=digest("indexer-source"),
                    config_identity=digest("index-config"),
                    signature_identity=digest("signature"),
                    schema_identity=digest("donor-schema"),
                    generation_ordinal=1,
                    archive=args["archive"],
                )
            self.assertEqual(sum(calls.values()), 0)


class DonorEvidenceBoundaryTests(unittest.TestCase):
    """R21: nested unsafe evidence and malformed query fields are refused."""

    def scan_bad_evidence(self, directory: Path, evidence):
        archive = ContentAddressedArchive(Path(directory) / "index")
        revisions, sources = fixture_revisions(archive)
        gate, gate_archive = mint_gate(directory)

        def scan_revision(revision):
            return (evidence(revision),)

        return build_donor_index(
            revisions,
            integration_gate=gate,
            integration_archive=gate_archive,
            scan_revision=scan_revision,
            indexer_identity=digest("indexer"),
            indexer_source_identity=digest("indexer-source"),
            config_identity=digest("index-config"),
            signature_identity=digest("signature"),
            schema_identity=digest("donor-schema"),
            generation_ordinal=1,
            archive=archive,
        )

    def test_nested_register_metadata_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(DonorIndexInputError):
                self.scan_bad_evidence(
                    Path(directory),
                    lambda revision: donor_evidence(
                        revision,
                        revision.source_artifact,
                        metadata={"fixture": {"registers": {"a0": 4}}},
                    ),
                )

    def test_nested_relocation_metadata_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(DonorIndexInputError):
                self.scan_bad_evidence(
                    Path(directory),
                    lambda revision: donor_evidence(
                        revision,
                        revision.source_artifact,
                        metadata={
                            "symbols": {"fn": {"relocations": ["R_MIPS_26"]}}
                        },
                    ),
                )

    def test_nested_branch_displacement_constant_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(DonorIndexInputError):
                self.scan_bad_evidence(
                    Path(directory),
                    lambda revision: donor_evidence(
                        revision,
                        revision.source_artifact,
                        constants={"table": {"branch_offset": "-0x7ffe"}},
                    ),
                )

    def test_nested_register_constant_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(DonorIndexInputError):
                self.scan_bad_evidence(
                    Path(directory),
                    lambda revision: donor_evidence(
                        revision,
                        revision.source_artifact,
                        constants={"registers": {"a0": 4}},
                    ),
                )

    def test_malformed_selector_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            gate, gate_archive = mint_gate(directory)

            def scan_revision(revision):
                evidence = donor_evidence(revision, sources[revision.version])
                return (replace(evidence, symbol=""),)

            with self.assertRaises(DonorIndexInputError):
                build_donor_index(
                    revisions,
                    integration_gate=gate,
                    integration_archive=gate_archive,
                    scan_revision=scan_revision,
                    indexer_identity=digest("indexer"),
                    indexer_source_identity=digest("indexer-source"),
                    config_identity=digest("index-config"),
                    signature_identity=digest("signature"),
                    schema_identity=digest("donor-schema"),
                    generation_ordinal=1,
                    archive=archive,
                )

    def test_string_compatibility_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            gate, gate_archive = mint_gate(directory)

            def scan_revision(revision):
                evidence = donor_evidence(revision, sources[revision.version])
                return (replace(evidence, compatible="yes"),)

            with self.assertRaises(DonorIndexInputError):
                build_donor_index(
                    revisions,
                    integration_gate=gate,
                    integration_archive=gate_archive,
                    scan_revision=scan_revision,
                    indexer_identity=digest("indexer"),
                    indexer_source_identity=digest("indexer-source"),
                    config_identity=digest("index-config"),
                    signature_identity=digest("signature"),
                    schema_identity=digest("donor-schema"),
                    generation_ordinal=1,
                    archive=archive,
                )

    def test_selector_free_evidence_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            gate, gate_archive = mint_gate(directory)

            def scan_revision(revision):
                evidence = donor_evidence(revision, sources[revision.version])
                return (
                    replace(
                        evidence,
                        symbol=None,
                        instruction_signature=None,
                        cfg_signature=None,
                        dataflow_signature=None,
                    ),
                )

            with self.assertRaises(DonorIndexInputError):
                build_donor_index(
                    revisions,
                    integration_gate=gate,
                    integration_archive=gate_archive,
                    scan_revision=scan_revision,
                    indexer_identity=digest("indexer"),
                    indexer_source_identity=digest("indexer-source"),
                    config_identity=digest("index-config"),
                    signature_identity=digest("signature"),
                    schema_identity=digest("donor-schema"),
                    generation_ordinal=1,
                    archive=archive,
                )

    def test_valid_semantic_declarations_and_constants_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(Path(directory) / "index")
            revisions, sources = fixture_revisions(archive)
            gate, gate_archive = mint_gate(directory)

            def scan_revision(revision):
                return (
                    donor_evidence(
                        revision,
                        sources[revision.version],
                        constants={"literal": 4, "mask": "0xff"},
                        metadata={"fixture": "scanner", "origin": "us"},
                    ),
                )

            index = build_donor_index(
                revisions,
                integration_gate=gate,
                integration_archive=gate_archive,
                scan_revision=scan_revision,
                indexer_identity=digest("indexer"),
                indexer_source_identity=digest("indexer-source"),
                config_identity=digest("index-config"),
                signature_identity=digest("signature"),
                schema_identity=digest("donor-schema"),
                generation_ordinal=1,
                archive=archive,
            )
            self.assertEqual(len(index.entries), 4)


if __name__ == "__main__":
    unittest.main()
