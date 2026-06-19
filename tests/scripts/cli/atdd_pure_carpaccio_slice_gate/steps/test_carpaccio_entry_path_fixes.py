"""Regression tests for the ATDD-pure carpaccio entry-path fixes.

Friction-log F-02 / F-03b / F-04 (docs/analysis/atdd-pure-dogfooding-friction-
2026-05-20.md). Dogfooding ``fix-installer-private-skill-leak`` through
``/nw-deliver`` in ``atdd_pure`` mode surfaced three defects in the carpaccio
entry path; each defect gets a RED test here.

These are classic-TDD unit tests on the pure gate functions + the new CLI --
they extend the existing gate suite without touching the BDD scenarios in
``carpaccio-slice-gate.feature``.

F-04  -- the gate must resolve a feature's ``.feature`` files wherever DISTILL
          placed them (selected by the file-level ``@feature-{feature_id}``
          tag), not only under the hardcoded ``tests/scripts/cli/`` tree.
F-03b -- an entering slice that maps to ZERO ``@slice-NN`` scenarios must be
          rejected loud, never cleared vacuously.
F-02  -- ``at_review_verdict.py`` must expose a CLI ``main()`` so a verdict can
          be recorded without hand-scripting against gate internals.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import io
import json
import os
from pathlib import Path

import yaml

from scripts.cli import at_review_verdict, carpaccio_slice_gate


_FIXTURE_KEY = b"carpaccio-entry-path-fix-signing-key"
_SIGNING_KEY_ENV = "NWAVE_REVIEWER_SIGNING_KEY"


# ---------------------------------------------------------------------------
# Repo fixture helpers
# ---------------------------------------------------------------------------


def _write_config(repo: Path) -> None:
    nwave = repo / ".nwave"
    nwave.mkdir(parents=True, exist_ok=True)
    (nwave / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "workflow": {"mode": "atdd_pure"},
                "atdd_pure": {"carpaccio_slice_max": 3},
            }
        ),
        encoding="utf-8",
    )


def _write_signing_key(repo: Path) -> None:
    key_file = repo / ".nwave" / "secrets" / "reviewer-signing.key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(_FIXTURE_KEY)


def _write_feature_delta(repo: Path, feature_id: str, rows: str) -> None:
    delta = repo / "docs" / "feature" / feature_id / "feature-delta.md"
    delta.parent.mkdir(parents=True, exist_ok=True)
    delta.write_text(
        "# Feature Delta: entry-path fixture\n\n"
        "## Wave: DISCUSS / [REF] Slice Plan\n\n"
        "| Slice | Value statement | Status | Annotation | Justification |\n"
        "|-------|-----------------|--------|------------|---------------|\n"
        f"{rows}\n",
        encoding="utf-8",
    )


def _signed_record(
    slice_id: str, at_ids: list[str], content_hash: str
) -> dict[str, object]:
    record: dict[str, object] = {
        "event": "ATReviewVerdict",
        "schema_version": "1.0.0",
        "slice_id": slice_id,
        "verdict": "APPROVED",
        "reviewer_agent_id": "nw-acceptance-designer-reviewer",
        "at_ids": at_ids,
        "at_content_hash": content_hash,
        "timestamp": "2026-05-20T00:00:00Z",
        "findings_summary": [],
    }
    record["hmac_sha256"] = hmac.new(
        _FIXTURE_KEY,
        carpaccio_slice_gate.canonical_at_review_json(record),
        hashlib.sha256,
    ).hexdigest()
    return record


def _write_ledger(repo: Path, feature_id: str, record: dict[str, object]) -> None:
    ledger = repo / ".nwave" / "telemetry" / "atdd-pure" / f"{feature_id}.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(record) + "\n", encoding="utf-8")


def _run_gate(repo: Path, feature_id: str, slice_id: str) -> tuple[int, dict]:
    argv = [
        "--feature-id",
        feature_id,
        "--entering-slice",
        slice_id,
        "--repo-root",
        str(repo),
    ]
    buffer = io.StringIO()
    saved = os.environ.pop(_SIGNING_KEY_ENV, None)
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            exit_code = carpaccio_slice_gate.main(argv)
    finally:
        if saved is not None:
            os.environ[_SIGNING_KEY_ENV] = saved
    payload: dict = {}
    for line in buffer.getvalue().splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            payload = json.loads(line)
    return exit_code, payload


_SLICE_BODY = (
    "  Given a fixture precondition\n"
    "  When the fixture action occurs\n"
    "  Then the fixture outcome holds\n"
)


def _normalized_hash(scenario_count: int) -> str:
    body = (
        "given a fixture precondition\n"
        "when the fixture action occurs\n"
        "then the fixture outcome holds"
    )
    bodies = sorted(body for _ in range(scenario_count))
    return hashlib.sha256("".join(bodies).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# F-04 -- the gate resolves .feature files outside tests/scripts/cli/
# ---------------------------------------------------------------------------


def test_f04_gate_resolves_feature_files_by_feature_tag_outside_cli_tree(
    tmp_path: Path,
) -> None:
    """F-04: a feature whose ``.feature`` files live OUTSIDE ``tests/scripts/cli/``
    is resolved by the file-level ``@feature-{feature_id}`` tag, and its
    scenarios bind to the slice plan -> the slice clears the gate.
    """
    repo = tmp_path / "repo"
    feature_id = "fix-installer-private-skill-leak"
    _write_config(repo)
    _write_signing_key(repo)
    _write_feature_delta(
        repo,
        feature_id,
        "| slice-01 | Operator previews a plan | pending | @walking-skeleton "
        "| thinnest end-to-end vertical |",
    )
    # DISTILL test-placement: the .feature lives under tests/installer/...,
    # NOT under tests/scripts/cli/. It self-identifies with the feature tag.
    real_feature = (
        repo
        / "tests"
        / "installer"
        / "acceptance"
        / "private_skill_leak"
        / "wheel-privacy.feature"
    )
    real_feature.parent.mkdir(parents=True, exist_ok=True)
    real_feature.write_text(
        f"@feature-{feature_id} @concern-1\n"
        "Feature: The public package excludes private work\n\n"
        f"@slice-01\nScenario: scenario one\n{_SLICE_BODY}\n"
        f"@slice-01\nScenario: scenario two\n{_SLICE_BODY}",
        encoding="utf-8",
    )
    _write_ledger(
        repo,
        feature_id,
        _signed_record("slice-01", ["AT-1", "AT-2"], _normalized_hash(2)),
    )

    exit_code, payload = _run_gate(repo, feature_id, "slice-01")

    assert exit_code == 0, payload
    assert payload.get("event") == "SliceCleared"


def test_f04_gate_ignores_feature_files_for_other_features(tmp_path: Path) -> None:
    """F-04: a ``.feature`` file tagged for a DIFFERENT feature is not bound,
    so its scenarios never leak into this feature's slice coverage.
    """
    repo = tmp_path / "repo"
    feature_id = "feature-under-test"
    _write_config(repo)
    _write_signing_key(repo)
    _write_feature_delta(
        repo,
        feature_id,
        "| slice-01 | Operator previews a plan | pending | @walking-skeleton "
        "| thinnest end-to-end vertical |",
    )
    ours = repo / "tests" / "domain" / "acceptance" / "ours.feature"
    ours.parent.mkdir(parents=True, exist_ok=True)
    ours.write_text(
        f"@feature-{feature_id}\nFeature: ours\n\n"
        f"@slice-01\nScenario: ours one\n{_SLICE_BODY}",
        encoding="utf-8",
    )
    # A foreign feature file with an untagged scenario -- if the gate globbed
    # blindly it would trip assertion 2 (untagged scenario). The feature tag
    # filter must exclude it.
    foreign = repo / "tests" / "other" / "acceptance" / "foreign.feature"
    foreign.parent.mkdir(parents=True, exist_ok=True)
    foreign.write_text(
        "@feature-some-other-feature\nFeature: foreign\n\n"
        f"Scenario: untagged foreign scenario\n{_SLICE_BODY}",
        encoding="utf-8",
    )
    _write_ledger(
        repo,
        feature_id,
        _signed_record("slice-01", ["AT-1"], _normalized_hash(1)),
    )

    exit_code, payload = _run_gate(repo, feature_id, "slice-01")

    assert exit_code == 0, payload


# ---------------------------------------------------------------------------
# F-03b -- a slice with zero mapped scenarios is rejected, not vacuously passed
# ---------------------------------------------------------------------------


def test_f03b_slice_with_zero_scenarios_is_rejected_not_vacuously_passed(
    tmp_path: Path,
) -> None:
    """F-03b: the entering slice has a plan row but NO ``@slice-NN`` scenario
    maps to it. The gate must fail loud -- never clear a slice with no ATs.
    """
    repo = tmp_path / "repo"
    feature_id = "feature-zero-scenarios"
    _write_config(repo)
    _write_signing_key(repo)
    _write_feature_delta(
        repo,
        feature_id,
        "| slice-01 | Operator previews a plan | pending | @walking-skeleton "
        "| thinnest end-to-end vertical |\n"
        "| slice-02 | Operator applies the plan | pending | @core "
        "| follow-on capability slice |",
    )
    # Both slice-01 and slice-02 are PLANNED slices. Every @slice-NN tag in the
    # .feature has a matching plan row -- so this is NOT an orphan-tag case.
    # The entering slice (slice-01) is a planned slice that simply has ZERO
    # @slice-NN scenarios mapped to it.
    feature_file = repo / "tests" / "domain" / "acceptance" / "slices.feature"
    feature_file.parent.mkdir(parents=True, exist_ok=True)
    feature_file.write_text(
        f"@feature-{feature_id}\nFeature: slices\n\n"
        f"@slice-02\nScenario: belongs to slice two\n{_SLICE_BODY}",
        encoding="utf-8",
    )
    # A signed verdict for the empty AT set -- the vacuous-pass attack vector.
    empty_hash = hashlib.sha256(b"").hexdigest()
    _write_ledger(repo, feature_id, _signed_record("slice-01", [], empty_hash))

    exit_code, payload = _run_gate(repo, feature_id, "slice-01")

    assert exit_code != 0, "a slice with zero scenarios must NOT clear the gate"
    assert payload.get("reason") == "no-scenarios-for-slice", payload


# ---------------------------------------------------------------------------
# F-02 -- at_review_verdict exposes a CLI main()
# ---------------------------------------------------------------------------


def test_f02_at_review_verdict_cli_records_verdict_the_gate_then_accepts(
    tmp_path: Path,
) -> None:
    """F-02: the new ``at_review_verdict`` CLI records an APPROVED verdict
    (computing ``at_ids`` + ``at_content_hash`` itself from the slice's
    scenarios), and ``carpaccio_slice_gate`` then clears the slice -- a
    full producer/consumer round-trip with no hand-scripted internals.
    """
    repo = tmp_path / "repo"
    feature_id = "feature-cli-roundtrip"
    _write_config(repo)
    _write_signing_key(repo)
    _write_feature_delta(
        repo,
        feature_id,
        "| slice-01 | Operator previews a plan | pending | @walking-skeleton "
        "| thinnest end-to-end vertical |",
    )
    feature_file = repo / "tests" / "domain" / "acceptance" / "roundtrip.feature"
    feature_file.parent.mkdir(parents=True, exist_ok=True)
    feature_file.write_text(
        f"@feature-{feature_id}\nFeature: roundtrip\n\n"
        f"@slice-01\nScenario: scenario one\n{_SLICE_BODY}\n"
        f"@slice-01\nScenario: scenario two\n{_SLICE_BODY}",
        encoding="utf-8",
    )

    saved = os.environ.pop(_SIGNING_KEY_ENV, None)
    try:
        cli_exit = at_review_verdict.main(
            [
                "--feature-id",
                feature_id,
                "--slice-id",
                "slice-01",
                "--verdict",
                "APPROVED",
                "--reviewer-agent-id",
                "nw-acceptance-designer-reviewer",
                "--repo-root",
                str(repo),
            ]
        )
    finally:
        if saved is not None:
            os.environ[_SIGNING_KEY_ENV] = saved

    assert cli_exit == 0

    gate_exit, gate_payload = _run_gate(repo, feature_id, "slice-01")
    assert gate_exit == 0, gate_payload
    assert gate_payload.get("event") == "SliceCleared"


def test_f02_at_review_verdict_cli_needs_revision_writes_nothing(
    tmp_path: Path,
) -> None:
    """F-02: on NEEDS_REVISION the CLI writes no verdict and the gate then
    rejects the slice (reason ``absent``).
    """
    repo = tmp_path / "repo"
    feature_id = "feature-needs-revision"
    _write_config(repo)
    _write_signing_key(repo)
    _write_feature_delta(
        repo,
        feature_id,
        "| slice-01 | Operator previews a plan | pending | @walking-skeleton "
        "| thinnest end-to-end vertical |",
    )
    feature_file = repo / "tests" / "domain" / "acceptance" / "nr.feature"
    feature_file.parent.mkdir(parents=True, exist_ok=True)
    feature_file.write_text(
        f"@feature-{feature_id}\nFeature: nr\n\n"
        f"@slice-01\nScenario: scenario one\n{_SLICE_BODY}",
        encoding="utf-8",
    )

    saved = os.environ.pop(_SIGNING_KEY_ENV, None)
    try:
        cli_exit = at_review_verdict.main(
            [
                "--feature-id",
                feature_id,
                "--slice-id",
                "slice-01",
                "--verdict",
                "NEEDS_REVISION",
                "--reviewer-agent-id",
                "nw-acceptance-designer-reviewer",
                "--repo-root",
                str(repo),
            ]
        )
    finally:
        if saved is not None:
            os.environ[_SIGNING_KEY_ENV] = saved

    assert cli_exit == 0
    ledger = repo / ".nwave" / "telemetry" / "atdd-pure" / f"{feature_id}.jsonl"
    assert not ledger.exists() or ledger.read_text(encoding="utf-8").strip() == ""

    gate_exit, gate_payload = _run_gate(repo, feature_id, "slice-01")
    assert gate_exit == 45
    assert gate_payload.get("reason") == "absent", gate_payload
