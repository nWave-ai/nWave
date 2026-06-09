"""Walking-skeleton @wiring_e2e integration test for the ATDD-pure carpaccio spine.

The carpaccio per-slice ENTRY path is a composition of four spine CLIs:
``carpaccio_slice_gate.py`` (the consumer) reads a feature-delta's ``[REF] Slice
Plan`` table + the feature's ``.feature`` files + the AT-completion ledger that
``at_review_verdict.py`` (the producer) writes. Slices 01-15 of the spine
rollout shipped each CLI with isolated unit/AT tests using hand-shaped fixtures.
NO test wired them together against a real feature's ``.feature`` files
end-to-end. That gap let three "fixture passes, real invocation fails" defects
ship (see ``docs/analysis/atdd-pure-dogfooding-friction-2026-05-20.md``):

  * F-04 — the gate hardcoded the AT directory to
    ``tests/scripts/cli/{feature_id}/acceptance`` (the rollout's own coherence-
    test layout). A real feature places ``.feature`` files per the DISTILL
    test-placement decision, OUTSIDE that path → gate found 0 scenarios.
  * F-06 — the F-04 fix's ``_file_feature_tags`` stopped scanning at the first
    ``#`` Gherkin comment line, so a ``.feature`` file with a leading comment
    block (before the ``@feature-`` tag) yielded zero file-level tags → the
    gate could not bind the file to the feature.

Both passed their own unit fixtures (comment-free, in-the-hardcoded-path) and
failed on the real ``wheel-privacy.feature``. A subprocess-real ``@wiring_e2e``
test that exercises the ENTRY path against a realistic feature layout closes
that whole class. This is the integration-layer walking skeleton the 5-layer
mandate requires but the spine rollout never produced.

Layer discipline (memory ``feedback_layered_test_discipline_universe_per_layer``):
this is an integration / walking-skeleton test — real composition via
subprocess, real I/O, kept lean (two tests). Universe is the user-visible
end-to-end output: subprocess exit code + emitted JSON ``event`` / ``reason``.
Each test builds a fully self-contained tmp project so it never reads or
mutates real-repo state (the real feature ledger lives under gitignored
``.nwave/`` — a test that touched it would be Fixture Theater of the worst kind).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = [pytest.mark.wiring_e2e, pytest.mark.integration]

_REPO_ROOT = Path(__file__).resolve().parents[4]
_GATE_CLI = _REPO_ROOT / "scripts" / "cli" / "carpaccio_slice_gate.py"
_VERDICT_CLI = _REPO_ROOT / "scripts" / "cli" / "at_review_verdict.py"

_SIGNING_KEY = "wiring-e2e-dev-key"

# A realistic feature-delta slice plan: the canonical 5-column [REF] Slice Plan
# table the real fix-installer-private-skill-leak feature carries.
_FEATURE_DELTA = """# Feature Delta: demo-privacy-leak

Workflow mode: `atdd_pure`.

## Wave: DISCUSS / [REF] Slice Plan

| Slice | Value statement | Status | Annotation | Justification |
|-------|-----------------|--------|------------|---------------|
| slice-01 | A customer installing the public wheel receives only public work | pending | @walking-skeleton | First end-to-end vertical: strip runs before the wheel build. |
| slice-02 | A release engineer cannot ship a wheel carrying private work | pending | | A mechanical post-build privacy gate. |
"""

# The real shape that tripped F-06: an 11-line leading `#` comment block BEFORE
# the file-level @feature- tag. F-04's own fixtures were comment-free.
_FEATURE_FILE = """# Concern 1 (wheel privacy) + Concern 2 (public skill survival).
#
# The public PyPI wheel is built by applying the privacy strip to the
# framework source tree. Two contracts hold over the resulting wheel:
#   1. No private agent file and no private skill directory is inside it.
#   2. Public skills that public artifacts depend on still survive the strip.
#
# These are regression scenarios: each FAILS against current master and
# PASSES once the fix lands.

@feature-demo-privacy-leak @concern-1
Feature: The public package excludes private work

  @slice-01 @walking_skeleton @driving_port
  Scenario: A customer receives the public package free of private work
    When the public package is prepared for release
    Then the prepared package contains no private agent

  @slice-01 @driving_port
  Scenario: Preparing the public package keeps every public agent
    When the public package is prepared for release
    Then the prepared package keeps every public agent

  @slice-01 @driving_port
  Scenario: Preparing the public package is idempotent
    When the public package is prepared for release again
    Then the twice-prepared package contains no private agent

  @slice-02 @driving_port
  Scenario: The release gate refuses a package carrying private work
    When the release privacy gate inspects a package with private work
    Then the release privacy gate refuses to pass

  @slice-02 @driving_port
  Scenario: The release gate passes a public-only package
    When the release privacy gate inspects a public-only package
    Then the release privacy gate passes
"""


def _run(cli: Path, *args: str, repo: Path) -> subprocess.CompletedProcess[str]:
    """Invoke a spine CLI as a real subprocess (not an in-process call)."""
    env = {
        "NWAVE_REVIEWER_SIGNING_KEY": _SIGNING_KEY,
        "NWAVE_REPO_ROOT": str(repo),
        "PATH": _path_env(),
    }
    return subprocess.run(
        [sys.executable, str(cli), "--repo-root", str(repo), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_REPO_ROOT),
        timeout=60,
    )


def _path_env() -> str:
    import os

    return os.environ.get("PATH", "")


def _build_tmp_project(
    root: Path,
    *,
    feature_id: str,
    feature_file_dir: str,
    feature_file_text: str,
    feature_delta_text: str = _FEATURE_DELTA,
) -> None:
    """Materialise a self-contained tmp project the spine CLIs can run against.

    Mirrors the real layout: a feature-delta with a 5-column slice-plan table,
    one ``.feature`` file placed at ``feature_file_dir`` (a path the test
    chooses — to exercise the F-04 out-of-hardcoded-path case), a
    ``.nwave/config.yaml`` with ``workflow.mode: atdd_pure``, and the reviewer
    signing key file.
    """
    delta = root / "docs" / "feature" / feature_id / "feature-delta.md"
    delta.parent.mkdir(parents=True, exist_ok=True)
    delta.write_text(feature_delta_text, encoding="utf-8")

    feature = root / feature_file_dir / "demo-privacy.feature"
    feature.parent.mkdir(parents=True, exist_ok=True)
    feature.write_text(feature_file_text, encoding="utf-8")

    config = root / ".nwave" / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        "workflow:\n  mode: atdd_pure\natdd_pure:\n  carpaccio_slice_max: 3\n",
        encoding="utf-8",
    )

    key = root / ".nwave" / "secrets" / "reviewer-signing.key"
    key.parent.mkdir(parents=True, exist_ok=True)
    key.write_text(_SIGNING_KEY, encoding="utf-8")


def test_carpaccio_entry_path_clears_a_well_formed_slice(tmp_path: Path) -> None:
    """The spine clears a well-formed slice end-to-end through real subprocesses.

    Wires producer → consumer against a realistic feature:
      * a ``.feature`` file with a leading ``#`` comment block (F-06 regression),
      * placed OUTSIDE ``tests/scripts/cli/`` — at ``tests/installer/acceptance/``,
        the kind of DISTILL test-placement a real feature uses (F-04 regression),
      * the AT-review verdict recorded by the real ``at_review_verdict.py`` CLI
        (round-trip through the CLI, not a hand-written ledger line).

    Universe: subprocess exit code + emitted JSON ``event``.
    """
    feature_id = "demo-privacy-leak"
    _build_tmp_project(
        tmp_path,
        feature_id=feature_id,
        # Real feature placement — NOT the F-04 hardcoded tests/scripts/cli path.
        feature_file_dir="tests/installer/acceptance/private_skill_leak",
        feature_file_text=_FEATURE_FILE,
    )

    # PRODUCER: record the AT-review verdict via the real CLI. The CLI computes
    # at_ids + at_content_hash itself from the slice's scenarios — the same
    # derivation the consumer re-runs, so producer and consumer stay DRY.
    produced = _run(
        _VERDICT_CLI,
        "--feature-id",
        feature_id,
        "--slice-id",
        "slice-01",
        "--verdict",
        "APPROVED",
        "--reviewer-agent-id",
        "nw-acceptance-designer-reviewer",
        repo=tmp_path,
    )
    assert produced.returncode == 0, produced.stderr
    assert json.loads(produced.stdout)["verdict_written"] is True

    # CONSUMER: the carpaccio slice gate, as a real subprocess.
    gated = _run(
        _GATE_CLI,
        "--feature-id",
        feature_id,
        "--entering-slice",
        "slice-01",
        repo=tmp_path,
    )
    payload = json.loads(gated.stdout)
    assert gated.returncode == 0, f"gate did not clear slice: {gated.stdout}"
    assert payload["event"] == "SliceCleared"
    assert payload["slice_id"] == "slice-01"
    assert payload["feature_id"] == feature_id


def test_carpaccio_entry_path_fails_loud_on_malformed_and_missing_inputs(
    tmp_path: Path,
) -> None:
    """The spine fails loud — never vacuous-passes — for malformed slice inputs.

    Three sad paths the unit fixtures under-covered, each via real subprocess:
      * an entering slice with NO matching scenarios → ``no-scenarios-for-slice``
        (the F-03/F-04 vacuous-pass class — must be a loud exit-45 rejection),
      * an AT verdict that was never recorded → ``absent`` rejection,
      * a slice-plan table with the wrong column count → exit-2 malformed input.
    """
    feature_id = "demo-privacy-leak"

    # --- Case A: a slice with zero mapped scenarios fails loud (not vacuous) ---
    _build_tmp_project(
        tmp_path,
        feature_id=feature_id,
        feature_file_dir="tests/installer/acceptance/private_skill_leak",
        feature_file_text=_FEATURE_FILE,
    )
    # Record a verdict so the AT-review half would pass — isolating the
    # no-scenarios check. slice-03 has no row, but we test an in-plan slice
    # with zero scenarios by recording for a tagged-but-empty slice instead:
    # add a slice-03 row + verdict, leaving it with no @slice-03 scenario.
    delta_with_empty_slice = _FEATURE_DELTA + (
        "| slice-03 | An orphan slice nothing tags | pending | | n/a |\n"
    )
    (tmp_path / "docs" / "feature" / feature_id / "feature-delta.md").write_text(
        delta_with_empty_slice, encoding="utf-8"
    )
    no_scenarios = _run(
        _GATE_CLI,
        "--feature-id",
        feature_id,
        "--entering-slice",
        "slice-03",
        repo=tmp_path,
    )
    payload_a = json.loads(no_scenarios.stdout)
    assert no_scenarios.returncode == 45, no_scenarios.stdout
    assert payload_a["reason"] == "no-scenarios-for-slice"

    # --- Case B: a well-formed slice with NO recorded verdict is rejected ---
    no_verdict_root = tmp_path / "no_verdict"
    _build_tmp_project(
        no_verdict_root,
        feature_id=feature_id,
        feature_file_dir="tests/installer/acceptance/private_skill_leak",
        feature_file_text=_FEATURE_FILE,
    )
    no_verdict = _run(
        _GATE_CLI,
        "--feature-id",
        feature_id,
        "--entering-slice",
        "slice-01",
        repo=no_verdict_root,
    )
    payload_b = json.loads(no_verdict.stdout)
    assert no_verdict.returncode == 45, no_verdict.stdout
    assert payload_b["reason"] == "absent"

    # --- Case C: a malformed slice-plan table is exit-2 malformed input ---
    malformed_root = tmp_path / "malformed"
    bad_delta = _FEATURE_DELTA.replace(
        "| slice-01 | A customer installing the public wheel receives only "
        "public work | pending | @walking-skeleton | First end-to-end "
        "vertical: strip runs before the wheel build. |",
        "| slice-01 | only three columns |",
    )
    _build_tmp_project(
        malformed_root,
        feature_id=feature_id,
        feature_file_dir="tests/installer/acceptance/private_skill_leak",
        feature_file_text=_FEATURE_FILE,
        feature_delta_text=bad_delta,
    )
    malformed = _run(
        _GATE_CLI,
        "--feature-id",
        feature_id,
        "--entering-slice",
        "slice-01",
        repo=malformed_root,
    )
    payload_c = json.loads(malformed.stdout)
    assert malformed.returncode == 2, malformed.stdout
    assert payload_c["event"] == "MalformedInput"
    assert payload_c["cause"] == "the slice-plan table"
