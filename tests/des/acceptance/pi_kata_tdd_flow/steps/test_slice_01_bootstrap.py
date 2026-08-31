"""Acceptance steps: Slice 01 -- self-bootstrap a DES-tracked kata session.

Driving port = the kata-session bootstrap helper the pi registered command
delegates to (ADR-PKT-001 KD1). Real filesystem + reused des-init-log
(@real-io @adapter-integration), example-only (Mandate 11), no PBT (Mandate 9).
State-mutating Then steps assert via state-delta over a port-exposed universe
(filesystem snapshot + bootstrap return) -- Mandate 8.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.common.state_delta import assert_state_delta, unchanged
from tests.des.acceptance.pi_kata_tdd_flow.steps import kata_support as support


scenarios("../slice-01-bootstrap.feature")


@pytest.fixture
def world() -> dict:
    return {}


# --------------------------------------------------------------------------- #
# Given
# --------------------------------------------------------------------------- #


@given("an activated pi project with no kata session yet")
def _activated_no_session(world: dict, tmp_path: Path) -> None:
    world["project"] = support.make_activated_project(tmp_path)


@given("a project that is not activated for the kata harness")
def _unactivated(world: dict, tmp_path: Path) -> None:
    world["project"] = support.make_unactivated_project(tmp_path)


@given(
    parsers.parse(
        'an activated pi project with an existing kata session for "{kata_id}"'
    )
)
def _activated_existing_session(world: dict, tmp_path: Path, kata_id: str) -> None:
    world["project"] = support.make_activated_project(tmp_path)
    world["existing"] = support.bootstrap_session(world["project"], kata_id)


# --------------------------------------------------------------------------- #
# When
# --------------------------------------------------------------------------- #


@when(parsers.parse('the crafter is invoked with the kata "{kata_id}"'))
def _invoke_crafter(world: dict, kata_id: str) -> None:
    world["kata_id"] = kata_id
    world["before"] = support.filesystem_snapshot(world["project"])
    world["result"] = support.bootstrap_session(world["project"], kata_id)


# --------------------------------------------------------------------------- #
# Then
# --------------------------------------------------------------------------- #


@then(
    parsers.parse(
        'a kata session is initialized for "{kata_id}" with first step "{step_id}"'
    )
)
def _session_initialized(world: dict, kata_id: str, step_id: str) -> None:
    manifest = support.read_manifest(world["project"], kata_id)
    assert manifest["project_id"] == kata_id and manifest["step_id"] == step_id


@then("the kata session is recorded under the kata's deliver directory")
def _recorded_under_deliver(world: dict) -> None:
    log = support.deliver_dir(world["project"], world["kata_id"]) / "execution-log.json"
    assert log.exists()


@then("no manual setup command was required")
def _no_manual_setup(world: dict) -> None:
    assert world["result"]["status"] == "bootstrapped"


@then("the kata bootstrap is refused")
def _bootstrap_refused(world: dict) -> None:
    assert world["result"]["status"] == "refused"


@then("no kata session is created")
def _no_session_created(world: dict) -> None:
    after = support.filesystem_snapshot(world["project"])
    assert_state_delta(
        world["before"],
        after,
        universe=set(world["before"]) | set(after),
        expected={key: unchanged() for key in set(world["before"]) | set(after)},
    )


@then("the project filesystem is otherwise unchanged")
def _filesystem_unchanged(world: dict) -> None:
    after = support.filesystem_snapshot(world["project"])
    assert after == world["before"]


@then(parsers.parse('the existing kata session for "{kata_id}" is preserved unchanged'))
def _session_preserved(world: dict, kata_id: str) -> None:
    assert support.read_manifest(world["project"], kata_id) == world["existing"]


@then("no duplicate kata session is created")
def _no_duplicate(world: dict) -> None:
    after = support.filesystem_snapshot(world["project"])
    assert after == world["before"]
