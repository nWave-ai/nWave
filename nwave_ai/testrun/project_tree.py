"""Read the file paths of a project tree once, for the selector.

Effects only. The selector is a pure function of the paths this module lists: every
file path of the tree. Hidden directories and the directories the project declares in
``selection.ignore`` are not entered; symbolic links to directories are not followed.
The text of a file is read by the command the project declares, not here.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path

    from nwave_ai.testrun.declaration import SelectionRules


def read_project(root: Path, rules: SelectionRules) -> frozenset[str]:
    """Every file path under ``root``, tree-relative and with forward slashes."""
    files: set[str] = set()
    ignored = set(rules.ignore)
    for directory, names, file_names in os.walk(root):
        names[:] = sorted(
            name for name in names if not name.startswith(".") and name not in ignored
        )
        inside = os.path.relpath(directory, root).replace(os.sep, "/")
        for name in file_names:
            files.add(name if inside == "." else f"{inside}/{name}")
    return frozenset(files)
