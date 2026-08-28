"""Content-addressed, immutable artifacts for an instrumented search run."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional, Union

from .search_types import ArtifactRef, canonical_bytes, hash_bytes, validate_relative_path


class ArchiveError(RuntimeError):
    """Base class for archive failures."""


class ArtifactCollision(ArchiveError):
    """An immutable artifact path already contains different bytes."""


class ArtifactMissing(ArchiveError):
    """A referenced artifact does not exist."""


class ArtifactCorrupt(ArchiveError):
    """A referenced artifact has a wrong size or content hash."""


class InvalidArtifactPath(ArchiveError):
    """An artifact path escaped the run root."""


class InjectedArchiveFault(ArchiveError):
    """Raised by an optional fault hook used by recovery tests."""


FaultHook = Callable[[str, Path], None]


def _safe_category(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise InvalidArtifactPath("artifact category must be nonempty")
    if value in (".", "..") or "/" in value or "\\" in value:
        raise InvalidArtifactPath("artifact category must be one path component")
    return value


def _safe_suffix(value: str) -> str:
    if not value:
        return ""
    if not value.startswith(".") or "/" in value or "\\" in value:
        raise InvalidArtifactPath("artifact suffix must be a file extension")
    return value


class ContentAddressedArchive:
    """Store bytes below ``run_root/artifacts`` under their SHA-256 identity.

    A successful ``put_*`` call is durable before its :class:`ArtifactRef` is
    returned.  Existing files are verified byte-for-byte and are never
    overwritten, which makes retries safe after a process loss.
    """

    def __init__(self, run_root: Union[str, os.PathLike[str]], fault_hook: Optional[FaultHook] = None):
        # Resolve the root once so every later containment check is against the
        # same filesystem location, including when the caller supplied a
        # symlinked run directory.
        try:
            self.run_root = Path(run_root).resolve(strict=False)
        except OSError as exc:
            raise InvalidArtifactPath("run root cannot be resolved") from exc
        self.artifacts_root = self.run_root / "artifacts"
        self.fault_hook = fault_hook

    def _fault(self, point: str, path: Path) -> None:
        if self.fault_hook is not None:
            self.fault_hook(point, path)

    def _checked_path(self, path: Path) -> Path:
        """Resolve a path and require its target to remain beneath run_root."""
        try:
            resolved_root = self.run_root.resolve(strict=False)
            resolved = Path(path).resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise InvalidArtifactPath("artifact path cannot be resolved") from exc
        try:
            resolved.relative_to(resolved_root)
        except ValueError as exc:
            raise InvalidArtifactPath("artifact path escaped run root") from exc
        return resolved

    def _ensure_directory(self, path: Path) -> Path:
        """Create one directory tree while checking every existing component."""
        root = self._checked_path(self.run_root)
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ArchiveError("unable to create run root") from exc
        try:
            relative = Path(path).relative_to(self.run_root)
        except ValueError as exc:
            raise InvalidArtifactPath("artifact directory escaped run root") from exc
        current = root
        for component in relative.parts:
            current = current / component
            if current.exists() or current.is_symlink():
                checked = self._checked_path(current)
                if not checked.is_dir():
                    raise InvalidArtifactPath("artifact path component is not a directory")
                current = checked
                continue
            try:
                current.mkdir()
            except FileExistsError:
                # Recheck a concurrent creator, including a symlink it may
                # have installed between the existence test and mkdir.
                checked = self._checked_path(current)
                if not checked.is_dir():
                    raise InvalidArtifactPath("artifact path component is not a directory")
                current = checked
            except OSError as exc:
                raise ArchiveError("unable to create artifact directory") from exc
            current = self._checked_path(current)
        return current

    def _relative(self, path: Path) -> str:
        resolved = self._checked_path(path)
        try:
            relative = resolved.relative_to(self.run_root.resolve(strict=False))
        except ValueError as exc:
            raise InvalidArtifactPath("artifact escaped run root") from exc
        return relative.as_posix()

    def _path_for(self, digest: str, category: str, suffix: str) -> Path:
        _safe_category(category)
        _safe_suffix(suffix)
        return self.artifacts_root / category / (digest + suffix)

    @staticmethod
    def _digest(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _reference(self, path: Path, media_type: str, data: bytes) -> ArtifactRef:
        return ArtifactRef(
            content_hash="sha256:" + self._digest(data),
            path=self._relative(path),
            media_type=media_type,
            byte_size=len(data),
        )

    def _verify_existing(self, path: Path, data: bytes) -> None:
        checked = self._checked_path(path)
        try:
            existing = checked.read_bytes()
        except FileNotFoundError:
            raise ArtifactMissing(f"artifact disappeared while verifying: {path}")
        except OSError as exc:
            raise ArtifactCorrupt(f"artifact cannot be read: {path}") from exc
        if existing != data:
            raise ArtifactCollision(f"immutable artifact collision at {path}")

    def _publish_exclusive(self, temporary: Path, destination: Path, data: bytes) -> None:
        """Publish one prepared file without replacing a concurrent winner."""
        temporary = self._checked_path(temporary)
        destination = self._checked_path(destination)
        try:
            os.link(str(temporary), str(destination))
        except FileExistsError:
            # A same-content winner is a valid retry only while that winner is
            # still present.  Treat a vanished destination as an interrupted
            # publication, never as a successful reference.
            self._verify_existing(destination, data)
            if not destination.exists():
                raise ArtifactMissing(f"artifact disappeared after verification: {destination}")
            temporary.unlink()
        except OSError as exc:
            raise ArchiveError("atomic artifact publication is unavailable") from exc
        else:
            temporary.unlink()

    def put_bytes(
        self,
        data: bytes,
        *,
        category: str = "objects",
        suffix: str = ".bin",
        media_type: str = "application/octet-stream",
    ) -> ArtifactRef:
        if not isinstance(data, bytes):
            raise TypeError("put_bytes expects bytes")
        if not isinstance(media_type, str) or not media_type:
            raise ArchiveError("media_type must be nonempty")
        digest = self._digest(data)
        destination = self._path_for(digest, category, suffix)
        destination_parent = self._ensure_directory(destination.parent)
        destination = destination_parent / destination.name
        # Resolve the final path before any existence test.  A symlinked
        # category or destination that escapes the run root is rejected.
        destination = self._checked_path(destination)

        # A retry may use a different suffix or category.  Reuse an existing
        # byte-identical object with the same digest instead of creating a
        # second authoritative identity.
        if destination.exists():
            self._verify_existing(destination, data)
            return self._reference(destination, media_type, data)
        for sibling in destination.parent.glob(digest + "*"):
            sibling = self._checked_path(sibling)
            if sibling.is_file():
                self._verify_existing(sibling, data)
                return self._reference(sibling, media_type, data)

        fd, temporary_name = tempfile.mkstemp(
            prefix="." + digest + ".",
            suffix=".tmp",
            dir=str(destination.parent),
        )
        temporary = Path(temporary_name)
        try:
            self._fault("before_artifact_write", temporary)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            self._fault("after_artifact_write", temporary)
            self._fault("before_artifact_rename", destination)
            self._publish_exclusive(temporary, destination, data)
            self._fault("after_artifact_rename", destination)
            self._fsync_directory(destination.parent)
        except Exception:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            raise
        return self._reference(destination, media_type, data)

    def put_text(
        self,
        text: str,
        *,
        category: str = "sources",
        suffix: str = ".c",
        media_type: str = "text/x-c",
    ) -> ArtifactRef:
        if not isinstance(text, str):
            raise TypeError("put_text expects str")
        return self.put_bytes(
            text.encode("utf-8"),
            category=category,
            suffix=suffix,
            media_type=media_type,
        )

    def put_json(
        self,
        value: Any,
        *,
        category: str = "receipts",
        suffix: str = ".json",
        media_type: str = "application/json",
    ) -> ArtifactRef:
        return self.put_bytes(
            canonical_bytes(value),
            category=category,
            suffix=suffix,
            media_type=media_type,
        )

    def put_source(self, source: str) -> ArtifactRef:
        return self.put_text(source, category="sources", suffix=".c", media_type="text/x-c")

    def put_object(self, data: bytes) -> ArtifactRef:
        return self.put_bytes(data, category="objects", suffix=".o", media_type="application/octet-stream")

    def put_patch(self, patch: Any) -> ArtifactRef:
        return self.put_json(patch, category="patches", suffix=".json")

    def put_diff(self, diff: str) -> ArtifactRef:
        return self.put_text(diff, category="diffs", suffix=".txt", media_type="text/plain")

    def put_receipt(self, receipt: Any) -> ArtifactRef:
        return self.put_json(receipt, category="receipts", suffix=".json")

    # Short aliases make the ordering explicit at call sites and ease use by
    # small lane adapters.
    materialize = put_bytes
    write = put_bytes

    def resolve(self, reference: ArtifactRef) -> Path:
        if not isinstance(reference, ArtifactRef):
            reference = ArtifactRef.from_dict(reference)  # type: ignore[arg-type]
        validate_relative_path(reference.path)
        path = self.run_root / Path(reference.path)
        return self._checked_path(path)

    def verify(self, reference: ArtifactRef) -> bytes:
        path = self.resolve(reference)
        try:
            data = path.read_bytes()
        except FileNotFoundError as exc:
            raise ArtifactMissing(str(path)) from exc
        actual = "sha256:" + self._digest(data)
        if actual != reference.content_hash or len(data) != reference.byte_size:
            raise ArtifactCorrupt(f"artifact verification failed for {reference.path}")
        return data

    def exists_and_valid(self, reference: ArtifactRef) -> bool:
        try:
            self.verify(reference)
        except ArchiveError:
            return False
        return True

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        # Windows does not expose a directory descriptor.  The artifact itself
        # is already durable there; on POSIX this closes the rename window.
        try:
            descriptor = os.open(str(path), os.O_RDONLY)
        except (OSError, ValueError):
            return
        try:
            os.fsync(descriptor)
        except OSError:
            pass
        finally:
            os.close(descriptor)


ArtifactArchive = ContentAddressedArchive
SearchArchive = ContentAddressedArchive


__all__ = [
    "ArchiveError", "ArtifactCollision", "ArtifactMissing", "ArtifactCorrupt",
    "InvalidArtifactPath", "InjectedArchiveFault", "ContentAddressedArchive",
    "ArtifactArchive", "SearchArchive",
]
