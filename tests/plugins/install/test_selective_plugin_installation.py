"""
Acceptance tests for selective plugin installation and uninstallation.

Step 04-02: Selective Installation and Uninstallation
- install_nwave.py --exclude des installs only 4 plugins
- DES module NOT found at ~/.claude/lib/python/des/ when excluded
- install_nwave.py --uninstall des removes DES files
- Other plugins remain installed after selective uninstall
- Uninstallation blocked when plugin has dependents
"""

from unittest.mock import Mock

import pytest

from scripts.install.plugins.base import InstallContext, PluginResult
from scripts.install.plugins.registry import PluginRegistry


class MockPlugin:
    """Mock plugin for testing selective installation."""

    def __init__(
        self, name: str, priority: int = 100, dependencies: list | None = None
    ):
        self.name = name
        self.priority = priority
        self.dependencies = dependencies or []
        self.install_called = False
        self.uninstall_called = False

    def get_dependencies(self) -> list[str]:
        return self.dependencies

    def set_dependencies(self, deps: list[str]) -> None:
        self.dependencies = deps

    def install(self, context: InstallContext) -> PluginResult:
        self.install_called = True
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=f"{self.name} installed",
        )

    def verify(self, context: InstallContext) -> PluginResult:
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=f"{self.name} verified",
        )

    def uninstall(self, context: InstallContext) -> PluginResult:
        self.uninstall_called = True
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=f"{self.name} uninstalled",
        )


@pytest.fixture
def mock_context(tmp_path):
    """Create mock installation context."""
    return InstallContext(
        claude_dir=tmp_path / "claude",
        scripts_dir=tmp_path / "scripts",
        templates_dir=tmp_path / "templates",
        logger=Mock(info=Mock(), error=Mock(), warn=Mock()),
        project_root=tmp_path,
        framework_source=tmp_path / "dist",
        dry_run=False,
    )


class TestSelectiveInstallationExcludeFlag:
    """AC1: install_nwave.py --exclude des installs only 4 plugins."""

    def test_exclude_flag_prevents_plugin_installation(self, mock_context):
        """When --exclude des is passed, DES plugin should not be installed."""
        registry = PluginRegistry()

        # Register 5 plugins (agents, commands, templates, utilities, des)
        agents = MockPlugin("agents", priority=10)
        commands = MockPlugin("commands", priority=20)
        templates = MockPlugin("templates", priority=30)
        utilities = MockPlugin("utilities", priority=40)
        des = MockPlugin("des", priority=50, dependencies=["templates", "utilities"])

        registry.register(agents)
        registry.register(commands)
        registry.register(templates)
        registry.register(utilities)
        registry.register(des)

        # Install with exclusion - this method should exist
        results = registry.install_all(mock_context, exclude=["des"])

        # DES should NOT be installed
        assert "des" not in results, "DES should be excluded from installation"
        assert agents.install_called, "agents should be installed"
        assert commands.install_called, "commands should be installed"
        assert templates.install_called, "templates should be installed"
        assert utilities.install_called, "utilities should be installed"
        assert not des.install_called, "DES should NOT be installed when excluded"

    def test_exclude_multiple_plugins(self, mock_context):
        """Multiple plugins can be excluded."""
        registry = PluginRegistry()

        agents = MockPlugin("agents", priority=10)
        commands = MockPlugin("commands", priority=20)
        templates = MockPlugin("templates", priority=30)

        registry.register(agents)
        registry.register(commands)
        registry.register(templates)

        # Exclude both agents and templates
        results = registry.install_all(mock_context, exclude=["agents", "templates"])

        assert "agents" not in results
        assert "templates" not in results
        assert "commands" in results
        assert not agents.install_called
        assert not templates.install_called
        assert commands.install_called


class TestExcludedPluginFilesNotPresent:
    """AC2: DES module NOT found at ~/.claude/lib/python/des/ when excluded."""

    def test_excluded_plugin_directories_not_created(self, mock_context):
        """When DES is excluded, its directories should not exist."""
        registry = PluginRegistry()

        des = MockPlugin("des", priority=50)
        registry.register(des)

        # Install with exclusion
        registry.install_all(mock_context, exclude=["des"])

        # DES directory should not exist
        des_dir = mock_context.claude_dir / "lib" / "python" / "des"
        assert not des_dir.exists(), "DES directory should not exist when excluded"


class TestUninstallFlag:
    """AC3: install_nwave.py --uninstall des removes DES files."""

    def test_uninstall_removes_specific_plugin(self, mock_context):
        """--uninstall des should remove only the DES plugin."""
        registry = PluginRegistry()

        des = MockPlugin("des", priority=50)
        registry.register(des)

        # Uninstall method should exist and work
        result = registry.uninstall(mock_context, plugin_name="des")

        assert result.success, "Uninstall should succeed"
        assert des.uninstall_called, "Plugin's uninstall method should be called"


class TestOtherPluginsRemainAfterUninstall:
    """AC4: Other plugins remain installed after selective uninstall."""

    def test_uninstall_preserves_other_plugins(self, mock_context, tmp_path):
        """Uninstalling DES should not affect other plugins."""
        registry = PluginRegistry()

        # Create mock installed files for agents
        agents_dir = mock_context.claude_dir / "agents" / "nw"
        agents_dir.mkdir(parents=True)
        (agents_dir / "test-agent.md").write_text("# Test Agent")

        des = MockPlugin("des", priority=50)
        registry.register(des)

        # Uninstall DES
        registry.uninstall(mock_context, plugin_name="des")

        # Agents should still exist
        assert agents_dir.exists(), "Agents directory should still exist"
        assert (agents_dir / "test-agent.md").exists(), "Agent files should remain"


class TestUninstallBlockedWithDependents:
    """AC5: Uninstallation blocked when plugin has dependents."""

    def test_uninstall_blocked_when_dependents_exist(self, mock_context):
        """Cannot uninstall a plugin that other plugins depend on."""
        registry = PluginRegistry()

        templates = MockPlugin("templates", priority=30)
        des = MockPlugin("des", priority=50, dependencies=["templates"])

        registry.register(templates)
        registry.register(des)

        # Try to uninstall templates (which des depends on)
        result = registry.uninstall(mock_context, plugin_name="templates")

        assert not result.success, "Uninstall should fail when dependents exist"
        assert (
            "des" in result.message.lower() or "dependent" in result.message.lower()
        ), "Error message should mention the dependent plugin"

    def test_uninstall_succeeds_when_no_dependents(self, mock_context):
        """Uninstall succeeds when no other plugins depend on it."""
        registry = PluginRegistry()

        templates = MockPlugin("templates", priority=30)
        des = MockPlugin("des", priority=50, dependencies=["templates"])

        registry.register(templates)
        registry.register(des)

        # DES has no dependents, so it can be uninstalled
        result = registry.uninstall(mock_context, plugin_name="des")

        assert result.success, "Uninstall should succeed when no dependents exist"

    def test_get_dependents_returns_plugins_depending_on_target(self, mock_context):
        """Registry should identify which plugins depend on a given plugin."""
        registry = PluginRegistry()

        templates = MockPlugin("templates", priority=30)
        utilities = MockPlugin("utilities", priority=40)
        des = MockPlugin("des", priority=50, dependencies=["templates", "utilities"])

        registry.register(templates)
        registry.register(utilities)
        registry.register(des)

        # Get dependents of templates
        dependents = registry.get_dependents("templates")

        assert "des" in dependents, "DES should be listed as dependent of templates"


class TestUninstallNonExistentPlugin:
    """Edge case: Uninstalling a plugin that doesn't exist."""

    def test_uninstall_nonexistent_plugin_returns_error(self, mock_context):
        """Attempting to uninstall unregistered plugin should return error."""
        registry = PluginRegistry()

        result = registry.uninstall(mock_context, plugin_name="nonexistent")

        assert not result.success, "Uninstall should fail for nonexistent plugin"
        assert (
            "not found" in result.message.lower()
            or "not registered" in result.message.lower()
        )


class TestExcludeNonExistentPlugin:
    """Edge case: Excluding a plugin that doesn't exist."""

    def test_exclude_nonexistent_plugin_is_ignored(self, mock_context):
        """Excluding a plugin that doesn't exist should not cause errors."""
        registry = PluginRegistry()

        agents = MockPlugin("agents", priority=10)
        registry.register(agents)

        # Exclude a plugin that doesn't exist - should just be ignored
        results = registry.install_all(mock_context, exclude=["nonexistent"])

        # Should still install agents without error
        assert "agents" in results
        assert agents.install_called
