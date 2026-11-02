"""VersionSyncCheck — detects an upgraded package whose framework was not reinstalled.

The ``nwave-ai`` package and the deployed nWave framework are kept in lock-step by
``nwave-ai install``: every install records the package version that performed it
into ``~/.nwave/config.json`` (``install.installed_version``). When a
package manager later upgrades ``nwave-ai`` (``pipx upgrade`` / ``uv tool upgrade``)
but the user forgets to re-run ``nwave-ai install``, the live package version
drifts ahead of the deployed framework assets — silently, with confusing
behaviour and no signal. This check surfaces that drift.

The two public version *tracks* (the ``nwave-ai`` wheel vs. ``nWave/VERSION``) are
NOT directly comparable, so the check never compares those. It compares the live
package version against the package version *recorded at the last install* — both
the same value type, captured from the same interpreter.

Fail-loud by construction: when either side cannot be determined (no recorded
version, package metadata absent, or a ``0.0.0`` sentinel) the check reports
``could not verify`` — never passed and never a mismatch. A check that could not
check must not look healthy, so the verdict is not-passed with an explanation
(what could not be read, why that matters, and the manual next step).

Mechanism (the load-bearing assumption): ``pipx upgrade`` / ``uv tool upgrade``
mutate the package *in place* inside the existing tool venv, so the interpreter
path baked into ``settings.json`` at the last install still launches that venv
and ``importlib.metadata`` reads the *upgraded* version — which is exactly the
asymmetry this check relies on (live version moves, recorded version does not).
The rare exception is an extraordinary venv recreation (e.g. a Python minor-
version bump that forces ``pipx reinstall``): the baked interpreter path can go
stale and the hook fails to launch, so no advisory is produced. That degraded
path is outside this check; the next ``nwave-ai install`` repairs both the path
and the recorded version.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
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


@dataclass(frozen=True)
class VersionReading:
    """What one version source reported, and how to say so when it is unusable."""

    source: str
    value: str | None
    absent_state: str
    unknown_state: str

    @classmethod
    def recorded(cls, value: str | None) -> VersionReading:
        """The version the last ``nwave-ai install`` recorded in the global config."""
        return cls(
            source="install.installed_version in the global config",
            value=value,
            absent_state="could not be read",
            unknown_state=f"holds the unknown version {_UNKNOWN_VERSION}",
        )

    @classmethod
    def running(cls, value: str | None) -> VersionReading:
        """The version the live ``nwave-ai`` package metadata reports."""
        return cls(
            source="nwave-ai package metadata",
            value=value,
            absent_state="was not found",
            unknown_state=f"reports the unknown version {_UNKNOWN_VERSION}",
        )

    @property
    def is_comparable(self) -> bool:
        """True only for a real version: absent and the 0.0.0 sentinel are not."""
        return self.value is not None and self.value != _UNKNOWN_VERSION

    def unavailability(self) -> str:
        """What was observed at the source, without guessing why."""
        state = self.absent_state if self.value is None else self.unknown_state
        return f"{self.source} {state}"


@dataclass(frozen=True)
class VersionComparison:
    """The recorded and running readings, and the one decision made from them."""

    recorded: VersionReading
    running: VersionReading

    def verdict(self) -> CheckResult:
        """Unavailable evidence is never decided: only two known versions are."""
        unavailable = [
            reading
            for reading in (self.recorded, self.running)
            if not reading.is_comparable
        ]
        if unavailable:
            return self._could_not_verify(unavailable)
        if self.recorded.value != self.running.value:
            return self._drift()
        return CheckResult(
            passed=True,
            error_code=None,
            message=f"Package and framework in sync (v{self.running.value})",
            remediation=None,
        )

    def _could_not_verify(self, unavailable: list[VersionReading]) -> CheckResult:
        observed = "; ".join(reading.unavailability() for reading in unavailable)
        return CheckResult.could_not_verify(
            error_code="VERSION_SYNC_UNVERIFIABLE",
            message=(
                f"Could not verify version sync: {observed}, "
                "so the package version cannot be compared with the version "
                "recorded by the last install"
            ),
            remediation=(
                "Run `nwave-ai install` with the intended nwave-ai package so it "
                "records install.installed_version, then run `nwave-ai doctor` "
                "again to verify. No mismatch was detected."
            ),
        )

    def _drift(self) -> CheckResult:
        return CheckResult(
            passed=False,
            error_code="FRAMEWORK_VERSION_DRIFT",
            message=(
                f"nwave-ai package is {self.running.value} but the installed "
                f"framework was deployed by {self.recorded.value} — the package "
                "was upgraded without re-running install"
            ),
            remediation=(
                "Run `nwave-ai install` to re-sync the nWave framework with the "
                "upgraded package."
            ),
        )


class VersionSyncCheck:
    """Check that the live package version matches the one that deployed the framework."""

    name: str = "version_sync"
    description: str = (
        "Installed package version matches the framework deployed by `nwave-ai install`"
    )

    def run(self, context: DoctorContext) -> CheckResult:
        """Decide whether the live package matches the one that deployed the framework.

        Args:
            context: Filesystem roots — reads ``context.global_config_path``.

        Returns:
            CheckResult; PASS when both versions are known and equal, FAIL on a
            known drift, COULD NOT VERIFY when either version is unavailable.
        """
        comparison = VersionComparison(
            recorded=VersionReading.recorded(
                _read_recorded_version(context.global_config_path)
            ),
            running=VersionReading.running(_detect_running_version()),
        )
        return comparison.verdict()
