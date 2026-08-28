"""Append-only, hash-chained ledger for search decisions."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence, Tuple, Union

from .search_archive import ContentAddressedArchive
from .search_types import (
    EVENT_TYPES,
    SCHEMA_VERSION,
    LedgerEvent,
    SearchValidationError,
    event_payload,
    hash_canonical,
    iter_artifact_refs,
    validate_id,
)


class LedgerError(RuntimeError):
    """Base class for ledger failures."""


class LedgerIntegrityError(LedgerError):
    """The on-disk ledger is not a valid prefix."""


class LedgerAppendError(LedgerError):
    """An append would violate the ledger contract."""


class PartialLedgerLine(LedgerError):
    """A trailing JSON line was interrupted before its newline."""


class MissingLedgerArtifact(LedgerError):
    """An event references an artifact unavailable to the archive."""


FaultHook = Callable[[str, Path], None]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class AppendOnlyLedger:
    """Durably append schema-valid events and validate the complete prefix."""

    def __init__(
        self,
        path: Union[str, os.PathLike[str]],
        *,
        run_id: Optional[str] = None,
        archive: Optional[ContentAddressedArchive] = None,
        fault_hook: Optional[FaultHook] = None,
    ) -> None:
        self.path = Path(path)
        self.run_id = run_id
        self.archive = archive
        self.fault_hook = fault_hook
        self._lock = threading.RLock()
        self._partial_bytes = b""

    def _fault(self, point: str) -> None:
        if self.fault_hook is not None:
            self.fault_hook(point, self.path)

    def _read_prefix(self) -> Tuple[List[LedgerEvent], int, bytes]:
        if not self.path.exists():
            return [], 0, b""
        raw = self.path.read_bytes()
        if not raw:
            return [], 0, b""
        complete_size = len(raw)
        partial = b""
        if not raw.endswith(b"\n"):
            last_newline = raw.rfind(b"\n")
            complete_size = last_newline + 1
            partial = raw[complete_size:]
        prefix = raw[:complete_size]
        events: List[LedgerEvent] = []
        for line_number, line in enumerate(prefix.splitlines(), 1):
            if not line.strip():
                raise LedgerIntegrityError(f"blank event at line {line_number}")
            try:
                data = json.loads(line.decode("utf-8"))
                event = LedgerEvent.from_dict(data)
            except (UnicodeDecodeError, json.JSONDecodeError, SearchValidationError) as exc:
                raise LedgerIntegrityError(f"invalid event at line {line_number}") from exc
            events.append(event)
        self._validate_chain(events)
        self._partial_bytes = partial
        return events, complete_size, partial

    def _validate_chain(self, events: Sequence[LedgerEvent]) -> None:
        previous: Optional[LedgerEvent] = None
        seen_ids = set()
        for expected_sequence, event in enumerate(events):
            if event.sequence != expected_sequence:
                raise LedgerIntegrityError(
                    f"sequence gap at {event.sequence}, expected {expected_sequence}"
                )
            if event.event_id in seen_ids:
                raise LedgerIntegrityError(f"duplicate event id: {event.event_id}")
            seen_ids.add(event.event_id)
            if self.run_id is not None and event.run_id != self.run_id:
                raise LedgerIntegrityError("event belongs to another run")
            if previous is None:
                if event.event_type != "run_started":
                    raise LedgerIntegrityError("ledger must begin with run_started")
                if event.previous_event_hash is not None:
                    raise LedgerIntegrityError("first event has a predecessor")
            else:
                if event.run_id != previous.run_id:
                    raise LedgerIntegrityError("run id changed in ledger")
                if event.previous_event_hash != previous.event_hash:
                    raise LedgerIntegrityError("broken previous_event_hash chain")
            if event.calculated_hash() != event.event_hash:
                raise LedgerIntegrityError(f"invalid event hash at sequence {event.sequence}")
            previous = event

    def events(self) -> Tuple[LedgerEvent, ...]:
        with self._lock:
            events, _, _ = self._read_prefix()
            return tuple(events)

    def verify(self) -> Tuple[LedgerEvent, ...]:
        """Validate the complete durable prefix, returning valid events.

        A partial trailing line is intentionally not treated as a committed
        event.  Callers can inspect ``partial_bytes`` and explicitly invoke
        ``truncate_partial`` after preserving forensic evidence.
        """
        with self._lock:
            events, _, _ = self._read_prefix()
            if events and events[0].event_type != "run_started":
                raise LedgerIntegrityError("ledger must begin with run_started")
            return tuple(events)

    @property
    def partial_bytes(self) -> bytes:
        with self._lock:
            self._read_prefix()
            return self._partial_bytes

    def truncate_partial(self) -> None:
        """Explicitly discard only an incomplete trailing line."""
        with self._lock:
            _, complete_size, partial = self._read_prefix()
            if not partial:
                return
            with self.path.open("r+b") as stream:
                stream.truncate(complete_size)
                stream.flush()
                os.fsync(stream.fileno())
            self._fsync_directory(self.path.parent)
            self._partial_bytes = b""

    def _verify_event_artifacts(self, event: LedgerEvent) -> None:
        refs = iter_artifact_refs(event.payload)
        if refs and self.archive is None:
            raise MissingLedgerArtifact("an archive is required to verify references")
        if self.archive is not None:
            for reference in refs:
                try:
                    self.archive.verify(reference)
                except Exception as exc:
                    raise MissingLedgerArtifact(reference.path) from exc

    def _make_event(
        self,
        event_type: str,
        payload: Any,
        *,
        event_id: Optional[str] = None,
        recorded_at: Optional[str] = None,
    ) -> LedgerEvent:
        if event_type not in EVENT_TYPES:
            raise LedgerAppendError(f"unknown event type: {event_type}")
        typed_payload = event_payload(event_type, payload)
        existing = self.events()
        if existing:
            run_id = existing[0].run_id
        elif self.run_id is not None:
            run_id = self.run_id
        elif event_type == "run_started":
            run_id = typed_payload.run_id  # type: ignore[attr-defined]
        else:
            raise LedgerAppendError("run_id is required before run_started")
        sequence = len(existing)
        if event_id is None:
            event_id = f"{run_id}:event:{sequence}:{event_type}"
        validate_id(event_id, "event_id")
        previous_hash = existing[-1].event_hash if existing else None
        provisional = {
            "schema_version": SCHEMA_VERSION,
            "sequence": sequence,
            "event_id": event_id,
            "previous_event_hash": previous_hash,
            "recorded_at": recorded_at or utc_now(),
            "run_id": run_id,
            "event_type": event_type,
            "payload": typed_payload,
        }
        event_hash = hash_canonical(provisional)
        return LedgerEvent(
            schema_version=SCHEMA_VERSION,
            sequence=sequence,
            event_id=event_id,
            previous_event_hash=previous_hash,
            event_hash=event_hash,
            recorded_at=provisional["recorded_at"],
            run_id=run_id,
            event_type=event_type,
            payload=typed_payload,
        )

    def append_event(
        self,
        event_type: str,
        payload: Any,
        *,
        event_id: Optional[str] = None,
        recorded_at: Optional[str] = None,
    ) -> LedgerEvent:
        with self._lock:
            # A partial append is evidence of an interrupted write.  Refuse to
            # hide it behind a new event until the operator explicitly repairs
            # the prefix.
            existing, _, partial = self._read_prefix()
            if partial:
                raise PartialLedgerLine("truncate_partial is required before append")
            event = self._make_event(
                event_type,
                payload,
                event_id=event_id,
                recorded_at=recorded_at,
            )
            if any(existing_event.event_id == event.event_id for existing_event in existing):
                raise LedgerAppendError("event id already exists")
            if not existing and event_type != "run_started":
                raise LedgerAppendError("ledger must begin with run_started")
            if existing and event_type == "run_started":
                raise LedgerAppendError("run_started may occur only once")
            if self.run_id is None:
                self.run_id = event.run_id
            elif event.run_id != self.run_id:
                raise LedgerAppendError("event belongs to another run")
            self._verify_event_artifacts(event)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            encoded = (event.to_json() + "\n").encode("utf-8")
            self._fault("before_ledger_append")
            with self.path.open("ab") as stream:
                stream.write(encoded)
                stream.flush()
                self._fault("after_ledger_write")
                os.fsync(stream.fileno())
            self._fault("after_ledger_append")
            self._fsync_directory(self.path.parent)
            return event

    append = append_event

    def append_record(self, event: LedgerEvent) -> LedgerEvent:
        """Append a pre-built event only when it exactly names the next prefix."""
        with self._lock:
            existing, _, partial = self._read_prefix()
            if partial:
                raise PartialLedgerLine("truncate_partial is required before append")
            expected_sequence = len(existing)
            if event.sequence != expected_sequence:
                raise LedgerAppendError("event sequence is not the next sequence")
            if existing and event.previous_event_hash != existing[-1].event_hash:
                raise LedgerAppendError("event predecessor is not the current tail")
            if not existing and event.event_type != "run_started":
                raise LedgerAppendError("ledger must begin with run_started")
            if existing and event.event_type == "run_started":
                raise LedgerAppendError("run_started may occur only once")
            if self.run_id is not None and event.run_id != self.run_id:
                raise LedgerAppendError("event belongs to another run")
            if any(existing_event.event_id == event.event_id for existing_event in existing):
                raise LedgerAppendError("event id already exists")
            if event.calculated_hash() != event.event_hash:
                raise LedgerAppendError("event hash does not match canonical payload")
            self._verify_event_artifacts(event)
            if self.run_id is None:
                self.run_id = event.run_id
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("ab") as stream:
                stream.write((event.to_json() + "\n").encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            self._fsync_directory(self.path.parent)
            return event

    def start_run(self, manifest: Any, *, event_id: Optional[str] = None) -> LedgerEvent:
        return self.append_event("run_started", manifest, event_id=event_id)

    @staticmethod
    def _fsync_directory(path: Path) -> None:
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


Ledger = AppendOnlyLedger
SearchLedger = AppendOnlyLedger


__all__ = [
    "LedgerError", "LedgerIntegrityError", "LedgerAppendError", "PartialLedgerLine",
    "MissingLedgerArtifact", "AppendOnlyLedger", "Ledger", "SearchLedger", "utc_now",
]
