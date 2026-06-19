"""Tier A step definitions — install-log hygiene (concern 3).

Driving port: the production ``SkillsPlugin.install(context)`` via the
``InstallLogService`` composition-root service. Step bodies delegate to
the service and assert against port-exposed observables (``InstallLog``);
no business logic is inlined (Mandate-12 criterion 3).

Layer 3 (real filesystem install) → example-based, no PBT machinery
(Mandate 9 / 11). The private-name set is parametrised inside the Then
steps via the canonical ``PRIVATE_AGENT_FILES`` / ``PRIVATE_SKILL_DIRS``
fixtures of record — one assertion covers the whole set (max density).
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.installer.acceptance.private_skill_leak.steps.domain_types import (
    PRIVATE_AGENT_FILES,
    PRIVATE_SKILL_DIRS,
    InstallMode,
)
from tests.installer.acceptance.private_skill_leak.steps.wheel_privacy_composition import (
    build_composition,
)


scenarios("../install-log-hygiene.feature")


# --- fixtures --------------------------------------------------------------


@pytest.fixture
def composition():
    """Production composition root over the real repository tree."""
    return build_composition()


@pytest.fixture
def run_state() -> dict:
    """Mutable carrier for InstallLog results across Given/When/Then."""
    return {}


# --- Given -----------------------------------------------------------------


@given("the nWave framework source with private agents and skills")
def given_framework_source(composition):
    # Precondition only — the real repo tree is the SUT input. No setup of
    # the expected output (no Fixture Theater).
    assert (composition.repo_root / "nWave" / "agents").is_dir()


@given("a developer install has recorded its output")
def given_developer_install_recorded(composition, run_state, tmp_path):
    run_state["dev"] = composition.install_log.run_skill_install(
        InstallMode.DEV, tmp_path / "dev-claude"
    )


# --- When ------------------------------------------------------------------


@when("a customer runs a public install")
def when_customer_public_install(composition, run_state, tmp_path):
    run_state["public"] = composition.install_log.run_skill_install(
        InstallMode.PUBLIC, tmp_path / "public-claude"
    )


@when("a framework developer runs a developer install")
def when_developer_install(composition, run_state, tmp_path):
    run_state["dev"] = composition.install_log.run_skill_install(
        InstallMode.DEV, tmp_path / "dev-claude"
    )


@when("the same source is installed in public mode")
def when_same_source_public(composition, run_state, tmp_path):
    run_state["public"] = composition.install_log.run_skill_install(
        InstallMode.PUBLIC, tmp_path / "public-claude"
    )


# --- Then ------------------------------------------------------------------


@then("the install output names no private agent")
def then_no_private_agent(run_state):
    log_text = run_state["public"].text
    leaked = [a for a in PRIVATE_AGENT_FILES if a.removesuffix(".md") in log_text]
    assert leaked == [], f"public install log leaked private agent names: {leaked}"


@then("the install output names no private skill")
def then_no_private_skill(run_state):
    log_text = run_state["public"].text
    leaked = [s for s in PRIVATE_SKILL_DIRS if s in log_text]
    assert leaked == [], f"public install log leaked private skill names: {leaked}"


@then("the install output reports an aggregate count of skipped skills")
def then_aggregate_count(run_state):
    log = run_state["public"]
    assert log.skipped_count > 0, "expected an aggregate skipped-skill report"
    assert any("non-public skill" in ln for ln in log.lines), (
        "public install must report an aggregate count, not per-skill names"
    )


@then("the install output may name skipped skills for the author's benefit")
def then_dev_may_name(run_state):
    # The dev diagnostic is permitted to exist — only assert the install
    # itself succeeded and produced a log (not Fixture Theater of names).
    assert run_state["dev"].lines, "developer install produced no log"


@then("the public output discloses no private name that the developer output revealed")
def then_public_drops_private(run_state):
    private_tokens = [a.removesuffix(".md") for a in PRIVATE_AGENT_FILES] + list(
        PRIVATE_SKILL_DIRS
    )
    public_text = run_state["public"].text
    leaked = [tok for tok in private_tokens if tok in public_text]
    assert leaked == [], f"public install regressed and leaked: {leaked}"
