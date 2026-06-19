"""Acceptance tests — closed-set strip survival + fail-closed gate (GAP-B, C6a).

Two threat-model gaps closed here:

GAP-B — full 11-skill triage. The privacy strip derives skill ownership
from agent frontmatter only. The 11 skills below are each referenced by a
public artifact (command-skill body or public agent) but owned by no
public agent, so the ownership-only strip drops them as "uncatalogued"
orphan work — shipping a public package with a dangling reference. The
fix must make EVERY one of the 11 survive the strip. Parametrised over
the exact 11 (max density: one test body, 11 cases).

The C6 closed-set negative is the complement: a GENUINE orphan (a skill
referenced by nothing public) strips cleanly WITHOUT collateral damage
to a public skill reference. The closed set is "public-referenced skills
survive; everything else may go" — proven by asserting the load-bearing
set survives while the strip still removes private skills.

C6a — malformed-catalog error contract. ``verify_wheel_privacy`` consults
``framework-catalog.yaml`` as the public allow-list. If that catalog is
corrupt or missing, the gate cannot prove the wheel is clean — so it MUST
refuse (fail-closed): treat the unparseable catalog as a privacy
violation, never silently pass.

All tests here are plain pytest (not pytest-bdd) and NOT ``@xfail`` —
they are genuinely RED until DELIVER lands the fix:
  * the 11 survival cases FAIL because master's strip drops them
    (``MISSING_FUNCTIONALITY``);
  * the C6a cases FAIL because ``verify_wheel_privacy`` is a RED scaffold
    (``MISSING_FUNCTIONALITY``).

Layer 3 (real filesystem build) → example-based, no PBT machinery
(Mandate 9 / 11). Step bodies delegate to composition services — no
business logic inlined (Mandate-12 criterion 3).
"""

from __future__ import annotations

import pytest

from tests.installer.acceptance.private_skill_leak.steps.domain_types import (
    LOAD_BEARING_PUBLIC_SKILLS,
    PRIVATE_SKILL_DIRS,
)
from tests.installer.acceptance.private_skill_leak.steps.wheel_privacy_composition import (
    build_composition,
)


@pytest.fixture
def composition():
    """Production composition root over the real repository tree."""
    return build_composition()


@pytest.fixture
def stripped_tree(composition, tmp_path):
    """A wheel tree built by applying the real privacy strip."""
    return composition.wheel.build_stripped_wheel_tree(tmp_path)


# --- GAP-B: full 11-skill triage -------------------------------------------


@pytest.mark.parametrize(
    "skill",
    LOAD_BEARING_PUBLIC_SKILLS,
    ids=list(LOAD_BEARING_PUBLIC_SKILLS),
)
def test_load_bearing_public_skill_survives_the_strip(
    composition, stripped_tree, skill
):
    """Every skill a public artifact depends on survives the release strip.

    Outcome (ubiquitous language): a customer installing the public
    package finds every skill that the public agents and command-skills
    point to — no dangling reference, no broken install.

    @contract-shape:unbounded-preservation — the strip must preserve the
    "public-referenced skill is present" property for the whole set.
    """
    contents = composition.wheel.read_wheel_contents(stripped_tree)
    assert contents.contains_skill(skill), (
        f"the privacy strip dropped load-bearing public skill {skill!r} "
        "as uncatalogued orphan work — a public artifact references it, "
        "so the public package now ships a dangling reference"
    )


# --- C6 closed-set negative: genuine orphans strip without collateral ------


def test_genuine_private_orphans_strip_without_breaking_public_skills(
    composition, stripped_tree
):
    """Stripping genuine private work leaves every public-referenced skill.

    The closed set is well-defined: skills referenced by a public artifact
    survive; private/orphan skills may be removed. This asserts both
    halves at once — the private skills are gone AND the load-bearing
    public skills are still present, proving the strip removed only the
    genuine orphans with zero collateral damage.

    @contract-shape:unbounded-preservation — preservation of the public
    closed set under removal of the private closed set.
    """
    contents = composition.wheel.read_wheel_contents(stripped_tree)

    leaked_private = [s for s in PRIVATE_SKILL_DIRS if contents.contains_skill(s)]
    assert leaked_private == [], (
        f"strip kept private skills it should remove: {leaked_private}"
    )

    dropped_public = [
        s for s in LOAD_BEARING_PUBLIC_SKILLS if not contents.contains_skill(s)
    ]
    assert dropped_public == [], (
        "stripping genuine orphans also dropped public-referenced skills "
        f"(collateral damage — closed-set violation): {dropped_public}"
    )


# --- C6a: fail-closed on malformed / missing catalog -----------------------


def test_privacy_gate_refuses_a_wheel_with_a_corrupt_catalog(composition, tmp_path):
    """The privacy gate refuses when the catalog allow-list is unparseable.

    Outcome (ubiquitous language): the release refuses to publish a
    package whose privacy cannot be verified — a corrupt allow-list is
    treated as a privacy violation, not waved through.

    @contract-shape:bounded-change — fail-closed: a malformed catalog
    yields a non-empty violation list (the gate refuses).
    """
    tree = composition.wheel.build_wheel_tree_with_corrupt_catalog(tmp_path)
    violations = composition.wheel.verify_wheel_privacy(tree)
    assert violations, (
        "the privacy gate passed a wheel whose framework-catalog.yaml is "
        "corrupt — it cannot have verified the allow-list. The gate must "
        "fail closed and report the unverifiable catalog as a violation."
    )


def test_privacy_gate_refuses_a_wheel_with_a_missing_catalog(composition, tmp_path):
    """The privacy gate refuses when the catalog allow-list is absent.

    A missing catalog is as untrustworthy as a corrupt one — the gate
    cannot enumerate the public allow-list, so it MUST refuse.

    @contract-shape:bounded-change — fail-closed: a missing catalog
    yields a non-empty violation list (the gate refuses).
    """
    tree = composition.wheel.build_wheel_tree_with_missing_catalog(tmp_path)
    violations = composition.wheel.verify_wheel_privacy(tree)
    assert violations, (
        "the privacy gate passed a wheel with no framework-catalog.yaml — "
        "it cannot have verified the allow-list. The gate must fail closed "
        "and report the missing catalog as a violation."
    )
