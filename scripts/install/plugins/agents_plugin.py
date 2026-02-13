"""
Plugin for installing agents from nWave/agents/ into ~/.claude/agents/nw/.

Reads agent files directly from the project source (nWave/agents/),
excluding legacy/ directory content and README.md.
"""

import shutil

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)


class AgentsPlugin(InstallationPlugin):
    """Plugin for installing agents into the nWave framework."""

    def __init__(self):
        """Initialize agents plugin with name and priority."""
        super().__init__(name="agents", priority=10)

    def install(self, context: InstallContext) -> PluginResult:
        """Install agents from nWave/agents/ to ~/.claude/agents/nw/.

        Copies nw-*.md agent files from the project source directory,
        excluding legacy/ directory content and README.md.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure of installation
        """
        try:
            context.logger.info("  📦 Installing agents...")

            # dist/ layout: agents/nw/ (build_dist.py adds nw/ namespace)
            # source layout: nWave/agents/ (nw-*.md files at root)
            dist_agents = context.framework_source / "agents" / "nw"
            if dist_agents.exists():
                source_agent_dir = dist_agents
            else:
                source_agent_dir = context.project_root / "nWave" / "agents"
            target_agent_dir = context.claude_dir / "agents" / "nw"

            if not source_agent_dir.exists():
                context.logger.info("  ⏭️ No agents directory found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No agents to install (source directory not found)",
                )

            # Clean and recreate target directory to remove stale files
            if target_agent_dir.exists():
                shutil.rmtree(target_agent_dir)
            target_agent_dir.mkdir(parents=True, exist_ok=True)

            source_agent_count = len(list(source_agent_dir.glob("nw-*.md")))
            context.logger.info(f"  ⏳ From source ({source_agent_count} agents)...")

            # Copy only nw-*.md files from source root (excludes legacy/ and README.md)
            copied_count = 0
            installed_files = []
            for source_file in sorted(source_agent_dir.glob("nw-*.md")):
                shutil.copy2(source_file, target_agent_dir / source_file.name)
                installed_files.append(str(target_agent_dir / source_file.name))
                copied_count += 1

            context.logger.info(f"  ✅ Agents installed ({copied_count} files)")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Agents installed successfully ({copied_count} files)",
                installed_files=installed_files,
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to install agents: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Agents installation failed: {e!s}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify agents were installed correctly.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating verification success or failure
        """
        try:
            context.logger.info("  🔎 Verifying agents...")

            target_agent_dir = context.claude_dir / "agents" / "nw"

            # Check target directory exists
            if not target_agent_dir.exists():
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Agents verification failed: target directory does not exist",
                    errors=["Target directory not found"],
                )

            # Check for agent files
            agent_files = list(target_agent_dir.glob("*.md"))
            if not agent_files:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Agents verification failed: no agent files found",
                    errors=["No .md files in target directory"],
                )

            context.logger.info(f"  ✅ Verified {len(agent_files)} agent files")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Agents verification passed ({len(agent_files)} files)",
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to verify agents: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Agents verification failed: {e!s}",
                errors=[str(e)],
            )
