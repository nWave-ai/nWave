"""The append-only journal file. Each transaction holds the lock for its whole duration."""

from __future__ import annotations

import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager

from nwstep.domain.journal import Journal
from nwstep.infrastructure.journal_session import JournalSession
from nwstep.infrastructure.workspace import Workspace


class JsonlJournal:
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    @contextmanager
    def exclusive(self) -> Iterator[JournalSession]:
        with self._locked(fcntl.LOCK_EX):
            yield JournalSession(self._workspace.journal_path)

    def snapshot(self) -> Journal:
        with self._locked(fcntl.LOCK_SH):
            return JournalSession(self._workspace.journal_path).snapshot()

    @contextmanager
    def _locked(self, mode: int) -> Iterator[None]:
        descriptor = os.open(self._workspace.lock_path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(descriptor, mode)
            yield
        finally:
            os.close(descriptor)
