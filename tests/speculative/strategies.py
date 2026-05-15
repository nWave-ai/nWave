"""Shared Hypothesis strategies for speculative dispatch tests."""

from __future__ import annotations

from hypothesis import strategies as st


def candidate_trace_strategy(
    fixed_step_id: str | None = None,
) -> st.SearchStrategy:
    """Generate arbitrary CandidateTrace instances.

    Args:
        fixed_step_id: When provided, all generated traces use this step_id.
            Useful for multi-trace tests that need a shared step.
    """
    from nwave_ai.speculative.audit import CandidateTrace

    step_id_strategy = (
        st.just(fixed_step_id)
        if fixed_step_id is not None
        else st.text(
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="-_"
            ),
            min_size=1,
            max_size=30,
        )
    )

    return st.builds(
        CandidateTrace,
        candidate_id=st.text(
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="-_"
            ),
            min_size=1,
            max_size=40,
        ),
        step_id=step_id_strategy,
        timestamp_iso=st.just("2026-05-05T00:00:00Z"),
        files_modified=st.lists(
            st.text(min_size=1, max_size=50),
            min_size=0,
            max_size=5,
        ).map(tuple),
        tests_added=st.lists(
            st.text(min_size=1, max_size=50),
            min_size=0,
            max_size=3,
        ).map(tuple),
        tests_pass=st.booleans(),
        rationale=st.text(min_size=1, max_size=200),
    )


def candidate_metrics_strategy(
    tests_pass: bool | None = None,
) -> st.SearchStrategy:
    """Generate arbitrary CandidateMetrics instances.

    Args:
        tests_pass: When provided, fixes the tests_pass field to that value.
    """
    from nwave_ai.speculative.score import CandidateMetrics

    tests_pass_strategy = (
        st.just(tests_pass) if tests_pass is not None else st.booleans()
    )

    return st.builds(
        CandidateMetrics,
        tests_pass=tests_pass_strategy,
        complexity_delta=st.integers(min_value=0, max_value=50),
        lines_added=st.integers(min_value=0, max_value=500),
        test_runtime_seconds=st.floats(
            min_value=0.0, max_value=120.0, allow_nan=False, allow_infinity=False
        ),
    )
