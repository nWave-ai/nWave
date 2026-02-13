"""
Walking Skeleton Test - DES Installation Bug Detection.

This test verifies the test infrastructure works before running bug-specific tests.
"""

from pytest_bdd import scenarios

# Import step definitions - must use star imports for pytest-bdd registration
from .steps.common_steps import *  # noqa: F403


# Collect all scenarios from the feature file
scenarios("walking-skeleton.feature")
