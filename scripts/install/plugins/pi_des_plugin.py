"""Plugin for installing the nWave DES TypeScript extension into the pi agent.

RED scaffold (created by DISTILL, ADR-025 / Mandate 7). The real implementation
is written by DELIVER. Until then every lifecycle method raises AssertionError so
acceptance tests classify as RED (implementation missing), never BROKEN
(import/collection error).

Mirrors `opencode_des_plugin.py` (the closest analog — a TS file rendered from a
template into a harness config dir; ADR-PI-002 / D11). pi extensions are loaded
from a pi config dir; the plugin renders `nWave/templates/pi-des-extension.ts.template`
(placeholders -> resolved python + DES lib via `install_paths` resolvers) into that
dir, places the single crafter skill (ADR-PI-003 / D9), and writes
`.nwave-des-manifest.json` for clean uninstall.

Contract shape: bounded-change. Declared mutation set = rendered extension file,
crafter skill file, manifest. The plugin owns no enforcement logic.
"""

from __future__ import annotations

import os
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)


__SCAFFOLD__ = True

_EXTENSION_FILENAME = "nwave-des.ts"
_MANIFEST_FILENAME = ".nwave-des-manifest.json"
_TEMPLATE_FILENAME = "pi-des-extension.ts.template"

_SCAFFOLD_MSG = "Not yet implemented -- RED scaffold (DISTILL); DELIVER writes this"


def _pi_config_dir() -> Path:
    """Return the pi configuration directory.

    Honors the ``PI_CONFIG_DIR`` env override (used by acceptance tests against a
    tmp dir); otherwise the assumed pi location (R1, confirmed in DELIVER/DEVOPS).
    """
    override = os.environ.get("PI_CONFIG_DIR")
    return Path(override) if override else Path.home() / ".pi" / "agent"


class PiDESPlugin(InstallationPlugin):
    """Installs the nWave DES TS extension + crafter skill into the pi agent."""

    def __init__(self) -> None:
        super().__init__(name="pi-des", priority=55)
        self.dependencies = ["des"]

    def validate_prerequisites(self, context: InstallContext) -> PluginResult:
        raise AssertionError(_SCAFFOLD_MSG)

    def install(self, context: InstallContext) -> PluginResult:
        raise AssertionError(_SCAFFOLD_MSG)

    def verify(self, context: InstallContext) -> PluginResult:
        raise AssertionError(_SCAFFOLD_MSG)

    def uninstall(self, context: InstallContext) -> PluginResult:
        raise AssertionError(_SCAFFOLD_MSG)
