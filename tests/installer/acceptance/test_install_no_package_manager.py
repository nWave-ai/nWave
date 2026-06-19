"""Guard (wtbd-44): `nwave-ai install` must never shell out to a package manager.

The framework install (`NWaveInstaller.install_framework`) provisions
`~/.claude` with pure file operations. It must NEVER invoke uv / pipx / pip as
a subprocess — doing so could silently switch toolchains mid-install, the exact
parallel-venv failure class the uv-first migration exists to prevent.

This is the behavioral counterpart to the resolver/self-update tests: those
prove the *deliberate* PM-picking paths choose correctly; this proves the
*provisioning* path never picks a PM at all. Strategy: spy every subprocess
entry point during a real install into an isolated CLAUDE_CONFIG_DIR and fail
if any package-manager command is invoked.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest


# Program names that would indicate the install path shelled out to a
# Python package manager. Matched against the basename of argv[0].
_PACKAGE_MANAGERS: frozenset[str] = frozenset(
    {"uv", "uvx", "pipx", "pip", "pip3", "pip3.10", "pip3.11", "pip3.12", "pip3.13"}
)


def _program_name(cmd: Any) -> str:
    """Extract the basename of the program a subprocess call would launch."""
    if isinstance(cmd, (list, tuple)) and cmd:
        prog = str(cmd[0])
    elif isinstance(cmd, str):
        parts = cmd.split()
        prog = parts[0] if parts else ""
    else:
        prog = ""
    return Path(prog).name


@pytest.fixture
def subprocess_spy(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Record every subprocess invocation while delegating to the real call."""
    recorded: list[Any] = []
    entry_points = ("run", "call", "check_call", "check_output", "Popen")
    originals = {name: getattr(subprocess, name) for name in entry_points}

    def make_spy(original):
        def spy(cmd, *args, **kwargs):
            recorded.append(cmd)
            return original(cmd, *args, **kwargs)

        return spy

    for name, original in originals.items():
        monkeypatch.setattr(subprocess, name, make_spy(original))
    return recorded


def test_install_framework_invokes_no_package_manager(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    subprocess_spy: list[Any],
) -> None:
    """A real framework install must record zero uv/pipx/pip subprocess calls."""
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / ".claude"))

    # Import after the env var is set so PathUtils resolves the isolated target.
    from scripts.install.install_nwave import NWaveInstaller

    installer = NWaveInstaller(dry_run=False)
    installer.install_framework()

    offenders = [
        cmd for cmd in subprocess_spy if _program_name(cmd) in _PACKAGE_MANAGERS
    ]
    assert not offenders, (
        "nwave-ai install shelled out to a package manager (forbidden — could "
        f"switch toolchains mid-install): {offenders}"
    )
