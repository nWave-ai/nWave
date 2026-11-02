"""Read-only local evidence verifier."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from .adapters.filesystem import (
    AtomicHealthReceiptStore,
    _paths,
    _read_frames,
    _ReceiptKind,
    _validate_root,
    _validated_receipt,
)
from .ports import (
    ExpectedPartition,
    ExpectedPopulation,
    LocalEvidenceIncomplete,
    LocalEvidenceIndeterminate,
    LocalEvidenceResult,
    LocalEvidenceVerified,
    TerminalReason,
)


if TYPE_CHECKING:
    from pathlib import Path

    from .manifest import RunManifest


class CaptureVerifier:
    def __init__(self, root: Path, manifest: RunManifest) -> None:
        _validate_root(root, manifest)
        self._root = root
        self._manifest = manifest

    def probe(self) -> None:
        _validate_root(self._root, self._manifest)
        health = self._root / "health"
        if health.exists() and not health.is_dir():
            raise ValueError("health root is not a directory")

    def verify(self, population: ExpectedPopulation) -> LocalEvidenceResult:
        if not isinstance(population, ExpectedPopulation):
            raise TypeError("population must be ExpectedPopulation")
        if population.run_id != self._manifest.run.run_id:
            raise ValueError("population run differs from manifest")
        if population.manifest_digest != self._manifest.manifest_digest:
            raise ValueError("population manifest differs from manifest")
        if not population.partitions:
            return LocalEvidenceIncomplete(("MISSING_ROOT_EXPECTATION",))
        if not (self._root / "health").is_dir():
            return LocalEvidenceIndeterminate(("MISSING_HEALTH_PROVENANCE",))
        records: list[dict[str, str]] = []
        failures: list[str] = []
        try:
            observer = AtomicHealthReceiptStore(self._root, self._manifest)
            for expected in sorted(
                population.partitions, key=lambda item: item.partition.partition_id
            ):
                result = self._verify_partition(observer, expected)
                if isinstance(result, str):
                    failures.append(result)
                else:
                    records.append(result)
        except Exception:
            return LocalEvidenceIndeterminate(("MALFORMED_RETAINED_EVIDENCE",))
        if failures:
            return LocalEvidenceIncomplete(tuple(failures))
        descriptor = {
            "manifest_digest": self._manifest.manifest_digest,
            "partitions": records,
            "run_id": str(self._manifest.run.run_id),
            "schema": "nwave_capture.bundle.v1",
        }
        digest = hashlib.sha256(
            b"nwave-capture:bundle:v1\x00"
            + json.dumps(
                descriptor,
                ensure_ascii=True,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return LocalEvidenceVerified(digest)

    def _verify_partition(
        self, observer: AtomicHealthReceiptStore, expected: ExpectedPartition
    ) -> dict[str, str] | str:
        retained: dict[_ReceiptKind, bytes] = {}
        envelopes: dict[_ReceiptKind, dict[str, object]] = {}
        for kind, item in observer._read_slots(expected):
            if kind in retained:
                raise ValueError("duplicate retained health receipt kind")
            retained[kind] = item
            envelopes[kind] = _validated_receipt(item, self._manifest, expected, kind)
        writers = {envelope["writer_id"] for envelope in envelopes.values()}
        if writers != {expected.writer_id}:
            return f"WRITER_CONFLICT:{expected.partition.partition_id}"
        if _ReceiptKind.TERMINAL in retained and _ReceiptKind.FAILURE in retained:
            raise ValueError("partition retained both terminal and failure receipts")
        if _ReceiptKind.FAILURE in retained:
            return f"RETAINED_FAILURE:{expected.partition.partition_id}"
        required = {
            _ReceiptKind.EXPECTED,
            _ReceiptKind.STARTED,
            _ReceiptKind.TERMINAL,
        }
        if not required <= set(retained):
            return f"MISSING_TERMINAL:{expected.partition.partition_id}"
        terminal = envelopes[_ReceiptKind.TERMINAL]
        payload = terminal["payload"]
        if not isinstance(payload, dict):
            raise ValueError("validated terminal payload is not an object")
        reason = TerminalReason(payload["reason"])
        if reason is TerminalReason.REFUSED_BEFORE_WORK:
            return f"REFUSED_BEFORE_WORK:{expected.partition.partition_id}"
        primary_path = _paths(self._root, expected)[1]
        frames = [
            frame
            for frame in _read_frames(primary_path)
            if frame["kind"] != "__empty__"
        ]
        primary_bytes = primary_path.read_bytes()
        digest = hashlib.sha256(primary_bytes).hexdigest()
        if digest != payload["primary_digest"]:
            raise ValueError("primary digest mismatch")
        if payload["record_count"] != len(frames):
            raise ValueError("primary record count mismatch")
        first = frames[0]["sequence"] if frames else None
        last = frames[-1]["sequence"] if frames else None
        if payload["first_sequence"] != first or payload["last_sequence"] != last:
            raise ValueError("primary bounds mismatch")
        if not frames and reason is not TerminalReason.NO_ELIGIBLE_EVENT:
            return f"INVALID_ZERO_REASON:{expected.partition.partition_id}"
        if frames and reason is not TerminalReason.CAPTURED:
            raise ValueError("invalid nonzero terminal reason")
        return {
            "expected_receipt_digest": hashlib.sha256(
                retained[_ReceiptKind.EXPECTED]
            ).hexdigest(),
            "partition_id": expected.partition.partition_id,
            "primary_digest": digest,
            "started_receipt_digest": hashlib.sha256(
                retained[_ReceiptKind.STARTED]
            ).hexdigest(),
            "terminal_receipt_digest": hashlib.sha256(
                retained[_ReceiptKind.TERMINAL]
            ).hexdigest(),
            "writer_id": expected.writer_id,
        }
