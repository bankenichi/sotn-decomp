"""Focused safety and lifecycle tests for :mod:`automation.search_cli`."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_cli import (
    ArgumentFailure,
    ManifestError,
    PathSafetyError,
    RunInputError,
    SubsetArtifactError,
    fork_run,
    main,
    plan_selection,
    resume_run,
    run_manifest,
    status_run,
    stop_run,
    subset_artifact,
    subset_artifact_text,
    verify_ledger,
)
from automation.search_types import Budget, LANES, RunManifest, canonical_json
from automation.test_search_schema import manifest as schema_manifest


FIXTURE_MANIFEST = schema_manifest()


def _tree_listing(root: Path) -> tuple[str, ...]:
    return tuple(sorted(str(path.relative_to(root)) for path in root.rglob("*")))


def _write_manifest(root: Path, manifest: RunManifest) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "manifest.json"
    path.write_text(manifest.to_json() + "\n", encoding="utf-8")
    return path


class TestSearchSubsetPlanning(unittest.TestCase):
    def test_one_record_subset_is_explicit_and_deterministic(self) -> None:
        first = plan_selection(
            record_groups=[["us:ST/RNO0:one"]],
            lane_groups=[["transplant", "upstream_current"]],
        )
        second = plan_selection(
            record_groups=[["us:ST/RNO0:one"]],
            lane_groups=[["upstream_current", "transplant"]],
        )
        self.assertEqual(first, second)
        self.assertEqual(first.record_ids, ("us:ST/RNO0:one",))
        self.assertEqual(first.lanes, ("upstream_current", "transplant"))
        self.assertEqual(
            first.subset_identity,
            subset_artifact(first.record_ids)["artifact_hash"],
        )
        self.assertEqual(first.to_dict()["record_count"], 1)

    def test_multiple_records_are_sorted_without_queue_access(self) -> None:
        selection = plan_selection(
            record_groups=[["record-b", "record-a"]],
            lane_groups=[["upstream_current"]],
        )
        self.assertEqual(selection.record_ids, ("record-a", "record-b"))
        self.assertEqual(selection.input_kind, "explicit")

    def test_empty_subset_requires_an_explicit_records_option(self) -> None:
        selection = plan_selection(record_groups=[[]], lane_groups=[["upstream_current"]])
        self.assertEqual(selection.record_ids, ())
        self.assertEqual(selection.to_dict()["record_count"], 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty-subset.json"
            path.write_text(subset_artifact_text(()), encoding="utf-8")
            saved = plan_selection(
                subset_path=path,
                lane_groups=[["upstream_current"]],
            )
            self.assertEqual(saved.subset_identity, selection.subset_identity)
        with self.assertRaises(ArgumentFailure):
            plan_selection(record_groups=None, lane_groups=[["upstream_current"]])

    def test_saved_subset_hash_binding_and_changed_artifact_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            path = base / "subset.json"
            path.write_text(subset_artifact_text(["record-a"]), encoding="utf-8")
            before_bytes = path.read_bytes()
            before_listing = _tree_listing(base)
            explicit = plan_selection(
                record_groups=[["record-a"]],
                lane_groups=[["upstream_current"]],
            )
            self.assertEqual(explicit.record_ids, ("record-a",))
            self.assertEqual(path.read_bytes(), before_bytes)
            self.assertEqual(_tree_listing(base), before_listing)
            expected = plan_selection(
                subset_path=path,
                lane_groups=[["upstream_current"]],
            )
            self.assertEqual(expected.input_kind, "saved_artifact")
            self.assertEqual(expected.record_ids, ("record-a",))
            self.assertEqual(expected.subset_identity, explicit.subset_identity)
            self.assertEqual(path.read_bytes(), before_bytes)
            self.assertEqual(_tree_listing(base), before_listing)
            with self.assertRaises(SubsetArtifactError):
                plan_selection(
                    subset_path=path,
                    subset_hash="sha256:" + "0" * 64,
                    lane_groups=[["upstream_current"]],
                )
            changed = json.loads(subset_artifact_text(["record-b"]))
            changed["artifact_hash"] = expected.subset_identity
            path.write_text(canonical_json(changed) + "\n", encoding="utf-8")
            with self.assertRaises(SubsetArtifactError):
                plan_selection(
                    subset_path=path,
                    subset_hash=expected.subset_identity,
                    lane_groups=[["upstream_current"]],
                )

    def test_no_queue_state_fallback_and_unknown_lane_refuse(self) -> None:
        with self.assertRaises(ArgumentFailure):
            plan_selection(record_groups=None, lane_groups=[["upstream_current"]])
        with self.assertRaises(ArgumentFailure):
            plan_selection(record_groups=[["record-a"]], lane_groups=[["unknown_lane"]])

    def test_path_traversal_and_symlink_escape_refuse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with self.assertRaises(PathSafetyError):
                plan_selection(
                    subset_path=base / ".." / "outside.json",
                    lane_groups=[["upstream_current"]],
                )
            outside = base / "owned-targets" / "outside.json"
            outside.parent.mkdir()
            outside.write_text(subset_artifact_text(["record-a"]), encoding="utf-8")
            link = base / "subset-link.json"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable on this host")
            with self.assertRaises(PathSafetyError):
                plan_selection(subset_path=link, lane_groups=[["upstream_current"]])

    def test_run_root_and_fork_destination_symlink_escape_refuse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            real_run = base / "real-run"
            manifest_path = _write_manifest(real_run, FIXTURE_MANIFEST)
            run_link = base / "run-link"
            try:
                run_link.symlink_to(real_run, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable on this host")
            with self.assertRaises(PathSafetyError):
                # The manifest path itself traverses a symlinked run root.
                run_manifest(run_link / "manifest.json")

            source_root = base / "source-run"
            source_manifest = _write_manifest(source_root, FIXTURE_MANIFEST)
            run_manifest(source_manifest)
            destination = base / "destination"
            destination.mkdir()
            destination_link = base / "destination-link"
            destination_link.symlink_to(destination, target_is_directory=True)
            config = base / "fork-config.json"
            config.write_text(
                canonical_json({
                    **replace(FIXTURE_MANIFEST, run_id="symlink-child").to_dict(),
                    "destination_root": str(destination_link),
                }) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(PathSafetyError):
                fork_run(source_root, config)

    def test_unrecognized_cli_options_are_rejected_as_json(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["plan", "--records", "record-a", "--lanes", "upstream_current", "--nope"])
        self.assertEqual(code, 2)
        document = json.loads(output.getvalue())
        self.assertFalse(document["ok"])
        self.assertEqual(document["error"]["code"], "invalid_arguments")


class TestSearchSubsetLifecycle(unittest.TestCase):
    def test_queue_evidence_identity_is_required_and_typed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            missing_document = FIXTURE_MANIFEST.to_dict()
            missing_document.pop("queue_evidence_identity")
            missing_path = base / "missing" / "manifest.json"
            missing_path.parent.mkdir()
            missing_path.write_text(canonical_json(missing_document) + "\n", encoding="utf-8")
            with self.assertRaises(ManifestError):
                run_manifest(missing_path)

            malformed_document = FIXTURE_MANIFEST.to_dict()
            malformed_document["queue_evidence_identity"] = "not-a-hash"
            malformed_path = base / "malformed" / "manifest.json"
            malformed_path.parent.mkdir()
            malformed_path.write_text(canonical_json(malformed_document) + "\n", encoding="utf-8")
            with self.assertRaises(ManifestError):
                run_manifest(malformed_path)

    def test_changed_queue_evidence_identity_refuses_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            path = _write_manifest(root, FIXTURE_MANIFEST)
            run_manifest(path)
            changed_document = FIXTURE_MANIFEST.to_dict()
            changed_document["queue_evidence_identity"] = subset_artifact(
                ["changed-evidence"]
            )["artifact_hash"]
            path.write_text(canonical_json(changed_document) + "\n", encoding="utf-8")
            with self.assertRaises(RunInputError):
                status_run(root)

    def test_manifest_subset_identity_mismatch_refuses_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            root.mkdir()
            document = FIXTURE_MANIFEST.to_dict()
            document["run_id"] = "bad-subset-run"
            document["subset_identity"] = subset_artifact(["different-record"])["artifact_hash"]
            path = root / "manifest.json"
            path.write_text(canonical_json(document) + "\n", encoding="utf-8")
            with self.assertRaises(ManifestError):
                run_manifest(path)

    def test_stop_resume_preserve_task_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            manifest_path = _write_manifest(root, FIXTURE_MANIFEST)
            self.assertTrue(main(["run", "--manifest", str(manifest_path)]) == 0)
            from automation.search_coordinator import SearchCoordinator

            coordinator = SearchCoordinator(root, FIXTURE_MANIFEST)
            task = coordinator.create_task(
                recipient_id=FIXTURE_MANIFEST.queue_record_ids[0],
                lane=FIXTURE_MANIFEST.selected_lanes[0],
                operation="explicit-test",
            )
            coordinator.schedule_task(task)
            stopped = stop_run(root)
            self.assertTrue(stopped["ok"])
            self.assertEqual(stopped["receipt"]["payload"]["pending_task_ids"], [task.task_id])
            resumed = resume_run(root)
            self.assertEqual(resumed["reissued_tasks"][0]["task_id"], task.task_id)
            self.assertEqual(resumed["reissued_tasks"][0]["task_seed"], task.task_seed)
            self.assertEqual(resumed["reissued_tasks"][0]["budget_ordinal"], task.budget_ordinal)

    def test_status_and_verify_ledger_are_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            path = _write_manifest(root, FIXTURE_MANIFEST)
            run_manifest_output = io.StringIO()
            with contextlib.redirect_stdout(run_manifest_output):
                self.assertEqual(main(["run", "--manifest", str(path)]), 0)
            status = status_run(root)
            verified = verify_ledger(root)
            self.assertTrue(status["ok"])
            self.assertTrue(verified["ok"])
            self.assertEqual(verified["verdict"], "valid")

    def test_fork_uses_parent_identity_and_leaves_parent_ledger_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "parent"
            config = Path(directory) / "child-config.json"
            parent_manifest_path = _write_manifest(parent, FIXTURE_MANIFEST)
            self.assertEqual(main(["run", "--manifest", str(parent_manifest_path)]), 0)
            parent_ledger_before = (parent / "ledger.jsonl").read_bytes()
            child_manifest = replace(FIXTURE_MANIFEST, run_id="child-run")
            config.write_text(child_manifest.to_json() + "\n", encoding="utf-8")
            result = fork_run(parent, config)
            self.assertTrue(result["ok"])
            self.assertEqual(result["parent_run_id"], FIXTURE_MANIFEST.run_id)
            self.assertNotEqual(result["run_id"], result["parent_run_id"])
            self.assertEqual((parent / "ledger.jsonl").read_bytes(), parent_ledger_before)

    def test_explicit_empty_manifest_is_a_noop_without_queue_fallback(self) -> None:
        empty_manifest = replace(
            FIXTURE_MANIFEST,
            run_id="empty-run",
            queue_record_ids=(),
            function_ids=(),
            selected_lanes=(LANES[0],),
            target_identities={},
            lane_budgets={LANES[0]: Budget("attempts", 16, 0)},
            subset_identity=subset_artifact(())["artifact_hash"],
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "empty-run"
            path = _write_manifest(root, empty_manifest)
            started = run_manifest(path)
            self.assertEqual(started["state"]["scheduled_task_ids"], [])
            self.assertEqual(started["state"]["pending_task_ids"], [])
            status = status_run(root)
            self.assertEqual(status["scheduled_task_ids"], [])
            self.assertEqual(status["incomplete_task_ids"], [])
            resumed = resume_run(root)
            self.assertEqual(resumed["reissued_tasks"], [])
            self.assertEqual(resumed["pending_task_ids"], [])


if __name__ == "__main__":
    unittest.main()
