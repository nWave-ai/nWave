"""Plugin for installing nWave agents into Codex CLI's TOML agent format.

Codex CLI expects agents at: ~/.codex/agents/{agent-name}.toml
Each agent file is TOML with:
  name = "agent-name"
  description = "..."
  developer_instructions = '''
  ...full agent body...
  '''
  model = "..."   (optional)

This is distinct from OpenCode (~/.config/opencode/agents/*.md), which uses
YAML-frontmatter Markdown. The transform pipeline:

  Claude Code source (.md, YAML frontmatter + Markdown body)
    -> parse frontmatter + body
    -> extract scalar fields (name, description, model)
    -> drop tools block (Codex has no tool-permission equivalent; WARN logged)
    -> render TOML with body as developer_instructions

A manifest (.nwave-agents-manifest.json) tracks which agents nWave installed,
enabling safe uninstallation without touching user-created agents.
"""

import json
import logging
import os
import shutil
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.opencode_common import parse_frontmatter
from scripts.shared.agent_catalog import is_public_agent, load_public_agents
from scripts.shared.platform_contracts import CODEX_AGENT_FORBIDDEN_FIELDS


_MANIFEST_FILENAME = ".nwave-agents-manifest.json"
_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _codex_agents_dir() -> Path:
    """Return the Codex CLI agents target directory.

    Codex agents live at ~/.codex/agents/. CODEX_HOME overrides ~/.codex/.

    Returns:
        Path to ~/.codex/agents/ (or $CODEX_HOME/agents/)
    """
    override = os.environ.get("CODEX_HOME")
    base = Path(override) if override else Path.home() / ".codex"
    return base / "agents"


def _codex_config_dir() -> Path:
    """Return the Codex CLI configuration directory.

    Returns:
        Path to ~/.codex/ (or $CODEX_HOME if set)
    """
    override = os.environ.get("CODEX_HOME")
    return Path(override) if override else Path.home() / ".codex"


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


# ---------------------------------------------------------------------------
# Transform pipeline (pure functions)
# ---------------------------------------------------------------------------


def _extract_scalar_fields(frontmatter: dict) -> dict[str, str]:
    """Extract string-valued TOML fields from the agent frontmatter.

    Keeps only scalar (string) fields that have TOML equivalents.
    Drops all fields in CODEX_AGENT_FORBIDDEN_FIELDS and any non-string
    complex values (lists, dicts).

    Args:
        frontmatter: Parsed YAML frontmatter dict from a Claude Code agent

    Returns:
        Dict of TOML-compatible scalar fields
    """
    return {
        key: str(value)
        for key, value in frontmatter.items()
        if key not in CODEX_AGENT_FORBIDDEN_FIELDS and isinstance(value, str)
    }


def _warn_if_tools_dropped(agent_name: str, frontmatter: dict) -> None:
    """Log a warning when a tools block is dropped during transform.

    Codex CLI has no per-agent tool-permission block equivalent; permissions
    are controlled via sandbox_mode and approval_policy at config level.

    Args:
        agent_name: Agent identifier (for log context)
        frontmatter: Parsed frontmatter dict, potentially containing tools
    """
    if "tools" in frontmatter:
        _logger.warning(
            "codex_agents_plugin: dropping 'tools' block for agent '%s' "
            "(Codex has no per-agent tool-permission equivalent; "
            "use sandbox_mode/approval_policy in config.toml instead)",
            agent_name,
        )


def _render_toml_agent(scalar_fields: dict[str, str], body: str) -> str:
    """Render a Codex agent TOML file from scalar fields and the agent body.

    The Codex agent TOML schema requires:
      name = "..."            (required)
      description = "..."     (required)
      developer_instructions = "..."  (multi-line string, equivalent to body)

    Optional fields (model, etc.) are included when present in scalar_fields.
    The body is assigned to developer_instructions using a TOML basic
    multi-line string (triple-quoted).

    Args:
        scalar_fields: TOML-compatible scalar fields (name, description, model…)
        body: Agent body text (Markdown section after the YAML frontmatter)

    Returns:
        Complete TOML file content as a string
    """
    lines: list[str] = []

    # Emit canonical fields first in a stable order
    for key in ("name", "description", "model"):
        if key in scalar_fields:
            lines.append(f"{key} = {_toml_string(scalar_fields[key])}")

    # Emit remaining scalar fields (alphabetical for stability)
    for key in sorted(scalar_fields):
        if key not in ("name", "description", "model"):
            lines.append(f"{key} = {_toml_string(scalar_fields[key])}")

    # Emit developer_instructions as a multi-line basic string
    lines.append(f"developer_instructions = {_toml_multiline_string(body)}")

    return "\n".join(lines) + "\n"


def _toml_string(value: str) -> str:
    """Render a TOML basic string, escaping backslashes and double-quotes.

    Args:
        value: Raw Python string value

    Returns:
        TOML-quoted string (e.g. '"hello \\"world\\""')
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_multiline_string(value: str) -> str:
    """Render a TOML basic multi-line string.

    TOML multi-line basic strings are delimited by triple double-quotes.
    The content must not contain the sequence \""" unescaped. We escape
    any embedded triple-quotes to be safe.

    Args:
        value: Multi-line string content (agent body)

    Returns:
        TOML multi-line basic string literal
    """
    # Escape any embedded triple-quotes to prevent premature termination
    safe_value = value.replace('"""', '""\\"')
    return f'"""\n{safe_value}"""'


def _transform_agent(source_content: str, agent_name: str) -> str:
    """Full transform pipeline: Claude Code agent MD -> Codex TOML.

    Pipeline:
      1. Parse YAML frontmatter + Markdown body
      2. Warn if tools block is present (will be dropped)
      3. Extract scalar TOML fields (drop forbidden + non-scalar)
      4. Render TOML with body as developer_instructions

    Args:
        source_content: Full source agent file content (Claude Code format)
        agent_name: Agent stem name (used for log context only)

    Returns:
        Transformed agent TOML content
    """
    frontmatter, body = parse_frontmatter(source_content)
    _warn_if_tools_dropped(agent_name, frontmatter)
    scalar_fields = _extract_scalar_fields(frontmatter)
    return _render_toml_agent(scalar_fields, body)


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------


def _write_manifest(target_dir: Path, installed_agent_names: list[str]) -> None:
    """Write the manifest tracking nWave-installed Codex agents.

    Args:
        target_dir: Codex agents directory
        installed_agent_names: List of installed agent stems (without .toml)
    """
    manifest = {
        "installed_agents": sorted(installed_agent_names),
        "version": "1.0",
    }
    manifest_path = target_dir / _MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _read_manifest(target_dir: Path) -> dict | None:
    """Read the manifest file if it exists.

    Args:
        target_dir: Codex agents directory

    Returns:
        Parsed manifest dict, or None if not found
    """
    manifest_path = target_dir / _MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Plugin class
# ---------------------------------------------------------------------------


class CodexAgentsPlugin(InstallationPlugin):
    """Plugin for installing nWave agents into Codex CLI TOML format."""

    def __init__(self) -> None:
        """Initialize Codex agents plugin with name and priority."""
        super().__init__(name="codex-agents", priority=45)
        self.dependencies = ["codex-skills"]

    def validate_prerequisites(self, context: InstallContext) -> PluginResult:
        """Check whether Codex CLI is present; skip gracefully if not.

        Detection: ~/.codex/ directory exists OR `codex` binary in PATH.

        Args:
            context: InstallContext (unused for detection, but required by ABC)

        Returns:
            PluginResult with success=True always (skip or proceed)
        """

        codex_dir = _codex_config_dir()
        codex_binary = shutil.which("codex") is not None
        if not codex_dir.exists() and not codex_binary:
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Codex CLI not detected, skipping agents installation",
            )

        return PluginResult(
            success=True,
            plugin_name=self.name,
            message="Codex agents prerequisites validated",
        )

    def install(self, context: InstallContext) -> PluginResult:
        """Install agents from nWave/agents/ as Codex TOML files.

        Transform pipeline per agent:
          1. Parse YAML frontmatter + Markdown body
          2. Drop tools block (WARN logged; Codex has no equivalent)
          3. Emit scalar fields (name, description, model) as TOML
          4. Emit Markdown body as developer_instructions multi-line string
          5. Write to ~/.codex/agents/{agent-name}.toml

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            prereq = self.validate_prerequisites(context)
            if "skip" in prereq.message.lower():
                return prereq

            context.logger.info("  Installing Codex agents...")

            agents_source = _find_agents_source(context)
            if agents_source is None:
                context.logger.info("  No agents directory found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No agents to install (source directory not found)",
                )

            target_dir = _codex_agents_dir()
            target_dir.mkdir(parents=True, exist_ok=True)

            public_agents = (
                set()
                if context.dev_mode
                else load_public_agents(context.project_root / "nWave")
            )

            agent_files = sorted(agents_source.glob("nw-*.md"))
            if not agent_files:
                context.logger.info("  No agent files found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No agent files found in source directory",
                )

            installed_names: list[str] = []
            installed_files: list[Path] = []

            for source_file in agent_files:
                if not is_public_agent(source_file.name, public_agents):
                    continue

                agent_name = source_file.stem
                content = source_file.read_text(encoding="utf-8")
                transformed = _transform_agent(content, agent_name)

                target_file = target_dir / f"{agent_name}.toml"
                target_file.write_text(transformed, encoding="utf-8")

                installed_names.append(agent_name)
                installed_files.append(target_file)

            _write_manifest(target_dir, installed_names)

            context.logger.info(
                f"  Codex agents installed ({len(installed_names)} agents)"
            )

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=(
                    f"Codex agents installed successfully ({len(installed_names)} agents)"
                ),
                installed_files=installed_files,
            )

        except Exception as e:
            context.logger.error(f"  Failed to install Codex agents: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex agents installation failed: {e!s}",
                errors=[str(e)],
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall only nWave-installed Codex agents using manifest.

        Reads the manifest to determine which agents were installed by nWave,
        removes only those (.toml files), and leaves user-created agents
        untouched. The manifest is also removed.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            context.logger.info("  Uninstalling Codex agents...")

            target_dir = _codex_agents_dir()
            manifest = _read_manifest(target_dir)

            if manifest is None:
                context.logger.info("  No Codex agents manifest found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No Codex agents to uninstall (no manifest found)",
                )

            installed_agents = manifest.get("installed_agents", [])
            removed_count = 0

            for agent_name in installed_agents:
                agent_file = target_dir / f"{agent_name}.toml"
                if agent_file.exists():
                    agent_file.unlink()
                    removed_count += 1

            manifest_path = target_dir / _MANIFEST_FILENAME
            if manifest_path.exists():
                manifest_path.unlink()

            context.logger.info(f"  Removed {removed_count} Codex agents")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Codex agents uninstalled ({removed_count} removed)",
            )

        except Exception as e:
            context.logger.error(f"  Failed to uninstall Codex agents: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex agents uninstallation failed: {e!s}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify Codex agents were installed correctly.

        Checks that each agent listed in the manifest has a valid .toml file.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating verification success or failure
        """
        try:
            context.logger.info("  Verifying Codex agents...")

            target_dir = _codex_agents_dir()
            manifest = _read_manifest(target_dir)

            if manifest is None:
                agents_source = _find_agents_source(context)
                if agents_source is None:
                    context.logger.info("  No Codex agents to verify (none configured)")
                    return PluginResult(
                        success=True,
                        plugin_name=self.name,
                        message="No Codex agents configured, verification skipped",
                    )

                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Codex agents verification failed: manifest not found",
                    errors=["Manifest file .nwave-agents-manifest.json not found"],
                )

            installed_agents = manifest.get("installed_agents", [])
            missing_agents: list[str] = []
            verified_count = 0

            for agent_name in installed_agents:
                agent_toml = target_dir / f"{agent_name}.toml"
                if not agent_toml.exists():
                    missing_agents.append(f"{agent_name}.toml not found")
                else:
                    verified_count += 1

            if missing_agents:
                context.logger.error(
                    f"  Codex agents verification failed: {len(missing_agents)} missing"
                )
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=(
                        f"Codex agents verification failed: "
                        f"{len(missing_agents)} agents missing .toml"
                    ),
                    errors=missing_agents,
                )

            context.logger.info(f"  Verified {verified_count} Codex agents")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Codex agents verification passed ({verified_count} agents)",
            )

        except Exception as e:
            context.logger.error(f"  Failed to verify Codex agents: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex agents verification failed: {e!s}",
                errors=[str(e)],
            )
