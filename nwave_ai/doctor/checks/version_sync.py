"""VersionSyncCheck — detects an upgraded package whose framework was not reinstalled.

The ``nwave-ai`` package and the deployed nWave framework are kept in lock-step by
``nwave-ai install``: every install records the package version that performed it
into ``~/.nwave/global-config.json`` (``install.installed_version``). When a
package manager later upgrades ``nwave-ai`` (``pipx upgrade`` / ``uv tool upgrade``)
but the user forgets to re-run ``nwave-ai install``, the live package version
drifts ahead of the deployed framework assets — silently, with confusing
behaviour and no signal. This check surfaces that drift.

The two public version *tracks* (the ``nwave-ai`` wheel vs. ``nWave/VERSION``) are
NOT directly comparable, so the check never compares those. It compares the live
package version against the package version *recorded at the last install* — both
the same value type, captured from the same interpreter.

Fail-open by construction: when either side cannot be determined (no recorded
version, package metadata absent, or a ``0.0.0`` sentinel) the check PASSES. An
install-health check that nags on an undeterminable-but-healthy state is worse
than silence.

Mechanism (the load-bearing assumption): ``pipx upgrade`` / ``uv tool upgrade``
mutate the package *in place* inside the existing tool venv, so the interpreter
path baked into ``settings.json`` at the last install still launches that venv
and ``importlib.metadata`` reads the *upgraded* version — which is exactly the
asymmetry this check relies on (live version moves, recorded version does not).
The rare exception is an extraordinary venv recreation (e.g. a Python minor-
version bump that forces ``pipx reinstall``): the baked interpreter path can go
stale, the hook fails to launch, and ``substrate_probe`` returns "" — no
advisory. That degraded path is silent-but-safe and consistent with the fail-
open contract; a subsequent ``nwave-ai install`` repairs both the path and the
recorded version.
"""

from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from typing import TYPE_CHECKING

from nwave_ai.common.check_result import CheckResult


if TYPE_CHECKING:
    from pathlib import Path

    from nwave_ai.doctor.context import DoctorContext


# A recorded/detected "0.0.0" means "unknown", not a real release — treat as
# undeterminable so the check never false-alarms on it.
_UNKNOWN_VERSION = "0.0.0"


def _detect_running_version() -> str | None:
    """Return the live installed ``nwave-ai`` version, or None when unavailable.

    Runs under the same interpreter as the hook/CLI (the pipx/uv tool venv),
    so this reflects the *currently active* package — which is exactly the value
    that drifts ahead of the deployed framework after an un-reinstalled upgrade.
    """
    try:
        return _pkg_version("nwave-ai")
    except PackageNotFoundError:
        return None


def _read_recorded_version(global_config_path: Path) -> str | None:
    """Read ``install.installed_version`` from the global config, or None.

    Returns None on any of: file absent, unreadable, non-JSON, non-dict shape,
    or the key missing — every one of which means "cannot determine".
    """
    try:
        raw = global_config_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    install = data.get("install")
    if not isinstance(install, dict):
        return None
    recorded = install.get("installed_version")
    return recorded if isinstance(recorded, str) else None


class VersionSyncCheck:
    """Check that the live package version matches the one that deployed the framework."""

    name: str = "version_sync"
    description: str = (
        "Installed package version matches the framework deployed by `nwave-ai install`"
    )

    def run(self, context: DoctorContext) -> CheckResult:
        """Return passed=False only on a determinable version mismatch.

        Args:
            context: Filesystem roots — reads ``context.global_config_path``.

        Returns:
            CheckResult; PASS when in sync or undeterminable, FAIL on drift.
        """
        recorded = _read_recorded_version(context.global_config_path)
        running = _detect_running_version()

        undeterminable = (
            recorded is None
            or running is None
            or _UNKNOWN_VERSION in (recorded, running)
        )
        if undeterminable:
            return CheckResult(
                passed=True,
                error_code=None,
                message=(
                    "Version sync not determinable "
                    f"(recorded={recorded or 'unset'}, running={running or 'unknown'})"
                ),
                remediation=None,
            )

        if recorded != running:
            return CheckResult(
                passed=False,
                error_code="FRAMEWORK_VERSION_DRIFT",
                message=(
                    f"nwave-ai package is {running} but the installed framework was "
                    f"deployed by {recorded} — the package was upgraded without "
                    "re-running install"
                ),
                remediation=(
                    "Run `nwave-ai install` to re-sync the nWave framework with the "
                    "upgraded package."
                ),
            )

        return CheckResult(
            passed=True,
            error_code=None,
            message=f"Package and framework in sync (v{running})",
            remediation=None,
        )
