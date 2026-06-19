"""Directory-level fixtures for the activation-gating acceptance suite.

The ``composition`` fixture (and its sandbox HOME wiring) is defined in
``steps/conftest.py`` for the shared step vocabulary. The pytest-bdd test
runner modules (``test_*.py``) live one level up, so they cannot see that
``steps``-scoped conftest. This module re-exports the fixture at the package
level so every scenario binding resolves the same production composition root.

DELIVER wiring fix (logged DELIVER/OQ-6): the original DISTILL scaffold placed
the ``composition`` fixture only under ``steps/conftest.py``; pytest-bdd
``scenarios(...)`` modules at the package root could not discover it. This
re-export is pure fixture wiring — no scenario, Given/When/Then, or assertion
is changed.
"""

from __future__ import annotations

from tests.des.acceptance.activation_gating.steps.conftest import (  # noqa: F401
    composition,
)
