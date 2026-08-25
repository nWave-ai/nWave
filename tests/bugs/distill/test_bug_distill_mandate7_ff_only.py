"""Regression guard: DISTILL Mandate 7 must not imply a RED (failing) hand-off commit.

CONTRACT_SHAPE: pure-function
Outcome anchor: After running the suite, a reader of nw-distill Mandate 7 sees
that the DISTILL hand-off commit is green even under fast-forward-only merge —
the "commit the RED scaffolds" misreading that caused issue #56 fails CI, not a
user report.

Assumes the '## Mandate 7' heading remains stable; renaming or splitting the
section into level-2 subsections requires updating this guard.

Empirical anchor (nWave-ai/nWave issue #56): a user on rebase + fast-forward-only
with a pre-commit test gate read Mandate 7 ("Every acceptance test MUST be RED,
not BROKEN, when first created") as a directive to *commit failing tests*, and
the pre-commit hook blocked the DISTILL hand-off (26 failing tests at commit).

Root cause: the skill contradicted itself. The One-at-a-Time / Walking Skeleton
sections (SKILL.md:729,732) already describe a GREEN hand-off — the single
@walking_skeleton scenario green, every other scenario @skip/@pending — which is
safe under any merge model. Mandate 7 separately read as "commit RED scaffolds".
nw-tdd-methodology/SKILL.md:28 confirms the intended canon ("DELIVER ... only
unskips the scaffolds DISTILL produced"), so Mandate 7 was the outlier.

This fitness function asserts Mandate 7 explicitly states the hand-off commit is
green and that "RED vs BROKEN" governs error *classification* (checked when
DELIVER unskips a scenario), not the commit state. Pure file parsing — no
subprocess, no network. The fix is methodology-text only; the inversion-primitive
mechanism and any enforcement gate are intentionally out of scope (deferred).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
DISTILL_SKILL = REPO_ROOT / "nWave" / "skills" / "nw-distill" / "SKILL.md"


def _mandate7_section(text: str) -> str:
    """Return the '## Mandate 7' section body (up to the next level-2 heading)."""
    lines = text.splitlines()
    start = next(
        (i for i, ln in enumerate(lines) if ln.strip().startswith("## Mandate 7")),
        None,
    )
    assert start is not None, (
        "Mandate 7 section heading not found in nw-distill SKILL.md"
    )
    end = next(
        (
            j
            for j in range(start + 1, len(lines))
            if re.match(r"^##\s", lines[j]) and not lines[j].startswith("###")
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


@pytest.fixture(scope="module")
def mandate7() -> str:
    return _mandate7_section(DISTILL_SKILL.read_text(encoding="utf-8")).lower()


# Each anchor is a (description, substring) the reconciled Mandate 7 text must
# contain. Substrings are deliberately specific so the guard is meaningful, and
# all are author-controlled by the fix edit.
REQUIRED_ANCHORS = [
    ("hand-off commit is green by construction", "green by construction"),
    ("non-skeleton scenarios are skipped at hand-off", "@skip"),
    ("merge-model safety names fast-forward-only", "fast-forward-only"),
    ("merge-model safety names squash", "squash"),
    (
        "clarifies classification is not a commit-failing directive",
        "not a directive to commit failing tests",
    ),
    ("links the originating issue", "#56"),
]


@pytest.mark.parametrize("description,substring", REQUIRED_ANCHORS)
def test_mandate7_documents_green_handoff(
    mandate7: str, description: str, substring: str
):
    assert substring in mandate7, (
        f"Mandate 7 must document: {description}. "
        f"Expected to find {substring!r} in the '## Mandate 7' section of "
        f"nw-distill/SKILL.md (issue #56 reconciliation)."
    )


# Presence anchors above are not enough: the document would still be
# contradictory if the original standalone directive returned alongside the new
# text. Guard the ABSENCE of the phrasing that caused #56. These substrings are
# the original directive headline only — chosen NOT to collide with the
# reconciled text, which legitimately contains "not a directive to commit
# failing tests" and the quoted misreading "commit the RED scaffolds".
FORBIDDEN_PHRASES = [
    "when first created",
    "must be red, not broken",
]


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_mandate7_does_not_restate_failing_commit_directive(mandate7: str, phrase: str):
    assert phrase not in mandate7, (
        f"Mandate 7 must not contain {phrase!r}: that is the original directive "
        f"phrasing read as 'commit the failing scaffolds' (issue #56). Frame "
        f"RED-vs-BROKEN as a classification checked when DELIVER unskips, not a "
        f"commit-state directive."
    )
