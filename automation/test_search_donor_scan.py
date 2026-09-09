"""Focused tests for the immutable four-platform donor scanner."""

from __future__ import annotations

import json
import io
import tarfile
import sys
import tempfile
import unittest
from unittest.mock import patch
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


class PinnedSourceCaptureTests(unittest.TestCase):
    def test_scalar_declarations_are_per_function_and_exclude_unbound_abis(self):
        from automation.search_donor_scan import _parse_c_file
        root = Path.cwd()
        functions = _parse_c_file(root / "donor.c", repo=root, text=(
            "static s32 first(u32 flags) { return flags; }\n"
            "void second(void) { }\n"
            "int third(int left, unsigned int right) { return left; }\n"
            "int pointer(int* ptr) { return *ptr; }\n"
            "int oldstyle() { return 1; }\n"
        ))
        self.assertEqual(functions[0].scalar_declaration, {"return_type": "int", "parameters": [{"type": "unsigned int", "name": "flags"}]})
        self.assertEqual(functions[1].scalar_declaration, {"return_type": "void", "parameters": []})
        self.assertEqual(len(functions[2].scalar_declaration["parameters"]), 2)
        self.assertIsNone(functions[3].scalar_declaration)
        self.assertIsNone(functions[4].scalar_declaration)

    def test_platform_projection_selects_donor_branch_and_preserves_offsets(self):
        from automation.search_donor_sources import project_platform_source
        source = '''#if defined(VERSION_US)
int donor(void) {return 1;}
#elif defined VERSION_HD
int donor(void) {return 2;}
#else
int donor(void) {return 3;}
#endif
'''
        for version, result in (("us", 1), ("hd", 2), ("pspeu", 3)):
            projected = project_platform_source(source, version)
            self.assertEqual(len(projected), len(source))
            self.assertEqual(projected.count("\n"), source.count("\n"))
            self.assertIn(f"return {result};", projected)
            self.assertEqual(projected.count("int donor"), 1)
            self.assertEqual(projected.index("int donor"), source.index(f"int donor(void) {{return {result};}}"))
        self.assertIsNone(project_platform_source(source, "saturn"))

    def test_platform_projection_refuses_unknown_active_conditions_and_bad_groups(self):
        from automation.search_donor_sources import project_platform_source as project
        for source in (
            "#ifdef UNKNOWN\nint f() {return 1;}\n#endif\n",
            "#if VERSION_US\n#endif\n",
            "#if 0 or 1\n#endif\n",
            "#if defined(VERSION_US)\n#else\n#else\n#endif\n",
            "#if 1\n#else\n#elif 0\n#endif\n",
            "#if 1\n", "#endif\n", "#define VERSION_US 0\n",
            "// continued comment " + "\\" + "\nint hidden() {return 1;}\n",
        ):
            self.assertIsNone(project(source, "us"), source)
        source = "#if 0\n#ifdef UNKNOWN\nwrong\n#endif\n#elif defined(VERSION_US)\nright\n#elif UNKNOWN\nwrong\n#endif\n"
        self.assertIn("right", project(source, "us"))
        self.assertNotIn("wrong", project(source, "us"))
        self.assertIsNone(project(source, "hd"))
        source = "#if !defined(VERSION_PSP) && \\\n (defined(VERSION_US) || defined(VERSION_HD)) // player's branch\nright\n#endif\n"
        self.assertIn("right", project(source, "us"))
        self.assertNotIn("right", project(source, "pspeu"))

    def test_source_membership_uses_only_active_donor_include_closure(self):
        from automation.search_donor_sources import configured_source_texts
        with tempfile.TemporaryDirectory() as temporary:
            fixture = DonorScanFixture(Path(temporary))
            source = fixture.source_roots["hd"]
            (source / "us_only.h").write_text("int wrong() {return 1;}")
            (source / "hd_only.h").write_text("int donor() {return 2;}")
            (source / "entry.c").write_text('/*\n#include "us_only.h"\n*/\n#if defined(VERSION_US)\n#include "us_only.h"\n#else\n#include "hd_only.h"\n#endif\n')
            roots = discover_platform_roots("hd", repo=fixture.repo, source_only=True)
            texts = {path: path.read_text() for path in fixture.repo.rglob("*") if path.is_file()}
            selected, coverage = configured_source_texts(roots, root=fixture.repo, texts=texts)
            self.assertIn(source / "hd_only.h", selected)
            self.assertNotIn(source / "us_only.h", selected)
            self.assertTrue(coverage["projection"]["defined_macros"]["VERSION_HD"])

    def test_nested_control_blocks_are_not_donor_functions(self):
        from automation.search_donor_scan import _parse_c_file
        root = Path("/fixture")
        source = '''int donor(int n) {
    if (n) { return 1; }
    if (n) { return 1; }
    while (n) { n--; }
    switch (n) { default: break; }
    return 0;
}
int next(void) { const char* url = "https://example/"; return 2; }
'''
        records = _parse_c_file(root / "donor.c", repo=root, text=source)
        self.assertEqual([item.name for item in records], ["donor", "next"])

    def test_function_extent_ignores_quotes_and_braces_in_line_comments(self):
        from automation.search_donor_scan import _parse_c_file
        root = Path("/fixture")
        body = "{\n// Player's state { is not a brace\n return 1; // }\n}"
        records = _parse_c_file(root / "donor.c", repo=root, text="int donor(void) " + body + "\nint next(void) {return 2;}\n")
        self.assertEqual([item.name for item in records], ["donor", "next"])
        self.assertEqual(records[0].body, body)

    def test_source_membership_follows_config_not_shared_directory(self):
        from automation.search_donor_sources import configured_source_texts
        with tempfile.TemporaryDirectory() as temporary:
            fixture = DonorScanFixture(Path(temporary))
            source = fixture.source_roots["hd"]
            (source / "wrong_platform.c").write_text("int excluded() { return 0; }")
            roots = discover_platform_roots("hd", repo=fixture.repo, source_only=True)
            texts = {path: path.read_text() for path in fixture.repo.rglob("*") if path.is_file()}
            selected, coverage = configured_source_texts(roots, root=fixture.repo, texts=texts)
            self.assertIn(source / "entry.c", selected)
            self.assertNotIn(source / "wrong_platform.c", selected)
            self.assertEqual(coverage["translation_units"], ["src/hd/mini/entry.c"])
            texts[source / "entry.c"] = "#if UNKNOWN\nint entry() {return 1;}\n#else\nint entry() {return 2;}\n#endif\n"
            selected, coverage = configured_source_texts(roots, root=fixture.repo, texts=texts)
            self.assertNotIn(source / "entry.c", selected)
            self.assertEqual(coverage["excluded_source_files"][0]["reason"], "conditional_source_requires_preprocessing")

    def test_source_capture_uses_commit_bytes_without_checkout_assembly(self):
        from automation.search_donor_capture import capture_pinned_donor_sources
        from automation.search_indexed_runtime import DONOR_SNAPSHOT_ARCHIVE_ROOT
        with tempfile.TemporaryDirectory() as temporary:
            fixture = DonorScanFixture(Path(temporary))
            hd_path = fixture.source_roots["hd"] / "entry.c"
            hd_text = hd_path.read_text()
            hd_text += "\nunsigned int distinct(unsigned int flags, int count) { return flags + count; }\n"
            hd_path.write_text("#if defined(VERSION_HD)\n" + hd_text +
                               "#else\nint wrong_platform() { return 999; }\n#endif\n")
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w") as bundle:
                for path in sorted(fixture.repo.rglob("*")):
                    if path.is_file() and path.relative_to(fixture.repo).parts[0] in {"src", "config"}:
                        bundle.add(path, arcname=path.relative_to(fixture.repo).as_posix())
            pairs = [(version, "a" * 40) for version in DONOR_VERSIONS]
            # Checkout drift is not a source input, even after acquisition.
            (fixture.source_roots["hd"] / "entry.c").write_text("int forged() { return 999; }")
            with patch("automation.search_donor_capture.commands_client.REPO", fixture.repo), patch(
                "automation.search_donor_capture.commands_client.read_pinned_donor_tree", return_value=stream.getvalue(),
            ) as read_tree:
                revisions = capture_pinned_donor_sources(pairs, repo=fixture.repo)
                self.assertEqual(read_tree.call_count, 1)
            archive = ContentAddressedArchive(fixture.repo / DONOR_SNAPSHOT_ARCHIVE_ROOT)
            evidence = scan_pinned_revisions(revisions, repo=fixture.repo, archive=archive)
            self.assertEqual({item.version for item in evidence}, set(DONOR_VERSIONS))
            self.assertTrue(all(item.symbol != "forged" for item in evidence))
            self.assertTrue(all(item.symbol != "wrong_platform" for item in evidence))
            self.assertTrue(any(item.version == "hd" and item.symbol == "entry" for item in evidence))
            distinct = next(item for item in evidence if item.version == "hd" and item.symbol == "distinct")
            self.assertEqual(distinct.declarations["return_type"], "unsigned int")
            self.assertEqual([p["name"] for p in distinct.declarations["parameters"]], ["flags", "count"])
            self.assertTrue(all("assembly_missing" in item.structural_differences for item in evidence))
            self.assertTrue(all(item.metadata["assembly_path"] is None for item in evidence))


if __name__ == "__main__":
    unittest.main()
