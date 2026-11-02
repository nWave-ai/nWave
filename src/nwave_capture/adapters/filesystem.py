"""Filesystem-backed local evidence stores."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any

from ..manifest import RunManifest
from ..ports import (
    CaptureStorageError,
    EvidenceRecord,
    ExpectedPartition,
    HealthReceiptUnavailableError,
    PartitionStateError,
    PartitionTerminal,
    PartitionWriterConflictError,
    ReceiptConflictError,
    TerminalReason,
)


class _ReceiptKind(Enum):
    EXPECTED = "expected"
    STARTED = "started"
    TERMINAL = "terminal"
    FAILURE = "failure"


_HEALTH_KEYS = {
    "kind",
    "manifest_digest",
    "partition_id",
    "payload",
    "run_id",
    "schema",
    "writer_id",
}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _canonical_object(retained: bytes) -> dict[str, Any]:
    if not isinstance(retained, bytes):
        raise TypeError("retained receipt must be bytes")
    try:
        value = json.loads(
            retained,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant: {constant}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError("receipt must be finite canonical UTF-8 JSON") from error
    if not isinstance(value, dict) or _canonical(value) != retained:
        raise ValueError("receipt must be a canonical JSON object")
    return value


def _paths(root: Path, expected: ExpectedPartition) -> tuple[Path, Path]:
    key = expected.partition.partition_id
    return root / "health" / key, root / "primary" / f"{key}.jsonl"


def _receipt_path(root: Path, expected: ExpectedPartition, kind: str) -> Path:
    directory, _primary = _paths(root, expected)
    return directory / f"{kind}.json"


def _receipt(
    manifest: RunManifest,
    expected: ExpectedPartition,
    kind: str,
    payload: dict[str, object],
) -> bytes:
    return _canonical(
        {
            "kind": kind,
            "manifest_digest": manifest.manifest_digest,
            "partition_id": expected.partition.partition_id,
            "payload": payload,
            "run_id": str(manifest.run.run_id),
            "schema": "nwave_capture.health.v1",
            "writer_id": expected.writer_id,
        }
    )


def _validated_receipt(
    retained: bytes,
    manifest: RunManifest,
    expected: ExpectedPartition,
    kind: _ReceiptKind,
) -> dict[str, Any]:
    envelope = _canonical_object(retained)
    if set(envelope) != _HEALTH_KEYS:
        raise ValueError("health receipt has an invalid envelope schema")
    if any(not isinstance(envelope[name], str) for name in _HEALTH_KEYS - {"payload"}):
        raise ValueError("health receipt envelope values must be strings")
    if envelope["kind"] != kind.value:
        raise ValueError("health receipt kind does not match its retained slot")
    if envelope["schema"] != "nwave_capture.health.v1":
        raise ValueError("health receipt schema is incompatible")
    if envelope["manifest_digest"] != manifest.manifest_digest:
        raise ValueError("health receipt manifest does not match the active manifest")
    if envelope["run_id"] != str(manifest.run.run_id):
        raise ValueError("health receipt run does not match the active manifest")
    if envelope["partition_id"] != expected.partition.partition_id:
        raise ValueError(
            "health receipt partition does not match the expected partition"
        )
    payload = envelope["payload"]
    if not isinstance(payload, dict):
        raise ValueError("health receipt payload must be an object")
    _validate_receipt_payload(kind, payload, expected)
    return envelope


def _validate_receipt_payload(
    kind: _ReceiptKind, payload: dict[str, Any], expected: ExpectedPartition
) -> None:
    if kind is _ReceiptKind.EXPECTED:
        declared_at = expected.declared_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if set(payload) != {"declared_at"} or payload["declared_at"] != declared_at:
            raise ValueError("expected receipt payload does not match its declaration")
        return
    if kind is _ReceiptKind.STARTED:
        if payload:
            raise ValueError("started receipt payload must be empty")
        return
    if kind is _ReceiptKind.TERMINAL:
        if set(payload) != {
            "first_sequence",
            "last_sequence",
            "primary_digest",
            "reason",
            "record_count",
        }:
            raise ValueError("terminal receipt payload has an invalid schema")
        _terminal_from_payload(payload)
        return
    if set(payload) != {"code"}:
        raise ValueError("failure receipt payload has an invalid schema")
    _validate_code(payload["code"])


def _load_receipt(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("receipt is not an object")
    return value


class AtomicHealthReceiptStore:
    def __init__(self, root: Path, manifest: RunManifest) -> None:
        _validate_root(root, manifest)
        self._root = root
        self._manifest = manifest

    def probe(self) -> None:
        _validate_root(self._root, self._manifest)
        health = self._root / "health"
        if health.exists() and not health.is_dir():
            raise HealthReceiptUnavailableError(
                "probe",
                self._manifest.root_partition.partition_id,
                "health root is not a directory",
                "restore the manifest-pinned health root",
            )

    def read(self, expected: ExpectedPartition) -> tuple[bytes, ...]:
        return tuple(retained for _kind, retained in self._read_slots(expected))

    def _read_slots(
        self, expected: ExpectedPartition
    ) -> tuple[tuple[_ReceiptKind, bytes], ...]:
        if not isinstance(expected, ExpectedPartition):
            raise TypeError("expected must be ExpectedPartition")
        self.probe()
        result: list[tuple[_ReceiptKind, bytes]] = []
        for kind in _ReceiptKind:
            path = _receipt_path(self._root, expected, kind.value)
            if path.exists():
                result.append((kind, path.read_bytes()))
        return tuple(result)


class FramedPartitionStore:
    def __init__(
        self, root: Path, manifest: RunManifest, expected: ExpectedPartition
    ) -> None:
        _validate_root(root, manifest)
        if not isinstance(expected, ExpectedPartition):
            raise TypeError("expected must be ExpectedPartition")
        if expected.partition.run_id != manifest.run.run_id:
            raise ValueError("expected partition belongs to another run")
        self._root = root
        self._manifest = manifest
        self._expected = expected

    def probe(self) -> None:
        _validate_root(self._root, self._manifest)
        health = self._root / "health"
        if health.exists() and not health.is_dir():
            raise HealthReceiptUnavailableError(
                "probe",
                self._expected.partition.partition_id,
                "health root is not a directory",
                "restore the manifest-pinned health root",
            )

    def open(self) -> None:
        self.probe()
        try:
            self._ensure_expected()
            terminal = _load_receipt(
                _receipt_path(self._root, self._expected, "terminal")
            )
            failure = _load_receipt(
                _receipt_path(self._root, self._expected, "failure")
            )
            started = _load_receipt(
                _receipt_path(self._root, self._expected, "started")
            )
            if terminal is not None or failure is not None or started is not None:
                raise PartitionStateError(
                    "open",
                    self._expected.partition.partition_id,
                    "partition has already progressed beyond expected",
                    "create a new declared partition for another attempt",
                )
            primary = _paths(self._root, self._expected)[1]
            primary.parent.mkdir(parents=True, exist_ok=True)
            primary.touch(exist_ok=True)
            self._acquire_started()
        except (
            PartitionStateError,
            PartitionWriterConflictError,
            ReceiptConflictError,
        ):
            raise
        except HealthReceiptUnavailableError:
            raise
        except Exception as error:
            self._record_failure("open-failed")
            raise CaptureStorageError(
                "open",
                self._expected.partition.partition_id,
                str(error),
                "restore writable primary storage and retry with the same declared writer",
            ) from error

    def append(self, record: EvidenceRecord) -> None:
        if not isinstance(record, EvidenceRecord):
            raise TypeError("record must be EvidenceRecord")
        if not self._started():
            raise PartitionStateError(
                "append",
                self._expected.partition.partition_id,
                "partition is not started",
                "open the declared partition before appending",
            )
        primary = _paths(self._root, self._expected)[1]
        try:
            retained = _read_frames(primary)
            existing = next(
                (item for item in retained if item["sequence"] == record.sequence), None
            )
            if existing is not None:
                if existing == _record_envelope(record):
                    return
                raise PartitionStateError(
                    "append",
                    self._expected.partition.partition_id,
                    "sequence already has different retained evidence",
                    "append the original record once or use the next sequence",
                )
            if record.sequence != len(retained) + 1:
                raise PartitionStateError(
                    "append",
                    self._expected.partition.partition_id,
                    "sequence is not the next retained sequence",
                    "append consecutive positive sequence numbers",
                )
            frame = _frame(_record_envelope(record))
            with primary.open("ab") as handle:
                handle.write(frame)
                handle.flush()
                os.fsync(handle.fileno())
        except PartitionStateError:
            raise
        except Exception as error:
            self._record_failure("append-failed")
            raise CaptureStorageError(
                "append",
                self._expected.partition.partition_id,
                str(error),
                "restore writable primary storage and retry with retained evidence",
            ) from error

    def close(self, reason: TerminalReason) -> PartitionTerminal:
        if not isinstance(reason, TerminalReason):
            raise TypeError("reason must be TerminalReason")
        terminal = _load_receipt(_receipt_path(self._root, self._expected, "terminal"))
        if terminal is not None:
            observed = TerminalReason(terminal["payload"]["reason"])
            if observed is not reason:
                raise ReceiptConflictError(
                    "close",
                    self._expected.partition.partition_id,
                    "terminal reason conflicts with retained terminal",
                    "retain the originally closed reason",
                )
            return _terminal_from_payload(terminal["payload"])
        if not self._started():
            raise PartitionStateError(
                "close",
                self._expected.partition.partition_id,
                "partition is not started",
                "open the declared partition before close",
            )
        primary = _paths(self._root, self._expected)[1]
        try:
            frames = _read_frames(primary)
            records = [frame for frame in frames if frame["kind"] != "__empty__"]
            if not records:
                with primary.open("ab") as handle:
                    handle.write(
                        _frame(
                            {
                                "kind": "__empty__",
                                "payload": {},
                                "schema": "nwave_capture.primary.v1",
                                "sequence": 1,
                            }
                        )
                    )
                    handle.flush()
                    os.fsync(handle.fileno())
            count = len(records)
            first = records[0]["sequence"] if records else None
            last = records[-1]["sequence"] if records else None
            digest = hashlib.sha256(primary.read_bytes()).hexdigest()
            observation = PartitionTerminal(digest, count, first, last, reason)
            self._publish(
                "terminal",
                {
                    "primary_digest": observation.primary_digest,
                    "record_count": observation.record_count,
                    "first_sequence": observation.first_sequence,
                    "last_sequence": observation.last_sequence,
                    "reason": observation.reason.value,
                },
            )
            return observation
        except ValueError:
            raise
        except Exception as error:
            self._record_failure("close-failed")
            raise CaptureStorageError(
                "close",
                self._expected.partition.partition_id,
                str(error),
                "restore coherent primary evidence and retry close",
            ) from error

    def abort(self, code: str) -> None:
        _validate_code(code)
        terminal = _load_receipt(_receipt_path(self._root, self._expected, "terminal"))
        if terminal is not None:
            raise PartitionStateError(
                "abort",
                self._expected.partition.partition_id,
                "partition already has a terminal receipt",
                "do not rewrite terminal history",
            )
        failure = _load_receipt(_receipt_path(self._root, self._expected, "failure"))
        if failure is not None:
            if failure["payload"]["code"] == code:
                return
            raise ReceiptConflictError(
                "abort",
                self._expected.partition.partition_id,
                "failure code conflicts with retained failure",
                "retain the original failure code",
            )
        try:
            self._ensure_expected()
            self._publish("failure", {"code": code})
        except HealthReceiptUnavailableError:
            raise
        except Exception as error:
            raise HealthReceiptUnavailableError(
                "abort",
                self._expected.partition.partition_id,
                str(error),
                "restore writable health storage before recording failure",
            ) from error

    def _started(self) -> bool:
        return _receipt_path(self._root, self._expected, "started").exists()

    def _ensure_expected(self) -> None:
        path = _receipt_path(self._root, self._expected, "expected")
        desired = _receipt(
            self._manifest,
            self._expected,
            "expected",
            {
                "declared_at": self._expected.declared_at.strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ"
                )
            },
        )
        try:
            current = path.read_bytes() if path.exists() else None
            if current is None:
                self._atomic_write(path, desired)
                return
            value = json.loads(current)
            if value["writer_id"] != self._expected.writer_id:
                raise PartitionWriterConflictError(
                    "open",
                    self._expected.partition.partition_id,
                    "another writer owns the declared partition",
                    "use the original writer or declare a different partition",
                )
            if current != desired:
                raise ReceiptConflictError(
                    "open",
                    self._expected.partition.partition_id,
                    "retained expected receipt differs from this declaration",
                    "reuse the exact original expected partition declaration",
                )
            return
        except (PartitionWriterConflictError, ReceiptConflictError):
            raise
        except Exception as error:
            raise HealthReceiptUnavailableError(
                "expected",
                self._expected.partition.partition_id,
                str(error),
                "restore writable health storage before opening the partition",
            ) from error

    def _publish(self, kind: str, payload: dict[str, object]) -> None:
        path = _receipt_path(self._root, self._expected, kind)
        desired = _receipt(self._manifest, self._expected, kind, payload)
        try:
            if path.exists():
                if path.read_bytes() == desired:
                    return
                raise ReceiptConflictError(
                    kind,
                    self._expected.partition.partition_id,
                    "retained receipt conflicts with requested publication",
                    "preserve the immutable retained receipt",
                )
            self._atomic_write(path, desired)
        except ReceiptConflictError:
            raise
        except Exception as error:
            raise HealthReceiptUnavailableError(
                kind,
                self._expected.partition.partition_id,
                str(error),
                "restore writable health storage before retrying publication",
            ) from error

    def _acquire_started(self) -> None:
        path = _receipt_path(self._root, self._expected, _ReceiptKind.STARTED.value)
        desired = _receipt(
            self._manifest, self._expected, _ReceiptKind.STARTED.value, {}
        )
        try:
            self._atomic_create(path, desired)
        except FileExistsError as error:
            raise PartitionStateError(
                "open",
                self._expected.partition.partition_id,
                "partition ownership was already acquired",
                "reuse the existing owner or declare a new partition attempt",
            ) from error
        except Exception as error:
            raise HealthReceiptUnavailableError(
                "started",
                self._expected.partition.partition_id,
                str(error),
                "restore writable health storage before retrying acquisition",
            ) from error

    def _record_failure(self, code: str) -> None:
        try:
            if not _receipt_path(self._root, self._expected, "failure").exists():
                self._publish("failure", {"code": code})
        except Exception:
            pass

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = _write_temporary(path, payload)
        try:
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _atomic_create(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = _write_temporary(path, payload)
        try:
            os.link(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def _validate_root(root: object, manifest: object) -> None:
    if not isinstance(root, Path):
        raise TypeError("root must be Path")
    if not isinstance(manifest, RunManifest):
        raise TypeError("manifest must be RunManifest")
    if root != Path(manifest.canonical_capture_root):
        raise ValueError("root must match manifest canonical capture root")


def _record_envelope(record: EvidenceRecord) -> dict[str, object]:
    return {
        "kind": record.kind,
        "payload": json.loads(record.payload_json),
        "schema": "nwave_capture.primary.v1",
        "sequence": record.sequence,
    }


def _frame(envelope: dict[str, object]) -> bytes:
    payload = _canonical(envelope)
    return f"{len(payload):08X}:".encode("ascii") + payload + b"\n"


def _read_frames(path: Path) -> list[dict[str, Any]]:
    payload = path.read_bytes()
    if not payload:
        return []
    offset = 0
    frames: list[dict[str, Any]] = []
    while offset < len(payload):
        header = payload[offset : offset + 8]
        if len(header) != 8 or any(byte not in b"0123456789ABCDEF" for byte in header):
            raise ValueError("invalid primary frame header")
        if payload[offset + 8 : offset + 9] != b":":
            raise ValueError("invalid primary frame separator")
        size = int(header, 16)
        start, end = offset + 9, offset + 9 + size
        envelope = payload[start:end]
        if len(envelope) != size or payload[end : end + 1] != b"\n":
            raise ValueError("incomplete primary frame")
        value = json.loads(envelope)
        if _canonical(value) != envelope or not isinstance(value, dict):
            raise ValueError("non-canonical primary frame")
        if set(value) != {"kind", "payload", "schema", "sequence"}:
            raise ValueError("invalid primary envelope")
        if value["schema"] != "nwave_capture.primary.v1":
            raise ValueError("invalid primary schema")
        if not isinstance(value["sequence"], int) or isinstance(
            value["sequence"], bool
        ):
            raise ValueError("invalid primary sequence")
        frames.append(value)
        offset = end + 1
    if [item["sequence"] for item in frames] != list(range(1, len(frames) + 1)):
        raise ValueError("non-consecutive primary sequences")
    return frames


def _terminal_from_payload(payload: dict[str, Any]) -> PartitionTerminal:
    return PartitionTerminal(
        payload["primary_digest"],
        payload["record_count"],
        payload["first_sequence"],
        payload["last_sequence"],
        TerminalReason(payload["reason"]),
    )


def _validate_code(code: object) -> None:
    if not isinstance(code, str):
        raise TypeError("code must be str")
    if not code or code != code.strip():
        raise ValueError("code must be trimmed non-empty str")


def _write_temporary(path: Path, payload: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return temporary
