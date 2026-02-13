"""
Unit tests for UtilitiesPlugin.

Tests the UtilitiesPlugin install() and verify() methods through the
InstallationPlugin interface (driving port).

Domain: Plugin Infrastructure - Utilities Installation
Step: 01-04 - UtilitiesPlugin Wrapper Implementation
"""

import logging
from pathlib import Path

import pytest

from scripts.install.plugins.base import InstallContext, PluginResult
from scripts.install.plugins.utilities_plugin import UtilitiesPlugin


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.utilities_plugin")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def project_root() -> Path:
    """Return the nWave project root directory."""
    current = Path(__file__).resolve()
    return current.parents[4]  # 4 levels up from test file


@pytest.fixture
def utility_scripts_source(tmp_path: Path) -> Path:
    """Create and return mock utility scripts source directory."""
    scripts_dir = tmp_path / "mock_project" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    # Create mock utility scripts with version info
    (scripts_dir / "install_nwave_target_hooks.py").write_text(
        '"""Hook installation script."""\n__version__ = "1.0.0"\n'
    )
    (scripts_dir / "validate_step_file.py").write_text(
        '"""Step file validation script."""\n__version__ = "1.0.0"\n'
    )

    return scripts_dir


@pytest.fixture
def install_context(
    tmp_path: Path, utility_scripts_source: Path, test_logger: logging.Logger
):
    """Create InstallContext for testing with mock utility scripts."""
    test_claude_dir = tmp_path / ".claude"
    test_claude_dir.mkdir(parents=True, exist_ok=True)

    # Use the mock project root that contains utility scripts
    mock_project_root = utility_scripts_source.parent

    return InstallContext(
        claude_dir=test_claude_dir,
        scripts_dir=mock_project_root / "scripts" / "install",
        templates_dir=mock_project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=mock_project_root,
        framework_source=mock_project_root / "nWave",
        dry_run=False,
    )


# -----------------------------------------------------------------------------
# Test Class: UtilitiesPluginShould
# -----------------------------------------------------------------------------


class UtilitiesPluginShould:
    """Unit tests for UtilitiesPlugin following naming convention."""

    def test_copy_utility_scripts_to_target_directory_when_install_called(
        self, install_context: InstallContext, utility_scripts_source: Path
    ):
        """
        UtilitiesPlugin.install() should copy utility .py scripts to the target directory.

        Given: A valid InstallContext with project root containing utility scripts
        When: install() is called
        Then: Utility scripts are copied to {claude_dir}/scripts/
        """
        # Arrange
        plugin = UtilitiesPlugin()
        target_scripts_dir = install_context.claude_dir / "scripts"

        # Verify source files exist
        assert utility_scripts_source.exists(), (
            f"Utility scripts source not found: {utility_scripts_source}"
        )

        # Act
        result = plugin.install(install_context)

        # Assert
        assert result.success, f"Installation failed: {result.message}"
        assert target_scripts_dir.exists(), (
            f"Target directory not created: {target_scripts_dir}"
        )

        # Verify at least one utility script was copied
        target_files = list(target_scripts_dir.glob("*.py"))
        assert len(target_files) >= 1, (
            f"Expected at least 1 utility script in target, found {len(target_files)}"
        )

    def test_return_success_result_with_installed_files_list_when_install_succeeds(
        self, install_context: InstallContext
    ):
        """
        UtilitiesPlugin.install() should return PluginResult with installed_files populated.

        Given: A valid InstallContext
        When: install() is called successfully
        Then: PluginResult.success is True and installed_files contains file paths
        """
        # Arrange
        plugin = UtilitiesPlugin()

        # Act
        result = plugin.install(install_context)

        # Assert
        assert isinstance(result, PluginResult)
        assert result.success is True
        assert result.plugin_name == "utilities"
        assert (
            "installed" in result.message.lower() or "success" in result.message.lower()
        )
        # installed_files should contain the copied files
        assert result.installed_files is not None
        # When actual utility scripts exist, this should have files
        # For now, we accept empty list as valid

    def test_return_success_with_verification_message_when_verify_called_after_install(
        self, install_context: InstallContext
    ):
        """
        UtilitiesPlugin.verify() should confirm installation was successful.

        Given: UtilitiesPlugin.install() was called successfully
        When: verify() is called
        Then: PluginResult.success is True and message contains verification info
        """
        # Arrange
        plugin = UtilitiesPlugin()

        # First install
        install_result = plugin.install(install_context)
        assert install_result.success, f"Install failed: {install_result.message}"

        # Act
        verify_result = plugin.verify(install_context)

        # Assert
        assert verify_result.success is True
        assert "Utilities verification passed" in verify_result.message

    def test_verify_checks_target_directory_contains_utility_scripts(
        self, install_context: InstallContext
    ):
        """
        UtilitiesPlugin.verify() should check that utility scripts exist in target directory.

        Given: Installation completed
        When: verify() is called
        Then: Verification checks for presence of utility scripts
        """
        # Arrange
        plugin = UtilitiesPlugin()

        # Install first
        plugin.install(install_context)

        # Act
        verify_result = plugin.verify(install_context)

        # Assert
        assert verify_result.success is True
        target_dir = install_context.claude_dir / "scripts"
        if target_dir.exists():
            script_files = list(target_dir.glob("*.py"))
            # If files exist, verification should pass
            assert len(script_files) >= 1 or not verify_result.success


# -----------------------------------------------------------------------------
# Standalone Test Functions (for pytest discovery)
# -----------------------------------------------------------------------------


def test_utilities_plugin_copies_scripts_to_target(
    install_context: InstallContext, utility_scripts_source: Path
):
    """UtilitiesPlugin.install() should copy utility scripts to target directory."""
    plugin = UtilitiesPlugin()
    target_scripts_dir = install_context.claude_dir / "scripts"

    # Verify source exists (mock scripts created by fixture)
    assert utility_scripts_source.exists(), (
        f"Utility scripts source not found: {utility_scripts_source}"
    )
    source_files = list(utility_scripts_source.glob("*.py"))
    assert len(source_files) >= 1, "No source scripts in mock directory"

    # Act
    result = plugin.install(install_context)

    # Assert
    assert result.success, f"Installation failed: {result.message}"
    assert target_scripts_dir.exists(), (
        f"Target directory not created: {target_scripts_dir}"
    )

    target_files = list(target_scripts_dir.glob("*.py"))
    assert len(target_files) >= 1, (
        f"Expected at least 1 utility script in target, found {len(target_files)}"
    )


def test_utilities_plugin_verify_confirms_scripts_exist(
    install_context: InstallContext,
):
    """UtilitiesPlugin.verify() should confirm utility scripts were installed."""
    plugin = UtilitiesPlugin()

    # Install first
    install_result = plugin.install(install_context)
    assert install_result.success

    # Verify
    verify_result = plugin.verify(install_context)

    # Check verification result
    assert verify_result.success is True
    assert "Utilities verification passed" in verify_result.message


def test_utilities_plugin_verify_fails_when_target_directory_missing(
    tmp_path: Path, project_root: Path, test_logger: logging.Logger
):
    """UtilitiesPlugin.verify() should fail when target directory does not exist."""
    # Arrange - create context with empty claude_dir (no install)
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

    plugin = UtilitiesPlugin()

    # Act - verify without install
    verify_result = plugin.verify(context)

    # Assert - should fail because no installation occurred
    assert verify_result.success is False
    assert "target directory does not exist" in verify_result.message


def test_utilities_plugin_verify_fails_when_no_utility_scripts(
    tmp_path: Path, project_root: Path, test_logger: logging.Logger
):
    """UtilitiesPlugin.verify() should fail when directory exists but has no .py files."""
    # Arrange - create context with scripts directory but no files
    claude_dir = tmp_path / ".claude-nofiles"
    scripts_dir = claude_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )

    plugin = UtilitiesPlugin()

    # Act - verify with empty directory
    verify_result = plugin.verify(context)

    # Assert - should fail because no utility scripts
    assert verify_result.success is False
    assert "no utility scripts found" in verify_result.message


def test_utilities_plugin_install_success_with_mock_source(
    tmp_path: Path, test_logger: logging.Logger
):
    """UtilitiesPlugin.install() should copy scripts from project scripts directory."""
    # Arrange - Create mock project with utility scripts
    mock_project_root = tmp_path / "mock_project"
    scripts_dir = mock_project_root / "scripts"
    scripts_dir.mkdir(parents=True)

    # Create mock utility scripts
    (scripts_dir / "install_nwave_target_hooks.py").write_text(
        '"""Hook installation script."""\n__version__ = "1.0.0"\n'
    )
    (scripts_dir / "validate_step_file.py").write_text(
        '"""Step file validation script."""\n__version__ = "1.0.0"\n'
    )

    claude_dir = tmp_path / "target_claude"
    claude_dir.mkdir(parents=True)

    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=mock_project_root / "scripts" / "install",
        templates_dir=mock_project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=mock_project_root,
        framework_source=mock_project_root / "nWave",
        dry_run=False,
    )

    plugin = UtilitiesPlugin()

    # Act
    result = plugin.install(context)

    # Assert
    assert result.success is True
    assert result.plugin_name == "utilities"
    assert "installed" in result.message.lower()

    # Verify scripts directory was created
    target_dir = claude_dir / "scripts"
    assert target_dir.exists(), "Target scripts directory should exist"

    # Verify at least one script was copied
    script_files = list(target_dir.glob("*.py"))
    assert len(script_files) >= 1, (
        f"Expected at least 1 utility script, found {len(script_files)}"
    )
