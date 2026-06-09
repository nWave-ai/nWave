"""Step definitions: the nw-deliver atdd_pure spine documents the feature-end cycle.

ADR-028 D6 / slice-15 of the atdd-pure-roadmap-free-rollout.

Layer 3 (FS-reading coherence). Example-only, no PBT machinery (Mandate 9/11):
the four feature-end-cycle contract clauses are a closed enumerable set, the
three NEW ones realised as a ``Scenario Outline``, NOT a Hypothesis @given.

Step bodies delegate to ``FeatureEndCoherenceComposition``; no inline business
logic (Mandate-12 criterion 3) -- each body is a typed lookup plus a
composition call or a single assertion over a composition-computed value.

Regression contract: every NEW-clause scenario FAILS on master and PASSES once
slice-15 lands. On master ``nw-deliver/SKILL.md`` describes the atdd_pure path
only as a per-slice 7-phase A->G sequence -- ``E_BATCH_REFACTOR``,
``C_REVIEWER_AUDIT``, ``F_FINAL_REVIEW`` are PER-SLICE phases. It does NOT
define a once-per-feature feature-end cycle, NOT a collapsed deep review with
final integrity verification, NOT a ``FeatureEndCheckpoint`` resume record.
Each NEW clause's master-absent token is verified absent on master, so these
are genuine missing-functionality RED, not test bugs.

This test is SEPARATE from slice-04's ``atdd_pure_nw_deliver_spine`` coherence
test (shipped, commit 8d78f5c6c) -- that test gates the per-slice spine
contract over the same file; this test gates ONLY the feature-end-cycle
clauses slice-04 did not cover.

See the acceptance brief WAVE: DISTILL section for the testable-surface
finding: slice-15 ships only prose, so this executable coherence test is the
honest mechanical gate (the Class-P mechanism the rollout itself mandates).
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from .composition import ClauseVerdict, FeatureEndCoherenceComposition
from .domain_types import FEATURE_END_CLAUSE_BY_PHRASE, ClauseKind


scenarios("../nw-deliver-feature-end-cycle.feature")


# --- fixtures ----------------------------------------------------------------


def _composition() -> FeatureEndCoherenceComposition:
    """Production-wired composition root over the real nw-deliver SKILL.md."""
    return FeatureEndCoherenceComposition()


# pytest-bdd target_fixture pattern: the Given builds the composition so the
# When/Then steps share one loaded SUT.


# --- Given -------------------------------------------------------------------


@given("the nw-deliver orchestration spine", target_fixture="composition")
def given_spine() -> FeatureEndCoherenceComposition:
    composition = _composition()
    composition.load_nw_deliver_skill()
    return composition


# --- When --------------------------------------------------------------------


@when("the spine is read for the atdd_pure workflow")
def when_read_atdd_pure(composition: FeatureEndCoherenceComposition) -> None:
    # The SUT (the SKILL.md content) is mode-independent text; the mode here
    # records intent for the chained narrative (Pillar 2). No-op against the
    # already-loaded composition.
    assert composition.skill_text


# --- Then --------------------------------------------------------------------


@then(parsers.parse("the spine {feature_end_clause_phrase}"), target_fixture="verdict")
def then_clause_present(
    composition: FeatureEndCoherenceComposition, feature_end_clause_phrase: str
) -> ClauseVerdict:
    clause = FEATURE_END_CLAUSE_BY_PHRASE[feature_end_clause_phrase]
    verdict = composition.evaluate_clause(clause)
    assert verdict.present, (
        f"nw-deliver/SKILL.md is missing the feature-end-cycle clause "
        f"'{clause.value}' -- slice-15 has not landed"
    )
    return verdict


@then("that contract clause is new relative to the per-slice-only master spine")
def then_clause_is_new(verdict: ClauseVerdict) -> None:
    # This step runs only on the NEW-clause Scenario Outline. Guard the
    # contract: a clause reaching this assertion MUST be ClauseKind.NEW -- a
    # PRESERVATION clause has no honest new-vs-master delta and must never be
    # asserted "new" (slice-04 review Blocking 1 precedent).
    assert verdict.kind is ClauseKind.NEW, (
        f"clause '{verdict.clause.value}' is a {verdict.kind.value} clause -- "
        f"only NEW clauses carry a new-vs-master regression signal"
    )
    assert verdict.is_new, (
        f"the master-absent token for clause '{verdict.clause.value}' is not "
        f"in the file -- this clause cannot be a slice-15 regression signal"
    )
