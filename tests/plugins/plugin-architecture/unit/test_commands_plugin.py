"""
Unit tests for CommandsPlugin.

Tests the CommandsPlugin install() and verify() methods through the
InstallationPlugin interface (driving port).

Source: nWave/tasks/nw/ (no dist/ide fallback)
Excludes: README.md

Domain: Plugin Infrastructure - Commands Installation
"""

import logging
from pathlib import Path

import pytest

from scripts.install.plugins.base import InstallContext, PluginResult
from scripts.install.plugins.commands_plugin import CommandsPlugin


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.commands_plugin")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def project_root() -> Path:
    """Return the nWave project root directory."""
    current = Path(__file__).resolve()
    return current.parents[4]  # 4 levels up from test file


@pytest.fixture
def commands_source_dir(project_root: Path) -> Path:
    """Return the canonical commands source directory: nWave/tasks/nw/."""
    return project_root / "nWave" / "tasks" / "nw"


@pytest.fixture
def install_context(tmp_path: Path, project_root: Path, test_logger: logging.Logger):
    """Create InstallContext for testing with real paths.

    framework_source deliberately points to a non-existent path to prove
    the plugin reads from project_root/nWave/tasks/nw/ instead.
    """
    test_claude_dir = tmp_path / ".claude"
    test_claude_dir.mkdir(parents=True, exist_ok=True)

    return InstallContext(
        claude_dir=test_claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=tmp_path / "nonexistent_dist",
        dry_run=False,
    )


# -----------------------------------------------------------------------------
# Acceptance Test: Single source, no dist/ide, installs only *.md commands
# -----------------------------------------------------------------------------


def test_commands_plugin_installs_only_nw_commands(
    tmp_path: Path,
    project_root: Path,
    test_logger: logging.Logger,
):
    """CommandsPlugin.install() should read only *.md files from nWave/tasks/nw/.

    Acceptance test: framework_source is set to a non-existent path to prove
    the plugin does NOT depend on dist/ide. It must read from
    project_root/nWave/tasks/nw/ directly. After install, the target directory
    must contain only *.md files, no dist/ide artifacts.
    All 18 commands must be discoverable at ~/.claude/commands/nw/.
    """
    # Arrange - framework_source deliberately does NOT exist
    test_claude_dir = tmp_path / ".claude"
    test_claude_dir.mkdir(parents=True, exist_ok=True)

    context = InstallContext(
        claude_dir=test_claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=tmp_path / "nonexistent_dist",  # NOT dist/ide
        dry_run=False,
    )

    plugin = CommandsPlugin()
    target_commands_dir = context.claude_dir / "commands" / "nw"
    source_commands_dir = context.project_root / "nWave" / "tasks" / "nw"

    # Count expected: *.md files in nWave/tasks/nw/ root
    expected_command_files = list(source_commands_dir.glob("*.md"))
    assert len(expected_command_files) >= 18, (
        f"Expected at least 18 *.md command files in source, found {len(expected_command_files)}"
    )

    # Act
    result = plugin.install(context)

    # Assert - installation succeeded even without dist/ide
    assert result.success, f"Installation failed: {result.message}"

    # Assert - no config.json (dist/ide artifact) was copied
    config_json = target_commands_dir / "config.json"
    assert not config_json.exists(), (
        "config.json (dist/ide artifact) should not be present in target"
    )

    # Assert - target contains only *.md files (matching source count)
    target_files = list(target_commands_dir.glob("*.md"))
    assert len(target_files) == len(expected_command_files), (
        f"Expected {len(expected_command_files)} *.md files in target, "
        f"found {len(target_files)}"
    )


# -----------------------------------------------------------------------------
# Unit Tests: CommandsPluginShould
# -----------------------------------------------------------------------------


class TestCommandsPluginShould:
    """Unit tests for CommandsPlugin through the InstallationPlugin interface."""

    def test_copy_md_files_from_nwave_tasks_nw_to_target(
        self, install_context: InstallContext, commands_source_dir: Path
    ):
        """
        Given: nWave/tasks/nw/ contains *.md command files
        When: install() is called
        Then: All *.md files are copied to {claude_dir}/commands/nw/
        """
        plugin = CommandsPlugin()
        target_commands_dir = install_context.claude_dir / "commands" / "nw"

        assert commands_source_dir.exists(), (
            f"Commands source not found: {commands_source_dir}"
        )
        source_md_files = list(commands_source_dir.glob("*.md"))
        assert len(source_md_files) >= 1, "No *.md command files in source"

        result = plugin.install(install_context)

        assert result.success, f"Installation failed: {result.message}"
        assert target_commands_dir.exists()

        target_files = list(target_commands_dir.glob("*.md"))
        assert len(target_files) == len(source_md_files), (
            f"Expected {len(source_md_files)} *.md files, found {len(target_files)}"
        )

    def test_return_plugin_result_with_correct_file_count(
        self, install_context: InstallContext
    ):
        """
        Given: nWave/tasks/nw/ contains command files
        When: install() is called
        Then: PluginResult reports correct count and installed_files list
        """
        plugin = CommandsPlugin()
        source_dir = install_context.project_root / "nWave" / "tasks" / "nw"
        expected_count = len(list(source_dir.glob("*.md")))

        result = plugin.install(install_context)

        assert isinstance(result, PluginResult)
        assert result.success is True
        assert result.plugin_name == "commands"
        assert f"{expected_count} files" in result.message
        assert result.installed_files is not None
        assert len(result.installed_files) == expected_count

    def test_verify_confirms_command_files_present_after_install(
        self, install_context: InstallContext
    ):
        """
        Given: install() completed successfully
        When: verify() is called
        Then: PluginResult.success is True with verification count
        """
        plugin = CommandsPlugin()
        install_result = plugin.install(install_context)
        assert install_result.success, f"Install failed: {install_result.message}"

        verify_result = plugin.verify(install_context)

        assert verify_result.success is True
        assert "Commands verification passed" in verify_result.message


# -----------------------------------------------------------------------------
# Verify Error Cases
# -----------------------------------------------------------------------------


def test_commands_plugin_verify_fails_when_target_directory_missing(
    tmp_path: Path, project_root: Path, test_logger: logging.Logger
):
    """CommandsPlugin.verify() should fail when target directory does not exist."""
    empty_claude_dir = tmp_path / ".claude-empty"
    empty_claude_dir.mkdir(parents=True, exist_ok=True)

    context = InstallContext(
        claude_dir=empty_claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )

    plugin = CommandsPlugin()
    verify_result = plugin.verify(context)

    assert verify_result.success is False
    assert "target directory does not exist" in verify_result.message


def test_commands_plugin_verify_fails_when_no_command_files(
    tmp_path: Path, project_root: Path, test_logger: logging.Logger
):
    """CommandsPlugin.verify() should fail when directory exists but has no .md files."""
    claude_dir = tmp_path / ".claude-nofiles"
    commands_dir = claude_dir / "commands" / "nw"
    commands_dir.mkdir(parents=True, exist_ok=True)

    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )

    plugin = CommandsPlugin()
    verify_result = plugin.verify(context)

    assert verify_result.success is False
    assert "no command files found" in verify_result.message
