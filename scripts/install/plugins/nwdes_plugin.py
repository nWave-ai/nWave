"""Probe the installed nwdes command without installing host-owned assets."""

import subprocess
import sys

from .base import InstallationPlugin, InstallContext, PluginResult


class NwdesPlugin(InstallationPlugin):
    def __init__(self, interpreter: str = sys.executable):
        super().__init__(name="nwdes", priority=100)
        self.interpreter = interpreter

    def install(self, context: InstallContext) -> PluginResult:
        return self._probe()

    def _probe(self) -> PluginResult:
        command = [self.interpreter, "-m", "nwdes", "--help"]
        try:
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                timeout=10,
                capture_output=True,
                text=True,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            stderr = error.stderr or ""
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            detail = f" stderr: {stderr.rstrip()}" if stderr.rstrip() else ""
            message = (
                f"WHAT: {' '.join(command)} timed out after 10 s.\n"
                f"WHY: The probe did not finish within 10 seconds.{detail}\n"
                "HOW: Run the installer with an interpreter that can complete nwdes --help."
            )
            return PluginResult(False, self.name, message, errors=[message])
        except OSError as error:
            message = (
                f"WHAT: {' '.join(command)} could not start.\n"
                f"WHY: The interpreter could not be started: {error}.\n"
                "HOW: Run the installer with an interpreter that exists and has nwdes installed."
            )
            return PluginResult(False, self.name, message, errors=[message])
        if result.returncode == 0:
            return PluginResult(success=True, plugin_name=self.name)
        detail = f" stderr: {result.stderr.rstrip()}" if result.stderr.rstrip() else ""
        message = (
            f"WHAT: {' '.join(command)} exited {result.returncode}.\n"
            f"WHY: nwdes --help failed under this interpreter.{detail}\n"
            "HOW: Run the installer with an interpreter that has nwdes installed."
        )
        return PluginResult(False, self.name, message, errors=[message])

    def verify(self, context: InstallContext) -> PluginResult:
        return self._probe()
