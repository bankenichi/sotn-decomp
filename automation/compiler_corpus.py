"""Exact PSX compiler observations for small, reproducible C snippets.

The corpus deliberately drives the same six-stage command configured for the US
permuter.  It keeps all transient files in one temporary directory and returns
only content identities and sanitized diagnostics, so an observation can be
stored without depending on a machine-specific pathname.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Optional

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "tools" / "sotn_permuter" / "permuter_settings.us.toml"
DEFAULT_WEIGHTS = {
    "stack": 1,
    "regalloc": 5,
    "reordering": 60,
    "insertion": 100,
    "deletion": 100,
}
_HASH_PREFIX = "sha256:"
_STAGE_SEPARATOR = "|"


class CompilerCorpusError(RuntimeError):
    """Raised when the exact corpus pipeline cannot produce an observation."""


@dataclass(frozen=True)
class CompilerPipelineIdentity:
    """Content identity for the configured compiler pipeline."""

    executable: str
    executable_hash: str
    arguments: tuple[str, ...]
    environment_defines: tuple[str, ...]
    tool_hashes: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "arguments", tuple(self.arguments))
        object.__setattr__(self, "environment_defines", tuple(self.environment_defines))
        normalized_tools = []
        for entry in self.tool_hashes:
            if isinstance(entry, Mapping):
                name = entry["name"]
                value = entry["hash"]
            else:
                name, value = entry
            normalized_tools.append((str(name), str(value)))
        object.__setattr__(self, "tool_hashes", tuple(normalized_tools))

    def to_dict(self) -> dict[str, object]:
        return {
            "executable": self.executable,
            "executable_hash": self.executable_hash,
            "arguments": list(self.arguments),
            "environment_defines": list(self.environment_defines),
            "tool_hashes": [
                {"name": name, "hash": value}
                for name, value in self.tool_hashes
            ],
        }

    @property
    def identity(self) -> str:
        return hash_bytes(_canonical_bytes(self.to_dict()))


@dataclass(frozen=True)
class CorpusObservation:
    """Stable result of compiling one bounded source case."""

    case_id: str
    source_hash: str
    object_hash: Optional[str]
    disassembly_hash: Optional[str]
    pipeline_identity: str
    score: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "score", MappingProxyType(dict(self.score)))

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "source_hash": self.source_hash,
            "object_hash": self.object_hash,
            "disassembly_hash": self.disassembly_hash,
            "pipeline_identity": self.pipeline_identity,
            "score": _plain(self.score),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


@dataclass(frozen=True)
class _Pipeline:
    stages: tuple[tuple[str, ...], ...]
    identity: CompilerPipelineIdentity
    config_path: Path


class _PipelineFailure(CompilerCorpusError):
    def __init__(
        self,
        label: str,
        detail: str,
        *,
        source_rejection: bool = False,
        source_name: str | None = None,
    ) -> None:
        self.label = label
        self.detail = detail
        self.source_rejection = source_rejection
        self.source_name = source_name
        super().__init__(f"{label}: {detail}")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        _plain(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if isinstance(value, MappingProxyType):
        return {str(key): _plain(item) for key, item in value.items()}
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())  # type: ignore[no-any-return]
    return value


def hash_bytes(value: bytes) -> str:
    return _HASH_PREFIX + hashlib.sha256(value).hexdigest()


def hash_file(path: Path) -> str:
    try:
        return hash_bytes(path.read_bytes())
    except OSError as exc:
        raise CompilerCorpusError(f"cannot hash {path.name}") from exc


def _relative_display(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return "<external>"
    return relative.as_posix()


def _resolve_tool(command: str) -> tuple[str, Path]:
    candidate = Path(command)
    if candidate.is_absolute():
        resolved = candidate
    elif command.startswith("./") or (ROOT / candidate).is_file():
        resolved = ROOT / command.removeprefix("./")
    else:
        found = shutil.which(command)
        if found is None:
            raise CompilerCorpusError(f"missing executable {command}")
        resolved = Path(found)
    resolved = resolved.resolve()
    if not resolved.is_file():
        raise CompilerCorpusError(f"missing executable {command}")
    return _relative_display(resolved) if resolved.is_relative_to(ROOT.resolve()) else command, resolved


def _load_settings(config_path: Path) -> Mapping[str, object]:
    try:
        with config_path.open("rb") as stream:
            settings = tomllib.load(stream)
    except OSError as exc:
        raise CompilerCorpusError("cannot read compiler configuration") from exc
    except (tomllib.TOMLDecodeError, ValueError) as exc:
        raise CompilerCorpusError("invalid compiler configuration") from exc
    if not isinstance(settings, Mapping):
        raise CompilerCorpusError("compiler configuration is not an object")
    return settings


def _parse_stages(settings: Mapping[str, object]) -> tuple[tuple[str, ...], ...]:
    command = settings.get("compiler_command")
    if not isinstance(command, str) or not command.strip():
        raise CompilerCorpusError("compiler configuration has no compiler_command")
    stages: list[tuple[str, ...]] = []
    for raw_stage in command.split(_STAGE_SEPARATOR):
        stage = tuple(shlex.split(raw_stage.strip()))
        if stage:
            stages.append(stage)
    if len(stages) < 2:
        raise CompilerCorpusError("compiler pipeline has too few stages")
    return tuple(stages)


def _with_compiler_args(
    stages: tuple[tuple[str, ...], ...],
    compiler_args: Sequence[str],
) -> tuple[tuple[str, ...], ...]:
    extras = tuple(str(arg) for arg in compiler_args)
    if not extras:
        return stages
    mutable = [list(stage) for stage in stages]
    compiler_index = None
    for index, stage in enumerate(mutable):
        name = Path(stage[0]).name
        if name.startswith("cc1-psx"):
            compiler_index = index
            break
    if compiler_index is None:
        raise CompilerCorpusError("compiler pipeline has no cc1-psx stage")
    mutable[compiler_index].extend(extras)
    return tuple(tuple(stage) for stage in mutable)


def _is_repo_file(argument: str) -> Optional[tuple[str, Path]]:
    if argument.startswith("./"):
        path = ROOT / argument[2:]
    else:
        path = ROOT / argument
    try:
        resolved = path.resolve()
        resolved.relative_to(ROOT.resolve())
    except (OSError, ValueError):
        return None
    if not resolved.is_file():
        return None
    return _relative_display(resolved), resolved


def _build_identity(
    stages: tuple[tuple[str, ...], ...],
    config_path: Path,
) -> CompilerPipelineIdentity:
    compiler_stage = next(
        (stage for stage in stages if Path(stage[0]).name.startswith("cc1-psx")),
        stages[0],
    )
    executable_display, compiler_executable_path = _resolve_tool(compiler_stage[0])
    tool_hashes: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add_tool(name: str, path: Path) -> None:
        if name in seen:
            return
        seen.add(name)
        tool_hashes.append((name, hash_file(path)))

    for stage in stages:
        display, executable_path = _resolve_tool(stage[0])
        add_tool(display, executable_path)
        for argument in stage[1:]:
            repo_file = _is_repo_file(argument)
            if repo_file is not None:
                add_tool(repo_file[0], repo_file[1])

    # Objdump is part of the observation identity because it defines the
    # normalized disassembly used by the scorer, even though it is not a
    # compiler stage.
    objdump_display, objdump_path = _resolve_tool("mipsel-linux-gnu-objdump")
    add_tool(objdump_display, objdump_path)
    add_tool(_relative_display(config_path), config_path.resolve())

    arguments: list[str] = []
    for index, stage in enumerate(stages):
        display, _ = _resolve_tool(stage[0])
        arguments.extend((f"stage{index}", display))
        arguments.extend(
            argument.removeprefix("./") if argument.startswith("./") else argument
            for argument in stage[1:]
        )
        if index + 1 < len(stages):
            arguments.append(_STAGE_SEPARATOR)

    defines = tuple(
        argument
        for stage in stages
        for argument in stage[1:]
        if argument.startswith("-D")
    )
    return CompilerPipelineIdentity(
        executable=executable_display,
        executable_hash=hash_file(compiler_executable_path),
        arguments=tuple(arguments),
        environment_defines=defines,
        tool_hashes=tuple(tool_hashes),
    )


def pipeline_identity(
    *,
    compiler_args: Sequence[str] = (),
    config_path: Path | str = DEFAULT_CONFIG_PATH,
) -> CompilerPipelineIdentity:
    """Return the exact configured pipeline identity without compiling."""

    config = Path(config_path)
    if not config.is_absolute():
        config = ROOT / config
    stages = _with_compiler_args(_parse_stages(_load_settings(config)), compiler_args)
    return _build_identity(stages, config)


def _pipeline(
    *,
    compiler_args: Sequence[str] = (),
    config_path: Path | str = DEFAULT_CONFIG_PATH,
) -> _Pipeline:
    config = Path(config_path)
    if not config.is_absolute():
        config = ROOT / config
    stages = _with_compiler_args(_parse_stages(_load_settings(config)), compiler_args)
    return _Pipeline(stages, _build_identity(stages, config), config)


def _sanitize(text: str, temporary_root: Path) -> str:
    replacements = {
        str(temporary_root): "<temporary>",
        temporary_root.as_posix(): "<temporary>",
        str(temporary_root).replace("/", "\\"): "<temporary>",
    }
    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def _is_source_rejection(stage: Sequence[str], diagnostic: str) -> bool:
    """Accept only diagnostics tied to the source stream as source failures."""
    if not Path(stage[0]).name.startswith("cc1-psx"):
        return False
    lowered = diagnostic.casefold()
    if any(
        marker in lowered
        for marker in (
            "internal compiler error",
            "segmentation fault",
            "fatal signal",
            "out of memory",
            "unrecognized option",
            "unknown option",
            "cannot execute",
        )
    ):
        return False
    has_source_location = any(
        marker in lowered
        for marker in ("<stdin>:", "<command-line>:", "<built-in>:")
    )
    return has_source_location and "error" in lowered


def _run_stage(
    stage: Sequence[str],
    input_bytes: bytes,
    *,
    cwd: Path,
    temporary_root: Path,
    label: str,
    source_name: str | None = None,
) -> bytes:
    display_stage = " ".join(
        argument.removeprefix("./") if argument.startswith("./") else argument
        for argument in stage
    )
    try:
        completed = subprocess.run(
            list(stage),
            cwd=str(cwd),
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        raise _PipelineFailure(
            label,
            f"missing executable {stage[0]}",
            source_name=source_name,
        ) from exc
    except OSError as exc:
        raise _PipelineFailure(
            label,
            type(exc).__name__,
            source_name=source_name,
        ) from exc

    if completed.returncode != 0:
        diagnostic_bytes = (completed.stderr or b"") + (completed.stdout or b"")
        diagnostic = _sanitize(
            diagnostic_bytes.decode("utf-8", errors="replace").strip(),
            temporary_root,
        )
        if not diagnostic:
            diagnostic = f"return code {completed.returncode}"
        raise _PipelineFailure(
            label,
            f"return code {completed.returncode}; {diagnostic[:1200]}",
            source_rejection=_is_source_rejection(stage, diagnostic),
            source_name=source_name,
        )
    return completed.stdout or b""


def _materialize(path: Path, value: bytes) -> None:
    try:
        path.write_bytes(value)
    except OSError as exc:
        raise CompilerCorpusError("cannot materialize compiler intermediate") from exc


def _compile_source(
    source: str,
    pipeline: _Pipeline,
    temporary_root: Path,
    *,
    name: str,
) -> tuple[Path, str, int]:
    source_bytes = source.encode("utf-8")
    source_path = temporary_root / f"{name}.c"
    _materialize(source_path, source_bytes)
    data = source_bytes
    started = time.monotonic()

    for index, stage in enumerate(pipeline.stages):
        label = f"stage-{index}-{Path(stage[0]).name}"
        if index == len(pipeline.stages) - 1:
            object_path = temporary_root / f"{name}.o"
            command = list(stage) + ["-o", str(object_path)]
            _run_stage(
                command,
                data,
                cwd=ROOT,
                temporary_root=temporary_root,
                label=label,
                source_name=name,
            )
            if not object_path.is_file():
                raise _PipelineFailure(
                    label,
                    "assembler produced no object",
                    source_name=name,
                )
            return object_path, source_path.name, int((time.monotonic() - started) * 1000)

        data = _run_stage(
            stage,
            data,
            cwd=ROOT,
            temporary_root=temporary_root,
            label=label,
            source_name=name,
        )
        _materialize(
            temporary_root / f"{index:02d}-{Path(stage[0]).name}.out",
            data,
        )

    raise CompilerCorpusError("compiler pipeline produced no object")


def _normalized_disassembly(
    object_path: Path,
    *,
    stack_differences: bool = True,
) -> tuple[str, int]:
    vendor_root = ROOT / "tools" / "decomp-permuter"
    if str(vendor_root) not in sys.path:
        sys.path.insert(0, str(vendor_root))
    try:
        from src.objdump import MIPS_SETTINGS, objdump
        lines = objdump(
            str(object_path),
            MIPS_SETTINGS,
            stack_differences=stack_differences,
        )
    except Exception as exc:  # noqa: BLE001
        raise CompilerCorpusError("cannot disassemble corpus object") from exc
    rows = tuple(line.row for line in lines)
    return "\n".join(rows), len(rows)


def _score_objects(
    candidate_path: Path,
    target_path: Path,
    pipeline: _Pipeline,
    candidate_disassembly: str,
    target_disassembly: str,
) -> dict[str, object]:
    vendor_root = ROOT / "tools" / "decomp-permuter"
    if str(vendor_root) not in sys.path:
        sys.path.insert(0, str(vendor_root))
    try:
        from src.scorer import Scorer
        scorer = Scorer(
            str(target_path),
            stack_differences=True,
            algorithm="difflib",
            debug_mode=False,
            compiler_command=pipeline.identity.executable,
            compiler_args=pipeline.identity.arguments,
            compiler_config={"pipeline_identity": pipeline.identity.identity},
        )
        result = scorer.score(str(candidate_path))
        if hasattr(result, "to_dict"):
            score = dict(result.to_dict())
        else:  # pragma: no cover - compatibility with an older vendored scorer
            total, normalized_hash = result
            score = {
                "compile_status": "success",
                "elapsed_ms": 0,
                "total": total,
                "components": {name: 0 for name in DEFAULT_WEIGHTS},
                "weights": dict(DEFAULT_WEIGHTS),
                "object_hash": _HASH_PREFIX + normalized_hash,
                "mismatch_signature": None,
                "first_divergence": None,
                "target_instruction_count": None,
                "candidate_instruction_count": None,
                "diagnostic_artifact": None,
                "scorer_algorithm": "difflib",
            }
    except Exception as exc:  # noqa: BLE001
        raise CompilerCorpusError(f"cannot score corpus object: {type(exc).__name__}: {exc}") from exc

    score["compiler_identity"] = pipeline.identity.identity
    score["weights"] = dict(DEFAULT_WEIGHTS)
    # The scorer's elapsed field is intentionally normalized.  Wall time is not
    # an identity and recording it would make retries non-deterministic.
    score["elapsed_ms"] = 0
    return score


def _failure_score(
    pipeline: _Pipeline,
) -> dict[str, object]:
    return {
        "compile_status": "failed",
        "elapsed_ms": 0,
        "total": None,
        "components": {name: 0 for name in DEFAULT_WEIGHTS},
        "weights": dict(DEFAULT_WEIGHTS),
        "object_hash": None,
        "mismatch_signature": None,
        "first_divergence": None,
        "target_instruction_count": None,
        "candidate_instruction_count": None,
        "diagnostic_artifact": None,
        "scorer_algorithm": "difflib",
        "compiler_identity": pipeline.identity.identity,
    }


def compile_snippet(
    source: str,
    case_id: str,
    *,
    compiler_args: Sequence[str] = (),
    reference_source: Optional[str] = None,
    target_source: Optional[str] = None,
    config_path: Path | str = DEFAULT_CONFIG_PATH,
) -> CorpusObservation:
    """Compile one snippet through the configured pipeline.

    If reference_source or target_source is provided, it is compiled in the
    same temporary directory and the vendored scorer compares the candidate
    with that target.  Without a reference, the candidate is scored against
    itself, yielding a real exact score rather than a synthetic placeholder.
    """

    if not isinstance(source, str):
        raise TypeError("source must be a string")
    if not isinstance(case_id, str) or not case_id or "/" in case_id or "\\" in case_id:
        raise ValueError("case_id must be a stable non-path identifier")
    if reference_source is not None and target_source is not None:
        raise ValueError("reference_source and target_source are aliases")
    reference = target_source if target_source is not None else reference_source
    pipeline = _pipeline(compiler_args=compiler_args, config_path=config_path)
    source_hash = hash_bytes(source.encode("utf-8"))

    with tempfile.TemporaryDirectory(prefix="compiler-corpus-") as raw_root:
        temporary_root = Path(raw_root)
        try:
            candidate_path, _source_name, _elapsed = _compile_source(
                source,
                pipeline,
                temporary_root,
                name="candidate",
            )
            candidate_disassembly, _candidate_count = _normalized_disassembly(candidate_path)
            target_path = candidate_path
            target_disassembly = candidate_disassembly
            if reference is not None:
                target_path, _target_name, _target_elapsed = _compile_source(
                    reference,
                    pipeline,
                    temporary_root,
                    name="target",
                )
                target_disassembly, _target_count = _normalized_disassembly(target_path)
            score = _score_objects(
                candidate_path,
                target_path,
                pipeline,
                candidate_disassembly,
                target_disassembly,
            )
            return CorpusObservation(
                case_id=case_id,
                source_hash=source_hash,
                object_hash=hash_file(candidate_path),
                disassembly_hash=hash_bytes(candidate_disassembly.encode("utf-8")),
                pipeline_identity=pipeline.identity.identity,
                score=score,
            )
        except _PipelineFailure as exc:
            if (
                not exc.source_rejection
                or exc.source_name != "candidate"
            ):
                raise
            return CorpusObservation(
                case_id=case_id,
                source_hash=source_hash,
                object_hash=None,
                disassembly_hash=None,
                pipeline_identity=pipeline.identity.identity,
                score=_failure_score(pipeline),
            )


# Explicit aliases make the identity and compiler entry points discoverable to
# callers without introducing a second implementation.
build_pipeline_identity = pipeline_identity
compile_case = compile_snippet


__all__ = [
    "CompilerCorpusError",
    "CompilerPipelineIdentity",
    "CorpusObservation",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_WEIGHTS",
    "build_pipeline_identity",
    "compile_case",
    "compile_snippet",
    "hash_bytes",
    "hash_file",
    "pipeline_identity",
]
