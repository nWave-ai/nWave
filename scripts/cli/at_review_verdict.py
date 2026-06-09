"""AT-review verdict producer (ADR-029 D5 -- PRODUCER half, slice-07).

After the acceptance-designer reviewer APPROVES a slice's AT set, the atdd_pure
DISTILL step records the approval as a tamper-evident ``ATReviewVerdict`` record
appended to the AT-completion ledger ``.nwave/telemetry/atdd-pure/{feature_id}.jsonl``.

slice-03's ``carpaccio_slice_gate.py`` is the CONSUMER (assertion 5) that reads
this record at the DELIVER entry gate; this module is the PRODUCER that writes
it. The HMAC signs EXACTLY the seven fields ``schema_version``, ``slice_id``,
``verdict``, ``reviewer_agent_id``, ``at_ids``, ``at_content_hash``,
``timestamp`` via ``canonical_at_review_json()``; ``event``, ``hmac_sha256`` and
``findings_summary`` are excluded from the signed input.

Stdlib-only (no third-party imports) so the module is bundle-safe.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path


# ADR-029 D5 B1: the seven HMAC-signed fields, in declaration order. The
# canonical serializer sorts keys, so ``event``, ``hmac_sha256`` and
# ``findings_summary`` are simply absent from the signed payload.
_SIGNED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "slice_id",
    "verdict",
    "reviewer_agent_id",
    "at_ids",
    "at_content_hash",
    "timestamp",
)

_SCHEMA_VERSION = "1.0.0"
_EVENT = "ATReviewVerdict"
_APPROVED = "APPROVED"

# Reviewer signing-key precedence -- mirrors carpaccio_slice_gate.py.
_SIGNING_KEY_ENV = "NWAVE_REVIEWER_SIGNING_KEY"
_SIGNING_KEY_FILE = ".nwave/secrets/reviewer-signing.key"


def canonical_at_review_json(record: dict[str, object]) -> bytes:
    """Serialize the seven signed fields of an ATReviewVerdict to canonical JSON.

    ADR-029 D5 B1: ``json.dumps`` over EXACTLY the seven signed fields with
    sorted keys and no whitespace, UTF-8 encoded. ``event``, ``hmac_sha256``
    and ``findings_summary`` are NOT part of the signed input.
    """
    signed = {field: record[field] for field in _SIGNED_FIELDS}
    return json.dumps(signed, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_verdict_hmac(record: dict[str, object], key: bytes) -> str:
    """Compute HMAC-SHA256 over ``canonical_at_review_json(record)`` as hex."""
    return hmac.new(key, canonical_at_review_json(record), hashlib.sha256).hexdigest()


def _load_signing_key(repo_root: Path) -> bytes:
    """Resolve the reviewer signing key: env first, file fallback."""
    env_value = os.environ.get(_SIGNING_KEY_ENV)
    if env_value:
        return env_value.encode("utf-8")
    key_file = repo_root / _SIGNING_KEY_FILE
    if key_file.is_file():
        return key_file.read_bytes().strip()
    raise AssertionError(
        "reviewer signing key unresolvable: set NWAVE_REVIEWER_SIGNING_KEY or "
        f"provide {_SIGNING_KEY_FILE}"
    )


def _ledger_path(repo_root: Path, feature_id: str) -> Path:
    """The AT-completion ledger path for ``feature_id`` (ADR-028 D3)."""
    return repo_root / ".nwave" / "telemetry" / "atdd-pure" / f"{feature_id}.jsonl"


def record_at_review_verdict(
    repo_root: Path,
    feature_id: str,
    slice_id: str,
    verdict: str,
    reviewer_agent_id: str,
    at_ids: list[str],
    at_content_hash: str,
    timestamp: str,
    findings_summary: list[object],
) -> None:
    """Append one signed ATReviewVerdict record to the AT-completion ledger.

    Writes a single JSONL line to ``.nwave/telemetry/atdd-pure/{feature_id}.jsonl``
    carrying the eight-field record (the seven signed fields + ``event``) plus
    the ``hmac_sha256`` signature and ``findings_summary``. Earlier ledger
    records are never altered (append-only).
    """
    record: dict[str, object] = {
        "event": _EVENT,
        "schema_version": _SCHEMA_VERSION,
        "slice_id": slice_id,
        "verdict": verdict,
        "reviewer_agent_id": reviewer_agent_id,
        "at_ids": list(at_ids),
        "at_content_hash": at_content_hash,
        "timestamp": timestamp,
        "findings_summary": list(findings_summary),
    }
    record["hmac_sha256"] = compute_verdict_hmac(record, _load_signing_key(repo_root))

    ledger = _ledger_path(repo_root, feature_id)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def record_review_outcome(
    repo_root: Path,
    feature_id: str,
    slice_id: str,
    verdict: str,
    reviewer_agent_id: str,
    at_ids: list[str],
    at_content_hash: str,
    timestamp: str,
    findings_summary: list[object],
) -> bool:
    """Record a reviewer outcome; return whether a verdict was written.

    ADR-029 D5 producer half: on an ``APPROVED`` verdict the producer appends a
    signed ``ATReviewVerdict`` record (via :func:`record_at_review_verdict`) and
    returns ``True``. On ``NEEDS_REVISION`` it writes NOTHING -- the slice loops
    back to the acceptance-designer -- and returns ``False``. The
    APPROVED-writes / NEEDS_REVISION-skips decision is the producer's, not the
    caller's.
    """
    if verdict != _APPROVED:
        return False

    record_at_review_verdict(
        repo_root=repo_root,
        feature_id=feature_id,
        slice_id=slice_id,
        verdict=verdict,
        reviewer_agent_id=reviewer_agent_id,
        at_ids=at_ids,
        at_content_hash=at_content_hash,
        timestamp=timestamp,
        findings_summary=findings_summary,
    )
    return True


# ---------------------------------------------------------------------------
# CLI -- friction-fix F-02
# ---------------------------------------------------------------------------
#
# docs/analysis/atdd-pure-dogfooding-friction-2026-05-20.md F-02: the producer
# exposed only library functions, so an operator recording an ATReviewVerdict
# had to hand-script the ``at_ids`` + ``at_content_hash`` derivation against
# ``carpaccio_slice_gate`` internals. This CLI computes those itself by reusing
# the gate's scenario parser, keeping the producer and consumer derivations DRY.


def _slice_at_derivation(
    repo_root: Path, feature_id: str, slice_id: str
) -> tuple[list[str], str]:
    """Derive ``(at_ids, at_content_hash)`` for ``slice_id`` from its scenarios.

    Reuses ``carpaccio_slice_gate``'s ``.feature`` resolution + parsing + the
    consumer's ``_at_content_hash`` so the producer signs exactly what the
    gate will later verify. ``carpaccio_slice_gate`` is stdlib-only at import
    time (``yaml`` is imported lazily), so this import keeps the bundle safe.
    """
    from scripts.cli import carpaccio_slice_gate

    scenarios = carpaccio_slice_gate.parse_scenarios(
        carpaccio_slice_gate._read_feature_files(repo_root, feature_id)
    )
    slice_scenarios = [s for s in scenarios if slice_id in s.slice_tags]
    at_ids = [f"AT-{n}" for n in range(1, len(slice_scenarios) + 1)]
    at_content_hash = carpaccio_slice_gate._at_content_hash(slice_scenarios)
    return at_ids, at_content_hash


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="at_review_verdict",
        description=(
            "Record an AT-review verdict (ADR-029 D5 producer). On APPROVED a "
            "signed ATReviewVerdict record is appended to the AT-completion "
            "ledger; on NEEDS_REVISION nothing is written."
        ),
    )
    parser.add_argument("--feature-id", required=True)
    parser.add_argument("--slice-id", required=True)
    parser.add_argument(
        "--verdict", required=True, choices=["APPROVED", "NEEDS_REVISION"]
    )
    parser.add_argument("--reviewer-agent-id", required=True)
    parser.add_argument("--findings", nargs="*", default=[])
    parser.add_argument("--repo-root", default=None)
    return parser.parse_args(sys.argv[1:] if argv is None else list(argv))


def _resolve_repo_root(override: str | None) -> Path:
    if override:
        return Path(override)
    env = os.environ.get("NWAVE_REPO_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    """Record an AT-review verdict from the command line.

    Computes ``at_ids`` + ``at_content_hash`` itself from the entering slice's
    scenarios -- the operator supplies only the feature id, slice id, verdict
    and reviewer id. On APPROVED a signed record is appended to the ledger; on
    NEEDS_REVISION nothing is written. Returns 0 on success.
    """
    args = _parse_args(argv)
    repo_root = _resolve_repo_root(args.repo_root)
    at_ids, at_content_hash = _slice_at_derivation(
        repo_root, args.feature_id, args.slice_id
    )
    timestamp = (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    written = record_review_outcome(
        repo_root=repo_root,
        feature_id=args.feature_id,
        slice_id=args.slice_id,
        verdict=args.verdict,
        reviewer_agent_id=args.reviewer_agent_id,
        at_ids=at_ids,
        at_content_hash=at_content_hash,
        timestamp=timestamp,
        findings_summary=list(args.findings),
    )
    outcome = "recorded" if written else "skipped (NEEDS_REVISION)"
    sys.stdout.write(
        json.dumps(
            {
                "event": "ATReviewVerdictCLI",
                "feature_id": args.feature_id,
                "slice_id": args.slice_id,
                "verdict": args.verdict,
                "verdict_written": written,
                "outcome": outcome,
            },
            sort_keys=True,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
