"""Focused tests for the immutable four-platform donor scanner."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive
from automation.search_donor_index import DONOR_VERSIONS, DonorRevision
from automation.search_donor_scan import (
    DONOR_SNAPSHOT_PROTOCOL,
    DonorScanConfigurationError,
    DonorScanInputError,
    discover_platform_roots,
    scan_pinned_revisions,
    scan_repository_revision,
)
from automation.search_semantic_signatures import SemanticInstruction, assembly_signatures
from automation.search_types import hash_bytes


def _revision(label: str) -> str:
    return hash_bytes(label.encode("utf-8")).removeprefix("sha256:")


class DonorScanFixture:
    """A real, small config/source/assembly tree for all supported versions."""

    def __init__(self, root: Path) -> None:
        self.repo = root / "repo"
        self.repo.mkdir()
        (self.repo / "config" / "saturn").mkdir(parents=True)
        self.archive = ContentAddressedArchive(root / "archive")
        self.revisions = []
        self.source_roots: dict[str, Path] = {}
        self.asm_roots: dict[str, Path] = {}
        for version in DONOR_VERSIONS:
            source_rel = Path("src") / version / "mini"
            asm_rel = Path("asm") / version / "mini"
            source_root = self.repo / source_rel
            asm_root = self.repo / asm_rel
            source_root.mkdir(parents=True)
            asm_root.mkdir(parents=True)
            self.source_roots[version] = source_root
            self.asm_roots[version] = asm_root
            (source_root / "entry.c").write_text(
                '#include "mini.h"\n'
                "typedef int MiniWord;\n"
                "static int helper(int value) { return value + 3; }\n"
                "int entry(int value) { return helper(value) + 7; }\n",
                encoding="utf-8",
            )
            (source_root / "mini.h").write_text(
                "#define MINI_LIMIT 12\n"
                "int entry(int value);\n",
                encoding="utf-8",
            )
            (asm_root / "entry.s").write_text(
                "glabel entry\n"
                "/* 0x00000000 */ addiu $sp, $sp, -16\n"
                "/* 0x00000004 */ jal helper\n"
                "/* 0x00000008 */ nop\n"
                "/* 0x0000000c */ jr $ra\n"
                "/* 0x00000010 */ nop\n",
                encoding="utf-8",
            )
            if version == "saturn":
                (self.repo / "config" / "saturn" / "mini.prg.yaml").write_text(
                    "options:\n"
                    "  asm_path: asm/saturn/mini\n"
                    "  src_path: src/saturn/mini\n"
                    "segments:\n"
                    "  - name: mini\n"
                    "    type: code\n"
                    "    subsegments:\n"
                    "      - [0x0, c, entry]\n",
                    encoding="utf-8",
                )
            else:
                (self.repo / "config" / f"assets.{version}.yaml").write_text(
                    f"version: {version}\n"
                    "files:\n"
                    "  - src_path: " + source_rel.as_posix() + "\n"
                    "    splat_config_path: config/splat."
                    + version
                    + ".mini.yaml\n",
                    encoding="utf-8",
                )
                (self.repo / "config" / f"splat.{version}.mini.yaml").write_text(
                    "options:\n"
                    f"  asm_path: {asm_rel.as_posix()}\n"
                    f"  src_path: {source_rel.as_posix()}\n"
                    "segments:\n"
                    "  - name: mini\n"
                    "    type: code\n"
                    "    subsegments:\n"
                    "      - [0x0, c, entry]\n",
                    encoding="utf-8",
                )
            source_manifest = self._publish_snapshot(version)
            self.revisions.append(
                DonorRevision(
                    version=version,
                    revision=_revision("mini-" + version),
                    source_artifact=source_manifest,
                )
            )

    def _snapshot_paths(self, version: str) -> tuple[Path, ...]:
        if version == "saturn":
            configs = tuple((self.repo / "config" / "saturn").glob("*.prg.yaml"))
        else:
            configs = (
                self.repo / "config" / f"assets.{version}.yaml",
                self.repo / "config" / f"splat.{version}.mini.yaml",
            )
        paths = list(configs)
        for root, suffixes in (
            (self.source_roots[version], {".c", ".h"}),
            (self.asm_roots[version], {".s", ".asm", ".inc"}),
        ):
            paths.extend(
                path
                for path in root.rglob("*")
                if path.is_file() and path.suffix.lower() in suffixes
            )
        return tuple(sorted(set(paths), key=lambda path: path.relative_to(self.repo).as_posix()))

    def _publish_snapshot(self, version: str):
        files = []
        for path in self._snapshot_paths(version):
            data = path.read_bytes()
            relative = path.relative_to(self.repo).as_posix()
            if relative.startswith("config/"):
                kind = "config"
            elif relative.startswith("src/"):
                kind = "source"
            else:
                kind = "assembly"
            artifact = self.archive.put_bytes(
                data,
                category="donor-snapshot-files",
                suffix=".bin",
                media_type="application/octet-stream",
            )
            files.append(
                {
                    "path": relative,
                    "kind": kind,
                    "content_hash": hash_bytes(data),
                    "byte_size": len(data),
                    "artifact": artifact.to_dict(),
                }
            )
        payload = {
            "protocol": DONOR_SNAPSHOT_PROTOCOL,
            "version": version,
            "revision": _revision("mini-" + version),
            "files": files,
        }
        return self.archive.put_json(payload, category="sources", suffix=".snapshot.json")

    def refresh_snapshot(self, version: str) -> None:
        index = DONOR_VERSIONS.index(version)
        self.revisions[index] = replace(
            self.revisions[index],
            source_artifact=self._publish_snapshot(version),
        )


class DonorScanTests(unittest.TestCase):
    def test_pspeu_arm_immediates_are_operands_not_comments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DonorScanFixture(Path(directory))
            asm_file = fixture.asm_roots["pspeu"] / "entry.s"
            asm_file.write_text(
                "entry:\n"
                "sub sp, sp, #16 @ stack frame\n"
                "bl helper\n"
                "add r0, r0, #7 @ result bias\n"
                "bx lr\n",
                encoding="utf-8",
            )
            fixture.refresh_snapshot("pspeu")
            evidence = scan_repository_revision(
                fixture.revisions[DONOR_VERSIONS.index("pspeu")],
                repo=fixture.repo,
                archive=fixture.archive,
            )
            entry = next(item for item in evidence if item.symbol == "entry")
            expected = assembly_signatures(
                (
                    SemanticInstruction("sub", "sp, sp, #16"),
                    SemanticInstruction("bl", "helper"),
                    SemanticInstruction("add", "r0, r0, #7"),
                    SemanticInstruction("bx", "lr"),
                )
            )
            self.assertEqual(
                (
                    entry.instruction_signature,
                    entry.cfg_signature,
                    entry.dataflow_signature,
                ),
                expected,
            )

    def test_saturn_sh_immediates_survive_bang_comments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DonorScanFixture(Path(directory))
            asm_file = fixture.asm_roots["saturn"] / "entry.s"
            asm_file.write_text(
                "entry:\n"
                "mov #7, r0 ! result value\n"
                "rts ! return\n"
                "nop\n",
                encoding="utf-8",
            )
            fixture.refresh_snapshot("saturn")
            evidence = scan_repository_revision(
                fixture.revisions[DONOR_VERSIONS.index("saturn")],
                repo=fixture.repo,
                archive=fixture.archive,
            )
            entry = next(item for item in evidence if item.symbol == "entry")
            expected = assembly_signatures(
                (
                    SemanticInstruction("mov", "#7, r0"),
                    SemanticInstruction("rts", ""),
                    SemanticInstruction("nop", ""),
                )
            )
            self.assertEqual(
                (
                    entry.instruction_signature,
                    entry.cfg_signature,
                    entry.dataflow_signature,
                ),
                expected,
            )

    def test_scans_all_platforms_in_canonical_order_with_stable_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DonorScanFixture(Path(directory))
            first = scan_pinned_revisions(
                fixture.revisions,
                repo=fixture.repo,
                archive=fixture.archive,
            )
            second = scan_pinned_revisions(
                tuple(reversed(fixture.revisions)),
                repo=fixture.repo,
                archive=fixture.archive,
            )
            self.assertEqual(
                tuple(
                    version
                    for version in DONOR_VERSIONS
                    if any(evidence.version == version for evidence in first)
                ),
                DONOR_VERSIONS,
            )
            self.assertEqual(
                tuple(evidence.to_dict() for evidence in first),
                tuple(evidence.to_dict() for evidence in second),
            )
            self.assertTrue(first)
            for evidence in first:
                self.assertIsNone(evidence.body)
                self.assertEqual(
                    evidence.source,
                    fixture.revisions[DONOR_VERSIONS.index(evidence.version)].source_artifact,
                )
                self.assertEqual(evidence.match_kind, "exact_symbol_path")
                self.assertTrue(evidence.symbol)
                self.assertTrue(evidence.instruction_signature)
                self.assertTrue(evidence.cfg_signature)
                self.assertTrue(evidence.dataflow_signature)
                self.assertIn("includes", evidence.declarations)
                self.assertIn("integer_literals", evidence.constants)
                self.assertIn("compatibility", evidence.metadata)
                forbidden = {
                    "bytes",
                    "registers",
                    "relocations",
                    "branch_displacements",
                }
                self.assertTrue(
                    forbidden.isdisjoint(evidence.metadata),
                    evidence.metadata,
                )
                self.assertTrue(forbidden.isdisjoint(evidence.constants))
                self.assertTrue(forbidden.isdisjoint(evidence.declarations))

    def test_each_revision_is_scanned_once_by_the_pinned_batch_helper(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DonorScanFixture(Path(directory))
            calls: list[str] = []

            def scanner(revision, *, repo, archive):
                calls.append(revision.version)
                return scan_repository_revision(
                    revision,
                    repo=repo,
                    archive=archive,
                )

            records = scan_pinned_revisions(
                fixture.revisions,
                repo=fixture.repo,
                archive=fixture.archive,
                scanner=scanner,
            )
            self.assertTrue(records)
            self.assertEqual(tuple(calls), DONOR_VERSIONS)

    def test_omits_common_unsafe_assembly_syntax_and_keeps_safe_semantics(self) -> None:
        cases = (
            (".byte 0x12, 0x34\n", "raw byte"),
            ("addiu $t0, $zero, %hi(symbol)\n", "relocation"),
            ("beq $t0, $zero, 0x10\n", "branch displacement"),
        )
        for assembly, _label in cases:
            with self.subTest(case=_label), tempfile.TemporaryDirectory() as directory:
                fixture = DonorScanFixture(Path(directory))
                asm_file = fixture.asm_roots["us"] / "entry.s"
                original = asm_file.read_text(encoding="utf-8")
                asm_file.write_text(
                    original.replace(
                        "/* 0x00000004 */ jal helper",
                        "/* 0x00000004 */ " + assembly.rstrip("\n"),
                    ),
                        encoding="utf-8",
                )
                fixture.refresh_snapshot("us")
                evidence = scan_repository_revision(
                    fixture.revisions[0],
                    repo=fixture.repo,
                    archive=fixture.archive,
                )
                self.assertTrue(evidence)
                self.assertTrue(any(item.symbol == "entry" for item in evidence))
                serialized = str([item.to_dict() for item in evidence])
                self.assertNotIn("%hi", serialized)
                self.assertNotIn("0x12", serialized)
                self.assertNotIn("0x10", serialized)

    def test_each_platform_traverses_common_unsafe_assembly_syntax(self) -> None:
        for version in DONOR_VERSIONS:
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                fixture = DonorScanFixture(Path(directory))
                asm_file = fixture.asm_roots[version] / "entry.s"
                original = asm_file.read_text(encoding="utf-8")
                asm_file.write_text(
                    original.replace(
                        "/* 0x00000004 */ jal helper",
                        "/* 0x00000004 */ .word %hi(helper)\n"
                        "/* 0x00000008 */ jal helper\n"
                        "/* 0x0000000c */ beq $t0, $zero, 0x10",
                    ),
                    encoding="utf-8",
                )
                fixture.refresh_snapshot(version)
                evidence = scan_repository_revision(
                    fixture.revisions[DONOR_VERSIONS.index(version)],
                    repo=fixture.repo,
                    archive=fixture.archive,
                )
                self.assertTrue(evidence)
                self.assertTrue(any(item.symbol == "entry" for item in evidence))

    def test_nested_source_resolves_matching_nested_assembly_before_basename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DonorScanFixture(Path(directory))
            source_nested = fixture.source_roots["us"] / "sub"
            asm_nested = fixture.asm_roots["us"] / "sub"
            source_nested.mkdir()
            asm_nested.mkdir()
            (source_nested / "nested.c").write_text(
                "int nested(void) { return 4; }\n",
                encoding="utf-8",
            )
            # A same-basename file at the assembly root contains a different
            # symbol.  A basename-first resolver would silently pair it with
            # nested.c and return the wrong semantic record.
            (fixture.asm_roots["us"] / "nested.s").write_text(
                "glabel wrong\n"
                "addiu $v0, $zero, 99\n"
                "jr $ra\n",
                encoding="utf-8",
            )
            (asm_nested / "nested.s").write_text(
                "glabel nested\n"
                "addiu $v0, $zero, 4\n"
                "jr $ra\n",
                encoding="utf-8",
            )
            fixture.refresh_snapshot("us")
            evidence = scan_repository_revision(
                fixture.revisions[0],
                repo=fixture.repo,
                archive=fixture.archive,
            )
            nested = next(item for item in evidence if item.symbol == "nested")
            self.assertEqual(nested.metadata["assembly_path"], "asm/us/mini/sub/nested.s")
            self.assertNotIn("assembly_missing", nested.structural_differences)

    def test_mutable_checkout_drift_cannot_change_published_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DonorScanFixture(Path(directory))
            before = scan_repository_revision(
                fixture.revisions[0],
                repo=fixture.repo,
                archive=fixture.archive,
            )
            source_file = fixture.source_roots["us"] / "entry.c"
            source_file.write_bytes(b"\xff mutable checkout drift\n")
            after = scan_repository_revision(
                fixture.revisions[0],
                repo=fixture.repo,
                archive=fixture.archive,
            )
            self.assertEqual(
                tuple(item.to_dict() for item in before),
                tuple(item.to_dict() for item in after),
            )

    def test_archive_snapshot_file_corruption_is_rejected_before_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DonorScanFixture(Path(directory))
            manifest_ref = fixture.revisions[0].source_artifact
            manifest = json.loads(fixture.archive.verify(manifest_ref).decode("utf-8"))
            file_ref = manifest["files"][0]["artifact"]
            fixture.archive.resolve(file_ref).write_bytes(b"corrupt")
            with self.assertRaises(DonorScanInputError):
                scan_repository_revision(
                    fixture.revisions[0],
                    repo=fixture.repo,
                    archive=fixture.archive,
                )

    def test_relabelled_shared_platform_roots_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DonorScanFixture(Path(directory))
            (fixture.repo / "config" / "assets.hd.yaml").write_text(
                "version: hd\n"
                "files:\n"
                "  - splat_config_path: config/splat.hd.mini.yaml\n",
                encoding="utf-8",
            )
            (fixture.repo / "config" / "splat.hd.mini.yaml").write_text(
                "options:\n"
                "  asm_path: asm/us/mini\n"
                "  src_path: src/us/mini\n"
                "segments:\n"
                "  - name: mini\n"
                "    type: code\n"
                "    subsegments:\n"
                "      - [0x0, c, entry]\n",
                encoding="utf-8",
            )
            fixture.refresh_snapshot("hd")
            with self.assertRaises(DonorScanConfigurationError):
                scan_pinned_revisions(
                    fixture.revisions,
                    repo=fixture.repo,
                    archive=fixture.archive,
                )

    def test_platform_metadata_persists_distinct_source_and_config_identities(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DonorScanFixture(Path(directory))
            evidence = scan_pinned_revisions(
                fixture.revisions,
                repo=fixture.repo,
                archive=fixture.archive,
            )
            by_version = {
                version: next(item for item in evidence if item.version == version)
                for version in DONOR_VERSIONS
            }
            for item in by_version.values():
                self.assertTrue(item.metadata["platform_identity"])
                self.assertTrue(item.metadata["source_identity"])
                self.assertTrue(item.metadata["assembly_identity"])
                self.assertTrue(item.metadata["config_identity"])
            self.assertEqual(
                len({item.metadata["platform_identity"] for item in by_version.values()}),
                len(DONOR_VERSIONS),
            )

    def test_mutable_root_removal_does_not_trigger_a_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DonorScanFixture(Path(directory))
            before = scan_repository_revision(
                fixture.revisions[1],
                repo=fixture.repo,
                archive=fixture.archive,
            )
            for child in (fixture.asm_roots["hd"]).iterdir():
                child.unlink()
            fixture.asm_roots["hd"].rmdir()
            after = scan_repository_revision(
                fixture.revisions[1],
                repo=fixture.repo,
                archive=fixture.archive,
            )
            self.assertEqual(
                tuple(item.to_dict() for item in before),
                tuple(item.to_dict() for item in after),
            )

    def test_shared_source_bytes_keep_platform_identities_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DonorScanFixture(Path(directory))
            shared_root = fixture.source_roots["us"]
            fixture.source_roots["hd"] = shared_root
            (fixture.repo / "config" / "assets.hd.yaml").write_text(
                "version: hd\n"
                "files:\n"
                "  - src_path: src/us/mini\n"
                "    splat_config_path: config/splat.hd.mini.yaml\n",
                encoding="utf-8",
            )
            (fixture.repo / "config" / "splat.hd.mini.yaml").write_text(
                "options:\n"
                "  asm_path: asm/hd/mini\n"
                "  src_path: src/us/mini\n"
                "segments:\n"
                "  - name: mini\n"
                "    type: code\n"
                "    subsegments:\n"
                "      - [0x0, c, entry]\n",
                encoding="utf-8",
            )
            fixture.revisions[1] = replace(
                fixture.revisions[1],
                source_artifact=fixture._publish_snapshot("hd"),
            )
            evidence = scan_pinned_revisions(
                fixture.revisions,
                repo=fixture.repo,
                archive=fixture.archive,
            )
            us = next(item for item in evidence if item.version == "us")
            hd = next(item for item in evidence if item.version == "hd")
            self.assertEqual(us.metadata["source_file_hash"], hd.metadata["source_file_hash"])
            self.assertNotEqual(us.metadata["source_identity"], hd.metadata["source_identity"])
            self.assertNotEqual(us.metadata["config_identity"], hd.metadata["config_identity"])
            self.assertNotEqual(us.metadata["assembly_identity"], hd.metadata["assembly_identity"])
            self.assertNotEqual(us.metadata["platform_identity"], hd.metadata["platform_identity"])

    def test_real_config_root_discovery_smoke_covers_each_platform(self) -> None:
        """Exercise bounded config traversal without scanning the full corpus."""

        repo = Path(__file__).resolve().parent.parent
        unavailable: list[str] = []
        for version in DONOR_VERSIONS:
            with self.subTest(version=version):
                try:
                    roots = discover_platform_roots(version, repo=repo)
                except DonorScanConfigurationError as exc:
                    # The checkout intentionally does not materialize every
                    # configured binary corpus.  Keep this smoke bounded and
                    # record that limitation rather than weakening discovery's
                    # refusal of a missing configured root.
                    if "is not a directory" not in str(exc):
                        raise
                    unavailable.append(version)
                    continue
                self.assertEqual(roots.version, version)
                self.assertTrue(roots.config_paths)
                self.assertTrue(roots.source_roots)
                self.assertTrue(roots.assembly_roots)
        if unavailable:
            self.skipTest(
                "bounded real-config smoke unavailable for materialized roots: "
                + ", ".join(unavailable)
            )


if __name__ == "__main__":
    unittest.main()
