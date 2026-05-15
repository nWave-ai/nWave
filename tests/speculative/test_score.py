"""Tests for nwave_ai.speculative.score — CandidateMetrics + score + pick_best.

Properties tested:
- Failing tests always score below passing tests (dominance invariant).
- score output is a sortable tuple (invariant: length == 5).
- pick_best rationale always references winner AND at least one loser (auditability mandate).
- pick_best selects the candidate whose tests pass when others fail.
- pick_best among all-passing candidates prefers lower complexity_delta.
- pick_best among equal complexity prefers fewer lines_added.
- pick_best rationale is non-empty string.
"""

from __future__ import annotations

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from tests.speculative.strategies import (
    candidate_metrics_strategy,
    candidate_trace_strategy,
)


# ---------------------------------------------------------------------------
# Invariant: score tuple has exactly 5 elements
# ---------------------------------------------------------------------------


@given(metrics=candidate_metrics_strategy())
@settings(max_examples=100)
def test_score_tuple_length_is_five(metrics):
    """score() always returns a 5-tuple."""
    from nwave_ai.speculative.score import score

    result = score(metrics)
    assert len(result) == 5


# ---------------------------------------------------------------------------
# Dominance invariant: passing > failing for any metrics values
# ---------------------------------------------------------------------------


@given(
    passing_metrics=candidate_metrics_strategy(tests_pass=True),
    failing_metrics=candidate_metrics_strategy(tests_pass=False),
)
@settings(max_examples=100)
def test_passing_always_dominates_failing(passing_metrics, failing_metrics):
    """A candidate whose tests pass always outscores one whose tests fail."""
    from nwave_ai.speculative.score import score

    passing_score = score(passing_metrics)
    failing_score = score(failing_metrics)
    assert passing_score > failing_score


# ---------------------------------------------------------------------------
# Ordering invariant: lower complexity_delta is better (among passing)
# ---------------------------------------------------------------------------


@given(
    base_complexity=st.integers(min_value=0, max_value=20),
    extra_complexity=st.integers(min_value=1, max_value=10),
    lines=st.integers(min_value=0, max_value=200),
    runtime=st.floats(
        min_value=0.0, max_value=60.0, allow_nan=False, allow_infinity=False
    ),
)
@settings(max_examples=100)
def test_lower_complexity_scores_higher_among_passing(
    base_complexity, extra_complexity, lines, runtime
):
    """Among passing candidates, lower complexity_delta yields higher score."""
    from nwave_ai.speculative.score import CandidateMetrics, score

    simpler = CandidateMetrics(
        tests_pass=True,
        complexity_delta=base_complexity,
        lines_added=lines,
        test_runtime_seconds=runtime,
    )
    more_complex = CandidateMetrics(
        tests_pass=True,
        complexity_delta=base_complexity + extra_complexity,
        lines_added=lines,
        test_runtime_seconds=runtime,
    )
    assert score(simpler) > score(more_complex)


# ---------------------------------------------------------------------------
# Ordering invariant: fewer lines_added is better (equal complexity, passing)
# ---------------------------------------------------------------------------


@given(
    complexity=st.integers(min_value=0, max_value=20),
    base_lines=st.integers(min_value=0, max_value=200),
    extra_lines=st.integers(min_value=1, max_value=50),
    runtime=st.floats(
        min_value=0.0, max_value=60.0, allow_nan=False, allow_infinity=False
    ),
)
@settings(max_examples=100)
def test_fewer_lines_scores_higher_at_equal_complexity(
    complexity, base_lines, extra_lines, runtime
):
    """Among passing candidates with equal complexity, fewer lines is better."""
    from nwave_ai.speculative.score import CandidateMetrics, score

    leaner = CandidateMetrics(
        tests_pass=True,
        complexity_delta=complexity,
        lines_added=base_lines,
        test_runtime_seconds=runtime,
    )
    bulkier = CandidateMetrics(
        tests_pass=True,
        complexity_delta=complexity,
        lines_added=base_lines + extra_lines,
        test_runtime_seconds=runtime,
    )
    assert score(leaner) > score(bulkier)


# ---------------------------------------------------------------------------
# pick_best: winner has tests_pass=True when others fail
# ---------------------------------------------------------------------------


@given(
    winner_trace=candidate_trace_strategy(fixed_step_id="step-x"),
    loser_traces=st.lists(
        candidate_trace_strategy(fixed_step_id="step-x"), min_size=1, max_size=3
    ),
)
@settings(max_examples=50)
def test_pick_best_selects_passing_over_failing(tmp_path, winner_trace, loser_traces):
    """pick_best selects the trace whose tests pass when others fail."""
    from nwave_ai.speculative.score import CandidateMetrics, pick_best

    # Force winner to pass, losers to fail
    metrics_map = {
        winner_trace.candidate_id: CandidateMetrics(
            tests_pass=True,
            complexity_delta=5,
            lines_added=10,
            test_runtime_seconds=1.0,
        )
    }
    for loser in loser_traces:
        assume(loser.candidate_id != winner_trace.candidate_id)
        metrics_map[loser.candidate_id] = CandidateMetrics(
            tests_pass=False,
            complexity_delta=0,
            lines_added=0,
            test_runtime_seconds=0.1,
        )

    all_traces = [winner_trace] + loser_traces
    chosen, rationale = pick_best(all_traces, metrics_map)

    assert chosen.candidate_id == winner_trace.candidate_id
    assert isinstance(rationale, str)
    assert len(rationale) > 0


# ---------------------------------------------------------------------------
# Auditability mandate: rationale references winner AND loser(s)
# ---------------------------------------------------------------------------


def test_pick_best_rationale_references_winner_and_losers():
    """pick_best rationale must name winner and all losers — auditability mandate."""
    from nwave_ai.speculative.audit import CandidateTrace
    from nwave_ai.speculative.score import CandidateMetrics, pick_best

    winner = CandidateTrace(
        candidate_id="minimal-change",
        step_id="step-1",
        timestamp_iso="2026-05-05T10:00:00Z",
        files_modified=("src/foo.py",),
        tests_added=("tests/test_foo.py",),
        tests_pass=True,
        rationale="Minimal diff, preserves existing structure.",
    )
    loser_a = CandidateTrace(
        candidate_id="refactor-heavy",
        step_id="step-1",
        timestamp_iso="2026-05-05T10:01:00Z",
        files_modified=("src/foo.py", "src/bar.py"),
        tests_added=("tests/test_foo.py",),
        tests_pass=True,
        rationale="Full refactor for cleaner abstractions.",
    )
    loser_b = CandidateTrace(
        candidate_id="pattern-extraction",
        step_id="step-1",
        timestamp_iso="2026-05-05T10:02:00Z",
        files_modified=("src/foo.py", "src/patterns.py"),
        tests_added=("tests/test_foo.py", "tests/test_patterns.py"),
        tests_pass=False,
        rationale="Extract reusable pattern — tests failed.",
    )

    metrics_map = {
        "minimal-change": CandidateMetrics(
            tests_pass=True, complexity_delta=1, lines_added=5, test_runtime_seconds=0.5
        ),
        "refactor-heavy": CandidateMetrics(
            tests_pass=True,
            complexity_delta=8,
            lines_added=40,
            test_runtime_seconds=1.2,
        ),
        "pattern-extraction": CandidateMetrics(
            tests_pass=False,
            complexity_delta=3,
            lines_added=20,
            test_runtime_seconds=2.1,
        ),
    }

    chosen, rationale = pick_best([winner, loser_a, loser_b], metrics_map)

    assert chosen.candidate_id == "minimal-change"
    # Auditability: rationale must name winner and losers
    assert "minimal-change" in rationale
    assert "refactor-heavy" in rationale
    assert "pattern-extraction" in rationale


# ---------------------------------------------------------------------------
# Rationale mentions tests_pass=False for failing candidates
# ---------------------------------------------------------------------------


def test_pick_best_rationale_mentions_test_failure():
    """Rationale must distinguish failing candidates from passing ones."""
    from nwave_ai.speculative.audit import CandidateTrace
    from nwave_ai.speculative.score import CandidateMetrics, pick_best

    winner = CandidateTrace(
        candidate_id="minimal-change",
        step_id="step-2",
        timestamp_iso="2026-05-05T11:00:00Z",
        files_modified=("src/a.py",),
        tests_added=(),
        tests_pass=True,
        rationale="Works.",
    )
    loser = CandidateTrace(
        candidate_id="broken-attempt",
        step_id="step-2",
        timestamp_iso="2026-05-05T11:01:00Z",
        files_modified=("src/a.py",),
        tests_added=(),
        tests_pass=False,
        rationale="Did not compile.",
    )

    metrics_map = {
        "minimal-change": CandidateMetrics(
            tests_pass=True, complexity_delta=0, lines_added=3, test_runtime_seconds=0.2
        ),
        "broken-attempt": CandidateMetrics(
            tests_pass=False,
            complexity_delta=0,
            lines_added=3,
            test_runtime_seconds=0.0,
        ),
    }

    _, rationale = pick_best([winner, loser], metrics_map)
    # Rationale must flag that broken-attempt failed tests
    assert "tests_failed" in rationale or "failed" in rationale.lower()
