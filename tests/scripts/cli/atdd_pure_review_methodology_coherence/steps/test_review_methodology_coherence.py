"""Step definitions: the review methodology and reviewer agents document the
atdd_pure roadmap-free spine.

ADR-028 7-phase A->G sibling spine + ADR-029 reviewer DoR/DoD re-split /
slice-10 of the atdd-pure-roadmap-free-rollout.

Layer 3 (FS-reading coherence). Example-only, no PBT machinery (Mandate 9/11):
the slice-10 contract is a closed enumerable set -- six files across two
coherence mechanisms -- realised as three ``Scenario Outline``s, NOT a
Hypothesis @given.

Step bodies delegate to ``ReviewMethodologyCoherenceComposition``; no inline
business logic (Mandate-12 criterion 3) -- each body is a typed lookup plus a
composition call or a single assertion over a composition-computed value.

Regression contract -- two mechanisms (slice-10 design note H2-final):

* REGEX (4 files): every ``present_regex`` token is verified 0 occurrences on
  master 2026-05-20 -- the "names the atdd_pure roadmap-free spine" Then FAILS
  on master and PASSES once slice-10 lands. The ``absent_regex`` tokens are
  ALSO 0 on master (vacuity audit) -- the "stale classic-only framing is
  absent" And step is asserted only as a documented non-regression guard, never
  as a slice-10 RED signal.

* SEMANTIC-ROLE (2 files): the ledger token "AT-completion ledger" is verified
  0 occurrences on master in both files -- predicate 1 FAILS on master. Each
  file carries 3 unscoped ``execution-log.json`` lines on master -- predicate 2
  FAILS on master. Both are genuine missing-functionality RED.

This test is SEPARATE from slices 04 / 09 / 15 (coherence over disjoint file
sets); slice-10 targets six disjoint files.

See the acceptance brief WAVE: DISTILL section for the testable-surface
finding: slice-10 ships only prose, so this executable coherence test is the
honest mechanical gate (the Class-P mechanism the rollout itself mandates).
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from .composition import (
    RegexVerdict,
    ReviewMethodologyCoherenceComposition,
)
from .domain_types import (
    REGEX_FILE_BY_PHRASE,
    SEMANTIC_ROLE_FILE_BY_PHRASE,
    Mechanism,
)


scenarios("../review-methodology-coherence.feature")


# --- fixtures ----------------------------------------------------------------


def _composition() -> ReviewMethodologyCoherenceComposition:
    """Production-wired composition root over the real slice-10 file set."""
    return ReviewMethodologyCoherenceComposition()


# --- Given -------------------------------------------------------------------


@given("a review-methodology or reviewer-agent file", target_fixture="composition")
def given_coherence_file() -> ReviewMethodologyCoherenceComposition:
    # The Background builds the composition; the When loads the per-row file so
    # the Scenario Outline rows share one composition object (Pillar 2).
    return _composition()


# --- When --------------------------------------------------------------------


@when(parsers.parse("{file_phrase} is read for the atdd_pure workflow"))
def when_read_file(
    composition: ReviewMethodologyCoherenceComposition, file_phrase: str
) -> None:
    composition.load_file(_file_by_phrase(file_phrase))


def _file_by_phrase(file_phrase: str):
    """Resolve a Gherkin file phrase to its typed ``CoherenceFile``.

    Both phrase maps are tried; a regex-gated and a semantic-role-gated phrase
    set are disjoint, so a single lookup is unambiguous. Kept a helper so the
    When body stays a single delegated call (Mandate-12 criterion 3).
    """
    if file_phrase in REGEX_FILE_BY_PHRASE:
        return REGEX_FILE_BY_PHRASE[file_phrase]
    return SEMANTIC_ROLE_FILE_BY_PHRASE[file_phrase]


# --- Then: REGEX mechanism ---------------------------------------------------


@then(
    parsers.parse("{file_phrase} names the atdd_pure roadmap-free spine"),
    target_fixture="regex_verdict",
)
def then_names_roadmap_free_spine(
    composition: ReviewMethodologyCoherenceComposition, file_phrase: str
) -> RegexVerdict:
    verdict = composition.evaluate_regex_clause()
    # Falsifiable slice-10 regression signal: the present_regex token is
    # verified 0 occurrences on master, so this assertion FAILS on master.
    assert verdict.present_matched, (
        f"{file_phrase}: the file does not name the atdd_pure roadmap-free "
        f"spine (its present_regex token, verified master-absent, is still "
        f"missing) -- slice-10 has not landed"
    )
    return verdict


@then(parsers.parse("the stale classic-only framing is absent from {file_phrase}"))
def then_stale_framing_absent(regex_verdict: RegexVerdict, file_phrase: str) -> None:
    # Non-regression GUARD, NOT the slice-10 RED signal. The four absent_regex
    # tokens already match zero on master (vacuity audit, domain_types.py) --
    # this step cannot distinguish master from post-slice-10. It is asserted
    # only to guard against a future edit RE-introducing the stale framing.
    # The composition flags absent_is_vacuous so this step is documented as
    # non-falsifiable and never masquerades as the regression signal.
    assert regex_verdict.absent_is_vacuous, (
        f"{file_phrase}: expected the absent clause to be the documented "
        f"vacuous non-regression guard -- if it became falsifiable the "
        f"contract metadata must be updated"
    )
    assert regex_verdict.absent_clear, (
        f"{file_phrase}: the stale classic-only framing token reappeared -- a "
        f"later edit re-introduced the absent_regex literal"
    )


# --- Then: SEMANTIC-ROLE mechanism -------------------------------------------


@then(
    parsers.parse("{file_phrase} names the atdd_pure AT-completion-ledger phase record")
)
def then_names_ledger(
    composition: ReviewMethodologyCoherenceComposition, file_phrase: str
) -> None:
    verdict = composition.evaluate_semantic_role_clause()
    # Predicate 1: the ledger token "AT-completion ledger" is verified 0
    # occurrences on master in both files -- this assertion FAILS on master.
    assert verdict.mechanism is Mechanism.SEMANTIC_ROLE, (
        f"{file_phrase}: expected a SEMANTIC-ROLE verdict"
    )
    assert verdict.names_ledger, (
        f"{file_phrase}: the file does not name the atdd_pure phase record "
        f"'AT-completion ledger' -- slice-10 has not landed"
    )


@then(parsers.parse("every execution-log line in {file_phrase} is classic-scoped"))
def then_execution_log_classic_scoped(
    composition: ReviewMethodologyCoherenceComposition, file_phrase: str
) -> None:
    verdict = composition.evaluate_semantic_role_clause()
    # Predicate 2: master carries 3 unscoped execution-log.json lines in each
    # file -- this assertion FAILS on master and PASSES once slice-10 scopes
    # every such line with a classic / workflow.mode qualifier.
    assert not verdict.unscoped_lines, (
        f"{file_phrase}: {len(verdict.unscoped_lines)} execution-log.json "
        f"line(s) carry no classic / workflow.mode qualifier -- an unscoped "
        f"mention frames execution-log.json as THE phase record (slice-10 has "
        f"not scoped the prose). First offender "
        f"L{verdict.unscoped_lines[0].line_number}: "
        f"{verdict.unscoped_lines[0].text!r}"
    )
