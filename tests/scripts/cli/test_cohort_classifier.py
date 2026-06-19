"""Tests for cohort_classifier CLI (plan v3 §4.1.bis).

CONTRACT_SHAPE: pure-function (CLI exit code + stdout JSON; FS read-only)
Outcome anchor: DISCUSS plan v3 §4.1.bis "Pilot scope drift risk — features
picked at random of M-cohort vs deliberate pre-assignment".

Tests enter through the CLI's main() driving port and assert on
(exit_code, stdout_json). The full universe is observable through these
two surfaces; no internal state inspected.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


REPO_ROOT = Path(__file__).resolve().parents[3]
CLI_PATH = REPO_ROOT / "scripts" / "cli" / "cohort_classifier.py"


# ---------------------------------------------------------------------------
# In-process driving port (faster than subprocess; PBT-friendly)
# ---------------------------------------------------------------------------


def _run_cli(args: list[str]) -> tuple[int, dict[str, object]]:
    """Invoke cohort_classifier.main() in-process; return (exit_code, json)."""
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from scripts.cli import cohort_classifier
    finally:
        sys.path.pop(0)

    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cohort_classifier.main(args)
    stdout = buf.getvalue().strip()
    payload = json.loads(stdout) if stdout else {}
    return code, payload


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _make_feature_dir(repo: Path, feature_id: str, scenario_count: int) -> Path:
    """Build a docs/feature/<id>/distill/ tree with N Scenario: entries."""
    distill = repo / "docs" / "feature" / feature_id / "distill"
    distill.mkdir(parents=True, exist_ok=True)
    if scenario_count > 0:
        lines = ["Feature: synthetic\n"]
        for i in range(scenario_count):
            lines.append(f"  Scenario: scenario_{i}\n")
            lines.append("    Given a precondition\n")
            lines.append("    When an action occurs\n")
            lines.append("    Then an outcome holds\n")
        (distill / "synthetic.feature").write_text("".join(lines))
    return distill


def _make_lean_feature_delta(repo: Path, feature_id: str, scenario_count: int) -> Path:
    """Build a lean docs/feature/<id>/feature-delta.md with inline scenarios."""
    feat_dir = repo / "docs" / "feature" / feature_id
    feat_dir.mkdir(parents=True, exist_ok=True)
    body = ["# feature-delta\n", "```gherkin\n", "Feature: lean\n"]
    for i in range(scenario_count):
        body.append(f"  Scenario: lean_{i}\n")
    body.append("```\n")
    (feat_dir / "feature-delta.md").write_text("".join(body))
    return feat_dir


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Synthetic repo root pointing the CLI at tmp_path."""
    monkeypatch.setenv("NWAVE_REPO_ROOT", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# Cohort boundary tests (S→M at 10/11, M→L at 30/31, L→XL at 80/81)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "at_count,expected_cohort",
    [
        (10, "S"),
        (11, "M"),
        (30, "M"),
        (31, "L"),
        (80, "L"),
        (81, "XL"),
    ],
)
def test_cohort_boundaries_classify_correctly(
    repo: Path, at_count: int, expected_cohort: str
) -> None:
    """Boundary thresholds match plan v3 §4.1.bis table."""
    _make_feature_dir(repo, "feat-x", at_count)
    args = [
        "--feature-id",
        "feat-x",
        "--workflow-mode",
        "classic",  # classic always succeeds; isolates classification
    ]
    code, payload = _run_cli(args)
    assert code == 0
    assert payload["cohort"] == expected_cohort
    assert payload["at_count"] == at_count


# ---------------------------------------------------------------------------
# atdd_pure gate semantics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("at_count,cohort", [(5, "S"), (50, "L"), (100, "XL")])
def test_atdd_pure_rejects_non_M_without_override(
    repo: Path, at_count: int, cohort: str
) -> None:
    """atdd_pure + S/L/XL without --accept-pilot-scope-extension → exit 43."""
    _make_feature_dir(repo, "feat-y", at_count)
    code, payload = _run_cli(["--feature-id", "feat-y", "--workflow-mode", "atdd_pure"])
    assert code == 43
    assert payload["event"] == "CohortAssignmentRejected"
    assert payload["cohort"] == cohort


@pytest.mark.parametrize("at_count,cohort", [(5, "S"), (50, "L"), (100, "XL")])
def test_atdd_pure_accepts_non_M_with_override(
    repo: Path, at_count: int, cohort: str
) -> None:
    """atdd_pure + S/L/XL + override flag → exit 0 + scope_extension=True."""
    _make_feature_dir(repo, "feat-z", at_count)
    code, payload = _run_cli(
        [
            "--feature-id",
            "feat-z",
            "--workflow-mode",
            "atdd_pure",
            "--accept-pilot-scope-extension",
        ]
    )
    assert code == 0
    assert payload["cohort"] == cohort
    assert payload["scope_extension"] is True
    assert payload["event"] == "CohortAssigned"


def test_atdd_pure_M_cohort_proceeds(repo: Path) -> None:
    """atdd_pure + M cohort → exit 0, scope_extension=False."""
    _make_feature_dir(repo, "feat-m", 20)
    code, payload = _run_cli(["--feature-id", "feat-m", "--workflow-mode", "atdd_pure"])
    assert code == 0
    assert payload["cohort"] == "M"
    assert payload["scope_extension"] is False
    assert payload["event"] == "CohortAssigned"


# ---------------------------------------------------------------------------
# Classic mode (always advisory)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("at_count", [5, 20, 50, 100])
def test_classic_mode_always_exits_zero(repo: Path, at_count: int) -> None:
    """Classic mode never blocks regardless of cohort."""
    _make_feature_dir(repo, "feat-c", at_count)
    code, payload = _run_cli(["--feature-id", "feat-c", "--workflow-mode", "classic"])
    assert code == 0
    assert payload["event"] == "CohortAssigned"
    assert payload["workflow_mode"] == "classic"


# ---------------------------------------------------------------------------
# Feature artifact location: legacy distill/ AND lean feature-delta.md
# ---------------------------------------------------------------------------


def test_lean_feature_delta_md_supported(repo: Path) -> None:
    """Lean v3.14 single-file layout (feature-delta.md) is countable."""
    _make_lean_feature_delta(repo, "feat-lean", 15)
    code, payload = _run_cli(
        ["--feature-id", "feat-lean", "--workflow-mode", "atdd_pure"]
    )
    assert code == 0
    assert payload["at_count"] == 15
    assert payload["cohort"] == "M"


def test_missing_feature_dir_exits_1(repo: Path) -> None:
    """Neither distill/ nor feature-delta.md → exit 1."""
    code, payload = _run_cli(
        ["--feature-id", "does-not-exist", "--workflow-mode", "classic"]
    )
    assert code == 1
    assert "error" in payload


def test_malformed_feature_artifact_exits_2(repo: Path) -> None:
    """Feature dir exists but contains no scenarios and no countable content → exit 2."""
    feat_dir = repo / "docs" / "feature" / "feat-malformed" / "distill"
    feat_dir.mkdir(parents=True)
    # Put a non-feature, non-py file with no Scenarios
    (feat_dir / "notes.txt").write_text("nothing parseable here\n")
    code, payload = _run_cli(
        ["--feature-id", "feat-malformed", "--workflow-mode", "atdd_pure"]
    )
    assert code == 2
    assert "error" in payload


# ---------------------------------------------------------------------------
# PBT: monotonic cohort assignment over [0, 200]
# ---------------------------------------------------------------------------


def _cohort_for(n: int) -> str:
    if n <= 10:
        return "S"
    if n <= 30:
        return "M"
    if n <= 80:
        return "L"
    return "XL"


_RANK = {"S": 0, "M": 1, "L": 2, "XL": 3}


@given(at_count=st.integers(min_value=1, max_value=200))
@settings(max_examples=80, deadline=None)
def test_cohort_assignment_is_monotonic(
    tmp_path_factory: pytest.TempPathFactory,
    at_count: int,
) -> None:
    """Cohort rank is monotonically non-decreasing in at_count.

    Uses context-manager env patching (not monkeypatch fixture) to satisfy
    the Hypothesis function-scoped-fixture health check on its own terms,
    rather than suppressing the warning. at_count starts at 1 because
    at_count=0 is the malformed-artifact contract (exit 2).
    """
    import os as _os

    repo = tmp_path_factory.mktemp("pbt")
    _make_feature_dir(repo, "feat-pbt", at_count)
    prior = _os.environ.get("NWAVE_REPO_ROOT")
    _os.environ["NWAVE_REPO_ROOT"] = str(repo)
    try:
        code, payload = _run_cli(
            ["--feature-id", "feat-pbt", "--workflow-mode", "classic"]
        )
    finally:
        if prior is None:
            _os.environ.pop("NWAVE_REPO_ROOT", None)
        else:
            _os.environ["NWAVE_REPO_ROOT"] = prior
    assert code == 0
    assert payload["cohort"] == _cohort_for(at_count)
    assert _RANK[payload["cohort"]] >= _RANK[_cohort_for(max(1, at_count - 1))]


# ---------------------------------------------------------------------------
# Subprocess smoke (walking-skeleton: confirms CLI is invokable end-to-end)
# ---------------------------------------------------------------------------


def test_subprocess_invocation_smoke(repo: Path) -> None:
    """End-to-end: invoke as a real subprocess (DES sequencer path)."""
    _make_feature_dir(repo, "feat-smoke", 15)
    result = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "--feature-id",
            "feat-smoke",
            "--workflow-mode",
            "atdd_pure",
        ],
        env={"NWAVE_REPO_ROOT": str(repo), "PATH": ""},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip())
    assert payload["cohort"] == "M"
    assert payload["event"] == "CohortAssigned"
