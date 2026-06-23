"""Plugin for installing the nWave DES TypeScript extension into the pi agent.

pi (pi.dev, the @earendil-works/pi-coding-agent) loads extensions from a config
dir (default ``~/.pi/agent``, overridable via ``PI_CONFIG_DIR``). This plugin
renders ``nWave/templates/pi-des-extension.ts.template`` (placeholders ->
resolved python + DES lib path via ``install_paths`` resolvers) into that dir and
writes ``.nwave-des-manifest.json`` for clean uninstall. All enforcement logic
lives in the reused Python DES engine (``src/des/**``) -- this extension is a
protocol translator only (zero adapter fork; mirrors the OpenCode shim, ADR-PI-002 /
D11). Contract shape: bounded-change -- declared mutation set = rendered extension
file + manifest.

A3 (pi skill-dir + ``resources_discover`` shape, confirmed against pi 0.79.9 types
at ``@earendil-works/pi-coding-agent/dist/core/extensions/types.d.ts``): pi exposes
skill directories to an extension through the ``resources_discover`` event. The
handler returns a ``ResourcesDiscoverResult`` whose relevant field is
``skillPaths?: string[]`` (siblings ``promptPaths?``, ``themePaths?``) -- an array
of absolute directory paths pi loads skills from. ``resources_discover`` fires
after ``session_start`` with ``reason: "startup" | "reload"``. Crafter-skill
wiring (ADR-PI-003 / D9) therefore rides this event by returning the installed
skill directory in ``skillPaths``; that handler lands in the extension template in
a later step (01-02/03), not here.
"""

from __future__ import annotations

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


_EXTENSION_FILENAME = "nwave-des.ts"
_MANIFEST_FILENAME = ".nwave-des-manifest.json"
_TEMPLATE_FILENAME = "pi-des-extension.ts.template"


def _pi_config_dir() -> Path:
    """Return the pi configuration directory.

    Honors the ``PI_CONFIG_DIR`` env override (used by acceptance tests against a
    tmp dir); otherwise the default pi location (R1).
    """
    override = os.environ.get("PI_CONFIG_DIR")
    return Path(override) if override else Path.home() / ".pi" / "agent"


def _get_framework_version(context: InstallContext) -> str:
    """Read the framework version from VERSION file or fallback."""
    version_file = context.framework_source / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


class PiDESPlugin(InstallationPlugin):
    """Installs the nWave DES TS extension into the pi agent config dir."""

    def __init__(self) -> None:
        super().__init__(name="pi-des", priority=55)
        self.dependencies = ["des"]

    def validate_prerequisites(self, context: InstallContext) -> PluginResult:
        """Validate that pi and DES prerequisites exist.

        Checks:
        1. pi config directory exists (``PI_CONFIG_DIR`` or ``~/.pi/agent``)
        2. DES Python module is installed (``~/.claude/lib/python/des/``)
        3. TS template exists in framework source

        If pi is not detected, returns success with a skip message (R1).
        """
        pi_dir = _pi_config_dir()

        # pi not detected: skip silently (not an error) -- R1 non-fatal warning.
        if not pi_dir.exists():
            context.logger.warn(
                "  pi not detected, skipping DES extension installation"
            )
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="pi not detected, skipping DES extension installation",
            )

        # DES module must be installed.
        des_module = context.claude_dir / "lib" / "python" / "des"
        if not des_module.exists():
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=(
                    f"DES Python library not found at {des_module}. Install DES first."
                ),
                errors=["DES library must be installed before pi DES extension"],
            )

        # TS template must exist.
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
            message="pi DES prerequisites validated",
        )

    def install(self, context: InstallContext) -> PluginResult:
        """Render the DES extension into the pi config dir and write a manifest.

        Steps:
        1. Validate prerequisites (skips with success if pi not detected).
        2. Read the TS template.
        3. Resolve the python interpreter + DES lib path.
        4. Replace ``{{PYTHON_PATH}}`` / ``{{PYTHONPATH}}`` placeholders.
        5. Write the rendered extension to ``<pi_dir>/nwave-des.ts``.
        6. Write the manifest with version + content hash.
        """
        try:
            prereq_result = self.validate_prerequisites(context)
            if not prereq_result.success:
                return prereq_result

            pi_dir = _pi_config_dir()
            if not pi_dir.exists():
                return prereq_result  # success=True with skip message

            template_path = self._find_template(context)
            template_content = template_path.read_text(encoding="utf-8")

            python_path = resolve_python_command_for_spawn()
            rendered = template_content.replace("{{PYTHON_PATH}}", python_path)
            rendered = rendered.replace(
                "{{PYTHONPATH}}", resolve_des_lib_path_for_spawn()
            )

            extension_path = pi_dir / _EXTENSION_FILENAME
            if not context.dry_run:
                extension_path.write_text(rendered, encoding="utf-8")

            content_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
            manifest = {
                "extension_file": str(extension_path),
                "version": _get_framework_version(context),
                "sha256": content_hash,
            }
            manifest_path = pi_dir / _MANIFEST_FILENAME
            if not context.dry_run:
                manifest_path.write_text(
                    json.dumps(manifest, indent=2) + "\n",
                    encoding="utf-8",
                )

            context.logger.info(f"  pi DES extension installed: {extension_path}")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="pi DES extension installed successfully",
                installed_files=[extension_path],
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"pi DES extension installation failed: {e}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify the DES extension and manifest are present in the pi config dir.

        If pi is not detected, verification is skipped with success.
        """
        try:
            pi_dir = _pi_config_dir()

            if not pi_dir.exists():
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="pi not detected, verification skipped",
                )

            errors = []

            extension_path = pi_dir / _EXTENSION_FILENAME
            if not extension_path.exists():
                errors.append(f"pi DES extension not found: {extension_path}")

            manifest_path = pi_dir / _MANIFEST_FILENAME
            if not manifest_path.exists():
                errors.append(f"pi DES manifest not found: {manifest_path}")

            if errors:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=(
                        f"pi DES verification failed: {_EXTENSION_FILENAME} missing"
                    ),
                    errors=errors,
                )

            context.logger.info("  pi DES extension verified")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="pi DES extension verification passed",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"pi DES extension verification failed: {e}",
                errors=[str(e)],
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Remove the DES extension file and manifest.

        Only removes ``nwave-des.ts`` and the manifest. Operator files in the pi
        config dir are untouched.
        """
        try:
            pi_dir = _pi_config_dir()

            extension_path = pi_dir / _EXTENSION_FILENAME
            if extension_path.exists():
                extension_path.unlink()
                context.logger.info(f"  Removed pi DES extension: {extension_path}")

            manifest_path = pi_dir / _MANIFEST_FILENAME
            if manifest_path.exists():
                manifest_path.unlink()
                context.logger.info(f"  Removed pi DES manifest: {manifest_path}")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="pi DES extension uninstalled",
            )

        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"pi DES extension uninstall failed: {e}",
                errors=[str(e)],
            )

    def _find_template(self, context: InstallContext) -> Path | None:
        """Locate the TS extension template file.

        Checks ``framework_source/templates/`` first, then
        ``project_root/nWave/templates/``.
        """
        if context.framework_source:
            template = context.framework_source / "templates" / _TEMPLATE_FILENAME
            if template.exists():
                return template

        if context.project_root:
            template = context.project_root / "nWave" / "templates" / _TEMPLATE_FILENAME
            if template.exists():
                return template

        return None
