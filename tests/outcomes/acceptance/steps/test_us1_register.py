"""Step definitions for US-1 register hardening scenarios.

Per Mandate 5: invokes the real `nwave-ai outcomes register` console
subcommand via subprocess (no in-process import). Real YAML filesystem
under tmp_path (Strategy C — real local).
"""

from __future__ import annotations

import re
from pathlib import Path  # used in fixture bodies

import yaml
from pytest_bdd import given, parsers, scenarios, then, when

from tests.outcomes.acceptance.conftest import registry_path


scenarios("../test_us1_register.feature")


CANONICAL_KEYS = (
    "id",
    "kind",
    "summary",
    "feature",
    "inputs",
    "output",
    "keywords",
    "artifact",
    "related",
    "superseded_by",
)


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        "OUT-1 has been registered as a specification with input shape "
        '"{input_shape}" and output shape "{output_shape}" with keywords '
        '"{keywords}"'
    )
)
def _register_out_1_precondition(
    run_cli, state: dict, input_shape: str, output_shape: str, keywords: str
) -> None:
    result = run_cli(
        "outcomes",
        "register",
        "--id",
        "OUT-1",
        "--kind",
        "specification",
        "--summary",
        "US-1 outcome",
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


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


@when(
    parsers.parse(
        "the author registers OUT-1 as a specification with input shape "
        '"{input_shape}" and output shape "{output_shape}" with keywords '
        '"{keywords}"'
    )
)
def _register_out_1(
    run_cli, state: dict, input_shape: str, output_shape: str, keywords: str
) -> None:
    state["register_result"] = run_cli(
        "outcomes",
        "register",
        "--id",
        "OUT-1",
        "--kind",
        "specification",
        "--summary",
        "US-1 outcome",
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


@when("the author registers OUT-1 again with shapes X and Y and keyword k")
def _register_out_1_again(run_cli, state: dict) -> None:
    state["register_result"] = run_cli(
        "outcomes",
        "register",
        "--id",
        "OUT-1",
        "--kind",
        "specification",
        "--input-shape",
        "X",
        "--output-shape",
        "Y",
        "--keywords",
        "k",
    )


@when("the registry file is parsed back as YAML")
def _parse_registry(sandbox: Path, state: dict) -> None:
    path = registry_path(sandbox)
    raw_text = path.read_text(encoding="utf-8")
    state["raw_text"] = raw_text
    state["parsed"] = yaml.safe_load(raw_text)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then(parsers.parse("the CLI register exit code is {code:d}"))
def _register_exit_code(state: dict, code: int) -> None:
    result = state["register_result"]
    assert result.exit_code == code, (
        f"expected exit {code}, got {result.exit_code}\n"
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


@then("the registry contains an entry with id OUT-1")
def _registry_has_out_1(sandbox: Path) -> None:
    path = registry_path(sandbox)
    assert path.exists(), f"registry not found at {path}"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    ids = [o["id"] for o in (data.get("outcomes") or [])]
    assert "OUT-1" in ids, f"OUT-1 not in {ids}"


@then(parsers.re(r"stderr matches /(?P<pattern>.+)/"))
def _stderr_matches(state: dict, pattern: str) -> None:
    result = state["register_result"]
    assert re.search(pattern, result.stderr), (
        f"stderr did not match /{pattern}/; stderr={result.stderr!r}"
    )


@then(
    "the entry keys are in canonical order id, kind, summary, feature, "
    "inputs, output, keywords, artifact, related, superseded_by"
)
def _canonical_keys(state: dict) -> None:
    data = state["parsed"]
    outcomes = data.get("outcomes") or []
    assert outcomes, "registry has no outcomes after register"
    entry = outcomes[0]
    actual_keys = tuple(entry.keys())
    assert actual_keys == CANONICAL_KEYS, (
        f"keys not canonical: expected {CANONICAL_KEYS}, got {actual_keys}"
    )


@then("the registry file ends with a trailing newline")
def _trailing_newline(state: dict) -> None:
    raw = state["raw_text"]
    assert raw.endswith("\n"), f"registry file missing trailing newline: {raw[-30:]!r}"
