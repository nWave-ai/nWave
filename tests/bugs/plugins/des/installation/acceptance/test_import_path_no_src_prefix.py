"""
Bug 3: Import Paths in Installed DES - Acceptance Tests.

Tests that verify:
- Installed DES contains no "from src.des" imports
- DES is importable with only installed path in PYTHONPATH
- Hooks work without development PYTHONPATH
- All DES submodules are importable
- Package structure has correct __init__.py files
"""

from pytest_bdd import scenarios

# Import step definitions - must use star imports for pytest-bdd registration
from .steps.common_steps import *  # noqa: F403
from .steps.import_path_steps import *  # noqa: F403


# Collect all scenarios from the feature file
scenarios("bug-3-import-paths.feature")
