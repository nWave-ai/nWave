"""The name of one skill: a directory name under the skills root, never a path."""

from __future__ import annotations

import re
from pathlib import Path


class SkillName:
    SKILL_FILE = "SKILL.md"
    _DIRECTORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")

    def __init__(self, text: str) -> None:
        if not self._DIRECTORY.fullmatch(text):
            raise ValueError(
                f"skill '{text}' must name one skill directory: letters, digits, '-' or '_', starting with a letter or digit"
            )
        self.text = text

    def __str__(self) -> str:
        return self.text

    def file_under(self, root: Path) -> Path:
        return root / self.text / self.SKILL_FILE
