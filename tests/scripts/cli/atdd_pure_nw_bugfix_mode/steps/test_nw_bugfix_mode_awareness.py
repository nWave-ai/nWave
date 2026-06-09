"""Step definitions: the nw-bugfix workflow branches on workflow mode.

ADR-028 D5 / slice-05 of the atdd-pure-roadmap-free-rollout (feature-delta
``### slice-05`` design note, L527-546).

Layer 3 (FS-reading coherence). Example-only, no PBT machinery (Mandate 9/11):
the bugfix-mode contract clauses are a closed enumerable set, realised as a
``Scenario Outline`` + two dedicated scenarios, NOT a Hypothesis @given.

Step bodies delegate to ``BugfixModeCoherenceComposition``; no inline business
logic (Mandate-12 criterion 3) -- each body is a typed lookup plus a composition
call or a single assertion over a composition-computed value.

Regression contract: every NEW and ABSENCE scenario FAILS on master and PASSES
once slice-05 lands. On master ``nw-bugfix/SKILL.md`` is mode-unaware -- Phase 3
always delegates to ``/nw-deliver`` which "creates a minimal roadmap" -- it does
NOT read ``workflow.mode``, name an ``atdd_pure`` path, use ``carpaccio``
vocabulary, or run a ``/nw-execute`` per-slice cycle. Each NEW clause's
master-absent token is verified absent on master and the ABSENCE clause's
master-present token verified present, so these are genuine
missing-functionality RED, not test bugs. The one PRESERVATION scenario is GREEN
on master by design.

See the acceptance brief WAVE: DISTILL section for the Class-typing +
testable-surface finding: slice-05 ships only prose, so this executable
coherence test is the honest mechanical gate (the Class-P mechanism the rollout
itself mandates).
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from .composition import BugfixModeCoherenceComposition, ClauseVerdict
from .domain_types import BUGFIX_CLAUSE_BY_PHRASE, ClauseKind


scenarios("../nw-bugfix-mode-awareness.feature")


# --- Given -------------------------------------------------------------------


@given("the nw-bugfix workflow skill", target_fixture="composition")
def given_workflow() -> BugfixModeCoherenceComposition:
    composition = BugfixModeCoherenceComposition()
    composition.load_nw_bugfix_skill()
    return composition


# --- When --------------------------------------------------------------------


@when("the workflow is read for the atdd_pure project mode")
def when_read_atdd_pure(composition: BugfixModeCoherenceComposition) -> None:
    # The SUT (the SKILL.md content) is mode-independent text; the mode here
    # records intent for the chained narrative (Pillar 2). No-op against the
    # already-loaded composition.
    assert composition.skill_text


@when("the workflow is read for the classic project mode")
def when_read_classic(composition: BugfixModeCoherenceComposition) -> None:
    assert composition.skill_text


# --- Then --------------------------------------------------------------------


@then(
    parsers.parse("the bugfix workflow {bugfix_clause_phrase}"),
    target_fixture="verdict",
)
def then_clause_satisfied(
    composition: BugfixModeCoherenceComposition, bugfix_clause_phrase: str
) -> ClauseVerdict:
    # bugfix_clause_phrase is a closed-set key -- every phrase used in the
    # .feature is registered in BUGFIX_CLAUSE_BY_PHRASE. A missing key here
    # would KeyError (the slice-04 step-resolution defect); the parser captures
    # ONLY phrases beginning "the bugfix workflow ", and every such phrase in
    # the feature file has a lookup entry (verified by the collect-only +
    # real-run gate).
    clause = BUGFIX_CLAUSE_BY_PHRASE[bugfix_clause_phrase]
    verdict = composition.evaluate_clause(clause)
    assert verdict.satisfied, (
        f"nw-bugfix/SKILL.md does not satisfy the bugfix-mode clause "
        f"'{clause.value}' ({verdict.kind.value}) -- slice-05 has not landed"
    )
    return verdict


@then("that contract clause is new relative to the mode-unaware master workflow")
def then_clause_is_new(verdict: ClauseVerdict) -> None:
    # This step runs only on the NEW-clause Scenario Outline. Guard the
    # contract: a clause reaching this assertion MUST be ClauseKind.NEW -- a
    # PRESERVATION clause has no honest new-vs-master delta and an ABSENCE
    # clause asserts a removal, not a newness; neither must ever be asserted
    # "new" (slice-04 review Blocking 1).
    assert verdict.kind is ClauseKind.NEW, (
        f"clause '{verdict.clause.value}' is a {verdict.kind.value} clause -- "
        f"only NEW clauses carry a new-vs-master regression signal"
    )
    assert verdict.regressed_from_master, (
        f"the master-absent token for clause '{verdict.clause.value}' is not "
        f"in the file -- this clause cannot be a slice-05 regression signal"
    )
