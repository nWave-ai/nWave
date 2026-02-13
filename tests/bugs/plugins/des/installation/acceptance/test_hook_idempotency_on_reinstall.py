"""
Bug 1: Duplicate Hooks on Install - Acceptance Tests.

Tests that verify:
- Multiple installs create exactly 1 hook (not duplicates)
- Uninstall removes ALL DES hooks (including duplicates)
- Hook detection works for both old and new formats
- Non-DES hooks are preserved during uninstall
"""

from pytest_bdd import scenarios

# Import step definitions - must use star imports for pytest-bdd registration
from .steps.common_steps import *  # noqa: F403
from .steps.hook_steps import *  # noqa: F403


# Collect all scenarios from the feature file
scenarios("bug-1-hook-idempotency.feature")
