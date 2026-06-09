"""Step definitions: the finalize-adjacent skills document the atdd_pure path.

ADR-028 D4.3 + D3 / slice-09 of the atdd-pure-roadmap-free-rollout.

Layer 3 (FS-reading coherence). Example-only, no PBT machinery (Mandate 9/11):
the slice-09 contract is a closed enumerable set -- three files x two clause
families -- realised as two ``Scenario Outline``s, NOT a Hypothesis @given.

Step bodies delegate to ``FinalizeMutationOptimizeComposition``; no inline
business logic (Mandate-12 criterion 3) -- each body is a typed lookup plus a
composition call or a single assertion over a composition-computed value.

Regression contract: every NEW-clause scenario FAILS on master and PASSES once
slice-09 lands. On master none of the three skills mention ``atdd_pure`` or the
``AT-completion ledger``; each carries unscoped ``roadmap.json`` /
``execution-log`` lines. The NEW master-absent token is verified absent on
master, so these are genuine missing-functionality RED, not test bugs.

This test is SEPARATE from slices 04 / 15 (coherence over nw-deliver/SKILL.md);
slice-09 targets three disjoint files.

See the acceptance brief WAVE: DISTILL section for the testable-surface
finding: slice-09 ships only prose, so this executable coherence test is the
honest mechanical gate (the Class-P mechanism the rollout itself mandates).
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from .composition import ClauseVerdict, FinalizeMutationOptimizeComposition
from .domain_types import SKILL_FILE_BY_PHRASE, ClauseKind


scenarios("../finalize-mutation-optimize-coherence.feature")


# --- fixtures ----------------------------------------------------------------


def _composition() -> FinalizeMutationOptimizeComposition:
    """Production-wired composition root over the real slice-09 SKILL.md set."""
    return FinalizeMutationOptimizeComposition()


# --- Given -------------------------------------------------------------------


@given("a finalize-adjacent skill", target_fixture="composition")
def given_skill() -> FinalizeMutationOptimizeComposition:
    # The Background builds the composition; the When loads the per-row file so
    # the Scenario Outline rows share one composition object (Pillar 2).
    return _composition()


# --- When --------------------------------------------------------------------


@when(parsers.parse("{skill_phrase} is read for the atdd_pure workflow"))
def when_read_skill(
    composition: FinalizeMutationOptimizeComposition, skill_phrase: str
) -> None:
    composition.load_skill(SKILL_FILE_BY_PHRASE[skill_phrase])


# --- Then --------------------------------------------------------------------


@then(
    parsers.parse("{skill_phrase} names the atdd_pure AT-completion-ledger path"),
    target_fixture="verdict",
)
def then_names_atdd_pure_path(
    composition: FinalizeMutationOptimizeComposition, skill_phrase: str
) -> ClauseVerdict:
    verdict = composition.evaluate_new_clause()
    assert verdict.present, (
        f"{skill_phrase}: the skill does not name the atdd_pure "
        f"AT-completion-ledger path -- slice-09 has not landed"
    )
    return verdict


@then("that atdd_pure prose is new relative to the classic-only master skill")
def then_clause_is_new(verdict: ClauseVerdict) -> None:
    # Guard the contract: a clause reaching this assertion MUST be
    # ClauseKind.NEW -- only a NEW clause carries an honest new-vs-master
    # regression signal (slice-04 review Blocking 1 precedent).
    assert verdict.kind is ClauseKind.NEW, (
        f"{verdict.skill.value}: a {verdict.kind.value} clause carries no "
        f"new-vs-master regression signal"
    )
    assert verdict.is_new, (
        f"{verdict.skill.value}: the master-absent token 'AT-completion "
        f"ledger' is not in the file -- this clause cannot be a slice-09 "
        f"regression signal"
    )


@then(
    parsers.parse(
        "every roadmap or execution-log line in {skill_phrase} is classic-scoped"
    )
)
def then_mode_scoped(
    composition: FinalizeMutationOptimizeComposition, skill_phrase: str
) -> None:
    verdict = composition.evaluate_mode_scoped_clause()
    assert not verdict.unscoped_lines, (
        f"{skill_phrase}: {len(verdict.unscoped_lines)} roadmap.json / "
        f"execution-log line(s) carry no classic / workflow.mode qualifier "
        f"-- an unscoped mention frames the roadmap/log as unconditional "
        f"(slice-09 has not scoped the prose). First offender "
        f"L{verdict.unscoped_lines[0].line_number}: "
        f"{verdict.unscoped_lines[0].text!r}"
    )
