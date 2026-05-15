"""CLI trend report for test suite runtime telemetry.

Read-only: reads .nwave/observability/test-runtime-log.jsonl, renders
a markdown table to stdout. No writes, no side effects beyond stdout.

Usage:
    python -m scripts.observability.test_runtime_report
    python scripts/observability/test_runtime_report.py [--log PATH] [--last N]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# ── Types ──────────────────────────────────────────────────────────────────

Entry = dict[str, Any]


# ── Pure functions ─────────────────────────────────────────────────────────


def load_entries(log_path: Path) -> list[Entry]:
    """Read all JSONL entries from the log file.

    Returns an empty list when the file does not exist or is empty.
    Skips lines that cannot be decoded (corrupt writes).
    """
    if not log_path.exists():
        return []
    entries: list[Entry] = []
    for raw_line in log_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def mean_wall_clock(entries: list[Entry]) -> float | None:
    """Return the mean wall_clock_seconds for a slice of entries, or None."""
    if not entries:
        return None
    values: list[float] = [
        float(e["wall_clock_seconds"]) for e in entries if "wall_clock_seconds" in e
    ]
    if not values:
        return None
    return sum(values) / len(values)


def format_delta(new_mean: float | None, old_mean: float | None) -> str:
    """Return a human-readable delta string between two means."""
    if new_mean is None or old_mean is None or old_mean == 0:
        return "n/a"
    delta_pct = ((new_mean - old_mean) / old_mean) * 100
    sign = "+" if delta_pct >= 0 else ""
    return f"{sign}{delta_pct:.1f}%"


def render_entries_table(entries: list[Entry]) -> list[str]:
    """Render the last-N entries as a markdown table.

    Returns a list of lines (no trailing newlines).
    """
    if not entries:
        return ["_No entries found._"]

    header = "| # | Timestamp | Scope | Tests | Wall-clock (s) | tests/s | SHA |"
    separator = "|---|-----------|-------|-------|----------------|---------|-----|"
    rows = [header, separator]
    for idx, entry in enumerate(entries, start=1):
        ts = entry.get("timestamp", "?")[:19].replace("T", " ")
        scope = entry.get("scope", "?")
        total = entry.get("tests_total", "?")
        wall = entry.get("wall_clock_seconds", "?")
        tps = entry.get("tests_per_sec", "?")
        sha = entry.get("git_sha", "?")[:8]
        rows.append(f"| {idx} | {ts} | {scope} | {total} | {wall} | {tps} | {sha} |")
    return rows


def render_trend_summary(all_entries: list[Entry]) -> list[str]:
    """Render a 2-line trend summary: mean last-10 vs last-30."""
    last_10 = all_entries[-10:] if len(all_entries) >= 10 else all_entries
    last_30 = all_entries[-30:] if len(all_entries) >= 30 else all_entries

    mean_10 = mean_wall_clock(last_10)
    mean_30 = mean_wall_clock(last_30)
    delta = format_delta(mean_10, mean_30)

    lines = ["", "## Trend summary", ""]
    mean_10_str = f"{mean_10:.1f}s" if mean_10 is not None else "n/a"
    mean_30_str = f"{mean_30:.1f}s" if mean_30 is not None else "n/a"
    lines.append(f"- Mean wall-clock last 10 runs : **{mean_10_str}**")
    lines.append(f"- Mean wall-clock last 30 runs : **{mean_30_str}**")
    lines.append(f"- Delta (10 vs 30)             : **{delta}**")
    return lines


def render_report(log_path: Path, last_n: int = 10) -> str:
    """Build the full markdown report string.

    Pure function: takes a path, returns a string.
    """
    all_entries = load_entries(log_path)
    recent = all_entries[-last_n:] if len(all_entries) > last_n else all_entries

    lines: list[str] = [
        f"# Test suite runtime — last {last_n} runs",
        "",
        f"_Log: `{log_path}`  |  Total entries: {len(all_entries)}_",
        "",
        "## Recent runs",
        "",
    ]
    lines.extend(render_entries_table(recent))
    lines.extend(render_trend_summary(all_entries))
    return "\n".join(lines)


# ── CLI entry point ────────────────────────────────────────────────────────


def _default_log_path() -> Path:
    """Resolve default log path relative to the project root."""
    script_dir = Path(__file__).resolve().parent
    # scripts/observability/ -> project root is two levels up
    project_root = script_dir.parent.parent
    return project_root / ".nwave" / "observability" / "test-runtime-log.jsonl"


def main(argv: list[str] | None = None) -> int:
    """Entry point for CLI invocation."""
    parser = argparse.ArgumentParser(
        description="Render test suite runtime trend report from JSONL telemetry log."
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Path to JSONL telemetry log (default: .nwave/observability/test-runtime-log.jsonl)",
    )
    parser.add_argument(
        "--last",
        type=int,
        default=10,
        help="Number of recent runs to display (default: 10)",
    )
    args = parser.parse_args(argv)

    log_path = args.log or _default_log_path()
    report = render_report(log_path, last_n=args.last)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
