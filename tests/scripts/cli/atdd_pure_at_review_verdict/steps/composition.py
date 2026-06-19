"""Composition root for the at-review-verdict-producer acceptance slice.

ADR-029 D5 / slice-07 (Mandate-12, Pillar 3). Wires the PRODUCTION
at-review-verdict producer surface (``scripts.cli.at_review_verdict``) against a
tmp_path repo fixture. Business logic lives here as the single source of truth;
step bodies delegate to ``ATReviewVerdictComposition`` methods and never inline
logic.

Layer 3 (subprocess/FS acceptance): the producer is the driving port; the only
driven port is the real filesystem (tmp_path). No PBT machinery (Mandate 9/11).

Contract shape: bounded-change. The producer's observable effect is one new
``ATReviewVerdict`` line appended to the AT-completion ledger
``.nwave/telemetry/atdd-pure/{feature_id}.jsonl`` -- earlier records are never
altered.

RED scaffold note: ``scripts/cli/at_review_verdict.py`` is a RED scaffold on
master (slice-07 implements it). Its functions raise ``AssertionError`` so
every scenario is RED (missing functionality), not BROKEN (import error) --
the import below resolves cleanly because the scaffold module exists.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path

# Production driving port -- slice-07 producer surface. RED scaffold on master.
from scripts.cli.at_review_verdict import (
    canonical_at_review_json,
    compute_verdict_hmac,
    record_at_review_verdict,
    record_review_outcome,
)

from .domain_types import (
    FeatureId,
    ReviewOutcome,
    SignedField,
    SliceId,
)


# Reviewer signing-key precedence -- mirrors verify_commit_trailers.py.
_SIGNING_KEY_ENV = "NWAVE_REVIEWER_SIGNING_KEY"
_SIGNING_KEY_FILE = ".nwave/secrets/reviewer-signing.key"
_FIXTURE_SIGNING_KEY = b"slice-07-acceptance-fixture-signing-key"

# A reviewed slice's normalized AT bodies -- the producer hashes these into
# at_content_hash. Default two scenarios so at_ids = {AT-1, AT-2} is non-trivial;
# cardinality scenarios override the count via ``set_reviewed_at_count``.
_REVIEWED_AT_BODIES = (
    "given a fixture precondition\nwhen the fixture action occurs\n"
    "then the first fixture outcome holds",
    "given another fixture precondition\nwhen a second fixture action occurs\n"
    "then the second fixture outcome holds",
)


def _at_body(index: int) -> str:
    """A distinct normalized AT body for scenario index ``index`` (1-based)."""
    return (
        f"given precondition number {index}\n"
        f"when action number {index} occurs\n"
        f"then outcome number {index} holds"
    )


@dataclass(frozen=True)
class RecordOutcome:
    """Observable result of one verdict-recording invocation.

    record_written -- whether the producer appended an ATReviewVerdict line.
    """

    record_written: bool


class ATReviewVerdictComposition:
    """Production-wired composition root for the at-review-verdict producer.

    Wires the real producer surface against a tmp_path repository. Holds the
    slice identity, the reviewed AT set, and the AT-completion ledger path.
    """

    def __init__(self, repo_dir: Path) -> None:
        self.repo_dir = repo_dir
        self.feature_id: FeatureId = FeatureId("atdd-pure-demo")
        self.entering_slice: SliceId = SliceId("slice-07")
        # The reviewed slice's normalized AT bodies. Cardinality scenarios
        # override this via ``set_reviewed_at_bodies``; default is two.
        self._at_bodies: tuple[str, ...] = _REVIEWED_AT_BODIES

    # --- Given: provision the repository -------------------------------------

    def create_repo_with_empty_ledger(self, feature_id: FeatureId) -> None:
        """Create a tmp_path repo with an empty AT-completion ledger + key."""
        self.feature_id = feature_id
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text("", encoding="utf-8")
        key_file = self.repo_dir / _SIGNING_KEY_FILE
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(_FIXTURE_SIGNING_KEY)

    def set_reviewed_at_count(self, count: int) -> None:
        """Set the entering slice's reviewed AT set to ``count`` distinct ATs.

        Drives the C3 cardinality scenario: the producer must hash and sign an
        AT set of any size -- singleton (count=1), the default pair, or many.
        Each body is distinct so ``at_content_hash`` genuinely covers content.
        """
        self._at_bodies = tuple(_at_body(i) for i in range(1, count + 1))

    def seed_unrelated_ledger_record(self) -> None:
        """Append one pre-existing record so 'no earlier record altered' bites."""
        prior = {"event": "ATCompletion", "slice_id": "slice-06", "phase": "G"}
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(prior) + "\n")

    def seed_recorded_verdict(self) -> None:
        """Append a genuine signed APPROVED verdict for the entering slice."""
        record_at_review_verdict(
            repo_root=self.repo_dir,
            feature_id=str(self.feature_id),
            slice_id=str(self.entering_slice),
            verdict=ReviewOutcome.APPROVED.value,
            reviewer_agent_id="nw-acceptance-designer-reviewer",
            at_ids=list(self.reviewed_at_ids),
            at_content_hash=self.reviewed_content_hash,
            timestamp="2026-05-20T00:00:00Z",
            findings_summary=[],
        )

    # --- When: record the AT-review verdict ----------------------------------

    def record_verdict(self, outcome: ReviewOutcome) -> RecordOutcome:
        """Record the reviewer outcome via the production producer surface.

        Both outcomes go through the producer (``record_review_outcome``): the
        producer owns the APPROVED-writes / NEEDS_REVISION-skips decision, so
        the rejected-slice scenario genuinely exercises producer behaviour
        rather than a step-local branch (no Fixture Theater).
        """
        written = record_review_outcome(
            repo_root=self.repo_dir,
            feature_id=str(self.feature_id),
            slice_id=str(self.entering_slice),
            verdict=outcome.value,
            reviewer_agent_id="nw-acceptance-designer-reviewer",
            at_ids=list(self.reviewed_at_ids),
            at_content_hash=self.reviewed_content_hash,
            timestamp="2026-05-20T00:00:00Z",
            findings_summary=[],
        )
        return RecordOutcome(record_written=written)

    def alter_recorded_field(self, target: SignedField) -> bool:
        """Alter one signed field of the recorded verdict; report verify result.

        Reads the recorded verdict back, mutates the named signed field, and
        recomputes the HMAC over the altered payload via the production
        ``compute_verdict_hmac``. Returns True iff the recomputed signature
        still matches the stored ``hmac_sha256`` (it must not).
        """
        record = self._latest_verdict()
        stored_signature = record["hmac_sha256"]
        record[target.value] = self._tampered_value(record[target.value])
        recomputed = compute_verdict_hmac(record, _FIXTURE_SIGNING_KEY)
        return hmac.compare_digest(str(recomputed), str(stored_signature))

    # --- Then: observe the ledger --------------------------------------------

    def verdicts_for_entering_slice(self) -> list[dict[str, object]]:
        """All ATReviewVerdict records in the ledger for the entering slice."""
        records: list[dict[str, object]] = []
        if not self.ledger_path.is_file():
            return records
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("event") == "ATReviewVerdict" and record.get(
                "slice_id"
            ) == str(self.entering_slice):
                records.append(record)
        return records

    def recorded_verdict_verifies(self) -> bool:
        """True iff the recorded verdict's HMAC verifies against the key."""
        record = self._latest_verdict()
        recomputed = compute_verdict_hmac(record, _FIXTURE_SIGNING_KEY)
        return hmac.compare_digest(str(recomputed), str(record["hmac_sha256"]))

    def signed_payload_keys(self) -> set[str]:
        """The exact key set the producer's canonical serializer signs.

        Decoded back from the canonical JSON byte sequence the producer feeds
        to HMAC -- proves the signed input is exactly the seven fields and
        excludes ``event`` and ``hmac_sha256``.
        """
        record = self._latest_verdict()
        signed_bytes = canonical_at_review_json(record)
        return set(json.loads(signed_bytes).keys())

    def signature_covers(self, field_name: str) -> bool:
        """True iff ``field_name`` is inside the signed payload."""
        return field_name in self.signed_payload_keys()

    def latest_verdict_field(self, field: SignedField) -> object:
        """The value of ``field`` on the LATEST recorded verdict for the slice.

        Assertion 5 selects the LATEST ``ATReviewVerdict``; this exposes a
        signed field of that record so the C4 re-review scenario can prove the
        second recording -- not the first -- is the one the gate would trust.
        """
        return self._latest_verdict()[field.value]

    def non_verdict_records(self) -> list[dict[str, object]]:
        """Ledger records that are NOT ATReviewVerdict (the seeded prior set)."""
        records: list[dict[str, object]] = []
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("event") != "ATReviewVerdict":
                records.append(record)
        return records

    # --- Universe snapshot (Mandate 8) ---------------------------------------

    def capture_universe(self) -> dict[str, object]:
        """Snapshot the port-exposed observable names the producer affects."""
        verdicts = self.verdicts_for_entering_slice()
        return {
            "ledger.verdict_count": len(verdicts),
            "ledger.prior_records": json.dumps(self.non_verdict_records()),
        }

    # --- Internals -----------------------------------------------------------

    @property
    def ledger_path(self) -> Path:
        return (
            self.repo_dir
            / ".nwave"
            / "telemetry"
            / "atdd-pure"
            / f"{self.feature_id}.jsonl"
        )

    @property
    def reviewed_at_ids(self) -> tuple[str, ...]:
        return tuple(f"AT-{n}" for n in range(1, len(self._at_bodies) + 1))

    @property
    def reviewed_content_hash(self) -> str:
        bodies = sorted(self._at_bodies)
        return hashlib.sha256("".join(bodies).encode("utf-8")).hexdigest()

    def _latest_verdict(self) -> dict[str, object]:
        verdicts = self.verdicts_for_entering_slice()
        assert verdicts, "no ATReviewVerdict record found for the entering slice"
        return verdicts[-1]

    @staticmethod
    def _tampered_value(original: object) -> object:
        """A guaranteed-different value of the same broad shape as ``original``."""
        if isinstance(original, list):
            return [*original, "AT-tampered"]
        return f"{original}-tampered"
