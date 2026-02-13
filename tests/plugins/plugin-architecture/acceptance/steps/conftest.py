"""
Pytest-BDD Configuration and Fixtures for Plugin Architecture Acceptance Tests.

This module provides shared fixtures and configuration for all acceptance tests
in the plugin-architecture feature.

Organization:
- Fixtures for test environment setup
- Service provider injection pattern
- Test data management
"""

import logging
from pathlib import Path

import pytest

# Import step definitions to register them with pytest-bdd
from . import (
    common_steps,  # noqa: F401
    installer_steps,  # noqa: F401
    plugin_steps,  # noqa: F401
    registry_steps,  # noqa: F401
    verification_steps,  # noqa: F401
)


# -----------------------------------------------------------------------------
# Fixtures: Test Environment
# -----------------------------------------------------------------------------


@pytest.fixture
def project_root() -> Path:
    """Return the nWave project root directory."""
    # Navigate from tests/nWave/plugin-architecture/acceptance/steps/ to project root
    current = Path(__file__).resolve()
    return current.parents[5]  # 5 levels up from conftest.py


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
    It uses production service patterns as required by DISTILL wave guidelines.
    """
    # Import here to avoid circular imports until plugin infrastructure exists
    try:
        from scripts.install.plugins.base import InstallContext

        return InstallContext(
            claude_dir=clean_test_directory,
            scripts_dir=project_root / "scripts" / "install",
            templates_dir=project_root / "nWave" / "templates",
            logger=test_logger,
            dry_run=False,
        )
    except ImportError:
        # Plugin infrastructure not yet implemented
        pytest.skip("Plugin infrastructure not yet implemented")


@pytest.fixture
def plugin_registry(project_root: Path):
    """
    Create a PluginRegistry instance for testing.

    This fixture provides the production PluginRegistry class,
    following the production service integration pattern.
    """
    try:
        from scripts.install.plugins.registry import PluginRegistry

        return PluginRegistry()
    except ImportError:
        pytest.skip("Plugin infrastructure not yet implemented")


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


@pytest.fixture
def baseline_file_tree() -> dict:
    """
    Capture baseline file tree from pre-plugin installer.

    This fixture is used for regression testing to ensure
    plugin-based installation produces identical results.
    """
    # TODO: Implement baseline capture when switchover testing begins
    return {}


# -----------------------------------------------------------------------------
# Fixtures: Service Providers (Production Integration Pattern)
# -----------------------------------------------------------------------------


@pytest.fixture
def backup_manager():
    """
    Provide BackupManager service for testing.

    Uses production service pattern (_serviceProvider.GetRequiredService<T>() equivalent).
    """
    try:
        from scripts.install.backup import BackupManager

        return BackupManager()
    except ImportError:
        pytest.skip("BackupManager not yet implemented")


@pytest.fixture
def installation_verifier():
    """
    Provide InstallationVerifier service for testing.

    Uses production service pattern for verification tests.
    """
    try:
        from scripts.install.verifier import InstallationVerifier

        return InstallationVerifier()
    except ImportError:
        pytest.skip("InstallationVerifier not yet implemented")


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
