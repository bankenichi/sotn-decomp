"""Focused tests for the trusted direct Zen/local model executor."""

from __future__ import annotations

import json
import sys
import tempfile
import socket
import urllib.error
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
from automation.search_model_lanes import MODEL_FLEET_LANE, ModelBinding, ModelInvalidResponse, ModelRefused, ModelTimeout, ModelUnavailable, ModelResponse
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
    def local_executor(self):
        return make_trusted_model_executor(
            _binding(), lane=MODEL_FLEET_LANE,
            manifest_identity=_hash({"manifest": "fixture"}),
            subset_identity=_hash({"subset": "fixture"}),
            selected=True, provider="local", endpoint=DEFAULT_LOCAL_ENDPOINT,
        )

    def test_response_keeps_sanitized_usage_and_provider_envelope(self):
        executor = self.local_executor()
        body = json.dumps({
            "id": "response-123", "model": "actually-served",
            "choices": [{"finish_reason": "length", "message": {
                "content": '{"candidates": []}', "reasoning_content": "private reasoning",
            }}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 9, "total_tokens": 21,
                      "completion_tokens_details": {"reasoning_tokens": 4}},
            "secret": "must not retain",
        }).encode()
        with patch("automation.search_model_executor.urllib.request.urlopen", return_value=_Response(body)):
            response = executor.invoke(_request(executor), prompt="Recover", contexts=())
        self.assertEqual(response.telemetry["returned_model"], "actually-served")
        self.assertEqual(response.telemetry["finish_reason"], "length")
        self.assertEqual(response.telemetry["usage"]["reasoning_tokens"], 4)
        self.assertEqual(response.telemetry["usage"]["total_tokens"], 21)
        self.assertIsNone(response.telemetry["usage"]["cached_tokens"])
        self.assertTrue(response.telemetry["has_reasoning"])
        self.assertNotIn("private reasoning", json.dumps(response.to_dict()))
        self.assertNotIn("must not retain", json.dumps(response.to_dict()))
        self.assertEqual(ModelResponse.from_dict(response.to_dict()), response)

    def test_elapsed_time_is_not_a_response_identity(self):
        executor = self.local_executor()
        body = b'{"choices":[{"message":{"content":"ok"}}]}'
        responses = []
        for elapsed in (1.0, 4.0):
            with patch("automation.search_model_executor.urllib.request.urlopen", return_value=_Response(body)), patch(
                "automation.search_model_executor.time.monotonic", side_effect=[0.0, elapsed],
            ):
                responses.append(executor.invoke(_request(executor), prompt="Recover", contexts=()))
        self.assertEqual([r.elapsed_ms for r in responses], [1000, 4000])
        self.assertEqual(responses[0].response_identity, responses[1].response_identity)
        self.assertEqual(responses[0].to_dict(), responses[1].to_dict())

    def test_transport_failures_keep_precise_outcomes(self):
        executor = self.local_executor()
        cases = (
            (socket.timeout("timed out"), ModelTimeout, "socket_timeout"),
            (urllib.error.URLError(socket.timeout("timed out")), ModelTimeout, "socket_timeout"),
            (urllib.error.HTTPError(executor.endpoint, 429, "limited", {}, None), ModelUnavailable, "rate_limited"),
            (urllib.error.HTTPError(executor.endpoint, 503, "down", {}, None), ModelUnavailable, "http_server_error"),
        )
        for failure, kind, code in cases:
            with self.subTest(code=code), patch(
                "automation.search_model_executor.urllib.request.urlopen", side_effect=failure,
            ):
                with self.assertRaises(kind) as caught:
                    executor.invoke(_request(executor), prompt="Recover", contexts=())
                self.assertEqual(caught.exception.response.error_code, code)
                self.assertEqual(caught.exception.response.telemetry["transport_outcome"], code)

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

    def test_operational_and_credential_fields_are_identity_bound(self) -> None:
        binding = _binding()
        executor = make_trusted_model_executor(
            binding,
            lane=MODEL_FLEET_LANE,
            manifest_identity=_hash({"manifest": "fixture"}),
            subset_identity=_hash({"subset": "fixture"}),
            selected=True,
            provider="local",
            endpoint=DEFAULT_LOCAL_ENDPOINT,
            timeout_seconds=17.0,
            max_tokens=1234,
            api_key_env="ALT_MODEL_KEY",
        )
        variants = {
            "timeout_seconds": 18.0,
            "max_tokens": 1235,
            "api_key_env": "OTHER_MODEL_KEY",
        }
        for field, changed in variants.items():
            with self.subTest(field=field):
                forged = executor.to_dict()
                forged[field] = changed
                with self.assertRaises(ModelExecutorError):
                    TrustedModelExecutor.from_dict(forged)

        timeout_variant = make_trusted_model_executor(
            binding,
            lane=MODEL_FLEET_LANE,
            manifest_identity=executor.manifest_identity,
            subset_identity=executor.subset_identity,
            selected=True,
            provider="local",
            endpoint=DEFAULT_LOCAL_ENDPOINT,
            timeout_seconds=18.0,
            max_tokens=1234,
            api_key_env="ALT_MODEL_KEY",
        )
        self.assertNotEqual(executor.executor_identity, timeout_variant.executor_identity)
        self.assertNotEqual(executor.binding_identity, timeout_variant.binding_identity)

    def test_selected_and_paid_require_exact_booleans(self) -> None:
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
        for field, value in (("selected", "false"), ("paid", 1)):
            with self.subTest(field=field):
                forged = executor.to_dict()
                forged[field] = value
                with self.assertRaises(ModelExecutorError):
                    TrustedModelExecutor.from_dict(forged)
        with self.assertRaises(ModelExecutorError):
            TrustedModelExecutor(
                model_identity=executor.model_identity,
                prompt_identity=executor.prompt_identity,
                reasoning_identity=executor.reasoning_identity,
                reasoning=executor.reasoning,
                provider_identity=executor.provider_identity,
                manifest_identity=executor.manifest_identity,
                subset_identity=executor.subset_identity,
                config_identity=executor.config_identity,
                tool_identity=executor.tool_identity,
                provider="local",
                lane=MODEL_FLEET_LANE,
                endpoint=DEFAULT_LOCAL_ENDPOINT,
                model_name=executor.model_name,
                selected="false",
            )

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
