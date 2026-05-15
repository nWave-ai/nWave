"""Tests for nwave_ai.speculative.audit — CandidateTrace JSONL I/O.

Properties tested:
- Round-trip: write_trace then read_traces returns equivalent trace.
- Append semantics: multiple traces for same step are all recovered.
- Isolation: traces from different steps do not appear in read_traces for another step.
- Invariant: read_traces always returns a list (empty when nothing written).
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.speculative.strategies import candidate_trace_strategy


# ---------------------------------------------------------------------------
# Round-trip property: write then read recovers the trace
# ---------------------------------------------------------------------------


@given(trace=candidate_trace_strategy())
@settings(max_examples=50)
def test_write_then_read_recovers_trace(tmp_path, trace):
    """Round-trip: a trace written to disk is fully recoverable via read_traces."""
    from nwave_ai.speculative.audit import read_traces, write_trace

    write_trace(trace, root=tmp_path)
    recovered = read_traces(trace.step_id, root=tmp_path)

    assert len(recovered) == 1
    recovered_trace = recovered[0]
    assert recovered_trace.candidate_id == trace.candidate_id
    assert recovered_trace.step_id == trace.step_id
    assert recovered_trace.timestamp_iso == trace.timestamp_iso
    assert recovered_trace.files_modified == trace.files_modified
    assert recovered_trace.tests_added == trace.tests_added
    assert recovered_trace.tests_pass == trace.tests_pass
    assert recovered_trace.rationale == trace.rationale


# ---------------------------------------------------------------------------
# Append property: N traces for same step all recovered
# ---------------------------------------------------------------------------


@given(
    traces=st.lists(
        candidate_trace_strategy(fixed_step_id="step-42"), min_size=2, max_size=5
    )
)
@settings(max_examples=30)
def test_multiple_traces_all_recovered(tmp_path, traces):
    """Append semantics: all traces for same step are accumulated."""
    from nwave_ai.speculative.audit import read_traces, write_trace

    for trace in traces:
        write_trace(trace, root=tmp_path)

    recovered = read_traces("step-42", root=tmp_path)
    assert len(recovered) == len(traces)


# ---------------------------------------------------------------------------
# Isolation property: traces from one step not visible under another step
# ---------------------------------------------------------------------------


@given(trace=candidate_trace_strategy(fixed_step_id="step-a"))
@settings(max_examples=30)
def test_trace_step_isolation(tmp_path, trace):
    """Traces for step-a are not returned when reading step-b."""
    from nwave_ai.speculative.audit import read_traces, write_trace

    write_trace(trace, root=tmp_path)
    other_step_traces = read_traces("step-b", root=tmp_path)
    assert other_step_traces == []


# ---------------------------------------------------------------------------
# Invariant: read_traces always returns a list
# ---------------------------------------------------------------------------


def test_read_traces_returns_empty_list_when_nothing_written(tmp_path):
    """read_traces returns [] when no traces have been written for a step."""
    from nwave_ai.speculative.audit import read_traces

    result = read_traces("no-such-step", root=tmp_path)
    assert result == []
