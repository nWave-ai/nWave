"""
Plugin for installing agents from nWave/agents/ into ~/.claude/agents/nw/.

Reads agent files directly from the project source (nWave/agents/),
excluding legacy/ directory content and README.md.
"""

import shutil

from nwave_ai.platform.role_render import render_installed_role
from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.shared.agent_catalog import is_public_agent, load_public_agents
from scripts.shared.platform_contracts import (
    UnbalancedToolSpecifier,
    project_claude_role_text,
)
from scripts.shared.settings import enable_todo_tools_env, todo_tools_receipt_path


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

            public_agents = (
                set()
                if context.dev_mode
                else load_public_agents(context.project_root / "nWave")
            )

            all_agents = list(source_agent_dir.glob("nw-*.md"))
            source_agent_count = sum(
                1 for f in all_agents if is_public_agent(f.name, public_agents)
            )
            context.logger.info(f"  ⏳ From source ({source_agent_count} agents)...")

            # Render everything before touching the target: a failure keeps
            # the previous install intact.
            rendered = []
            for source_file in sorted(all_agents):
                if not is_public_agent(source_file.name, public_agents):
                    continue
                try:
                    text = render_installed_role(
                        source_file, str(context.claude_dir / "skills")
                    )
                    text = project_claude_role_text(text)
                    if isinstance(text, UnbalancedToolSpecifier):
                        raise ValueError(
                            f"UnbalancedToolSpecifier: {text.raw}. "
                            "Balance the parentheses in the role's tools line."
                        )
                except (OSError, ValueError) as error:
                    message = (
                        f"Cannot render role {source_file.name} from {source_file}: "
                        f"{error}. Restore the SKILL.md or fix the role's skills declaration."
                    )
                    context.logger.error(f"  ❌ {message}")
                    return PluginResult(
                        success=False,
                        plugin_name=self.name,
                        message=message,
                        errors=[message],
                    )
                rendered.append((source_file.name, text))

            if target_agent_dir.exists():
                shutil.rmtree(target_agent_dir)
            target_agent_dir.mkdir(parents=True, exist_ok=True)

            copied_count = 0
            installed_files = []
            for name, text in rendered:
                target_file = target_agent_dir / name
                target_file.write_text(text, encoding="utf-8")
                installed_files.append(str(target_file))
                copied_count += 1

            enable_todo_tools_env(
                context.claude_dir / "settings.json",
                todo_tools_receipt_path(context.claude_dir),
            )

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
