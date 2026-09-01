"""Focused tests for production export call-graph closure."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_production_audit import (
    EXPECTED_LANE_CLOSURE_GAPS,
    audit_production_exports,
)


class ProductionAuditTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        annotate_value: bool = True,
        add_forged_annotations: bool = False,
    ) -> Path:
        automation = root / "automation"
        automation.mkdir(parents=True)
        annotation = "# production-audit: pure-value\n" if annotate_value else ""
        forged = ""
        if add_forged_annotations:
            forged = (
                "# production-audit: pure-value\n"
                "class ForgedMutable:\n"
                "    items: list[int]\n"
                "\n"
                "# production-audit: pure-value\n"
                "@dataclass(frozen=True)\n"
                "class ForgedFrozenMutable:\n"
                "    items: list[int]\n"
                "\n"
                "# production-audit: pure-value\n"
                "def forged_function():\n"
                "    return 1\n"
            )
        (automation / "tranche.py").write_text(
            "from dataclasses import dataclass\n"
            + annotation
            + "@dataclass(frozen=True)\n"
            "class Value:\n"
            "    number: int\n"
            "\n"
            "def used(value):\n"
            "    return helper(value)\n"
            "\n"
            "def helper(value):\n"
            "    return value + 1\n"
            "\n"
            "def orphan():\n"
            "    return 99\n"
            + forged,
            encoding="utf-8",
        )
        (automation / "connector.py").write_text(
            "from automation.tranche import used\n"
            "\n"
            "def tool(function):\n"
            "    return function\n"
            "\n"
            "@tool\n"
            "def entry(value):\n"
            "    return used(value)\n",
            encoding="utf-8",
        )
        return root

    def test_reports_orphaned_exports_and_retains_a_cli_caller_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = audit_production_exports(self._fixture(Path(directory)))
            self.assertFalse(report.passed)
            self.assertIn(
                "automation.tranche.orphan",
                report.unreachable_exports,
            )
            self.assertNotIn(
                "automation.tranche.used",
                report.unreachable_exports,
            )
            chain = report.caller_chains["automation.tranche.used"]
            self.assertEqual(chain[0], "automation.connector.entry")
            self.assertEqual(chain[-1], "automation.tranche.used")

    def test_dataclass_value_requires_explicit_annotation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = audit_production_exports(
                self._fixture(Path(directory), annotate_value=False)
            )
            self.assertIn("automation.tranche.Value", report.annotation_errors)
            self.assertFalse(report.passed)

    def test_pure_value_annotations_cannot_waive_mutable_classes_or_functions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = audit_production_exports(
                self._fixture(Path(directory), add_forged_annotations=True)
            )
            exports = {item.identity: item for item in report.exports}
            self.assertFalse(report.passed)
            self.assertIn("automation.tranche.ForgedMutable", report.unreachable_exports)
            self.assertIn("automation.tranche.ForgedFrozenMutable", report.annotation_errors)
            self.assertIn("automation.tranche.forged_function", report.unreachable_exports)
            self.assertNotEqual(exports["automation.tranche.ForgedMutable"].classification, "pure_value")
            self.assertNotEqual(
                exports["automation.tranche.ForgedFrozenMutable"].classification,
                "pure_value",
            )
            self.assertNotEqual(exports["automation.tranche.forged_function"].classification, "pure_value")

    def test_dispatcher_only_does_not_hide_factory_provider_or_runtime_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            automation = root / "automation"
            (automation / "mcp").mkdir(parents=True)
            (automation / "search_types.py").write_text(
                'LANES = ("new_lane",)\n',
                encoding="utf-8",
            )
            (automation / "search_lanes.py").write_text(
                "class LaneAdapters:\n"
                "    pass\n"
                "\n"
                "def _dispatch(lane):\n"
                '    if lane == "new_lane":\n'
                "        return None\n"
                "    return None\n",
                encoding="utf-8",
            )
            (automation / "search_run_factory.py").write_text(
                "_LANE_MODULES = {}\n",
                encoding="utf-8",
            )
            (automation / "search_cli.py").write_text(
                "def main():\n"
                "    return None\n",
                encoding="utf-8",
            )
            (automation / "search_supervisor.py").write_text(
                "def run():\n"
                "    return None\n",
                encoding="utf-8",
            )
            (automation / "search_recovery.py").write_text(
                "def recover():\n"
                "    return None\n",
                encoding="utf-8",
            )
            (automation / "mcp" / "commands_client.py").write_text(
                "_SEARCH_LANES = ()\n"
                "\n"
                "def _search_lanes(values):\n"
                "    return values\n",
                encoding="utf-8",
            )
            report = audit_production_exports(root)
            finding = report.lane_closure_by_lane["new_lane"]
            # A branch that returns ``None`` is not a dispatcher implementation.
            # The old substring/branch check falsely treated this as closed.
            self.assertTrue(finding.missing_dispatcher)
            self.assertTrue(finding.missing_factory_tool_binding)
            self.assertTrue(finding.missing_factory_module)
            self.assertTrue(finding.missing_factory_tool)
            self.assertTrue(finding.missing_factory_input)
            self.assertTrue(finding.missing_provider_input)
            self.assertTrue(finding.missing_provider_module)
            self.assertTrue(finding.missing_provider_adaptor)
            self.assertTrue(finding.missing_supervisor_reachability)
            self.assertTrue(finding.missing_recovery_reachability)
            self.assertTrue(finding.missing_cli_reachability)
            self.assertTrue(finding.missing_connector_reachability)
            self.assertIn("factory_tool_binding", finding.categories)
            self.assertIn("provider_input", finding.categories)
            self.assertIn("supervisor_reachability", finding.categories)
            self.assertIn("recovery_reachability", finding.categories)
            self.assertIn("cli_reachability", finding.categories)
            self.assertIn("connector_reachability", finding.categories)

    def test_adapter_field_only_does_not_close_provider_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            automation = root / "automation"
            automation.mkdir(parents=True)
            (automation / "search_types.py").write_text(
                'LANES = ("new_lane",)\n',
                encoding="utf-8",
            )
            (automation / "search_lanes.py").write_text(
                "import dataclasses\n"
                "from dataclasses import dataclass\n"
                "from typing import Any, Mapping\n"
                "\n"
                "@dataclass(frozen=True)\n"
                "class LaneAdapters:\n"
                "    new_lane: Any = None\n"
                "\n"
                "    @classmethod\n"
                "    def from_mapping(cls, value: Mapping[str, Any]):\n"
                "        names = {field.name for field in dataclasses.fields(cls)}\n"
                "        for name, callback in value.items():\n"
                "            if callback is not None and not callable(callback):\n"
                "                raise ValueError(name)\n"
                "        return cls(**{name: value.get(name) for name in names})\n"
                "\n"
                "def _dispatch(lane):\n"
                "    return None\n",
                encoding="utf-8",
            )
            report = audit_production_exports(root)
            finding = report.lane_closure_by_lane["new_lane"]
            self.assertFalse(finding.missing_provider_module)
            self.assertFalse(finding.missing_provider_adaptor)
            self.assertTrue(finding.missing_provider_input)
            self.assertIn("provider_input", finding.categories)

    def test_generic_supervisor_and_recovery_do_not_close_a_bound_lane(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            automation = root / "automation"
            automation.mkdir(parents=True)
            (automation / "search_types.py").write_text(
                'LANES = ("new_lane",)\n',
                encoding="utf-8",
            )
            (automation / "search_lanes.py").write_text(
                "import dataclasses\n"
                "from dataclasses import dataclass\n"
                "from typing import Any, Mapping\n"
                "\n"
                "@dataclass(frozen=True)\n"
                "class LaneAdapters:\n"
                "    new_lane: Any = None\n"
                "\n"
                "    @classmethod\n"
                "    def from_mapping(cls, value: Mapping[str, Any]):\n"
                "        names = {field.name for field in dataclasses.fields(cls)}\n"
                "        for name, callback in value.items():\n"
                "            if callback is not None and not callable(callback):\n"
                "                raise ValueError(name)\n"
                "        return cls(**{name: value.get(name) for name in names})\n"
                "\n"
                "def provider(lane):\n"
                "    return lane\n"
                "\n"
                "def _dispatch(lane):\n"
                '    if lane == "new_lane":\n'
                "        return provider(lane)\n"
                "    raise ValueError(lane)\n",
                encoding="utf-8",
            )
            (automation / "search_run_factory.py").write_text(
                "from automation.search_types import LANES\n"
                "\n"
                "def _normalize_inputs(name, record_ids, lanes):\n"
                "    if not lanes or lanes[0] not in LANES:\n"
                "        raise ValueError(lanes)\n"
                "    return name, record_ids, lanes\n"
                "\n"
                "def create_instrumented_run(name, record_ids, lanes):\n"
                "    return _normalize_inputs(name, record_ids, lanes)\n",
                encoding="utf-8",
            )
            (automation / "search_supervisor.py").write_text(
                "def execute_task():\n"
                "    return None\n"
                "\n"
                "def verify_factory_runtime():\n"
                "    return None\n"
                "\n"
                "def run_instrumented():\n"
                "    return execute_task()\n"
                "\n"
                "def resume_instrumented():\n"
                "    return execute_task()\n",
                encoding="utf-8",
            )
            (automation / "search_recovery.py").write_text(
                "def _load_manifest():\n"
                "    return None\n"
                "\n"
                "def validate_ledger_prefix():\n"
                "    return None\n"
                "\n"
                "def frontier_from_events():\n"
                "    return None\n"
                "\n"
                "def recover_run():\n"
                "    _load_manifest()\n"
                "    validate_ledger_prefix()\n"
                "    return frontier_from_events()\n",
                encoding="utf-8",
            )
            report = audit_production_exports(root)
            finding = report.lane_closure_by_lane["new_lane"]
            self.assertFalse(finding.missing_dispatcher)
            # A concrete-looking dispatcher helper is still not a provider
            # admission path without a lane-bound registry or factory.
            self.assertTrue(finding.missing_provider_input)
            self.assertTrue(finding.missing_factory_tool_binding)
            self.assertTrue(finding.missing_supervisor_reachability)
            self.assertTrue(finding.missing_recovery_reachability)
            self.assertIn("provider_input", finding.categories)
            self.assertIn("supervisor_reachability", finding.categories)
            self.assertIn("recovery_reachability", finding.categories)

    def test_self_consumed_registry_and_generic_supervisor_do_not_close_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            automation = root / "automation"
            automation.mkdir(parents=True)
            (automation / "search_types.py").write_text(
                'LANES = ("new_lane",)\n',
                encoding="utf-8",
            )
            (automation / "search_lanes.py").write_text(
                "from dataclasses import dataclass\n"
                "from typing import Any, Mapping\n"
                "\n"
                "def provider(lane):\n"
                "    return lane\n"
                "\n"
                "PROVIDER_REGISTRY = {\"new_lane\": provider}\n"
                "\n"
                "@dataclass(frozen=True)\n"
                "class LaneAdapters:\n"
                "    new_lane: Any = None\n"
                "\n"
                "    @classmethod\n"
                "    def from_mapping(cls, value: Mapping[str, Any]):\n"
                "        names = {field.name for field in dataclasses.fields(cls)}\n"
                "        for name, callback in value.items():\n"
                "            if callback is not None and not callable(callback):\n"
                "                raise ValueError(name)\n"
                "        return cls(**{name: value.get(name) for name in names})\n"
                "\n"
                "def provider_for(lane):\n"
                "    return PROVIDER_REGISTRY[lane]\n"
                "\n"
                "def _dispatch(lane):\n"
                '    if lane == "new_lane":\n'
                "        return provider_for(lane)\n"
                "    raise ValueError(lane)\n",
                encoding="utf-8",
            )
            (automation / "search_run_factory.py").write_text(
                "from automation.search_types import LANES\n"
                "_LANE_MODULES = {\"new_lane\": (\"automation/search_lanes.py\",)}\n"
                "\n"
                "def _normalize_inputs(name, record_ids, lanes):\n"
                "    if not lanes or lanes[0] not in LANES:\n"
                "        raise ValueError(lanes)\n"
                "    return name, record_ids, lanes\n"
                "\n"
                "def _tool_identities(repo, selected_lanes):\n"
                "    for lane in selected_lanes:\n"
                "        _LANE_MODULES.get(lane)\n"
                "    return {}\n"
                "\n"
                "def create_instrumented_run(name, record_ids, lanes):\n"
                "    name, record_ids, selected_lanes = _normalize_inputs(name, record_ids, lanes)\n"
                "    _tool_identities(None, selected_lanes)\n"
                "    return name, record_ids, selected_lanes\n",
                encoding="utf-8",
            )
            (automation / "search_supervisor.py").write_text(
                "def create_task(lane=None):\n"
                "    return lane\n"
                "\n"
                "def start_task(task):\n"
                "    return task\n"
                "\n"
                "def lane_executor(task, adapters=None, lane=None):\n"
                "    return adapters\n"
                "\n"
                "def _run_instrumented_locked(lanes, adapters):\n"
                "    for lane in lanes:\n"
                "        task = create_task(lane=lane)\n"
                "        started = start_task(task)\n"
                "        lane_executor(started, adapters=adapters, lane=lane)\n"
                "\n"
                "def _run_instrumented_entry(manifest):\n"
                "    _load_manifest_file(manifest)\n"
                "    verify_factory_runtime(manifest)\n"
                "    lanes = _ordered_lanes(manifest)\n"
                "    return _run_instrumented_locked(lanes, adapters=None)\n"
                "\n"
                "def run_instrumented(manifest):\n"
                "    return _run_instrumented_entry(manifest)\n"
                "\n"
                "def resume_instrumented(manifest):\n"
                "    return _run_instrumented_entry(manifest)\n",
                encoding="utf-8",
            )
            (automation / "search_recovery.py").write_text(
                "LANE_TOOL_KEYS = {\"new_lane\": (\"new_lane\",)}\n"
                "\n"
                "def _load_manifest():\n"
                "    return None\n"
                "\n"
                "def validate_ledger_prefix():\n"
                "    return None\n"
                "\n"
                "def frontier_from_events():\n"
                "    return None\n"
                "\n"
                "def recover_run(event, receipt, manifest):\n"
                '    if event.event_type == "exhaustion_recorded":\n'
                "        if receipt.lane in manifest.selected_lanes:\n"
                "            if receipt.tool_identities and manifest.tool_identities:\n"
                "                return receipt\n"
                "    _load_manifest()\n"
                "    validate_ledger_prefix()\n"
                "    return frontier_from_events()\n",
                encoding="utf-8",
            )
            (automation / "search_cli.py").write_text(
                "def build_parser():\n"
                "    parser = Parser()\n"
                '    parser.add_argument("--lanes")\n'
                "    return parser\n"
                "\n"
                "def _normalize_lanes(groups):\n"
                "    validate_lane(groups[0])\n"
                "    LANES\n"
                "    return tuple(groups)\n"
                "\n"
                "def _dispatch(args):\n"
                "    plan_selection(args.lanes)\n"
                "    create_instrumented_run(args.lanes)\n"
                "    return args.lanes\n",
                encoding="utf-8",
            )
            (automation / "mcp" ).mkdir()
            (automation / "mcp" / "commands_client.py").write_text(
                "_SEARCH_LANES = (\"new_lane\",)\n"
                "\n"
                "def _search_lanes(values):\n"
                "    set(values)\n"
                "    tuple(values)\n"
                "    set(values).difference(_SEARCH_LANES)\n"
                "    return values\n"
                "\n"
                "def _search_component(value):\n"
                "    return value\n"
                "\n"
                "def _search_record_ids(values):\n"
                "    return values\n"
                "\n"
                "def _search_create_argv(name, record_ids, lanes):\n"
                "    _search_component(name)\n"
                "    _search_record_ids(record_ids)\n"
                "    _search_lanes(lanes)\n"
                "    return []\n"
                "\n"
                "REGISTRY = {\"search_create_instrumented\": _search_create_argv(\"run\", (), ())}\n",
                encoding="utf-8",
            )
            report = audit_production_exports(root)
            finding = report.lane_closure_by_lane["new_lane"]
            self.assertFalse(finding.missing_dispatcher)
            self.assertFalse(finding.missing_factory_tool_binding)
            self.assertFalse(finding.missing_provider_input)
            self.assertTrue(finding.missing_supervisor_reachability)
            self.assertTrue(finding.missing_recovery_reachability)
            self.assertEqual(
                finding.categories,
                ("supervisor_reachability", "recovery_reachability"),
            )

    def test_audit_identity_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = audit_production_exports(self._fixture(root / "one"))
            second = audit_production_exports(self._fixture(root / "two"))
            self.assertEqual(first.identity, second.identity)
            self.assertEqual(first.to_dict(), second.to_dict())

    def test_current_lane_surface_reports_the_nine_unclosed_lanes(self) -> None:
        root = Path(__file__).resolve().parent.parent
        report = audit_production_exports(root)
        self.assertFalse(report.passed)
        findings = {item.lane: item for item in report.lane_findings}
        self.assertEqual(tuple(findings), EXPECTED_LANE_CLOSURE_GAPS)
        self.assertEqual(
            tuple(report.lane_closure_errors),
            EXPECTED_LANE_CLOSURE_GAPS,
        )
        for lane in EXPECTED_LANE_CLOSURE_GAPS:
            finding = findings[lane]
            self.assertTrue(finding.missing_dispatcher)
            self.assertTrue(finding.missing_factory_tool_binding)
            self.assertTrue(finding.missing_provider_input)
            self.assertTrue(finding.missing_supervisor_reachability)
            self.assertTrue(finding.missing_recovery_reachability)
            # Generic CLI/connector lane selection is already registered.  The
            # missing core dispatch is the closure defect being surfaced.
            self.assertFalse(finding.missing_cli_connector_reachability)
            self.assertFalse(finding.missing_cli_reachability)
            self.assertFalse(finding.missing_connector_reachability)
            self.assertTrue(finding.cli_reachable)
            self.assertTrue(finding.connector_reachable)
            self.assertEqual(
                finding.categories,
                (
                    "dispatcher",
                    "factory_tool_binding",
                    "provider_input",
                    "supervisor_reachability",
                    "recovery_reachability",
                ),
            )


if __name__ == "__main__":
    unittest.main()
