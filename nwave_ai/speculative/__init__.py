"""Speculative dispatch sub-package.

Public API:
    audit  — CandidateTrace JSONL I/O (write_trace, read_traces)
    score  — CandidateMetrics, composite scoring, pick_best
"""

from nwave_ai.speculative.audit import CandidateTrace, read_traces, write_trace
from nwave_ai.speculative.score import CandidateMetrics, pick_best, score


__all__ = [
    "CandidateMetrics",
    "CandidateTrace",
    "pick_best",
    "read_traces",
    "score",
    "write_trace",
]
