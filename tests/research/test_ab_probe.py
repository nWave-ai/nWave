"""A/B token-cost probe — tests for the research harness.

Test layers per task spec:
- Acceptance (1): port-to-port via `run_probe` with fake dispatcher + fake writer.
- Property (1): pure-function invariant for `delta_pct`.
- Parametrized (3): default `quality_check` verdict matrix.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


if TYPE_CHECKING:
    from pathlib import Path

from scripts.research.ab_token_probe import (
    ConfigRun,
    ProbeResult,
    TokenUsage,
    default_quality_check,
    delta_pct,
    run_probe,
)


# ---------------------------------------------------------------------------
# Fakes — in-memory driven-port doubles
# ---------------------------------------------------------------------------


@dataclass
class FakeDispatcher:
    """In-memory CLIDispatcher double — returns scripted ConfigRuns."""

    scripted: dict[str, ConfigRun]
    calls: list[tuple[str, str]] = field(default_factory=list)

    def dispatch(self, config_label: str, task_spec: str) -> ConfigRun:
        self.calls.append((config_label, task_spec))
        return self.scripted[config_label]


@dataclass
class FakeWriter:
    """In-memory ReportWriter double — captures write calls."""

    written: list[tuple[ProbeResult, Path]] = field(default_factory=list)

    def write(self, result: ProbeResult, dest: Path) -> None:
        # Also write to real path so acceptance test can inspect on disk.
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(
                {
                    "task_spec": result.task_spec,
                    "run_a": {
                        "config_label": result.run_a.config_label,
                        "input": result.run_a.usage.input_tokens,
                        "output": result.run_a.usage.output_tokens,
                        "cache_creation": result.run_a.usage.cache_creation_tokens,
                        "cache_read": result.run_a.usage.cache_read_tokens,
                        "output_text": result.run_a.output_text,
                        "duration_seconds": result.run_a.duration_seconds,
                    },
                    "run_b": {
                        "config_label": result.run_b.config_label,
                        "input": result.run_b.usage.input_tokens,
                        "output": result.run_b.usage.output_tokens,
                        "cache_creation": result.run_b.usage.cache_creation_tokens,
                        "cache_read": result.run_b.usage.cache_read_tokens,
                        "output_text": result.run_b.output_text,
                        "duration_seconds": result.run_b.duration_seconds,
                    },
                    "delta_input_pct": result.delta_input_pct,
                    "delta_output_pct": result.delta_output_pct,
                    "delta_total_pct": result.delta_total_pct,
                    "quality_verdict": result.quality_verdict,
                    "verdict_reason": result.verdict_reason,
                }
            )
        )
        self.written.append((result, dest))


def _usage(
    input_t: int, output_t: int, cache_c: int = 0, cache_r: int = 0
) -> TokenUsage:
    return TokenUsage(
        input_tokens=input_t,
        output_tokens=output_t,
        cache_creation_tokens=cache_c,
        cache_read_tokens=cache_r,
    )


def _run(
    label: str, task: str, total: int, text: str = "ok", dur: float = 1.0
) -> ConfigRun:
    """Helper: build a ConfigRun whose usage sums to `total` tokens (all in input)."""
    return ConfigRun(
        config_label=label,
        task_spec=task,
        usage=_usage(input_t=total, output_t=0),
        output_text=text,
        duration_seconds=dur,
    )


# ---------------------------------------------------------------------------
# Acceptance test — port-to-port via driving port `run_probe`
# ---------------------------------------------------------------------------


def test_run_probe_writes_report_with_deltas(tmp_path: Path) -> None:
    """run_probe orchestrates A + B dispatch, computes deltas, writes report.

    Universe at the driving-port boundary: report on disk, both runs captured,
    delta_total_pct ≈ -15% when B saves 150 tokens of 1000.
    """
    task = "convert nw-agent X to Codex"
    run_a = _run("A", task, total=1000, text="full output A")
    run_b = _run("B", task, total=850, text="full output B")

    def quality(a: ConfigRun, b: ConfigRun) -> tuple[str, str]:
        return ("PASS", "ok")

    dispatcher = FakeDispatcher(scripted={"A": run_a, "B": run_b})
    writer = FakeWriter()

    result = run_probe(
        task_spec=task,
        dispatcher=dispatcher,
        writer=writer,
        quality_check=quality,
        dest_dir=tmp_path,
    )

    # Driving-port return value
    assert result.run_a is run_a
    assert result.run_b is run_b
    assert result.quality_verdict == "PASS"
    assert result.delta_total_pct == pytest.approx(-15.0, abs=0.01)

    # Driven-port boundary — dispatcher saw both configs against the same spec
    assert dispatcher.calls == [("A", task), ("B", task)]

    # Driven-port boundary — writer was invoked once with a path inside dest_dir
    assert len(writer.written) == 1
    written_result, written_path = writer.written[0]
    assert written_result is result
    assert written_path.parent == tmp_path
    assert written_path.suffix == ".json"

    # Round-trip: report on disk has both runs + deltas
    payload = json.loads(written_path.read_text())
    assert payload["task_spec"] == task
    assert payload["run_a"]["input"] == 1000
    assert payload["run_b"]["input"] == 850
    assert payload["quality_verdict"] == "PASS"
    assert payload["delta_total_pct"] == pytest.approx(-15.0, abs=0.01)


# ---------------------------------------------------------------------------
# Property-based test — delta_pct invariant
# ---------------------------------------------------------------------------


@given(
    a_tokens=st.integers(min_value=1, max_value=10**6),
    b_tokens=st.integers(min_value=0, max_value=10**6),
)
@settings(max_examples=200, deadline=None)
def test_delta_pct_invariant_b_minus_a_over_a(a_tokens: int, b_tokens: int) -> None:
    """`delta_pct(a, b) == (b - a) / a * 100` for any positive a and any non-negative b."""
    expected = (b_tokens - a_tokens) / a_tokens * 100
    assert delta_pct(a_tokens, b_tokens) == pytest.approx(expected, rel=1e-9, abs=1e-9)


# ---------------------------------------------------------------------------
# Parametrized quality verdict (3 cases)
# ---------------------------------------------------------------------------


_TASK = "verify quality_check verdict matrix"
_BASE_USAGE = _usage(1000, 200)
_MARKERS = ["MARKER_ALPHA", "MARKER_BETA"]
_A_TEXT = "intro " + " ".join(_MARKERS) + " conclusion " + "x" * 80  # ~120 chars


def _config_run(label: str, output_text: str) -> ConfigRun:
    return ConfigRun(
        config_label=label,
        task_spec=_TASK,
        usage=_BASE_USAGE,
        output_text=output_text,
        duration_seconds=1.0,
    )


@pytest.mark.parametrize(
    "b_output, expected_verdict, case_id",
    [
        # Case 1: B preserves length above 85% AND contains both markers — PASS
        (
            "intro "
            + " ".join(_MARKERS)
            + " conclusion "
            + "y" * 75,  # ~115 chars > 85% of 120
            "PASS",
            "b_output_length_above_85pct_and_markers_present",
        ),
        # Case 2: B output collapses to <85% of A's length — FAIL
        (
            "tiny",  # 4 chars — well below 85% of 120
            "FAIL",
            "b_output_length_below_85pct_of_a",
        ),
        # Case 3: B preserves length but loses key markers — FAIL
        (
            "intro placeholder placeholder conclusion "
            + "z" * 80,  # length OK, markers gone
            "FAIL",
            "b_output_missing_key_markers",
        ),
    ],
    ids=lambda v: v if isinstance(v, str) and v.startswith("b_") else None,
)
def test_default_quality_check_verdict_matrix(
    b_output: str, expected_verdict: str, case_id: str
) -> None:
    run_a = _config_run("A", _A_TEXT)
    run_b = _config_run("B", b_output)

    verdict, reason = default_quality_check(run_a, run_b, key_markers=_MARKERS)

    assert verdict == expected_verdict, (
        f"case={case_id}: expected {expected_verdict}, got {verdict} ({reason})"
    )
    assert reason  # always non-empty diagnostic
