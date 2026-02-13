#!/usr/bin/env python3
"""
nWave Step Structure Validator - Pre-commit hook

Validates that step files have the required structure including phase_execution_log.
This runs BEFORE the phase validation to catch malformed step files early.

Version: 1.2.26

Exit codes:
    0 - All step files have valid structure
    1 - Structure validation failed
"""

import json
import sys


__version__ = "1.2.26"

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

REQUIRED_FIELDS = ["task_id", "project_id", "tdd_cycle"]


def validate_step_structure(file_path: str) -> tuple[bool, list[str]]:
    """Validate step file has required structure."""
    issues: list[str] = []

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except Exception as e:
        return False, [f"Cannot read: {e}"]

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            issues.append(f"Missing required field: {field}")

    # Check tdd_cycle structure
    tdd_cycle = data.get("tdd_cycle", {})
    if not tdd_cycle:
        issues.append("Missing tdd_cycle section")
        return False, issues

    # Check phase_execution_log
    phase_log = tdd_cycle.get("phase_execution_log", [])
    if not phase_log:
        issues.append("Missing phase_execution_log - step cannot track TDD phases")
        return False, issues

    if len(phase_log) != 14:
        issues.append(f"phase_execution_log has {len(phase_log)} entries, expected 14")

    # Verify all phases present
    phase_names = {p.get("phase_name") for p in phase_log}
    for phase in REQUIRED_PHASES:
        if phase not in phase_names:
            issues.append(f"Missing phase: {phase}")

    return len(issues) == 0, issues


def main():
    """Validate step files passed as arguments."""
    if len(sys.argv) < 2:
        print("nWave Structure: No files to validate")
        return 0

    all_valid = True
    files_checked = 0

    for file_path in sys.argv[1:]:
        if not file_path.endswith(".json"):
            continue

        files_checked += 1
        is_valid, issues = validate_step_structure(file_path)

        if not is_valid:
            all_valid = False
            print(f"\n❌ {file_path}:")
            for issue in issues:
                print(f"   • {issue}")

    if files_checked == 0:
        return 0

    if all_valid:
        print(f"✅ nWave Structure: {files_checked} step file(s) valid")
        return 0
    else:
        print("\n❌ nWave Structure: COMMIT BLOCKED")
        print("   Step files must have phase_execution_log with all 14 phases")
        print("   Run /nw:split to regenerate step files correctly")
        return 1


if __name__ == "__main__":
    sys.exit(main())
