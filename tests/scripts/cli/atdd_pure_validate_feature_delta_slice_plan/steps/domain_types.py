"""Domain types for the slice-plan-validation acceptance slice.

ADR-028 D2 / D2-bis (slice-plan section structure) + ADR-029 D3 / slice-06 of
the atdd-pure-roadmap-free-rollout (Mandate-12 criterion 1). Every domain noun
used in the Gherkin is expressed once here as a typed enum or NewType. Step
bodies and the composition service consume these typed parameters -- no raw
``str`` where a domain enum exists.
"""

from __future__ import annotations

from enum import Enum
from typing import NewType


# A kebab-case feature identifier (e.g. "atdd-pure-demo").
FeatureId = NewType("FeatureId", str)


class CheckMode(str, Enum):
    """How the validate-feature-delta CLI is invoked.

    PLAIN            -- the existing heading-form-only invocation
                        (``validate_feature_delta.py <path>``). Validates that
                        every ``## Wave:`` heading carries a [REF|WHY|HOW]
                        token; says nothing about the slice plan.
    REQUIRE_SLICE_PLAN -- the new slice-06 invocation
                        (``validate_feature_delta.py --require-slice-plan
                        --format=json <path>``). Adds the structural slice-plan
                        assertion on top of the heading-form check and emits a
                        single JSON object with a stable ``verdict`` token.
    """

    PLAIN = "plain"
    REQUIRE_SLICE_PLAN = "require_slice_plan"


class SlicePlanVerdict(str, Enum):
    """User-observable verdict of one slice-plan check invocation.

    The slice-06 CLI is invoked with ``--require-slice-plan --format=json`` and
    emits a single JSON object whose ``verdict`` field is one of a closed token
    set. The first four members below pair one-to-one with those tokens
    (``accepted`` / ``missing-slice-plan`` / ``malformed-slice-plan`` /
    ``malformed-wave-heading``); the verdict is read from that STRUCTURED token,
    never from free-text stdout substrings.

    ACCEPTED                -- token ``accepted``: the feature-delta passes
                               every check the selected mode runs.
    MISSING_SLICE_PLAN      -- token ``missing-slice-plan``: --require-slice-plan
                               was requested but the ``[REF] Slice Plan``
                               section is absent.
    MALFORMED_SLICE_PLAN    -- token ``malformed-slice-plan``: the section exists
                               but its table is not the D2 fixed five-column
                               shape -- wrong column count, columns reordered,
                               or zero slice rows.
    MALFORMED_WAVE_HEADING  -- token ``malformed-wave-heading``: a ``## Wave:``
                               heading violates the D2 [REF|WHY|HOW] schema (the
                               pre-existing check, still enforced under
                               --require-slice-plan).
    UNRECOGNISED_INVOCATION -- NO structured ``verdict`` token in stdout: the CLI
                               did not produce JSON output. On master the
                               --require-slice-plan / --format=json flags are
                               unknown, so the invocation lands here -- this is
                               the regression RED signal, NOT a real verdict.
    """

    ACCEPTED = "accepted"
    MISSING_SLICE_PLAN = "missing_slice_plan"
    MALFORMED_SLICE_PLAN = "malformed_slice_plan"
    MALFORMED_WAVE_HEADING = "malformed_wave_heading"
    UNRECOGNISED_INVOCATION = "unrecognised_invocation"


class SlicePlanShape(str, Enum):
    """The shape of the slice-plan section the validator inspects.

    WELL_FORMED        -- the canonical ``[REF] Slice Plan`` heading followed by
                          a five-column GFM table (Slice, Value statement,
                          Status, Annotation, Justification) with >= 1 slice
                          row -- the structural happy path.
    MANY_ROWS          -- a well-formed five-column table carrying many slice
                          rows (C3 cardinality: the "many" case).
    SECTION_ABSENT     -- the feature-delta has wave headings but no
                          ``[REF] Slice Plan`` heading at all.
    FOUR_COLUMNS       -- the section is present but its table has only four
                          columns instead of the required five.
    HEADER_ONLY        -- the section is present, the table header carries the
                          five columns, but there are zero slice rows
                          (C1 boundary: the empty-collection case).
    COLUMNS_REORDERED  -- a five-column table whose columns appear in a
                          different order. ADR-028 D2 (L137) mandates "Five
                          columns, fixed order", so a re-order is a malformed
                          slice plan (rejected), not an accepted variant.
    MALFORMED_HEADING  -- a well-formed slice plan, but elsewhere a ``## Wave:``
                          heading violates the D2 [REF|WHY|HOW] schema -- the
                          pre-existing heading check still fires.
    """

    WELL_FORMED = "well_formed"
    MANY_ROWS = "many_rows"
    SECTION_ABSENT = "section_absent"
    FOUR_COLUMNS = "four_columns"
    HEADER_ONLY = "header_only"
    COLUMNS_REORDERED = "columns_reordered"
    MALFORMED_HEADING = "malformed_heading"


# Gherkin-phrase -> typed-value lookups. Keeping these as module-level dicts
# lets each step body stay a single typed lookup + a single composition call
# (Mandate-12 criterion 3: no control flow in step bodies).

SLICE_PLAN_SHAPE_BY_PHRASE: dict[str, SlicePlanShape] = {
    "a well-formed slice plan": SlicePlanShape.WELL_FORMED,
    "a slice plan with many slice rows": SlicePlanShape.MANY_ROWS,
    "no slice-plan section": SlicePlanShape.SECTION_ABSENT,
    "a slice plan with only four columns": SlicePlanShape.FOUR_COLUMNS,
    "a slice plan with a header but zero slice rows": SlicePlanShape.HEADER_ONLY,
    "a slice plan whose table has the columns reordered": (
        SlicePlanShape.COLUMNS_REORDERED
    ),
    "a malformed wave heading and a well-formed slice plan": (
        SlicePlanShape.MALFORMED_HEADING
    ),
}

VERDICT_BY_PHRASE: dict[str, SlicePlanVerdict] = {
    "accepted": SlicePlanVerdict.ACCEPTED,
    "rejected for a missing slice plan": SlicePlanVerdict.MISSING_SLICE_PLAN,
    "rejected for a malformed slice plan": SlicePlanVerdict.MALFORMED_SLICE_PLAN,
    "rejected for a malformed wave heading": (SlicePlanVerdict.MALFORMED_WAVE_HEADING),
}

CHECK_MODE_BY_PHRASE: dict[str, CheckMode] = {
    "the slice-plan check": CheckMode.REQUIRE_SLICE_PLAN,
    "the plain heading check": CheckMode.PLAIN,
}
