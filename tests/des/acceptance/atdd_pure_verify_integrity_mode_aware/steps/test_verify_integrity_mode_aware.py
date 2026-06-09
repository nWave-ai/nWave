"""Step definitions: des-verify-integrity respects the project's workflow mode.

ADR-028 D4.2 / slice-02 of the atdd-pure-roadmap-free-rollout.

Layer 3 (subprocess/FS acceptance). Example-only, no PBT machinery
(Mandate 9/11). The verifier has a pure-read contract: the one state-observing
step asserts via `assert_state_delta` over a port-exposed filesystem universe
that NO project file is mutated (Mandate 8).

Step bodies delegate to `VerifyIntegrityComposition`; no inline business logic
(Mandate-12 criterion 3) -- each body is a typed lookup plus a composition call.

Regression contract: the atdd_pure scenarios FAIL on master and PASS once
slice-02 lands. On master, des-verify-integrity reads `roadmap.json` first and
returns exit 2 the instant it is absent -- before any `workflow.mode` check
exists. The classic / unset scenarios PASS on master AND after slice-02: they
pin the no-regression limb (ADR-028 D4.2 limb 4) so a mode-aware EXTEND cannot
silently break the existing 0/1 contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.common.state_delta import assert_state_delta, unchanged

from .composition import VerifyIntegrityComposition, VerifyIntegrityResult
from .domain_types import (
    CLASSIC_SHAPE_BY_PHRASE,
    VERDICT_BY_PHRASE,
    FeatureId,
    IntegrityVerdict,
    LedgerState,
    LeftoverRoadmap,
    VerifyInvocation,
    WorkflowMode,
)


scenarios("../verify-integrity-mode-aware.feature")


@pytest.fixture
def composition(tmp_path: Path) -> VerifyIntegrityComposition:
    """Production-wired composition root over a tmp_path deliver project."""
    return VerifyIntegrityComposition(project_dir=tmp_path / "deliver")


@pytest.fixture
def result_box() -> dict[str, VerifyIntegrityResult]:
    """Carrier for the des-verify-integrity result across When -> Then steps."""
    return {}


# --- Given -------------------------------------------------------------------


@given(parsers.parse('a deliver project directory for feature "{feature_id}"'))
def given_project(composition: VerifyIntegrityComposition, feature_id: str) -> None:
    composition.create_project(FeatureId(feature_id))


@given(parsers.parse('the project workflow mode is "{mode}"'))
def given_workflow_mode(composition: VerifyIntegrityComposition, mode: str) -> None:
    composition.set_workflow_mode(WorkflowMode(mode))


@given("the AT-completion ledger is present with every slice shipped")
def given_ledger_present(composition: VerifyIntegrityComposition) -> None:
    composition.provision_ledger(LedgerState.PRESENT_ALL_SHIPPED)


@given("the AT-completion ledger is absent")
def given_ledger_absent(composition: VerifyIntegrityComposition) -> None:
    composition.provision_ledger(LedgerState.ABSENT)


@given(parsers.parse('a leftover roadmap is "{leftover}" in the project directory'))
def given_leftover_roadmap(
    composition: VerifyIntegrityComposition, leftover: str
) -> None:
    composition.provision_leftover_roadmap(LeftoverRoadmap(leftover))


@given(parsers.parse('a classic deliver project with "{trace_completeness}"'))
def given_classic_project(
    composition: VerifyIntegrityComposition, trace_completeness: str
) -> None:
    composition.provision_classic_project(CLASSIC_SHAPE_BY_PHRASE[trace_completeness])


# --- When --------------------------------------------------------------------


@when("the operator runs des-verify-integrity for that feature")
def when_run_verify_integrity(
    composition: VerifyIntegrityComposition,
    result_box: dict[str, VerifyIntegrityResult],
) -> None:
    before = composition.capture_universe()
    result_box["result"] = composition.run_verify_integrity(VerifyInvocation.FULL)
    _assert_pure_read(composition, before)


@when("the operator runs des-verify-integrity with --roadmap-only for that feature")
def when_run_verify_integrity_roadmap_only(
    composition: VerifyIntegrityComposition,
    result_box: dict[str, VerifyIntegrityResult],
) -> None:
    before = composition.capture_universe()
    result_box["result"] = composition.run_verify_integrity(
        VerifyInvocation.ROADMAP_ONLY
    )
    _assert_pure_read(composition, before)


def _assert_pure_read(
    composition: VerifyIntegrityComposition,
    before: dict[str, object],
) -> None:
    """Universe-bound state-delta: des-verify-integrity mutates no project file.

    The verifier reads roadmap.json / execution-log.json / the ledger; it must
    never create or delete any of them. Every universe entry is `unchanged`.
    """
    assert_state_delta(
        before=before,
        after=composition.capture_universe(),
        universe={
            "roadmap.json.exists",
            "execution_log.json.exists",
            "ledger.exists",
        },
        expected={
            "roadmap.json.exists": unchanged(),
            "execution_log.json.exists": unchanged(),
            "ledger.exists": unchanged(),
        },
    )


# --- Then --------------------------------------------------------------------


@then("des-verify-integrity reports the feature verified")
def then_verified(result_box: dict[str, VerifyIntegrityResult]) -> None:
    assert result_box["result"].verdict is IntegrityVerdict.VERIFIED


@then("des-verify-integrity reports an integrity violation")
def then_violation(result_box: dict[str, VerifyIntegrityResult]) -> None:
    assert result_box["result"].verdict is IntegrityVerdict.VIOLATION


@then(parsers.parse('des-verify-integrity reports "{verdict_phrase}"'))
def then_verdict(
    result_box: dict[str, VerifyIntegrityResult], verdict_phrase: str
) -> None:
    assert result_box["result"].verdict is VERDICT_BY_PHRASE[verdict_phrase]


@then("the diagnostic message names the missing AT-completion ledger")
def then_diagnostic_names_ledger(
    result_box: dict[str, VerifyIntegrityResult],
) -> None:
    message = result_box["result"].output.lower()
    assert "ledger" in message


@then("des-verify-integrity does not crash")
def then_no_crash(result_box: dict[str, VerifyIntegrityResult]) -> None:
    # A crash would surface as an uncaught exception before `result` is set,
    # or as the argparse usage-error exit code 2. A graceful diagnostic is
    # exit 1 (VIOLATION) with a non-empty message.
    result = result_box["result"]
    assert result.verdict is not IntegrityVerdict.USAGE_ERROR
    assert result.output.strip() != ""


@then("des-verify-integrity does not fail for a missing roadmap")
def then_no_missing_roadmap_failure(
    result_box: dict[str, VerifyIntegrityResult],
) -> None:
    # On master, --roadmap-only with no roadmap returns exit 2 (USAGE_ERROR)
    # with a "roadmap.json not found" message. Under atdd_pure the flag is a
    # no-op: neither the usage-error verdict nor the missing-roadmap message.
    result = result_box["result"]
    assert result.verdict is not IntegrityVerdict.USAGE_ERROR
    assert "not found" not in result.output.lower()


def _assert_roadmap_reported_as_warning(
    composition: VerifyIntegrityComposition, result: VerifyIntegrityResult
) -> None:
    """A leftover roadmap is surfaced as a WARNING, never a verdict-changing error."""
    message = result.output.lower()
    assert "warning" in message and "roadmap" in message


def _assert_roadmap_not_required(
    composition: VerifyIntegrityComposition, result: VerifyIntegrityResult
) -> None:
    """No roadmap is required, and the verifier creates none (atdd_pure default)."""
    assert not composition.roadmap_path.exists()


# Gherkin-phrase -> roadmap-treatment assertion. Keeping the dispatch in a
# module-level dict lets the parsed `@then` body stay a single statement with
# no control flow (Mandate-12 criterion 3).
_ROADMAP_TREATMENT_ASSERTIONS = {
    "reported as a warning": _assert_roadmap_reported_as_warning,
    "not required and not created": _assert_roadmap_not_required,
}


@then(parsers.parse('the leftover roadmap is treated as "{treatment}"'))
def then_leftover_roadmap_treatment(
    composition: VerifyIntegrityComposition,
    result_box: dict[str, VerifyIntegrityResult],
    treatment: str,
) -> None:
    _ROADMAP_TREATMENT_ASSERTIONS[treatment](composition, result_box["result"])
