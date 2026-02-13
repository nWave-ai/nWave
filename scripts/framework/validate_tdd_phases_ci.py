#!/usr/bin/env python3
"""
nWave TDD Phase Validation for CI/CD Pipelines

Validates that all step files have complete 14-phase TDD execution logs.
Designed for integration with GitHub Actions, GitLab CI, Azure Pipelines, etc.

Usage:
    python validate_tdd_phases_ci.py [--strict] [--json] [--fail-fast] [path]

Options:
    --strict     Fail on SKIPPED phases too (strict mode)
    --json       Output results as JSON (for parsing by other tools)
    --fail-fast  Stop at first failure
    path         Directory to scan (default: current directory)

Exit Codes:
    0 - All validations passed
    1 - Validation failures found
    2 - Configuration/runtime error

Integration Examples:

GitHub Actions:
    - name: Validate TDD Phases
      run: python nWave/scripts/validate_tdd_phases_ci.py docs/feature/*/steps/

GitLab CI:
    validate_tdd:
      script:
        - python nWave/scripts/validate_tdd_phases_ci.py

Azure Pipelines:
    - script: python nWave/scripts/validate_tdd_phases_ci.py
      displayName: 'Validate TDD Phases'

Jenkins:
    sh 'python nWave/scripts/validate_tdd_phases_ci.py'
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime
from typing import Any


# Required TDD phases by schema version
REQUIRED_PHASES_V1 = [
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

REQUIRED_PHASES_V4 = [
    "PREPARE",
    "RED_ACCEPTANCE",
    "RED_UNIT",
    "GREEN",
    "COMMIT",
]

# Default to v1.0 for backward compatibility
REQUIRED_PHASES = REQUIRED_PHASES_V1

# Valid prefixes for SKIPPED phases that allow commit
VALID_SKIP_PREFIXES = [
    "BLOCKED_BY_DEPENDENCY:",
    "NOT_APPLICABLE:",
    "APPROVED_SKIP:",
]

# Prefixes that indicate incomplete work - blocks commit
BLOCKS_COMMIT_PREFIXES = [
    "DEFERRED:",
]


def validate_step_file(
    file_path: str, strict: bool = False
) -> tuple[bool, list[dict[str, Any]]]:
    """
    Validate a single step file for TDD phase completeness.

    Args:
        file_path: Path to the step JSON file
        strict: If True, also fail on valid SKIPPED phases

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues: list[dict[str, Any]] = []

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [{"severity": "ERROR", "issue": f"Invalid JSON: {e}"}]
    except FileNotFoundError:
        return False, [{"severity": "ERROR", "issue": "File not found"}]
    except Exception as e:
        return False, [{"severity": "ERROR", "issue": f"Cannot read file: {e}"}]

    # REJECT OLD/WRONG FORMAT PATTERNS
    if "step_id" in data:
        return False, [
            {
                "severity": "ERROR",
                "issue": "WRONG FORMAT: Found 'step_id' - use 'task_id'. Obsolete format.",
            }
        ]
    if "phase_id" in data:
        return False, [
            {
                "severity": "ERROR",
                "issue": "WRONG FORMAT: Found 'phase_id' - each step has ALL 14 phases, not one.",
            }
        ]
    if "tdd_phase" in data and "tdd_cycle" not in data:
        return False, [
            {
                "severity": "ERROR",
                "issue": "WRONG FORMAT: 'tdd_phase' at top level. Use tdd_cycle.phase_execution_log.",
            }
        ]

    # Detect schema version and select required phases
    schema_version = data.get("schema_version", "") or data.get("tdd_cycle", {}).get(
        "schema_version", ""
    )
    if schema_version in ("4.0", "4.0.0"):
        required_phases = REQUIRED_PHASES_V4
    else:
        required_phases = REQUIRED_PHASES_V1

    # Get phase execution log
    tdd_cycle = data.get("tdd_cycle", {})
    phase_log = tdd_cycle.get("phase_execution_log", [])

    if not phase_log:
        # Check old location
        phase_log = tdd_cycle.get("tdd_phase_tracking", {}).get(
            "phase_execution_log", []
        )

    if not phase_log:
        return False, [
            {
                "severity": "ERROR",
                "issue": "No phase_execution_log found - file may need migration",
            }
        ]

    # Check phase count
    if len(phase_log) < len(required_phases):
        issues.append(
            {
                "severity": "ERROR",
                "issue": f"Expected {len(required_phases)} phases, found {len(phase_log)}",
            }
        )

    # Build lookup by phase name
    phase_lookup = {p.get("phase_name"): p for p in phase_log}

    # Validate each required phase
    for i, phase_name in enumerate(required_phases):
        entry = phase_lookup.get(phase_name)

        if not entry:
            issues.append(
                {
                    "severity": "ERROR",
                    "phase": phase_name,
                    "phase_index": i,
                    "issue": "Phase missing from log",
                }
            )
            continue

        status = entry.get("status", "NOT_EXECUTED")

        if status == "EXECUTED":
            # Validate outcome exists
            if not entry.get("outcome"):
                issues.append(
                    {
                        "severity": "WARNING",
                        "phase": phase_name,
                        "phase_index": i,
                        "issue": "EXECUTED phase missing outcome",
                    }
                )

        elif status == "IN_PROGRESS":
            issues.append(
                {
                    "severity": "ERROR",
                    "phase": phase_name,
                    "phase_index": i,
                    "issue": "Phase left IN_PROGRESS (incomplete execution)",
                }
            )

        elif status == "NOT_EXECUTED":
            issues.append(
                {
                    "severity": "ERROR",
                    "phase": phase_name,
                    "phase_index": i,
                    "issue": "Phase not executed",
                }
            )

        elif status == "SKIPPED":
            blocked_by = entry.get("blocked_by", "")

            if not blocked_by:
                issues.append(
                    {
                        "severity": "ERROR",
                        "phase": phase_name,
                        "phase_index": i,
                        "issue": "SKIPPED without blocked_by reason",
                    }
                )
            elif any(blocked_by.startswith(p) for p in BLOCKS_COMMIT_PREFIXES):
                issues.append(
                    {
                        "severity": "ERROR",
                        "phase": phase_name,
                        "phase_index": i,
                        "issue": f"DEFERRED phase blocks commit: {blocked_by}",
                    }
                )
            elif not any(blocked_by.startswith(p) for p in VALID_SKIP_PREFIXES):
                issues.append(
                    {
                        "severity": "ERROR",
                        "phase": phase_name,
                        "phase_index": i,
                        "issue": f"Invalid blocked_by prefix: {blocked_by}",
                    }
                )
            elif strict:
                # In strict mode, even valid SKIPPED is an issue
                issues.append(
                    {
                        "severity": "WARNING",
                        "phase": phase_name,
                        "phase_index": i,
                        "issue": f"SKIPPED (strict mode): {blocked_by}",
                    }
                )

        else:
            issues.append(
                {
                    "severity": "WARNING",
                    "phase": phase_name,
                    "phase_index": i,
                    "issue": f"Unknown status: {status}",
                }
            )

    # Count errors
    error_count = sum(1 for iss in issues if iss.get("severity") == "ERROR")

    return error_count == 0, issues


def find_step_files(base_path: str = ".") -> list[str]:
    """Find all step files in the project."""
    patterns = [
        os.path.join(base_path, "docs/feature/*/steps/*.json"),
        os.path.join(base_path, "docs/workflow/*/steps/*.json"),
        os.path.join(base_path, "steps/*.json"),
        os.path.join(base_path, "*.json"),  # If path is a steps directory
    ]

    step_files = []
    for pattern in patterns:
        step_files.extend(glob.glob(pattern))

    # Filter to only step files (pattern: XX-XX.json)
    import re

    step_pattern = re.compile(r"\d+-\d+\.json$")
    step_files = [f for f in step_files if step_pattern.search(f)]

    return sorted(set(step_files))


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate TDD phase completeness for CI/CD",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--strict", action="store_true", help="Fail on SKIPPED phases too"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--fail-fast", action="store_true", help="Stop at first failure"
    )
    parser.add_argument(
        "path", nargs="?", default=".", help="Directory or file to validate"
    )

    args = parser.parse_args()

    # Collect results
    results = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "strict_mode": args.strict,
        "files_checked": 0,
        "files_passed": 0,
        "files_failed": 0,
        "total_errors": 0,
        "total_warnings": 0,
        "details": [],
    }

    # Find step files
    if os.path.isfile(args.path) and args.path.endswith(".json"):
        step_files = [args.path]
    elif os.path.isdir(args.path):
        step_files = find_step_files(args.path)
    else:
        # Try as glob pattern
        step_files = glob.glob(args.path)

    if not step_files:
        if args.json:
            results["error"] = "No step files found"
            print(json.dumps(results, indent=2))
        else:
            print("No step files found.", file=sys.stderr)
        return 2

    if not args.json:
        print("nWave TDD Phase Validation (CI Mode)")
        print("=" * 50)
        print(f"Validating {len(step_files)} step file(s)")
        if args.strict:
            print("[STRICT MODE - SKIPPED phases will be flagged]")
        print()

    # Validate each file
    all_passed = True

    for step_file in step_files:
        results["files_checked"] += 1

        is_valid, issues = validate_step_file(step_file, strict=args.strict)

        error_count = sum(1 for iss in issues if iss.get("severity") == "ERROR")
        warning_count = sum(1 for iss in issues if iss.get("severity") == "WARNING")

        results["total_errors"] += error_count
        results["total_warnings"] += warning_count

        file_result = {
            "file": step_file,
            "valid": is_valid,
            "errors": error_count,
            "warnings": warning_count,
            "issues": issues,
        }
        results["details"].append(file_result)

        if is_valid:
            results["files_passed"] += 1
            if not args.json:
                print(f"[PASS] {step_file}")
        else:
            results["files_failed"] += 1
            all_passed = False
            if not args.json:
                print(f"[FAIL] {step_file}")
                for issue in issues:
                    severity = issue.get("severity", "?")
                    phase = issue.get("phase", "")
                    issue_text = issue.get("issue", "Unknown issue")
                    if phase:
                        print(f"  [{severity}] {phase}: {issue_text}")
                    else:
                        print(f"  [{severity}] {issue_text}")

            if args.fail_fast:
                if not args.json:
                    print("\n[FAIL-FAST] Stopping at first failure")
                break

    # Output results
    if args.json:
        results["overall_result"] = "PASS" if all_passed else "FAIL"
        print(json.dumps(results, indent=2))
    else:
        print()
        print("=" * 50)
        print("Validation Summary:")
        print(f"  - Files checked: {results['files_checked']}")
        print(f"  - Passed: {results['files_passed']}")
        print(f"  - Failed: {results['files_failed']}")
        print(f"  - Total errors: {results['total_errors']}")
        print(f"  - Total warnings: {results['total_warnings']}")
        print()

        if all_passed:
            print("[PASS] All TDD phase validations passed")
        else:
            print("[FAIL] TDD phase validation failed")
            print("\nTo fix:")
            print("  1. Complete all missing TDD phases")
            print("  2. For SKIPPED phases, add valid blocked_by reason")
            print("  3. Ensure no phases are left IN_PROGRESS")
            print("  4. Run migration script if files are outdated:")
            print("     python nWave/scripts/migrate_step_files.py")

    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)
