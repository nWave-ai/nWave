"""
nWave Step File Validation Script.

This script validates step files against the canonical TDD phase schema
to ensure all required phases are documented before allowing commits.

Version: 1.0.0
"""

__version__ = "1.0.0"

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# Required TDD phases from canonical schema v3.0
REQUIRED_PHASES = [
    "PREPARE",
    "RED_ACCEPTANCE",
    "RED_UNIT",
    "GREEN",
    "REVIEW",
    "REFACTOR_CONTINUOUS",
    "COMMIT",
]


def load_step_file(file_path: Path) -> dict[str, Any] | None:
    """Load and parse a step file."""
    try:
        with open(file_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading step file: {e}")
        return None


def validate_phase_log(step_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate that all required TDD phases are present in the execution log.

    Args:
        step_data: Parsed step file data

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    # Navigate to phase execution log
    tdd_cycle = step_data.get("tdd_cycle", {})
    phase_tracking = tdd_cycle.get("tdd_phase_tracking", {})
    phase_log = phase_tracking.get("phase_execution_log", [])

    if not phase_log:
        errors.append("No phase_execution_log found in step file")
        return False, errors

    # Check each required phase
    logged_phases = {entry.get("phase_name") for entry in phase_log}

    for required_phase in REQUIRED_PHASES:
        if required_phase not in logged_phases:
            errors.append(f"Missing required phase: {required_phase}")

    # Check phase outcomes
    for entry in phase_log:
        phase_name = entry.get("phase_name", "UNKNOWN")
        outcome = entry.get("outcome", "")
        status = entry.get("status", "")

        if status == "SKIPPED" and not entry.get("justification"):
            errors.append(f"Phase {phase_name} is SKIPPED without justification")

        if outcome not in ["PASS", "SKIP", ""] and status != "SKIPPED":
            if outcome == "FAIL":
                errors.append(f"Phase {phase_name} has FAIL outcome - cannot commit")

    return len(errors) == 0, errors


def validate_step_file(file_path: Path) -> bool:
    """
    Validate a step file for commit readiness.

    Args:
        file_path: Path to the step file

    Returns:
        True if step file is valid and ready for commit
    """
    print(f"Validating step file: {file_path}")

    step_data = load_step_file(file_path)
    if step_data is None:
        return False

    is_valid, errors = validate_phase_log(step_data)

    if errors:
        print("\nValidation errors:")
        for error in errors:
            print(f"  - {error}")
        print()

    if is_valid:
        print("Step file validation PASSED")
    else:
        print("Step file validation FAILED")

    return is_valid


def main() -> int:
    """Main entry point for step file validation."""
    parser = argparse.ArgumentParser(
        description="Validate nWave step files for TDD phase compliance"
    )
    parser.add_argument(
        "step_file",
        type=Path,
        nargs="?",
        help="Path to step file to validate",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate all step files in docs/feature/*/steps/",
    )

    args = parser.parse_args()

    if args.all:
        # Find all step files
        step_files = list(Path("docs/feature").glob("*/steps/*.json"))
        if not step_files:
            print("No step files found")
            return 0

        all_valid = True
        for step_file in step_files:
            if not validate_step_file(step_file):
                all_valid = False

        return 0 if all_valid else 1

    elif args.step_file:
        return 0 if validate_step_file(args.step_file) else 1

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
