"""Collect test suite wall-clock per pytest run, append to telemetry log.

Observation-only -- does NOT block, does NOT enforce thresholds.
Trend interpretation is human-driven.

Appends JSONL entries to .nwave/observability/test-runtime-log.jsonl.
Called from hook wiring after pytest completes; always exits without raising.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path  # noqa: TC003
from typing import NamedTuple


# ── Types ──────────────────────────────────────────────────────────────────


class ParsedPytestOutput(NamedTuple):
    """Parsed summary line from pytest stdout."""

    tests_total: int
    wall_clock_seconds: float


class TelemetryEntry(NamedTuple):
    """One observation entry written to the JSONL log."""

    timestamp: str
    tests_total: int
    wall_clock_seconds: float
    tests_per_sec: float
    scope: str
    git_sha: str


# ── Pure parsing functions ─────────────────────────────────────────────────

_SUMMARY_PATTERN = re.compile(
    r"(?:(\d+) passed)?.*in ([\d.]+)s",
    re.IGNORECASE,
)

_PASSED_PATTERN = re.compile(r"(\d+) passed")
_ELAPSED_PATTERN = re.compile(r"in ([\d.]+)s")


def parse_pytest_output(output: str) -> ParsedPytestOutput | None:
    """Extract test count and wall-clock from pytest stdout/stderr.

    Looks for the summary line produced by pytest:
      "N passed in X.XXs"

    Returns None when the summary cannot be found (e.g. no tests collected,
    import error, or unexpected format).
    """
    # Search the last 20 lines — the summary is always near the end
    tail = "\n".join(output.splitlines()[-20:])

    passed_match = _PASSED_PATTERN.search(tail)
    elapsed_match = _ELAPSED_PATTERN.search(tail)

    if not passed_match or not elapsed_match:
        return None

    tests_total = int(passed_match.group(1))
    wall_clock_seconds = float(elapsed_match.group(1))

    if wall_clock_seconds <= 0:
        return None

    return ParsedPytestOutput(
        tests_total=tests_total,
        wall_clock_seconds=wall_clock_seconds,
    )


def build_telemetry_entry(
    parsed: ParsedPytestOutput,
    scope: str,
    git_sha: str,
    now: datetime,
) -> TelemetryEntry:
    """Construct a TelemetryEntry from parsed output and context.

    Pure function — all inputs explicit, no side effects.
    """
    tests_per_sec = (
        parsed.tests_total / parsed.wall_clock_seconds
        if parsed.wall_clock_seconds > 0
        else 0.0
    )
    return TelemetryEntry(
        timestamp=now.isoformat(),
        tests_total=parsed.tests_total,
        wall_clock_seconds=parsed.wall_clock_seconds,
        tests_per_sec=round(tests_per_sec, 2),
        scope=scope,
        git_sha=git_sha,
    )


def entry_to_jsonl_line(entry: TelemetryEntry) -> str:
    """Serialize a TelemetryEntry to a single JSONL line (no trailing newline)."""
    return json.dumps(entry._asdict())


# ── Side-effectful helpers (kept thin, at the edge) ───────────────────────


def resolve_git_sha(project_root: Path) -> str:
    """Return the current HEAD sha (short), or 'unknown' on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def append_to_log(log_path: Path, line: str) -> None:
    """Append a JSONL line to the telemetry log, creating parent dirs as needed."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ── Public entry point ─────────────────────────────────────────────────────


def collect(
    pytest_output: str,
    scope: str,
    project_root: Path,
    log_path: Path | None = None,
) -> TelemetryEntry | None:
    """Parse pytest output and append one telemetry entry to the log.

    Observation-only: never raises, never returns a non-zero exit code.

    Args:
        pytest_output: Combined stdout+stderr from a pytest run.
        scope:         Human label for the run ('unit', 'integration', 'all', …).
        project_root:  Repo root used to resolve the git SHA.
        log_path:      Override the log file path (defaults to
                       <project_root>/.nwave/observability/test-runtime-log.jsonl).

    Returns:
        The TelemetryEntry that was appended, or None when parsing failed.
    """
    resolved_log = log_path or (
        project_root / ".nwave" / "observability" / "test-runtime-log.jsonl"
    )

    parsed = parse_pytest_output(pytest_output)
    if parsed is None:
        return None

    git_sha = resolve_git_sha(project_root)
    now = datetime.now(timezone.utc)
    entry = build_telemetry_entry(parsed, scope, git_sha, now)
    line = entry_to_jsonl_line(entry)
    append_to_log(resolved_log, line)
    return entry
