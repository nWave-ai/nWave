"""
Integration tests for Behavioral Equivalence Validation.

Step 02-02: Behavioral Equivalence Validation

This test validates that plugin-based installation produces correct results
matching the expected installation structure.

Domain: Plugin Infrastructure - Behavioral Equivalence
"""

import logging
import sys
from pathlib import Path

import pytest

from scripts.install.plugins.agents_plugin import AgentsPlugin
from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.commands_plugin import CommandsPlugin
from scripts.install.plugins.registry import PluginRegistry
from scripts.install.plugins.templates_plugin import TemplatesPlugin
from scripts.install.plugins.utilities_plugin import UtilitiesPlugin


# Add fixtures directory to path due to hyphenated directory name
_fixtures_path = Path(__file__).parent.parent / "fixtures"
if str(_fixtures_path) not in sys.path:
    sys.path.insert(0, str(_fixtures_path))

from baseline_snapshot import (  # noqa: E402
    InstallationSnapshot,
    compare_snapshots,
    validate_installation_structure,
)


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.behavioral_equivalence")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def project_root() -> Path:
    """Return the nWave project root directory."""
    current = Path(__file__).resolve()
    return current.parents[4]


@pytest.fixture
def framework_source(project_root: Path) -> Path:
    """Return path to the framework source directory."""
    return project_root / "nWave"


@pytest.fixture
def install_context(
    tmp_path: Path,
    project_root: Path,
    framework_source: Path,
    test_logger: logging.Logger,
) -> InstallContext:
    """Create InstallContext for testing."""
    test_claude_dir = tmp_path / ".claude"
    test_claude_dir.mkdir(parents=True, exist_ok=True)

    return InstallContext(
        claude_dir=test_claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=framework_source,
        dry_run=False,
    )


@pytest.fixture
def plugin_registry() -> PluginRegistry:
    """Create a PluginRegistry with all wrapper plugins."""
    registry = PluginRegistry()
    registry.register(AgentsPlugin())
    registry.register(CommandsPlugin())
    registry.register(TemplatesPlugin())
    registry.register(UtilitiesPlugin())
    return registry


# -----------------------------------------------------------------------------
# Test: Plugin Installation Creates Valid Structure
# -----------------------------------------------------------------------------


def test_plugin_installation_creates_expected_file_structure(
    plugin_registry: PluginRegistry,
    install_context: InstallContext,
):
    """
    Plugin-based installation should create expected file structure.

    Given: PluginRegistry with all 4 wrapper plugins
    When: registry.install_all(context) is called
    Then: Installation directory has expected structure
    """
    # Act
    results = plugin_registry.install_all(install_context)

    # Assert - all plugins succeeded
    for plugin_name, result in results.items():
        assert result.success, f"Plugin '{plugin_name}' failed: {result.message}"

    # Validate installation structure
    is_valid, issues = validate_installation_structure(install_context.claude_dir)
    assert is_valid, f"Installation structure validation failed: {issues}"


def test_plugin_installation_creates_agents_directory(
    plugin_registry: PluginRegistry,
    install_context: InstallContext,
):
    """
    Plugin-based installation should create agents directory with files.

    Given: PluginRegistry with AgentsPlugin
    When: registry.install_all(context) is called
    Then: agents/nw/ directory exists with .md files
    """
    # Act
    plugin_registry.install_all(install_context)

    # Assert
    agents_dir = install_context.claude_dir / "agents" / "nw"
    assert agents_dir.exists(), f"Agents directory not found: {agents_dir}"

    agent_files = list(agents_dir.glob("*.md"))
    assert len(agent_files) >= 10, (
        f"Expected >= 10 agent files, found {len(agent_files)}"
    )


def test_plugin_installation_creates_commands_directory(
    plugin_registry: PluginRegistry,
    install_context: InstallContext,
):
    """
    Plugin-based installation should create commands directory with files.

    Given: PluginRegistry with CommandsPlugin
    When: registry.install_all(context) is called
    Then: commands/nw/ directory exists with .md files
    """
    # Act
    plugin_registry.install_all(install_context)

    # Assert
    commands_dir = install_context.claude_dir / "commands" / "nw"
    assert commands_dir.exists(), f"Commands directory not found: {commands_dir}"

    command_files = list(commands_dir.glob("*.md"))
    assert len(command_files) >= 1, (
        f"Expected >= 1 command files, found {len(command_files)}"
    )


def test_plugin_installation_creates_templates_directory(
    plugin_registry: PluginRegistry,
    install_context: InstallContext,
):
    """
    Plugin-based installation should create templates directory with files.

    Given: PluginRegistry with TemplatesPlugin
    When: registry.install_all(context) is called
    Then: templates/ directory exists with template files
    """
    # Act
    plugin_registry.install_all(install_context)

    # Assert
    templates_dir = install_context.claude_dir / "templates"
    assert templates_dir.exists(), f"Templates directory not found: {templates_dir}"

    json_templates = list(templates_dir.glob("*.json"))
    yaml_templates = list(templates_dir.glob("*.yaml"))
    total_templates = len(json_templates) + len(yaml_templates)
    assert total_templates >= 1, (
        f"Expected >= 1 template files, found {total_templates}"
    )


# -----------------------------------------------------------------------------
# Test: Verification Produces Identical Results
# -----------------------------------------------------------------------------


def test_all_plugins_verify_successfully(
    plugin_registry: PluginRegistry,
    install_context: InstallContext,
):
    """
    All plugins should verify successfully after installation.

    Given: Plugin-based installation is complete
    When: Each plugin's verify() method is called
    Then: All verifications pass
    """
    # Arrange - install first
    install_results = plugin_registry.install_all(install_context)

    # Assert all installed successfully
    for plugin_name, result in install_results.items():
        assert result.success, (
            f"Plugin '{plugin_name}' install failed: {result.message}"
        )

    # Act & Assert - verify each plugin
    for plugin_name, plugin in plugin_registry.plugins.items():
        verify_result = plugin.verify(install_context)
        assert verify_result.success, (
            f"Plugin '{plugin_name}' verification failed: {verify_result.message}"
        )


# -----------------------------------------------------------------------------
# Test: Snapshot Comparison for Behavioral Equivalence
# -----------------------------------------------------------------------------


def test_installation_snapshot_captures_all_files(
    plugin_registry: PluginRegistry,
    install_context: InstallContext,
):
    """
    InstallationSnapshot should capture all installed files.

    Given: Plugin-based installation is complete
    When: InstallationSnapshot.capture() is called
    Then: Snapshot contains all installed files with correct counts
    """
    # Arrange - install first
    plugin_registry.install_all(install_context)

    # Act - capture snapshot
    snapshot = InstallationSnapshot.capture(install_context.claude_dir)

    # Assert
    assert snapshot.total_file_count > 0, "Snapshot should contain files"
    assert snapshot.total_size_bytes > 0, "Snapshot should have non-zero size"
    assert len(snapshot.files) == snapshot.total_file_count, (
        "Files dict should match total count"
    )


def test_identical_installations_produce_matching_snapshots(
    plugin_registry: PluginRegistry,
    install_context: InstallContext,
    project_root: Path,
    framework_source: Path,
    test_logger: logging.Logger,
    tmp_path: Path,
):
    """
    Two identical installations should produce matching snapshots.

    Given: Two clean directories
    When: Plugin-based installation runs on both
    Then: Snapshots are identical
    """
    # First installation
    plugin_registry.install_all(install_context)
    snapshot1 = InstallationSnapshot.capture(install_context.claude_dir)

    # Second installation in different temp directory
    second_dir = tmp_path / ".claude2"
    second_dir.mkdir(parents=True, exist_ok=True)

    second_context = InstallContext(
        claude_dir=second_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=framework_source,
        dry_run=False,
    )

    # Create fresh registry for second install
    registry2 = PluginRegistry()
    registry2.register(AgentsPlugin())
    registry2.register(CommandsPlugin())
    registry2.register(TemplatesPlugin())
    registry2.register(UtilitiesPlugin())

    registry2.install_all(second_context)
    snapshot2 = InstallationSnapshot.capture(second_dir)

    # Compare
    comparison = compare_snapshots(snapshot1, snapshot2)

    assert comparison.files_match, (
        f"File sets differ: missing={comparison.missing_files}, extra={comparison.extra_files}"
    )
    assert comparison.content_match, (
        f"Content differs for files: {comparison.content_mismatches}"
    )
    assert comparison.identical, comparison.message


# -----------------------------------------------------------------------------
# Test: No Regressions in Installation Behavior
# -----------------------------------------------------------------------------


def test_installation_does_not_leave_empty_directories(
    plugin_registry: PluginRegistry,
    install_context: InstallContext,
):
    """
    Installation should not leave empty directories.

    Given: Plugin-based installation is complete
    When: Checking for empty directories
    Then: No empty directories exist
    """
    # Act
    plugin_registry.install_all(install_context)

    # Assert - check for empty directories
    empty_dirs = []
    for dir_path in install_context.claude_dir.rglob("*"):
        if dir_path.is_dir() and not any(dir_path.iterdir()):
            empty_dirs.append(str(dir_path))

    assert len(empty_dirs) == 0, f"Found empty directories: {empty_dirs}"


def test_installation_creates_valid_file_contents(
    plugin_registry: PluginRegistry,
    install_context: InstallContext,
):
    """
    All installed files should have valid (non-empty) contents.

    Given: Plugin-based installation is complete
    When: Checking file contents
    Then: All files have non-empty content
    """
    # Act
    plugin_registry.install_all(install_context)

    # Assert - check for empty files
    empty_files = []
    for file_path in install_context.claude_dir.rglob("*"):
        if file_path.is_file() and file_path.stat().st_size == 0:
            empty_files.append(str(file_path))

    assert len(empty_files) == 0, f"Found empty files: {empty_files}"


def test_installation_idempotent(
    plugin_registry: PluginRegistry,
    install_context: InstallContext,
):
    """
    Running installation twice should produce identical results.

    Given: Plugin-based installation has run once
    When: Installation runs again
    Then: File structure remains identical
    """
    # First install
    plugin_registry.install_all(install_context)
    snapshot1 = InstallationSnapshot.capture(install_context.claude_dir)

    # Second install (re-run)
    plugin_registry.install_all(install_context)
    snapshot2 = InstallationSnapshot.capture(install_context.claude_dir)

    # Compare
    comparison = compare_snapshots(snapshot1, snapshot2)

    assert comparison.identical, f"Installation not idempotent: {comparison.message}"
