"""Install the kept nWave hook registrations into each selected host's hook file.

nwave_ai.hooks.registration is the single definition of the kept entries, their command
and their merge rule. This plugin is the filesystem shell around it: it resolves each
host's hook file, refuses a non-durable interpreter, writes compare-and-swap (a file is
replaced only while its bytes are unchanged since they were read) and verifies that the
kept entries are present. It is not registered in install_nwave.py: that cutover belongs
to slice S5.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from nwave_ai.hooks.registration import HOOK_FILE, interpreter_for_shell, merge
from nwave_ai.upgrade_shell import (
    Changed,
    Occupied,
    copilot_config_dir,
    cursor_config_dir,
    real_port,
)
from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.shared.install_paths import codex_config_dir, is_durable_interpreter_path


_PLATFORM_HOST = {
    "claude_code": "claude",
    "codex": "codex",
    "cursor": "cursor",
    "copilot": "copilot",
}


class HooksPlugin(InstallationPlugin):
    """Writes the kept registrations for each selected host and verifies them."""

    def __init__(self, interpreter: str | None = None, *, windows: bool | None = None):
        super().__init__(name="nwave-hooks", priority=110)
        self._interpreter = interpreter
        self._windows = os.name == "nt" if windows is None else windows

    @property
    def native_interpreter(self) -> str:
        return str(Path(self._interpreter or sys.executable).absolute())

    @property
    def interpreter(self) -> str:
        return interpreter_for_shell(self.native_interpreter, windows=self._windows)

    def _targets(self, context: InstallContext) -> list[tuple[str, Path]]:
        home = Path.home()
        codex_dir = (
            context.locations.codex_config_dir
            if context.locations is not None
            else codex_config_dir()
        )
        directories = {
            "claude": context.claude_dir,
            "codex": codex_dir,
            "cursor": cursor_config_dir(home),
            "copilot": copilot_config_dir(home),
        }
        return [
            (host, directories[host] / HOOK_FILE[host])
            for platform, host in sorted(_PLATFORM_HOST.items())
            if platform in context.target_platforms
        ]

    def install(self, context: InstallContext) -> PluginResult:
        interpreter = self.interpreter
        native = self.native_interpreter
        if not is_durable_interpreter_path(native):
            message = (
                f"WHAT: kept nWave hooks not written. WHY: interpreter {native} "
                "is not durable (temporary or ephemeral). HOW: rerun the installer "
                "with a durable Python interpreter."
            )
            return PluginResult(
                success=False, plugin_name=self.name, message=message, errors=[message]
            )
        port = real_port()
        installed: list[Path] = []
        for host, path in self._targets(context):
            try:
                before = path.read_bytes() if path.is_file() else None
                document = (
                    json.loads(before.decode("utf-8")) if before is not None else {}
                )
                if not isinstance(document, dict):
                    raise ValueError("top level is not a JSON object")
                after = (
                    json.dumps(merge(document, host, interpreter), indent=2) + "\n"
                ).encode("utf-8")
                if context.dry_run:
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                if before is None:
                    outcome = port.write_new(str(path), after)
                else:
                    outcome = port.replace_if_unchanged(str(path), before, after)
            except (OSError, ValueError) as error:
                message = (
                    f"WHAT: kept nWave hooks not written into {path}. WHY: {error}. "
                    "HOW: repair the file and rerun the installer."
                )
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=message,
                    errors=[message],
                )
            if isinstance(outcome, (Changed, Occupied)):
                message = (
                    f"WHAT: {path} changed while nWave wrote kept hooks. WHY: another "
                    "writer holds the file. HOW: rerun the installer."
                )
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=message,
                    errors=[message],
                )
            installed.append(path)
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=f"kept nWave hooks written for {len(installed)} host file(s)",
            installed_files=installed,
        )

    def verify(self, context: InstallContext) -> PluginResult:
        interpreter = self.interpreter
        for host, path in self._targets(context):
            try:
                if not path.is_file():
                    raise FileNotFoundError(str(path))
                document = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(document, dict):
                    raise ValueError("top level is not a JSON object")
                if merge(document, host, interpreter) != document:
                    raise ValueError("kept nWave hooks missing or stale")
            except (OSError, ValueError) as error:
                message = (
                    f"WHAT: kept nWave hooks not verified in {path}. WHY: {error}. "
                    "HOW: rerun the installer."
                )
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=message,
                    errors=[message],
                )
        return PluginResult(success=True, plugin_name=self.name)
