"""Acceptance tests for VersionSyncCheck.

Tests enter through the check's run() driving port.

The check flags the "upgraded the package but forgot to re-run install" failure
mode: the live ``importlib.metadata`` version of ``nwave-ai`` differs from the
version recorded in ``~/.nwave/global-config.json`` at the last install (the
version that actually deployed the framework assets).

It must NEVER false-alarm when it cannot determine both sides (no recorded
version, package metadata absent, or a "0.0.0" sentinel) — an install-health
check that nags on a healthy-but-undeterminable state is worse than silent.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from nwave_ai.doctor.checks.version_sync import VersionSyncCheck
from nwave_ai.doctor.context import DoctorContext

from nwave_ai.doctor.checks import version_sync


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def context(tmp_path: Path) -> DoctorContext:
    return DoctorContext(home_dir=tmp_path)


def _write_global_config(context: DoctorContext, data: dict) -> None:
    path = context.global_config_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _set_running_version(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    monkeypatch.setattr(version_sync, "_detect_running_version", lambda: value)


def test_fails_when_recorded_and_running_versions_differ(
    context: DoctorContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drift: package upgraded to 1.2.0 but framework deployed by 1.1.0 -> FAIL."""
    _write_global_config(context, {"install": {"installed_version": "1.1.0"}})
    _set_running_version(monkeypatch, "1.2.0")

    result = VersionSyncCheck().run(context)

    assert result.passed is False
    assert result.error_code == "FRAMEWORK_VERSION_DRIFT"
    assert "1.1.0" in result.message and "1.2.0" in result.message
    assert result.remediation is not None
    assert "nwave-ai install" in result.remediation


def test_fails_when_running_version_is_older_than_recorded(
    context: DoctorContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Downgrade also drifts: a re-install is still needed to realign assets.

    Regression guard for the comparison operator: the check uses ``!=`` (any
    mismatch), not ``<``. If someone narrowed it to "running newer than recorded"
    the downgrade path would silently become a false negative — this test fails
    the moment that happens.
    """
    _write_global_config(context, {"install": {"installed_version": "1.2.0"}})
    _set_running_version(monkeypatch, "1.1.0")

    result = VersionSyncCheck().run(context)

    assert result.passed is False
    assert result.error_code == "FRAMEWORK_VERSION_DRIFT"
    assert "1.2.0" in result.message and "1.1.0" in result.message


def test_passes_when_versions_match(
    context: DoctorContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In-sync: recorded == running -> PASS, no remediation."""
    _write_global_config(context, {"install": {"installed_version": "1.2.0"}})
    _set_running_version(monkeypatch, "1.2.0")

    result = VersionSyncCheck().run(context)

    assert result.passed is True
    assert result.error_code is None
    assert result.remediation is None
    assert "1.2.0" in result.message


def test_passes_when_no_recorded_version(
    context: DoctorContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-feature install (no install block recorded) -> can't determine -> PASS."""
    _write_global_config(context, {"update_check": {"frequency": "daily"}})
    _set_running_version(monkeypatch, "1.2.0")

    result = VersionSyncCheck().run(context)

    assert result.passed is True
    assert result.error_code is None


def test_passes_when_global_config_absent(
    context: DoctorContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No global-config.json at all -> can't determine -> PASS (fail-open)."""
    assert not context.global_config_path.exists()
    _set_running_version(monkeypatch, "1.2.0")

    result = VersionSyncCheck().run(context)

    assert result.passed is True


def test_passes_when_running_version_undetectable(
    context: DoctorContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Package metadata absent (e.g. editable/dev) -> can't determine -> PASS."""
    _write_global_config(context, {"install": {"installed_version": "1.1.0"}})
    _set_running_version(monkeypatch, None)

    result = VersionSyncCheck().run(context)

    assert result.passed is True


def test_passes_when_recorded_version_is_sentinel(
    context: DoctorContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recorded '0.0.0' sentinel is 'unknown', not a real version -> PASS."""
    _write_global_config(context, {"install": {"installed_version": "0.0.0"}})
    _set_running_version(monkeypatch, "1.2.0")

    result = VersionSyncCheck().run(context)

    assert result.passed is True


def test_passes_when_running_version_is_sentinel(
    context: DoctorContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A live '0.0.0' (e.g. dev/editable) is 'unknown' on the running side -> PASS.

    Complements test_passes_when_recorded_version_is_sentinel so both sides of the
    ``_UNKNOWN_VERSION in (recorded, running)`` guard are covered; a refactor that
    dropped either side would now fail a test.
    """
    _write_global_config(context, {"install": {"installed_version": "1.1.0"}})
    _set_running_version(monkeypatch, "0.0.0")

    result = VersionSyncCheck().run(context)

    assert result.passed is True


def test_passes_on_corrupt_global_config(
    context: DoctorContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Corrupt JSON must not crash the check -> can't determine -> PASS."""
    path = context.global_config_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ not json", encoding="utf-8")
    _set_running_version(monkeypatch, "1.2.0")

    result = VersionSyncCheck().run(context)

    assert result.passed is True


def test_check_has_stable_name(context: DoctorContext) -> None:
    """The check exposes a stable name attribute for the runner to annotate."""
    assert VersionSyncCheck().name == "version_sync"
