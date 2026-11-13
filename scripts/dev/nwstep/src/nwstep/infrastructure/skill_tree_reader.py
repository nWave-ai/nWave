"""Reads a folder of skill files into a mapping from relative name to bytes. An unreadable file or a missing folder is a refusal naming it."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwstep.domain.refusal import Refusal


if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _everything(name: str) -> bool:
    return True


class SkillTreeReader:
    def read(
        self, root: Path, keep: Callable[[str], bool] = _everything
    ) -> dict[str, bytes]:
        if not root.is_dir():
            raise Refusal(
                what=f"the skills folder {root} is missing: no folder of skill files is there",
                why="a run carries the files it names in its own copy, so the folder must exist and be readable",
            )
        files: dict[str, bytes] = {}
        for path in sorted(root.rglob("*")):
            if path.is_dir() and not path.is_symlink():
                continue
            name = path.relative_to(root).as_posix()
            if not keep(name):
                continue
            try:
                files[name] = path.read_bytes()
            except OSError as error:
                raise Refusal(
                    what=f"{path} cannot be read: {error.strerror or error}",
                    why="a skill file that cannot be read would be missing from the copy without anyone noticing",
                ) from None
        return files
