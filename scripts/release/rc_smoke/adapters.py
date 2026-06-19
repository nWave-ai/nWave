"""Real driven adapters for the rc_smoke harness.

These run ONLY in the ``validate-rc-multitool`` CI gate against real
TestPyPI / npm / third-party CLIs. The LOCAL acceptance suite uses the
in-memory fakes (see ``tests/release/rc_smoke/acceptance/steps/fakes.py``),
never these adapters — the real cross-OS install is the CI e2e contract
(SPIKE proved it empirically), not a dev-box test.

DESIGN reuse: ``SubprocessInstaller`` borrows the ``_run`` capture/print shape
from ``validate_published_rc_locally.py``; ``RealArtifactFileSystem`` composes
``installation_verifier.InstallationVerifier`` for the claude-code contract.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path

    from scripts.release.rc_smoke.contracts import ToolContract


# Bounded TestPyPI retry, mirroring the existing validate-rc install loop
# (index propagation lag on fresh pre-release uploads). 10 x 30s = 5 min.
_INSTALL_ATTEMPTS = 10
_INSTALL_RETRY_SECONDS = 30


@dataclass
class _InstallResult:
    """Concrete InstallResult (succeeded + diagnostic)."""

    succeeded: bool
    diagnostic: str = ""


@dataclass
class _ProcessResult:
    """Concrete ProcessResult (exit_code + stdout + stderr)."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command, capturing output (the validate_published_rc_locally shape).

    ALWAYS inherits the current environment — never a replacement ``env=``. On
    Windows, passing an explicit env block defeats ``CreateProcess``'s PATH/.exe
    resolution of bare console-script names (it surfaced as ``FileNotFoundError``
    on the selftest). Callers that need isolation mutate ``os.environ`` around
    the call instead (see ``provision_tool``).

    Resolves the executable via ``shutil.which`` so npm ``.cmd`` shims and uv
    ``.exe`` shims are found by extension; ``.cmd`` / ``.bat`` are routed through
    the command processor since ``CreateProcess`` cannot exec them directly.
    Falls back to the bare name (inherited PATH + ``.exe`` auto-append still
    resolves real ``.exe`` shims) so a genuine "not installed" error is real.
    """
    resolved = shutil.which(cmd[0]) or cmd[0]
    argv = [resolved, *cmd[1:]]
    if os.name == "nt" and resolved.lower().endswith((".cmd", ".bat")):
        argv = ["cmd", "/c", *argv]
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(argv, check=False, capture_output=True, text=True)


class SubprocessInstaller:
    """Real uv/pipx install of published nwave-ai + ``nwave-ai install``."""

    def __init__(self, installer: str) -> None:
        if installer not in ("uv", "pipx"):
            raise ValueError(f"unsupported installer {installer!r} (uv | pipx)")
        self._installer = installer

    def install_published_nwave(self, version: str, venv: Path) -> _InstallResult:
        """Install published ``nwave-ai==version`` from TestPyPI, with retry."""
        cmd = self._install_command(version)
        last = ""
        for attempt in range(1, _INSTALL_ATTEMPTS + 1):
            result = _run(cmd)
            if result.returncode == 0:
                return _InstallResult(True)
            last = result.stderr[-2000:]
            print(
                f"::warning::{self._installer} install attempt {attempt} failed, "
                f"retrying in {_INSTALL_RETRY_SECONDS}s...",
                file=sys.stderr,
            )
            if attempt < _INSTALL_ATTEMPTS:
                time.sleep(_INSTALL_RETRY_SECONDS)
        return _InstallResult(
            False,
            f"install of nwave-ai=={version} via {self._installer} failed: {last}",
        )

    def provision_tool(self, contract: ToolContract, target: Path) -> _InstallResult:
        """Run ``nwave-ai install --platform <tool> --yes`` isolated via env var.

        Isolation is the per-tool config env var (CLAUDE_CONFIG_DIR / CODEX_HOME
        / OPENCODE_CONFIG_DIR), NOT a ``--target`` flag: the published installer
        does not accept ``--target`` on its install path (it is forwarded to
        ``install_nwave.py``, which rejects it), and ``--target`` is an
        unreleased CLI feature. The env var is the mechanism the installer
        actually reads (ADR-001) and works on Windows where ``$HOME`` is ignored
        by ``Path.home()``. See ADR-PLAT-007 D-6 (revised 2026-06-08).
        """
        cmd = [
            "nwave-ai",
            "install",
            "--platform",
            contract.tool_id,
            "--yes",
        ]
        previous = os.environ.get(contract.isolation_env_var)
        os.environ[contract.isolation_env_var] = str(target)
        try:
            result = _run(cmd)
        finally:
            if previous is None:
                os.environ.pop(contract.isolation_env_var, None)
            else:
                os.environ[contract.isolation_env_var] = previous
        if result.returncode == 0:
            return _InstallResult(True)
        return _InstallResult(
            False,
            f"nwave-ai install --platform {contract.tool_id} failed "
            f"(exit {result.returncode}): {result.stderr[-2000:]}",
        )

    def _install_command(self, version: str) -> list[str]:
        pkg = f"nwave-ai=={version}"
        if self._installer == "uv":
            return [
                "uv",
                "tool",
                "install",
                "--index",
                "https://test.pypi.org/simple/",
                "--index",
                "https://pypi.org/simple/",
                "--index-strategy",
                "unsafe-best-match",
                pkg,
            ]
        return [
            "pipx",
            "install",
            "--pip-args=--pre --index-url https://test.pypi.org/simple/ "
            "--extra-index-url https://pypi.org/simple/",
            pkg,
        ]


class SubprocessRunner:
    """Real ``subprocess.run`` of the tool's version flag (no model call)."""

    def boot(self, contract: ToolContract) -> _ProcessResult:
        cmd = list(contract.boot_argv)
        try:
            result = _run(cmd)
        except FileNotFoundError as exc:
            return _ProcessResult(127, "", f"{contract.tool_id} not on PATH: {exc}")
        return _ProcessResult(result.returncode, result.stdout, result.stderr)


class RealArtifactFileSystem:
    """Real glob/exists over the isolated target (real nWave files).

    For the claude-code contract, composes ``InstallationVerifier`` to assert
    the full Claude layout (agents/nw, skills, manifest, DES) — not bare dirs.
    For the other tools, globs the contract's ``required_artifact_globs``
    directly under the isolated target.
    """

    def missing_artifacts(
        self, contract: ToolContract, target: Path
    ) -> tuple[str, ...]:
        if contract.tool_id == "claude-code":
            verifier_missing = self._claude_verifier_gaps(target)
            if verifier_missing:
                return verifier_missing
        return self._missing_globs(contract, target)

    def _claude_verifier_gaps(self, target: Path) -> tuple[str, ...]:
        """Run InstallationVerifier against the isolated Claude config dir."""
        from scripts.install.installation_verifier import InstallationVerifier

        previous = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = str(target)
        try:
            result = InstallationVerifier(claude_config_dir=target).run_verification()
        finally:
            if previous is None:
                os.environ.pop("CLAUDE_CONFIG_DIR", None)
            else:
                os.environ["CLAUDE_CONFIG_DIR"] = previous
        if result.success:
            return ()
        return (result.message,)

    def _missing_globs(self, contract: ToolContract, target: Path) -> tuple[str, ...]:
        """Return required globs that match NOTHING under the isolated target."""
        return tuple(
            glob
            for glob in contract.required_artifact_globs
            if not any(target.glob(glob))
        )
