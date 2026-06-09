"""Step definitions: F-07 multi-`Slice-Id:` batched-commit completeness gate.

Friction F-07 (docs/analysis/atdd-pure-dogfooding-friction-2026-05-20.md). The
slice-commit-completeness exit gate must accept a batched commit listing
multiple `Slice-Id:` trailers and verify completeness for EACH listed slice.

Layer 3 (subprocess / FS / git acceptance). Example-only, no PBT machinery
(Mandate 9/11) -- sad paths are enumerated. The PASS scenario asserts via
`assert_state_delta` over a port-exposed git-state universe that the exit gate
mutates no commit and no working-tree state (Mandate 8).

Step bodies delegate to `MultiSliceComposition`; no inline business logic
(Mandate-12 criterion 3) -- each body is a typed lookup plus a composition call.

Regression contract: the two MULTIPLE-trailer scenarios FAIL on master (the
current gate reads only the first `Slice-Id:` trailer; multi-trailer handling
is absent -- MISSING_FUNCTIONALITY). The SINGLE-trailer and NONE-trailer
scenarios are no-regression pins and already pass on master.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.common.state_delta import assert_state_delta, unchanged

from .composition import (
    DEFICIENT_SLICE,
    CompletenessResult,
    MultiSliceComposition,
)
from .domain_types import (
    SLICE_COVERAGE_BY_PHRASE,
    TRAILER_SHAPE_BY_PHRASE,
    ExitGateVerdict,
)


scenarios("../multi-slice-trailer-completeness.feature")


@pytest.fixture
def composition(tmp_path: Path) -> MultiSliceComposition:
    """Production-wired composition root over a tmp_path git repository."""
    return MultiSliceComposition(repo_dir=tmp_path / "deliver")


@pytest.fixture
def result_box() -> dict[str, object]:
    """Carrier for the exit-gate result + the pre-evaluation universe snapshot."""
    return {}


# --- Given -------------------------------------------------------------------


@given("a deliver repository for an interleaved multi-slice session")
def given_repository(composition: MultiSliceComposition) -> None:
    composition.create_repository()


@given(
    "the operator has authored each slice's acceptance-test files and production code"
)
def given_slices_authored(composition: MultiSliceComposition) -> None:
    composition.author_batched_slices()


# --- When --------------------------------------------------------------------


@when(
    parsers.parse(
        "the operator commits a batched commit carrying {trailer_shape} "
        "with {slice_coverage}"
    )
)
def when_commit_batched(
    composition: MultiSliceComposition,
    trailer_shape: str,
    slice_coverage: str,
) -> None:
    composition.commit_batched(
        TRAILER_SHAPE_BY_PHRASE[trailer_shape],
        SLICE_COVERAGE_BY_PHRASE[slice_coverage],
    )


@when("the slice-commit-completeness exit gate is evaluated")
def when_evaluate_gate(
    composition: MultiSliceComposition,
    result_box: dict[str, object],
) -> None:
    result_box["universe_before"] = composition.capture_universe()
    result_box["result"] = composition.evaluate_completeness_gate()


# --- Then --------------------------------------------------------------------


def _result(result_box: dict[str, object]) -> CompletenessResult:
    return result_box["result"]  # type: ignore[return-value]


@then("the exit gate accepts the batched commit")
def then_gate_accepts(result_box: dict[str, object]) -> None:
    assert _result(result_box).verdict is ExitGateVerdict.ACCEPTED


@then("the exit gate rejects the batched commit")
def then_gate_rejects(result_box: dict[str, object]) -> None:
    assert _result(result_box).verdict is ExitGateVerdict.REJECTED


@then("the exit-gate result reports completeness for every listed slice")
def then_reports_every_slice(result_box: dict[str, object]) -> None:
    # The batched commit lists slice-01 and slice-02. A multi-trailer-aware
    # gate must report a completeness verdict that accounts for BOTH slices --
    # the JSON payload names every listed slice, not just the first one.
    output = _result(result_box).output
    assert "slice-01" in output and "slice-02" in output


@then("the exit-gate diagnostic reports malformed input")
def then_reports_malformed_input(result_box: dict[str, object]) -> None:
    # A zero-trailer commit cannot be verified -- the gate exits 2 and emits a
    # MalformedInput diagnostic. The F-07 fix must not loosen this pin.
    output = _result(result_box).output.lower()
    assert _result(result_box).exit_code == 2
    assert "malformedinput" in output or "malformed input" in output


@then("the exit-gate diagnostic names the deficient slice")
def then_names_deficient_slice(result_box: dict[str, object]) -> None:
    # One listed slice's `.feature` AT files were authored but never staged.
    # The diagnostic must name THAT slice so the operator knows which slice's
    # ATs to add -- naming only the first listed slice would mask the defect.
    output = _result(result_box).output
    assert DEFICIENT_SLICE in output and ".feature" in output.lower()


@then("the exit gate leaves the repository unchanged")
def then_repository_unchanged(
    composition: MultiSliceComposition,
    result_box: dict[str, object],
) -> None:
    # Mandate 8: verify_slice_commit_completeness has a pure-read git contract.
    # Evaluating the gate must create no commit and touch no working-tree
    # state -- both universe entries are `unchanged`.
    assert_state_delta(
        before=result_box["universe_before"],  # type: ignore[arg-type]
        after=composition.capture_universe(),
        universe={"git.head_sha", "git.status_porcelain"},
        expected={
            "git.head_sha": unchanged(),
            "git.status_porcelain": unchanged(),
        },
    )
