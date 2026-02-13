"""
Pytest-BDD Configuration for DES Installation Bug Acceptance Tests.

This conftest.py at the acceptance level configures pytest-bdd
to discover feature files and step definitions.
"""

# Import fixtures from steps/conftest.py to make them available
from .steps.conftest import (
    claude_config_dir,
    clean_env,
    clean_settings_file,
    des_plugin,
    env_with_audit_log_dir,
    install_context,
    installed_des_path,
    project_root,
    settings_with_duplicates,
    settings_with_mixed_hooks,
    settings_with_old_format_hook,
    temp_claude_dir,
    temp_project_dir,
    test_context,
    test_logger,
)


# Re-export fixtures so they're discoverable
__all__ = [
    "claude_config_dir",
    "clean_env",
    "clean_settings_file",
    "des_plugin",
    "env_with_audit_log_dir",
    "install_context",
    "installed_des_path",
    "project_root",
    "settings_with_duplicates",
    "settings_with_mixed_hooks",
    "settings_with_old_format_hook",
    "temp_claude_dir",
    "temp_project_dir",
    "test_context",
    "test_logger",
]


def pytest_configure(config):
    """Register custom markers for DES bug tests."""
    config.addinivalue_line("markers", "bug_1: Bug 1 - Duplicate hooks on install")
    config.addinivalue_line("markers", "bug_2: Bug 2 - Audit logs location")
    config.addinivalue_line("markers", "bug_3: Bug 3 - Import paths")
    config.addinivalue_line("markers", "walking_skeleton: Walking skeleton tests")
    config.addinivalue_line("markers", "failing: Expected to fail until bug is fixed")


def pytest_collection_modifyitems(items):
    """Mark @failing-tagged scenarios as xfail."""
    import pytest

    for item in items:
        # pytest-bdd stores scenario tags in the item's own markers
        for marker in item.iter_markers():
            if marker.name == "failing":
                item.add_marker(
                    pytest.mark.xfail(
                        reason="Known bug - expected to fail until fix is deployed",
                        strict=False,
                    )
                )
                break
