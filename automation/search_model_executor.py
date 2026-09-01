"""Concrete, proposal-only model execution over the direct Zen/local API.

The regular model lane accepts a narrow ``ModelProvider`` protocol.  This
module supplies the production implementation for that protocol without
importing the worker, touching a checkout, or invoking a CLI that can inspect
the repository.  Endpoint, provider, model, prompt, reasoning, and lane
bindings are frozen at construction.  A call is refused unless the lane was
explicitly selected and bound to immutable run identities.
"""

from __future__ import annotations

import json
import os
import socket
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from urllib.parse import urlsplit, urlunsplit

try:
    from .search_model_lanes import (
        MODEL_EXPENSIVE_LANE,
        MODEL_FLEET_LANE,
        MODEL_LANES,
        ModelBinding,
        ModelInvalidResponse,
        ModelRefused,
        ModelResponse,
        ModelTimeout,
        ModelUnavailable,
    )
    from .search_types import hash_canonical, hash_bytes, validate_hash
except ImportError:  # pragma: no cover - direct script compatibility
    from search_model_lanes import (  # type: ignore
        MODEL_EXPENSIVE_LANE,
        MODEL_FLEET_LANE,
        MODEL_LANES,
        ModelBinding,
        ModelInvalidResponse,
        ModelRefused,
        ModelResponse,
        ModelTimeout,
        ModelUnavailable,
    )
    from search_types import hash_canonical, hash_bytes, validate_hash  # type: ignore


MODEL_EXECUTOR_PROTOCOL = "sotn-model-executor-v1"
TRUSTED_ZEN_PROVIDER = "zen"
TRUSTED_LOCAL_PROVIDER = "local"
TRUSTED_PROVIDERS = frozenset({TRUSTED_ZEN_PROVIDER, TRUSTED_LOCAL_PROVIDER})
DEFAULT_ZEN_ENDPOINT = "https://opencode.ai/zen/v1"
DEFAULT_LOCAL_ENDPOINT = "http://localhost:8081/v1"
DEFAULT_ZEN_MODEL = "mimo-v2.5-free"
DEFAULT_LOCAL_MODEL = "Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-APEX-MTP-I-Compact.gguf"
_MAX_ENDPOINT_BYTES = 2048
_MAX_MODEL_BYTES = 512
_MAX_REASONING_BYTES = 128
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class ModelExecutorError(ValueError):
    """Invalid immutable executor configuration."""


class ModelExecutorBindingError(ModelExecutorError):
    """The executor is not bound to the request's immutable run inputs."""


@dataclass(frozen=True)
class ModelExecutorPreflight:
    """Typed, side-effect-free readiness result."""

    status: str
    code: str
    detail: str = ""

    def __post_init__(self) -> None:
        if self.status not in {"ready", "unavailable", "refused"}:
            raise ModelExecutorError("invalid model executor preflight status")
        if not isinstance(self.code, str) or not self.code:
            raise ModelExecutorError("model executor preflight code is required")
        if not isinstance(self.detail, str):
            raise ModelExecutorError("model executor preflight detail must be text")

    @property
    def ready(self) -> bool:
        return self.status == "ready"


def _endpoint(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ModelExecutorError("endpoint must be nonempty text")
    if len(value.encode("utf-8")) > _MAX_ENDPOINT_BYTES:
        raise ModelExecutorError("endpoint is too long")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ModelExecutorError("endpoint must be an HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ModelExecutorError("endpoint must not embed credentials")
    if parsed.query or parsed.fragment:
        raise ModelExecutorError("endpoint must not contain a query or fragment")
    path = parsed.path.rstrip("/") or ""
    if any(part in {"", ".", ".."} for part in path.replace("\\", "/").split("/") if part):
        raise ModelExecutorError("endpoint path contains traversal")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, path, "", ""))


def _text(value: Any, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value:
        raise ModelExecutorError(f"{label} must be nonempty text")
    if len(value.encode("utf-8")) > maximum:
        raise ModelExecutorError(f"{label} is too long")
    return value


def _optional_hash(value: str, label: str) -> str:
    if not value:
        return ""
    try:
        return validate_hash(value, label)
    except Exception as exc:
        raise ModelExecutorError(f"{label} must be a sha256 identity") from exc


@dataclass(frozen=True)
class TrustedModelExecutor:
    """Trusted implementation of the model lane's typed provider protocol.

    ``selected`` is deliberately false by default.  In particular, a paid
    endpoint/model pair cannot be reached merely because an executor object
    was constructed.  ``manifest_identity`` and ``subset_identity`` are the
    immutable run binding; paid lanes also require config and tool identities.
    """

    endpoint: str = DEFAULT_ZEN_ENDPOINT
    model_name: str = DEFAULT_ZEN_MODEL
    provider: str = TRUSTED_ZEN_PROVIDER
    lane: str = MODEL_FLEET_LANE
    model_identity: str = ""
    prompt_identity: str = ""
    reasoning_identity: str = ""
    reasoning: str = "none"
    provider_identity: str = ""
    manifest_identity: str = ""
    subset_identity: str = ""
    config_identity: str = ""
    tool_identity: str = ""
    selected: bool = False
    paid: bool = False
    timeout_seconds: float = 60.0
    max_tokens: int = 4096
    api_key_env: str = "MODEL_API_KEY"

    def __post_init__(self) -> None:
        object.__setattr__(self, "endpoint", _endpoint(self.endpoint))
        if self.provider not in TRUSTED_PROVIDERS:
            raise ModelExecutorError("provider is not a trusted Zen/local provider")
        if self.lane not in MODEL_LANES:
            raise ModelExecutorError("executor lane is not a model lane")
        object.__setattr__(self, "model_name", _text(self.model_name, "model_name", _MAX_MODEL_BYTES))
        object.__setattr__(self, "reasoning", _text(self.reasoning, "reasoning", _MAX_REASONING_BYTES))
        for name in (
            "model_identity", "prompt_identity", "reasoning_identity", "provider_identity",
            "manifest_identity", "subset_identity", "config_identity", "tool_identity",
        ):
            object.__setattr__(self, name, _optional_hash(getattr(self, name), name))
        if self.model_identity == "":
            object.__setattr__(
                self,
                "model_identity",
                hash_canonical({"model": self.model_name}),
            )
        if self.prompt_identity == "":
            raise ModelExecutorError("prompt_identity is required for a bound executor")
        if self.reasoning_identity == "":
            expected_reasoning = hash_canonical({"reasoning": self.reasoning})
            object.__setattr__(self, "reasoning_identity", expected_reasoning)
        if self.provider_identity == "":
            object.__setattr__(
                self,
                "provider_identity",
                hash_canonical(self._identity_payload_without_provider_identity()),
            )
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)):
            raise ModelExecutorError("timeout_seconds must be numeric")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 3600:
            raise ModelExecutorError("timeout_seconds is outside the safe bound")
        if isinstance(self.max_tokens, bool) or not isinstance(self.max_tokens, int):
            raise ModelExecutorError("max_tokens must be an integer")
        if self.max_tokens < 1 or self.max_tokens > 65536:
            raise ModelExecutorError("max_tokens is outside the safe bound")
        if not isinstance(self.api_key_env, str) or not self.api_key_env.isidentifier():
            raise ModelExecutorError("api_key_env must be a safe environment name")
        if self.paid and self.provider == TRUSTED_ZEN_PROVIDER and self.model_name.endswith("-free"):
            raise ModelExecutorError("a free Zen model cannot be marked paid")

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "protocol": MODEL_EXECUTOR_PROTOCOL,
            "endpoint": self.endpoint,
            "model_name": self.model_name,
            "provider": self.provider,
            "lane": self.lane,
            "model_identity": self.model_identity,
            "prompt_identity": self.prompt_identity,
            "reasoning_identity": self.reasoning_identity,
            "reasoning": self.reasoning,
            "provider_identity": self.provider_identity,
            "manifest_identity": self.manifest_identity,
            "subset_identity": self.subset_identity,
            "config_identity": self.config_identity,
            "tool_identity": self.tool_identity,
            "selected": self.selected,
            "paid": self.paid,
        }

    @property
    def executor_identity(self) -> str:
        return hash_canonical(
            {
                **self._identity_payload_without_provider_identity(),
                "provider_identity": self.provider_identity,
            }
        )

    def _identity_payload_without_provider_identity(self) -> dict[str, Any]:
        return {
            "protocol": MODEL_EXECUTOR_PROTOCOL,
            "endpoint": self.endpoint,
            "model_name": self.model_name,
            "provider": self.provider,
            "lane": self.lane,
            "model_identity": self.model_identity,
            "prompt_identity": self.prompt_identity,
            "reasoning_identity": self.reasoning_identity,
            "reasoning": self.reasoning,
            "manifest_identity": self.manifest_identity,
            "subset_identity": self.subset_identity,
            "config_identity": self.config_identity,
            "tool_identity": self.tool_identity,
            "selected": self.selected,
            "paid": self.paid,
        }

    @property
    def endpoint_identity(self) -> str:
        return hash_canonical({"endpoint": self.endpoint})

    @property
    def binding_identity(self) -> str:
        return hash_canonical(self._identity_payload())

    @classmethod
    def from_binding(
        cls,
        binding: ModelBinding,
        *,
        lane: str,
        manifest_identity: str,
        subset_identity: str,
        selected: bool,
        provider: str = TRUSTED_ZEN_PROVIDER,
        endpoint: Optional[str] = None,
        paid: bool = False,
        timeout_seconds: float = 60.0,
        max_tokens: int = 4096,
    ) -> "TrustedModelExecutor":
        if not isinstance(binding, ModelBinding):
            raise ModelExecutorBindingError("from_binding requires a typed ModelBinding")
        if lane not in MODEL_LANES:
            raise ModelExecutorBindingError("from_binding requires a model lane")
        if provider not in TRUSTED_PROVIDERS:
            raise ModelExecutorBindingError("from_binding requires Zen or local provider")
        if endpoint is None:
            endpoint = (
                os.environ.get("ZEN_BASE_URL", DEFAULT_ZEN_ENDPOINT)
                if provider == TRUSTED_ZEN_PROVIDER
                else os.environ.get("LLAMA_BASE_URL", DEFAULT_LOCAL_ENDPOINT)
            )
        return cls(
            endpoint=endpoint,
            model_name=binding.model_name,
            provider=provider,
            lane=lane,
            model_identity=binding.model_identity,
            prompt_identity=binding.prompt_identity,
            reasoning_identity=binding.reasoning_identity,
            reasoning=binding.reasoning,
            provider_identity=binding.provider_identity,
            manifest_identity=manifest_identity,
            subset_identity=subset_identity,
            config_identity=binding.config_identity,
            tool_identity=binding.tool_identity,
            selected=selected,
            paid=paid,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": MODEL_EXECUTOR_PROTOCOL,
            **self._identity_payload(),
            "executor_identity": self.executor_identity,
            "endpoint_identity": self.endpoint_identity,
            "binding_identity": self.binding_identity,
            "timeout_seconds": self.timeout_seconds,
            "max_tokens": self.max_tokens,
            "api_key_env": self.api_key_env,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TrustedModelExecutor":
        if not isinstance(value, Mapping):
            raise ModelExecutorError("executor state must be an object")
        required = {
            "protocol", "endpoint", "model_name", "provider", "lane", "model_identity",
            "prompt_identity", "reasoning_identity", "reasoning", "provider_identity",
            "manifest_identity", "subset_identity", "config_identity", "tool_identity",
            "selected", "paid", "executor_identity", "endpoint_identity", "binding_identity",
            "timeout_seconds", "max_tokens", "api_key_env",
        }
        if set(value) != required or value.get("protocol") != MODEL_EXECUTOR_PROTOCOL:
            raise ModelExecutorError("executor state has the wrong schema")
        executor = cls(
            endpoint=value["endpoint"],
            model_name=value["model_name"],
            provider=value["provider"],
            lane=value["lane"],
            model_identity=value["model_identity"],
            prompt_identity=value["prompt_identity"],
            reasoning_identity=value["reasoning_identity"],
            reasoning=value["reasoning"],
            provider_identity=value["provider_identity"],
            manifest_identity=value["manifest_identity"],
            subset_identity=value["subset_identity"],
            config_identity=value["config_identity"],
            tool_identity=value["tool_identity"],
            selected=value["selected"],
            paid=value["paid"],
            timeout_seconds=value["timeout_seconds"],
            max_tokens=value["max_tokens"],
            api_key_env=value["api_key_env"],
        )
        if (
            value["executor_identity"] != executor.executor_identity
            or value["endpoint_identity"] != executor.endpoint_identity
            or value["binding_identity"] != executor.binding_identity
        ):
            raise ModelExecutorError("executor state identities are forged")
        return executor

    def preflight(self) -> ModelExecutorPreflight:
        if not self.selected:
            return ModelExecutorPreflight(
                "refused",
                "model_lane_not_selected",
                "the model lane was not explicitly selected",
            )
        if not self.manifest_identity or not self.subset_identity:
            return ModelExecutorPreflight(
                "refused",
                "model_binding_required",
                "executor is not bound to a manifest subset",
            )
        if self.paid and not (self.config_identity and self.tool_identity):
            return ModelExecutorPreflight(
                "refused",
                "model_paid_binding_required",
                "paid execution requires immutable config and tool bindings",
            )
        if self.provider == TRUSTED_ZEN_PROVIDER and not self.endpoint.startswith("https://"):
            return ModelExecutorPreflight(
                "unavailable",
                "model_zen_endpoint_unavailable",
                "Zen requires its HTTPS endpoint",
            )
        return ModelExecutorPreflight("ready", "model_executor_ready")

    def _validate_request(self, request: Any, prompt: str) -> None:
        if not hasattr(request, "request_id"):
            raise ModelExecutorBindingError("executor requires a typed ModelRequest")
        fields = {
            "provider_identity": self.provider_identity,
            "model_identity": self.model_identity,
            "model_name": self.model_name,
            "prompt_identity": self.prompt_identity,
            "reasoning_identity": self.reasoning_identity,
            "reasoning": self.reasoning,
            "manifest_identity": self.manifest_identity,
            "subset_identity": self.subset_identity,
            "config_identity": self.config_identity,
            "tool_identity": self.tool_identity,
        }
        for name, expected in fields.items():
            actual = getattr(request, name, None)
            if expected and actual != expected:
                raise ModelExecutorBindingError(f"request {name} differs from executor binding")
        if not isinstance(prompt, str) or not prompt:
            raise ModelInvalidResponse("model prompt is empty")
        if len(prompt.encode("utf-8")) > 3 * 1024 * 1024:
            raise ModelInvalidResponse("model prompt exceeds the immutable bound")

    def _headers(self) -> Mapping[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.provider == TRUSTED_ZEN_PROVIDER:
            headers = {
                **headers,
                "User-Agent": "opencode/1.18.12",
                "x-opencode-client": "cli",
            }
        key = os.environ.get(self.api_key_env, "").strip()
        if key:
            headers = {**headers, "Authorization": f"Bearer {key}"}
        return headers

    def _payload(self, prompt: str) -> bytes:
        effort = self.reasoning.lower()
        body: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        if effort in {"none", "off", "0"}:
            body.update(
                {
                    "reasoning_effort": "none",
                    "reasoning_budget": 0,
                    "chat_template_kwargs": {"enable_thinking": False},
                    "thinking": {"type": "disabled"},
                }
            )
        else:
            body.update(
                {
                    "reasoning_effort": self.reasoning,
                    "reasoning_budget": max(0, self.max_tokens // 2),
                    "chat_template_kwargs": {"enable_thinking": True},
                }
            )
        return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def _content(decoded: Mapping[str, Any]) -> str:
        choices = decoded.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ModelInvalidResponse("model response has no choices")
        first = choices[0]
        if not isinstance(first, Mapping):
            raise ModelInvalidResponse("model response choice is malformed")
        message = first.get("message")
        if not isinstance(message, Mapping):
            message = first
        content = message.get("content")
        if isinstance(content, list):
            pieces = []
            for item in content:
                if isinstance(item, Mapping) and isinstance(item.get("text"), str):
                    pieces.append(item["text"])
            content = "".join(pieces)
        if not isinstance(content, str) or not content.strip():
            if message.get("reasoning_content"):
                raise ModelInvalidResponse("model response contains reasoning but no content")
            raise ModelInvalidResponse("model response content is empty")
        if len(content.encode("utf-8")) > _MAX_RESPONSE_BYTES:
            raise ModelInvalidResponse("model response exceeds the immutable bound")
        return content

    def invoke(
        self,
        request: Any,
        *,
        prompt: str,
        contexts: tuple[bytes, ...],
    ) -> ModelResponse:
        preflight = self.preflight()
        if preflight.status == "refused":
            raise ModelRefused(preflight.detail)
        if preflight.status == "unavailable":
            raise ModelUnavailable(preflight.detail)
        self._validate_request(request, prompt)
        if not isinstance(contexts, tuple) or any(not isinstance(item, bytes) for item in contexts):
            raise ModelInvalidResponse("model contexts are not immutable bytes")
        url = self.endpoint + "/chat/completions"
        req = urllib.request.Request(
            url,
            data=self._payload(prompt),
            headers=dict(self._headers()),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            if exc.code in {408, 429, 500, 502, 503, 504}:
                raise ModelTimeout(f"model endpoint returned HTTP {exc.code}") from exc
            if exc.code in {401, 403}:
                raise ModelRefused(f"model endpoint returned HTTP {exc.code}") from exc
            raise ModelUnavailable(f"model endpoint returned HTTP {exc.code}") from exc
        except (urllib.error.URLError, socket.timeout, TimeoutError, ssl.SSLError, OSError) as exc:
            raise ModelUnavailable(f"model endpoint is unavailable: {type(exc).__name__}") from exc
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise ModelInvalidResponse("model response exceeds the immutable bound")
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ModelInvalidResponse("model endpoint returned non-JSON data") from exc
        if not isinstance(decoded, Mapping):
            raise ModelInvalidResponse("model endpoint returned a non-object")
        if decoded.get("error"):
            raise ModelRefused("model endpoint returned an error envelope")
        content = self._content(decoded)
        return ModelResponse(request_id=request.request_id, status="ok", response_text=content)


TrustedModelProvider = TrustedModelExecutor
DirectModelExecutor = TrustedModelExecutor


def make_trusted_model_executor(
    binding: ModelBinding,
    *,
    lane: str,
    manifest_identity: str,
    subset_identity: str,
    selected: bool,
    provider: str = TRUSTED_ZEN_PROVIDER,
    endpoint: Optional[str] = None,
    paid: bool = False,
    timeout_seconds: float = 60.0,
    max_tokens: int = 4096,
) -> TrustedModelExecutor:
    return TrustedModelExecutor.from_binding(
        binding,
        lane=lane,
        manifest_identity=manifest_identity,
        subset_identity=subset_identity,
        selected=selected,
        provider=provider,
        endpoint=endpoint,
        paid=paid,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
    )


__all__ = [
    "DEFAULT_LOCAL_ENDPOINT",
    "DEFAULT_LOCAL_MODEL",
    "DEFAULT_ZEN_ENDPOINT",
    "DEFAULT_ZEN_MODEL",
    "DirectModelExecutor",
    "MODEL_EXECUTOR_PROTOCOL",
    "ModelExecutorBindingError",
    "ModelExecutorError",
    "ModelExecutorPreflight",
    "TRUSTED_LOCAL_PROVIDER",
    "TRUSTED_PROVIDERS",
    "TRUSTED_ZEN_PROVIDER",
    "TrustedModelExecutor",
    "TrustedModelProvider",
    "make_trusted_model_executor",
]
