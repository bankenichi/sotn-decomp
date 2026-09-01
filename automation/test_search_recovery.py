import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
import sys
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_coordinator import (
    BudgetExhausted,
    CoordinatorError,
    DURABLE_FAULT_POINTS,
    ORACLE_FAULT_POINTS,
    SearchCoordinator,
    TaskResult,
)
from automation.search_types import (
    ArtifactRef,
    Budget,
    CandidateRecord,
    EvaluationEvent,
    canonical_subset_identity,
    GroupedPatch,
    MutationEvent,
    ParentRun,
    PatchHunk,
    ScoreDeltas,
    hash_bytes,
    hash_canonical,
)
from automation.search_recovery import (
    FaultInjector,
    InjectedFault,
    RecoveryError,
    ResumeRefused,
    fork_run,
    latest_checkpoint,
    recover_run,
)
from automation.test_search_schema import manifest, score


class CountingOracle:
    identity = hash_bytes(b"recovery-durable-oracle")

    def __init__(self, identity=None):
        if identity is not None:
            self.identity = identity
        self.results = {}
        self.requests = []
        self.execute_count = 0
        self.lookup_count = 0

    def lookup(self, request_id):
        self.lookup_count += 1
        return self.results.get(request_id)

    def execute(self, request):
        self.requests.append(request)
        self.execute_count += 1
        result = {
            "outcome": "matched",
            "result": {"request_id": request.request_id, "matched": True},
        }
        self.results[request.request_id] = result
        return result


class TestSearchRecovery(unittest.TestCase):
    @staticmethod
    def _factory_manifest():
        base = manifest()
        return replace(
            base,
            tool_identities={
                **base.tool_identities,
                "search_run_factory": hash_bytes(b"factory-module"),
                "search_run_factory_marker": hash_bytes(b"factory-marker"),
            },
        )

    @staticmethod
    def _manifest_for_oracle(oracle):
        base = manifest()
        return replace(
            base,
            tool_identities={
                **base.tool_identities,
                "full_oracle": oracle.identity,
            },
        )

    @staticmethod
    def _candidate(source: str, number: str = "one") -> CandidateRecord:
        source_bytes = source.encode("utf-8")
        source_hash = hash_bytes(source_bytes)
        artifact = ArtifactRef(
            source_hash,
            "artifacts/sources/" + source_hash[7:] + ".c",
            "text/x-c",
            len(source_bytes),
        )
        return CandidateRecord(
            source_hash,
            "record-1",
            artifact,
            (),
            None,
            "upstream_current",
            0,
            None,
            "materialized",
        )

    @staticmethod
    def _scenario_result(coordinator, task):
        source = "int candidate(void) { return 1; }\n"
        candidate = TestSearchRecovery._candidate(source)
        parent_id = hash_bytes(b"matrix-parent")
        mutation_id = hash_bytes(b"matrix-mutation")
        grouped_patch = GroupedPatch(
            hash_canonical(
                {
                    "format": "line_context",
                    "base_source_hash": candidate.candidate_id,
                    "atomic": True,
                    "hunks": [
                        PatchHunk(0, "return 1;\\n", "return 2;\\n", (), ())
                    ],
                }
            ),
            "line_context",
            candidate.candidate_id,
            True,
            (PatchHunk(0, "return 1;\\n", "return 2;\\n", (), ()),),
        )
        mutation = MutationEvent(
            mutation_id,
            parent_id,
            "record-1",
            "upstream_current",
            "matrix-pass",
            17,
            grouped_patch,
            (),
            "applied",
            candidate.candidate_id,
        )
        candidate = replace(
            candidate,
            parent_candidate_ids=(parent_id,),
            mutation_id=mutation_id,
        )
        after = score(1)
        evaluation = EvaluationEvent(
            task.task_id,
            "record-1",
            candidate.candidate_id,
            None,
            None,
            after,
            ScoreDeltas(1, 0, 0, 0, 0, 1),
            coordinator.frontier.cache.key_for(
                "record-1", candidate.candidate_id, after.compiler_identity
            ),
            "scalar_elite",
        )
        return TaskResult(
            task.task_id,
            mutation=mutation,
            candidate=candidate,
            source=source,
            evaluation=evaluation,
        )

    @staticmethod
    def _logical_state(directory):
        state = recover_run(directory)
        logical_events = []
        for event in state.events:
            payload = event.payload.to_dict()
            if event.event_type == "checkpoint_committed":
                # Checkpoint content names the predecessor event hash, whose
                # envelope includes recorded_at. Compare its typed state,
                # while treating that volatile identity as an integrity field.
                payload["through_event_hash"] = "<event-hash>"
                payload["checkpoint_artifact"]["content_hash"] = "<artifact-hash>"
                payload["checkpoint_artifact"]["path"] = "<checkpoint>"
            elif event.event_type == "run_resumed":
                # The resume binds the exact stop event, whose envelope also
                # contains the wall-clock recording time. Compare transition
                # semantics while treating that volatile chain hash as an
                # integrity field.
                payload["stop_event_hash"] = "<event-hash>"
            logical_events.append((event.event_type, payload))
        events = tuple(logical_events)
        graph = tuple(
            candidate.to_dict()
            for candidate in state.frontier.graph.all()
        )
        cache = tuple(
            (key, value.to_dict())
            for key, value in state.frontier.cache.items()
        )
        terminals = tuple(
            (task_id, terminal.to_dict())
            for task_id, terminal in sorted(state.terminal_tasks.items())
        )
        tasks = tuple(
            (task_id, task.to_dict())
            for task_id, task in sorted(state.tasks.items())
        )
        checkpoint = latest_checkpoint(directory, state)
        if checkpoint is not None:
            checkpoint = dict(checkpoint)
            checkpoint["through_event_hash"] = "<event-hash>"
        return {
            "events": events,
            "tasks": tasks,
            "terminals": terminals,
            "reissue": tuple(item.task_id for item in state.reissue_tasks()),
            "graph": graph,
            "cache": cache,
            "budget": state.consumed_budget_ordinals,
            "scalar_elite": state.frontier.scalar_elite_id,
            "pareto": state.frontier.pareto_ids,
            "receipts": tuple(item.to_dict() for item in state.receipts),
            "pending_oracle": state.pending_oracle_candidate_ids,
            "oracle_requests": tuple(
                (key, value.to_dict())
                for key, value in sorted(state.oracle_requests.items())
            ),
            "oracle_results": tuple(
                (key, value.to_dict())
                for key, value in sorted(state.oracle_results.items())
            ),
            "stopped": state.stopped.to_dict() if state.stopped is not None else None,
            "checkpoint": checkpoint,
            "checkpoint_valid": checkpoint is not None,
        }

    @classmethod
    def _complete_scenario(cls, directory, fault_point=None):
        injector = FaultInjector(fault_point) if fault_point is not None else None
        try:
            coordinator = SearchCoordinator(
                directory,
                manifest(),
                fault_hook=injector,
            )
        except InjectedFault:
            coordinator = SearchCoordinator(directory, manifest())

        task = coordinator.create_task(
            recipient_id="record-1",
            lane="upstream_current",
            operation="matrix",
            parent_candidate_ids=(hash_bytes(b"matrix-parent"),),
        )
        try:
            coordinator.schedule_task(task)
        except InjectedFault:
            coordinator = SearchCoordinator(directory, manifest())
            if task.task_id not in coordinator._tasks:
                coordinator.schedule_task(task)

        result = cls._scenario_result(coordinator, task)
        try:
            coordinator.commit_epoch([result])
        except InjectedFault:
            coordinator = SearchCoordinator(directory, manifest())
            if task.task_id not in coordinator._tasks:
                coordinator.schedule_task(task)
            coordinator.commit_epoch([result])

        try:
            coordinator.write_checkpoint()
        except InjectedFault:
            coordinator = SearchCoordinator(directory, manifest())
            coordinator.write_checkpoint()

        try:
            coordinator.record_exhaustion(
                recipient_id="record-1",
                lane="upstream_current",
                tier="exact_deterministic",
                tool_identities={
                    "upstream_current": manifest().tool_identities["upstream_current"],
                },
                input_identities=(manifest().source_identity,),
                budget_unit=manifest().lane_budgets["upstream_current"].unit,
                budget_limit=manifest().lane_budgets["upstream_current"].limit,
                budget_consumed=1,
                attempts=1,
                rejection_counts={"none": 0},
                best_candidate_ids=(result.candidate.candidate_id,),
                completion_reason="search_space_exhausted",
            )
        except InjectedFault:
            coordinator = SearchCoordinator(directory, manifest())
            coordinator.record_exhaustion(
                recipient_id="record-1",
                lane="upstream_current",
                tier="exact_deterministic",
                tool_identities={
                    "upstream_current": manifest().tool_identities["upstream_current"],
                },
                input_identities=(manifest().source_identity,),
                budget_unit=manifest().lane_budgets["upstream_current"].unit,
                budget_limit=manifest().lane_budgets["upstream_current"].limit,
                budget_consumed=1,
                attempts=1,
                rejection_counts={"none": 0},
                best_candidate_ids=(result.candidate.candidate_id,),
                completion_reason="search_space_exhausted",
            )

        try:
            coordinator.stop()
        except InjectedFault:
            coordinator = SearchCoordinator(directory, manifest())
            coordinator.stop()
        return injector


    @staticmethod
    def _oracle_scenario_result(coordinator, task):
        source = "int candidate(void) { return 0; }\n"
        candidate = TestSearchRecovery._candidate(source)
        after = score(0)
        evaluation = EvaluationEvent(
            task.task_id,
            "record-1",
            candidate.candidate_id,
            None,
            None,
            after,
            ScoreDeltas(0, 0, 0, 0, 0, 0),
            coordinator.frontier.cache.key_for(
                "record-1", candidate.candidate_id, after.compiler_identity
            ),
            "zero_pending_oracle",
        )
        return TaskResult(
            task.task_id,
            candidate=candidate,
            source=source,
            evaluation=evaluation,
        )

    @classmethod
    def _complete_oracle_scenario(cls, directory, fault_point=None):
        oracle = CountingOracle()
        run_manifest = cls._manifest_for_oracle(oracle)
        injector = FaultInjector(fault_point) if fault_point is not None else None
        coordinator = SearchCoordinator(
            directory,
            run_manifest,
            oracle=oracle,
            fault_hook=injector,
        )
        task = coordinator.create_task(
            recipient_id="record-1",
            lane="upstream_current",
            operation="oracle-matrix",
        )
        coordinator.schedule_task(task)
        result = cls._oracle_scenario_result(coordinator, task)
        interrupted = None
        try:
            coordinator.commit_epoch([result])
        except InjectedFault:
            interrupted = recover_run(directory)
            coordinator = SearchCoordinator(directory, run_manifest, oracle=oracle)
            coordinator.commit_epoch([result])
        return injector, oracle, interrupted

    def test_changed_manifest_budget_lanes_and_subset_refuse_resume(self):
        base = manifest()
        with tempfile.TemporaryDirectory() as directory:
            SearchCoordinator(directory, base)

            changed_budget = replace(
                base,
                coordinator_budget=Budget("tasks", 63, 0),
            )
            with self.assertRaises(ResumeRefused):
                recover_run(directory, expected_identity=changed_budget)

            changed_lane_budget = replace(
                base,
                lane_budgets={
                    **base.lane_budgets,
                    "upstream_current": Budget("attempts", 17, 0),
                },
            )
            with self.assertRaises(ResumeRefused):
                recover_run(directory, expected_identity=changed_lane_budget)

            changed_lanes = replace(
                base,
                selected_lanes=("upstream_current",),
                lane_budgets={
                    "upstream_current": base.lane_budgets["upstream_current"],
                },
            )
            with self.assertRaises(ResumeRefused):
                recover_run(directory, expected_identity=changed_lanes)

            changed_queue_evidence = replace(
                base,
                queue_evidence_identity=hash_bytes(b"changed-queue-evidence"),
            )
            with self.assertRaises(ResumeRefused):
                recover_run(directory, expected_identity=changed_queue_evidence)

            changed_subset = replace(
                base,
                queue_record_ids=("record-2",),
                function_ids=("record-2",),
                subset_identity=canonical_subset_identity(("record-2",)),
                queue_evidence_identity=hash_bytes(b"changed-queue-evidence"),
                target_identities={"record-2": hash_bytes(b"changed-target")},
            )
            with self.assertRaises(ResumeRefused):
                recover_run(directory, expected_identity=changed_subset)

    def test_explicit_empty_subset_is_a_deterministic_noop(self):
        base = manifest()
        empty = replace(
            base,
            run_id="run-empty",
            queue_record_ids=(),
            function_ids=(),
            subset_identity=canonical_subset_identity(()),
            queue_evidence_identity=hash_bytes(b"empty-queue-evidence"),
            target_identities={},
            selected_lanes=("upstream_current", "mipsmatch_exact"),
            lane_budgets={
                "upstream_current": base.lane_budgets["upstream_current"],
                "mipsmatch_exact": base.lane_budgets["mipsmatch_exact"],
            },
        )
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, empty)
            self.assertEqual(coordinator.pending_task_ids(), ())
            state = recover_run(directory, expected_identity=empty)
            self.assertEqual(state.tasks, {})
            self.assertEqual(state.incomplete_tasks, ())
            self.assertEqual(
                [event.event_type for event in state.events],
                ["run_started"],
            )
            resumed = SearchCoordinator(directory, empty)
            self.assertEqual(resumed.pending_task_ids(), ())

    def test_factory_recovery_verifies_archive_then_provider_before_accepting_state(self):
        run_manifest = self._factory_manifest()
        with tempfile.TemporaryDirectory() as directory:
            SearchCoordinator(directory, run_manifest)
            order = []

            def verify_archive(run_root, typed_manifest):
                order.append(("archive", run_root, typed_manifest))
                self.assertIsInstance(typed_manifest, type(run_manifest))
                return typed_manifest

            def verify_provider(typed_manifest, run_root):
                order.append(("provider", run_root, typed_manifest))

            with mock.patch(
                "automation.search_run_factory.verify_factory_archive",
                side_effect=verify_archive,
            ), mock.patch(
                "automation.search_provider_lanes.verify_lane_provider",
                side_effect=verify_provider,
            ):
                state = recover_run(directory)

            self.assertEqual([entry[0] for entry in order], ["archive", "provider"])
            self.assertEqual(state.manifest, run_manifest)

    def test_factory_recovery_refuses_missing_or_corrupt_provider_state(self):
        for failure in (FileNotFoundError("provider state missing"), RuntimeError("provider state corrupt")):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as directory:
                run_manifest = self._factory_manifest()
                SearchCoordinator(directory, run_manifest)
                with mock.patch(
                    "automation.search_run_factory.verify_factory_archive",
                    return_value=run_manifest,
                ), mock.patch(
                    "automation.search_provider_lanes.verify_lane_provider",
                    side_effect=failure,
                ):
                    with self.assertRaisesRegex(
                        RecoveryError,
                        "provider state could not be revalidated",
                    ):
                        recover_run(directory)

    def test_legacy_recovery_does_not_require_factory_provider_state(self):
        with tempfile.TemporaryDirectory() as directory:
            run_manifest = manifest()
            SearchCoordinator(directory, run_manifest)
            with mock.patch(
                "automation.search_run_factory.verify_factory_archive",
                side_effect=AssertionError("legacy recovery must not use factory archive"),
            ), mock.patch(
                "automation.search_provider_lanes.verify_lane_provider",
                side_effect=AssertionError("legacy recovery must not use providers"),
            ):
                state = recover_run(directory)
            self.assertEqual(state.manifest, run_manifest)

    def test_repeated_factory_recovery_has_no_provider_side_effects(self):
        run_manifest = self._factory_manifest()
        with tempfile.TemporaryDirectory() as directory:
            SearchCoordinator(directory, run_manifest)
            provider_calls = []

            def verify_provider(typed_manifest, run_root):
                provider_calls.append((typed_manifest, run_root))

            def snapshot():
                return {
                    path.relative_to(directory): path.read_bytes()
                    for path in Path(directory).rglob("*")
                    if path.is_file()
                }

            with mock.patch(
                "automation.search_run_factory.verify_factory_archive",
                return_value=run_manifest,
            ), mock.patch(
                "automation.search_provider_lanes.verify_lane_provider",
                side_effect=verify_provider,
            ):
                before = snapshot()
                recover_run(directory)
                middle = snapshot()
                recover_run(directory)
                after = snapshot()

            self.assertEqual(before, middle)
            self.assertEqual(middle, after)
            self.assertEqual(len(provider_calls), 2)

    def test_oracle_recovery_reuses_request_and_result_without_execution(self):
        with tempfile.TemporaryDirectory() as reference_directory:
            self._complete_oracle_scenario(reference_directory)
            reference = self._logical_state(reference_directory)
            for point in ORACLE_FAULT_POINTS:
                with self.subTest(point=point), tempfile.TemporaryDirectory() as directory:
                    injector, oracle, interrupted = self._complete_oracle_scenario(directory, point)
                    self.assertIn(point, injector.seen)
                    self.assertIsNotNone(interrupted)
                    self.assertEqual(oracle.execute_count, 1)
                    self.assertEqual(
                        len(interrupted.oracle_requests),
                        0
                        if point in ("before_oracle_request", "before_oracle_request_artifact", "after_oracle_request_artifact", "before_oracle_request_event")
                        else 1,
                    )
                    self.assertEqual(
                        len(interrupted.oracle_results),
                        1
                        if point in ("after_oracle_result_event", "after_oracle_result", "before_task_terminal", "after_task_terminal")
                        else 0,
                    )
                    self.assertEqual(
                        interrupted.pending_oracle_candidate_ids,
                        ()
                        if point == "after_task_terminal"
                        else (hash_bytes(b"int candidate(void) { return 0; }\n"),),
                    )
                    actual = self._logical_state(directory)
                    for key in reference:
                        self.assertEqual(actual[key], reference[key], msg=f"{point}: {key}")
                    state = recover_run(directory)
                    self.assertEqual(len(state.oracle_requests), 1)
                    self.assertEqual(len(state.oracle_results), 1)
                    self.assertEqual(state.pending_oracle_candidate_ids, ())
                    self.assertEqual(
                        sum(event.event_type == "oracle_requested" for event in state.events),
                        1,
                    )
                    self.assertEqual(
                        sum(event.event_type == "oracle_result_recorded" for event in state.events),
                        1,
                    )

    def test_changed_oracle_identity_refuses_existing_request_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            original_oracle = CountingOracle()
            run_manifest = self._manifest_for_oracle(original_oracle)
            injector = FaultInjector("before_oracle_execution")
            coordinator = SearchCoordinator(
                directory,
                run_manifest,
                oracle=original_oracle,
                fault_hook=injector,
            )
            task = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="oracle-identity",
            )
            coordinator.schedule_task(task)
            result = self._oracle_scenario_result(coordinator, task)

            with self.assertRaises(InjectedFault):
                coordinator.commit_epoch([result])

            interrupted = recover_run(directory)
            self.assertEqual(len(interrupted.oracle_requests), 1)
            self.assertEqual(len(interrupted.oracle_results), 0)
            self.assertEqual(original_oracle.execute_count, 0)
            self.assertEqual(
                interrupted.pending_oracle_candidate_ids,
                (result.candidate.candidate_id,),
            )

            changed_oracle = CountingOracle(
                identity=hash_bytes(b"changed-recovery-oracle"),
            )
            with self.assertRaisesRegex(CoordinatorError, "full_oracle"):
                SearchCoordinator(
                    directory,
                    run_manifest,
                    oracle=changed_oracle,
                )

            self.assertEqual(changed_oracle.lookup_count, 0)
            self.assertEqual(changed_oracle.execute_count, 0)
            final = recover_run(directory)
            self.assertEqual(len(final.oracle_requests), 1)
            self.assertEqual(len(final.oracle_results), 0)
            self.assertEqual(final.completed_task_ids, ())
            self.assertEqual(
                final.pending_oracle_candidate_ids,
                (result.candidate.candidate_id,),
            )
            self.assertEqual(
                sum(event.event_type == "oracle_requested" for event in final.events),
                1,
            )
            self.assertEqual(
                sum(event.event_type == "oracle_result_recorded" for event in final.events),
                0,
            )
            self.assertEqual(
                sum(event.event_type == "task_completed" for event in final.events),
                0,
            )

    def test_started_task_is_reissued_without_new_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            task = coordinator.create_task(recipient_id="record-1", lane="upstream_current", operation="discover")
            coordinator.schedule_task(task)
            coordinator.start_task(task.task_id)
            state = recover_run(directory)
            self.assertEqual([item.task_id for item in state.reissue_tasks()], [task.task_id])
            self.assertEqual(state.reissue_tasks()[0].task_seed, task.task_seed)
            self.assertEqual(state.consumed_budget_ordinals, ())

    def test_checkpoint_is_optional_and_changed_identity_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            checkpoint_event = coordinator.write_checkpoint()
            self.assertIsNotNone(latest_checkpoint(directory))
            checkpoint = Path(directory) / checkpoint_event.payload.checkpoint_artifact.path
            checkpoint.unlink()
            self.assertIsNone(latest_checkpoint(directory))
            with self.assertRaises(ResumeRefused):
                recover_run(directory, expected_identity={"config_identity": "sha256:" + "0" * 64})

    def test_explicit_fork_preserves_parent(self):
        with tempfile.TemporaryDirectory() as parent, tempfile.TemporaryDirectory() as child:
            coordinator = SearchCoordinator(parent, manifest())
            task = coordinator.create_task(recipient_id="record-1", lane="upstream_current", operation="discover")
            coordinator.schedule_task(task)
            forked = fork_run(parent, child, run_id="run-fork")
            state = recover_run(child)
            self.assertEqual(state.manifest.parent_run.run_id, manifest().run_id)
            self.assertTrue(Path(parent, "ledger.jsonl").exists())
            self.assertEqual(forked.manifest.run_id, "run-fork")

    def test_fork_rejects_wrong_non_null_parent_and_source_identity(self):
        with tempfile.TemporaryDirectory() as parent, tempfile.TemporaryDirectory() as child:
            SearchCoordinator(parent, manifest())
            wrong_parent = replace(
                manifest(),
                run_id="run-child",
                parent_run=ParentRun("wrong-parent", 0, hash_bytes(b"wrong-event")),
            )
            with self.assertRaises(ResumeRefused):
                fork_run(parent, child, manifest=wrong_parent)

    def test_fault_injector_is_named_and_one_shot(self):
        fault = FaultInjector("epoch", "checkpoint")
        with self.assertRaises(InjectedFault):
            fault("epoch")
        fault("epoch")
        self.assertEqual(fault.seen, ["epoch", "epoch"])
        for point in DURABLE_FAULT_POINTS:
            one_shot = FaultInjector(point)
            with self.assertRaises(InjectedFault):
                one_shot(point)
            one_shot(point)
            self.assertEqual(one_shot.seen, [point, point])

    def test_fault_after_archive_rename_reissues_same_task(self):
        source = "int candidate(void) { return 1; }\n"
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            task = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="discover",
            )
            coordinator.schedule_task(task)
            result = TaskResult(task.task_id, candidate=self._candidate(source), source=source)
            coordinator.fault_hook = FaultInjector("after_artifact_rename")
            with self.assertRaises(InjectedFault):
                coordinator.commit_epoch([result])
            interrupted = recover_run(directory)
            self.assertEqual([item.task_id for item in interrupted.reissue_tasks()], [task.task_id])

            resumed = SearchCoordinator(directory, manifest())
            resumed.commit_epoch([result])
            completed = recover_run(directory)
            self.assertEqual(completed.completed_task_ids, (task.task_id,))
            self.assertEqual(completed.incomplete_tasks, ())

    def test_fault_after_ledger_append_is_idempotent_on_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            task = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="discover",
            )
            coordinator.schedule_task(task)
            result = TaskResult(task.task_id)
            coordinator.fault_hook = FaultInjector("after_ledger_append")
            with self.assertRaises(InjectedFault):
                coordinator.commit_epoch([result])

            interrupted = recover_run(directory)
            self.assertEqual(interrupted.reissue_tasks()[0].task_id, task.task_id)
            resumed = SearchCoordinator(directory, manifest())
            resumed.commit_epoch([result])
            events = recover_run(directory).events
            self.assertEqual(
                sum(event.event_type == "task_completed" for event in events),
                1,
            )

    def test_duplicate_results_and_out_of_order_delivery_commit_once(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            one = SearchCoordinator(first, manifest())
            two = SearchCoordinator(second, manifest())
            tasks_one = one.schedule_tasks(
                one.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="discover-" + str(index),
                    budget_ordinal=index,
                )
                for index in (0, 1)
            )
            tasks_two = two.schedule_tasks(
                two.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="discover-" + str(index),
                    budget_ordinal=index,
                )
                for index in (0, 1)
            )
            results_one = [TaskResult(task.task_id) for task in tasks_one]
            results_two = [TaskResult(task.task_id) for task in tasks_two]
            one.commit_epoch((results_one[1], results_one[0], results_one[0]))
            two.commit_epoch((results_two[0], results_two[1]))
            one_events = recover_run(first).events
            two_events = recover_run(second).events
            one_logical = [(event.event_type, event.payload.to_dict()) for event in one_events]
            two_logical = [(event.event_type, event.payload.to_dict()) for event in two_events]
            self.assertEqual(one_logical, two_logical)
            self.assertEqual(
                sum(event.event_type == "task_completed" for event in one_events),
                2,
            )

    def test_global_budget_claims_recover_and_refuse_ordinal_collisions(self):
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            task = coordinator.create_task(
                recipient_id="record-1",
                lane="upstream_current",
                operation="current",
                budget_ordinal=0,
            )
            coordinator.schedule_task(task)
            coordinator.commit_epoch([TaskResult(task.task_id)])
            state = recover_run(directory)
            self.assertEqual(
                state.consumed_budget_ordinals,
                (("record-1", "upstream_current", 0),),
            )

            resumed = SearchCoordinator(directory, manifest())
            replayed = resumed.schedule_task(
                resumed.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="current",
                    budget_ordinal=0,
                )
            )
            self.assertEqual(replayed.task_id, task.task_id)
            self.assertEqual(replace(replayed, state="scheduled"), task)
            with self.assertRaises(BudgetExhausted):
                resumed.create_task(
                    recipient_id="record-1",
                    lane="upstream_pinned",
                    operation="pinned",
                    budget_ordinal=0,
                )

    def test_schema_valid_forged_task_id_or_seed_refuses_recovery(self):
        for field in ("task_id", "task_seed"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                coordinator = SearchCoordinator(directory, manifest())
                task = coordinator.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="forged-ledger-" + field,
                )
                coordinator.schedule_task(task)

                ledger_path = Path(directory) / "ledger.jsonl"
                lines = ledger_path.read_text(encoding="utf-8").splitlines()
                envelope = json.loads(lines[-1])
                forged_payload = dict(envelope["payload"])
                forged_payload[field] = (
                    hash_bytes(b"forged-ledger-task-id")
                    if field == "task_id"
                    else forged_payload["task_seed"] + 1
                )
                envelope["payload"] = forged_payload
                envelope.pop("event_hash", None)
                envelope["event_hash"] = hash_canonical(envelope)
                lines[-1] = json.dumps(
                    envelope,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

                # The forged SearchTask remains schema-valid and the envelope
                # hash is recomputed, so recovery must enforce the manifest
                # binding rather than relying on generic ledger integrity.
                with self.assertRaises(RecoveryError):
                    recover_run(directory)

    def test_recovery_refuses_recomputed_hash_global_ordinal_collision(self):
        base = manifest()
        expanded = replace(
            base,
            queue_record_ids=("record-1", "record-2"),
            function_ids=("record-1", "record-2"),
            subset_identity=canonical_subset_identity(("record-1", "record-2")),
            queue_evidence_identity=hash_bytes(b"collision-evidence"),
            target_identities={
                "record-1": hash_bytes(b"collision-target-one"),
                "record-2": hash_bytes(b"collision-target-two"),
            },
        )
        for recipient_id, lane in (
            ("record-1", "upstream_pinned"),
            ("record-2", "upstream_current"),
        ):
            with self.subTest(recipient_id=recipient_id, lane=lane), tempfile.TemporaryDirectory() as directory:
                coordinator = SearchCoordinator(directory, expanded)
                first = coordinator.create_task(
                    recipient_id="record-1",
                    lane="upstream_current",
                    operation="collision-first",
                    budget_ordinal=0,
                )
                second = coordinator.create_task(
                    recipient_id=recipient_id,
                    lane=lane,
                    operation="collision-second",
                    budget_ordinal=0,
                )
                coordinator.schedule_task(first)
                # Bypass the coordinator's local claim guard to construct a
                # valid, hash-recomputed ledger prefix. Recovery must rebuild
                # the same run-global ordinal ownership and refuse it.
                coordinator.ledger.append_event(
                    "task_scheduled",
                    second,
                    event_id=second.task_id + ":scheduled-collision",
                )
                with self.assertRaises(RecoveryError):
                    recover_run(directory)

    def test_checkpoint_and_graceful_stop_faults_leave_prefix_recoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            coordinator = SearchCoordinator(directory, manifest())
            coordinator.fault_hook = FaultInjector("after_checkpoint_write")
            with self.assertRaises(InjectedFault):
                coordinator.write_checkpoint()
            self.assertIsNone(latest_checkpoint(directory))
            coordinator.fault_hook = FaultInjector("after_graceful_stop")
            with self.assertRaises(InjectedFault):
                coordinator.stop()
            state = recover_run(directory)
            self.assertIsNotNone(state.stopped)
            self.assertEqual(state.stopped.reason, "graceful_stop")

    def test_every_coordinator_durable_fault_point_recovers_logically(self):
        with tempfile.TemporaryDirectory() as reference_directory:
            self._complete_scenario(reference_directory)
            reference = self._logical_state(reference_directory)
            for point in DURABLE_FAULT_POINTS:
                if point in ORACLE_FAULT_POINTS or point in {
                    "before_run_resume",
                    "before_run_resume_event",
                    "after_run_resume_event",
                    "after_run_resume",
                }:
                    continue
                with self.subTest(point=point), tempfile.TemporaryDirectory() as directory:
                    injector = self._complete_scenario(directory, point)
                    self.assertIn(point, injector.seen)
                    actual = self._logical_state(directory)
                    for key in reference:
                        self.assertEqual(actual[key], reference[key], msg=f"{point}: {key}")
                    self.assertTrue(actual["checkpoint_valid"], point)

    @classmethod
    def _resume_scenario(cls, directory, fault_point=None):
        request_id = hash_bytes(b"resume-fault-request")
        injector = FaultInjector(fault_point) if fault_point is not None else None
        coordinator = SearchCoordinator(
            directory,
            manifest(),
            fault_hook=injector,
        )
        task = coordinator.create_task(
            recipient_id="record-1",
            lane="upstream_current",
            operation="resume-fault-matrix",
        )
        coordinator.schedule_task(task)
        coordinator.stop(reason="graceful_stop", resumable=True)
        try:
            coordinator.resume(request_id=request_id)
        except InjectedFault:
            coordinator = SearchCoordinator(directory, manifest())
            coordinator.resume(request_id=request_id)
        return injector

    def test_every_resume_fault_point_replays_the_same_transition(self):
        resume_points = {
            "before_run_resume",
            "before_run_resume_event",
            "after_run_resume_event",
            "after_run_resume",
        }
        with tempfile.TemporaryDirectory() as reference_directory:
            self._resume_scenario(reference_directory)
            reference = self._logical_state(reference_directory)
            for point in sorted(resume_points):
                with self.subTest(point=point), tempfile.TemporaryDirectory() as directory:
                    injector = self._resume_scenario(directory, point)
                    self.assertIn(point, injector.seen)
                    actual = self._logical_state(directory)
                    self.assertEqual(actual, reference, point)


if __name__ == "__main__":
    unittest.main()
