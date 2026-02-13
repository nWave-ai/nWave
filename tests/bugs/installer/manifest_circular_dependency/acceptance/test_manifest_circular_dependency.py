"""
Installer Bug: Manifest Circular Dependency - Acceptance Tests.

Tests that verify:
- Fresh installation creates manifest before validation
- Validation doesn't fail due to missing manifest
- Manifest creation is independent of validation result
- Installation completes successfully with manifest present

NOTE: These are integration tests that require a virtual environment
and run the actual install-nwave script. Skip in regular test runs.
"""

import pytest
from pytest_bdd import scenarios

# Import step definitions - must use star imports for pytest-bdd registration
from .steps.common_steps import *  # noqa: F403
from .steps.installer_steps import *  # noqa: F403
from .steps.manifest_steps import *  # noqa: F403


# Mark all scenarios as integration tests requiring venv setup
pytestmark = pytest.mark.skip(
    reason="Integration test - requires venv setup and install-nwave script"
)

# Collect all scenarios from the feature file
scenarios("manifest_circular_dependency.feature")
