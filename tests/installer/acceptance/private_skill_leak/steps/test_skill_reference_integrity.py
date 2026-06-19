"""Tier A step definitions — skill-reference integrity (concern 4).

The dangling-reference prevention guard: every skill referenced by a
public artifact must survive the privacy strip.

Driving port: ``SkillReferenceService.find_dangling_references`` →
production ``validate_skill_references.check_references`` (RED scaffold).

Layer 3 (real filesystem source scan) → example-based, no PBT machinery
(Mandate 9 / 11). Step bodies delegate to the service; no business logic
is inlined (Mandate-12 criterion 3).
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.installer.acceptance.private_skill_leak.steps.wheel_privacy_composition import (
    build_composition,
)


scenarios("../skill-reference-integrity.feature")


# --- fixtures --------------------------------------------------------------


@pytest.fixture
def composition():
    """Production composition root over the real repository tree."""
    return build_composition()


@pytest.fixture
def run_state() -> dict:
    """Mutable carrier for guard results across Given/When/Then."""
    return {}


# --- Given -----------------------------------------------------------------


@given("the nWave framework source with private agents and skills")
def given_framework_source(composition):
    assert (composition.repo_root / "nWave" / "agents").is_dir()


@given(
    "a framework source where a public artifact names a skill the release strip removes"
)
def given_dangling_referrer(composition, tmp_path, run_state):
    # Materialise a REAL dangling referrer: an existing catalogued public
    # agent (survives the strip) is given a body reference to a planted
    # uncatalogued skill (removed by the strip). The mutated tree — not the
    # real repo — is what the guard scans for this scenario. No Fixture
    # Theater: the strip-probe inside the service asserts the precondition.
    run_state["nwave_dir"] = composition.references.build_source_with_dangling_referrer(
        tmp_path
    )


# --- When ------------------------------------------------------------------


@when("the skill-reference guard inspects the framework source")
def when_guard_inspects_real_source(composition, run_state):
    run_state["dangling"] = composition.references.find_dangling_references()


@when("the skill-reference guard inspects that framework source")
def when_guard_inspects_planted_source(composition, run_state):
    run_state["dangling"] = composition.references.find_dangling_references(
        run_state["nwave_dir"]
    )


# --- Then ------------------------------------------------------------------


@then("the guard finds no public artifact depending on removable work")
def then_no_dangling(run_state):
    assert run_state["dangling"] == [], (
        f"public artifacts depend on removable skills: {run_state['dangling']}"
    )


@then("the guard names that public artifact and the removable skill it depends on")
def then_guard_names_dangling(run_state):
    dangling = run_state["dangling"]
    assert dangling, "guard found no dangling reference where one exists"
    report = "\n".join(dangling)
    assert "nw-troubleshooter" in report, (
        f"guard report did not name the referring public artifact: {report}"
    )
    assert "nw-planted-removable-skill" in report, (
        f"guard report did not name the removable skill: {report}"
    )
