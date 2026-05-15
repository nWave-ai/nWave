"""Step definitions for the rigor-aware integrity regression (F-3 / RC-C).

Drives four scenarios from
``tests/bugs/installer/acceptance/test_rigor_aware_integrity.feature``.

Driving port: ``des-verify-integrity`` CLI invoked via ``subprocess.run``.
Driven adapter: real ``.nwave/des-config.json`` on disk (no mocking of
``DESConfig`` internals — port-to-port).

State-delta universes asserted under
``nwave_ai.state_delta.assert_state_delta(..., strict=True)``:

  A (3-phase rigor + 3-phase log):
    universe = {"cli.exit_code", "cli.has_missing_phases_error",
                "cli.stdout_ok"}
    expected post-fix: 0 / False / True

  B (legacy 5-phase rigor + 5-phase log):
    universe = same as A
    expected: 0 / False / True (no regression)

  C (empty rigor.tdd_phases):
    universe = {"cli.exit_code", "cli.stderr_names_offending_phases"}
    expected post-fix: non-zero / True

  D (no rigor override + canonical phase log):
    universe = same as A
    expected: 0 / False / True (default canon fallback)

Pre-fix, scenarios A and C FAIL (fail-for-right-reason gate). Scenarios B
and D pass both pre- and post-fix (backward-compat + default fallback).
The conftest at ``tests/bugs/installer/acceptance/conftest.py`` auto-marks
``@failing`` scenarios as ``xfail`` (non-strict). Removing the tags in
GREEN flips XFAIL→PASS.
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
from pytest_bdd import given, scenarios, then, when


_FEATURE = Path(__file__).resolve().parents[1] / "test_rigor_aware_integrity.feature"
scenarios(str(_FEATURE))


pytestmark = pytest.mark.xdist_group("rigor_aware_integrity_regression")


# ---------------------------------------------------------------------------
# Scenario state container
# ---------------------------------------------------------------------------


@dataclass
class _ScenarioState:
    cli_returncode: int | None = None
    cli_stdout: str = ""
    cli_stderr: str = ""
    project_root: Path | None = None  # CWD for subprocess (holds .nwave/)
    deliver_dir: Path | None = None  # passed as project-dir argument
    universe_before: dict = field(default_factory=dict)
    universe_after: dict = field(default_factory=dict)


@pytest.fixture
def scenario_state() -> _ScenarioState:
    return _ScenarioState()


# ---------------------------------------------------------------------------
# Helpers — port invocation via subprocess (driving port)
# ---------------------------------------------------------------------------


def _resolve_verify_integrity_cmd() -> list[str]:
    """Resolve the `des-verify-integrity` driving port.

    Prefer the installed console-script when available, else fall back to
    `python -m des.cli.verify_deliver_integrity` so the test runs in a fresh
    checkout that has not yet been `pip install -e .`'d.
    """
    bin_path = shutil.which("des-verify-integrity")
    if bin_path:
        return [bin_path]
    return [sys.executable, "-m", "des.cli.verify_deliver_integrity"]


_MIN_ROADMAP: dict = {
    "roadmap": {
        "project_id": "rigor-aware-integrity-fixture",
        "created_at": "2026-05-15T00:00:00Z",
        "total_steps": 1,
    },
    "phases": [
        {
            "id": "01",
            "name": "Single-step phase",
            "steps": [
                {
                    "id": "01-01",
                    "name": "Single fixture step",
                    "criteria": ["criterion one"],
                }
            ],
        }
    ],
    "implementation_scope": {
        "source_directories": ["src/fixture/"],
    },
}


def _write_execution_log(deliver_dir: Path, step_id: str, phases: list[str]) -> None:
    """Write an execution-log.json with given phases for one step."""
    events = [
        {
            "sid": step_id,
            "p": phase,
            "s": "EXECUTED",
            "d": "PASS",
            "t": f"2026-05-15T00:00:{idx:02d}Z",
        }
        for idx, phase in enumerate(phases)
    ]
    log = {
        "schema_version": "3.0",
        "feature_id": "rigor-aware-integrity-fixture",
        "events": events,
    }
    (deliver_dir / "execution-log.json").write_text(json.dumps(log), encoding="utf-8")


def _build_fixture(
    tmp_path: Path,
    *,
    rigor: dict | None,
    log_phases: list[str],
) -> tuple[Path, Path]:
    """Build a project-root + deliver-dir fixture.

    Layout:
        tmp_path/
          .nwave/des-config.json   (if rigor is not None — else absent)
          feature/deliver/roadmap.json
          feature/deliver/execution-log.json

    Returns (project_root, deliver_dir).
    """
    project_root = tmp_path
    deliver_dir = tmp_path / "feature" / "deliver"
    deliver_dir.mkdir(parents=True)

    # Roadmap fixture (always present, contract-conforming).
    (deliver_dir / "roadmap.json").write_text(
        json.dumps(_MIN_ROADMAP), encoding="utf-8"
    )

    # Optional rigor override.
    if rigor is not None:
        nwave_dir = project_root / ".nwave"
        nwave_dir.mkdir()
        config = {"rigor": rigor}
        (nwave_dir / "des-config.json").write_text(json.dumps(config), encoding="utf-8")

    # Execution-log with exact phases for the single fixture step.
    _write_execution_log(deliver_dir, step_id="01-01", phases=log_phases)

    return project_root, deliver_dir


def _run_verifier(project_root: Path, deliver_dir: Path) -> subprocess.CompletedProcess:
    """Invoke `des-verify-integrity` as a subprocess with cwd=project_root.

    Setting cwd=project_root lets DESConfig() resolve `.nwave/des-config.json`
    correctly (it reads via Path.cwd() at construction time).
    """
    cmd = _resolve_verify_integrity_cmd() + [str(deliver_dir)]
    return subprocess.run(
        cmd,
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given(
    "a feature dir with a 3-phase rigor profile and execution-log entries for "
    "RED GREEN COMMIT",
    target_fixture="scenario_state",
)
def _given_3phase_rigor_3phase_log(
    scenario_state: _ScenarioState, tmp_path: Path
) -> _ScenarioState:
    project_root, deliver_dir = _build_fixture(
        tmp_path,
        rigor={"tdd_phases": ["RED", "GREEN", "COMMIT"]},
        log_phases=["RED", "GREEN", "COMMIT"],
    )
    scenario_state.project_root = project_root
    scenario_state.deliver_dir = deliver_dir
    return scenario_state


@given(
    "a feature dir with a legacy 5-phase rigor profile and execution-log "
    "entries for all 5 phases",
    target_fixture="scenario_state",
)
def _given_5phase_rigor_5phase_log(
    scenario_state: _ScenarioState, tmp_path: Path
) -> _ScenarioState:
    legacy_phases = ["PREPARE", "RED_ACCEPTANCE", "RED_UNIT", "GREEN", "COMMIT"]
    project_root, deliver_dir = _build_fixture(
        tmp_path,
        rigor={"tdd_phases": legacy_phases},
        log_phases=legacy_phases,
    )
    scenario_state.project_root = project_root
    scenario_state.deliver_dir = deliver_dir
    return scenario_state


@given(
    "a feature dir with a rigor profile declaring tdd_phases as an empty list",
    target_fixture="scenario_state",
)
def _given_empty_rigor_phases(
    scenario_state: _ScenarioState, tmp_path: Path
) -> _ScenarioState:
    project_root, deliver_dir = _build_fixture(
        tmp_path,
        rigor={"tdd_phases": []},
        # Log content irrelevant — verifier must error before checking entries.
        log_phases=["GREEN"],
    )
    scenario_state.project_root = project_root
    scenario_state.deliver_dir = deliver_dir
    return scenario_state


@given(
    "a feature dir with no rigor override and execution-log entries for the "
    "canonical phase set",
    target_fixture="scenario_state",
)
def _given_no_rigor_override(
    scenario_state: _ScenarioState, tmp_path: Path
) -> _ScenarioState:
    # No rigor override → DESConfig.rigor_tdd_phases returns the default tuple
    # (legacy 5-phase, per des_config.py:167-174). Log must satisfy that set.
    legacy_phases = ["PREPARE", "RED_ACCEPTANCE", "RED_UNIT", "GREEN", "COMMIT"]
    project_root, deliver_dir = _build_fixture(
        tmp_path,
        rigor=None,
        log_phases=legacy_phases,
    )
    scenario_state.project_root = project_root
    scenario_state.deliver_dir = deliver_dir
    return scenario_state


# ---------------------------------------------------------------------------
# When step (single invocation shape — same for all four scenarios)
# ---------------------------------------------------------------------------


@when(
    "the des-verify-integrity CLI runs against the feature dir",
    target_fixture="scenario_state",
)
def _when_cli_runs(scenario_state: _ScenarioState) -> _ScenarioState:
    assert scenario_state.project_root is not None
    assert scenario_state.deliver_dir is not None
    proc = _run_verifier(scenario_state.project_root, scenario_state.deliver_dir)
    scenario_state.cli_returncode = proc.returncode
    scenario_state.cli_stdout = proc.stdout
    scenario_state.cli_stderr = proc.stderr
    return scenario_state


# ---------------------------------------------------------------------------
# Then steps — happy path (A, B, D)
# ---------------------------------------------------------------------------


@then("the verifier exits with status 0")
def _then_exit_zero(scenario_state: _ScenarioState) -> None:
    assert scenario_state.cli_returncode == 0, (
        f"CLI returncode={scenario_state.cli_returncode}, "
        f"stdout={scenario_state.cli_stdout!r}, "
        f"stderr={scenario_state.cli_stderr!r}"
    )


@then("the verifier output reports complete DES traces")
def _then_complete_traces(scenario_state: _ScenarioState) -> None:
    stdout = scenario_state.cli_stdout
    has_missing_phases_error = "INTEGRITY VIOLATIONS" in stdout or "missing" in stdout
    stdout_ok = "complete DES traces" in stdout

    universe = {
        "cli.exit_code",
        "cli.has_missing_phases_error",
        "cli.stdout_ok",
    }
    before = {
        "cli.exit_code": None,
        "cli.has_missing_phases_error": None,
        "cli.stdout_ok": None,
    }
    after = {
        "cli.exit_code": scenario_state.cli_returncode,
        "cli.has_missing_phases_error": has_missing_phases_error,
        "cli.stdout_ok": stdout_ok,
    }
    assert_state_delta(
        before,
        after,
        universe=universe,
        expected={
            "cli.exit_code": set_to(0),
            "cli.has_missing_phases_error": set_to(False),
            "cli.stdout_ok": set_to(True),
        },
        strict=True,
    )


# ---------------------------------------------------------------------------
# Then steps — misconfig path (C)
# ---------------------------------------------------------------------------


@then("the verifier exits with non-zero status")
def _then_exit_nonzero(scenario_state: _ScenarioState) -> None:
    assert scenario_state.cli_returncode != 0, (
        f"Expected non-zero exit, got returncode={scenario_state.cli_returncode}; "
        f"stdout={scenario_state.cli_stdout!r}"
    )


@then("the verifier stderr names the misconfigured rigor phases")
def _then_stderr_names_offending(scenario_state: _ScenarioState) -> None:
    combined_output = scenario_state.cli_stdout + "\n" + scenario_state.cli_stderr
    # Diagnostic must reference both the offending rigor phases (empty) AND
    # signal that it is the rigor.tdd_phases setting at fault. We accept any
    # of: literal "rigor.tdd_phases", or the phrase "rigor" together with
    # a recognisable error keyword.
    names_offending = "rigor.tdd_phases" in combined_output or (
        "rigor" in combined_output and "phases" in combined_output.lower()
    )

    universe = {
        "cli.exit_code",
        "cli.stderr_names_offending_phases",
    }
    before = {
        "cli.exit_code": None,
        "cli.stderr_names_offending_phases": None,
    }
    after = {
        "cli.exit_code": scenario_state.cli_returncode,
        "cli.stderr_names_offending_phases": names_offending,
    }
    assert_state_delta(
        before,
        after,
        universe=universe,
        expected={
            "cli.exit_code": lambda before_val, after_val: after_val != 0,
            "cli.stderr_names_offending_phases": set_to(True),
        },
        strict=True,
    )
