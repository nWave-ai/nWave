"""
Pytest-BDD Configuration and Fixtures for DES Installation Bug Acceptance Tests.

This module provides shared fixtures for testing DES installation bugs:
- Bug 1: Duplicate hooks on multiple installs
- Bug 2: Audit logs in global instead of project-local location
- Bug 3: Import paths using "from src.des" instead of "from des"

Organization:
- Fixtures for test environment setup
- Service provider injection pattern (production service integration)
- Test data management for settings.local.json manipulation
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

import pytest

# Helper functions are in helpers.py to avoid circular imports
from .helpers import (  # noqa: F401
    count_des_hooks,
    is_des_hook,
    is_des_hook_entry,
    scan_for_bad_imports,
)


# Step definitions are auto-discovered by pytest-bdd from this package
# No explicit imports needed - pytest-bdd finds them via the steps directory


# -----------------------------------------------------------------------------
# Fixtures: Test Environment
# -----------------------------------------------------------------------------


@pytest.fixture
def project_root() -> Path:
    """Return the ai-craft project root directory."""
    # Navigate from tests/bugs/plugins/des/installation/acceptance/steps/ to project root
    current = Path(__file__).resolve()
    return current.parents[7]  # 7 levels up from conftest.py


@pytest.fixture
def claude_config_dir() -> str:
    """Return the real Claude config directory path."""
    return str(Path.home() / ".claude")


@pytest.fixture
def installed_des_path() -> Path:
    """Return the installed DES module path."""
    return Path.home() / ".claude" / "lib" / "python" / "des"


@pytest.fixture
def temp_claude_dir(tmp_path: Path) -> Path:
    """
    Provide a temporary Claude config directory for testing.

    Returns a temporary directory that simulates ~/.claude for testing.
    The directory is automatically cleaned up after the test.
    """
    test_dir = tmp_path / ".claude"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """
    Provide a temporary project directory for testing.

    Used for testing project-local audit log location.
    """
    project_dir = tmp_path / "test-project"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.des-installation-bugs")
    logger.setLevel(logging.DEBUG)

    # Add console handler if not already present
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# -----------------------------------------------------------------------------
# Fixtures: Settings File Management
# -----------------------------------------------------------------------------


@pytest.fixture
def clean_settings_file(temp_claude_dir: Path) -> Path:
    """
    Create a clean settings.json with no hooks.

    Used for testing hook installation from scratch.
    """
    settings_file = temp_claude_dir / "settings.json"
    settings_file.write_text(json.dumps({"permissions": {"allow": []}}, indent=2))
    return settings_file


@pytest.fixture
def settings_with_duplicates(temp_claude_dir: Path) -> Path:
    """
    Create settings.json with duplicate DES hooks in nested format.

    Simulates the bug state where multiple installs created duplicates.
    Includes a non-DES hook to verify preservation during uninstall.
    """
    settings_file = temp_claude_dir / "settings.json"
    lib_path = temp_claude_dir / "lib" / "python"

    # Create hook command matching the real nested format
    hook_command_pretask = (
        f"PYTHONPATH={lib_path} python3 -m "
        f"des.adapters.drivers.hooks.claude_code_hook_adapter pre-task"
    )
    hook_command_stop = (
        f"PYTHONPATH={lib_path} python3 -m "
        f"des.adapters.drivers.hooks.claude_code_hook_adapter subagent-stop"
    )

    config = {
        "permissions": {"allow": []},
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Task",
                    "hooks": [{"type": "command", "command": hook_command_pretask}],
                },
                {
                    "matcher": "Task",
                    "hooks": [{"type": "command", "command": hook_command_pretask}],
                },  # DUPLICATE
                # Non-DES hook that should be preserved during uninstall
                {"matcher": "Write", "command": "custom-write-validator.py"},
            ],
            "SubagentStop": [
                {"hooks": [{"type": "command", "command": hook_command_stop}]},
                {
                    "hooks": [{"type": "command", "command": hook_command_stop}]
                },  # DUPLICATE
            ],
        },
    }
    settings_file.write_text(json.dumps(config, indent=2))
    return settings_file


@pytest.fixture
def settings_with_mixed_hooks(temp_claude_dir: Path) -> Path:
    """
    Create settings.json with DES hooks and non-DES hooks.

    Used for testing that non-DES hooks are preserved during uninstall.
    """
    settings_file = temp_claude_dir / "settings.json"
    lib_path = temp_claude_dir / "lib" / "python"

    hook_command_pretask = (
        f"PYTHONPATH={lib_path} python3 -m "
        f"des.adapters.drivers.hooks.claude_code_hook_adapter pre-task"
    )
    hook_command_stop = (
        f"PYTHONPATH={lib_path} python3 -m "
        f"des.adapters.drivers.hooks.claude_code_hook_adapter subagent-stop"
    )

    config = {
        "permissions": {"allow": []},
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Task",
                    "hooks": [{"type": "command", "command": hook_command_pretask}],
                },
                # Non-DES hook that should be preserved
                {"matcher": "Write", "command": "custom-write-validator.py"},
            ],
            "SubagentStop": [
                {"hooks": [{"type": "command", "command": hook_command_stop}]},
            ],
        },
    }
    settings_file.write_text(json.dumps(config, indent=2))
    return settings_file


@pytest.fixture
def settings_with_old_format_hook(temp_claude_dir: Path) -> Path:
    """
    Create settings.json with old-format DES hook command.

    Old format: python3 src/des/.../claude_code_hook_adapter.py (flat)
    New format: python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter (nested)
    """
    settings_file = temp_claude_dir / "settings.json"

    # Old format command (flat, contains claude_code_hook_adapter but different path)
    old_command = (
        "python3 src/des/adapters/drivers/hooks/claude_code_hook_adapter.py pre-task"
    )

    config = {
        "permissions": {"allow": []},
        "hooks": {
            "PreToolUse": [
                {"matcher": "Task", "command": old_command},
            ],
            "SubagentStop": [],
        },
    }
    settings_file.write_text(json.dumps(config, indent=2))
    return settings_file


# -----------------------------------------------------------------------------
# Fixtures: Plugin Infrastructure
# -----------------------------------------------------------------------------


@pytest.fixture
def install_context(
    temp_claude_dir: Path, project_root: Path, test_logger: logging.Logger
):
    """
    Create InstallContext for testing DES plugin.

    This fixture provides dependency injection for plugin installation tests.
    Uses production service patterns as required by DISTILL wave guidelines.
    """
    try:
        from scripts.install.plugins.base import InstallContext

        return InstallContext(
            claude_dir=temp_claude_dir,
            scripts_dir=project_root / "scripts" / "install",
            templates_dir=project_root / "nWave" / "templates",
            logger=test_logger,
            project_root=project_root,
            dry_run=False,
        )
    except ImportError as e:
        pytest.skip(f"Plugin infrastructure not importable: {e}")


@pytest.fixture
def des_plugin():
    """
    Provide DESPlugin instance for testing.

    Uses production service pattern.
    """
    try:
        from scripts.install.plugins.des_plugin import DESPlugin

        return DESPlugin()
    except ImportError as e:
        pytest.skip(f"DESPlugin not importable: {e}")


# -----------------------------------------------------------------------------
# Fixtures: Environment Variable Management
# -----------------------------------------------------------------------------


@pytest.fixture
def clean_env():
    """
    Fixture to capture and restore environment variables.

    Ensures tests don't pollute the environment.
    """
    original_env = os.environ.copy()
    yield os.environ
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def env_with_audit_log_dir(clean_env, tmp_path: Path) -> dict[str, Any]:
    """
    Set DES_AUDIT_LOG_DIR environment variable for testing.

    Returns dict with the custom log directory path.
    """
    custom_log_dir = tmp_path / "custom" / "logs"
    custom_log_dir.mkdir(parents=True, exist_ok=True)
    clean_env["DES_AUDIT_LOG_DIR"] = str(custom_log_dir)
    return {"log_dir": custom_log_dir, "env": clean_env}


# -----------------------------------------------------------------------------
# Fixtures: Test Data and Context
# -----------------------------------------------------------------------------


@pytest.fixture
def test_context() -> dict:
    """
    Provide a mutable context dictionary for sharing state between steps.

    This is used by pytest-bdd steps to pass data between Given/When/Then.
    """
    context = {}
    yield context

    # Cleanup: restore original working directory if changed
    if "original_cwd" in context:
        os.chdir(context["original_cwd"])


# -----------------------------------------------------------------------------
# Pytest-BDD Configuration
# -----------------------------------------------------------------------------


def pytest_bdd_step_error(
    request, feature, scenario, step, step_func, step_func_args, exception
):
    """Log step errors for debugging."""
    logging.error(f"Step failed: {step.name}")
    logging.error(f"Feature: {feature.name}")
    logging.error(f"Scenario: {scenario.name}")
    logging.error(f"Exception: {exception}")
