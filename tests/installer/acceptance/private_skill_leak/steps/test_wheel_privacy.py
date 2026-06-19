"""Tier A step definitions — wheel privacy + public-skill survival.

Concern 1 (no private artifact in the wheel) + concern 2 (public skills a
public artifact depends on survive the strip).

Driving ports exercised through the composition-root services:
  * ``WheelBuildService.build_stripped_wheel_tree`` — the privacy strip
    (production ``strip_private_agents.strip``).
  * ``WheelBuildService.verify_wheel_privacy`` — the release privacy gate
    (production ``verify_wheel_privacy.verify`` — RED scaffold).

Layer 3 (real filesystem build) → example-based, no PBT machinery
(Mandate 9 / 11). The private-artifact set is parametrised inside the Then
steps via the canonical ``PRIVATE_AGENT_FILES`` / ``PRIVATE_SKILL_DIRS``
fixtures of record — one assertion covers the whole set (max density).

Step bodies delegate to services; no business logic is inlined
(Mandate-12 criterion 3).
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.installer.acceptance.private_skill_leak.steps.domain_types import (
    LOAD_BEARING_PUBLIC_SKILLS,
    PRIVATE_AGENT_FILES,
    PRIVATE_SKILL_DIRS,
    PUBLIC_AGENT_FILES,
)
from tests.installer.acceptance.private_skill_leak.steps.wheel_privacy_composition import (
    build_composition,
)


scenarios("../wheel-privacy.feature")


# --- fixtures --------------------------------------------------------------


@pytest.fixture
def composition():
    """Production composition root over the real repository tree."""
    return build_composition()


@pytest.fixture
def run_state() -> dict:
    """Mutable carrier for wheel/gate results across Given/When/Then."""
    return {}


# --- Given -----------------------------------------------------------------


@given("the nWave framework source with private agents and skills")
def given_framework_source(composition):
    # Precondition only — the real repo tree is the SUT input.
    assert (composition.repo_root / "nWave" / "agents").is_dir()
    assert (composition.repo_root / "nWave" / "skills").is_dir()


@given("a package that was prepared without removing private work")
def given_unstripped_package(composition, run_state, tmp_path):
    run_state["wheel_tree"] = composition.wheel.build_unstripped_wheel_tree(tmp_path)


@given("a package that was prepared with private work removed")
def given_stripped_package(composition, run_state, tmp_path):
    run_state["wheel_tree"] = composition.wheel.build_stripped_wheel_tree(tmp_path)


# --- When ------------------------------------------------------------------


@when("the public package is prepared for release")
def when_prepare_public_package(composition, run_state, tmp_path):
    tree = composition.wheel.build_stripped_wheel_tree(tmp_path)
    run_state["wheel_tree"] = tree
    run_state["contents"] = composition.wheel.read_wheel_contents(tree)


@when("the public package is prepared for release again from that package")
def when_prepare_again(composition, run_state):
    tree = composition.wheel.reprepare_wheel_tree(run_state["wheel_tree"])
    run_state["contents"] = composition.wheel.read_wheel_contents(tree)


@when("the release privacy gate inspects that package")
def when_gate_inspects(composition, run_state):
    run_state["violations"] = composition.wheel.verify_wheel_privacy(
        run_state["wheel_tree"]
    )


# --- Then ------------------------------------------------------------------


@then("the prepared package contains no private agent")
def then_no_private_agent(run_state):
    contents = run_state["contents"]
    leaked = [a for a in PRIVATE_AGENT_FILES if contents.contains_agent(a)]
    assert leaked == [], f"prepared package leaked private agents: {leaked}"


@then("the prepared package contains no private skill")
def then_no_private_skill(run_state):
    contents = run_state["contents"]
    leaked = [s for s in PRIVATE_SKILL_DIRS if contents.contains_skill(s)]
    assert leaked == [], f"prepared package leaked private skills: {leaked}"


@then(
    "the prepared package still contains every public skill a public artifact depends on"
)
def then_load_bearing_survive(run_state):
    contents = run_state["contents"]
    missing = [s for s in LOAD_BEARING_PUBLIC_SKILLS if not contents.contains_skill(s)]
    assert missing == [], (
        f"strip dropped load-bearing public skills (dangling refs): {missing}"
    )


@then("the prepared package keeps every public agent")
def then_keeps_public_agents(run_state):
    contents = run_state["contents"]
    # Closed-set survival: the strip must keep EVERY public agent, not
    # merely "some agent". A non-empty check would pass even if the strip
    # kept 1 public agent and dropped 31 — the Gherkin says "every".
    dropped = [a for a in PUBLIC_AGENT_FILES if not contents.contains_agent(a)]
    assert dropped == [], f"strip dropped public agents that must survive: {dropped}"


@then("the prepared package removes every private agent")
def then_removes_private_agents(run_state):
    contents = run_state["contents"]
    leaked = [a for a in PRIVATE_AGENT_FILES if contents.contains_agent(a)]
    assert leaked == [], f"prepared package leaked private agents: {leaked}"


@then("the prepared package keeps every public skill a public artifact depends on")
def then_keeps_load_bearing(run_state):
    contents = run_state["contents"]
    missing = [s for s in LOAD_BEARING_PUBLIC_SKILLS if not contents.contains_skill(s)]
    assert missing == [], f"strip dropped load-bearing public skills: {missing}"


@then("the twice-prepared package contains no private agent")
def then_twice_no_private_agent(run_state):
    contents = run_state["contents"]
    leaked = [a for a in PRIVATE_AGENT_FILES if contents.contains_agent(a)]
    assert leaked == [], f"second prepare leaked private agents: {leaked}"


@then("the twice-prepared package contains no private skill")
def then_twice_no_private_skill(run_state):
    contents = run_state["contents"]
    leaked = [s for s in PRIVATE_SKILL_DIRS if contents.contains_skill(s)]
    assert leaked == [], f"second prepare leaked private skills: {leaked}"


@then(
    "the twice-prepared package still contains every public skill a public artifact depends on"
)
def then_twice_load_bearing(run_state):
    contents = run_state["contents"]
    missing = [s for s in LOAD_BEARING_PUBLIC_SKILLS if not contents.contains_skill(s)]
    assert missing == [], (
        f"second prepare dropped load-bearing public skills: {missing}"
    )


@then("the release privacy gate reports the private work it found")
def then_gate_reports_private(run_state):
    assert run_state["violations"], (
        "release privacy gate found no private work in a leaking package"
    )


@then("the release privacy gate refuses to pass")
def then_gate_refuses(run_state):
    assert len(run_state["violations"]) > 0, "gate must refuse a leaking package"


@then("the release privacy gate reports no private work")
def then_gate_reports_clean(run_state):
    assert run_state["violations"] == [], (
        f"gate flagged a clean package: {run_state['violations']}"
    )


@then("the release privacy gate passes")
def then_gate_passes(run_state):
    assert run_state["violations"] == [], "gate must pass a clean package"
