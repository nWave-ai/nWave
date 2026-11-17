"""Plugin for installing nWave's public role agents for GitHub Copilot CLI (card t-0467).

Copilot reads a custom agent from ``<COPILOT_HOME or ~/.copilot>/agents/<name>.agent.md``. Each public role is written
there as the Copilot agent text of copilot_common.convert_agent: name and description in the frontmatter, the body with
its Claude folders rewritten, and no model field (no Copilot model id is known to be valid).

A manifest (``.nwave-agents-manifest.json``) lists the agents this install wrote. A file at a target name that the
manifest does not list is a user's file: the install refuses before writing anything, and never overwrites it.

The folder writer is public as install_public_agents, so the project-level install (copilot_project) writes the same
agents into a project's .github/agents folder through the same code (card t-0515).

The install reports what it did not check. It does not start the CLI, so whether Copilot lists or invokes the roles is
proved by a real session, not by this plugin.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from nwave_ai.platform.role_render import render_installed_role
from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.copilot_common import (
    NOT_CHECKED,
    convert_agent,
    copilot_agents_dir,
)
from scripts.install.plugins.opencode_common import (
    ManifestPluginConfig,
    read_manifest,
    remove_manifest_owned_assets,
    uninstall_with_manifest,
    verify_with_manifest,
)
from scripts.shared.agent_catalog import is_public_agent, load_public_agents


if TYPE_CHECKING:
    from pathlib import Path


AGENT_MANIFEST_FILENAME = ".nwave-agents-manifest.json"
AGENT_SUFFIX = ".agent.md"
_PLUGIN_NAME = "copilot-agents"


def find_agents_source(context: InstallContext) -> Path | None:
    """Locate the agents source directory from dist or project layout."""
    dist_agents = context.framework_source / "agents"
    if dist_agents.exists():
        return dist_agents

    project_agents = context.project_root / "nWave" / "agents"
    if project_agents.exists():
        return project_agents

    return None


def _write_manifest(target_dir: Path, installed_names: list[str]) -> None:
    """Record the agents this install wrote. Same format as the OpenCode agents manifest."""
    manifest = {"installed_agents": sorted(installed_names), "version": "1.0"}
    (target_dir / AGENT_MANIFEST_FILENAME).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def _refusal(target: Path) -> str:
    return (
        f"WHAT: {target} is a file nWave did not write, so the Copilot agents are not installed. "
        "WHY: nWave replaces only the agents its manifest lists, so a user's file of the same name is never overwritten. "
        f"HOW: rename or move {target}, then run the installer again."
    )


def _config(target_dir: Path, plugin_name: str) -> ManifestPluginConfig:
    return ManifestPluginConfig(
        plugin_name=plugin_name,
        target_dir=target_dir,
        manifest_filename=AGENT_MANIFEST_FILENAME,
        noun="agents",
        installed_key="installed_agents",
        host_name="Copilot",
        suffix=AGENT_SUFFIX,
    )


def public_agent_sources(context: InstallContext, agents_source: Path) -> list[Path]:
    """The role source files the Copilot install writes: every nw-*.md the catalog marks public (all in dev mode)."""
    public_agents = (
        set()
        if context.dev_mode
        else load_public_agents(context.project_root / "nWave")
    )
    return [
        source
        for source in sorted(agents_source.glob("nw-*.md"))
        if is_public_agent(source.name, public_agents)
    ]


def agent_collision(target_dir: Path, sources: list[Path]) -> str | None:
    """The refusal for the first target that is a file the previous manifest does not list, or None.

    Refuse before any write: a file at a target name that the previous manifest does not list is the user's.
    """
    previous = (
        read_manifest(target_dir, AGENT_MANIFEST_FILENAME)
        if target_dir.exists()
        else None
    )
    previously_written = (
        set(previous.get("installed_agents", [])) if previous else set()
    )
    for source in sources:
        target = target_dir / f"{source.stem}{AGENT_SUFFIX}"
        if target.exists() and source.stem not in previously_written:
            return _refusal(target)
    return None


def install_public_agents(
    context: InstallContext, agents_source: Path, target_dir: Path
) -> PluginResult:
    """Write the public role sources as Copilot agents into target_dir, replacing only what the manifest lists."""
    try:
        sources = public_agent_sources(context, agents_source)
        message = agent_collision(target_dir, sources)
        if message is not None:
            context.logger.error(f"  ❌ {message}")
            return PluginResult(
                success=False,
                plugin_name=_PLUGIN_NAME,
                message=message,
                errors=[message],
            )

        target_dir.mkdir(parents=True, exist_ok=True)
        removed = remove_manifest_owned_assets(
            target_dir, AGENT_MANIFEST_FILENAME, AGENT_SUFFIX
        )
        if removed:
            context.logger.info(
                f"  Removed {len(removed)} previously installed Copilot agents"
            )

        installed_names: list[str] = []
        installed_files: list[Path] = []
        for source in sources:
            # Copilot has no skills preload: the shared renderer inlines each frontmatter skill once.
            content = render_installed_role(source, "~/.claude/skills")
            target = target_dir / f"{source.stem}{AGENT_SUFFIX}"
            target.write_text(convert_agent(content), encoding="utf-8")
            installed_names.append(source.stem)
            installed_files.append(target)

        _write_manifest(target_dir, installed_names)

        message = (
            f"Copilot agents installed ({len(installed_names)} agents in {target_dir}; "
            f"{NOT_CHECKED})"
        )
        context.logger.summary(f"  ✅ {message}")
        return PluginResult(
            success=True,
            plugin_name=_PLUGIN_NAME,
            message=message,
            installed_files=installed_files,
        )
    except Exception as e:
        context.logger.error(f"  ❌ Failed to install Copilot agents: {e}")
        return PluginResult(
            success=False,
            plugin_name=_PLUGIN_NAME,
            message=f"Copilot agents installation failed: {e!s}",
            errors=[str(e)],
        )


class CopilotAgentsPlugin(InstallationPlugin):
    """Writes the public nWave roles as Copilot custom agents, and verifies and removes them."""

    def __init__(self) -> None:
        super().__init__(name=_PLUGIN_NAME, priority=37)

    def install(self, context: InstallContext) -> PluginResult:
        """Install public roles from nWave/agents/ into the Copilot agents folder."""
        context.logger.info("  📦 Installing Copilot agents...")

        agents_source = find_agents_source(context)
        if agents_source is None:
            context.logger.info("  ⏭️ No agents directory found, skipping")
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="No agents to install (source directory not found)",
            )
        return install_public_agents(context, agents_source, copilot_agents_dir())

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Remove only the agents the manifest lists; the user's own agents stay."""
        return uninstall_with_manifest(
            context=context,
            config=_config(copilot_agents_dir(), self.name),
        )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify the agent files the manifest lists exist."""
        return verify_with_manifest(
            context=context,
            config=_config(copilot_agents_dir(), self.name),
            source_finder=find_agents_source,
        )
