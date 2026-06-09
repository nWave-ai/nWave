"""Step definitions: the G_COMMIT slice-commit-completeness + contract-gate exit gate.

slice-14 of the atdd-pure-roadmap-free-rollout. The exit-side symmetric
counterpart of slice-03's carpaccio entry gate; closes the RCA-diagnosed
"verification narrower than the contract" defect class.

Layer 3 (subprocess / FS / git acceptance). Example-only, no PBT machinery
(Mandate 9/11). `verify_slice_commit_completeness` has a pure-read git
contract: the one state-observing step asserts via `assert_state_delta` over a
port-exposed git-state universe that the exit gate mutates no commit and no
working-tree state (Mandate 8).

Step bodies delegate to `ExitGateComposition`; no inline business logic
(Mandate-12 criterion 3) -- each body is a typed lookup plus a composition call.

Regression contract: the slice-14 scenarios FAIL on master and PASS once
slice-14 lands. On master, `des.cli.run_contract_gate` and
`des.cli.verify_slice_commit_completeness` are RED scaffolds whose `main()`
raises AssertionError -- the exit gate cannot be evaluated, so every scenario
reds for the RIGHT reason (missing functionality), not ImportError.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.common.state_delta import assert_state_delta, unchanged

from .composition import ExitGateComposition, ExitGateResult
from .domain_types import (
    COMMIT_CONTENT_BY_PHRASE,
    DIGEST_STATE_BY_PHRASE,
    ExitGateVerdict,
    FeatureId,
)


scenarios("../slice-commit-completeness-exit-gate.feature")


@pytest.fixture
def composition(tmp_path: Path) -> ExitGateComposition:
    """Production-wired composition root over a tmp_path git repository."""
    return ExitGateComposition(repo_dir=tmp_path / "deliver")


@pytest.fixture
def result_box() -> dict[str, object]:
    """Carrier for the exit-gate result + the pre-evaluation universe snapshot."""
    return {}


# --- Given -------------------------------------------------------------------


@given(parsers.parse('a deliver repository for feature "{feature_id}"'))
def given_repository(composition: ExitGateComposition, feature_id: str) -> None:
    composition.create_repository(FeatureId(feature_id))


@given(
    "the operator has authored the slice's acceptance-test files and production code"
)
def given_slice_authored(composition: ExitGateComposition) -> None:
    composition.author_slice_at_files()
    composition.author_slice_production_code()


# --- When --------------------------------------------------------------------


@when(
    parsers.parse(
        "the operator commits a G_COMMIT commit that {commit_content} "
        "with a {digest_state} contract-gate digest"
    )
)
def when_commit_g_commit(
    composition: ExitGateComposition,
    commit_content: str,
    digest_state: str,
) -> None:
    composition.commit_g_commit(
        COMMIT_CONTENT_BY_PHRASE[commit_content],
        DIGEST_STATE_BY_PHRASE[digest_state],
    )


@when("the G_COMMIT exit gate is evaluated")
def when_evaluate_exit_gate(
    composition: ExitGateComposition,
    result_box: dict[str, object],
) -> None:
    result_box["universe_before"] = composition.capture_universe()
    result_box["result"] = composition.evaluate_g_commit_exit_gate()


# --- Then --------------------------------------------------------------------


def _result(result_box: dict[str, object]) -> ExitGateResult:
    return result_box["result"]  # type: ignore[return-value]


@then("the G_COMMIT exit gate fails")
def then_exit_gate_fails(result_box: dict[str, object]) -> None:
    assert _result(result_box).verdict is ExitGateVerdict.FAIL


@then("the G_COMMIT exit gate passes")
def then_exit_gate_passes(result_box: dict[str, object]) -> None:
    assert _result(result_box).verdict is ExitGateVerdict.PASS


@then("the exit-gate diagnostic names the missing acceptance-test files")
def then_diagnostic_names_missing_at_files(result_box: dict[str, object]) -> None:
    # E1 FAIL emits a JSON payload naming the missing .feature files. The demo
    # slice's AT file is `slice_99_demo.feature` -- its name MUST appear.
    output = _result(result_box).e1_output.lower()
    assert ".feature" in output and "slice_99_demo" in output


@then("the exit-gate diagnostic names the unverified contract-gate scope")
def then_diagnostic_names_unverified_scope(result_box: dict[str, object]) -> None:
    # E2 FAIL emits a diagnostic about the Gate-Scope: digest -- either absent
    # or mismatching a fresh --collect-only digest.
    output = _result(result_box).e2_output.lower()
    assert "gate-scope" in output or "gate scope" in output or "digest" in output


@then("the slice is not certified as shipped")
def then_not_shipped(result_box: dict[str, object]) -> None:
    # "shipped" is mechanical: a FAIL verdict means DES blocks G_COMMIT phase
    # completion -- the slice cannot reach COMMIT/PASS, so it is not shipped.
    assert _result(result_box).verdict is ExitGateVerdict.FAIL


@then("the slice is certified as shipped")
def then_shipped(result_box: dict[str, object]) -> None:
    # A PASS verdict is the mechanical, log-derivable basis for "shipped"
    # (RCA Gate 3, Branch C) -- not an agent's narrative claim.
    assert _result(result_box).verdict is ExitGateVerdict.PASS


@then("the exit gate leaves the repository unchanged")
def then_repository_unchanged(
    composition: ExitGateComposition,
    result_box: dict[str, object],
) -> None:
    # Mandate 8: verify_slice_commit_completeness has a pure-read git contract.
    # Evaluating the exit gate must create no commit and touch no working-tree
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
