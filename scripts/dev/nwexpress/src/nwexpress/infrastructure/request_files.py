"""The files the request step touches: the standing-block template in the checkout and REQUEST.md in the workspace."""

from __future__ import annotations

from pathlib import Path

from nwexpress.domain.refusal import Refusal
from nwexpress.infrastructure.atomic_text import write_text
from nwexpress.infrastructure.package_paths import PackagePaths


REQUEST_FILE = "REQUEST.md"


class RequestFiles:
    def __init__(self, template: Path = PackagePaths.REQUEST_TEMPLATE) -> None:
        self._template = template

    def read_template(self) -> str:
        try:
            return self._template.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise Refusal(
                what=f"the standing-block template {self._template} cannot be read: {error}",
                why="the standing rules of every request come from this one file, so no request can be written without it",
                how=f"restore {self._template} in the nwexpress checkout",
            ) from None

    @staticmethod
    def path_of(workspace: Path) -> Path:
        return workspace / REQUEST_FILE

    @classmethod
    def write(cls, workspace: Path, text: str) -> Path:
        """Creates the workspace when it is missing, then writes the request in one step: a reader sees the old file or the new one."""
        workspace.mkdir(parents=True, exist_ok=True)
        path = cls.path_of(workspace)
        write_text(path, text)
        return path
