"""
Unit tests for TemplatesPlugin.

Tests the TemplatesPlugin install() and verify() methods through the
InstallationPlugin interface (driving port).

Domain: Plugin Infrastructure - Template Installation
"""

import logging
from pathlib import Path

import pytest

from scripts.install.plugins.base import InstallContext, PluginResult
from scripts.install.plugins.templates_plugin import TemplatesPlugin


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.templates_plugin")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def project_root() -> Path:
    """Return the nWave project root directory."""
    current = Path(__file__).resolve()
    return current.parents[4]  # 4 levels up from test file


@pytest.fixture
def template_source_dir(project_root: Path) -> Path:
    """Return the template source directory: nWave/templates/."""
    return project_root / "nWave" / "templates"


@pytest.fixture
def install_context(tmp_path: Path, project_root: Path, test_logger: logging.Logger):
    """Create InstallContext for testing with real paths."""
    test_claude_dir = tmp_path / ".claude"
    test_claude_dir.mkdir(parents=True, exist_ok=True)

    return InstallContext(
        claude_dir=test_claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )


# -----------------------------------------------------------------------------
# Test Class: TemplatesPluginShould
# -----------------------------------------------------------------------------


class TemplatesPluginShould:
    """Unit tests for TemplatesPlugin following naming convention."""

    def test_copy_template_files_to_target_directory_when_install_called(
        self, install_context: InstallContext, template_source_dir: Path
    ):
        """
        TemplatesPlugin.install() should copy template .yaml files to the target directory.

        Given: A valid InstallContext with project root containing template source files
        When: install() is called
        Then: Template files are copied to {claude_dir}/templates/
        """
        # Arrange
        plugin = TemplatesPlugin()
        target_templates_dir = install_context.claude_dir / "templates"

        # Verify source files exist
        assert template_source_dir.exists(), (
            f"Template source not found: {template_source_dir}"
        )
        source_files = list(template_source_dir.glob("*.yaml"))
        assert len(source_files) >= 1, "No template .yaml files in source directory"

        # Act
        result = plugin.install(install_context)

        # Assert
        assert result.success, f"Installation failed: {result.message}"
        assert target_templates_dir.exists(), (
            f"Target directory not created: {target_templates_dir}"
        )

        target_files = list(target_templates_dir.glob("*.yaml"))
        assert len(target_files) >= 1, (
            f"Expected at least 1 template file in target, found {len(target_files)}"
        )

    def test_return_success_result_with_installed_files_list_when_install_succeeds(
        self, install_context: InstallContext
    ):
        """
        TemplatesPlugin.install() should return PluginResult with installed_files populated.

        Given: A valid InstallContext
        When: install() is called successfully
        Then: PluginResult.success is True and installed_files contains file paths
        """
        # Arrange
        plugin = TemplatesPlugin()

        # Act
        result = plugin.install(install_context)

        # Assert
        assert isinstance(result, PluginResult)
        assert result.success is True
        assert result.plugin_name == "templates"
        assert (
            "Templates installed" in result.message
            or "success" in result.message.lower()
        )
        # installed_files should contain the copied files
        assert result.installed_files is not None
        assert len(result.installed_files) >= 1, (
            "Expected installed_files to contain at least one file path"
        )

    def test_return_success_with_verification_message_when_verify_called_after_install(
        self, install_context: InstallContext
    ):
        """
        TemplatesPlugin.verify() should confirm installation was successful.

        Given: TemplatesPlugin.install() was called successfully
        When: verify() is called
        Then: PluginResult.success is True and message contains verification info
        """
        # Arrange
        plugin = TemplatesPlugin()

        # First install
        install_result = plugin.install(install_context)
        assert install_result.success, f"Install failed: {install_result.message}"

        # Act
        verify_result = plugin.verify(install_context)

        # Assert
        assert verify_result.success is True
        assert "Templates verification passed" in verify_result.message

    def test_verify_checks_target_directory_contains_template_files(
        self, install_context: InstallContext
    ):
        """
        TemplatesPlugin.verify() should check that template files exist in target directory.

        Given: Installation completed
        When: verify() is called
        Then: Verification checks for presence of template files
        """
        # Arrange
        plugin = TemplatesPlugin()

        # Install first
        plugin.install(install_context)

        # Act
        verify_result = plugin.verify(install_context)

        # Assert
        assert verify_result.success is True
        # The verification should have actually checked for files
        target_dir = install_context.claude_dir / "templates"
        if target_dir.exists():
            template_files = list(target_dir.glob("*.yaml"))
            # If files exist, verification should pass
            assert len(template_files) >= 1 or not verify_result.success


# -----------------------------------------------------------------------------
# Standalone Test Functions (for pytest discovery)
# -----------------------------------------------------------------------------


def test_templates_plugin_copies_files_to_target(
    install_context: InstallContext, template_source_dir: Path
):
    """TemplatesPlugin.install() should copy template files to target directory."""
    plugin = TemplatesPlugin()
    target_templates_dir = install_context.claude_dir / "templates"

    # Verify source exists
    assert template_source_dir.exists(), (
        f"Template source not found: {template_source_dir}"
    )

    # Act
    result = plugin.install(install_context)

    # Assert - this should fail with current stub implementation
    assert result.success, f"Installation failed: {result.message}"
    assert target_templates_dir.exists(), (
        f"Target directory not created: {target_templates_dir}"
    )

    target_files = list(target_templates_dir.glob("*.yaml"))
    assert len(target_files) >= 1, (
        f"Expected at least 1 template file in target, found {len(target_files)}"
    )


def test_templates_plugin_verify_confirms_files_exist(install_context: InstallContext):
    """TemplatesPlugin.verify() should confirm template files were installed."""
    plugin = TemplatesPlugin()

    # Install first
    install_result = plugin.install(install_context)
    assert install_result.success

    # Verify
    verify_result = plugin.verify(install_context)

    # Check verification result
    assert verify_result.success is True
    assert "Templates verification passed" in verify_result.message


def test_templates_plugin_verify_fails_when_target_directory_missing(
    tmp_path: Path, project_root: Path, test_logger: logging.Logger
):
    """TemplatesPlugin.verify() should fail when target directory does not exist."""
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

    plugin = TemplatesPlugin()

    # Act - verify without install
    verify_result = plugin.verify(context)

    # Assert - should fail because no installation occurred
    assert verify_result.success is False
    assert "target directory does not exist" in verify_result.message


def test_templates_plugin_verify_fails_when_no_template_files(
    tmp_path: Path, project_root: Path, test_logger: logging.Logger
):
    """TemplatesPlugin.verify() should fail when directory exists but has no .yaml files."""
    # Arrange - create context with templates directory but no files
    claude_dir = tmp_path / ".claude-nofiles"
    templates_dir = claude_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )

    plugin = TemplatesPlugin()

    # Act - verify with empty directory
    verify_result = plugin.verify(context)

    # Assert - should fail because no template files
    assert verify_result.success is False
    assert "no template files found" in verify_result.message


def test_templates_plugin_install_success_with_real_source(
    tmp_path: Path, project_root: Path, test_logger: logging.Logger
):
    """TemplatesPlugin.install() should copy files from templates_dir to target."""
    # Arrange - Set up with real source templates
    source_templates = tmp_path / "source_templates"
    source_templates.mkdir(parents=True)
    (source_templates / "develop.yaml").write_text("# Develop Template")
    (source_templates / "design.yaml").write_text("# Design Template")

    claude_dir = tmp_path / "target_claude"
    claude_dir.mkdir(parents=True)

    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=source_templates,
        logger=test_logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )

    plugin = TemplatesPlugin()

    # Act
    result = plugin.install(context)

    # Assert
    assert result.success is True
    assert result.plugin_name == "templates"
    assert "installed" in result.message.lower()

    # Verify files were actually copied
    target_dir = claude_dir / "templates"
    assert target_dir.exists(), "Target templates directory should exist"
    assert (target_dir / "develop.yaml").exists(), "develop.yaml should be copied"
    assert (target_dir / "design.yaml").exists(), "design.yaml should be copied"
