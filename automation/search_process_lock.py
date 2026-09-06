"""Process-lifetime ownership for restartable isolated search workers."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import os

from .search_archive import ContentAddressedArchive
from .search_types import validate_hash


class WorkerStillRunning(RuntimeError):
    """A previous worker still owns this immutable logical session."""


@contextmanager
def worker_session_lock(run_root: Path, session_identity: str):
    """Hold an OS lock in the worker, including after its launcher exits.

    Search workers execute on POSIX, including the Windows WSL adapter. PID
    files alone cannot establish ownership because PIDs can be reused. Never
    unlink the lock file: replacing its inode could admit a second owner.
    """
    import fcntl

    validate_hash(session_identity, "worker session identity")
    archive = ContentAddressedArchive(run_root)
    directory = archive._ensure_directory(archive.run_root / "worker-locks")
    path = directory / (session_identity.removeprefix("sha256:") + ".lock")
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WorkerStillRunning("a worker still owns this search session") from exc
        yield
    finally:
        os.close(descriptor)
