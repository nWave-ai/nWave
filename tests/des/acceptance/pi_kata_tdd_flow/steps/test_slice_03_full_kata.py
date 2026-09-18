"""Acceptance steps: Slice 03 -- solve a kata end-to-end, strictly verified.

Driving ports = multi-step recording (reused des-log-phase) verified by the
UNCHANGED subagent-stop adapter via the NEW synthesized transcript (KD4). Real
tmp git repo + real reused CLIs (@real-io @adapter-integration), example-only
(Mandate 11), no PBT (Mandate 9). The single live-model end-to-end run is
@requires_external (skipped); its deterministic analog is asserted model-free.
Engine reused UNCHANGED (K2). Fresh step-id per cycle (SPIKE constraint 3).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.des.acceptance.pi_kata_tdd_flow.steps import kata_support as support
from tests.des.acceptance.pi_kata_tdd_flow.steps.domain_types import TddPhase


scenarios("../slice-03-full-kata.feature")

_PLAN = ("01-01", "01-02", "01-03", "01-04", "01-05")


@pytest.fixture
def world(tmp_path: Path) -> dict:
    return {"project": support.make_activated_project(tmp_path)}


# --------------------------------------------------------------------------- #
# Given
# --------------------------------------------------------------------------- #


@given(parsers.parse('a kata "{kata_id}" decomposed into an ordered step-by-step plan'))
def _decomposed(world: dict, kata_id: str) -> None:
    world["kata_id"], world["plan"] = kata_id, list(_PLAN)
    support.bootstrap_session(world["project"], kata_id)


@given("an earlier step was completed and committed")
def _earlier_committed(world: dict) -> None:
    step = world["plan"][0]
    support.record_complete_cycle(world["project"], world["kata_id"], step)
    support.commit_with_trailers(world["project"], step, world["kata_id"])
    world["earlier_step"] = step


@given("a later step is committed without recording its cycle")
def _later_skipped(world: dict) -> None:
    world["skipped_step"] = world["plan"][1]
    # The crafter wrote code for this step but skipped recording its cycle, so the
    # commit carries real content yet no RED/GREEN/COMMIT phases — the boundary
    # must then block on the incomplete cycle. Without a change there is nothing
    # to commit (the prior step left the tree clean), so create one here.
    (world["project"] / f"step_{world['skipped_step']}.py").write_text(
        "# implementation committed without a recorded TDD cycle\n",
        encoding="utf-8",
    )
    support.commit_with_trailers(world["project"], world["plan"][1], world["kata_id"])


@given(
    parsers.parse(
        'a kata "{kata_id}" with a step "{step_id}" recorded as a completed increment'
    )
)
def _step_completed(world: dict, kata_id: str, step_id: str) -> None:
    world["kata_id"], world["step_id"] = kata_id, step_id
    support.bootstrap_session(world["project"], kata_id)
    support.record_complete_cycle(world["project"], kata_id, step_id)
    support.commit_with_trailers(world["project"], step_id, kata_id)


@given("the current step records a complete RED then GREEN then COMMIT cycle")
def _records_complete_cycle(world: dict) -> None:
    step = support.current_step(world["project"], world["kata_id"])
    world["step_id"] = step
    support.record_complete_cycle(world["project"], world["kata_id"], step)


@given("the current step records only a RED phase")
def _records_only_red(world: dict) -> None:
    step = support.current_step(world["project"], world["kata_id"])
    world["step_id"] = step
    support.record_phase_only(world["project"], world["kata_id"], step, TddPhase.RED)


@given("the kata manifest step-id is reverted to an earlier step mid-kata")
def _revert_manifest(world: dict) -> None:
    world["step_id"] = "01-01"


@given("a real pi model backend is available")
def _model_backend(world: dict) -> None:
    pytest.skip("requires a live pi model backend (SPIKE-0 CI caveat, R4)")


@given(
    parsers.parse(
        'the crafter is invoked with the kata "{kata_id}" in an activated pi project'
    )
)
def _crafter_invoked_live(world: dict, kata_id: str) -> None:  # pragma: no cover
    raise AssertionError("unreachable: model backend skip fires first")


# --------------------------------------------------------------------------- #
# When
# --------------------------------------------------------------------------- #


@when("the crafter completes every planned step in order")
def _complete_all_steps(world: dict) -> None:
    # The manifest's current step-id is the source of truth for which step the
    # next cycle records; between cycles the harness advances it deterministically
    # (advance_step_id) so each RED gets a FRESH NN-NN -- never reusing a step-id
    # (SPIKE constraint 3) that would trip the engine's second-attempt-allow.
    for index, _planned in enumerate(world["plan"]):
        step = support.current_step(world["project"], world["kata_id"])
        support.record_complete_cycle(world["project"], world["kata_id"], step)
        support.commit_with_trailers(world["project"], step, world["kata_id"])
        if index < len(world["plan"]) - 1:
            support.advance_to_next_step(world["project"], world["kata_id"])


@when("the skipped step is validated at the commit boundary")
def _validate_skipped(world: dict) -> None:
    code, out = support.validate_at_commit_boundary(
        world["project"], world["kata_id"], world["skipped_step"]
    )
    world["exit"], world["stdout"] = code, out


@when("the step completion is validated at the commit boundary")
def _validate_boundary(world: dict) -> None:
    code, out = support.validate_at_commit_boundary(
        world["project"], world["kata_id"], world["step_id"]
    )
    world["exit"], world["stdout"] = code, out


@when("the step completion is validated at the pre-commit boundary before committing")
def _validate_pre_commit(world: dict) -> None:
    code, out = support.validate_at_commit_boundary_pre_commit(
        world["project"], world["kata_id"], world["step_id"]
    )
    world["exit"], world["stdout"] = code, out


@when("the crafter solves the kata through self-driven strict TDD")
def _solve_live(world: dict) -> None:  # pragma: no cover - skipped path
    raise AssertionError("unreachable: model backend skip fires first")


# --------------------------------------------------------------------------- #
# Then
# --------------------------------------------------------------------------- #


def _events(world: dict) -> list[dict]:
    log = support.deliver_dir(world["project"], world["kata_id"]) / "execution-log.json"
    return json.loads(log.read_text()).get("events", []) if log.exists() else []


@then("each step shows RED then GREEN then COMMIT in plan order")
def _plan_order_phases(world: dict) -> None:
    seen = [(e["sid"], e["p"]) for e in _events(world)]
    expected = [(s, p) for s in world["plan"] for p in ("RED", "GREEN", "COMMIT")]
    assert seen == expected


@then("the Step-Id commit history matches the planned step order")
def _commit_order(world: dict) -> None:
    trailers = _git_step_id_trailers(world["project"])
    assert trailers == world["plan"]


def _git_step_id_trailers(project: Path) -> list[str]:
    import subprocess

    out = subprocess.run(
        ["git", "log", "--reverse", "--format=%(trailers:key=Step-Id,valueonly)"],
        cwd=str(project),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


@then("the step completion is rejected at the commit boundary with a reason")
def _rejected_with_reason(world: dict) -> None:
    parsed = json.loads(world["stdout"])
    assert parsed.get("decision") == "block" and parsed.get("reason")


@then("the step completion is allowed at the pre-commit boundary")
def _allowed_pre_commit(world: dict) -> None:
    # ALLOW = exit 0 + empty stdout (no block JSON). R1: a genuine verified
    # allow emits SUBAGENT_STOP_PASSED -- it must NOT be a non-DES passthrough.
    assert world["exit"] == 0, (
        f"expected ALLOW, got exit {world['exit']}: {world['stdout']!r}"
    )
    assert world["stdout"].strip() == "", f"unexpected stdout: {world['stdout']!r}"
    types = _event_types(world)
    assert "HOOK_SUBAGENT_STOP_PASSED" in types, (
        f"expected a genuine SUBAGENT_STOP_PASSED verdict (R1), got events: {types}"
    )


def _event_types(world: dict) -> list[str]:
    return [e.get("event") for e in support.audit_events(world["project"])]


@then("the commit gate never attempted commit verification")
def _no_commit_verification(world: dict) -> None:
    events = support.audit_events(world["project"])
    types = _event_types(world)
    assert "COMMIT_NOT_VERIFIED" not in types, (
        f"GitCommitVerifier ran at pre-commit (the defect): events {types}"
    )
    assert "COMMIT_VERIFIED" not in types, (
        f"GitCommitVerifier ran at pre-commit (the defect): events {types}"
    )
    blob = json.dumps(events)
    assert "does not have any commits yet" not in blob, (
        "audit log shows the 'no commits yet' git error -- the gate ran "
        "GitCommitVerifier before the commit existed (the defect)"
    )


@then("the completed earlier step remains accepted")
def _earlier_remains_accepted(world: dict) -> None:
    code, out = support.validate_at_commit_boundary(
        world["project"], world["kata_id"], world["earlier_step"]
    )
    assert code == 0 and out.strip() == ""


@then("the execution log and Step-Id commit history show the strict ordered cycle")
def _live_ordered(world: dict) -> None:  # pragma: no cover - skipped path
    raise AssertionError("unreachable: model backend skip fires first")


@then("an attempted step-skip was blocked at the commit boundary")
def _live_skip_blocked(world: dict) -> None:  # pragma: no cover - skipped path
    raise AssertionError("unreachable: model backend skip fires first")


# --------------------------------------------------------------------------- #
# Post-hoc provenance backstop (step 01-02, R3 mitigation)
#
# The LIVE gate (step 01-01) verifies phase-completeness at the pre-commit
# `tool_call` -- it canNOT verify a not-yet-existing commit. So a model could
# record its COMMIT phase, pass the live gate, then NOT git-commit (or commit
# with wrong trailers). This post-hoc check closes that gap: after the kata,
# every step that recorded a COMMIT phase MUST map to a real
# `Step-Id`+`Task-Id`-trailered commit (AND-semantics), by REUSING the
# UNCHANGED engine `GitCommitVerifier`. Example-only (Mandate 11), no PBT
# (Mandate 9): a single faithfully-committed-vs-recorded-but-not-committed
# pair. Real tmp git repo + reused CLIs (@real-io). Engine reused UNCHANGED (K2).
# --------------------------------------------------------------------------- #


def test_provenance_passes_when_every_recorded_commit_step_was_committed(
    tmp_path: Path,
) -> None:
    """A faithfully-committed kata: every recorded-COMMIT step maps to a commit."""
    from scripts.install.pi_kata import provenance

    project = support.make_activated_project(tmp_path)
    kata_id = "fizzbuzz"
    support.bootstrap_session(project, kata_id)

    plan = list(_PLAN)
    for index, _planned in enumerate(plan):
        step = support.current_step(project, kata_id)
        support.record_complete_cycle(project, kata_id, step)
        support.commit_with_trailers(project, step, kata_id)
        if index < len(plan) - 1:
            support.advance_to_next_step(project, kata_id)

    result = provenance.check_kata_provenance(
        project_root=str(project), kata_id=kata_id
    )

    assert result.verified is True, (
        f"expected provenance PASS, got unverified steps: {result.unverified_steps}"
    )
    assert result.unverified_steps == []
    assert result.verified_steps == plan


def test_provenance_fails_when_a_recorded_commit_step_was_never_committed(
    tmp_path: Path,
) -> None:
    """The R3 gap: a step records its COMMIT phase but no matching commit exists."""
    from scripts.install.pi_kata import provenance

    project = support.make_activated_project(tmp_path)
    kata_id = "fizzbuzz"
    support.bootstrap_session(project, kata_id)

    committed_step = support.current_step(project, kata_id)
    support.record_complete_cycle(project, kata_id, committed_step)
    support.commit_with_trailers(project, committed_step, kata_id)

    # The model recorded a COMMIT phase for the next step but never git-committed
    # it -- the "recorded-but-not-committed" gap the live gate cannot catch.
    skipped_step = support.advance_to_next_step(project, kata_id)
    support.record_complete_cycle(project, kata_id, skipped_step)

    result = provenance.check_kata_provenance(
        project_root=str(project), kata_id=kata_id
    )

    assert result.verified is False
    assert result.unverified_steps == [skipped_step]
    assert committed_step in result.verified_steps
    assert skipped_step not in result.verified_steps


def test_provenance_fails_when_a_recorded_commit_step_has_wrong_trailers(
    tmp_path: Path,
) -> None:
    """A commit exists but carries a mismatched Task-Id -- AND-semantics rejects it."""
    from scripts.install.pi_kata import provenance

    project = support.make_activated_project(tmp_path)
    kata_id = "fizzbuzz"
    support.bootstrap_session(project, kata_id)

    step = support.current_step(project, kata_id)
    support.record_complete_cycle(project, kata_id, step)
    # Commit carries the right Step-Id but a DIFFERENT Task-Id (cross-feature
    # confusion) -- the AND-semantics Step-Id+Task-Id match must reject it.
    support.commit_with_trailers(project, step, "some-other-kata")

    result = provenance.check_kata_provenance(
        project_root=str(project), kata_id=kata_id
    )

    assert result.verified is False
    assert result.unverified_steps == [step]
