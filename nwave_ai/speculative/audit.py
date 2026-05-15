"""Speculative dispatch audit log — CandidateTrace JSONL I/O.

Design:
    Pure data type (CandidateTrace, frozen dataclass) + two I/O functions.
    Storage layout: <root>/.nwave/speculative/<step_id>/traces.jsonl
    One JSONL file per step; each line is a serialised CandidateTrace.
    All candidates are written — including losers — per auditability mandate.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class CandidateTrace:
    """Immutable record of a single candidate's execution.

    Fields:
        candidate_id:     Unique identifier for this candidate within the step.
        step_id:          Identifies the TDD step these candidates compete on.
        timestamp_iso:    ISO-8601 timestamp of when the trace was recorded.
        files_modified:   Tuple of relative file paths modified by this candidate.
        tests_added:      Tuple of test file paths added by this candidate.
        tests_pass:       True if the candidate's full test suite passed.
        rationale:        Human-readable explanation of this candidate's approach.
    """

    candidate_id: str
    step_id: str
    timestamp_iso: str
    files_modified: tuple[str, ...]
    tests_added: tuple[str, ...]
    tests_pass: bool
    rationale: str


def _trace_file(step_id: str, root: Path) -> Path:
    """Return the JSONL file path for a given step, creating parent dirs."""
    target = root / ".nwave" / "speculative" / step_id / "traces.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _trace_to_dict(trace: CandidateTrace) -> dict[str, Any]:
    """Convert a CandidateTrace to a JSON-serialisable dict."""
    raw: dict[str, Any] = asdict(trace)
    # tuples serialise as lists in JSON — keep them as lists for round-trip safety
    return raw


def _dict_to_trace(data: dict[str, Any]) -> CandidateTrace:
    """Reconstruct a CandidateTrace from a deserialised dict."""
    return CandidateTrace(
        candidate_id=data["candidate_id"],
        step_id=data["step_id"],
        timestamp_iso=data["timestamp_iso"],
        files_modified=tuple(data["files_modified"]),
        tests_added=tuple(data["tests_added"]),
        tests_pass=data["tests_pass"],
        rationale=data["rationale"],
    )


def write_trace(trace: CandidateTrace, *, root: Path) -> None:
    """Append a CandidateTrace to the step's JSONL audit log.

    Appends (never overwrites) so all candidates — winner and losers — are
    permanently recorded. Human reviewers can validate the orchestrator's pick
    by inspecting the full log.

    Args:
        trace: The trace to persist.
        root:  Root directory under which .nwave/speculative/<step>/ is created.
    """
    trace_file = _trace_file(trace.step_id, root)
    with trace_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(_trace_to_dict(trace)) + "\n")


def read_traces(step_id: str, *, root: Path) -> list[CandidateTrace]:
    """Return all CandidateTraces written for *step_id*.

    Returns an empty list when no traces have been written for the step.

    Args:
        step_id: The step whose traces to retrieve.
        root:    Root directory (same value passed to write_trace).
    """
    trace_file = _trace_file(step_id, root)
    if not trace_file.exists():
        return []

    traces: list[CandidateTrace] = []
    with trace_file.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                traces.append(_dict_to_trace(json.loads(line)))
    return traces
