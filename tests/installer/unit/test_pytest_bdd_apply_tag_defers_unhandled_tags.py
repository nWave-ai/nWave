"""Repo-wide invariant: per-directory ``pytest_bdd_apply_tag`` hooks MUST defer
unhandled gherkin tags to the root terminal handler (return ``None``), never
blanket-absorb them.

Regression guard for WTBD-165. ``pytest_bdd_apply_tag`` is a session-global
``firstresult`` hook (``pytest_bdd/hooks.py``); per-directory conftest hooks fire
*before* the root ``tests/conftest.py`` (LIFO scope precedence). Two per-dir
conftests returned a non-``None`` value for **every** tag, so they swallowed the
bugs-track ``@failing`` tag before the root hook could apply
``pytest.mark.failing`` (which the bugs conftest then rewrites to ``xfail``). The
two stale guards therefore hard-failed instead of xfailing whenever the offending
directories were collected in the same session — yet passed in isolation.

Contract pinned here:

* The **root** ``tests/conftest.py`` is the single designated *terminal
  absorber*: it returns the function unchanged (non-``None``) for unregistered
  tags so ``--strict-markers`` does not trip on descriptive gherkin metadata. It
  is EXCLUDED from the deferral invariant by design — see
  ``test_root_conftest_is_the_terminal_absorber``.
* Every **other** conftest's ``pytest_bdd_apply_tag`` MUST return ``None`` for any
  tag it does not explicitly own, so foreign tags fall through to the root.

The hook is loaded by exec-ing each conftest's source with its *relative* imports
stripped (only the pure ``pytest_bdd_apply_tag`` function + its module-level
constants are exercised; production collaborators imported relatively are
irrelevant to tag routing). Discovery walks the filesystem, so a new conftest
that adds a blanket-absorbing hook is caught automatically.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from pathlib import Path

import pytest


# tests/installer/unit/<this file> -> parents[2] == the tests/ root.
_TESTS_DIR = Path(__file__).resolve().parents[2]
_ROOT_CONFTEST = _TESTS_DIR / "conftest.py"

# Clearly-foreign tags that no per-directory tag-translation conftest owns:
# ``__unhandled_probe__`` is owned by nobody; ``failing`` is the bugs-track tag
# whose mishandling caused WTBD-165 (owned by the bugs conftest's
# ``pytest_collection_modifyitems`` + the root hook, never by a per-dir
# ``pytest_bdd_apply_tag``).
_FOREIGN_TAGS = ("__unhandled_probe__", "failing")


def _discover_apply_tag_conftests() -> list[Path]:
    """Every ``conftest.py`` under tests/ that defines ``pytest_bdd_apply_tag``."""
    return sorted(
        path
        for path in _TESTS_DIR.rglob("conftest.py")
        if "def pytest_bdd_apply_tag" in path.read_text(encoding="utf-8")
    )


def _load_apply_tag_hook(conftest_path: Path) -> Callable[..., object] | None:
    """Exec a conftest's source (minus relative imports) and return its hook.

    Relative ``from . import x`` statements are dropped: the
    ``pytest_bdd_apply_tag`` functions depend only on ``pytest`` + module-level
    constants, never on the relatively-imported production collaborators. This
    keeps the guard from pulling the whole composition root into the unit test.
    """
    tree = ast.parse(conftest_path.read_text(encoding="utf-8"))
    kept = [
        node
        for node in tree.body
        if not (isinstance(node, ast.ImportFrom) and (node.level or 0) > 0)
    ]
    code = compile(
        ast.Module(body=kept, type_ignores=[]),
        filename=str(conftest_path),
        mode="exec",
    )
    namespace: dict[str, object] = {"__file__": str(conftest_path)}
    exec(code, namespace)
    return namespace.get("pytest_bdd_apply_tag")  # type: ignore[return-value]


def _probe_function() -> None:
    """A throw-away callable to stand in for a pytest-bdd scenario function."""


_PER_DIRECTORY_CONFTESTS = [
    path for path in _discover_apply_tag_conftests() if path != _ROOT_CONFTEST
]


def test_discovery_found_per_directory_apply_tag_hooks() -> None:
    """Fail loudly if discovery silently matched nothing (e.g. an rglob miss)."""
    assert _PER_DIRECTORY_CONFTESTS, (
        "No per-directory pytest_bdd_apply_tag conftests discovered under "
        f"{_TESTS_DIR}; the deferral invariant below would vacuously pass."
    )


@pytest.mark.parametrize("foreign_tag", _FOREIGN_TAGS)
@pytest.mark.parametrize(
    "conftest_path",
    _PER_DIRECTORY_CONFTESTS,
    ids=lambda path: str(path.relative_to(_TESTS_DIR)),
)
def test_per_directory_apply_tag_defers_unhandled_tag(
    conftest_path: Path, foreign_tag: str
) -> None:
    """Every non-root hook returns None for a tag it does not own."""
    hook = _load_apply_tag_hook(conftest_path)
    assert hook is not None, f"{conftest_path} defines no pytest_bdd_apply_tag"

    result = hook(foreign_tag, _probe_function)

    assert result is None, (
        f"{conftest_path.relative_to(_TESTS_DIR)} absorbed foreign tag "
        f"@{foreign_tag} (returned {result!r}). A per-directory "
        "pytest_bdd_apply_tag must return None for tags it does not own so the "
        "tag falls through to the root terminal handler (tests/conftest.py), "
        "which either applies a registered marker or absorbs it. Blanket "
        "absorption hijacks the whole tree's tag routing — this is WTBD-165."
    )


def test_root_conftest_is_the_terminal_absorber() -> None:
    """The root hook absorbs (non-None) unregistered tags by design.

    Documents WHY the root is excluded from the deferral invariant: if it
    returned None for an unregistered tag, pytest-bdd's default would apply that
    tag as a mark and ``--strict-markers`` would error at collection.
    """
    hook = _load_apply_tag_hook(_ROOT_CONFTEST)
    assert hook is not None, "root tests/conftest.py defines no pytest_bdd_apply_tag"
    assert hook("__unhandled_probe__", _probe_function) is not None, (
        "root tests/conftest.py must absorb unregistered tags (return the "
        "function), otherwise strict-markers breaks collection for descriptive "
        "gherkin metadata."
    )
