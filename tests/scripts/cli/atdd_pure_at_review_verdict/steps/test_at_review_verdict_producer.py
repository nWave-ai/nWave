"""Step definitions: DISTILL records a tamper-evident AT-review verdict.

ADR-029 D5 / slice-07 of the atdd-pure-roadmap-free-rollout.

Layer 3 (subprocess/FS acceptance). Example-only, no PBT machinery
(Mandate 9/11) -- the @property tag on the tamper outline marks it as a
universal-invariant criterion (altering ANY signed field voids the signature),
realised at this layer as a `Scenario Outline` enumerating the signed field
set, NOT a Hypothesis @given.

The producer has a bounded-change contract: its only observable effect is one
new ATReviewVerdict line in the AT-completion ledger. The When-step asserts via
`assert_state_delta` over a port-exposed ledger universe (Mandate 8): the
verdict count changes as expected; the prior records are unchanged.

Step bodies delegate to `ATReviewVerdictComposition`; no inline business logic
(Mandate-12 criterion 3) -- each body is a typed lookup plus a composition call.

Regression contract: every scenario FAILS on master and PASSES once slice-07
lands. On master `scripts/cli/at_review_verdict.py` is a RED scaffold whose
producer functions raise `AssertionError` -- a deliberate missing-functionality
RED (the producer is unimplemented), not a test bug. Imports resolve cleanly
(Mandate 7: RED, not BROKEN). Once slice-07 implements the producer the
assertions exercise real record-writing behaviour.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.common.state_delta import assert_state_delta, set_to, unchanged

from .composition import ATReviewVerdictComposition
from .domain_types import (
    REVIEW_OUTCOME_BY_PHRASE,
    SIGNED_FIELD_BY_PHRASE,
    SIGNED_FIELD_NAMES,
    FeatureId,
    SignedField,
)


scenarios("../at-review-verdict-producer.feature")


@pytest.fixture
def composition(tmp_path: Path) -> ATReviewVerdictComposition:
    """Production-wired composition root over a tmp_path repository."""
    return ATReviewVerdictComposition(repo_dir=tmp_path / "repo")


@pytest.fixture
def result_box() -> dict[str, object]:
    """Carrier for the recording result across When -> Then steps."""
    return {}


# --- Given -------------------------------------------------------------------


@given("an atdd_pure feature with an empty AT-completion ledger")
def given_feature_with_empty_ledger(composition: ATReviewVerdictComposition) -> None:
    composition.create_repo_with_empty_ledger(FeatureId("atdd-pure-demo"))
    composition.seed_unrelated_ledger_record()


@given("an acceptance-designer reviewer approved the entering slice's AT set")
def given_reviewer_approved(composition: ATReviewVerdictComposition) -> None:
    # Precondition only: the approval verdict is supplied to the When-step.
    assert composition.ledger_path.exists()


@given("an acceptance-designer reviewer asked the entering slice for revision")
def given_reviewer_needs_revision(composition: ATReviewVerdictComposition) -> None:
    assert composition.ledger_path.exists()


@given("a slice with a recorded approved AT-review verdict in the ledger")
def given_recorded_verdict(composition: ATReviewVerdictComposition) -> None:
    composition.seed_recorded_verdict()


@given(parsers.parse("the entering slice has {count:d} reviewed acceptance tests"))
def given_reviewed_at_count(
    composition: ATReviewVerdictComposition, count: int
) -> None:
    composition.set_reviewed_at_count(count)


# --- When --------------------------------------------------------------------


@when("the designer records the AT-review verdict for the entering slice")
def when_record_approved(
    composition: ATReviewVerdictComposition,
    result_box: dict[str, object],
) -> None:
    before = composition.capture_universe()
    outcome = composition.record_verdict(
        REVIEW_OUTCOME_BY_PHRASE["approved the entering slice's AT set"]
    )
    after = composition.capture_universe()
    assert_state_delta(
        before=before,
        after=after,
        universe={"ledger.verdict_count", "ledger.prior_records"},
        expected={
            "ledger.verdict_count": set_to(1),
            "ledger.prior_records": unchanged(),
        },
    )
    result_box["outcome"] = outcome


@when("the designer completes the AT-review for the entering slice")
def when_complete_revision_review(
    composition: ATReviewVerdictComposition,
    result_box: dict[str, object],
) -> None:
    before = composition.capture_universe()
    outcome = composition.record_verdict(
        REVIEW_OUTCOME_BY_PHRASE["asked the entering slice for revision"]
    )
    after = composition.capture_universe()
    assert_state_delta(
        before=before,
        after=after,
        universe={"ledger.verdict_count", "ledger.prior_records"},
        expected={
            "ledger.verdict_count": unchanged(),
            "ledger.prior_records": unchanged(),
        },
    )
    result_box["outcome"] = outcome


@when("the designer records the AT-review verdict a second time for the slice")
def when_record_approved_again(
    composition: ATReviewVerdictComposition,
    result_box: dict[str, object],
) -> None:
    before = composition.capture_universe()
    outcome = composition.record_verdict(
        REVIEW_OUTCOME_BY_PHRASE["approved the entering slice's AT set"]
    )
    after = composition.capture_universe()
    assert_state_delta(
        before=before,
        after=after,
        universe={"ledger.verdict_count", "ledger.prior_records"},
        expected={
            "ledger.verdict_count": set_to(2),
            "ledger.prior_records": unchanged(),
        },
    )
    result_box["outcome"] = outcome


@when(parsers.parse('the recorded verdict has its "{altered_field}" altered'))
def when_alter_recorded_field(
    composition: ATReviewVerdictComposition,
    result_box: dict[str, object],
    altered_field: str,
) -> None:
    target = SIGNED_FIELD_BY_PHRASE[altered_field]
    result_box["still_verifies"] = composition.alter_recorded_field(target)


# --- Then --------------------------------------------------------------------


@then("the ledger gains one signed AT-review verdict for the entering slice")
def then_one_signed_verdict(composition: ATReviewVerdictComposition) -> None:
    assert len(composition.verdicts_for_entering_slice()) == 1


@then("the recorded verdict verifies against the reviewer signing key")
def then_recorded_verdict_verifies(composition: ATReviewVerdictComposition) -> None:
    assert composition.recorded_verdict_verifies()


@then("no earlier ledger record is altered")
def then_no_earlier_record_altered(composition: ATReviewVerdictComposition) -> None:
    prior = composition.non_verdict_records()
    assert prior == [{"event": "ATCompletion", "slice_id": "slice-06", "phase": "G"}]


@then("the signed verdict covers the slice identity and the reviewed AT set")
def then_signature_covers_identity_and_at_set(
    composition: ATReviewVerdictComposition,
) -> None:
    for field_name in ("slice_id", "at_ids", "at_content_hash"):
        assert composition.signature_covers(field_name), (
            f"{field_name} must be inside the HMAC-signed payload"
        )


@then("the signing input excludes the routing tag and the signature itself")
def then_signature_excludes_event_and_hmac(
    composition: ATReviewVerdictComposition,
) -> None:
    signed_keys = composition.signed_payload_keys()
    assert "event" not in signed_keys
    assert "hmac_sha256" not in signed_keys
    # SSOT: the closed signed-field set is derived from SignedField, never
    # re-transcribed as a literal here (Mandate-12 criterion 1/2).
    assert signed_keys == set(SIGNED_FIELD_NAMES)


@then("recomputing the signature over the altered verdict fails to verify")
def then_altered_verdict_fails_to_verify(result_box: dict[str, object]) -> None:
    assert result_box["still_verifies"] is False


@then("the ledger gains no AT-review verdict for the entering slice")
def then_no_verdict_recorded(
    composition: ATReviewVerdictComposition,
    result_box: dict[str, object],
) -> None:
    assert composition.verdicts_for_entering_slice() == []
    outcome = result_box["outcome"]
    assert outcome.record_written is False


@then(parsers.parse("the signed verdict lists {count:d} reviewed test identifiers"))
def then_signed_verdict_lists_at_ids(
    composition: ATReviewVerdictComposition, count: int
) -> None:
    recorded_ids = composition.latest_verdict_field(SignedField.AT_IDS)
    assert isinstance(recorded_ids, list)
    assert len(recorded_ids) == count


@then("the signed content fingerprint matches the reviewed acceptance tests")
def then_content_hash_matches_reviewed_bodies(
    composition: ATReviewVerdictComposition,
) -> None:
    # C6 Hole-fix: at_content_hash must reflect the actual reviewed bodies,
    # not just the at_ids set -- an in-place body rewrite must move the hash.
    recorded_hash = composition.latest_verdict_field(SignedField.AT_CONTENT_HASH)
    assert recorded_hash == composition.reviewed_content_hash


@then("the ledger holds two signed AT-review verdicts for the entering slice")
def then_two_signed_verdicts(composition: ATReviewVerdictComposition) -> None:
    assert len(composition.verdicts_for_entering_slice()) == 2


@then("the second recorded verdict is the one a later gate would trust")
def then_latest_verdict_is_the_second(
    composition: ATReviewVerdictComposition,
) -> None:
    verdicts = composition.verdicts_for_entering_slice()
    assert (
        composition.latest_verdict_field(SignedField.VERDICT) == verdicts[-1]["verdict"]
    )
    assert composition.recorded_verdict_verifies()
