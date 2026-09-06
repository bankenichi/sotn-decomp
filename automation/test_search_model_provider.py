"""Lazy dispatch and shared durable model budget regressions."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from automation.search_archive import ContentAddressedArchive
from automation.search_lanes import Recipient
from automation.search_model_executor import TrustedModelExecutor
from automation.search_model_provider import DeferredModelLaneProvider
from automation.search_model_lanes import discover_model_archive
from automation.search_types import hash_canonical
from automation.test_search_model_lanes import _manifest, _binding, _target, RECIPIENT, OTHER_RECIPIENT
from automation.test_search_model_executor import _Response


class LazyModelTests(unittest.TestCase):
    def test_factory_spec_is_lazy_and_reverse_dispatch_cannot_exceed_shared_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            manifest = _manifest(budget_limit=1, target_ids=(RECIPIENT, OTHER_RECIPIENT))
            binding = _binding(manifest)
            executor = TrustedModelExecutor.from_binding(
                binding, lane="model_fleet", selected=True, provider="local", endpoint="http://localhost:8080/v1",
                manifest_identity=hash_canonical(manifest.to_dict()), subset_identity=manifest.subset_identity,
            )
            with patch("automation.search_model_executor.urllib.request.urlopen") as network:
                provider = DeferredModelLaneProvider(
                    manifest, "model_fleet", tuple(_target(archive, item) for item in manifest.queue_record_ids),
                    binding, archive, executor,
                )
                rebuilt = DeferredModelLaneProvider.from_dict(provider.to_dict(), archive=archive, executor=executor)
                network.assert_not_called()
                self.assertEqual(len(discover_model_archive(archive).requests), 0)
            body = json.dumps({"choices": [{"message": {"content": '{"candidates":[{"source":"int answer(void) { return 7; }"}]}'}}]}).encode()
            second = Recipient(OTHER_RECIPIENT, "MODEL", "func_model_two")
            first = Recipient(RECIPIENT, "MODEL", "func_model_one")
            with patch("automation.search_model_executor.urllib.request.urlopen", return_value=_Response(body)) as network:
                completed = rebuilt.callback(second)
                self.assertTrue(completed["candidates"])
                self.assertEqual(network.call_count, 1)
                self.assertEqual(provider.callback(second), completed)
                rejected = provider.callback(first)
                self.assertEqual(rejected["refusal_code"], "model_external_call_budget_exhausted")
                self.assertEqual(network.call_count, 1)
                self.assertEqual(len(discover_model_archive(archive).requests), 1)


if __name__ == "__main__":
    unittest.main()
