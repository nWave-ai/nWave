"""pytest-bdd tag handling for the installer-orphan-sweep acceptance track.

Gherkin tags on these scenarios are split in two classes:

- registered pytest markers (``acceptance``, …) — applied as real marks;
- metadata tags (``slice-01``, ``walking_skeleton``, ``driving_port``,
  ``real-io``, ``contract-shape:*``) — wave-protocol annotations consumed
  here so they stay grep-able in the ``.feature`` file without generating
  ``PytestUnknownMarkWarning`` noise under ``--strict-markers``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import pytest


_T = TypeVar("_T")

_REGISTERED_MARKERS = {"acceptance", "slow", "e2e", "unit", "integration", "wiring_e2e"}


def pytest_bdd_apply_tag(
    tag: str, function: Callable[..., _T]
) -> Callable[..., _T] | None:
    """Apply this track's registered markers; defer every other tag to root.

    Returning ``None`` for non-owned tags lets the chain fall through to the
    root ``tests/conftest.py`` terminal handler (``pytest_bdd_apply_tag`` is
    ``firstresult``; per-dir conftests fire first via LIFO). The root applies
    registered markers and absorbs descriptive gherkin metadata, so foreign
    tags like ``@failing`` are NOT swallowed here. Blanket-absorbing them
    (the WTBD-165 defect) hijacked the bugs-track ``@failing`` -> xfail routing.
    """
    if tag in _REGISTERED_MARKERS:
        return getattr(pytest.mark, tag)(function)
    return None
