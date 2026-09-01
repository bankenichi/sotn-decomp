"""Focused tests for the trusted direct Zen/local model executor."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_model_executor import (
    DEFAULT_LOCAL_ENDPOINT,
    DEFAULT_ZEN_ENDPOINT,
    ModelExecutorBindingError,
    ModelExecutorError,
    TrustedModelExecutor,
    make_trusted_model_executor,
)
from automation.search_model_lanes import MODEL_FLEET_LANE, ModelBinding, ModelInvalidResponse, ModelRefused
from automation.search_types import hash_bytes, hash_canonical


def _hash(value):
    return hash_canonical(value)


def _binding() -> ModelBinding:
    template = "Recover {symbol}: {context}"
    return ModelBinding(
        provider_identity=_hash({"provider": "trusted"}),
        model_identity=_hash({"model": "fixture-model"}),
        model_name="fixture-model",
        prompt_identity=hash_bytes(template.encode("utf-8")),
        prompt_template=template,
        reasoning_identity=_hash({"reasoning": "none"}),
        reasoning="none",
        config_identity=_hash({"config": "fixture"}),
        tool_identity=_hash({"tool": MODEL_FLEET_LANE}),
        max_candidates=2,
        max_response_bytes=65536,
    )


def _request(executor: TrustedModelExecutor):
    return SimpleNamespace(
        request_id=_hash({"request": "fixture"}),
        provider_identity=executor.provider_identity,
        model_identity=executor.model_identity,
        model_name=executor.model_name,
        prompt_identity=executor.prompt_identity,
        reasoning_identity=executor.reasoning_identity,
        reasoning=executor.reasoning,
        manifest_identity=executor.manifest_identity,
        subset_identity=executor.subset_identity,
        config_identity=executor.config_identity,
        tool_identity=executor.tool_identity,
    )


class _Response:
    status = 200

    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, limit=-1):
        return self.body if limit < 0 else self.body[:limit]


class TrustedModelExecutorTests(unittest.TestCase):
    def test_unselected_executor_is_typed_refusal_without_network(self) -> None:
        binding = _binding()
        executor = make_trusted_model_executor(
            binding,
            lane=MODEL_FLEET_LANE,
            manifest_identity=_hash({"manifest": "fixture"}),
            subset_identity=_hash({"subset": "fixture"}),
            selected=False,
        )
        self.assertEqual(executor.preflight().code, "model_lane_not_selected")
        with patch("automation.search_model_executor.urllib.request.urlopen") as urlopen:
            with self.assertRaises(ModelRefused):
                executor.invoke(_request(executor), prompt="{}", contexts=())
            urlopen.assert_not_called()

    def test_paid_executor_requires_explicit_binding(self) -> None:
        binding = _binding()
        executor = TrustedModelExecutor(
            endpoint=DEFAULT_ZEN_ENDPOINT,
            model_name=binding.model_name,
            provider="zen",
            lane=MODEL_FLEET_LANE,
            model_identity=binding.model_identity,
            prompt_identity=binding.prompt_identity,
            reasoning_identity=binding.reasoning_identity,
            reasoning=binding.reasoning,
            provider_identity=binding.provider_identity,
            manifest_identity=_hash({"manifest": "fixture"}),
            subset_identity=_hash({"subset": "fixture"}),
            selected=True,
            paid=True,
        )
        self.assertEqual(executor.preflight().code, "model_paid_binding_required")

    def test_endpoint_model_prompt_reasoning_and_provider_change_identity(self) -> None:
        binding = _binding()
        kwargs = dict(
            lane=MODEL_FLEET_LANE,
            manifest_identity=_hash({"manifest": "fixture"}),
            subset_identity=_hash({"subset": "fixture"}),
            selected=True,
        )
        first = make_trusted_model_executor(binding, endpoint=DEFAULT_LOCAL_ENDPOINT, **kwargs)
        second = make_trusted_model_executor(
            binding,
            endpoint="http://localhost:8082/v1",
            **kwargs,
        )
        self.assertNotEqual(first.endpoint_identity, second.endpoint_identity)
        self.assertNotEqual(first.executor_identity, second.executor_identity)
        self.assertNotEqual(first.binding_identity, second.binding_identity)

    def test_direct_local_completion_uses_immutable_request_bindings(self) -> None:
        binding = _binding()
        executor = make_trusted_model_executor(
            binding,
            lane=MODEL_FLEET_LANE,
            manifest_identity=_hash({"manifest": "fixture"}),
            subset_identity=_hash({"subset": "fixture"}),
            selected=True,
            provider="local",
            endpoint=DEFAULT_LOCAL_ENDPOINT,
        )
        body = json.dumps(
            {"choices": [{"message": {"content": '{"candidates": []}'}}]}
        ).encode("utf-8")
        with patch(
            "automation.search_model_executor.urllib.request.urlopen",
            return_value=_Response(body),
        ) as urlopen:
            response = executor.invoke(
                _request(executor),
                prompt="Recover the target",
                contexts=(b"immutable context",),
            )
        self.assertEqual(response.status, "ok")
        self.assertEqual(response.response_text, '{"candidates": []}')
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, DEFAULT_LOCAL_ENDPOINT + "/chat/completions")
        self.assertEqual(payload["model"], binding.model_name)
        self.assertEqual(payload["messages"][0]["content"], "Recover the target")
        self.assertEqual(payload["reasoning_budget"], 0)

    def test_empty_direct_completion_is_typed_invalid(self) -> None:
        binding = _binding()
        executor = make_trusted_model_executor(
            binding,
            lane=MODEL_FLEET_LANE,
            manifest_identity=_hash({"manifest": "fixture"}),
            subset_identity=_hash({"subset": "fixture"}),
            selected=True,
            provider="local",
            endpoint=DEFAULT_LOCAL_ENDPOINT,
        )
        body = b'{"choices":[{"message":{"content":""}}]}'
        with patch(
            "automation.search_model_executor.urllib.request.urlopen",
            return_value=_Response(body),
        ):
            with self.assertRaises(ModelInvalidResponse):
                executor.invoke(_request(executor), prompt="Recover", contexts=())

    def test_executor_state_round_trip_and_forgery_refusal(self) -> None:
        binding = _binding()
        executor = make_trusted_model_executor(
            binding,
            lane=MODEL_FLEET_LANE,
            manifest_identity=_hash({"manifest": "fixture"}),
            subset_identity=_hash({"subset": "fixture"}),
            selected=True,
            provider="local",
            endpoint=DEFAULT_LOCAL_ENDPOINT,
        )
        rebuilt = TrustedModelExecutor.from_dict(executor.to_dict())
        self.assertEqual(rebuilt.to_dict(), executor.to_dict())
        forged = executor.to_dict()
        forged["endpoint"] = "http://localhost:9999/v1"
        with self.assertRaises(ModelExecutorError):
            TrustedModelExecutor.from_dict(forged)

    def test_noncanonical_windows_endpoint_is_refused_at_construction(self) -> None:
        binding = _binding()
        with self.assertRaises(ModelExecutorError):
            make_trusted_model_executor(
                binding,
                lane=MODEL_FLEET_LANE,
                manifest_identity=_hash({"manifest": "fixture"}),
                subset_identity=_hash({"subset": "fixture"}),
                selected=True,
                endpoint="C:\\models\\server",
            )

    def test_from_binding_requires_typed_binding(self) -> None:
        with self.assertRaises(ModelExecutorBindingError):
            TrustedModelExecutor.from_binding(
                object(),
                lane=MODEL_FLEET_LANE,
                manifest_identity=_hash({"manifest": "fixture"}),
                subset_identity=_hash({"subset": "fixture"}),
                selected=True,
            )


if __name__ == "__main__":
    unittest.main()
