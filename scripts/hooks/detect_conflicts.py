#!/usr/bin/env python3
"""Conflict Detection Hook

Detects when related files (agent + catalog) change together.
Suggests manual review before commit.
"""

import subprocess
import sys


# Color codes
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"


def get_staged_files():
    """Get list of staged files.

    Returns:
        list: List of staged file paths, or empty list if none
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            check=True,
            capture_output=True,
            text=True,
        )
        files = result.stdout.strip().split("\n") if result.stdout.strip() else []
        return files
    except subprocess.CalledProcessError:
        return []


def main():
    """Check for file conflicts."""
    print(f"{BLUE}Checking for file conflicts...{NC}")

    # Define related file pairs that should not change together
    # Format: (pattern1, pattern2)
    conflict_pairs = [
        ("nWave/agents/", "nWave/commands/"),
        ("nWave/templates/", "nWave/agents/"),
    ]

    # Get list of staged files
    staged_files = get_staged_files()

    if not staged_files:
        print(f"{BLUE}No staged files to check{NC}")
        return 0

    # Track if conflicts found
    conflicts_found = False

    # Check for conflict pairs
    for pattern1, pattern2 in conflict_pairs:
        # Check if any files matching patterns are staged
        files_pattern1 = [f for f in staged_files if f.startswith(pattern1)]
        files_pattern2 = [f for f in staged_files if f.startswith(pattern2)]

        # If both patterns have changes, flag as conflict
        if files_pattern1 and files_pattern2:
            conflicts_found = True

            print()
            print(f"{YELLOW}CONFLICT DETECTED: Related files changed together{NC}")
            print(f"{YELLOW}Files affected:{NC}")

            for f in files_pattern1:
                print(f"  [1] {f}")
            for f in files_pattern2:
                print(f"  [2] {f}")

            print()
            print(f"{YELLOW}Discrepancy Details:{NC}")
            print(
                f"  - Files from pattern '{pattern1}' and '{pattern2}' modified in same commit"
            )
            print(
                "  - This may indicate incomplete refactoring or coupling between agent/catalog"
            )
            print()
            print(f"{YELLOW}Recommendation:{NC}")
            print("  - Review changes manually to ensure consistency")
            print("  - Verify agent behavior matches catalog documentation")
            print(
                "  - Consider splitting into separate commits if logically independent"
            )
            print()

    if conflicts_found:
        print(f"{YELLOW}Review suggested before committing{NC}")
        print(f"{YELLOW}Bypass with: git commit --no-verify{NC}")
        return 0  # Warning only, non-blocking
    else:
        print(f"{BLUE}No file conflicts detected{NC}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
