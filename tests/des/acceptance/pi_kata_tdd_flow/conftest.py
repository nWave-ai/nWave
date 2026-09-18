"""pytest-bdd tag handling for the pi-kata-tdd-flow acceptance suite.

Gherkin tags split into two classes:

- registered pytest markers (tier markers) — applied as real marks;
- wave-metadata tags (``US-1``, ``real-io``, ``adapter-integration``,
  ``error``, ``walking_skeleton``, ``driving_port``, ``in-memory``,
  ``requires_external``, ``contract-shape:*``) — wave-protocol annotations
  consumed here so they stay grep-able in the ``.feature`` files without
  tripping ``--strict-markers`` (colon names like ``contract-shape:bounded-change``
  cannot be registered via ``addinivalue_line`` — pytest truncates the marker
  name at the first colon).

Mirrors the established repo pattern in
``tests/installer/acceptance/installer_orphan_sweep/conftest.py``. The
``@requires_external`` live-model scenario is skipped at the step level
(its Given fires ``pytest.skip``), so no marker-based selection is needed.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import pytest


_T = TypeVar("_T")

_REGISTERED_MARKERS = {"acceptance", "slow", "e2e", "unit", "integration", "wiring_e2e"}


def pytest_bdd_apply_tag(tag: str, function: Callable[..., _T]) -> Callable[..., _T]:
    """Apply registered tier markers; consume wave-metadata tags without marking."""
    if tag in _REGISTERED_MARKERS:
        return getattr(pytest.mark, tag)(function)
    return function
