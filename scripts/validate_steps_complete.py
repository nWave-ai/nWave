#!/usr/bin/env python3
"""
CRITICAL INVARIANT GATE: Validate All Steps Complete Before Finalize

Usage: python3 validate_steps_complete.py <project-id>
Exit code 0: Safe to finalize
Exit code 1: Blocked - incomplete steps found
Exit code 2: Invalid arguments or file errors
"""

__version__ = "1.0.0"

import glob
import json
import os
import sys
from typing import Any


def validate_all_steps_complete(
    project_id: str,
) -> tuple[bool, list[dict[str, Any]], str]:
    """Verify ALL steps have COMMIT phase with outcome=PASS."""
    steps_dir = f"docs/feature/{project_id}/steps"

    if not os.path.exists(steps_dir):
        return False, [], f"BLOCKER: Steps directory not found: {steps_dir}"

    step_files = sorted(glob.glob(os.path.join(steps_dir, "*.json")))

    if not step_files:
        return False, [], f"BLOCKER: No step files found in {steps_dir}"

    incomplete_steps = []

    for step_file in step_files:
        try:
            with open(step_file) as f:
                step_data = json.load(f)
        except Exception as e:
            incomplete_steps.append(
                {
                    "file": os.path.basename(step_file),
                    "task_id": "unknown",
                    "reason": f"Error reading file: {e!s}",
                }
            )
            continue

        task_id = step_data.get("task_specification", {}).get("task_id", "unknown")
        tdd_cycle = step_data.get("tdd_cycle", {})
        phase_log = tdd_cycle.get("phase_execution_log", [])

        if not phase_log:
            incomplete_steps.append(
                {
                    "file": os.path.basename(step_file),
                    "task_id": task_id,
                    "reason": "INVALID FORMAT: phase_execution_log is empty (old format?)",
                }
            )
            continue

        commit_phase = None
        for phase in phase_log:
            if phase.get("phase_name") == "COMMIT":
                commit_phase = phase
                break

        if not commit_phase:
            incomplete_steps.append(
                {
                    "file": os.path.basename(step_file),
                    "task_id": task_id,
                    "reason": "COMMIT phase not found in phase_execution_log",
                }
            )
            continue

        outcome = commit_phase.get("outcome")
        if outcome != "PASS":
            status = commit_phase.get("status", "unknown")
            incomplete_steps.append(
                {
                    "file": os.path.basename(step_file),
                    "task_id": task_id,
                    "reason": f"COMMIT phase outcome={outcome}, status={status} (expected outcome=PASS)",
                }
            )

    if incomplete_steps:
        error_lines = [
            "",
            "=" * 70,
            "🛑 CRITICAL INVARIANT VIOLATION - FINALIZE BLOCKED",
            "=" * 70,
            "",
            f"Project: {project_id}",
            f"Incomplete steps: {len(incomplete_steps)} / {len(step_files)}",
            "",
            "The following steps do NOT have COMMIT phase with outcome=PASS:",
            "",
        ]

        for step in incomplete_steps:
            error_lines.append(
                f"  ❌ {step.get('task_id', step['file'])}: {step['reason']}"
            )

        error_lines.extend(
            [
                "",
                "RESOLUTION REQUIRED:",
                "  1. Execute all incomplete steps through full 14-phase TDD",
                "  2. Ensure each step reaches COMMIT phase with outcome=PASS",
                "  3. Re-run /nw:finalize after all steps complete",
                "",
                "This gate exists to prevent 'silent completion' where features",
                "are archived without actually being implemented.",
                "",
                "=" * 70,
            ]
        )

        return False, incomplete_steps, "\n".join(error_lines)

    return (
        True,
        [],
        f"✅ CRITICAL INVARIANT PASSED: All {len(step_files)} steps have COMMIT/PASS",
    )


def main() -> None:
    """Main entry point."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <project-id>")
        sys.exit(2)

    project_id = sys.argv[1]
    print(f"Validating steps for project: {project_id}")
    print("-" * 50)

    all_complete, _incomplete, message = validate_all_steps_complete(project_id)
    print(message)

    if not all_complete:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
