"""Real compiler weighting, bounded trials and leakage/refusal regressions."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation import compiler_corpus as cc
from automation import weight_tuner as wt
from automation.search_archive import ContentAddressedArchive
from automation.search_types import hash_bytes, hash_canonical


class TunerTests(unittest.TestCase):
    def case(self, key, family=None, source=None, target=None, lineage=()):
        return {"case_id": key, "family": family or key, "lineage": list(lineage),
                "source": {"content_hash": source or key}, "target": {"content_hash": target or key}}

    def test_related_sources_and_lineages_never_cross_holdout(self):
        cases = [self.case("a", lineage=("ancestor",)), self.case("b", lineage=("ancestor",)),
                 self.case("c", source="b"), self.case("d")]
        split = wt.split_cases(cases, 7)
        self.assertIn(["a", "b", "c"], split["groups"])
        self.assertFalse(set(split["train"]).intersection(split["holdout"]))
        self.assertEqual(split, wt.split_cases(cases, 7))
        with self.assertRaisesRegex(wt.TuningError, "holdout would leak"):
            wt.split_cases(cases[:-1], 7)

    def test_five_weights_are_strict_and_positive(self):
        for invalid in ({**cc.DEFAULT_WEIGHTS, "stack": 0}, {**cc.DEFAULT_WEIGHTS, "stack": True},
                        {**cc.DEFAULT_WEIGHTS, "stack": 10001}, {"stack": 1}):
            with self.assertRaises(ValueError):
                wt.checked_weights(invalid)

    def test_top_level_assembly_isolated_but_inline_assembly_refused(self):
        source = '__asm__(".include \\"macro.inc\\"\\n");\nint f(void) { return 1; }'
        self.assertEqual(wt.mutation_source(source).strip(), "int f(void) { return 1; }")
        with self.assertRaisesRegex(wt.TuningError, "inline assembly"):
            wt.mutation_source('int f(void) { __asm__("nop"); return 1; }')

    def test_holdout_outcomes_do_not_select_weights(self):
        dataset = {"cases": [{"case_id": "a"}, {"case_id": "b"}],
                   "split": {"train": ["a"], "holdout": ["b"]}}
        def result(train, holdout):
            return {"trial": {"weights": cc.DEFAULT_WEIGHTS}, "cases": [
                {"case_id": key, "best_score": score, "exact_rediscovered": False, "cost_units": 1}
                for key, score in (("a", train), ("b", holdout))]}
        trained = result(1, 1000)
        self.assertIs(wt.rank_trials([result(2, 0), trained], dataset)[0][1], trained)

    def test_exact_rediscovery_outranks_lower_scalar_and_cost(self):
        dataset = {"cases": [{"case_id": "a"}, {"case_id": "b"}], "split": {"train": ["a"], "holdout": ["b"]}}
        def result(exact, score, cost):
            return {"trial": {"weights": cc.DEFAULT_WEIGHTS}, "cases": [
                {"case_id": key, "best_score": score, "exact_rediscovered": exact, "cost_units": cost}
                for key in ("a", "b")]}
        exact = result(True, 50, 10)
        self.assertIs(wt.rank_trials([result(False, 0, 1), exact], dataset)[0][1], exact)

    def test_actual_compiler_scores_use_requested_weights_and_restore_defaults(self):
        pipeline = cc._pipeline()
        with tempfile.TemporaryDirectory() as directory:
            target, _, _ = cc._compile_source("int f(int x) { return x + 1; }", pipeline, Path(directory), name="target")
            raw = target.read_bytes()
        source = "int f(int x) { return x * 7; }"
        normal = cc.compile_against_object(source, raw, expected_pipeline_identity=pipeline.identity.identity, symbol="f")
        doubled = {key: value * 2 for key, value in cc.DEFAULT_WEIGHTS.items()}
        changed = cc.compile_against_object(source, raw, expected_pipeline_identity=pipeline.identity.identity, symbol="f", weights=doubled)
        restored = cc.compile_against_object(source, raw, expected_pipeline_identity=pipeline.identity.identity, symbol="f")
        self.assertGreater(normal.score["total"], 0)
        self.assertEqual(changed.score["total"], normal.score["total"] * 2)
        self.assertEqual(changed.score["weights"], doubled)
        self.assertEqual(restored.score, normal.score)
        with patch.object(cc, "_pipeline", side_effect=AssertionError("must refuse before compiler")):
            with self.assertRaises(cc.CompilerCorpusError):
                cc.compile_against_object(source, raw, expected_pipeline_identity=pipeline.identity.identity, weights={"stack": 1})

    def test_real_trial_replays_without_compiler_or_archive_writes(self):
        pipeline = cc._pipeline()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target, _, _ = cc._compile_source("int f(int x) { return x + 1; }", pipeline, root, name="target")
            archive = ContentAddressedArchive(root / "run")
            case = {"case_id": hash_bytes(b"case"), "symbol": "f", "recipient": "us:ST/RNO1:f",
                    "compiler_identity": pipeline.identity.identity,
                    "source": archive.put_source("int f(int x) { return x * 7; }").to_dict(),
                    "target": archive.put_object(target.read_bytes()).to_dict()}
            dataset = {"dataset_id": hash_bytes(b"dataset"), "cases": [case]}
            trial = wt.trial_specs(dataset, 3, 0)[0]
            result = wt.run_trial(trial, dataset, archive)
            self.assertEqual(result["cases"][0]["cost_units"], 3)
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            with patch.object(wt, "compile_against_object", side_effect=AssertionError("duplicate compile")):
                replay = wt.run_trial(trial, dataset, wt.ReplayArchive(root / "run"), replay_only=True)
            self.assertEqual(replay, result)
            self.assertEqual(before, {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main()
