"""The pre-feature tree with the change's declared test files copied over it. A RED run and a probe case both run on this
tree, so both judge the tests the change adds against the code before the change.

What it proves: the tree holds the pre-feature code and exactly the declared test files that exist in the working tree.
What it does not prove: that the declared list is complete; the oracle author declares the files, and the review checks them.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path

from nwstep.domain.baseline import Baseline
from nwstep.domain.declared_path import DeclaredPath

TREE_NAME = "red-tree"


class RedTree:
    """Builds the overlay tree in the workspace directory, replacing any earlier one."""

    def __init__(self, baseline: Baseline, workspace_directory: Path) -> None:
        self._baseline = baseline
        self._directory = workspace_directory / TREE_NAME

    def build(self, root: Path, declared: Iterable[str]) -> Path:
        if self._directory.exists():
            shutil.rmtree(self._directory)
        shutil.copytree(self._baseline.tree(), self._directory, symlinks=True)
        for path in declared:
            source = root / DeclaredPath.parse(path).text
            if source.is_file():
                target = self._directory / DeclaredPath.parse(path).text
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        return self._directory
