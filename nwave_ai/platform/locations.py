"""The one location result every nWave write/read destination shares.

Three independent ordered override channels -- ``NWAVE_AGENTS_HOME``,
``CLAUDE_CONFIG_DIR``, ``CODEX_HOME`` -- each name a root that may be
absent, empty, absolute or relative. Before this module the installer
(``scripts/install/install_nwave.py``) re-read the ambient environment at
five separate call sites and the status reader
(``nwave_ai.platform.config.NWaveConfig``) read a FOURTH,
frozen-at-import snapshot of ``Path.home()`` -- so a write destination and
a read destination could silently disagree whenever ``NWAVE_AGENTS_HOME``
diverged from ``HOME``, and no call site ever refused a relative override
before a write. :func:`NWaveLocations.resolve` is the single pure
function every one of those call sites now reads from.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from nwave_ai.platform.result import Failure, Result, Success


@dataclass(frozen=True)
class NWaveLocations:
    """The three install-destination roots one invocation must agree on."""

    agents_home: Path
    claude_config_dir: Path
    codex_config_dir: Path

    @staticmethod
    def resolve(
        home: Path,
        repo_root: Path,
        agents_home_override: str | None,
        claude_config_override: str | None,
        codex_config_override: str | None,
    ) -> Result[NWaveLocations, str]:
        """Resolve one location result from the three override channels.

        Total and pure: never stats, creates or touches a directory, and
        never raises -- a caller wanting refusal-before-write (the
        installer's construction-time obligation) inspects the returned
        :class:`~nwave_ai.platform.result.Failure` and raises itself; a caller
        content to degrade (a read-only status loader) unwraps with a
        fallback instead.

        Per channel, applying the SAME rule: an absent or empty override is
        absent (native root under ``home``); an absolute override is a
        valid root; a relative override never becomes a root -- this
        returns a :class:`~nwave_ai.platform.result.Failure` naming the offending
        channel and value, rather than silently joining it under ``home``,
        ``repo_root``, or any other ambient directory. ``repo_root`` is
        accepted for the caller's own provenance and is never itself
        consulted to normalize a relative override -- refusal is
        unconditional, never cwd-relative or repo-relative.
        """
        del repo_root  # never joined onto a relative override; see docstring.

        agents_home_result = _resolve_channel(
            "NWAVE_AGENTS_HOME", home, agents_home_override
        )
        if isinstance(agents_home_result, Failure):
            return agents_home_result

        claude_config_result = _resolve_channel(
            "CLAUDE_CONFIG_DIR", home / ".claude", claude_config_override
        )
        if isinstance(claude_config_result, Failure):
            return claude_config_result

        codex_config_result = _resolve_channel(
            "CODEX_HOME", home / ".codex", codex_config_override
        )
        if isinstance(codex_config_result, Failure):
            return codex_config_result

        return Success(
            NWaveLocations(
                agents_home=agents_home_result.unwrap(),
                claude_config_dir=claude_config_result.unwrap(),
                codex_config_dir=codex_config_result.unwrap(),
            )
        )


def _resolve_channel(
    channel_name: str, default_root: Path, override: str | None
) -> Result[Path, str]:
    """Resolve one override channel: absent/empty -> default; absolute -> as-is;
    relative -> refusal.
    """
    if not override:
        return Success(default_root)
    candidate = Path(override)
    if not candidate.is_absolute():
        return Failure(
            f"{channel_name}={override!r} is a relative path -- refused: "
            "an override root must be absolute, never silently joined "
            "under an ambient directory."
        )
    return Success(candidate)


def resolve_nwave_root() -> Path:
    """Return the active `.nwave` root for the current process.

    Prefer the ``DES_PROJECT_DIR`` env override (the per-test tmp dir the isolation
    fixture sets) over the shared repo ``Path.cwd()``, so each test resolves a
    per-test isolated `.nwave` root. With no override the shared repo cwd is the
    layout-independent fallback (the un-isolated status).
    """
    override = os.environ.get("DES_PROJECT_DIR")
    if override:
        return Path(override)
    return Path.cwd()


def resolve_repo_root(override: str | None) -> Path:
    """Resolve the repo root: an explicit override, a non-empty NWAVE_REPO_ROOT, then cwd."""
    if override:
        return Path(override)
    env = os.environ.get("NWAVE_REPO_ROOT")
    if env:
        return Path(env)
    return Path.cwd()
