from __future__ import annotations

import shutil
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation import search_indexed_runtime as runtime_module
from automation.search_archive import ArtifactRef, ContentAddressedArchive
from automation.search_donor_index import (
    DONOR_VERSIONS,
    DonorRevision,
)
from automation.search_indexed_runtime import (
    IndexedRuntimeArtifactError,
    IndexedRuntimeCollision,
    IndexedRuntimeError,
    IndexedRuntimeGeneration,
    IndexedRuntimeIdentityMismatch,
    IndexedRuntimeInputError,
    IndexedRuntimePartialPublication,
    DonorSnapshot,
    DonorSnapshotFile,
    load_indexed_runtime,
    publish_donor_snapshots,
    publish_indexed_runtime,
    verify_indexed_runtime,
)
from automation.search_lanes import DonorEvidence
from automation.search_target_renderer import TARGET_RENDERER_IDENTITY
from automation.search_types import canonical_bytes, hash_bytes, hash_canonical
from automation.test_search_donor_index import fixture_revisions
from automation.test_search_evidence_corpus import _factory_gate


_PROJECT_LESSONS = Path(__file__).resolve().parent.parent / "MATCHING-LESSONS.md"


def digest(label: str) -> str:
    return hash_bytes(label.encode("utf-8"))


def commit_identity(label: str) -> str:
    return digest(label).removeprefix("sha256:")


def _runtime_fixture(base: Path):
    """Create a real completed gate below the canonical repository root."""

    gate_archive = ContentAddressedArchive(base / "gate-archive")
    gate = _factory_gate(gate_archive, multi_record=True)
    revisions, original_sources = fixture_revisions(gate_archive)
    repo_candidates = tuple(base.glob("factory-repo-many-*"))
    if len(repo_candidates) != 1:
        raise AssertionError("factory gate did not leave exactly one fixture repository")
    repo = repo_candidates[0]
    shutil.copyfile(_PROJECT_LESSONS, repo / "MATCHING-LESSONS.md")
    snapshot_archive = ContentAddressedArchive(
        repo / runtime_module.DONOR_SNAPSHOT_ARCHIVE_ROOT
    )

    # DonorRevision.source_artifact is the scanner-owned, archive-backed
    # snapshot manifest, not a mutable checkout path.  Each manifest entry
    # points at an archive-owned byte object, and publication copies only those
    # verified bytes to the immutable per-version snapshot root.
    for module in (
        "search_donor_scan.py",
        "search_target_renderer.py",
        "search_donor_index.py",
        "search_types.py",
        "search_patterns.py",
        "search_evidence_corpus.py",
        "search_semantic_signatures.py",
    ):
        (repo / "automation" / module).write_text(
            f"fixture_{module.replace('.', '_')} = 1\n",
            encoding="utf-8",
        )
    revisions_with_snapshots = []
    sources = {}
    for revision in revisions:
        if revision.version == "saturn":
            config_files = (
                (
                    Path("config") / "saturn" / "runtime.prg.yaml",
                    (
                        "options:\n"
                        f"  src_path: src/{revision.version}\n"
                        f"  asm_path: asm/{revision.version}\n"
                    ).encode("utf-8"),
                ),
            )
        else:
            splat_path = Path("config") / f"splat.{revision.version}.runtime.yaml"
            config_files = (
                (
                    Path("config") / f"assets.{revision.version}.yaml",
                    (
                        f"version: {revision.version}\n"
                        f"src_path: src/{revision.version}\n"
                        "files:\n"
                        f"  - src_path: src/{revision.version}\n"
                        f"    splat_config_path: {splat_path.as_posix()}\n"
                    ).encode("utf-8"),
                ),
                (
                    splat_path,
                    (
                        "options:\n"
                        f"  src_path: src/{revision.version}\n"
                        f"  asm_path: asm/{revision.version}\n"
                    ).encode("utf-8"),
                ),
            )
        source_path = Path("src") / revision.version / "donor.c"
        assembly_path = Path("asm") / revision.version / "donor.s"
        source_bytes = gate_archive.verify(original_sources[revision.version])
        assembly_bytes = (
            f"glabel donor_{revision.version}\n"
            "\tnop\n"
        ).encode("utf-8")
        files = []
        for path, data in sorted(
            (*config_files, (source_path, source_bytes), (assembly_path, assembly_bytes)),
            key=lambda item: item[0].as_posix(),
        ):
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            kind = (
                "config"
                if path.parts[0] == "config"
                else "source"
                if path.suffix.lower() in {".c", ".h"}
                else "assembly"
            )
            byte_artifact = snapshot_archive.put_bytes(
                data,
                category="snapshot-files",
                suffix=path.suffix or ".bin",
                media_type=(
                    "text/yaml"
                    if kind == "config"
                    else "text/x-c"
                    if kind == "source"
                    else "text/x-asm"
                ),
            )
            files.append(
                {
                    "path": path.as_posix(),
                    "kind": kind,
                    "content_hash": hash_bytes(data),
                    "byte_size": len(data),
                    "artifact": byte_artifact.to_dict(),
                }
            )
        manifest_ref = snapshot_archive.put_json(
            {
                "protocol": "sotn-donor-snapshot-manifest-v1",
                "version": revision.version,
                "revision": revision.revision,
                "files": files,
            },
            category="sources",
            suffix=".snapshot.json",
        )
        pinned = replace(revision, source_artifact=manifest_ref)
        revisions_with_snapshots.append(pinned)
        sources[revision.version] = manifest_ref
    gate_root = (
        repo
        / "nonmatchings"
        / "EntityFrozenShadeCrystal"
        / "search-runs"
        / gate.run_id
    )
    gate_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(gate_archive.run_root, gate_root)
    return repo, gate, tuple(revisions_with_snapshots), sources


def _scanner(sources, calls):
    def scan(revision, *, repo, archive):
        calls.append((revision.version, Path(repo), archive.run_root))
        return (
            DonorEvidence(
                donor_id=digest("runtime-donor:" + revision.version),
                recipient_id="us:ST/RNO0:func_a",
                version=revision.version,
                source=sources[revision.version],
                match_kind="exact_symbol",
                signature="runtime-signature:" + revision.version,
                symbol="func_a",
                instruction_signature="runtime-instructions",
                cfg_signature="runtime-cfg",
                dataflow_signature="runtime-dataflow",
                body=None,
                declarations={"return": {"types": ["int"]}},
                constants={"literal": 4},
                metadata={"scanner": "local-runtime-test"},
            ),
        )

    return scan


def _runtime_dir(repo: Path, generation: IndexedRuntimeGeneration) -> Path:
    return (
        repo
        / "nonmatchings/search-evidence/indexed-runtimes"
        / generation.runtime_id.removeprefix("sha256:")
    )


def _staging_dirs(repo: Path) -> tuple[Path, ...]:
    root = repo / runtime_module.INDEXED_RUNTIME_ROOT
    if not root.is_dir():
        return ()
    return tuple(
        sorted(
            path
            for path in root.iterdir()
            if path.name.startswith(runtime_module._STAGING_PREFIX)
        )
    )


class IndexedRuntimePublicationTests(unittest.TestCase):
    def test_real_gate_corpus_index_and_complete_binding_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, sources = _runtime_fixture(Path(directory))
            calls = []
            scanner = _scanner(sources, calls)
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=scanner,
            ):
                generation = publish_indexed_runtime(
                    gate.run_id,
                    revisions,
                    repo=repo,
                )

            self.assertEqual(
                [version for version, _repo, _archive in calls],
                list(DONOR_VERSIONS),
            )
            self.assertTrue(all(item[1] != repo for item in calls))
            self.assertTrue(
                all("snapshots" in item[1].parts for item in calls)
            )
            self.assertEqual(generation.binding.integration_gate_id, gate.gate_id)
            self.assertEqual(generation.binding.integration_gate, gate)
            self.assertEqual(generation.binding.revisions, revisions)
            self.assertEqual(
                generation.binding.corpus_generation_id,
                generation.corpus.generation_id,
            )
            self.assertEqual(
                generation.binding.donor_index_generation_id,
                generation.donor_index.generation_id,
            )
            self.assertTrue(generation.corpus.entries)
            self.assertTrue(any(entry.kind == "lesson" for entry in generation.corpus.entries))
            self.assertEqual(len(generation.donor_index.entries), len(DONOR_VERSIONS))
            self.assertTrue(
                all(entry.evidence.body is None for entry in generation.donor_index.entries)
            )
            self.assertEqual(
                generation.binding.scanner_identity,
                generation.binding.scanner_source_identity,
            )
            renderer_source_identity = hash_bytes(
                (repo / "automation" / "search_target_renderer.py").read_bytes()
            )
            self.assertEqual(
                generation.binding.renderer_identity,
                TARGET_RENDERER_IDENTITY,
            )
            self.assertEqual(
                generation.binding.renderer_source_identity,
                renderer_source_identity,
            )
            self.assertNotEqual(
                generation.binding.renderer_identity,
                generation.binding.renderer_source_identity,
            )
            serialized_binding = generation.to_dict()["binding"]
            self.assertEqual(
                serialized_binding["renderer_identity"],
                TARGET_RENDERER_IDENTITY,
            )
            self.assertEqual(
                serialized_binding["renderer_source_identity"],
                renderer_source_identity,
            )
            gate_root = (
                repo
                / "nonmatchings"
                / "EntityFrozenShadeCrystal"
                / "search-runs"
                / gate.run_id
            )
            gate_manifest = json.loads(
                (gate_root / "manifest.json").read_bytes().decode("utf-8")
            )
            expected_signature = hash_canonical(
                {
                    "protocol": "sotn-indexed-runtime-signature-v1",
                    "scanner_identity": generation.binding.scanner_identity,
                    "signature_module_identities": {
                        name: hash_bytes(
                            (repo / "automation" / name).read_bytes()
                        )
                        for name in (
                            "search_types.py",
                            "search_patterns.py",
                            "search_evidence_corpus.py",
                            "search_semantic_signatures.py",
                        )
                    },
                    "config_identity": gate_manifest["config_identity"],
                    "schema_identity": gate_manifest["schema_identity"],
                }
            )
            self.assertEqual(generation.binding.signature_identity, expected_signature)
            self.assertEqual(
                generation.runtime_id,
                generation.artifact.content_hash,
            )
            self.assertEqual(
                generation.artifact.path,
                "artifacts/indexed_runtimes/"
                + generation.runtime_id.removeprefix("sha256:")
                + ".json",
            )
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=AssertionError("verification rescanned a pinned revision"),
            ):
                verify_indexed_runtime(generation, repo=repo)
                loaded = load_indexed_runtime(generation.runtime_id, repo=repo)
            self.assertEqual(loaded, generation)
            self.assertEqual(
                IndexedRuntimeGeneration.from_dict(generation.to_dict()),
                generation,
            )

    def test_real_scanner_consumes_the_archive_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, _sources = _runtime_fixture(Path(directory))
            generation = publish_indexed_runtime(gate.run_id, revisions, repo=repo)
            self.assertEqual(
                {
                    entry.revision.version
                    for entry in generation.donor_index.entries
                },
                set(DONOR_VERSIONS),
            )
            self.assertTrue(generation.donor_index.entries)
            self.assertTrue(
                all(
                    entry.evidence.source == revisions[DONOR_VERSIONS.index(entry.revision.version)].source_artifact
                    for entry in generation.donor_index.entries
                )
            )
            verify_indexed_runtime(generation, repo=repo)

    def test_ordering_is_canonical_and_republication_is_idempotent_without_rescan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, sources = _runtime_fixture(Path(directory))
            calls = []
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=_scanner(sources, calls),
            ):
                first = publish_indexed_runtime(gate.run_id, revisions, repo=repo)
            self.assertEqual(len(calls), len(DONOR_VERSIONS))
            self.assertEqual(_staging_dirs(repo), ())

            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=AssertionError("idempotent publication rescanned"),
            ):
                second = publish_indexed_runtime(
                    gate.run_id,
                    tuple(reversed(revisions)),
                    repo=repo,
                )
            self.assertEqual(second, first)
            self.assertEqual(len(calls), len(DONOR_VERSIONS))
            self.assertEqual(_staging_dirs(repo), ())

    def test_source_artifact_must_be_an_archive_owned_snapshot_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, _sources = _runtime_fixture(Path(directory))
            forged_source = ArtifactRef(
                hash_bytes(b"mutable source"),
                "artifacts/sources/mutable.c",
                "text/x-c",
                len(b"mutable source"),
            )
            forged = (replace(revisions[0], source_artifact=forged_source), *revisions[1:])
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=AssertionError("invalid source artifact reached scanner"),
            ):
                with self.assertRaises(IndexedRuntimeError):
                    publish_indexed_runtime(gate.run_id, forged, repo=repo)

    def test_missing_or_corrupt_snapshot_bytes_fail_closed(self) -> None:
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as directory:
                repo, gate, revisions, _sources = _runtime_fixture(Path(directory))
                snapshot_root = repo / runtime_module.DONOR_SNAPSHOT_ARCHIVE_ROOT
                snapshot_archive = ContentAddressedArchive(snapshot_root)
                manifest = json.loads(
                    snapshot_archive.verify(revisions[0].source_artifact).decode("utf-8")
                )
                source_entry = next(
                    item for item in manifest["files"] if item["kind"] == "source"
                )
                source_path = snapshot_root / source_entry["artifact"]["path"]
                if corrupt:
                    source_path.write_bytes(b"corrupt pinned bytes")
                else:
                    source_path.unlink()
                with patch(
                    "automation.search_indexed_runtime.scan_repository_revision",
                    side_effect=AssertionError("corrupt source artifact reached scanner"),
                ):
                    with self.assertRaises(IndexedRuntimeError):
                        publish_indexed_runtime(gate.run_id, revisions, repo=repo)

    def test_checkout_drift_after_snapshot_does_not_change_scanned_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, sources = _runtime_fixture(Path(directory))
            calls = []
            base_scanner = _scanner(sources, calls)
            drifted = False
            checkout_repo = repo

            def scan(revision, *, repo: Path, archive):
                nonlocal drifted
                if not drifted:
                    (
                        checkout_repo
                        / "src"
                        / revisions[0].version
                        / "donor.c"
                    ).write_bytes(
                        b"checkout drift after immutable snapshot\n"
                    )
                    drifted = True
                return base_scanner(revision, repo=repo, archive=archive)

            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=scan,
            ):
                generation = publish_indexed_runtime(gate.run_id, revisions, repo=repo)
            self.assertTrue(drifted)
            self.assertEqual(len(calls), len(DONOR_VERSIONS))
            snapshot_source = (
                _runtime_dir(repo, generation)
                / "snapshots"
                / revisions[0].version
                / "src"
                / revisions[0].version
                / "donor.c"
            )
            snapshot_archive = ContentAddressedArchive(
                repo / runtime_module.DONOR_SNAPSHOT_ARCHIVE_ROOT
            )
            manifest = json.loads(
                snapshot_archive.verify(revisions[0].source_artifact).decode("utf-8")
            )
            source_entry = next(
                item for item in manifest["files"] if item["kind"] == "source"
            )
            expected_source = snapshot_archive.verify(
                ArtifactRef.from_dict(source_entry["artifact"])
            )
            self.assertEqual(snapshot_source.read_bytes(), expected_source)
            verify_indexed_runtime(generation, repo=repo)

    def test_required_production_modules_refuse_when_absent(self) -> None:
        required = (
            "search_donor_scan.py",
            "search_target_renderer.py",
            "search_donor_index.py",
            "search_types.py",
            "search_patterns.py",
            "search_evidence_corpus.py",
            "search_semantic_signatures.py",
        )
        for module in required:
            with self.subTest(module=module), tempfile.TemporaryDirectory() as directory:
                repo, _gate, _revisions, _sources = _runtime_fixture(Path(directory))
                (repo / "automation" / module).unlink()
                with self.assertRaises(IndexedRuntimeInputError):
                    runtime_module._module_identity(repo, module)

    def test_separate_snapshot_publisher_preserves_sealed_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, _sources = _runtime_fixture(Path(directory))
            gate_root = (
                repo
                / "nonmatchings"
                / "EntityFrozenShadeCrystal"
                / "search-runs"
                / gate.run_id
            )
            gate_before = {
                path.relative_to(gate_root).as_posix(): path.read_bytes()
                for path in gate_root.rglob("*")
                if path.is_file()
            }
            snapshot_archive = ContentAddressedArchive(
                repo / runtime_module.DONOR_SNAPSHOT_ARCHIVE_ROOT
            )
            snapshots = []
            for revision in revisions:
                manifest = json.loads(
                    snapshot_archive.verify(revision.source_artifact).decode("utf-8")
                )
                files = tuple(
                    DonorSnapshotFile(
                        item["path"],
                        item["kind"],
                        snapshot_archive.verify(ArtifactRef.from_dict(item["artifact"])),
                    )
                    for item in manifest["files"]
                )
                snapshots.append(
                    DonorSnapshot(revision.version, revision.revision, files)
                )
            published = publish_donor_snapshots(tuple(snapshots), repo=repo)
            self.assertEqual(
                gate_before,
                {
                    path.relative_to(gate_root).as_posix(): path.read_bytes()
                    for path in gate_root.rglob("*")
                    if path.is_file()
                },
            )
            calls = []
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=_scanner(
                    {item.version: item.source_artifact for item in published},
                    calls,
                ),
            ):
                generation = publish_indexed_runtime(
                    gate.run_id,
                    published,
                    repo=repo,
                )
            self.assertEqual(tuple(item.version for item in published), DONOR_VERSIONS)
            self.assertEqual(tuple(item[0] for item in calls), DONOR_VERSIONS)
            verify_indexed_runtime(generation, repo=repo)

    def test_publication_intent_is_canonical_and_precedes_destination_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, sources = _runtime_fixture(Path(directory))
            writes = []
            original_write = runtime_module._write_exact

            def recording_write(path, data, *, label):
                writes.append((Path(path), label))
                return original_write(path, data, label=label)

            with patch(
                "automation.search_indexed_runtime._write_exact",
                side_effect=recording_write,
            ):
                generation = publish_indexed_runtime(
                    gate.run_id,
                    revisions,
                    repo=repo,
                )
            runtime_dir = _runtime_dir(repo, generation)
            intent_path = runtime_dir / "intent.json"
            intent_bytes = intent_path.read_bytes()
            intent = json.loads(intent_bytes.decode("utf-8"))
            self.assertEqual(intent_bytes, canonical_bytes(intent))
            self.assertEqual(
                [item["path"] for item in intent["artifacts"]],
                sorted(item["path"] for item in intent["artifacts"]),
            )
            destination_writes = [
                path
                for path, _label in writes
                if path == runtime_dir / "intent.json"
                or runtime_dir in path.parents
            ]
            intent_index = destination_writes.index(runtime_dir / "intent.json")
            artifact_indexes = [
                index
                for index, path in enumerate(destination_writes)
                if path != runtime_dir / "intent.json"
            ]
            self.assertTrue(artifact_indexes)
            self.assertLess(intent_index, min(artifact_indexes))

            intent["artifacts"] = list(reversed(intent["artifacts"]))
            intent_path.write_bytes(canonical_bytes(intent))
            with self.assertRaises(IndexedRuntimePartialPublication):
                publish_indexed_runtime(gate.run_id, revisions, repo=repo)

    def test_nested_artifact_and_snapshot_corruption_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, sources = _runtime_fixture(Path(directory))
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=_scanner(sources, []),
            ):
                generation = publish_indexed_runtime(gate.run_id, revisions, repo=repo)
            runtime_dir = _runtime_dir(repo, generation)
            runtime_dir.joinpath(generation.binding.corpus_artifact.path).write_bytes(
                b"corrupt nested corpus artifact"
            )
            with self.assertRaises(IndexedRuntimeError):
                verify_indexed_runtime(generation, repo=repo)

        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, sources = _runtime_fixture(Path(directory))
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=_scanner(sources, []),
            ):
                generation = publish_indexed_runtime(gate.run_id, revisions, repo=repo)
            snapshot_file = (
                _runtime_dir(repo, generation)
                / "snapshots"
                / revisions[0].version
                / "src"
                / revisions[0].version
                / "donor.c"
            )
            snapshot_file.unlink()
            with self.assertRaises(IndexedRuntimeError):
                load_indexed_runtime(generation.runtime_id, repo=repo)

    def test_renderer_identity_drift_and_binding_corruption_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, sources = _runtime_fixture(Path(directory))
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=_scanner(sources, []),
            ):
                generation = publish_indexed_runtime(gate.run_id, revisions, repo=repo)

            renderer_path = repo / "automation" / "search_target_renderer.py"
            renderer_bytes = renderer_path.read_bytes()
            try:
                renderer_path.write_bytes(renderer_bytes + b"renderer_drift = 1\n")
                with self.assertRaises(IndexedRuntimeIdentityMismatch):
                    verify_indexed_runtime(generation, repo=repo)
            finally:
                renderer_path.write_bytes(renderer_bytes)

            generation_path = _runtime_dir(repo, generation) / "generation.json"
            document = json.loads(generation_path.read_bytes().decode("utf-8"))
            document["binding"]["renderer_identity"] = (
                generation.binding.renderer_source_identity
            )
            generation_path.write_bytes(canonical_bytes(document))
            with self.assertRaises(IndexedRuntimeError):
                load_indexed_runtime(generation.runtime_id, repo=repo)

    def test_changed_pinned_revision_creates_a_distinct_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, sources = _runtime_fixture(Path(directory))
            calls = []
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=_scanner(sources, calls),
            ):
                first = publish_indexed_runtime(gate.run_id, revisions, repo=repo)
                changed_revision = commit_identity("changed-us")
                snapshot_archive = ContentAddressedArchive(
                    repo / runtime_module.DONOR_SNAPSHOT_ARCHIVE_ROOT
                )
                manifest_payload = json.loads(
                    snapshot_archive.verify(revisions[0].source_artifact).decode("utf-8")
                )
                manifest_payload["revision"] = changed_revision
                changed_manifest = snapshot_archive.put_json(
                    manifest_payload,
                    category="sources",
                    suffix=".snapshot.json",
                )
                sources[revisions[0].version] = changed_manifest
                changed = (
                    replace(
                        revisions[0],
                        revision=changed_revision,
                        source_artifact=changed_manifest,
                    ),
                    *revisions[1:],
                )
                second = publish_indexed_runtime(gate.run_id, changed, repo=repo)
            self.assertNotEqual(first.runtime_id, second.runtime_id)
            self.assertNotEqual(first.binding.revision_set_identity, second.binding.revision_set_identity)
            self.assertEqual(len(calls), len(DONOR_VERSIONS) * 2)
            verify_indexed_runtime(second, repo=repo)

    def test_publication_requires_exactly_one_revision_per_supported_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, _sources = _runtime_fixture(Path(directory))
            with self.assertRaises(IndexedRuntimeInputError):
                publish_indexed_runtime(gate.run_id, revisions[:-1], repo=repo)
            with self.assertRaises(IndexedRuntimeInputError):
                publish_indexed_runtime(
                    gate.run_id,
                    (*revisions[:3], revisions[0]),
                    repo=repo,
                )
            with self.assertRaises(IndexedRuntimeInputError):
                publish_indexed_runtime("missing-gate", revisions, repo=repo)

    def test_partial_publication_recovers_from_durable_stage_without_rescan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, sources = _runtime_fixture(Path(directory))
            calls = []
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=_scanner(sources, calls),
            ), patch(
                "automation.search_indexed_runtime.verify_indexed_runtime",
                side_effect=IndexedRuntimeArtifactError("injected pre-terminal failure"),
            ):
                with self.assertRaises(IndexedRuntimeArtifactError):
                    publish_indexed_runtime(gate.run_id, revisions, repo=repo)
            stages = _staging_dirs(repo)
            self.assertEqual(len(stages), 1)
            self.assertTrue(stages[0].is_dir())

            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=AssertionError("recovery rescanned a pinned revision"),
            ):
                recovered = publish_indexed_runtime(gate.run_id, revisions, repo=repo)
            self.assertEqual(recovered.runtime_id, recovered.artifact.content_hash)
            self.assertEqual(len(calls), len(DONOR_VERSIONS))
            self.assertEqual(_staging_dirs(repo), ())

    def test_archive_collision_is_refused_and_does_not_replace_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, sources = _runtime_fixture(Path(directory))
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=_scanner(sources, []),
            ):
                generation = publish_indexed_runtime(gate.run_id, revisions, repo=repo)
            runtime_dir = (
                repo
                / "nonmatchings/search-evidence/indexed-runtimes"
                / generation.runtime_id.removeprefix("sha256:")
            )
            runtime_artifact = runtime_dir / Path(generation.artifact.path)
            runtime_artifact.write_bytes(b"different immutable winner")
            with self.assertRaises(IndexedRuntimeCollision):
                publish_indexed_runtime(gate.run_id, revisions, repo=repo)
            self.assertEqual(runtime_artifact.read_bytes(), b"different immutable winner")

    def test_resume_rejects_a_canonical_different_generation_as_collision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, sources = _runtime_fixture(Path(directory))
            calls = []
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=_scanner(sources, calls),
            ):
                first = publish_indexed_runtime(gate.run_id, revisions, repo=repo)
                changed_revision = commit_identity("canonical-different-generation")
                snapshot_archive = ContentAddressedArchive(
                    repo / runtime_module.DONOR_SNAPSHOT_ARCHIVE_ROOT
                )
                manifest_payload = json.loads(
                    snapshot_archive.verify(revisions[0].source_artifact).decode("utf-8")
                )
                manifest_payload["revision"] = changed_revision
                changed_manifest = snapshot_archive.put_json(
                    manifest_payload,
                    category="sources",
                    suffix=".snapshot.json",
                )
                sources[revisions[0].version] = changed_manifest
                changed = (
                    replace(
                        revisions[0],
                        revision=changed_revision,
                        source_artifact=changed_manifest,
                    ),
                    *revisions[1:],
                )
                second = publish_indexed_runtime(gate.run_id, changed, repo=repo)

            first_generation_path = _runtime_dir(repo, first) / "generation.json"
            first_generation_path.write_bytes(canonical_bytes(second.to_dict()))
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=AssertionError("canonical collision path rescanned"),
            ):
                with self.assertRaises(IndexedRuntimeCollision):
                    publish_indexed_runtime(gate.run_id, revisions, repo=repo)

    def test_corrupt_runtime_and_wrong_root_inputs_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, sources = _runtime_fixture(Path(directory))
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=_scanner(sources, []),
            ):
                generation = publish_indexed_runtime(gate.run_id, revisions, repo=repo)
            generation_path = (
                repo
                / "nonmatchings/search-evidence/indexed-runtimes"
                / generation.runtime_id.removeprefix("sha256:")
                / "generation.json"
            )
            generation_path.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(IndexedRuntimeError):
                publish_indexed_runtime(gate.run_id, revisions, repo=repo)
            with self.assertRaises((IndexedRuntimeError, IndexedRuntimeIdentityMismatch)):
                load_indexed_runtime(generation.runtime_id, repo=repo)
            with self.assertRaises(IndexedRuntimeError):
                load_indexed_runtime(generation.runtime_id, repo=Path(directory) / "wrong-root")

    def test_typed_generation_rejects_duplicate_lineage_contexts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo, gate, revisions, sources = _runtime_fixture(Path(directory))
            with patch(
                "automation.search_indexed_runtime.scan_repository_revision",
                side_effect=_scanner(sources, []),
            ):
                generation = publish_indexed_runtime(gate.run_id, revisions, repo=repo)
            forged = generation.to_dict()
            forged["lineage_contexts"] = list(forged["lineage_contexts"]) * 2
            with self.assertRaises(IndexedRuntimeIdentityMismatch):
                IndexedRuntimeGeneration.from_dict(forged)


if __name__ == "__main__":
    unittest.main()
