"""Keeps the size declarations of a workspace: every declaration in order, the last one is the size in force."""

from __future__ import annotations

from nwstep.domain.size_declaration import SizeDeclaration
from nwstep.infrastructure.atomic_json import read_json, write_json
from nwstep.infrastructure.workspace import Workspace


class SizeStore:
    def __init__(self, workspace: Workspace) -> None:
        self._path = workspace.size_path

    def current(self) -> SizeDeclaration | None:
        """The declaration in force, or None when no size has been declared."""
        declarations = self._read()
        return declarations[-1] if declarations else None

    def append(self, declaration: SizeDeclaration) -> None:
        write_json(
            self._path,
            {"declarations": [item.to_dict() for item in [*self._read(), declaration]]},
        )

    def _read(self) -> list[SizeDeclaration]:
        document = read_json(self._path)
        if document is None:
            return []
        return [SizeDeclaration.from_dict(item) for item in document["declarations"]]
