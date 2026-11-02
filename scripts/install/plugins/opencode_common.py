"""Shared utilities for OpenCode installer plugins.

Provides pure functions for parsing/rendering YAML frontmatter and
manifest-based uninstall/verify lifecycle helpers, used by both
opencode_agents_plugin and opencode_commands_plugin. Also provides
``opencode_config_dir()``, the single OPENCODE_CONFIG_DIR-override-or-
default resolution shared by all four OpenCode plugins (des, skills,
agents, commands) -- previously copied verbatim into each one.

These functions handle malformed input gracefully by returning empty
dicts rather than raising exceptions -- the caller's install() method
wraps everything in try/except for higher-level error reporting.

The lifecycle helpers (read_manifest, uninstall_with_manifest,
verify_with_manifest) abstract the noun-vs-noun differences between
"commands" and "agents" plugins via callable + label parameters,
preserving exact behavior of both pre-refactor implementations.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml


if TYPE_CHECKING:
    from collections.abc import Callable

    from scripts.install.plugins.base import InstallContext, PluginResult


def opencode_config_dir() -> Path:
    """Return the OpenCode configuration directory.

    Single source for the OPENCODE_CONFIG_DIR-override-or-default
    resolution every OpenCode plugin needs (des/skills/agents/commands
    each add their own subpath on top of this).

    Returns:
        Path to ``$OPENCODE_CONFIG_DIR`` if set, else ``~/.config/opencode``.
    """
    override = os.environ.get("OPENCODE_CONFIG_DIR")
    return Path(override) if override else Path.home() / ".config" / "opencode"


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body content.

    Expects content in the form:
        ---
        key: value
        ---

        Body content here.

    Handles gracefully:
    - Missing opening delimiter: returns ({}, content)
    - Missing closing delimiter: returns ({}, content)
    - Malformed YAML: returns ({}, content)

    Args:
        content: Full file content with YAML frontmatter

    Returns:
        Tuple of (parsed frontmatter dict, body string including leading newline)
    """
    if not content.startswith("---"):
        return {}, content

    end_index = content.find("---", 3)
    if end_index == -1:
        return {}, content

    frontmatter_text = content[3:end_index].strip()
    body = content[end_index + 3 :]

    try:
        frontmatter = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError:
        return {}, content

    return frontmatter, body


def render_frontmatter(frontmatter: dict) -> str:
    """Serialize a frontmatter dict back to YAML frontmatter string.

    Uses block style for nested mappings (not flow style) because
    OpenCode's Zod parser expects a record format.

    Args:
        frontmatter: Transformed frontmatter dict

    Returns:
        String in "---\\nkey: value\\n---" format
    """
    yaml_text = yaml.dump(
        frontmatter,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    return f"---\n{yaml_text}---"


def read_manifest(target_dir: Path, manifest_filename: str) -> dict | None:
    """Read the install manifest from target_dir, or None if absent.

    Args:
        target_dir: Directory containing the manifest
        manifest_filename: Manifest file name (e.g. ".nwave-commands-manifest.json")

    Returns:
        Parsed manifest dict, or None if file does not exist.
    """
    manifest_path = target_dir / manifest_filename
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def remove_manifest_owned_assets(
    target_dir: Path,
    manifest_filename: str,
    suffix: str | None,
    *,
    manifest_key: str = "installed_agents",
    required_prefix: str = "nw-",
) -> list[str]:
    """Delete every asset the previous install manifest records as nWave-owned.

    Clean-then-write: an install must leave the target containing ONLY what
    this run wrote.  Without this, narrowing the population (dev install ->
    public install) leaves the no-longer-written assets on disk as orphans --
    private skills/agents leaking past the public filter, retired commands
    still resolvable, and a later ownership preflight refusing them as
    untracked collisions.

    Ownership is decided by the PREVIOUS manifest, never by name: a foreign
    or user-created asset, even one carrying the ``nw-`` prefix but absent
    from the manifest, is not touched (name-is-not-ownership, the same rule
    the Codex preflight enforces).  ``required_prefix`` is a belt-and-braces
    guard on top of that, not the ownership test -- families whose names
    legitimately carry no prefix (OpenCode commands are ``deliver``,
    ``distill``, ...) pass ``required_prefix=""``.

    Args:
        target_dir: Host directory the plugin writes its family into
        manifest_filename: Manifest file name in target_dir
        suffix: Asset file suffix including the dot (".toml" / ".md"), or
            ``None`` when the family's assets are DIRECTORIES (skills), in
            which case the whole owned subtree is removed.
        manifest_key: Manifest key listing the previously written names
            ("installed_agents" / "installed_skills" / "installed_commands")
        required_prefix: Extra name guard; "" disables it.

    Returns:
        Sorted stems that were removed.
    """
    manifest_path = target_dir / manifest_filename
    if manifest_path.is_symlink() or not manifest_path.is_file():
        return []
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    names = document.get(manifest_key) if isinstance(document, dict) else None
    if not isinstance(names, list):
        return []
    if target_dir.is_symlink() or not target_dir.is_dir():
        return []
    removed: list[str] = []
    for name in names:
        if not (
            isinstance(name, str)
            and name.startswith(required_prefix)
            and Path(name).name == name
        ):
            continue
        if suffix is None:
            asset = target_dir / name
            if asset.parent != target_dir or asset.is_symlink() or not asset.is_dir():
                continue
            shutil.rmtree(asset)
        else:
            asset = target_dir / f"{name}{suffix}"
            if asset.is_symlink() or not asset.is_file():
                continue
            asset.unlink()
        removed.append(name)
    return sorted(removed)


@dataclass(frozen=True, slots=True)
class ManifestPluginConfig:
    """What a manifest-driven plugin lifecycle needs: its name, where and how
    its manifest lives, and the noun to call its items in a message.

    Abstracts the noun-vs-noun differences ("commands" vs "agents") between
    the two OpenCode plugins that both drive their lifecycle off a manifest.
    """

    plugin_name: str
    target_dir: Path
    manifest_filename: str
    noun: str
    installed_key: str
    host_name: str = "OpenCode"


def uninstall_with_manifest(
    context: InstallContext,
    config: ManifestPluginConfig,
) -> PluginResult:
    """Manifest-driven uninstall shared between OpenCode commands + agents plugins.

    Reads the manifest from target_dir, removes each item listed under
    ``installed_key`` (file = ``<name>.md`` in target_dir), then deletes the
    manifest itself. Items not in the manifest are preserved (user-created).

    Args:
        context: Install context (used for logging).
        config: Plugin name, target directory, manifest file name, noun
            label, and manifest key shared between commands + agents plugins.

    Returns:
        PluginResult with success/failure outcome.
    """
    from scripts.install.plugins.base import PluginResult

    plugin_name = config.plugin_name
    target_dir = config.target_dir
    manifest_filename = config.manifest_filename
    noun = config.noun
    installed_key = config.installed_key

    try:
        context.logger.info(f"  \U0001f5d1️ Uninstalling {config.host_name} {noun}...")
        manifest = read_manifest(target_dir, manifest_filename)

        if manifest is None:
            context.logger.info(
                f"  ⏭️ No {config.host_name} {noun} manifest found, skipping"
            )
            return PluginResult(
                success=True,
                plugin_name=plugin_name,
                message=f"No {config.host_name} {noun} to uninstall (no manifest found)",
            )

        installed = manifest.get(installed_key, [])
        removed_count = 0
        for item_name in installed:
            item_file = target_dir / f"{item_name}.md"
            if item_file.exists():
                item_file.unlink()
                removed_count += 1

        manifest_path = target_dir / manifest_filename
        if manifest_path.exists():
            manifest_path.unlink()

        context.logger.info(
            f"  \U0001f5d1️ Removed {removed_count} {config.host_name} {noun}"
        )
        return PluginResult(
            success=True,
            plugin_name=plugin_name,
            message=f"{config.host_name} {noun} uninstalled ({removed_count} removed)",
        )
    except Exception as e:
        context.logger.error(f"  ❌ Failed to uninstall {config.host_name} {noun}: {e}")
        return PluginResult(
            success=False,
            plugin_name=plugin_name,
            message=f"{config.host_name} {noun} uninstallation failed: {e!s}",
            errors=[str(e)],
        )


def verify_with_manifest(
    context: InstallContext,
    config: ManifestPluginConfig,
    source_finder: Callable[[InstallContext], Path | None],
) -> PluginResult:
    """Manifest-driven verify shared between OpenCode commands + agents plugins.

    Reads the manifest and asserts each listed file exists. If the manifest is
    absent AND the source path resolves (via source_finder), the absence is a
    failure (manifest expected but missing). If both manifest and source are
    absent, verification is skipped (nothing was configured).

    Args:
        context: Install context (used for logging).
        config: Plugin name, target directory, manifest file name, noun
            label, and manifest key shared between commands + agents plugins.
        source_finder: Callable returning the source directory if present,
            or None if the plugin had nothing to install.

    Returns:
        PluginResult with verification outcome.
    """
    from scripts.install.plugins.base import PluginResult

    plugin_name = config.plugin_name
    target_dir = config.target_dir
    manifest_filename = config.manifest_filename
    noun = config.noun
    installed_key = config.installed_key

    try:
        context.logger.info(f"  \U0001f50e Verifying {config.host_name} {noun}...")
        manifest = read_manifest(target_dir, manifest_filename)

        if manifest is None:
            source = source_finder(context)
            if source is None:
                context.logger.info(
                    f"  ⏭️ No {config.host_name} {noun} to verify (none configured)"
                )
                return PluginResult(
                    success=True,
                    plugin_name=plugin_name,
                    message=f"No {config.host_name} {noun} configured, verification skipped",
                )
            return PluginResult(
                success=False,
                plugin_name=plugin_name,
                message=f"{config.host_name} {noun} verification failed: manifest not found",
                errors=[f"Manifest file {manifest_filename} not found"],
            )

        installed = manifest.get(installed_key, [])
        missing: list[str] = []
        verified_count = 0
        for item_name in installed:
            item_file = target_dir / f"{item_name}.md"
            if not item_file.exists():
                missing.append(f"{item_name}.md not found")
            else:
                verified_count += 1

        if missing:
            context.logger.error(
                f"  ❌ {config.host_name} {noun} verification failed: {len(missing)} missing"
            )
            return PluginResult(
                success=False,
                plugin_name=plugin_name,
                message=(
                    f"{config.host_name} {noun} verification failed: "
                    f"{len(missing)} {noun} missing"
                ),
                errors=missing,
            )

        context.logger.info(f"  ✅ Verified {verified_count} {config.host_name} {noun}")
        return PluginResult(
            success=True,
            plugin_name=plugin_name,
            message=f"{config.host_name} {noun} verification passed ({verified_count} {noun})",
        )
    except Exception as e:
        context.logger.error(f"  ❌ Failed to verify {config.host_name} {noun}: {e}")
        return PluginResult(
            success=False,
            plugin_name=plugin_name,
            message=f"{config.host_name} {noun} verification failed: {e!s}",
            errors=[str(e)],
        )
