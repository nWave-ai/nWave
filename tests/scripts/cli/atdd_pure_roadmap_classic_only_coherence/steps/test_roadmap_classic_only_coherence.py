"""Step definitions: the roadmap skill / command flag classic-mode-only.

ADR-028 / ADR-029 / slice-11 of the atdd-pure-roadmap-free-rollout.

Layer 3 (FS-reading coherence). Example-only, no PBT machinery (Mandate 9/11):
the slice-11 contract is a closed enumerable set -- three NEW literal-regex
clauses (one per file) -- realised as one ``Scenario Outline``, NOT a
Hypothesis @given.

Step bodies delegate to ``RoadmapClassicOnlyComposition``; no inline business
logic (Mandate-12 criterion 3) -- each body is a typed lookup plus a
composition call or a single assertion over a composition-computed value.

Regression contract: every clause scenario FAILS on master and PASSES once
slice-11 lands. On master none of the three files match their present_regex
(verified 0 matches 2026-05-20). The present_regex is verified 0 matches on
master, so these are genuine missing-functionality RED, not test bugs.

This test is SEPARATE from slices 04 / 15 (coherence over nw-deliver/SKILL.md),
slice-09 (the three finalize-adjacent skills), and slice-13 (the three
mode/resume/AT-set skills); slice-11 targets three disjoint files.

See the acceptance brief WAVE: DISTILL section for the testable-surface
finding and the per-file regex master-evidence table.
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from .composition import RoadmapClassicOnlyComposition
from .domain_types import ROADMAP_FILE_BY_PHRASE


scenarios("../roadmap-classic-only-coherence.feature")


# --- fixtures ----------------------------------------------------------------


def _composition() -> RoadmapClassicOnlyComposition:
    """Production-wired composition root over the real slice-11 .md file set."""
    return RoadmapClassicOnlyComposition()


# --- Given -------------------------------------------------------------------


@given("a roadmap-or-root-why file", target_fixture="composition")
def given_roadmap_file() -> RoadmapClassicOnlyComposition:
    # The Background builds the composition; the When loads the per-row file so
    # the Scenario Outline rows share one composition object (Pillar 2).
    return _composition()


# --- When --------------------------------------------------------------------


@when(parsers.parse("{file_phrase} is read for the atdd_pure workflow"))
def when_read_file(
    composition: RoadmapClassicOnlyComposition, file_phrase: str
) -> None:
    composition.load_file(ROADMAP_FILE_BY_PHRASE[file_phrase])


# --- Then --------------------------------------------------------------------


@then(
    parsers.parse(
        "{file_phrase} matches its slice-11 classic-only-or-atdd_pure-context regex"
    )
)
def then_matches_present_regex(
    composition: RoadmapClassicOnlyComposition, file_phrase: str
) -> None:
    verdict = composition.evaluate_present_clause()
    assert verdict.present, (
        f"{file_phrase}: the slice-11 present_regex matches "
        f"{verdict.match_count} line(s) -- expected >=1. The file does not "
        f"carry its classic-only flag / atdd_pure-context paragraph -- "
        f"slice-11 has not landed"
    )
