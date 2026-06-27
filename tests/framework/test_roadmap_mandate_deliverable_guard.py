"""Skill-lint (NB-1): nw-roadmap test-paradigm mandate is deliverable-type guarded.

CONTRACT_SHAPE: pure-function
Outcome anchor: After running the test suite, practitioners can no longer
hand-suppress the Hypothesis/state-delta mandate on plugin- or skill-class
projects, because the mandate is emitted by nw-roadmap ONLY when the target
deliverable produces application code. The roadmap prompt itself routes
plugin/skill projects to a structural-verification directive instead — so
there is nothing to suppress, and the suppression smell that motivated #66
cannot recur.

This is the NB-1 DELIVER obligation promoted from a possibility to a named,
gated test: a golden assertion over nWave/skills/nw-roadmap/SKILL.md. It is a
pure file-parsing fitness function — no subprocess, no network.

Empirical anchor (nWave-ai/nWave issue #66): the "TEST PARADIGM (mandatory)"
block in nw-roadmap/SKILL.md was UNCONDITIONAL prompt text. On plugin/skill
projects (which ship no application code and therefore no Hypothesis unit
tests), practitioners hand-edited roadmaps to drop the mandate, normalising
ad-hoc suppression of a STANDING test-design directive. The fix (ADR-PST-003 /
OPEN-5-A) wraps the verbatim mandate in a single
`deliverable_type == application` conditional: full mandate for app-code (or
when deliverable_type is unset), a one-line structural-verification directive
for plugin/skill.

Design reference: ADR-PST-003 + docs/feature/plugin-skill-deliverable-type
feature-delta.
"""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROADMAP_SKILL = REPO_ROOT / "nWave" / "skills" / "nw-roadmap" / "SKILL.md"

# The verbatim opening of the mandate block. This MUST remain byte-identical
# for the application branch (AC-5 regression). If this string drifts, either
# the mandate text changed (update both the skill and this anchor) or the guard
# was removed.
MANDATE_ANCHOR = (
    "TEST PARADIGM (mandatory): Unit tests for this step MUST be written as"
)

# The guard must name the deliverable-type conditional that gates the mandate.
# We accept either `deliverable_type == application` or
# `deliverable_type == "application"` (quoted), with flexible surrounding
# whitespace, so the skill author is not boxed into one phrasing.
GUARD_RE = re.compile(
    r"deliverable_type\s*==\s*[\"']?application[\"']?",
)

# The plugin/skill alternative must be a structural-verification directive.
# We look for the routing keyword pair that distinguishes the non-application
# branch from the (suppressed) mandate.
PLUGIN_SKILL_BRANCH_RE = re.compile(
    r"plugin\s*/\s*skill|plugin or skill|plugin/skill",
    re.IGNORECASE,
)
STRUCTURAL_DIRECTIVE_RE = re.compile(
    r"structural(?:[ -]verification| verify| check)?",
    re.IGNORECASE,
)


def _skill_text() -> str:
    assert ROADMAP_SKILL.exists(), f"nw-roadmap skill not found at {ROADMAP_SKILL}"
    return ROADMAP_SKILL.read_text(encoding="utf-8")


def test_mandate_block_is_present() -> None:
    """Sanity: the verbatim mandate text still exists (precondition for the lint).

    If this fails, the mandate was deleted rather than guarded — a regression.
    """
    text = _skill_text()
    assert MANDATE_ANCHOR in text, (
        "The verbatim 'TEST PARADIGM (mandatory)' anchor is missing from "
        "nw-roadmap/SKILL.md. The mandate must be PRESENT (and guarded), "
        "not deleted."
    )


def test_mandate_is_wrapped_in_deliverable_type_application_guard() -> None:
    """The mandate block emits ONLY under deliverable_type == application.

    RED while the mandate is unconditional prompt text. GREEN once the verbatim
    block is wrapped in a `deliverable_type == application` conditional, with a
    plugin/skill structural-verification fallback.
    """
    text = _skill_text()

    mandate_idx = text.find(MANDATE_ANCHOR)
    assert mandate_idx != -1, (
        "Mandate anchor missing — cannot verify the guard. "
        "See test_mandate_block_is_present."
    )

    guard_match = GUARD_RE.search(text)
    assert guard_match is not None, (
        "nw-roadmap/SKILL.md emits the TEST PARADIGM mandate UNCONDITIONALLY. "
        "It must be wrapped in a `deliverable_type == application` conditional "
        "so plugin/skill roadmaps do not carry the Hypothesis/state-delta "
        "mandate (issue #66 / ADR-PST-003 / OPEN-5-A). No "
        "`deliverable_type == application` guard was found anywhere in the "
        "skill."
    )

    # The guard must PRECEDE the mandate text — it gates it, it does not trail
    # it. A guard sentence appearing only after the mandate would not actually
    # condition the emission.
    assert guard_match.start() < mandate_idx, (
        "Found a `deliverable_type == application` guard, but it appears AFTER "
        "the mandate block. The guard must precede (and therefore gate) the "
        "verbatim mandate so the mandate is emitted only for application code."
    )


def test_plugin_skill_branch_routes_to_structural_directive() -> None:
    """The non-application branch must offer a structural-verification directive.

    Guarding the mandate is only half the fix: plugin/skill projects must be
    routed to a one-line structural-verification directive rather than left
    with no test-paradigm guidance at all.
    """
    text = _skill_text()

    assert PLUGIN_SKILL_BRANCH_RE.search(text), (
        "The deliverable-type guard must name a plugin/skill branch so the "
        "non-application case is explicitly handled, not silently dropped."
    )
    assert STRUCTURAL_DIRECTIVE_RE.search(text), (
        "The plugin/skill branch must route to a structural-verification "
        "directive (ADR-PST-003 / OPEN-5-A), replacing the suppressed "
        "Hypothesis/state-delta mandate."
    )
