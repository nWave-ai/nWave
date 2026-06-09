"""Domain types for the carpaccio-slice-gate acceptance slice.

ADR-028 D2-bis + ADR-029 D5 / slice-03 of the atdd-pure-roadmap-free-rollout
(Mandate-12 criterion 1). Every domain noun used in the Gherkin is expressed
once here as a typed enum or NewType. Step bodies and the composition service
consume these typed parameters -- no raw ``str`` where a domain enum exists.
"""

from __future__ import annotations

from enum import Enum
from typing import NewType


# A kebab-case feature identifier (e.g. "atdd-pure-demo").
FeatureId = NewType("FeatureId", str)

# A ``slice-NN`` slice identifier (e.g. "slice-01").
SliceId = NewType("SliceId", str)


class GateVerdict(str, Enum):
    """User-observable verdict of one carpaccio-slice-gate invocation.

    Maps onto the gate CLI exit-code contract (ADR-028 D2-bis + ADR-029 D5).

    CLEARED            -- exit 0: the slice is cleared to enter A_GREEN_ATS.
    SLICE_PLAN_MISSING -- exit 1: feature-delta or the slice-plan section absent.
    MALFORMED_INPUT    -- exit 2: malformed slice-plan table OR an orphan
                          ``@slice-NN`` tag with no matching plan row.
    SLICE_TOO_LARGE    -- exit 44 CARPACCIO_SLICE_TOO_LARGE: an un-annotated
                          over-N slice, a coverage/ordering violation, or an
                          annotated slice missing its justification.
    AT_REVIEW_REJECTED -- exit 45 AT_REVIEW_NOT_APPROVED: assertion 5 failed --
                          the AT-review verdict is absent / stale / unsigned.
    """

    CLEARED = "cleared"  # exit 0
    SLICE_PLAN_MISSING = "slice_plan_missing"  # exit 1
    MALFORMED_INPUT = "malformed_input"  # exit 2
    SLICE_TOO_LARGE = "slice_too_large"  # exit 44
    AT_REVIEW_REJECTED = "at_review_rejected"  # exit 45


class SlicePlanShape(str, Enum):
    """The shape of the ``[REF] Slice Plan`` table the gate parses.

    VALID_IN_SIZE       -- a well-formed five-column table; the entering slice
                           carries an AT count within the N ceiling.
    OVER_N_UNANNOTATED  -- the entering slice has more than N ATs, no @coupled
                           tag, no annotation -- a big-bang attempt.
    OVER_N_COUPLED      -- the entering slice has more than N ATs but every AT
                           is @coupled:<group-id>-tagged and the plan row records
                           a coupling_justification -- an indivisible group.
    ORDERED_BEFORE_WS   -- the entering slice is ordered before the
                           @walking-skeleton slice (carpaccio assertion 3 --
                           walking-skeleton-first ordering violation -> exit 44).
    UNTAGGED_SCENARIO   -- an authored ``.feature`` scenario carries no
                           @slice-NN tag at all (carpaccio assertion 2 --
                           incremental total-coverage violation -> exit 44).
    MALFORMED_TABLE     -- wrong column count / duplicate slice id / a
                           non-``slice-NN`` identifier (exit 2).
    ORPHAN_FEATURE_TAG  -- a ``.feature`` scenario carries a @slice-NN tag for
                           which no slice-NN row exists in the plan table
                           (exit 2 -- the tag set disagrees with the plan).
    SECTION_ABSENT      -- the feature-delta has no ``[REF] Slice Plan`` heading
                           (exit 1).
    """

    VALID_IN_SIZE = "valid_in_size"
    OVER_N_UNANNOTATED = "over_n_unannotated"
    OVER_N_COUPLED = "over_n_coupled"
    ORDERED_BEFORE_WS = "ordered_before_ws"
    UNTAGGED_SCENARIO = "untagged_scenario"
    MALFORMED_TABLE = "malformed_table"
    ORPHAN_FEATURE_TAG = "orphan_feature_tag"
    SECTION_ABSENT = "section_absent"


class MalformedCause(str, Enum):
    """Which input the gate identifies as malformed on an exit-2 verdict.

    Exit 2 (MALFORMED_INPUT) is reached by two distinct, differently-fixed
    conditions; the gate's emitted JSON diagnostic MUST name which one so the
    operator knows whether to fix the slice-plan table or the ``.feature`` tag.

    SLICE_PLAN_TABLE -- the ``[REF] Slice Plan`` GFM table is malformed (wrong
                        column count / duplicate slice id / bad identifier).
    FEATURE_SLICE_TAG -- a ``.feature`` scenario carries an orphan @slice-NN tag
                         with no matching slice-plan row.
    """

    SLICE_PLAN_TABLE = "the slice-plan table"
    FEATURE_SLICE_TAG = "a .feature slice tag"


class ATReviewRejectReason(str, Enum):
    """The closed six-value ``ATReviewGateRejected`` reason set (ADR-029 D5).

    Assertion 5 of the carpaccio gate emits exactly one of these on exit 45.
    The set is closed: no other reason may escape the AT-review gate.

    KEY_ABSENT       -- the reviewer signing key cannot be resolved
                        (NWAVE_REVIEWER_SIGNING_KEY unset AND
                        .nwave/secrets/reviewer-signing.key absent). Fail-closed.
    ABSENT           -- no ATReviewVerdict record exists for the entering slice.
    NOT_APPROVED     -- a record exists but its verdict is not APPROVED.
    HMAC_MISMATCH    -- the HMAC does not recompute over the seven signed fields.
    STALE_AT_SET     -- the record's at_ids set differs from the slice's current
                        @slice-NN scenario id set.
    STALE_AT_CONTENT -- the record's at_content_hash differs from the hash over
                        the slice's current normalized AT bodies.
    """

    KEY_ABSENT = "key-absent"
    ABSENT = "absent"
    NOT_APPROVED = "not-approved"
    HMAC_MISMATCH = "hmac-mismatch"
    STALE_AT_SET = "stale-at-set"
    STALE_AT_CONTENT = "stale-at-content"


class ATReviewRecordState(str, Enum):
    """How the ATReviewVerdict record is provisioned in the AT-completion ledger.

    Each state isolates exactly one of the six assertion-5 failure conditions,
    plus the APPROVED happy state. The composition translates the state into a
    concrete ledger + signing-key fixture.

    APPROVED_VALID  -- a correctly-signed APPROVED record matching the slice's
                       current AT set by id and content hash; assertion 5 PASS.
    NO_SIGNING_KEY  -- env unset, no key file -> reason key-absent.
    NO_RECORD       -- ledger has no record for the entering slice -> reason absent.
    NEEDS_REVISION  -- a signed record whose verdict is NEEDS_REVISION
                       -> reason not-approved.
    TAMPERED_HMAC   -- an APPROVED record whose hmac_sha256 was altered
                       -> reason hmac-mismatch.
    STALE_AT_IDS    -- an APPROVED record whose at_ids no longer match the
                       slice's scenario set -> reason stale-at-set.
    STALE_BODY_HASH -- an APPROVED record whose at_content_hash no longer
                       matches the slice's normalized AT bodies -> reason
                       stale-at-content.
    """

    APPROVED_VALID = "approved_valid"
    NO_SIGNING_KEY = "no_signing_key"
    NO_RECORD = "no_record"
    NEEDS_REVISION = "needs_revision"
    TAMPERED_HMAC = "tampered_hmac"
    STALE_AT_IDS = "stale_at_ids"
    STALE_BODY_HASH = "stale_body_hash"


# Gherkin-phrase -> typed-value lookups. Keeping these as module-level dicts
# lets each step body stay a single typed lookup + a single composition call
# (Mandate-12 criterion 3: no control flow in step bodies).

SLICE_PLAN_SHAPE_BY_PHRASE: dict[str, SlicePlanShape] = {
    "a valid in-size slice plan": SlicePlanShape.VALID_IN_SIZE,
    "an un-annotated over-size slice": SlicePlanShape.OVER_N_UNANNOTATED,
    "a coupled over-size slice with a recorded justification": (
        SlicePlanShape.OVER_N_COUPLED
    ),
    "a slice ordered before the walking-skeleton slice": (
        SlicePlanShape.ORDERED_BEFORE_WS
    ),
    "an untagged authored scenario": SlicePlanShape.UNTAGGED_SCENARIO,
    "a malformed slice-plan table": SlicePlanShape.MALFORMED_TABLE,
    "an orphan slice tag with no plan row": SlicePlanShape.ORPHAN_FEATURE_TAG,
    "no slice plan section": SlicePlanShape.SECTION_ABSENT,
}

VERDICT_BY_PHRASE: dict[str, GateVerdict] = {
    "cleared to enter implementation": GateVerdict.CLEARED,
    "blocked with a missing slice plan": GateVerdict.SLICE_PLAN_MISSING,
    "blocked with a malformed input error": GateVerdict.MALFORMED_INPUT,
    "blocked with an oversized slice error": GateVerdict.SLICE_TOO_LARGE,
    "blocked with an AT-review rejection": GateVerdict.AT_REVIEW_REJECTED,
}

# Exit-2 diagnostic cause phrase -> typed cause. The malformed-input Examples
# rows pair a slice-plan shape with the cause the gate's JSON diagnostic must
# name (H2 -- the operator must know which input to fix).
MALFORMED_CAUSE_BY_PHRASE: dict[str, MalformedCause] = {
    "the slice-plan table": MalformedCause.SLICE_PLAN_TABLE,
    "a .feature slice tag": MalformedCause.FEATURE_SLICE_TAG,
}

# Each rejection-reason phrase pairs the closed-set reason with the ledger
# fixture state that triggers exactly that reason -- the parametrized AT (d)
# iterates this mapping so all six assertion-5 branches are covered.
AT_REVIEW_REASON_BY_PHRASE: dict[
    str, tuple[ATReviewRecordState, ATReviewRejectReason]
] = {
    "the reviewer signing key is unavailable": (
        ATReviewRecordState.NO_SIGNING_KEY,
        ATReviewRejectReason.KEY_ABSENT,
    ),
    "no AT-review verdict was recorded for the slice": (
        ATReviewRecordState.NO_RECORD,
        ATReviewRejectReason.ABSENT,
    ),
    "the AT-review verdict is not an approval": (
        ATReviewRecordState.NEEDS_REVISION,
        ATReviewRejectReason.NOT_APPROVED,
    ),
    "the AT-review verdict signature does not verify": (
        ATReviewRecordState.TAMPERED_HMAC,
        ATReviewRejectReason.HMAC_MISMATCH,
    ),
    "the reviewed scenario set no longer matches the slice": (
        ATReviewRecordState.STALE_AT_IDS,
        ATReviewRejectReason.STALE_AT_SET,
    ),
    "a reviewed scenario body was rewritten after approval": (
        ATReviewRecordState.STALE_BODY_HASH,
        ATReviewRejectReason.STALE_AT_CONTENT,
    ),
}
