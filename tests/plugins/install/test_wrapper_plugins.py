"""
Tests for wrapper plugins that encapsulate existing installer methods.

These tests validate that wrapper plugins correctly install files,
verify installations, and maintain execution order.
"""

from unittest.mock import Mock

from scripts.install.plugins import (
    InstallContext,
)


class TestAgentsPlugin:
    """Tests for agents wrapper plugin."""

    def test_agents_plugin_install_success(self, tmp_path):
        """Verify successful agents plugin installation."""
        from scripts.install.plugins.agents_plugin import AgentsPlugin

        plugin = AgentsPlugin()

        # Set up source directory with agent files
        source_agents = tmp_path / "nWave" / "agents"
        source_agents.mkdir(parents=True)
        (source_agents / "researcher.md").write_text("# Researcher Agent")
        (source_agents / "software-crafter.md").write_text("# Software Crafter Agent")

        # Set up target directory
        claude_dir = tmp_path / "claude_config"
        claude_dir.mkdir(parents=True)

        context = Mock(spec=InstallContext)
        context.dry_run = False
        context.project_root = tmp_path
        context.framework_source = tmp_path / "framework_source"
        context.claude_dir = claude_dir
        context.logger = Mock()

        result = plugin.install(context)

        assert result.success is True
        assert result.plugin_name == "agents"
        assert "installed" in result.message.lower()


class TestCommandsPlugin:
    """Tests for commands wrapper plugin."""

    def test_commands_plugin_install_success(self, tmp_path):
        """Verify successful commands plugin installation copies files to target."""
        from scripts.install.plugins.commands_plugin import CommandsPlugin

        plugin = CommandsPlugin()

        # Set up source directory with command files (matches plugin path)
        source_commands = tmp_path / "nWave" / "tasks" / "nw"
        source_commands.mkdir(parents=True)
        (source_commands / "devop.md").write_text("# Devop Command")
        (source_commands / "design.md").write_text("# Design Command")

        # Set up target directory
        claude_dir = tmp_path / "claude_config"
        claude_dir.mkdir(parents=True)

        context = Mock(spec=InstallContext)
        context.dry_run = False
        context.project_root = tmp_path
        context.framework_source = tmp_path / "framework_source"
        context.claude_dir = claude_dir
        context.logger = Mock()

        result = plugin.install(context)

        # Verify result
        assert result.success is True
        assert result.plugin_name == "commands"
        assert "installed" in result.message.lower()

        # Verify files were actually copied to target
        target_commands_dir = claude_dir / "commands" / "nw"
        assert target_commands_dir.exists(), "Target commands/nw directory should exist"
        assert (target_commands_dir / "devop.md").exists(), "devop.md should be copied"
        assert (target_commands_dir / "design.md").exists(), (
            "design.md should be copied"
        )

    def test_commands_plugin_verify_success_when_files_exist(self, tmp_path):
        """Verify CommandsPlugin.verify() returns success when command files exist."""
        from scripts.install.plugins.commands_plugin import CommandsPlugin

        plugin = CommandsPlugin()

        # Set up target directory with command files
        target_commands = tmp_path / "commands" / "nw"
        target_commands.mkdir(parents=True)
        (target_commands / "devop.md").write_text("# Devop Command")
        (target_commands / "design.md").write_text("# Design Command")

        context = Mock(spec=InstallContext)
        context.claude_dir = tmp_path
        context.logger = Mock()

        result = plugin.verify(context)

        assert result.success is True
        assert result.plugin_name == "commands"
        assert "2" in result.message or "passed" in result.message.lower()

    def test_commands_plugin_verify_failure_when_no_files(self, tmp_path):
        """Verify CommandsPlugin.verify() returns failure when no command files exist."""
        from scripts.install.plugins.commands_plugin import CommandsPlugin

        plugin = CommandsPlugin()

        # Set up empty target directory
        target_commands = tmp_path / "commands" / "nw"
        target_commands.mkdir(parents=True)

        context = Mock(spec=InstallContext)
        context.claude_dir = tmp_path
        context.logger = Mock()

        result = plugin.verify(context)

        assert result.success is False
        assert result.plugin_name == "commands"
        assert result.errors is not None and len(result.errors) > 0

    def test_commands_plugin_verify_failure_when_directory_missing(self, tmp_path):
        """Verify CommandsPlugin.verify() returns failure when target directory missing."""
        from scripts.install.plugins.commands_plugin import CommandsPlugin

        plugin = CommandsPlugin()

        # Do not create any directory
        context = Mock(spec=InstallContext)
        context.claude_dir = tmp_path
        context.logger = Mock()

        result = plugin.verify(context)

        assert result.success is False
        assert result.plugin_name == "commands"
        assert result.errors is not None and len(result.errors) > 0


class TestTemplatesPlugin:
    """Tests for templates wrapper plugin."""

    def test_templates_plugin_install_success(self, tmp_path):
        """Verify successful templates plugin installation copies files to target."""
        from scripts.install.plugins.templates_plugin import TemplatesPlugin

        plugin = TemplatesPlugin()

        # Set up source directory with template files
        source_templates = tmp_path / "source_templates"
        source_templates.mkdir(parents=True)
        (source_templates / "develop.yaml").write_text("# Develop Template")
        (source_templates / "design.yaml").write_text("# Design Template")

        # Set up target directory
        claude_dir = tmp_path / "claude_config"
        claude_dir.mkdir(parents=True)

        context = Mock(spec=InstallContext)
        context.dry_run = False
        context.project_root = tmp_path
        context.templates_dir = source_templates
        context.framework_source = tmp_path / "framework_source"
        context.claude_dir = claude_dir
        context.logger = Mock()

        result = plugin.install(context)

        # Verify result
        assert result.success is True
        assert result.plugin_name == "templates"
        assert "installed" in result.message.lower()

        # Verify files were actually copied to target
        target_templates_dir = claude_dir / "templates"
        assert target_templates_dir.exists(), "Target templates directory should exist"
        assert (target_templates_dir / "develop.yaml").exists(), (
            "develop.yaml should be copied"
        )
        assert (target_templates_dir / "design.yaml").exists(), (
            "design.yaml should be copied"
        )

    def test_templates_plugin_verify_success_when_files_exist(self, tmp_path):
        """Verify TemplatesPlugin.verify() returns success when template files exist."""
        from scripts.install.plugins.templates_plugin import TemplatesPlugin

        plugin = TemplatesPlugin()

        # Set up target directory with template files
        target_templates = tmp_path / "templates"
        target_templates.mkdir(parents=True)
        (target_templates / "develop.yaml").write_text("# Develop Template")
        (target_templates / "design.yaml").write_text("# Design Template")

        context = Mock(spec=InstallContext)
        context.claude_dir = tmp_path
        context.logger = Mock()

        result = plugin.verify(context)

        assert result.success is True
        assert result.plugin_name == "templates"
        assert "2" in result.message or "passed" in result.message.lower()

    def test_templates_plugin_verify_failure_when_no_files(self, tmp_path):
        """Verify TemplatesPlugin.verify() returns failure when no template files exist."""
        from scripts.install.plugins.templates_plugin import TemplatesPlugin

        plugin = TemplatesPlugin()

        # Set up empty target directory
        target_templates = tmp_path / "templates"
        target_templates.mkdir(parents=True)

        context = Mock(spec=InstallContext)
        context.claude_dir = tmp_path
        context.logger = Mock()

        result = plugin.verify(context)

        assert result.success is False
        assert result.plugin_name == "templates"
        assert result.errors is not None and len(result.errors) > 0

    def test_templates_plugin_verify_failure_when_directory_missing(self, tmp_path):
        """Verify TemplatesPlugin.verify() returns failure when target directory missing."""
        from scripts.install.plugins.templates_plugin import TemplatesPlugin

        plugin = TemplatesPlugin()

        # Do not create any directory
        context = Mock(spec=InstallContext)
        context.claude_dir = tmp_path
        context.logger = Mock()

        result = plugin.verify(context)

        assert result.success is False
        assert result.plugin_name == "templates"
        assert result.errors is not None and len(result.errors) > 0


class TestUtilitiesPlugin:
    """Tests for utilities wrapper plugin."""

    def test_utilities_plugin_install_success(self, tmp_path):
        """Verify successful utilities plugin installation copies scripts to target."""
        from scripts.install.plugins.utilities_plugin import UtilitiesPlugin

        plugin = UtilitiesPlugin()

        # Set up source directory with utility scripts
        source_scripts = tmp_path / "scripts"
        source_scripts.mkdir(parents=True)
        (source_scripts / "install_nwave_target_hooks.py").write_text(
            '"""Hook installation script."""\n__version__ = "1.0.0"\n'
        )
        (source_scripts / "validate_step_file.py").write_text(
            '"""Step file validation script."""\n__version__ = "1.0.0"\n'
        )

        # Set up target directory
        claude_dir = tmp_path / "claude_config"
        claude_dir.mkdir(parents=True)

        context = Mock(spec=InstallContext)
        context.dry_run = False
        context.project_root = tmp_path
        context.claude_dir = claude_dir
        context.framework_source = (
            tmp_path  # dist layout: scripts/ under framework_source
        )
        context.logger = Mock()

        result = plugin.install(context)

        # Verify result
        assert result.success is True
        assert result.plugin_name == "utilities"
        assert "installed" in result.message.lower()

        # Verify scripts were actually copied to target
        target_scripts_dir = claude_dir / "scripts"
        assert target_scripts_dir.exists(), "Target scripts directory should exist"
        assert (target_scripts_dir / "install_nwave_target_hooks.py").exists(), (
            "install_nwave_target_hooks.py should be copied"
        )
        assert (target_scripts_dir / "validate_step_file.py").exists(), (
            "validate_step_file.py should be copied"
        )


class TestPluginIntegration:
    """Integration tests for all wrapper plugins."""

    def test_plugins_execute_in_priority_order(self):
        """Verify plugins execute in correct priority order when no dependencies."""
        from scripts.install.plugins.agents_plugin import AgentsPlugin
        from scripts.install.plugins.commands_plugin import CommandsPlugin
        from scripts.install.plugins.registry import PluginRegistry
        from scripts.install.plugins.templates_plugin import TemplatesPlugin
        from scripts.install.plugins.utilities_plugin import UtilitiesPlugin

        registry = PluginRegistry()
        registry.register(UtilitiesPlugin())  # priority 40
        registry.register(TemplatesPlugin())  # priority 30
        registry.register(CommandsPlugin())  # priority 20
        registry.register(AgentsPlugin())  # priority 10

        execution_order = registry.get_execution_order()

        # Should be sorted by priority (lower = earlier)
        assert execution_order == ["agents", "commands", "templates", "utilities"]
