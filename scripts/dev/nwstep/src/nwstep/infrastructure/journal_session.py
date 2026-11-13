"""Reads and appends records while the caller holds the journal lock."""

from __future__ import annotations

import json
import os
from pathlib import Path

from nwstep.domain.journal import Journal
from nwstep.domain.record import Record


class JournalSession:
    def __init__(self, path: Path) -> None:
        self._path = path

    def snapshot(self) -> Journal:
        if not self._path.exists():
            return Journal()
        lines = self._path.read_text(encoding="utf-8").splitlines()
        return Journal(
            tuple(Record.from_dict(json.loads(line)) for line in lines if line.strip())
        )

    def append(self, record: Record) -> None:
        line = json.dumps(record.to_dict(), sort_keys=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
