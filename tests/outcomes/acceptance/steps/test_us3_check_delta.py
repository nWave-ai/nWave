"""Step definitions for US-3 check-delta scenarios (aggregate scan).

Per Mandate 5: invokes the real `nwave-ai outcomes check-delta` console
subcommand via subprocess (no in-process import). Real YAML filesystem
under tmp_path (Strategy C — real local).
"""

from __future__ import annotations

from pathlib import Path  # used in fixture bodies

from pytest_bdd import given, parsers, scenarios, then, when


scenarios("../test_us3_check_delta.feature")


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        '{outcome_id} has been registered with input shape "{input_shape}" '
        'and output shape "{output_shape}" and keywords "{keywords}"'
    )
)
def _register_precondition(
    run_cli,
    outcome_id: str,
    input_shape: str,
    output_shape: str,
    keywords: str,
) -> None:
    result = run_cli(
        "outcomes",
        "register",
        "--id",
        outcome_id,
        "--kind",
        "specification",
        "--summary",
        "US-3 precondition outcome",
        "--feature",
        "outcomes-registry",
        "--input-shape",
        input_shape,
        "--output-shape",
        output_shape,
        "--keywords",
        keywords,
        "--artifact",
        "nwave_ai/outcomes/cli.py",
    )
    assert result.exit_code == 0, (
        f"precondition register failed: exit={result.exit_code} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


@given(parsers.parse("a feature-delta.md exists referencing {ids}"))
def _create_feature_delta(sandbox: Path, state: dict, ids: str) -> None:
    delta_path = sandbox / "docs" / "feature" / "F-test" / "feature-delta.md"
    delta_path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "# Feature Delta — F-test\n\n"
        "## DISTILL\n\n"
        f"Outcomes referenced: {ids}\n\n"
        "These outcomes are scanned by `outcomes check-delta`.\n"
    )
    delta_path.write_text(body, encoding="utf-8")
    state["delta_path"] = delta_path


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


@when("the author runs check-delta on the feature-delta.md")
def _run_check_delta(run_cli, state: dict) -> None:
    delta_path = state["delta_path"]
    state["check_result"] = run_cli(
        "outcomes",
        "check-delta",
        str(delta_path),
    )


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then(parsers.parse("the CLI check-delta exit code is {code:d}"))
def _check_exit_code(state: dict, code: int) -> None:
    result = state["check_result"]
    assert result.exit_code == code, (
        f"expected exit {code}, got {result.exit_code}\n"
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


@then(parsers.parse('stdout contains "{needle}"'))
def _stdout_contains(state: dict, needle: str) -> None:
    result = state["check_result"]
    assert needle in result.stdout, (
        f"expected {needle!r} in stdout; got stdout={result.stdout!r}"
    )
