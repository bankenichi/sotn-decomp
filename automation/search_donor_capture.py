"""Capture configured C donor trees from full Git revisions via the connector.

Source-only snapshots deliberately contain no checkout assembly. Generated
assembly cannot be attributed to a Git commit merely because Git is clean.
The distinct snapshot protocol records that limitation for every consumer.
"""
from __future__ import annotations

import io
import tarfile
import tempfile
from pathlib import Path
from typing import Sequence

from automation.mcp import commands_client
from automation.search_donor_scan import discover_platform_roots
from automation.search_indexed_runtime import (
    DonorSnapshot, DonorSnapshotFile, IndexedRuntimeInputError,
    publish_donor_snapshots,
)
from automation.search_types import validate_relative_path


def capture_pinned_donor_sources(pairs: Sequence[tuple[str, str]], *, repo: Path):
    """Publish four configured source snapshots using immutable commit bytes."""
    if repo.resolve() != commands_client.REPO.resolve():
        raise IndexedRuntimeInputError("capture repository differs from connector authority")
    from automation.search_cli import _normalize_revision_pairs
    pairs = _normalize_revision_pairs([f"{version}={revision}" for version, revision in pairs])
    snapshots = []
    # Shared commits are read once, even when they contain all four platforms.
    trees = {revision: commands_client.read_pinned_donor_tree(revision) for revision in sorted({revision for _, revision in pairs})}
    for version, revision in pairs:
        with tempfile.TemporaryDirectory(prefix="sotn-donor-capture-") as temporary:
            root = Path(temporary)
            with tarfile.open(fileobj=io.BytesIO(trees[revision]), mode="r:") as archive:
                seen = set()
                for member in archive:
                    relative = member.name.rstrip("/")
                    validate_relative_path(relative, "pinned donor path")
                    if "\\" in relative or relative.split("/")[0] not in {"config", "src"}:
                        raise IndexedRuntimeInputError("pinned donor path is outside source/config")
                    if member.isdir():
                        continue
                    if not member.isfile() or relative in seen:
                        raise IndexedRuntimeInputError("pinned donor tree contains a nonregular or duplicate file")
                    seen.add(relative)
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise IndexedRuntimeInputError("pinned donor file has no bytes")
                    path.write_bytes(stream.read())
            roots = discover_platform_roots(version, repo=root, source_only=True)
            selected = {path: "config" for path in roots.config_paths}
            for source in roots.source_roots:
                for path in (root / source).rglob("*"):
                    if path.is_file() and path.suffix.lower() in {".c", ".h"}:
                        selected[path.relative_to(root).as_posix()] = "source"
            snapshots.append(DonorSnapshot(
                version, revision,
                tuple(DonorSnapshotFile(path, kind, (root / path).read_bytes()) for path, kind in sorted(selected.items())),
                source_only=True,
            ))
    return publish_donor_snapshots(snapshots, repo=repo)
