"""Acceptance tests for DensityCheck — port-to-port at the check.run() seam.

The driving port is `DensityCheck.run(context) -> CheckResult`. Inputs flow
through `~/.nwave/global-config.json` (driven adapter: real filesystem under
tmp_path); the check reads that file, calls `resolve_density()`, and emits a
human-readable message line capturing mode + provenance.

Coverage maps to step 02-02's three branches of the D12 cascade:
  1. No config file at all -> default ("default (no config)")
  2. Explicit `documentation.density` set -> "<mode> (explicit override)"
  3. `rigor.profile` only -> "<mode> (inherited from rigor.profile=<name>)"
  4. Both set -> explicit wins (regression guard for AC-3.g)
  5. Unknown rigor.profile -> failed result with remediation
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from nwave_ai.doctor.checks.density import DensityCheck
from nwave_ai.doctor.context import DoctorContext


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def context(tmp_path: Path) -> DoctorContext:
    """DoctorContext rooted at a fresh tmp_path home (no ~/.nwave yet)."""
    return DoctorContext(home_dir=tmp_path)


def _write_global_config(home: Path, payload: dict) -> Path:
    """Write `~/.nwave/global-config.json` under the test home."""
    nwave_dir = home / ".nwave"
    nwave_dir.mkdir(parents=True, exist_ok=True)
    config_path = nwave_dir / "global-config.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    return config_path


def test_passes_with_lean_default_when_no_config_file(context: DoctorContext) -> None:
    """Fresh install: no config file -> lean (default (no config))."""
    check = DensityCheck()
    result = check.run(context)
    assert result.passed is True
    assert "Documentation density: lean (default (no config))" in result.message


def test_passes_with_full_inherited_from_rigor_profile_thorough(
    context: DoctorContext,
) -> None:
    """AC-3.f: rigor.profile=thorough only -> full (inherited from ...)."""
    _write_global_config(context.home_dir, {"rigor": {"profile": "thorough"}})
    check = DensityCheck()
    result = check.run(context)
    assert result.passed is True
    assert (
        "Documentation density: full (inherited from rigor.profile=thorough)"
        in result.message
    )


def test_passes_with_lean_explicit_override(context: DoctorContext) -> None:
    """AC-3.g: explicit documentation.density wins over rigor.profile."""
    _write_global_config(
        context.home_dir,
        {
            "documentation": {"density": "lean", "expansion_prompt": "always-skip"},
            "rigor": {"profile": "thorough"},
        },
    )
    check = DensityCheck()
    result = check.run(context)
    assert result.passed is True
    assert "Documentation density: lean (explicit override)" in result.message
    assert "expansion prompt: always-skip" in result.message


def test_passes_with_full_explicit_override(context: DoctorContext) -> None:
    """Explicit density=full produces the override label even without rigor."""
    _write_global_config(
        context.home_dir,
        {"documentation": {"density": "full"}},
    )
    check = DensityCheck()
    result = check.run(context)
    assert result.passed is True
    assert "Documentation density: full (explicit override)" in result.message


def test_fails_with_remediation_on_unknown_rigor_profile(
    context: DoctorContext,
) -> None:
    """Unknown rigor.profile -> failed CheckResult with remediation guidance."""
    _write_global_config(context.home_dir, {"rigor": {"profile": "ludicrous"}})
    check = DensityCheck()
    result = check.run(context)
    assert result.passed is False
    assert result.error_code is not None
    assert result.remediation is not None
    assert "rigor" in result.message.lower() or "profile" in result.message.lower()


def test_fails_loudly_on_unknown_expansion_prompt(context: DoctorContext) -> None:
    """Doctor makes an invalid expansion mode observable and actionable."""
    _write_global_config(
        context.home_dir,
        {
            "documentation": {
                "density": "lean",
                "expansion_prompt": "ask-clever",
            }
        },
    )

    result = DensityCheck().run(context)

    assert result.passed is False
    assert result.error_code == "DENSITY_RESOLUTION_FAILED"
    assert "expansion_prompt" in result.message
    assert result.remediation is not None
    assert "ask-intelligent" in result.remediation


def test_passes_when_config_exists_but_is_empty_json(context: DoctorContext) -> None:
    """Empty config -> falls back to default branch (lean (default (no config)))."""
    _write_global_config(context.home_dir, {})
    check = DensityCheck()
    result = check.run(context)
    assert result.passed is True
    assert "Documentation density: lean" in result.message
    assert "default" in result.message


def test_check_name_is_documentation_density(context: DoctorContext) -> None:
    """Identifier emitted in formatter output and JSON renderer."""
    assert DensityCheck.name == "documentation_density"
