"""Installer plugin for Amp (ampcode.com): places the nWave guard plugin where Amp loads it.

Amp loads every ``.ts`` file placed directly in its system plugins directory, ``$XDG_CONFIG_HOME/amp/plugins`` or
``~/.config/amp/plugins``. This plugin renders ``nWave/templates/amp-nwave-hooks-plugin.ts.template`` with the resolved
interpreter and the nWave runtime (the shared core in ``guard_extension``), writes it as ``nwave-hooks.ts`` there, and
records the sha256 of its bytes in the manifest. The rendered plugin decides nothing: every verdict is the kept
guard's, run as ``nwave_ai.hooks PreToolUse --host amp``.

The collision, probe and manifest rules are the pi guard's (``pi_guard_plugin``); only the directory, the template and
the messages differ. The manifest is written before the plugin file, so a crash between the two leaves a state the next
install accepts.
"""

from __future__ import annotations

import json

from nwave_ai.rendered_bytes import owns_digest
from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.guard_extension import (
    EXTENSION_NAME,
    MANIFEST_NAME,
    extension_bytes,
    manifest_text,
    render_guard_extension,
)
from scripts.install.plugins.pi_guard_plugin import PiGuardExtensionPlugin
from scripts.shared.install_paths import (
    amp_plugins_dir,
    hook_interpreter_warning,
    resolve_python_command_for_spawn,
    resolve_python_path_for_shell,
)


TEMPLATE_NAME = "amp-nwave-hooks-plugin.ts.template"


class AmpGuardPlugin(InstallationPlugin):
    """Installs the nWave guard plugin into Amp's system plugins directory."""

    def __init__(self) -> None:
        super().__init__(name="amp-guard-plugin", priority=55)

    def install(self, context: InstallContext) -> PluginResult:
        directory = amp_plugins_dir()
        shim = directory / EXTENSION_NAME
        manifest = directory / MANIFEST_NAME
        if directory.is_symlink() or shim.is_symlink() or manifest.is_symlink():
            return self._refuse(
                f"WHAT: {directory} or one of its nWave files is a symlink. "
                "WHY: nWave writes only real files it owns, and a symlink can point outside the Amp plugins directory. "
                "HOW: replace the symlink with a real directory or file, or remove it yourself, then rerun the installer."
            )
        if shim.exists() and not manifest.is_file():
            return self._refuse(
                f"WHAT: {shim} exists and no nWave manifest owns it. "
                "WHY: nWave will not overwrite a file it did not write, because that would destroy the operator's own plugin. "
                f"HOW: move {shim} aside or remove it yourself, then rerun the installer so nWave writes its own copy."
            )
        template_path = context.framework_source / "templates" / TEMPLATE_NAME
        if not template_path.is_file():
            template_path = context.project_root / "nWave/templates" / TEMPLATE_NAME
        if not template_path.is_file():
            return self._refuse(
                f"WHAT: the Amp guard template {TEMPLATE_NAME} is missing. "
                "WHY: the installer renders the guard plugin from this shipped template. "
                "HOW: restore nWave/templates/ from the nWave package and rerun the installer."
            )
        python = resolve_python_command_for_spawn()
        warning = hook_interpreter_warning(resolve_python_path_for_shell())
        if warning is not None:
            context.logger.warn_once(warning)
        runtime = PiGuardExtensionPlugin._runtime_root()
        probe_failure = PiGuardExtensionPlugin._probe_runtime(python, runtime)
        if probe_failure is not None:
            return self._refuse(probe_failure)
        rendered = render_guard_extension(
            template_path.read_text(encoding="utf-8"), python, runtime
        )
        if not context.dry_run:
            directory.mkdir(parents=True, exist_ok=True)
            manifest.write_text(manifest_text(rendered), encoding="utf-8")
            shim.write_bytes(extension_bytes(rendered))
        verb = "Would install" if context.dry_run else "Installed"
        message = f"{verb} Amp nWave guard plugin at {shim}; Python: {python}; runtime: {runtime}."
        context.logger.info(message)
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=message,
            installed_files=[shim],
        )

    def verify(self, context: InstallContext) -> PluginResult:
        directory = amp_plugins_dir()
        shim = directory / EXTENSION_NAME
        manifest = directory / MANIFEST_NAME
        if not shim.is_file() or not manifest.is_file():
            return self._refuse(
                f"WHAT: the Amp nWave guard plugin at {shim} or its manifest is missing. "
                "WHY: Amp cannot run the nWave guard without its plugin file. "
                "HOW: run the installer with --platform amp to write both files."
            )
        try:
            recorded = json.loads(manifest.read_text(encoding="utf-8")).get("sha256")
        except (OSError, ValueError):
            return self._refuse(
                f"WHAT: the manifest {manifest} cannot be read as JSON. "
                "WHY: nWave cannot tell its plugin from a foreign one without a readable manifest. "
                "HOW: delete the manifest and rerun the installer with --platform amp."
            )
        if not owns_digest(
            shim.read_bytes(), recorded if isinstance(recorded, str) else None
        ):
            return self._refuse(
                f"WHAT: {shim} does not match the digest its manifest records. "
                "WHY: the plugin was edited or replaced after nWave wrote it. "
                "HOW: rerun the installer with --platform amp to restore nWave's copy."
            )
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=f"Amp nWave guard plugin verified at {shim}",
        )

    def _refuse(self, message: str) -> PluginResult:
        return PluginResult(False, self.name, message, errors=[message])
