"""
Test file for dependency verification acceptance tests (AC-06).

This file imports step definitions and loads scenarios from feature files.
pytest-bdd requires test files to be named test_*.py for discovery.
"""

from tests.installer.acceptance.installation.step_defs.steps_dependency import *  # noqa: F403
from tests.installer.acceptance.installation.step_defs.steps_preflight import *  # noqa: F403
