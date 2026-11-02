"""
Plugin for installing nWave agents into OpenCode's agent format.

OpenCode expects agents at: ~/.config/opencode/agents/{agent-name}.md
Each agent has YAML frontmatter with mode, steps, tools (as mapping), and
description -- but no name, model, or skills fields.

A manifest file (.nwave-agents-manifest.json) tracks which agents nWave
installed, so uninstall() can remove only nWave agents without touching
user-created ones.
"""

import json
from pathlib import Path

from nwave_ai.platform.capability import provider_tool_name, split_declared_tools
from nwave_ai.platform.role_render import render_installed_role
from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.opencode_common import (
    ManifestPluginConfig,
    opencode_config_dir,
    parse_frontmatter,
    remove_manifest_owned_assets,
    render_frontmatter,
    uninstall_with_manifest,
    verify_with_manifest,
)
from scripts.shared.agent_catalog import is_public_agent, load_public_agents
from scripts.shared.skill_path_rewrite import rewrite_host_paths


_MANIFEST_FILENAME = ".nwave-agents-manifest.json"

_FIELDS_TO_REMOVE = {"name", "model", "skills"}


def _opencode_agents_dir() -> Path:
    """Return the OpenCode agents target directory.

    Returns:
        Path to ~/.config/opencode/agents/
    """
    return opencode_config_dir() / "agents"


def _find_agents_source(context: InstallContext) -> Path | None:
    """Locate the agents source directory from dist or project layout.

    Args:
        context: InstallContext with framework_source and project_root

    Returns:
        Path to the agents source directory, or None if not found
    """
    dist_agents = context.framework_source / "agents"
    if dist_agents.exists():
        return dist_agents

    project_agents = context.project_root / "nWave" / "agents"
    if project_agents.exists():
        return project_agents

    return None


def _parse_tools(tools_value: str | list) -> dict[str, str]:
    """Normalize tools from CSV string or YAML array to OpenCode permission mapping.

    Handles both formats:
        CSV:   "Read, Write, Edit, Bash"
        Array: ["Read", "Glob", "Grep"]

    OpenCode markdown agents require permission values as strings ("allow",
    "deny", "ask"), not booleans. The legacy boolean format is ignored in
    markdown frontmatter.

    A declared entry may be a permission SPECIFIER carrying its own scope
    (``Bash(<tool>:*)``). OpenCode's mapping has no place to put a
    scope, so a scoped grant becomes "ask" rather than "allow": the scope is
    part of the grant, and projecting it as "allow" would hand the role the
    whole tool it was deliberately not given. "ask" is the platform's own
    third state, so the loss of precision surfaces at use time instead of
    disappearing.

    Args:
        tools_value: Tools specification as CSV string or list

    Returns:
        Dict mapping lowercase tool names to "allow" or "ask"
    """
    if isinstance(tools_value, list):
        entries = [str(tool).strip() for tool in tools_value if str(tool).strip()]
    else:
        entries = list(split_declared_tools(str(tools_value)))

    permissions: dict[str, str] = {}
    for entry in entries:
        name = provider_tool_name(entry).lower()
        # Claude-only native spelling: OpenCode has no sendmessage permission,
        # and its absence is not evidence that a native peer primitive is absent.
        if not name or name == "sendmessage":
            continue
        scoped = entry != provider_tool_name(entry)
        # An unscoped grant on the same tool wins: it is the wider declaration.
        if scoped and permissions.get(name) == "allow":
            continue
        permissions[name] = "ask" if scoped else "allow"
    return permissions


def _transform_frontmatter(frontmatter: dict) -> dict:
    """Apply all transformation rules to convert Claude Code frontmatter to OpenCode.

    Transformations:
        1. Remove name, model, skills fields
        2. Rename maxTurns to steps
        3. Add mode: subagent
        4. Transform tools from CSV/array to mapping

    Args:
        frontmatter: Parsed YAML frontmatter dict from Claude Code agent

    Returns:
        New dict with OpenCode-compatible frontmatter
    """
    result = {
        key: value
        for key, value in frontmatter.items()
        if key not in _FIELDS_TO_REMOVE and key != "maxTurns"
    }

    if "maxTurns" in frontmatter:
        result["steps"] = frontmatter["maxTurns"]

    result["mode"] = "subagent"

    if "tools" in result:
        result["permission"] = _parse_tools(result.pop("tools"))

    return result


def _transform_agent(content: str) -> str:
    """Full transformation pipeline: parse, transform, render with body.

    Pipeline:
      1. Parse YAML frontmatter + Markdown body
      2. Transform frontmatter (rename fields, add mode, convert tools)
      3. Rewrite host paths
      4. Render frontmatter + body

    Args:
        content: Full source agent file content (Claude Code format), with
            its frontmatter skills already preloaded by the role renderer

    Returns:
        Transformed agent file content (OpenCode format)
    """
    frontmatter, body = parse_frontmatter(content)
    transformed = _transform_frontmatter(frontmatter)
    rendered = render_frontmatter(transformed)
    body = rewrite_host_paths(body, "opencode")
    return rendered + body


def _write_manifest(
    target_dir: Path,
    installed_agent_names: list[str],
) -> None:
    """Write the manifest file tracking nWave-installed agents.

    Args:
        target_dir: OpenCode agents directory
        installed_agent_names: List of installed agent filenames (without .md)
    """
    manifest = {
        "installed_agents": sorted(installed_agent_names),
        "version": "1.0",
    }
    manifest_path = target_dir / _MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


# _read_manifest moved to opencode_common.read_manifest (parameterized).


class OpenCodeAgentsPlugin(InstallationPlugin):
    """Plugin for installing nWave agents into OpenCode format."""

    def __init__(self):
        """Initialize OpenCode agents plugin with name and priority."""
        super().__init__(name="opencode-agents", priority=37)

    def install(self, context: InstallContext) -> PluginResult:
        """Install agents from nWave/agents/ as OpenCode agent files.

        Transforms each source agent file by:
        - Removing name, model, skills fields
        - Renaming maxTurns to steps
        - Adding mode: subagent
        - Converting tools to permission mapping with "allow" string values

        A manifest tracks installed agents for safe uninstallation.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            context.logger.info("  \U0001f4e6 Installing OpenCode agents...")

            agents_source = _find_agents_source(context)
            if agents_source is None:
                context.logger.info(
                    "  \u23ed\ufe0f No agents directory found, skipping"
                )
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No agents to install (source directory not found)",
                )

            target_dir = _opencode_agents_dir()
            target_dir.mkdir(parents=True, exist_ok=True)

            # Clean-then-write: the target holds ONLY what this run writes.
            # Ownership comes from the previous manifest, never the prefix.
            stale = remove_manifest_owned_assets(target_dir, _MANIFEST_FILENAME, ".md")
            if stale:
                context.logger.info(
                    f"  Removed {len(stale)} previously installed OpenCode agents"
                )

            public_agents = (
                set()
                if context.dev_mode
                else load_public_agents(context.project_root / "nWave")
            )

            agent_files = sorted(agents_source.glob("nw-*.md"))
            if not agent_files:
                context.logger.info("  \u23ed\ufe0f No agent files found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No agent files found in source directory",
                )

            installed_names = []
            installed_files = []

            for source_file in agent_files:
                if not is_public_agent(source_file.name, public_agents):
                    continue
                agent_name = source_file.stem
                # OpenCode has no skills preload: the shared renderer inlines
                # each frontmatter skill once, as for Claude and Codex.
                content = render_installed_role(source_file, "~/.claude/skills")

                transformed = _transform_agent(content)

                target_file = target_dir / f"{agent_name}.md"
                target_file.write_text(transformed, encoding="utf-8")

                installed_names.append(agent_name)
                installed_files.append(target_file)

            _write_manifest(target_dir, installed_names)

            context.logger.info(
                f"  \u2705 OpenCode agents installed ({len(installed_names)} agents)"
            )

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=(
                    f"OpenCode agents installed successfully "
                    f"({len(installed_names)} agents)"
                ),
                installed_files=installed_files,
            )
        except Exception as e:
            context.logger.error(f"  \u274c Failed to install OpenCode agents: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OpenCode agents installation failed: {e!s}",
                errors=[str(e)],
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall only nWave-installed OpenCode agents using manifest."""
        return uninstall_with_manifest(
            context=context,
            config=ManifestPluginConfig(
                plugin_name=self.name,
                target_dir=_opencode_agents_dir(),
                manifest_filename=_MANIFEST_FILENAME,
                noun="agents",
                installed_key="installed_agents",
            ),
        )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify OpenCode agents were installed correctly."""
        return verify_with_manifest(
            context=context,
            config=ManifestPluginConfig(
                plugin_name=self.name,
                target_dir=_opencode_agents_dir(),
                manifest_filename=_MANIFEST_FILENAME,
                noun="agents",
                installed_key="installed_agents",
            ),
            source_finder=_find_agents_source,
        )
