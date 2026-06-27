"""Package-level fixture re-export for the plugin/skill deliverable-type suite.

The ``composition`` fixture is defined in ``steps/conftest.py`` for the shared
step vocabulary. The pytest-bdd runner modules (``test_*.py``) live one level up
and cannot see that ``steps``-scoped conftest, so this module re-exports the
fixture at the package level (mirrors the ``activation_gating`` precedent). Pure
fixture wiring -- no scenario, Given/When/Then, or assertion is defined here.
"""

from __future__ import annotations

from tests.des.acceptance.plugin_skill_deliverable_type.steps.conftest import (  # noqa: F401
    composition,
)
