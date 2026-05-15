"""Step definitions for the roadmap schema-contract regression (F-1 / RC-A).

Drives two scenarios from
``tests/bugs/installer/acceptance/test_roadmap_schema_contract.feature``.

Driving port: ``des-roadmap`` CLI invoked via ``subprocess.run``.

State-delta universes asserted under
``nwave_ai.state_delta.assert_state_delta(..., strict=True)``:

  A (skeleton):
    universe = {
        "step.criteria_type",            # "list" | "str" | other type name
        "roadmap.has_phases_int_field",  # True iff roadmap.phases int present
        "cli.exit_code",                 # 0 on success
    }
    expected post-fix:
      step.criteria_type           -> "list"
      roadmap.has_phases_int_field -> False
      cli.exit_code                -> 0

  B (validator on legacy-string criteria):
    universe = {
        "cli.exit_code",                       # 0 — warnings, not errors
        "validator.has_legacy_criteria_warning",  # True iff LEGACY_CRITERIA_STRING in stdout
        "validator.has_error_line",            # False iff no "ERROR " line in stdout
    }
    expected post-fix:
      cli.exit_code                          -> 0
      validator.has_legacy_criteria_warning  -> True
      validator.has_error_line               -> False

Pre-fix, BOTH scenarios FAIL (fail-for-right-reason gate). The conftest at
``tests/bugs/installer/acceptance/conftest.py`` auto-marks ``@failing``
scenarios as ``xfail`` (non-strict). Removing the tag in GREEN flips XFAIL→PASS.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from nwave_ai.state_delta import assert_state_delta, set_to
from pytest_bdd import given, parsers, scenarios, then, when


_FEATURE = Path(__file__).resolve().parents[1] / "test_roadmap_schema_contract.feature"
scenarios(str(_FEATURE))


pytestmark = pytest.mark.xdist_group("roadmap_schema_contract_regression")


# ---------------------------------------------------------------------------
# Scenario state container
# ---------------------------------------------------------------------------


@dataclass
class _ScenarioState:
    cli_returncode: int | None = None
    cli_stdout: str = ""
    cli_stderr: str = ""
    skeleton: dict | None = None
    fixture_path: Path | None = None
    universe_before: dict = field(default_factory=dict)
    universe_after: dict = field(default_factory=dict)


@pytest.fixture
def scenario_state() -> _ScenarioState:
    return _ScenarioState()


# ---------------------------------------------------------------------------
# Helpers — port invocation via subprocess (driving port)
# ---------------------------------------------------------------------------


def _resolve_des_roadmap_cmd() -> list[str]:
    """Resolve the `des-roadmap` driving port.

    Prefer the installed console-script when available, else fall back to
    `python -m des.cli.roadmap` so the test runs in a fresh checkout that has
    not yet been `pip install -e .`'d.
    """
    bin_path = shutil.which("des-roadmap")
    if bin_path:
        return [bin_path]
    return [sys.executable, "-m", "des.cli.roadmap"]


# ---------------------------------------------------------------------------
# Scenario A — skeleton
# ---------------------------------------------------------------------------


@given("the des-roadmap CLI is available on PATH")
def _given_cli_available(scenario_state: _ScenarioState) -> None:
    # Resolution failure raises before When; acceptable because it represents
    # an environmental fault, not a business-logic failure.
    cmd = _resolve_des_roadmap_cmd()
    assert cmd, "des-roadmap driving port unavailable"


@when(
    parsers.parse('the CLI runs "init {init_args}"'),
    target_fixture="scenario_state",
)
def _when_cli_runs_init(
    scenario_state: _ScenarioState, init_args: str
) -> _ScenarioState:
    cmd = _resolve_des_roadmap_cmd() + ["init"] + init_args.split()
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    scenario_state.cli_returncode = proc.returncode
    scenario_state.cli_stdout = proc.stdout
    scenario_state.cli_stderr = proc.stderr
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            scenario_state.skeleton = json.loads(proc.stdout)
        except json.JSONDecodeError:
            scenario_state.skeleton = None
    return scenario_state


@then("the CLI exits with status 0")
def _then_cli_exit_0(scenario_state: _ScenarioState) -> None:
    assert scenario_state.cli_returncode == 0, (
        f"CLI returncode={scenario_state.cli_returncode}, "
        f"stderr={scenario_state.cli_stderr!r}"
    )


@then("the emitted skeleton declares step criteria as a JSON list")
def _then_skeleton_criteria_is_list(scenario_state: _ScenarioState) -> None:
    skeleton = scenario_state.skeleton
    assert skeleton is not None, "Skeleton not parsed from stdout"
    # Capture full universe for the state-delta assertion.
    phases = skeleton.get("phases", [])
    first_step = phases[0]["steps"][0] if phases and phases[0].get("steps") else {}
    criteria_type = type(first_step.get("criteria", None)).__name__
    has_phases_int = isinstance(skeleton.get("roadmap", {}).get("phases"), int)

    universe = {"step.criteria_type", "roadmap.has_phases_int_field", "cli.exit_code"}
    before = {
        "step.criteria_type": None,
        "roadmap.has_phases_int_field": None,
        "cli.exit_code": None,
    }
    after = {
        "step.criteria_type": criteria_type,
        "roadmap.has_phases_int_field": has_phases_int,
        "cli.exit_code": scenario_state.cli_returncode,
    }
    assert_state_delta(
        before,
        after,
        universe=universe,
        expected={
            "step.criteria_type": set_to("list"),
            "roadmap.has_phases_int_field": set_to(False),
            "cli.exit_code": set_to(0),
        },
        strict=True,
    )


@then("the emitted skeleton omits the legacy roadmap.phases integer field")
def _then_skeleton_no_phases_int(scenario_state: _ScenarioState) -> None:
    # This step exists for readability; the universe assertion above already
    # forbids the integer field. We still surface a clean error message here.
    skeleton = scenario_state.skeleton
    assert skeleton is not None
    phases_field = skeleton.get("roadmap", {}).get("phases", None)
    assert not isinstance(phases_field, int), (
        f"roadmap.phases should not be int; got {phases_field!r}. "
        "F-1 mandates skeleton omits this collision-prone field."
    )


# ---------------------------------------------------------------------------
# Scenario B — validator legacy-string compat
# ---------------------------------------------------------------------------


_LEGACY_FIXTURE = {
    "roadmap": {
        "project_id": "fixture-legacy-string",
        "created_at": "2026-05-15T00:00:00Z",
        "total_steps": 1,
    },
    "phases": [
        {
            "id": "01",
            "name": "Legacy phase",
            "steps": [
                {
                    "id": "01-01",
                    "name": "Legacy step",
                    "criteria": "Legacy criterion as a single string",
                }
            ],
        }
    ],
    "implementation_scope": {
        "source_directories": ["src/legacy/"],
    },
}


@given(
    "a legacy roadmap fixture with step criteria stored as a single string",
    target_fixture="scenario_state",
)
def _given_legacy_fixture(
    scenario_state: _ScenarioState, tmp_path: Path
) -> _ScenarioState:
    fixture = tmp_path / "legacy-roadmap.json"
    fixture.write_text(json.dumps(_LEGACY_FIXTURE), encoding="utf-8")
    scenario_state.fixture_path = fixture
    return scenario_state


@when(
    "the des-roadmap CLI validates the fixture",
    target_fixture="scenario_state",
)
def _when_cli_validates(scenario_state: _ScenarioState) -> _ScenarioState:
    assert scenario_state.fixture_path is not None
    cmd = _resolve_des_roadmap_cmd() + ["validate", str(scenario_state.fixture_path)]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    scenario_state.cli_returncode = proc.returncode
    scenario_state.cli_stdout = proc.stdout
    scenario_state.cli_stderr = proc.stderr
    return scenario_state


@then("the validator output contains a LEGACY_CRITERIA_STRING warning")
def _then_legacy_warning_present(scenario_state: _ScenarioState) -> None:
    has_legacy_warning = "LEGACY_CRITERIA_STRING" in scenario_state.cli_stdout
    has_error_line = any(
        line.lstrip().startswith("ERROR ")
        for line in scenario_state.cli_stdout.splitlines()
    )

    universe = {
        "cli.exit_code",
        "validator.has_legacy_criteria_warning",
        "validator.has_error_line",
    }
    before = {
        "cli.exit_code": None,
        "validator.has_legacy_criteria_warning": None,
        "validator.has_error_line": None,
    }
    after = {
        "cli.exit_code": scenario_state.cli_returncode,
        "validator.has_legacy_criteria_warning": has_legacy_warning,
        "validator.has_error_line": has_error_line,
    }
    assert_state_delta(
        before,
        after,
        universe=universe,
        expected={
            "cli.exit_code": set_to(0),
            "validator.has_legacy_criteria_warning": set_to(True),
            "validator.has_error_line": set_to(False),
        },
        strict=True,
    )


@then("the validator output contains no error lines")
def _then_no_error_lines(scenario_state: _ScenarioState) -> None:
    # Redundancy guard alongside the state-delta universe.
    error_lines = [
        line
        for line in scenario_state.cli_stdout.splitlines()
        if line.lstrip().startswith("ERROR ")
    ]
    assert not error_lines, (
        f"Validator emitted unexpected ERROR lines on legacy string fixture: "
        f"{error_lines!r}"
    )
