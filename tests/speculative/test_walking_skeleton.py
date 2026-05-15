"""Walking skeleton: speculative dispatch with 3 candidate implementations.

Demonstrates the full audit + score pipeline end-to-end:
  1. Three candidates implement the same trivial function (prepended_with predicate).
  2. Each writes a CandidateTrace to .nwave/speculative/<step>/<candidate>/trace.jsonl.
  3. score() computes metrics for each candidate.
  4. pick_best() selects the winner and produces a rationale.
  5. Rationale references winner AND losers (auditability mandate).

The three candidate strategies:
  - minimal-change: inline boolean check, no helpers.
  - refactor-heavy: extracts a named helper + type alias.
  - pattern-extraction: generalises to a factory function.

All three produce correct implementations, but differ in complexity and lines.
pick_best must select minimal-change (lowest complexity_delta + lines_added).
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# The three candidate implementations (pure functions, no side effects)
# ---------------------------------------------------------------------------


def prepended_with_minimal(value: str, prefix: str) -> bool:
    """Candidate: minimal-change — single inline expression."""
    return value.startswith(prefix)


def prepended_with_refactor(value: str, prefix: str) -> bool:
    """Candidate: refactor-heavy — named helper + guard clause."""
    StringPredicate = type("StringPredicate", (), {})  # type alias marker

    def _check_prefix(v: str, p: str) -> bool:
        if not isinstance(v, str):
            return False
        if not isinstance(p, str):
            return False
        return v.startswith(p)

    del StringPredicate  # unused in this scope; marker only
    return _check_prefix(value, prefix)


def prepended_with_factory(value: str, prefix: str) -> bool:
    """Candidate: pattern-extraction — factory returning a predicate closure."""

    def make_prefix_predicate(p: str):
        def check(v: str) -> bool:
            return v.startswith(p)

        return check

    return make_prefix_predicate(prefix)(value)


# ---------------------------------------------------------------------------
# Walking skeleton test
# ---------------------------------------------------------------------------


def test_walking_skeleton_pick_best_with_audit(tmp_path: Path) -> None:
    """End-to-end: 3 candidates, write traces, score, pick_best.

    Verifies:
    - All 3 candidates produce correct results for sample inputs.
    - All 3 traces are written and recoverable.
    - pick_best selects minimal-change (lowest complexity + lines).
    - Rationale references ALL three candidate_ids (auditability mandate).
    """
    from nwave_ai.speculative.audit import CandidateTrace, read_traces, write_trace
    from nwave_ai.speculative.score import CandidateMetrics, pick_best

    step_id = "ws-prepended-with"

    # --- Verify all three candidates are behaviourally correct ---
    for fn in (prepended_with_minimal, prepended_with_refactor, prepended_with_factory):
        assert fn("hello world", "hello") is True
        assert fn("hello world", "world") is False
        assert fn("", "") is True
        assert fn("abc", "") is True

    # --- Build traces ---
    trace_minimal = CandidateTrace(
        candidate_id="minimal-change",
        step_id=step_id,
        timestamp_iso="2026-05-05T12:00:00Z",
        files_modified=("nwave_ai/speculative/predicates.py",),
        tests_added=("tests/speculative/test_predicates.py",),
        tests_pass=True,
        rationale=(
            "Single-expression implementation. No new abstractions. "
            "Directly delegates to str.startswith — zero complexity overhead."
        ),
    )
    trace_refactor = CandidateTrace(
        candidate_id="refactor-heavy",
        step_id=step_id,
        timestamp_iso="2026-05-05T12:01:00Z",
        files_modified=("nwave_ai/speculative/predicates.py",),
        tests_added=("tests/speculative/test_predicates.py",),
        tests_pass=True,
        rationale=(
            "Extracts _check_prefix helper for reuse. Adds type guards. "
            "More defensive but higher complexity delta."
        ),
    )
    trace_factory = CandidateTrace(
        candidate_id="pattern-extraction",
        step_id=step_id,
        timestamp_iso="2026-05-05T12:02:00Z",
        files_modified=("nwave_ai/speculative/predicates.py",),
        tests_added=("tests/speculative/test_predicates.py",),
        tests_pass=True,
        rationale=(
            "Factory pattern for composable predicates. "
            "Highest lines_added; justified only if predicate composition is needed."
        ),
    )

    # --- Write all traces ---
    for trace in (trace_minimal, trace_refactor, trace_factory):
        write_trace(trace, root=tmp_path)

    # --- Verify all traces recoverable ---
    recovered = read_traces(step_id, root=tmp_path)
    assert len(recovered) == 3
    recovered_ids = {t.candidate_id for t in recovered}
    assert recovered_ids == {"minimal-change", "refactor-heavy", "pattern-extraction"}

    # --- Build metrics (measured from the implementations above) ---
    metrics_map = {
        "minimal-change": CandidateMetrics(
            tests_pass=True,
            complexity_delta=1,
            lines_added=2,
            test_runtime_seconds=0.05,
        ),
        "refactor-heavy": CandidateMetrics(
            tests_pass=True,
            complexity_delta=5,
            lines_added=12,
            test_runtime_seconds=0.07,
        ),
        "pattern-extraction": CandidateMetrics(
            tests_pass=True,
            complexity_delta=4,
            lines_added=10,
            test_runtime_seconds=0.06,
        ),
    }

    # --- Pick best ---
    winner, rationale = pick_best(list(recovered), metrics_map)

    # Winner must be minimal-change (lowest complexity_delta AND lines_added)
    assert winner.candidate_id == "minimal-change"

    # Auditability mandate: rationale names winner AND all losers
    assert "minimal-change" in rationale
    assert "refactor-heavy" in rationale
    assert "pattern-extraction" in rationale

    # Rationale is a non-empty string with meaningful content
    assert len(rationale) > 20

    # Print the sample audit log and rationale for the OUTPUT REPORT
    print("\n--- SAMPLE AUDIT LOG ---")
    for t in sorted(recovered, key=lambda x: x.candidate_id):
        print(
            f"  [{t.candidate_id}] tests_pass={t.tests_pass} "
            f"files={t.files_modified} rationale='{t.rationale[:60]}...'"
        )
    print(f"\n--- PICK_BEST RATIONALE ---\n  {rationale}\n")
