"""Step definitions: the nw-deliver spine branches on workflow mode.

ADR-028 D5 / slice-04 of the atdd-pure-roadmap-free-rollout.

Layer 3 (FS-reading coherence). Example-only, no PBT machinery (Mandate 9/11):
the four spine-branch contract clauses are a closed enumerable set, realised as
a `Scenario Outline`, NOT a Hypothesis @given.

Step bodies delegate to `SpineCoherenceComposition`; no inline business logic
(Mandate-12 criterion 3) -- each body is a typed lookup plus a composition call
or a single assertion over a composition-computed value.

Regression contract: every scenario FAILS on master and PASSES once slice-04
lands. On master `nw-deliver/SKILL.md` frames atdd_pure as an inner 7-phase
A->G replacement of the classic per-step cycle -- it does NOT branch the whole
spine into sibling workflows, skip Phase 1 roadmap creation, provision the
telemetry ledger dir, bump the telemetry schema, or route on the slice Class
column. Each clause's master-absent token is verified absent on master, so
these are genuine missing-functionality RED, not test bugs.

See the acceptance brief WAVE: DISTILL section for the testable-surface
finding: slice-04 ships only prose, so this executable coherence test is the
honest mechanical gate (the Class-P mechanism the rollout itself mandates).
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from .composition import ClauseVerdict, SpineCoherenceComposition
from .domain_types import SPINE_CLAUSE_BY_PHRASE, ClauseKind, SetupProvision


scenarios("../nw-deliver-spine-branch.feature")


# --- fixtures ----------------------------------------------------------------


def _composition() -> SpineCoherenceComposition:
    """Production-wired composition root over the real nw-deliver SKILL.md."""
    return SpineCoherenceComposition()


# pytest-bdd target_fixture pattern: the Given builds the composition so the
# When/Then steps share one loaded SUT.


# --- Given -------------------------------------------------------------------


@given("the nw-deliver orchestration spine", target_fixture="composition")
def given_spine() -> SpineCoherenceComposition:
    composition = _composition()
    composition.load_nw_deliver_skill()
    return composition


# --- When --------------------------------------------------------------------


@when("the spine is read for the atdd_pure workflow")
def when_read_atdd_pure(composition: SpineCoherenceComposition) -> None:
    # The SUT (the SKILL.md content) is mode-independent text; the mode here
    # records intent for the chained narrative (Pillar 2). No-op against the
    # already-loaded composition.
    assert composition.skill_text


@when("the spine is read for the classic workflow")
def when_read_classic(composition: SpineCoherenceComposition) -> None:
    assert composition.skill_text


# --- Then --------------------------------------------------------------------


@then(parsers.parse("the spine {spine_clause_phrase}"), target_fixture="verdict")
def then_clause_present(
    composition: SpineCoherenceComposition, spine_clause_phrase: str
) -> ClauseVerdict:
    clause = SPINE_CLAUSE_BY_PHRASE[spine_clause_phrase]
    verdict = composition.evaluate_clause(clause)
    assert verdict.present, (
        f"nw-deliver/SKILL.md is missing the spine-branch clause "
        f"'{clause.value}' -- slice-04 has not landed"
    )
    return verdict


@then("that contract clause is new relative to the classic-only master spine")
def then_clause_is_new(verdict: ClauseVerdict) -> None:
    # This step runs only on the NEW-clause Scenario Outline. Guard the
    # contract: a clause reaching this assertion MUST be ClauseKind.NEW -- a
    # PRESERVATION clause has no honest new-vs-master delta and must never be
    # asserted "new" (review Blocking 1).
    assert verdict.kind is ClauseKind.NEW, (
        f"clause '{verdict.clause.value}' is a {verdict.kind.value} clause -- "
        f"only NEW clauses carry a new-vs-master regression signal"
    )
    assert verdict.is_new, (
        f"the master-absent token for clause '{verdict.clause.value}' is not "
        f"in the file -- this clause cannot be a slice-04 regression signal"
    )


@then("the Setup phase provisions the AT-completion ledger directory")
def then_setup_provisions_ledger(composition: SpineCoherenceComposition) -> None:
    assert composition.setup_provisions(SetupProvision.TELEMETRY_LEDGER_DIR), (
        "the atdd_pure Setup does not provision .nwave/telemetry/atdd-pure/ "
        "in place of the skipped des-init-log step"
    )


# NOTE: this step text deliberately does NOT begin with "the spine " so it
# cannot be captured by the generic `@then(parsers.parse("the spine
# {spine_clause_phrase}"))` step above. The telemetry-schema check is its own
# dedicated predicate (composition.telemetry_schema_is_bumped) -- it is NOT a
# SpineContract clause, so routing it to `then_clause_present` would KeyError
# on SPINE_CLAUSE_BY_PHRASE. Keeping the leading token distinct is the
# structural fix for that step-resolution collision.
@then("the per-slice telemetry schema is declared as 1.1.0")
def then_telemetry_schema_bumped(composition: SpineCoherenceComposition) -> None:
    assert composition.telemetry_schema_is_bumped(), (
        "the SKILL.md does not declare telemetry_schema_version 1.1.0 "
        "(slice_id + at_ids per-phase-boundary record, ADR-028 D5)"
    )


@then("the classic roadmap creation phase is still documented")
def then_classic_phase_1_preserved(composition: SpineCoherenceComposition) -> None:
    assert composition.classic_phase_1_still_documented(), (
        "the classic Roadmap Creation phase was dropped -- slice-04 must add "
        "the atdd_pure sibling spine, never delete the classic one (AT c)"
    )


@then("the classic spine is named as a sibling top-level workflow")
def then_classic_named_sibling(composition: SpineCoherenceComposition) -> None:
    verdict = composition.evaluate_clause(
        SPINE_CLAUSE_BY_PHRASE["preserves the classic spine unchanged"]
    )
    assert verdict.present, (
        "the classic spine is not named as a sibling top-level workflow -- "
        "the orchestrator can fall through from atdd_pure into roadmap creation"
    )
