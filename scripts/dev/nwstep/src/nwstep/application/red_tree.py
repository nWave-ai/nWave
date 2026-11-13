"""The pre-feature tree with the change's test files copied over it. A RED run and a probe case both run on this tree,
so both judge the tests the change adds against the code before the change.

What it proves: the tree holds the pre-feature code and the change's test files, nothing else.
What it does not prove: that the copied tests are complete; only the files the change names are copied.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path

from nwstep.domain.baseline import Baseline


TREE_NAME = "red-tree"


def changed_tests(names: Iterable[str]) -> list[str]:
    """The changed files that are test material for the red-tree overlay.

    A Python test file as before: a basename starting with test_ or a tests path part.
    A Rust suite only under a tests path part, never by a name prefix, so a production
    source cannot be classified as a test the way the Python prefix rule classifies a
    test_-prefixed production .py (the DEC4 near-defect, which this change leaves as is).
    A changed Cargo.toml manifest at any depth, exactly that name.
    """
    return sorted(
        name
        for name in names
        if (
            name.endswith(".py")
            and (Path(name).name.startswith("test_") or "tests" in Path(name).parts)
        )
        or (name.endswith(".rs") and "tests" in Path(name).parts)
        or Path(name).name == "Cargo.toml"
    )


class RedTree:
    """Builds the overlay tree in the workspace directory, replacing any earlier one."""

    def __init__(self, baseline: Baseline, workspace_directory: Path) -> None:
        self._baseline = baseline
        self._directory = workspace_directory / TREE_NAME

    def build(self, root: Path, changed_names: Iterable[str]) -> Path:
        if self._directory.exists():
            shutil.rmtree(self._directory)
        shutil.copytree(self._baseline.tree(), self._directory, symlinks=True)
        for path in changed_tests(changed_names):
            source = root / path
            if source.is_file():
                target = self._directory / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        return self._directory
