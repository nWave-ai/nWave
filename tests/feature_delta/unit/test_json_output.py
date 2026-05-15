"""
Unit tests for --format=json CLI output and exit-code-2 did-you-mean behavior.

Test Budget: 4 behaviors x 1 test each = 4 unit tests (within 12 budget).
Behaviors:
  B1 -- validate() with fmt="json" emits valid JSON to stdout (schema fields present)
  B2 -- JSON output contains schema_version=1 and results array
  B3 -- CLI exits 2 with stderr message when no path positional argument given
  B4 -- CLI exit 2 for nonexistent path (did-you-mean path routing)

All tests enter through driving ports:
  - validate_feature_delta_command() / main() -- driving port for the CLI layer
  - ValidationOrchestrator.validate() -- driving port for the application layer
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path  # used in fixture bodies and runtime calls

import pytest  # noqa: TC002  # used at runtime via pytest.CaptureFixture


# ---------------------------------------------------------------------------
# B1 + B2 — JSON output schema through the ValidationOrchestrator driving port
# ---------------------------------------------------------------------------


def _write_e3b_violation(tmp_path: Path) -> Path:
    """Feature-delta with one E3b violation (cherry-pick: commitment dropped without DDD ratification)."""
    path = tmp_path / "feature-delta.md"
    path.write_text(
        "# token-billing\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | real WSGI handler bound to /api/usage | n/a | establishes protocol surface |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| DISCUSS#row1 | framework-agnostic dispatcher | (none) | tradeoffs apply across the stack |\n",
        encoding="utf-8",
    )
    return path


def test_json_format_produces_valid_json_with_required_fields(tmp_path: Path) -> None:
    """B1+B2: validate() in fmt='json' mode emits JSON with required schema fields."""
    from nwave_ai.feature_delta.application.validator import ValidationOrchestrator

    path = _write_e3b_violation(tmp_path)

    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        orchestrator = ValidationOrchestrator()
        orchestrator.validate(path, mode="warn-only", fmt="json")
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue().strip()
    assert output, "json mode must emit non-empty stdout"

    parsed = json.loads(output)
    assert parsed.get("schema_version") == 1, f"expected schema_version=1, got {parsed}"
    results = parsed.get("results", [])
    assert isinstance(results, list), "results must be a list"
    # At least one violation must be present for E3 fixture
    assert len(results) >= 1, f"expected at least one violation, got {results}"
    required_fields = {"check", "severity", "file", "line", "offender", "remediation"}
    for item in results:
        missing = required_fields - set(item.keys())
        assert not missing, f"result item missing fields {missing}: {item}"


# ---------------------------------------------------------------------------
# B3 — Exit 2 returned when no positional path supplied (CLI driving port)
# ---------------------------------------------------------------------------


def test_cli_exits_2_when_no_path_argument() -> None:
    """B3: main(['validate-feature-delta']) with no path returns exit code 2."""
    from nwave_ai.feature_delta.cli import main

    exit_code = main(["validate-feature-delta"])
    assert exit_code == 2, f"expected exit 2 for missing path, got {exit_code}"


# ---------------------------------------------------------------------------
# B4 — CLI exits 2 for nonexistent path (usage error / did-you-mean)
# ---------------------------------------------------------------------------


def test_cli_exits_2_for_nonexistent_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """B4: main(['validate-feature-delta', '<missing>']) returns exit 2 with file-not-found in stderr.

    Per US-07A AC-3: a nonexistent path is treated as a usage error (did-you-mean),
    not an internal I/O error (exit 65 is reserved for files that exist but can't be read).
    """
    from nwave_ai.feature_delta.cli import main

    missing = str(tmp_path / "does_not_exist.md")
    exit_code = main(["validate-feature-delta", missing])
    assert exit_code == 2, f"expected exit 2 for missing file, got {exit_code}"
    stderr = capsys.readouterr().err
    assert "file not found" in stderr.lower(), (
        f"expected 'file not found' in stderr: {stderr!r}"
    )
