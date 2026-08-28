import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import ContentAddressedArchive
from automation.search_ledger import AppendOnlyLedger, LedgerIntegrityError, PartialLedgerLine
from automation.search_types import SearchTask, hash_bytes
from automation.test_search_schema import manifest


class TestSearchLedger(unittest.TestCase):
    def test_append_chain_and_recover_partial_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            ledger = AppendOnlyLedger(Path(directory) / "ledger.jsonl", archive=archive)
            ledger.start_run(manifest())
            task = SearchTask(
                task_id=hash_bytes(b"task"),
                recipient_id="record-1",
                lane="upstream_current",
                tier="exact_deterministic",
                operation="discover",
                parent_candidate_ids=(),
                budget_ordinal=0,
                task_seed=1,
                config_identity=manifest().config_identity,
                state="scheduled",
            )
            ledger.append_event("task_scheduled", task)
            path = Path(directory) / "ledger.jsonl"
            with path.open("ab") as stream:
                stream.write(b'{"partial":')
            self.assertEqual(len(ledger.verify()), 2)
            self.assertTrue(ledger.partial_bytes)
            with self.assertRaises(PartialLedgerLine):
                ledger.append_event("task_started", replace(task, state="started"))
            ledger.truncate_partial()
            ledger.append_event("task_started", replace(task, state="started"))
            self.assertEqual(len(ledger.verify()), 3)

    def test_chain_corruption_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = AppendOnlyLedger(Path(directory) / "ledger.jsonl")
            ledger.start_run(manifest())
            path = Path(directory) / "ledger.jsonl"
            data = path.read_text(encoding="utf-8").replace('"sequence":0', '"sequence":1', 1)
            path.write_text(data, encoding="utf-8")
            with self.assertRaises(LedgerIntegrityError):
                ledger.verify()


if __name__ == "__main__":
    unittest.main()
