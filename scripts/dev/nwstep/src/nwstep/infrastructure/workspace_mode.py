"""Reads and writes the run mode a workspace is bound to."""

from __future__ import annotations

from nwstep.infrastructure.workspace import Workspace


class WorkspaceMode:
    def __init__(self, workspace: Workspace) -> None:
        self._path = workspace.mode_path

    def read(self) -> str | None:
        """The recorded mode, or None when no prompt or init has bound one yet."""
        if not self._path.is_file():
            return None
        return self._path.read_text(encoding="utf-8").strip()

    def write(self, mode: str) -> None:
        self._path.write_text(mode + "\n", encoding="utf-8")
