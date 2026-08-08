"""CLI: Initialize execution-log.json for a deliver session.

Usage:
    des-init-log \\
      --project-dir docs/feature/my-feature/deliver \\
      --feature-id my-feature

Creates: {"schema_version": "5.0", "feature_id": "my-feature", "events": []}

Workflow-mode awareness (ADR-028 D4.1):
    The execution log belongs to the classic, roadmap-based DELIVER spine.
    The atdd_pure spine is roadmap-free and execution-log-free, so when the
    project's `.nwave/config.yaml` declares `workflow.mode: atdd_pure`,
    des-init-log refuses to create the log and exits non-zero. Any other
    mode -- `classic`, an absent key, or an absent config file -- is treated
    as classic and behaves exactly as before (zero regression).

Exit codes:
    0 = Success, file created
    1 = Validation error (file already exists, directory missing) or
        atdd_pure refusal (the execution log must not exist in that mode)
    2 = Usage error (argparse default for missing/invalid arguments)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from des.cli._log_discovery import describe_other_logs, find_other_logs_in_worktree
from des.domain.result import Failure


ATDD_PURE_MODE = "atdd_pure"


def _strip_inline_comment(value: str) -> str:
    """Drop a trailing ` # comment` from a YAML scalar (outside quotes)."""
    in_single = in_double = False
    for index, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            if index == 0 or value[index - 1].isspace():
                return value[:index]
    return value


def _unquote(value: str) -> str:
    """Strip matching surrounding single or double quotes from a scalar."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _parse_workflow_mode(text: str) -> str | None:
    """Extract `workflow.mode` from a machine-managed `.nwave/config.yaml`.

    Stdlib-only parser (the DES bundle installs standalone and must not depend
    on PyYAML). Handles the simple two-level `workflow:` -> `mode:` nesting
    written by scripts/automation/atdd_pure_falsifier_gate.py, tolerating
    indentation, blank lines, comments, and quoted/unquoted values.

    Returns the mode string, or None if the key is absent.
    """
    inside_workflow = False
    workflow_indent = -1
    for raw_line in text.splitlines():
        without_comment = _strip_inline_comment(raw_line)
        if not without_comment.strip():
            continue
        indent = len(without_comment) - len(without_comment.lstrip())
        stripped = without_comment.strip()
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()

        if not inside_workflow:
            if key == "workflow" and not value:
                inside_workflow = True
                workflow_indent = indent
            continue

        # Inside the `workflow:` block: a key at or below its indent ends it.
        if indent <= workflow_indent:
            inside_workflow = False
            if key == "workflow" and not value:
                inside_workflow = True
                workflow_indent = indent
            continue
        if key == "mode" and value:
            return _unquote(value)
    return None


def _resolve_workflow_mode(project_dir: Path) -> str:
    """Resolve `workflow.mode` from {project_dir}/.nwave/config.yaml.

    Absent config file or absent key -> "classic" (the default). Uses a
    stdlib-only parser so the standalone DES bundle stays PyYAML-free.
    """
    config_path = project_dir / ".nwave" / "config.yaml"
    if not config_path.exists():
        return "classic"
    return _parse_workflow_mode(config_path.read_text()) or "classic"


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
    parser.add_argument(
        "--allow-duplicate-log",
        action="store_true",
        help=(
            "Create the log even when another execution-log.json for the same "
            "feature id already exists elsewhere under the git worktree root. "
            "Use only when a second, deliberately separate log is intended "
            "(issue #79)."
        ),
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

    # Refuse under the atdd_pure spine: it is roadmap-free and
    # execution-log-free (ADR-028 D4.1). No log is created.
    if _resolve_workflow_mode(project_dir) == ATDD_PURE_MODE:
        print(
            "Error: workflow.mode is atdd_pure -- the ATDD-pure spine is "
            "roadmap-free and execution-log-free (ADR-028 D4.1).\n"
            "       No execution-log.json is created. The atdd_pure DELIVER "
            "spine tracks progress via the AT-completion ledger instead.\n"
            "       To create an execution log, set workflow.mode to classic "
            "in .nwave/config.yaml.",
            file=sys.stderr,
        )
        return 1

    log_path = project_dir / "execution-log.json"

    # Fail if file already exists
    if log_path.exists():
        print(f"Error: execution-log.json already exists at {log_path}")
        return 1

    # Issue #79: a relative --project-dir resolves against the process CWD. An
    # agent that cd'd into a monorepo subdirectory mid-DELIVER would otherwise
    # start a SECOND, divergent log for a feature that already has a canonical
    # one elsewhere in this worktree. Fail loudly naming both paths; the
    # deliberate-second-log case has an explicit opt-out.
    if not args.allow_duplicate_log:
        scan = find_other_logs_in_worktree(project_dir, feature_id=args.feature_id)
        if isinstance(scan, Failure):
            # The guard could not run. Initialization still proceeds: this check
            # is a safety net, not a precondition, and des-init-log must remain
            # usable outside a git worktree. But the operator is told the net
            # was not in place — a silent skip here would recreate exactly the
            # undetected fork the guard exists to prevent.
            print(
                "Warning: could not check for an existing execution log "
                f"({scan.error}). Proceeding without the duplicate-log guard; "
                "if this feature already has a log elsewhere, the audit trail "
                "is now split (issue #79).",
                file=sys.stderr,
            )
        elif scan.value:
            listed = "\n".join(describe_other_logs(scan))
            print(
                f"Error: an execution log for feature '{args.feature_id}' already "
                f"exists elsewhere in this git worktree.\n"
                f"       would create: {log_path.absolute()}\n"
                f"       existing log(s):\n{listed}\n"
                "       Creating a second log splits the DELIVER audit trail "
                "(issue #79). Point --project-dir at the existing log's "
                "directory, or pass --allow-duplicate-log when a separate log "
                "is intended.",
                file=sys.stderr,
            )
            return 1

    # Create execution log with the ADR-025 v5.0 (3-phase canon) schema, so new
    # DELIVER logs default to RED/GREEN/COMMIT (issue #65). Legacy v4 logs stay
    # valid for audit-log replay via per-log dispatch.
    log_data = {
        "schema_version": "5.0",
        "feature_id": args.feature_id,
        "events": [],
    }
    log_path.write_text(json.dumps(log_data, indent=2))

    print(f"Created execution-log.json at {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
