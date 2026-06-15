"""Package manager detector - identifies which PM owns a Python executable.

Single source of truth for package-manager identity, shared by two callers so
they never disagree about which toolchain owns nwave-ai:

- ``/nw-update`` self-update flow — records the PM backend before
  ``PendingUpdateService.request_update()``.
- ``nwave-ai plugin install`` (``nwave_ai.cli._resolve_installer``) — picks
  the installer for tool plugins.

Resolution order:
1. ``NWAVE_INSTALLER`` env override (``uv`` / ``pipx`` / ``pip``) — explicit
   user choice, honored in BOTH callers so the override can never be obeyed by
   one path and ignored by the other.
2. ``uv tool dir`` prefix match (authoritative for uv; survives a custom
   ``UV_TOOL_DIR``).
3. ``/uv/tools/`` substring (fallback when the probe can't run, e.g. uv not on
   PATH at detection time but the executable still lives under its tools dir).
4. ``/pipx/venvs/`` substring.
5. ``unknown``.

pip-installed packages have no PM-specific path marker, so ``pip`` is reported
only via the override; an unmarked pip install resolves to ``unknown``.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Literal


PMBackend = Literal["pipx", "uv", "pip", "unknown"]

# Environment variable that lets a user force the installer when auto-detection
# would pick the wrong one (e.g. both uv and pipx present, or a custom
# UV_TOOL_DIR that the path heuristics miss).
OVERRIDE_ENV_VAR = "NWAVE_INSTALLER"
_VALID_OVERRIDES: frozenset[str] = frozenset({"uv", "pipx", "pip"})


def _override_pm() -> PMBackend | None:
    """Return the PM forced via ``NWAVE_INSTALLER``, or None if unset/invalid."""
    override = os.environ.get(OVERRIDE_ENV_VAR, "").strip().lower()
    if override in _VALID_OVERRIDES:
        return override  # type: ignore[return-value]
    return None


def _probe_uv_tool_dir() -> Path | None:
    """Return the directory reported by `uv tool dir`, or None on any failure."""
    try:
        output = subprocess.check_output(["uv", "tool", "dir"], text=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    stripped = output.strip()
    if not stripped:
        return None
    return Path(stripped)


def _is_under(path: Path, ancestor: Path) -> bool:
    try:
        path.relative_to(ancestor)
    except ValueError:
        return False
    return True


def detect_pm(executable: Path) -> PMBackend:
    """Identify the package manager that owns ``executable``.

    Args:
        executable: absolute path to the Python interpreter of the installed package.

    Returns:
        ``"uv"``, ``"pipx"``, or ``"pip"`` per the resolution order documented
        at module level; ``"unknown"`` when no signal identifies a manager.
    """
    override = _override_pm()
    if override is not None:
        return override

    uv_root = _probe_uv_tool_dir()
    if uv_root is not None and _is_under(executable, uv_root):
        return "uv"

    exe = str(executable).replace("\\", "/")
    if "/uv/tools/" in exe:
        return "uv"
    if "/pipx/venvs/" in exe:
        return "pipx"
    return "unknown"


def resolve_nwave_pm(recorded_pm: str | None, executable: Path) -> PMBackend:
    """Resolve the PM that owns the nwave-ai install for an arbitrary caller.

    ``detect_pm(sys.executable)`` is only correct when called from inside the
    nwave-ai process. Callers running under an unrelated interpreter -- notably
    the ``/nw-update`` skill, which shells out via ambient ``python3`` -- would
    otherwise inspect the wrong interpreter and get ``unknown``. They pass the
    value the installer recorded at install time instead.

    Order of authority:
    1. ``NWAVE_INSTALLER`` override -- explicit user choice always wins.
    2. ``recorded_pm`` -- captured by the installer from its OWN interpreter at
       install time, when path detection is reliable. Trusted ahead of live
       detection precisely because the caller's interpreter may be unrelated.
    3. ``detect_pm(executable)`` -- path heuristics as a last resort (covers
       installs predating PM recording).

    Args:
        recorded_pm: PM persisted at install time (``uv``/``pipx``/``pip``), or
            None/``unknown`` when unrecorded.
        executable: interpreter to fall back to for path-based detection.
    """
    override = _override_pm()
    if override is not None:
        return override
    if recorded_pm in ("uv", "pipx", "pip"):
        return recorded_pm  # type: ignore[return-value]
    return detect_pm(executable)
