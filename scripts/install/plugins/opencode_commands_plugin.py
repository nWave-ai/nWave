"""
Plugin for installing nWave commands into OpenCode's command format.

OpenCode expects commands at: ~/.config/opencode/commands/{command-name}.md
Each command has YAML frontmatter with description -- but no argument-hint
or disable-model-invocation fields.

A manifest file (.nwave-commands-manifest.json) tracks which commands nWave
installed, so uninstall() can remove only nWave commands without touching
user-created ones.
"""

import json
import os
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.opencode_common import (
    parse_frontmatter,
    render_frontmatter,
)
from scripts.shared.install_paths import (
    PYTHON_CMD_SUBSTITUTION,
    resolve_python_command,
)
from scripts.shared.platform_contracts import (
    OPENCODE_COMMAND_FORBIDDEN_FIELDS,
    OPENCODE_PATH_REWRITE_EXCEPTIONS,
    OPENCODE_PATH_REWRITES,
)


_MANIFEST_FILENAME = ".nwave-commands-manifest.json"


def _opencode_commands_dir() -> Path:
    """Return the OpenCode commands target directory.

    Returns:
        Path to ~/.config/opencode/commands/
    """
    override = os.environ.get("OPENCODE_CONFIG_DIR")
    base = Path(override) if override else Path.home() / ".config" / "opencode"
    return base / "commands"


def _find_commands_source(context: InstallContext) -> Path | None:
    """Locate the commands source directory from dist or project layout.

    Args:
        context: InstallContext with framework_source and project_root

    Returns:
        Path to the commands source directory, or None if not found
    """
    dist_commands = context.framework_source / "tasks" / "nw"
    if dist_commands.exists():
        return dist_commands

    project_commands = context.project_root / "nWave" / "tasks" / "nw"
    if project_commands.exists():
        return project_commands

    return None


def _transform_frontmatter(frontmatter: dict) -> dict:
    """Apply transformation rules to convert Claude Code command frontmatter to OpenCode.

    Transformations:
        1. Remove argument-hint (not an OpenCode concept)
        2. Remove disable-model-invocation (not applicable to OpenCode)
        3. Keep everything else unchanged (especially description)

    Args:
        frontmatter: Parsed YAML frontmatter dict from Claude Code command

    Returns:
        New dict with OpenCode-compatible frontmatter
    """
    return {
        key: value
        for key, value in frontmatter.items()
        if key not in OPENCODE_COMMAND_FORBIDDEN_FIELDS
    }


def _transform_command(content: str) -> str:
    """Full transformation pipeline: parse, transform, render with body.

    Args:
        content: Full source command file content (Claude Code format)

    Returns:
        Transformed command file content (OpenCode format)
    """
    frontmatter, body = parse_frontmatter(content)
    transformed = _transform_frontmatter(frontmatter)
    rendered = render_frontmatter(transformed)
    return rendered + body


def _is_exception_path(text_segment: str) -> bool:
    """Check if a text segment contains an exception path that should not be rewritten.

    Args:
        text_segment: A portion of text surrounding a potential rewrite match

    Returns:
        True if the segment contains an exception path
    """
    return any(
        exception in text_segment for exception in OPENCODE_PATH_REWRITE_EXCEPTIONS
    )


def _rewrite_paths(content: str) -> str:
    """Rewrite Claude Code paths to OpenCode equivalents in command body text.

    Applies path rewrite rules from platform_contracts.OPENCODE_PATH_REWRITES,
    respecting exceptions from platform_contracts.OPENCODE_PATH_REWRITE_EXCEPTIONS.

    Rules are applied in order. Exception paths (e.g. ~/.claude/lib/python) are
    protected from rewriting by checking each match against the exceptions list.

    Args:
        content: Command file body text containing Claude Code paths

    Returns:
        Text with all non-exception paths rewritten to OpenCode equivalents
    """
    result = content
    for claude_prefix, opencode_prefix in OPENCODE_PATH_REWRITES:
        # Process each occurrence, skipping exceptions
        new_result = []
        remaining = result
        while claude_prefix in remaining:
            match_index = remaining.index(claude_prefix)
            # Check if this match is part of an exception path
            # Look at enough context after the match to check exceptions
            context_end = min(match_index + 100, len(remaining))
            context_segment = remaining[match_index:context_end]
            if _is_exception_path(context_segment):
                # Keep this occurrence as-is, skip past it
                new_result.append(remaining[: match_index + len(claude_prefix)])
                remaining = remaining[match_index + len(claude_prefix) :]
            else:
                # Rewrite this occurrence
                new_result.append(remaining[:match_index])
                new_result.append(opencode_prefix)
                remaining = remaining[match_index + len(claude_prefix) :]
        new_result.append(remaining)
        result = "".join(new_result)
    return result


def _write_manifest(
    target_dir: Path,
    installed_command_names: list[str],
) -> None:
    """Write the manifest file tracking nWave-installed commands.

    Args:
        target_dir: OpenCode commands directory
        installed_command_names: List of installed command filenames (without .md)
    """
    manifest = {
        "installed_commands": sorted(installed_command_names),
        "version": "1.0",
    }
    manifest_path = target_dir / _MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _read_manifest(target_dir: Path) -> dict | None:
    """Read the manifest file if it exists.

    Args:
        target_dir: OpenCode commands directory

    Returns:
        Parsed manifest dict, or None if not found
    """
    manifest_path = target_dir / _MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


class OpenCodeCommandsPlugin(InstallationPlugin):
    """Plugin for installing nWave commands into OpenCode format."""

    def __init__(self):
        """Initialize OpenCode commands plugin with name and priority."""
        super().__init__(name="opencode-commands", priority=38)

    def install(self, context: InstallContext) -> PluginResult:
        """Install commands from nWave/tasks/nw/ as OpenCode command files.

        Transforms each source command file by:
        - Removing argument-hint field
        - Removing disable-model-invocation field
        - Keeping description and all other fields

        A manifest tracks installed commands for safe uninstallation.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            context.logger.info("  \U0001f4e6 Installing OpenCode commands...")

            commands_source = _find_commands_source(context)
            if commands_source is None:
                context.logger.info(
                    "  \u23ed\ufe0f No commands directory found, skipping"
                )
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No commands to install (source directory not found)",
                )

            target_dir = _opencode_commands_dir()
            target_dir.mkdir(parents=True, exist_ok=True)

            command_files = sorted(commands_source.glob("*.md"))
            if not command_files:
                context.logger.info("  \u23ed\ufe0f No command files found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No command files found in source directory",
                )

            installed_names = []
            installed_files = []

            python_cmd = resolve_python_command()

            for source_file in command_files:
                command_name = source_file.stem
                content = source_file.read_text(encoding="utf-8")

                transformed = _transform_command(content)

                # Rewrite Claude Code paths to OpenCode equivalents
                transformed = _rewrite_paths(transformed)

                # Resolve Python command substitution at install time
                if PYTHON_CMD_SUBSTITUTION in transformed:
                    transformed = transformed.replace(
                        PYTHON_CMD_SUBSTITUTION, python_cmd
                    )

                target_file = target_dir / f"{command_name}.md"
                target_file.write_text(transformed, encoding="utf-8")

                installed_names.append(command_name)
                installed_files.append(target_file)

            _write_manifest(target_dir, installed_names)

            context.logger.info(
                f"  \u2705 OpenCode commands installed "
                f"({len(installed_names)} commands)"
            )

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=(
                    f"OpenCode commands installed successfully "
                    f"({len(installed_names)} commands)"
                ),
                installed_files=installed_files,
            )
        except Exception as e:
            context.logger.error(f"  \u274c Failed to install OpenCode commands: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OpenCode commands installation failed: {e!s}",
                errors=[str(e)],
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall only nWave-installed OpenCode commands using manifest.

        Reads the manifest to determine which commands were installed by nWave,
        removes only those, and leaves user-created commands untouched.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            context.logger.info("  \U0001f5d1\ufe0f Uninstalling OpenCode commands...")

            target_dir = _opencode_commands_dir()
            manifest = _read_manifest(target_dir)

            if manifest is None:
                context.logger.info(
                    "  \u23ed\ufe0f No OpenCode commands manifest found, skipping"
                )
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No OpenCode commands to uninstall (no manifest found)",
                )

            installed_commands = manifest.get("installed_commands", [])
            removed_count = 0

            for command_name in installed_commands:
                command_file = target_dir / f"{command_name}.md"
                if command_file.exists():
                    command_file.unlink()
                    removed_count += 1

            # Remove the manifest itself
            manifest_path = target_dir / _MANIFEST_FILENAME
            if manifest_path.exists():
                manifest_path.unlink()

            context.logger.info(
                f"  \U0001f5d1\ufe0f Removed {removed_count} OpenCode commands"
            )

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"OpenCode commands uninstalled ({removed_count} removed)",
            )
        except Exception as e:
            context.logger.error(f"  \u274c Failed to uninstall OpenCode commands: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OpenCode commands uninstallation failed: {e!s}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify OpenCode commands were installed correctly.

        Checks that each command listed in the manifest exists as a file
        with valid YAML frontmatter.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating verification success or failure
        """
        try:
            context.logger.info("  \U0001f50e Verifying OpenCode commands...")

            target_dir = _opencode_commands_dir()
            manifest = _read_manifest(target_dir)

            if manifest is None:
                commands_source = _find_commands_source(context)
                if commands_source is None:
                    context.logger.info(
                        "  \u23ed\ufe0f No OpenCode commands to verify "
                        "(none configured)"
                    )
                    return PluginResult(
                        success=True,
                        plugin_name=self.name,
                        message=(
                            "No OpenCode commands configured, verification skipped"
                        ),
                    )

                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=(
                        "OpenCode commands verification failed: manifest not found"
                    ),
                    errors=[f"Manifest file {_MANIFEST_FILENAME} not found"],
                )

            installed_commands = manifest.get("installed_commands", [])
            missing_commands = []
            verified_count = 0

            for command_name in installed_commands:
                command_file = target_dir / f"{command_name}.md"
                if not command_file.exists():
                    missing_commands.append(f"{command_name}.md not found")
                else:
                    verified_count += 1

            if missing_commands:
                context.logger.error(
                    f"  \u274c OpenCode commands verification failed: "
                    f"{len(missing_commands)} missing"
                )
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=(
                        f"OpenCode commands verification failed: "
                        f"{len(missing_commands)} commands missing"
                    ),
                    errors=missing_commands,
                )

            context.logger.info(f"  \u2705 Verified {verified_count} OpenCode commands")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=(
                    f"OpenCode commands verification passed ({verified_count} commands)"
                ),
            )
        except Exception as e:
            context.logger.error(f"  \u274c Failed to verify OpenCode commands: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OpenCode commands verification failed: {e!s}",
                errors=[str(e)],
            )
