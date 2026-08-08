"""CLI: Append a phase entry to execution-log.json with a real UTC timestamp.

Usage:
    des-log-phase \\
      --project-dir docs/feature/build-pipeline-elimination \\
      --step-id 02-03 \\
      --phase GREEN \\
      --status EXECUTED \\
      --data PASS

Writes structured JSON objects (schema v3.0):
    {"sid": "02-03", "p": "GREEN", "s": "EXECUTED", "d": "PASS", "t": "2026-02-10T20:28:18Z"}

stdout (agent sees structured representation):
    sid=02-03 p=GREEN s=EXECUTED d=PASS t=2026-02-10T20:28:18Z

Exit codes:
    0 = Success, entry appended
    1 = Validation error (invalid phase, invalid skip prefix, missing log file)
    2 = Usage error (argparse default for missing/invalid arguments)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from des.cli._log_discovery import find_sibling_logs
from des.domain.tdd_schema import TDDSchemaLoader


try:
    import fcntl

    _HAS_FCNTL = True
except ImportError:  # pragma: no cover - Windows has no fcntl
    _HAS_FCNTL = False


def _append_event_locked(log_path: Path, entry: dict[str, object]) -> None:
    """Append an event under an exclusive file lock (last-writer-wins fix).

    Parallel DELIVER waves run several ``des-log-phase`` processes against the
    same ``execution-log.json``. The read-modify-write below must be serialized
    or interleaved writers silently overwrite each other's appends (issue #51).
    An ``fcntl.flock(LOCK_EX)`` held for the whole read+write window blocks
    concurrent writers until this one finishes. The buffered write is flushed
    and fsync'd *before* the lock is released, so the next writer can never read
    a half-written file. On platforms without ``fcntl`` (Windows) we degrade to
    the previous unlocked behaviour rather than fail.
    """
    with open(log_path, "r+", encoding="utf-8") as handle:
        if _HAS_FCNTL:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            raw = handle.read()
            log_data = json.loads(raw) if raw.strip() else {}
            # Recover an empty/null/non-object root to a fresh dict so a
            # malformed array/scalar root doesn't raise on item assignment.
            if not isinstance(log_data, dict):
                log_data = {}
            if "events" not in log_data:
                log_data["events"] = []
            log_data["events"].append(entry)
            log_data["schema_version"] = "3.0"
            handle.seek(0)
            handle.truncate()
            handle.write(json.dumps(log_data, indent=2))
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            if _HAS_FCNTL:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for log_phase CLI."""
    parser = argparse.ArgumentParser(
        prog="des.cli.log_phase",
        description="Append a phase entry to execution-log.json with a real UTC timestamp.",
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Path to the project directory containing execution-log.json",
    )
    parser.add_argument(
        "--step-id",
        required=True,
        help="Step identifier (e.g., 02-03)",
    )
    parser.add_argument(
        "--phase",
        required=True,
        help="TDD phase name (e.g., GREEN, PREPARE)",
    )
    parser.add_argument(
        "--status",
        required=True,
        choices=["EXECUTED", "SKIPPED"],
        help="Phase execution status",
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Outcome data (e.g., PASS, FAIL, or skip reason with prefix)",
    )
    parser.add_argument(
        "--turns-used",
        type=int,
        default=None,
        help="Optional: number of turns consumed during this step",
    )
    parser.add_argument(
        "--tokens-used",
        type=int,
        default=None,
        help="Optional: number of tokens consumed during this step",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the log_phase CLI tool.

    Args:
        argv: Command-line arguments. Uses sys.argv[1:] if None.

    Returns:
        Exit code: 0=success, 1=validation error, 2=usage error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    schema = TDDSchemaLoader().load()

    # Validate phase name against schema
    if args.phase not in schema.tdd_phases:
        print(
            f"Error: Invalid phase '{args.phase}'. "
            f"Valid phases: {', '.join(schema.tdd_phases)}"
        )
        return 1

    # Validate skip prefix for SKIPPED status
    if args.status == "SKIPPED":
        all_skip_prefixes = schema.valid_skip_prefixes + schema.blocking_skip_prefixes
        has_valid_prefix = any(
            args.data.startswith(prefix) for prefix in all_skip_prefixes
        )
        if not has_valid_prefix:
            print(
                f"Error: SKIPPED status requires a valid skip prefix. "
                f"Valid prefixes: {', '.join(all_skip_prefixes)}"
            )
            return 1

    # Check execution-log.json exists
    project_dir = Path(args.project_dir)
    log_path = project_dir / "execution-log.json"
    if not log_path.exists():
        # Issue #79: --project-dir resolves against the process CWD, so a
        # mid-DELIVER `cd` into a monorepo subdirectory makes the same relative
        # string miss the canonical log. Name the log(s) that DO exist in this
        # worktree so the agent re-points --project-dir instead of re-running
        # des-init-log and forking the audit trail.
        print(f"Error: execution-log.json not found at {log_path.absolute()}")
        siblings = find_sibling_logs(project_dir)
        if siblings:
            print("       An execution log exists elsewhere in this git worktree:")
            for path in siblings:
                print(f"         - {path}")
            print(
                "       The --project-dir was resolved against the current "
                f"working directory ({Path.cwd()}). Re-point --project-dir at "
                "the existing log's directory rather than initializing a "
                "second log."
            )
        return 1

    # Generate real UTC timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build structured entry (v3.0 format)
    entry: dict = {
        "sid": args.step_id,
        "p": args.phase,
        "s": args.status,
        "d": args.data,
        "t": timestamp,
    }
    if args.turns_used is not None and args.tokens_used is not None:
        entry["tu"] = args.turns_used
        entry["tk"] = args.tokens_used

    # JSON read-modify-write, serialized across concurrent writers (issue #51)
    _append_event_locked(log_path, entry)

    # Print entry to stdout (human-readable key=value format)
    parts = [
        f"sid={entry['sid']}",
        f"p={entry['p']}",
        f"s={entry['s']}",
        f"d={entry['d']}",
        f"t={entry['t']}",
    ]
    if "tu" in entry:
        parts.extend([f"tu={entry['tu']}", f"tk={entry['tk']}"])
    print(" ".join(parts))

    return 0


if __name__ == "__main__":
    sys.exit(main())
