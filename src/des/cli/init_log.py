"""CLI: Initialize execution-log.json for a deliver session.

Usage:
    des-init-log \\
      --project-dir docs/feature/my-feature/deliver \\
      --feature-id my-feature

Creates: {"schema_version": "3.0", "feature_id": "my-feature", "events": []}

Exit codes:
    0 = Success, file created
    1 = Validation error (file already exists, directory missing)
    2 = Usage error (argparse default for missing/invalid arguments)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for init_log CLI."""
    parser = argparse.ArgumentParser(
        prog="des.cli.init_log",
        description="Initialize execution-log.json for a deliver session.",
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Path to the project directory where execution-log.json will be created",
    )
    parser.add_argument(
        "--feature-id",
        required=True,
        help="Feature identifier (kebab-case, e.g., my-feature)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the init_log CLI tool.

    Args:
        argv: Command-line arguments. Uses sys.argv[1:] if None.

    Returns:
        Exit code: 0=success, 1=validation error, 2=usage error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    project_dir = Path(args.project_dir)

    # Validate project directory exists
    if not project_dir.is_dir():
        print(f"Error: Project directory does not exist: {project_dir}")
        return 1

    log_path = project_dir / "execution-log.json"

    # Fail if file already exists
    if log_path.exists():
        print(f"Error: execution-log.json already exists at {log_path}")
        return 1

    # Create execution log with v3.0 schema
    log_data = {
        "schema_version": "3.0",
        "feature_id": args.feature_id,
        "events": [],
    }
    log_path.write_text(json.dumps(log_data, indent=2))

    print(f"Created execution-log.json at {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
