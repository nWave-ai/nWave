"""Plugin for installing the nWave DES TypeScript shim into OpenCode.

OpenCode plugins live at: ~/.config/opencode/plugins/
The DES shim translates OpenCode hook events to Claude Code JSON format
and invokes the existing Python DES adapter via subprocess.

A manifest (.nwave-des-manifest.json) tracks the installed shim for
clean uninstallation and version tracking.
"""

import hashlib
import json
import os
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.shared.install_paths import (
    resolve_des_lib_path_for_spawn,
    resolve_python_command_for_spawn,
)


_SHIM_FILENAME = "nwave-des.ts"
_MANIFEST_FILENAME = ".nwave-des-manifest.json"
_TEMPLATE_FILENAME = "opencode-des-plugin.ts.template"


def _opencode_config_dir() -> Path:
    """Return the OpenCode configuration directory.

    Returns:
        Path to ~/.config/opencode/
    """
    override = os.environ.get("OPENCODE_CONFIG_DIR")
    return Path(override) if override else Path.home() / ".config" / "opencode"


def _get_framework_version(context: InstallContext) -> str:
    """Read the framework version from VERSION file or fallback.

    Args:
        context: InstallContext with framework_source

    Returns:
        Version string (e.g. '1.7.0')
    """
    version_file = context.framework_source / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


class OpenCodeDESPlugin(InstallationPlugin):
    """Plugin for installing the nWave DES TypeScript shim into OpenCode."""

    def __init__(self):
        """Initialize OpenCode DES plugin with name, priority, and dependencies."""
        super().__init__(name="opencode-des", priority=55)
        self.dependencies = ["des", "opencode-skills"]

    def validate_prerequisites(self, context: InstallContext) -> PluginResult:
        """Validate that OpenCode and DES prerequisites exist.

        Checks:
        1. OpenCode config directory exists (~/.config/opencode/)
        2. DES Python module is installed (~/.claude/lib/python/des/)
        3. TS template exists in framework source

        If OpenCode is not detected, returns success with skip message.

        Args:
            context: InstallContext with claude_dir and framework_source

        Returns:
            PluginResult with success=True to skip, or success=False on real errors
        """
        opencode_dir = _opencode_config_dir()

        # OpenCode not detected: skip silently (not an error)
        if not opencode_dir.exists():
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="OpenCode not detected, skipping DES shim installation",
            )

        # DES module must be installed
        des_module = context.claude_dir / "lib" / "python" / "des"
        if not des_module.exists():
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=(
                    f"DES Python module not found at {des_module}. Install DES first."
                ),
                errors=["DES module must be installed before OpenCode DES shim"],
            )

        # TS template must exist
        template_path = self._find_template(context)
        if template_path is None:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"TS template {_TEMPLATE_FILENAME} not found",
                errors=[f"Template {_TEMPLATE_FILENAME} missing from framework source"],
            )

        return PluginResult(
            success=True,
            plugin_name=self.name,
            message="OpenCode DES prerequisites validated",
        )

    def install(self, context: InstallContext) -> PluginResult:
        """Install the DES TypeScript shim into OpenCode plugins directory.

        Steps:
        1. Validate prerequisites
        2. Read TS template
        3. Resolve Python path
        4. Replace {{PYTHON_PATH}} and {{PYTHONPATH}} placeholders
        5. Write rendered shim to ~/.config/opencode/plugins/nwave-des.ts
        6. Write manifest with version and content hash

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            # Validate prerequisites first
            prereq_result = self.validate_prerequisites(context)
            if not prereq_result.success:
                return prereq_result

            # Skip if OpenCode not detected
            opencode_dir = _opencode_config_dir()
            if not opencode_dir.exists():
                return prereq_result  # success=True with skip message

            # Read template
            template_path = self._find_template(context)
            template_content = template_path.read_text(encoding="utf-8")

            # Resolve Python path and render template
            python_path = resolve_python_command_for_spawn()
            rendered = template_content.replace("{{PYTHON_PATH}}", python_path)
            rendered = rendered.replace(
                "{{PYTHONPATH}}", resolve_des_lib_path_for_spawn()
            )

            # Write shim file
            plugins_dir = opencode_dir / "plugins"
            plugins_dir.mkdir(parents=True, exist_ok=True)
            shim_path = plugins_dir / _SHIM_FILENAME

            if not context.dry_run:
                shim_path.write_text(rendered, encoding="utf-8")

            # Write manifest
            content_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
            version = _get_framework_version(context)
            manifest = {
                "shim_file": str(shim_path),
                "version": version,
                "sha256": content_hash,
            }
            manifest_path = opencode_dir / _MANIFEST_FILENAME

            if not context.dry_run:
                manifest_path.write_text(
                    json.dumps(manifest, indent=2) + "\n",
                    encoding="utf-8",
                )

            context.logger.info(f"  OpenCode DES shim installed: {shim_path}")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="OpenCode DES shim installed successfully",
                installed_files=[shim_path],
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OpenCode DES shim installation failed: {e}",
                errors=[str(e)],
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Remove the DES shim file and manifest.

        Only removes nwave-des.ts and the manifest. Other user plugins
        in the plugins directory are untouched.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            opencode_dir = _opencode_config_dir()

            # Remove shim
            shim_path = opencode_dir / "plugins" / _SHIM_FILENAME
            if shim_path.exists():
                shim_path.unlink()
                context.logger.info(f"  Removed DES shim: {shim_path}")

            # Remove manifest
            manifest_path = opencode_dir / _MANIFEST_FILENAME
            if manifest_path.exists():
                manifest_path.unlink()
                context.logger.info(f"  Removed DES manifest: {manifest_path}")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="OpenCode DES shim uninstalled",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OpenCode DES shim uninstall failed: {e}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify the DES shim is installed and valid.

        Checks:
        1. Shim file exists at ~/.config/opencode/plugins/nwave-des.ts
        2. Manifest exists at ~/.config/opencode/.nwave-des-manifest.json

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating verification success or failure
        """
        try:
            opencode_dir = _opencode_config_dir()

            # If OpenCode not detected, skip verification
            if not opencode_dir.exists():
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="OpenCode not detected, verification skipped",
                )

            errors = []

            # Check shim file
            shim_path = opencode_dir / "plugins" / _SHIM_FILENAME
            if not shim_path.exists():
                errors.append(f"DES shim not found: {shim_path}")

            # Check manifest
            manifest_path = opencode_dir / _MANIFEST_FILENAME
            if not manifest_path.exists():
                errors.append(f"DES manifest not found: {manifest_path}")

            if errors:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="OpenCode DES shim verification failed: nwave-des.ts missing",
                    errors=errors,
                )

            context.logger.info("  OpenCode DES shim verified")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="OpenCode DES shim verification passed",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"OpenCode DES shim verification failed: {e}",
                errors=[str(e)],
            )

    def _find_template(self, context: InstallContext) -> Path | None:
        """Locate the TS shim template file.

        Checks framework_source/templates/ first, then project_root/nWave/templates/.

        Args:
            context: InstallContext with framework_source and project_root

        Returns:
            Path to the template file, or None if not found
        """
        # Check framework source (dist/ or nWave/)
        if context.framework_source:
            template = context.framework_source / "templates" / _TEMPLATE_FILENAME
            if template.exists():
                return template

        # Check project root fallback
        if context.project_root:
            template = context.project_root / "nWave" / "templates" / _TEMPLATE_FILENAME
            if template.exists():
                return template

        return None
