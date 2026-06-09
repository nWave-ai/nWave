"""Domain types for the at-review-verdict-producer acceptance slice.

ADR-029 D5 / slice-07 of the atdd-pure-roadmap-free-rollout (Mandate-12
criterion 1). Every domain noun used in the Gherkin is expressed once here as a
typed enum or NewType. Step bodies and the composition service consume these
typed parameters -- no raw ``str`` where a domain enum exists.
"""

from __future__ import annotations

from enum import Enum
from typing import NewType


# A kebab-case feature identifier (e.g. "atdd-pure-demo").
FeatureId = NewType("FeatureId", str)

# A ``slice-NN`` slice identifier (e.g. "slice-07").
SliceId = NewType("SliceId", str)


class ReviewOutcome(str, Enum):
    """The acceptance-designer reviewer's verdict on a slice's AT set.

    APPROVED        -- the reviewer approved the AT set; the producer records a
                       signed ATReviewVerdict in the ledger.
    NEEDS_REVISION  -- the reviewer asked for another authoring pass; the
                       producer records NO verdict (the slice loops back).
    """

    APPROVED = "APPROVED"
    NEEDS_REVISION = "NEEDS_REVISION"


class SignedField(str, Enum):
    """A field inside the HMAC-signed payload of an ATReviewVerdict record.

    ADR-029 D5 B1: the producer signs EXACTLY these seven fields. Altering any
    of them after recording voids the signature -- the closed-world guarantee
    the DELIVER entry gate (slice-03 assertion 5) depends on. ``event`` and
    ``hmac_sha256`` are NOT members -- they are excluded from the signed input.

    This enum is the SINGLE SOURCE OF TRUTH for the signed-field set: the
    composition root and every step assertion derive the closed seven-field
    set from :data:`SIGNED_FIELD_NAMES` / :data:`EXCLUDED_FROM_SIGNATURE`
    rather than re-transcribing the literal field names.
    """

    SLICE_ID = "slice_id"
    AT_IDS = "at_ids"
    AT_CONTENT_HASH = "at_content_hash"
    SCHEMA_VERSION = "schema_version"
    VERDICT = "verdict"
    REVIEWER_AGENT_ID = "reviewer_agent_id"
    TIMESTAMP = "timestamp"


# SSOT: the exact closed set of HMAC-signed field names (ADR-029 D5 B1).
# Composition root and step assertions consume this -- never a re-typed literal.
SIGNED_FIELD_NAMES: frozenset[str] = frozenset(f.value for f in SignedField)

# SSOT: the record keys that are NOT part of the signed input -- ``event`` is a
# constant routing tag, ``hmac_sha256`` is the signature itself,
# ``findings_summary`` is human-readable prose not load-bearing for the gate.
EXCLUDED_FROM_SIGNATURE: frozenset[str] = frozenset(
    {"event", "hmac_sha256", "findings_summary"}
)


# Gherkin phrase -> ReviewOutcome (Mandate-12: parse-time coercion).
REVIEW_OUTCOME_BY_PHRASE: dict[str, ReviewOutcome] = {
    "approved the entering slice's AT set": ReviewOutcome.APPROVED,
    "asked the entering slice for revision": ReviewOutcome.NEEDS_REVISION,
}

# Gherkin phrase -> SignedField (the @property tamper outline's Examples rows).
SIGNED_FIELD_BY_PHRASE: dict[str, SignedField] = {
    "slice identity": SignedField.SLICE_ID,
    "reviewed AT set": SignedField.AT_IDS,
    "reviewed content": SignedField.AT_CONTENT_HASH,
    "schema version": SignedField.SCHEMA_VERSION,
    "reviewer verdict": SignedField.VERDICT,
}
