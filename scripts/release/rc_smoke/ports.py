"""Driven-port Protocols — the harness's hexagonal boundary (DISTILL scaffold).

These are typing.Protocol interfaces, not behaviour, so they need no scaffold
marker assertions: the RED behaviour lives in the real adapters (adapters.py)
and the SmokeRunner (runner.py). Fakes for the acceptance suite implement
these same Protocols (Pillar 3 / Mandate 10 shared-interface contract).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol


if TYPE_CHECKING:
    from pathlib import Path

    from scripts.release.rc_smoke.contracts import ToolContract


class InstallResult(Protocol):
    """Outcome of an install attempt."""

    succeeded: bool
    diagnostic: str


class InstallerPort(Protocol):
    """Installs the published nwave-ai and provisions a tool layout."""

    def install_published_nwave(self, version: str, venv: Path) -> InstallResult:
        """Install the published ``nwave-ai`` (TestPyPI, via uv/pipx) into venv."""
        ...

    def provision_tool(self, contract: ToolContract, target: Path) -> InstallResult:
        """Run ``nwave-ai install --platform <tool> --target <isolated>``."""
        ...


class ProcessResult(Protocol):
    """Outcome of a subprocess boot."""

    exit_code: int
    stdout: str
    stderr: str


class ProcessPort(Protocol):
    """Boots the tool via its version flag (no model call)."""

    def boot(self, contract: ToolContract) -> ProcessResult:
        """Run the tool's ``boot_argv``; capture exit/stdout/stderr."""
        ...


class FileSystemPort(Protocol):
    """Asserts REAL provisioned artifacts exist under the isolated target."""

    def missing_artifacts(
        self, contract: ToolContract, target: Path
    ) -> tuple[str, ...]:
        """Return globs from ``required_artifact_globs`` matching NOTHING.

        Empty tuple == every required artifact is present. A non-empty tuple
        is the readable diagnostic of what provisioning failed to write.
        """
        ...
