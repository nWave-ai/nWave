"""The pre-feature tree with the change's declared test files copied over it. A RED run and a probe case both run on this
tree, so both judge the tests the change adds against the code before the change.

The tree is materialised from git for the length of the with-block and removed when it ends. What it proves: the tree
holds the pre-feature code and exactly the declared test files that exist in the working tree. What it does not prove:
that the declared list is complete; the oracle author declares the files, and the review checks them.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

from nwexpress.domain.baseline import Baseline
from nwexpress.domain.declared_path import DeclaredPath
from nwexpress.infrastructure.prefeature_tree import materialized_tree


TREE_NAME = "red-tree"


class RedTree:
    """Builds the overlay tree in the workspace directory for one run; the tree is removed once the step is recorded."""

    def __init__(self, baseline: Baseline, workspace_directory: Path) -> None:
        self._baseline = baseline
        self._directory = workspace_directory / TREE_NAME

    @contextmanager
    def built(self, root: Path, declared: Iterable[str]) -> Iterator[Path]:
        with materialized_tree(self._baseline, self._directory) as tree:
            for path in declared:
                source = root / DeclaredPath.parse(path).text
                if source.is_file():
                    target = tree / DeclaredPath.parse(path).text
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
            yield tree
