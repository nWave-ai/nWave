"""Regression: doctor + CLI status fail OPEN to inactive (step 01-06).

The enforcement gate (resolve_activation under the opt-in default) resolves a
missing/corrupt config to INACTIVE — fail-safe, don't act. The two diagnostic
helpers must AGREE with the gate: on a config-read exception they must report
INACTIVE, never "active". A diagnostic that is more optimistic than the gate
lies about the system's real behaviour.

This module forces a resolution exception (DESConfig construction raising) and
asserts BOTH diagnostics fail to inactive:
  - doctor report line  -> "this repo activation: inactive"
  - `attribution status` -> "Attribution is inactive for this repo."
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from nwave_ai.doctor.checks.attribution import AttributionCheck
from nwave_ai.doctor.context import DoctorContext

from nwave_ai import cli


if TYPE_CHECKING:
    from pathlib import Path


def _raise(*_args: object, **_kwargs: object) -> object:
    raise RuntimeError("forced config-read failure")


@pytest.fixture()
def context(tmp_path: Path) -> DoctorContext:
    return DoctorContext(home_dir=tmp_path, project_root=tmp_path)


def test_doctor_reports_inactive_when_activation_resolution_raises(
    context: DoctorContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Doctor fails OPEN to inactive when the config read raises.

    A config-read failure must surface as 'inactive' — matching the gate's
    fail-to-inactive-under-opt-in semantics, never the more optimistic 'active'.
    """
    monkeypatch.setattr(
        "des.adapters.driven.config.des_config.DESConfig",
        _raise,
    )

    result = AttributionCheck().run(context)

    assert "this repo activation: inactive" in result.message
    assert "this repo activation: active" not in result.message


def test_cli_status_reports_inactive_when_activation_resolution_raises(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`attribution status` (preference on) fails OPEN to inactive on a read error.

    With the preference ON, a config-read failure must print 'inactive for this
    repo', agreeing with the gate — never 'active'.
    """
    monkeypatch.setattr(cli, "read_attribution_preference", lambda _config_dir: True)
    monkeypatch.setattr(
        "des.adapters.driven.config.des_config.DESConfig",
        _raise,
    )

    exit_code = cli._handle_attribution(["status"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Attribution is inactive for this repo." in out
    assert "Attribution is active for this repo." not in out
