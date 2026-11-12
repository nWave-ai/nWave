"""Installer plugin for the pi.dev host: places the nWave guard extension where pi loads it.

pi (@earendil-works/pi-coding-agent, pi 1.5.2 docs) auto-loads ``*.ts`` extensions from
``<agent dir>/extensions/``. This plugin renders ``nWave/templates/pi-nwave-hooks-extension.ts.template``
with the resolved interpreter and the nWave runtime (the shared core in ``guard_extension``), writes it as
``nwave-hooks.ts`` there, and records the sha256 of its bytes in the manifest. The rendered extension decides
nothing: every verdict is the kept guard's, run as ``nwave_ai.hooks PreToolUse --host pi``.

Effect shell: ``PiGuardExtensionPlugin``. Contract shape: bounded change; the declared mutation set is the
extension file and its manifest in the pi extensions directory. The manifest is written before the extension,
so a crash between the two leaves a state the next install accepts (the extension path is not yet nWave's).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.guard_extension import (
    EXTENSION_NAME,
    MANIFEST_NAME,
    manifest_text,
    render_guard_extension,
)
from scripts.shared.install_paths import (
    pi_extensions_dir,
    resolve_python_command_for_spawn,
)


TEMPLATE_NAME = "pi-nwave-hooks-extension.ts.template"


class PiGuardExtensionPlugin(InstallationPlugin):
    """Installs the nWave guard extension into the pi extensions directory."""

    def __init__(self) -> None:
        super().__init__(name="pi-guard-extension", priority=55)

    def install(self, context: InstallContext) -> PluginResult:
        directory = pi_extensions_dir()
        shim = directory / EXTENSION_NAME
        manifest = directory / MANIFEST_NAME
        if directory.is_symlink() or shim.is_symlink() or manifest.is_symlink():
            return self._refuse(
                f"WHAT: {directory} or one of its nWave files is a symlink. "
                "WHY: nWave writes only real files it owns, and a symlink can point outside the pi agent directory. "
                "HOW: replace the symlink with a real directory or file, or remove it yourself, then rerun the installer."
            )
        if shim.exists() and not manifest.is_file():
            return self._refuse(
                f"WHAT: {shim} exists and no nWave manifest owns it. "
                "WHY: nWave will not overwrite a file it did not write, because that would destroy the operator's own extension. "
                f"HOW: move {shim} aside or remove it yourself, then rerun the installer so nWave writes its own copy."
            )
        template_path = context.framework_source / "templates" / TEMPLATE_NAME
        if not template_path.is_file():
            template_path = context.project_root / "nWave/templates" / TEMPLATE_NAME
        if not template_path.is_file():
            return self._refuse(
                f"WHAT: the pi guard template {TEMPLATE_NAME} is missing. "
                "WHY: the installer renders the guard extension from this shipped template. "
                "HOW: restore nWave/templates/ from the nWave package and rerun the installer."
            )
        python = resolve_python_command_for_spawn()
        runtime = self._runtime_root()
        probe_failure = self._probe_runtime(python, runtime)
        if probe_failure is not None:
            return self._refuse(probe_failure)
        rendered = render_guard_extension(
            template_path.read_text(encoding="utf-8"), python, runtime
        )
        if not context.dry_run:
            directory.mkdir(parents=True, exist_ok=True)
            manifest.write_text(manifest_text(rendered), encoding="utf-8")
            shim.write_text(rendered, encoding="utf-8")
        verb = "Would install" if context.dry_run else "Installed"
        message = f"{verb} pi nWave guard extension at {shim}; Python: {python}; runtime: {runtime}."
        context.logger.info(message)
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=message,
            installed_files=[shim],
        )

    def verify(self, context: InstallContext) -> PluginResult:
        directory = pi_extensions_dir()
        shim = directory / EXTENSION_NAME
        manifest = directory / MANIFEST_NAME
        if not shim.is_file() or not manifest.is_file():
            return self._refuse(
                f"WHAT: the pi nWave guard extension at {shim} or its manifest is missing. "
                "WHY: pi cannot run the nWave guard without its extension file. "
                "HOW: run the installer with --platform pi to write both files."
            )
        try:
            recorded = json.loads(manifest.read_text(encoding="utf-8")).get("sha256")
        except (OSError, ValueError):
            return self._refuse(
                f"WHAT: the manifest {manifest} cannot be read as JSON. "
                "WHY: nWave cannot tell its extension from a foreign one without a readable manifest. "
                "HOW: delete the manifest and rerun the installer with --platform pi."
            )
        actual = hashlib.sha256(shim.read_bytes()).hexdigest()
        if recorded != actual:
            return self._refuse(
                f"WHAT: {shim} does not match the digest its manifest records. "
                "WHY: the extension was edited or replaced after nWave wrote it. "
                "HOW: rerun the installer with --platform pi to restore nWave's copy."
            )
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=f"pi nWave guard extension verified at {shim}",
        )

    def _refuse(self, message: str) -> PluginResult:
        return PluginResult(False, self.name, message, errors=[message])

    @staticmethod
    def _runtime_root() -> str:
        import nwave_ai

        return str(Path(nwave_ai.__file__).resolve().parent.parent)

    @staticmethod
    def _probe_runtime(python: str, runtime: str) -> str | None:
        """Return a WHAT WHY HOW message when the interpreter cannot import the kept guard, else None."""
        try:
            probe = subprocess.run(
                [python, "-c", "import nwave_ai.hooks"],
                env={**os.environ, "PYTHONPATH": runtime},
                cwd=Path.home(),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return (
                f"WHAT: the interpreter {python} could not run the nWave guard probe. "
                f"WHY: {error}. "
                "HOW: install Python 3.11 or newer, put it on PATH, and rerun the installer with that interpreter."
            )
        if probe.returncode != 0:
            return (
                f"WHAT: nwave_ai.hooks import failed with PYTHONPATH={runtime}. "
                f"WHY: {probe.stderr.strip()}. "
                "HOW: rerun the installer with Python 3.11 or newer and its required dependencies installed."
            )
        return None
