"""Trusted subprocess execution for the vendored decomp-permuter.

The permuter lane records are deliberately independent from the historical
``permuter_import`` command.  That command prepares a directory in
``nonmatchings`` from mutable source and build state, which is not a safe
production provider input.  This module consumes one typed
:class:`PermuterRequest`, verifies every archive and tool binding, and runs the
vendored runner only in an identity-derived directory below the run archive.

The request schema contains source and target assembly evidence, but the
vendored runner also needs a target object and a compile script.  A production
factory may provide those as an immutable :class:`PermuterRuntimeBinding`.
When it does not, the executor runs the real runner preflight and returns a
typed, platform-specific unavailable result explaining the missing binding.
It never falls back to a callback, a checkout path, or a fabricated candidate.
"""

from __future__ import annotations

import json
import math
import os
import queue
import re
import signal
import shutil
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from types import MappingProxyType

try:
    from .search_archive import ArchiveError, ContentAddressedArchive
    from .search_permuter_lanes import (
        PERMUTER_CHECKPOINT_PROTOCOL,
        PERMUTER_CONFIG_PROTOCOL,
        PERMUTER_MAX_CANDIDATE_CHARS,
        PERMUTER_MAX_ITERATIONS,
        PermuterCheckpoint,
        PermuterHandoffStore,
        PermuterProviderError,
        PermuterProviderInputError,
        PermuterProviderInvalidResponse,
        PermuterProviderRefused,
        PermuterProviderTimeout,
        PermuterProviderUnavailable,
        PermuterRequest,
        PermuterToolBinding,
        _artifact_identity,
    )
    from .search_types import (
        ArtifactRef,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_relative_path,
    )
except ImportError:  # pragma: no cover - direct invocation compatibility
    from search_archive import ArchiveError, ContentAddressedArchive  # type: ignore
    from search_permuter_lanes import (  # type: ignore
        PERMUTER_CHECKPOINT_PROTOCOL,
        PERMUTER_CONFIG_PROTOCOL,
        PERMUTER_MAX_CANDIDATE_CHARS,
        PERMUTER_MAX_ITERATIONS,
        PermuterCheckpoint,
        PermuterHandoffStore,
        PermuterProviderError,
        PermuterProviderInputError,
        PermuterProviderInvalidResponse,
        PermuterProviderRefused,
        PermuterProviderTimeout,
        PermuterProviderUnavailable,
        PermuterRequest,
        PermuterToolBinding,
        _artifact_identity,
    )
    from search_types import (  # type: ignore
        ArtifactRef,
        canonical_bytes,
        hash_bytes,
        hash_canonical,
        validate_hash,
        validate_relative_path,
    )


EXECUTOR_PROTOCOL = "sotn-permuter-executor-v1"
RUNTIME_PROTOCOL = "sotn-permuter-runtime-v1"
PREFLIGHT_PROTOCOL = "sotn-permuter-preflight-v1"
STATE_PROTOCOL = "sotn-permuter-executor-state-v1"
VENDOR_REVISION_PROTOCOL = "sotn-decomp-permuter-vendor-tree-v1"
MODULE_IDENTITY = hash_canonical(
    {
        "module": "automation.search_permuter_executor",
        "protocol": EXECUTOR_PROTOCOL,
        "version": "1.0.0",
    }
)

_VENDOR_RELATIVE_ROOT = Path("tools") / "decomp-permuter"
_RUNNER_RELATIVE_PATH = Path("tools") / "decomp-permuter" / "permuter.py"
_WEIGHTS_RELATIVE_PATH = Path("tools") / "decomp-permuter" / "default_weights.toml"
_RUNNER_HELP_FLAG = "--help=randomization-passes"
_RUNNER_HELP_MARKER = "perm_"
_ALGORITHM_MAP = {
    # The lane algorithm is the immutable strategy identity.  The vendored
    # runner's scorer accepts only these two names, so this translation is
    # explicit and identity-bearing rather than silently passing an invalid
    # lane name to its parser.
    "random": "difflib",
    "targeted": "difflib",
    "recombine": "difflib",
    "ddmin": "difflib",
    "difflib": "difflib",
    "levenshtein": "levenshtein",
}
_COMPILER_TYPES = frozenset({"base", "ido", "mwcc", "gcc"})
_PLATFORM_POSIX = "native-posix"
_PLATFORM_WSL = "windows-wsl"
_MAX_TIMEOUT_SECONDS = 3600.0
_PREFLIGHT_TIMEOUT_SECONDS = 30.0
_MAX_OUTPUT_BYTES = 16 * 1024 * 1024
_MAX_SOURCE_BYTES = PERMUTER_MAX_CANDIDATE_CHARS
_OUTPUT_DIR_RE = re.compile(r"^output-((?:[0-9]+(?:\.[0-9]+)?|inf))-([0-9]+)$", re.IGNORECASE)
_ITERATION_RE = re.compile(r"\biteration\s+(\d+)\s*,")
_SCORE_RE = re.compile(r"\bscore\s*=\s*(-?(?:\d+(?:\.\d+)?|inf))\b", re.I)

# The vendored runner has one compiler-wrapper entry point.  Its bytes and the
# structured invocation are repository-owned constants, not authority granted
# by a caller-provided executable or shell body.  The wrapper is intentionally
# tiny because the runner supplies exactly ``input.c -o output.o``.
_COMPILER_DRIVER_PATH = Path(__file__).with_name("search_compile_driver.py")
_COMPILER_CORPUS_PATH = Path(__file__).with_name("compiler_corpus.py")
_COMPILER_DRIVER_IDENTITY = hash_bytes(_COMPILER_DRIVER_PATH.read_bytes())
_COMPILER_CORPUS_IDENTITY = hash_bytes(_COMPILER_CORPUS_PATH.read_bytes())
_STRATEGY_WORKER_IDENTITY = hash_bytes(Path(__file__).with_name("search_permuter_worker.py").read_bytes())
_MUTATIONS_IDENTITY = hash_bytes(Path(__file__).with_name("search_mutations.py").read_bytes())
_SOURCE_CONTEXT_IDENTITY = hash_bytes(Path(__file__).with_name("search_source_context.py").read_bytes())
_PROCESS_LOCK_IDENTITY = hash_bytes(Path(__file__).with_name("search_process_lock.py").read_bytes())
REPOSITORY_COMPILE_WRAPPER_BYTES = (
    '#!/bin/sh\n'
    '# driver ' + _COMPILER_DRIVER_IDENTITY + '\n'
    '# pipeline ' + _COMPILER_CORPUS_IDENTITY + '\n'
    '# strategies ' + _STRATEGY_WORKER_IDENTITY + '\n'
    '# patches ' + _MUTATIONS_IDENTITY + '\n'
    '# source-context ' + _SOURCE_CONTEXT_IDENTITY + '\n'
    '# process-lock ' + _PROCESS_LOCK_IDENTITY + '\n'
    'exec python3 "${SOTN_REPO_ROOT:?}/automation/search_compile_driver.py" "$@"\n'
).encode("utf-8")
REPOSITORY_COMPILE_WRAPPER_IDENTITY = hash_bytes(REPOSITORY_COMPILE_WRAPPER_BYTES)
REPOSITORY_COMPILER_EXECUTABLE = "python3"
REPOSITORY_COMPILER_ARGV_TEMPLATE = ("{input}", "-o", "{output}")
REPOSITORY_COMPILER_ENVIRONMENT = (
    ("LANG", "C"),
    ("LC_ALL", "C"),
    ("PATH", "/usr/bin:/bin"),
)
REPOSITORY_COMPILER_INPUT_LOCATION = "argv[0]"
REPOSITORY_COMPILER_OUTPUT_LOCATION = "argv[2]"


class PermuterExecutorError(PermuterProviderError):
    """Base class for trusted executor failures."""


class PermuterExecutorInputError(PermuterProviderInputError, PermuterExecutorError):
    """A request, immutable binding, or runtime bundle is invalid."""


class PermuterExecutorUnavailable(PermuterProviderUnavailable, PermuterExecutorError):
    """The real vendored runner cannot be used on this platform or input."""

    code = "permuter_executor_unavailable"

    def __init__(self, reason: str, code: Optional[str] = None) -> None:
        super().__init__(reason)
        if code:
            self.code = code


class PermuterExecutorRefused(PermuterProviderRefused, PermuterExecutorError):
    """The runner rejected a trusted, bounded request."""

    code = "permuter_executor_refused"

    def __init__(self, reason: str, code: Optional[str] = None) -> None:
        super().__init__(reason, code=code)


class PermuterExecutorTimeout(PermuterProviderTimeout, PermuterExecutorError):
    """The bounded runner process exceeded its timeout."""


class PermuterExecutorInvalidResponse(
    PermuterProviderInvalidResponse, PermuterExecutorError
):
    """The runner output was not a bounded candidate response."""


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if isinstance(value, ArtifactRef):
        return value.to_dict()
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _plain(value.to_dict())
    return value


def _identity(value: Any, label: str) -> str:
    try:
        return validate_hash(value, label)
    except (TypeError, ValueError) as exc:
        raise PermuterExecutorInputError(f"{label} must be a sha256 identity") from exc


def _text(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        raise PermuterExecutorInputError(f"{label} must be nonempty text")
    return value


def _bytes(value: Any, label: str, maximum: int, *, binary: bool = False) -> bytes:
    if not isinstance(value, bytes) or not value:
        raise PermuterExecutorInputError(f"{label} must be nonempty bytes")
    if len(value) > maximum:
        raise PermuterExecutorInputError(f"{label} exceeds its immutable bound")
    if not binary and b"\x00" in value:
        raise PermuterExecutorInputError(f"{label} contains NUL bytes")
    return value


def _compiler_environment(value: Any) -> tuple[tuple[str, str], ...]:
    if isinstance(value, Mapping):
        items = tuple(sorted(value.items()))
    elif isinstance(value, (tuple, list)):
        items = tuple(value)
    else:
        raise PermuterExecutorInputError("compiler environment must be a mapping")
    normalized: list[tuple[str, str]] = []
    for item in items:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise PermuterExecutorInputError("compiler environment entries must be pairs")
        key, value_item = item
        if not isinstance(key, str) or not isinstance(value_item, str):
            raise PermuterExecutorInputError("compiler environment entries must be text")
        normalized.append((key, value_item))
    result = tuple(sorted(normalized))
    if len({key for key, _value in result}) != len(result):
        raise PermuterExecutorInputError("compiler environment has duplicate keys")
    return result


def _safe_artifact(value: Any, label: str) -> ArtifactRef:
    try:
        item = value if isinstance(value, ArtifactRef) else ArtifactRef.from_dict(value)
    except Exception as exc:  # typed boundary below
        raise PermuterExecutorInputError(f"{label} is not an ArtifactRef") from exc
    if "\\" in item.path or not item.path.startswith("artifacts/"):
        raise PermuterExecutorInputError(
            f"{label} must use an archive-relative artifacts path"
        )
    return item


def _safe_component_path(root: Path, relative: str, label: str) -> Path:
    try:
        validate_relative_path(relative, label)
    except Exception as exc:
        raise PermuterExecutorInputError(f"{label} is not a safe relative path") from exc
    if "\\" in relative:
        raise PermuterExecutorInputError(f"{label} must use POSIX separators")
    candidate = root / Path(relative)
    try:
        resolved_root = root.resolve(strict=False)
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise PermuterExecutorInputError(f"{label} escaped the archive run root") from exc
    return resolved


def _strict_mapping(
    value: Any,
    required: Sequence[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PermuterExecutorInputError(f"{label} must be an object")
    data = dict(value)
    if any(not isinstance(key, str) for key in data):
        raise PermuterExecutorInputError(f"{label} keys must be text")
    required_set = set(required)
    missing = required_set.difference(data)
    unknown = set(data).difference(required_set)
    if missing:
        raise PermuterExecutorInputError(
            f"{label} is missing fields: " + ", ".join(sorted(missing))
        )
    if unknown:
        raise PermuterExecutorInputError(
            f"{label} has unknown fields: " + ", ".join(sorted(unknown))
        )
    return data


def _artifact_bytes(
    archive: ContentAddressedArchive, reference: ArtifactRef, expected: bytes, label: str
) -> bytes:
    try:
        actual = archive.verify(reference)
    except (ArchiveError, OSError, ValueError) as exc:
        raise PermuterExecutorInputError(f"{label} is missing or corrupt") from exc
    if actual != expected:
        raise PermuterExecutorInputError(f"{label} bytes differ from its archive artifact")
    return actual


def _regular_file(path: Path, label: str) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            raise OSError("not a regular file")
        return path.read_bytes()
    except OSError as exc:
        raise PermuterExecutorUnavailable(f"{label} is unavailable") from exc


def _candidate_file(path: Path, label: str) -> bytes:
    """Read a runner-produced file, classifying malformed output as invalid."""

    try:
        if path.is_symlink() or not path.is_file():
            raise OSError("not a regular file")
        return path.read_bytes()
    except OSError as exc:
        raise PermuterExecutorInvalidResponse(f"{label} is unavailable") from exc


def _vendor_files(root: Path) -> tuple[tuple[str, bytes], ...]:
    """Return regular vendored files, refusing symlinks and cache trees."""

    if root.is_symlink() or not root.is_dir():
        raise PermuterExecutorUnavailable("pinned decomp-permuter root is unavailable")
    ignored = {".git", "__pycache__", ".mypy_cache", ".pytest_cache"}
    files: list[tuple[str, bytes]] = []
    try:
        paths = sorted(root.rglob("*"), key=lambda item: item.as_posix())
    except OSError as exc:
        raise PermuterExecutorUnavailable("pinned decomp-permuter tree cannot be listed") from exc
    for path in paths:
        if any(part in ignored for part in path.relative_to(root).parts):
            continue
        if path.is_symlink():
            raise PermuterExecutorUnavailable("pinned decomp-permuter tree contains a symlink")
        if path.is_file():
            files.append((path.relative_to(root).as_posix(), _regular_file(path, "vendored file")))
        elif not path.is_dir():
            raise PermuterExecutorUnavailable("pinned decomp-permuter tree contains a special file")
    if not files:
        raise PermuterExecutorUnavailable("pinned decomp-permuter tree is empty")
    return tuple(files)


def _vendor_manifest_from_files(
    files: Sequence[tuple[str, bytes]],
) -> dict[str, Any]:
    """Build a vendor manifest from one already-read immutable snapshot."""

    return {
        "protocol": VENDOR_REVISION_PROTOCOL,
        "root": _VENDOR_RELATIVE_ROOT.as_posix(),
        "files": [
            {"path": path, "content_hash": hash_bytes(data), "byte_size": len(data)}
            for path, data in files
        ],
    }


def vendored_tree_manifest(root: str | os.PathLike[str]) -> dict[str, Any]:
    """Describe the pinned vendored tree without exposing a machine path."""

    resolved = Path(root).resolve(strict=False)
    return _vendor_manifest_from_files(_vendor_files(resolved))


def vendored_tree_identity(root: str | os.PathLike[str]) -> str:
    """Return the exact content identity accepted as ``vendor_revision``."""

    return hash_canonical(vendored_tree_manifest(root))


def vendored_runner_identity(root: str | os.PathLike[str]) -> str:
    """Return the content identity of the fixed ``permuter.py`` entrypoint."""

    resolved = Path(root).resolve(strict=False)
    return hash_bytes(_regular_file(resolved / "permuter.py", "vendored runner"))


def _runtime_identity(
    *,
    evaluator_identity: str,
    compile_script_artifact: ArtifactRef,
    target_object_artifact: Optional[ArtifactRef],
    compiler_type: str,
    function_name: Optional[str],
    compiler_executable: str,
    compiler_argv_template: Sequence[str],
    compiler_environment: Sequence[tuple[str, str]],
    input_location: str,
    output_location: str,
    wrapper_identity: str,
) -> str:
    return hash_canonical(
        {
            "protocol": RUNTIME_PROTOCOL,
            "evaluator_identity": evaluator_identity,
            "compile_script_artifact": _artifact_identity(compile_script_artifact),
            "target_object_artifact": (
                _artifact_identity(target_object_artifact)
                if target_object_artifact is not None
                else None
            ),
            "compiler_type": compiler_type,
            "function_name": function_name,
            "compiler_executable": compiler_executable,
            "compiler_argv_template": list(compiler_argv_template),
            "compiler_environment": dict(compiler_environment),
            "input_location": input_location,
            "output_location": output_location,
            "wrapper_identity": wrapper_identity,
        }
    )


@dataclass(frozen=True)
class PermuterRuntimeBinding:
    """Archive-owned runner inputs omitted from the lane request itself.

    ``compile_script_bytes`` must invoke the compiler in its current working
    directory and consume the source/object arguments supplied by the vendored
    compiler wrapper.  It is materialized below the request scratch directory;
    no command is inherited from the checkout.  ``target_object_*`` is optional
    only when the request target artifact is itself an object file.
    """

    evaluator_identity: str
    compile_script_artifact: ArtifactRef
    compile_script_bytes: bytes
    compiler_type: str = "base"
    function_name: Optional[str] = None
    target_object_artifact: Optional[ArtifactRef] = None
    target_object_bytes: Optional[bytes] = None
    compiler_executable: str = REPOSITORY_COMPILER_EXECUTABLE
    compiler_argv_template: tuple[str, ...] = REPOSITORY_COMPILER_ARGV_TEMPLATE
    compiler_environment: tuple[tuple[str, str], ...] = REPOSITORY_COMPILER_ENVIRONMENT
    input_location: str = REPOSITORY_COMPILER_INPUT_LOCATION
    output_location: str = REPOSITORY_COMPILER_OUTPUT_LOCATION
    wrapper_identity: str = REPOSITORY_COMPILE_WRAPPER_IDENTITY

    def __post_init__(self) -> None:
        object.__setattr__(self, "evaluator_identity", _identity(self.evaluator_identity, "runtime evaluator identity"))
        object.__setattr__(
            self,
            "compile_script_artifact",
            _safe_artifact(self.compile_script_artifact, "compile script artifact"),
        )
        object.__setattr__(
            self,
            "compile_script_bytes",
            _bytes(self.compile_script_bytes, "compile script", 128 * 1024),
        )
        if self.compiler_type not in _COMPILER_TYPES:
            raise PermuterExecutorInputError("runtime compiler type is not supported")
        if self.function_name is not None:
            object.__setattr__(self, "function_name", _text(self.function_name, "runtime function name"))
        if self.target_object_artifact is not None:
            object.__setattr__(
                self,
                "target_object_artifact",
                _safe_artifact(self.target_object_artifact, "target object artifact"),
            )
        if self.target_object_artifact is None and self.target_object_bytes is not None:
            raise PermuterExecutorInputError(
                "target object bytes need a target object artifact"
            )
        if self.target_object_artifact is not None and self.target_object_bytes is not None:
            object.__setattr__(
                self,
                "target_object_bytes",
                _bytes(self.target_object_bytes, "target object", 16 * 1024 * 1024, binary=True),
            )
            if hash_bytes(self.target_object_bytes) != self.target_object_artifact.content_hash:
                raise PermuterExecutorInputError("target object differs from its artifact")
            if len(self.target_object_bytes) != self.target_object_artifact.byte_size:
                raise PermuterExecutorInputError("target object size differs from its artifact")
        if self.compiler_executable != REPOSITORY_COMPILER_EXECUTABLE:
            raise PermuterExecutorInputError("compiler executable is not repository-owned")
        try:
            argv_template = tuple(self.compiler_argv_template)
        except TypeError as exc:
            raise PermuterExecutorInputError("compiler argv template must be a sequence") from exc
        if argv_template != REPOSITORY_COMPILER_ARGV_TEMPLATE:
            raise PermuterExecutorInputError("compiler argv template is not repository-owned")
        object.__setattr__(self, "compiler_argv_template", argv_template)
        environment = _compiler_environment(self.compiler_environment)
        if environment != REPOSITORY_COMPILER_ENVIRONMENT:
            raise PermuterExecutorInputError("compiler environment is not repository-owned")
        object.__setattr__(self, "compiler_environment", environment)
        if self.input_location != REPOSITORY_COMPILER_INPUT_LOCATION:
            raise PermuterExecutorInputError("compiler input location is not repository-owned")
        if self.output_location != REPOSITORY_COMPILER_OUTPUT_LOCATION:
            raise PermuterExecutorInputError("compiler output location is not repository-owned")
        object.__setattr__(self, "wrapper_identity", _identity(self.wrapper_identity, "wrapper_identity"))
        if self.wrapper_identity != REPOSITORY_COMPILE_WRAPPER_IDENTITY:
            raise PermuterExecutorInputError("compile wrapper identity is not repository-owned")
        self._validate_compile_script()

    def _validate_compile_script(self) -> None:
        if self.compile_script_bytes != REPOSITORY_COMPILE_WRAPPER_BYTES:
            raise PermuterExecutorInputError(
                "compile wrapper bytes are not the repository-owned immutable wrapper"
            )
        if self.compile_script_artifact.content_hash != REPOSITORY_COMPILE_WRAPPER_IDENTITY:
            raise PermuterExecutorInputError(
                "compile wrapper artifact is not the repository-owned immutable wrapper"
            )
        if self.compile_script_artifact.byte_size != len(REPOSITORY_COMPILE_WRAPPER_BYTES):
            raise PermuterExecutorInputError("compile wrapper artifact size is not canonical")

    @property
    def runtime_identity(self) -> str:
        return _runtime_identity(
            evaluator_identity=self.evaluator_identity,
            compile_script_artifact=self.compile_script_artifact,
            target_object_artifact=self.target_object_artifact,
            compiler_type=self.compiler_type,
            function_name=self.function_name,
            compiler_executable=self.compiler_executable,
            compiler_argv_template=self.compiler_argv_template,
            compiler_environment=self.compiler_environment,
            input_location=self.input_location,
            output_location=self.output_location,
            wrapper_identity=self.wrapper_identity,
        )

    def verify(self, archive: ContentAddressedArchive) -> None:
        _artifact_bytes(
            archive,
            self.compile_script_artifact,
            self.compile_script_bytes,
            "compile script artifact",
        )
        if self.target_object_artifact is not None:
            if self.target_object_bytes is None:
                raise PermuterExecutorUnavailable("target object bytes are not bound")
            _artifact_bytes(
                archive,
                self.target_object_artifact,
                self.target_object_bytes,
                "target object artifact",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": RUNTIME_PROTOCOL,
            "evaluator_identity": self.evaluator_identity,
            "compile_script_artifact": _artifact_identity(self.compile_script_artifact),
            "compile_script_identity": self.compile_script_artifact.content_hash,
            "compiler_type": self.compiler_type,
            "function_name": self.function_name,
            "compiler_executable": self.compiler_executable,
            "compiler_argv_template": list(self.compiler_argv_template),
            "compiler_environment": dict(self.compiler_environment),
            "input_location": self.input_location,
            "output_location": self.output_location,
            "wrapper_identity": self.wrapper_identity,
            "target_object_artifact": (
                _artifact_identity(self.target_object_artifact)
                if self.target_object_artifact is not None
                else None
            ),
            "target_object_identity": (
                self.target_object_artifact.content_hash
                if self.target_object_artifact is not None
                else None
            ),
            "runtime_identity": self.runtime_identity,
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        archive: Optional[ContentAddressedArchive] = None,
    ) -> "PermuterRuntimeBinding":
        """Reconstruct runtime inputs only from their verified archive artifacts."""

        data = _strict_mapping(
            value,
            (
                "protocol",
                "evaluator_identity",
                "compile_script_artifact",
                "compile_script_identity",
                "compiler_type",
                "function_name",
                "compiler_executable",
                "compiler_argv_template",
                "compiler_environment",
                "input_location",
                "output_location",
                "wrapper_identity",
                "target_object_artifact",
                "target_object_identity",
                "runtime_identity",
            ),
            "permuter runtime binding",
        )
        if data["protocol"] != RUNTIME_PROTOCOL:
            raise PermuterExecutorInputError("runtime binding protocol differs")
        if not isinstance(archive, ContentAddressedArchive):
            raise PermuterExecutorUnavailable(
                "runtime binding reconstruction needs its archive",
                code="permuter_runtime_archive_unavailable",
            )
        compile_script_artifact = _safe_artifact(
            data["compile_script_artifact"], "compile script artifact"
        )
        if data["compile_script_identity"] != compile_script_artifact.content_hash:
            raise PermuterExecutorInputError("compile script identity changed")
        try:
            compile_script_bytes = archive.verify(compile_script_artifact)
        except (ArchiveError, OSError, ValueError) as exc:
            raise PermuterExecutorUnavailable(
                "compile script artifact is absent or corrupt",
                code="permuter_runtime_artifact_unavailable",
            ) from exc
        target_object_artifact = data["target_object_artifact"]
        target_object_ref = (
            _safe_artifact(target_object_artifact, "target object artifact")
            if target_object_artifact is not None
            else None
        )
        if data["target_object_identity"] != (
            target_object_ref.content_hash if target_object_ref is not None else None
        ):
            raise PermuterExecutorInputError("target object identity changed")
        target_object_bytes = None
        if target_object_ref is not None:
            try:
                target_object_bytes = archive.verify(target_object_ref)
            except (ArchiveError, OSError, ValueError) as exc:
                raise PermuterExecutorUnavailable(
                    "target object artifact is absent or corrupt",
                    code="permuter_runtime_artifact_unavailable",
                ) from exc
        item = cls(
            evaluator_identity=data["evaluator_identity"],
            compile_script_artifact=compile_script_artifact,
            compile_script_bytes=compile_script_bytes,
            compiler_type=data["compiler_type"],
            function_name=data["function_name"],
            compiler_executable=data["compiler_executable"],
            compiler_argv_template=tuple(data["compiler_argv_template"]),
            compiler_environment=data["compiler_environment"],
            input_location=data["input_location"],
            output_location=data["output_location"],
            wrapper_identity=data["wrapper_identity"],
            target_object_artifact=target_object_ref,
            target_object_bytes=target_object_bytes,
        )
        if data["runtime_identity"] != item.runtime_identity:
            raise PermuterExecutorInputError("runtime binding identity changed")
        return item


@dataclass(frozen=True)
class PermuterPreflight:
    """Deterministic typed report from the real runner preflight."""

    status: str
    request_identity: str
    platform: str
    runner_identity: str
    vendor_revision: str
    tool_identity: str
    weights_identity: str
    runtime_identity: Optional[str]
    reason: str = ""
    refusal_code: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status not in {"ready", "unavailable"}:
            raise PermuterExecutorInputError("preflight status is invalid")
        _identity(self.request_identity, "preflight request identity")
        _identity(self.runner_identity, "preflight runner identity")
        _identity(self.vendor_revision, "preflight vendor revision")
        _identity(self.tool_identity, "preflight tool identity")
        _identity(self.weights_identity, "preflight weights identity")
        if self.runtime_identity is not None:
            _identity(self.runtime_identity, "preflight runtime identity")
        _text(self.reason, "preflight reason", allow_empty=True)
        if self.refusal_code is not None:
            _text(self.refusal_code, "preflight refusal code")

    @property
    def ready(self) -> bool:
        return self.status == "ready"

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": PREFLIGHT_PROTOCOL,
            "status": self.status,
            "request_identity": self.request_identity,
            "platform": self.platform,
            "runner_identity": self.runner_identity,
            "vendor_revision": self.vendor_revision,
            "tool_identity": self.tool_identity,
            "weights_identity": self.weights_identity,
            "runtime_identity": self.runtime_identity,
            "reason": self.reason,
            "refusal_code": self.refusal_code,
        }


def _derived_scratch_identity(request: PermuterRequest) -> str:
    session_identity = hash_canonical(
        {
            "provider_identity": request.provider_identity,
            "recipient_id": request.recipient_id,
            "input_identity": request.input_identity,
        }
    )
    return hash_canonical(
        {
            "protocol": "sotn-permuter-scratch-v1",
            "lane": request.lane,
            "session_identity": session_identity,
            "seed_identity": request.seed_identity,
            "target_artifact_identity": request.target_artifact_identity,
            "tool_identity": request.tool_identity,
            "weights_identity": request.weights_identity,
            "algorithm_identity": request.algorithm_identity,
        }
    )


def _stable_seed(request: PermuterRequest) -> int:
    digest = request.seed_identity.removeprefix("sha256:")
    # The vendored CLI accepts a decimal Python integer.  Keeping this below
    # 10**20 also matches the randomizer's own rng_seed range.
    return int(digest[:16], 16) % (10**20 - 1) + 1


def _function_name(recipient_id: str) -> str:
    pieces = recipient_id.split(":", 2)
    if len(pieces) != 3 or not pieces[2]:
        raise PermuterExecutorInputError("recipient id does not carry a function name")
    name = pieces[2]
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise PermuterExecutorInputError("recipient function name is not a C identifier")
    return name


def _number_from_score(value: str) -> Optional[float]:
    if value.lower() == "inf":
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


class PermuterExecutor:
    """A factory-bound callable for the real vendored decomp-permuter."""

    def __init__(
        self,
        archive: ContentAddressedArchive,
        binding: PermuterToolBinding,
        *,
        runtime: Optional[PermuterRuntimeBinding] = None,
        runtimes: Optional[Mapping[str, PermuterRuntimeBinding]] = None,
        repo_root: Optional[str | os.PathLike[str]] = None,
        timeout_seconds: float = 300.0,
    ) -> None:
        if not isinstance(archive, ContentAddressedArchive):
            raise PermuterExecutorInputError("executor archive must be a ContentAddressedArchive")
        if not isinstance(binding, PermuterToolBinding):
            raise PermuterExecutorInputError("executor binding must be a PermuterToolBinding")
        if runtime is not None and not isinstance(runtime, PermuterRuntimeBinding):
            raise PermuterExecutorInputError("executor runtime must be a PermuterRuntimeBinding")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise PermuterExecutorInputError("executor timeout must be numeric")
        timeout = float(timeout_seconds)
        if not math.isfinite(timeout) or timeout <= 0 or timeout > _MAX_TIMEOUT_SECONDS:
            raise PermuterExecutorInputError("executor timeout is outside its bound")
        self.archive = archive
        self.binding = binding
        self.runtime = runtime
        routes = dict(runtimes or {})
        if routes and runtime is not None:
            raise PermuterExecutorInputError("executor cannot mix a single runtime with recipient routes")
        for recipient, bound_runtime in routes.items():
            if not isinstance(recipient, str) or not isinstance(bound_runtime, PermuterRuntimeBinding):
                raise PermuterExecutorInputError("runtime routes must bind recipients to typed runtimes")
            if bound_runtime.function_name != recipient.split(":")[-1]:
                raise PermuterExecutorInputError("routed runtime function differs from recipient")
            bound_runtime.verify(archive)
        self.runtimes = MappingProxyType(dict(sorted(routes.items())))
        if repo_root is None:
            root = Path(__file__).resolve().parents[1]
        else:
            root = Path(repo_root)
        try:
            root = root.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise PermuterExecutorInputError("executor repository root cannot be resolved") from exc
        if root.is_symlink() or not root.is_dir():
            raise PermuterExecutorInputError("executor repository root must be a real directory")
        self.repo_root = root
        self.vendor_root = root / _VENDOR_RELATIVE_ROOT
        self.timeout_seconds = timeout
        self._runner_identity: Optional[str] = None
        self._vendor_revision: Optional[str] = None
        self._vendor_snapshot: Optional[tuple[tuple[str, bytes], ...]] = None

    @property
    def platform(self) -> str:
        return _PLATFORM_WSL if os.name == "nt" else _PLATFORM_POSIX

    @property
    def runner_identity(self) -> str:
        if self._runner_identity is None:
            self._runner_identity = vendored_runner_identity(self.vendor_root)
        return self._runner_identity

    @property
    def vendor_revision(self) -> str:
        if self._vendor_revision is None:
            self._vendor_revision = vendored_tree_identity(self.vendor_root)
        return self._vendor_revision

    @property
    def identity(self) -> str:
        return hash_canonical(
            {
                "protocol": EXECUTOR_PROTOCOL,
                "module_identity": MODULE_IDENTITY,
                "runner_relative_path": _RUNNER_RELATIVE_PATH.as_posix(),
                "weights_relative_path": _WEIGHTS_RELATIVE_PATH.as_posix(),
                "runner_identity": self.runner_identity,
                "vendor_revision": self.vendor_revision,
                "binding_identity": self.binding.identity,
                "runtime_identity": self.runtime.runtime_identity if self.runtime else None,
                **({"runtime_routes": {key: value.runtime_identity for key, value in self.runtimes.items()}} if self.runtimes else {}),
                "platform": self.platform,
                "timeout_seconds": self.timeout_seconds,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": EXECUTOR_PROTOCOL,
            "module_identity": MODULE_IDENTITY,
            "runner_relative_path": _RUNNER_RELATIVE_PATH.as_posix(),
            "weights_relative_path": _WEIGHTS_RELATIVE_PATH.as_posix(),
            "runner_identity": self.runner_identity,
            "vendor_revision": self.vendor_revision,
            "binding": self.binding.to_dict(),
            "runtime": self.runtime.to_dict() if self.runtime else None,
            **({"runtime_routes": {key: value.to_dict() for key, value in self.runtimes.items()}} if self.runtimes else {}),
            "executor_identity": self.identity,
            "platform": self.platform,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        archive: ContentAddressedArchive,
        repo_root: Optional[str | os.PathLike[str]] = None,
    ) -> "PermuterExecutor":
        """Reconstruct an executor from immutable archive-backed bindings.

        The checkout is used only to locate the fixed vendored source tree.
        Its runner and weight bytes are rechecked against the archived binding
        before this method accepts the serialized executor identity.  No
        command, callback, or filesystem path is restored from the document.
        """

        data = _strict_mapping(
            value,
            (
                "protocol",
                "module_identity",
                "runner_relative_path",
                "weights_relative_path",
                "runner_identity",
                "vendor_revision",
                "binding",
                "runtime",
                "executor_identity",
                "platform",
                "timeout_seconds",
                *(("runtime_routes",) if "runtime_routes" in value else ()),
            ),
            "permuter executor",
        )
        if data["protocol"] != EXECUTOR_PROTOCOL:
            raise PermuterExecutorInputError("executor protocol differs")
        if data["module_identity"] != MODULE_IDENTITY:
            raise PermuterExecutorInputError("executor module identity differs")
        if data["runner_relative_path"] != _RUNNER_RELATIVE_PATH.as_posix():
            raise PermuterExecutorInputError("executor runner path differs")
        if data["weights_relative_path"] != _WEIGHTS_RELATIVE_PATH.as_posix():
            raise PermuterExecutorInputError("executor weights path differs")
        if data["platform"] not in {_PLATFORM_POSIX, _PLATFORM_WSL}:
            raise PermuterExecutorInputError("executor platform is invalid")
        if not isinstance(archive, ContentAddressedArchive):
            raise PermuterExecutorInputError("executor reconstruction needs its archive")
        try:
            binding = PermuterToolBinding.from_dict(data["binding"], archive=archive)
        except PermuterProviderError:
            raise
        runtime_value = data["runtime"]
        if runtime_value is None:
            runtime = None
        else:
            runtime = PermuterRuntimeBinding.from_dict(runtime_value, archive=archive)
        routes = data.get("runtime_routes", {})
        if not isinstance(routes, Mapping) or ("runtime_routes" in data and not routes):
            raise PermuterExecutorInputError("runtime routes must be a nonempty mapping when present")
        runtimes = {
            key: PermuterRuntimeBinding.from_dict(item, archive=archive)
            for key, item in routes.items()
        }
        executor = cls(
            archive,
            binding,
            runtime=runtime,
            runtimes=runtimes,
            repo_root=repo_root,
            timeout_seconds=data["timeout_seconds"],
        )
        if data["platform"] != executor.platform:
            raise PermuterExecutorInputError("executor platform differs")
        if data["runner_identity"] != executor.runner_identity:
            raise PermuterExecutorInputError("executor runner identity changed")
        if data["vendor_revision"] != executor.vendor_revision:
            raise PermuterExecutorInputError("executor vendor revision changed")
        if data["executor_identity"] != executor.identity:
            raise PermuterExecutorInputError("executor identity changed")
        return executor

    def _verify_request(self, request: PermuterRequest) -> tuple[bytes, bytes]:
        if not isinstance(request, PermuterRequest):
            raise PermuterExecutorInputError("executor accepts only a typed PermuterRequest")
        if request.algorithm not in _ALGORITHM_MAP:
            raise PermuterExecutorInputError("request lane algorithm has no vendored translation")
        if _derived_scratch_identity(request) != request.scratch_identity:
            raise PermuterExecutorInputError("request scratch identity changed")
        expected_path = (
            "permuter-scratch/"
            + request.lane
            + "/"
            + request.scratch_identity.removeprefix("sha256:")
        )
        if request.scratch_path != expected_path:
            raise PermuterExecutorInputError("request scratch path is not identity-derived")
        scratch = _safe_component_path(self.archive.run_root, request.scratch_path, "scratch path")
        del scratch
        if request.phase == "start" and request.prior_checkpoint_identity is not None:
            raise PermuterExecutorInputError("start request unexpectedly carries a checkpoint")
        if request.phase == "resume" and request.prior_checkpoint_identity is None:
            raise PermuterExecutorInputError("resume request has no prior checkpoint identity")
        if request.start_iteration > request.max_iterations:
            raise PermuterExecutorRefused(
                "request has no remaining iteration budget",
                code="permuter_iteration_budget_exhausted",
            )
        if request.max_iterations > PERMUTER_MAX_ITERATIONS:
            raise PermuterExecutorInputError(
                "request iteration budget exceeds the global permuter bound"
            )
        if request.seed_artifact.path == request.target_artifact.path:
            raise PermuterExecutorInputError("seed and target artifacts must be distinct")
        seed_bytes = _artifact_bytes(
            self.archive,
            _safe_artifact(request.seed_artifact, "request seed artifact"),
            request.seed_source.encode("utf-8"),
            "request seed artifact",
        )
        target_bytes = _artifact_bytes(
            self.archive,
            _safe_artifact(request.target_artifact, "request target artifact"),
            request.target_assembly.encode("utf-8"),
            "request target artifact",
        )
        if hash_bytes(seed_bytes) != request.seed_identity:
            raise PermuterExecutorInputError("request seed identity changed")
        if hash_bytes(target_bytes) != request.target_artifact_identity:
            raise PermuterExecutorInputError("request target identity changed")
        expected_session = hash_canonical(
            {
                "protocol": "sotn-permuter-provider-v1",
                "provider_identity": request.provider_identity,
                "recipient_id": request.recipient_id,
                "input_identity": request.input_identity,
            }
        )
        if request.session_identity != expected_session:
            raise PermuterExecutorInputError("request session identity changed")
        for name, actual in (
            ("lane", self.binding.lane),
            ("algorithm", self.binding.algorithm),
            ("vendor_revision", self.binding.vendor_revision),
            ("tool_identity", self.binding.tool_identity),
            ("weights_identity", self.binding.weights_identity),
            ("algorithm_identity", self.binding.algorithm_identity),
        ):
            if getattr(request, name) != actual:
                raise PermuterExecutorInputError(f"request {name} differs from its binding")
        expected_algorithm_identity = hash_canonical(
            {
                "protocol": PERMUTER_CONFIG_PROTOCOL,
                "lane": request.lane,
                "algorithm": request.algorithm,
            }
        )
        if request.algorithm_identity != expected_algorithm_identity:
            raise PermuterExecutorInputError("request algorithm identity changed")
        expected_config_identity = hash_canonical(
            {
                "protocol": PERMUTER_CONFIG_PROTOCOL,
                "lane": request.lane,
                "algorithm": request.algorithm,
                "algorithm_identity": request.algorithm_identity,
                "max_calls": request.max_calls,
                "max_iterations": request.max_iterations,
                "max_candidates": request.max_candidates,
                "checkpoint_interval": request.checkpoint_interval,
                "evaluator_identity": request.evaluator_identity,
            }
        )
        if request.config_identity != expected_config_identity:
            raise PermuterExecutorInputError("request config identity changed")
        if self.runtime is not None and request.evaluator_identity != self.runtime.evaluator_identity:
            raise PermuterExecutorInputError("request evaluator identity differs from runtime binding")
        if b"\x00" in seed_bytes or b"\x00" in target_bytes:
            raise PermuterExecutorInputError("request source or target contains NUL bytes")
        return seed_bytes, target_bytes

    def _verify_binding(self) -> tuple[bytes, bytes]:
        try:
            self.binding.verify(self.archive)
        except PermuterProviderUnavailable as exc:
            raise PermuterExecutorUnavailable(str(exc), code=exc.code) from exc
        except PermuterProviderError:
            raise
        files = _vendor_files(self.vendor_root)
        file_map = dict(files)
        try:
            runner = file_map["permuter.py"]
            weights = file_map["default_weights.toml"]
        except KeyError as exc:
            raise PermuterExecutorUnavailable(
                "pinned decomp-permuter tree has no fixed runner or weights",
                code="permuter_vendor_incomplete",
            ) from exc
        self._runner_identity = hash_bytes(runner)
        self._vendor_revision = hash_canonical(_vendor_manifest_from_files(files))
        self._vendor_snapshot = files
        if self.binding.vendor_revision != self._vendor_revision:
            raise PermuterExecutorInputError("binding vendor revision differs from vendored bytes")
        if self.binding.tool_identity != self._runner_identity:
            raise PermuterExecutorInputError("binding tool identity differs from vendored runner")
        if self.binding.weights_identity != hash_bytes(weights):
            raise PermuterExecutorInputError("binding weights identity differs from vendored weights")
        if self.binding.tool_bytes != runner or self.binding.weights_bytes != weights:
            raise PermuterExecutorInputError("binding bytes differ from vendored bytes")
        if self.runtime is not None:
            self.runtime.verify(self.archive)
            for relative, expected in (
                ("automation/search_compile_driver.py", _COMPILER_DRIVER_IDENTITY),
                ("automation/compiler_corpus.py", _COMPILER_CORPUS_IDENTITY),
                ("automation/search_permuter_worker.py", _STRATEGY_WORKER_IDENTITY),
                ("automation/search_mutations.py", _MUTATIONS_IDENTITY),
                ("automation/search_source_context.py", _SOURCE_CONTEXT_IDENTITY),
                ("automation/search_process_lock.py", _PROCESS_LOCK_IDENTITY),
            ):
                if hash_bytes(_regular_file(self.repo_root / relative, "compiler driver")) != expected:
                    raise PermuterExecutorInputError("repository compiler driver identity changed")
        return runner, weights

    def _minimal_env(self) -> dict[str, str]:
        path = os.environ.get("PATH", "")
        return {
            "PATH": path,
            "LANG": "C",
            "LC_ALL": "C",
            "PYTHONHASHSEED": "0",
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
        }

    def _execution_env(self) -> dict[str, str]:
        environment = self._minimal_env()
        if self.runtime is not None:
            environment.update(dict(self.runtime.compiler_environment))
            environment["SOTN_REPO_ROOT"] = str(self.repo_root)
            environment["SOTN_COMPILER_IDENTITY"] = self.runtime.evaluator_identity
        return environment

    def _wsl_executable(self) -> str:
        if os.name != "nt":
            raise PermuterExecutorInputError("WSL executable requested on a non-Windows host")
        executable = shutil.which("wsl.exe")
        if executable is None:
            raise PermuterExecutorUnavailable(
                "Windows host has no usable wsl.exe for the vendored runner",
                code="permuter_wsl_unavailable",
            )
        return executable

    def _wsl_path(self, path: Path) -> str:
        wsl = self._wsl_executable()
        try:
            result = subprocess.run(
                [wsl, "--exec", "wslpath", "-a", "-u", str(path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                timeout=_PREFLIGHT_TIMEOUT_SECONDS,
                check=False,
                shell=False,
                env=self._minimal_env(),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise PermuterExecutorUnavailable(
                "Windows WSL path translation failed", code="permuter_wsl_path_unavailable"
            ) from exc
        translated = (result.stdout or "").strip()
        if result.returncode != 0 or not translated.startswith("/") or "\n" in translated:
            raise PermuterExecutorUnavailable(
                "Windows WSL returned an unsafe path translation",
                code="permuter_wsl_path_unavailable",
            )
        return translated

    def _make_wsl_executable(self, path: Path) -> None:
        """Set the compile wrapper's execute bit inside the WSL view."""

        wsl = self._wsl_executable()
        translated = self._wsl_path(path)
        try:
            result = subprocess.run(
                [wsl, "--exec", "chmod", "u+x", translated],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=_PREFLIGHT_TIMEOUT_SECONDS,
                check=False,
                shell=False,
                env=self._minimal_env(),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise PermuterExecutorUnavailable(
                "Windows WSL could not make the compile wrapper executable",
                code="permuter_wsl_compile_unavailable",
            ) from exc
        if result.returncode != 0:
            raise PermuterExecutorUnavailable(
                "Windows WSL could not make the compile wrapper executable",
                code="permuter_wsl_compile_unavailable",
            )

    def _help_command(self, root: Path) -> tuple[list[str], Optional[str]]:
        runner = root / "permuter.py"
        if os.name == "nt":
            wsl = self._wsl_executable()
            wsl_root = self._wsl_path(root)
            return (
                [
                    wsl,
                    "--cd",
                    wsl_root,
                    "--exec",
                    "python3",
                    "-B",
                    "-u",
                    f"{wsl_root}/permuter.py",
                    wsl_root,
                    _RUNNER_HELP_FLAG,
                ],
                None,
            )
        return [sys.executable, "-B", "-u", str(runner), str(root), _RUNNER_HELP_FLAG], str(root)

    def _runner_command(
        self,
        vendor_root: Path,
        work_root: Path,
        request: PermuterRequest,
        runner_algorithm: str,
        runner_seed: int,
    ) -> tuple[list[str], Optional[str]]:
        del vendor_root, runner_algorithm, runner_seed
        worker = self.repo_root / "automation/search_permuter_worker.py"
        if os.name == "nt":
            return [
                self._wsl_executable(), "--exec", "python3", "-B", "-u",
                self._wsl_path(worker), "--work", self._wsl_path(work_root),
                "--run-root", self._wsl_path(self.archive.run_root),
            ], None
        return [
            sys.executable, "-B", "-u", str(worker),
            "--work", str(work_root), "--run-root", str(self.archive.run_root),
        ], str(work_root / "vendor")

    def _probe_runner(self) -> None:
        command, cwd = self._help_command(self.vendor_root)
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=min(self.timeout_seconds, _PREFLIGHT_TIMEOUT_SECONDS),
                check=False,
                shell=False,
                env=self._minimal_env(),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise PermuterExecutorUnavailable(
                f"vendored decomp-permuter preflight could not start on {self.platform}",
                code="permuter_runner_preflight_failed",
            ) from exc
        output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
        if result.returncode != 0 or _RUNNER_HELP_MARKER not in output:
            detail = " ".join(output.split())[:256] or "no runner output"
            raise PermuterExecutorUnavailable(
                f"vendored decomp-permuter preflight failed on {self.platform}: {detail}",
                code="permuter_runner_preflight_failed",
            )

    def _target_object_available(self, request: PermuterRequest) -> bool:
        if self.runtime is not None and self.runtime.target_object_artifact is not None:
            return self.runtime.target_object_bytes is not None
        return request.target_artifact.path.lower().endswith(".o") or "object" in request.target_artifact.media_type.lower()

    def _preflight_unavailable(
        self,
        request: PermuterRequest,
        reason: str,
        refusal_code: str,
    ) -> PermuterPreflight:
        try:
            runner_identity = self.runner_identity
        except PermuterExecutorError:
            runner_identity = request.tool_identity
        try:
            vendor_revision = self.vendor_revision
        except PermuterExecutorError:
            vendor_revision = request.vendor_revision
        return PermuterPreflight(
            status="unavailable",
            request_identity=request.request_identity,
            platform=self.platform,
            runner_identity=runner_identity,
            vendor_revision=vendor_revision,
            tool_identity=request.tool_identity,
            weights_identity=request.weights_identity,
            runtime_identity=self.runtime.runtime_identity if self.runtime else None,
            reason=reason,
            refusal_code=refusal_code,
        )

    def preflight(self, request: PermuterRequest) -> PermuterPreflight:
        """Verify bindings and execute the vendor's real ``--help`` probe."""

        self._verify_request(request)
        try:
            self._verify_binding()
        except PermuterExecutorUnavailable as exc:
            return self._preflight_unavailable(request, str(exc), exc.code)
        try:
            self._probe_runner()
        except PermuterExecutorUnavailable as exc:
            return self._preflight_unavailable(request, str(exc), exc.code)
        if self.runtime is None:
            return self._preflight_unavailable(
                request,
                (
                    "vendored decomp-permuter needs an archive-bound compile script "
                    "and target object; this request contains source and target "
                    "assembly only"
                ),
                "permuter_runner_inputs_unavailable",
            )
        if not self._target_object_available(request):
            return self._preflight_unavailable(
                request,
                (
                    "vendored decomp-permuter target.o is not archive-bound; "
                    "target_assembly cannot be treated as an object file"
                ),
                "permuter_target_object_unavailable",
            )
        return PermuterPreflight(
            status="ready",
            request_identity=request.request_identity,
            platform=self.platform,
            runner_identity=self.runner_identity,
            vendor_revision=self.vendor_revision,
            tool_identity=request.tool_identity,
            weights_identity=request.weights_identity,
            runtime_identity=self.runtime.runtime_identity,
        )

    def _ensure_directory(self, root: Path, relative: str) -> Path:
        target = _safe_component_path(root, relative, "scratch child")
        try:
            root_resolved = root.resolve(strict=False)
            relative_parts = target.relative_to(root_resolved).parts
        except (OSError, RuntimeError, ValueError) as exc:
            raise PermuterExecutorInputError("scratch child escaped its root") from exc
        current = root_resolved
        for part in relative_parts:
            current = current / part
            if current.is_symlink():
                raise PermuterExecutorInputError("scratch path contains a symlink")
            if current.exists():
                if not current.is_dir():
                    raise PermuterExecutorInputError("scratch path component is not a directory")
            else:
                try:
                    current.mkdir()
                except FileExistsError:
                    if current.is_symlink() or not current.is_dir():
                        raise PermuterExecutorInputError("scratch path raced with a non-directory")
                except OSError as exc:
                    raise PermuterExecutorUnavailable("scratch directory cannot be created") from exc
        return current

    def _write_exact(self, root: Path, relative: str, data: bytes, *, executable: bool = False) -> Path:
        path = _safe_component_path(root, relative, "scratch artifact")
        parent_rel = path.parent.relative_to(root.resolve(strict=False)).as_posix()
        if parent_rel != ".":
            self._ensure_directory(root, parent_rel)
        elif root.is_symlink() or not root.is_dir():
            raise PermuterExecutorInputError("scratch artifact root is not a directory")
        if path.is_symlink():
            raise PermuterExecutorInputError("scratch artifact is a symlink")
        if path.exists():
            if not path.is_file() or path.read_bytes() != data:
                raise PermuterExecutorInputError("existing scratch artifact differs")
        else:
            try:
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                descriptor = os.open(str(path), flags, 0o644)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError:
                if path.is_symlink() or not path.is_file() or path.read_bytes() != data:
                    raise PermuterExecutorInputError("scratch artifact raced with different bytes")
            except OSError as exc:
                raise PermuterExecutorUnavailable("scratch artifact cannot be materialized") from exc
        if executable and os.name != "nt":
            try:
                path.chmod(path.stat().st_mode | stat.S_IXUSR)
            except OSError as exc:
                raise PermuterExecutorUnavailable("scratch compile script cannot be made executable") from exc
        return path

    def _copy_vendor_tree(self, destination: Path, files: Sequence[tuple[str, bytes]]) -> None:
        self._ensure_directory(destination.parent, destination.name)
        for relative, data in files:
            self._write_exact(destination, relative, data, executable=relative == "permuter.py")

    def _checkpoint_state(self, request: PermuterRequest) -> Mapping[str, Any]:
        if request.phase == "start":
            return {}
        store = PermuterHandoffStore(self.archive)
        try:
            found = store.find_checkpoint(request.prior_checkpoint_identity or "")
        except Exception as exc:
            raise PermuterExecutorInputError("resume checkpoint archive cannot be inspected") from exc
        if found is None:
            raise PermuterExecutorRefused(
                "resume checkpoint is missing from the immutable run archive",
                code="permuter_checkpoint_missing",
            )
        try:
            checkpoint = PermuterCheckpoint.from_dict(found[0])
        except Exception as exc:
            raise PermuterExecutorInputError("resume checkpoint is malformed") from exc
        # The handoff artifact is the hash of the complete canonical document;
        # ``checkpoint_identity`` intentionally hashes only its identity
        # payload.  Comparing those two different layers would reject every
        # valid checkpoint and would make resume impossible after a restart.
        if found[1].content_hash != hash_canonical(found[0]):
            raise PermuterExecutorInputError("resume checkpoint artifact identity changed")
        if (
            checkpoint.checkpoint_identity != request.prior_checkpoint_identity
            or checkpoint.lane != request.lane
            or checkpoint.phase not in {"start", "resume"}
            or checkpoint.session_identity != request.session_identity
            or checkpoint.scratch_identity != request.scratch_identity
            or checkpoint.iterations != request.start_iteration
            or not checkpoint.stopped
        ):
            raise PermuterExecutorInputError("resume checkpoint does not bind to this request")
        if len(checkpoint.candidates) > request.max_candidates:
            raise PermuterExecutorInvalidResponse(
                "resume checkpoint candidate count exceeds its bound"
            )
        if any("\x00" in item.source for item in checkpoint.candidates):
            raise PermuterExecutorInputError("resume checkpoint contains NUL source bytes")
        return _plain(checkpoint.state)

    def _materialize(
        self,
        request: PermuterRequest,
        seed_bytes: bytes,
        target_bytes: bytes,
        runner_bytes: bytes,
        weights_bytes: bytes,
        checkpoint_state: Mapping[str, Any],
    ) -> tuple[Path, Path, int]:
        scratch = _safe_component_path(self.archive.run_root, request.scratch_path, "scratch path")
        self._ensure_directory(self.archive.run_root, request.scratch_path)
        scratch = self._ensure_directory(scratch, request.phase + "-" + request.request_identity[7:23])
        self._write_exact(scratch, "prior-state.json", canonical_bytes(checkpoint_state))
        marker = {
            "protocol": EXECUTOR_PROTOCOL,
            "request_identity": request.request_identity,
            "request": request.to_dict(),
            "runner_identity": hash_bytes(runner_bytes),
            "vendor_revision": self.vendor_revision,
            "tool_identity": request.tool_identity,
            "weights_identity": hash_bytes(weights_bytes),
            "phase": request.phase,
            "prior_checkpoint_identity": request.prior_checkpoint_identity,
        }
        self._write_exact(scratch, "executor-request.json", canonical_bytes(marker))
        vendor_destination = self._ensure_directory(scratch, "vendor")
        vendor_files = self._vendor_snapshot
        if vendor_files is None:
            raise PermuterExecutorInputError("vendored bytes were not verified before materialization")
        self._copy_vendor_tree(vendor_destination, vendor_files)
        self._write_exact(vendor_destination, "default_weights.toml", weights_bytes)
        self._ensure_directory(scratch, "tmp")
        self._write_exact(scratch, "base.c", seed_bytes)
        self._write_exact(scratch, "target.s", target_bytes)
        if self.runtime is None:
            raise PermuterExecutorUnavailable(
                "vendored decomp-permuter runtime inputs are not bound",
                code="permuter_runner_inputs_unavailable",
            )
        self._write_exact(scratch, "compile.sh", self.runtime.compile_script_bytes, executable=True)
        function_name = self.runtime.function_name or _function_name(request.recipient_id)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", function_name):
            raise PermuterExecutorInputError("runtime function name is not a C identifier")
        settings = (
            f'func_name = "{function_name}"\n'
            f'compiler_type = "{self.runtime.compiler_type}"\n'
        ).encode("utf-8")
        self._write_exact(scratch, "settings.toml", settings)
        self._write_exact(scratch, "function.txt", (function_name + "\n").encode("utf-8"))
        object_bytes = self.runtime.target_object_bytes
        if object_bytes is None and self._target_object_available(request):
            object_bytes = target_bytes
        if object_bytes is None:
            raise PermuterExecutorUnavailable(
                "vendored decomp-permuter target.o is not archive-bound",
                code="permuter_target_object_unavailable",
            )
        self._write_exact(scratch, "target.o", object_bytes)
        runner_algorithm = _ALGORITHM_MAP[request.algorithm]
        runner_seed = _stable_seed(request)
        if request.phase == "resume":
            saved_seed = checkpoint_state.get("runner_seed")
            if (
                isinstance(saved_seed, bool)
                or not isinstance(saved_seed, int)
                or saved_seed <= 0
                or saved_seed >= 10**20
            ):
                raise PermuterExecutorInputError("resume checkpoint has no valid runner seed")
            runner_seed = saved_seed
            saved_algorithm = checkpoint_state.get("runner_algorithm")
            if saved_algorithm != runner_algorithm:
                raise PermuterExecutorInputError("resume checkpoint runner algorithm differs")
        state = {
            "protocol": STATE_PROTOCOL,
            "request_identity": request.request_identity,
            "phase": request.phase,
            "runner_identity": self.runner_identity,
            "vendor_revision": self.vendor_revision,
            "tool_identity": request.tool_identity,
            "weights_identity": request.weights_identity,
            "runner_algorithm": runner_algorithm,
            "runner_seed": runner_seed,
            "start_iteration": request.start_iteration,
            "prior_checkpoint_identity": request.prior_checkpoint_identity,
        }
        self._write_exact(scratch, "executor-state.json", canonical_bytes(state))
        return scratch, vendor_destination, runner_seed

    def _terminate(self, process: subprocess.Popen[str]) -> None:
        try:
            if os.name == "nt" and isinstance(getattr(process, "pid", None), int):
                # ``wsl.exe`` is only the host wrapper.  A Windows process
                # group is not sufficient to prove Linux descendants are
                # gone, so use the OS tree terminator for the wrapper and all
                # descendants before waiting at this boundary.
                subprocess.run(
                    ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=5,
                    check=False,
                    shell=False,
                )
            elif isinstance(getattr(process, "pid", None), int):
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
            process.wait(timeout=5)
        except (OSError, subprocess.SubprocessError):
            try:
                if os.name != "nt" and isinstance(getattr(process, "pid", None), int):
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait(timeout=5)
            except (OSError, subprocess.SubprocessError):
                pass

    def _run_process(
        self,
        command: Sequence[str],
        cwd: Optional[str],
        request: PermuterRequest,
        *,
        iteration_limit: int,
    ) -> tuple[int, str, bool]:
        try:
            kwargs: dict[str, Any] = {
                "cwd": cwd,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True,
                "encoding": "utf-8",
                "errors": "replace",
                "bufsize": 1,
                "shell": False,
                "env": {**self._execution_env(), **(
                    {"TMPDIR": str(Path(cwd).parent / "tmp")} if cwd is not None else {}
                )},
            }
            if os.name != "nt":
                kwargs["start_new_session"] = True
            else:
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            process = subprocess.Popen(list(command), **kwargs)
        except OSError as exc:
            raise PermuterExecutorUnavailable(
                f"vendored decomp-permuter could not start on {self.platform}",
                code="permuter_runner_start_failed",
            ) from exc
        lines: list[str] = []
        line_queue: queue.Queue[Optional[str]] = queue.Queue()

        def read_output() -> None:
            stream = process.stdout
            if stream is None:
                line_queue.put(None)
                return
            try:
                for line in stream:
                    line_queue.put(line)
            finally:
                line_queue.put(None)

        reader = threading.Thread(target=read_output, name="permuter-output", daemon=True)
        reader.start()
        started = time.monotonic()
        observed = request.start_iteration
        output_bytes = 0
        controlled_stop = False
        finished_reading = False
        while True:
            try:
                item = line_queue.get(timeout=0.1)
            except queue.Empty:
                item = ""
            if item is None:
                finished_reading = True
            elif item:
                output_bytes += len(item.encode("utf-8", errors="replace"))
                if output_bytes > _MAX_OUTPUT_BYTES:
                    self._terminate(process)
                    reader.join(timeout=5)
                    raise PermuterExecutorInvalidResponse("vendored runner output exceeds its bound")
                lines.append(item)
                for match in _ITERATION_RE.finditer(item):
                    # The vendored process starts its own counter at one on
                    # every invocation.  The provider request's counter is
                    # cumulative, so translate the local line number before
                    # enforcing the immutable cumulative limit.
                    observed = max(observed, request.start_iteration + int(match.group(1)))
                if observed >= iteration_limit and process.poll() is None:
                    controlled_stop = True
                    self._terminate(process)
            if time.monotonic() - started > self.timeout_seconds:
                self._terminate(process)
                reader.join(timeout=5)
                raise PermuterExecutorTimeout("vendored decomp-permuter exceeded its time bound")
            if finished_reading and process.poll() is not None:
                break
        reader.join(timeout=5)
        return process.returncode or 0, "".join(lines), controlled_stop

    def _parse_output(
        self,
        request: PermuterRequest,
        scratch: Path,
        output_before: frozenset[str],
        output: str,
        returncode: int,
        controlled_stop: bool,
        runner_algorithm: str,
        runner_seed: int,
    ) -> dict[str, Any]:
        from .search_permuter_worker import load_events
        del scratch, output_before
        if returncode == 75:
            from .search_permuter_lanes import PermuterProviderHandoffPending
            raise PermuterProviderHandoffPending("the previous worker still owns this session; retry after it exits")
        failed = returncode != 0 and not controlled_stop
        failure_detail = " ".join(output.split())[-512:] or "worker returned a nonzero status"
        terminals = []
        for line in output.splitlines():
            try:
                document = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(document, dict) and "permuter_terminal" in document:
                terminals.append(document["permuter_terminal"])
        events = load_events(self.archive, request.session_identity)
        if not failed and not controlled_stop and len(terminals) != 1:
            raise PermuterExecutorInvalidResponse("runner has no unique structured terminal")
        references = [reference.to_dict() for reference, _ in events]
        if terminals and (
            terminals[0].get("evaluation_artifacts") != references
            or terminals[0].get("absolute_iterations") != len(events)
        ):
            raise PermuterExecutorInvalidResponse("runner terminal differs from durable evaluations")
        if not request.start_iteration <= len(events) <= request.max_iterations:
            raise PermuterExecutorInvalidResponse("durable evaluation count exceeds request bounds")
        candidates = []
        scores = []
        for reference, event in events:
            if (
                event["evaluator_identity"] != request.evaluator_identity
                or event["target_identity"] != request.target_identity
                or event["strategy"] != request.algorithm
            ):
                raise PermuterExecutorInvalidResponse("evaluation event binding differs")
            score = event["score"]["total"]
            if score is not None:
                scores.append(score)
            if event["iteration"] <= request.start_iteration:
                continue
            source = self.archive.verify(ArtifactRef.from_dict(event["source"])).decode("utf-8")
            candidates.append({
                "source": source, "score": score, "iteration": event["iteration"],
                "provenance": {
                    **event["provenance"],
                    "kind": "vendored_decomp_permuter",
                    "evaluation_artifact": reference.to_dict(),
                    "score_vector": event["score"],
                    "executor_protocol": EXECUTOR_PROTOCOL,
                    "vendor_revision": self.vendor_revision,
                    "tool_identity": request.tool_identity,
                    "weights_identity": request.weights_identity,
                    "lane_algorithm": request.algorithm,
                    "runner_algorithm": runner_algorithm,
                },
            })
        candidates.sort(key=lambda item: (
            item["score"] is None, item["score"] if item["score"] is not None else 0,
            item["iteration"],
        ))
        selected = candidates[:request.max_candidates]
        stopped = controlled_stop or not terminals[0]["completed"] if terminals else True
        terminal = terminals[0] if terminals else {}
        status = "refused" if failed else terminal.get("status", "stopped" if stopped else "completed")
        return {
            "status": status,
            "iterations": len(events) - request.start_iteration,
            "candidates": selected,
            "state": {
                "protocol": STATE_PROTOCOL,
                "runner_seed": runner_seed, "runner_algorithm": runner_algorithm,
                "absolute_iterations": len(events),
                "evaluation_artifacts": references,
                "unreturned_candidate_ids": [
                    hash_bytes(item["source"].encode("utf-8"))
                    for item in candidates[request.max_candidates:]
                ],
            },
            "best_score": min(scores) if scores else None,
            "reason": ("structured permuter failed: " + failure_detail if failed else
                       terminal.get("reason", "structured permutation evaluations are durable")),
            "refusal_code": "permuter_runner_failed" if failed else terminal.get("refusal_code"),
            "stop_reason": "budget_exhausted" if stopped else "",
        }

    def __call__(self, request: PermuterRequest) -> Mapping[str, Any]:
        if self.runtimes:
            self._verify_request(request)
            runtime = self.runtimes.get(request.recipient_id)
            if runtime is None:
                raise PermuterExecutorInputError("recipient has no immutable runtime route")
            return PermuterExecutor(
                self.archive, self.binding, runtime=runtime,
                repo_root=self.repo_root, timeout_seconds=self.timeout_seconds,
            )(request)
        preflight = self.preflight(request)
        if not preflight.ready:
            raise PermuterExecutorUnavailable(
                preflight.reason,
                code=preflight.refusal_code or "permuter_executor_unavailable",
            )
        seed_bytes, target_bytes = self._verify_request(request)
        runner_bytes, weights_bytes = self._verify_binding()
        checkpoint_state = self._checkpoint_state(request)
        scratch, vendor_destination, runner_seed = self._materialize(
            request,
            seed_bytes,
            target_bytes,
            runner_bytes,
            weights_bytes,
            checkpoint_state,
        )
        try:
            before = frozenset(item.name for item in scratch.iterdir())
        except OSError as exc:
            raise PermuterExecutorUnavailable("runner scratch cannot be listed") from exc
        if os.name == "nt":
            self._make_wsl_executable(scratch / "compile.sh")
        runner_algorithm = _ALGORITHM_MAP[request.algorithm]
        command, cwd = self._runner_command(
            vendor_destination,
            scratch,
            request,
            runner_algorithm,
            runner_seed,
        )
        # The OS result is (returncode, output, stopped). Pass named fields
        # to the parser so a tuple-order change cannot corrupt the boundary.
        returncode, output, controlled_stop = self._run_process(
            command,
            cwd,
            request,
            iteration_limit=request.max_iterations,
        )
        return self._parse_output(
            request,
            scratch,
            before,
            output=output,
            returncode=returncode,
            controlled_stop=controlled_stop,
            runner_algorithm=runner_algorithm,
            runner_seed=runner_seed,
        )

    execute = __call__
    invoke = __call__


TrustedPermuterExecutor = PermuterExecutor


def build_permuter_executor(
    archive: ContentAddressedArchive,
    binding: PermuterToolBinding,
    *,
    runtime: Optional[PermuterRuntimeBinding] = None,
    repo_root: Optional[str | os.PathLike[str]] = None,
    timeout_seconds: float = 300.0,
) -> PermuterExecutor:
    """Build the concrete executor used by a production lane registry."""

    return PermuterExecutor(
        archive,
        binding,
        runtime=runtime,
        repo_root=repo_root,
        timeout_seconds=timeout_seconds,
    )


make_permuter_executor = build_permuter_executor


__all__ = [
    "EXECUTOR_PROTOCOL",
    "MODULE_IDENTITY",
    "PREFLIGHT_PROTOCOL",
    "REPOSITORY_COMPILE_WRAPPER_BYTES",
    "REPOSITORY_COMPILE_WRAPPER_IDENTITY",
    "REPOSITORY_COMPILER_ARGV_TEMPLATE",
    "REPOSITORY_COMPILER_ENVIRONMENT",
    "REPOSITORY_COMPILER_EXECUTABLE",
    "REPOSITORY_COMPILER_INPUT_LOCATION",
    "REPOSITORY_COMPILER_OUTPUT_LOCATION",
    "RUNTIME_PROTOCOL",
    "STATE_PROTOCOL",
    "TrustedPermuterExecutor",
    "PermuterExecutor",
    "PermuterExecutorError",
    "PermuterExecutorInputError",
    "PermuterExecutorInvalidResponse",
    "PermuterExecutorRefused",
    "PermuterExecutorTimeout",
    "PermuterExecutorUnavailable",
    "PermuterPreflight",
    "PermuterRuntimeBinding",
    "build_permuter_executor",
    "make_permuter_executor",
    "vendored_runner_identity",
    "vendored_tree_identity",
    "vendored_tree_manifest",
]
