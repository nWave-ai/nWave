"""Unit tests for test_runtime_collector.py.

Behaviors under test:
1. parse_pytest_output: extracts count + wall-clock from valid summary lines
2. parse_pytest_output: returns None for malformed / empty / no-test output
3. build_telemetry_entry: computes tests_per_sec correctly
4. entry_to_jsonl_line: round-trips through JSON with correct keys
5. collect: writes JSONL entry to log on parseable output
6. collect: returns None and does NOT create log on unparseable output

PBT rationale:
- Behaviors 1-4 are pure-function invariants suited for property tests.
- Behaviors 5-6 involve I/O (tmp_path) → example-based with
  # bypass: I/O side effects; single-example is cleaner and sufficient.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from scripts.observability.test_runtime_collector import (
    ParsedPytestOutput,
    build_telemetry_entry,
    collect,
    entry_to_jsonl_line,
    parse_pytest_output,
)


pytestmark = pytest.mark.unit


# ── Strategies ─────────────────────────────────────────────────────────────

_positive_int = st.integers(min_value=1, max_value=9999)
_positive_float = st.floats(min_value=0.01, max_value=9999.0, allow_nan=False)
_scope_text = st.text(
    min_size=1,
    max_size=20,
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"
    ),
)
_sha_text = st.text(min_size=7, max_size=40, alphabet="0123456789abcdef")


def _make_pytest_summary(passed: int, seconds: float) -> str:
    """Build a minimal pytest summary line matching the real format."""
    return f"===== {passed} passed in {seconds:.3f}s ====="


# ── Behavior 1: parse_pytest_output — valid summaries ─────────────────────


@given(passed=_positive_int, seconds=_positive_float)
@settings(max_examples=100)
def test_parse_extracts_count_and_wall_clock_from_valid_summary(
    passed: int, seconds: float
) -> None:
    """parse_pytest_output returns values matching the summary line.

    Tolerance is 0.001 because _make_pytest_summary formats seconds to 3
    decimal places (:.3f), so the parsed value may differ from the original
    float by up to half a ULP at that precision.
    """
    output = _make_pytest_summary(passed, seconds)
    result = parse_pytest_output(output)
    assert result is not None
    assert result.tests_total == passed
    assert abs(result.wall_clock_seconds - seconds) < 0.001


@given(passed=_positive_int, seconds=_positive_float)
@settings(max_examples=50)
def test_parse_works_when_summary_is_not_on_last_line(
    passed: int, seconds: float
) -> None:
    """parse_pytest_output finds the summary even with trailing noise lines."""
    summary = _make_pytest_summary(passed, seconds)
    output = summary + "\n\nsome trailing output\nanother line"
    result = parse_pytest_output(output)
    assert result is not None
    assert result.tests_total == passed


# ── Behavior 2: parse_pytest_output — invalid / empty output ───────────────


@pytest.mark.parametrize(
    "bad_output",
    [
        "",
        "no summary here",
        "ERROR collecting tests",
        "no tests ran",
        "collected 0 items",
        "====== 0 failed in 1.23s ======",  # no 'passed' token
    ],
)
def test_parse_returns_none_for_unparseable_output(bad_output: str) -> None:
    # bypass: parametrize over fixed enum of malformed inputs; PBT adds no value here
    assert parse_pytest_output(bad_output) is None


# ── Behavior 3: build_telemetry_entry — tests_per_sec invariant ───────────


@given(passed=_positive_int, seconds=_positive_float, scope=_scope_text, sha=_sha_text)
@settings(max_examples=100)
def test_build_entry_tests_per_sec_equals_total_divided_by_wall_clock(
    passed: int, seconds: float, scope: str, sha: str
) -> None:
    """tests_per_sec must always equal tests_total / wall_clock_seconds."""
    parsed = ParsedPytestOutput(tests_total=passed, wall_clock_seconds=seconds)
    now = datetime.now(timezone.utc)
    entry = build_telemetry_entry(parsed, scope=scope, git_sha=sha, now=now)
    expected_tps = round(passed / seconds, 2)
    assert abs(entry.tests_per_sec - expected_tps) < 0.01


@given(passed=_positive_int, seconds=_positive_float)
@settings(max_examples=50)
def test_build_entry_preserves_scope_and_sha(passed: int, seconds: float) -> None:
    """build_telemetry_entry passes scope and sha through unchanged."""
    parsed = ParsedPytestOutput(tests_total=passed, wall_clock_seconds=seconds)
    now = datetime.now(timezone.utc)
    entry = build_telemetry_entry(
        parsed, scope="integration", git_sha="abc1234", now=now
    )
    assert entry.scope == "integration"
    assert entry.git_sha == "abc1234"


# ── Behavior 4: entry_to_jsonl_line — JSON round-trip ─────────────────────


@given(passed=_positive_int, seconds=_positive_float, scope=_scope_text, sha=_sha_text)
@settings(max_examples=100)
def test_entry_to_jsonl_line_round_trips_all_fields(
    passed: int, seconds: float, scope: str, sha: str
) -> None:
    """Serialised line decodes back to a dict with all TelemetryEntry fields."""
    parsed = ParsedPytestOutput(tests_total=passed, wall_clock_seconds=seconds)
    now = datetime.now(timezone.utc)
    entry = build_telemetry_entry(parsed, scope=scope, git_sha=sha, now=now)
    line = entry_to_jsonl_line(entry)

    decoded = json.loads(line)
    assert decoded["tests_total"] == entry.tests_total
    assert decoded["wall_clock_seconds"] == entry.wall_clock_seconds
    assert decoded["tests_per_sec"] == entry.tests_per_sec
    assert decoded["scope"] == entry.scope
    assert decoded["git_sha"] == entry.git_sha
    assert "timestamp" in decoded


@given(passed=_positive_int, seconds=_positive_float)
@settings(max_examples=50)
def test_entry_to_jsonl_line_produces_single_line(passed: int, seconds: float) -> None:
    """Serialised output contains no newlines (JSONL invariant)."""
    parsed = ParsedPytestOutput(tests_total=passed, wall_clock_seconds=seconds)
    now = datetime.now(timezone.utc)
    entry = build_telemetry_entry(parsed, scope="unit", git_sha="abc1234", now=now)
    line = entry_to_jsonl_line(entry)
    assert "\n" not in line


# ── Behavior 5: collect — writes log entry on parseable output ─────────────


def test_collect_appends_entry_to_log_when_output_parseable(tmp_path: Path) -> None:
    # bypass: I/O side effects make PBT impractical; single-example verifies wiring
    log_path = tmp_path / "obs" / "test-runtime-log.jsonl"
    output = "===== 42 passed in 3.210s ====="

    result = collect(output, scope="unit", project_root=tmp_path, log_path=log_path)

    assert result is not None
    assert log_path.exists()
    lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1
    decoded = json.loads(lines[0])
    assert decoded["tests_total"] == 42
    assert abs(decoded["wall_clock_seconds"] - 3.210) < 1e-6
    assert decoded["scope"] == "unit"


def test_collect_appends_multiple_entries_sequentially(tmp_path: Path) -> None:
    # bypass: verifies append-not-overwrite semantics; I/O boundary
    log_path = tmp_path / "test-runtime-log.jsonl"
    output_a = "===== 10 passed in 1.000s ====="
    output_b = "===== 20 passed in 2.000s ====="

    collect(output_a, scope="unit", project_root=tmp_path, log_path=log_path)
    collect(output_b, scope="integration", project_root=tmp_path, log_path=log_path)

    lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 2
    assert json.loads(lines[0])["tests_total"] == 10
    assert json.loads(lines[1])["tests_total"] == 20


# ── Behavior 6: collect — no log created on unparseable output ─────────────


def test_collect_returns_none_and_does_not_create_log_on_unparseable_output(
    tmp_path: Path,
) -> None:
    # bypass: verifies non-creation guard; I/O boundary
    log_path = tmp_path / "test-runtime-log.jsonl"

    result = collect(
        "no summary here", scope="unit", project_root=tmp_path, log_path=log_path
    )

    assert result is None
    assert not log_path.exists()
