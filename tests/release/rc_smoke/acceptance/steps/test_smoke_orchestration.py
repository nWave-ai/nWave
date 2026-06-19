"""Tier A step definitions — smoke-lane orchestration + exit-code contract.

Driving port: the harness CLI (``scripts.release.rc_smoke.__main__.main``) and
the ``SmokeRunner`` application surface. Driven ports (install / boot / fs) are
in-memory fakes — the real cross-OS install runs ONLY in the
``validate-rc-multitool`` CI gate (SPIKE is the empirical e2e proof).

Layer 2 in-memory acceptance (Mandate 9): example-based per scenario; the
failure-combination property lives in the unit suite
(``test_smoke_runner_failure_property.py``) where PBT is cheap.

Step bodies delegate to the composition / fakes and assert against
port-exposed observables (lane verdict, exit code, recorded port calls);
no business logic is inlined (Mandate-12 criterion 3).
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, scenarios, then, when

from scripts.release.rc_smoke.result import SmokeDepth
from tests.common.state_delta import assert_state_delta, set_to
from tests.release.rc_smoke.acceptance.steps.composition import (
    build_composition,
    contract_for,
)
from tests.release.rc_smoke.acceptance.steps.domain_types import (
    EXIT_FAIL_NONZERO,
    EXIT_PASS,
    ScriptedStep,
    SmokeStepKind,
    Tool,
)
from tests.release.rc_smoke.acceptance.steps.fakes import (
    FakeFileSystem,
    FakeInstaller,
    FakeProcess,
)


scenarios("../smoke-orchestration.feature")


# --- fixtures --------------------------------------------------------------


@pytest.fixture
def run_state() -> dict:
    """Mutable carrier across Given/When/Then for one scenario."""
    return {
        "scripted_install": {},
        "scripted_boot": {},
        "present_globs": set(),
        "tool": Tool.CLAUDE_CODE,
    }


# --- Given -----------------------------------------------------------------


@given("a published release candidate and an isolated install target")
def given_published_rc_and_isolated_target(run_state, tmp_path):
    run_state["version"] = "9.9.9rc1"
    run_state["target"] = tmp_path / "isolated"


@given("the tool installs, provisions, boots, and writes its nWave artifacts")
def given_all_steps_succeed(run_state):
    contract = contract_for(run_state["tool"])
    run_state["present_globs"] = set(contract.required_artifact_globs)


@given("installing the published package aborts")
def given_install_aborts(run_state):
    run_state["scripted_install"][SmokeStepKind.INSTALL_PUBLISHED] = ScriptedStep(
        SmokeStepKind.INSTALL_PUBLISHED, succeeds=False, diagnostic="install aborted"
    )


@given("the tool is installed and provisioned but fails to boot")
def given_boot_fails(run_state):
    contract = contract_for(run_state["tool"])
    run_state["present_globs"] = set(contract.required_artifact_globs)
    run_state["scripted_boot"][SmokeStepKind.BOOT] = ScriptedStep(
        SmokeStepKind.BOOT, succeeds=False, diagnostic="boot failed"
    )


@given("the tool boots but provisioned no real nWave artifacts")
def given_no_artifacts(run_state):
    run_state["present_globs"] = set()


@given("the tool boots and only a bare config directory exists")
def given_bare_dir_only(run_state):
    # A bare directory is NOT a real artifact: present_globs stays empty even
    # though "the dir exists" — this is the codex false-PASS discriminator.
    run_state["present_globs"] = set()


# --- When ------------------------------------------------------------------


def _run_lane(run_state) -> None:
    comp = build_composition(
        installer=FakeInstaller(scripted=run_state["scripted_install"]),
        process=FakeProcess(scripted=run_state["scripted_boot"]),
        filesystem=FakeFileSystem(present_globs=run_state["present_globs"]),
    )
    contract = contract_for(run_state["tool"])
    run_state["comp"] = comp
    run_state["result"] = comp.runner.run(
        contract=contract,
        version=run_state["version"],
        target=run_state["target"],
        depth=SmokeDepth.BOOT,
    )


@when("the release engineer runs the smoke lane")
def when_run_lane(run_state):
    _run_lane(run_state)


@when("the release engineer runs the smoke lane twice")
def when_run_lane_twice(run_state):
    _run_lane(run_state)
    run_state["result_first"] = run_state["result"]
    _run_lane(run_state)
    run_state["result_second"] = run_state["result"]


# --- Then ------------------------------------------------------------------


@then("the lane passes")
def then_lane_passes(run_state):
    before = {"lane.passed": None}
    after = {"lane.passed": run_state["result"].passed}
    assert_state_delta(
        before,
        after,
        universe={"lane.passed"},
        expected={"lane.passed": set_to(True)},
    )


@then("the lane fails")
def then_lane_fails(run_state):
    before = {"lane.passed": None}
    after = {"lane.passed": run_state["result"].passed}
    assert_state_delta(
        before,
        after,
        universe={"lane.passed"},
        expected={"lane.passed": set_to(False)},
    )


@then("the harness reports success to the release pipeline")
def then_reports_success(run_state):
    assert run_state["result"].passed is True
    # exit-code contract (L1): a passing lane maps to EXIT_PASS.
    assert _exit_code_for(run_state["result"]) == EXIT_PASS


@then("the harness reports failure to the release pipeline")
def then_reports_failure(run_state):
    assert run_state["result"].passed is False
    assert _exit_code_for(run_state["result"]) == EXIT_FAIL_NONZERO


@then("the failure names the install step in a readable diagnostic")
def then_names_install_step(run_state):
    diag = run_state["result"].diagnostics
    assert "install" in diag.lower(), f"diagnostic did not name install: {diag!r}"


@then("the failure names the missing artifacts in a readable diagnostic")
def then_names_missing_artifacts(run_state):
    diag = run_state["result"].diagnostics
    contract = contract_for(run_state["tool"])
    assert any(g in diag for g in contract.required_artifact_globs), (
        f"diagnostic did not name a missing artifact: {diag!r}"
    )


@then("both runs pass with the same verdict")
def then_both_runs_same_verdict(run_state):
    first = run_state["result_first"].passed
    second = run_state["result_second"].passed
    assert first is True and second is True, (first, second)
    assert first is second, (
        "idempotency violated: re-running the lane changed the verdict"
    )


@then("every install and artifact check used the isolated target only")
def then_isolation_respected(run_state):
    target = str(run_state["target"])
    inst_targets = [
        t for (kind, t) in run_state["comp"].installer.calls if kind == "provision"
    ]
    fs_targets = run_state["comp"].filesystem.calls
    assert inst_targets == [target], inst_targets
    assert fs_targets == [target], fs_targets


# --- helpers ---------------------------------------------------------------


def _exit_code_for(result) -> int:
    """Local mirror of the L1 exit-code contract for assertion purposes."""
    return EXIT_PASS if result.passed else EXIT_FAIL_NONZERO
