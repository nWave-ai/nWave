"""Speculative dispatch scoring — CandidateMetrics + composite score + pick_best.

Design:
    Pure functions only. No I/O, no side effects.
    score() returns a comparable 5-tuple so Python's built-in tuple ordering
    implements the full priority hierarchy: passing > lower-complexity > fewer-lines
    > faster-runtime. First element dominates (tests_pass as int: 1 > 0).

    pick_best() selects the highest-scoring candidate and produces a rationale
    that names EVERY candidate — winner AND losers — per the auditability mandate.
    Discarded candidates have audit value: a human reviewer can validate the pick.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nwave_ai.speculative.audit import CandidateTrace


@dataclass(frozen=True)
class CandidateMetrics:
    """Measured attributes of a single candidate implementation.

    Fields:
        tests_pass:            True if the candidate's full test suite passed.
        complexity_delta:      Net cyclomatic complexity added (lower is better).
        lines_added:           Net lines of production code added (lower is better).
        test_runtime_seconds:  Wall-clock seconds for the test run (lower is better).
    """

    tests_pass: bool
    complexity_delta: int
    lines_added: int
    test_runtime_seconds: float


def score(metrics: CandidateMetrics) -> tuple[int, int, int, int, float]:
    """Compute a comparable 5-tuple score for a candidate.

    Ordering (highest wins):
        1. tests_pass        — 1 if passing, 0 if failing  (dominates everything)
        2. -complexity_delta — negated so lower delta = higher score
        3. -lines_added      — negated so fewer lines = higher score
        4. 0                 — reserved for future tiebreaker
        5. -runtime          — negated so faster = higher score

    Returns:
        A 5-tuple suitable for direct comparison with > / < / max().
    """
    return (
        int(metrics.tests_pass),
        -metrics.complexity_delta,
        -metrics.lines_added,
        0,
        -metrics.test_runtime_seconds,
    )


def _build_rationale(
    winner: CandidateTrace,
    all_traces: list[CandidateTrace],
    metrics_map: dict[str, CandidateMetrics],
) -> str:
    """Produce a rationale string naming winner and ALL losers.

    Auditability mandate: every candidate is mentioned — discarded candidates
    carry audit value for human reviewers validating the orchestrator's pick.
    """
    winner_metrics = metrics_map[winner.candidate_id]
    lines: list[str] = [
        f"Selected: {winner.candidate_id} "
        f"(tests_pass={winner_metrics.tests_pass}, "
        f"complexity_delta={winner_metrics.complexity_delta}, "
        f"lines_added={winner_metrics.lines_added}).",
    ]

    losers = [t for t in all_traces if t.candidate_id != winner.candidate_id]
    if losers:
        lines.append("Discarded candidates:")
        for loser in losers:
            m = metrics_map[loser.candidate_id]
            status = "tests_passed" if m.tests_pass else "tests_failed"
            lines.append(
                f"  - {loser.candidate_id}: {status}, "
                f"complexity_delta={m.complexity_delta}, "
                f"lines_added={m.lines_added}."
            )

    return " ".join(lines)


def pick_best(
    traces: list[CandidateTrace],
    metrics_map: dict[str, CandidateMetrics],
) -> tuple[CandidateTrace, str]:
    """Select the highest-scoring candidate and produce an audit rationale.

    Scoring priority (see score()):
        1. tests_pass = True dominates all other criteria.
        2. Lower complexity_delta preferred among passing candidates.
        3. Fewer lines_added preferred at equal complexity.
        4. Faster test_runtime_seconds as final tiebreaker.

    The returned rationale names EVERY candidate (winner + losers) to satisfy
    the auditability mandate: human reviewers must be able to validate the pick
    without re-running the candidates.

    Args:
        traces:      All CandidateTrace records for the step.
        metrics_map: Maps candidate_id -> CandidateMetrics.

    Returns:
        (winner_trace, rationale_string)
    """
    winner = max(traces, key=lambda t: score(metrics_map[t.candidate_id]))
    rationale = _build_rationale(winner, traces, metrics_map)
    return winner, rationale
