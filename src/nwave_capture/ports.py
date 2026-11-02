"""Public values and errors for local certified-capture evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TypeAlias
from uuid import UUID

from .contracts import PartitionRef, _digest, _string
from .result import _failures


def _utc(value: object) -> None:
    if not isinstance(value, datetime):
        raise TypeError("expected datetime")
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("expected UTC datetime")


def _canonical_object(value: object) -> None:
    if not isinstance(value, str):
        raise TypeError("expected canonical JSON str")
    if not value or value != value.strip():
        raise ValueError("expected trimmed canonical JSON object")
    try:
        parsed = json.loads(
            value, parse_constant=lambda _: (_ for _ in ()).throw(ValueError())
        )
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError("expected finite canonical JSON object") from error
    if not isinstance(parsed, dict):
        raise ValueError("expected canonical JSON object")
    encoded = json.dumps(
        parsed,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    if value != encoded:
        raise ValueError("expected canonical JSON object")


class TerminalReason(Enum):
    CAPTURED = "captured"
    NO_ELIGIBLE_EVENT = "no_eligible_event"
    REFUSED_BEFORE_WORK = "refused_before_work"


@dataclass(frozen=True)
class ExpectedPartition:
    partition: PartitionRef
    writer_id: str
    declared_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.partition, PartitionRef):
            raise TypeError("partition must be PartitionRef")
        _string(self.writer_id)
        _utc(self.declared_at)


@dataclass(frozen=True)
class ExpectedPopulation:
    run_id: UUID
    manifest_digest: str
    partitions: tuple[ExpectedPartition, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, UUID):
            raise TypeError("run_id must be UUID")
        _digest(self.manifest_digest)
        if not isinstance(self.partitions, tuple):
            raise TypeError("partitions must be tuple")
        if not all(isinstance(item, ExpectedPartition) for item in self.partitions):
            raise TypeError("partitions must contain ExpectedPartition")
        identifiers = [item.partition.partition_id for item in self.partitions]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("duplicate partition")
        if any(item.partition.run_id != self.run_id for item in self.partitions):
            raise ValueError("mixed partition run")
        roots = [
            item
            for item in self.partitions
            if item.partition.parent_partition_id is None
        ]
        if self.partitions and len(roots) != 1:
            raise ValueError("expected population requires one root")
        identifiers_set = set(identifiers)
        if any(
            item.partition.parent_partition_id not in identifiers_set
            for item in self.partitions
            if item.partition.parent_partition_id is not None
        ):
            raise ValueError("expected population must be parent-closed")


@dataclass(frozen=True)
class EvidenceRecord:
    sequence: int
    kind: str
    payload_json: str

    def __post_init__(self) -> None:
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise TypeError("sequence must be int")
        if self.sequence <= 0:
            raise ValueError("sequence must be positive")
        _string(self.kind)
        _canonical_object(self.payload_json)


@dataclass(frozen=True)
class PartitionTerminal:
    primary_digest: str
    record_count: int
    first_sequence: int | None
    last_sequence: int | None
    reason: TerminalReason

    def __post_init__(self) -> None:
        _digest(self.primary_digest)
        if isinstance(self.record_count, bool) or not isinstance(
            self.record_count, int
        ):
            raise TypeError("record_count must be int")
        if self.record_count < 0:
            raise ValueError("record_count must be non-negative")
        for value in (self.first_sequence, self.last_sequence):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int)
            ):
                raise TypeError("sequence bound must be int or None")
        if not isinstance(self.reason, TerminalReason):
            raise TypeError("reason must be TerminalReason")
        if self.record_count == 0:
            if self.first_sequence is not None or self.last_sequence is not None:
                raise ValueError("zero records require null bounds")
            if self.reason is TerminalReason.CAPTURED:
                raise ValueError("captured requires records")
        elif (
            self.first_sequence is None
            or self.last_sequence is None
            or self.first_sequence > self.last_sequence
            or self.reason is not TerminalReason.CAPTURED
        ):
            raise ValueError("captured records require ordered bounds")


@dataclass(frozen=True)
class LocalEvidenceVerified:
    bundle_digest: str

    def __post_init__(self) -> None:
        _digest(self.bundle_digest)


@dataclass(frozen=True)
class LocalEvidenceIncomplete:
    known_failures: tuple[str, ...]

    def __post_init__(self) -> None:
        _failures(self.known_failures)


@dataclass(frozen=True)
class LocalEvidenceIndeterminate:
    unknowns: tuple[str, ...]

    def __post_init__(self) -> None:
        _failures(self.unknowns)


LocalEvidenceResult: TypeAlias = (
    LocalEvidenceVerified | LocalEvidenceIncomplete | LocalEvidenceIndeterminate
)


class CaptureStorageError(Exception):
    def __init__(
        self, operation: str, partition_id: str, reason: str, remediation: str
    ) -> None:
        self.operation = operation
        self.partition_id = partition_id
        self.reason = reason
        self.remediation = remediation
        super().__init__(
            f"WHAT: {operation} failed for {partition_id}. WHY: {reason}. "
            f"HOW: {remediation}."
        )


class HealthReceiptUnavailableError(CaptureStorageError):
    pass


class PartitionStateError(CaptureStorageError):
    pass


class PartitionWriterConflictError(PartitionStateError):
    pass


class ReceiptConflictError(CaptureStorageError):
    pass
