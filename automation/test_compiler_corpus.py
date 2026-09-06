"""Focused tests for the exact PSX compiler micro-corpus."""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import automation.compiler_corpus as compiler_corpus  # noqa: E402
from automation.compiler_corpus import (  # noqa: E402
    CompilerCorpusError,
    CompilerPipelineIdentity,
    DEFAULT_WEIGHTS,
    compile_snippet,
    pipeline_identity,
)
from automation.search_types import ScoreVector  # noqa: E402


FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "search"
    / "scorer-v1.json"
)


class TestCompilerCorpus(unittest.TestCase):
    def test_archived_translation_unit_uses_its_recipient_overlay_header(self):
        pipeline = compiler_corpus._pipeline()
        with tempfile.TemporaryDirectory() as directory:
            target, _, _ = compiler_corpus._compile_source(
                "int f(void) { return 7; }", pipeline, Path(directory), name="target",
            )
            measured = compiler_corpus.compile_against_object(
                '#include "rnz1.h"\nint f(void) { return 7; }', target.read_bytes(),
                expected_pipeline_identity=pipeline.identity.identity,
                recipient_id="us:ST/RNZ1:f", symbol="f",
            )
            rejected = compiler_corpus.compile_against_object(
                '#include "nonexistent-candidate-header.h"\nint f(void) { return 7; }', target.read_bytes(),
                expected_pipeline_identity=pipeline.identity.identity,
                recipient_id="us:ST/RNZ1:f", symbol="f",
            )
        self.assertEqual(measured.score["total"], 0)
        self.assertEqual(rejected.score["compile_status"], "failed")
        self.assertIn("nonexistent-candidate-header.h", rejected.diagnostic)

    def test_archived_target_evaluation_uses_real_psx_objects(self) -> None:
        pipeline = compiler_corpus._pipeline()
        with tempfile.TemporaryDirectory() as directory:
            target, _, _ = compiler_corpus._compile_source(
                "int f(int x) { return x + 1; }", pipeline, Path(directory), name="target"
            )
            target_bytes = target.read_bytes()
        exact = compiler_corpus.compile_against_object(
            "int f(int x) { return x + 1; }", target_bytes,
            expected_pipeline_identity=pipeline.identity.identity,
        )
        changed = compiler_corpus.compile_against_object(
            "int f(int x) { return x + 2; }", target_bytes,
            expected_pipeline_identity=pipeline.identity.identity,
        )
        self.assertEqual(exact.score["total"], 0)
        self.assertGreater(changed.score["total"], 0)
        self.assertTrue(exact.object_bytes.startswith(bytes.fromhex("7f454c46")))
        self.assertEqual(exact.score["compiler_identity"], pipeline.identity.identity)
        ScoreVector.from_dict(exact.score)

    def test_selected_function_rebases_internal_branch_destinations(self) -> None:
        pipeline = compiler_corpus._pipeline()
        source = "int f(int x) { if (x > 10) return x * 7; return x + 3; }"
        with tempfile.TemporaryDirectory() as directory:
            target, _, _ = compiler_corpus._compile_source(
                "int neighbor(int x) { return x * 7; } " + source,
                pipeline, Path(directory), name="target",
            )
            result = compiler_corpus.compile_against_object(
                source, target.read_bytes(), symbol="f",
                expected_pipeline_identity=pipeline.identity.identity,
            )
        self.assertEqual(result.score["total"], 0)

    def test_selected_function_rebases_unconditional_join_branch(self) -> None:
        pipeline = compiler_corpus._pipeline()
        source = ("extern void consume(int); int f(int x) { "
                  "if (x > 10) { consume(x); x *= 7; } "
                  "else { consume(x + 1); x += 3; } consume(x); return x; }")
        with tempfile.TemporaryDirectory() as directory:
            target, _, _ = compiler_corpus._compile_source(
                "int neighbor(int x) { return x * 7; } " + source,
                pipeline, Path(directory), name="target",
            )
            normalized, _ = compiler_corpus._normalized_disassembly(target, symbol="f")
            self.assertRegex(normalized, r"(?m)^j\t\.text\+0x[0-9a-f]+$")
            result = compiler_corpus.compile_against_object(
                source, target.read_bytes(), symbol="f",
                expected_pipeline_identity=pipeline.identity.identity,
            )
        self.assertEqual(result.score["total"], 0)

    def test_target_function_is_scored_without_neighbor_functions(self) -> None:
        pipeline = compiler_corpus._pipeline()
        with tempfile.TemporaryDirectory() as directory:
            target, _, _ = compiler_corpus._compile_source(
                "int neighbor(int x) { return x * 7; } int f(int x) { return x + 1; }",
                pipeline, Path(directory), name="target",
            )
            result = compiler_corpus.compile_against_object(
                "int f(int x) { return x + 1; }", target.read_bytes(),
                expected_pipeline_identity=pipeline.identity.identity, symbol="f",
            )
            self.assertEqual(result.score["total"], 0)
            with self.assertRaises(CompilerCorpusError):
                compiler_corpus.compile_against_object(
                    "int f(int x) { return x + 1; }", target.read_bytes(),
                    expected_pipeline_identity=pipeline.identity.identity, symbol="absent",
                )

    def test_archived_target_rejects_compiler_drift_before_execution(self) -> None:
        with patch.object(compiler_corpus, "_compile_source") as compile_source:
            with self.assertRaisesRegex(CompilerCorpusError, "identity"):
                compiler_corpus.compile_against_object(
                    "int f(void) { return 1; }", b"target",
                    expected_pipeline_identity="sha256:" + "0" * 64,
                )
            compile_source.assert_not_called()

    def test_archived_target_is_validated_even_when_candidate_is_invalid(self) -> None:
        with self.assertRaises(CompilerCorpusError):
            compiler_corpus.compile_against_object(
                "int f(void) { return + ; }", b"invalid target",
                expected_pipeline_identity=pipeline_identity().identity,
            )

    def test_archived_target_keeps_source_rejection_diagnostics(self) -> None:
        pipeline = compiler_corpus._pipeline()
        with tempfile.TemporaryDirectory() as directory:
            target, _, _ = compiler_corpus._compile_source(
                "int f(void) { return 1; }", pipeline, Path(directory), name="target"
            )
            result = compiler_corpus.compile_against_object(
                "int f(void) { return + ; }", target.read_bytes(),
                expected_pipeline_identity=pipeline.identity.identity,
            )
        self.assertEqual(result.score["compile_status"], "failed")
        self.assertIsNone(result.score["total"])
        self.assertIsNone(result.object_bytes)
        self.assertTrue(result.diagnostic)
        self.assertNotIn(directory, result.diagnostic)

    def test_identity_records_real_pipeline_inputs(self) -> None:
        identity = pipeline_identity()
        self.assertIn("cc1-psx", Path(identity.executable).name)
        self.assertRegex(identity.executable_hash, r"^sha256:[0-9a-f]{64}$")
        self.assertTrue(identity.arguments)
        self.assertTrue(identity.environment_defines)
        self.assertGreaterEqual(len(identity.tool_hashes), 5)
        self.assertTrue(
            all(re.fullmatch(r"sha256:[0-9a-f]{64}", value)
                for _name, value in identity.tool_hashes)
        )

    def test_identical_cases_have_identical_observations(self) -> None:
        source = "int f(int x) { return x + 1; }\n"
        first = compile_snippet(source, "plus-one-a")
        retry = compile_snippet(source, "plus-one-b")
        self.assertEqual(first.source_hash, retry.source_hash)
        self.assertEqual(first.object_hash, retry.object_hash)
        self.assertEqual(first.disassembly_hash, retry.disassembly_hash)
        self.assertEqual(first.pipeline_identity, retry.pipeline_identity)
        self.assertEqual(first.score, retry.score)

    def test_changed_source_changes_compiled_identity(self) -> None:
        first = compile_snippet("int f(int x) { return x + 1; }\n", "plus-one")
        changed = compile_snippet("int f(int x) { return x + 2; }\n", "plus-two")
        self.assertNotEqual(changed.source_hash, first.source_hash)
        self.assertNotEqual(changed.object_hash, first.object_hash, msg=f'first={first.to_dict()} changed={changed.to_dict()}')
        self.assertNotEqual(changed.disassembly_hash, first.disassembly_hash)

    def test_compiler_argument_changes_identity_before_compile(self) -> None:
        self.assertNotEqual(
            pipeline_identity().identity,
            pipeline_identity(compiler_args=("-O1",)).identity,
        )

    def test_compile_failure_has_no_fake_success_values(self) -> None:
        observation = compile_snippet(
            "int f(int x) { return x + ; }\n",
            "compile-failure",
        )
        self.assertIsNone(observation.object_hash, msg=str(observation.to_dict()))
        self.assertIsNone(observation.disassembly_hash)
        self.assertIsNone(observation.score["total"])
        self.assertEqual(observation.score["compile_status"], "failed")
        self.assertEqual(observation.score["components"], {
            "stack": 0,
            "regalloc": 0,
            "reordering": 0,
            "insertion": 0,
            "deletion": 0,
        })
        self.assertIsNone(observation.score["diagnostic_artifact"])
        self.assertNotIn("compiler-corpus-", observation.to_json())

    def test_invalid_reference_fails_closed(self) -> None:
        with self.assertRaises(CompilerCorpusError):
            compile_snippet(
                "int f(int x) { return x + 1; }\n",
                "invalid-reference",
                reference_source="int f(int x) { return x + ; }\n",
            )

    def test_internal_disassembly_failure_fails_closed(self) -> None:
        with patch.object(
            compiler_corpus,
            "_normalized_disassembly",
            side_effect=CompilerCorpusError("forced disassembly failure"),
        ):
            with self.assertRaises(CompilerCorpusError):
                compile_snippet(
                    "int f(int x) { return x + 1; }\n",
                    "forced-disassembly-failure",
                )

    def test_internal_scorer_failure_fails_closed(self) -> None:
        with patch.object(
            compiler_corpus,
            "_score_objects",
            side_effect=CompilerCorpusError("forced scorer failure"),
        ):
            with self.assertRaises(CompilerCorpusError):
                compile_snippet(
                    "int f(int x) { return x + 1; }\n",
                    "forced-scorer-failure",
                )

    def test_real_scorer_fixture_covers_required_cases(self) -> None:
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(data["fixture_version"], "scorer-v1")
        self.assertEqual(data["weights"], DEFAULT_WEIGHTS)
        pipeline = data["pipeline_identity"]
        pipeline_id = data["pipeline_identity_hash"]
        self.assertIn("cc1-psx", Path(pipeline["executable"]).name)
        self.assertRegex(pipeline["executable_hash"], r"^sha256:[0-9a-f]{64}$")
        self.assertRegex(pipeline_id, r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(
            CompilerPipelineIdentity(**pipeline).identity, pipeline_id
        )
        self.assertEqual(pipeline_identity().identity, pipeline_id)
        self.assertTrue(pipeline["arguments"])
        self.assertTrue(pipeline["environment_defines"])
        self.assertTrue(pipeline["tool_hashes"])
        tool_hashes = {
            item["name"]: item["hash"] for item in pipeline["tool_hashes"]
        }
        self.assertEqual(
            pipeline["executable_hash"], tool_hashes[pipeline["executable"]]
        )
        self.assertEqual(
            {case["name"] for case in data["cases"]},
            {"exact", "reorder", "register", "stack",
             "insertion", "deletion", "compile-failure"},
        )
        for case in data["cases"]:
            observation = case["observation"]
            self.assertRegex(
                observation["source_hash"], r"^sha256:[0-9a-f]{64}$"
            )
            self.assertRegex(
                observation["pipeline_identity"], r"^sha256:[0-9a-f]{64}$"
            )
            self.assertEqual(
                observation["pipeline_identity"], pipeline_id
            )
            self.assertIn(case["kind"], {
                "exact", "reordering", "register-allocation",
                "stack", "insertion", "deletion", "compile-failure",
            })
            score = observation["score"]
            ScoreVector.from_dict(score)
            self.assertEqual(score["compiler_identity"], pipeline_id)
            if case["kind"] == "compile-failure":
                self.assertIsNone(observation["object_hash"])
                self.assertIsNone(observation["disassembly_hash"])
                self.assertIsNone(score["total"])
                self.assertEqual(score["compile_status"], "failed")
                self.assertNotIn("compiler-corpus-", json.dumps(score))
            else:
                expected_component = {
                    "exact": None,
                    "reordering": "reordering",
                    "register-allocation": "regalloc",
                    "stack": "stack",
                    "insertion": "insertion",
                    "deletion": "deletion",
                }[case["kind"]]
                if expected_component is not None:
                    self.assertGreater(
                        score["components"][expected_component], 0
                    )
                self.assertRegex(score["object_hash"], r"^sha256:[0-9a-f]{64}$")
                self.assertRegex(
                    observation["object_hash"], r"^sha256:[0-9a-f]{64}$"
                )
                self.assertRegex(
                    observation["disassembly_hash"], r"^sha256:[0-9a-f]{64}$"
                )
                self.assertIsInstance(score["total"], int)
                self.assertRegex(
                    score["mismatch_signature"],
                    r"^sha256:[0-9a-f]{64}$",
                )
                self.assertEqual(score["weights"], DEFAULT_WEIGHTS)





if __name__ == "__main__":
    unittest.main()
