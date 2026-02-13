"""
Plugin for installing commands from nWave/tasks/nw/ into ~/.claude/commands/nw/.

Reads command files directly from the project source (nWave/tasks/nw/),
excluding legacy/ directory content.
"""

import shutil

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)


class CommandsPlugin(InstallationPlugin):
    """Plugin for installing commands into the nWave framework."""

    def __init__(self):
        """Initialize commands plugin with name and priority."""
        super().__init__(name="commands", priority=20)

    def install(self, context: InstallContext) -> PluginResult:
        """Install commands from nWave/tasks/nw/ to ~/.claude/commands/nw/.

        Copies *.md command files from the project source directory,
        excluding legacy/ directory content.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure of installation
        """
        try:
            context.logger.info("  📦 Installing commands...")

            # dist/ layout: commands/nw/ (build_dist.py maps tasks → commands)
            # source layout: nWave/tasks/nw/
            dist_commands = context.framework_source / "commands" / "nw"
            if dist_commands.exists():
                source_commands_dir = dist_commands
            else:
                source_commands_dir = context.project_root / "nWave" / "tasks" / "nw"
            target_commands_dir = context.claude_dir / "commands" / "nw"

            if not source_commands_dir.exists():
                context.logger.info("  ⏭️ No commands directory found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No commands to install (source directory not found)",
                )

            # Clean and recreate target directory to remove stale files
            if target_commands_dir.exists():
                shutil.rmtree(target_commands_dir)
            target_commands_dir.mkdir(parents=True, exist_ok=True)

            source_command_count = len(list(source_commands_dir.glob("*.md")))
            context.logger.info(
                f"  ⏳ From source ({source_command_count} commands)..."
            )

            # Copy only *.md files from source root (excludes legacy/ and subdirectories)
            copied_count = 0
            installed_files = []
            for source_file in sorted(source_commands_dir.glob("*.md")):
                shutil.copy2(source_file, target_commands_dir / source_file.name)
                installed_files.append(str(target_commands_dir / source_file.name))
                copied_count += 1

            context.logger.info(f"  ✅ Commands installed ({copied_count} files)")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Commands installed successfully ({copied_count} files)",
                installed_files=installed_files,
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to install commands: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Commands installation failed: {e!s}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify commands were installed correctly.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating verification success or failure
        """
        try:
            context.logger.info("  🔎 Verifying commands...")

            target_commands_dir = context.claude_dir / "commands" / "nw"

            # Check target directory exists
            if not target_commands_dir.exists():
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Commands verification failed: target directory does not exist",
                    errors=["Target directory not found"],
                )

            # Check for command files
            command_files = list(target_commands_dir.glob("*.md"))
            if not command_files:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Commands verification failed: no command files found",
                    errors=["No .md files in target directory"],
                )

            context.logger.info(f"  ✅ Verified {len(command_files)} command files")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Commands verification passed ({len(command_files)} files)",
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to verify commands: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Commands verification failed: {e!s}",
                errors=[str(e)],
            )
