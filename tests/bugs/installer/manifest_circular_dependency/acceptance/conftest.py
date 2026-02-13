"""
Pytest-BDD Configuration for Installer Manifest Circular Dependency Bug Tests.

This conftest.py at the acceptance level configures pytest-bdd
to discover feature files and step definitions.
"""

# Import fixtures from steps/conftest.py to make them available
from .steps.conftest import project_root, test_logger


# Re-export fixtures so they're discoverable
__all__ = [
    "project_root",
    "test_logger",
]


def pytest_configure(config):
    """Register custom markers for manifest bug tests."""
    config.addinivalue_line(
        "markers",
        "manifest_bug: Bug - Manifest circular dependency in installer validation",
    )
    config.addinivalue_line("markers", "failing: Expected to fail until bug is fixed")
