"""Step definitions: des-init-log respects the project's workflow mode.

ADR-028 D4.1 / slice 1 of 6 -- the walking-skeleton slice.

Layer 3 (subprocess/FS acceptance). Example-only, no PBT machinery
(Mandate 9/11). The one state-mutating step (`run des-init-log`) asserts via
`assert_state_delta` over a port-exposed filesystem universe (Mandate 8).

Step bodies delegate to `InitLogComposition`; no inline business logic
(Mandate-12 criterion 3).

Regression contract: these scenarios FAIL on master (des-init-log has no
mode-awareness -- it creates the log unconditionally, so the ATDD-pure
refusal scenario fails on the non-zero-exit assertion) and PASS once D4.1
lands.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.common.state_delta import assert_state_delta, set_to, unchanged

from .composition import InitLogComposition, InitLogResult
from .domain_types import FeatureId, WorkflowMode


scenarios("../init-log-mode-aware.feature")


@pytest.fixture
def composition(tmp_path: Path) -> InitLogComposition:
    """Production-wired composition root over a tmp_path deliver project."""
    return InitLogComposition(project_dir=tmp_path / "deliver")


@pytest.fixture
def result_box() -> dict[str, InitLogResult]:
    """Carrier for the des-init-log result across When -> Then steps."""
    return {}


@given(parsers.parse('a deliver project directory for feature "{feature_id}"'))
def given_project(composition: InitLogComposition, feature_id: str) -> None:
    composition.create_project(FeatureId(feature_id))


@given(parsers.parse('the project workflow mode is "{mode}"'))
def given_workflow_mode(composition: InitLogComposition, mode: str) -> None:
    composition.set_workflow_mode(WorkflowMode(mode))


@when("the operator runs des-init-log for that feature")
def when_run_init_log(
    composition: InitLogComposition, result_box: dict[str, InitLogResult]
) -> None:
    before = composition.capture_universe()
    result_box["result"] = composition.run_init_log()
    _assert_log_delta(composition, before, result_box["result"])


def _assert_log_delta(
    composition: InitLogComposition,
    before: dict[str, object],
    result: InitLogResult,
) -> None:
    """Universe-bound state-delta over the one observable: log file existence."""
    log_now_expected = set_to(True) if result.exit_code == 0 else unchanged()
    assert_state_delta(
        before=before,
        after=composition.capture_universe(),
        universe={"execution_log.exists"},
        expected={"execution_log.exists": log_now_expected},
    )


@then("des-init-log refuses with a non-zero exit code")
def then_refuses(result_box: dict[str, InitLogResult]) -> None:
    assert result_box["result"].exit_code != 0


@then("the refusal message explains ATDD-pure is execution-log-free")
def then_refusal_message(result_box: dict[str, InitLogResult]) -> None:
    message = result_box["result"].output.lower()
    assert "atdd-pure" in message and "execution-log" in message


@then("no execution log is created in the project directory")
def then_no_log(composition: InitLogComposition) -> None:
    assert not composition.execution_log_path.exists()


@then("des-init-log succeeds with a zero exit code")
def then_succeeds(result_box: dict[str, InitLogResult]) -> None:
    assert result_box["result"].exit_code == 0


@then(parsers.parse('an execution log is created for feature "{feature_id}"'))
def then_log_created(composition: InitLogComposition, feature_id: str) -> None:
    assert composition.execution_log_path.exists()
