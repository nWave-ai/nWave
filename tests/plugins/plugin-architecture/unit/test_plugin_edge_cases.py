"""
Unit tests to fill coverage gaps in plugin system.

These tests target uncovered behavioral paths identified by coverage analysis.
Theater tests (str representation, trivial getters, duplicate registry tests,
mock-Path exception tests) have been removed.
"""

import logging
from pathlib import Path

import pytest

from scripts.install.plugins.agents_plugin import AgentsPlugin
from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.commands_plugin import CommandsPlugin
from scripts.install.plugins.registry import PluginRegistry
from scripts.install.plugins.templates_plugin import TemplatesPlugin
from scripts.install.plugins.utilities_plugin import UtilitiesPlugin


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.coverage_gaps")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def project_root() -> Path:
    """Return the nWave project root directory."""
    current = Path(__file__).resolve()
    return current.parents[4]


# =============================================================================
# Shared Test Helpers
# =============================================================================


class FailingPlugin(InstallationPlugin):
    """Plugin that fails installation."""

    def install(self, context: InstallContext) -> PluginResult:
        return PluginResult(
            success=False,
            plugin_name=self.name,
            message="Deliberate failure",
            errors=["Test error"],
        )

    def verify(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name, message="OK")


class SuccessPlugin(InstallationPlugin):
    """Plugin that succeeds installation."""

    def __init__(
        self, name: str, priority: int = 100, files_to_create: list | None = None
    ):
        super().__init__(name=name, priority=priority)
        self._files_to_create = files_to_create or []

    def install(self, context: InstallContext) -> PluginResult:
        installed = []
        for filename in self._files_to_create:
            file_path = context.claude_dir / self.name / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f"content of {filename}")
            installed.append(str(file_path))
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message="Success",
            installed_files=installed,
        )

    def verify(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name, message="OK")


# =============================================================================
# PluginRegistry Coverage Tests
# =============================================================================


class TestPluginRegistryVerifyAll:
    """Tests for verify_all method."""

    @pytest.fixture
    def test_context(self, tmp_path: Path, test_logger: logging.Logger):
        """Create test InstallContext."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        return InstallContext(
            claude_dir=claude_dir,
            scripts_dir=tmp_path / "scripts",
            templates_dir=tmp_path / "templates",
            logger=test_logger,
            project_root=tmp_path,
        )

    def test_verify_all_returns_results_for_all_plugins(
        self, test_context: InstallContext
    ):
        """verify_all should return verification results for all registered plugins."""
        registry = PluginRegistry()

        plugin1 = SuccessPlugin(name="plugin1", priority=10)
        plugin2 = SuccessPlugin(name="plugin2", priority=20)

        registry.register(plugin1)
        registry.register(plugin2)

        results = registry.verify_all(test_context)

        assert "plugin1" in results
        assert "plugin2" in results
        assert results["plugin1"].success
        assert results["plugin2"].success


class TestPluginRegistryRollbackFileRemoval:
    """Tests for rollback file removal logic."""

    @pytest.fixture
    def test_context(self, tmp_path: Path, test_logger: logging.Logger):
        """Create test InstallContext."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        return InstallContext(
            claude_dir=claude_dir,
            scripts_dir=tmp_path / "scripts",
            templates_dir=tmp_path / "templates",
            logger=test_logger,
            project_root=tmp_path,
        )

    def test_rollback_removes_installed_files(self, test_context: InstallContext):
        """rollback_installation should remove files tracked during installation."""
        registry = PluginRegistry()

        # Create a plugin that creates files
        plugin = SuccessPlugin(
            name="testplugin", priority=10, files_to_create=["file1.txt", "file2.txt"]
        )
        registry.register(plugin)

        # Install
        results = registry.install_all(test_context)
        assert results["testplugin"].success

        # Verify files exist
        file1 = test_context.claude_dir / "testplugin" / "file1.txt"
        file2 = test_context.claude_dir / "testplugin" / "file2.txt"
        assert file1.exists()
        assert file2.exists()

        # Rollback
        registry.rollback_installation(test_context)

        # Files should be removed
        assert not file1.exists()
        assert not file2.exists()

    def test_rollback_cleans_empty_directories(self, test_context: InstallContext):
        """rollback_installation should remove empty plugin directories."""
        registry = PluginRegistry()

        plugin = SuccessPlugin(
            name="emptydir", priority=10, files_to_create=["only.txt"]
        )
        registry.register(plugin)

        results = registry.install_all(test_context)
        assert results["emptydir"].success

        plugin_dir = test_context.claude_dir / "emptydir"
        assert plugin_dir.exists()

        # Rollback
        registry.rollback_installation(test_context)

        # Directory should be removed after all files removed
        assert not plugin_dir.exists()


class TestPluginRegistryBackupRestore:
    """Tests for backup restore functionality."""

    @pytest.fixture
    def context_with_backup(self, tmp_path: Path, test_logger: logging.Logger):
        """Create test context with backup directory."""
        from scripts.install.install_utils import BackupManager

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        backup_mgr = BackupManager(test_logger, "install")
        # Override all path attributes to use tmp_path for test isolation
        backup_mgr.claude_config_dir = claude_dir
        backup_mgr.backup_root = claude_dir / "backups"
        # Must also override backup_dir which was calculated in __init__
        backup_mgr.backup_dir = (
            backup_mgr.backup_root / f"nwave-install-{backup_mgr.timestamp}"
        )

        # Create original agents directory to backup
        agents_dir = claude_dir / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "original.md").write_text("# Original Agent")

        # Create backup
        backup_mgr.create_backup()

        return InstallContext(
            claude_dir=claude_dir,
            scripts_dir=tmp_path / "scripts",
            templates_dir=tmp_path / "templates",
            logger=test_logger,
            project_root=tmp_path,
            backup_manager=backup_mgr,
        )

    def test_rollback_restores_agents_from_backup(
        self, context_with_backup: InstallContext
    ):
        """rollback_installation should restore agents directory from backup."""
        registry = PluginRegistry()

        # Modify agents directory
        agents_dir = context_with_backup.claude_dir / "agents"
        (agents_dir / "original.md").write_text("# Modified!")

        # Create a failing plugin scenario
        plugin = FailingPlugin(name="failing", priority=10)
        registry.register(plugin)

        results = registry.install_all(context_with_backup)
        assert not results["failing"].success

        # Rollback should restore from backup
        registry.rollback_installation(context_with_backup)

        # Original content should be restored
        restored_file = agents_dir / "original.md"
        assert restored_file.exists()
        content = restored_file.read_text()
        assert "Original Agent" in content


# =============================================================================
# TemplatesPlugin Coverage Tests
# =============================================================================


class TestTemplatesPluginFallbackPath:
    """Tests for templates_dir fallback to framework_source."""

    @pytest.fixture
    def context_with_nonexistent_templates_dir(
        self, tmp_path: Path, test_logger: logging.Logger, project_root: Path
    ):
        """Create context where templates_dir doesn't exist."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Create framework_source with templates
        framework_source = tmp_path / "framework"
        templates_in_framework = framework_source / "templates"
        templates_in_framework.mkdir(parents=True, exist_ok=True)
        (templates_in_framework / "test.yaml").write_text("key: value")

        return InstallContext(
            claude_dir=claude_dir,
            scripts_dir=tmp_path / "scripts",
            templates_dir=tmp_path / "nonexistent_templates",  # Doesn't exist
            logger=test_logger,
            project_root=project_root,
            framework_source=framework_source,
        )

    def test_install_uses_framework_source_when_templates_dir_missing(
        self, context_with_nonexistent_templates_dir: InstallContext
    ):
        """install should fallback to framework_source/templates when templates_dir missing."""
        plugin = TemplatesPlugin()
        result = plugin.install(context_with_nonexistent_templates_dir)

        assert result.success
        target = context_with_nonexistent_templates_dir.claude_dir / "templates"
        assert target.exists()


class TestTemplatesPluginNoSource:
    """Tests for when no templates source exists."""

    def test_install_fails_when_no_templates_source_exists(
        self, tmp_path: Path, test_logger: logging.Logger
    ):
        """install should fail when neither templates_dir nor framework_source has templates."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        context = InstallContext(
            claude_dir=claude_dir,
            scripts_dir=tmp_path / "scripts",
            templates_dir=tmp_path / "nonexistent1",
            logger=test_logger,
            project_root=tmp_path,
            framework_source=tmp_path / "nonexistent2",
        )

        plugin = TemplatesPlugin()
        result = plugin.install(context)

        assert not result.success
        assert "does not exist" in result.message


class TestTemplatesPluginDirectoryCopy:
    """Tests for directory copy with subdirectories."""

    def test_install_copies_subdirectories_recursively(
        self, tmp_path: Path, test_logger: logging.Logger
    ):
        """install should copy subdirectories and collect .yaml/.md files."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Create source with subdirectory
        templates_source = tmp_path / "source_templates"
        subdir = templates_source / "sub"
        subdir.mkdir(parents=True)
        (subdir / "nested.yaml").write_text("nested: true")
        (subdir / "nested.md").write_text("# Nested")
        (templates_source / "root.yaml").write_text("root: true")

        context = InstallContext(
            claude_dir=claude_dir,
            scripts_dir=tmp_path / "scripts",
            templates_dir=templates_source,
            logger=test_logger,
            project_root=tmp_path,
            framework_source=tmp_path / "framework",
        )

        plugin = TemplatesPlugin()
        result = plugin.install(context)

        assert result.success
        assert len(result.installed_files) >= 2  # nested.yaml, nested.md

        target_subdir = claude_dir / "templates" / "sub"
        assert target_subdir.exists()
        assert (target_subdir / "nested.yaml").exists()
        assert (target_subdir / "nested.md").exists()


# =============================================================================
# AgentsPlugin Coverage Tests
# =============================================================================


class TestAgentsPluginSourceFallback:
    """Tests for source file fallback logic."""

    def test_install_uses_source_from_nwave_agents(
        self, tmp_path: Path, test_logger: logging.Logger, project_root: Path
    ):
        """install should use source files from nWave/agents/."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Create source directory with agents
        source_agents = tmp_path / "nWave" / "agents"
        source_agents.mkdir(parents=True, exist_ok=True)
        for i in range(10):
            (source_agents / f"nw-agent{i}.md").write_text(f"# Agent {i}")

        context = InstallContext(
            claude_dir=claude_dir,
            scripts_dir=tmp_path / "scripts",
            templates_dir=tmp_path / "templates",
            logger=test_logger,
            project_root=tmp_path,
            framework_source=tmp_path / "nWave",
        )

        plugin = AgentsPlugin()
        result = plugin.install(context)

        assert result.success
        target = claude_dir / "agents" / "nw"
        assert target.exists()


# =============================================================================
# UtilitiesPlugin Coverage Tests
# =============================================================================


class TestUtilitiesPluginScriptNotFound:
    """Tests for script not found continue."""

    def test_install_skips_missing_scripts(
        self, tmp_path: Path, test_logger: logging.Logger
    ):
        """install should skip utility scripts that don't exist in source."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Create project with only one of the expected scripts
        scripts_source = tmp_path / "scripts"
        scripts_source.mkdir(parents=True)
        (scripts_source / "validate_step_file.py").write_text(
            '"""Script."""\n__version__ = "1.0.0"'
        )
        # install_nwave_target_hooks.py is missing

        context = InstallContext(
            claude_dir=claude_dir,
            scripts_dir=tmp_path / "scripts" / "install",
            templates_dir=tmp_path / "templates",
            logger=test_logger,
            project_root=tmp_path,
            framework_source=tmp_path / "framework",
        )

        plugin = UtilitiesPlugin()
        result = plugin.install(context)

        # Should succeed even with missing scripts
        assert result.success


class TestUtilitiesPluginFreshInstall:
    """Tests for fresh install (not upgrade) path."""

    def test_install_copies_new_script_when_target_missing(
        self, tmp_path: Path, test_logger: logging.Logger
    ):
        """install should copy script when target doesn't exist (fresh install)."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Create source scripts
        scripts_source = tmp_path / "scripts"
        scripts_source.mkdir(parents=True)
        (scripts_source / "validate_step_file.py").write_text(
            '"""Script."""\n__version__ = "1.0.0"'
        )

        context = InstallContext(
            claude_dir=claude_dir,
            scripts_dir=tmp_path / "scripts" / "install",
            templates_dir=tmp_path / "templates",
            logger=test_logger,
            project_root=tmp_path,
            framework_source=tmp_path / "framework",
        )

        plugin = UtilitiesPlugin()
        result = plugin.install(context)

        assert result.success
        target = claude_dir / "scripts" / "validate_step_file.py"
        assert target.exists()


# =============================================================================
# CommandsPlugin Coverage Tests
# =============================================================================


class TestCommandsPluginFileCopy:
    """Tests for file (not directory) copy path."""

    def test_install_copies_individual_files(
        self, tmp_path: Path, test_logger: logging.Logger
    ):
        """install should copy individual files in commands source."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Create source at the path the plugin actually reads
        commands_source = tmp_path / "nWave" / "tasks" / "nw"
        commands_source.mkdir(parents=True)
        (commands_source / "standalone.md").write_text("# Standalone Command")

        context = InstallContext(
            claude_dir=claude_dir,
            scripts_dir=tmp_path / "scripts",
            templates_dir=tmp_path / "templates",
            logger=test_logger,
            project_root=tmp_path,
            framework_source=tmp_path / "framework",
        )

        plugin = CommandsPlugin()
        result = plugin.install(context)

        assert result.success
        target = claude_dir / "commands" / "nw" / "standalone.md"
        assert target.exists()
