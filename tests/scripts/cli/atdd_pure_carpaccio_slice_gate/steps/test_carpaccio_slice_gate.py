"""Step definitions: the carpaccio slice gate clears or blocks a slice.

ADR-028 D2-bis + ADR-029 D5 / slice-03 of the atdd-pure-roadmap-free-rollout.

Layer 3 (subprocess/FS acceptance). Example-only, no PBT machinery
(Mandate 9/11) -- the @property tag on the assertion-5 outline marks it as a
universal-invariant criterion (every rejection reason yields the same blocked
outcome), realised at this layer as a `Scenario Outline` enumerating the closed
six-value reason set, NOT a Hypothesis @given.

The gate has a pure-function contract (ADR-028 D2-bis): it MUST mutate no file.
The When-step asserts via `assert_state_delta` over a port-exposed filesystem
universe that NO repository file is written (Mandate 8).

Step bodies delegate to `CarpaccioGateComposition`; no inline business logic
(Mandate-12 criterion 3) -- each body is a typed lookup plus a composition call.

Regression contract: every scenario FAILS on master and PASSES once slice-03
lands. On master, `scripts/cli/carpaccio_slice_gate.py` does not exist, so the
`composition` import fails at collection -- a deliberate missing-functionality
RED (the gate CLI is unimplemented), not a test bug. Once slice-03 creates the
CLI the imports resolve and the assertions exercise real gate behaviour.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.common.state_delta import assert_state_delta, unchanged

from .composition import CarpaccioGateComposition, GateResult
from .domain_types import (
    AT_REVIEW_REASON_BY_PHRASE,
    MALFORMED_CAUSE_BY_PHRASE,
    SLICE_PLAN_SHAPE_BY_PHRASE,
    VERDICT_BY_PHRASE,
    ATReviewRecordState,
    FeatureId,
)


scenarios("../carpaccio-slice-gate.feature")


@pytest.fixture
def composition(tmp_path: Path) -> CarpaccioGateComposition:
    """Production-wired composition root over a tmp_path repository."""
    return CarpaccioGateComposition(repo_dir=tmp_path / "repo")


@pytest.fixture
def result_box() -> dict[str, GateResult]:
    """Carrier for the gate result across When -> Then steps."""
    return {}


# --- Given -------------------------------------------------------------------


@given("a repository for an atdd_pure feature")
def given_repository(composition: CarpaccioGateComposition) -> None:
    composition.create_repo(FeatureId("atdd-pure-demo"))


@given(parsers.parse("the feature carries {slice_plan}"))
def given_slice_plan(composition: CarpaccioGateComposition, slice_plan: str) -> None:
    composition.provision_slice_plan(SLICE_PLAN_SHAPE_BY_PHRASE[slice_plan])


@given("the entering slice has a recorded approved AT-review verdict")
def given_approved_verdict(composition: CarpaccioGateComposition) -> None:
    composition.provision_at_review_record(ATReviewRecordState.APPROVED_VALID)


@given("the carpaccio decomposition check would otherwise pass")
def given_carpaccio_would_pass(composition: CarpaccioGateComposition) -> None:
    # No-op precondition: the valid in-size slice plan provisioned above already
    # satisfies carpaccio assertions 1-4. The step exists so the chained
    # narrative reads explicitly (Pillar 2): assertion 5 is tested in isolation.
    assert composition.feature_delta_path.exists()


@given(parsers.parse('the AT-review state is "{at_review_condition}"'))
def given_at_review_condition(
    composition: CarpaccioGateComposition, at_review_condition: str
) -> None:
    record_state, _reason = AT_REVIEW_REASON_BY_PHRASE[at_review_condition]
    composition.provision_at_review_record(record_state)


# --- When --------------------------------------------------------------------


@when("the operator runs the carpaccio slice gate for the entering slice")
def when_run_gate(
    composition: CarpaccioGateComposition,
    result_box: dict[str, GateResult],
) -> None:
    before = composition.capture_universe()
    result_box["result"] = composition.run_gate()
    result_box["universe_before"] = before  # type: ignore[assignment]


# --- Then --------------------------------------------------------------------


@then("the slice is cleared to enter implementation")
def then_cleared(result_box: dict[str, GateResult]) -> None:
    result = result_box["result"]
    assert result.verdict is VERDICT_BY_PHRASE["cleared to enter implementation"]


@then(parsers.parse("the slice is {verdict_phrase}"))
def then_verdict(result_box: dict[str, GateResult], verdict_phrase: str) -> None:
    assert result_box["result"].verdict is VERDICT_BY_PHRASE[verdict_phrase]


@then("the gate records that the coupled slice was accepted")
def then_coupled_accepted(result_box: dict[str, GateResult]) -> None:
    payload = result_box["result"].payload
    assert payload.get("event") == "CoupledSliceAccepted"


@then(parsers.parse('the rejection names the reason "{reason}"'))
def then_rejection_reason(result_box: dict[str, GateResult], reason: str) -> None:
    payload = result_box["result"].payload
    assert payload.get("event") == "ATReviewGateRejected"
    assert payload.get("reason") == reason


@then(parsers.parse('the malformed-input diagnostic identifies "{cause_phrase}"'))
def then_malformed_cause(result_box: dict[str, GateResult], cause_phrase: str) -> None:
    """H2: exit 2 is reached by two differently-fixed conditions.

    The gate's emitted JSON diagnostic MUST name which input is malformed --
    the slice-plan table or a `.feature` slice tag -- so the operator knows
    which artifact to repair. Parallel to `then_rejection_reason` for exit 45.
    """
    expected = MALFORMED_CAUSE_BY_PHRASE[cause_phrase]
    assert result_box["result"].payload.get("cause") == expected.value


@then("the gate writes no file in the repository")
def then_gate_writes_no_file(
    composition: CarpaccioGateComposition,
    result_box: dict[str, GateResult],
) -> None:
    """Pure-function contract: the gate mutates no repository file (Mandate 8).

    The universe is every file the gate reads -- the feature-delta, the slice
    `.feature`, the AT-completion ledger, the workflow config. Each is asserted
    `unchanged`: same existence and same bytes before and after the gate runs.
    """
    assert_state_delta(
        before=result_box["universe_before"],  # type: ignore[arg-type]
        after=composition.capture_universe(),
        universe={
            "feature_delta.exists",
            "feature_delta.bytes",
            "feature_file.exists",
            "feature_file.bytes",
            "ledger.exists",
            "ledger.bytes",
            "config.bytes",
        },
        expected={
            "feature_delta.exists": unchanged(),
            "feature_delta.bytes": unchanged(),
            "feature_file.exists": unchanged(),
            "feature_file.bytes": unchanged(),
            "ledger.exists": unchanged(),
            "ledger.bytes": unchanged(),
            "config.bytes": unchanged(),
        },
    )
