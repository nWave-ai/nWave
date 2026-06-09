"""Step definitions: the mode/resume/AT-set skills document the atdd_pure path.

ADR-028 / ADR-029 / slice-13 of the atdd-pure-roadmap-free-rollout.

Layer 3 (FS-reading coherence). Example-only, no PBT machinery (Mandate 9/11):
the slice-13 contract is a closed enumerable set -- three NEW clauses (one per
file) + one MODE_SCOPED clause -- realised as one ``Scenario Outline`` plus one
plain ``Scenario``, NOT a Hypothesis @given.

Step bodies delegate to ``ModeDetectionResumeComposition``; no inline business
logic (Mandate-12 criterion 3) -- each body is a typed lookup plus a
composition call or a single assertion over a composition-computed value.

Regression contract: every NEW-clause scenario FAILS on master and PASSES once
slice-13 lands. On master none of the three skills mention ``atdd_pure``; none
name the ``AT-completion ledger`` / ``workflow.mode`` / ``per-slice`` mechanism.
nw-buddy-project-reading carries 1 unscoped ``roadmap.json`` line (L92). The NEW
master-absent token is verified absent on master, so these are genuine
missing-functionality RED, not test bugs.

This test is SEPARATE from slices 04 / 15 (coherence over nw-deliver/SKILL.md)
and slice-09 (the three finalize-adjacent skills); slice-13 targets three
disjoint files.

See the acceptance brief WAVE: DISTILL section for the testable-surface
finding and the vacuous-clause flags (the nw-fast-forward mode-scope clause and
the nw-at-completeness-check absence clause from the design note are vacuous on
master and are NOT shipped).
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from .composition import ClauseVerdict, ModeDetectionResumeComposition
from .domain_types import SKILL_FILE_BY_PHRASE, ClauseKind


scenarios("../mode-detection-resume-coherence.feature")


# --- fixtures ----------------------------------------------------------------


def _composition() -> ModeDetectionResumeComposition:
    """Production-wired composition root over the real slice-13 SKILL.md set."""
    return ModeDetectionResumeComposition()


# --- Given -------------------------------------------------------------------


@given("a mode-detection / resume / AT-set skill", target_fixture="composition")
def given_skill() -> ModeDetectionResumeComposition:
    # The Background builds the composition; the When loads the per-row file so
    # the Scenario Outline rows share one composition object (Pillar 2).
    return _composition()


# --- When --------------------------------------------------------------------


@when(parsers.parse("{skill_phrase} is read for the atdd_pure workflow"))
def when_read_skill(
    composition: ModeDetectionResumeComposition, skill_phrase: str
) -> None:
    composition.load_skill(SKILL_FILE_BY_PHRASE[skill_phrase])


# --- Then --------------------------------------------------------------------


@then(
    parsers.parse("{skill_phrase} names the atdd_pure roadmap-free mechanism"),
    target_fixture="verdict",
)
def then_names_atdd_pure_mechanism(
    composition: ModeDetectionResumeComposition, skill_phrase: str
) -> ClauseVerdict:
    verdict = composition.evaluate_new_clause()
    assert verdict.present, (
        f"{skill_phrase}: the skill does not name the atdd_pure roadmap-free "
        f"mechanism -- slice-13 has not landed"
    )
    return verdict


@then("that atdd_pure prose is new relative to the classic-only master skill")
def then_clause_is_new(verdict: ClauseVerdict) -> None:
    # Guard the contract: a clause reaching this assertion MUST be
    # ClauseKind.NEW -- only a NEW clause carries an honest new-vs-master
    # regression signal (slice-04 review Blocking 1 / slice-09 precedent).
    assert verdict.kind is ClauseKind.NEW, (
        f"{verdict.skill.value}: a {verdict.kind.value} clause carries no "
        f"new-vs-master regression signal"
    )
    assert verdict.is_new, (
        f"{verdict.skill.value}: the master-absent token is not in the file "
        f"-- this clause cannot be a slice-13 regression signal"
    )


@then(parsers.parse("every roadmap line in {skill_phrase} is classic-scoped"))
def then_mode_scoped(
    composition: ModeDetectionResumeComposition, skill_phrase: str
) -> None:
    verdict = composition.evaluate_mode_scoped_clause()
    assert not verdict.unscoped_lines, (
        f"{skill_phrase}: {len(verdict.unscoped_lines)} roadmap.json line(s) "
        f"carry no classic / workflow.mode qualifier -- an unscoped mention "
        f"frames the roadmap as unconditional (slice-13 has not scoped the "
        f"prose). First offender L{verdict.unscoped_lines[0].line_number}: "
        f"{verdict.unscoped_lines[0].text!r}"
    )
