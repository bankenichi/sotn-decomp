import json
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import automation.search_supervisor as _search_supervisor
import automation.permuter_supervisor as _permuter_supervisor

sys.modules.setdefault("search_supervisor", _search_supervisor)

from automation.search_coordinator import SearchCoordinator
from automation.search_lanes import LaneCandidate, LaneError, execute_task
from automation.search_recovery import recover_run
from automation.search_cli import RunInputError, resume_run, stop_run
from automation.search_supervisor import (
    InstrumentedLandingOracle,
    INSTRUMENTED_MODE,
    MODE_TOOL_KEY,
    SupervisorConflict,
    SupervisorLease,
    SupervisorIntegrationError,
    resume_instrumented,
    run_instrumented,
    mode_identity,
)
from automation.permuter_supervisor import _instrumented_landing
from automation.search_types import (
    Budget,
    CandidateRecord,
    SearchTask,
    canonical_bytes,
    hash_bytes,
)
from automation.test_search_schema import artifact, candidate_record, manifest, score


class SearchSupervisorIntegrationTests(unittest.TestCase):
    def instrumented_manifest(self, *, with_oracle=False, coordinator_limit=1):
        base = manifest()
        tools = dict(base.tool_identities)
        tools[MODE_TOOL_KEY] = mode_identity(INSTRUMENTED_MODE)
        if with_oracle:
            tools["full_oracle"] = hash_bytes(b"test-landing-oracle")
        return replace(
            base,
            selected_lanes=("upstream_current",),
            tool_identities=tools,
            coordinator_budget=Budget("tasks", coordinator_limit, 0),
            lane_budgets={"upstream_current": base.lane_budgets["upstream_current"]},
        )

    def multi_lane_manifest(self, *, coordinator_limit=5):
        base = self.instrumented_manifest(coordinator_limit=coordinator_limit)
        return replace(
            base,
            selected_lanes=("upstream_current", "upstream_pinned"),
            lane_budgets={
                "upstream_current": base.lane_budgets["upstream_current"],
                "upstream_pinned": manifest().lane_budgets["upstream_pinned"],
            },
        )

    @staticmethod
    def write_manifest(root, value):
        root.mkdir(parents=True, exist_ok=True)
        (root / "manifest.json").write_bytes(canonical_bytes(value.to_dict()) + b"\n")

    @staticmethod
    def adapters():
        return {
            "upstream_current": lambda _recipient: LaneCandidate(
                candidate_record(), "candidate-source"
            )
        }

    @staticmethod
    def candidate(source, *, total=None, lane="upstream_current", parents=()):
        source_artifact = artifact(source)
        evaluation = None
        status = "materialized"
        if total is not None:
            evaluation = score(total, signature=source)
            status = "zero_pending_oracle" if total == 0 else "evaluated"
        return CandidateRecord(
            source_artifact.content_hash,
            "record-1",
            source_artifact,
            tuple(parents),
            None,
            lane,
            0,
            evaluation,
            status,
        )

    @staticmethod
    def two_candidate_adapters(first, second):
        return {
            "upstream_current": lambda _recipient: {
                "candidates": [
                    LaneCandidate(first, "candidate-source-1"),
                    LaneCandidate(second, "candidate-source-2"),
                ]
            }
        }

    def test_score_zero_oracle_is_replayed_without_a_second_landing_call(self):
        landing_calls = []

        def landing(recipient_id, source, persist_terminal):
            landing_calls.append((recipient_id, source))
            persist_terminal("matched", "verified before simulated process loss")
            raise KeyboardInterrupt("simulated loss after durable oracle callback")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(
                with_oracle=True,
                coordinator_limit=2,
            )
            self.write_manifest(root, value)
            with self.assertRaises(KeyboardInterrupt):
                run_instrumented(
                    root / "manifest.json",
                    adapters=self.adapters(),
                    landing=landing,
                    lease_path=Path(directory) / "lease.json",
                )

            result = run_instrumented(
                root / "manifest.json",
                adapters=self.adapters(),
                landing=landing,
                lease_path=Path(directory) / "lease.json",
            )

            self.assertEqual(len(landing_calls), 1)
            self.assertEqual(len(result["recovered_task_ids"]), 1)
            self.assertIn(
                result["recovered_task_ids"][0],
                result["state"]["completed_task_ids"],
            )
            self.assertEqual(result["executed_task_ids"], [])
            self.assertEqual(len(result["state"]["completed_task_ids"]), 2)

            def unexpected_executor(*_args, **_kwargs):
                raise AssertionError("a terminal unchanged task must not execute again")

            before_replay = recover_run(root)
            replay = run_instrumented(
                root / "manifest.json",
                adapters=self.adapters(),
                landing=landing,
                lease_path=Path(directory) / "lease.json",
                lane_executor=unexpected_executor,
            )
            self.assertEqual(replay["executed_task_ids"], [])
            self.assertEqual(replay["recovered_task_ids"], result["recovered_task_ids"])
            after_replay = recover_run(root)
            self.assertEqual(len(after_replay.events), len(before_replay.events))
            self.assertEqual(after_replay.last_event_hash, before_replay.last_event_hash)

    def test_not_matched_oracle_receipt_survives_loss_after_callback_returns(self):
        landing_calls = []

        def landing(recipient_id, source, persist_terminal):
            landing_calls.append((recipient_id, source))
            persist_terminal("not_matched", "candidate did not match")
            return False, "candidate did not match"

        original_lookup = InstrumentedLandingOracle.lookup
        lookup_calls = []

        def lose_after_callback(oracle, request_id):
            lookup_calls.append(request_id)
            # The coordinator lookup is first, the execute preflight lookup is
            # second, and this third lookup is the mandatory post-callback
            # read-after-write proof. Simulate process loss at that boundary.
            if len(lookup_calls) == 3:
                raise KeyboardInterrupt("simulated loss after callback return")
            return original_lookup(oracle, request_id)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(with_oracle=True, coordinator_limit=2)
            self.write_manifest(root, value)
            with patch.object(
                InstrumentedLandingOracle,
                "lookup",
                new=lose_after_callback,
            ):
                with self.assertRaises(KeyboardInterrupt):
                    run_instrumented(
                        root / "manifest.json",
                        adapters=self.adapters(),
                        landing=landing,
                        lease_path=Path(directory) / "lease.json",
                    )

            result = run_instrumented(
                root / "manifest.json",
                adapters=self.adapters(),
                landing=landing,
                lease_path=Path(directory) / "lease.json",
            )
            self.assertEqual(len(landing_calls), 1)
            self.assertEqual(result["executed_task_ids"], [])
            self.assertEqual(len(result["state"]["completed_task_ids"]), 2)

    def test_default_landing_persists_each_terminal_before_return(self):
        matched_events = []

        def matched_gate(_cwd, _function, **kwargs):
            kwargs["on_verified"]("verified")
            return True, "verified"

        with patch("automation.permuter_supervisor.land_match", new=matched_gate):
            result = _instrumented_landing(
                "us:ST/RDAI:func_test",
                "body",
                lambda outcome, detail: matched_events.append((outcome, detail)),
            )
        self.assertEqual(result, (True, "verified"))
        self.assertEqual(matched_events, [("matched", "verified")])

        nonmatched_events = []

        def nonmatched_gate(_cwd, _function, **kwargs):
            kwargs["on_terminal"](False, "not matched")
            return False, "not matched"

        with patch("automation.permuter_supervisor.land_match", new=nonmatched_gate):
            result = _instrumented_landing(
                "us:ST/RDAI:func_test",
                "body",
                lambda outcome, detail: nonmatched_events.append((outcome, detail)),
            )
        self.assertEqual(result, (False, "not matched"))
        self.assertEqual(nonmatched_events, [("not_matched", "not matched")])

    def test_nonmatch_terminal_hook_runs_before_land_match_returns(self):
        terminal = []

        def gate(_cwd, _function, **kwargs):
            kwargs["on_terminal"](False, "restored and attributed")
            raise KeyboardInterrupt("simulated loss after durable nonmatch")

        def persist(outcome, detail):
            terminal.append((outcome, detail))

        with patch("automation.permuter_supervisor.land_match", new=gate):
            with self.assertRaises(KeyboardInterrupt):
                _instrumented_landing(
                    "us:ST/RDAI:func_test", "body", persist
                )
        self.assertEqual(terminal, [("not_matched", "restored and attributed")])

    def test_started_task_is_replayed_with_the_same_task_identity(self):
        calls = []

        def executor(task, run_manifest, recipients, **kwargs):
            calls.append(task.task_id)
            if len(calls) == 1:
                raise KeyboardInterrupt("simulated loss after task start")
            return execute_task(task, run_manifest, recipients, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(coordinator_limit=2)
            self.write_manifest(root, value)
            with self.assertRaises(KeyboardInterrupt):
                run_instrumented(
                    root / "manifest.json",
                    adapters={},
                    lease_path=Path(directory) / "lease.json",
                    lane_executor=executor,
                )

            result = run_instrumented(
                root / "manifest.json",
                adapters={},
                lease_path=Path(directory) / "lease.json",
                lane_executor=executor,
            )

            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0], calls[1])
            self.assertEqual(len(result["state"]["completed_task_ids"]), 1)

    def test_two_candidates_fan_out_into_child_tasks_and_preserve_outcome(self):
        first = self.candidate("candidate-source-1")
        second = self.candidate("candidate-source-2")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(coordinator_limit=3)
            self.write_manifest(root, value)
            result = run_instrumented(
                root / "manifest.json",
                adapters=self.two_candidate_adapters(first, second),
                lease_path=Path(directory) / "lease.json",
            )

            state = recover_run(root)
            task_events = [
                event.payload
                for event in state.events
                if event.event_type == "task_scheduled"
            ]
            child_tasks = [
                task for task in task_events
                if task.operation.startswith("materialize_candidate:")
            ]
            candidate_events = [
                event.payload
                for event in state.events
                if event.event_type == "candidate_materialized"
            ]
            terminals = [
                event.payload
                for event in state.events
                if event.event_type == "task_completed"
            ]
            self.assertEqual(len(child_tasks), 2)
            self.assertEqual(
                {task.budget_ordinal for task in child_tasks},
                {1, 2},
            )
            self.assertEqual(
                {candidate.candidate_id for candidate in candidate_events},
                {first.candidate_id, second.candidate_id},
            )
            self.assertEqual(len(terminals), 3)
            self.assertEqual(
                sum(event.event_type == "exhaustion_recorded" for event in state.events),
                1,
            )
            self.assertEqual(
                {
                    candidate["candidate_id"]
                    for candidate in result["state"]["frontier_candidates"]
                },
                {first.candidate_id, second.candidate_id},
            )

            lane_terminal = next(
                terminal for terminal in terminals
                if terminal.task_id not in {task.task_id for task in child_tasks}
            )
            self.assertEqual(len(lane_terminal.result_artifacts), 1)
            outcome_document = json.loads(
                (root / lane_terminal.result_artifacts[0].path).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                len(outcome_document["outcome"]["candidates"]),
                2,
            )

    def test_three_candidates_materialize_only_allowance_and_archive_full_outcome(self):
        first = self.candidate("candidate-source-1")
        second = self.candidate("candidate-source-2")
        third = self.candidate("candidate-source-3")
        adapters = {
            "upstream_current": lambda _recipient: {
                "candidates": [
                    LaneCandidate(first, "candidate-source-1"),
                    LaneCandidate(second, "candidate-source-2"),
                    LaneCandidate(third, "candidate-source-3"),
                ]
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(coordinator_limit=3)
            self.write_manifest(root, value)
            result = run_instrumented(
                root / "manifest.json",
                adapters=adapters,
                lease_path=Path(directory) / "lease.json",
            )

            state = recover_run(root)
            scheduled = [
                event.payload
                for event in state.events
                if event.event_type == "task_scheduled"
            ]
            child_tasks = [
                task
                for task in scheduled
                if task.operation.startswith("materialize_candidate:")
            ]
            selected_ids = {
                candidate.candidate_id
                for candidate in sorted(
                    (first, second, third),
                    key=lambda item: item.candidate_id,
                )[:2]
            }
            self.assertEqual(len(child_tasks), 2)
            self.assertEqual(
                {task.budget_ordinal for task in child_tasks},
                {1, 2},
            )
            self.assertEqual(
                {task.operation for task in child_tasks},
                {"materialize_candidate:" + item for item in selected_ids},
            )
            self.assertEqual(
                {
                    candidate["candidate_id"]
                    for candidate in result["state"]["frontier_candidates"]
                },
                selected_ids,
            )
            terminals = [
                event.payload
                for event in state.events
                if event.event_type == "task_completed"
            ]
            self.assertEqual(len(terminals), 3)
            lane_terminal = next(
                terminal
                for terminal in terminals
                if terminal.task_id not in {task.task_id for task in child_tasks}
            )
            self.assertEqual(len(lane_terminal.result_artifacts), 1)
            outcome_document = json.loads(
                (root / lane_terminal.result_artifacts[0].path).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(outcome_document["outcome"]["candidates"]), 3)
            self.assertEqual(
                len(outcome_document["outcome"]["receipt_proposal"]["best_candidate_ids"]),
                3,
            )

    def test_child_offset_counts_only_selected_candidates(self):
        current = [
            self.candidate("offset-current-one", lane="upstream_current"),
            self.candidate("offset-current-two", lane="upstream_current"),
            self.candidate("offset-current-three", lane="upstream_current"),
        ]
        pinned = self.candidate("offset-pinned-one", lane="upstream_pinned")
        adapters = {
            "upstream_current": lambda _recipient: {
                "candidates": [
                    LaneCandidate(item, "offset-current-" + label)
                    for item, label in zip(
                        current,
                        ("one", "two", "three"),
                    )
                ]
            },
            "upstream_pinned": lambda _recipient: LaneCandidate(
                pinned, "offset-pinned-one"
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.multi_lane_manifest(coordinator_limit=5)
            self.write_manifest(root, value)
            run_instrumented(
                root / "manifest.json",
                adapters=adapters,
                lease_path=Path(directory) / "lease.json",
            )

            state = recover_run(root)
            scheduled = [
                event.payload
                for event in state.events
                if event.event_type == "task_scheduled"
            ]
            child_tasks = [
                task
                for task in scheduled
                if task.operation.startswith("materialize_candidate:")
            ]
            self.assertEqual(
                [task.budget_ordinal for task in child_tasks],
                [2, 3, 4],
            )
            self.assertEqual(len(state.terminal_tasks), 5)
            lane_terminals = [
                event.payload
                for event in state.events
                if event.event_type == "task_completed"
                and event.payload.task_id
                in {
                    task.task_id
                    for task in scheduled
                    if task.operation == "execute_lane"
                }
            ]
            self.assertEqual(len(lane_terminals), 2)
            archived_candidate_counts = sorted(
                len(
                    json.loads(
                        (root / terminal.result_artifacts[0].path).read_text(
                            encoding="utf-8"
                        )
                    )["outcome"]["candidates"]
                )
                for terminal in lane_terminals
            )
            self.assertEqual(archived_candidate_counts, [1, 3])

    def test_malformed_third_candidate_is_rejected_before_any_child(self):
        first = self.candidate("candidate-source-1")
        second = self.candidate("candidate-source-2")
        malformed = self.candidate("candidate-source-3")
        adapters = {
            "upstream_current": lambda _recipient: {
                "candidates": [
                    LaneCandidate(first, "candidate-source-1"),
                    LaneCandidate(second, "candidate-source-2"),
                    LaneCandidate(malformed, ""),
                ]
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(coordinator_limit=3)
            self.write_manifest(root, value)
            with self.assertRaises(SupervisorIntegrationError):
                run_instrumented(
                    root / "manifest.json",
                    adapters=adapters,
                    lease_path=Path(directory) / "lease.json",
                )
            state = recover_run(root)
            scheduled = [
                event.payload
                for event in state.events
                if event.event_type == "task_scheduled"
            ]
            self.assertEqual(
                [task.operation for task in scheduled],
                ["execute_lane"],
            )
            self.assertEqual(
                sum(
                    event.event_type == "candidate_materialized"
                    for event in state.events
                ),
                0,
            )

    def test_foreign_third_candidate_is_rejected_before_any_child(self):
        first = self.candidate("candidate-source-1")
        second = self.candidate("candidate-source-2")
        foreign = self.candidate(
            "candidate-source-3",
            lane="upstream_pinned",
        )
        adapters = {
            "upstream_current": lambda _recipient: {
                "candidates": [
                    LaneCandidate(first, "candidate-source-1"),
                    LaneCandidate(second, "candidate-source-2"),
                    LaneCandidate(foreign, "candidate-source-3"),
                ]
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(coordinator_limit=3)
            self.write_manifest(root, value)
            with self.assertRaises(SupervisorIntegrationError):
                run_instrumented(
                    root / "manifest.json",
                    adapters=adapters,
                    lease_path=Path(directory) / "lease.json",
                )
            state = recover_run(root)
            scheduled = [
                event.payload
                for event in state.events
                if event.event_type == "task_scheduled"
            ]
            self.assertEqual(
                [task.operation for task in scheduled],
                ["execute_lane"],
            )
            self.assertEqual(
                sum(
                    event.event_type == "candidate_materialized"
                    for event in state.events
                ),
                0,
            )

    def test_duplicate_third_candidate_is_rejected_before_any_child(self):
        first = self.candidate("candidate-source-1")
        second = self.candidate("candidate-source-2")
        adapters = self.two_candidate_adapters(first, second)

        def duplicate_executor(task, run_manifest, recipients, **kwargs):
            outcome = execute_task(
                task,
                run_manifest,
                recipients,
                **kwargs,
            )
            return replace(
                outcome,
                candidates=outcome.candidates + (outcome.candidates[0],),
            )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(coordinator_limit=3)
            self.write_manifest(root, value)
            with self.assertRaises(SupervisorIntegrationError):
                run_instrumented(
                    root / "manifest.json",
                    adapters=adapters,
                    lease_path=Path(directory) / "lease.json",
                    lane_executor=duplicate_executor,
                )
            state = recover_run(root)
            scheduled = [
                event.payload
                for event in state.events
                if event.event_type == "task_scheduled"
            ]
            self.assertEqual(
                [task.operation for task in scheduled],
                ["execute_lane"],
            )
            self.assertEqual(
                sum(
                    event.event_type == "candidate_materialized"
                    for event in state.events
                ),
                0,
            )

    def test_started_archived_oversized_outcome_replays_without_lane_execution(self):
        first = self.candidate("candidate-source-1")
        second = self.candidate("candidate-source-2")
        third = self.candidate("candidate-source-3")
        adapters = {
            "upstream_current": lambda _recipient: {
                "candidates": [
                    LaneCandidate(first, "candidate-source-1"),
                    LaneCandidate(second, "candidate-source-2"),
                    LaneCandidate(third, "candidate-source-3"),
                ]
            }
        }
        calls = []

        def executor(task, run_manifest, recipients, **kwargs):
            calls.append(task.task_id)
            return execute_task(
                task,
                run_manifest,
                recipients,
                **kwargs,
            )

        original_fan_out = _search_supervisor._fan_out_candidates
        faulted = [False]

        def crash_after_archiving(*args, **kwargs):
            if not faulted[0]:
                faulted[0] = True
                raise KeyboardInterrupt("simulated loss after lane outcome archive")
            return original_fan_out(*args, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(coordinator_limit=3)
            self.write_manifest(root, value)
            with patch.object(
                _search_supervisor,
                "_fan_out_candidates",
                new=crash_after_archiving,
            ):
                with self.assertRaises(KeyboardInterrupt):
                    run_instrumented(
                        root / "manifest.json",
                        adapters=adapters,
                        lease_path=Path(directory) / "lease.json",
                        lane_executor=executor,
                    )

            state_after_crash = recover_run(root)
            self.assertEqual(len(calls), 1)
            self.assertEqual(
                sum(event.event_type == "task_scheduled" for event in state_after_crash.events),
                1,
            )
            self.assertEqual(
                len(list((root / "artifacts" / "lane_results").glob("*.json"))),
                1,
            )

            def unexpected_executor(*_args, **_kwargs):
                raise AssertionError("archived oversized lane result must be replayed")

            result = run_instrumented(
                root / "manifest.json",
                adapters=adapters,
                lease_path=Path(directory) / "lease.json",
                lane_executor=unexpected_executor,
            )
            state = recover_run(root)
            self.assertEqual(result["executed_task_ids"], [])
            self.assertEqual(len(calls), 1)
            child_tasks = [
                event.payload
                for event in state.events
                if event.event_type == "task_scheduled"
                and event.payload.operation.startswith("materialize_candidate:")
            ]
            self.assertEqual(len(child_tasks), 2)
            self.assertEqual(len(state.terminal_tasks), 3)
            self.assertEqual(
                sum(event.event_type == "candidate_materialized" for event in state.events),
                2,
            )
            before_replay = len(state.events)
            replay = run_instrumented(
                root / "manifest.json",
                adapters=adapters,
                lease_path=Path(directory) / "lease.json",
                lane_executor=unexpected_executor,
            )
            after_replay = recover_run(root)
            self.assertEqual(replay["executed_task_ids"], [])
            self.assertEqual(len(after_replay.events), before_replay)
            self.assertEqual(
                len(
                    [
                        event
                        for event in after_replay.events
                        if event.event_type == "task_scheduled"
                        and event.payload.operation.startswith("materialize_candidate:")
                    ]
                ),
                2,
            )

    def test_fan_out_replay_recovers_archived_outcome_without_rerunning_lane(self):
        first = self.candidate("candidate-source-1")
        second = self.candidate("candidate-source-2")
        calls = []

        def executor(task, run_manifest, recipients, **kwargs):
            calls.append(task.task_id)
            return execute_task(
                task,
                run_manifest,
                recipients,
                **kwargs,
            )

        original_commit = SearchCoordinator.commit_epoch
        commit_calls = []

        def crash_after_first_child(coordinator, results=None, **kwargs):
            events = original_commit(coordinator, results, **kwargs)
            commit_calls.append(True)
            if len(commit_calls) == 1:
                raise KeyboardInterrupt("simulated loss during candidate fan-out")
            return events

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(coordinator_limit=3)
            self.write_manifest(root, value)
            adapters = self.two_candidate_adapters(first, second)
            with patch.object(
                SearchCoordinator,
                "commit_epoch",
                new=crash_after_first_child,
            ):
                with self.assertRaises(KeyboardInterrupt):
                    run_instrumented(
                        root / "manifest.json",
                        adapters=adapters,
                        lease_path=Path(directory) / "lease.json",
                        lane_executor=executor,
                    )

            self.assertEqual(len(calls), 1)
            def unexpected_executor(*_args, **_kwargs):
                raise AssertionError("archived lane result must be replayed")

            result = run_instrumented(
                root / "manifest.json",
                adapters=adapters,
                lease_path=Path(directory) / "lease.json",
                lane_executor=unexpected_executor,
            )
            state = recover_run(root)
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(state.frontier.graph.all()), 2)
            self.assertEqual(len(result["state"]["completed_task_ids"]), 3)
            self.assertEqual(
                sum(event.event_type == "candidate_materialized" for event in state.events),
                2,
            )

    def test_fan_out_refuses_before_scheduling_children_past_budget(self):
        first = self.candidate("candidate-source-1")
        second = self.candidate("candidate-source-2")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(coordinator_limit=2)
            self.write_manifest(root, value)
            with self.assertRaises(SupervisorIntegrationError):
                run_instrumented(
                    root / "manifest.json",
                    adapters=self.two_candidate_adapters(first, second),
                    lease_path=Path(directory) / "lease.json",
                )
            state = recover_run(root)
            scheduled = [
                event.payload
                for event in state.events
                if event.event_type == "task_scheduled"
            ]
            self.assertEqual(len(scheduled), 1)
            self.assertTrue(all(not task.operation.startswith("materialize_candidate:") for task in scheduled))

    def test_fan_out_rejects_candidate_ancestry_not_bound_to_lane(self):
        candidate = replace(
            self.candidate("candidate-source-1"),
            parent_candidate_ids=(hash_bytes(b"forged-parent"),),
        )
        adapters = {
            "upstream_current": lambda _recipient: LaneCandidate(
                candidate, "candidate-source-1"
            )
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(coordinator_limit=2)
            self.write_manifest(root, value)
            with self.assertRaises(SupervisorIntegrationError):
                run_instrumented(
                    root / "manifest.json",
                    adapters=adapters,
                    lease_path=Path(directory) / "lease.json",
                )
            state = recover_run(root)
            scheduled = [
                event.payload
                for event in state.events
                if event.event_type == "task_scheduled"
            ]
            self.assertEqual(len(scheduled), 1)
            self.assertEqual(scheduled[0].operation, "execute_lane")

    def test_fan_out_preflights_all_candidates_before_any_child(self):
        first = self.candidate("candidate-source-1")
        invalid = replace(
            self.candidate("candidate-source-2"),
            lane="upstream_pinned",
        )
        adapters = {
            "upstream_current": lambda _recipient: {
                "candidates": [
                    LaneCandidate(first, "candidate-source-1"),
                    LaneCandidate(invalid, "candidate-source-2"),
                ]
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(coordinator_limit=3)
            self.write_manifest(root, value)
            with self.assertRaises(SupervisorIntegrationError):
                run_instrumented(
                    root / "manifest.json",
                    adapters=adapters,
                    lease_path=Path(directory) / "lease.json",
                )
            state = recover_run(root)
            self.assertEqual(
                [
                    event.payload.operation
                    for event in state.events
                    if event.event_type == "task_scheduled"
                ],
                ["execute_lane"],
            )
            self.assertEqual(
                sum(event.event_type == "candidate_materialized" for event in state.events),
                0,
            )

    def test_instrumented_stop_is_atomic_request_consumed_by_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest()
            self.write_manifest(root, value)
            SearchCoordinator(root, value)
            lease_path = Path(directory) / "lease.json"
            current_pid = os.getpid()
            with SupervisorLease(
                mode=INSTRUMENTED_MODE,
                run_id=value.run_id,
                record_ids=value.queue_record_ids,
                path=lease_path,
                pid=current_pid,
                pid_alive=lambda pid: pid == current_pid,
            ):
                requested = stop_run(root)
                self.assertEqual(requested["command"], "instrumented-stop-request")
                self.assertTrue(requested["pending"])
                self.assertIsNone(recover_run(root).stopped)
                with self.assertRaises(SupervisorConflict):
                    run_instrumented(
                        root / "manifest.json",
                        adapters={},
                        lease_path=lease_path,
                    )
                self.assertIsNone(recover_run(root).stopped)

            result = run_instrumented(
                root / "manifest.json",
                adapters={},
                lease_path=lease_path,
            )
            state = recover_run(root)
            self.assertIsNotNone(state.stopped)
            self.assertEqual(
                sum(event.event_type == "run_stopped" for event in state.events),
                1,
            )
            self.assertEqual(
                sum(event.event_type == "task_scheduled" for event in state.events),
                0,
            )
            self.assertEqual(result["state"]["stopped"], state.stopped.to_dict())
            repeated = stop_run(root)
            self.assertFalse(repeated["pending"])

    def test_generic_cli_refuses_instrumented_resume_while_run_remains_stopped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest()
            self.write_manifest(root, value)
            SearchCoordinator(root, value)
            lease_path = Path(directory) / "lease.json"
            stop_run(root)
            run_instrumented(
                root / "manifest.json",
                adapters={},
                lease_path=lease_path,
            )

            with self.assertRaises(RunInputError):
                resume_run(root)

            state = recover_run(root)
            self.assertIsNotNone(state.stopped)
            self.assertEqual(
                sum(event.event_type == "run_resumed" for event in state.events),
                0,
            )

    def test_cli_resume_passes_landing_gate_for_score_zero_candidate(self):
        persisted = []
        received_landing = []

        def fake_resume(_manifest_path, **kwargs):
            received_landing.append(kwargs["landing"])
            result = kwargs["landing"](
                "us:ST/RDAI:func_cli_resume",
                "score-zero candidate",
                lambda outcome, detail: persisted.append((outcome, detail)),
            )
            return {"ok": True, "result": result}

        def fake_nonmatch(_cwd, _function, **kwargs):
            kwargs["on_terminal"](False, "score-zero candidate did not match")
            return False, "score-zero candidate did not match"

        argv = [
            "permuter_supervisor.py",
            "--resume",
            "--mode",
            "instrumented",
            "--manifest",
            "manifest.json",
        ]
        with patch.object(sys, "argv", argv):
            with patch.object(
                _permuter_supervisor.search_supervisor,
                "resume_instrumented",
                new=fake_resume,
            ):
                with patch.object(
                    _permuter_supervisor,
                    "land_match",
                    new=fake_nonmatch,
                ):
                    self.assertEqual(_permuter_supervisor.main(), 0)

        self.assertEqual(received_landing, [_permuter_supervisor._instrumented_landing])
        self.assertEqual(
            persisted,
            [("not_matched", "score-zero candidate did not match")],
        )

    def test_instrumented_resume_continues_exact_boundaries_and_fans_out(self):
        first = self.candidate("resume-first", lane="upstream_current")
        second_a = self.candidate("resume-second-a", lane="upstream_pinned")
        second_b = self.candidate("resume-second-b", lane="upstream_pinned")
        adapters = {
            "upstream_current": lambda _recipient: LaneCandidate(first, "resume-first"),
            "upstream_pinned": lambda _recipient: {
                "candidates": [
                    LaneCandidate(second_a, "resume-second-a"),
                    LaneCandidate(second_b, "resume-second-b"),
                ]
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.multi_lane_manifest(coordinator_limit=5)
            self.write_manifest(root, value)
            stop_once = [False]

            def stop_after_first(task, run_manifest, recipients, **kwargs):
                outcome = execute_task(
                    task,
                    run_manifest,
                    recipients,
                    **kwargs,
                )
                if task.lane == "upstream_current" and not stop_once[0]:
                    stop_once[0] = True
                    _search_supervisor.request_instrumented_stop(
                        root / "manifest.json"
                    )
                return outcome

            first_result = run_instrumented(
                root / "manifest.json",
                adapters=adapters,
                lease_path=Path(directory) / "lease.json",
                lane_executor=stop_after_first,
            )
            before = recover_run(root)
            self.assertIsNotNone(before.stopped)
            self.assertEqual(
                sum(event.event_type == "run_stopped" for event in before.events),
                1,
            )
            self.assertEqual(
                sum(event.event_type == "run_resumed" for event in before.events),
                0,
            )
            before_tasks = {
                event.payload.operation: event.payload
                for event in before.events
                if event.event_type == "task_scheduled"
            }
            self.assertEqual(set(before_tasks), {"execute_lane", "materialize_candidate:" + first.candidate_id})

            resumed = resume_instrumented(
                root / "manifest.json",
                adapters=adapters,
                lease_path=Path(directory) / "lease.json",
            )
            after = recover_run(root)
            self.assertEqual(resumed["command"], "instrumented-resume")
            self.assertIsNone(after.stopped)
            self.assertEqual(
                sum(event.event_type == "run_stopped" for event in after.events),
                1,
            )
            self.assertEqual(
                sum(event.event_type == "run_resumed" for event in after.events),
                1,
            )
            all_tasks = [
                event.payload
                for event in after.events
                if event.event_type == "task_scheduled"
            ]
            self.assertEqual(
                [task.budget_ordinal for task in all_tasks],
                [0, 2, 1, 3, 4],
            )
            for operation, task in before_tasks.items():
                self.assertIn(task.task_id, {item.task_id for item in all_tasks})
            self.assertEqual(
                sum(event.event_type == "exhaustion_recorded" for event in after.events),
                2,
            )
            self.assertEqual(len(after.terminal_tasks), 5)
            self.assertEqual(len(after.frontier.graph.all()), 3)
            request = json.loads(
                (root / "stop-request.json").read_text(encoding="utf-8")
            )
            self.assertEqual(request["state"], "acknowledged")

    def test_resume_request_ack_is_replayed_after_durable_resume_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest(coordinator_limit=2)
            self.write_manifest(root, value)
            SearchCoordinator(root, value)
            stop_run(root)
            run_instrumented(
                root / "manifest.json",
                adapters={},
                lease_path=Path(directory) / "lease.json",
            )
            original_atomic = _search_supervisor._atomic_json
            failed = [False]

            def crash_after_ack(path, document):
                original_atomic(path, document)
                if (
                    document.get("state") == "acknowledged"
                    and not failed[0]
                ):
                    failed[0] = True
                    raise KeyboardInterrupt("simulated loss after request acknowledgement")

            with patch.object(
                _search_supervisor, "_atomic_json", new=crash_after_ack
            ):
                with self.assertRaises(KeyboardInterrupt):
                    resume_instrumented(
                        root / "manifest.json",
                        adapters={},
                        lease_path=Path(directory) / "lease.json",
                    )
            after_crash = recover_run(root)
            self.assertIsNone(after_crash.stopped)
            self.assertEqual(
                sum(event.event_type == "run_resumed" for event in after_crash.events),
                1,
            )
            resumed = resume_instrumented(
                root / "manifest.json",
                adapters={},
                lease_path=Path(directory) / "lease.json",
            )
            final = recover_run(root)
            self.assertEqual(resumed["command"], "instrumented-resume")
            self.assertEqual(
                sum(event.event_type == "run_resumed" for event in final.events),
                1,
            )
            self.assertEqual(
                sum(event.event_type == "exhaustion_recorded" for event in final.events),
                1,
            )

    def test_instrumented_resume_refuses_a_live_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            value = self.instrumented_manifest()
            self.write_manifest(root, value)
            SearchCoordinator(root, value)
            stop_run(root)
            run_instrumented(
                root / "manifest.json",
                adapters={},
                lease_path=Path(directory) / "lease.json",
            )
            current_pid = os.getpid()
            with SupervisorLease(
                mode=INSTRUMENTED_MODE,
                run_id=value.run_id,
                record_ids=value.queue_record_ids,
                path=Path(directory) / "lease.json",
                pid=current_pid,
                pid_alive=lambda pid: pid == current_pid,
            ):
                with self.assertRaises(SupervisorConflict):
                    resume_instrumented(
                        root / "manifest.json",
                        adapters=self.adapters(),
                        lease_path=Path(directory) / "lease.json",
                    )
            self.assertIsNotNone(recover_run(root).stopped)

    def test_legacy_and_instrumented_leases_allow_disjoint_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "owners.json"
            alive = {101, 102}
            with SupervisorLease(
                mode="legacy",
                run_id="legacy-run",
                record_ids=("record-1",),
                path=path,
                pid=101,
                pid_alive=lambda pid: pid in alive,
            ):
                with SupervisorLease(
                    mode=INSTRUMENTED_MODE,
                    run_id="instrumented-run",
                    record_ids=("record-2",),
                    path=path,
                    pid=102,
                    pid_alive=lambda pid: pid in alive,
                ):
                    pass

    def test_legacy_and_instrumented_leases_cannot_overlap_a_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "owners.json"
            alive = {101, 102}
            first = SupervisorLease(
                mode="legacy",
                run_id="legacy-run",
                record_ids=("record-1",),
                path=path,
                pid=101,
                pid_alive=lambda pid: pid in alive,
            )
            with first:
                with self.assertRaises(SupervisorConflict):
                    with SupervisorLease(
                        mode=INSTRUMENTED_MODE,
                        run_id="instrumented-run",
                        record_ids=("record-1",),
                        path=path,
                        pid=102,
                        pid_alive=lambda pid: pid in alive,
                    ):
                        pass

    def test_execute_task_rejects_forged_task_identity_before_adapter(self):
        value = self.instrumented_manifest()
        base_task = SearchTask(
            task_id=hash_bytes(b"not-the-derived-task"),
            recipient_id="record-1",
            lane="upstream_current",
            tier="exact_deterministic",
            operation="execute_lane",
            parent_candidate_ids=(),
            budget_ordinal=0,
            task_seed=1,
            config_identity=value.config_identity,
            state="started",
        )
        called = []

        def adapter(_recipient):
            called.append(True)
            return None

        with self.assertRaises(LaneError):
            execute_task(
                base_task,
                value,
                ("record-1",),
                adapters={"upstream_current": adapter},
            )
        self.assertEqual(called, [])


if __name__ == "__main__":
    unittest.main()
