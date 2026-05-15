"""Step definitions for the --roadmap-only flag regression (F-2 / RC-B).

Drives four scenarios from
``tests/bugs/installer/acceptance/test_roadmap_only_flag.feature``.

Driving port: ``des-verify-integrity`` CLI invoked via ``subprocess.run``.
Driven adapter: real ``roadmap.json`` (+ optional ``execution-log.json``) on
tmp_path — no mocking of internals.

State-delta universes asserted under
``nwave_ai.state_delta.assert_state_delta(..., strict=True)``:

  A (--roadmap-only on valid roadmap, NO execution-log):
    universe = {"cli.exit_code", "cli.skipped_execution_log",
                "cli.touched_validator"}
    expected post-fix: 0 / True / True

  B (--roadmap-only on malformed roadmap, NO execution-log):
    universe = {"cli.exit_code", "cli.skipped_execution_log",
                "cli.stdout_reports_errors"}
    expected post-fix: 2 / True / True

  C (no flag — backward compat):
    universe = {"cli.exit_code", "cli.stdout_ok"}
    expected: 0 / True (no regression)

  D (unknown flag):
    universe = {"cli.exit_code", "cli.stderr_contains_usage"}
    expected post-fix: non-zero / True (argparse usage banner)

Pre-fix, scenarios A, B and D FAIL (fail-for-right-reason gate). Scenario C
passes both pre- and post-fix (backward compat — no flag at all).
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


_FEATURE = Path(__file__).resolve().parents[1] / "test_roadmap_only_flag.feature"
scenarios(str(_FEATURE))


pytestmark = pytest.mark.xdist_group("roadmap_only_flag_regression")


# ---------------------------------------------------------------------------
# Scenario state container
# ---------------------------------------------------------------------------


@dataclass
class _ScenarioState:
    cli_returncode: int | None = None
    cli_stdout: str = ""
    cli_stderr: str = ""
    project_root: Path | None = None
    deliver_dir: Path | None = None
    used_flag: bool = False
    used_unknown_flag: bool = False
    execution_log_present_before: bool = False
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
    `python -m des.cli.verify_deliver_integrity`.
    """
    bin_path = shutil.which("des-verify-integrity")
    if bin_path:
        return [bin_path]
    return [sys.executable, "-m", "des.cli.verify_deliver_integrity"]


_VALID_ROADMAP: dict = {
    "roadmap": {
        "project_id": "roadmap-only-flag-fixture",
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


# Missing the `roadmap` block AND empty `phases` — guaranteed to produce
# MISSING_REQUIRED_FIELD errors at the validator level.
_MALFORMED_ROADMAP: dict = {
    "phases": [],
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
        "feature_id": "roadmap-only-flag-fixture",
        "events": events,
    }
    (deliver_dir / "execution-log.json").write_text(json.dumps(log), encoding="utf-8")


def _build_fixture(
    tmp_path: Path,
    *,
    roadmap_payload: dict,
    write_execution_log: bool,
) -> tuple[Path, Path]:
    """Build a project-root + deliver-dir fixture.

    Layout:
        tmp_path/
          feature/deliver/roadmap.json
          feature/deliver/execution-log.json   (if write_execution_log)

    Returns (project_root, deliver_dir).
    """
    project_root = tmp_path
    deliver_dir = tmp_path / "feature" / "deliver"
    deliver_dir.mkdir(parents=True)

    (deliver_dir / "roadmap.json").write_text(
        json.dumps(roadmap_payload), encoding="utf-8"
    )

    if write_execution_log:
        _write_execution_log(
            deliver_dir,
            step_id="01-01",
            phases=["PREPARE", "RED_ACCEPTANCE", "RED_UNIT", "GREEN", "COMMIT"],
        )

    return project_root, deliver_dir


def _run_verifier(
    project_root: Path,
    deliver_dir: Path,
    *,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Invoke `des-verify-integrity` as a subprocess with cwd=project_root."""
    cmd = _resolve_verify_integrity_cmd() + [str(deliver_dir)]
    if extra_args:
        cmd.extend(extra_args)
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
    "a feature dir with a well-formed roadmap and no execution-log file",
    target_fixture="scenario_state",
)
def _given_valid_roadmap_no_log(
    scenario_state: _ScenarioState, tmp_path: Path
) -> _ScenarioState:
    project_root, deliver_dir = _build_fixture(
        tmp_path,
        roadmap_payload=_VALID_ROADMAP,
        write_execution_log=False,
    )
    scenario_state.project_root = project_root
    scenario_state.deliver_dir = deliver_dir
    scenario_state.execution_log_present_before = (
        deliver_dir / "execution-log.json"
    ).exists()
    return scenario_state


@given(
    "a feature dir with a malformed roadmap and no execution-log file",
    target_fixture="scenario_state",
)
def _given_malformed_roadmap_no_log(
    scenario_state: _ScenarioState, tmp_path: Path
) -> _ScenarioState:
    project_root, deliver_dir = _build_fixture(
        tmp_path,
        roadmap_payload=_MALFORMED_ROADMAP,
        write_execution_log=False,
    )
    scenario_state.project_root = project_root
    scenario_state.deliver_dir = deliver_dir
    scenario_state.execution_log_present_before = (
        deliver_dir / "execution-log.json"
    ).exists()
    return scenario_state


@given(
    "a feature dir with a well-formed roadmap and a complete execution-log",
    target_fixture="scenario_state",
)
def _given_valid_roadmap_with_log(
    scenario_state: _ScenarioState, tmp_path: Path
) -> _ScenarioState:
    project_root, deliver_dir = _build_fixture(
        tmp_path,
        roadmap_payload=_VALID_ROADMAP,
        write_execution_log=True,
    )
    scenario_state.project_root = project_root
    scenario_state.deliver_dir = deliver_dir
    scenario_state.execution_log_present_before = (
        deliver_dir / "execution-log.json"
    ).exists()
    return scenario_state


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when(
    "the des-verify-integrity CLI runs with --roadmap-only against the feature dir",
    target_fixture="scenario_state",
)
def _when_cli_runs_with_flag(scenario_state: _ScenarioState) -> _ScenarioState:
    assert scenario_state.project_root is not None
    assert scenario_state.deliver_dir is not None
    proc = _run_verifier(
        scenario_state.project_root,
        scenario_state.deliver_dir,
        extra_args=["--roadmap-only"],
    )
    scenario_state.cli_returncode = proc.returncode
    scenario_state.cli_stdout = proc.stdout
    scenario_state.cli_stderr = proc.stderr
    scenario_state.used_flag = True
    return scenario_state


@when(
    "the des-verify-integrity CLI runs without --roadmap-only against the feature dir",
    target_fixture="scenario_state",
)
def _when_cli_runs_without_flag(scenario_state: _ScenarioState) -> _ScenarioState:
    assert scenario_state.project_root is not None
    assert scenario_state.deliver_dir is not None
    proc = _run_verifier(scenario_state.project_root, scenario_state.deliver_dir)
    scenario_state.cli_returncode = proc.returncode
    scenario_state.cli_stdout = proc.stdout
    scenario_state.cli_stderr = proc.stderr
    scenario_state.used_flag = False
    return scenario_state


@when(
    "the des-verify-integrity CLI runs with an unknown flag against the feature dir",
    target_fixture="scenario_state",
)
def _when_cli_runs_unknown_flag(scenario_state: _ScenarioState) -> _ScenarioState:
    assert scenario_state.project_root is not None
    assert scenario_state.deliver_dir is not None
    proc = _run_verifier(
        scenario_state.project_root,
        scenario_state.deliver_dir,
        extra_args=["--bogus-flag-not-defined"],
    )
    scenario_state.cli_returncode = proc.returncode
    scenario_state.cli_stdout = proc.stdout
    scenario_state.cli_stderr = proc.stderr
    scenario_state.used_unknown_flag = True
    return scenario_state


# ---------------------------------------------------------------------------
# Then steps — exit code
# ---------------------------------------------------------------------------


@then("the verifier exits with status 0")
def _then_exit_zero(scenario_state: _ScenarioState) -> None:
    assert scenario_state.cli_returncode == 0, (
        f"CLI returncode={scenario_state.cli_returncode}, "
        f"stdout={scenario_state.cli_stdout!r}, "
        f"stderr={scenario_state.cli_stderr!r}"
    )


@then("the verifier exits with non-zero status")
def _then_exit_nonzero(scenario_state: _ScenarioState) -> None:
    assert scenario_state.cli_returncode != 0, (
        f"Expected non-zero exit, got returncode={scenario_state.cli_returncode}; "
        f"stdout={scenario_state.cli_stdout!r}"
    )


# ---------------------------------------------------------------------------
# Then steps — roadmap-only happy path (A)
# ---------------------------------------------------------------------------


@then("the verifier skipped reading the execution-log")
def _then_skipped_execution_log(scenario_state: _ScenarioState) -> None:
    # Mechanical proof: execution-log was absent at fixture time AND the CLI
    # exited cleanly. If the verifier had attempted to read it, the legacy
    # path would have exited with code 2 and printed
    # "Error: execution-log.json not found".
    log_path = scenario_state.deliver_dir / "execution-log.json"
    log_present_after = log_path.exists()
    cli_complained_about_log = (
        "execution-log.json not found" in scenario_state.cli_stdout
        or "execution-log.json not found" in scenario_state.cli_stderr
    )
    # The "skip" predicate: log absent before & after, AND verifier did NOT
    # complain about its absence.
    skipped = (
        not scenario_state.execution_log_present_before
        and not log_present_after
        and not cli_complained_about_log
    )
    # Touched validator → stdout/stderr contains either validator-success
    # silence (clean exit 0, no errors), or a recognisable validator marker.
    touched_validator = scenario_state.cli_returncode == 0

    universe = {
        "cli.exit_code",
        "cli.skipped_execution_log",
        "cli.touched_validator",
    }
    before = {
        "cli.exit_code": None,
        "cli.skipped_execution_log": None,
        "cli.touched_validator": None,
    }
    after = {
        "cli.exit_code": scenario_state.cli_returncode,
        "cli.skipped_execution_log": skipped,
        "cli.touched_validator": touched_validator,
    }
    assert_state_delta(
        before,
        after,
        universe=universe,
        expected={
            "cli.exit_code": set_to(0),
            "cli.skipped_execution_log": set_to(True),
            "cli.touched_validator": set_to(True),
        },
        strict=True,
    )


# ---------------------------------------------------------------------------
# Then steps — roadmap-only error path (B)
# ---------------------------------------------------------------------------


@then("the verifier stdout reports schema errors")
def _then_stdout_reports_schema_errors(scenario_state: _ScenarioState) -> None:
    combined = scenario_state.cli_stdout + "\n" + scenario_state.cli_stderr
    # The validator prints "ROADMAP FORMAT ERRORS" or "MISSING_REQUIRED_FIELD"
    # when a malformed roadmap is rejected. Either marker counts.
    reports_errors = (
        "ROADMAP FORMAT ERRORS" in combined or "MISSING_REQUIRED_FIELD" in combined
    )
    log_path = scenario_state.deliver_dir / "execution-log.json"
    log_present_after = log_path.exists()
    cli_complained_about_log = (
        "execution-log.json not found" in scenario_state.cli_stdout
        or "execution-log.json not found" in scenario_state.cli_stderr
    )
    skipped = (
        not scenario_state.execution_log_present_before
        and not log_present_after
        and not cli_complained_about_log
    )

    universe = {
        "cli.exit_code",
        "cli.skipped_execution_log",
        "cli.stdout_reports_errors",
    }
    before = {
        "cli.exit_code": None,
        "cli.skipped_execution_log": None,
        "cli.stdout_reports_errors": None,
    }
    after = {
        "cli.exit_code": scenario_state.cli_returncode,
        "cli.skipped_execution_log": skipped,
        "cli.stdout_reports_errors": reports_errors,
    }
    assert_state_delta(
        before,
        after,
        universe=universe,
        expected={
            "cli.exit_code": lambda before_val, after_val: after_val != 0,
            "cli.skipped_execution_log": set_to(True),
            "cli.stdout_reports_errors": set_to(True),
        },
        strict=True,
    )


# ---------------------------------------------------------------------------
# Then steps — backward compat (C)
# ---------------------------------------------------------------------------


@then("the verifier output reports complete DES traces")
def _then_complete_traces(scenario_state: _ScenarioState) -> None:
    stdout = scenario_state.cli_stdout
    stdout_ok = "complete DES traces" in stdout

    universe = {"cli.exit_code", "cli.stdout_ok"}
    before = {"cli.exit_code": None, "cli.stdout_ok": None}
    after = {
        "cli.exit_code": scenario_state.cli_returncode,
        "cli.stdout_ok": stdout_ok,
    }
    assert_state_delta(
        before,
        after,
        universe=universe,
        expected={
            "cli.exit_code": set_to(0),
            "cli.stdout_ok": set_to(True),
        },
        strict=True,
    )


# ---------------------------------------------------------------------------
# Then steps — unknown flag (D)
# ---------------------------------------------------------------------------


@then("the verifier stderr contains the argparse usage banner")
def _then_stderr_contains_usage(scenario_state: _ScenarioState) -> None:
    combined = scenario_state.cli_stdout + "\n" + scenario_state.cli_stderr
    # argparse error banner: "usage:" prefix + the unknown flag mentioned in
    # the error line ("unrecognized arguments: --bogus-flag-not-defined").
    contains_usage = "usage:" in combined and (
        "--bogus-flag-not-defined" in combined or "unrecognized" in combined
    )

    universe = {"cli.exit_code", "cli.stderr_contains_usage"}
    before = {"cli.exit_code": None, "cli.stderr_contains_usage": None}
    after = {
        "cli.exit_code": scenario_state.cli_returncode,
        "cli.stderr_contains_usage": contains_usage,
    }
    assert_state_delta(
        before,
        after,
        universe=universe,
        expected={
            "cli.exit_code": lambda before_val, after_val: after_val != 0,
            "cli.stderr_contains_usage": set_to(True),
        },
        strict=True,
    )
