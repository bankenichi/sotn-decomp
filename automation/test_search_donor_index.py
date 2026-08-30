"""Task 5 tests: the four-version immutable donor index generation."""

from __future__ import annotations

import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive
from automation.search_donor_index import (
    DONOR_VERSIONS,
    DonorIndexGeneration,
    DonorIndexIdentityMismatch,
    DonorIndexInputError,
    DonorRevision,
    DonorRevisionSetError,
    build_donor_index,
)
from automation.search_lanes import DonorEvidence
from automation.search_types import hash_bytes
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
    """Mint one multi-record gate in its own fresh archive.

    ``_factory_gate`` moves its completed run root onto the archive root, so
    every minting needs an untouched archive. The donor binding records the
    receipt payload; the index archive itself stays independent.
    """

    _GATE_COUNTER[str(directory)] += 1
    gate_archive = ContentAddressedArchive(
        Path(directory) / f"gate-archive-{_GATE_COUNTER[str(directory)]}"
    )
    return _factory_gate(gate_archive, multi_record=True)


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

            index = build_donor_index(
                revisions,
                integration_gate=mint_gate(Path(directory)),
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
            gate = mint_gate(Path(directory))
            forward = build_donor_index(
                revisions,
                integration_gate=gate,
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
                build_donor_index(
                    revisions[:3],
                    integration_gate=mint_gate(Path(directory)),
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
                build_donor_index(
                    revisions + (DonorRevision(
                        version="pspeu",
                        revision=revision_identity("duplicate-pspeu"),
                        source_artifact=revisions[2].source_artifact,
                    ),),
                    integration_gate=mint_gate(Path(directory)),
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
            gate = mint_gate(Path(directory))

            def scan_swapped(revision):
                other = next(
                    item for item in revisions if item.version != revision.version
                )
                return (donor_evidence(revision, sources[other.version]),)

            with self.assertRaises(DonorIndexIdentityMismatch):
                build_donor_index(
                    revisions,
                    integration_gate=gate,
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
                build_donor_index(
                    revisions,
                    integration_gate=mint_gate(Path(directory)),
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
            gate = mint_gate(Path(directory))

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
            gate = mint_gate(Path(directory))
            base = build_donor_index(
                revisions,
                integration_gate=gate,
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
                    scan_revision=counting_scanner(Counter(), sources),
                    archive=archive,
                    **variant,
                )
                self.assertNotEqual(base.generation_id, changed.generation_id)

    def build_index(self, root: Path, *, config_identity: str):
        archive = ContentAddressedArchive(root)
        revisions, sources = fixture_revisions(archive)
        index = build_donor_index(
            revisions,
            integration_gate=mint_gate(root),
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


if __name__ == "__main__":
    unittest.main()
