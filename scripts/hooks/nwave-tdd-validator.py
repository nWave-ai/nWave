#!/usr/bin/env python3
"""
nWave TDD Phase Validator - Pre-commit hook

Validates that all 14 TDD phases are properly executed before allowing commits.
Blocks commits with incomplete phase execution.

Exit codes:
    0 - Validation passed (or no step files staged)
    1 - Validation failed (phases incomplete)
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


# Required TDD phases in order (14 total)
REQUIRED_PHASES = [
    "PREPARE",
    "RED_ACCEPTANCE",
    "RED_UNIT",
    "GREEN_UNIT",
    "CHECK_ACCEPTANCE",
    "GREEN_ACCEPTANCE",
    "REVIEW",
    "REFACTOR_L1",
    "REFACTOR_L2",
    "REFACTOR_L3",
    "REFACTOR_L4",
    "POST_REFACTOR_REVIEW",
    "FINAL_VALIDATE",
    "COMMIT",
]

# Valid prefixes for SKIPPED phases that allow commit
VALID_SKIP_PREFIXES = [
    "BLOCKED_BY_DEPENDENCY:",
    "NOT_APPLICABLE:",
    "APPROVED_SKIP:",
]


def get_staged_step_files() -> list[str]:
    """Get list of step files staged for commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        files = result.stdout.strip().split("\n")

        # Filter for step files
        step_patterns = [
            re.compile(r"steps/\d+-\d+\.json$"),
            re.compile(r"docs/.*/steps/\d+-\d+\.json$"),
        ]

        return [f for f in files if f and any(p.search(f) for p in step_patterns)]
    except Exception:
        return []


def validate_skipped_phase(entry: dict[str, Any]) -> tuple[bool, str]:
    """Validate that a SKIPPED phase has proper justification."""
    blocked_by = entry.get("blocked_by", "")

    if not blocked_by:
        return False, "SKIPPED phase missing blocked_by reason"

    for prefix in VALID_SKIP_PREFIXES:
        if blocked_by.startswith(prefix):
            return True, ""

    return False, f"SKIPPED phase has invalid blocked_by: {blocked_by}"


def validate_step_file(file_path: str) -> tuple[bool, list[dict[str, Any]]]:
    """Validate a step file has all TDD phases properly executed."""
    issues: list[dict[str, Any]] = []

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [{"phase": "N/A", "issue": f"Invalid JSON: {e}"}]
    except FileNotFoundError:
        return False, [{"phase": "N/A", "issue": "File not found"}]
    except Exception as e:
        return False, [{"phase": "N/A", "issue": f"Cannot read: {e}"}]

    # Get phase execution log
    tdd_cycle = data.get("tdd_cycle", {})
    phase_log = tdd_cycle.get("phase_execution_log", [])

    if not phase_log:
        # Check if step is marked as not requiring TDD validation
        if tdd_cycle.get("skip_validation"):
            return True, []
        return False, [{"phase": "N/A", "issue": "No phase_execution_log found"}]

    # Build lookup by phase name
    phase_lookup = {p.get("phase_name"): p for p in phase_log}

    for _i, phase_name in enumerate(REQUIRED_PHASES):
        entry = phase_lookup.get(phase_name)

        if not entry:
            issues.append({"phase": phase_name, "issue": "Phase not in log"})
            continue

        status = entry.get("status", "NOT_EXECUTED")

        if status == "EXECUTED":
            outcome = entry.get("outcome")
            if outcome not in ["PASS", "FAIL"]:
                issues.append(
                    {"phase": phase_name, "issue": f"Invalid outcome: {outcome}"}
                )

        elif status == "IN_PROGRESS":
            issues.append({"phase": phase_name, "issue": "Phase left IN_PROGRESS"})

        elif status == "NOT_EXECUTED":
            issues.append({"phase": phase_name, "issue": "Phase NOT_EXECUTED"})

        elif status == "SKIPPED":
            is_valid, msg = validate_skipped_phase(entry)
            if not is_valid:
                issues.append({"phase": phase_name, "issue": msg})

    return len(issues) == 0, issues


def extract_step_id(file_path: str) -> str:
    """Extract step ID from file path (e.g., '01-02' from 'steps/01-02.json')."""
    import os

    basename = os.path.basename(file_path)
    return basename.replace(".json", "")


def get_staged_progress_file() -> bool:
    """Check if .develop-progress.json is staged."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return ".develop-progress.json" in result.stdout
    except Exception:
        return False


def validate_progress_file(step_files: list[str]) -> tuple[bool, list[str]]:
    """Validate progress file consistency with step files.

    Args:
        step_files: List of step files being committed

    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues: list[str] = []

    # Find progress file (could be in docs/feature/{project}/ or root)
    progress_paths = [
        Path(".develop-progress.json"),
    ]

    # Try to find project-specific progress file from step file paths
    if step_files:
        for sf in step_files:
            parts = Path(sf).parts
            for i, part in enumerate(parts):
                if part == "steps" and i > 0:
                    # Found steps dir, progress file should be one level up
                    parent = Path(*parts[:i])
                    progress_paths.insert(0, parent / ".develop-progress.json")
                    break

    progress_file = None
    for p in progress_paths:
        if p.exists():
            progress_file = p
            break

    if not progress_file:
        # No progress file - this is OK if no active session
        return True, []

    try:
        with open(progress_file, encoding="utf-8") as f:
            progress = json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        return False, [f"Cannot read progress file: {e}"]

    # Extract step IDs being committed
    committed_step_ids = {extract_step_id(sf) for sf in step_files}

    # Check if progress file is also staged when step files are staged
    progress_staged = get_staged_progress_file()

    # Get completed steps from progress file
    completed_steps = set(progress.get("completed_steps", []))
    current_step = progress.get("current_step")

    # Validate: if committing a step, it should be current_step or in completed_steps
    for step_id in committed_step_ids:
        if step_id not in completed_steps and step_id != current_step:
            issues.append(
                f"Step {step_id} not tracked in progress file "
                f"(current_step={current_step}, completed={len(completed_steps)})"
            )

    # Warn if progress file not staged but step files are
    if step_files and not progress_staged and progress_file.exists():
        issues.append(f"⚠️  Progress file not staged - run: git add {progress_file}")

    return len(issues) == 0, issues


def main():
    """Main validation entry point."""
    # Check for staged step files
    step_files = get_staged_step_files()

    if not step_files:
        # No step files staged - check for .develop-progress.json
        progress_file = Path(".develop-progress.json")
        if not progress_file.exists():
            print("nWave TDD: No active session, no step files staged")
            return 0

        # Active session but no step files - warn but allow
        print("nWave TDD: Active session, no step files staged (OK)")
        return 0

    # Validate each staged step file
    all_valid = True
    print(f"nWave TDD: Validating {len(step_files)} step file(s)...")

    for step_file in step_files:
        is_valid, issues = validate_step_file(step_file)

        if not is_valid:
            all_valid = False
            print(f"\n❌ {step_file}:")
            for issue in issues[:5]:  # Show first 5 issues
                print(f"   • {issue['phase']}: {issue['issue']}")
            if len(issues) > 5:
                print(f"   ... and {len(issues) - 5} more issues")

    # Validate progress file consistency
    progress_valid, progress_issues = validate_progress_file(step_files)
    if not progress_valid:
        all_valid = False
        print("\n❌ Progress file issues:")
        for issue in progress_issues:
            print(f"   • {issue}")

    if all_valid:
        print("✅ nWave TDD: All phases validated")
        return 0
    else:
        print("\n❌ nWave TDD: COMMIT BLOCKED - Complete all 14 phases first")
        print("   Phases: PREPARE → RED → GREEN → REVIEW → REFACTOR → COMMIT")
        return 1


if __name__ == "__main__":
    sys.exit(main())
