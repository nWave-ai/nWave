"""Step definitions: the reference / tutorial / wave-flow docs name atdd_pure.

ADR-028 / ADR-029 / slice-12 of the atdd-pure-roadmap-free-rollout.

Layer 3 (FS-reading coherence). Example-only, no PBT machinery (Mandate 9/11):
the slice-12 contract is a closed enumerable set -- three NEW literal-regex
clauses (one per file) -- realised as one ``Scenario Outline``, NOT a
Hypothesis @given.

Step bodies delegate to ``DocumentationCoherenceComposition``; no inline
business logic (Mandate-12 criterion 3) -- each body is a typed lookup plus a
composition call or a single assertion over a composition-computed value.

Regression contract: every clause scenario FAILS on master and PASSES once
slice-12 lands. On master none of the three docs match their present_regex
(verified 0 matches 2026-05-20). The present_regex is verified 0 matches on
master, so these are genuine missing-functionality RED, not test bugs.

This test is SEPARATE from slices 04 / 15 (coherence over nw-deliver/SKILL.md),
slice-09 (the three finalize-adjacent skills), slice-11 (the roadmap skill /
command / root-why skill), and slice-13 (the three mode/resume/AT-set skills);
slice-12 targets three disjoint files.

See the acceptance brief WAVE: DISTILL section for the testable-surface
finding and the per-file regex master-evidence table.
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from .composition import DocumentationCoherenceComposition
from .domain_types import DOC_FILE_BY_PHRASE


scenarios("../documentation-coherence.feature")


# --- fixtures ----------------------------------------------------------------


def _composition() -> DocumentationCoherenceComposition:
    """Production-wired composition root over the real slice-12 doc file set."""
    return DocumentationCoherenceComposition()


# --- Given -------------------------------------------------------------------


@given("a reference / tutorial / wave-flow doc", target_fixture="composition")
def given_doc() -> DocumentationCoherenceComposition:
    # The Background builds the composition; the When loads the per-row file so
    # the Scenario Outline rows share one composition object (Pillar 2).
    return _composition()


# --- When --------------------------------------------------------------------


@when(parsers.parse("{doc_phrase} is read for the atdd_pure workflow"))
def when_read_doc(
    composition: DocumentationCoherenceComposition, doc_phrase: str
) -> None:
    composition.load_doc(DOC_FILE_BY_PHRASE[doc_phrase])


# --- Then --------------------------------------------------------------------


@then(parsers.parse("{doc_phrase} matches its slice-12 atdd_pure documentation regex"))
def then_matches_present_regex(
    composition: DocumentationCoherenceComposition, doc_phrase: str
) -> None:
    verdict = composition.evaluate_present_clause()
    assert verdict.present, (
        f"{doc_phrase}: the slice-12 present_regex matches "
        f"{verdict.match_count} line(s) -- expected >=1. The doc does not "
        f"document the atdd_pure roadmap-free path -- slice-12 has not landed"
    )
