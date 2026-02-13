"""
Pytest-BDD Configuration for Plugin Architecture Acceptance Tests.

This conftest.py is at the acceptance test root level and registers
the step definitions for all feature files.
"""

import logging
from pathlib import Path

import pytest


# Step definitions are defined directly in this conftest.py
# and in the test files themselves to avoid import issues
# with hyphenated directory names


# -----------------------------------------------------------------------------
# Fixtures: Test Environment
# -----------------------------------------------------------------------------


@pytest.fixture
def project_root() -> Path:
    """Return the nWave project root directory."""
    # Navigate from tests/nWave/plugin-architecture/acceptance/ to project root
    current = Path(__file__).resolve()
    return current.parents[4]  # 4 levels up from conftest.py


@pytest.fixture
def claude_config_dir() -> str:
    """Return the Claude config directory path."""
    return "~/.claude"


@pytest.fixture
def clean_test_directory(tmp_path: Path) -> Path:
    """
    Provide a clean test installation directory.

    Returns a temporary directory that simulates ~/.claude for testing.
    The directory is automatically cleaned up after the test.
    """
    test_dir = tmp_path / ".claude"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.plugin-architecture")
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
# Fixtures: Plugin Infrastructure
# -----------------------------------------------------------------------------


@pytest.fixture
def install_context(
    clean_test_directory: Path, project_root: Path, test_logger: logging.Logger
):
    """
    Create InstallContext for testing.

    This fixture provides dependency injection for plugin installation tests.
    """
    from scripts.install.plugins.base import InstallContext

    return InstallContext(
        claude_dir=clean_test_directory,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )


@pytest.fixture
def plugin_registry():
    """
    Create a PluginRegistry instance for testing.
    """
    from scripts.install.plugins.registry import PluginRegistry

    return PluginRegistry()


# -----------------------------------------------------------------------------
# Fixtures: Test Data
# -----------------------------------------------------------------------------


@pytest.fixture
def agent_source_files(project_root: Path) -> list[Path]:
    """Return list of agent source files for testing."""
    agents_dir = project_root / "nWave" / "agents" / "nw"
    if not agents_dir.exists():
        pytest.skip(f"Agent source directory not found: {agents_dir}")

    return list(agents_dir.glob("*.md"))
