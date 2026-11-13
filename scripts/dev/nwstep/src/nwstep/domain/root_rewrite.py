"""Rewrites the candidate root in a command's argv and environment to the baseline directory.

An argv element or environment value equal to the candidate root, or starting with it at a
path boundary, is moved under the baseline directory. A path-list value (PYTHONPATH style) is
rewritten element by element. Nothing else changes, so the baseline run differs from the
candidate run only in where its files are.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


class RootRewrite:
    def __init__(self, candidate: Path, baseline: Path) -> None:
        self._candidate = str(candidate)
        self._baseline = str(baseline)

    def argv(self, argv: tuple[str, ...]) -> list[str]:
        return [self._path(element) for element in argv]

    def environment(self, environment: Mapping[str, str]) -> dict[str, str]:
        return {
            key: os.pathsep.join(self._path(part) for part in value.split(os.pathsep))
            for key, value in environment.items()
        }

    def _path(self, text: str) -> str:
        if text == self._candidate or text.startswith(self._candidate + os.sep):
            return self._baseline + text[len(self._candidate) :]
        return text
