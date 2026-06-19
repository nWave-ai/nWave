"""Step definitions: the slice-plan validator clears or rejects a slice plan.

ADR-028 D2 / D2-bis + ADR-029 D3 / slice-06 of the atdd-pure-roadmap-free-rollout.

Layer 3 (subprocess/FS acceptance). Example-only, no PBT machinery
(Mandate 9/11): the slice-plan shapes form a finite, enumerable closed set
(well-formed / many-rows / section-absent / four-columns / header-only /
columns-reordered / malformed-heading), so a `Scenario Outline` over the closed
set is the correct paradigm -- the falsifier-gate forbids PBT on a closed-world
finite domain.

The validator has a pure-function contract (it reads the feature-delta and
returns a verdict). The When-step asserts via `assert_state_delta` over a
port-exposed filesystem universe that the feature-delta is NOT mutated
(Mandate 8).

Step bodies delegate to `SlicePlanValidationComposition`; no inline business
logic (Mandate-12 criterion 3) -- each body is a typed lookup plus a
composition call.

Regression contract: every slice-plan acceptance / rejection assertion FAILS
on master and PASSES once slice-06 lands. On master, `validate_feature_delta`'s
`main` does not accept `--require-slice-plan`; invoked with two arguments it
prints usage and returns exit 1, so a well-formed feature-delta is reported as
a rejection -- a deliberate missing-functionality RED (wrong verdict), not a
test bug. The plain-heading-check scenario passes on master (the existing
contract is unchanged) -- it pins the no-regression guarantee.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.common.state_delta import assert_state_delta, unchanged

from .composition import SlicePlanValidationComposition, ValidationResult
from .domain_types import (
    CHECK_MODE_BY_PHRASE,
    SLICE_PLAN_SHAPE_BY_PHRASE,
    VERDICT_BY_PHRASE,
    FeatureId,
)


scenarios("../slice-plan-validation.feature")


@pytest.fixture
def composition(tmp_path: Path) -> SlicePlanValidationComposition:
    """Production-wired composition root over a tmp_path repository."""
    return SlicePlanValidationComposition(repo_dir=tmp_path / "repo")


@pytest.fixture
def result_box() -> dict[str, object]:
    """Carrier for the validation result + universe across When -> Then steps."""
    return {}


# --- Given -------------------------------------------------------------------


@given("a feature-delta authored for an atdd_pure feature")
def given_feature(composition: SlicePlanValidationComposition) -> None:
    composition.create_feature(FeatureId("atdd-pure-demo"))


@given(parsers.parse("the feature-delta carries {slice_plan}"))
def given_slice_plan(
    composition: SlicePlanValidationComposition, slice_plan: str
) -> None:
    composition.provision_feature_delta(SLICE_PLAN_SHAPE_BY_PHRASE[slice_plan])


# --- When --------------------------------------------------------------------


@when(parsers.parse("the Product Owner runs {check_mode} on the feature-delta"))
def when_run_check(
    composition: SlicePlanValidationComposition,
    result_box: dict[str, object],
    check_mode: str,
) -> None:
    result_box["universe_before"] = composition.capture_universe()
    result_box["result"] = composition.run_check(CHECK_MODE_BY_PHRASE[check_mode])


# --- Then --------------------------------------------------------------------


@then(parsers.parse("the slice plan is {verdict_phrase}"))
def then_verdict(result_box: dict[str, object], verdict_phrase: str) -> None:
    result = result_box["result"]
    assert isinstance(result, ValidationResult)
    assert result.verdict is VERDICT_BY_PHRASE[verdict_phrase]


@then("the check leaves the feature-delta unchanged")
def then_feature_delta_unchanged(
    composition: SlicePlanValidationComposition,
    result_box: dict[str, object],
) -> None:
    """Pure-function contract: the validator mutates no file (Mandate 8).

    The universe is the feature-delta's existence and bytes; both are asserted
    `unchanged` -- same existence and same bytes before and after the check.
    """
    assert_state_delta(
        before=result_box["universe_before"],  # type: ignore[arg-type]
        after=composition.capture_universe(),
        universe={"feature_delta.exists", "feature_delta.bytes"},
        expected={
            "feature_delta.exists": unchanged(),
            "feature_delta.bytes": unchanged(),
        },
    )
