"""Read-only semantic donor scanning for the four pinned platform trees.

The donor index accepts source *evidence*, not copied source bodies.  This
module therefore resolves the platform roots from the repository's explicit
configuration, parses C and assembly into normalized semantic selectors, and
returns records whose only source reference is the caller-owned immutable
archive artifact.  It intentionally does not invoke Git, a compiler, the
checksum oracle, or any queue writer.

The scanner is deliberately conservative around assembly.  Raw data
directives, relocation expressions, and numeric branch targets are omitted
before they can become evidence.  Ordinary register operands are used only
while parsing an instruction and are normalized away; no register evidence is
ever returned in a donor record.
"""

from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:  # package imports
    from .search_archive import ArchiveError, ArtifactRef, ContentAddressedArchive
    from .search_donor_index import DONOR_VERSIONS, DonorRevision
    from .search_lanes import DonorEvidence
    from .search_semantic_signatures import (
        cfg_signature as _shared_cfg_signature,
        dataflow_signature as _shared_dataflow_signature,
        has_numeric_branch_target,
        instruction_signature as _shared_instruction_signature,
        normalize_operands as _shared_normalize_operands,
    )
    from .search_types import (
        canonical_bytes,
        SearchValidationError,
        hash_canonical,
        hash_bytes,
        validate_hash,
        validate_relative_path,
    )
except ImportError:  # direct invocation from the automation directory
    from automation.search_archive import (  # type: ignore
        ArchiveError,
        ArtifactRef,
        ContentAddressedArchive,
    )
    from automation.search_donor_index import DONOR_VERSIONS, DonorRevision  # type: ignore
    from automation.search_lanes import DonorEvidence  # type: ignore
    from automation.search_semantic_signatures import (  # type: ignore
        cfg_signature as _shared_cfg_signature,
        dataflow_signature as _shared_dataflow_signature,
        has_numeric_branch_target,
        instruction_signature as _shared_instruction_signature,
        normalize_operands as _shared_normalize_operands,
    )
    from automation.search_types import (  # type: ignore
        canonical_bytes,
        SearchValidationError,
        hash_canonical,
        hash_bytes,
        validate_hash,
        validate_relative_path,
    )


DONOR_SCAN_PROTOCOL = "sotn-search-donor-scan-v1"
DONOR_SIGNATURE_PROTOCOL = "sotn-search-semantic-signature-v1"
# This is shared with search_indexed_runtime.  The manifest is an archive
# object, not a claim that mutable checkout bytes were measured previously.
DONOR_SNAPSHOT_MANIFEST_PROTOCOL = "sotn-donor-snapshot-manifest-v1"
DONOR_SNAPSHOT_PROTOCOL = DONOR_SNAPSHOT_MANIFEST_PROTOCOL
DONOR_SNAPSHOT_MANIFEST_FILENAME = ".sotn-donor-snapshot.json"
DONOR_SNAPSHOT_FILE_KINDS = ("assembly", "config", "source")

# The scanner has one canonical configuration entry point per platform.  The
# three PSX-family trees list their splat configs in assets.<version>.yaml;
# Saturn's source and assembly roots live in config/saturn/*.prg.yaml.
_ASSET_CONFIG_VERSIONS = frozenset({"us", "hd", "pspeu"})
_SATURN_CONFIG_GLOB = "*.prg.yaml"
_SOURCE_SUFFIXES = frozenset({".c", ".h"})
_ASSEMBLY_SUFFIXES = frozenset({".s", ".S", ".asm", ".inc"})
_CONTROL_IDENTIFIERS = frozenset(
    {
        "if",
        "else",
        "for",
        "while",
        "switch",
        "case",
        "return",
        "sizeof",
        "do",
        "goto",
    }
)
_C_FUNCTION_RE = re.compile(
    r"(?m)^\s*(?:(?:static|inline|extern|__inline__|__forceinline)\s+)*"
    r"(?:[A-Za-z_]\w*|\*)[\w\s*]*?"
    r"(?:OVL_EXPORT\(\s*(?P<export>[A-Za-z_]\w*)\s*\)|"
    r"(?P<name>[A-Za-z_]\w*))\s*\([^;{}]*\)\s*\{"
)
_INCLUDE_RE = re.compile(r"^\s*#\s*include\s*[<\"]([^>\"]+)[>\"]", re.M)
_TYPEDEF_RE = re.compile(
    r"\btypedef\s+(?:struct\s+)?[A-Za-z_]\w*(?:\s*\*)?\s+([A-Za-z_]\w*)\s*;"
)
_STRUCT_RE = re.compile(r"\b(?:struct|union|enum)\s+([A-Za-z_]\w*)")
_IDENT_RE = re.compile(r"[A-Za-z_]\w*")
_NUMBER_RE = re.compile(r"(?<![A-Za-z_])-?(?:0[xX][0-9A-Fa-f]+|[0-9]+)(?![A-Za-z_])")
_C_TOKEN_RE = re.compile(
    r"0[xX][0-9A-Fa-f]+|[0-9]+|[A-Za-z_]\w*|==|!=|<=|>=|&&|\|\||->|."
)
_C_COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
_C_STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')

_ASM_COMMON_COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
_ASM_LABEL_RE = re.compile(r"^\s*([.$A-Za-z_]\w*)\s*:\s*$")
_ASM_GLABEL_RE = re.compile(r"^\s*(?:glabel|\.globl|\.global)\s+([.$A-Za-z_]\w*)")
_ASM_INSTRUCTION_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_.]*)\b\s*(.*?)\s*$")
_ASM_REGISTER_RE = re.compile(
    r"(?:\$[0-9]{1,2}|\$(?:zero|at|v[01]|a[0-3]|t[0-9]|s[0-7]|k[01]|gp|sp|fp|ra)|"
    r"r(?:[0-9]{1,2}|zero|at|v[01]|a[0-3]|t[0-9]|s[0-7]|k[01]|gp|sp|fp|ra))",
    re.I,
)
_ASM_NUMBER_RE = re.compile(r"(?<![A-Za-z_])(?:-?0[xX][0-9A-Fa-f]+|-?[0-9]+)(?![A-Za-z_])")
_ASM_BRANCH_RE = re.compile(
    r"^(?:b|beq|bne|beqz|bnez|bgez|bgtz|blez|bltz|bc[0-9]+f|bc[0-9]+t|"
    r"j|jal|jr|jalr|bal|bgezal|bltzal)$",
    re.I,
)
_ASM_RETURN_RE = re.compile(r"^(?:jr|rts|ret)$", re.I)
_ASM_CALL_RE = re.compile(r"^(?:jal|jalr|bl|bsr|call)$", re.I)
# A directive is assembler metadata or object data, not a stable instruction
# semantic.  Keep the old named expression as a compatibility alias for
# callers that imported it, but classify every dotted directive below.
_ASM_DATA_DIRECTIVE_RE = re.compile(r"^\s*\.[A-Za-z_]", re.I)
_ASM_RELOCATION_RE = re.compile(
    r"(?:\.reloc\b|%hi\b|%lo\b|%higher\b|%highest\b|@(?:ha|l|h)\b|"
    r"R_(?:MIPS|SH|ARM)|\b(?:HI16|LO16|REL(?:32|24)?)\b)",
    re.I,
)


class DonorScanError(RuntimeError):
    """Base class for scanner input, configuration, and safety failures."""


class DonorScanInputError(DonorScanError):
    """A scanner argument or typed revision is malformed."""


class DonorScanConfigurationError(DonorScanInputError):
    """The explicit platform configuration is missing or inconsistent."""


class DonorScanUnsafeError(DonorScanInputError):
    """The source contains evidence that is not safe to archive semantically."""


# Compatibility names make the refusal boundary explicit to callers that use
# the broader evidence terminology from the donor-index protocol.
DonorScanRefusal = DonorScanUnsafeError
UnsafeDonorEvidence = DonorScanUnsafeError


@dataclass(frozen=True)
class PlatformRoots:
    """Canonical roots and configs selected for one supported platform."""

    version: str
    config_paths: tuple[str, ...]
    source_roots: tuple[str, ...]
    assembly_roots: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "config_paths": list(self.config_paths),
            "source_roots": list(self.source_roots),
            "assembly_roots": list(self.assembly_roots),
        }


@dataclass(frozen=True)
class _SnapshotFile:
    """One file whose bytes were verified from the archive before scanning."""

    path: str
    kind: str
    artifact: ArtifactRef
    data: bytes


@dataclass(frozen=True)
class _CFunction:
    path: Path
    relative_path: str
    name: str
    body: str
    includes: tuple[str, ...]
    types: tuple[str, ...]


@dataclass(frozen=True)
class _AsmFunction:
    path: Path
    relative_path: str
    name: str
    instructions: tuple[tuple[str, str], ...]
    labels: tuple[str, ...]


def _as_repo(repo: Path | str) -> Path:
    try:
        root = Path(repo).resolve(strict=False)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise DonorScanInputError("repository root cannot be resolved") from exc
    if not root.is_dir():
        raise DonorScanInputError("repository root must be a directory")
    return root


def _as_revision(value: DonorRevision | Mapping[str, Any]) -> DonorRevision:
    if isinstance(value, DonorRevision):
        return value
    if isinstance(value, Mapping):
        try:
            return DonorRevision.from_dict(value)
        except Exception as exc:  # typed boundary: preserve one scanner error
            raise DonorScanInputError("revision is not a complete pinned record") from exc
    raise DonorScanInputError("revision must be a DonorRevision")


def _safe_repo_path(repo: Path, relative: str, label: str, *, directory: bool) -> Path:
    try:
        relative = validate_relative_path(relative, label)
    except (SearchValidationError, TypeError, ValueError) as exc:
        raise DonorScanConfigurationError(f"{label} is not a safe relative path") from exc
    try:
        candidate = (repo / Path(relative)).resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise DonorScanConfigurationError(f"{label} cannot be resolved") from exc
    try:
        candidate.relative_to(repo)
    except ValueError as exc:
        raise DonorScanConfigurationError(f"{label} escapes the repository") from exc
    if directory:
        if not candidate.is_dir():
            raise DonorScanConfigurationError(f"configured {label} is not a directory: {relative}")
    elif not candidate.is_file():
        raise DonorScanConfigurationError(f"configured {label} is not a file: {relative}")
    return candidate


def _read_bytes(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise DonorScanConfigurationError(f"unable to read {label}: {path}") from exc


def _decode_text(data: bytes, path: Path, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeError as exc:
        raise DonorScanConfigurationError(f"unable to decode {label}: {path}") from exc


def _read_text(path: Path, label: str) -> str:
    return _decode_text(_read_bytes(path, label), path, label)


def _load_config(
    path: Path,
    *,
    verified_texts: Optional[Mapping[Path, str]] = None,
) -> Mapping[str, Any]:
    """Load one canonical YAML/JSON document without executing constructors."""

    if verified_texts is None:
        text = _read_text(path, "configuration")
    else:
        try:
            text = verified_texts[path]
        except KeyError as exc:
            raise DonorScanInputError(
                f"configuration was not present in the pinned source snapshot: {path}"
            ) from exc
    try:
        if path.suffix.lower() == ".json":
            value = json.loads(text)
        else:
            import yaml  # PyYAML is already an automation dependency.

            value = yaml.safe_load(text)
    except Exception as exc:
        raise DonorScanConfigurationError(f"configuration is not valid YAML: {path}") from exc
    if not isinstance(value, Mapping):
        raise DonorScanConfigurationError(f"configuration root must be an object: {path}")
    return value


def _nonempty_path(value: Any, label: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise DonorScanConfigurationError(f"configured {label} must be a relative path")
    return value.replace("\\", "/")


def discover_platform_roots(
    version: str,
    *,
    repo: Path | str,
    verified_texts: Optional[Mapping[Path, str]] = None,
) -> PlatformRoots:
    """Resolve only the explicit configuration for ``version``.

    There is intentionally no fallback to another platform, to a guessed
    ``src`` directory, or to the current working directory.  A missing root
    fails the scan before any source file is read.
    """

    if version not in DONOR_VERSIONS:
        raise DonorScanConfigurationError(f"unsupported donor version: {version!r}")
    root = _as_repo(repo)
    config_root = _safe_repo_path(root, "config", "config root", directory=True)
    config_paths: list[str] = []
    source_paths: list[str] = []
    assembly_paths: list[str] = []

    if version in _ASSET_CONFIG_VERSIONS:
        assets_rel = f"config/assets.{version}.yaml"
        config_paths.append(assets_rel)
        assets_path = _safe_repo_path(root, assets_rel, "asset configuration", directory=False)
        assets = _load_config(assets_path, verified_texts=verified_texts)
        if assets.get("version") != version:
            raise DonorScanConfigurationError(
                f"asset configuration version does not match {version}: {assets_rel}"
            )
        files = assets.get("files")
        if not isinstance(files, (list, tuple)):
            raise DonorScanConfigurationError(f"asset configuration files are missing: {assets_rel}")
        for index, item in enumerate(files):
            if not isinstance(item, Mapping):
                raise DonorScanConfigurationError(f"asset file {index} is not an object")
            splat_rel = _nonempty_path(item.get("splat_config_path"), "splat_config_path")
            direct_src = _nonempty_path(item.get("src_path"), "src_path")
            if splat_rel is None:
                # Assets such as the HD executable have no source/config pair.
                # They are not a scanner root and must not cause a guessed root.
                if direct_src is not None:
                    source_paths.append(direct_src)
                continue
            try:
                validate_relative_path(splat_rel, "splat_config_path")
            except (SearchValidationError, TypeError, ValueError) as exc:
                raise DonorScanConfigurationError(
                    f"asset file {index} has an unsafe splat_config_path"
                ) from exc
            if not splat_rel.startswith("config/"):
                raise DonorScanConfigurationError(
                    "splat_config_path must remain under config/"
                )
            if not splat_rel.lower().startswith(f"config/splat.{version}."):
                raise DonorScanConfigurationError(
                    f"splat_config_path does not belong to pinned {version}: {splat_rel}"
                )
            config_paths.append(splat_rel)
        if not config_paths and not source_paths:
            raise DonorScanConfigurationError(
                f"asset configuration has no source-bearing entries: {assets_rel}"
            )
    else:
        # Saturn has no splat asset manifest for its PRG inputs.  Every PRG
        # config is a pinned source/assembly declaration and is scanned once.
        for path in sorted(config_root.joinpath("saturn").glob(_SATURN_CONFIG_GLOB)):
            try:
                path.relative_to(root)
            except ValueError:
                raise DonorScanConfigurationError("Saturn configuration escapes repository")
            config_paths.append(path.relative_to(root).as_posix())
        if not config_paths:
            raise DonorScanConfigurationError(
                "Saturn requires config/saturn/*.prg.yaml"
            )

    # Parse each referenced config and collect only its options roots.
    for config_rel in tuple(sorted(set(config_paths))):
        config_path = _safe_repo_path(root, config_rel, "platform configuration", directory=False)
        document = _load_config(config_path, verified_texts=verified_texts)
        # The assets manifest is itself a required pinned configuration, but
        # its entries point at splat configs and source roots rather than
        # carrying one ``options`` block of its own.  Validate and archive it
        # above, then derive roots from the referenced splat documents below.
        if version in _ASSET_CONFIG_VERSIONS and config_rel == f"config/assets.{version}.yaml":
            continue
        options = document.get("options", document)
        if not isinstance(options, Mapping):
            raise DonorScanConfigurationError(f"platform options are missing: {config_rel}")
        source_rel = _nonempty_path(options.get("src_path"), "src_path")
        asm_rel = _nonempty_path(options.get("asm_path"), "asm_path")
        if source_rel is not None:
            source_paths.append(source_rel)
        if asm_rel is not None:
            assembly_paths.append(asm_rel)
        if source_rel is None and asm_rel is None:
            raise DonorScanConfigurationError(
                f"platform configuration has no source or assembly root: {config_rel}"
            )

    # De-duplicate while keeping a deterministic lexical order.  Validate all
    # roots now, before enumerating either source family.
    source_paths = sorted(set(source_paths))
    assembly_paths = sorted(set(assembly_paths))
    if not source_paths:
        raise DonorScanConfigurationError(f"no source root configured for {version}")
    if not assembly_paths:
        raise DonorScanConfigurationError(f"no assembly root configured for {version}")
    for path in source_paths:
        _safe_repo_path(root, path, "src_path", directory=True)
    for path in assembly_paths:
        _safe_repo_path(root, path, "asm_path", directory=True)
    return PlatformRoots(
        version=version,
        config_paths=tuple(sorted(set(config_paths))),
        source_roots=tuple(source_paths),
        assembly_roots=tuple(assembly_paths),
    )


def _archive_artifact_path(reference: ArtifactRef, label: str) -> None:
    """Require a reference to resolve to an object owned by this archive."""

    if not isinstance(reference, ArtifactRef):
        raise DonorScanInputError(f"{label} is not a typed artifact reference")
    path = reference.path
    if (
        not path.startswith("artifacts/")
        or "\\" in path
        or Path(path).as_posix() != path
        or path.endswith("/")
    ):
        raise DonorScanInputError(f"{label} must remain under the archive artifacts root")


def _verified_archive_bytes(
    archive: ContentAddressedArchive,
    reference: ArtifactRef,
    *,
    label: str,
    expected_hash: Optional[str] = None,
    expected_size: Optional[int] = None,
) -> bytes:
    _archive_artifact_path(reference, label)
    try:
        data = archive.verify(reference)
    except (ArchiveError, SearchValidationError, TypeError, ValueError) as exc:
        raise DonorScanInputError(f"{label} is missing or corrupt") from exc
    if expected_hash is not None and reference.content_hash != expected_hash:
        raise DonorScanInputError(f"{label} hash does not match its manifest entry")
    if expected_size is not None and reference.byte_size != expected_size:
        raise DonorScanInputError(f"{label} size does not match its manifest entry")
    if expected_hash is not None and hash_bytes(data) != expected_hash:
        raise DonorScanInputError(f"{label} bytes do not match its manifest entry")
    if expected_size is not None and len(data) != expected_size:
        raise DonorScanInputError(f"{label} bytes have the wrong size")
    return data


def _load_snapshot_manifest(
    revision: DonorRevision,
    *,
    archive: ContentAddressedArchive,
) -> tuple[dict[str, _SnapshotFile], str, bytes]:
    """Load and verify the complete archive-owned source snapshot.

    The revision source artifact names the canonical manifest.  Each manifest
    entry names a second archive object containing the bytes for one configured
    config, source, or assembly path.  The checkout is deliberately absent from
    this operation: an old manifest can never be paired with newer mutable
    files.
    """

    reference = revision.source_artifact
    if reference.media_type != "application/json" or not reference.path.endswith(".json"):
        raise DonorScanInputError(
            "pinned revision source artifact must be an archive JSON snapshot manifest"
        )
    raw_manifest = _verified_archive_bytes(
        archive,
        reference,
        label="pinned revision source artifact",
    )
    try:
        value = json.loads(raw_manifest.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError, TypeError) as exc:
        raise DonorScanInputError(
            "pinned revision source artifact is not valid JSON"
        ) from exc
    if not isinstance(value, Mapping):
        raise DonorScanInputError("source snapshot manifest must be an object")
    if set(value) != {"protocol", "version", "revision", "files"}:
        raise DonorScanInputError(
            "source snapshot manifest fields do not match its protocol"
        )
    try:
        if canonical_bytes(value) != raw_manifest:
            raise DonorScanInputError("source snapshot manifest is not canonical JSON")
    except (TypeError, ValueError) as exc:
        raise DonorScanInputError("source snapshot manifest cannot be canonicalized") from exc
    if value.get("protocol") != DONOR_SNAPSHOT_MANIFEST_PROTOCOL:
        raise DonorScanInputError("source snapshot manifest protocol is unsupported")
    if value.get("version") != revision.version:
        raise DonorScanInputError(
            "source snapshot manifest version does not match the pinned revision"
        )
    if value.get("revision") != revision.revision:
        raise DonorScanInputError(
            "source snapshot manifest revision does not match the pinned revision"
        )
    files = value.get("files")
    if not isinstance(files, list) or not files:
        raise DonorScanInputError("source snapshot manifest files must be a nonempty list")

    result: dict[str, _SnapshotFile] = {}
    paths: list[str] = []
    for index, entry in enumerate(files):
        if not isinstance(entry, Mapping) or set(entry) != {
            "path",
            "kind",
            "content_hash",
            "byte_size",
            "artifact",
        }:
            raise DonorScanInputError(
                f"source snapshot file entry {index} does not match its protocol"
            )
        path = entry.get("path")
        if (
            not isinstance(path, str)
            or "\\" in path
            or Path(path).as_posix() != path
            or path == DONOR_SNAPSHOT_MANIFEST_FILENAME
            or path.startswith("artifacts/")
        ):
            raise DonorScanInputError(
                f"source snapshot file entry {index} has an unsafe path"
            )
        try:
            validate_relative_path(path, f"source snapshot file {index} path")
        except (SearchValidationError, TypeError, ValueError) as exc:
            raise DonorScanInputError(
                f"source snapshot file entry {index} has an unsafe path"
            ) from exc
        kind = entry.get("kind")
        if kind not in DONOR_SNAPSHOT_FILE_KINDS:
            raise DonorScanInputError(
                f"source snapshot file entry {index} has an unsupported kind"
            )
        try:
            content_hash = validate_hash(
                entry.get("content_hash"),
                f"source snapshot file {index} content_hash",
            )
        except (SearchValidationError, TypeError, ValueError) as exc:
            raise DonorScanInputError(
                f"source snapshot file entry {index} has an invalid content hash"
            ) from exc
        byte_size = entry.get("byte_size")
        if isinstance(byte_size, bool) or not isinstance(byte_size, int) or byte_size < 0:
            raise DonorScanInputError(
                f"source snapshot file entry {index} has an invalid byte size"
            )
        try:
            artifact = ArtifactRef.from_dict(entry.get("artifact"))
        except (AttributeError, KeyError, SearchValidationError, TypeError, ValueError) as exc:
            raise DonorScanInputError(
                f"source snapshot file entry {index} has an invalid artifact"
            ) from exc
        if path in result:
            raise DonorScanInputError(
                f"source snapshot manifest contains duplicate path: {path}"
            )
        data = _verified_archive_bytes(
            archive,
            artifact,
            label=f"source snapshot file {index} artifact",
            expected_hash=content_hash,
            expected_size=byte_size,
        )
        result[path] = _SnapshotFile(path, kind, artifact, data)
        paths.append(path)
    if paths != sorted(paths) or len(set(paths)) != len(paths):
        raise DonorScanInputError(
            "source snapshot manifest files must be sorted and unique"
        )
    kinds = {item.kind for item in result.values()}
    missing_kinds = set(DONOR_SNAPSHOT_FILE_KINDS).difference(kinds)
    if missing_kinds:
        raise DonorScanInputError(
            "source snapshot manifest does not bind every file family: "
            + ",".join(sorted(missing_kinds))
        )
    return result, reference.content_hash, raw_manifest


def _materialize_snapshot(
    files: Mapping[str, _SnapshotFile],
    manifest_bytes: bytes,
    *,
    root: Path,
) -> None:
    """Materialize verified archive bytes under a private, read-only root."""

    try:
        root.mkdir(parents=True, exist_ok=False)
    except (FileExistsError, OSError) as exc:
        raise DonorScanInputError("immutable source snapshot root cannot be created") from exc
    for relative, item in sorted(files.items()):
        try:
            target = (root / Path(relative)).resolve(strict=False)
            target.relative_to(root.resolve(strict=False))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(item.data)
            target.chmod(0o444)
        except (OSError, RuntimeError, ValueError) as exc:
            raise DonorScanInputError(
                "immutable source snapshot cannot be materialized: " + relative
            ) from exc
    try:
        manifest_path = root / DONOR_SNAPSHOT_MANIFEST_FILENAME
        manifest_path.write_bytes(manifest_bytes)
        manifest_path.chmod(0o444)
    except OSError as exc:
        raise DonorScanInputError(
            "immutable source snapshot manifest cannot be materialized"
        ) from exc


def _verify_snapshot_inputs(
    manifest: Mapping[str, _SnapshotFile],
    *,
    root: Path,
    roots: PlatformRoots,
) -> tuple[dict[Path, str], dict[str, bytes]]:
    """Verify the materialized snapshot covers exactly configured inputs."""

    source_root_paths = tuple(
        _safe_repo_path(root, path, "src_path", directory=True)
        for path in roots.source_roots
    )
    assembly_root_paths = tuple(
        _safe_repo_path(root, path, "asm_path", directory=True)
        for path in roots.assembly_roots
    )
    source_files: list[Path] = []
    for source_root in source_root_paths:
        source_files.extend(_all_files(root=source_root, repo=root, suffixes=_SOURCE_SUFFIXES))
    source_files = sorted(set(source_files), key=lambda path: path.relative_to(root).as_posix())
    assembly_files: list[Path] = []
    for assembly_root in assembly_root_paths:
        assembly_files.extend(_all_files(root=assembly_root, repo=root, suffixes=_ASSEMBLY_SUFFIXES))
    assembly_files = sorted(set(assembly_files), key=lambda path: path.relative_to(root).as_posix())
    expected_paths = {
        *roots.config_paths,
        *(path.relative_to(root).as_posix() for path in source_files),
        *(path.relative_to(root).as_posix() for path in assembly_files),
    }
    actual_paths = set(manifest)
    if actual_paths != expected_paths:
        missing = sorted(expected_paths.difference(actual_paths))
        extra = sorted(actual_paths.difference(expected_paths))
        details = []
        if missing:
            details.append("missing " + ", ".join(missing[:3]))
        if extra:
            details.append("unexpected " + ", ".join(extra[:3]))
        raise DonorScanInputError(
            "source snapshot manifest does not cover the configured files"
            + (": " + "; ".join(details) if details else "")
        )
    texts: dict[Path, str] = {}
    raw_files: dict[str, bytes] = {}
    for relative in sorted(expected_paths):
        path = _safe_repo_path(root, relative, "source snapshot input", directory=False)
        data = _read_bytes(path, "source snapshot input")
        expected = manifest[relative]
        expected_kind = (
            "config"
            if relative in set(roots.config_paths)
            else "source"
            if relative in {
                path.relative_to(root).as_posix() for path in source_files
            }
            else "assembly"
        )
        if expected.kind != expected_kind:
            raise DonorScanInputError(
                f"source snapshot file kind does not match configured path: {relative}"
            )
        if data != expected.data or hash_bytes(data) != expected.artifact.content_hash:
            raise DonorScanInputError(
                "materialized source snapshot bytes differ from the verified archive: "
                + relative
            )
        raw_files[relative] = data
        texts[path] = _decode_text(data, path, "source snapshot input")
    return texts, raw_files


def _strip_c_comments(text: str) -> str:
    # Keep offsets stable for brace matching.  Replacing a multi-line comment
    # with one space would make the scrubbed function opening point at the
    # wrong byte in the original source.
    def blank(match: re.Match[str]) -> str:
        return "".join("\n" if char == "\n" else " " for char in match.group(0))

    return _C_COMMENT_RE.sub(blank, text)


def _matching_brace(text: str, opening: int) -> int:
    depth = 0
    in_string: Optional[str] = None
    escaped = False
    in_block_comment = False
    i = opening
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_block_comment:
            if char == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_string is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            i += 1
            continue
        if char == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if char in "\"'":
            in_string = char
            i += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise DonorScanInputError("unterminated C function body")


def _parse_c_file(
    path: Path,
    *,
    repo: Path,
    text: Optional[str] = None,
) -> tuple[_CFunction, ...]:
    if text is None:
        text = _read_text(path, "C source")
    scrubbed = _strip_c_comments(text)
    includes = tuple(sorted(set(_INCLUDE_RE.findall(scrubbed))))
    types = tuple(sorted(set(_TYPEDEF_RE.findall(scrubbed)) | set(_STRUCT_RE.findall(scrubbed))))
    functions: list[_CFunction] = []
    for match in _C_FUNCTION_RE.finditer(scrubbed):
        name = match.group("export") or match.group("name")
        if not name or name in _CONTROL_IDENTIFIERS:
            continue
        opening = scrubbed.find("{", match.start(), match.end())
        if opening < 0:
            continue
        closing = _matching_brace(text, opening)
        rel = path.relative_to(repo).as_posix()
        functions.append(
            _CFunction(
                path=path,
                relative_path=rel,
                name=name,
                body=text[opening : closing + 1],
                includes=includes,
                types=types,
            )
        )
    return tuple(functions)


def _declaration_closure(
    function: _CFunction,
    *,
    repo: Path,
    source_roots: Sequence[Path],
    snapshot_texts: Optional[Mapping[Path, str]] = None,
) -> dict[str, Any]:
    """Collect a bounded, path-safe closure of quoted C declarations."""

    includes = set(function.includes)
    types = set(function.types)
    files: set[str] = {function.relative_path}
    pending = list(function.includes)
    visited: set[Path] = set()
    while pending:
        include = pending.pop(0)
        if not include or include.startswith("<"):
            continue
        candidates = [function.path.parent / include]
        candidates.extend(root / include for root in source_roots)
        selected: Optional[Path] = None
        for candidate in candidates:
            try:
                resolved = candidate.resolve(strict=False)
                resolved.relative_to(repo)
            except (OSError, RuntimeError, ValueError):
                continue
            if resolved.is_file():
                selected = resolved
                break
        if selected is None or selected in visited:
            continue
        if snapshot_texts is not None and selected not in snapshot_texts:
            # A header not listed in the immutable manifest is not allowed to
            # influence evidence.  The configured source-file set normally
            # includes every header, so this is also a useful fail-closed
            # guard for unusual include paths.
            continue
        visited.add(selected)
        files.add(selected.relative_to(repo).as_posix())
        included_text = (
            snapshot_texts[selected]
            if snapshot_texts is not None
            else _read_text(selected, "declaration source")
        )
        text = _strip_c_comments(included_text)
        nested_includes = _INCLUDE_RE.findall(text)
        includes.update(nested_includes)
        pending.extend(item for item in nested_includes if item not in visited)
        types.update(_TYPEDEF_RE.findall(text))
        types.update(_STRUCT_RE.findall(text))
    return {
        "includes": tuple(sorted(includes)),
        "types": tuple(sorted(types)),
        "files": tuple(sorted(files)),
        "callees": _called_identifiers(function.body, own_name=function.name),
    }


def _safe_numbers(text: str) -> tuple[int, ...]:
    # Large address-shaped values are not useful semantic constants and can
    # accidentally preserve a version-specific placement.  Keep only compact
    # source literals, with a stable integer representation.
    result: set[int] = set()
    text = _C_STRING_RE.sub(" ", _strip_c_comments(text))
    for raw in _NUMBER_RE.findall(text):
        try:
            value = int(raw, 16 if raw.lstrip("-").lower().startswith("0x") else 10)
        except ValueError:
            continue
        if 0 <= value <= 0xFFFF:
            result.add(value)
    return tuple(sorted(result))


def _normalise_c_tokens(body: str) -> tuple[str, ...]:
    scrubbed = _strip_c_comments(body)
    scrubbed = _C_STRING_RE.sub(" STR ", scrubbed)
    tokens: list[str] = []
    for token in _C_TOKEN_RE.findall(scrubbed):
        if token.isspace():
            continue
        if _NUMBER_RE.fullmatch(token):
            try:
                number = int(token, 16 if token.lstrip("-").lower().startswith("0x") else 10)
            except ValueError:
                tokens.append("NUM")
            else:
                tokens.append(str(number) if number <= 0xFFFF else "NUM")
        elif _IDENT_RE.fullmatch(token):
            tokens.append(token.lower())
        else:
            tokens.append(token)
    return tuple(tokens)


def _called_identifiers(body: str, *, own_name: str) -> tuple[str, ...]:
    scrubbed = _strip_c_comments(body)
    names = {
        match.group(1)
        for match in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", scrubbed)
        if match.group(1) not in _CONTROL_IDENTIFIERS and match.group(1) != own_name
    }
    return tuple(sorted(names))


def _strip_asm_comments(line: str, *, version: str) -> str:
    # Address comments emitted by splat are deliberately discarded.  A
    # comment is provenance, not a semantic instruction operand.  ``#`` is an
    # inline comment delimiter in the MIPS trees, but it introduces immediate
    # operands in both ARM-like PSPEU and SH-like Saturn assembly.  Applying
    # the MIPS rule to every platform silently truncates those operands before
    # the shared signature boundary.
    stripped = _ASM_COMMON_COMMENT_RE.sub(" ", line).strip()
    if version in {"us", "hd"}:
        stripped = re.sub(r"#[^\n]*", " ", stripped).strip()
    elif version == "pspeu":
        stripped = re.sub(r"\s+@[^\n]*$", " ", stripped).strip()
    elif version == "saturn":
        stripped = re.sub(r"\s+![^\n]*$", " ", stripped).strip()
    elif stripped.startswith("#"):
        stripped = ""
    if version in {"pspeu", "saturn"} and stripped.startswith("#"):
        stripped = ""
    return stripped


def _normalise_asm_operand(operand: str) -> str:
    # Keep the compatibility helper, but make the shared module the sole
    # owner of operand categories used in semantic signatures.
    return _shared_normalize_operands("", operand)


def _parse_asm_file(
    path: Path,
    *,
    repo: Path,
    version: str,
    text: Optional[str] = None,
) -> tuple[_AsmFunction, ...]:
    if text is None:
        text = _read_text(path, "assembly source")
    functions: list[_AsmFunction] = []
    current_name: Optional[str] = None
    current_instructions: list[tuple[str, str]] = []
    current_labels: list[str] = []

    def finish() -> None:
        nonlocal current_name, current_instructions, current_labels
        if current_name is not None and current_instructions:
            functions.append(
                _AsmFunction(
                    path=path,
                    relative_path=path.relative_to(repo).as_posix(),
                    name=current_name,
                    instructions=tuple(current_instructions),
                    labels=tuple(current_labels),
                )
            )
        current_name = None
        current_instructions = []
        current_labels = []

    for raw_line in text.splitlines():
        line = _strip_asm_comments(raw_line, version=version)
        if not line:
            continue
        glabel = _ASM_GLABEL_RE.match(line)
        if glabel:
            finish()
            current_name = glabel.group(1).lstrip(".$")
            continue
        label = _ASM_LABEL_RE.match(line)
        if label:
            label_name = label.group(1)
            if current_name is None and not label_name.startswith("."):
                current_name = label_name
            elif label_name.startswith("."):
                current_labels.append(label_name)
            continue
        if _ASM_DATA_DIRECTIVE_RE.match(line):
            # Data bytes, section/layout directives, and assembler metadata
            # are valid input in a real tree, but none is stable instruction
            # evidence.  Omit only this line so later safe instructions and
            # sibling functions remain usable.
            continue
        if _ASM_RELOCATION_RE.search(line):
            # Relocation syntax is placement-dependent.  It must never enter a
            # donor signature, but an unrelated relocation must not abort a
            # whole platform scan.
            continue
        instruction = _ASM_INSTRUCTION_RE.match(line)
        if not instruction:
            continue
        mnemonic = instruction.group(1).lower()
        operands = instruction.group(2).strip()
        if has_numeric_branch_target(mnemonic, operands):
            # A numeric displacement is not stable CFG evidence.  Keep
            # scanning the function and omit this branch record.
            continue
        if current_name is None:
            current_name = path.stem
        # Store source operands until the shared selector boundary.  Storing
        # pre-normalized categories here would make a second parser user
        # produce a different signature for the same assembly.
        current_instructions.append((mnemonic, operands))
    finish()
    return tuple(functions)


def _instruction_signature(asm: Optional[_AsmFunction], c_tokens: tuple[str, ...]) -> str:
    payload: Mapping[str, Any]
    if asm is None:
        payload = {"source_tokens": c_tokens, "assembly": False}
    else:
        return _shared_instruction_signature(asm.instructions)
    return hash_canonical({"protocol": DONOR_SIGNATURE_PROTOCOL, "kind": "instruction", **payload})


def _cfg_signature(asm: Optional[_AsmFunction], c_tokens: tuple[str, ...]) -> str:
    if asm is None:
        blocks: tuple[Mapping[str, Any], ...] = (
            {"instructions": tuple(token for token in c_tokens if token in {"if", "for", "while", "return"})},
        )
    else:
        return _shared_cfg_signature(asm.instructions)
    return hash_canonical({"protocol": DONOR_SIGNATURE_PROTOCOL, "kind": "cfg", "blocks": blocks})


def _dataflow_signature(asm: Optional[_AsmFunction], c_function: _CFunction) -> str:
    if asm is None:
        calls = _called_identifiers(c_function.body, own_name=c_function.name)
        payload: Mapping[str, Any] = {
            "calls": calls,
            "loads": 0,
            "stores": 0,
            "returns": c_function.body.count("return"),
        }
    else:
        return _shared_dataflow_signature(asm.instructions)
    return hash_canonical({"protocol": DONOR_SIGNATURE_PROTOCOL, "kind": "dataflow", **payload})


def _source_signature(c_tokens: tuple[str, ...]) -> str:
    return hash_canonical(
        {
            "protocol": DONOR_SIGNATURE_PROTOCOL,
            "kind": "source",
            "tokens": c_tokens,
        }
    )


_FORBIDDEN_EVIDENCE_KEYS = frozenset(
    {
        "body",
        "raw_body",
        "bytes",
        "registers",
        "relocations",
        "branch_displacements",
    }
)


def _reject_forbidden_evidence_tree(value: Any, *, label: str) -> None:
    """Reject forbidden evidence recursively before constructing a record."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise DonorScanUnsafeError(f"{label} keys must be strings")
            if key.strip().lower() in _FORBIDDEN_EVIDENCE_KEYS:
                raise DonorScanUnsafeError(
                    f"{label} contains forbidden semantic field: {key}"
                )
            _reject_forbidden_evidence_tree(item, label=f"{label}.{key}")
        return
    if isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            _reject_forbidden_evidence_tree(item, label=f"{label}[{index}]")
        return
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    raise DonorScanUnsafeError(f"{label} contains an unsupported semantic value")


def _validate_semantic_record_parts(
    declarations: Mapping[str, Any],
    constants: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> None:
    for label, value in (
        ("declarations", declarations),
        ("constants", constants),
        ("metadata", metadata),
    ):
        _reject_forbidden_evidence_tree(value, label=label)


def _all_files(root: Path, *, repo: Path, suffixes: frozenset[str]) -> tuple[Path, ...]:
    found: set[Path] = set()
    try:
        candidates = root.rglob("*")
    except OSError as exc:
        raise DonorScanConfigurationError(f"cannot enumerate configured root: {root}") from exc
    for path in candidates:
        try:
            resolved = path.resolve(strict=False)
            resolved.relative_to(repo)
        except (OSError, RuntimeError, ValueError) as exc:
            raise DonorScanConfigurationError(
                f"configured source entry escapes repository: {path}"
            ) from exc
        normalized_suffixes = {item.lower() for item in suffixes}
        if path.is_file() and path.suffix.lower() in normalized_suffixes:
            found.add(resolved)
    return tuple(sorted(found, key=lambda item: item.relative_to(repo).as_posix()))


def _overlay_for(relative_source_path: str, *, version: str) -> str:
    parts = Path(relative_source_path).parts
    if parts and parts[0].lower() == "src":
        parts = parts[1:-1]
    else:
        parts = parts[:-1]
    overlay = "/".join(part.upper() for part in parts if part)
    return overlay or version.upper()


def _assembly_candidates(
    source: _CFunction,
    *,
    repo: Path,
    assembly_roots: Sequence[Path],
    source_roots: Sequence[Path] = (),
    by_symbol: Mapping[str, tuple[_AsmFunction, ...]],
    snapshot_texts: Optional[Mapping[Path, str]] = None,
    version: str,
) -> Optional[_AsmFunction]:
    """Resolve assembly by configured relative path before symbol fallback."""

    source_path = Path(source.path)
    relative_candidates: list[Path] = []
    for source_root in source_roots:
        try:
            relative = source_path.relative_to(source_root)
        except ValueError:
            continue
        relative_candidates.extend(
            root / relative.with_suffix(suffix)
            for root in assembly_roots
            for suffix in (".s", ".S", ".asm", ".inc")
        )
    # A legacy flat tree has no source-root-relative match.  Its basename is a
    # compatibility hint only and is accepted below only if the file contains
    # the exact source symbol.
    if not relative_candidates:
        relative_candidates.extend(
            root / (Path(source.relative_path).stem + suffix)
            for root in assembly_roots
            for suffix in (".s", ".S", ".asm", ".inc")
        )
    for candidate in relative_candidates:
        try:
            if not candidate.is_file():
                continue
            resolved = candidate.resolve(strict=False)
            parsed = _parse_asm_file(
                resolved,
                repo=repo,
                version=version,
                text=snapshot_texts[resolved] if snapshot_texts is not None else None,
            )
        except (OSError, KeyError):
            continue
        for item in parsed:
            if item.name == source.name:
                return item
    # Only a globally unique symbol is safe when the configured paths do not
    # mirror the source tree.  Never select the first function in an unrelated
    # assembly file just because its basename happens to match.
    candidates = by_symbol.get(source.name, ())
    return candidates[0] if len(candidates) == 1 else None


def _snapshot_file_identity(
    manifest: Mapping[str, _SnapshotFile],
    paths: Iterable[Path],
    *,
    root: Path,
    kind: str,
    version: str,
    revision: str,
) -> str:
    rows: list[dict[str, Any]] = []
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        entry = manifest[relative]
        rows.append(
            {
                "path": relative,
                "kind": entry.kind,
                "content_hash": entry.artifact.content_hash,
                "byte_size": entry.artifact.byte_size,
            }
        )
    return hash_canonical(
        {
            "protocol": DONOR_SNAPSHOT_MANIFEST_PROTOCOL,
            "kind": kind,
            "version": version,
            "revision": revision,
            "files": rows,
        }
    )


def _scan_materialized_revision(
    revision: DonorRevision | Mapping[str, Any],
    *,
    repo: Path | str,
    archive: ContentAddressedArchive,
    snapshot_manifest: Mapping[str, _SnapshotFile],
    snapshot_identity: str,
) -> tuple[DonorEvidence, ...]:
    """Scan one already materialized immutable revision snapshot."""

    typed_revision = _as_revision(revision)
    root = _as_repo(repo)
    # Configuration is parsed from the materialized snapshot itself.  The
    # caller has already verified every archive object, so this is the only
    # discovery pass and no mutable checkout path is consulted.
    roots = discover_platform_roots(typed_revision.version, repo=root)
    snapshot_texts, _raw_snapshot_files = _verify_snapshot_inputs(
        snapshot_manifest,
        root=root,
        roots=roots,
    )
    source_files = tuple(
        sorted(
            (
                path
                for path in snapshot_texts
                if path.suffix.lower() in {item.lower() for item in _SOURCE_SUFFIXES}
            ),
            key=lambda path: path.relative_to(root).as_posix(),
        )
    )
    asm_files = tuple(
        sorted(
            (
                path
                for path in snapshot_texts
                if path.suffix.lower() in {item.lower() for item in _ASSEMBLY_SUFFIXES}
            ),
            key=lambda path: path.relative_to(root).as_posix(),
        )
    )
    config_identity = hash_canonical(
        {
            "protocol": DONOR_SCAN_PROTOCOL,
            "version": typed_revision.version,
            "revision": typed_revision.revision,
            "configs": {
                path: snapshot_manifest[path].artifact.content_hash
                for path in roots.config_paths
            },
        }
    )
    source_root_paths = tuple(
        _safe_repo_path(root, path, "src_path", directory=True)
        for path in roots.source_roots
    )
    assembly_root_paths = tuple(
        _safe_repo_path(root, path, "asm_path", directory=True)
        for path in roots.assembly_roots
    )
    source_identity = _snapshot_file_identity(
        snapshot_manifest,
        source_files,
        root=root,
        kind="source",
        version=typed_revision.version,
        revision=typed_revision.revision,
    )
    assembly_identity = _snapshot_file_identity(
        snapshot_manifest,
        asm_files,
        root=root,
        kind="assembly",
        version=typed_revision.version,
        revision=typed_revision.revision,
    )
    platform_identity = hash_canonical(
        {
            "protocol": DONOR_SNAPSHOT_PROTOCOL,
            "version": typed_revision.version,
            "config_paths": roots.config_paths,
            "source_roots": roots.source_roots,
            "assembly_roots": roots.assembly_roots,
            "config_identity": config_identity,
            "source_identity": source_identity,
            "assembly_identity": assembly_identity,
            "snapshot_identity": snapshot_identity,
        }
    )

    parsed_sources: list[_CFunction] = []
    for path in source_files:
        parsed_sources.extend(
            _parse_c_file(path, repo=root, text=snapshot_texts[path])
        )
    parsed_asm: list[_AsmFunction] = []
    for path in asm_files:
        parsed_asm.extend(
            _parse_asm_file(
                path,
                repo=root,
                version=typed_revision.version,
                text=snapshot_texts[path],
            )
        )
    by_symbol: dict[str, tuple[_AsmFunction, ...]] = {}
    grouped: dict[str, list[_AsmFunction]] = {}
    for function in parsed_asm:
        grouped.setdefault(function.name, []).append(function)
    by_symbol = {name: tuple(values) for name, values in grouped.items()}

    evidence: list[DonorEvidence] = []
    matched_assembly: set[_AsmFunction] = set()
    for function in parsed_sources:
        asm = _assembly_candidates(
            function,
            repo=root,
            assembly_roots=assembly_root_paths,
            source_roots=source_root_paths,
            by_symbol=by_symbol,
            snapshot_texts=snapshot_texts,
            version=typed_revision.version,
        )
        c_tokens = _normalise_c_tokens(function.body)
        declarations = _declaration_closure(
            function,
            repo=root,
            source_roots=source_root_paths,
            snapshot_texts=snapshot_texts,
        )
        callees = _called_identifiers(function.body, own_name=function.name)
        declarations["callees"] = callees
        constants = {
            "integer_literals": _safe_numbers(function.body),
        }
        instruction_signature = _instruction_signature(asm, c_tokens)
        cfg_signature = _cfg_signature(asm, c_tokens)
        dataflow_signature = _dataflow_signature(asm, function)
        source_signature = _source_signature(c_tokens)
        source_rel = function.relative_path
        asm_rel = asm.relative_path if asm is not None else None
        if asm is not None:
            matched_assembly.add(asm)
        overlay = _overlay_for(source_rel, version=typed_revision.version)
        recipient_id = f"{typed_revision.version}:{overlay}:{function.name}"
        semantic_payload = {
            "protocol": DONOR_SIGNATURE_PROTOCOL,
            "instruction": instruction_signature,
            "cfg": cfg_signature,
            "dataflow": dataflow_signature,
            "source": source_signature,
            "config": config_identity,
            "declarations": declarations,
            "constants": constants,
        }
        donor_id = hash_canonical(
            {
                "protocol": DONOR_SCAN_PROTOCOL,
                "revision": typed_revision.revision,
                "source": source_rel,
                "symbol": function.name,
                "semantic": semantic_payload,
            }
        )
        metadata = {
            "scanner_protocol": DONOR_SCAN_PROTOCOL,
            "platform": typed_revision.version,
            "source_path": source_rel,
            "assembly_path": asm_rel,
            "config_paths": roots.config_paths,
            "config_identity": config_identity,
            "source_identity": source_identity,
            "assembly_identity": assembly_identity,
            "platform_identity": platform_identity,
            "snapshot_identity": snapshot_identity,
            "snapshot_manifest": typed_revision.source_artifact.to_dict(),
            "source_file_hash": snapshot_manifest[source_rel].artifact.content_hash,
            "source_file_size": snapshot_manifest[source_rel].artifact.byte_size,
            "compatibility": {
                "language": "c",
                "assembly_available": asm is not None,
                "source_revision": typed_revision.revision,
            },
        }
        # A malformed or future unsafe semantic extension invalidates only
        # this donor record.  The platform scan must retain its other safe
        # records rather than turning one refusal into a platform-wide abort.
        try:
            _validate_semantic_record_parts(declarations, constants, metadata)
        except DonorScanUnsafeError:
            continue
        evidence.append(
            DonorEvidence(
                donor_id=donor_id,
                recipient_id=recipient_id,
                version=typed_revision.version,
                source=typed_revision.source_artifact,
                match_kind="exact_symbol_path",
                signature=hash_canonical(semantic_payload),
                body=None,
                symbol=function.name,
                instruction_signature=instruction_signature,
                cfg_signature=cfg_signature,
                dataflow_signature=dataflow_signature,
                declarations=declarations,
                constants=constants,
                structural_differences=("assembly_missing",) if asm is None else (),
                compatible=True,
                metadata=metadata,
            )
        )
    # Assembly-only functions are retained as semantic evidence as well.  The
    # absence of a C body is a structural fact, never an invitation to copy
    # the assembly text into the archive.
    empty_c = _CFunction(
        path=root,
        relative_path="",
        name="",
        body="{}",
        includes=(),
        types=(),
    )
    for asm in parsed_asm:
        if asm in matched_assembly:
            continue
        c_tokens: tuple[str, ...] = ()
        instruction_signature = _instruction_signature(asm, c_tokens)
        cfg_signature = _cfg_signature(asm, c_tokens)
        dataflow_signature = _dataflow_signature(asm, empty_c)
        source_signature = _source_signature(c_tokens)
        declarations = {"includes": (), "types": (), "files": (), "callees": ()}
        constants = {"integer_literals": ()}
        semantic_payload = {
            "protocol": DONOR_SIGNATURE_PROTOCOL,
            "instruction": instruction_signature,
            "cfg": cfg_signature,
            "dataflow": dataflow_signature,
            "source": source_signature,
            "config": config_identity,
            "declarations": declarations,
            "constants": constants,
        }
        metadata = {
            "scanner_protocol": DONOR_SCAN_PROTOCOL,
            "platform": typed_revision.version,
            "source_path": asm.relative_path,
            "assembly_path": asm.relative_path,
            "config_paths": roots.config_paths,
            "config_identity": config_identity,
            "source_identity": source_identity,
            "assembly_identity": assembly_identity,
            "platform_identity": platform_identity,
            "snapshot_identity": snapshot_identity,
            "snapshot_manifest": typed_revision.source_artifact.to_dict(),
            "assembly_file_hash": snapshot_manifest[asm.relative_path].artifact.content_hash,
            "assembly_file_size": snapshot_manifest[asm.relative_path].artifact.byte_size,
            "compatibility": {
                "language": "assembly",
                "assembly_available": True,
                "source_revision": typed_revision.revision,
            },
        }
        try:
            _validate_semantic_record_parts(declarations, constants, metadata)
        except DonorScanUnsafeError:
            continue
        overlay = _overlay_for(asm.relative_path, version=typed_revision.version)
        recipient_id = f"{typed_revision.version}:{overlay}:{asm.name}"
        evidence.append(
            DonorEvidence(
                donor_id=hash_canonical(
                    {
                        "protocol": DONOR_SCAN_PROTOCOL,
                        "revision": typed_revision.revision,
                        "source": asm.relative_path,
                        "symbol": asm.name,
                        "semantic": semantic_payload,
                    }
                ),
                recipient_id=recipient_id,
                version=typed_revision.version,
                source=typed_revision.source_artifact,
                match_kind="exact_symbol_path",
                signature=hash_canonical(semantic_payload),
                body=None,
                symbol=asm.name,
                instruction_signature=instruction_signature,
                cfg_signature=cfg_signature,
                dataflow_signature=dataflow_signature,
                declarations=declarations,
                constants=constants,
                structural_differences=("source_missing",),
                compatible=True,
                metadata=metadata,
            )
        )
    evidence.sort(key=lambda item: (item.recipient_id, item.symbol or "", item.donor_id))
    return tuple(evidence)


def scan_repository_revision(
    revision: DonorRevision | Mapping[str, Any],
    *,
    repo: Path | str,
    archive: ContentAddressedArchive,
) -> tuple[DonorEvidence, ...]:
    """Scan one pinned revision from archive-owned bytes only.

    The repo argument is retained as an explicit interface and is checked only
    as a repository-root value.  No file under it is read.  The complete
    snapshot is verified from the archive and copied into a private
    materialization root; all parsing then uses that root.
    """

    typed_revision = _as_revision(revision)
    if not isinstance(archive, ContentAddressedArchive):
        raise DonorScanInputError("scanner needs a ContentAddressedArchive")
    # Keep the repository argument typed and path-safe without allowing it to
    # become an input source.  The materialized snapshot is the only root
    # passed to parsing helpers below.
    _as_repo(repo)
    snapshot_manifest, snapshot_identity, manifest_bytes = _load_snapshot_manifest(
        typed_revision,
        archive=archive,
    )
    with tempfile.TemporaryDirectory(prefix="sotn-donor-snapshot-") as temporary:
        snapshot_root = Path(temporary) / "root"
        _materialize_snapshot(
            snapshot_manifest,
            manifest_bytes,
            root=snapshot_root,
        )
        return _scan_materialized_revision(
            typed_revision,
            repo=snapshot_root,
            archive=archive,
            snapshot_manifest=snapshot_manifest,
            snapshot_identity=snapshot_identity,
        )


def scan_pinned_revisions(
    revisions: Sequence[DonorRevision | Mapping[str, Any]],
    *,
    repo: Path | str,
    archive: ContentAddressedArchive,
    scanner: Optional[
        Callable[..., Iterable[DonorEvidence]]
    ] = None,
) -> tuple[DonorEvidence, ...]:
    """Scan exactly one time per canonical pinned version.

    ``scanner`` is injectable only for tests and higher-level generation code;
    it receives one typed revision plus the same explicit repository and
    archive.  The helper rejects duplicate or incomplete revision sets before
    the first scan and never retries a failed scanner call.
    """

    if not isinstance(revisions, (tuple, list)):
        raise DonorScanInputError("pinned revisions must be an explicit tuple or list")
    typed = tuple(_as_revision(value) for value in revisions)
    if tuple(sorted(item.version for item in typed)) != tuple(sorted(DONOR_VERSIONS)):
        raise DonorScanConfigurationError(
            "one pinned revision for US, HD, PSPEU, and Saturn is required"
        )
    if len({item.version for item in typed}) != len(DONOR_VERSIONS):
        raise DonorScanConfigurationError("pinned revisions must contain one entry per version")
    ordered = tuple(sorted(typed, key=lambda item: DONOR_VERSIONS.index(item.version)))
    worker = scanner or scan_repository_revision
    if not callable(worker):
        raise DonorScanInputError("scanner must be callable")
    all_evidence: list[DonorEvidence] = []
    seen_donor_ids: set[str] = set()
    platform_identities: dict[str, tuple[str, str, str, str]] = {}
    for revision in ordered:
        values = worker(revision, repo=repo, archive=archive)
        if values is None:
            raise DonorScanInputError(f"scanner returned no evidence for {revision.version}")
        try:
            current = tuple(values)
        except (TypeError, ValueError) as exc:
            raise DonorScanInputError(
                f"scanner returned a non-iterable result for {revision.version}"
            ) from exc
        if not current:
            raise DonorScanInputError(
                f"scanner returned no semantic evidence for {revision.version}"
            )
        current = tuple(
            sorted(
                current,
                key=lambda item: (
                    getattr(item, "recipient_id", ""),
                    getattr(item, "symbol", "") or "",
                    getattr(item, "donor_id", ""),
                ),
            )
        )
        current_identity: Optional[tuple[str, str, str, str]] = None
        for evidence in current:
            if not isinstance(evidence, DonorEvidence):
                raise DonorScanInputError("scanner returned an untyped donor record")
            if evidence.donor_id in seen_donor_ids:
                raise DonorScanInputError(
                    "scanner returned duplicate donor identity: " + evidence.donor_id
                )
            seen_donor_ids.add(evidence.donor_id)
            if evidence.version != revision.version or evidence.source != revision.source_artifact:
                raise DonorScanInputError(
                    f"scanner evidence does not match pinned {revision.version}"
                )
            metadata = evidence.metadata
            required_identities = (
                "config_identity",
                "source_identity",
                "assembly_identity",
                "platform_identity",
            )
            if any(
                not isinstance(metadata.get(name), str) or not metadata.get(name)
                for name in required_identities
            ):
                raise DonorScanInputError(
                    f"scanner evidence lacks complete platform identities for {revision.version}"
                )
            identity = tuple(metadata[name] for name in required_identities)
            if current_identity is None:
                current_identity = identity  # type: ignore[assignment]
            elif identity != current_identity:
                raise DonorScanInputError(
                    f"scanner evidence mixes platform identities for {revision.version}"
                )
        if current_identity is None:
            raise DonorScanInputError(
                f"scanner returned no platform identity for {revision.version}"
            )
        platform_identities[revision.version] = current_identity
        all_evidence.extend(current)
    seen: dict[str, str] = {}
    for version, identities in platform_identities.items():
        for index, label in enumerate(("config", "source", "assembly", "platform")):
            identity = identities[index]
            previous = seen.get(f"{label}:{identity}")
            if previous is not None and previous != version:
                raise DonorScanConfigurationError(
                    f"{label} snapshot identity is shared by {previous} and {version}"
                )
            seen[f"{label}:{identity}"] = version
    return tuple(all_evidence)


__all__ = [
    "DONOR_SCAN_PROTOCOL",
    "DONOR_SIGNATURE_PROTOCOL",
    "DONOR_SNAPSHOT_MANIFEST_PROTOCOL",
    "DONOR_SNAPSHOT_MANIFEST_FILENAME",
    "DONOR_SNAPSHOT_FILE_KINDS",
    "DONOR_SNAPSHOT_PROTOCOL",
    "DonorScanConfigurationError",
    "DonorScanError",
    "DonorScanInputError",
    "DonorScanRefusal",
    "DonorScanUnsafeError",
    "PlatformRoots",
    "discover_platform_roots",
    "scan_pinned_revisions",
    "scan_repository_revision",
    "UnsafeDonorEvidence",
]
