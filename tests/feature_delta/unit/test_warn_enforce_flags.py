"""
Unit tests for warn-only / enforce flag handling (US-15).

Test budget: 3 behaviors x 2 = 6 max.
Actual: 3 unit tests -- one per distinct behavior.

Driving port: validate_feature_delta_command (CLI layer).
Driven port boundary: stderr output + exit code.
"""

from __future__ import annotations

import json
from pathlib import Path  # used in fixture bodies via tmp_path

import pytest
from nwave_ai.feature_delta.cli import validate_feature_delta_command


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def e5_violation_file(tmp_path: Path) -> Path:
    """Feature-delta with one E5 violation (DISCUSS commits CLI, DESIGN drops it)."""
    content = (
        "# warn test\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | POST /api/usage real WSGI handler | n/a | protocol surface |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| DISCUSS#row1 | framework-agnostic dispatcher | n/a | tradeoffs apply |\n"
    )
    p = tmp_path / "feature-delta.md"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def clean_file(tmp_path: Path) -> Path:
    """Well-formed feature-delta with no violations."""
    content = (
        "# clean\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | POST /api/login backed by Flask 3.x | n/a | establishes login surface |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| DISCUSS#row1 | POST /api/login backed by Flask 3.x | n/a | preserves DISCUSS#row1 verbatim |\n"
    )
    p = tmp_path / "feature-delta.md"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def stable_manifest(tmp_path: Path) -> Path:
    """Maturity manifest where all required rules are stable."""
    manifest = {
        "schema_version": 1,
        "rules": {
            "E1": {"status": "stable", "reason": "implemented"},
            "E2": {"status": "stable", "reason": "implemented"},
            "E3": {"status": "stable", "reason": "implemented"},
            "E3b": {"status": "stable", "reason": "implemented"},
            "E5": {"status": "stable", "reason": "implemented"},
        },
        "enforce_eligibility": {
            "required_stable": ["E1", "E2", "E3", "E3b", "E5"],
            "current_eligible": True,
            "reason": "All required rules stable.",
        },
    }
    p = tmp_path / "maturity.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


@pytest.fixture
def pending_manifest(tmp_path: Path) -> Path:
    """Maturity manifest with at least one required rule pending."""
    manifest = {
        "schema_version": 1,
        "rules": {
            "E1": {"status": "stable", "reason": "implemented"},
            "E2": {"status": "stable", "reason": "implemented"},
            "E3": {"status": "stable", "reason": "implemented"},
            "E3b": {"status": "pending", "reason": "not yet implemented"},
            "E5": {"status": "stable", "reason": "implemented"},
        },
        "enforce_eligibility": {
            "required_stable": ["E1", "E2", "E3", "E3b", "E5"],
            "current_eligible": False,
            "reason": "E3b still pending.",
        },
    }
    p = tmp_path / "pending-maturity.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# US-15 AC-1 / AC-3 — warn-only mode exits 0 even with violations
# ---------------------------------------------------------------------------


def test_warn_only_exits_zero_on_violations(
    e5_violation_file: Path, capsys: pytest.CaptureFixture
) -> None:
    """
    Warn-only mode (default) must exit 0 and emit [WARN] prefix on violations.
    Behavior: warn mode collects violations but does NOT block (exit 0).
    """
    exit_code = validate_feature_delta_command(str(e5_violation_file), mode="warn-only")

    assert exit_code == 0, "warn-only must exit 0 even when violations found"
    captured = capsys.readouterr()
    assert "[WARN]" in captured.err, (
        f"warn-only must emit [WARN] prefix; got stderr={captured.err!r}"
    )


# ---------------------------------------------------------------------------
# US-15 AC-2 / AC-6 — enforce mode refused when maturity manifest has pending rules
# ---------------------------------------------------------------------------


def test_enforce_refused_when_rules_pending(
    e5_violation_file: Path, pending_manifest: Path, capsys: pytest.CaptureFixture
) -> None:
    """
    Enforce mode must exit EX_CONFIG=78 when manifest reports any rule as pending.
    Behavior: enforce mode checks maturity manifest BEFORE running validation.
    Uses an explicit pending manifest fixture — does not depend on production manifest state.
    """
    exit_code = validate_feature_delta_command(
        str(e5_violation_file),
        mode="enforce",
        maturity_manifest_path=pending_manifest,
    )

    assert exit_code == 78, (
        f"enforce with pending rules must exit 78 (EX_CONFIG); got {exit_code}"
    )
    captured = capsys.readouterr()
    assert "cannot enable --enforce" in captured.err, (
        f"enforce refusal must name the reason; got stderr={captured.err!r}"
    )


# ---------------------------------------------------------------------------
# US-15 AC-3 — enforce mode runs validation when manifest all stable
# ---------------------------------------------------------------------------


def test_enforce_runs_when_all_rules_stable(
    clean_file: Path, stable_manifest: Path, capsys: pytest.CaptureFixture
) -> None:
    """
    Enforce mode with all-stable manifest must run validation and exit 0 on clean file.
    Behavior: enforce mode proceeds to validate when manifest gate passes.
    """
    exit_code = validate_feature_delta_command(
        str(clean_file), mode="enforce", maturity_manifest_path=stable_manifest
    )

    assert exit_code == 0, (
        f"enforce with stable manifest and clean file must exit 0; got {exit_code}"
    )
    captured = capsys.readouterr()
    # Validation ran to completion — should emit [PASS] markers
    assert "[PASS]" in captured.out, (
        f"enforce mode must run validation to completion; got stdout={captured.out!r}"
    )
