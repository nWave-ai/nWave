"""Acceptance steps: Slice 02 -- self-driven per-test cycle with phase recording.

Driving ports = the reused des-log-phase (phase recording) and the UNCHANGED
subagent-stop adapter fed by the NEW synthesized-transcript commit-context
assembler (ADR-PKT-001 KD4). Chained narrative (Pillar 2): each Given reuses the
prior scenario's Given+When step methods. Real tmp git repo + real reused CLIs
(@real-io @adapter-integration), example-only (Mandate 11), no PBT (Mandate 9).
Block is delivered via stdout decision=block at exit 0 (SPIKE constraint 1);
markers must be exact (SPIKE constraint 2); fresh step-id per cycle (SPIKE
constraint 3). Engine reused UNCHANGED (K2).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.des.acceptance.pi_kata_tdd_flow.steps import kata_support as support
from tests.des.acceptance.pi_kata_tdd_flow.steps.domain_types import (
    REQUIRED_DES_MARKERS,
    TddPhase,
)


scenarios("../slice-02-self-driven-cycle.feature")


@pytest.fixture
def world(tmp_path: Path) -> dict:
    return {"project": support.make_activated_project(tmp_path)}


# --------------------------------------------------------------------------- #
# Given (reuse When step methods -- Pillar 2 chained narrative)
# --------------------------------------------------------------------------- #


@given(parsers.parse('a bootstrapped kata session for "{kata_id}" on step "{step_id}"'))
def _bootstrapped(world: dict, kata_id: str, step_id: str) -> None:
    world["kata_id"], world["step_id"] = kata_id, step_id
    support.bootstrap_session(world["project"], kata_id)


@given(parsers.parse('a kata step "{step_id}" recorded a completed increment'))
def _recorded_completed(world: dict, step_id: str) -> None:
    _bootstrapped(world, "fizzbuzz", step_id)
    support.record_complete_cycle(world["project"], "fizzbuzz", step_id)


@given("the increment was committed with Step-Id and Task-Id trailers")
def _committed_with_trailers(world: dict) -> None:
    support.commit_with_trailers(world["project"], world["step_id"], world["kata_id"])


@given("the step recorded only the failing-test phase")
def _only_red(world: dict) -> None:
    support.record_phase(
        world["project"], world["kata_id"], world["step_id"], TddPhase.RED
    )


@given("the commit-context transcript markers are malformed")
def _markers_malformed(world: dict) -> None:
    world["malformed"] = True


# --------------------------------------------------------------------------- #
# When
# --------------------------------------------------------------------------- #


@when(parsers.parse('the crafter records a completed increment for step "{step_id}"'))
def _record_increment(world: dict, step_id: str) -> None:
    world["before"] = _phase_trail(world)
    support.record_complete_cycle(world["project"], world["kata_id"], step_id)


@when("the step completion is validated at the commit boundary")
def _validate_boundary(world: dict) -> None:
    code, out = support.validate_at_commit_boundary(
        world["project"],
        world["kata_id"],
        world["step_id"],
        malformed=world.get("malformed", False),
    )
    world["exit"], world["stdout"] = code, out


# --------------------------------------------------------------------------- #
# Then
# --------------------------------------------------------------------------- #


def _phase_trail(world: dict) -> list[str]:
    log = support.deliver_dir(world["project"], world["kata_id"]) / "execution-log.json"
    if not log.exists():
        return []
    return [
        f"{e['sid']}|{e['p']}" for e in json.loads(log.read_text()).get("events", [])
    ]


@then("the step shows phases RED then GREEN then COMMIT in order")
def _ordered_phases(world: dict) -> None:
    trail = [
        p.split("|")[1] for p in _phase_trail(world) if p.startswith(world["step_id"])
    ]
    assert trail == ["RED", "GREEN", "COMMIT"]


@then("only that step's phase trail changed")
def _only_step_trail_changed(world: dict) -> None:
    other = [p for p in _phase_trail(world) if not p.startswith(world["step_id"])]
    assert other == world["before"]


@then("the step completion is accepted at the commit boundary")
def _accepted(world: dict) -> None:
    assert world["exit"] == 0 and world["stdout"].strip() == ""


@then("the commit-context transcript carried the four required DES markers")
def _markers_present(world: dict) -> None:
    content = support.transcript_context.build_transcript_content(
        kata_id=world["kata_id"],
        step_id=world["step_id"],
        project_root=str(world["project"]),
    )
    assert all(marker in content for marker in REQUIRED_DES_MARKERS)


@then("the step completion is rejected at the commit boundary with a reason")
def _rejected_with_reason(world: dict) -> None:
    parsed = json.loads(world["stdout"])
    assert parsed.get("decision") == "block" and parsed.get("reason")


@then("no increment is recorded as accepted")
def _no_accepted_increment(world: dict) -> None:
    assert world["stdout"].strip() != ""


@then("the boundary finds no DES context to verify")
def _no_des_context(world: dict) -> None:
    parsed = json.loads(world["stdout"])
    assert parsed.get("decision") == "allow"
