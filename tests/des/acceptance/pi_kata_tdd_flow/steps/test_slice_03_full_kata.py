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
    for step in world["plan"]:
        support.record_complete_cycle(world["project"], world["kata_id"], step)
        support.commit_with_trailers(world["project"], step, world["kata_id"])


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
