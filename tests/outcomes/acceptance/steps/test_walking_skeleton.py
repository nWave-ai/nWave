"""Step definitions for the outcomes registry walking skeleton scenario.

Mandate 5 (Driving Adapter): the WS scenario invokes the real
`nwave-ai outcomes register|check` console subcommands via subprocess.
No in-process import of the outcomes module — the CLI surface is the
contract.
"""

from __future__ import annotations

from pathlib import Path  # used in fixture bodies

import yaml
from pytest_bdd import scenarios, then, when

from tests.outcomes.acceptance.conftest import registry_path


scenarios("../test_walking_skeleton.feature")


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


@when(
    "the author registers OUT-A as a specification with input shape "
    '"FeatureDeltaModel" and output shape "tuple[Violation, ...]"'
)
def _register_out_a(run_cli, state: dict) -> None:
    result = run_cli(
        "outcomes",
        "register",
        "--id",
        "OUT-A",
        "--kind",
        "specification",
        "--summary",
        "Walking skeleton outcome",
        "--feature",
        "outcomes-registry",
        "--input-shape",
        "FeatureDeltaModel",
        "--output-shape",
        "tuple[Violation, ...]",
        "--keywords",
        "non-empty,required",
        "--artifact",
        "nwave_ai/outcomes/walking_skeleton.py",
    )
    state["register_result"] = result
    assert result.exit_code == 0, (
        f"register exit_code={result.exit_code}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )


@when("the author runs check with the same shapes")
def _check_collision(run_cli, state: dict) -> None:
    result = run_cli(
        "outcomes",
        "check",
        "--input-shape",
        "FeatureDeltaModel",
        "--output-shape",
        "tuple[Violation, ...]",
        "--keywords",
        "cherry-pick,row-count",
    )
    state["check_result"] = result


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then("the registry contains OUT-A")
def _registry_contains_out_a(sandbox: Path) -> None:
    path = registry_path(sandbox)
    assert path.exists(), f"registry not written at {path}"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    ids = [o["id"] for o in data["outcomes"]]
    assert "OUT-A" in ids, f"OUT-A not in registry; ids={ids}"


@then("the CLI exits with code 1")
def _check_exit_1(state: dict) -> None:
    result = state["check_result"]
    assert result.exit_code == 1, (
        f"expected check exit 1, got {result.exit_code}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )


@then("stdout reports a collision with OUT-A")
def _collision_reports_out_a(state: dict) -> None:
    result = state["check_result"]
    assert "OUT-A" in result.stdout, (
        f"expected OUT-A in stdout; got stdout={result.stdout!r}"
    )
