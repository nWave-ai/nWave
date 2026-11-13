"""Read a project tree once, for the selector.

Effects only. The selector is a pure function of what this module read: every file
path of the tree and the text of the files a declared adapter can read. Hidden
directories and the directories the project declares in ``selection.ignore`` are not
entered; symbolic links to directories are not followed.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from nwave_ai.testrun.selection import ProjectSnapshot


if TYPE_CHECKING:
    from pathlib import Path

    from nwave_ai.testrun.declaration import SelectionRules


def read_project(root: Path, rules: SelectionRules) -> ProjectSnapshot:
    """Every file under ``root`` and the text of those with a declared adapter."""
    files: set[str] = set()
    texts: dict[str, str] = {}
    ignored = set(rules.ignore)
    for directory, names, file_names in os.walk(root):
        names[:] = sorted(
            name for name in names if not name.startswith(".") and name not in ignored
        )
        inside = os.path.relpath(directory, root).replace(os.sep, "/")
        for name in sorted(file_names):
            path = name if inside == "." else f"{inside}/{name}"
            files.add(path)
            if os.path.splitext(name)[1] not in rules.adapters:
                continue
            try:
                with open(
                    os.path.join(directory, name), encoding="utf-8", errors="replace"
                ) as stream:
                    texts[path] = stream.read()
            except OSError:
                # A file that cannot be opened is still a file of the tree; with no
                # text, nothing can be said of what it depends on.
                continue
    return ProjectSnapshot(frozenset(files), texts)
