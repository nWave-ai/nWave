"""Regression + prevention guard: conftest/test module names must be globally unique.

Repo runs pytest under ``--import-mode=importlib`` (pyproject.toml). In that mode
pytest derives each module's import name via
``_pytest.pathlib.resolve_pkg_root_and_module_name`` by walking the ``__init__.py``
chain and re-rooting at the first non-identifier (hyphenated) directory. Two
distinct trees can therefore derive the *same* module name, which makes pluggy
abort collection with::

    ValueError: Plugin already registered under a different name

This guard enumerates every ``conftest.py`` and test module under ``tests/``,
derives the importlib module name the way pytest does, and asserts the derived
names are globally unique. It is both the regression test for the
``acceptance.steps.conftest`` collision (PR #37) and the standing P2 prevention
guard against any future duplicate.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from _pytest.pathlib import (
    CouldNotResolvePathError,
    module_name_from_path,
    resolve_pkg_root_and_module_name,
)


TESTS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TESTS_ROOT.parent


def _collected_module_files() -> list[Path]:
    """Every conftest.py and test module pytest would import under tests/."""
    conftests = TESTS_ROOT.rglob("conftest.py")
    test_modules = TESTS_ROOT.rglob("test_*.py")
    paths = {
        path.resolve()
        for path in (*conftests, *test_modules)
        if "__pycache__" not in path.parts
    }
    return sorted(paths)


def _derived_module_name(path: Path) -> str:
    """Module name pytest derives under --import-mode=importlib.

    Mirrors ``_pytest.pathlib.import_path``'s importlib branch: first try the
    ``__init__.py``-chain resolution (the path that yields colliding short names
    like ``acceptance.steps.conftest``); on ``CouldNotResolvePathError`` fall
    back to the unique path-based name pytest uses for rootless modules.

    pytest does not pass ``consider_namespace_packages`` here, so the default
    (False) is what reproduces the collision.
    """
    try:
        _root, module_name = resolve_pkg_root_and_module_name(path)
    except CouldNotResolvePathError:
        return module_name_from_path(path, REPO_ROOT)
    return module_name


def test_derived_module_names_are_globally_unique() -> None:
    names_to_paths: dict[str, list[Path]] = defaultdict(list)
    for path in _collected_module_files():
        names_to_paths[_derived_module_name(path)].append(path)

    collisions = {
        name: paths for name, paths in names_to_paths.items() if len(paths) > 1
    }

    assert not collisions, "Duplicate pytest-derived module names: " + "; ".join(
        f"{name} <- [{', '.join(str(p.relative_to(TESTS_ROOT)) for p in paths)}]"
        for name, paths in sorted(collisions.items())
    )
